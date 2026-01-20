# SENTINEL AI - Karar Motoru (Orchestrator)
# Action Planner v2: Intent-Based Architecture
#
# Yeni Akis (v2):
#   User Input -> Intent Resolver -> Policy Gate -> Tool Registry -> Command Builder -> Execution
#
# LLM sadece intent belirler, tool/arguman/risk belirleme deterministic.

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# V2 Imports
from src.ai.schemas import (
    Intent,
    IntentType,
    ToolSpec,
    FinalCommand,
    RiskLevel,
    # Legacy (backward compat)
    ToolCommand,
    AIResponse,
)
from src.ai.intent_resolver import IntentResolver, get_intent_resolver
from src.ai.tool_registry import build_tool_spec, get_tool_for_intent
from src.ai.command_builder import CommandBuilder, get_command_builder
from src.ai.policy_gate import PolicyGate, get_policy_gate

load_dotenv()


class AIOrchestrator:
    """
    Action Planner v2 - Katmanli Karar Motoru.
    
    Yeni Mimari:
    1. Intent Resolver: LLM sadece kullanici niyetini belirler
    2. Policy Gate: Opsiyonel intent kontrolu (varsayilan kapali)
    3. Tool Registry: Intent -> Tool mapping (deterministic)
    4. Command Builder: ToolSpec -> FinalCommand (deterministic)
    
    Avantajlar:
    - LLM daha dar scope'ta calisir (sadece intent)
    - Tool metadata (requires_root, risk) statik, LLM'den bagimsiz
    - Her katman ayri test edilebilir
    - Policy gate kolayca eklenip cikartilabilir
    """
    
    def __init__(self, model: str = "whiterabbitneo", coordinator=None):
        """
        Orchestrator'i baslat.
        
        Args:
            model: Kullanilacak LLM modeli (whiterabbitneo veya llama3:8b)
            coordinator: SentinelCoordinator instance (tool execution için)
        """
        self._model = model
        self._coordinator = coordinator
        
        # V2 Components
        self._intent_resolver = IntentResolver(model=model)
        self._command_builder = CommandBuilder()
        self._policy_gate = PolicyGate()
        
        # Cache
        self._last_intent: Optional[Intent] = None
        self._last_tool_spec: Optional[ToolSpec] = None
    
    # =========================================================================
    # V2 API - Yeni Katmanli Mimari
    # =========================================================================
    
    def process_v2(
        self,
        user_input: str,
        target: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Kullanici girdisini isle (V2 - Katmanli Mimari).
        
        Args:
            user_input: Kullanicinin dogal dildeki talebi
            target: Hedef IP/URL (UI'dan gelebilir)
        
        Returns:
            {
                "success": bool,
                "command": FinalCommand veya None,
                "message": str,
                "intent": Intent,
                "needs_clarification": bool,
                "policy_warning": str veya None
            }
        """
        result = {
            "success": False,
            "command": None,
            "message": "",
            "intent": None,
            "needs_clarification": False,
            "policy_warning": None
        }
        
        # =====================================================================
        # 1. INTENT RESOLVER - LLM sadece niyet belirler
        # =====================================================================
        print(f"[Orchestrator] Resolving intent for: '{user_input[:50]}...'")
        
        intent = self._intent_resolver.resolve(user_input, target)
        self._last_intent = intent
        result["intent"] = intent
        
        # Netlestime gerekli mi?
        if intent.needs_clarification:
            result["message"] = intent.clarification_reason or "Lutfen talebi netlestirin."
            result["needs_clarification"] = True
            return result
        
        # Bilgi sorusu mu?
        if intent.intent_type == IntentType.INFO_QUERY:
            result["success"] = True
            result["message"] = "Bu bir bilgi sorusu, komut gerektirmiyor."
            return result
        
        # Unknown intent
        if intent.intent_type == IntentType.UNKNOWN:
            result["message"] = "Talebi anlayamadim. Lutfen daha acik belirtin."
            result["needs_clarification"] = True
            return result
        
        # =====================================================================
        # 2. POLICY GATE - Opsiyonel kontrol
        # =====================================================================
        allowed, policy_message = self._policy_gate.check(intent.intent_type)
        
        if not allowed:
            result["message"] = policy_message
            return result
        
        if policy_message:
            result["policy_warning"] = policy_message
        
        # =====================================================================
        # 3. TOOL REGISTRY - Intent -> ToolSpec
        # =====================================================================
        # Target: UI'dan gelen, intent'ten cikan, veya params'tan
        final_target = target or intent.target or intent.params.get("target")
        
        # Debug logging
        print(f"[Orchestrator] Target resolution:")
        print(f"  UI target: {target}")
        print(f"  Intent target: {intent.target}")
        print(f"  Intent params: {intent.params}")
        print(f"  Final target: {final_target}")
        
        # Target validation
        if not final_target:
            result["message"] = "Hedef IP adresi belirtilmedi. Lütfen 'Hedef' alanına IP/domain girin."
            result["needs_clarification"] = True
            return result
        
        tool_spec = build_tool_spec(
            intent_type=intent.intent_type,
            target=final_target,
            params=intent.params
        )
        
        if tool_spec is None:
            result["message"] = f"Bu intent icin tool bulunamadi: {intent.intent_type.value}"
            return result
        
        self._last_tool_spec = tool_spec
        
        # =====================================================================
        # 4. COMMAND BUILDER - ToolSpec -> FinalCommand
        # =====================================================================
        tool_def = get_tool_for_intent(intent.intent_type)
        explanation = tool_def.description if tool_def else ""
        
        command, error = self._command_builder.build(tool_spec, explanation)
        
        if error:
            result["message"] = f"Komut olusturulamadi: {error}"
            return result
        
        # =====================================================================
        # 5. BASARILI SONUC
        # =====================================================================
        result["success"] = True
        result["command"] = command
        result["message"] = f"Komut hazir: {command.to_display_string()}"
        
        return result
    
    def process(
        self,
        user_input: str,
        target: Optional[str] = None
    ) -> AIResponse:
        """
        Kullanici girdisini isle (Backward Compatible API).
        
        V2 API'yi cagirir ve sonucu eski AIResponse formatina donusturur.
        UI ile uyumluluk icin.
        """
        v2_result = self.process_v2(user_input, target)
        
        # FinalCommand -> ToolCommand donusumu (legacy compat)
        tool_command = None
        if v2_result["command"]:
            cmd = v2_result["command"]
            tool_command = ToolCommand(
                tool=cmd.executable,
                arguments=cmd.arguments,
                requires_root=cmd.requires_root,
                risk_level=cmd.risk_level,
                explanation=cmd.explanation
            )
        
        return AIResponse(
            command=tool_command,
            message=v2_result["message"],
            needs_clarification=v2_result["needs_clarification"]
        )
    
    # =========================================================================
    # STATUS & DIAGNOSTICS
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """
        Orchestrator durumunu doner.
        """
        return {
            "version": "v2",
            "model": self._model,
            "llm_available": self._intent_resolver.check_available(),
            "policy_enabled": self._policy_gate.is_enabled,
            "policy_status": self._policy_gate.get_policy_status(),
            "last_intent": self._last_intent.intent_type.value if self._last_intent else None,
        }
    
    def check_services(self, force: bool = False) -> tuple:
        """
        Servis durumlarini kontrol et (legacy compat).
        
        Returns:
            (local_available, cloud_available)
        """
        local = self._intent_resolver.check_available()
        cloud = os.getenv("OPENAI_API_KEY") is not None
        return (local, cloud)
    
    def set_model(self, model: str):
        """Kullanilacak modeli degistir"""
        self._model = model
        self._intent_resolver = IntentResolver(model=model)
    
    def enable_policy(self):
        """Policy gate'i aktif et"""
        self._policy_gate.enable()
    
    def disable_policy(self):
        """Policy gate'i devre disi birak"""
        self._policy_gate.disable()
    
    # =========================================================================
    # TOOL EXECUTION - AI-Driven Workflow
    # =========================================================================
    
    def execute_intent(self, user_input: str, target: Optional[str] = None) -> Dict[str, Any]:
        """
        AI-driven tool execution: Intent → Tool selection → Auto-execute.
        
        Workflow:
        1. process_v2() ile intent belirle ve komut oluştur
        2. Intent type'a göre doğru coordinator metodunu çağır
        3. Tool execution başlat (async via signals)
        
        Args:
            user_input: Kullanıcı girdisi ("192.168.1.1'i tara")
            target: Opsiyonel hedef (UI'dan gelebilir)
        
        Returns:
            {
                "success": bool,
                "message": str,
                "intent": IntentType,
                "tool_started": bool,
                "execution_id": str veya None
            }
        """
        result = {
            "success": False,
            "message": "",
            "intent": None,
            "tool_started": False,
            "execution_id": None
        }
        
        # Coordinator yoksa hata
        if not self._coordinator:
            result["message"] = "SentinelCoordinator not initialized. Cannot execute tools."
            return result
        
        # AI processing - intent + command generation
        ai_result = self.process_v2(user_input, target)
        
        result["intent"] = ai_result["intent"].intent_type if ai_result["intent"] else None
        
        # AI başarısız veya command yok
        if not ai_result["success"] or not ai_result["command"]:
            result["message"] = ai_result["message"]
            return result
        
        # Intent → Tool mapping
        intent = ai_result["intent"]
        intent_type = intent.intent_type
        command = ai_result["command"]
        
        # Intent type'a göre tool çalıştır
        try:
            if intent_type == IntentType.HOST_DISCOVERY:
                # Ping sweep - target from intent params or UI
                target_range = intent.params.get("target", intent.target or target or "192.168.1.0/24")
                self._coordinator.execute_ping_sweep(target_range=target_range)
                result["tool_started"] = True
                result["message"] = f"Ping sweep started: {target_range}"
            
            elif intent_type == IntentType.PORT_SCAN:
                # Port scan - target and ports from intent
                scan_target = intent.target or target or "127.0.0.1"
                ports = intent.params.get("ports", "1-1000")
                self._coordinator.execute_port_scan(target=scan_target, ports=ports)
                result["tool_started"] = True
                result["message"] = f"Port scan started: {scan_target} (ports: {ports})"
            
            elif intent_type == IntentType.SERVICE_DETECTION:
                # Service detection (nmap -sV)
                scan_target = intent.target or target or "127.0.0.1"
                ports = intent.params.get("ports", "1-1000")
                self._coordinator.execute_port_scan(target=scan_target, ports=ports)
                result["tool_started"] = True
                result["message"] = f"Service detection started: {scan_target}"
            
            else:
                # Diğer intent'ler için henüz tool yok
                result["message"] = f"Tool execution not implemented for: {intent_type.value}"
                result["success"] = False
                return result
            
            result["success"] = True
            
        except Exception as e:
            result["message"] = f"Tool execution failed: {str(e)}"
            result["success"] = False
        
        return result


# =============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# =============================================================================

_orchestrator: Optional[AIOrchestrator] = None


def get_orchestrator(model: str = "whiterabbitneo") -> AIOrchestrator:
    """
    Singleton orchestrator instance doner.
    
    Kullanim:
        from src.ai.orchestrator import get_orchestrator
        
        orch = get_orchestrator()
        response = orch.process("Agi tara", target="192.168.1.0/24")
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AIOrchestrator(model=model)
    return _orchestrator


def quick_command(user_input: str, target: Optional[str] = None) -> Optional[ToolCommand]:
    """
    Hizli komut uretimi (legacy compat).
    
    Returns:
        ToolCommand veya None
    """
    orch = get_orchestrator()
    response = orch.process(user_input, target)
    return response.command


def quick_process(user_input: str, target: Optional[str] = None) -> Dict[str, Any]:
    """
    Hizli V2 isleme.
    
    Returns:
        V2 result dict
    """
    orch = get_orchestrator()
    return orch.process_v2(user_input, target)


# =============================================================================
# DEBUG
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SENTINEL AI - Orchestrator v2 Test")
    print("=" * 70)
    
    orch = AIOrchestrator(model="whiterabbitneo")
    
    print(f"\nStatus: {orch.get_status()}")
    
    # Test cases
    test_inputs = [
        ("192.168.1.0/24 agini tara", None),
        ("example.com portlarini kontrol et", None),
        ("google.com DNS sorgusu yap", None),
        ("web sitesinde dizin ara", "http://example.com"),
        ("nmap nedir?", None),
    ]
    
    for user_input, target in test_inputs:
        print(f"\n{'='*70}")
        print(f"Input: {user_input}")
        if target:
            print(f"Target: {target}")
        print("-" * 70)
        
        result = orch.process_v2(user_input, target)
        
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
        
        if result['intent']:
            print(f"Intent: {result['intent'].intent_type.value}")
        
        if result['command']:
            print(f"Command: {result['command'].to_display_string()}")
            print(f"Root: {result['command'].requires_root}")
            print(f"Risk: {result['command'].risk_level.value}")
        
        if result['policy_warning']:
            print(f"Warning: {result['policy_warning']}")

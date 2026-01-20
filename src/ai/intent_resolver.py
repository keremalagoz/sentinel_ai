# SENTINEL AI - Intent Resolver
# Action Planner v2: LLM sadece kullanici niyetini belirler
#
# LLM'in TEK gorevi: Kullanicinin ne yapmak istedigini anlamak
# LLM ASLA uretmez: tool adi, argumanlar, risk seviyesi, requires_root

import os
import json
from typing import Optional, List, Dict
from openai import OpenAI
from dotenv import load_dotenv

from src.ai.schemas import Intent, IntentType, INTENT_SCHEMA

load_dotenv()


# =============================================================================
# INTENT RESOLVER PROMPT
# =============================================================================

INTENT_RESOLVER_PROMPT = """Sen bir niyet cozucusun (Intent Resolver).
Gorev: Kullanicinin siber guvenlik talebini analiz et ve SADECE niyetini belirle.

ONEMLI KURALLAR:
1. ASLA tool adi yazma (nmap, gobuster, vb.)
2. ASLA argumanlar uretme (-sS, -p, vb.)
3. ASLA risk seviyesi veya root bilgisi verme
4. SADECE kullanicinin ne yapmak istedigini anla
5. Kullanici "hedef", "target", "ağ" gibi GENEL ifadeler kullaniyorsa target=null birak
   (Cunku hedef bilgisi UI'dan ayrıca gelecek)
6. SADECE kullanici SPESIFIK IP/domain belirtirse target doldur
   - Spesifik: "192.168.1.1", "example.com", "10.0.0.1/24"
   - Genel: "hedef", "hedef ağ", "target", "bu sistem"

INTENT TURLERI:
- host_discovery: Agdaki aktif cihazlari bul, ping taramasi
- port_scan: Port taramasi, hangi portlar acik
- service_detection: Servis ve versiyon tespiti
- os_detection: Isletim sistemi tespiti
- vuln_scan: Zafiyet taramasi
- web_dir_enum: Web dizin/dosya kesfet
- web_vuln_scan: Web sunucu zafiyet taramasi
- dns_lookup: DNS sorgusu
- whois_lookup: Domain whois bilgisi
- brute_force_ssh: SSH brute force
- brute_force_http: HTTP form brute force
- sql_injection: SQL injection testi
- info_query: Genel bilgi sorusu (komut gerektirmez)
- unknown: Anlasılamadi, netlestime gerekli

CIKTI FORMATI (STRICT JSON):
{
    "intent_type": "...",
    "target": "hedef IP/domain veya null",
    "params": {
        "ports": "port araligi (varsa)",
        "wordlist": "wordlist tercihi (varsa)"
    },
    "needs_clarification": false,
    "clarification_reason": null
}

ORNEKLER:

Girdi: "192.168.1.0/24 agini tara"
Cikti: {"intent_type": "host_discovery", "target": "192.168.1.0/24", "params": {}, "needs_clarification": false, "clarification_reason": null}

Girdi: "example.com portlarini tara"
Cikti: {"intent_type": "port_scan", "target": "example.com", "params": {}, "needs_clarification": false, "clarification_reason": null}

Girdi: "hedef ağda tam tarama yap"
Cikti: {"intent_type": "port_scan", "target": null, "params": {}, "needs_clarification": false, "clarification_reason": null}

Girdi: "tarama yap"
Cikti: {"intent_type": "port_scan", "target": null, "params": {}, "needs_clarification": false, "clarification_reason": null}

Girdi: "80 ve 443 portlarini kontrol et 10.0.0.1 de"
Cikti: {"intent_type": "port_scan", "target": "10.0.0.1", "params": {"ports": "80,443"}, "needs_clarification": false, "clarification_reason": null}

Girdi: "web sitesinde dizin ara"
Cikti: {"intent_type": "web_dir_enum", "target": null, "params": {}, "needs_clarification": false, "clarification_reason": null}

Girdi: "nmap nedir?"
Cikti: {"intent_type": "info_query", "target": null, "params": {}, "needs_clarification": false, "clarification_reason": null}

Girdi: "birseyler yap"
Cikti: {"intent_type": "unknown", "target": null, "params": {}, "needs_clarification": true, "clarification_reason": "Ne yapmak istediginizi anlayamadim"}
"""


class IntentResolver:
    """
    LLM tabanli niyet cozucusu.
    
    Kullanici girdisini alir, LLM'e gonderir ve Intent objesi doner.
    LLM sadece niyet belirler, tool/argumanlar Registry'den gelir.
    """
    
    def __init__(self, model: str = "whiterabbitneo", base_url: str = None):
        """
        IntentResolver'i baslat.
        
        Args:
            model: Kullanilacak model (whiterabbitneo, llama3:8b, gpt-4o-mini)
            base_url: Ollama endpoint (default: localhost:11434)
        """
        self._model = model
        
        # Local Ollama client
        self._base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self._client = OpenAI(
            base_url=f"{self._base_url}/v1",
            api_key="ollama"  # Ollama requires dummy key
        )
        
        # Cloud client (fallback)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "your_openai_api_key_here":
            self._cloud_client = OpenAI(api_key=openai_key)
        else:
            self._cloud_client = None
    
    def resolve(self, user_input: str, target_hint: Optional[str] = None) -> Intent:
        """
        Kullanici girdisinden Intent cozumle.
        
        Args:
            user_input: Kullanicinin dogal dildeki talebi
            target_hint: UI'dan gelen hedef bilgisi (opsiyonel)
        
        Returns:
            Intent objesi
        """
        # Hedef bilgisini ekle
        context = user_input
        if target_hint:
            context = f"[Hedef: {target_hint}]\n{user_input}"
        
        messages = [
            {"role": "system", "content": INTENT_RESOLVER_PROMPT},
            {"role": "user", "content": context}
        ]
        
        try:
            # Local LLM cagir
            response = self._call_local(messages)
            return self._parse_response(response)
            
        except Exception as e:
            print(f"[IntentResolver] Error: {e}")
            
            # Cloud fallback
            if self._cloud_client:
                try:
                    response = self._call_cloud(messages)
                    return self._parse_response(response)
                except Exception as cloud_error:
                    print(f"[IntentResolver] Cloud fallback failed: {cloud_error}")
            
            # Hata durumunda UNKNOWN don
            return Intent(
                intent_type=IntentType.UNKNOWN,
                target=None,
                params={},
                needs_clarification=True,
                clarification_reason=f"AI hatasi: {str(e)}"
            )
    
    def _call_local(self, messages: List[Dict[str, str]]) -> str:
        """Local Ollama LLM cagrisi"""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.1,  # Dusuk temperature = tutarli cikti
            max_tokens=300
        )
        return response.choices[0].message.content
    
    def _call_cloud(self, messages: List[Dict[str, str]]) -> str:
        """Cloud OpenAI cagrisi (fallback)"""
        if not self._cloud_client:
            raise RuntimeError("Cloud client not configured")
        
        response = self._cloud_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_schema", "json_schema": INTENT_SCHEMA},
            temperature=0.1,
            max_tokens=300
        )
        return response.choices[0].message.content
    
    def _parse_response(self, raw_response: str) -> Intent:
        """
        LLM yanitini Intent objesine donustur.
        
        JSON parse + validation yapar.
        """
        try:
            # JSON'u cikar
            json_str = self._extract_json(raw_response)
            data = json.loads(json_str)
            
            # IntentType'a donustur
            intent_type_str = data.get("intent_type", "unknown")
            try:
                intent_type = IntentType(intent_type_str)
            except ValueError:
                intent_type = IntentType.UNKNOWN
            
            return Intent(
                intent_type=intent_type,
                target=data.get("target"),
                params=data.get("params", {}),
                needs_clarification=data.get("needs_clarification", False),
                clarification_reason=data.get("clarification_reason")
            )
            
        except json.JSONDecodeError:
            return Intent(
                intent_type=IntentType.UNKNOWN,
                target=None,
                params={},
                needs_clarification=True,
                clarification_reason="AI yaniti parse edilemedi"
            )
    
    def _extract_json(self, text: str) -> str:
        """Text icinden JSON objesini cikar"""
        import re
        
        # Markdown code block
        pattern = r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        
        # Normal JSON
        start = text.find('{')
        if start == -1:
            return text
        
        # Bracket sayarak dogru kapanisi bul
        depth = 0
        end = start
        for i, char in enumerate(text[start:], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        
        if end > start:
            return text[start:end + 1]
        
        return text
    
    def check_available(self) -> bool:
        """LLM servisinin kullanilabilir olup olmadigini kontrol et"""
        try:
            self._client.models.list()
            return True
        except Exception:
            return False


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_resolver: Optional[IntentResolver] = None


def get_intent_resolver(model: str = "whiterabbitneo") -> IntentResolver:
    """Singleton IntentResolver instance doner"""
    global _resolver
    if _resolver is None:
        _resolver = IntentResolver(model=model)
    return _resolver


def quick_resolve(user_input: str, target: Optional[str] = None) -> Intent:
    """Hizli intent cozumleme"""
    resolver = get_intent_resolver()
    return resolver.resolve(user_input, target)


# =============================================================================
# DEBUG
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SENTINEL AI - Intent Resolver Test")
    print("=" * 60)
    
    resolver = IntentResolver(model="whiterabbitneo")
    
    # Servis kontrolu
    print(f"\nLLM Available: {resolver.check_available()}")
    
    # Test cases
    test_inputs = [
        "192.168.1.0/24 agini tara",
        "example.com portlarini kontrol et",
        "google.com DNS sorgusu yap",
        "web sitesinde dizin ara",
        "nmap nedir?",
    ]
    
    for user_input in test_inputs:
        print(f"\n{'='*60}")
        print(f"Input: {user_input}")
        print("-" * 60)
        
        intent = resolver.resolve(user_input)
        
        print(f"Intent: {intent.intent_type.value}")
        print(f"Target: {intent.target}")
        print(f"Params: {intent.params}")
        print(f"Clarify: {intent.needs_clarification}")
        if intent.clarification_reason:
            print(f"Reason: {intent.clarification_reason}")

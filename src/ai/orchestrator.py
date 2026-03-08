# SENTINEL AI - Karar Motoru (Orchestrator)
# Action Planner v2: Intent-Based Architecture
#
# Yeni Akis (v2):
#   User Input -> Intent Resolver -> Tool Registry -> Command Builder -> Execution
#
# LLM sadece intent belirler, tool/arguman/risk belirleme deterministic.

from typing import Optional, Dict, Any
import logging
import os
import re
import time
import threading

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
from src.ai.keyword_filter import KeywordPreFilter
from src.ai.hierarchical_resolver import HierarchicalResolver, get_hierarchical_resolver
from src.ai.tool_registry import (
    build_tool_spec,
    get_clarification_message,
    get_tool_for_intent,
    get_execution_tool_id,
    build_execution_kwargs,
    get_missing_required_params,
)
from src.ai.command_builder import CommandBuilder, get_command_builder
from src.core.conversation_memory import ConversationMemoryStore
from src.ui.i18n import t
from src.ai.schemas import get_category_for_intent

# Root gerektiren komut flag'leri — dinamik risk hesaplama icin
_ROOT_FLAGS: frozenset = frozenset({"-sS", "-sU", "-O", "-A", "--privileged"})

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """
    Action Planner v2 - Katmanli Karar Motoru.
    
    Yeni Mimari:
    1. Intent Resolver: LLM sadece kullanici niyetini belirler
    2. Tool Registry: Intent -> Tool mapping (deterministic)
    3. Command Builder: ToolSpec -> FinalCommand (deterministic)
    
    Avantajlar:
    - LLM daha dar scope'ta calisir (sadece intent)
    - Tool metadata (requires_root, risk) statik, LLM'den bagimsiz
    - Her katman ayri test edilebilir
    """

    # Confidence esik degeri: Bu degerin altinda clarification istenir
    CONFIDENCE_THRESHOLD: float = 0.7

    # Maksimum LLM yanit suresi (ms). Asildiyinda keyword fallback denenebilir.
    MAX_RESPONSE_MS: int = 10_000

    # Feature flag: True ise 2-asamali HierarchicalResolver kullanilir
    USE_HIERARCHICAL: bool = os.getenv("SENTINEL_USE_HIERARCHICAL", "false").lower() in ("true", "1", "yes")
    
    def __init__(self, model: str = "qwen2.5:3b", coordinator=None):
        """
        Orchestrator'i baslat.
        
        Args:
            model: Kullanilacak LLM modeli (qwen2.5:3b, whiterabbitneo, llama3:8b)
            coordinator: SentinelCoordinator instance (tool execution için)
        """
        self._model = model
        self._coordinator = coordinator
        
        # V2 Components
        self._intent_resolver = IntentResolver(model=model)
        self._command_builder = CommandBuilder()
        self._keyword_filter = KeywordPreFilter()

        # Sprint 3.3: Hierarchical resolver (2-asamali)
        self._hierarchical_resolver: Optional[HierarchicalResolver] = None
        if self.USE_HIERARCHICAL:
            self._hierarchical_resolver = HierarchicalResolver(
                category_model=os.getenv("SENTINEL_CATEGORY_MODEL"),
                sub_intent_model=model,
            )
        
        # Cache
        self._last_intent: Optional[Intent] = None
        self._last_tool_spec: Optional[ToolSpec] = None
        self._conversation_memory = ConversationMemoryStore()

    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create (or ensure) backend conversation session and return session id."""
        return self._conversation_memory.create_session(session_id=session_id)

    def get_session_turns(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Read session turns for API/debug use."""
        return self._conversation_memory.get_recent_turns(session_id=session_id, limit=limit)

    # ── Helpers ──

    _IP_OR_HOST_RE = re.compile(
        r"((?:https?://)?\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d{1,5})?(?:/\d{1,2})?)"
        r"|"
        r"((?:https?://)?(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?::\d{1,5})?)"
    )

    def _extract_target_from_input(self, user_input: str) -> Optional[str]:
        """Try to extract an IP address or hostname from raw user text."""
        # Find all matches, avoid matching well-known DNS servers as primary targets
        matches = list(self._IP_OR_HOST_RE.finditer(user_input))
        for m in matches:
            val = m.group(0)
            if val in ["8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1"]:
                 continue
            return val
        return None

    def _extract_target_from_context(self, context_text: str) -> Optional[str]:
        """Conversation context'inden onceki turlardaki target'i cikar."""
        # En son target'i bul (sagdan tara)
        matches = list(self._IP_OR_HOST_RE.finditer(context_text))
        for m in reversed(matches):
            val = m.group(0)
            if val in ["8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1"]:
                 continue
            return val
        return None

    # Regex patterns for param extraction (Fix 3: keyword fallback param cikma)
    _PORT_RE = re.compile(
        r"(?:-p\s*|port[u\s]*\s*)(\d[\d,\-]+)", re.IGNORECASE
    )
    _TOP_PORTS_RE = re.compile(
        r"(?:ilk|top|en\s+pop[u\xfc]ler)\s+(\d+)\s+port[u\xfc]?"
        r"|--top-ports\s+(\d+)"
        r"|(\d+)\s+(?:pop[u\xfc]ler|\xf6nemli|yayg[i\u0131]n)\s+port[u\xfc]?",
        re.IGNORECASE,
    )
    _TIMING_RE = re.compile(
        r"(?:T(\d)|timing\s+(\d)|h[i\u0131]z\s+(\d))", re.IGNORECASE
    )
    _NO_DNS_RE = re.compile(
        r"(dns\s*(yapma|[c\xe7][o\xf6]z[u\xfc]mleme\s*(yap|kapat)|yok|kapat|olmadan)|-n\b|no.?dns)",
        re.IGNORECASE,
    )
    _SVC_DETECT_RE = re.compile(
        r"(versiyon|version|servis\s+tespit|servis\s+versiyon|-sV\b)",
        re.IGNORECASE,
    )
    _AGGRESSIVE_RE = re.compile(
        r"(agresif|aggressive|-A\b|full\s+scan|tam\s+tarama)", re.IGNORECASE
    )
    _TRACEROUTE_RE = re.compile(
        r"(traceroute|--traceroute)", re.IGNORECASE
    )
    _SYN_RE = re.compile(r"(SYN|-sS)\b", re.IGNORECASE)
    _UDP_RE = re.compile(r"(UDP|-sU)\b", re.IGNORECASE)
    _NO_PING_RE = re.compile(
        r"(ping\s*(atma|olmadan|yok)|no.?ping|-Pn\b)", re.IGNORECASE
    )
    _VERBOSE_RE = re.compile(
        r"(verbose|detayl[i\u0131]|ayr[i\u0131]nt[i\u0131]l[i\u0131]|-v\b)",
        re.IGNORECASE,
    )
    _OSSCAN_RE = re.compile(
        r"(osscan.?guess|os\s+tahmin|--osscan-guess)", re.IGNORECASE
    )

    # -- Gobuster patterns --
    _EXT_RE = re.compile(
        r"(?:uzant[i\u0131]|extension|ext|-x)\s*[:\s]?\s*([a-zA-Z0-9,]+)",
        re.IGNORECASE,
    )
    _THREADS_RE = re.compile(
        r"(?:thread|i[s\u015f][c\xe7]i|paralel|-t)\s*(\d+)", re.IGNORECASE
    )
    _WORDLIST_RE = re.compile(
        r"(?:wordlist|s[o\xf6]zl[u\xfc]k|kelime\s*liste)\s*[:\s]?\s*(\S+)",
        re.IGNORECASE,
    )
    # -- DNS patterns --
    _RECORD_TYPE_RE = re.compile(
        r"\b(MX|AAAA|NS|TXT|CNAME|SOA|PTR|SRV|A)\b\s*(?:kay[i\u0131]t|record)?",
        re.IGNORECASE,
    )
    # -- SSL patterns --
    _SSL_PORT_RE = re.compile(
        r"(?:port|:)(\d{2,5})", re.IGNORECASE
    )
    _TLS_VER_RE = re.compile(
        r"tls\s*1\.?(2|3)|tls1_(2|3)", re.IGNORECASE
    )
    # -- SQLMap patterns --
    _LEVEL_RE = re.compile(
        r"(?:level|seviye)\s*(\d)", re.IGNORECASE
    )
    _RISK_RE = re.compile(
        r"(?:risk|risk)\s*(\d)", re.IGNORECASE
    )

    # Intent groups for param extraction routing
    _NMAP_INTENTS = frozenset({
        IntentType.HOST_DISCOVERY, IntentType.PORT_SCAN,
        IntentType.SERVICE_DETECTION, IntentType.OS_DETECTION,
        IntentType.VULN_SCAN,
    })

    def _extract_params_from_input(
        self, text: str, intent_type: IntentType
    ) -> Dict[str, Any]:
        """Keyword fallback sirasinda regex ile temel parametreleri cikar.

        Intent tipine gore farkli parametreler cikarilir.
        """
        params: Dict[str, Any] = {}

        # ── Nmap ailesi ──
        if intent_type in self._NMAP_INTENTS:
            m = self._PORT_RE.search(text)
            if m:
                params["ports"] = m.group(1)

            m = self._TOP_PORTS_RE.search(text)
            if m:
                val = m.group(1) or m.group(2) or m.group(3)
                if val:
                    params["top_ports"] = int(val)
                    params.pop("ports", None)

            m = self._TIMING_RE.search(text)
            if m:
                val = m.group(1) or m.group(2) or m.group(3)
                if val:
                    params["timing"] = int(val)

            if self._NO_DNS_RE.search(text):
                params["no_dns"] = True
            if self._SVC_DETECT_RE.search(text):
                params["service_detection"] = True
            if self._AGGRESSIVE_RE.search(text):
                params["aggressive"] = True
            if self._TRACEROUTE_RE.search(text):
                params["traceroute"] = True
            if self._NO_PING_RE.search(text):
                params["no_ping"] = True
            if self._VERBOSE_RE.search(text):
                params["verbose"] = True
            if self._OSSCAN_RE.search(text):
                params["osscan_guess"] = True

            if self._SYN_RE.search(text):
                params["scan_type"] = "sS"
            elif self._UDP_RE.search(text):
                params["scan_type"] = "sU"

        # ── Gobuster ──
        elif intent_type == IntentType.WEB_DIR_ENUM:
            m = self._EXT_RE.search(text)
            if m:
                params["extensions"] = m.group(1).strip()
            m = self._WORDLIST_RE.search(text)
            if m:
                params["wordlist"] = m.group(1).strip()
            m = self._THREADS_RE.search(text)
            if m:
                params["threads"] = int(m.group(1))
            if re.search(r"(tls\s*(do[g\u011f]rulama|validation)\s*(yapma|kapat|yok)|no.?tls|-k\b)",
                         text, re.IGNORECASE):
                params["no_tls_validation"] = True
            if re.search(r"(redirect|y[o\xf6]nlendir|takip\s+et|-r\b)",
                         text, re.IGNORECASE):
                params["follow_redirect"] = True

        # ── DNS Lookup ──
        elif intent_type == IntentType.DNS_LOOKUP:
            m = self._RECORD_TYPE_RE.search(text)
            if m:
                params["record_type"] = m.group(1).upper()

        # ── SSL Scan ──
        elif intent_type == IntentType.SSL_SCAN:
            m = self._SSL_PORT_RE.search(text)
            if m:
                params["port"] = int(m.group(1))
            m = self._TLS_VER_RE.search(text)
            if m:
                val = m.group(1) or m.group(2)
                if val:
                    params["tls_version"] = f"1.{val}"

        # ── Hydra SSH/HTTP ──
        elif intent_type in (IntentType.BRUTE_FORCE_SSH, IntentType.BRUTE_FORCE_HTTP):
            m = re.search(r"(?:kullan[i\u0131]c[i\u0131]|user(?:name)?|login)[:\s]+([\w.-]+)",
                          text, re.IGNORECASE)
            if m:
                params["username"] = m.group(1)
            m = self._WORDLIST_RE.search(text)
            if m:
                params["wordlist"] = m.group(1)
            m = self._THREADS_RE.search(text)
            if m:
                params["threads"] = int(m.group(1))

        # ── SQLMap ──
        elif intent_type == IntentType.SQL_INJECTION:
            m = self._LEVEL_RE.search(text)
            if m:
                params["level"] = int(m.group(1))
            m = self._RISK_RE.search(text)
            if m:
                params["risk"] = int(m.group(1))
            if re.search(r"(form|--forms)", text, re.IGNORECASE):
                params["forms"] = True
            if re.search(r"(veritaban|database|--dbs)", text, re.IGNORECASE):
                params["dbs"] = True

        return params

    # =========================================================================
    # V2 API - Yeni Katmanli Mimari
    # =========================================================================
    
    def process_v2(
        self,
        user_input: str,
        target: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_turn_limit: int = 6,
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
                "needs_clarification": bool
            }
        """
        result = {
            "success": False,
            "command": None,
            "secondary_commands": [],
            "message": "",
            "intent": None,
            "needs_clarification": False,
            "session_id": session_id,
            "requires_approval": False,
            "agent_observation": None,
        }

        effective_session_id: Optional[str] = None
        enriched_input = user_input
        if session_id:
            effective_session_id = self.create_session(session_id)
            result["session_id"] = effective_session_id
            self._conversation_memory.append_turn(
                session_id=effective_session_id,
                role="user",
                content=user_input,
                metadata={"target": target} if target else None,
            )
            context_text = self._conversation_memory.render_context(
                effective_session_id,
                limit=memory_turn_limit,
            )
            # Fix 2: Context'i user prompt'a eklemek LLM JSON ciktisini bozuyor.
            # Sadece onceki turlardan target bilgisini cikar, prompt'u temiz tut.
            if context_text and not target:
                target = self._extract_target_from_context(context_text)
        
        # =====================================================================
        # 1. INTENT RESOLVER - LLM sadece niyet belirler
        # =====================================================================
        logger.debug("Resolving intent for input='%s...'", user_input[:50])
        
        t0 = time.monotonic()

        # Sprint 3.3: Hierarchical (2-asamali) veya flat resolver
        if self._hierarchical_resolver is not None:
            intent = self._hierarchical_resolver.resolve(enriched_input, target)
        else:
            intent = self._intent_resolver.resolve(enriched_input, target)

        elapsed_ms = (time.monotonic() - t0) * 1000

        if elapsed_ms > self.MAX_RESPONSE_MS:
            logger.warning(
                "Intent resolution slow: %.0f ms (budget: %d ms)",
                elapsed_ms,
                self.MAX_RESPONSE_MS,
            )

        self._last_intent = intent
        result["intent"] = intent

        # Keyword pre-filter cross-validation (C2)
        kf_suggestion = self._keyword_filter.suggest(user_input)
        kf_ok, kf_msg = self._keyword_filter.cross_validate(
            intent.intent_type, user_input,
        )
        if not kf_ok:
            logger.info("Keyword cross-validation mismatch: %s", kf_msg)
            
            # --- HARD OVERRIDE FOR KNOWN LLM HALLUCINATIONS ---
            # 3B models rigidly associate "kayit" (record) with WHOIS and ignore few-shots.
            if kf_suggestion == IntentType.DNS_LOOKUP and intent.intent_type == IntentType.WHOIS_LOOKUP:
                 logger.info("Hard override: Forcing DNS_LOOKUP over WHOIS_LOOKUP due to known LLM hallucination.")
                 intent.intent_type = IntentType.DNS_LOOKUP
                 # Re-extract params since LLM missed it
                 fallback_params = self._extract_params_from_input(user_input, intent.intent_type)
                 intent.params.update(fallback_params)

        # ── Keyword fallback: LLM parse başarısızsa keyword önerisini kullan ──
        if (
            intent.intent_type == IntentType.UNKNOWN
            and intent.needs_clarification
            and kf_suggestion is not None
            and kf_suggestion != IntentType.UNKNOWN
        ):
            logger.info(
                "LLM failed (%s), keyword fallback to %s",
                intent.clarification_reason,
                kf_suggestion.value,
            )
            # Keyword eşleşmesinden target çıkarmaya çalış
            fallback_target = target or intent.target or intent.params.get("target")
            if not fallback_target:
                fallback_target = self._extract_target_from_input(user_input)

            # Fix 3: Regex ile temel parametreleri user input'tan cikar
            fallback_params = self._extract_params_from_input(
                user_input, kf_suggestion
            )

            intent = Intent(
                intent_type=kf_suggestion,
                target=fallback_target,
                params=fallback_params,
                needs_clarification=False,
                confidence=0.75,
            )
            result["intent"] = intent
            result["agent_observation"] = "keyword_fallback"

        # Confidence dusukse clarification iste
        if intent.confidence < self.CONFIDENCE_THRESHOLD and not intent.needs_clarification:
            logger.info(
                "Low confidence %.2f (threshold %.2f) for intent %s, requesting clarification",
                intent.confidence,
                self.CONFIDENCE_THRESHOLD,
                intent.intent_type.value,
            )
            result["message"] = (
                t("ai.low_confidence").format(conf=f"{intent.confidence:.0%}")
            )
            result["needs_clarification"] = True
            result["agent_observation"] = "low_confidence"
            if effective_session_id:
                self._conversation_memory.append_turn(
                    session_id=effective_session_id,
                    role="assistant",
                    content=result["message"],
                    metadata={"intent": intent.intent_type.value, "confidence": intent.confidence},
                )
            return result

        # Netlestime gerekli mi?
        if intent.needs_clarification:
            result["message"] = intent.clarification_reason or t("ai.clarify")
            result["needs_clarification"] = True
            result["agent_observation"] = "clarification_required"
            if effective_session_id:
                self._conversation_memory.append_turn(
                    session_id=effective_session_id,
                    role="assistant",
                    content=result["message"],
                    metadata={"intent": intent.intent_type.value, "confidence": intent.confidence},
                )
            return result
        
        # Bilgi sorusu mu?
        if intent.intent_type == IntentType.INFO_QUERY:
            result["success"] = True
            result["message"] = t("ai.info_query")
            result["agent_observation"] = "info_query"
            if effective_session_id:
                self._conversation_memory.append_turn(
                    session_id=effective_session_id,
                    role="assistant",
                    content=result["message"],
                    metadata={"intent": intent.intent_type.value, "confidence": intent.confidence},
                )
            return result
        
        # Unknown intent
        if intent.intent_type == IntentType.UNKNOWN:
            result["message"] = t("ai.unknown_intent")
            result["needs_clarification"] = True
            result["agent_observation"] = "unknown_intent"
            if effective_session_id:
                self._conversation_memory.append_turn(
                    session_id=effective_session_id,
                    role="assistant",
                    content=result["message"],
                    metadata={"intent": intent.intent_type.value, "confidence": intent.confidence},
                )
            return result
        
        # =====================================================================
        # 2. TOOL REGISTRY - Intent -> ToolSpec
        # =====================================================================
        # Target: Mesajdan/intent'ten cikan veya params'tan
        final_target = target or intent.target or intent.params.get("target")
        
        # Debug logging
        logger.debug(
            "Target resolution ui_target=%s intent_target=%s intent_params=%s final_target=%s",
            target,
            intent.target,
            intent.params,
            final_target,
        )
        
        # Target validation
        if not final_target:
            result["message"] = (
                t("ai.no_target")
            )
            result["needs_clarification"] = True
            result["agent_observation"] = "missing_target"
            if effective_session_id:
                self._conversation_memory.append_turn(
                    session_id=effective_session_id,
                    role="assistant",
                    content=result["message"],
                    metadata={"intent": intent.intent_type.value, "confidence": intent.confidence},
                )
            return result

        clarification_message = get_clarification_message(
            intent.intent_type,
            final_target,
            intent.params,
        )
        if clarification_message:
            result["message"] = clarification_message
            result["needs_clarification"] = True
            result["agent_observation"] = "clarification_required"
            if effective_session_id:
                self._conversation_memory.append_turn(
                    session_id=effective_session_id,
                    role="assistant",
                    content=result["message"],
                    metadata={"intent": intent.intent_type.value, "confidence": intent.confidence},
                )
            return result
        
        tool_spec = build_tool_spec(
            intent_type=intent.intent_type,
            target=final_target,
            params=intent.params
        )
        
        if tool_spec is None:
            result["message"] = t("ai.no_tool").format(intent=intent.intent_type.value)
            result["agent_observation"] = "tool_not_found"
            if effective_session_id:
                self._conversation_memory.append_turn(
                    session_id=effective_session_id,
                    role="assistant",
                    content=result["message"],
                    metadata={"intent": intent.intent_type.value, "confidence": intent.confidence},
                )
            return result
        
        self._last_tool_spec = tool_spec

        missing_required = get_missing_required_params(intent.intent_type, intent.params)
        if missing_required:
            result["message"] = (
                f"Ek bilgi gerekli: {', '.join(missing_required)}"
            )
            result["needs_clarification"] = True
            result["agent_observation"] = "missing_required_params"
            if effective_session_id:
                self._conversation_memory.append_turn(
                    session_id=effective_session_id,
                    role="assistant",
                    content=result["message"],
                    metadata={
                        "intent": intent.intent_type.value,
                        "confidence": intent.confidence,
                        "missing_params": missing_required,
                    },
                )
            return result
        
        # =====================================================================
        # 3. COMMAND BUILDER - ToolSpec -> FinalCommand
        # =====================================================================
        tool_def = get_tool_for_intent(intent.intent_type)
        explanation = tool_def.description if tool_def else ""

        command = None
        error = None

        # Preferred path (Track E): build display command from real execution tool
        try:
            final_target = tool_spec.target
            exec_tool_id = get_execution_tool_id(intent.intent_type)
            exec_kwargs = build_execution_kwargs(intent.intent_type, final_target, intent.params)

            if (
                exec_tool_id
                and exec_kwargs
            ):
                integrated_tool = None
                if self._coordinator is not None and hasattr(self._coordinator, "manager"):
                    integrated_tool = self._coordinator.manager.get_tool(exec_tool_id)
                # Coordinator yoksa da fallback'e dusmeden execution tool'u dogrudan olustur.
                if integrated_tool is None:
                    from src.core.tool_base import TOOL_CLASS_MAP

                    tool_cls = TOOL_CLASS_MAP.get(exec_tool_id)
                    if tool_cls is not None:
                        class _IntegratedWrapper:
                            def __init__(self, tool):
                                self.tool = tool

                        integrated_tool = _IntegratedWrapper(tool_cls())

                if integrated_tool is not None:
                    cmd_list = integrated_tool.tool.build_command(**exec_kwargs)
                    if cmd_list:
                        display_args = cmd_list[1:]
                        if (
                            intent.intent_type == IntentType.SQL_INJECTION
                            and len(display_args) >= 2
                            and display_args[0] == "-u"
                        ):
                            sqlmap_target = display_args[1]
                            remaining_args = display_args[2:]
                            display_args = list(remaining_args) + ["-u", sqlmap_target]

                        # Dinamik risk hesaplama: statik registry yerine
                        # gercek komut flag'lerine bakilir
                        actual_requires_root = bool(
                            _ROOT_FLAGS.intersection(cmd_list)
                        )
                        actual_risk = tool_spec.risk_level
                        if actual_requires_root:
                            actual_risk = RiskLevel.HIGH

                        command = FinalCommand(
                            executable=cmd_list[0],
                            arguments=display_args,
                            requires_root=actual_requires_root,
                            risk_level=actual_risk,
                            explanation=explanation,
                        )
        except Exception:
            logger.exception("Execution-tool display build failed, falling back to CommandBuilder")
            result["agent_observation"] = "execution_tool_fallback"

        # Fallback path for compatibility
        if command is None:
            fallback_command, error = self._command_builder.build(tool_spec, explanation)
            if fallback_command is not None:
                # Bare command guard: fallback'in yeterli arguman urettigini dogrula
                if not fallback_command.arguments or (
                    len(fallback_command.arguments) == 1
                    and fallback_command.arguments[0] == tool_spec.target
                ):
                    logger.warning(
                        "Fallback produced bare command for intent=%s, target=%s",
                        intent.intent_type.value,
                        tool_spec.target,
                    )
                    result["agent_observation"] = "bare_command_fallback"
                    result["message"] = t("ai.clarify")
                    result["needs_clarification"] = True
                    if effective_session_id:
                        self._conversation_memory.append_turn(
                            session_id=effective_session_id,
                            role="assistant",
                            content=result["message"],
                            metadata={
                                "intent": intent.intent_type.value,
                                "confidence": intent.confidence,
                                "reason": "bare_command_blocked",
                            },
                        )
                    return result
            command = fallback_command
        
        if error:
            result["message"] = t("ai.cmd_failed").format(error=error)
            result["agent_observation"] = "command_build_failed"
            if effective_session_id:
                self._conversation_memory.append_turn(
                    session_id=effective_session_id,
                    role="assistant",
                    content=result["message"],
                    metadata={"intent": intent.intent_type.value, "confidence": intent.confidence},
                )
            return result
        
        # =====================================================================
        # 5. BASARILI SONUC
        # =====================================================================
        result["success"] = True
        result["command"] = command

        # Compound prompt desteği (hafif): keyword'ten ikinci/ucuncu intent adaylari
        # varsa ayni target ile ek komut onerileri olustur.
        try:
            primary = intent.intent_type
            primary_cat = get_category_for_intent(primary)
            all_candidates = self._keyword_filter.suggest_all(user_input)
            secondary: list[FinalCommand] = []
            seen_intents: set[IntentType] = {primary}

            for cand in all_candidates:
                if cand in seen_intents:
                    continue
                if cand in {IntentType.INFO_QUERY, IntentType.UNKNOWN}:
                    continue

                # Ayni kategori icinde yakin intent kombinasyonlarini ikinci komut yapma
                # (port_scan + service_detection gibi) -> primary komut parametresiyle cozulsun.
                cand_cat = get_category_for_intent(cand)
                if cand_cat == primary_cat and cand_cat == get_category_for_intent(IntentType.PORT_SCAN):
                    continue

                exec_tool_id2 = get_execution_tool_id(cand)
                exec_kwargs2 = build_execution_kwargs(cand, final_target, intent.params)
                if not exec_tool_id2 or not exec_kwargs2:
                    continue

                integrated_tool2 = None
                if self._coordinator is not None and hasattr(self._coordinator, "manager"):
                    integrated_tool2 = self._coordinator.manager.get_tool(exec_tool_id2)
                if integrated_tool2 is None:
                    from src.core.tool_base import TOOL_CLASS_MAP

                    tool_cls2 = TOOL_CLASS_MAP.get(exec_tool_id2)
                    if tool_cls2 is not None:
                        class _IntegratedWrapper2:
                            def __init__(self, tool):
                                self.tool = tool

                        integrated_tool2 = _IntegratedWrapper2(tool_cls2())

                if integrated_tool2 is None:
                    continue

                cmd2 = integrated_tool2.tool.build_command(**exec_kwargs2)
                if not cmd2:
                    continue

                req_root2 = bool(_ROOT_FLAGS.intersection(cmd2))
                risk2 = RiskLevel.HIGH if req_root2 else RiskLevel.MEDIUM

                secondary.append(
                    FinalCommand(
                        executable=cmd2[0],
                        arguments=cmd2[1:],
                        requires_root=req_root2,
                        risk_level=risk2,
                        explanation=f"Ek onerilen komut ({cand.value})",
                    )
                )
                seen_intents.add(cand)

                if len(secondary) >= 2:
                    break

            result["secondary_commands"] = secondary
        except Exception:
            logger.exception("Failed to build secondary commands for compound prompt")

        result["message"] = t("ai.cmd_ready").format(cmd=command.to_display_string())
        result["requires_approval"] = True
        result["agent_observation"] = "action_suggested"

        if effective_session_id:
            self._conversation_memory.append_turn(
                session_id=effective_session_id,
                role="assistant",
                content=result["message"],
                metadata={
                    "intent": intent.intent_type.value,
                    "confidence": intent.confidence,
                    "requires_approval": True,
                    "risk_level": command.risk_level.value,
                },
            )
        
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
        return self._v2_to_response(v2_result)

    def process_with_session(
        self,
        user_input: str,
        target: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AIResponse:
        """Session-aware islem, AIResponse formatinda doner.

        UI → BackendGateway → Orchestrator yolu icin.
        process_v2'yi session_id ile cagirir, sonucu legacy AIResponse'a donusturur.
        """
        v2_result = self.process_v2(user_input, target, session_id=session_id)
        return self._v2_to_response(v2_result)

    @staticmethod
    def _v2_to_response(v2_result: Dict[str, Any]) -> AIResponse:
        """process_v2 sonucunu legacy AIResponse'a donustur."""
        tool_command = None
        if v2_result["command"]:
            cmd = v2_result["command"]
            # model_construct: Pydantic validator'lari bypass et.
            # FinalCommand zaten guvenli pipeline'dan (tool_registry + build_command)
            # gectiginden legacy ALLOWED_TOOLS / _MAX_ARG_LENGTH dogrulamasi
            # tekrar uygulanmamali.  Bu yuzden model_construct() kullanilir.
            tool_command = ToolCommand.model_construct(
                tool=cmd.executable,
                arguments=list(cmd.arguments),
                requires_root=cmd.requires_root,
                risk_level=cmd.risk_level,
                explanation=cmd.explanation,
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
            "last_intent": self._last_intent.intent_type.value if self._last_intent else None,
        }
    
    def check_services(self, force: bool = False) -> tuple:
        """
        Servis durumlarini kontrol et (legacy compat).
        
        Returns:
            (local_available, cloud_available)
        """
        local = self._intent_resolver.check_available()
        cloud = False  # Local-only mode
        return (local, cloud)
    
    def set_model(self, model: str):
        """Kullanilacak modeli degistir"""
        self._model = model
        self._intent_resolver = IntentResolver(model=model)
        # Sprint 3.3: Hierarchical resolver modeli de guncelle
        if self._hierarchical_resolver is not None:
            self._hierarchical_resolver.set_models(
                category_model=self._hierarchical_resolver.category_model,
                sub_intent_model=model,
            )

    def set_hierarchical(self, enabled: bool, category_model: Optional[str] = None) -> None:
        """Hierarchical (2-asamali) resolver'i ac/kapa (runtime)."""
        if enabled:
            self._hierarchical_resolver = HierarchicalResolver(
                category_model=category_model,
                sub_intent_model=self._model,
            )
            logger.info("Hierarchical resolver ENABLED (cat=%s, sub=%s)",
                        category_model, self._model)
        else:
            self._hierarchical_resolver = None
            logger.info("Hierarchical resolver DISABLED, using flat resolver")
    
    
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
        
        # Intent → Tool execution (registry tabanli)
        intent = ai_result["intent"]
        intent_type = intent.intent_type

        try:
            final_target = intent.target or target or intent.params.get("target")
            tool_id = get_execution_tool_id(intent_type)
            kwargs = build_execution_kwargs(intent_type, final_target, intent.params)

            if not tool_id or not kwargs:
                result["message"] = f"Tool execution not available for: {intent_type.value}"
                result["success"] = False
                return result

            started = self._coordinator.manager.execute_tool(tool_id, callback=None, **kwargs)

            result["tool_started"] = bool(started)
            result["message"] = (
                f"Execution started: {tool_id} ({final_target})"
                if started else
                f"Tool not registered: {tool_id}"
            )
            result["success"] = True
            return result
            
        except Exception as e:
            result["message"] = f"Tool execution failed: {str(e)}"
            result["success"] = False
        
        return result


# =============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# =============================================================================

_orchestrator: Optional[AIOrchestrator] = None
_orchestrator_lock = threading.Lock()


def get_orchestrator(model: str = "qwen2.5:3b") -> AIOrchestrator:
    """
    Singleton orchestrator instance doner (thread-safe).
    
    Kullanim:
        from src.ai.orchestrator import get_orchestrator
        
        orch = get_orchestrator()
        response = orch.process("Agi tara", target="192.168.1.0/24")
    """
    global _orchestrator
    if _orchestrator is None:
        with _orchestrator_lock:
            if _orchestrator is None:
                from src.core.sentinel_coordinator import SentinelCoordinator
                _default_coordinator = SentinelCoordinator()
                _orchestrator = AIOrchestrator(model=model, coordinator=_default_coordinator)
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
    
    orch = AIOrchestrator(model="qwen2.5:3b")
    
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
        

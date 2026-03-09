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
from src.ai.param_extractor import ParamExtractor
from src.core.conversation_memory import ConversationMemoryStore
from src.ui.i18n import t
from src.ai.schemas import get_category_for_intent

# Root gerektiren komut flag'leri — dinamik risk hesaplama icin
_ROOT_FLAGS: frozenset = frozenset({"-sS", "-sU", "-O", "-A", "--privileged"})

INTENT_OVERRIDE_RULES = [
    {
        "name": "dns_record_vs_whois",
        "pattern": re.compile(r"\b(kay[iı]t|record|mx|aaaa|ns|txt|cname|soa|ptr|srv)\b", re.IGNORECASE),
        "from_intent": IntentType.WHOIS_LOOKUP,
        "to_intent": IntentType.DNS_LOOKUP,
        "keyword_must_match": IntentType.DNS_LOOKUP,
    },
]

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

    def _extract_target_from_input(self, user_input: str) -> Optional[str]:
        """Try to extract an IP address or hostname from raw user text."""
        return ParamExtractor.extract_target(user_input)

    def _extract_target_from_context(self, context_text: str) -> Optional[str]:
        """Conversation context'inden onceki turlardaki target'i cikar."""
        return ParamExtractor.extract_target(context_text)

    def _extract_params_from_input(
        self, text: str, intent_type: IntentType
    ) -> Dict[str, Any]:
        """Keyword fallback sirasinda regex ile temel parametreleri cikar.

        Intent tipine gore farkli parametreler cikarilir.
        """
        return ParamExtractor.extract(text, intent_type)

    def _merge_params_with_regex(
        self,
        user_input: str,
        intent_type: IntentType,
        llm_params: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Merge deterministic regex params with LLM params (LLM wins) and prune implicit noise."""
        regex_params = self._extract_params_from_input(user_input, intent_type)
        merged = dict(regex_params)
        if llm_params:
            merged.update(llm_params)
        return self._prune_implicit_params(intent_type, merged, regex_params)

    # All action intents use strict-regex: only regex-extracted params are kept.
    # This eliminates LLM param hallucination which is the #1 cause of benchmark failures.
    _STRICT_REGEX_INTENTS: frozenset = frozenset({
        IntentType.HOST_DISCOVERY,
        IntentType.PORT_SCAN,
        IntentType.SERVICE_DETECTION,
        IntentType.OS_DETECTION,
        IntentType.VULN_SCAN,
        IntentType.SSL_SCAN,
        IntentType.WEB_DIR_ENUM,
        IntentType.WEB_VULN_SCAN,
        IntentType.DNS_LOOKUP,
        IntentType.WHOIS_LOOKUP,
        IntentType.SUBDOMAIN_ENUM,
        IntentType.BRUTE_FORCE_SSH,
        IntentType.BRUTE_FORCE_HTTP,
        IntentType.SQL_INJECTION,
    })

    def _prune_implicit_params(
        self,
        intent_type: IntentType,
        merged_params: Dict[str, Any],
        regex_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Drop non-explicit params for intents where defaults are frequently hallucinated."""
        if intent_type in self._STRICT_REGEX_INTENTS:
            return dict(regex_params)
        return dict(merged_params)

    def _apply_intent_overrides(
        self,
        intent: Intent,
        user_input: str,
        keyword_suggestion: Optional[IntentType],
    ) -> Intent:
        """Apply minimal, configurable intent override rules for known LLM confusions."""
        for rule in INTENT_OVERRIDE_RULES:
            if keyword_suggestion != rule["keyword_must_match"]:
                continue
            if intent.intent_type != rule["from_intent"]:
                continue
            if not rule["pattern"].search(user_input):
                continue

            logger.info(
                "Intent override applied (%s): %s -> %s",
                rule["name"],
                rule["from_intent"].value,
                rule["to_intent"].value,
            )
            intent.intent_type = rule["to_intent"]
            intent.params = self._merge_params_with_regex(
                user_input,
                intent.intent_type,
                intent.params,
            )
            return intent

        return intent

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
            intent = self._apply_intent_overrides(intent, user_input, kf_suggestion)

        # Sprint 3.7 A3: Deterministic param enrichment for all resolved intents.
        intent.params = self._merge_params_with_regex(
            user_input,
            intent.intent_type,
            intent.params,
        )

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
            # Sprint 3.7 B3: target fallback chain
            fallback_target = intent.target
            if not fallback_target:
                fallback_target = self._extract_target_from_input(user_input)
            if not fallback_target:
                fallback_target = target

            fallback_params = self._merge_params_with_regex(
                user_input,
                kf_suggestion,
                {},
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
            intent.target = None
            intent.params = {}
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
            intent.target = None
            intent.params = {}
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
        # Sprint 3.7 B3: LLM target -> regex extract -> UI target_hint -> null
        # Sprint 3.7.1: Regex URL preferred over LLM target (LLM truncates paths/queries)
        regex_target = self._extract_target_from_input(user_input)
        llm_target = intent.target or intent.params.get("target")

        # Prefer regex URL when LLM would lose path/query/protocol
        if regex_target and regex_target.startswith(("http://", "https://")):
            final_target = regex_target
        else:
            final_target = llm_target
        if not final_target:
            final_target = regex_target
        if not final_target:
            final_target = target
        
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
        

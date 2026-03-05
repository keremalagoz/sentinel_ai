"""Hierarchical Intent Resolver — 2 Asamali Niyet Cozumleme

Sprint 3.3: Hybrid LLM Motoru.
Flat 16-intent yerine 2 asamali (Category -> Sub-Intent) cozumleme:
  Stage 1 (hafif model): 5 kategoriden birini sec  (~1-2s)
  Stage 2 (ana model):   Kategori icindeki spesifik intent'i belirle

Kullanim:
    from src.ai.hierarchical_resolver import HierarchicalResolver, get_hierarchical_resolver

    resolver = get_hierarchical_resolver()
    intent = resolver.resolve("192.168.1.0/24 agini tara")
    # -> Intent(intent_type=HOST_DISCOVERY, confidence=0.95, ...)

Tasarim referansi: docs/hierarchical_intent_design.md
"""

import json
import logging
import os
import re
import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

# Pre-compiled regex for JSON extraction (H5 optimization)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```")

from openai import OpenAI

from src.ai.schemas import (
    CategoryResult,
    CategoryType,
    Intent,
    IntentType,
    SENTINEL_CATEGORIES,
    get_category_for_intent,
)
from src.ai.keyword_filter import KeywordPreFilter

logger = logging.getLogger(__name__)


# =============================================================================
# PROMPT SABLONLARI
# =============================================================================

CATEGORY_PROMPT = """Sen bir niyet siniflandiricisin (Category Classifier).
Gorev: Kullanicinin siber guvenlik talebini asagidaki 5 kategoriden BIRINE siniflandir.

KATEGORILER:
- scanning: Ag tarama islemi (port taramasi, host kesfetme, servis/OS tespiti, zafiyet taramasi, SSL analizi)
- web: Web uygulamasi testi (dizin/dosya kesfetme, web zafiyet taramasi)
- recon: Bilgi toplama (DNS sorgusu, WHOIS, subdomain kesfetme)
- attack: Aktif saldiri (SSH/HTTP brute force, SQL injection)
- info: Genel bilgi sorusu veya anlasılamayan talep

KURALLAR:
1. SADECE kategori sec, spesifik islem belirtme
2. confidence degerini 0.0-1.0 arasinda ver
3. Birden fazla kategoriye uyuyorsa EN UYGUN olani sec
4. Belirsiz talepler icin "info" sec

CIKTI FORMATI (STRICT JSON):
{
    "category": "scanning",
    "confidence": 0.95
}

ORNEKLER:

Girdi: "192.168.1.0/24 agini tara"
Cikti: {"category": "scanning", "confidence": 0.95}

Girdi: "example.com portlarini kontrol et"
Cikti: {"category": "scanning", "confidence": 0.95}

Girdi: "web sitesinde dizin ara"
Cikti: {"category": "web", "confidence": 0.90}

Girdi: "nikto ile web taramasi yap"
Cikti: {"category": "web", "confidence": 0.95}

Girdi: "google.com DNS sorgusu yap"
Cikti: {"category": "recon", "confidence": 0.95}

Girdi: "subdomain kesfet"
Cikti: {"category": "recon", "confidence": 0.90}

Girdi: "SSH brute force dene"
Cikti: {"category": "attack", "confidence": 0.95}

Girdi: "sqlmap ile test et"
Cikti: {"category": "attack", "confidence": 0.90}

Girdi: "nmap nedir?"
Cikti: {"category": "info", "confidence": 0.95}

Girdi: "birseyler yap"
Cikti: {"category": "info", "confidence": 0.3}
"""


SUB_INTENT_PROMPT_TEMPLATE = """Sen bir niyet cozucusun (Intent Resolver).
Gorev: Kullanicinin talebini analiz et ve SADECE niyetini belirle.

KATEGORI: {category}
BU KATEGORIDEKI INTENT TURLERI:
{intent_list}

ONEMLI KURALLAR:
1. ASLA tool adi yazma (nmap, gobuster, vb.)
2. ASLA argumanlar uretme (-sS, -p, vb.)
3. SADECE yukaridaki intent turlerinden birini sec
4. Kullanici SPESIFIK IP/domain verdiyse target doldur, aksi halde null birak
5. confidence degerini 0.0-1.0 arasinda ver

CIKTI FORMATI (STRICT JSON):
{{
    "intent_type": "...",
    "target": "hedef IP/domain veya null",
    "params": {{
        "ports": "port araligi (varsa, ornek: '80,443' veya '1-1000')",
        "top_ports": "en populer N port (varsa, ornek: 100)",
        "scan_type": "tarama tipi (varsa: 'sT','sS','sU')",
        "timing": "hiz seviyesi 0-5 (varsa, ornek: 4)",
        "service_detection": "versiyon tespiti (true/false)",
        "no_dns": "DNS cozumleme kapatma (true/false)",
        "wordlist": "wordlist tercihi (varsa)",
        "record_type": "DNS kayit tipi (varsa: 'A','AAAA','MX','NS','TXT')",
        "extensions": "dosya uzantilari (varsa, ornek: 'php,html,txt')",
        "username": "kullanici adi (varsa)"
    }},
    "needs_clarification": false,
    "clarification_reason": null,
    "confidence": 0.95
}}

NOT: params icinde sadece kullanicinin BELIRTTIGI parametreleri ekle.
Belirtilmeyen parametreleri EKLEME, bos birak.

CONFIDENCE KURALLARI:
- 0.9-1.0: Niyet cok net
- 0.7-0.9: Buyuk olasilikla dogru
- 0.5-0.7: Belirsiz
- 0.0-0.5: Anlasilamadi, needs_clarification=true yap
"""


# Intent aciklamalari (Stage 2 prompt'unda kullanilir)
_INTENT_DESCRIPTIONS: Dict[IntentType, str] = {
    IntentType.HOST_DISCOVERY: "Agdaki aktif cihazlari bul, ping taramasi",
    IntentType.PORT_SCAN: "Port taramasi, hangi portlar acik",
    IntentType.SERVICE_DETECTION: "Servis ve versiyon tespiti",
    IntentType.OS_DETECTION: "Isletim sistemi tespiti",
    IntentType.VULN_SCAN: "Zafiyet taramasi",
    IntentType.SSL_SCAN: "SSL/TLS sertifika ve cipher analizi",
    IntentType.WEB_DIR_ENUM: "Web dizin/dosya kesfet",
    IntentType.WEB_VULN_SCAN: "Web sunucu zafiyet taramasi",
    IntentType.DNS_LOOKUP: "DNS sorgusu",
    IntentType.WHOIS_LOOKUP: "Domain whois bilgisi",
    IntentType.SUBDOMAIN_ENUM: "Subdomain kesfet",
    IntentType.BRUTE_FORCE_SSH: "SSH brute force",
    IntentType.BRUTE_FORCE_HTTP: "HTTP form brute force",
    IntentType.SQL_INJECTION: "SQL injection testi",
    IntentType.INFO_QUERY: "Genel bilgi sorusu (komut gerektirmez)",
    IntentType.UNKNOWN: "Anlasilamadi, netlestime gerekli",
}


# =============================================================================
# ABSTRACT BASE CLASS
# =============================================================================

class HierarchicalResolverBase(ABC):
    """2 asamali intent cozumleme arayuzu."""

    @abstractmethod
    def resolve_category(self, user_input: str) -> CategoryResult:
        """Stage 1: Kullanici girdisini kategoriye siniflandir."""
        ...

    @abstractmethod
    def resolve_sub_intent(
        self,
        user_input: str,
        category: CategoryType,
        target_hint: Optional[str] = None,
    ) -> Intent:
        """Stage 2: Kategori icindeki spesifik intent'i coz."""
        ...

    def resolve(
        self,
        user_input: str,
        target_hint: Optional[str] = None,
    ) -> Intent:
        """Tam pipeline: Category -> Sub-Intent (keyword bypass dahil)."""
        cat = self.resolve_category(user_input)
        return self.resolve_sub_intent(user_input, cat.category, target_hint)


# =============================================================================
# CONCRETE IMPLEMENTATION
# =============================================================================

class HierarchicalResolver(HierarchicalResolverBase):
    """
    2 asamali intent cozucusu (Ollama LLM tabanli).

    Stage 1: Hafif model -> 5 kategoriden birini sec
    Stage 2: Ana model   -> Kategori icindeki intent'i belirle

    Keyword pre-filter bypass:
      KeywordPreFilter yuksek guvenle intent oneriyorsa Stage 1 atlanir,
      dogrudan Stage 2'ye kategori bilgisiyle gecilir.
    """

    def __init__(
        self,
        category_model: Optional[str] = None,
        sub_intent_model: str = "qwen2.5:3b",
        base_url: Optional[str] = None,
        request_timeout: Optional[float] = None,
        max_attempts: Optional[int] = None,
    ):
        self._category_model = category_model or os.getenv(
            "SENTINEL_CATEGORY_MODEL", "qwen2.5:3b"
        )
        self._sub_intent_model = sub_intent_model
        self._request_timeout = float(
            request_timeout or os.getenv("INTENT_LLM_TIMEOUT", "20")
        )
        self._max_attempts = max(
            1, int(max_attempts or os.getenv("INTENT_LLM_MAX_ATTEMPTS", "2"))
        )

        self._base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self._client = OpenAI(
            base_url=f"{self._base_url}/v1",
            api_key="ollama",
        )

        self._keyword_filter = KeywordPreFilter()

    # -----------------------------------------------------------------
    # Stage 1 — Category Resolution
    # -----------------------------------------------------------------

    def resolve_category(self, user_input: str) -> CategoryResult:
        """Stage 1: Kullanici girdisini 5 kategoriden birine siniflandir."""
        messages = [
            {"role": "system", "content": CATEGORY_PROMPT},
            {"role": "user", "content": user_input},
        ]
        try:
            raw = self._call_llm(messages, model=self._category_model)
            return self._parse_category_response(raw)
        except Exception as e:
            logger.warning("Stage 1 (category) failed: %s — fallback INFO", e)
            return CategoryResult(
                category=CategoryType.INFO,
                confidence=0.0,
                raw_response={"error": str(e)},
            )

    def _parse_category_response(self, raw_response: str) -> CategoryResult:
        """Stage 1 LLM yanitini CategoryResult'a donustur."""
        try:
            json_str = self._extract_json(raw_response)
            data = json.loads(json_str)

            category_str = data.get("category", "info")
            try:
                category = CategoryType(category_str)
            except ValueError:
                logger.warning("Unknown category '%s', falling back to INFO", category_str)
                category = CategoryType.INFO

            confidence = float(data.get("confidence", 1.0))
            confidence = max(0.0, min(1.0, confidence))

            return CategoryResult(
                category=category,
                confidence=confidence,
                raw_response=data,
            )

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning("Stage 1 parse error: %s", e)
            return CategoryResult(
                category=CategoryType.INFO,
                confidence=0.0,
                raw_response={"parse_error": str(e)},
            )

    # -----------------------------------------------------------------
    # Stage 2 — Sub-Intent Resolution
    # -----------------------------------------------------------------

    def resolve_sub_intent(
        self,
        user_input: str,
        category: CategoryType,
        target_hint: Optional[str] = None,
    ) -> Intent:
        """Stage 2: Kategori icindeki spesifik intent'i coz."""
        # Dinamik prompt: sadece bu kategorinin intent'lerini icerir
        intents_in_category = SENTINEL_CATEGORIES.get(category, [])
        intent_list_str = "\n".join(
            f"- {it.value}: {_INTENT_DESCRIPTIONS.get(it, '')}"
            for it in intents_in_category
        )

        prompt = SUB_INTENT_PROMPT_TEMPLATE.format(
            category=category.value,
            intent_list=intent_list_str,
        )

        context = user_input
        if target_hint:
            context = f"[Hedef: {target_hint}]\n{user_input}"

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": context},
        ]

        try:
            raw = self._call_llm(messages, model=self._sub_intent_model)
            intent = self._parse_sub_intent_response(raw, category)
            return intent
        except Exception as e:
            logger.warning("Stage 2 (sub-intent) failed: %s — fallback UNKNOWN", e)
            return Intent(
                intent_type=IntentType.UNKNOWN,
                target=None,
                params={},
                needs_clarification=True,
                clarification_reason=f"AI hatasi (Stage 2): {str(e)}",
                confidence=0.0,
            )

    def _parse_sub_intent_response(
        self, raw_response: str, category: CategoryType
    ) -> Intent:
        """Stage 2 LLM yanitini Intent'e donustur (kategori-kisitli validasyon)."""
        try:
            json_str = self._extract_json(raw_response)
            data = json.loads(json_str)

            # Temel validasyon
            if not isinstance(data, dict):
                raise ValueError("payload dict degil")

            intent_type_str = data.get("intent_type", "unknown")
            try:
                intent_type = IntentType(intent_type_str)
            except ValueError:
                intent_type = IntentType.UNKNOWN

            # Kategori-kisitli validasyon: intent bu kategoriye ait mi?
            valid_intents = SENTINEL_CATEGORIES.get(category, [])
            if intent_type not in valid_intents:
                logger.warning(
                    "Intent '%s' not in category '%s' (valid: %s). Keeping anyway.",
                    intent_type.value,
                    category.value,
                    [i.value for i in valid_intents],
                )
                # Yanlış kategorideki intent'i kabul et ama confidence düşür
                # (LLM bazen doğru intent'i bulur ama Stage 1 farklı kategori seçmiş olabilir)

            return Intent(
                intent_type=intent_type,
                target=data.get("target"),
                params=data.get("params", {}),
                needs_clarification=data.get("needs_clarification", False),
                clarification_reason=data.get("clarification_reason"),
                confidence=float(data.get("confidence", 1.0)),
            )

        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Stage 2 parse error: %s", e)
            return Intent(
                intent_type=IntentType.UNKNOWN,
                target=None,
                params={},
                needs_clarification=True,
                clarification_reason=f"AI yaniti parse edilemedi (Stage 2): {str(e)}",
                confidence=0.0,
            )

    # -----------------------------------------------------------------
    # resolve() — Tam pipeline (keyword bypass dahil)
    # -----------------------------------------------------------------

    def resolve(
        self,
        user_input: str,
        target_hint: Optional[str] = None,
    ) -> Intent:
        """
        Tam 2-asamali pipeline: [Keyword Bypass] -> Category -> Sub-Intent.

        Keyword pre-filter yuksek guvenle intent oneriyorsa:
          Stage 1 atlanir, dogrudan Stage 2'ye kategori bilgisiyle gecilir.
        """
        t0 = time.monotonic()

        # Keyword bypass: hizli regex eslesmesi varsa Stage 1'i atla
        kw_suggestion = self._keyword_filter.suggest(user_input)
        if kw_suggestion is not None:
            category = get_category_for_intent(kw_suggestion)
            logger.debug(
                "Keyword bypass: '%s' -> %s (category: %s), skipping Stage 1",
                user_input[:40],
                kw_suggestion.value,
                category.value,
            )
            intent = self.resolve_sub_intent(user_input, category, target_hint)

            # Keyword pre-filter spesifik intent biliyorsa, LLM intent_type'ini override et
            # LLM'den sadece target/params (NER) bilgisini kullaniyoruz
            if intent.intent_type != kw_suggestion:
                logger.debug(
                    "Keyword override: LLM='%s' -> keyword='%s'",
                    intent.intent_type.value,
                    kw_suggestion.value,
                )
                intent = Intent(
                    intent_type=kw_suggestion,
                    target=intent.target,
                    params=intent.params,
                    needs_clarification=intent.needs_clarification,
                    clarification_reason=intent.clarification_reason,
                    confidence=intent.confidence,
                )

            elapsed_ms = (time.monotonic() - t0) * 1000
            logger.info(
                "Hierarchical resolve (keyword bypass): %s -> %s [%.0f ms]",
                category.value,
                intent.intent_type.value,
                elapsed_ms,
            )
            return intent

        # Normal 2-asamali akis
        cat_result = self.resolve_category(user_input)
        logger.debug(
            "Stage 1 result: category=%s confidence=%.2f",
            cat_result.category.value,
            cat_result.confidence,
        )

        # Stage 1 confidence cok dusukse fallback: flat resolve (INFO kategorisi)
        if cat_result.confidence < 0.3:
            logger.warning(
                "Stage 1 confidence too low (%.2f), falling back to INFO category",
                cat_result.confidence,
            )
            cat_result = CategoryResult(
                category=CategoryType.INFO,
                confidence=cat_result.confidence,
                raw_response=cat_result.raw_response,
            )

        intent = self.resolve_sub_intent(
            user_input, cat_result.category, target_hint
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "Hierarchical resolve: %s -> %s (confidence: %.2f/%.2f) [%.0f ms]",
            cat_result.category.value,
            intent.intent_type.value,
            cat_result.confidence,
            intent.confidence,
            elapsed_ms,
        )
        return intent

    # -----------------------------------------------------------------
    # LLM Call — retry + backoff (IntentResolver pattern'i)
    # -----------------------------------------------------------------

    def _call_llm(self, messages: List[Dict[str, str]], model: str) -> str:
        """LLM cagrisi (retry + backoff)."""
        last_error: Optional[Exception] = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=300,
                    timeout=self._request_timeout,
                )
                return response.choices[0].message.content
            except Exception as exc:
                last_error = exc
                if attempt >= self._max_attempts:
                    break
                backoff = 0.2 * attempt
                logger.debug(
                    "HierarchicalResolver attempt %s/%s failed (%s), retrying in %.1fs",
                    attempt,
                    self._max_attempts,
                    model,
                    backoff,
                )
                time.sleep(backoff)

        if last_error:
            raise last_error
        raise RuntimeError("HierarchicalResolver LLM call failed without error")

    # -----------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> str:
        """Text icinden JSON objesini cikar."""
        # Markdown code block
        match = _JSON_BLOCK_RE.search(text)
        if match:
            return match.group(1).strip()

        # Normal JSON
        start = text.find("{")
        if start == -1:
            return text

        depth = 0
        end = start
        for i, char in enumerate(text[start:], start):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break

        if end > start:
            return text[start : end + 1]

        return text

    def check_available(self) -> bool:
        """LLM servislerinin kullanilabilir olup olmadigini kontrol et."""
        try:
            self._client.models.list()
            return True
        except Exception:
            return False

    def set_models(self, category_model: str, sub_intent_model: str) -> None:
        """Kullanilacak modelleri degistir."""
        self._category_model = category_model
        self._sub_intent_model = sub_intent_model

    @property
    def category_model(self) -> str:
        return self._category_model

    @property
    def sub_intent_model(self) -> str:
        return self._sub_intent_model


# =============================================================================
# SINGLETON
# =============================================================================

_hierarchical_resolver: Optional[HierarchicalResolver] = None
_hierarchical_lock = threading.Lock()


def get_hierarchical_resolver(
    category_model: Optional[str] = None,
    sub_intent_model: str = "qwen2.5:3b",
) -> HierarchicalResolver:
    """Singleton HierarchicalResolver instance doner (thread-safe)."""
    global _hierarchical_resolver
    if _hierarchical_resolver is None:
        with _hierarchical_lock:
            if _hierarchical_resolver is None:
                _hierarchical_resolver = HierarchicalResolver(
                    category_model=category_model,
                    sub_intent_model=sub_intent_model,
                )
    return _hierarchical_resolver

"""Keyword Pre-filter for Intent Resolution

Sprint 3.2 Track C2: Regex/keyword tabanli hizli intent on-eleme.
LLM sonucunu cross-validate eder. Uyumsuzlukta warning log + clarification.

Kullanim:
    from src.ai.keyword_filter import KeywordPreFilter

    kf = KeywordPreFilter()
    suggestion = kf.suggest("192.168.1.0/24 agini tara")
    # -> IntentType.HOST_DISCOVERY

    # LLM cross-validation
    is_ok, msg = kf.cross_validate(llm_intent, "kullanici girdisi")
"""

import logging
import re
from typing import Optional, Tuple

from src.ai.schemas import IntentType

logger = logging.getLogger(__name__)


# =============================================================================
# KEYWORD PATTERNS
# =============================================================================
# Her pattern bir (regex, IntentType) ciftidir.
# Ilk eslesen kazanir (oncelik sirasi onemli).

_KEYWORD_PATTERNS: list[Tuple[re.Pattern, IntentType]] = [
    # Info query (soru isaretli, "nedir", "nasil calisir", "acikla" iceren)
    # ONCELIKLI: "port tarama nasil calisir" gibi sorular action'dan once yakalanmali
    (re.compile(
        r"(nedir\??|ne\s+ise?\s+yarar|nas[i\u0131]l\s+(calisir|kullanilir|yapilir)|"
        r"what\s+is|how\s+to\s+use|how\s+does|explain|acikla\b)",
        re.IGNORECASE,
    ), IntentType.INFO_QUERY),

    # Host Discovery / Ping sweep
    (re.compile(
        r"(ping\s+sweep|host\s+discovery|agdaki\s+(aktif\s+)?(cihaz|host)|"
        r"ag[i\u0131]n[i\u0131]\s+tara|canli\s+host|alive\s+host|ping\s+tara)",
        re.IGNORECASE,
    ), IntentType.HOST_DISCOVERY),

    # Web vuln scan (vuln_scan'den ONCE gelmeli — "nikto", "web zafiyet" burada yakalar)
    (re.compile(
        r"(nikto|web\s+vuln|web\s+zafiyet|web\s+scan|"
        r"web\s+sunucu.*(tara|test|zafiyet))",
        re.IGNORECASE,
    ), IntentType.WEB_VULN_SCAN),

    # Vulnerability scan (genel zafiyet — web_vuln_scan'den sonra gelmeli)
    (re.compile(
        r"(vuln|zafiyet|vulnerability|exploit\s+scan|nse\s+script|"
        r"zafiyet\s+tara|guvenlik\s+acig)",
        re.IGNORECASE,
    ), IntentType.VULN_SCAN),

    # Service detection
    (re.compile(
        r"(servis\s+tespit|service\s+detect|version\s+detect|"
        r"servis\s+versiyon|banner\s+grab|-sV)",
        re.IGNORECASE,
    ), IntentType.SERVICE_DETECTION),

    # OS detection
    (re.compile(
        r"(isletim\s+sistemi|os\s+detect|os\s+tespit|"
        r"operating\s+system|fingerprint\s+os|-O\b)",
        re.IGNORECASE,
    ), IntentType.OS_DETECTION),

    # Port scan (genel tarama da buraya duser)
    (re.compile(
        r"(port\s*(lar[i\u0131]?)?\s*(tara|scan|kontrol|check)|"
        r"port\s+tarama|tcp\s+scan|syn\s+scan|udp\s+scan|"
        r"acik\s+port|open\s+port|-sS\b|-sT\b|-sU\b|"
        r"(tarama|scan)\s+yap)",
        re.IGNORECASE,
    ), IntentType.PORT_SCAN),

    # SSL / TLS
    (re.compile(
        r"(ssl|tls|sertifika|certificate|cipher|https\s+analiz|"
        r"ssl.?scan|openssl)",
        re.IGNORECASE,
    ), IntentType.SSL_SCAN),

    # Web directory enumeration
    (re.compile(
        r"(dizin\s+(ara|tara|kesfet|enum)|dir\s*(ectory)?\s*(enum|scan|buster)|"
        r"gobuster|dirb|dirsearch|web\s+dizin|hidden\s+(path|dir))",
        re.IGNORECASE,
    ), IntentType.WEB_DIR_ENUM),

    # DNS lookup
    (re.compile(
        r"(dns\s+(sorgu|lookup|query|record)|"
        r"nslookup|dig\s+|mx\s+record|a\s+record|"
        r"ns\s+record|txt\s+record|aaaa\s+record)",
        re.IGNORECASE,
    ), IntentType.DNS_LOOKUP),

    # Subdomain enum
    (re.compile(
        r"(subdomain|alt\s*alan|sub\s*domain\s*(enum|kesfet|tara|bul))",
        re.IGNORECASE,
    ), IntentType.SUBDOMAIN_ENUM),

    # Whois
    (re.compile(
        r"(whois|domain\s+bilgi|domain\s+info|registrar|"
        r"domain\s+owner|alan\s+adi\s+bilgi)",
        re.IGNORECASE,
    ), IntentType.WHOIS_LOOKUP),

    # Brute force SSH
    (re.compile(
        r"(ssh\s+brute|brute\s*force\s+ssh|hydra\s+ssh|"
        r"ssh\s+sifre\s+kir|ssh\s+password)",
        re.IGNORECASE,
    ), IntentType.BRUTE_FORCE_SSH),

    # Brute force HTTP
    (re.compile(
        r"(http\s+brute|brute\s*force\s+http|login\s+brute|"
        r"form\s+brute|hydra\s+http|web\s+login\s+kir)",
        re.IGNORECASE,
    ), IntentType.BRUTE_FORCE_HTTP),

    # SQL injection
    (re.compile(
        r"(sql\s*injection|sqlmap|sqli\b|sql\s+enjeksiyon|"
        r"sql\s+test|veritaban[i\u0131]\s+injection)",
        re.IGNORECASE,
    ), IntentType.SQL_INJECTION),

    # Selamlama / chitchat -> UNKNOWN
    # Aksiyon pattern'lari eslesmediyse ve selamlama geciyorsa unknown
    (re.compile(
        r"^(merhaba|selam|hey\b|hi\b|hello|gunayd[i\u0131]n|"
        r"iyi\s+(gunler|aksamlar|geceler))",
        re.IGNORECASE,
    ), IntentType.UNKNOWN),
]


class KeywordPreFilter:
    """Keyword/regex tabanli hizli intent on-eleme ve cross-validation."""

    def __init__(self) -> None:
        self._patterns = _KEYWORD_PATTERNS

    @property
    def pattern_count(self) -> int:
        """Tanimli keyword pattern sayisi."""
        return len(self._patterns)

    def suggest(self, user_input: str) -> Optional[IntentType]:
        """Kullanici girdisinden keyword-tabanli intent tahmini.

        Ilk eslesen pattern'in IntentType'ini doner.
        Hicbir pattern eslesmediyse None doner.
        """
        for pattern, intent_type in self._patterns:
            if pattern.search(user_input):
                return intent_type
        return None

    def cross_validate(
        self,
        llm_intent: IntentType,
        user_input: str,
    ) -> Tuple[bool, Optional[str]]:
        """LLM sonucunu keyword pre-filter ile cross-validate et.

        Returns:
            (is_consistent, warning_message)
            - is_consistent=True: LLM sonucu keyword ile uyumlu (veya keyword eslesme yok)
            - is_consistent=False: LLM ve keyword uyumsuz -> warning + clarification onerilir
        """
        keyword_suggestion = self.suggest(user_input)

        # Keyword eslesmesi yoksa LLM'e guveniyoruz
        if keyword_suggestion is None:
            return (True, None)

        # LLM ve keyword ayni sonucu verdiyse tutarli
        if llm_intent == keyword_suggestion:
            return (True, None)

        # Bazi intent'ler yakin akraba (ornegin port_scan ve host_discovery)
        # Bu durumlarda uyumsuzluk warning'i bastiriyoruz
        compatible_groups: list[set[IntentType]] = [
            {IntentType.PORT_SCAN, IntentType.HOST_DISCOVERY, IntentType.SERVICE_DETECTION},
            {IntentType.WEB_DIR_ENUM, IntentType.WEB_VULN_SCAN},
            {IntentType.BRUTE_FORCE_SSH, IntentType.BRUTE_FORCE_HTTP},
        ]

        for group in compatible_groups:
            if llm_intent in group and keyword_suggestion in group:
                return (True, None)

        # Uyumsuzluk
        msg = (
            f"Keyword pre-filter ({keyword_suggestion.value}) ile "
            f"LLM sonucu ({llm_intent.value}) uyumsuz. "
            f"Talep netlestirilebilir."
        )
        logger.warning(msg)
        return (False, msg)

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
# TURKISH UNICODE NORMALIZATION
# =============================================================================
_TR_CHAR_MAP = str.maketrans({
    "\u011f": "g",   # ğ -> g
    "\u011e": "G",   # Ğ -> G
    "\u015f": "s",   # ş -> s
    "\u015e": "S",   # Ş -> S
    "\u00e7": "c",   # ç -> c
    "\u00c7": "C",   # Ç -> C
    "\u00f6": "o",   # ö -> o
    "\u00d6": "O",   # Ö -> O
    "\u00fc": "u",   # ü -> u
    "\u00dc": "U",   # Ü -> U
    "\u0131": "i",   # ı -> i (dotless i)
    "\u0130": "I",   # İ -> I (dotted I)
})


def _normalize_turkish(text: str) -> str:
    """Turkce ozel karakterleri ASCII karsiliklarına donusturur.

    Bu normalizasyon keyword pattern eslesmesini kolaylastirir:
    "ağını tara" -> "agini tara" (pattern "ag[i]n[i]\\s+tara" ile eslesir).
    """
    return text.translate(_TR_CHAR_MAP)


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
        r"ag[i\u0131]n[i\u0131]\s+tara|canli\s+host|alive\s+host|ping\s+tara|"
        r"ping\s+atmadan\s+host\s+kesfet)",
        re.IGNORECASE,
    ), IntentType.HOST_DISCOVERY),

    # Port scan with no-ping expressions (-Pn behavior)
    (re.compile(
        r"((no\s*-?\s*ping|ping\s+atmadan|-Pn\b).{0,30}(tara|scan|port))"
        r"|((tara|scan|port).{0,30}(no\s*-?\s*ping|ping\s+atmadan|-Pn\b))",
        re.IGNORECASE,
    ), IntentType.PORT_SCAN),

    # Aggressive scan language maps to port scan intent with aggressive param extraction in LLM
    (re.compile(
        r"(agresif\s+tara(ma)?|aggressive\s+scan|full\s+scan|tam\s+tarama)",
        re.IGNORECASE,
    ), IntentType.PORT_SCAN),

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
        r"operating\s+system|fingerprint\s+os|os\s+fingerprint|-O\b)",
        re.IGNORECASE,
    ), IntentType.OS_DETECTION),

    # Port scan (genel tarama da buraya duser)
    (re.compile(
        r"(port\w*\s+.*?(tara|scan|kontrol|check)|"
        r"port\s+tarama|tcp\s+scan|syn\s+scan|udp\s+scan|"
        r"acik\s+port|open\s+port|-sS\b|-sT\b|-sU\b|"
        r"h[i\u0131]zl[i\u0131]ca\s+tara|h[i\u0131]zl[i\u0131]\s+tara)",
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
        r"nslookup|dig\s+|"
        r"(mx|a|aaaa|ns|txt|soa|cname)\s+(record|kay[iı]t|kayd[iı]))",
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
        normalized = _normalize_turkish(user_input)
        for pattern, intent_type in self._patterns:
            if pattern.search(normalized):
                return intent_type
        return None

    def suggest_all(self, user_input: str) -> list[IntentType]:
        """Kullanici girdisinden eslesen tum intent adaylarini don.

        Ilk eslesen kazanir davranisini bozmaz; ancak compound/ek-komut
        senaryolari icin tum adaylari oncelik sirasiyla dondurur.
        """
        normalized = _normalize_turkish(user_input)
        matches: list[IntentType] = []
        seen: set[IntentType] = set()

        for pattern, intent_type in self._patterns:
            if pattern.search(normalized) and intent_type not in seen:
                matches.append(intent_type)
                seen.add(intent_type)

        return matches

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
        keyword_suggestion = self.suggest(user_input)  # Already normalizes internally

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

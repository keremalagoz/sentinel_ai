# SENTINEL AI - JSON Semalari
# Sprint 2.1: AI yanit formatlari
# Action Planner v2: Intent-based architecture (17 Ocak 2026)
# OpenAI response_format uyumlu, strict=True icin tasarlandi

import re
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Literal, Optional, Dict, Any
from enum import Enum


# =============================================================================
# ACTION PLANNER v2 - Intent-Based Architecture
# =============================================================================

class RiskLevel(str, Enum):
    """
    Komut risk seviyeleri.
    
    - low: Pasif tarama, bilgi toplama (ping, dns lookup)
    - medium: Aktif tarama, port scan (nmap -sS)
    - high: Exploit, bruteforce, sistem degisikligi
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IntentType(str, Enum):
    """
    Kullanici niyeti turleri.
    
    LLM SADECE bu intent'lerden birini secer.
    Tool, argumanlar ve risk seviyesi Registry'den gelir.
    """
    # Tarama (Scanning)
    HOST_DISCOVERY = "host_discovery"      # Agdaki aktif hostlari bul
    PORT_SCAN = "port_scan"                # Port taramasi
    SERVICE_DETECTION = "service_detection" # Servis ve versiyon tespiti
    OS_DETECTION = "os_detection"          # Isletim sistemi tespiti
    VULN_SCAN = "vuln_scan"                # Zafiyet taramasi
    SSL_SCAN = "ssl_scan"                  # SSL/TLS sertifika ve cipher analizi
    
    # Web (Web Enumeration)
    WEB_DIR_ENUM = "web_dir_enum"          # Dizin/dosya kesfet
    WEB_VULN_SCAN = "web_vuln_scan"        # Web zafiyet taramasi
    
    # Recon (Bilgi Toplama)
    DNS_LOOKUP = "dns_lookup"              # DNS sorgusu
    WHOIS_LOOKUP = "whois_lookup"          # Domain bilgisi
    SUBDOMAIN_ENUM = "subdomain_enum"      # Subdomain kesfet
    
    # Brute Force
    BRUTE_FORCE_SSH = "brute_force_ssh"    # SSH brute force
    BRUTE_FORCE_HTTP = "brute_force_http"  # HTTP brute force
    
    # Exploit
    SQL_INJECTION = "sql_injection"        # SQL injection testi
    
    # Bilgi
    INFO_QUERY = "info_query"              # Genel bilgi sorusu (komut yok)
    
    # Belirsiz
    UNKNOWN = "unknown"                    # Anlasılamadi, netlestime gerekli


# =============================================================================
# HIERARCHICAL INTENT — Sprint 3.7: Kategori Taksonomisi
# =============================================================================

class CategoryType(str, Enum):
    """
    2 asamali intent resolution icin ust-duzey kategoriler.
    
    Stage 1 (hafif model) bu 5 kategoriden birini secer.
    Stage 2 (ana model) kategori icindeki spesifik intent'i belirler.
    """
    SCANNING = "scanning"    # Ag tarama: port, host, servis, OS, zafiyet, SSL
    WEB = "web"              # Web uygulamasi: dizin enum, web zafiyet
    RECON = "recon"          # Bilgi toplama: DNS, WHOIS, subdomain
    ATTACK = "attack"        # Saldiri: brute force, SQL injection
    INFO = "info"            # Bilgi sorusu veya belirsiz


# Kategori -> Intent mapping (sabit, kod tabaninin kaynak gercekligi)
SENTINEL_CATEGORIES: Dict[CategoryType, List[IntentType]] = {
    CategoryType.SCANNING: [
        IntentType.HOST_DISCOVERY,
        IntentType.PORT_SCAN,
        IntentType.SERVICE_DETECTION,
        IntentType.OS_DETECTION,
        IntentType.VULN_SCAN,
        IntentType.SSL_SCAN,
    ],
    CategoryType.WEB: [
        IntentType.WEB_DIR_ENUM,
        IntentType.WEB_VULN_SCAN,
    ],
    CategoryType.RECON: [
        IntentType.DNS_LOOKUP,
        IntentType.WHOIS_LOOKUP,
        IntentType.SUBDOMAIN_ENUM,
    ],
    CategoryType.ATTACK: [
        IntentType.BRUTE_FORCE_SSH,
        IntentType.BRUTE_FORCE_HTTP,
        IntentType.SQL_INJECTION,
    ],
    CategoryType.INFO: [
        IntentType.INFO_QUERY,
        IntentType.UNKNOWN,
    ],
}

# Ters lookup: IntentType -> CategoryType (runtime'da hesaplanir)
_INTENT_TO_CATEGORY: Dict[IntentType, CategoryType] = {}
for _cat, _intents in SENTINEL_CATEGORIES.items():
    for _intent in _intents:
        _INTENT_TO_CATEGORY[_intent] = _cat


def get_category_for_intent(intent_type: IntentType) -> CategoryType:
    """IntentType'dan CategoryType'a ters lookup."""
    return _INTENT_TO_CATEGORY.get(intent_type, CategoryType.INFO)


class CategoryResult(BaseModel):
    """
    Stage 1 sonucu — ust duzey kategori siniflandirmasi.
    
    HierarchicalResolver.resolve_category() bu modeli doner.
    """
    category: CategoryType = Field(
        ...,
        description="Ust-duzey kategori (scanning, web, recon, attack, info)"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Kategori siniflandirma guvenliligi"
    )
    raw_response: Optional[Dict[str, Any]] = Field(
        default=None,
        description="LLM'den gelen ham JSON yaniti"
    )


class Intent(BaseModel):
    """
    LLM'in uretiği niyet yapisi.
    
    LLM SADECE kullanicinin ne yapmak istedigini anlar.
    Tool secimi, arguman uretimi ve risk belirleme YAPILMAZ.
    
    Ornek LLM ciktisi:
    {
        "intent_type": "port_scan",
        "target": "192.168.1.1",
        "params": {"ports": "1-1000"},
        "needs_clarification": false
    }
    """
    
    intent_type: IntentType = Field(
        ...,
        description="Kullanicinin niyeti (host_discovery, port_scan, dns_lookup, vb.)"
    )
    
    target: Optional[str] = Field(
        default=None,
        description="Hedef IP, domain veya URL (kullanici verdiyse)"
    )
    
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Ek parametreler: ports, wordlist, protocol, vb."
    )
    
    needs_clarification: bool = Field(
        default=False,
        description="Niyet anlasilamadiysa True"
    )
    
    clarification_reason: Optional[str] = Field(
        default=None,
        description="Neden netlestime gerekiyor"
    )

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Intent guvenliligi (0.0-1.0). LLM'in kendi tahminine olan guveni."
    )


class ToolDef(BaseModel):
    """
    Tool Registry'de tutulan arac tanimi.
    
    Bu bilgiler STATIK ve LLM'den BAGIMSIZ.
    requires_root ve risk_level burada tanimlanir, LLM tarafindan uretilmez.
    """
    
    tool: str = Field(
        ...,
        description="Arac adi (nmap, gobuster, nikto, vb.)"
    )
    
    base_args: List[str] = Field(
        default_factory=list,
        description="Varsayilan argumanlar"
    )
    
    requires_root: bool = Field(
        default=False,
        description="Root yetkisi gerekli mi (STATIK, LLM uretmez)"
    )
    
    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Risk seviyesi (STATIK, LLM uretmez)"
    )
    
    description: str = Field(
        default="",
        description="Arac aciklamasi"
    )
    
    arg_templates: Dict[str, str] = Field(
        default_factory=dict,
        description="Parametre sablonlari: {'ports': '-p {value}', 'wordlist': '-w {value}'}"
    )

    priority: int = Field(
        default=0,
        ge=0,
        description="Ayni intent'e birden fazla tool eslenirse oncelik sirasi (yuksek = tercih edilir)"
    )

    condition: Optional[str] = Field(
        default=None,
        description="Tool secim kosulu (orn: 'target_is_url', 'has_wordlist'). Sprint 5'te aktif routing icin."
    )


class ToolSpec(BaseModel):
    """
    Islenmiş tool bilgisi (Registry'den gelen + parametrelerle birlestirilmis).
    
    CommandBuilder'a gonderilir.
    """
    
    tool: str = Field(..., description="Arac adi")
    arguments: List[str] = Field(default_factory=list, description="Argumanlar")
    target: Optional[str] = Field(default=None, description="Hedef")
    requires_root: bool = Field(default=False, description="Root gerekli mi")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Risk seviyesi")


class FinalCommand(BaseModel):
    """
    Execution Layer'a gonderilen son komut.
    
    ProcessManager bu yapiyi alir ve calistirir.
    """
    
    executable: str = Field(..., description="Calistirilacak program")
    arguments: List[str] = Field(default_factory=list, description="Argumanlar")
    requires_root: bool = Field(default=False, description="Root/pkexec gerekli mi")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Risk seviyesi")
    explanation: str = Field(default="", description="Kullaniciya gosterilecek aciklama")
    
    def to_command_list(self) -> List[str]:
        """Komut listesi olarak don (subprocess icin)"""
        return [self.executable] + self.arguments
    
    def to_display_string(self) -> str:
        """Kullaniciya gosterilecek format"""
        return f"{self.executable} {' '.join(self.arguments)}"


# =============================================================================
# Intent JSON Schema (LLM icin)
# =============================================================================

INTENT_SCHEMA = {
    "name": "user_intent",
    "description": "Kullanicinin siber guvenlik niyetini belirle",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "intent_type": {
                "type": "string",
                "enum": [e.value for e in IntentType],
                "description": "Niyet turu"
            },
            "target": {
                "type": ["string", "null"],
                "description": "Hedef IP/domain/URL"
            },
            "params": {
                "type": "object",
                "description": "Ek parametreler (ports, wordlist, vb.)",
                "additionalProperties": True
            },
            "needs_clarification": {
                "type": "boolean",
                "description": "Netlestime gerekli mi"
            },
            "clarification_reason": {
                "type": ["string", "null"],
                "description": "Netlestime nedeni"
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Intent guvenliligi (0.0-1.0)"
            }
        },
        "required": ["intent_type", "target", "params", "needs_clarification", "clarification_reason", "confidence"],
        "additionalProperties": False
    }
}


# =============================================================================
# LEGACY Re-exports — asil kaynak: src/ai/schemas_legacy.py
# Sprint 3.6 D3: Legacy sema kodu ayri dosyaya tasinmistir.
# Mevcut importlar (`from src.ai.schemas import ToolCommand`) calismaya devam eder.
# =============================================================================

from src.ai.schemas_legacy import (  # noqa: F401
    ALLOWED_TOOLS,
    ToolCommand,
    AIResponse,
    TOOL_COMMAND_SCHEMA,
    AI_RESPONSE_SCHEMA,
    validate_command,
    get_response_format,
)


# =============================================================================
# Sprint 5: Oneri Semasi (Recommendation Engine)
# =============================================================================

class SuggestionSchema(BaseModel):
    """
    Bulgulara dayali oneri semasi.
    
    AI, mevcut bulgulari analiz edip sonraki adimlari onerir.
    
    Ornek:
    - Nmap 80/tcp acik buldu -> "Gobuster ile dizin taramasi yap"
    - SSH acik -> "Hydra ile brute force dene"
    """
    
    related_finding_id: Optional[str] = Field(
        default=None,
        description="Bu onerinin dayandigi bulgu ID'si"
    )
    
    action_title: str = Field(
        ...,
        description="Oneri basligi (UI'da gosterilecek)",
        examples=["Gobuster ile dizin tara", "SSH brute force dene"]
    )
    
    suggested_command_template: str = Field(
        ...,
        description="Onerilen komut sablonu ({target} placeholder kullanilabilir)",
        examples=["gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt"]
    )
    
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Oneri onceligi (1=dusuk, 10=yuksek)"
    )
    
    risk_level: RiskLevel = Field(
        default=RiskLevel.MEDIUM,
        description="Onerilen islemin risk seviyesi"
    )
    
    rationale: str = Field(
        ...,
        description="Bu onerinin gerekcesi (AI'nin dusunce sureci)"
    )


class SuggestionList(BaseModel):
    """Birden fazla oneri iceren liste."""
    
    suggestions: List[SuggestionSchema] = Field(
        default_factory=list,
        description="Oneri listesi"
    )
    
    context_summary: str = Field(
        ...,
        description="Mevcut durumun ozeti"
    )


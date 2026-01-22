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
            }
        },
        "required": ["intent_type", "target", "params", "needs_clarification", "clarification_reason"],
        "additionalProperties": False
    }
}


# =============================================================================
# LEGACY - Sprint 2 Schemas (Backward Compatibility)
# =============================================================================


ALLOWED_TOOLS = frozenset({
    # Security tools (Docker tools-service)
    "nmap",
    "gobuster",
    "nikto",
    "dirb",
    "hydra",
    "sqlmap",
    # Basic recon / network utils
    "whois",
    "dig",
    "nslookup",
    "ping",
    # Common HTTP utilities (optional but safe)
    "curl",
    "wget",
})

_TOOL_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._+-]*$", re.IGNORECASE)
_MAX_ARGUMENTS = 64
_MAX_ARG_LENGTH = 512
_ALLOWED_PLACEHOLDER = "{target}"


class ToolCommand(BaseModel):
    """
    AI'ın ürettiği komut şeması.
    
    OpenAI Structured Output için tasarlandı.
    strict=True modunda bu şemaya tam uyum zorunludur.
    
    Örnek:
    {
        "tool": "nmap",
        "arguments": ["-sS", "-p-", "192.168.1.1"],
        "requires_root": true,
        "risk_level": "medium"
    }
    
    Güvenlik Notu:
    - arguments liste olarak tutulur (shell injection önlemi)
    - Komut string birleştirme yerine QProcess.start(tool, args) kullanılır
    """
    
    tool: str = Field(
        ...,
        description="Çalıştırılacak araç adı (nmap, gobuster, nikto, etc.)",
        examples=["nmap", "gobuster", "dirb", "nikto"]
    )
    
    arguments: List[str] = Field(
        ...,
        description="Araç argümanları - HER BİRİ AYRI ELEMAN (shell injection önlemi)",
        examples=[["-sS", "-p-", "192.168.1.1"], ["dir", "-u", "http://target", "-w", "wordlist.txt"]]
    )
    
    requires_root: bool = Field(
        default=False,
        description="Komut root/sudo yetkisi gerektiriyor mu? True ise pkexec kullanılır."
    )
    
    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Komutun risk seviyesi - UI'da uyarı göstermek için kullanılır"
    )
    
    explanation: Optional[str] = Field(
        default=None,
        description="AI'ın bu komutu neden önerdiğine dair kısa açıklama"
    )

    @field_validator("tool", mode="before")
    @classmethod
    def _validate_tool(cls, v: str) -> str:
        if not isinstance(v, str):
            raise TypeError("tool must be a string")

        tool = v.strip().lower()
        if not tool:
            raise ValueError("tool cannot be empty")

        # Disallow absolute/relative paths and weird formats (only allow binary names)
        if not _TOOL_NAME_PATTERN.match(tool):
            raise ValueError("tool format is invalid")

        if tool not in ALLOWED_TOOLS:
            raise ValueError(f"tool is not allowed: {tool}")

        return tool

    @field_validator("arguments", mode="before")
    @classmethod
    def _validate_arguments(cls, v: List[str]) -> List[str]:
        if not isinstance(v, list):
            raise TypeError("arguments must be a list of strings")

        if len(v) == 0:
            raise ValueError("arguments cannot be empty")

        if len(v) > _MAX_ARGUMENTS:
            raise ValueError("too many arguments")

        normalized: List[str] = []
        for raw in v:
            if not isinstance(raw, str):
                raise TypeError("each argument must be a string")

            # Fail-closed: reject control characters even if they are trailing and would be stripped
            if ("\x00" in raw) or ("\n" in raw) or ("\r" in raw):
                raise ValueError("argument contains control characters")

            arg = raw.strip()
            if not arg:
                raise ValueError("argument cannot be empty")

            # Common LLM formatting: remove surrounding quotes
            if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
                arg = arg[1:-1].strip()
                if not arg:
                    raise ValueError("argument cannot be empty")

            if len(arg) > _MAX_ARG_LENGTH:
                raise ValueError("argument is too long")

            # Block control characters (newline/null byte injection hardening)
            if ("\x00" in arg) or ("\n" in arg) or ("\r" in arg):
                raise ValueError("argument contains control characters")

            # Only allow {target} placeholder usage (no other template expansions)
            tmp = arg.replace(_ALLOWED_PLACEHOLDER, "")
            if ("{" in tmp) or ("}" in tmp):
                raise ValueError("only {target} placeholder is allowed in arguments")

            normalized.append(arg)

        return normalized
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tool": "nmap",
                    "arguments": ["-sn", "192.168.1.0/24"],
                    "requires_root": False,
                    "risk_level": "low",
                    "explanation": "Ağdaki aktif hostları keşfetmek için ping taraması"
                },
                {
                    "tool": "nmap",
                    "arguments": ["-sS", "-sV", "-p-", "192.168.1.100"],
                    "requires_root": True,
                    "risk_level": "medium",
                    "explanation": "Hedef üzerinde tüm portları ve servisleri tespit etmek için SYN taraması"
                }
            ]
        }
    )


class AIResponse(BaseModel):
    """
    AI yanıt wrapper'ı.
    
    Tek komut veya açıklama içerebilir.
    Komut yoksa sadece message döner (yardım, sohbet, vb.)
    """
    
    command: Optional[ToolCommand] = Field(
        default=None,
        description="Çalıştırılacak komut (varsa)"
    )
    
    message: str = Field(
        ...,
        description="Kullanıcıya gösterilecek mesaj (açıklama, uyarı, bilgi)"
    )
    
    needs_clarification: bool = Field(
        default=False,
        description="AI'ın daha fazla bilgiye ihtiyacı var mı?"
    )


# =============================================================================
# OpenAI Structured Output için JSON Schema
# =============================================================================

TOOL_COMMAND_SCHEMA = {
    "name": "tool_command",
    "description": "Güvenlik test aracı komutu üretir",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "tool": {
                "type": "string",
                "description": "Çalıştırılacak araç adı"
            },
            "arguments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Araç argümanları (her biri ayrı eleman)"
            },
            "requires_root": {
                "type": "boolean",
                "description": "Root yetkisi gerekli mi"
            },
            "risk_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Risk seviyesi"
            },
            "explanation": {
                "type": "string",
                "description": "Komut açıklaması"
            }
        },
        "required": ["tool", "arguments", "requires_root", "risk_level", "explanation"],
        "additionalProperties": False
    }
}

AI_RESPONSE_SCHEMA = {
    "name": "ai_response",
    "description": "AI asistan yanıtı",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "command": {
                "anyOf": [
                    {"$ref": "#/$defs/tool_command"},
                    {"type": "null"}
                ],
                "description": "Çalıştırılacak komut (varsa)"
            },
            "message": {
                "type": "string",
                "description": "Kullanıcıya mesaj"
            },
            "needs_clarification": {
                "type": "boolean",
                "description": "Daha fazla bilgi gerekli mi"
            }
        },
        "required": ["command", "message", "needs_clarification"],
        "additionalProperties": False,
        "$defs": {
            "tool_command": TOOL_COMMAND_SCHEMA["schema"]
        }
    }
}


# =============================================================================
# Sprint 5: Öneri Şeması (Recommendation Engine)
# =============================================================================

class SuggestionSchema(BaseModel):
    """
    Bulgulara dayalı öneri şeması.
    
    AI, mevcut bulguları analiz edip sonraki adımları önerir.
    
    Örnek:
    - Nmap 80/tcp açık buldu → "Gobuster ile dizin taraması yap"
    - SSH açık → "Hydra ile brute force dene"
    """
    
    related_finding_id: Optional[str] = Field(
        default=None,
        description="Bu önerinin dayandığı bulgu ID'si"
    )
    
    action_title: str = Field(
        ...,
        description="Öneri başlığı (UI'da gösterilecek)",
        examples=["Gobuster ile dizin tara", "SSH brute force dene"]
    )
    
    suggested_command_template: str = Field(
        ...,
        description="Önerilen komut şablonu ({target} placeholder kullanılabilir)",
        examples=["gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt"]
    )
    
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Öneri önceliği (1=düşük, 10=yüksek)"
    )
    
    risk_level: RiskLevel = Field(
        default=RiskLevel.MEDIUM,
        description="Önerilen işlemin risk seviyesi"
    )
    
    rationale: str = Field(
        ...,
        description="Bu önerinin gerekçesi (AI'ın düşünce süreci)"
    )


class SuggestionList(BaseModel):
    """Birden fazla öneri içeren liste."""
    
    suggestions: List[SuggestionSchema] = Field(
        default_factory=list,
        description="Öneri listesi"
    )
    
    context_summary: str = Field(
        ...,
        description="Mevcut durumun özeti"
    )


# =============================================================================
# Yardımcı Fonksiyonlar
# =============================================================================

def validate_command(data: dict) -> ToolCommand:
    """
    AI yanıtını doğrula ve ToolCommand objesine çevir.
    
    Raises:
        ValidationError: Şema uyumsuzluğunda
    """
    return ToolCommand.model_validate(data)


def get_openai_response_format() -> dict:
    """
    OpenAI API için response_format parametresi.
    
    Kullanım:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[...],
            response_format=get_openai_response_format()
        )
    """
    return {
        "type": "json_schema",
        "json_schema": AI_RESPONSE_SCHEMA
    }


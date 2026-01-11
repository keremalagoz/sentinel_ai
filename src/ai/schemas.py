# SENTINEL AI - JSON Şemaları
# Sprint 2.1: AI yanıt formatları
# OpenAI response_format uyumlu, strict=True için tasarlandı

import re
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional
from enum import Enum


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


class RiskLevel(str, Enum):
    """
    Komut risk seviyeleri.
    
    - low: Pasif tarama, bilgi toplama (ping, dns lookup)
    - medium: Aktif tarama, port scan (nmap -sS)
    - high: Exploit, bruteforce, sistem değişikliği
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


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
    
    class Config:
        json_schema_extra = {
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


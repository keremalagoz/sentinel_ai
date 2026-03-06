"""Legacy Sprint 2 Schemas — Backward Compatibility

Sprint 3.2 Track D3: schemas.py'deki eski ToolCommand, AIResponse,
TOOL_COMMAND_SCHEMA, AI_RESPONSE_SCHEMA burada tutulur.
Yeni kodlar Action Planner v2 (schemas.py) API'sini kullanmalidir.

Bu dosya SADECE geriye uyumluluk icin korunmaktadir.
"""

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

from src.ai.schemas import RiskLevel


# ---------------------------------------------------------------------------
# Izin verilen arac beyaz listesi (legacy)
# ---------------------------------------------------------------------------

ALLOWED_TOOLS = frozenset({
    # Security tools (Docker tools-service)
    "nmap",
    "gobuster",
    "nikto",
    "dirb",
    "hydra",
    "sqlmap",
    # SSL/TLS analysis
    "openssl",
    "sslscan",
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
_MAX_ARG_LENGTH = 2048
_ALLOWED_PLACEHOLDER = "{target}"


# ---------------------------------------------------------------------------
# ToolCommand (legacy Pydantic model)
# ---------------------------------------------------------------------------

class ToolCommand(BaseModel):
    """
    AI'nin urettigi komut semasi (Legacy — Sprint 2).

    Yeni kodlar FinalCommand (Action Planner v2) kullaniyor.
    Bu model geriye uyumluluk icin korunmaktadir.
    """

    tool: str = Field(
        ...,
        description="Calistirilacak arac adi (nmap, gobuster, nikto, etc.)",
        examples=["nmap", "gobuster", "dirb", "nikto"],
    )

    arguments: List[str] = Field(
        ...,
        description="Arac argumanlari — HER BIRI AYRI ELEMAN (shell injection onlemi)",
        examples=[
            ["-sS", "-p-", "192.168.1.1"],
            ["dir", "-u", "http://target", "-w", "wordlist.txt"],
        ],
    )

    requires_root: bool = Field(
        default=False,
        description="Komut root/sudo yetkisi gerektiriyor mu?",
    )

    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Komutun risk seviyesi",
    )

    explanation: Optional[str] = Field(
        default=None,
        description="AI'nin bu komutu neden oneridgine dair kisa aciklama",
    )

    # -- validators --------------------------------------------------------

    @field_validator("tool", mode="before")
    @classmethod
    def _validate_tool(cls, v: str) -> str:
        if not isinstance(v, str):
            raise TypeError("tool must be a string")

        tool = v.strip().lower()
        if not tool:
            raise ValueError("tool cannot be empty")

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

            if ("\x00" in raw) or ("\n" in raw) or ("\r" in raw):
                raise ValueError("argument contains control characters")

            arg = raw.strip()
            if not arg:
                raise ValueError("argument cannot be empty")

            if (arg.startswith('"') and arg.endswith('"')) or (
                arg.startswith("'") and arg.endswith("'")
            ):
                arg = arg[1:-1].strip()
                if not arg:
                    raise ValueError("argument cannot be empty")

            if len(arg) > _MAX_ARG_LENGTH:
                raise ValueError("argument is too long")

            if ("\x00" in arg) or ("\n" in arg) or ("\r" in arg):
                raise ValueError("argument contains control characters")

            tmp = arg.replace(_ALLOWED_PLACEHOLDER, "")
            if ("{" in tmp) or ("}" in tmp):
                raise ValueError(
                    "only {target} placeholder is allowed in arguments"
                )

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
                    "explanation": "Agdaki aktif hostlari kesfetmek icin ping taramasi",
                },
            ]
        }
    )


# ---------------------------------------------------------------------------
# AIResponse (legacy wrapper)
# ---------------------------------------------------------------------------

class AIResponse(BaseModel):
    """
    AI yanit wrapper'i (Legacy — Sprint 2).

    Yeni kodlar FinalCommand + explanations kullaniyor.
    """

    command: Optional[ToolCommand] = Field(
        default=None,
        description="Calistirilacak komut (varsa)",
    )

    message: str = Field(
        ...,
        description="Kullaniciya gosterilecek mesaj",
    )

    needs_clarification: bool = Field(
        default=False,
        description="AI'nin daha fazla bilgiye ihtiyaci var mi?",
    )


# ---------------------------------------------------------------------------
# JSON Schema tanimlari (legacy)
# ---------------------------------------------------------------------------

TOOL_COMMAND_SCHEMA = {
    "name": "tool_command",
    "description": "Guvenlik test araci komutu uretir",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "tool": {
                "type": "string",
                "description": "Calistirilacak arac adi",
            },
            "arguments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Arac argumanlari (her biri ayri eleman)",
            },
            "requires_root": {
                "type": "boolean",
                "description": "Root yetkisi gerekli mi",
            },
            "risk_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Risk seviyesi",
            },
            "explanation": {
                "type": "string",
                "description": "Komut aciklamasi",
            },
        },
        "required": [
            "tool",
            "arguments",
            "requires_root",
            "risk_level",
            "explanation",
        ],
        "additionalProperties": False,
    },
}

AI_RESPONSE_SCHEMA = {
    "name": "ai_response",
    "description": "AI asistan yaniti",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "command": {
                "anyOf": [
                    {"$ref": "#/$defs/tool_command"},
                    {"type": "null"},
                ],
                "description": "Calistirilacak komut (varsa)",
            },
            "message": {
                "type": "string",
                "description": "Kullaniciya mesaj",
            },
            "needs_clarification": {
                "type": "boolean",
                "description": "Daha fazla bilgi gerekli mi",
            },
        },
        "required": ["command", "message", "needs_clarification"],
        "additionalProperties": False,
        "$defs": {"tool_command": TOOL_COMMAND_SCHEMA["schema"]},
    },
}


# ---------------------------------------------------------------------------
# Yardimci fonksiyonlar (legacy)
# ---------------------------------------------------------------------------

def validate_command(data: dict) -> ToolCommand:
    """AI yanitini dogrula ve ToolCommand objesine cevir."""
    return ToolCommand.model_validate(data)


def get_response_format() -> dict:
    """JSON sema zorlamasi kullanan istemciler icin response_format parametresi."""
    return {"type": "json_schema", "json_schema": AI_RESPONSE_SCHEMA}

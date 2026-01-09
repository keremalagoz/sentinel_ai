# SENTINEL AI - JSON Şemaları
# Sprint 2.1: AI yanıt formatları
# OpenAI response_format uyumlu, strict=True için tasarlandı

from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from enum import Enum


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


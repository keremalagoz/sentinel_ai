# SENTINEL AI - Karar Motoru (Orchestrator)
# Sprint 2.2: Hibrit AI sistemi (Local + Cloud)
# 
# Mantık:
# - Basit komutlar → Local LLM (Llama 3 via Docker)
# - Karmaşık senaryolar → Cloud AI (OpenAI GPT-4o-mini)

import os
import json
import re
from typing import Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import ValidationError

from src.ai.schemas import (
    ToolCommand,
    AIResponse,
    RiskLevel,
    validate_command,
    get_openai_response_format,
    TOOL_COMMAND_SCHEMA
)

# .env dosyasını yükle
load_dotenv()


class AIOrchestrator:
    """
    Hibrit AI Karar Motoru.
    
    Kullanıcı girdisini analiz eder ve uygun AI motoruna yönlendirir:
    - Local: Llama 3 (Docker üzerinde, port 8001)
    - Cloud: OpenAI GPT-4o-mini
    
    Güvenlik:
    - Tüm çıktılar JSON şemasına zorlanır (strict mode)
    - Shell injection riski minimize edilir (arguments list formatı)
    """
    
    # Basit komutlar için anahtar kelimeler (Local LLM yeterli)
    SIMPLE_PATTERNS = [
        r"yardım|help|nasıl",
        r"^ping\s",
        r"^nslookup\s",
        r"^whois\s",
        r"basit\s+tara",
        r"host\s+keşf",
        r"port\s+tara",
    ]
    
    # Karmaşık senaryolar (Cloud AI gerekli)
    COMPLEX_PATTERNS = [
        r"senaryo|scenario",
        r"exploit|zafiyet|vulnerability",
        r"kapsamlı|comprehensive",
        r"strateji|strategy",
        r"analiz\s+et|analyze",
        r"çoklu\s+hedef|multiple\s+target",
        r"pentest|penetration",
    ]
    
    # Sistem promptu - AI'ın davranışını tanımlar
    SYSTEM_PROMPT = """Sen SENTINEL AI, bir siber güvenlik test asistanısın.

GÖREV: Kullanıcının doğal dildeki taleplerini güvenlik test komutlarına çevir.

KURALLAR:
1. SADECE güvenlik test araçları için komut üret (nmap, gobuster, nikto, dirb, hydra, sqlmap, vb.)
2. Argümanları MUTLAKA liste olarak ver, string birleştirme YASAK
3. Root gerektiren komutları (SYN scan, raw socket) requires_root=true olarak işaretle
4. Risk seviyesini doğru belirle:
   - low: Pasif tarama, bilgi toplama
   - medium: Aktif tarama, port scan
   - high: Exploit, brute force, sistem değişikliği

ÖRNEKLER:
- "Ağı tara" → nmap -sn 192.168.1.0/24 (low risk)
- "Portları tara" → nmap -sS -sV -p- {target} (medium risk, requires_root=true)
- "Web dizinlerini bul" → gobuster dir -u {target} -w wordlist.txt (medium risk)

ÖNEMLİ:
- Hedef IP/URL verilmemişse {target} placeholder kullan
- Belirsiz taleplerde needs_clarification=true dön
- Her zaman geçerli JSON formatında yanıt ver"""

    def __init__(self):
        """
        Orchestrator'ı başlat.
        
        Environment variables:
        - OPENAI_API_KEY: Cloud AI için
        - LLAMA_SERVICE_URL: Local LLM endpoint (default: http://localhost:8001)
        """
        self._cloud_client: Optional[OpenAI] = None
        self._local_client: Optional[OpenAI] = None
        
        # Cloud client (OpenAI)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "your_openai_api_key_here":
            self._cloud_client = OpenAI(api_key=openai_key)
        
        # Local client (Ollama - OpenAI compatible API)
        llama_url = os.getenv("LLAMA_SERVICE_URL", "http://localhost:8001")
        self._local_client = OpenAI(
            base_url=f"{llama_url}/v1",
            api_key="ollama"  # Ollama requires a dummy key
        )
        
        self._local_available = False
        self._cloud_available = self._cloud_client is not None
        
        # Cache: Servis kontrolu icin (30 saniye gecerli)
        self._last_check_time = 0
        self._check_cache_ttl = 30  # saniye
    
    def check_services(self, force: bool = False) -> Tuple[bool, bool]:
        """
        Servis durumlarını kontrol et (cache mekanizmalı).
        
        Args:
            force: True ise cache'i atla ve yeniden kontrol et
        
        Returns:
            (local_available, cloud_available)
        """
        import time
        current_time = time.time()
        
        # Cache gecerli mi? (TTL icinde ve force degil)
        if not force and (current_time - self._last_check_time) < self._check_cache_ttl:
            return (self._local_available, self._cloud_available)
        
        # Local LLM kontrolü
        try:
            self._local_client.models.list()
            self._local_available = True
        except Exception:
            self._local_available = False
        
        # Cloud kontrolü (API key varlığı yeterli)
        self._cloud_available = self._cloud_client is not None
        
        # Cache guncelle
        self._last_check_time = current_time
        
        return (self._local_available, self._cloud_available)
    
    def _is_complex_query(self, user_input: str) -> bool:
        """
        Sorgunun karmaşık olup olmadığını belirle.
        
        Karmaşık sorgular Cloud AI'ya yönlendirilir.
        """
        input_lower = user_input.lower()
        
        # Karmaşık pattern kontrolü
        for pattern in self.COMPLEX_PATTERNS:
            if re.search(pattern, input_lower):
                return True
        
        # Uzun sorgular genellikle karmaşıktır
        if len(user_input.split()) > 15:
            return True
        
        return False
    
    def _is_simple_query(self, user_input: str) -> bool:
        """
        Sorgunun basit olup olmadığını belirle.
        
        Basit sorgular Local LLM ile işlenebilir.
        """
        input_lower = user_input.lower()
        
        for pattern in self.SIMPLE_PATTERNS:
            if re.search(pattern, input_lower):
                return True
        
        # Kısa sorgular genellikle basittir
        if len(user_input.split()) <= 5:
            return True
        
        return False
    
    def _select_engine(self, user_input: str) -> str:
        """
        Uygun AI motorunu seç.
        
        Returns:
            "local" veya "cloud"
        """
        # Servis durumlarını güncelle
        self.check_services()
        
        # Karmaşık sorgu ve cloud varsa → Cloud
        if self._is_complex_query(user_input) and self._cloud_available:
            return "cloud"
        
        # Basit sorgu ve local varsa → Local
        if self._is_simple_query(user_input) and self._local_available:
            return "local"
        
        # Fallback: Hangisi varsa onu kullan
        if self._local_available:
            return "local"
        if self._cloud_available:
            return "cloud"
        
        raise RuntimeError("Hiçbir AI servisi kullanılamıyor!")
    
    def process(self, user_input: str, target: Optional[str] = None) -> AIResponse:
        """
        Kullanıcı girdisini işle ve AI yanıtı üret.
        
        Args:
            user_input: Kullanıcının doğal dildeki talebi
            target: Hedef IP/URL (opsiyonel)
        
        Returns:
            AIResponse: Komut ve/veya mesaj içeren yanıt
        
        Raises:
            RuntimeError: AI servisi kullanılamıyorsa
        """
        engine = self._select_engine(user_input)
        
        # Hedef bilgisini ekle
        context = user_input
        if target:
            context = f"Hedef: {target}\n\nTalep: {user_input}"
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": context}
        ]
        
        try:
            if engine == "cloud":
                response = self._call_cloud(messages)
            else:
                response = self._call_local(messages)
            
            return self._parse_response(response, engine)
            
        except Exception as e:
            # Hata durumunda fallback yanıt
            return AIResponse(
                command=None,
                message=f"AI işleme hatası: {str(e)}",
                needs_clarification=True
            )
    
    def _call_cloud(self, messages: list) -> str:
        """
        Cloud AI (OpenAI) çağrısı.
        
        Structured output kullanır (strict=True).
        """
        if not self._cloud_client:
            raise RuntimeError("Cloud AI yapılandırılmamış")
        
        response = self._cloud_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format=get_openai_response_format(),
            temperature=0.3,  # Düşük temperature = tutarlı çıktı
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    def _call_local(self, messages: list) -> str:
        """
        Local LLM (Llama 3) çağrısı.
        
        Ollama OpenAI-compatible API kullanır.
        """
        # Local model için JSON talimatı ekle
        json_instruction = """

YANIT FORMATI (STRICT JSON):
{
    "command": {
        "tool": "araç_adı",
        "arguments": ["arg1", "arg2"],
        "requires_root": false,
        "risk_level": "low|medium|high",
        "explanation": "açıklama"
    },
    "message": "kullanıcıya mesaj",
    "needs_clarification": false
}

Eğer komut üretemiyorsan command=null yap."""
        
        messages[-1]["content"] += json_instruction
        
        response = self._local_client.chat.completions.create(
            model="llama3:8b-instruct-q4_K_M",
            messages=messages,
            temperature=0.3,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    def _extract_json(self, text: str) -> str:
        """
        Text içinden JSON objesini çıkar.
        
        Local LLM bazen yanıtın başına/sonuna text ekler.
        Bu fonksiyon nested bracket'ları düzgün handle eder.
        """
        # Markdown code block kontrolü (re zaten dosya başında import edilmiş)
        pattern = r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        
        # Normal JSON arama (nested bracket'ları düzgün handle et)
        start = text.find('{')
        if start == -1:
            return text
        
        # Bracket sayarak doğru kapanış noktasını bul
        depth = 0
        end = start
        for i, char in enumerate(text[start:], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        
        if end > start:
            return text[start:end + 1]
        
        return text
    
    def _parse_response(self, raw_response: str, engine: str) -> AIResponse:
        """
        AI yanıtını parse et ve doğrula.
        
        JSON formatına uymayan yanıtlar için fallback uygular.
        """
        try:
            # JSON'u text içinden çıkar
            json_str = self._extract_json(raw_response)
            
            # JSON parse
            data = json.loads(json_str)
            
            # Pydantic ile doğrula
            if data.get("command"):
                command = validate_command(data["command"])
            else:
                command = None
            
            return AIResponse(
                command=command,
                message=data.get("message", "Komut hazır."),
                needs_clarification=data.get("needs_clarification", False)
            )
            
        except json.JSONDecodeError:
            # JSON değilse, raw text olarak dön
            return AIResponse(
                command=None,
                message=raw_response,
                needs_clarification=True
            )

        except ValidationError:
            # Komut, güvenlik doğrulamasından geçemedi (allowlist/arg policy)
            return AIResponse(
                command=None,
                message="Uretilen komut guvenlik politikasina uymuyor. Lutfen talebi daha net yazin ve izinli araclarla tekrar deneyin.",
                needs_clarification=True
            )
            
        except Exception as e:
            return AIResponse(
                command=None,
                message=f"Yanıt işleme hatası: {str(e)}\n\nHam yanıt: {raw_response[:200]}",
                needs_clarification=True
            )
    
    def get_status(self) -> dict:
        """
        Orchestrator durumunu döndür.
        
        UI'da servis durumu göstermek için kullanılır.
        """
        self.check_services()
        
        return {
            "local": {
                "available": self._local_available,
                "model": "llama3",
                "url": os.getenv("LLAMA_SERVICE_URL", "http://localhost:8001")
            },
            "cloud": {
                "available": self._cloud_available,
                "model": "gpt-4o-mini",
                "configured": os.getenv("OPENAI_API_KEY") is not None
            }
        }


# =============================================================================
# Convenience Functions
# =============================================================================

_orchestrator: Optional[AIOrchestrator] = None


def get_orchestrator() -> AIOrchestrator:
    """
    Singleton orchestrator instance döndür.
    
    Kullanım:
        from src.ai.orchestrator import get_orchestrator
        
        orch = get_orchestrator()
        response = orch.process("Ağı tara", target="192.168.1.0/24")
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AIOrchestrator()
    return _orchestrator


def quick_command(user_input: str, target: Optional[str] = None) -> Optional[ToolCommand]:
    """
    Hızlı komut üretimi.
    
    Returns:
        ToolCommand veya None (komut üretilemezse)
    """
    orch = get_orchestrator()
    response = orch.process(user_input, target)
    return response.command


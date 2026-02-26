# SENTINEL AI - Intent Resolver
# Action Planner v2: LLM sadece kullanici niyetini belirler
#
# LLM'in TEK gorevi: Kullanicinin ne yapmak istedigini anlamak
# LLM ASLA uretmez: tool adi, argumanlar, risk seviyesi, requires_root

import os
import json
import logging
import time
import threading
from typing import Optional, List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

from src.ai.schemas import Intent, IntentType

load_dotenv()
logger = logging.getLogger(__name__)


# =============================================================================
# INTENT RESOLVER PROMPT
# =============================================================================

INTENT_RESOLVER_PROMPT = """Sen bir niyet cozucusun (Intent Resolver).
Gorev: Kullanicinin siber guvenlik talebini analiz et ve SADECE niyetini belirle.

ONEMLI KURALLAR:
1. ASLA tool adi yazma (nmap, gobuster, vb.)
2. ASLA argumanlar uretme (-sS, -p, vb.)
3. ASLA risk seviyesi veya root bilgisi verme
4. SADECE kullanicinin ne yapmak istedigini anla
5. Kullanici "hedef", "target", "ağ" gibi GENEL ifadeler kullaniyorsa target=null birak
   (Cunku hedef bilgisi UI'dan ayrıca gelecek)
6. SADECE kullanici SPESIFIK IP/domain belirtirse target doldur
   - Spesifik: "192.168.1.1", "example.com", "10.0.0.1/24"
   - Genel: "hedef", "hedef ağ", "target", "bu sistem"

INTENT TURLERI:
- host_discovery: Agdaki aktif cihazlari bul, ping taramasi
- port_scan: Port taramasi, hangi portlar acik
- service_detection: Servis ve versiyon tespiti
- os_detection: Isletim sistemi tespiti
- vuln_scan: Zafiyet taramasi
- web_dir_enum: Web dizin/dosya kesfet
- web_vuln_scan: Web sunucu zafiyet taramasi
- dns_lookup: DNS sorgusu
- whois_lookup: Domain whois bilgisi
- brute_force_ssh: SSH brute force
- brute_force_http: HTTP form brute force
- sql_injection: SQL injection testi
- info_query: Genel bilgi sorusu (komut gerektirmez)
- unknown: Anlasılamadi, netlestime gerekli

CIKTI FORMATI (STRICT JSON):
{
    "intent_type": "...",
    "target": "hedef IP/domain veya null",
    "params": {
        "ports": "port araligi (varsa)",
        "wordlist": "wordlist tercihi (varsa)"
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "confidence": 0.95
}

CONFIDENCE KURALLARI:
- 0.9-1.0: Niyet cok net, kesin esleme
- 0.7-0.9: Niyet buyuk olasilikla dogru
- 0.5-0.7: Belirsiz, clarification gerekebilir
- 0.0-0.5: Anlasılamadı, needs_clarification=true yap

ORNEKLER:

Girdi: "192.168.1.0/24 agini tara"
Cikti: {"intent_type": "host_discovery", "target": "192.168.1.0/24", "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "example.com portlarini tara"
Cikti: {"intent_type": "port_scan", "target": "example.com", "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "hedef ağda tam tarama yap"
Cikti: {"intent_type": "port_scan", "target": null, "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.8}

Girdi: "tarama yap"
Cikti: {"intent_type": "port_scan", "target": null, "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.6}

Girdi: "80 ve 443 portlarini kontrol et 10.0.0.1 de"
Cikti: {"intent_type": "port_scan", "target": "10.0.0.1", "params": {"ports": "80,443"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "web sitesinde dizin ara"
Cikti: {"intent_type": "web_dir_enum", "target": null, "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.85}

Girdi: "nmap nedir?"
Cikti: {"intent_type": "info_query", "target": null, "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "birseyler yap"
Cikti: {"intent_type": "unknown", "target": null, "params": {}, "needs_clarification": true, "clarification_reason": "Ne yapmak istediginizi anlayamadim", "confidence": 0.2}
"""


class IntentResolver:
    """
    LLM tabanli niyet cozucusu.
    
    Kullanici girdisini alir, LLM'e gonderir ve Intent objesi doner.
    LLM sadece niyet belirler, tool/argumanlar Registry'den gelir.
    """
    
    def __init__(
        self,
        model: str = "whiterabbitneo",
        base_url: str = None,
        request_timeout: Optional[float] = None,
        max_attempts: Optional[int] = None,
    ):
        """
        IntentResolver'i baslat.
        
        Args:
            model: Kullanilacak local model (whiterabbitneo, llama3:8b, vb.)
            base_url: Ollama endpoint (default: localhost:11434)
            request_timeout: Her LLM istegi icin timeout (saniye)
            max_attempts: LLM istegi icin max deneme sayisi
        """
        self._model = model
        self._request_timeout = float(request_timeout or os.getenv("INTENT_LLM_TIMEOUT", "20"))
        self._max_attempts = max(1, int(max_attempts or os.getenv("INTENT_LLM_MAX_ATTEMPTS", "2")))
        
        # Local Ollama client
        self._base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self._client = OpenAI(
            base_url=f"{self._base_url}/v1",
            api_key="ollama"  # Ollama requires dummy key
        )
    
    def resolve(self, user_input: str, target_hint: Optional[str] = None) -> Intent:
        """
        Kullanici girdisinden Intent cozumle.
        
        Args:
            user_input: Kullanicinin dogal dildeki talebi
            target_hint: UI'dan gelen hedef bilgisi (opsiyonel)
        
        Returns:
            Intent objesi
        """
        # Hedef bilgisini ekle
        context = user_input
        if target_hint:
            context = f"[Hedef: {target_hint}]\n{user_input}"
        
        messages = [
            {"role": "system", "content": INTENT_RESOLVER_PROMPT},
            {"role": "user", "content": context}
        ]
        
        try:
            # Local LLM cagir
            response = self._call_local_with_retry(messages)
            return self._parse_response(response)
            
        except Exception as e:
            logger.warning("Intent resolver failed after retries: %s", e)

            # Hata durumunda UNKNOWN don
            return Intent(
                intent_type=IntentType.UNKNOWN,
                target=None,
                params={},
                needs_clarification=True,
                clarification_reason=f"AI hatasi: {str(e)}"
            )

    def _call_local_with_retry(self, messages: List[Dict[str, str]]) -> str:
        """Local çağrıyı timeout+retry ile çalıştır."""
        last_error: Optional[Exception] = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                return self._call_local(messages)
            except Exception as exc:
                last_error = exc
                if attempt >= self._max_attempts:
                    break

                # Hafif backoff: 0.2s, 0.4s, 0.6s ...
                backoff = 0.2 * attempt
                logger.debug(
                    "IntentResolver attempt %s/%s failed, retrying in %.1fs: %s",
                    attempt,
                    self._max_attempts,
                    backoff,
                    exc,
                )
                time.sleep(backoff)

        if last_error:
            raise last_error
        raise RuntimeError("Intent resolver failed without explicit error")
    
    def _call_local(self, messages: List[Dict[str, str]]) -> str:
        """Local Ollama LLM cagrisi"""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.1,  # Dusuk temperature = tutarli cikti
            max_tokens=300,
            timeout=self._request_timeout,
        )
        return response.choices[0].message.content
    
    def _parse_response(self, raw_response: str) -> Intent:
        """
        LLM yanitini Intent objesine donustur.
        
        JSON parse + validation yapar.
        """
        try:
            # JSON'u cikar
            json_str = self._extract_json(raw_response)
            data = json.loads(json_str)
            
            is_valid, error = self._validate_payload(data)
            if not is_valid:
                return Intent(
                    intent_type=IntentType.UNKNOWN,
                    target=None,
                    params={},
                    needs_clarification=True,
                    clarification_reason=f"Gecersiz JSON: {error}"
                )

            # IntentType'a donustur
            intent_type_str = data.get("intent_type", "unknown")
            try:
                intent_type = IntentType(intent_type_str)
            except ValueError:
                intent_type = IntentType.UNKNOWN
            
            return Intent(
                intent_type=intent_type,
                target=data.get("target"),
                params=data.get("params", {}),
                needs_clarification=data.get("needs_clarification", False),
                clarification_reason=data.get("clarification_reason"),
                confidence=float(data.get("confidence", 1.0)),
            )
            
        except json.JSONDecodeError:
            return Intent(
                intent_type=IntentType.UNKNOWN,
                target=None,
                params={},
                needs_clarification=True,
                clarification_reason="AI yaniti parse edilemedi"
            )
    
    def _extract_json(self, text: str) -> str:
        """Text icinden JSON objesini cikar"""
        import re
        
        # Markdown code block
        pattern = r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        
        # Normal JSON
        start = text.find('{')
        if start == -1:
            return text
        
        # Bracket sayarak dogru kapanisi bul
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

    def _validate_payload(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """Intent JSON payload dogrulama (strict)"""
        if not isinstance(data, dict):
            return (False, "payload dict degil")

        required_keys = {
            "intent_type",
            "target",
            "params",
            "needs_clarification",
            "clarification_reason",
        }
        # confidence opsiyonel kabul edilir (eski LLM uyumlulugu icin)
        allowed_keys = required_keys | {"confidence"}

        if not required_keys.issubset(set(data.keys())):
            return (False, "beklenen alanlar eksik")

        if not set(data.keys()).issubset(allowed_keys):
            return (False, "beklenmeyen alan mevcut")

        if not isinstance(data["intent_type"], str):
            return (False, "intent_type string degil")

        if data["target"] is not None and not isinstance(data["target"], str):
            return (False, "target string veya null olmali")

        if not isinstance(data["params"], dict):
            return (False, "params dict olmali")

        if not isinstance(data["needs_clarification"], bool):
            return (False, "needs_clarification boolean olmali")

        if data["clarification_reason"] is not None and not isinstance(data["clarification_reason"], str):
            return (False, "clarification_reason string veya null olmali")

        return (True, "")
    
    def check_available(self) -> bool:
        """LLM servisinin kullanilabilir olup olmadigini kontrol et"""
        try:
            self._client.models.list()
            return True
        except Exception:
            return False


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_resolver: Optional[IntentResolver] = None
_resolver_lock = threading.Lock()


def get_intent_resolver(model: str = "whiterabbitneo") -> IntentResolver:
    """Singleton IntentResolver instance doner (thread-safe)"""
    global _resolver
    if _resolver is None:
        with _resolver_lock:
            if _resolver is None:
                _resolver = IntentResolver(model=model)
    return _resolver


def quick_resolve(user_input: str, target: Optional[str] = None) -> Intent:
    """Hizli intent cozumleme"""
    resolver = get_intent_resolver()
    return resolver.resolve(user_input, target)


# =============================================================================
# DEBUG
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SENTINEL AI - Intent Resolver Test")
    print("=" * 60)
    
    resolver = IntentResolver(model="whiterabbitneo")
    
    # Servis kontrolu
    print(f"\nLLM Available: {resolver.check_available()}")
    
    # Test cases
    test_inputs = [
        "192.168.1.0/24 agini tara",
        "example.com portlarini kontrol et",
        "google.com DNS sorgusu yap",
        "web sitesinde dizin ara",
        "nmap nedir?",
    ]
    
    for user_input in test_inputs:
        print(f"\n{'='*60}")
        print(f"Input: {user_input}")
        print("-" * 60)
        
        intent = resolver.resolve(user_input)
        
        print(f"Intent: {intent.intent_type.value}")
        print(f"Target: {intent.target}")
        print(f"Params: {intent.params}")
        print(f"Clarify: {intent.needs_clarification}")
        if intent.clarification_reason:
            print(f"Reason: {intent.clarification_reason}")

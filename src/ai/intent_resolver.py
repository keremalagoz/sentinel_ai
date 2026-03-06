# SENTINEL AI - Intent Resolver
# Action Planner v2: LLM sadece kullanici niyetini belirler
#
# LLM'in TEK gorevi: Kullanicinin ne yapmak istedigini anlamak
# LLM ASLA uretmez: tool adi, argumanlar, risk seviyesi, requires_root

import os
import json
import logging
import re
import time
import threading
from typing import Optional, List, Dict, Any
from openai import OpenAI

from src.ai.schemas import Intent, IntentType

logger = logging.getLogger(__name__)

# Pre-compiled regex for JSON extraction (H5 optimization)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```")


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
7. KESIN KURAL: Eger kullanici "TXT", "A", "MX", "NS", "AAAA" gibi kayitlari soruyorsa, bu %100 "dns_lookup" niyetidir, ASLA "whois_lookup" secmeyin!

INTENT TURLERI:
- host_discovery: Agdaki aktif cihazlari bul, ping taramasi, hangi cihazlar acik
- port_scan: Port taramasi, hangi portlar acik, TCP/SYN/UDP tarama
- service_detection: Servis ve versiyon tespiti (hangi yazilim/versiyon calisiyor)
- os_detection: Isletim sistemi tespiti (Windows/Linux/macOS)
- vuln_scan: Ag servisi zafiyet taramasi (nmap NSE script'leri, IP hedefli, "zafiyet tara")
- ssl_scan: SSL/TLS sertifika analizi, cipher suite kontrolu
- web_dir_enum: Web dizin/dosya kesfet (gobuster, dirb)
- web_vuln_scan: Web sunucu/uygulama taramasi (nikto, web teknoloji tespiti, "web zafiyet", "web tara")
- dns_lookup: DNS sorgusu, IP adresi tespit etme (A, MX, NS, TXT kayitlari bulma)
- subdomain_enum: Alt alan adi kesfet (subdomain brute force)
- whois_lookup: Domain kime ait, alan adi tescil/sahiplik bilgileri, whois
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
        "ports": "port araligi (varsa, ornek: '80,443' veya '1-1000')",
        "top_ports": "en populer N port (varsa, tam sayi, ornek: 100)",
        "scan_type": "tarama tipi (varsa: 'sT','sS','sU')",
        "timing": "hiz seviyesi 0-5 (varsa, tam sayi, ornek: 4)",
        "service_detection": "versiyon tespiti (true/false)",
        "no_dns": "DNS cozumleme kapatma (true/false)",
        "verbose": "detayli cikti (true/false)",
        "no_ping": "ping atmadan tara (true/false)",
        "osscan_guess": "OS tahmini yap (true/false)",
        "aggressive": "agresif mod, nmap -A (true/false)",
        "traceroute": "traceroute bilgisi ekle (true/false)",
        "scripts": "NSE script kategorisi (varsa, ornek: 'vuln', 'default')",
        "exclude": "taramadan haric tutulacak IP (varsa)",
        "port": "tek port numarasi (ssl_scan icin, tam sayi, ornek: 8443)",
        "tls_version": "TLS versiyon filtresi (varsa: '1.2', '1.3')",
        "starttls": "STARTTLS protokolu (varsa: 'smtp', 'pop3', 'imap', 'ftp')",
        "version_intensity": "versiyon tespit yogunlugu 0-9 (varsa, tam sayi)",
        "version_mode": "versiyon tespiti modu (varsa: 'default', 'light', 'all')",
        "wordlist": "wordlist tercihi (varsa)",
        "record_type": "DNS kayit tipi (varsa: 'A','AAAA','MX','NS','TXT')",
        "extensions": "dosya uzantilari (varsa, ornek: 'php,html,txt')",
        "username": "kullanici adi (varsa)"
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "confidence": 0.95
}

NOT: params icinde sadece kullanicinin BELIRTTIGI parametreleri ekle.
Belirtilmeyen parametreleri EKLEME, bos birak.

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

Girdi: "192.168.0.8 bu ip adresinin ilk 100 portunu tara ve versiyon bilgilerini tara"
Cikti: {"intent_type": "port_scan", "target": "192.168.0.8", "params": {"top_ports": 100, "service_detection": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "10.0.0.1 ilk 100 portu SYN taramasi ile tara"
Cikti: {"intent_type": "port_scan", "target": "10.0.0.1", "params": {"top_ports": 100, "scan_type": "sS"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "192.168.1.1 en populer 50 portunu tara"
Cikti: {"intent_type": "port_scan", "target": "192.168.1.1", "params": {"top_ports": 50}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "hedef ağda tam tarama yap"
Cikti: {"intent_type": "port_scan", "target": null, "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.8}

Girdi: "tarama yap"
Cikti: {"intent_type": "port_scan", "target": null, "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.6}

Girdi: "80 ve 443 portlarini kontrol et 10.0.0.1 de"
Cikti: {"intent_type": "port_scan", "target": "10.0.0.1", "params": {"ports": "80,443"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "10.0.0.5 hizli port scan yap T4 ile DNS cozumleme yapma"
Cikti: {"intent_type": "port_scan", "target": "10.0.0.5", "params": {"timing": 4, "no_dns": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "10.0.0.1 uzerinde agresif tarama baslat"
Cikti: {"intent_type": "port_scan", "target": "10.0.0.1", "params": {"aggressive": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "192.168.1.1 ping atmadan tara"
Cikti: {"intent_type": "port_scan", "target": "192.168.1.1", "params": {"no_ping": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "verbose port taramasi yap"
Cikti: {"intent_type": "port_scan", "target": null, "params": {"verbose": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.85}

Girdi: "web sitesinde dizin ara php ve html dosyalarini bul"
Cikti: {"intent_type": "web_dir_enum", "target": null, "params": {"extensions": "php,html"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.85}

Girdi: "http://10.0.0.1 dizin ara uzanti php,html,txt"
Cikti: {"intent_type": "web_dir_enum", "target": "http://10.0.0.1", "params": {"extensions": "php,html,txt"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "192.168.1.1 gobuster ile dosya bul"
Cikti: {"intent_type": "web_dir_enum", "target": "http://192.168.1.1", "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.90}

Girdi: "https://hedef.com web dizin kesfet redirect takip et TLS dogrulama yapma"
Cikti: {"intent_type": "web_dir_enum", "target": "https://hedef.com", "params": {"follow_redirect": true, "no_tls_validation": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "http://192.168.1.1:8080 dizin taramasi 20 thread ile"
Cikti: {"intent_type": "web_dir_enum", "target": "http://192.168.1.1:8080", "params": {"threads": 20}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "http://example.com web zafiyet taramasi yap"
Cikti: {"intent_type": "web_vuln_scan", "target": "http://example.com", "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "192.168.1.100 web sunucu teknolojilerini tespit et"
Cikti: {"intent_type": "web_vuln_scan", "target": "http://192.168.1.100", "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.90}

Girdi: "nmap ile 10.0.0.1 i tara 80,443 portlari agresif mod ping atma"
Cikti: {"intent_type": "port_scan", "target": "10.0.0.1", "params": {"ports": "80,443", "aggressive": true, "no_ping": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "192.168.1.10 uzerinde ilk 50 portu tara servisleri bul T4 hizinda"
Cikti: {"intent_type": "port_scan", "target": "192.168.1.10", "params": {"top_ports": 50, "service_detection": true, "timing": 4}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "hedef.com isletim sistemi tahmini yap ve traceroute ekle"
Cikti: {"intent_type": "os_detection", "target": "hedef.com", "params": {"osscan_guess": true, "traceroute": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "google.com zafiyet tara nse scriptleri ile dns cozme"
Cikti: {"intent_type": "vuln_scan", "target": "google.com", "params": {"no_dns": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "10.0.0.1 UDP taramasi yap port 53,161 verbose aktif"
Cikti: {"intent_type": "port_scan", "target": "10.0.0.1", "params": {"scan_type": "sU", "ports": "53,161", "verbose": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "http://test.com dizin ara 32 thread kullan tls yok say"
Cikti: {"intent_type": "web_dir_enum", "target": "http://test.com", "params": {"threads": 32, "no_tls_validation": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "example.com wfuzz gibi dizin bul yonlendirmeleri takip et kelime listesi /tmp/wordlist.txt"
Cikti: {"intent_type": "web_dir_enum", "target": "example.com", "params": {"follow_redirect": true, "wordlist": "/tmp/wordlist.txt"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "http://10.0.0.1:8080 nikto ile tara"
Cikti: {"intent_type": "web_vuln_scan", "target": "http://10.0.0.1:8080", "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "example.com MX kayitlarini sorgula"
Cikti: {"intent_type": "dns_lookup", "target": "example.com", "params": {"record_type": "MX"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "google.com TXT kayitlarini bul"
Cikti: {"intent_type": "dns_lookup", "target": "google.com", "params": {"record_type": "TXT"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "example.com DNS sorgusu 8.8.8.8 sunucusundan yap"
Cikti: {"intent_type": "dns_lookup", "target": "example.com", "params": {"dns_server": "8.8.8.8"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "example.com AAAA kayitlari nedir"
Cikti: {"intent_type": "dns_lookup", "target": "example.com", "params": {"record_type": "AAAA"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "example.com SSL sertifika analizi port 8443"
Cikti: {"intent_type": "ssl_scan", "target": "example.com", "params": {"port": 8443}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "example.com whois bilgisi"
Cikti: {"intent_type": "whois_lookup", "target": "example.com", "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "10.0.0.1 SSH brute force admin kullanicisi rockyou.txt"
Cikti: {"intent_type": "brute_force_ssh", "target": "10.0.0.1", "params": {"username": "admin", "wordlist": "rockyou.txt"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "192.168.1.50 SSH saldirisi root port 2222 10 thread ile"
Cikti: {"intent_type": "brute_force_ssh", "target": "192.168.1.50", "params": {"username": "root", "port": 2222, "threads": 10}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "http://example.com/login HTTP form brute force admin pass.txt"
Cikti: {"intent_type": "brute_force_http", "target": "http://example.com/login", "params": {"username": "admin", "wordlist": "pass.txt"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "http://example.com/page?id=1 SQL injection testi yap risk 3 level 5"
Cikti: {"intent_type": "sql_injection", "target": "http://example.com/page?id=1", "params": {"risk": 3, "level": 5}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "http://10.0.0.1 sqlmap ile tara veritabanlarini bul formlari test et"
Cikti: {"intent_type": "sql_injection", "target": "http://10.0.0.1", "params": {"dbs": true, "forms": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "nmap nedir?"
Cikti: {"intent_type": "info_query", "target": null, "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "birseyler yap"
Cikti: {"intent_type": "unknown", "target": null, "params": {}, "needs_clarification": true, "clarification_reason": "Ne yapmak istediginizi anlayamadim", "confidence": 0.2}

Girdi: "192.168.1.0/24 agini tara ama 192.168.1.1 haric tut"
Cikti: {"intent_type": "host_discovery", "target": "192.168.1.0/24", "params": {"exclude": "192.168.1.1"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "10.0.0.0/24 hostlarini bul T4 hizinda DNS sorgusu yapmadan"
Cikti: {"intent_type": "host_discovery", "target": "10.0.0.0/24", "params": {"timing": 4, "no_dns": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "192.168.1.10 servislerini tespit et"
Cikti: {"intent_type": "service_detection", "target": "192.168.1.10", "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "10.0.0.1 80 ve 443 portlarindaki servisleri ve versiyonlari bul"
Cikti: {"intent_type": "service_detection", "target": "10.0.0.1", "params": {"ports": "80,443"}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "172.16.0.1 tum versiyon bilgilerini derinlemesine bul"
Cikti: {"intent_type": "service_detection", "target": "172.16.0.1", "params": {"version_intensity": 9}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "192.168.1.1 isletim sistemini tespit et"
Cikti: {"intent_type": "os_detection", "target": "192.168.1.1", "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "10.0.0.1 OS ve servis tespiti birlikte yap tahmini ac"
Cikti: {"intent_type": "os_detection", "target": "10.0.0.1", "params": {"service_detection": true, "osscan_guess": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "192.168.1.1 zafiyet taramasi yap"
Cikti: {"intent_type": "vuln_scan", "target": "192.168.1.1", "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "10.0.0.1 80 ve 443 portlarinda zafiyet tara T3 hizinda"
Cikti: {"intent_type": "vuln_scan", "target": "10.0.0.1", "params": {"ports": "80,443", "timing": 3}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "example.com SSL sertifikasini analiz et"
Cikti: {"intent_type": "ssl_scan", "target": "example.com", "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "10.0.0.1 8443 portundaki SSL kontrol et"
Cikti: {"intent_type": "ssl_scan", "target": "10.0.0.1", "params": {"port": 8443}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "192.168.1.1 port ve versiyon taramasi yap traceroute ile"
Cikti: {"intent_type": "port_scan", "target": "192.168.1.1", "params": {"service_detection": true, "traceroute": true}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}

Girdi: "example.com alt alan adlarini kesfet"
Cikti: {"intent_type": "subdomain_enum", "target": "example.com", "params": {}, "needs_clarification": false, "clarification_reason": null, "confidence": 0.95}
"""


class IntentResolver:
    """
    LLM tabanli niyet cozucusu.
    
    Kullanici girdisini alir, LLM'e gonderir ve Intent objesi doner.
    LLM sadece niyet belirler, tool/argumanlar Registry'den gelir.
    """
    
    def __init__(
        self,
        model: str = "qwen2.5:3b",
        base_url: str = None,
        request_timeout: Optional[float] = None,
        max_attempts: Optional[int] = None,
    ):
        """
        IntentResolver'i baslat.
        
        Args:
            model: Kullanilacak local model (qwen2.5:3b, whiterabbitneo, llama3:8b, vb.)
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
        # Markdown code block
        match = _JSON_BLOCK_RE.search(text)
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
        """Intent JSON payload dogrulama (tolerant).

        Beklenmeyen alanlar silently drop edilir — payload reddedilmez.
        Bu sayede LLM ekstra alan eklese bile (reasoning, explanation, vb.)
        intent+params korunur.
        """
        if not isinstance(data, dict):
            return (False, "payload dict degil")

        required_keys = {
            "intent_type",
            "target",
            "params",
        }
        # Diger alanlar opsiyonel (3B model bazen unutuyor)
        allowed_keys = required_keys | {"needs_clarification", "clarification_reason", "confidence"}

        if not required_keys.issubset(set(data.keys())):
            return (False, "beklenen alanlar eksik")

        # Varsayilan degerleri ekle
        data.setdefault("needs_clarification", False)
        data.setdefault("clarification_reason", None)

        # Beklenmeyen alanlari sil ama payload'i reddetme
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            logger.debug("Stripping unexpected keys from LLM payload: %s", extra_keys)
            for k in extra_keys:
                del data[k]

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


def get_intent_resolver(model: str = "qwen2.5:3b") -> IntentResolver:
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
    
    resolver = IntentResolver(model="qwen2.5:3b")
    
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

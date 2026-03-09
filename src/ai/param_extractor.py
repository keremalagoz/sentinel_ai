"""Deterministic regex-based extraction helpers for params and target hints.

Sprint 3.7:
- Track A2: Intent-specific parameter extraction
- Track B1: Target pre-extraction (URL/IP/domain)
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from src.ai.schemas import IntentType


class ParamExtractor:
    """Extract tool params and target candidates from free-form user input."""

    _IPV4_OR_CIDR_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?)\b")
    _URL_RE = re.compile(r"\b(https?://[^\s]+)", re.IGNORECASE)
    _DOMAIN_RE = re.compile(
        r"\b((?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,})\b"
    )

    _PORT_RE = re.compile(r"(?:-p\s*|ports?\s*[:=]?\s*)(\d[\d,\-]+)", re.IGNORECASE)
    _TOP_PORTS_RE = re.compile(
        r"(?:ilk|top|en\s+pop[u\xfc]ler)\s+(\d+)\s+port[u\xfc]?"
        r"|--top-ports\s+(\d+)"
        r"|(\d+)\s+(?:pop[u\xfc]ler|\xf6nemli|yayg[i\u0131]n)\s+port[u\xfc]?",
        re.IGNORECASE,
    )
    _TIMING_RE = re.compile(r"(?:\b[Tt](\d)\b|timing\s*[:=]?\s*(\d)|h[i\u0131]z\s*(\d))", re.IGNORECASE)
    _NO_DNS_RE = re.compile(
        r"(dns\s*(yapma|[c\xe7][o\xf6]z[u\xfc]mleme\s*(yap|kapat)|yok|kapat|olmadan)|-n\b|no.?dns)",
        re.IGNORECASE,
    )
    _SVC_DETECT_RE = re.compile(r"(versiyon|version|servis\s+tespit|servis\s+versiyon|-sV\b)", re.IGNORECASE)
    _AGGRESSIVE_RE = re.compile(r"(agresif|aggressive|-A\b|full\s+scan|tam\s+tarama)", re.IGNORECASE)
    _TRACEROUTE_RE = re.compile(r"(traceroute|--traceroute)", re.IGNORECASE)
    _SYN_RE = re.compile(r"(SYN|-sS)\b", re.IGNORECASE)
    _UDP_RE = re.compile(r"(UDP|-sU)\b", re.IGNORECASE)
    _NO_PING_RE = re.compile(r"(ping\s*(atma|olmadan|yok)|no.?ping|-Pn\b)", re.IGNORECASE)
    _VERBOSE_RE = re.compile(r"(verbose|detayl[i\u0131]|ayr[i\u0131]nt[i\u0131]l[i\u0131]|-v\b)", re.IGNORECASE)
    _OSSCAN_RE = re.compile(r"(osscan.?guess|os\s+tahmin|--osscan-guess)", re.IGNORECASE)
    _SCRIPTS_RE = re.compile(r"(?:script|nse|scripts?)\s*[:=]?\s*([\w,\-]+)", re.IGNORECASE)
    _SCRIPTS_PREFIX_RE = re.compile(r"\b([\w\-]+)\s+script(?:ler(?:i)?)?\b", re.IGNORECASE)

    _EXT_RE = re.compile(
        r"(?:uzant[i\u0131]|extension|ext|-x)\s*[:\s]?\s*([a-zA-Z0-9,]+)",
        re.IGNORECASE,
    )
    _THREADS_RE = re.compile(r"(?:thread|i[s\u015f][c\xe7]i|paralel|-t)\s*(\d+)", re.IGNORECASE)
    _WORDLIST_RE = re.compile(r"(?:wordlist|s[o\xf6]zl[u\xfc]k|kelime\s*liste)\s*[:\s]?\s*(\S+)", re.IGNORECASE)
    _RECORD_TYPE_RE = re.compile(r"\b(MX|AAAA|NS|TXT|CNAME|SOA|PTR|SRV|A)\b\s*(?:kay[i\u0131]t|record)?", re.IGNORECASE)

    _SSL_PORT_RE = re.compile(r"(?:port\s*[:=]?\s*|:)(\d{2,5})", re.IGNORECASE)
    _TLS_VER_RE = re.compile(r"tls\s*1\.?(2|3)|tls1_(2|3)", re.IGNORECASE)

    _LEVEL_RE = re.compile(r"(?:level|seviye)\s*(\d)", re.IGNORECASE)
    _RISK_RE = re.compile(r"(?:risk)\s*(\d)", re.IGNORECASE)

    _NMAP_INTENTS = frozenset(
        {
            IntentType.HOST_DISCOVERY,
            IntentType.PORT_SCAN,
            IntentType.SERVICE_DETECTION,
            IntentType.OS_DETECTION,
            IntentType.VULN_SCAN,
        }
    )

    _WELL_KNOWN_DNS = {"8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1"}

    @classmethod
    def extract_target(cls, user_input: str) -> Optional[str]:
        """Extract best target candidate from text: URL > IPv4/CIDR > domain."""
        if not user_input:
            return None

        url_match = cls._URL_RE.search(user_input)
        if url_match:
            return url_match.group(1)

        for m in cls._IPV4_OR_CIDR_RE.finditer(user_input):
            val = m.group(1)
            if val in cls._WELL_KNOWN_DNS:
                continue
            return val

        domain_match = cls._DOMAIN_RE.search(user_input)
        if domain_match:
            return domain_match.group(1)

        return None

    @classmethod
    def extract(cls, text: str, intent_type: IntentType) -> Dict[str, Any]:
        """Intent-specific deterministic parameter extraction."""
        params: Dict[str, Any] = {}

        if intent_type in cls._NMAP_INTENTS:
            cls._extract_nmap_params(text, params)
        elif intent_type == IntentType.WEB_DIR_ENUM:
            cls._extract_web_dir_params(text, params)
        elif intent_type == IntentType.DNS_LOOKUP:
            m = cls._RECORD_TYPE_RE.search(text)
            if m:
                params["record_type"] = m.group(1).upper()
        elif intent_type == IntentType.SSL_SCAN:
            m = cls._SSL_PORT_RE.search(text)
            if m:
                params["port"] = int(m.group(1))
            m = cls._TLS_VER_RE.search(text)
            if m:
                val = m.group(1) or m.group(2)
                if val:
                    params["tls_version"] = f"1.{val}"
        elif intent_type in (IntentType.BRUTE_FORCE_SSH, IntentType.BRUTE_FORCE_HTTP):
            m = re.search(
                r"(?:kullan[i\u0131]c[i\u0131]|user(?:name)?|login)[:\s]+([\w.-]+)",
                text,
                re.IGNORECASE,
            )
            if m:
                params["username"] = m.group(1)
            m = cls._WORDLIST_RE.search(text)
            if m:
                params["wordlist"] = m.group(1)
            m = cls._THREADS_RE.search(text)
            if m:
                params["threads"] = int(m.group(1))
        elif intent_type == IntentType.SQL_INJECTION:
            m = cls._LEVEL_RE.search(text)
            if m:
                params["level"] = int(m.group(1))
            m = cls._RISK_RE.search(text)
            if m:
                params["risk"] = int(m.group(1))
            if re.search(r"(form|--forms)", text, re.IGNORECASE):
                params["forms"] = True
            if re.search(r"(veritaban|database|--dbs)", text, re.IGNORECASE):
                params["dbs"] = True

        return params

    @classmethod
    def _extract_nmap_params(cls, text: str, params: Dict[str, Any]) -> None:
        m = cls._PORT_RE.search(text)
        if m:
            params["ports"] = m.group(1)

        m = cls._TOP_PORTS_RE.search(text)
        if m:
            val = m.group(1) or m.group(2) or m.group(3)
            if val:
                params["top_ports"] = int(val)
                params.pop("ports", None)

        m = cls._TIMING_RE.search(text)
        if m:
            val = m.group(1) or m.group(2) or m.group(3)
            if val:
                params["timing"] = int(val)

        if cls._NO_DNS_RE.search(text):
            params["no_dns"] = True
        if cls._SVC_DETECT_RE.search(text):
            params["service_detection"] = True
        if cls._AGGRESSIVE_RE.search(text):
            params["aggressive"] = True
        if cls._TRACEROUTE_RE.search(text):
            params["traceroute"] = True
        if cls._NO_PING_RE.search(text):
            params["no_ping"] = True
        if cls._VERBOSE_RE.search(text):
            params["verbose"] = True
        if cls._OSSCAN_RE.search(text):
            params["osscan_guess"] = True

        m = cls._SCRIPTS_PREFIX_RE.search(text)
        if m:
            params["scripts"] = m.group(1)
        else:
            m = cls._SCRIPTS_RE.search(text)
            if m:
                params["scripts"] = m.group(1)
        if "scripts" not in params and re.search(r"\bvuln\b", text, re.IGNORECASE):
            params["scripts"] = "vuln"

        if cls._SYN_RE.search(text):
            params["scan_type"] = "sS"
        elif cls._UDP_RE.search(text):
            params["scan_type"] = "sU"

    @classmethod
    def _extract_web_dir_params(cls, text: str, params: Dict[str, Any]) -> None:
        m = cls._EXT_RE.search(text)
        if m:
            params["extensions"] = m.group(1).strip()
        m = cls._WORDLIST_RE.search(text)
        if m:
            params["wordlist"] = m.group(1).strip()
        m = cls._THREADS_RE.search(text)
        if m:
            params["threads"] = int(m.group(1))
        if re.search(
            r"(tls\s*(do[g\u011f]rulama|validation)\s*(yapma|kapat|yok)|no.?tls|-k\b)",
            text,
            re.IGNORECASE,
        ):
            params["no_tls_validation"] = True
        if re.search(r"(redirect|y[o\xf6]nlendir|takip\s+et|-r\b)", text, re.IGNORECASE):
            params["follow_redirect"] = True

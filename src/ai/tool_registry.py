# SENTINEL AI - Tool Registry
# Action Planner v2: Intent -> Tool mapping
# 
# Bu dosya STATIK tool metadata'si icerir.
# LLM bu bilgileri URETMEZ, sadece intent belirler.
# Tool secimi, requires_root ve risk_level buradan gelir.

from typing import Dict, Optional, List, Any, Set, Tuple
from src.ai.schemas import IntentType, ToolDef, ToolSpec, RiskLevel


# =============================================================================
# TOOL REGISTRY - 15 Core Security Tools
# =============================================================================

TOOL_REGISTRY: Dict[IntentType, ToolDef] = {
    
    # =========================================================================
    # SCANNING TOOLS
    # =========================================================================
    
    IntentType.HOST_DISCOVERY: ToolDef(
        tool="nmap",
        base_args=["-sn"],
        requires_root=False,
        risk_level=RiskLevel.LOW,
        description="Agdaki aktif hostlari ping taramasiyla kesfet",
        arg_templates={}
    ),
    
    IntentType.PORT_SCAN: ToolDef(
        tool="nmap",
        base_args=["-sT"],
        requires_root=False,  # TCP Connect scan root gerektirmez
        risk_level=RiskLevel.MEDIUM,
        description="TCP port taramasi (varsayilan: TCP Connect)",
        arg_templates={
            "ports": "-p {value}",  # -p 1-1000 veya -p 22,80,443
        }
    ),
    
    IntentType.SERVICE_DETECTION: ToolDef(
        tool="nmap",
        base_args=["-sV", "--version-intensity", "5"],
        requires_root=False,
        risk_level=RiskLevel.MEDIUM,
        description="Servis versiyon tespiti",
        arg_templates={
            "ports": "-p {value}",
        }
    ),
    
    IntentType.OS_DETECTION: ToolDef(
        tool="nmap",
        base_args=["-O"],
        requires_root=True,  # OS detection root gerektirir
        risk_level=RiskLevel.MEDIUM,
        description="Isletim sistemi ve servis tespiti",
        arg_templates={
            "ports": "-p {value}",
            "timing": "-T{value}",
            "aggressive": "--osscan-guess",
        }
    ),
    
    IntentType.VULN_SCAN: ToolDef(
        tool="nmap",
        base_args=["--script", "vuln"],
        requires_root=True,
        risk_level=RiskLevel.HIGH,
        description="NSE script ile zafiyet taramasi",
        arg_templates={
            "ports": "-p {value}",
        }
    ),

    IntentType.SSL_SCAN: ToolDef(
        tool="nmap",
        base_args=["--script", "ssl-enum-ciphers"],
        requires_root=False,
        risk_level=RiskLevel.MEDIUM,
        description="SSL/TLS sertifika ve cipher analizi",
        arg_templates={
            "port": "-p {value}",
        }
    ),
    
    # =========================================================================
    # WEB ENUMERATION TOOLS
    # =========================================================================
    
    IntentType.WEB_DIR_ENUM: ToolDef(
        tool="gobuster",
        base_args=["dir", "-w", "/usr/share/wordlists/dirb/common.txt"],
        requires_root=False,
        risk_level=RiskLevel.MEDIUM,
        description="Web dizin ve dosya kesfet",
        arg_templates={
            "wordlist": "-w {value}",
            "extensions": "-x {value}",  # -x php,html,txt
        }
    ),
    
    IntentType.WEB_VULN_SCAN: ToolDef(
        tool="nikto",
        base_args=[],
        requires_root=False,
        risk_level=RiskLevel.MEDIUM,
        description="Web sunucu zafiyet taramasi",
        arg_templates={
            "port": "-p {value}",
        }
    ),
    
    # =========================================================================
    # RECON TOOLS
    # =========================================================================
    
    IntentType.DNS_LOOKUP: ToolDef(
        tool="nslookup",
        base_args=[],
        requires_root=False,
        risk_level=RiskLevel.LOW,
        description="DNS sorgusu",
        arg_templates={
            "record_type": "-type={value}",
        }
    ),

    IntentType.SUBDOMAIN_ENUM: ToolDef(
        tool="nslookup",
        base_args=[],
        requires_root=False,
        risk_level=RiskLevel.MEDIUM,
        description="Subdomain kesfi (basit DNS sorgusu)",
        arg_templates={}
    ),
    
    IntentType.WHOIS_LOOKUP: ToolDef(
        tool="whois",
        base_args=[],
        requires_root=False,
        risk_level=RiskLevel.LOW,
        description="Domain whois bilgisi",
        arg_templates={}
    ),
    
    # =========================================================================
    # BRUTE FORCE TOOLS
    # =========================================================================
    
    IntentType.BRUTE_FORCE_SSH: ToolDef(
        tool="hydra",
        base_args=[],
        requires_root=False,
        risk_level=RiskLevel.HIGH,
        description="SSH brute force saldirisi",
        arg_templates={
            "username": "-l {value}",
            "wordlist": "-P {value}",
            "threads": "-t {value}",
        }
    ),
    
    IntentType.BRUTE_FORCE_HTTP: ToolDef(
        tool="hydra",
        base_args=[],
        requires_root=False,
        risk_level=RiskLevel.HIGH,
        description="HTTP form brute force",
        arg_templates={
            "username": "-l {value}",
            "wordlist": "-P {value}",
            "threads": "-t {value}",
        }
    ),
    
    # =========================================================================
    # EXPLOIT TOOLS
    # =========================================================================
    
    IntentType.SQL_INJECTION: ToolDef(
        tool="sqlmap",
        base_args=["--batch"],
        requires_root=False,
        risk_level=RiskLevel.HIGH,
        description="SQL injection testi",
        arg_templates={
            "url": "-u {value}",
            "level": "--level {value}",
            "risk": "--risk {value}",
        }
    ),
    
    # =========================================================================
    # INFO / UNKNOWN
    # =========================================================================
    
    IntentType.INFO_QUERY: ToolDef(
        tool="",  # Komut yok, sadece bilgi
        base_args=[],
        requires_root=False,
        risk_level=RiskLevel.LOW,
        description="Bilgi sorusu, komut uretilmez",
        arg_templates={}
    ),
    
    IntentType.UNKNOWN: ToolDef(
        tool="",  # Netlestime gerekli
        base_args=[],
        requires_root=False,
        risk_level=RiskLevel.LOW,
        description="Anlasılamadi, netlestime gerekli",
        arg_templates={}
    ),
}


# =============================================================================
# EXECUTION REGISTRY - Intent -> Integrated Tool Mapping
# =============================================================================

_EXECUTION_REGISTRY: Dict[IntentType, Dict[str, Any]] = {
    IntentType.HOST_DISCOVERY: {
        "tool_id": "nmap_ping_sweep",
        "target_arg": "target",
        "param_map": {
            "timing": "timing",
            "exclude": "exclude",
            "no_dns": "no_dns",
            "verbose": "verbose",
        }
    },
    IntentType.PORT_SCAN: {
        "tool_id": "nmap_port_scan",
        "target_arg": "target",
        "param_map": {
            "ports": "ports",
            "scan_type": "scan_type",
            "timing": "timing",
            "top_ports": "top_ports",
            "no_dns": "no_dns",
            "verbose": "verbose",
            "service_detection": "service_detection",
            "no_ping": "no_ping",
            "osscan_guess": "osscan_guess",
            "aggressive": "aggressive",
            "traceroute": "traceroute",
        }
    },
    IntentType.SERVICE_DETECTION: {
        "tool_id": "nmap_service_detection",
        "target_arg": "target",
        "param_map": {
            "ports": "ports",
            "intensity": "intensity",
            "version_intensity": "version_intensity",
            "timing": "timing",
            "version_mode": "version_mode",
            "verbose": "verbose",
            "no_ping": "no_ping",
        }
    },
    IntentType.OS_DETECTION: {
        "tool_id": "nmap_os_detection",
        "target_arg": "target",
        "param_map": {
            "ports": "ports",
            "timing": "timing",
            "osscan_guess": "osscan_guess",
            "service_detection": "service_detection",
            "verbose": "verbose",
            "top_ports": "top_ports",
            "no_ping": "no_ping",
            "aggressive": "aggressive",
        }
    },
    IntentType.VULN_SCAN: {
        "tool_id": "nmap_vuln_scan",
        "target_arg": "target",
        "param_map": {
            "ports": "ports",
            "scripts": "scripts",
            "script_args": "script_args",
            "timing": "timing",
            "verbose": "verbose",
            "no_ping": "no_ping",
        }
    },
    IntentType.DNS_LOOKUP: {
        "tool_id": "dns_lookup",
        "target_arg": "domain",
        "param_map": {
            "record_type": "record_type",
            "dns_server": "dns_server",
        }
    },
    IntentType.SSL_SCAN: {
        "tool_id": "ssl_scan",
        "target_arg": "target",
        "param_map": {
            "port": "port",
            "servername": "servername",
            "tls_version": "tls_version",
            "starttls": "starttls",
        }
    },
    IntentType.WEB_DIR_ENUM: {
        "tool_id": "gobuster_dir",
        "target_arg": "url",
        "param_map": {
            "wordlist": "wordlist",
            "extensions": "extensions",
            "threads": "threads",
            "status_codes": "status_codes",
            "no_tls_validation": "no_tls_validation",
            "follow_redirect": "follow_redirect",
        }
    },
    IntentType.SUBDOMAIN_ENUM: {
        "tool_id": "subdomain_enum",
        "target_arg": "domain",
        "param_map": {
            "wordlist": "wordlist"
        }
    },
    IntentType.WEB_VULN_SCAN: {
        "tool_id": "web_app_scan",
        "target_arg": "url",
        "param_map": {}
    },
    IntentType.WHOIS_LOOKUP: {
        "tool_id": "whois_lookup",
        "target_arg": "domain",
        "param_map": {}
    },
    IntentType.BRUTE_FORCE_SSH: {
        "tool_id": "hydra_ssh",
        "target_arg": "target",
        "param_map": {
            "username": "username",
            "wordlist": "wordlist",
            "port": "port",
            "threads": "threads",
            "verbose": "verbose",
        }
    },
    IntentType.BRUTE_FORCE_HTTP: {
        "tool_id": "hydra_http",
        "target_arg": "target",
        "param_map": {
            "username": "username",
            "wordlist": "wordlist",
            "form_path": "form_path",
            "form_params": "form_params",
            "fail_string": "fail_string",
            "port": "port",
            "threads": "threads",
            "method": "method",
        }
    },
    IntentType.SQL_INJECTION: {
        "tool_id": "sqlmap_scan",
        "target_arg": "url",
        "param_map": {
            "level": "level",
            "risk": "risk",
            "batch": "batch",
            "forms": "forms",
            "dbs": "dbs",
            "threads": "threads",
        }
    },
}


_PHASE2_CLARIFICATION_POLICIES: Dict[IntentType, Dict[str, Any]] = {
    IntentType.BRUTE_FORCE_SSH: {
        "message": (
            "SSH brute force icin hedefe ek olarak username veya userlist ve "
            "password veya passlist belirtmelisiniz."
        ),
        "requirements": [
            ("username", "userlist"),
            ("password", "passlist"),
        ],
    },
    IntentType.BRUTE_FORCE_HTTP: {
        "message": (
            "HTTP brute force icin hedef URL, username veya userlist, password veya passlist, "
            "form_path, form_params ve fail_string belirtmelisiniz."
        ),
        "requirements": [
            ("username", "userlist"),
            ("password", "passlist"),
            ("form_path",),
            ("form_params",),
            ("fail_string",),
        ],
    },
    IntentType.SQL_INJECTION: {
        "message": (
            "SQL injection testi icin tam hedef URL belirtmelisiniz. "
            "Ornek: http://example.com/login.php?id=1"
        ),
        "requires_url_target": True,
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_tool_for_intent(intent_type: IntentType) -> Optional[ToolDef]:
    """
    Intent'e gore tool metadata'sini getir.
    
    Args:
        intent_type: Kullanici niyeti
    
    Returns:
        ToolDef veya None (intent desteklenmiyorsa)
    """
    return TOOL_REGISTRY.get(intent_type)


def get_supported_intents() -> List[IntentType]:
    """
    Desteklenen tum intent'leri listele.
    
    Returns:
        IntentType listesi
    """
    return list(TOOL_REGISTRY.keys())


def get_intents_for_tool(tool_name: str) -> List[IntentType]:
    """
    Belirli bir tool'u kullanan intent'leri bul.
    
    Args:
        tool_name: Arac adi (ornek: "nmap")
    
    Returns:
        Bu araci kullanan IntentType listesi
    """
    return [
        intent for intent, tool_def in TOOL_REGISTRY.items()
        if tool_def.tool == tool_name
    ]


def build_tool_spec(
    intent_type: IntentType,
    target: Optional[str] = None,
    params: Optional[Dict[str, str]] = None
) -> Optional[ToolSpec]:
    """
    Intent + parametrelerden ToolSpec olustur.
    
    Bu fonksiyon Registry'den tool bilgisini alir ve
    kullanici parametreleriyle birlestirir.
    
    Args:
        intent_type: Kullanici niyeti
        target: Hedef IP/domain (REQUIRED for most tools)
        params: Ek parametreler (ports, wordlist, vb.)
    
    Returns:
        ToolSpec veya None (tool yoksa)
    
    Raises:
        ValueError: Target gerekli ama saglanmamissa
    
    Example:
        >>> build_tool_spec(IntentType.PORT_SCAN, "192.168.1.1", {"ports": "1-1000"})
        ToolSpec(tool="nmap", arguments=["-sS", "-sV", "-p", "1-1000"], target="192.168.1.1", ...)
    """
    # Target validation for most tools
    if not target and intent_type not in [IntentType.INFO_QUERY, IntentType.UNKNOWN]:
        raise ValueError("Hedef belirtilmedi; lütfen IP veya domain ekleyin")
    
    tool_def = get_tool_for_intent(intent_type)
    
    if tool_def is None or not tool_def.tool:
        return None
    
    # Base argumanlarla baslat
    arguments = list(tool_def.base_args)
    effective_params = dict(params or {})

    if intent_type == IntentType.SQL_INJECTION and "level" not in effective_params:
        effective_params["level"] = 3
    
    # Parametreleri ekle
    if effective_params:
        for param_key, param_value in effective_params.items():
            if param_key in tool_def.arg_templates:
                if param_value is None or param_value is False:
                    continue
                template = tool_def.arg_templates[param_key]
                if "{value}" in template:
                    formatted = template.replace("{value}", str(param_value))
                else:
                    if not bool(param_value):
                        continue
                    formatted = template
                arguments.extend(formatted.split())
    
    return ToolSpec(
        tool=tool_def.tool,
        arguments=arguments,
        target=target,
        requires_root=tool_def.requires_root,
        risk_level=tool_def.risk_level
    )


def get_execution_tool_id(intent_type: IntentType) -> Optional[str]:
    """
    Intent'e gore IntegratedTool tool_id'sini getir.
    """
    mapping = _EXECUTION_REGISTRY.get(intent_type)
    if not mapping:
        return None
    return mapping.get("tool_id")


def get_execution_intents() -> Set[IntentType]:
    """Execution mapping'i olan intent'leri getir."""
    return set(_EXECUTION_REGISTRY.keys())


def get_required_execution_tool_ids() -> Set[str]:
    """Execution mapping için zorunlu tool_id listesini getir."""
    return {
        mapping["tool_id"]
        for mapping in _EXECUTION_REGISTRY.values()
        if mapping.get("tool_id")
    }


def validate_execution_registry(registered_tool_ids: Optional[Set[str]] = None) -> Tuple[bool, List[str]]:
    """
    Execution registry tutarlılığını doğrula.

    Kontroller:
    1) Execution intent'lerin ToolDef'i var mı?
    2) Execution intent'lerde tool boş mu?
    3) (Opsiyonel) Execution tool_id'ler gerçekten register edilmiş mi?
    """
    errors: List[str] = []

    for intent_type in _EXECUTION_REGISTRY.keys():
        tool_def = TOOL_REGISTRY.get(intent_type)
        if tool_def is None:
            errors.append(f"Missing ToolDef for execution intent: {intent_type.value}")
            continue
        if not tool_def.tool:
            errors.append(f"Execution intent has empty tool: {intent_type.value}")

    if registered_tool_ids is not None:
        required_ids = get_required_execution_tool_ids()
        missing_ids = sorted(required_ids - set(registered_tool_ids))
        for tool_id in missing_ids:
            errors.append(f"Execution tool_id not registered in coordinator: {tool_id}")

    return (len(errors) == 0, errors)


# =============================================================================
# PARAM TYPE COERCION — LLM ciktisindaki tip duzeltmeleri
# =============================================================================

# LLM JSON'da genellikle "4" (string) veya "true" (string) doner.
# build_command int/bool beklediginden, burada tip donusumu yapilir.

_INT_PARAMS: frozenset = frozenset({
    "timing", "top_ports", "port", "threads", "intensity",
    "version_intensity", "level", "risk",
})

_BOOL_PARAMS: frozenset = frozenset({
    "no_dns", "verbose", "no_ping", "service_detection",
    "osscan_guess", "aggressive", "no_tls_validation",
    "follow_redirect", "traceroute", "batch", "forms", "dbs",
})


def _coerce_param(key: str, value: Any) -> Any:
    """LLM ciktisindaki tip farkliliklarini duzelt."""
    if key in _INT_PARAMS:
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if key in _BOOL_PARAMS:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "evet")
        return bool(value)
    # LLM bazen ports icin "*", "all", "tum" gibi wildcard doner
    if key == "ports" and isinstance(value, str):
        if value.strip() in ("*", "all", "tüm", "tum", "hepsi", "-"):
            return None  # build_command varsayilan port araligini kullansin
    return value


def build_execution_kwargs(
    intent_type: IntentType,
    target: Optional[str],
    params: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Intent -> Tool kwargs mapping.

    LLM ciktisindaki tip farkliliklarini duzeltir (str -> int/bool)
    ve build_command icin dogru tipleri uretir.

    Returns:
        kwargs dict or None if intent is not executable
    """
    mapping = _EXECUTION_REGISTRY.get(intent_type)
    if not mapping:
        return None

    kwargs: Dict[str, Any] = {}
    target_arg = mapping.get("target_arg")
    if target_arg:
        if not target:
            return None
        # URL gerektiren tool'lar icin http:// prefix otomatik ekle
        if target_arg == "url" and not (
            target.startswith("http://") or target.startswith("https://")
        ):
            target = f"http://{target}"
        kwargs[target_arg] = target

    param_map = mapping.get("param_map", {})
    if params:
        for param_key, tool_arg in param_map.items():
            if param_key in params and params[param_key] is not None:
                coerced = _coerce_param(param_key, params[param_key])
                if coerced is not None:
                    kwargs[tool_arg] = coerced

    if intent_type == IntentType.SQL_INJECTION and "level" not in kwargs:
        kwargs["level"] = 3

    return kwargs


def get_missing_required_params(
    intent_type: IntentType,
    params: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Intent icin zorunlu parametrelerden eksik olanlari don.

    Sadece execution registry'de required_params tanimli intent'ler icin calisir.
    """
    mapping = _EXECUTION_REGISTRY.get(intent_type)
    if not mapping:
        return []

    required = mapping.get("required_params", []) or []
    provided = params or {}

    missing: List[str] = []
    for key in required:
        value = provided.get(key)
        if value is None:
            missing.append(key)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(key)

    return missing

def get_clarification_message(
    intent_type: IntentType,
    target: Optional[str],
    params: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Faz-2 veya eksik parametre gerektiren intent'ler icin clarification mesaji dondur.

    Returns:
        clarification message veya None
    """
    policy = _PHASE2_CLARIFICATION_POLICIES.get(intent_type)
    if not policy:
        return None

    normalized_params = params or {}

    if policy.get("requires_url_target"):
        target_value = str(target or normalized_params.get("url") or "").strip().lower()
        if not (target_value.startswith("http://") or target_value.startswith("https://")):
            return str(policy["message"])

    for requirement_group in policy.get("requirements", []):
        if not any(normalized_params.get(key) for key in requirement_group):
            return str(policy["message"])

    return None


def print_registry_summary():
    """Debug: Registry ozetini yazdir"""
    print("=" * 60)
    print("SENTINEL AI - Tool Registry Summary")
    print("=" * 60)
    
    for intent, tool_def in TOOL_REGISTRY.items():
        if tool_def.tool:
            print(f"\n{intent.value}:")
            print(f"  Tool: {tool_def.tool}")
            print(f"  Args: {tool_def.base_args}")
            print(f"  Root: {tool_def.requires_root}")
            print(f"  Risk: {tool_def.risk_level.value}")


# =============================================================================
# DEBUG
# =============================================================================

if __name__ == "__main__":
    print_registry_summary()
    
    # Test: ToolSpec olustur
    print("\n" + "=" * 60)
    print("Test: build_tool_spec()")
    print("=" * 60)
    
    spec = build_tool_spec(
        IntentType.PORT_SCAN,
        target="192.168.1.1",
        params={"ports": "22,80,443"}
    )
    
    if spec:
        print(f"\nIntent: PORT_SCAN")
        print(f"Tool: {spec.tool}")
        print(f"Args: {spec.arguments}")
        print(f"Target: {spec.target}")
        print(f"Root: {spec.requires_root}")
        print(f"Risk: {spec.risk_level.value}")

# SENTINEL AI - Tool Registry
# Action Planner v2: Intent -> Tool mapping
# 
# Bu dosya STATIK tool metadata'si icerir.
# LLM bu bilgileri URETMEZ, sadece intent belirler.
# Tool secimi, requires_root ve risk_level buradan gelir.

from typing import Dict, Optional, List
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
        base_args=["-sS", "-sV"],
        requires_root=True,  # SYN scan root gerektirir
        risk_level=RiskLevel.MEDIUM,
        description="TCP SYN port taramasi ve servis tespiti",
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
        base_args=["-O", "-sV"],
        requires_root=True,  # OS detection root gerektirir
        risk_level=RiskLevel.MEDIUM,
        description="Isletim sistemi ve servis tespiti",
        arg_templates={}
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
        base_args=["-t", "4"],  # 4 thread
        requires_root=False,
        risk_level=RiskLevel.HIGH,
        description="SSH brute force saldirisi",
        arg_templates={
            "username": "-l {value}",
            "userlist": "-L {value}",
            "password": "-p {value}",
            "passlist": "-P {value}",
        }
    ),
    
    IntentType.BRUTE_FORCE_HTTP: ToolDef(
        tool="hydra",
        base_args=["-t", "4"],
        requires_root=False,
        risk_level=RiskLevel.HIGH,
        description="HTTP form brute force",
        arg_templates={
            "username": "-l {value}",
            "passlist": "-P {value}",
        }
    ),
    
    # =========================================================================
    # EXPLOIT TOOLS
    # =========================================================================
    
    IntentType.SQL_INJECTION: ToolDef(
        tool="sqlmap",
        base_args=["--batch", "--level", "3"],  # Non-interactive, level 3
        requires_root=False,
        risk_level=RiskLevel.HIGH,
        description="SQL injection testi",
        arg_templates={
            "url": "-u {value}",
            "data": "--data {value}",
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
        target: Hedef IP/domain
        params: Ek parametreler (ports, wordlist, vb.)
    
    Returns:
        ToolSpec veya None (tool yoksa)
    
    Example:
        >>> build_tool_spec(IntentType.PORT_SCAN, "192.168.1.1", {"ports": "1-1000"})
        ToolSpec(tool="nmap", arguments=["-sS", "-sV", "-p", "1-1000"], target="192.168.1.1", ...)
    """
    tool_def = get_tool_for_intent(intent_type)
    
    if tool_def is None or not tool_def.tool:
        return None
    
    # Base argumanlarla baslat
    arguments = list(tool_def.base_args)
    
    # Parametreleri ekle
    if params:
        for param_key, param_value in params.items():
            if param_key in tool_def.arg_templates:
                template = tool_def.arg_templates[param_key]
                # Template'i parse et: "-p {value}" -> ["-p", value]
                formatted = template.replace("{value}", str(param_value))
                arguments.extend(formatted.split())
    
    return ToolSpec(
        tool=tool_def.tool,
        arguments=arguments,
        target=target,
        requires_root=tool_def.requires_root,
        risk_level=tool_def.risk_level
    )


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

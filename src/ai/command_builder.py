# SENTINEL AI - Command Builder
# Action Planner v2: ToolSpec + Params -> Final Command
#
# Bu modul DETERMINISTIK calisir, LLM kullanmaz.
# ToolSpec ve parametreleri alir, calistirilabilir komut uretir.

import re
from typing import Optional, List, Dict, Tuple
from src.ai.schemas import ToolSpec, FinalCommand, RiskLevel


# =============================================================================
# VALIDATION PATTERNS
# =============================================================================

# IP address pattern (IPv4)
IP_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    r"(?:/(?:3[0-2]|[12]?[0-9]))?$"  # CIDR notation optional
)

# Domain pattern
DOMAIN_PATTERN = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}$"
)

# URL pattern
URL_PATTERN = re.compile(
    r"^https?://[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*"
    r"(?::\d{1,5})?(?:/[^\s]*)?$"
)

# Port range pattern
PORT_PATTERN = re.compile(r"^(?:\d{1,5}(?:-\d{1,5})?(?:,\d{1,5}(?:-\d{1,5})?)*)$")

# Dangerous characters (shell injection prevention)
DANGEROUS_CHARS = frozenset([";", "|", "&", "$", "`", "(", ")", "{", "}", "<", ">", "\n", "\r", "\x00"])


class CommandBuilder:
    """
    ToolSpec + Parameters -> FinalCommand donusturucusu.
    
    Gorevleri:
    1. Target validasyonu (IP, domain, URL)
    2. Parametre validasyonu (port range, wordlist)
    3. Shell injection korumasi
    4. Final komut olusturma
    """
    
    def __init__(self):
        pass
    
    def build(
        self,
        tool_spec: ToolSpec,
        explanation: str = ""
    ) -> Tuple[Optional[FinalCommand], Optional[str]]:
        """
        ToolSpec'ten FinalCommand olustur.
        
        Args:
            tool_spec: Registry'den gelen tool bilgisi
            explanation: Kullaniciya gosterilecek aciklama
        
        Returns:
            (FinalCommand, error_message)
            Basarili: (FinalCommand, None)
            Basarisiz: (None, hata mesaji)
        """
        # Tool bos mu?
        if not tool_spec.tool:
            return (None, "Tool adi bos")
        
        # Target validasyonu
        if tool_spec.target:
            is_valid, error = self._validate_target(tool_spec.target)
            if not is_valid:
                return (None, f"Gecersiz hedef: {error}")
        
        # Arguman validasyonu
        for arg in tool_spec.arguments:
            is_valid, error = self._validate_argument(arg)
            if not is_valid:
                return (None, f"Gecersiz arguman: {error}")
        
        # Komutu olustur
        arguments = list(tool_spec.arguments)
        
        # Target'i ekle (varsa)
        if tool_spec.target:
            # Web tools icin -u flag'i
            if tool_spec.tool in ["gobuster", "nikto"]:
                if "-h" not in arguments and "-u" not in arguments:
                    if tool_spec.tool == "gobuster":
                        arguments.extend(["-u", tool_spec.target])
                    else:  # nikto
                        arguments.extend(["-h", tool_spec.target])
            # Hydra icin service://target format
            elif tool_spec.tool == "hydra":
                # Hydra target'i en sona ekler, service bilgisi ile
                pass  # Simdilik basit birak
            # Diger toollar icin target en sona
            else:
                arguments.append(tool_spec.target)
        
        return (
            FinalCommand(
                executable=tool_spec.tool,
                arguments=arguments,
                requires_root=tool_spec.requires_root,
                risk_level=tool_spec.risk_level,
                explanation=explanation
            ),
            None
        )
    
    def _validate_target(self, target: str) -> Tuple[bool, Optional[str]]:
        """
        Hedef validasyonu.
        
        Kabul edilen formatlar:
        - IPv4 address (with optional CIDR)
        - Domain name
        - URL (http/https)
        """
        # Tehlikeli karakter kontrolu
        for char in DANGEROUS_CHARS:
            if char in target:
                return (False, f"Tehlikeli karakter: {repr(char)}")
        
        # Format kontrolu
        if IP_PATTERN.match(target):
            return (True, None)
        
        if DOMAIN_PATTERN.match(target):
            return (True, None)
        
        if URL_PATTERN.match(target):
            return (True, None)
        
        # Belki IP range (192.168.1.0/24)
        if "/" in target:
            parts = target.split("/")
            if len(parts) == 2:
                ip_part = parts[0]
                if IP_PATTERN.match(ip_part + "/0"):  # Trick: add /0 for pattern match
                    try:
                        cidr = int(parts[1])
                        if 0 <= cidr <= 32:
                            return (True, None)
                    except ValueError:
                        pass
        
        return (False, "Gecersiz format (IP, domain veya URL olmali)")
    
    def _validate_argument(self, arg: str) -> Tuple[bool, Optional[str]]:
        """
        Arguman validasyonu (shell injection korumasi).
        """
        # Bos kontrolu
        if not arg or not arg.strip():
            return (False, "Bos arguman")
        
        # Cok uzun arguman
        if len(arg) > 512:
            return (False, "Arguman cok uzun (max 512 karakter)")
        
        # Tehlikeli karakter kontrolu
        for char in DANGEROUS_CHARS:
            if char in arg:
                return (False, f"Tehlikeli karakter: {repr(char)}")
        
        return (True, None)
    
    def validate_port_range(self, ports: str) -> Tuple[bool, Optional[str]]:
        """
        Port range validasyonu.
        
        Kabul edilen formatlar:
        - Tek port: "80"
        - Port listesi: "22,80,443"
        - Port araligi: "1-1000"
        - Karisik: "22,80,443-500,8080"
        - Ozel: "-" (tum portlar)
        """
        if ports == "-":
            return (True, None)
        
        if not PORT_PATTERN.match(ports):
            return (False, "Gecersiz port formati")
        
        # Port numaralarini kontrol et
        for part in ports.split(","):
            if "-" in part:
                start, end = part.split("-")
                if int(start) > int(end):
                    return (False, "Baslangic > bitis")
                if int(end) > 65535:
                    return (False, "Port > 65535")
            else:
                if int(part) > 65535:
                    return (False, "Port > 65535")
        
        return (True, None)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_builder: Optional[CommandBuilder] = None


def get_command_builder() -> CommandBuilder:
    """Singleton CommandBuilder instance doner"""
    global _builder
    if _builder is None:
        _builder = CommandBuilder()
    return _builder


def quick_build(tool_spec: ToolSpec, explanation: str = "") -> Tuple[Optional[FinalCommand], Optional[str]]:
    """Hizli komut olusturma"""
    builder = get_command_builder()
    return builder.build(tool_spec, explanation)


# =============================================================================
# DEBUG
# =============================================================================

if __name__ == "__main__":
    from src.ai.schemas import IntentType
    from src.ai.tool_registry import build_tool_spec
    
    print("=" * 60)
    print("SENTINEL AI - Command Builder Test")
    print("=" * 60)
    
    builder = CommandBuilder()
    
    # Test 1: Port scan
    print("\n[Test 1] Port Scan")
    print("-" * 40)
    
    spec = build_tool_spec(
        IntentType.PORT_SCAN,
        target="192.168.1.1",
        params={"ports": "22,80,443"}
    )
    
    if spec:
        cmd, error = builder.build(spec, "TCP SYN port taramasi")
        if cmd:
            print(f"Command: {cmd.to_display_string()}")
            print(f"Root: {cmd.requires_root}")
            print(f"Risk: {cmd.risk_level.value}")
        else:
            print(f"Error: {error}")
    
    # Test 2: Web dir enum
    print("\n[Test 2] Web Directory Enumeration")
    print("-" * 40)
    
    spec = build_tool_spec(
        IntentType.WEB_DIR_ENUM,
        target="http://example.com"
    )
    
    if spec:
        cmd, error = builder.build(spec, "Web dizin taramasi")
        if cmd:
            print(f"Command: {cmd.to_display_string()}")
        else:
            print(f"Error: {error}")
    
    # Test 3: DNS lookup
    print("\n[Test 3] DNS Lookup")
    print("-" * 40)
    
    spec = build_tool_spec(
        IntentType.DNS_LOOKUP,
        target="google.com"
    )
    
    if spec:
        cmd, error = builder.build(spec, "DNS sorgusu")
        if cmd:
            print(f"Command: {cmd.to_display_string()}")
        else:
            print(f"Error: {error}")
    
    # Test 4: Invalid target (shell injection attempt)
    print("\n[Test 4] Shell Injection Attempt")
    print("-" * 40)
    
    spec = ToolSpec(
        tool="nmap",
        arguments=["-sn"],
        target="192.168.1.1; rm -rf /",
        requires_root=False,
        risk_level=RiskLevel.LOW
    )
    
    cmd, error = builder.build(spec)
    if error:
        print(f"BLOCKED: {error}")
    else:
        print(f"OOPS: {cmd.to_display_string()}")

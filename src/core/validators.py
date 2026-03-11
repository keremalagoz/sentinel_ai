import ipaddress
import re
from urllib.parse import urlparse


class InputValidator:
    """
    Basic validation helpers for user-provided targets and command arguments.

    The raw-command path remains intentionally strict. Structured argv coming
    from the orchestrator can use the more permissive helpers below.
    """

    DANGEROUS_CHARS = [
        ";", "&", "|", "`", "$", "(", ")", "<", ">", "\\",
        "'", '"', "\n", "\r", "\x00",
    ]

    SAFE_ARG_PATTERN = re.compile(r"^[a-zA-Z0-9\-._/:?=%+,~\[\]@^]+$")
    _HOSTNAME_RE = re.compile(
        r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$"
    )
    _INTERNAL_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]*$")
    _STRUCTURED_ARG_FORBIDDEN_RE = re.compile(r"[`\\\x00\n\r]|\$\(|\$\{")
    _SHELL_WRAPPER_FORBIDDEN_RE = re.compile(r"[\x00\n\r]")

    @staticmethod
    def validate_ip(ip: str) -> bool:
        """Return True when the value is a valid IPv4/IPv6 address or CIDR."""
        try:
            if "/" in ip:
                ipaddress.ip_network(ip, strict=False)
            else:
                ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_hostname(hostname: str) -> bool:
        """Return True when the value is a valid hostname or URL hostname."""
        if len(hostname) > 255:
            return False

        if "://" in hostname:
            try:
                hostname = urlparse(hostname).hostname
                if not hostname:
                    return False
            except Exception:
                return False

        if hostname == "localhost":
            return True

        internal_tlds = (".local", ".lan", ".internal", ".home", ".localdomain")
        if any(hostname.endswith(tld) for tld in internal_tlds):
            return bool(InputValidator._INTERNAL_HOSTNAME_RE.match(hostname))

        if InputValidator.validate_ip(hostname):
            return True

        return bool(InputValidator._HOSTNAME_RE.match(hostname))

    @staticmethod
    def sanitize(text: str) -> str:
        """Remove high-risk shell characters from raw free-form input."""
        if not text:
            return ""

        clean_text = text
        for char in InputValidator.DANGEROUS_CHARS:
            clean_text = clean_text.replace(char, "")
        return clean_text

    @staticmethod
    def is_safe_arg(arg: str) -> bool:
        """Strict validator for raw manual command args after shell splitting."""
        return isinstance(arg, str) and bool(InputValidator.SAFE_ARG_PATTERN.match(arg))

    @staticmethod
    def is_safe_structured_arg(arg: str) -> bool:
        """Permissive validator for structured argv from trusted orchestrator code."""
        if not isinstance(arg, str):
            return False
        return not InputValidator._STRUCTURED_ARG_FORBIDDEN_RE.search(arg)

    @staticmethod
    def is_safe_shell_wrapper_arg(arg: str) -> bool:
        """Validator for internal shell-wrapper payloads."""
        if not isinstance(arg, str):
            return False
        return not InputValidator._SHELL_WRAPPER_FORBIDDEN_RE.search(arg)

    @staticmethod
    def validate_target(target: str) -> bool:
        """General target validation (IP or hostname)."""
        if not target:
            return False

        clean_target = InputValidator.sanitize(target)
        return (
            InputValidator.validate_ip(clean_target)
            or InputValidator.validate_hostname(clean_target)
        )

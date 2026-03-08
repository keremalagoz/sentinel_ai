"""Nmap Port Scan Tool (-sS/-sT/-sU)"""

import re
from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals
from src.core.validators import InputValidator


_PORTS_RE = re.compile(r"^\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*$")
_ALLOWED_SCAN_TYPES = {"sT", "sS", "sU"}


class NmapPortScanTool(BaseTool):
    """
    Nmap port scan tool (-sS/-sT).

    Usage:
        tool = NmapPortScanTool()
        tool.execute(callback=my_callback, target="192.168.1.10", ports="1-1000")
    """

    def __init__(self, timeout: int = 120, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("nmap_port_scan", timeout, signals)

    @staticmethod
    def _estimate_port_count(ports: str) -> int:
        if not ports:
            return 1000

        total = 0
        for part in str(ports).split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    total += max(0, int(end) - int(start) + 1)
                except Exception:
                    total += 1
            else:
                total += 1

        return max(1, min(total, 65535))

    @staticmethod
    def _normalize_target(target: str) -> str:
        raw_value = str(target or "").strip()
        sanitized = InputValidator.sanitize(raw_value)
        if sanitized != raw_value:
            raise ValueError("Invalid scan target")
        if not InputValidator.validate_target(sanitized):
            raise ValueError("Invalid scan target")
        return sanitized

    @staticmethod
    def _normalize_ports(ports: str) -> str:
        value = str(ports or "1-1000").replace(" ", "")
        if not _PORTS_RE.fullmatch(value):
            raise ValueError("Invalid port range")

        for part in value.split(","):
            if "-" in part:
                start_str, end_str = part.split("-", 1)
                start = int(start_str)
                end = int(end_str)
                if start < 1 or end > 65535 or start > end:
                    raise ValueError("Invalid port range")
            else:
                port = int(part)
                if port < 1 or port > 65535:
                    raise ValueError("Invalid port range")

        return value

    @staticmethod
    def _normalize_scan_type(scan_type: str) -> str:
        value = str(scan_type or "sT").strip()
        if value not in _ALLOWED_SCAN_TYPES:
            raise ValueError("Invalid scan type")
        return value

    def estimate_timeout(self, **kwargs) -> int:
        ports = self._normalize_ports(kwargs.get("ports", "1-1000"))
        scan_type = self._normalize_scan_type(kwargs.get("scan_type", "sT"))

        port_count = self._estimate_port_count(ports)
        factor = {"sT": 1.0, "sS": 0.8, "sU": 2.2, "sA": 1.1}.get(scan_type, 1.2)
        estimate = int((20 + port_count * 0.12) * factor)

        return max(20, min(900, estimate))

    def build_command(
        self,
        target: str,
        ports: str = "1-1000",
        scan_type: str = "sT",
        timing: Optional[int] = None,
        top_ports: Optional[int] = None,
        no_dns: bool = False,
        verbose: bool = False,
        service_detection: bool = False,
        no_ping: bool = False,
        osscan_guess: bool = False,
        aggressive: bool = False,
        traceroute: bool = False,
        **kwargs
    ) -> List[str]:
        """
        Build nmap port scan command.

        Args:
            target: Target IP
            ports: Port range (1-1000, 80,443, etc.)
            scan_type: Scan type (sT, sS, sU)
            service_detection: Enable version detection (-sV)
            traceroute: Enable traceroute (--traceroute)

        Returns:
            Command: ["nmap", "-sT", "-p", "1-1000", "192.168.1.10"]
        """
        normalized_target = self._normalize_target(target)
        normalized_scan_type = self._normalize_scan_type(scan_type)
        cmd: List[str] = ["nmap", "-A"] if aggressive else ["nmap", f"-{normalized_scan_type}"]

        if service_detection and not aggressive:
            cmd.append("-sV")

        if osscan_guess and "--osscan-guess" not in cmd:
            cmd.append("--osscan-guess")

        if top_ports is not None:
            safe_top_ports = self.validate_range(top_ports, 1, 65535, "top_ports")
            cmd.extend(["--top-ports", str(safe_top_ports)])
        else:
            cmd.extend(["-p", self._normalize_ports(ports)])

        if timing is not None:
            safe_timing = self.validate_range(timing, 0, 5, "timing")
            cmd.append(f"-T{safe_timing}")

        if no_dns:
            cmd.append("-n")
        if no_ping:
            cmd.append("-Pn")
        if verbose:
            cmd.append("-v")
        if traceroute:
            cmd.append("--traceroute")

        cmd.append(normalized_target)
        return cmd

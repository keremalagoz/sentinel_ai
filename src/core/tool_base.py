"""Backward-compatibility shim for tool_base.py

Sprint 3.2 Track D1: Monolithic tool_base.py split into src/core/tools/ package.
All implementations now live under src.core.tools.*  modules.
This file re-exports every public symbol so that existing imports like
    ``from src.core.tool_base import PingTool``
continue to work without changes.
"""

from src.core.tools import (  # noqa: F401
    BaseTool,
    ToolStatus,
    ToolResult,
    ToolExecutionSignals,
    PingTool,
    NmapPingSweepTool,
    NmapPortScanTool,
    NmapServiceDetectionTool,
    NmapVulnScanTool,
    SslScanTool,
    GobusterDirTool,
    SubdomainEnumTool,
    DnsLookupTool,
    WebAppScanTool,
    NmapOsDetectionTool,
    WhoisLookupTool,
    HydraSshTool,
    HydraHttpTool,
    SqlmapScanTool,
)

__all__ = [
    "BaseTool",
    "ToolStatus",
    "ToolResult",
    "ToolExecutionSignals",
    "PingTool",
    "NmapPingSweepTool",
    "NmapPortScanTool",
    "NmapServiceDetectionTool",
    "NmapVulnScanTool",
    "SslScanTool",
    "GobusterDirTool",
    "SubdomainEnumTool",
    "DnsLookupTool",
    "WebAppScanTool",
    "NmapOsDetectionTool",
    "WhoisLookupTool",
    "HydraSshTool",
    "HydraHttpTool",
    "SqlmapScanTool",
    "TOOL_CLASS_MAP",
]

# tool_id -> Tool class mapping (execution registry ile eslesir)
TOOL_CLASS_MAP = {
    "ping": PingTool,
    "nmap_ping_sweep": NmapPingSweepTool,
    "nmap_port_scan": NmapPortScanTool,
    "nmap_service_detection": NmapServiceDetectionTool,
    "nmap_vuln_scan": NmapVulnScanTool,
    "dns_lookup": DnsLookupTool,
    "ssl_scan": SslScanTool,
    "gobuster_dir": GobusterDirTool,
    "subdomain_enum": SubdomainEnumTool,
    "web_app_scan": WebAppScanTool,
    "nmap_os_detection": NmapOsDetectionTool,
    "whois_lookup": WhoisLookupTool,
    "hydra_ssh": HydraSshTool,
    "hydra_http": HydraHttpTool,
    "sqlmap_scan": SqlmapScanTool,
}

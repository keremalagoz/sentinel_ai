"""Advanced parser helper tests (detailed + specific)."""

import pytest

from src.core.sqlite_backend import EntityType
from src.core.parser_framework import (
    extract_cve_info,
    calculate_risk_score,
    parse_service_version,
    analyze_banner,
    NmapVulnScanParser
)


@pytest.mark.parametrize(
    "text,expected_cves,expected_cvss,expected_severity",
    [
        ("CVE-2021-44228 Log4Shell vulnerability CVSS: 10.0", ["CVE-2021-44228"], 10.0, "critical"),
        (
            "Multiple vulnerabilities: CVE-2019-11510, CVE-2019-11539 CVSS: 8.5",
            ["CVE-2019-11510", "CVE-2019-11539"],
            8.5,
            "high",
        ),
        ("SSL vulnerability detected (medium severity)", [], None, "medium"),
        ("Critical security issue found", [], None, "critical"),
    ],
)
def test_cve_extraction(text, expected_cves, expected_cvss, expected_severity):
    result = extract_cve_info(text)
    assert set(result["cve_ids"]) == set(expected_cves)
    assert result["cvss_score"] == expected_cvss
    assert result["severity"] == expected_severity


@pytest.mark.parametrize(
    "confidence,severity,expected_score",
    [
        (1.0, "critical", 10.0),
        (0.9, "high", 7.65),
        (0.8, "medium", 4.8),
        (1.0, "low", 3.0),
        (0.5, "critical", 5.0),
    ],
)
def test_risk_scoring(confidence, severity, expected_score):
    assert calculate_risk_score(confidence, severity) == expected_score


@pytest.mark.parametrize(
    "version_string,expected_product,expected_version,expected_extra",
    [
        ("OpenSSH 8.2p1 Ubuntu 4ubuntu0.5", "OpenSSH", "8.2p1", "Ubuntu 4ubuntu0.5"),
        ("Apache httpd 2.4.41", "Apache", "2.4.41", None),
        ("nginx 1.18.0", "nginx", "1.18.0", None),
        ("MySQL 5.7.33-0ubuntu0.18.04.1", "MySQL", "5.7.33-0ubuntu0.18.04.1", None),
    ],
)
def test_version_parsing(version_string, expected_product, expected_version, expected_extra):
    result = parse_service_version(version_string)
    assert result["product"] == expected_product
    assert result["version"] == expected_version
    assert result["extra_info"] == expected_extra


@pytest.mark.parametrize(
    "banner,expected_service,expected_os_hints",
    [
        ("SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5", "ssh", ["Ubuntu"]),
        ("220 ProFTPD 1.3.5 Server (Debian)", "ftp", ["Debian"]),
        ("HTTP/1.1 200 OK\r\nServer: nginx/1.18.0 (Ubuntu)", "http", ["Ubuntu"]),
    ],
)
def test_banner_analysis(banner, expected_service, expected_os_hints):
    result = analyze_banner(banner)
    assert result["service_type"] == expected_service
    for os_hint in expected_os_hints:
        assert os_hint in result["os_hints"]


def test_integrated_parsing_adds_advanced_vulnerability_fields():
    """Nmap vuln parser, advanced alanları doldurmalı."""
    # Test vulnerability parser with CVE
    vuln_output = """Nmap scan report for 192.168.1.10
PORT     STATE SERVICE
443/tcp  open  https
| ssl-heartbleed: 
|   VULNERABLE:
|   The Heartbleed Bug is a serious vulnerability in the popular OpenSSL cryptographic software library.
|   State: VULNERABLE
|   Risk factor: High
|   CVE-2014-0160
|   CVSS: 7.5
|   OpenSSL versions 1.0.1 through 1.0.1f contain a flaw in its implementation
"""

    parser = NmapVulnScanParser()
    entities = parser.parse(vuln_output)

    vuln_entities = [e for e in entities if e.entity_type == EntityType.VULNERABILITY]
    assert vuln_entities, "Parser did not produce vulnerability entity"

    vuln = vuln_entities[0]
    assert vuln.data.get("cve_ids")
    assert vuln.data.get("cvss_score") is not None
    assert vuln.data.get("risk_score", 0) > 0
    assert vuln.data.get("severity") in {"high", "critical", "medium", "low", "info"}

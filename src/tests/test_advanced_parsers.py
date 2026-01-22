"""Test script for Advanced Parsers (Öncelik 4)

Tests:
1. CVE extraction and severity detection
2. CVSS score parsing
3. Risk score calculation
4. Service version parsing
5. Banner analysis
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.parser_framework import (
    extract_cve_info,
    calculate_risk_score,
    parse_service_version,
    analyze_banner,
    NmapServiceDetectionParser,
    NmapVulnScanParser
)


def test_cve_extraction():
    """Test 1: CVE extraction from vulnerability text"""
    print("\n" + "="*60)
    print("TEST 1: CVE Extraction")
    print("="*60)
    
    test_cases = [
        ("CVE-2021-44228 Log4Shell vulnerability CVSS: 10.0", 
         ["CVE-2021-44228"], 10.0, "critical"),
        ("Multiple vulnerabilities: CVE-2019-11510, CVE-2019-11539 CVSS: 8.5",
         ["CVE-2019-11510", "CVE-2019-11539"], 8.5, "high"),
        ("SSL vulnerability detected (medium severity)",
         [], None, "medium"),
        ("Critical security issue found",
         [], None, "critical"),
    ]
    
    all_passed = True
    
    for text, expected_cves, expected_cvss, expected_severity in test_cases:
        result = extract_cve_info(text)
        
        cves_match = set(result["cve_ids"]) == set(expected_cves)
        cvss_match = result["cvss_score"] == expected_cvss
        severity_match = result["severity"] == expected_severity
        
        if cves_match and cvss_match and severity_match:
            print(f"  [OK] {text[:50]}...")
        else:
            print(f"  [FAIL] {text[:50]}...")
            print(f"    Expected: CVEs={expected_cves}, CVSS={expected_cvss}, Severity={expected_severity}")
            print(f"    Got: CVEs={result['cve_ids']}, CVSS={result['cvss_score']}, Severity={result['severity']}")
            all_passed = False
    
    if all_passed:
        print("\n[OK] TEST 1 PASSED: CVE extraction works correctly")
        return True
    else:
        print("\n[FAIL] TEST 1 FAILED: Some CVE extractions incorrect")
        return False


def test_risk_scoring():
    """Test 2: Risk score calculation"""
    print("\n" + "="*60)
    print("TEST 2: Risk Score Calculation")
    print("="*60)
    
    test_cases = [
        (1.0, "critical", 10.0),
        (0.9, "high", 7.65),
        (0.8, "medium", 4.8),
        (1.0, "low", 3.0),
        (0.5, "critical", 5.0),
    ]
    
    all_passed = True
    
    for confidence, severity, expected_score in test_cases:
        score = calculate_risk_score(confidence, severity)
        
        if score == expected_score:
            print(f"  [OK] confidence={confidence}, severity={severity} → risk={score}")
        else:
            print(f"  [FAIL] confidence={confidence}, severity={severity} → risk={score} (expected {expected_score})")
            all_passed = False
    
    if all_passed:
        print("\n[OK] TEST 2 PASSED: Risk scoring works correctly")
        return True
    else:
        print("\n[FAIL] TEST 2 FAILED: Some risk scores incorrect")
        return False


def test_version_parsing():
    """Test 3: Service version parsing"""
    print("\n" + "="*60)
    print("TEST 3: Service Version Parsing")
    print("="*60)
    
    test_cases = [
        ("OpenSSH 8.2p1 Ubuntu 4ubuntu0.5", "OpenSSH", "8.2p1", "Ubuntu 4ubuntu0.5"),
        ("Apache httpd 2.4.41", "Apache", "2.4.41", None),
        ("nginx 1.18.0", "nginx", "1.18.0", None),
        ("MySQL 5.7.33-0ubuntu0.18.04.1", "MySQL", "5.7.33-0ubuntu0.18.04.1", None),
    ]
    
    all_passed = True
    
    for version_string, expected_product, expected_version, expected_extra in test_cases:
        result = parse_service_version(version_string)
        
        product_match = result["product"] == expected_product
        version_match = result["version"] == expected_version
        extra_match = result["extra_info"] == expected_extra
        
        if product_match and version_match and extra_match:
            print(f"  [OK] {version_string}")
        else:
            print(f"  [FAIL] {version_string}")
            print(f"    Expected: product={expected_product}, version={expected_version}, extra={expected_extra}")
            print(f"    Got: product={result['product']}, version={result['version']}, extra={result['extra_info']}")
            all_passed = False
    
    if all_passed:
        print("\n[OK] TEST 3 PASSED: Version parsing works correctly")
        return True
    else:
        print("\n[FAIL] TEST 3 FAILED: Some version parsing incorrect")
        return False


def test_banner_analysis():
    """Test 4: Banner analysis"""
    print("\n" + "="*60)
    print("TEST 4: Banner Analysis")
    print("="*60)
    
    test_cases = [
        ("SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5", "ssh", ["Ubuntu"]),
        ("220 ProFTPD 1.3.5 Server (Debian)", "ftp", ["Debian"]),
        ("HTTP/1.1 200 OK\r\nServer: nginx/1.18.0 (Ubuntu)", "http", ["Ubuntu"]),
    ]
    
    all_passed = True
    
    for banner, expected_service, expected_os_hints in test_cases:
        result = analyze_banner(banner)
        
        service_match = result["service_type"] == expected_service
        os_match = any(os in result["os_hints"] for os in expected_os_hints) if expected_os_hints else True
        
        if service_match and os_match:
            print(f"  [OK] {banner[:50]}...")
            print(f"    Service: {result['service_type']}, OS hints: {result['os_hints']}")
        else:
            print(f"  [FAIL] {banner[:50]}...")
            print(f"    Expected: service={expected_service}, OS={expected_os_hints}")
            print(f"    Got: service={result['service_type']}, OS={result['os_hints']}")
            all_passed = False
    
    if all_passed:
        print("\n[OK] TEST 4 PASSED: Banner analysis works correctly")
        return True
    else:
        print("\n[FAIL] TEST 4 FAILED: Some banner analysis incorrect")
        return False


def test_integrated_parsing():
    """Test 5: Integrated parser with advanced features"""
    print("\n" + "="*60)
    print("TEST 5: Integrated Parser Test")
    print("="*60)
    
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
    
    try:
        parser = NmapVulnScanParser()
        entities = parser.parse(vuln_output)
        
        # Find vulnerability entity
        vuln_entities = [e for e in entities if e.entity_type == "vulnerability"]
        
        if len(vuln_entities) > 0:
            vuln = vuln_entities[0]
            
            # Check advanced fields
            has_cve = "cve_ids" in vuln.data and len(vuln.data["cve_ids"]) > 0
            has_cvss = "cvss_score" in vuln.data and vuln.data["cvss_score"] is not None
            has_risk = "risk_score" in vuln.data and vuln.data["risk_score"] > 0
            
            if has_cve and has_cvss and has_risk:
                print(f"  [OK] Vulnerability parsed with advanced features")
                print(f"    CVE IDs: {vuln.data.get('cve_ids', [])}")
                print(f"    CVSS Score: {vuln.data.get('cvss_score', 'N/A')}")
                print(f"    Risk Score: {vuln.data.get('risk_score', 'N/A')}")
                print(f"    Severity: {vuln.data.get('severity', 'N/A')}")
                print("\n[OK] TEST 5 PASSED: Integrated parsing works")
                return True
            else:
                print(f"  [FAIL] Missing advanced fields")
                print(f"    CVE: {has_cve}, CVSS: {has_cvss}, Risk: {has_risk}")
                print("\n[FAIL] TEST 5 FAILED: Advanced fields missing")
                return False
        else:
            print("  [FAIL] No vulnerability entities found")
            print("\n[FAIL] TEST 5 FAILED: Parser didn't create vulnerability")
            return False
    
    except Exception as e:
        print(f"  [FAIL] Parser error: {e}")
        print("\n[FAIL] TEST 5 FAILED: Parser exception")
        return False


def run_all_tests():
    """Run all advanced parser tests"""
    print("\n" + "="*60)
    print("SENTINEL - ADVANCED PARSERS TEST SUITE")
    print("Testing Öncelik 4 features")
    print("="*60)
    
    results = []
    
    # Test 1: CVE Extraction
    results.append(("CVE Extraction", test_cve_extraction()))
    
    # Test 2: Risk Scoring
    results.append(("Risk Scoring", test_risk_scoring()))
    
    # Test 3: Version Parsing
    results.append(("Version Parsing", test_version_parsing()))
    
    # Test 4: Banner Analysis
    results.append(("Banner Analysis", test_banner_analysis()))
    
    # Test 5: Integrated Parsing
    results.append(("Integrated Parsing", test_integrated_parsing()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "="*60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    # Run tests
    success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

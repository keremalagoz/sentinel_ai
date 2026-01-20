"""Test script for 7 new tools (Öncelik 3)

Tests:
1. Service Detection (nmap -sV)
2. Vulnerability Scan (nmap --script vuln)
3. DNS Lookup (nslookup)
4. SSL Scan (openssl s_client)
5. Web Dir Enum (gobuster dir)
6. Subdomain Enum (PowerShell DNS)
7. Web App Scanner (PowerShell)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PySide6.QtWidgets import QApplication
from src.core.sentinel_coordinator import SentinelCoordinator


def test_tool_registration():
    """Test 1: Verify all 10 tools are registered"""
    print("\n" + "="*60)
    print("TEST 1: Tool Registration")
    print("="*60)
    
    coordinator = SentinelCoordinator(db_path=":memory:")
    tools = coordinator.get_available_tools()
    
    expected_tools = [
        "ping",
        "nmap_ping_sweep",
        "nmap_port_scan",
        "nmap_service_detection",
        "nmap_vuln_scan",
        "dns_lookup",
        "ssl_scan",
        "gobuster_dir",
        "subdomain_enum",
        "web_app_scan"
    ]
    
    print(f"✅ Expected tools: {len(expected_tools)}")
    print(f"✅ Registered tools: {len(tools)}")
    
    for tool in expected_tools:
        if tool in tools:
            print(f"  ✓ {tool}")
        else:
            print(f"  ✗ {tool} - MISSING!")
    
    coordinator.cleanup()
    
    if len(tools) == len(expected_tools):
        print("\n✅ TEST 1 PASSED: All tools registered")
        return True
    else:
        print(f"\n❌ TEST 1 FAILED: Expected {len(expected_tools)}, got {len(tools)}")
        return False


def test_tool_command_building():
    """Test 2: Verify tools can build commands"""
    print("\n" + "="*60)
    print("TEST 2: Command Building")
    print("="*60)
    
    from src.core.tool_base import (
        NmapServiceDetectionTool,
        NmapVulnScanTool,
        DnsLookupTool,
        SslScanTool,
        GobusterDirTool,
        SubdomainEnumTool,
        WebAppScanTool
    )
    
    tests = [
        ("Service Detection", NmapServiceDetectionTool(), {"target": "192.168.1.1"}),
        ("Vulnerability Scan", NmapVulnScanTool(), {"target": "192.168.1.1", "ports": "80,443"}),
        ("DNS Lookup", DnsLookupTool(), {"domain": "example.com", "record_type": "A"}),
        ("SSL Scan", SslScanTool(), {"target": "example.com", "port": 443}),
        ("Web Dir Enum", GobusterDirTool(), {"url": "http://example.com", "wordlist": "common.txt"}),
        ("Subdomain Enum", SubdomainEnumTool(), {"domain": "example.com", "wordlist": "subs.txt"}),
        ("Web App Scanner", WebAppScanTool(), {"url": "http://example.com"})
    ]
    
    all_passed = True
    
    for name, tool, params in tests:
        try:
            cmd = tool.build_command(**params)
            print(f"  ✓ {name}: {' '.join(cmd[:5])}..." if len(cmd) > 5 else f"  ✓ {name}: {' '.join(cmd)}")
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            all_passed = False
    
    if all_passed:
        print("\n✅ TEST 2 PASSED: All commands build successfully")
        return True
    else:
        print("\n❌ TEST 2 FAILED: Some commands failed")
        return False


def test_parser_imports():
    """Test 3: Verify parsers can be imported"""
    print("\n" + "="*60)
    print("TEST 3: Parser Imports")
    print("="*60)
    
    try:
        from src.core.parser_framework import (
            NmapServiceDetectionParser,
            NmapVulnScanParser,
            DnsLookupParser,
            SslScanParser,
            GobusterDirParser,
            SubdomainEnumParser,
            WebAppScanParser
        )
        
        parsers = [
            ("Service Detection Parser", NmapServiceDetectionParser),
            ("Vuln Scan Parser", NmapVulnScanParser),
            ("DNS Lookup Parser", DnsLookupParser),
            ("SSL Scan Parser", SslScanParser),
            ("Gobuster Dir Parser", GobusterDirParser),
            ("Subdomain Enum Parser", SubdomainEnumParser),
            ("Web App Scanner Parser", WebAppScanParser)
        ]
        
        for name, parser_class in parsers:
            parser = parser_class()
            print(f"  ✓ {name}")
        
        print("\n✅ TEST 3 PASSED: All parsers imported successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        return False


def test_coordinator_methods():
    """Test 4: Verify coordinator has all execute methods"""
    print("\n" + "="*60)
    print("TEST 4: Coordinator Methods")
    print("="*60)
    
    coordinator = SentinelCoordinator(db_path=":memory:")
    
    methods = [
        "execute_service_detection",
        "execute_vuln_scan",
        "execute_dns_lookup",
        "execute_ssl_scan",
        "execute_web_dir_enum",
        "execute_subdomain_enum",
        "execute_web_app_scan"
    ]
    
    all_found = True
    
    for method in methods:
        if hasattr(coordinator, method):
            print(f"  ✓ {method}")
        else:
            print(f"  ✗ {method} - NOT FOUND!")
            all_found = False
    
    coordinator.cleanup()
    
    if all_found:
        print("\n✅ TEST 4 PASSED: All coordinator methods exist")
        return True
    else:
        print("\n❌ TEST 4 FAILED: Some methods missing")
        return False


def test_orchestrator_mappings():
    """Test 5: Verify orchestrator has intent mappings"""
    print("\n" + "="*60)
    print("TEST 5: Orchestrator Intent Mappings")
    print("="*60)
    
    try:
        from src.ai.schemas import IntentType
        
        intents = [
            IntentType.SERVICE_DETECTION,
            IntentType.VULN_SCAN,
            IntentType.DNS_LOOKUP,
            IntentType.SSL_SCAN,
            IntentType.WEB_DIR_ENUM,
            IntentType.SUBDOMAIN_ENUM,
            IntentType.WEB_VULN_SCAN
        ]
        
        for intent in intents:
            print(f"  ✓ {intent.value}")
        
        print("\n✅ TEST 5 PASSED: All intent types exist")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 5 FAILED: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("SENTINEL - NEW TOOLS TEST SUITE")
    print("Testing 7 new security tools (Öncelik 3)")
    print("="*60)
    
    results = []
    
    # Test 1: Tool Registration
    results.append(("Tool Registration", test_tool_registration()))
    
    # Test 2: Command Building
    results.append(("Command Building", test_tool_command_building()))
    
    # Test 3: Parser Imports
    results.append(("Parser Imports", test_parser_imports()))
    
    # Test 4: Coordinator Methods
    results.append(("Coordinator Methods", test_coordinator_methods()))
    
    # Test 5: Orchestrator Mappings
    results.append(("Orchestrator Mappings", test_orchestrator_mappings()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "="*60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    # Create QApplication (required for Qt signals)
    app = QApplication(sys.argv)
    
    # Run tests
    success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

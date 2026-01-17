# SENTINEL AI - Action Planner v2 Test Suite
# Yeni katmanli mimari icin kapsamli testler

import sys
import time
from typing import List, Tuple

# Test edilecek moduller
from src.ai.schemas import IntentType, RiskLevel, Intent, ToolSpec, FinalCommand
from src.ai.tool_registry import (
    TOOL_REGISTRY,
    get_tool_for_intent,
    build_tool_spec,
    get_supported_intents
)
from src.ai.intent_resolver import IntentResolver
from src.ai.command_builder import CommandBuilder
from src.ai.policy_gate import PolicyGate
from src.ai.orchestrator import AIOrchestrator


# =============================================================================
# TEST CASES
# =============================================================================

# (user_input, expected_intent, expected_tool, target_hint)
INTENT_TEST_CASES = [
    # Host Discovery
    ("192.168.1.0/24 agini tara", IntentType.HOST_DISCOVERY, "nmap", None),
    ("agdaki cihazlari bul", IntentType.HOST_DISCOVERY, "nmap", None),
    ("ping taramasi yap", IntentType.HOST_DISCOVERY, "nmap", None),
    
    # Port Scan
    ("portlari tara", IntentType.PORT_SCAN, "nmap", None),
    ("example.com portlarini kontrol et", IntentType.PORT_SCAN, "nmap", None),
    ("acik portlari bul", IntentType.PORT_SCAN, "nmap", None),
    
    # DNS Lookup
    ("google.com DNS sorgusu yap", IntentType.DNS_LOOKUP, "nslookup", None),
    ("DNS kayitlarini goster", IntentType.DNS_LOOKUP, "nslookup", None),
    
    # Web Dir Enum
    ("web sitesinde dizin ara", IntentType.WEB_DIR_ENUM, "gobuster", None),
    ("dizin taramasi yap", IntentType.WEB_DIR_ENUM, "gobuster", None),
    
    # Vuln Scan
    ("zafiyet taramasi yap", IntentType.VULN_SCAN, "nmap", None),
    
    # Info Query
    ("nmap nedir?", IntentType.INFO_QUERY, "", None),
    ("nasil kullanilir?", IntentType.INFO_QUERY, "", None),
]


def run_test(name: str, test_func) -> bool:
    """Test calistir ve sonucu raporla"""
    try:
        result = test_func()
        status = "[OK]" if result else "[FAIL]"
        print(f"  {status} {name}")
        return result
    except Exception as e:
        print(f"  [ERROR] {name}: {e}")
        return False


def test_tool_registry() -> bool:
    """Tool Registry testleri"""
    print("\n" + "=" * 60)
    print("TEST: Tool Registry")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    # Test 1: Tum intent'ler icin tool var mi?
    def check_all_intents():
        for intent in IntentType:
            if intent not in TOOL_REGISTRY:
                return False
        return True
    
    if run_test("Tum intent'ler registry'de var", check_all_intents):
        passed += 1
    else:
        failed += 1
    
    # Test 2: build_tool_spec calisiyor mu?
    def check_build_tool_spec():
        spec = build_tool_spec(IntentType.PORT_SCAN, "192.168.1.1", {"ports": "22,80"})
        return spec is not None and spec.tool == "nmap" and "-p" in spec.arguments
    
    if run_test("build_tool_spec() calisiyor", check_build_tool_spec):
        passed += 1
    else:
        failed += 1
    
    # Test 3: requires_root dogru mu?
    def check_requires_root():
        # PORT_SCAN root gerektirmeli
        tool_def = get_tool_for_intent(IntentType.PORT_SCAN)
        if not tool_def.requires_root:
            return False
        # DNS_LOOKUP root gerektirmemeli
        tool_def = get_tool_for_intent(IntentType.DNS_LOOKUP)
        if tool_def.requires_root:
            return False
        return True
    
    if run_test("requires_root dogru ayarlanmis", check_requires_root):
        passed += 1
    else:
        failed += 1
    
    print(f"\nRegistry Tests: {passed}/{passed+failed} passed")
    return failed == 0


def test_command_builder() -> bool:
    """Command Builder testleri"""
    print("\n" + "=" * 60)
    print("TEST: Command Builder")
    print("=" * 60)
    
    passed = 0
    failed = 0
    builder = CommandBuilder()
    
    # Test 1: Valid target
    def check_valid_target():
        spec = ToolSpec(tool="nmap", arguments=["-sn"], target="192.168.1.1", 
                       requires_root=False, risk_level=RiskLevel.LOW)
        cmd, err = builder.build(spec)
        return cmd is not None and err is None
    
    if run_test("Valid IP target kabul ediliyor", check_valid_target):
        passed += 1
    else:
        failed += 1
    
    # Test 2: Shell injection blocked
    def check_shell_injection():
        spec = ToolSpec(tool="nmap", arguments=["-sn"], target="192.168.1.1; rm -rf /",
                       requires_root=False, risk_level=RiskLevel.LOW)
        cmd, err = builder.build(spec)
        return cmd is None and err is not None
    
    if run_test("Shell injection engelleniyor", check_shell_injection):
        passed += 1
    else:
        failed += 1
    
    # Test 3: URL target
    def check_url_target():
        spec = ToolSpec(tool="gobuster", arguments=["dir"], target="http://example.com",
                       requires_root=False, risk_level=RiskLevel.MEDIUM)
        cmd, err = builder.build(spec)
        return cmd is not None and "http://example.com" in cmd.arguments
    
    if run_test("URL target kabul ediliyor", check_url_target):
        passed += 1
    else:
        failed += 1
    
    # Test 4: Domain target
    def check_domain_target():
        spec = ToolSpec(tool="nslookup", arguments=[], target="google.com",
                       requires_root=False, risk_level=RiskLevel.LOW)
        cmd, err = builder.build(spec)
        return cmd is not None
    
    if run_test("Domain target kabul ediliyor", check_domain_target):
        passed += 1
    else:
        failed += 1
    
    print(f"\nCommand Builder Tests: {passed}/{passed+failed} passed")
    return failed == 0


def test_policy_gate() -> bool:
    """Policy Gate testleri"""
    print("\n" + "=" * 60)
    print("TEST: Policy Gate")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    # Test 1: Policy kapali - her sey serbest
    def check_policy_disabled():
        gate = PolicyGate(enabled=False)
        allowed, _ = gate.check(IntentType.SQL_INJECTION)
        return allowed
    
    if run_test("Policy kapali = her sey serbest", check_policy_disabled):
        passed += 1
    else:
        failed += 1
    
    # Test 2: Policy acik - uyari var
    def check_policy_warning():
        gate = PolicyGate(enabled=True)
        allowed, msg = gate.check(IntentType.BRUTE_FORCE_SSH)
        return allowed and msg is not None
    
    if run_test("Policy acik = uyari mesaji", check_policy_warning):
        passed += 1
    else:
        failed += 1
    
    # Test 3: Toggle calisiyor
    def check_toggle():
        gate = PolicyGate(enabled=False)
        gate.enable()
        return gate.is_enabled
    
    if run_test("Toggle calisiyor", check_toggle):
        passed += 1
    else:
        failed += 1
    
    print(f"\nPolicy Gate Tests: {passed}/{passed+failed} passed")
    return failed == 0


def test_intent_resolver() -> bool:
    """Intent Resolver testleri (LLM gerektirir)"""
    print("\n" + "=" * 60)
    print("TEST: Intent Resolver (LLM)")
    print("=" * 60)
    
    resolver = IntentResolver(model="whiterabbitneo")
    
    if not resolver.check_available():
        print("  [SKIP] LLM mevcut degil")
        return True
    
    passed = 0
    failed = 0
    
    for user_input, expected_intent, _, _ in INTENT_TEST_CASES[:6]:  # Ilk 6 test
        intent = resolver.resolve(user_input)
        
        if intent.intent_type == expected_intent:
            print(f"  [OK] '{user_input[:30]}...' -> {intent.intent_type.value}")
            passed += 1
        else:
            print(f"  [FAIL] '{user_input[:30]}...' -> {intent.intent_type.value} (expected: {expected_intent.value})")
            failed += 1
    
    print(f"\nIntent Resolver Tests: {passed}/{passed+failed} passed")
    return failed == 0


def test_orchestrator_e2e() -> bool:
    """End-to-end Orchestrator testleri"""
    print("\n" + "=" * 60)
    print("TEST: Orchestrator E2E")
    print("=" * 60)
    
    orch = AIOrchestrator(model="whiterabbitneo")
    
    if not orch.check_services()[0]:
        print("  [SKIP] LLM mevcut degil")
        return True
    
    passed = 0
    failed = 0
    total_time = 0
    
    test_cases = [
        ("192.168.1.0/24 agini tara", None, "nmap"),
        ("example.com portlarini kontrol et", None, "nmap"),
        ("google.com DNS sorgusu yap", None, "nslookup"),
    ]
    
    for user_input, target, expected_tool in test_cases:
        start = time.time()
        result = orch.process_v2(user_input, target)
        elapsed = time.time() - start
        total_time += elapsed
        
        if result["success"] and result["command"]:
            if result["command"].executable == expected_tool:
                print(f"  [OK] '{user_input[:30]}...' -> {result['command'].executable} ({elapsed:.1f}s)")
                passed += 1
            else:
                print(f"  [FAIL] '{user_input[:30]}...' -> {result['command'].executable} (expected: {expected_tool})")
                failed += 1
        else:
            print(f"  [FAIL] '{user_input[:30]}...' -> {result['message']}")
            failed += 1
    
    print(f"\nOrchestrator E2E Tests: {passed}/{passed+failed} passed")
    print(f"Toplam sure: {total_time:.1f}s, Ortalama: {total_time/len(test_cases):.1f}s")
    return failed == 0


def test_backward_compatibility() -> bool:
    """Legacy API uyumluluk testleri"""
    print("\n" + "=" * 60)
    print("TEST: Backward Compatibility")
    print("=" * 60)
    
    orch = AIOrchestrator(model="whiterabbitneo")
    
    if not orch.check_services()[0]:
        print("  [SKIP] LLM mevcut degil")
        return True
    
    passed = 0
    failed = 0
    
    # Test 1: process() AIResponse donuyor mu?
    def check_process_returns_airesponse():
        response = orch.process("192.168.1.0/24 tara")
        from src.ai.schemas import AIResponse
        return isinstance(response, AIResponse)
    
    if run_test("process() AIResponse donuyor", check_process_returns_airesponse):
        passed += 1
    else:
        failed += 1
    
    # Test 2: ToolCommand dogru mu?
    def check_toolcommand():
        response = orch.process("192.168.1.0/24 tara")
        if response.command:
            return hasattr(response.command, 'tool') and hasattr(response.command, 'arguments')
        return False
    
    if run_test("ToolCommand yapisi dogru", check_toolcommand):
        passed += 1
    else:
        failed += 1
    
    # Test 3: get_status() calisiyor mu?
    def check_get_status():
        status = orch.get_status()
        return "version" in status and status["version"] == "v2"
    
    if run_test("get_status() v2 donuyor", check_get_status):
        passed += 1
    else:
        failed += 1
    
    print(f"\nBackward Compatibility Tests: {passed}/{passed+failed} passed")
    return failed == 0


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 70)
    print("SENTINEL AI - Action Planner v2 Test Suite")
    print("=" * 70)
    
    results = []
    
    # Unit tests (LLM gerektirmez)
    results.append(("Tool Registry", test_tool_registry()))
    results.append(("Command Builder", test_command_builder()))
    results.append(("Policy Gate", test_policy_gate()))
    
    # Integration tests (LLM gerektirir)
    results.append(("Intent Resolver", test_intent_resolver()))
    results.append(("Orchestrator E2E", test_orchestrator_e2e()))
    results.append(("Backward Compat", test_backward_compatibility()))
    
    # Summary
    print("\n" + "=" * 70)
    print("OZET")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("TUM TESTLER BASARILI!")
    else:
        print("BAZI TESTLER BASARISIZ!")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

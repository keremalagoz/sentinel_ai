# SENTINEL AI - Policy Gate
# Action Planner v2: Opsiyonel intent/action kontrolu
#
# Bu modul VARSAYILAN OLARAK ACIK.
# POLICY_ENABLED = False yapilirsa intent kontrolleri bypass edilir.
# Modular tasarim: Toggle ile kolayca acilip kapatilabilir.

from typing import Tuple, Optional, Dict
from src.ai.schemas import IntentType, RiskLevel
from src.ai.execution_policy import ExecutionPolicy, TacticalIntent
from src.ai.tool_registry import get_tool_for_intent


# =============================================================================
# CONFIGURATION
# =============================================================================

# Ana switch - True = policy aktif (tek akış)
POLICY_ENABLED = True

# Intent -> TacticalIntent mapping (ExecutionPolicy icin)
_INTENT_TO_TACTIC: Dict[IntentType, TacticalIntent] = {
    IntentType.HOST_DISCOVERY: TacticalIntent.PING_SWEEP,
    IntentType.PORT_SCAN: TacticalIntent.PORT_SCAN,
    IntentType.SERVICE_DETECTION: TacticalIntent.SERVICE_DETECTION,
    IntentType.OS_DETECTION: TacticalIntent.OS_FINGERPRINT,
    IntentType.VULN_SCAN: TacticalIntent.VULN_SCAN,
    IntentType.SSL_SCAN: TacticalIntent.SSL_TLS_ANALYSIS,
    IntentType.WEB_DIR_ENUM: TacticalIntent.DIRECTORY_BRUTE_FORCE,
    IntentType.DNS_LOOKUP: TacticalIntent.DNS_ENUMERATION,
    IntentType.SUBDOMAIN_ENUM: TacticalIntent.SUBDOMAIN_ENUMERATION,
    IntentType.BRUTE_FORCE_SSH: TacticalIntent.CREDENTIAL_BRUTE_FORCE,
    IntentType.BRUTE_FORCE_HTTP: TacticalIntent.CREDENTIAL_BRUTE_FORCE,
    IntentType.SQL_INJECTION: TacticalIntent.EXPLOIT_WEAKNESS,
}


# =============================================================================
# POLICY GATE
# =============================================================================

class PolicyGate:
    """
    Intent-based policy kontrolu.
    
    Varsayilan olarak ACIK (POLICY_ENABLED = True).
    Acildiginda intent'leri kontrol eder ve engeller/uyarir.
    
    Kullanim:
        gate = PolicyGate()
        allowed, message = gate.check(IntentType.PORT_SCAN)
        
        if not allowed:
            return error_response(message)
        elif message:
            show_warning(message)
    """
    
    def __init__(self, enabled: Optional[bool] = None):
        """
        PolicyGate'i baslat.
        
        Args:
            enabled: Policy aktif mi? None ise global POLICY_ENABLED kullanilir.
        """
        self._enabled = enabled if enabled is not None else POLICY_ENABLED
        self._policy = ExecutionPolicy()
    
    @property
    def is_enabled(self) -> bool:
        """Policy aktif mi?"""
        return self._enabled
    
    def enable(self):
        """Policy'yi aktif et"""
        self._enabled = True
    
    def disable(self):
        """Policy'yi devre disi birak"""
        self._enabled = False
    
    def check(self, intent_type: IntentType) -> Tuple[bool, Optional[str]]:
        """
        Intent'i kontrol et.
        
        Args:
            intent_type: Kontrol edilecek intent
        
        Returns:
            (allowed, message)
            - (True, None): Izin verildi, mesaj yok
            - (True, "warning..."): Izin verildi ama uyari var
            - (False, "error..."): Engellendi
        """
        # Policy kapali - her sey serbest
        if not self._enabled:
            return (True, None)

        tactic = _INTENT_TO_TACTIC.get(intent_type)
        if tactic:
            # Sprint policy: confirm-required veya blocked
            if not self._policy.is_tactic_allowed_auto(tactic):
                if self._policy.requires_confirmation(tactic):
                    return (
                        False,
                        f"Bu islem onay gerektirir: {intent_type.value}. "
                        f"Lutfen manuel onay verin."
                    )
                return (
                    False,
                    f"Bu islem policy tarafindan engellendi: {intent_type.value}."
                )

        # Risk seviyesine gore uyari
        tool_def = get_tool_for_intent(intent_type)
        if tool_def and tool_def.risk_level in [RiskLevel.HIGH]:
            return (
                True,
                f"Dikkat: {intent_type.value} yuksek riskli bir islemdir. "
                f"Sadece yetkili sistemlerde kullanin."
            )

        return (True, None)
    
    def add_blocked_intent(self, intent_type: IntentType):
        """Legacy - policy tek akis, disaridan engelleme desteklenmez"""
        raise NotImplementedError("Policy tek akis: bloklama ExecutionPolicy ile yonetilir")
    
    def remove_blocked_intent(self, intent_type: IntentType):
        """Legacy - policy tek akis, disaridan engelleme desteklenmez"""
        raise NotImplementedError("Policy tek akis: bloklama ExecutionPolicy ile yonetilir")
    
    def add_warn_intent(self, intent_type: IntentType):
        """Legacy - policy tek akis, disaridan uyari ekleme desteklenmez"""
        raise NotImplementedError("Policy tek akis: uyari risk seviyesinden gelir")
    
    def remove_warn_intent(self, intent_type: IntentType):
        """Legacy - policy tek akis, disaridan uyari ekleme desteklenmez"""
        raise NotImplementedError("Policy tek akis: uyari risk seviyesinden gelir")
    
    def get_policy_status(self) -> dict:
        """Policy durumunu doner"""
        return {
            "enabled": self._enabled,
            "blocked_intents": [i.value for i in self._policy.get_blocked_tactics()],
            "warn_intents": ["high_risk"],
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_gate: Optional[PolicyGate] = None


def get_policy_gate() -> PolicyGate:
    """Singleton PolicyGate instance doner"""
    global _gate
    if _gate is None:
        _gate = PolicyGate()
    return _gate


def quick_check(intent_type: IntentType) -> Tuple[bool, Optional[str]]:
    """Hizli policy kontrolu"""
    gate = get_policy_gate()
    return gate.check(intent_type)


def set_policy_enabled(enabled: bool):
    """Global policy durumunu ayarla"""
    gate = get_policy_gate()
    if enabled:
        gate.enable()
    else:
        gate.disable()


# =============================================================================
# DEBUG
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SENTINEL AI - Policy Gate Test")
    print("=" * 60)
    
    gate = PolicyGate()
    
    print(f"\nPolicy Enabled: {gate.is_enabled}")
    print(f"Status: {gate.get_policy_status()}")
    
    # Test: Policy kapali
    print("\n[Test 1] Policy KAPALI")
    print("-" * 40)
    
    for intent in [IntentType.PORT_SCAN, IntentType.SQL_INJECTION, IntentType.BRUTE_FORCE_SSH]:
        allowed, msg = gate.check(intent)
        print(f"{intent.value}: allowed={allowed}, msg={msg}")
    
    # Test: Policy acik
    print("\n[Test 2] Policy ACIK")
    print("-" * 40)
    
    gate.enable()
    
    for intent in [IntentType.PORT_SCAN, IntentType.SQL_INJECTION, IntentType.BRUTE_FORCE_SSH]:
        allowed, msg = gate.check(intent)
        status = "OK" if allowed else "BLOCKED"
        print(f"{intent.value}: {status}")
        if msg:
            print(f"  -> {msg}")
    
    # Test: Risk uyari
    print("\n[Test 3] Yuksek risk uyari")
    print("-" * 40)
    
    allowed, msg = gate.check(IntentType.SQL_INJECTION)
    print(f"allowed={allowed}")
    print(f"msg={msg}")

# SENTINEL AI - Policy Gate
# Action Planner v2: Opsiyonel intent/action kontrolu
#
# Bu modul VARSAYILAN OLARAK KAPALI.
# POLICY_ENABLED = True yapilirsa intent'ler kontrol edilir.
# Modular tasarim: Toggle ile kolayca acilip kapatilabilir.

from typing import Tuple, Optional, Set
from src.ai.schemas import IntentType


# =============================================================================
# CONFIGURATION
# =============================================================================

# Ana switch - False = tum kontroller bypass edilir
POLICY_ENABLED = False

# Engellenecek intent'ler (POLICY_ENABLED = True oldugunda)
BLOCKED_INTENTS: Set[IntentType] = set()
# Ornek: BLOCKED_INTENTS = {IntentType.SQL_INJECTION}

# Uyari verilecek intent'ler (engellenmez ama kullanici uyarilir)
WARN_INTENTS: Set[IntentType] = {
    IntentType.BRUTE_FORCE_SSH,
    IntentType.BRUTE_FORCE_HTTP,
    IntentType.SQL_INJECTION,
    IntentType.VULN_SCAN,
}


# =============================================================================
# POLICY GATE
# =============================================================================

class PolicyGate:
    """
    Intent-based policy kontrolu.
    
    Varsayilan olarak KAPALI (POLICY_ENABLED = False).
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
        
        # Engellenen intent mi?
        if intent_type in BLOCKED_INTENTS:
            return (
                False,
                f"Bu islem engellenmistir: {intent_type.value}. "
                f"Policy ayarlarindan degistirilebilir."
            )
        
        # Uyari gerektiren intent mi?
        if intent_type in WARN_INTENTS:
            return (
                True,
                f"Dikkat: {intent_type.value} yuksek riskli bir islemdir. "
                f"Sadece yetkili sistemlerde kullanin."
            )
        
        # Normal islem - gecis serbest
        return (True, None)
    
    def add_blocked_intent(self, intent_type: IntentType):
        """Intent'i engelleme listesine ekle"""
        BLOCKED_INTENTS.add(intent_type)
    
    def remove_blocked_intent(self, intent_type: IntentType):
        """Intent'i engelleme listesinden cikar"""
        BLOCKED_INTENTS.discard(intent_type)
    
    def add_warn_intent(self, intent_type: IntentType):
        """Intent'i uyari listesine ekle"""
        WARN_INTENTS.add(intent_type)
    
    def remove_warn_intent(self, intent_type: IntentType):
        """Intent'i uyari listesinden cikar"""
        WARN_INTENTS.discard(intent_type)
    
    def get_policy_status(self) -> dict:
        """Policy durumunu doner"""
        return {
            "enabled": self._enabled,
            "blocked_intents": [i.value for i in BLOCKED_INTENTS],
            "warn_intents": [i.value for i in WARN_INTENTS],
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
    
    # Test: Intent engelleme
    print("\n[Test 3] SQL_INJECTION engellendi")
    print("-" * 40)
    
    gate.add_blocked_intent(IntentType.SQL_INJECTION)
    allowed, msg = gate.check(IntentType.SQL_INJECTION)
    print(f"allowed={allowed}")
    print(f"msg={msg}")

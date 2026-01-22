"""Execution Policy - Safe by Default

Sprint 1 Locked Policy Configuration
"""

from enum import Enum
from typing import List
from pydantic import BaseModel, ConfigDict


class RiskLevel(Enum):
    """Tool risk classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TacticalIntent(Enum):
    """Tactical intents from intent_hierarchy_design.md"""
    # Reconnaissance
    PING_SWEEP = "ping_sweep"
    PORT_SCAN = "port_scan"
    SERVICE_DETECTION = "service_detection"
    OS_FINGERPRINT = "os_fingerprint"
    DNS_ENUMERATION = "dns_enumeration"
    SUBDOMAIN_ENUMERATION = "subdomain_enumeration"
    
    # Web Enumeration
    DIRECTORY_BRUTE_FORCE = "directory_brute_force"
    TECHNOLOGY_DETECTION = "technology_detection"
    PARAMETER_FUZZING = "parameter_fuzzing"
    
    # Vulnerability Assessment
    VULN_SCAN = "vuln_scan"
    SSL_TLS_ANALYSIS = "ssl_tls_analysis"
    
    # Exploitation (HIGH RISK)
    EXPLOIT_WEAKNESS = "exploit_weakness"
    CREDENTIAL_BRUTE_FORCE = "credential_brute_force"
    PASSWORD_SPRAY = "password_spray"


class ExecutionPolicy(BaseModel):
    """
    Execution policy for planner and recommendation engine.
    
    Sprint 1 LOCKED RULES:
    - allow_persistent_changes = False (IMMUTABLE)
    - confirm_before_tactics = [EXPLOIT_WEAKNESS, CREDENTIAL_BRUTE_FORCE] (IMMUTABLE)
    
    These rules CANNOT be changed during Sprint 1 implementation.
    """
    
    # ========================================
    # SPRINT 1 LOCKED RULES (IMMUTABLE)
    # ========================================
    
    allow_persistent_changes: bool = False
    """
    SPRINT 1 LOCKED: False
    
    Persistent changes include:
    - File write/modify on target
    - Exploit execution
    - Credential brute force
    - DoS attacks
    - Service modification
    
    When False:
    - Tools with persistent_changes_risk=True are BLOCKED
    - User cannot override without explicit policy change
    - Recommendation engine will NOT suggest these tools
    
    Legal Safety: Default deny prevents unauthorized modifications.
    """
    
    confirm_before_tactics: List[TacticalIntent] = [
        TacticalIntent.EXPLOIT_WEAKNESS,
        TacticalIntent.CREDENTIAL_BRUTE_FORCE,
    ]
    """
    SPRINT 1 LOCKED: [EXPLOIT_WEAKNESS, CREDENTIAL_BRUTE_FORCE]
    
    Tactics requiring explicit user confirmation before execution.
    
    Planner behavior:
    - If tactic in this list → Skip automatic addition
    - Recommendation engine → Suggest with WARNING + confirmation prompt
    - User must explicitly approve each instance
    
    Legal Safety: High-risk actions require conscious user decision.
    """
    
    # ========================================
    # SPRINT 2+ RULES (Deferred)
    # ========================================
    
    # Sprint 2: DoS risk control
    # allow_dos_risk: bool = False
    
    # Sprint 2: Max auto-add risk level
    # max_auto_risk: RiskLevel = RiskLevel.MEDIUM
    
    # Sprint 2: Stealth requirements
    # require_stealth: bool = False
    
    # Sprint 2: Time limits
    # max_tool_duration_seconds: int = 3600
    
    def is_tactic_allowed_auto(self, tactic: TacticalIntent) -> bool:
        """
        Check if tactic can be automatically added to plan.
        
        Returns:
            False if tactic requires confirmation
            False if tactic involves persistent changes (blocked)
            True otherwise
        """
        # Sprint 1 rule: Confirm-before tactics not allowed auto
        if tactic in self.confirm_before_tactics:
            return False
        
        # Sprint 1 rule: Persistent changes not allowed
        if tactic in [
            TacticalIntent.EXPLOIT_WEAKNESS,
            TacticalIntent.CREDENTIAL_BRUTE_FORCE,
            TacticalIntent.PASSWORD_SPRAY,
        ]:
            if not self.allow_persistent_changes:
                return False
        
        return True
    
    def requires_confirmation(self, tactic: TacticalIntent) -> bool:
        """Check if tactic requires user confirmation"""
        return tactic in self.confirm_before_tactics
    
    def get_blocked_tactics(self) -> List[TacticalIntent]:
        """
        Get list of tactics that are completely blocked by policy.
        
        Sprint 1: All persistent-change tactics blocked when allow_persistent_changes=False
        """
        if not self.allow_persistent_changes:
            return [
                TacticalIntent.EXPLOIT_WEAKNESS,
                TacticalIntent.CREDENTIAL_BRUTE_FORCE,
                TacticalIntent.PASSWORD_SPRAY,
            ]
        return []
    
    model_config = ConfigDict(
        frozen=False  # Allow runtime modification (for Sprint 2+ policy updates)
    )


# ========================================
# DEFAULT POLICY (Sprint 1)
# ========================================

DEFAULT_POLICY = ExecutionPolicy(
    allow_persistent_changes=False,
    confirm_before_tactics=[
        TacticalIntent.EXPLOIT_WEAKNESS,
        TacticalIntent.CREDENTIAL_BRUTE_FORCE,
    ]
)
"""
Default policy for Sprint 1.

Safe by default:
- No persistent changes
- High-risk tactics require confirmation
- Legal compliance enforced
"""


# ========================================
# VALIDATION FUNCTIONS
# ========================================

def validate_policy_sprint1(policy: ExecutionPolicy) -> None:
    """
    Validate policy against Sprint 1 locked rules.
    
    Raises:
        ValueError: If policy violates Sprint 1 rules
    """
    if policy.allow_persistent_changes != False:
        raise ValueError(
            "Sprint 1 rule violation: allow_persistent_changes must be False"
        )
    
    required_confirmations = {
        TacticalIntent.EXPLOIT_WEAKNESS,
        TacticalIntent.CREDENTIAL_BRUTE_FORCE,
    }
    
    actual_confirmations = set(policy.confirm_before_tactics)
    
    if not required_confirmations.issubset(actual_confirmations):
        missing = required_confirmations - actual_confirmations
        raise ValueError(
            f"Sprint 1 rule violation: confirm_before_tactics missing {missing}"
        )


# ========================================
# USAGE EXAMPLES
# ========================================

if __name__ == "__main__":
    # Example 1: Default policy (Sprint 1)
    policy = DEFAULT_POLICY
    
    print(f"Allow persistent changes: {policy.allow_persistent_changes}")
    print(f"Blocked tactics: {policy.get_blocked_tactics()}")
    print(f"Confirm before: {policy.confirm_before_tactics}")
    
    # Example 2: Check tactic allowance
    print(f"\nPORT_SCAN auto-allowed: {policy.is_tactic_allowed_auto(TacticalIntent.PORT_SCAN)}")
    print(f"EXPLOIT_WEAKNESS auto-allowed: {policy.is_tactic_allowed_auto(TacticalIntent.EXPLOIT_WEAKNESS)}")
    
    # Example 3: Confirmation check
    print(f"\nEXPLOIT_WEAKNESS requires confirmation: {policy.requires_confirmation(TacticalIntent.EXPLOIT_WEAKNESS)}")
    print(f"VULN_SCAN requires confirmation: {policy.requires_confirmation(TacticalIntent.VULN_SCAN)}")
    
    # Example 4: Validate Sprint 1 compliance
    try:
        validate_policy_sprint1(policy)
        print("\n[OK] Policy compliant with Sprint 1 rules")
    except ValueError as e:
        print(f"\n[FAIL] Policy violation: {e}")
    
    # Example 5: Invalid policy (would fail validation)
    try:
        invalid_policy = ExecutionPolicy(
            allow_persistent_changes=True,  # VIOLATION
            confirm_before_tactics=[]  # VIOLATION
        )
        validate_policy_sprint1(invalid_policy)
    except ValueError as e:
        print(f"\n[FAIL] Expected violation caught: {e}")

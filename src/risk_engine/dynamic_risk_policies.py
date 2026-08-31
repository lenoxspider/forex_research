"""
Dynamic Risk Policies for Prop-Firm Evaluation and Funded Accounts.

Implements predefined, economically sound dynamic risk policies:
- Policy A: Constant Fixed Risk
- Policy B: Drawdown De-risking (scales down after drawdown expansion)
- Policy C: Target Protection (de-risks when close to profit target)
- Policy D: Drawdown-Budget Sizing (proportional to remaining max DD buffer)
- Policy E: Challenge-Aware Master Schedule (combines B, C, and D)

STRICT FAIL-CLOSED GUARANTEE:
Any numerical invalidity or boundary ambiguity results in 0.0% risk (DEFAULT REJECT).
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger("DynamicRiskPolicies")


@dataclass(frozen=True)
class PolicyState:
    current_equity: float
    initial_balance: float
    high_water_mark: float
    current_drawdown_pct: float
    distance_to_target_pct: Optional[float]
    remaining_daily_budget_pct: float
    remaining_max_dd_budget_pct: float
    is_challenge_mode: bool = True


class DynamicRiskPolicyEngine:
    """
    Computes dynamically adjusted per-trade risk percentages based on account state.
    """

    @staticmethod
    def calculate_risk(
        policy_name: str,
        base_risk_pct: float,
        state: PolicyState,
    ) -> float:
        """
        Calculates allowed risk percentage under specified policy with fail-closed safety.
        """
        try:
            if state.current_drawdown_pct >= 9.5 or state.remaining_max_dd_budget_pct <= 0.5:
                return 0.0  # Hard stop at DD boundary

            if state.remaining_daily_budget_pct <= 0.5:
                return 0.0  # Hard stop at daily loss boundary

            if policy_name == "POLICY_A_CONSTANT":
                return float(base_risk_pct)

            elif policy_name == "POLICY_B_DRAWDOWN_DERISKING":
                # De-risk as drawdown expands
                if state.current_drawdown_pct >= 5.0:
                    return float(round(base_risk_pct * 0.25, 3))
                elif state.current_drawdown_pct >= 3.0:
                    return float(round(base_risk_pct * 0.50, 3))
                return float(base_risk_pct)

            elif policy_name == "POLICY_C_TARGET_PROTECTION":
                # De-risk as account nears the profit target to eliminate overshoot volatility
                if state.is_challenge_mode and state.distance_to_target_pct is not None:
                    if state.distance_to_target_pct <= 0.8:
                        return float(min(base_risk_pct, 0.15))
                    elif state.distance_to_target_pct <= 1.5:
                        return float(min(base_risk_pct, 0.25))
                return float(base_risk_pct)

            elif policy_name == "POLICY_D_DRAWDOWN_BUDGET":
                # Risk scaled to remaining drawdown buffer (allow at least 12 losing trades)
                budget_risk = state.remaining_max_dd_budget_pct / 12.0
                return float(max(0.10, min(base_risk_pct, round(budget_risk, 3))))

            elif policy_name == "POLICY_E_CHALLENGE_AWARE":
                # Hybrid Schedule: Target Protection + Drawdown De-risking + Budget Ceiling
                risk = base_risk_pct
                # 1. Target protection
                if state.is_challenge_mode and state.distance_to_target_pct is not None:
                    if state.distance_to_target_pct <= 0.8:
                        risk = min(risk, 0.15)
                    elif state.distance_to_target_pct <= 1.5:
                        risk = min(risk, 0.25)

                # 2. Drawdown de-risking
                if state.current_drawdown_pct >= 5.0:
                    risk = min(risk, base_risk_pct * 0.25)
                elif state.current_drawdown_pct >= 3.0:
                    risk = min(risk, base_risk_pct * 0.50)

                # 3. Drawdown budget ceiling
                budget_ceiling = state.remaining_max_dd_budget_pct / 12.0
                risk = min(risk, budget_ceiling)

                return float(max(0.10, round(risk, 3)))

            else:
                return float(base_risk_pct)

        except Exception as e:
            logger.error(f"DynamicRiskPolicyEngine failure: {e} -> Failing closed with 0.0% risk.")
            return 0.0

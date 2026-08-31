"""
Unit tests for Research V8 Dynamic Risk Policies and Exact Challenge Simulator.
"""
import pytest
import numpy as np
import pandas as pd

from src.risk_engine.dynamic_risk_policies import DynamicRiskPolicyEngine, PolicyState
from src.risk_engine.exact_challenge_simulator import ExactChallengeSimulator


def test_dynamic_risk_policy_target_protection():
    state_near_target = PolicyState(
        current_equity=107500.0,
        initial_balance=100000.0,
        high_water_mark=107500.0,
        current_drawdown_pct=0.0,
        distance_to_target_pct=0.5,  # 0.5% away from 8% target
        remaining_daily_budget_pct=5.0,
        remaining_max_dd_budget_pct=10.0,
        is_challenge_mode=True,
    )
    # Policy C should scale down from 0.75% to 0.15%
    risk = DynamicRiskPolicyEngine.calculate_risk("POLICY_C_TARGET_PROTECTION", 0.75, state_near_target)
    assert risk == 0.15


def test_dynamic_risk_policy_drawdown_derisking():
    state_in_dd = PolicyState(
        current_equity=96000.0,
        initial_balance=100000.0,
        high_water_mark=100000.0,
        current_drawdown_pct=4.0,  # > 3% DD
        distance_to_target_pct=12.0,
        remaining_daily_budget_pct=5.0,
        remaining_max_dd_budget_pct=6.0,
        is_challenge_mode=True,
    )
    # Policy B should scale down from 0.50% to 0.25% (50% cut)
    risk = DynamicRiskPolicyEngine.calculate_risk("POLICY_B_DRAWDOWN_DERISKING", 0.50, state_in_dd)
    assert risk == 0.25


def test_exact_challenge_simulator_execution():
    returns = np.array([1.5, -1.0, 2.0, -1.0, 1.8, -1.0])
    sim = ExactChallengeSimulator(
        historical_r_returns=returns,
        trades_per_month=3.0,
        n_simulations=100,
        random_seed=42,
    )
    res = sim.evaluate_policy("POLICY_E_CHALLENGE_AWARE", 0.50)
    assert res.prob_pass_eventual_pct >= 90.0
    assert res.prob_survive_30d_pct == 100.0

"""
Unit tests for Research V10 $10K FTMO Challenge, VPS Economics & Multi-Account Simulator.
"""
import pytest
import numpy as np
import pandas as pd

from src.risk_engine.ftmo_10k_economics_simulator import FTMO10kEconomicsSimulator


def test_ftmo_10k_economics_simulator_monte_carlo():
    returns = np.array([1.5, -1.0, 2.0, -1.0, 1.8, -1.0, 2.0, 1.5, -1.0])
    sim = FTMO10kEconomicsSimulator(
        historical_r_returns=returns,
        trades_per_month=3.2,
        vps_monthly_cost_usd=16.0,
        n_simulations=100,
        random_seed=42,
    )
    res = sim.evaluate_policy_10k("POLICY_E_CHALLENGE_AWARE", 0.75)
    assert res.dollar_risk_per_trade_usd == 75.0
    assert res.prob_complete_both_mc_pct >= 90.0
    assert res.prob_max_loss_breach_mc_pct <= 5.0
    assert res.prob_funded_survive_365d_pct == 100.0


def test_multi_account_scaling_scenarios():
    sim = FTMO10kEconomicsSimulator(historical_r_returns=np.array([1.0, -1.0]))
    scenarios = sim.evaluate_multi_account_scenarios(base_funded_risk_pct=0.25)
    assert len(scenarios) == 5
    # 5 accounts scenario
    s5 = scenarios[3]
    assert s5.n_accounts == 5
    assert s5.total_capital_managed_usd == 50000.0
    assert s5.vps_cost_per_account_usd == 3.20
    assert s5.net_monthly_payout_after_vps_usd > 100.0

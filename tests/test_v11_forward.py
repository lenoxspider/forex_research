"""
Unit tests for Research V11 Forward $10K FTMO Paper Validation.
"""
import pytest
import numpy as np
import pandas as pd

from src.strategy_engine.production_candidate import ProductionFreezeCandidate
from src.risk_engine.ftmo_10k_economics_simulator import FTMO10kEconomicsSimulator
from src.execution_engine.drift_monitor import ExecutionDriftMonitor


def test_production_candidate_fingerprint_integrity():
    candidate = ProductionFreezeCandidate("EURUSD")
    current_hash = candidate.fingerprint
    assert len(current_hash) == 64
    assert current_hash == "e25d59830e183890a91446bde99d5a63ee31306e90a09c8106c9b7ead5a8c639"


def test_v11_virtual_risk_policies():
    returns = np.array([1.5, -1.0, 2.0, -1.0, 1.8, -1.0, 2.0, 1.5, -1.0])
    sim = FTMO10kEconomicsSimulator(
        historical_r_returns=returns,
        trades_per_month=3.2,
        vps_monthly_cost_usd=16.0,
        n_simulations=100,
        random_seed=42,
    )
    # Test 0.75% challenge-aware
    res = sim.evaluate_policy_10k("POLICY_E_CHALLENGE_AWARE", 0.75)
    assert res.dollar_risk_per_trade_usd == 75.0
    assert res.prob_complete_both_mc_pct >= 90.0
    assert res.net_monthly_income_after_vps_usd > 0.0


def test_execution_drift_monitor():
    benchmarks = {
        "EURUSD": {"trades": 51, "win_rate_pct": 52.9, "expectancy_r": 0.346, "assumed_spread_pips": 0.8, "assumed_slippage_pips": 0.2},
    }
    monitor = ExecutionDriftMonitor(benchmarks)
    d = monitor.compute_pair_drift("EURUSD", pd.DataFrame())
    assert d.symbol == "EURUSD"
    assert d.is_execution_consistent

"""
Unit tests for Research V9 FTMO 2-Step Challenge Simulator.
"""
import pytest
import numpy as np
import pandas as pd

from src.risk_engine.ftmo_two_phase_simulator import FTMO2StepSimulator


def test_ftmo_two_phase_simulator_monte_carlo():
    returns = np.array([1.5, -1.0, 2.0, -1.0, 1.8, -1.0, 2.0, 1.5, -1.0])
    sim = FTMO2StepSimulator(
        historical_r_returns=returns,
        trades_per_month=3.2,
        n_simulations=100,
        random_seed=42,
    )
    res = sim.evaluate_policy_monte_carlo("POLICY_E_CHALLENGE_AWARE", 0.75)
    assert res.prob_complete_both_phases_pct >= 90.0
    assert res.prob_max_loss_breach_pct <= 5.0
    assert res.prob_funded_survive_30d_pct == 100.0


def test_ftmo_two_phase_chronological_replay():
    # Synthetic trades df
    dates = pd.date_range("2023-01-01", periods=30, freq="5D", tz="UTC")
    df_tr = pd.DataFrame({
        "entry_time": dates,
        "symbol": ["EURUSD"] * 30,
        "pnl_net_pips": [30.0, -15.0, 30.0, 30.0, -15.0, 30.0] * 5,
        "risk_pips": [15.0] * 30,
    })
    sim = FTMO2StepSimulator(
        historical_r_returns=(df_tr["pnl_net_pips"] / df_tr["risk_pips"]).values,
        trades_df=df_tr,
    )
    df_res = sim.run_chronological_rolling_replay("POLICY_E_CHALLENGE_AWARE", 0.75)
    assert not df_res.empty
    assert df_res["is_breached"].sum() == 0

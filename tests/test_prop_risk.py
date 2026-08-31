"""
Unit tests for PropFirmRiskEngine and MonteCarloPropSimulator.
"""
import pytest
import pandas as pd
import numpy as np

from src.risk_engine.prop_firm_risk import PropFirmConfig, PropFirmRiskEngine, RiskDecision
from src.risk_engine.monte_carlo_simulator import MonteCarloPropSimulator
from src.strategy_engine.strategies import TradeSignal


def test_prop_risk_engine_daily_loss_firewall():
    cfg = PropFirmConfig(initial_balance_usd=100000.0, daily_loss_limit_pct=5.0, max_drawdown_pct=10.0)
    engine = PropFirmRiskEngine(cfg)

    # Initialize day at 100k equity
    engine.update_account_state(pd.Timestamp("2026-01-15 00:00", tz="UTC"), 100000.0, 100000.0)
    # Day progresses, equity drops to $95,100 (near $95,000 floor)
    engine.equity = 95100.0
    engine.balance = 95100.0

    sig = TradeSignal(
        timestamp=pd.Timestamp("2026-01-15 10:15", tz="UTC"),
        symbol="EURUSD",
        direction=1,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        max_holding_bars=32,
        strategy_name="FROZEN",
        regime="RANGE_TO_TREND",
        risk_pips=50.0,
        target_pips=100.0,
    )

    # Proposed risk of 0.50% ($475.50) exceeds remaining daily budget ($100)
    dec = engine.evaluate_proposed_trade(sig, pd.Timestamp("2026-01-15 10:15", tz="UTC"), proposed_risk_pct=0.50, current_spread_pips=0.8)
    assert not dec.is_approved
    assert "DAILY_LOSS_FIREWALL" in dec.rejection_reason


def test_monte_carlo_simulator_basic():
    returns = np.array([1.5, -1.0, 2.0, -1.0, 1.8, -1.0])
    sim = MonteCarloPropSimulator(historical_r_returns=returns, trades_per_month=3.0, n_simulations=100, random_seed=42)
    res = sim.simulate_all_risk_levels([0.25, 0.50])
    assert len(res) == 2
    assert res[0].prob_survive_90d_pct >= 90.0

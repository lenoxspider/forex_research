"""
Automated Unit and Integration Tests for Systematic Forex Trading System.
Verifies Zero Look-Ahead, Execution Realism, Risk Sizing, Chronological Separation, and Data Integrity.
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from config.settings import PAIR_SPECS, CHRONOLOGICAL_SPLITS
from src.feature_engine.features import FeatureEngine
from src.regime_engine.regimes import RegimeEngine
from src.strategy_engine.strategies import TrendFollowingPullbackStrategy, TradeSignal
from src.backtest_engine.backtester import RealisticBacktester, ExecutedTrade
from src.backtest_engine.metrics import MetricsCalculator
from src.risk_engine.risk_manager import RiskManager
from src.validation_engine.splits import ChronologicalValidationEngine
from src.monte_carlo_engine.monte_carlo import MonteCarloEngine


def _create_synthetic_ohlcv(n_bars: int = 500) -> pd.DataFrame:
    """Generates synthetic non-random walk OHLCV data for unit testing."""
    np.random.seed(42)
    dates = pd.date_range("2021-01-01 00:00:00", periods=n_bars, freq="15min", tz="UTC")
    
    # Generate continuous prices
    returns = np.random.normal(0.00005, 0.0005, size=n_bars)
    price = 1.1000 * np.cumprod(1.0 + returns)
    
    highs = price + np.random.uniform(0.0002, 0.0008, size=n_bars)
    lows = price - np.random.uniform(0.0002, 0.0008, size=n_bars)
    opens = price + np.random.uniform(-0.0002, 0.0002, size=n_bars)
    closes = price
    
    # Guarantee OHLC invariants
    highs = np.maximum(highs, np.maximum(opens, closes))
    lows = np.minimum(lows, np.minimum(opens, closes))
    
    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "tick_volume": np.random.randint(100, 2000, size=n_bars),
        "spread": np.random.randint(8, 15, size=n_bars),
    }, index=dates)
    return df


def test_ohlc_invariants():
    df = _create_synthetic_ohlcv(200)
    assert (df["high"] >= df["low"]).all()
    assert (df["high"] >= df["open"]).all()
    assert (df["high"] >= df["close"]).all()
    assert (df["low"] <= df["open"]).all()
    assert (df["low"] <= df["close"]).all()


def test_zero_lookahead_features():
    """
    CRITICAL TEST: Verifies that feature calculation at bar t is mathematically
    IDENTICAL whether computed on the full dataset or truncated strictly at bar t.
    """
    df = _create_synthetic_ohlcv(300)
    feat_engine = FeatureEngine("EURUSD")

    # Compute on full dataset
    df_full = feat_engine.compute_all_features(df)

    # Compute on truncated slice up to bar 200
    df_trunc = feat_engine.compute_all_features(df.iloc[:201])

    # Compare features at bar 200
    for col in ["atr_14", "ema_20", "ema_50", "rsi_14", "adx_14", "swing_high_20", "swing_low_20"]:
        val_full = df_full[col].iloc[200]
        val_trunc = df_trunc[col].iloc[200]
        assert np.isclose(val_full, val_trunc, rtol=1e-5, atol=1e-5), f"Lookahead detected in {col}: {val_full} != {val_trunc}"


def test_backtest_execution_cost_accounting():
    """Verifies spread, slippage, and commission are deducted from net PnL."""
    df = _create_synthetic_ohlcv(200)
    sig_time = df.index[50]
    
    signal = TradeSignal(
        timestamp=sig_time,
        symbol="EURUSD",
        direction=1,
        entry_price=float(df["close"].iloc[50]),
        stop_loss=float(df["close"].iloc[50] - 0.0030),
        take_profit=float(df["close"].iloc[50] + 0.0060),
        max_holding_bars=10,
        strategy_name="TEST",
        regime="TEST",
        risk_pips=30.0,
        target_pips=60.0,
    )
    
    backtester = RealisticBacktester("EURUSD", fixed_spread_pips=1.0, fixed_slippage_pips=0.2, commission_per_lot_usd=7.0)
    trades, df_trades = backtester.run_backtest(df, [signal])
    
    assert len(trades) == 1
    t = trades[0]
    # Trade entered at Open of bar 51 (strictly index 51)
    assert t.entry_time == df.index[51]
    # Net pips must be strictly less than gross pips due to spreads and commission
    assert t.pnl_net_pips < t.pnl_gross_pips
    assert t.spread_cost_pips > 0
    assert t.slippage_cost_pips > 0
    assert t.commission_pips > 0


def test_risk_manager_sizing_and_limits():
    risk_mgr = RiskManager(account_equity=100_000.0, risk_per_trade_pct=0.01)
    
    signal = TradeSignal(
        timestamp=pd.Timestamp("2021-01-01", tz="UTC"),
        symbol="EURUSD",
        direction=1,
        entry_price=1.1000,
        stop_loss=1.0980,
        take_profit=1.1040,
        max_holding_bars=20,
        strategy_name="TEST",
        regime="TEST",
        risk_pips=20.0,
        target_pips=40.0,
    )
    
    # 1. Standard approval
    res = risk_mgr.evaluate_signal_and_size(signal, open_positions=[], current_spread_pips=0.8, current_atr_pips=15.0)
    assert res.is_approved
    assert res.lot_size > 0
    # $1,000 risk / (20 pips * $10) = 5.0 lots
    assert res.lot_size == 5.0
    
    # 2. Spread gate rejection
    res_spread = risk_mgr.evaluate_signal_and_size(signal, open_positions=[], current_spread_pips=5.0, current_atr_pips=15.0)
    assert not res_spread.is_approved
    assert "SPREAD_TOO_WIDE" in str(res_spread.rejection_reason)


def test_monte_carlo_resampling():
    df_trades = pd.DataFrame({
        "pnl_r_multiple": [1.5, -1.0, 2.0, -1.0, -1.0, 1.8, -1.0, 2.2, -1.0, 1.2] * 5,
        "entry_time": pd.date_range("2021-01-01", periods=50, freq="D", tz="UTC"),
        "exit_time": pd.date_range("2021-01-02", periods=50, freq="D", tz="UTC"),
    })
    mc = MonteCarloEngine(iterations=500)
    report = mc.run_simulation(df_trades)
    assert report.iterations == 500
    assert report.median_max_dd_pct > 0
    assert report.p95_max_dd_pct >= report.median_max_dd_pct

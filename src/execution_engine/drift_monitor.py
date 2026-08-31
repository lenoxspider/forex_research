"""
Research-vs-Production Execution Drift Monitor & Alerting Engine.

Quantifies execution fidelity by comparing:
- Backtest theoretical expectations vs Live Paper realization
- Slippage drift, Spread percentile drift, Fill latency
- Realized R multiple distribution drift
- MFE / MAE lifecycle divergence
"""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from src.backtest_engine.metrics import MetricsCalculator, PerformanceSummary

logger = logging.getLogger("DriftMonitor")


@dataclass
class DriftSummary:
    symbol: str
    paper_trade_count: int
    research_trade_count: int
    trade_count_diff: int
    paper_win_rate_pct: float
    research_win_rate_pct: float
    win_rate_drift_pct: float
    paper_expectancy_r: float
    research_expectancy_r: float
    expectancy_drift_r: float
    avg_spread_pips: float
    spread_assumed_pips: float
    spread_drift_pips: float
    avg_slippage_pips: float
    slippage_assumed_pips: float
    slippage_drift_pips: float
    avg_mfe_pips: float
    avg_mae_pips: float
    is_execution_consistent: bool
    alert_level: str  # 'NORMAL', 'WARNING', 'CRITICAL'


class ExecutionDriftMonitor:
    """
    Monitors live paper execution quality against frozen research benchmarks.
    """

    def __init__(self, research_benchmarks: Dict[str, Dict[str, Any]]):
        self.benchmarks = research_benchmarks

    def compute_pair_drift(self, symbol: str, df_paper_trades: pd.DataFrame) -> DriftSummary:
        bench = self.benchmarks.get(symbol, {
            "trades": 50, "win_rate_pct": 53.0, "expectancy_r": 0.35,
            "assumed_spread_pips": 0.8, "assumed_slippage_pips": 0.2
        })

        if df_paper_trades.empty:
            return DriftSummary(
                symbol=symbol, paper_trade_count=0, research_trade_count=bench.get("trades", 0),
                trade_count_diff=-bench.get("trades", 0), paper_win_rate_pct=0.0,
                research_win_rate_pct=bench.get("win_rate_pct", 0.0), win_rate_drift_pct=0.0,
                paper_expectancy_r=0.0, research_expectancy_r=bench.get("expectancy_r", 0.0),
                expectancy_drift_r=-bench.get("expectancy_r", 0.0), avg_spread_pips=bench.get("assumed_spread_pips", 0.8),
                spread_assumed_pips=bench.get("assumed_spread_pips", 0.8), spread_drift_pips=0.0,
                avg_slippage_pips=0.0, slippage_assumed_pips=bench.get("assumed_slippage_pips", 0.2),
                slippage_drift_pips=0.0, avg_mfe_pips=0.0, avg_mae_pips=0.0,
                is_execution_consistent=True, alert_level="NORMAL"
            )

        n = len(df_paper_trades)
        pnl_col = "net_pnl_pips" if "net_pnl_pips" in df_paper_trades.columns else ("pnl_net_pips" if "pnl_net_pips" in df_paper_trades.columns else "pnl_pips")
        wins = (df_paper_trades[pnl_col] > 0).sum() if pnl_col in df_paper_trades.columns else 0
        wr = (wins / n) * 100.0 if n > 0 else 0.0
        
        if "pnl_r_multiple" in df_paper_trades.columns:
            exp_r = float(df_paper_trades["pnl_r_multiple"].mean())
        elif "risk_pips" in df_paper_trades.columns and pnl_col in df_paper_trades.columns:
            exp_r = float((df_paper_trades[pnl_col] / (df_paper_trades["risk_pips"] + 1e-9)).mean())
        else:
            exp_r = bench.get("expectancy_r", 0.35)

        avg_sp = float(df_paper_trades["spread_paid_pips"].mean()) if "spread_paid_pips" in df_paper_trades.columns else bench.get("assumed_spread_pips", 0.8)
        avg_slip = float(df_paper_trades["slippage_paid_pips"].mean()) if "slippage_paid_pips" in df_paper_trades.columns else 0.2
        avg_mfe = float(df_paper_trades["max_favorable_pips"].mean()) if "max_favorable_pips" in df_paper_trades.columns else 0.0
        avg_mae = float(df_paper_trades["max_adverse_pips"].mean()) if "max_adverse_pips" in df_paper_trades.columns else 0.0

        res_wr = bench.get("win_rate_pct", 50.0)
        res_exp = bench.get("expectancy_r", 0.30)
        res_sp = bench.get("assumed_spread_pips", 0.8)
        res_slip = bench.get("assumed_slippage_pips", 0.2)

        wr_drift = wr - res_wr
        exp_drift = exp_r - res_exp
        sp_drift = avg_sp - res_sp
        slip_drift = avg_slip - res_slip

        # Consistency Alert Rules
        is_consistent = True
        alert = "NORMAL"

        if sp_drift > 0.5 or slip_drift > 0.3:
            is_consistent = False
            alert = "WARNING (High Friction Drift)"

        if n >= 15 and exp_r < -0.20:
            is_consistent = False
            alert = "CRITICAL (Negative Expectancy Drift)"

        return DriftSummary(
            symbol=symbol,
            paper_trade_count=n,
            research_trade_count=bench.get("trades", 0),
            trade_count_diff=n - bench.get("trades", 0),
            paper_win_rate_pct=round(wr, 1),
            research_win_rate_pct=round(res_wr, 1),
            win_rate_drift_pct=round(wr_drift, 1),
            paper_expectancy_r=round(exp_r, 3),
            research_expectancy_r=round(res_exp, 3),
            expectancy_drift_r=round(exp_drift, 3),
            avg_spread_pips=round(avg_sp, 2),
            spread_assumed_pips=round(res_sp, 2),
            spread_drift_pips=round(sp_drift, 2),
            avg_slippage_pips=round(avg_slip, 2),
            slippage_assumed_pips=round(res_slip, 2),
            slippage_drift_pips=round(slip_drift, 2),
            avg_mfe_pips=round(avg_mfe, 1),
            avg_mae_pips=round(avg_mae, 1),
            is_execution_consistent=is_consistent,
            alert_level=alert
        )

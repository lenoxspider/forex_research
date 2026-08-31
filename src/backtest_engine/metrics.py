"""
Performance Metrics & Statistical Breakdown Engine.
Calculates expectancy in R, profit factor, max drawdown duration, Sharpe, Sortino, Calmar,
losing streaks, and multi-dimensional breakdowns (by Year, Regime, Session, Direction).
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd


@dataclass
class PerformanceSummary:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    gross_profit_pips: float
    gross_loss_pips: float
    net_profit_pips: float
    profit_factor: float
    expectancy_pips: float
    expectancy_r: float
    avg_win_pips: float
    avg_loss_pips: float
    avg_rr_ratio: float
    max_drawdown_pips: float
    max_drawdown_pct: float
    max_drawdown_duration_trades: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_losing_streak: int
    avg_holding_bars: float
    total_costs_paid_pips: float
    annual_return_pct: float


class MetricsCalculator:
    """Computes comprehensive institutional performance statistics on trade lists."""

    @staticmethod
    def calculate_summary(
        trades_df: pd.DataFrame,
        initial_capital: float = 100_000.0,
        risk_per_trade_pct: float = 0.01,
    ) -> PerformanceSummary:
        if trades_df.empty or len(trades_df) == 0:
            return PerformanceSummary(
                total_trades=0, winning_trades=0, losing_trades=0, win_rate_pct=0.0,
                gross_profit_pips=0.0, gross_loss_pips=0.0, net_profit_pips=0.0,
                profit_factor=0.0, expectancy_pips=0.0, expectancy_r=0.0,
                avg_win_pips=0.0, avg_loss_pips=0.0, avg_rr_ratio=0.0,
                max_drawdown_pips=0.0, max_drawdown_pct=0.0, max_drawdown_duration_trades=0,
                sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0,
                max_losing_streak=0, avg_holding_bars=0.0, total_costs_paid_pips=0.0,
                annual_return_pct=0.0,
            )

        n = len(trades_df)
        net_pips = trades_df["pnl_net_pips"].values
        r_mults = trades_df["pnl_r_multiple"].values
        holding_bars = trades_df["holding_bars"].values if "holding_bars" in trades_df.columns else np.zeros(n)

        wins = net_pips[net_pips > 0]
        losses = net_pips[net_pips <= 0]

        n_wins = len(wins)
        n_losses = len(losses)
        win_rate = (n_wins / n) * 100.0

        gross_profit = float(np.sum(wins)) if n_wins > 0 else 0.0
        gross_loss = float(np.abs(np.sum(losses))) if n_losses > 0 else 0.0
        net_profit = float(np.sum(net_pips))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        expectancy_pips = float(np.mean(net_pips))
        expectancy_r = float(np.mean(r_mults))
        avg_win = float(np.mean(wins)) if n_wins > 0 else 0.0
        avg_loss = float(np.abs(np.mean(losses))) if n_losses > 0 else 0.0
        avg_rr = (avg_win / avg_loss) if avg_loss > 0 else 0.0

        # Equity Curve in % (Compounded fixed-fractional R)
        trade_returns_pct = r_mults * risk_per_trade_pct
        equity_curve = np.cumprod(1.0 + trade_returns_pct)
        running_max = np.maximum.accumulate(equity_curve)
        drawdowns = (equity_curve - running_max) / running_max
        max_dd_pct = float(np.abs(np.min(drawdowns))) * 100.0 if len(drawdowns) > 0 else 0.0

        # Pip Drawdown
        cum_pips = np.cumsum(net_pips)
        running_max_pips = np.maximum.accumulate(cum_pips)
        pip_dd = running_max_pips - cum_pips
        max_dd_pips = float(np.max(pip_dd)) if len(pip_dd) > 0 else 0.0

        # Drawdown Duration (in trades)
        dd_dur = 0
        max_dd_dur = 0
        for dd in pip_dd:
            if dd > 0:
                dd_dur += 1
                max_dd_dur = max(max_dd_dur, dd_dur)
            else:
                dd_dur = 0

        # Losing Streak
        curr_streak = 0
        max_streak = 0
        for p in net_pips:
            if p <= 0:
                curr_streak += 1
                max_streak = max(max_streak, curr_streak)
            else:
                curr_streak = 0

        # R-Multiple Sharpe & Sortino (assuming ~200 trades/year)
        r_std = np.std(r_mults)
        neg_r_std = np.std(r_mults[r_mults < 0]) if (r_mults < 0).any() else 1e-9
        ann_factor = np.sqrt(max(len(r_mults), 1))
        sharpe = (expectancy_r / (r_std + 1e-9)) * np.sqrt(50)  # normalized ~50-100 trades scale
        sortino = (expectancy_r / (neg_r_std + 1e-9)) * np.sqrt(50)

        # Annualized return estimate
        if "exit_time" in trades_df.columns and "entry_time" in trades_df.columns and len(trades_df) > 0:
            total_days = (pd.to_datetime(trades_df["exit_time"].iloc[-1]) - pd.to_datetime(trades_df["entry_time"].iloc[0])).days
        else:
            total_days = 365
        years = max(total_days / 365.25, 0.1)
        total_compounded_return = (equity_curve[-1] - 1.0)
        cagr = ((1.0 + total_compounded_return) ** (1.0 / years) - 1.0) * 100.0 if total_compounded_return > -1.0 else -99.0
        calmar = (cagr / max_dd_pct) if max_dd_pct > 0 else 0.0

        total_costs = 0.0
        for col in ["spread_cost_pips", "entry_spread_pips", "slippage_cost_pips", "commission_pips"]:
            if col in trades_df.columns:
                total_costs += float(trades_df[col].sum())

        return PerformanceSummary(
            total_trades=n,
            winning_trades=n_wins,
            losing_trades=n_losses,
            win_rate_pct=round(win_rate, 2),
            gross_profit_pips=round(gross_profit, 2),
            gross_loss_pips=round(gross_loss, 2),
            net_profit_pips=round(net_profit, 2),
            profit_factor=round(profit_factor, 2),
            expectancy_pips=round(expectancy_pips, 2),
            expectancy_r=round(expectancy_r, 3),
            avg_win_pips=round(avg_win, 2),
            avg_loss_pips=round(avg_loss, 2),
            avg_rr_ratio=round(avg_rr, 2),
            max_drawdown_pips=round(max_dd_pips, 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            max_drawdown_duration_trades=max_dd_dur,
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            calmar_ratio=round(calmar, 2),
            max_losing_streak=max_streak,
            avg_holding_bars=round(float(np.mean(holding_bars)), 1),
            total_costs_paid_pips=round(total_costs, 2),
            annual_return_pct=round(cagr, 2),
        )

    @staticmethod
    def breakdown_by(trades_df: pd.DataFrame, group_col: str) -> pd.DataFrame:
        """Groups trades and computes win rate, expectancy, and profit factor per slice."""
        if trades_df.empty or group_col not in trades_df.columns:
            return pd.DataFrame()

        rows = []
        for name, group in trades_df.groupby(group_col):
            summary = MetricsCalculator.calculate_summary(group)
            rows.append({
                group_col: name,
                "Trades": summary.total_trades,
                "WinRate%": summary.win_rate_pct,
                "Exp(R)": summary.expectancy_r,
                "NetPips": summary.net_profit_pips,
                "ProfitFactor": summary.profit_factor,
                "MaxDD%": summary.max_drawdown_pct,
            })
        return pd.DataFrame(rows).sort_values("Trades", ascending=False)

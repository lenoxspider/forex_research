"""
Cross-Pair Diversification & Correlation Engine.
Evaluates strategy return correlation across EURUSD, GBPUSD, and USDJPY
and determines whether the basket genuinely provides diversification vs redundant USD risk.
"""
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from src.strategy_engine.strategies import BaseStrategy
from src.backtest_engine.backtester import RealisticBacktester, ExecutedTrade
from src.backtest_engine.metrics import MetricsCalculator, PerformanceSummary


class CrossPairAnalyzer:
    """Measures correlation of returns and equity curves across EURUSD, GBPUSD, and USDJPY."""

    @staticmethod
    def compute_daily_returns_matrix(
        pair_trades_dict: Dict[str, pd.DataFrame],
        date_range_index: pd.DatetimeIndex,
    ) -> pd.DataFrame:
        """Constructs aligned daily PnL (in R-multiples or pips) for each pair."""
        daily_df = pd.DataFrame(index=pd.date_range(date_range_index.min().date(), date_range_index.max().date(), freq="D", tz="UTC"))

        for pair, trades_df in pair_trades_dict.items():
            if trades_df.empty:
                daily_df[pair] = 0.0
                continue

            trades_copy = trades_df.copy()
            trades_copy["exit_date"] = pd.to_datetime(trades_copy["exit_time"]).dt.tz_convert("UTC").dt.date
            daily_r = trades_copy.groupby("exit_date")["pnl_r_multiple"].sum()
            daily_r.index = pd.to_datetime(daily_r.index, utc=True)
            daily_df[pair] = daily_r

        daily_df = daily_df.fillna(0.0)
        return daily_df

    @staticmethod
    def calculate_correlation_matrix(daily_returns_matrix: pd.DataFrame) -> pd.DataFrame:
        """Returns pairwise Pearson correlation matrix of daily strategy returns."""
        return daily_returns_matrix.corr()

    @staticmethod
    def calculate_portfolio_combined_metrics(
        pair_trades_dict: Dict[str, pd.DataFrame],
    ) -> Tuple[PerformanceSummary, pd.DataFrame]:
        """Merges all trades across all pairs into one combined chronological portfolio."""
        all_dfs = []
        for pair, df in pair_trades_dict.items():
            if not df.empty:
                all_dfs.append(df)

        if not all_dfs:
            return MetricsCalculator.calculate_summary(pd.DataFrame()), pd.DataFrame()

        merged_trades = pd.concat(all_dfs, ignore_index=True)
        merged_trades = merged_trades.sort_values("entry_time").reset_index(drop=True)
        portfolio_summary = MetricsCalculator.calculate_summary(merged_trades)
        return portfolio_summary, merged_trades

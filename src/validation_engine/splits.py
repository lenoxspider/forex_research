"""
Chronological Splitter & Rolling Walk-Forward Optimization (WFO) Engine.
Enforces strict chronological separation with zero train/test leakage.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd

from config.settings import CHRONOLOGICAL_SPLITS, DateSplit
from src.strategy_engine.strategies import BaseStrategy, TradeSignal
from src.backtest_engine.backtester import RealisticBacktester
from src.backtest_engine.metrics import MetricsCalculator, PerformanceSummary


@dataclass
class WFOResult:
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    is_trades: int
    is_expectancy_r: float
    is_profit_factor: float
    oos_trades: int
    oos_expectancy_r: float
    oos_profit_factor: float
    wfe_ratio: float  # Walk-Forward Efficiency (OOS Exp / IS Exp)


class ChronologicalValidationEngine:
    """Manages multi-period fixed OOS splits and rolling walk-forward evaluation."""

    def __init__(self, symbol: str):
        self.symbol = symbol

    def split_dataset(
        self, df: pd.DataFrame, splits: List[DateSplit] = CHRONOLOGICAL_SPLITS
    ) -> Dict[str, pd.DataFrame]:
        """Slices dataframe into distinct chronological periods."""
        split_dfs = {}
        for sp in splits:
            mask = (df.index >= pd.Timestamp(sp.start_date, tz="UTC")) & (
                df.index <= pd.Timestamp(sp.end_date + " 23:59:59", tz="UTC")
            )
            split_dfs[sp.name] = df[mask].copy()
        return split_dfs

    def run_multi_period_oos(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
        splits: List[DateSplit] = CHRONOLOGICAL_SPLITS,
    ) -> Dict[str, Tuple[PerformanceSummary, pd.DataFrame]]:
        """
        Runs the strategy independently across all chronological splits.
        """
        backtester = RealisticBacktester(self.symbol)
        results = {}

        split_dict = self.split_dataset(df, splits)
        for split_name, split_df in split_dict.items():
            if len(split_df) < 100:
                continue
            signals = strategy.generate_signals(split_df)
            _, trades_df = backtester.run_backtest(split_df, signals)
            summary = MetricsCalculator.calculate_summary(trades_df)
            results[split_name] = (summary, trades_df)

        return results

    def run_rolling_walk_forward(
        self,
        strategy_class,
        df: pd.DataFrame,
        train_years: int = 3,
        test_years: int = 1,
        step_years: int = 1,
    ) -> List[WFOResult]:
        """
        Executes rolling walk-forward test (e.g., Train: 2010-2012, Test: 2013 -> Train: 2011-2013, Test: 2014).
        """
        if len(df) == 0:
            return []

        years = sorted(df.index.year.unique())
        if len(years) < (train_years + test_years):
            return []

        wfo_results = []
        backtester = RealisticBacktester(self.symbol)

        for i in range(0, len(years) - train_years - test_years + 1, step_years):
            train_yr_start = years[i]
            train_yr_end = years[i + train_years - 1]
            test_yr_start = years[i + train_years]
            test_yr_end = years[i + train_years + test_years - 1]

            train_mask = (df.index.year >= train_yr_start) & (df.index.year <= train_yr_end)
            test_mask = (df.index.year >= test_yr_start) & (df.index.year <= test_yr_end)

            df_train = df[train_mask]
            df_test = df[test_mask]

            # In-sample
            strat_is = strategy_class(self.symbol)
            signals_is = strat_is.generate_signals(df_train)
            _, is_trades_df = backtester.run_backtest(df_train, signals_is)
            is_summary = MetricsCalculator.calculate_summary(is_trades_df)

            # Out-of-sample
            strat_oos = strategy_class(self.symbol)
            signals_oos = strat_oos.generate_signals(df_test)
            _, oos_trades_df = backtester.run_backtest(df_test, signals_oos)
            oos_summary = MetricsCalculator.calculate_summary(oos_trades_df)

            # Walk Forward Efficiency ratio
            wfe = (oos_summary.expectancy_r / (is_summary.expectancy_r + 1e-9)) if is_summary.expectancy_r > 0 else 0.0

            wfo_results.append(
                WFOResult(
                    train_start=str(train_yr_start),
                    train_end=str(train_yr_end),
                    test_start=str(test_yr_start),
                    test_end=str(test_yr_end),
                    is_trades=is_summary.total_trades,
                    is_expectancy_r=is_summary.expectancy_r,
                    is_profit_factor=is_summary.profit_factor,
                    oos_trades=oos_summary.total_trades,
                    oos_expectancy_r=oos_summary.expectancy_r,
                    oos_profit_factor=oos_summary.profit_factor,
                    wfe_ratio=round(wfe, 2),
                )
            )

        return wfo_results

"""
Robustness & Parameter Perturbation Engine.
Tests parameter stability across neighbor spaces and subjects strategies to +25%, +50%, +100% cost stress tests.
"""
from dataclasses import dataclass
from typing import Dict, List, Any
import numpy as np
import pandas as pd

from src.strategy_engine.strategies import BaseStrategy
from src.backtest_engine.backtester import RealisticBacktester
from src.backtest_engine.metrics import MetricsCalculator, PerformanceSummary


@dataclass
class CostStressResult:
    cost_multiplier_label: str
    cost_multiplier: float
    trades: int
    expectancy_pips: float
    expectancy_r: float
    profit_factor: float
    net_profit_pips: float
    max_drawdown_pct: float
    is_profitable: bool


class RobustnessEngine:
    """Evaluates parameter plateau stability and transaction cost fragility."""

    def __init__(self, symbol: str):
        self.symbol = symbol

    def run_cost_stress_test(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
    ) -> List[CostStressResult]:
        """
        Evaluates performance under Baseline, +25%, +50%, and +100% transaction costs.
        """
        stress_levels = [
            ("Baseline (1.0x)", 1.0),
            ("+25% Costs (1.25x)", 1.25),
            ("+50% Costs (1.50x)", 1.50),
            ("+100% Costs (2.00x)", 2.00),
        ]

        results = []
        signals = strategy.generate_signals(df)

        for label, mult in stress_levels:
            backtester = RealisticBacktester(self.symbol, cost_multiplier=mult)
            _, trades_df = backtester.run_backtest(df, signals)
            summary = MetricsCalculator.calculate_summary(trades_df)

            results.append(
                CostStressResult(
                    cost_multiplier_label=label,
                    cost_multiplier=mult,
                    trades=summary.total_trades,
                    expectancy_pips=summary.expectancy_pips,
                    expectancy_r=summary.expectancy_r,
                    profit_factor=summary.profit_factor,
                    net_profit_pips=summary.net_profit_pips,
                    max_drawdown_pct=summary.max_drawdown_pct,
                    is_profitable=(summary.expectancy_r > 0 and summary.profit_factor > 1.0),
                )
            )

        return results

    def run_parameter_perturbations(
        self,
        strategy_class,
        df: pd.DataFrame,
        base_params: Dict[str, Any],
        param_grid: Dict[str, List[Any]],
    ) -> pd.DataFrame:
        """
        Perturbs parameters independently across neighborhood ranges to verify plateau consistency.
        """
        backtester = RealisticBacktester(self.symbol)
        rows = []

        for param_name, values in param_grid.items():
            for val in values:
                test_params = dict(base_params)
                test_params[param_name] = val
                strat = strategy_class(self.symbol, params=test_params)
                signals = strat.generate_signals(df)
                _, trades_df = backtester.run_backtest(df, signals)
                summary = MetricsCalculator.calculate_summary(trades_df)

                rows.append({
                    "PerturbedParam": param_name,
                    "Value": val,
                    "Trades": summary.total_trades,
                    "WinRate%": summary.win_rate_pct,
                    "Exp(R)": summary.expectancy_r,
                    "NetPips": summary.net_profit_pips,
                    "ProfitFactor": summary.profit_factor,
                    "MaxDD%": summary.max_drawdown_pct,
                })

        return pd.DataFrame(rows)

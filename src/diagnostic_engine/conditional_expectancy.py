"""
Conditional Expectancy & Factor Stability Engine.
Computes multi-dimensional trade expectancy across ATR percentiles, ADX, Trend States,
Sessions, Days of Week, Spread Buckets, and Higher-Timeframe Alignments.
Evaluates inter-temporal stability across calendar years (2023, 2024, 2025, 2026).
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from src.backtest_engine.metrics import MetricsCalculator, PerformanceSummary


@dataclass
class BucketMetric:
    factor_name: str
    bucket_value: str
    sample_size: int
    win_rate_pct: float
    expectancy_r: float
    profit_factor: float
    avg_win_r: float
    avg_loss_r: float
    max_drawdown_pct: float
    is_statistically_valid: bool  # True if sample >= min_sample
    yearly_consistency_score: float  # % of active years with Exp(R) > 0
    yearly_exp_r_map: Dict[int, float]


class ConditionalExpectancyAnalyzer:
    """Evaluates conditional performance profiles across all candidate factors."""

    FACTORS = [
        "atr_bucket",
        "adx_bucket",
        "trend_regime",
        "vol_regime",
        "combined_regime",
        "session",
        "day_of_week",
        "spread_bucket",
        "htf_alignment",
        "direction_label",
    ]

    def __init__(self, min_sample_size: int = 25):
        self.min_sample = min_sample_size

    def analyze_factors(self, df_trades: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Groups trades across all factors and computes conditional statistics and yearly consistency.
        """
        if df_trades.empty or len(df_trades) < self.min_sample:
            return {}

        results = {}
        all_years = sorted(df_trades["year"].unique())

        for factor in self.FACTORS:
            if factor not in df_trades.columns:
                continue

            rows = []
            for val, group in df_trades.groupby(factor, observed=False):
                n_trades = len(group)
                summary = MetricsCalculator.calculate_summary(group)

                # Compute yearly consistency
                yearly_exp = {}
                positive_years = 0
                active_years = 0
                for yr in all_years:
                    yr_group = group[group["year"] == yr]
                    if len(yr_group) >= 5:
                        yr_summary = MetricsCalculator.calculate_summary(yr_group)
                        yearly_exp[yr] = yr_summary.expectancy_r
                        active_years += 1
                        if yr_summary.expectancy_r > 0:
                            positive_years += 1
                    else:
                        yearly_exp[yr] = None

                consistency_score = (positive_years / max(1, active_years)) * 100.0 if active_years > 0 else 0.0

                rows.append({
                    "Factor": factor,
                    "Bucket": str(val),
                    "Trades": n_trades,
                    "WinRate%": summary.win_rate_pct,
                    "Exp(R)": summary.expectancy_r,
                    "PF": summary.profit_factor,
                    "AvgWin(R)": summary.avg_rr_ratio,
                    "MaxDD%": summary.max_drawdown_pct,
                    "Stable_Years%": round(consistency_score, 1),
                    "Valid_Sample": (n_trades >= self.min_sample),
                    "Yearly_Exp_R": yearly_exp,
                })

            df_factor = pd.DataFrame(rows).sort_values("Exp(R)", ascending=False).reset_index(drop=True)
            results[factor] = df_factor

        return results

    def identify_promising_conditions(self, factor_results: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """
        Identifies positive-expectancy conditions that meet sample thresholds and cross-year consistency.
        """
        promising = []
        for factor, df_f in factor_results.items():
            valid_df = df_f[df_f["Valid_Sample"] == True]
            for _, row in valid_df.iterrows():
                if row["Exp(R)"] > 0.04 and row["PF"] >= 1.10 and row["Stable_Years%"] >= 50.0:
                    promising.append({
                        "Factor": factor,
                        "Condition": row["Bucket"],
                        "Trades": row["Trades"],
                        "WinRate%": row["WinRate%"],
                        "Exp(R)": row["Exp(R)"],
                        "PF": row["PF"],
                        "Stable_Years%": row["Stable_Years%"],
                        "Yearly_Breakdown": row["Yearly_Exp_R"],
                    })
        return sorted(promising, key=lambda x: x["Exp(R)"], reverse=True)

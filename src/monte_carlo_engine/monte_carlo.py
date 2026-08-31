"""
Monte Carlo Robustness & Risk of Ruin Engine.
Performs bootstrap resampling of trade sequences to calculate realistic drawdown percentiles,
losing streak distributions, and risk of ruin across risk fractions.
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Any
import numpy as np
import pandas as pd


@dataclass
class MonteCarloReport:
    iterations: int
    trades_sample_size: int
    median_max_dd_pct: float
    p90_max_dd_pct: float
    p95_max_dd_pct: float
    p99_max_dd_pct: float
    prob_losing_streak_ge_6: float
    prob_losing_streak_ge_8: float
    prob_losing_streak_ge_10: float
    prob_negative_year: float
    ruin_prob_0_5pct_risk: float
    ruin_prob_1_0pct_risk: float
    ruin_prob_2_0pct_risk: float
    recommended_risk_per_trade_pct: float


class MonteCarloEngine:
    """Simulates thousands of alternative trade order paths via bootstrap resampling."""

    def __init__(self, iterations: int = 2500, random_seed: int = 42):
        self.iterations = iterations
        self.random_seed = random_seed

    def run_simulation(
        self,
        trades_df: pd.DataFrame,
        ruin_dd_threshold_pct: float = 25.0,
    ) -> MonteCarloReport:
        if trades_df.empty or len(trades_df) < 20:
            return MonteCarloReport(
                iterations=0, trades_sample_size=0,
                median_max_dd_pct=0.0, p90_max_dd_pct=0.0, p95_max_dd_pct=0.0, p99_max_dd_pct=0.0,
                prob_losing_streak_ge_6=0.0, prob_losing_streak_ge_8=0.0, prob_losing_streak_ge_10=0.0,
                prob_negative_year=0.0, ruin_prob_0_5pct_risk=0.0, ruin_prob_1_0pct_risk=0.0,
                ruin_prob_2_0pct_risk=0.0, recommended_risk_per_trade_pct=1.0,
            )

        np.random.seed(self.random_seed)
        r_mults = trades_df["pnl_r_multiple"].values
        n_trades = len(r_mults)

        # Preallocate simulation matrices
        max_dds_1pct = []
        max_dds_05pct = []
        max_dds_2pct = []
        losing_streaks = []
        negative_years_count = 0

        trades_per_year = max(int(n_trades / max(1.0, (pd.to_datetime(trades_df['exit_time'].iloc[-1]) - pd.to_datetime(trades_df['entry_time'].iloc[0])).days / 365.25)), 20)

        for _ in range(self.iterations):
            # Sample with replacement
            sampled_r = np.random.choice(r_mults, size=n_trades, replace=True)

            # Max streak
            streak = 0
            max_s = 0
            for r in sampled_r:
                if r <= 0:
                    streak += 1
                    max_s = max(max_s, streak)
                else:
                    streak = 0
            losing_streaks.append(max_s)

            # Drawdown for 1.0% risk
            eq_1 = np.cumprod(1.0 + sampled_r * 0.01)
            dd_1 = (eq_1 - np.maximum.accumulate(eq_1)) / np.maximum.accumulate(eq_1)
            max_dds_1pct.append(np.abs(np.min(dd_1)) * 100.0)

            # Drawdown for 0.5% risk
            eq_05 = np.cumprod(1.0 + sampled_r * 0.005)
            dd_05 = (eq_05 - np.maximum.accumulate(eq_05)) / np.maximum.accumulate(eq_05)
            max_dds_05pct.append(np.abs(np.min(dd_05)) * 100.0)

            # Drawdown for 2.0% risk
            eq_2 = np.cumprod(1.0 + sampled_r * 0.02)
            dd_2 = (eq_2 - np.maximum.accumulate(eq_2)) / np.maximum.accumulate(eq_2)
            max_dds_2pct.append(np.abs(np.min(dd_2)) * 100.0)

            # 1-year sample performance
            sample_1yr_r = sampled_r[:trades_per_year]
            if np.sum(sample_1yr_r) < 0:
                negative_years_count += 1

        max_dds_1pct = np.array(max_dds_1pct)
        max_dds_05pct = np.array(max_dds_05pct)
        max_dds_2pct = np.array(max_dds_2pct)
        losing_streaks = np.array(losing_streaks)

        ruin_05 = float(np.mean(max_dds_05pct >= ruin_dd_threshold_pct)) * 100.0
        ruin_10 = float(np.mean(max_dds_1pct >= ruin_dd_threshold_pct)) * 100.0
        ruin_20 = float(np.mean(max_dds_2pct >= ruin_dd_threshold_pct)) * 100.0

        p95_dd = float(np.percentile(max_dds_1pct, 95))
        recommended_risk = 0.5 if p95_dd > 15.0 else (1.0 if p95_dd <= 10.0 else 0.75)

        return MonteCarloReport(
            iterations=self.iterations,
            trades_sample_size=n_trades,
            median_max_dd_pct=round(float(np.median(max_dds_1pct)), 2),
            p90_max_dd_pct=round(float(np.percentile(max_dds_1pct, 90)), 2),
            p95_max_dd_pct=round(p95_dd, 2),
            p99_max_dd_pct=round(float(np.percentile(max_dds_1pct, 99)), 2),
            prob_losing_streak_ge_6=round(float(np.mean(losing_streaks >= 6)) * 100.0, 1),
            prob_losing_streak_ge_8=round(float(np.mean(losing_streaks >= 8)) * 100.0, 1),
            prob_losing_streak_ge_10=round(float(np.mean(losing_streaks >= 10)) * 100.0, 1),
            prob_negative_year=round((negative_years_count / self.iterations) * 100.0, 1),
            ruin_prob_0_5pct_risk=round(ruin_05, 2),
            ruin_prob_1_0pct_risk=round(ruin_10, 2),
            ruin_prob_2_0pct_risk=round(ruin_20, 2),
            recommended_risk_per_trade_pct=recommended_risk,
        )

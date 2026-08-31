"""
Statistical Significance & Bootstrap Confidence Interval Engine.
Performs 5,000 bootstrap resamples on trade R-multiples to compute 95% Confidence Intervals
for Expectancy and the true probability of positive expectancy (P(Exp > 0)).
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd


@dataclass
class SignificanceReport:
    trade_count: int
    point_expectancy_r: float
    bootstrap_mean_r: float
    bootstrap_median_r: float
    ci_95_lower_r: float
    ci_95_upper_r: float
    ci_90_lower_r: float
    ci_90_upper_r: float
    standard_error_r: float
    prob_expectancy_greater_than_zero: float  # % of bootstrap samples with mean > 0
    is_statistically_significant_95: bool  # True if 95% CI lower bound > 0
    t_statistic: float


class StatisticalSignificanceEngine:
    """Computes rigorous non-parametric bootstrap confidence intervals on strategy returns."""

    def __init__(self, n_resamples: int = 5000, random_seed: int = 42):
        self.n_resamples = n_resamples
        self.random_seed = random_seed

    def evaluate_significance(self, r_multiples: np.ndarray) -> SignificanceReport:
        clean_r = r_multiples[~np.isnan(r_multiples)]
        n = len(clean_r)
        if n < 15:
            return SignificanceReport(
                trade_count=n, point_expectancy_r=0.0, bootstrap_mean_r=0.0, bootstrap_median_r=0.0,
                ci_95_lower_r=0.0, ci_95_upper_r=0.0, ci_90_lower_r=0.0, ci_90_upper_r=0.0,
                standard_error_r=0.0, prob_expectancy_greater_than_zero=0.0,
                is_statistically_significant_95=False, t_statistic=0.0,
            )

        np.random.seed(self.random_seed)
        point_mean = float(np.mean(clean_r))
        point_std = float(np.std(clean_r, ddof=1))
        se = point_std / np.sqrt(n)
        t_stat = point_mean / (se + 1e-9)

        # Bootstrap resampling of the sample mean
        resampled_means = []
        for _ in range(self.n_resamples):
            sample = np.random.choice(clean_r, size=n, replace=True)
            resampled_means.append(np.mean(sample))

        resampled_means = np.array(resampled_means)

        ci_95_low = float(np.percentile(resampled_means, 2.5))
        ci_95_high = float(np.percentile(resampled_means, 97.5))
        ci_90_low = float(np.percentile(resampled_means, 5.0))
        ci_90_high = float(np.percentile(resampled_means, 95.0))
        prob_pos = float(np.mean(resampled_means > 0)) * 100.0

        return SignificanceReport(
            trade_count=n,
            point_expectancy_r=round(point_mean, 3),
            bootstrap_mean_r=round(float(np.mean(resampled_means)), 3),
            bootstrap_median_r=round(float(np.median(resampled_means)), 3),
            ci_95_lower_r=round(ci_95_low, 3),
            ci_95_upper_r=round(ci_95_high, 3),
            ci_90_lower_r=round(ci_90_low, 3),
            ci_90_upper_r=round(ci_90_high, 3),
            standard_error_r=round(se, 3),
            prob_expectancy_greater_than_zero=round(prob_pos, 1),
            is_statistically_significant_95=(ci_95_low > 0),
            t_statistic=round(t_stat, 2),
        )

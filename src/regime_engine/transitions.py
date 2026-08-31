"""
Regime Transition & Dynamic Volatility Structure Engine.
Extracts non-leaking transition features capturing:
- Volatility Compression -> Expansion
- Volatility Expansion -> Contraction
- Range -> Trend breakouts
- Trend -> Range decay
- Bullish <-> Bearish structural shifts
- Pre-transition vs Steady-State categorization
"""
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


class TransitionEngine:
    """Computes regime transition signals and volatility structure dynamics."""

    def __init__(self, symbol: str):
        self.symbol = symbol

    def compute_transition_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enriches feature dataframe with causality-preserved transition vectors.
        """
        res = df.copy()

        # 1. Volatility Structure & Percentile Shifts
        atr_14 = res["atr_14"]
        tr = res["true_range"] if "true_range" in res.columns else (res["high"] - res["low"])
        atr_100 = tr.rolling(window=100, min_periods=100).mean()
        res["short_long_vol_ratio"] = atr_14 / (atr_100 + 1e-9)

        # 10-bar ATR percentile shift
        atr_pctl = res["atr_percentile_200"]
        res["atr_percentile_lag10"] = atr_pctl.shift(10)
        res["vol_percentile_change_10"] = atr_pctl - res["atr_percentile_lag10"]

        # 5-bar ATR slope
        res["atr_slope_5"] = (atr_14 - atr_14.shift(5)) / (5.0 * (atr_14.shift(5) + 1e-9))

        # Range compression ratio (20-bar Donchian range / 100-bar Donchian range)
        range_20 = res["high"].rolling(20).max() - res["low"].rolling(20).min()
        range_100 = res["high"].rolling(100).max() - res["low"].rolling(100).min()
        res["range_compression_ratio"] = range_20 / (range_100 + 1e-9)

        # 2. Discrete Volatility Transition State
        squeeze = res["squeeze_on"]
        had_prior_squeeze = squeeze.shift(1) | squeeze.shift(2) | squeeze.shift(3) | squeeze.shift(4)
        is_expanding_now = (~squeeze) & (res["atr_ratio_14_50"] > 1.10)

        vol_trans = pd.Series("STEADY_VOL", index=res.index)

        is_comp_to_exp = had_prior_squeeze & is_expanding_now
        is_exp_to_cont = (res["atr_ratio_14_50"] > 1.20).shift(5) & (res["atr_slope_5"] < -0.04)
        is_low_to_high = (res["atr_percentile_lag10"] < 0.30) & (atr_pctl > 0.60)
        is_high_to_high = (res["atr_percentile_lag10"] > 0.60) & (atr_pctl > 0.60)
        is_low_to_low = (res["atr_percentile_lag10"] < 0.35) & (atr_pctl < 0.35)

        vol_trans[is_high_to_high] = "HIGH_TO_HIGH_VOL"
        vol_trans[is_low_to_low] = "LOW_TO_LOW_VOL"
        vol_trans[is_low_to_high] = "LOW_TO_HIGH_VOL"
        vol_trans[is_exp_to_cont] = "EXPANSION_TO_CONTRACTION"
        vol_trans[is_comp_to_exp] = "COMPRESSION_TO_EXPANSION"

        res["volatility_transition"] = vol_trans

        # 3. Trend State Transitions
        adx = res["adx_14"]
        adx_lag10 = adx.shift(10)
        ema_stack = res["ema_stack"]
        ema_stack_lag5 = ema_stack.shift(5)

        trend_trans = pd.Series("STEADY_TREND", index=res.index)

        is_range_to_trend = (adx_lag10 < 18.0) & (adx >= 22.0) & (ema_stack != 0)
        is_trend_to_range = (adx_lag10 > 25.0) & (adx < 20.0)
        is_bull_to_bear = (ema_stack_lag5 == 1) & (ema_stack == -1)
        is_bear_to_bull = (ema_stack_lag5 == -1) & (ema_stack == 1)
        is_weak_to_strong = (adx_lag10 >= 18.0) & (adx > adx_lag10 + 5.0) & (ema_stack != 0)

        trend_trans[is_trend_to_range] = "TREND_TO_RANGE"
        trend_trans[is_weak_to_strong] = "WEAK_TO_STRONG_TREND"
        trend_trans[is_bull_to_bear] = "BULL_TO_BEAR"
        trend_trans[is_bear_to_bull] = "BEAR_TO_BULL"
        trend_trans[is_range_to_trend] = "RANGE_TO_TREND"

        res["trend_transition"] = trend_trans

        # 4. Composite Macro Transition Tag
        res["macro_transition"] = res["trend_transition"] + "__" + res["volatility_transition"]

        return res

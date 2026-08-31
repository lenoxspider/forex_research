"""
Market Regime Classification Engine.
Quantifies Trend Regimes, Volatility Regimes, and Transition States.
"""
from enum import Enum
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


class TrendRegime(str, Enum):
    STRONG_BULL = "STRONG_BULL"
    STRONG_BEAR = "STRONG_BEAR"
    WEAK_BULL = "WEAK_BULL"
    WEAK_BEAR = "WEAK_BEAR"
    RANGING = "RANGING"
    CHOPPY = "CHOPPY"


class VolatilityRegime(str, Enum):
    LOW_VOL = "LOW_VOL"
    NORMAL_VOL = "NORMAL_VOL"
    HIGH_VOL = "HIGH_VOL"
    EXPANSION = "EXPANSION"
    CONTRACTION = "CONTRACTION"


class RegimeEngine:
    """Classifies discrete market conditions without look-ahead."""

    def __init__(self, adx_trend_threshold: float = 22.0, adx_range_threshold: float = 18.0):
        self.adx_trend_threshold = adx_trend_threshold
        self.adx_range_threshold = adx_range_threshold

    def classify_regimes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Appends trend_regime, vol_regime, and combined_regime to the feature DataFrame.
        """
        res = df.copy()

        # 1. Trend Regime Classification
        adx = res["adx_14"]
        plus_di = res["plus_di_14"]
        minus_di = res["minus_di_14"]
        ema_stack = res["ema_stack"]
        ema_50_slope = res["ema_50_slope_5"]

        trend_series = pd.Series(TrendRegime.CHOPPY.value, index=res.index)

        is_strong_bull = (adx >= self.adx_trend_threshold) & (plus_di > minus_di) & (ema_stack == 1) & (ema_50_slope > 0)
        is_strong_bear = (adx >= self.adx_trend_threshold) & (minus_di > plus_di) & (ema_stack == -1) & (ema_50_slope < 0)
        is_weak_bull = (ema_stack == 1) & ~is_strong_bull
        is_weak_bear = (ema_stack == -1) & ~is_strong_bear
        is_ranging = (adx < self.adx_range_threshold) & (res["atr_ratio_14_50"] < 1.0)

        trend_series[is_weak_bull] = TrendRegime.WEAK_BULL.value
        trend_series[is_weak_bear] = TrendRegime.WEAK_BEAR.value
        trend_series[is_ranging] = TrendRegime.RANGING.value
        trend_series[is_strong_bull] = TrendRegime.STRONG_BULL.value
        trend_series[is_strong_bear] = TrendRegime.STRONG_BEAR.value

        res["trend_regime"] = trend_series

        # 2. Volatility Regime Classification
        atr_pctl = res["atr_percentile_200"]
        atr_ratio = res["atr_ratio_14_50"]
        squeeze = res["squeeze_on"]

        vol_series = pd.Series(VolatilityRegime.NORMAL_VOL.value, index=res.index)

        is_low_vol = (atr_pctl < 0.25) | squeeze
        is_high_vol = (atr_pctl > 0.75) & (atr_ratio > 1.15)
        is_expansion = (atr_ratio > 1.25) & (~squeeze) & (squeeze.shift(1) | squeeze.shift(2))
        is_contraction = (atr_ratio < 0.80) & (atr_pctl < 0.40)

        vol_series[is_low_vol] = VolatilityRegime.LOW_VOL.value
        vol_series[is_contraction] = VolatilityRegime.CONTRACTION.value
        vol_series[is_high_vol] = VolatilityRegime.HIGH_VOL.value
        vol_series[is_expansion] = VolatilityRegime.EXPANSION.value

        res["vol_regime"] = vol_series

        # 3. Combined Macro-Regime
        res["combined_regime"] = res["trend_regime"] + "__" + res["vol_regime"]

        return res

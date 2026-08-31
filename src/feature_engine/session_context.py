"""
Pre-Session Context & Order Flow State Engine.
Quantifies market conditions immediately preceding major liquidity sessions (London 07:00 UTC and NY 12:00 UTC).
"""
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from config.settings import PAIR_SPECS, PairSpec


class SessionContextEngine:
    """Computes overnight range, pre-session momentum drift, and distance to previous day extremes."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.spec: PairSpec = PAIR_SPECS.get(symbol, PAIR_SPECS["EURUSD"])
        self.pip_size = self.spec.pip_size

    def compute_session_context(self, df: pd.DataFrame) -> pd.DataFrame:
        res = df.copy()
        times = res.index
        close = res["close"]
        high = res["high"]
        low = res["low"]

        # 1. Asian Session Range (00:00 to 06:45 UTC)
        df_asian = res[(times.hour >= 0) & (times.hour < 7)]
        asian_highs = df_asian["high"].groupby(df_asian.index.date).max()
        asian_lows = df_asian["low"].groupby(df_asian.index.date).min()
        asian_ranges = (asian_highs - asian_lows) / self.pip_size

        # Map back to date
        dates = pd.Series(times.date, index=times)
        res["asian_high"] = dates.map(asian_highs)
        res["asian_low"] = dates.map(asian_lows)
        res["asian_range_pips"] = dates.map(asian_ranges)

        # Categorize Asian Range
        asian_r_cat = pd.Series("NORMAL (25-45p)", index=times)
        asian_r_cat[res["asian_range_pips"] < 25.0] = "TIGHT (<25p)"
        asian_r_cat[res["asian_range_pips"] > 45.0] = "EXPANDED (>45p)"
        res["asian_range_category"] = asian_r_cat

        # 2. Previous Day High (PDH) & Previous Day Low (PDL)
        daily_highs = res["high"].groupby(dates).max()
        daily_lows = res["low"].groupby(dates).min()

        prev_day_high = daily_highs.shift(1)
        prev_day_low = daily_lows.shift(1)

        res["pdh"] = dates.map(prev_day_high)
        res["pdl"] = dates.map(prev_day_low)

        res["dist_to_pdh_pips"] = (res["pdh"] - close) / self.pip_size
        res["dist_to_pdl_pips"] = (close - res["pdl"]) / self.pip_size

        # 3. Pre-Session 4-Hour Momentum Drift (16 bars of M15)
        res["pre_session_drift_4h_pips"] = (close - close.shift(16)) / self.pip_size

        drift_bias = pd.Series("FLAT", index=times)
        drift_bias[res["pre_session_drift_4h_pips"] > 15.0] = "BULLISH_DRIFT"
        drift_bias[res["pre_session_drift_4h_pips"] < -15.0] = "BEARISH_DRIFT"
        res["pre_session_bias"] = drift_bias

        return res

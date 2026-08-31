"""
Feature Engineering Engine for Systematic Multi-Pair Forex Trading.
Extracts strictly non-leaking, causal technical, structural, volatility, and session features.
"""
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd

from config.settings import SESSION_WINDOWS, PAIR_SPECS


class FeatureEngine:
    """
    Computes deterministic technical, volatility, momentum, and structural features.
    Guarantees causal execution (no look-ahead).
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.spec = PAIR_SPECS.get(symbol)
        self.pip_size = self.spec.pip_size if self.spec else 0.0001

    def compute_all_features(
        self,
        df_m15: pd.DataFrame,
        df_h1: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Calculates all feature groups on M15 bars, merging higher-timeframe H1 trend context causally.
        """
        df = df_m15.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, utc=True)

        # 1. Price Returns & Volatility Features
        df = self._add_volatility_features(df)

        # 2. Moving Averages & Trend Momentum
        df = self._add_trend_momentum_features(df)

        # 3. Market Structure (Pivots, BOS, CHoCH, Range Compression)
        df = self._add_market_structure_features(df)

        # 4. Session & Temporal Features
        df = self._add_session_features(df)

        # 5. Higher Timeframe (H1) Alignment (Strictly Causal Merge)
        if df_h1 is not None:
            df = self._merge_h1_context(df, df_h1)

        return df

    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Computes True Range, ATR(14), ATR%, Realized Vol, and Vol Expansion/Contraction."""
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df["true_range"] = tr
        df["atr_14"] = tr.rolling(window=14, min_periods=14).mean()
        df["atr_pips"] = df["atr_14"] / self.pip_size
        df["atr_pct"] = df["atr_14"] / close

        # Rolling Realized Volatility (20-bar annualized log returns)
        log_ret = np.log(close / prev_close)
        df["log_return"] = log_ret
        # 1 year ~ 252 * 24 * 4 = 24,192 M15 bars
        df["realized_vol_20"] = log_ret.rolling(window=20).std() * np.sqrt(24192)

        # Volatility Expansion / Contraction Ratio (Short ATR / Long ATR)
        atr_50 = tr.rolling(window=50, min_periods=50).mean()
        df["atr_ratio_14_50"] = df["atr_14"] / (atr_50 + 1e-9)

        # Rolling ATR Percentile (over 200 bars)
        df["atr_percentile_200"] = df["atr_14"].rolling(window=200).apply(
            lambda s: (s.iloc[-1] - s.min()) / (s.max() - s.min() + 1e-9) if (s.max() > s.min()) else 0.5,
            raw=False,
        )

        return df

    def _add_trend_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Computes EMAs (20, 50, 200), slopes, ADX, RSI, and MACD."""
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # EMAs
        df["ema_20"] = close.ewm(span=20, adjust=False).mean()
        df["ema_50"] = close.ewm(span=50, adjust=False).mean()
        df["ema_200"] = close.ewm(span=200, adjust=False).mean()

        # EMA Slopes (Normalized in pips per 5 bars)
        df["ema_20_slope_5"] = (df["ema_20"] - df["ema_20"].shift(5)) / (5 * self.pip_size)
        df["ema_50_slope_5"] = (df["ema_50"] - df["ema_50"].shift(5)) / (5 * self.pip_size)
        df["ema_200_slope_10"] = (df["ema_200"] - df["ema_200"].shift(10)) / (10 * self.pip_size)

        # EMA Alignment (+1 Bullish Stack, -1 Bearish Stack, 0 Neutral)
        df["ema_stack"] = 0
        bull_stack = (close > df["ema_20"]) & (df["ema_20"] > df["ema_50"]) & (df["ema_50"] > df["ema_200"])
        bear_stack = (close < df["ema_20"]) & (df["ema_20"] < df["ema_50"]) & (df["ema_50"] < df["ema_200"])
        df.loc[bull_stack, "ema_stack"] = 1
        df.loc[bear_stack, "ema_stack"] = -1

        # RSI (14)
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        df["rsi_14"] = 100.0 - (100.0 / (1.0 + rs))

        # ADX (14) with +DI / -DI
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        tr = df["true_range"]
        tr_smooth = tr.rolling(window=14).sum()
        plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(window=14).sum() / (tr_smooth + 1e-9))
        minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(window=14).sum() / (tr_smooth + 1e-9))

        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9))
        df["adx_14"] = dx.rolling(window=14).mean()
        df["plus_di_14"] = plus_di
        df["minus_di_14"] = minus_di

        # Bollinger Bands (20, 2.0)
        sma_20 = close.rolling(window=20).mean()
        std_20 = close.rolling(window=20).std()
        df["bb_upper"] = sma_20 + 2.0 * std_20
        df["bb_lower"] = sma_20 - 2.0 * std_20
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / sma_20
        df["bb_pct"] = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-9)

        # Keltner Channels (20, 1.5 ATR)
        df["kc_upper"] = sma_20 + 1.5 * df["atr_14"]
        df["kc_lower"] = sma_20 - 1.5 * df["atr_14"]
        # Squeeze indicator: BB inside KC
        df["squeeze_on"] = (df["bb_lower"] > df["kc_lower"]) & (df["bb_upper"] < df["kc_upper"])

        return df

    def _add_market_structure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes rolling swing highs/lows, Break of Structure (BOS), Change of Character (CHoCH),
        and distance from recent swing extremes.
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # Rolling 20-bar & 50-bar highs and lows (using lagged window to avoid lookahead on current bar)
        df["swing_high_20"] = high.shift(1).rolling(window=20).max()
        df["swing_low_20"] = low.shift(1).rolling(window=20).min()
        df["swing_high_50"] = high.shift(1).rolling(window=50).max()
        df["swing_low_50"] = low.shift(1).rolling(window=50).min()

        # Distance from swing highs/lows in pips
        df["dist_to_swing_high_20_pips"] = (df["swing_high_20"] - close) / self.pip_size
        df["dist_to_swing_low_20_pips"] = (close - df["swing_low_20"]) / self.pip_size

        # Break of Structure (BOS): Bar closes beyond the prior 20-bar swing extreme
        df["bos_bullish"] = (close > df["swing_high_20"]) & (close.shift(1) <= df["swing_high_20"])
        df["bos_bearish"] = (close < df["swing_low_20"]) & (close.shift(1) >= df["swing_low_20"])

        # Change of Character (CHoCH): Counter-trend break of 50-bar structural level
        df["choch_bullish"] = (close > df["swing_high_50"]) & (df["ema_stack"] <= 0)
        df["choch_bearish"] = (close < df["swing_low_50"]) & (df["ema_stack"] >= 0)

        # Pullback Distance to EMA20 / EMA50 (in ATR units)
        df["pullback_ema20_atr"] = (close - df["ema_20"]) / (df["atr_14"] + 1e-9)
        df["pullback_ema50_atr"] = (close - df["ema_50"]) / (df["atr_14"] + 1e-9)

        # Price Action Candle Metrics
        body = (close - df["open"]).abs()
        total_range = high - low + 1e-9
        df["candle_body_ratio"] = body / total_range
        df["upper_wick_ratio"] = (high - np.maximum(close, df["open"])) / total_range
        df["lower_wick_ratio"] = (np.minimum(close, df["open"]) - low) / total_range

        return df

    def _add_session_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adds Session indicators (Asian, London, Overlap, NY) and Day of Week."""
        hour = df.index.hour
        dow = df.index.dayofweek

        df["hour_utc"] = hour
        df["day_of_week"] = dow  # 0=Monday, 4=Friday, 6=Sunday

        df["is_asian_session"] = (hour >= 0) & (hour < 7)
        df["is_london_session"] = (hour >= 7) & (hour < 12)
        df["is_london_ny_overlap"] = (hour >= 12) & (hour < 16)
        df["is_ny_afternoon"] = (hour >= 16) & (hour < 21)
        df["is_rollover_window"] = (hour >= 21) & (hour < 23)

        return df

    def _merge_h1_context(self, df_m15: pd.DataFrame, df_h1: pd.DataFrame) -> pd.DataFrame:
        """
        Merges H1 trend context into M15 bars strictly causally.
        H1 bar completed at 08:00 is only available to M15 bars starting at 08:00+.
        """
        h1_feat = pd.DataFrame(index=df_h1.index)
        h1_close = df_h1["close"]
        h1_feat["h1_ema_50"] = h1_close.ewm(span=50, adjust=False).mean()
        h1_feat["h1_ema_200"] = h1_close.ewm(span=200, adjust=False).mean()
        
        # H1 Trend State: +1 Bullish, -1 Bearish, 0 Neutral
        h1_feat["h1_trend_bullish"] = (h1_close > h1_feat["h1_ema_50"]) & (h1_feat["h1_ema_50"] > h1_feat["h1_ema_200"])
        h1_feat["h1_trend_bearish"] = (h1_close < h1_feat["h1_ema_50"]) & (h1_feat["h1_ema_50"] < h1_feat["h1_ema_200"])
        h1_feat["h1_trend_state"] = 0
        h1_feat.loc[h1_feat["h1_trend_bullish"], "h1_trend_state"] = 1
        h1_feat.loc[h1_feat["h1_trend_bearish"], "h1_trend_state"] = -1

        # Shift H1 by 1 bar so that H1 bar t-1 is merged into M15 bars of bar t
        h1_feat_shifted = h1_feat.shift(1)

        # Merge asof backward
        df_merged = pd.merge_asof(
            df_m15.sort_index(),
            h1_feat_shifted.sort_index(),
            left_index=True,
            right_index=True,
            direction="backward",
        )
        return df_merged

"""
Baseline Strategy Engine for Systematic Multi-Pair Forex Trading.
Implements 5 independent, mathematically precise rule-based setups with strict SL/TP and session filters.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from config.settings import PAIR_SPECS, PairSpec


@dataclass
class TradeSignal:
    timestamp: pd.Timestamp
    symbol: str
    direction: int  # +1 for Buy (Long), -1 for Sell (Short)
    entry_price: float
    stop_loss: float
    take_profit: float
    max_holding_bars: int
    strategy_name: str
    regime: str
    risk_pips: float
    target_pips: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """Abstract Strategy Interface."""

    def __init__(self, symbol: str, name: str, params: Optional[Dict[str, Any]] = None):
        self.symbol = symbol
        self.name = name
        self.params = params or {}
        self.spec: PairSpec = PAIR_SPECS.get(symbol, PAIR_SPECS["EURUSD"])
        self.pip_size = self.spec.pip_size

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """Scans feature dataframe and produces discrete causal TradeSignals."""
        pass


class TrendFollowingPullbackStrategy(BaseStrategy):
    """
    Strategy A: Trend-Following Pullback (TF_PB).
    Aligns with H1/M15 trend stack and enters on pullbacks into dynamic EMA support/resistance zones.
    """

    def __init__(self, symbol: str, params: Optional[Dict[str, Any]] = None):
        default_params = {
            "adx_threshold": 20.0,
            "atr_sl_mult": 1.5,
            "rr_ratio": 2.0,
            "max_holding_bars": 32,  # 8 hours on M15
            "allowed_sessions": ["is_london_session", "is_london_ny_overlap"],
            "max_spread_pips": 2.0,
        }
        if params:
            default_params.update(params)
        super().__init__(symbol, "TF_PB", default_params)

    def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        signals = []
        n = len(df)
        if n < 200:
            return signals

        close = df["close"].values
        open_p = df["open"].values
        high = df["high"].values
        low = df["low"].values
        ema_20 = df["ema_20"].values
        ema_50 = df["ema_50"].values
        ema_stack = df["ema_stack"].values
        adx = df["adx_14"].values
        atr = df["atr_14"].values
        lower_wick = df["lower_wick_ratio"].values
        upper_wick = df["upper_wick_ratio"].values
        regimes = df["combined_regime"].values if "combined_regime" in df.columns else ["UNKNOWN"] * n
        h1_trend = df["h1_trend_state"].values if "h1_trend_state" in df.columns else np.zeros(n)
        spread = (df["spread"].values * 0.1) if "spread" in df.columns else np.zeros(n)  # points to pips

        # Session mask
        session_mask = np.zeros(n, dtype=bool)
        for s in self.params["allowed_sessions"]:
            if s in df.columns:
                session_mask |= df[s].values

        for i in range(50, n - 1):
            if not session_mask[i]:
                continue
            if spread[i] > self.params["max_spread_pips"]:
                continue
            if np.isnan(atr[i]) or atr[i] <= 0:
                continue

            # --- LONG SIGNAL ---
            # 1. Bullish trend alignment (M15 EMA stack + H1 trend bullish + ADX >= 20)
            if ema_stack[i] == 1 and h1_trend[i] >= 0 and adx[i] >= self.params["adx_threshold"]:
                # 2. Pullback into dynamic support (low touched EMA20, close held above EMA50)
                if low[i] <= ema_20[i] and close[i] >= ema_50[i]:
                    # 3. Bullish rejection trigger
                    if close[i] > open_p[i] and lower_wick[i] >= 0.25:
                        entry_price = close[i]
                        sl_dist = self.params["atr_sl_mult"] * atr[i]
                        sl_price = entry_price - sl_dist
                        tp_dist = sl_dist * self.params["rr_ratio"]
                        tp_price = entry_price + tp_dist

                        signals.append(
                            TradeSignal(
                                timestamp=df.index[i],
                                symbol=self.symbol,
                                direction=1,
                                entry_price=float(entry_price),
                                stop_loss=float(sl_price),
                                take_profit=float(tp_price),
                                max_holding_bars=self.params["max_holding_bars"],
                                strategy_name=self.name,
                                regime=str(regimes[i]),
                                risk_pips=float(sl_dist / self.pip_size),
                                target_pips=float(tp_dist / self.pip_size),
                                metadata={"atr": float(atr[i])},
                            )
                        )

            # --- SHORT SIGNAL ---
            elif ema_stack[i] == -1 and h1_trend[i] <= 0 and adx[i] >= self.params["adx_threshold"]:
                if high[i] >= ema_20[i] and close[i] <= ema_50[i]:
                    if close[i] < open_p[i] and upper_wick[i] >= 0.25:
                        entry_price = close[i]
                        sl_dist = self.params["atr_sl_mult"] * atr[i]
                        sl_price = entry_price + sl_dist
                        tp_dist = sl_dist * self.params["rr_ratio"]
                        tp_price = entry_price - tp_dist

                        signals.append(
                            TradeSignal(
                                timestamp=df.index[i],
                                symbol=self.symbol,
                                direction=-1,
                                entry_price=float(entry_price),
                                stop_loss=float(sl_price),
                                take_profit=float(tp_price),
                                max_holding_bars=self.params["max_holding_bars"],
                                strategy_name=self.name,
                                regime=str(regimes[i]),
                                risk_pips=float(sl_dist / self.pip_size),
                                target_pips=float(tp_dist / self.pip_size),
                                metadata={"atr": float(atr[i])},
                            )
                        )

        return signals


class VolatilityExpansionBreakoutStrategy(BaseStrategy):
    """
    Strategy B: Volatility Expansion Breakout (VE_BO).
    Enters on structural range breakouts following volatility squeeze compression.
    """

    def __init__(self, symbol: str, params: Optional[Dict[str, Any]] = None):
        default_params = {
            "atr_sl_mult": 1.2,
            "rr_ratio": 2.2,
            "max_holding_bars": 24,
            "body_ratio_threshold": 0.55,
            "allowed_sessions": ["is_london_session", "is_london_ny_overlap"],
            "max_spread_pips": 2.0,
        }
        if params:
            default_params.update(params)
        super().__init__(symbol, "VE_BO", default_params)

    def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        signals = []
        n = len(df)
        if n < 200:
            return signals

        close = df["close"].values
        bos_bull = df["bos_bullish"].values
        bos_bear = df["bos_bearish"].values
        squeeze = df["squeeze_on"].values
        atr = df["atr_14"].values
        atr_ratio = df["atr_ratio_14_50"].values
        body_ratio = df["candle_body_ratio"].values
        regimes = df["combined_regime"].values if "combined_regime" in df.columns else ["UNKNOWN"] * n
        spread = (df["spread"].values * 0.1) if "spread" in df.columns else np.zeros(n)

        session_mask = np.zeros(n, dtype=bool)
        for s in self.params["allowed_sessions"]:
            if s in df.columns:
                session_mask |= df[s].values

        for i in range(50, n - 1):
            if not session_mask[i]:
                continue
            if spread[i] > self.params["max_spread_pips"]:
                continue
            if np.isnan(atr[i]) or atr[i] <= 0:
                continue

            # Prior squeeze condition within last 4 bars
            had_prior_squeeze = squeeze[i - 4 : i].any()
            is_expanding = atr_ratio[i] >= 1.05 and body_ratio[i] >= self.params["body_ratio_threshold"]

            if had_prior_squeeze and is_expanding:
                if bos_bull[i]:
                    entry_price = close[i]
                    sl_dist = self.params["atr_sl_mult"] * atr[i]
                    sl_price = entry_price - sl_dist
                    tp_dist = sl_dist * self.params["rr_ratio"]
                    tp_price = entry_price + tp_dist

                    signals.append(
                        TradeSignal(
                            timestamp=df.index[i],
                            symbol=self.symbol,
                            direction=1,
                            entry_price=float(entry_price),
                            stop_loss=float(sl_price),
                            take_profit=float(tp_price),
                            max_holding_bars=self.params["max_holding_bars"],
                            strategy_name=self.name,
                            regime=str(regimes[i]),
                            risk_pips=float(sl_dist / self.pip_size),
                            target_pips=float(tp_dist / self.pip_size),
                            metadata={"atr": float(atr[i])},
                        )
                    )
                elif bos_bear[i]:
                    entry_price = close[i]
                    sl_dist = self.params["atr_sl_mult"] * atr[i]
                    sl_price = entry_price + sl_dist
                    tp_dist = sl_dist * self.params["rr_ratio"]
                    tp_price = entry_price - tp_dist

                    signals.append(
                        TradeSignal(
                            timestamp=df.index[i],
                            symbol=self.symbol,
                            direction=-1,
                            entry_price=float(entry_price),
                            stop_loss=float(sl_price),
                            take_profit=float(tp_price),
                            max_holding_bars=self.params["max_holding_bars"],
                            strategy_name=self.name,
                            regime=str(regimes[i]),
                            risk_pips=float(sl_dist / self.pip_size),
                            target_pips=float(tp_dist / self.pip_size),
                            metadata={"atr": float(atr[i])},
                        )
                    )

        return signals


class MeanReversionRangeStrategy(BaseStrategy):
    """
    Strategy C: Mean Reversion in Range (MR_RG).
    Trades envelope overextensions in low ADX/ranging market regimes.
    """

    def __init__(self, symbol: str, params: Optional[Dict[str, Any]] = None):
        default_params = {
            "adx_max": 20.0,
            "rsi_oversold": 30.0,
            "rsi_overbought": 70.0,
            "atr_sl_mult": 1.0,
            "max_holding_bars": 16,
            "allowed_sessions": ["is_asian_session", "is_london_session", "is_london_ny_overlap"],
            "max_spread_pips": 1.8,
        }
        if params:
            default_params.update(params)
        super().__init__(symbol, "MR_RG", default_params)

    def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        signals = []
        n = len(df)
        if n < 200:
            return signals

        close = df["close"].values
        low = df["low"].values
        high = df["high"].values
        bb_upper = df["bb_upper"].values
        bb_lower = df["bb_lower"].values
        rsi = df["rsi_14"].values
        adx = df["adx_14"].values
        atr = df["atr_14"].values
        regimes = df["combined_regime"].values if "combined_regime" in df.columns else ["UNKNOWN"] * n
        spread = (df["spread"].values * 0.1) if "spread" in df.columns else np.zeros(n)

        session_mask = np.zeros(n, dtype=bool)
        for s in self.params["allowed_sessions"]:
            if s in df.columns:
                session_mask |= df[s].values

        for i in range(50, n - 1):
            if not session_mask[i]:
                continue
            if spread[i] > self.params["max_spread_pips"]:
                continue
            if np.isnan(atr[i]) or atr[i] <= 0:
                continue

            # Only trade in low ADX / ranging regimes
            if adx[i] > self.params["adx_max"]:
                continue

            # Long Reversal: low pierced lower BB, RSI was oversold, and bar closed back above lower BB
            if low[i] <= bb_lower[i] and rsi[i] < self.params["rsi_oversold"] and close[i] > bb_lower[i]:
                entry_price = close[i]
                sl_dist = self.params["atr_sl_mult"] * atr[i]
                sl_price = entry_price - sl_dist
                # Target is middle of BB (ema/sma 20)
                tp_dist = max(sl_dist * 1.5, (bb_upper[i] - bb_lower[i]) * 0.5)
                tp_price = entry_price + tp_dist

                signals.append(
                    TradeSignal(
                        timestamp=df.index[i],
                        symbol=self.symbol,
                        direction=1,
                        entry_price=float(entry_price),
                        stop_loss=float(sl_price),
                        take_profit=float(tp_price),
                        max_holding_bars=self.params["max_holding_bars"],
                        strategy_name=self.name,
                        regime=str(regimes[i]),
                        risk_pips=float(sl_dist / self.pip_size),
                        target_pips=float(tp_dist / self.pip_size),
                        metadata={"atr": float(atr[i])},
                    )
                )

            # Short Reversal: high pierced upper BB, RSI was overbought, and bar closed back below upper BB
            elif high[i] >= bb_upper[i] and rsi[i] > self.params["rsi_overbought"] and close[i] < bb_upper[i]:
                entry_price = close[i]
                sl_dist = self.params["atr_sl_mult"] * atr[i]
                sl_price = entry_price + sl_dist
                tp_dist = max(sl_dist * 1.5, (bb_upper[i] - bb_lower[i]) * 0.5)
                tp_price = entry_price - tp_dist

                signals.append(
                    TradeSignal(
                        timestamp=df.index[i],
                        symbol=self.symbol,
                        direction=-1,
                        entry_price=float(entry_price),
                        stop_loss=float(sl_price),
                        take_profit=float(tp_price),
                        max_holding_bars=self.params["max_holding_bars"],
                        strategy_name=self.name,
                        regime=str(regimes[i]),
                        risk_pips=float(sl_dist / self.pip_size),
                        target_pips=float(tp_dist / self.pip_size),
                        metadata={"atr": float(atr[i])},
                    )
                )

        return signals


class LondonSessionBreakoutStrategy(BaseStrategy):
    """
    Strategy D: London Session Momentum Breakout (LDN_MO).
    Calculates Asian session (00:00 - 06:45 UTC) high/low range and enters on London open breakouts.
    """

    def __init__(self, symbol: str, params: Optional[Dict[str, Any]] = None):
        default_params = {
            "atr_sl_mult": 1.4,
            "rr_ratio": 2.0,
            "max_holding_bars": 28,  # 7 hours
            "max_spread_pips": 2.0,
        }
        if params:
            default_params.update(params)
        super().__init__(symbol, "LDN_MO", default_params)

    def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        signals = []
        n = len(df)
        if n < 200:
            return signals

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        atr = df["atr_14"].values
        regimes = df["combined_regime"].values if "combined_regime" in df.columns else ["UNKNOWN"] * n
        spread = (df["spread"].values * 0.1) if "spread" in df.columns else np.zeros(n)
        times = df.index

        # Group by day to compute Asian Session Range (00:00 to 06:45 UTC)
        df_asian = df[(times.hour >= 0) & (times.hour < 7)]
        daily_asian_high = df_asian["high"].groupby(df_asian.index.date).max()
        daily_asian_low = df_asian["low"].groupby(df_asian.index.date).min()

        for i in range(50, n - 1):
            curr_time = times[i]
            # Only trigger between 07:00 and 10:00 UTC (London Morning Open)
            if curr_time.hour < 7 or curr_time.hour > 10:
                continue
            if spread[i] > self.params["max_spread_pips"]:
                continue
            if np.isnan(atr[i]) or atr[i] <= 0:
                continue

            day = curr_time.date()
            if day not in daily_asian_high or day not in daily_asian_low:
                continue

            asian_h = daily_asian_high[day]
            asian_l = daily_asian_low[day]
            range_pips = (asian_h - asian_l) / self.pip_size

            # Asian range must be reasonable (not excessively wide or tiny)
            if range_pips < 10 or range_pips > 80:
                continue

            # Long Breakout above Asian High
            if close[i] > asian_h and close[i - 1] <= asian_h:
                entry_price = close[i]
                sl_dist = max(self.params["atr_sl_mult"] * atr[i], (entry_price - asian_l) * 0.5)
                sl_price = entry_price - sl_dist
                tp_dist = sl_dist * self.params["rr_ratio"]
                tp_price = entry_price + tp_dist

                signals.append(
                    TradeSignal(
                        timestamp=curr_time,
                        symbol=self.symbol,
                        direction=1,
                        entry_price=float(entry_price),
                        stop_loss=float(sl_price),
                        take_profit=float(tp_price),
                        max_holding_bars=self.params["max_holding_bars"],
                        strategy_name=self.name,
                        regime=str(regimes[i]),
                        risk_pips=float(sl_dist / self.pip_size),
                        target_pips=float(tp_dist / self.pip_size),
                        metadata={"asian_range_pips": float(range_pips)},
                    )
                )

            # Short Breakout below Asian Low
            elif close[i] < asian_l and close[i - 1] >= asian_l:
                entry_price = close[i]
                sl_dist = max(self.params["atr_sl_mult"] * atr[i], (asian_h - entry_price) * 0.5)
                sl_price = entry_price + sl_dist
                tp_dist = sl_dist * self.params["rr_ratio"]
                tp_price = entry_price - tp_dist

                signals.append(
                    TradeSignal(
                        timestamp=curr_time,
                        symbol=self.symbol,
                        direction=-1,
                        entry_price=float(entry_price),
                        stop_loss=float(sl_price),
                        take_profit=float(tp_price),
                        max_holding_bars=self.params["max_holding_bars"],
                        strategy_name=self.name,
                        regime=str(regimes[i]),
                        risk_pips=float(sl_dist / self.pip_size),
                        target_pips=float(tp_dist / self.pip_size),
                        metadata={"asian_range_pips": float(range_pips)},
                    )
                )

        return signals


class MarketStructureBOSStrategy(BaseStrategy):
    """
    Strategy E: Market Structure BOS / Retest (MS_BOS).
    Identifies clear Break of Structure (BOS) and enters on structural retest.
    """

    def __init__(self, symbol: str, params: Optional[Dict[str, Any]] = None):
        default_params = {
            "atr_sl_mult": 1.5,
            "rr_ratio": 2.0,
            "max_holding_bars": 32,
            "allowed_sessions": ["is_london_session", "is_london_ny_overlap", "is_ny_afternoon"],
            "max_spread_pips": 2.0,
        }
        if params:
            default_params.update(params)
        super().__init__(symbol, "MS_BOS", default_params)

    def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        signals = []
        n = len(df)
        if n < 200:
            return signals

        close = df["close"].values
        low = df["low"].values
        high = df["high"].values
        swing_h = df["swing_high_20"].values
        swing_l = df["swing_low_20"].values
        bos_bull = df["bos_bullish"].values
        bos_bear = df["bos_bearish"].values
        atr = df["atr_14"].values
        regimes = df["combined_regime"].values if "combined_regime" in df.columns else ["UNKNOWN"] * n
        spread = (df["spread"].values * 0.1) if "spread" in df.columns else np.zeros(n)

        session_mask = np.zeros(n, dtype=bool)
        for s in self.params["allowed_sessions"]:
            if s in df.columns:
                session_mask |= df[s].values

        for i in range(50, n - 1):
            if not session_mask[i]:
                continue
            if spread[i] > self.params["max_spread_pips"]:
                continue
            if np.isnan(atr[i]) or atr[i] <= 0:
                continue

            # Bullish BOS retest: BOS fired 1 to 5 bars ago, current bar retests broken swing high
            recent_bos_bull = bos_bull[max(0, i - 5) : i].any()
            if recent_bos_bull:
                broken_level = swing_h[i - 2]
                if low[i] <= broken_level and close[i] >= broken_level:
                    entry_price = close[i]
                    sl_dist = self.params["atr_sl_mult"] * atr[i]
                    sl_price = entry_price - sl_dist
                    tp_dist = sl_dist * self.params["rr_ratio"]
                    tp_price = entry_price + tp_dist

                    signals.append(
                        TradeSignal(
                            timestamp=df.index[i],
                            symbol=self.symbol,
                            direction=1,
                            entry_price=float(entry_price),
                            stop_loss=float(sl_price),
                            take_profit=float(tp_price),
                            max_holding_bars=self.params["max_holding_bars"],
                            strategy_name=self.name,
                            regime=str(regimes[i]),
                            risk_pips=float(sl_dist / self.pip_size),
                            target_pips=float(tp_dist / self.pip_size),
                            metadata={"atr": float(atr[i])},
                        )
                    )

            # Bearish BOS retest
            recent_bos_bear = bos_bear[max(0, i - 5) : i].any()
            if recent_bos_bear:
                broken_level = swing_l[i - 2]
                if high[i] >= broken_level and close[i] <= broken_level:
                    entry_price = close[i]
                    sl_dist = self.params["atr_sl_mult"] * atr[i]
                    sl_price = entry_price + sl_dist
                    tp_dist = sl_dist * self.params["rr_ratio"]
                    tp_price = entry_price - tp_dist

                    signals.append(
                        TradeSignal(
                            timestamp=df.index[i],
                            symbol=self.symbol,
                            direction=-1,
                            entry_price=float(entry_price),
                            stop_loss=float(sl_price),
                            take_profit=float(tp_price),
                            max_holding_bars=self.params["max_holding_bars"],
                            strategy_name=self.name,
                            regime=str(regimes[i]),
                            risk_pips=float(sl_dist / self.pip_size),
                            target_pips=float(tp_dist / self.pip_size),
                            metadata={"atr": float(atr[i])},
                        )
                    )

        return signals

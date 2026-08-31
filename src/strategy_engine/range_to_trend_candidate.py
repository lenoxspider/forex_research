"""
RANGE_TO_TREND_TFPB_V1 Strategy Candidate Specification.

IMMUTABLE DEFINITION:
- Strategy Family: Trend-Following Pullback (TF_PB)
- Regime Transition Gate: trend_transition == 'RANGE_TO_TREND'
    Where:
    - ADX(14) shifted by 10 bars < 18.0 (Low-trend compression state)
    - ADX(14) at bar close t >= 22.0 (Active trend development)
    - EMA Stack at bar close t != 0 (EMA 20 > EMA 50 > EMA 200 for Bull, reverse for Bear)
- Pullback Entry Trigger:
    - Bullish: low <= ema_20 and close >= ema_50 and close > open and lower_wick >= 0.25 and ema_stack == 1
    - Bearish: high >= ema_20 and close <= ema_50 and close < open and upper_wick >= 0.25 and ema_stack == -1
- Execution Timing: Bar open t+1 (strictly after bar close t confirmation)
- Stop Loss: 1.5 * ATR(14) from entry price
- Initial Target: 1.00R (frozen based on broad reward plateau discovery)
- Max Holding Bars: 32 (8 hours)
- Transaction Friction: Live dynamic spread + broker commission ($7/lot = 0.7 pips) + slippage model
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from config.settings import PAIR_SPECS, PairSpec
from src.strategy_engine.strategies import BaseStrategy, TradeSignal


@dataclass(frozen=True)
class CandidateV1Config:
    """Immutable parameter container for RANGE_TO_TREND_TFPB_V1."""
    strategy_name: str = "RANGE_TO_TREND_TFPB_V1"
    adx_period: int = 14
    adx_lag_bars: int = 10
    adx_compression_threshold: float = 18.0
    adx_expansion_threshold: float = 22.0
    ema_fast: int = 20
    ema_mid: int = 50
    ema_slow: int = 200
    stop_atr_multiple: float = 1.50
    target_r_multiple: float = 1.00
    max_holding_bars: int = 32
    commission_per_lot_usd: float = 7.00


class RangeToTrendTFPBCandidate(BaseStrategy):
    """
    Frozen execution strategy for RANGE_TO_TREND_TFPB_V1.
    Ensures 100% causal signal generation strictly at bar close t.
    """

    def __init__(self, symbol: str, config: Optional[CandidateV1Config] = None):
        self.config = config or CandidateV1Config()
        super().__init__(symbol=symbol, name="RANGE_TO_TREND_TFPB_V1")

    def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        signals = []
        n = len(df)
        if n < 200:
            return signals

        close = df["close"].values
        open_p = df["open"].values
        high = df["high"].values
        low = df["low"].values
        ema_20 = df["ema_20"].values if "ema_20" in df.columns else np.zeros(n)
        ema_50 = df["ema_50"].values if "ema_50" in df.columns else np.zeros(n)
        ema_stack = df["ema_stack"].values if "ema_stack" in df.columns else np.zeros(n)
        adx = df["adx_14"].values if "adx_14" in df.columns else np.zeros(n)
        atr = df["atr_14"].values if "atr_14" in df.columns else np.zeros(n)
        lower_wick = df["lower_wick_ratio"].values if "lower_wick_ratio" in df.columns else np.zeros(n)
        upper_wick = df["upper_wick_ratio"].values if "upper_wick_ratio" in df.columns else np.zeros(n)
        trend_trans = df["trend_transition"].values if "trend_transition" in df.columns else np.array(["UNKNOWN"] * n)
        regimes = df["combined_regime"].values if "combined_regime" in df.columns else np.array(["UNKNOWN"] * n)

        # 10-bar lag ADX
        adx_lag = np.roll(adx, self.config.adx_lag_bars)
        adx_lag[:self.config.adx_lag_bars] = np.nan

        for i in range(50, n - 1):
            if np.isnan(atr[i]) or atr[i] <= 0:
                continue

            # 1. Causal Transition Gate: RANGE_TO_TREND
            is_range_to_trend = (
                (adx_lag[i] < self.config.adx_compression_threshold) and
                (adx[i] >= self.config.adx_expansion_threshold) and
                (ema_stack[i] != 0)
            )
            # Or from precomputed column
            if not (is_range_to_trend or trend_trans[i] == "RANGE_TO_TREND"):
                continue

            # Transition Quality Metric
            adx_delta = adx[i] - adx_lag[i]
            if adx_delta >= 10.0:
                quality = "STRONG"
            elif adx_delta >= 6.0:
                quality = "MODERATE"
            else:
                quality = "WEAK"

            # --- LONG SIGNAL ---
            if ema_stack[i] == 1 and low[i] <= ema_20[i] and close[i] >= ema_50[i]:
                if close[i] > open_p[i] and lower_wick[i] >= 0.25:
                    entry_price = close[i]
                    sl_dist = self.config.stop_atr_multiple * atr[i]
                    sl_price = entry_price - sl_dist
                    tp_dist = sl_dist * self.config.target_r_multiple
                    tp_price = entry_price + tp_dist
                    risk_pips = sl_dist / self.pip_size

                    signals.append(
                        TradeSignal(
                            timestamp=df.index[i],
                            symbol=self.symbol,
                            direction=1,
                            entry_price=float(entry_price),
                            stop_loss=float(sl_price),
                            take_profit=float(tp_price),
                            max_holding_bars=self.config.max_holding_bars,
                            strategy_name=self.name,
                            regime=str(regimes[i]),
                            risk_pips=float(risk_pips),
                            target_pips=float(tp_dist / self.pip_size),
                            metadata={"transition_quality": quality, "adx_delta": float(adx_delta)},
                        )
                    )

            # --- SHORT SIGNAL ---
            elif ema_stack[i] == -1 and high[i] >= ema_20[i] and close[i] <= ema_50[i]:
                if close[i] < open_p[i] and upper_wick[i] >= 0.25:
                    entry_price = close[i]
                    sl_dist = self.config.stop_atr_multiple * atr[i]
                    sl_price = entry_price + sl_dist
                    tp_dist = sl_dist * self.config.target_r_multiple
                    tp_price = entry_price - tp_dist
                    risk_pips = sl_dist / self.pip_size

                    signals.append(
                        TradeSignal(
                            timestamp=df.index[i],
                            symbol=self.symbol,
                            direction=-1,
                            entry_price=float(entry_price),
                            stop_loss=float(sl_price),
                            take_profit=float(tp_price),
                            max_holding_bars=self.config.max_holding_bars,
                            strategy_name=self.name,
                            regime=str(regimes[i]),
                            risk_pips=float(risk_pips),
                            target_pips=float(tp_dist / self.pip_size),
                            metadata={"transition_quality": quality, "adx_delta": float(adx_delta)},
                        )
                    )

        return signals

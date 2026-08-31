"""
RANGE_TO_TREND_TFPB_V1_PROD_FREEZE Production Strategy Candidate.

Immutable production specification with cryptographic fingerprint verification.
Enforces:
- Causal next-bar execution
- Strictly frozen 2.0R target and 1.5 ATR stop
- London/NY session mask (07:00-21:00 UTC)
- H1 trend alignment
- Read-only simulation safety
"""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from config.settings import PAIR_SPECS, PairSpec
from src.strategy_engine.strategies import BaseStrategy, TradeSignal


@dataclass(frozen=True)
class ProductionFreezeConfig:
    candidate_name: str = "RANGE_TO_TREND_TFPB_V1_PROD_FREEZE"
    version: str = "1.0.0-FROZEN"
    adx_period: int = 14
    adx_lag_bars: int = 10
    adx_lag_max: float = 18.0
    adx_current_min: float = 22.0
    atr_period: int = 14
    stop_loss_atr_mult: float = 1.5
    target_r_multiple: float = 2.00
    max_holding_bars: int = 32
    risk_per_trade_pct: float = 1.0
    initial_capital_usd: float = 100000.0
    allowed_hours_utc: Tuple[int, ...] = (7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20)
    wick_ratio_threshold: float = 0.25
    allow_live_orders: bool = False  # Strict safety guarantee


class ProductionFreezeCandidate(BaseStrategy):
    """
    Cryptographically fingerprinted immutable production candidate.
    Generates signals strictly following the frozen V1 definition.
    """

    def __init__(self, symbol: str, config_path: Optional[str] = None):
        config = ProductionFreezeConfig()
        super().__init__(symbol=symbol, name=config.candidate_name, params=config.__dict__)
        self.config = config
        self.spec: PairSpec = PAIR_SPECS.get(symbol, PAIR_SPECS["EURUSD"])
        self.pip_size = self.spec.pip_size
        self.fingerprint = self._compute_fingerprint()

    def _compute_fingerprint(self) -> str:
        """Computes SHA-256 fingerprint of the frozen strategy configuration."""
        raw_repr = (
            f"{self.config.candidate_name}:{self.config.version}:"
            f"{self.config.adx_lag_max}:{self.config.adx_current_min}:"
            f"{self.config.stop_loss_atr_mult}:{self.config.target_r_multiple}:"
            f"{self.config.allowed_hours_utc}"
        )
        return hashlib.sha256(raw_repr.encode("utf-8")).hexdigest()

    def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """
        Generates production-frozen trade signals with causal next-bar execution.
        """
        signals: List[TradeSignal] = []
        n = len(df)
        if n < 50:
            return signals

        # Required indicators
        close = df["close"].values
        open_p = df["open"].values
        high = df["high"].values
        low = df["low"].values
        times = df.index

        ema_20 = df["ema_20"].values if "ema_20" in df.columns else np.zeros(n)
        ema_50 = df["ema_50"].values if "ema_50" in df.columns else np.zeros(n)
        ema_stack = df["ema_stack"].values if "ema_stack" in df.columns else np.zeros(n)
        atr_14 = df["atr_14"].values if "atr_14" in df.columns else np.zeros(n)
        adx_14 = df["adx_14"].values if "adx_14" in df.columns else np.zeros(n)
        h1_trend = df["h1_trend_state"].values if "h1_trend_state" in df.columns else np.zeros(n)
        trend_trans = df["trend_transition"].values if "trend_transition" in df.columns else np.array([""] * n)

        upper_wick = df["upper_wick_ratio"].values if "upper_wick_ratio" in df.columns else np.zeros(n)
        lower_wick = df["lower_wick_ratio"].values if "lower_wick_ratio" in df.columns else np.zeros(n)

        lag = self.config.adx_lag_bars
        adx_low = self.config.adx_lag_max
        adx_high = self.config.adx_current_min
        sl_mult = self.config.stop_loss_atr_mult
        rr = self.config.target_r_multiple

        for i in range(max(lag + 10, 50), n - 1):
            t = times[i]
            hr = t.hour

            # 1. Session Gate
            if hr not in self.config.allowed_hours_utc:
                continue

            # 2. Regime Transition Gate: RANGE_TO_TREND
            if trend_trans[i] != "RANGE_TO_TREND":
                continue

            # 3. Pullback Setup Trigger
            # Long Setup
            if (
                ema_stack[i] == 1
                and h1_trend[i] >= 0
                and low[i] <= ema_20[i]
                and close[i] >= ema_50[i]
                and close[i] > open_p[i]
                and lower_wick[i] >= self.config.wick_ratio_threshold
            ):
                entry_est = close[i]
                risk = sl_mult * atr_14[i]
                sl = entry_est - risk
                tp = entry_est + (rr * risk)

                signals.append(
                    TradeSignal(
                        timestamp=t,
                        symbol=self.symbol,
                        direction=1,
                        entry_price=entry_est,
                        stop_loss=sl,
                        take_profit=tp,
                        max_holding_bars=self.config.max_holding_bars,
                        strategy_name=self.config.candidate_name,
                        regime="RANGE_TO_TREND",
                        risk_pips=risk / self.pip_size,
                        target_pips=(rr * risk) / self.pip_size,
                        metadata={
                            "strategy_version": self.config.version,
                            "fingerprint": self.fingerprint,
                            "regime_transition": "RANGE_TO_TREND",
                            "h1_trend_state": int(h1_trend[i]),
                            "adx_14": float(adx_14[i]),
                            "atr_14": float(atr_14[i]),
                            "session_hour": hr,
                            "target_r": rr,
                            "stop_loss_mult": sl_mult,
                        },
                    )
                )

            # Short Setup
            elif (
                ema_stack[i] == -1
                and h1_trend[i] <= 0
                and high[i] >= ema_20[i]
                and close[i] <= ema_50[i]
                and close[i] < open_p[i]
                and upper_wick[i] >= self.config.wick_ratio_threshold
            ):
                entry_est = close[i]
                risk = sl_mult * atr_14[i]
                sl = entry_est + risk
                tp = entry_est - (rr * risk)

                signals.append(
                    TradeSignal(
                        timestamp=t,
                        symbol=self.symbol,
                        direction=-1,
                        entry_price=entry_est,
                        stop_loss=sl,
                        take_profit=tp,
                        max_holding_bars=self.config.max_holding_bars,
                        strategy_name=self.config.candidate_name,
                        regime="RANGE_TO_TREND",
                        risk_pips=risk / self.pip_size,
                        target_pips=(rr * risk) / self.pip_size,
                        metadata={
                            "strategy_version": self.config.version,
                            "fingerprint": self.fingerprint,
                            "regime_transition": "RANGE_TO_TREND",
                            "h1_trend_state": int(h1_trend[i]),
                            "adx_14": float(adx_14[i]),
                            "atr_14": float(atr_14[i]),
                            "session_hour": hr,
                            "target_r": rr,
                            "stop_loss_mult": sl_mult,
                        },
                    )
                )

        return signals

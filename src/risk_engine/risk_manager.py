"""
Institutional Risk Management & Portfolio Guard Engine.
Enforces volatility position sizing, USD correlation limits, daily loss circuit breakers,
and abnormal volatility locks independently from strategy signals.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from config.settings import (
    PAIR_SPECS,
    DEFAULT_RISK_PER_TRADE_PCT,
    MAX_PORTFOLIO_CONCURRENT_RISK,
    MAX_USD_CONCURRENT_RISK,
    MAX_DAILY_PORTFOLIO_LOSS_PCT,
    MAX_TOTAL_DRAWDOWN_LIMIT,
)
from src.strategy_engine.strategies import TradeSignal


@dataclass
class SizingResult:
    is_approved: bool
    rejection_reason: Optional[str]
    lot_size: float
    units: float
    risk_amount_usd: float
    risk_pct_equity: float
    risk_pips: float


class RiskManager:
    """Independent Portfolio Risk Engine."""

    def __init__(
        self,
        account_equity: float = 100_000.0,
        risk_per_trade_pct: float = DEFAULT_RISK_PER_TRADE_PCT,
        max_portfolio_risk_pct: float = MAX_PORTFOLIO_CONCURRENT_RISK,
        max_usd_directional_risk_pct: float = MAX_USD_CONCURRENT_RISK,
        max_daily_loss_pct: float = MAX_DAILY_PORTFOLIO_LOSS_PCT,
        max_total_drawdown_pct: float = MAX_TOTAL_DRAWDOWN_LIMIT,
    ):
        self.equity = account_equity
        self.peak_equity = account_equity
        self.daily_starting_equity = account_equity
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_portfolio_risk_pct = max_portfolio_risk_pct
        self.max_usd_directional_risk_pct = max_usd_directional_risk_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_total_drawdown_pct = max_total_drawdown_pct

    def evaluate_signal_and_size(
        self,
        signal: TradeSignal,
        open_positions: List[Dict[str, Any]],
        current_spread_pips: float,
        current_atr_pips: float,
    ) -> SizingResult:
        """
        Evaluates portfolio constraints and calculates exact lot size based on volatility & account equity.
        """
        # 1. Check Global Drawdown Circuit Breaker
        current_dd = (self.peak_equity - self.equity) / self.peak_equity
        if current_dd >= self.max_total_drawdown_pct:
            return SizingResult(
                is_approved=False,
                rejection_reason=f"GLOBAL_DD_CIRCUIT_BREAKER_TRIGGERED ({current_dd*100:.1f}% >= {self.max_total_drawdown_pct*100:.1f}%)",
                lot_size=0.0, units=0.0, risk_amount_usd=0.0, risk_pct_equity=0.0, risk_pips=signal.risk_pips,
            )

        # 2. Check Daily Loss Limit
        daily_loss = (self.daily_starting_equity - self.equity) / self.daily_starting_equity
        if daily_loss >= self.max_daily_loss_pct:
            return SizingResult(
                is_approved=False,
                rejection_reason=f"DAILY_LOSS_LIMIT_REACHED ({daily_loss*100:.1f}% >= {self.max_daily_loss_pct*100:.1f}%)",
                lot_size=0.0, units=0.0, risk_amount_usd=0.0, risk_pct_equity=0.0, risk_pips=signal.risk_pips,
            )

        # 3. Spread / Volatility Gate
        spec = PAIR_SPECS.get(signal.symbol, PAIR_SPECS["EURUSD"])
        if current_spread_pips > (spec.base_spread_pips * 2.5):
            return SizingResult(
                is_approved=False,
                rejection_reason=f"SPREAD_TOO_WIDE ({current_spread_pips:.1f} pips > {spec.base_spread_pips * 2.5:.1f} threshold)",
                lot_size=0.0, units=0.0, risk_amount_usd=0.0, risk_pct_equity=0.0, risk_pips=signal.risk_pips,
            )

        # 4. Check Total Portfolio Concurrent Open Risk
        total_open_risk_pct = sum(pos.get("risk_pct", 0.0) for pos in open_positions)
        if (total_open_risk_pct + self.risk_per_trade_pct) > self.max_portfolio_risk_pct:
            return SizingResult(
                is_approved=False,
                rejection_reason=f"MAX_PORTFOLIO_RISK_EXCEEDED ({total_open_risk_pct*100:.1f}% open + {self.risk_per_trade_pct*100:.1f}% > {self.max_portfolio_risk_pct*100:.1f}%)",
                lot_size=0.0, units=0.0, risk_amount_usd=0.0, risk_pct_equity=0.0, risk_pips=signal.risk_pips,
            )

        # 5. Check USD Directional Correlation Risk
        # EURUSD Long = Short USD, GBPUSD Long = Short USD, USDJPY Long = Long USD
        usd_exposure_delta = 0.0
        if signal.symbol in ["EURUSD", "GBPUSD"]:
            usd_exposure_delta = -1.0 * signal.direction * self.risk_per_trade_pct
        elif signal.symbol == "USDJPY":
            usd_exposure_delta = 1.0 * signal.direction * self.risk_per_trade_pct

        current_usd_exposure = 0.0
        for pos in open_positions:
            pos_sym = pos.get("symbol", "")
            pos_dir = pos.get("direction", 0)
            pos_risk = pos.get("risk_pct", 0.0)
            if pos_sym in ["EURUSD", "GBPUSD"]:
                current_usd_exposure += -1.0 * pos_dir * pos_risk
            elif pos_sym == "USDJPY":
                current_usd_exposure += 1.0 * pos_dir * pos_risk

        new_usd_exposure = abs(current_usd_exposure + usd_exposure_delta)
        if new_usd_exposure > self.max_usd_directional_risk_pct:
            return SizingResult(
                is_approved=False,
                rejection_reason=f"MAX_USD_CONCURRENT_RISK_EXCEEDED ({new_usd_exposure*100:.1f}% > {self.max_usd_directional_risk_pct*100:.1f}%)",
                lot_size=0.0, units=0.0, risk_amount_usd=0.0, risk_pct_equity=0.0, risk_pips=signal.risk_pips,
            )

        # 6. Volatility Position Sizing Calculation
        # Risk Amount in USD = Equity * Risk %
        risk_usd = self.equity * self.risk_per_trade_pct
        risk_pips = signal.risk_pips
        if risk_pips <= 0:
            risk_pips = max(current_atr_pips * 1.5, 10.0)

        # Pip value for 1.0 standard lot ($100k) ~ $10 for EURUSD/GBPUSD, ~$6.50-10 for USDJPY
        pip_val_per_std_lot = 10.0
        if signal.symbol == "USDJPY" and signal.entry_price > 0:
            pip_val_per_std_lot = (100_000.0 * 0.01) / signal.entry_price

        # Standard Lots = Risk USD / (Risk Pips * Pip Value per lot)
        lots = risk_usd / (risk_pips * pip_val_per_std_lot + 1e-9)
        # Round to 2 decimal places (min 0.01 lot)
        lots_rounded = round(max(lots, 0.01), 2)
        units = lots_rounded * spec.contract_size

        return SizingResult(
            is_approved=True,
            rejection_reason=None,
            lot_size=lots_rounded,
            units=units,
            risk_amount_usd=round(risk_usd, 2),
            risk_pct_equity=self.risk_per_trade_pct,
            risk_pips=round(risk_pips, 1),
        )

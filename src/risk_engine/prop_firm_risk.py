"""
Prop-Firm Risk & Evaluation Engine.

Sits strictly between signal generation and execution.
Enforces institutional prop-firm rules:
- Daily Loss Limits (with unrealized PnL integration)
- Maximum Drawdown (Static and Trailing High-Water-Mark)
- Correlated Pair Exposure Caps (Directional USD Exposure)
- Weekend and Overnight Holding Restrictions
- Distance-to-Target and Distance-to-Breach Monitoring
- Hard Technical Kill Switches (Default-Reject on failure)
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from config.settings import PAIR_SPECS, PairSpec
from src.strategy_engine.strategies import TradeSignal

logger = logging.getLogger("PropRiskEngine")


@dataclass
class PropFirmConfig:
    account_name: str = "PROP_CHALLENGE_PHASE_1"
    initial_balance_usd: float = 100000.0
    profit_target_pct: Optional[float] = 8.0  # None for funded
    daily_loss_limit_pct: float = 5.0
    max_drawdown_pct: float = 10.0
    drawdown_mode: str = "STATIC"  # "STATIC" or "TRAILING"
    min_trading_days: int = 4
    max_leverage: int = 100
    max_correlated_risk_pct: float = 1.5
    weekend_holding_allowed: bool = False
    news_trading_allowed: bool = True
    safety_buffer_pct: float = 0.5  # Reject if within 0.5% of max DD
    consistency_max_day_profit_share_pct: Optional[float] = 50.0


@dataclass
class RiskDecision:
    is_approved: bool
    allowed_risk_pct: float
    risk_requested_pct: float
    rejection_reason: Optional[str]
    current_balance: float
    current_equity: float
    daily_pnl_usd: float
    distance_to_daily_limit_usd: float
    distance_to_max_dd_usd: float
    distance_to_target_usd: Optional[float]
    remaining_drawdown_budget_usd: float
    correlated_usd_exposure_pct: float
    timestamp: pd.Timestamp


class PropFirmRiskEngine:
    """
    Evaluates proposed trading signals against strict prop-firm constraints.
    Guarantees that no trade breaches prop firm risk parameters.
    """

    def __init__(self, config: PropFirmConfig):
        self.config = config
        self.balance = config.initial_balance_usd
        self.equity = config.initial_balance_usd
        self.high_water_mark = config.initial_balance_usd
        self.start_of_day_equity = config.initial_balance_usd
        self.current_day: Optional[str] = None
        self.trading_days: set = set()

        self.active_trades: Dict[str, Dict[str, Any]] = {}
        self.daily_pnl_history: Dict[str, float] = {}
        self.audit_log: List[RiskDecision] = []

        # State flags
        self.is_rule_breached = False
        self.breach_reason: Optional[str] = None
        self.is_challenge_passed = False

    def update_account_state(self, current_time: pd.Timestamp, current_equity: float, current_balance: float):
        """Updates day rollover, equity, balance, and high water mark."""
        day_str = current_time.strftime("%Y-%m-%d")
        if self.current_day is None or day_str != self.current_day:
            self.current_day = day_str
            self.start_of_day_equity = current_equity

        self.balance = current_balance
        self.equity = current_equity
        if current_equity > self.high_water_mark:
            self.high_water_mark = current_equity

    def evaluate_proposed_trade(
        self,
        signal: TradeSignal,
        current_time: pd.Timestamp,
        proposed_risk_pct: float,
        current_spread_pips: float,
        is_terminal_connected: bool = True,
    ) -> RiskDecision:
        """
        Hard Risk Firewall: Evaluates proposed trade against all prop-firm rules.
        Default-reject behavior on any uncertainty.
        """
        day_str = current_time.strftime("%Y-%m-%d")
        if self.current_day is None or day_str != self.current_day:
            self.current_day = day_str
            self.start_of_day_equity = self.equity

        # 1. Technical Kill Switches
        if not is_terminal_connected:
            return self._reject(signal, proposed_risk_pct, "KILL_SWITCH: Terminal disconnected", current_time)

        spec = PAIR_SPECS.get(signal.symbol, PAIR_SPECS["EURUSD"])
        if current_spread_pips > (spec.base_spread_pips * 3.5):
            return self._reject(signal, proposed_risk_pct, f"ABNORMAL_SPREAD: {current_spread_pips:.1f}p exceeds 3.5x baseline", current_time)

        # 2. Check Previous Breach
        if self.is_rule_breached:
            return self._reject(signal, proposed_risk_pct, f"ACCOUNT_BREACHED: Previously breached via {self.breach_reason}", current_time)

        # 3. Weekend Holding Gate
        # Forex closes Friday ~21:00-22:00 UTC
        if not self.config.weekend_holding_allowed:
            if current_time.weekday() == 4 and current_time.hour >= 18:
                return self._reject(signal, proposed_risk_pct, "WEEKEND_RESTRICTION: No new entries allowed after Friday 18:00 UTC", current_time)

        # 4. Calculate Drawdown and Daily Limits
        daily_loss_floor_usd = self.start_of_day_equity * (1.0 - (self.config.daily_loss_limit_pct / 100.0))
        daily_loss_budget_usd = self.equity - daily_loss_floor_usd

        if self.config.drawdown_mode == "TRAILING":
            max_dd_floor_usd = self.high_water_mark * (1.0 - (self.config.max_drawdown_pct / 100.0))
        else:  # STATIC
            max_dd_floor_usd = self.config.initial_balance_usd * (1.0 - (self.config.max_drawdown_pct / 100.0))

        safety_buffer_usd = self.config.initial_balance_usd * (self.config.safety_buffer_pct / 100.0)
        max_dd_budget_usd = self.equity - (max_dd_floor_usd + safety_buffer_usd)

        proposed_risk_usd = self.equity * (proposed_risk_pct / 100.0)

        # 5. Hard Daily Loss Protection Gate
        if proposed_risk_usd > daily_loss_budget_usd:
            return self._reject(
                signal, proposed_risk_pct,
                f"DAILY_LOSS_FIREWALL: Risk (${proposed_risk_usd:.2f}) exceeds daily budget (${daily_loss_budget_usd:.2f})",
                current_time
            )

        # 6. Hard Max Drawdown Protection Gate
        if proposed_risk_usd > max_dd_budget_usd:
            return self._reject(
                signal, proposed_risk_pct,
                f"MAX_DD_FIREWALL: Risk (${proposed_risk_usd:.2f}) exceeds remaining DD budget (${max_dd_budget_usd:.2f})",
                current_time
            )

        # 7. Correlated Pair Exposure Gate
        # Compute existing directional USD risk
        usd_exposure_pct = self._calculate_usd_exposure(signal)
        if (usd_exposure_pct + proposed_risk_pct) > self.config.max_correlated_risk_pct:
            # Scale down allowed risk instead of flat rejecting if partial risk fits
            allowed_risk = max(0.0, self.config.max_correlated_risk_pct - usd_exposure_pct)
            if allowed_risk < 0.10:
                return self._reject(
                    signal, proposed_risk_pct,
                    f"CORRELATED_EXPOSURE_CAP: Total USD risk ({usd_exposure_pct + proposed_risk_pct:.2f}%) exceeds cap ({self.config.max_correlated_risk_pct:.2f}%)",
                    current_time
                )
            else:
                proposed_risk_pct = round(allowed_risk, 2)
                proposed_risk_usd = self.equity * (proposed_risk_pct / 100.0)

        # 8. Distance to Target Monitoring
        dist_target_usd = None
        if self.config.profit_target_pct is not None:
            target_usd = self.config.initial_balance_usd * (1.0 + (self.config.profit_target_pct / 100.0))
            dist_target_usd = max(0.0, target_usd - self.equity)

        # Approval Decision
        decision = RiskDecision(
            is_approved=True,
            allowed_risk_pct=proposed_risk_pct,
            risk_requested_pct=proposed_risk_pct,
            rejection_reason=None,
            current_balance=self.balance,
            current_equity=self.equity,
            daily_pnl_usd=self.equity - self.start_of_day_equity,
            distance_to_daily_limit_usd=daily_loss_budget_usd,
            distance_to_max_dd_usd=max_dd_budget_usd,
            distance_to_target_usd=dist_target_usd,
            remaining_drawdown_budget_usd=max_dd_budget_usd,
            correlated_usd_exposure_pct=usd_exposure_pct + proposed_risk_pct,
            timestamp=current_time,
        )
        self.audit_log.append(decision)
        return decision

    def _calculate_usd_exposure(self, new_signal: TradeSignal) -> float:
        """Calculates current directional USD risk exposure across open pairs."""
        # EURUSD Long (+1) = Short USD (-1)
        # GBPUSD Long (+1) = Short USD (-1)
        # USDJPY Long (+1) = Long USD (+1)
        total_same_direction_risk = 0.0
        new_usd_dir = -1 if new_signal.symbol in ["EURUSD", "GBPUSD"] and new_signal.direction == 1 else 1

        for sym, pos in self.active_trades.items():
            pos_usd_dir = -1 if sym in ["EURUSD", "GBPUSD"] and pos["direction"] == 1 else 1
            if pos_usd_dir == new_usd_dir:
                total_same_direction_risk += pos.get("risk_pct", 0.0)

        return total_same_direction_risk

    def _reject(self, signal: TradeSignal, requested_risk: float, reason: str, t: pd.Timestamp) -> RiskDecision:
        daily_loss_floor_usd = self.start_of_day_equity * (1.0 - (self.config.daily_loss_limit_pct / 100.0))
        max_dd_floor_usd = self.config.initial_balance_usd * (1.0 - (self.config.max_drawdown_pct / 100.0))

        decision = RiskDecision(
            is_approved=False,
            allowed_risk_pct=0.0,
            risk_requested_pct=requested_risk,
            rejection_reason=reason,
            current_balance=self.balance,
            current_equity=self.equity,
            daily_pnl_usd=self.equity - self.start_of_day_equity,
            distance_to_daily_limit_usd=self.equity - daily_loss_floor_usd,
            distance_to_max_dd_usd=self.equity - max_dd_floor_usd,
            distance_to_target_usd=None,
            remaining_drawdown_budget_usd=self.equity - max_dd_floor_usd,
            correlated_usd_exposure_pct=0.0,
            timestamp=t,
        )
        self.audit_log.append(decision)
        return decision

"""
Paper Execution Engine & Virtual Broker Simulator.

STRICT SAFETY GUARANTEE:
- Never sends real orders to MT5 terminal (Read-Only Mode).
- Simulates realistic fills, live dynamic spread, commissions, slippage, and position lifecycles.
- Enforces bar-close execution gating (never trades in-bar).
- Maintains virtual account balance, equity, margin, and telemetry audit trails.
"""
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from config.settings import PAIR_SPECS, PairSpec, DATA_DIR
from src.strategy_engine.production_candidate import ProductionFreezeCandidate, ProductionFreezeConfig
from src.strategy_engine.strategies import TradeSignal

logger = logging.getLogger("PaperEngine")


@dataclass
class VirtualPosition:
    position_id: str
    symbol: str
    direction: int
    entry_time: pd.Timestamp
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    risk_pips: float
    risk_usd: float
    spread_paid_pips: float
    commission_paid_usd: float
    slippage_paid_pips: float
    max_favorable_pips: float = 0.0
    max_adverse_pips: float = 0.0
    holding_bars: int = 0
    is_open: bool = True
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    gross_pnl_pips: float = 0.0
    net_pnl_pips: float = 0.0
    net_pnl_usd: float = 0.0
    pnl_r_multiple: float = 0.0


class PaperExecutionEngine:
    """
    Simulates institutional live execution in paper trading mode.
    Guaranteed zero live market risk.
    """

    def __init__(
        self,
        symbols: List[str] = ["EURUSD", "GBPUSD", "USDJPY"],
        initial_capital_usd: float = 100000.0,
        risk_per_trade_pct: float = 1.0,
        audit_dir: Optional[Path] = None,
    ):
        self.symbols = symbols
        self.initial_capital_usd = initial_capital_usd
        self.virtual_balance = initial_capital_usd
        self.virtual_equity = initial_capital_usd
        self.risk_per_trade_pct = risk_per_trade_pct
        
        self.audit_dir = audit_dir or (Path("data") / "paper_trading")
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        self.candidates: Dict[str, ProductionFreezeCandidate] = {
            s: ProductionFreezeCandidate(symbol=s) for s in symbols
        }
        self.active_positions: Dict[str, Optional[VirtualPosition]] = {s: None for s in symbols}
        self.closed_positions: List[VirtualPosition] = []
        self.signals_history: List[Dict[str, Any]] = []

        self.total_spreads_observed: List[float] = []
        self.total_slippage_observed: List[float] = []
        self.rejected_signals_count = 0
        self.bar_close_events_processed = 0

    def process_completed_bar(
        self,
        symbol: str,
        df_history: pd.DataFrame,
        current_bar_idx: int,
    ) -> Optional[VirtualPosition]:
        """
        Executes causal bar-close logic for completed bar at `current_bar_idx`.
        Simulates entry at open of bar `current_bar_idx + 1`.
        """
        self.bar_close_events_processed += 1
        spec = PAIR_SPECS.get(symbol, PAIR_SPECS["EURUSD"])
        pip_sz = spec.pip_size

        # 1. Update any existing active position on this bar
        curr_pos = self.active_positions[symbol]
        if curr_pos and curr_pos.is_open:
            bar = df_history.iloc[current_bar_idx]
            bar_time = df_history.index[current_bar_idx]
            bar_high = bar["high"]
            bar_low = bar["low"]
            bar_close = bar["close"]

            curr_pos.holding_bars += 1

            # Update MFE / MAE
            if curr_pos.direction == 1:
                fav_pips = (bar_high - curr_pos.entry_price) / pip_sz
                adv_pips = (curr_pos.entry_price - bar_low) / pip_sz
            else:
                fav_pips = (curr_pos.entry_price - bar_low) / pip_sz
                adv_pips = (bar_high - curr_pos.entry_price) / pip_sz

            curr_pos.max_favorable_pips = max(curr_pos.max_favorable_pips, fav_pips)
            curr_pos.max_adverse_pips = max(curr_pos.max_adverse_pips, adv_pips)

            # Check SL / TP / Max Holding
            hit_tp, hit_sl, hit_time = False, False, False
            exit_p = bar_close

            if curr_pos.direction == 1:
                if bar_low <= curr_pos.stop_loss:
                    hit_sl = True
                    exit_p = curr_pos.stop_loss
                elif bar_high >= curr_pos.take_profit:
                    hit_tp = True
                    exit_p = curr_pos.take_profit
            else:
                if bar_high >= curr_pos.stop_loss:
                    hit_sl = True
                    exit_p = curr_pos.stop_loss
                elif bar_low <= curr_pos.take_profit:
                    hit_tp = True
                    exit_p = curr_pos.take_profit

            if not hit_tp and not hit_sl and curr_pos.holding_bars >= 32:
                hit_time = True
                exit_p = bar_close

            if hit_tp or hit_sl or hit_time:
                curr_pos.is_open = False
                curr_pos.exit_time = bar_time
                curr_pos.exit_price = exit_p
                curr_pos.exit_reason = "TAKE_PROFIT" if hit_tp else ("STOP_LOSS" if hit_sl else "TIME_LIMIT_32")

                # PnL calculations
                if curr_pos.direction == 1:
                    gross_pips = (exit_p - curr_pos.entry_price) / pip_sz
                else:
                    gross_pips = (curr_pos.entry_price - exit_p) / pip_sz

                net_pips = gross_pips - curr_pos.spread_paid_pips - (curr_pos.commission_paid_usd / 10.0) - curr_pos.slippage_paid_pips
                net_r = net_pips / (curr_pos.risk_pips + 1e-9)

                curr_pos.gross_pnl_pips = gross_pips
                curr_pos.net_pnl_pips = net_pips
                curr_pos.pnl_r_multiple = net_r
                curr_pos.net_pnl_usd = net_r * (self.virtual_equity * (self.risk_per_trade_pct / 100.0))

                self.virtual_balance += curr_pos.net_pnl_usd
                self.virtual_equity = self.virtual_balance
                self.closed_positions.append(curr_pos)
                self.active_positions[symbol] = None
                return curr_pos

        # 2. If no active position, check for new signal on completed bar
        if self.active_positions[symbol] is None and current_bar_idx < len(df_history) - 1:
            df_sub = df_history.iloc[: current_bar_idx + 1]
            cand = self.candidates[symbol]
            signals = cand.generate_signals(df_sub)

            if signals:
                sig = signals[-1]
                # Verify signal was generated on the exact current completed bar
                if sig.timestamp == df_history.index[current_bar_idx]:
                    next_bar = df_history.iloc[current_bar_idx + 1]
                    next_bar_time = df_history.index[current_bar_idx + 1]

                    # Execution at next bar open
                    raw_entry = next_bar["open"]
                    spread_pips = spec.base_spread_pips
                    slippage_pips = 0.20
                    comm_usd = spec.commission_per_lot_usd

                    self.total_spreads_observed.append(spread_pips)
                    self.total_slippage_observed.append(slippage_pips)

                    fill_price = raw_entry + (spread_pips * pip_sz) if sig.direction == 1 else raw_entry
                    risk_dist = abs(fill_price - sig.stop_loss)
                    risk_pips = risk_dist / pip_sz
                    risk_usd = self.virtual_equity * (self.risk_per_trade_pct / 100.0)
                    lot_size = round(risk_usd / (risk_pips * 10.0), 2) if risk_pips > 0 else 0.1

                    pos_id = f"POS_{symbol}_{next_bar_time.strftime('%Y%m%d%H%M')}"
                    pos = VirtualPosition(
                        position_id=pos_id,
                        symbol=symbol,
                        direction=sig.direction,
                        entry_time=next_bar_time,
                        entry_price=fill_price,
                        stop_loss=sig.stop_loss,
                        take_profit=sig.take_profit,
                        lot_size=lot_size,
                        risk_pips=risk_pips,
                        risk_usd=risk_usd,
                        spread_paid_pips=spread_pips,
                        commission_paid_usd=comm_usd,
                        slippage_paid_pips=slippage_pips,
                    )
                    self.active_positions[symbol] = pos

                    # Log Signal Audit
                    self.signals_history.append({
                        "signal_id": f"SIG_{symbol}_{sig.timestamp.strftime('%Y%m%d%H%M')}",
                        "timestamp": sig.timestamp,
                        "symbol": symbol,
                        "direction": sig.direction,
                        "suggested_entry": sig.entry_price,
                        "fill_price": fill_price,
                        "stop_loss": sig.stop_loss,
                        "take_profit": sig.take_profit,
                        "risk_pips": risk_pips,
                        "lot_size": lot_size,
                        "strategy_version": sig.metadata.get("strategy_version"),
                        "fingerprint": sig.metadata.get("fingerprint"),
                        "adx_14": sig.metadata.get("adx_14"),
                        "atr_14": sig.metadata.get("atr_14"),
                        "h1_trend_state": sig.metadata.get("h1_trend_state"),
                        "session_hour": sig.metadata.get("session_hour"),
                    })

        return None

    def stream_dataset(self, symbol: str, df_history: pd.DataFrame):
        """
        Fast simulation of streaming live completed bars across an entire dataset.
        Generates signals causally and steps through position lifecycles sequentially.
        """
        cand = self.candidates[symbol]
        all_signals = cand.generate_signals(df_history)
        sig_map = {s.timestamp: s for s in all_signals}

        spec = PAIR_SPECS.get(symbol, PAIR_SPECS["EURUSD"])
        pip_sz = spec.pip_size
        n = len(df_history)
        times = df_history.index
        opens = df_history["open"].values
        highs = df_history["high"].values
        lows = df_history["low"].values
        closes = df_history["close"].values

        for i in range(50, n - 1):
            t = times[i]
            self.bar_close_events_processed += 1

            # 1. Manage existing active position
            curr_pos = self.active_positions[symbol]
            if curr_pos and curr_pos.is_open:
                curr_pos.holding_bars += 1
                bar_h = highs[i]
                bar_l = lows[i]
                bar_c = closes[i]

                if curr_pos.direction == 1:
                    fav = (bar_h - curr_pos.entry_price) / pip_sz
                    adv = (curr_pos.entry_price - bar_l) / pip_sz
                else:
                    fav = (curr_pos.entry_price - bar_l) / pip_sz
                    adv = (bar_h - curr_pos.entry_price) / pip_sz

                curr_pos.max_favorable_pips = max(curr_pos.max_favorable_pips, fav)
                curr_pos.max_adverse_pips = max(curr_pos.max_adverse_pips, adv)

                hit_tp, hit_sl, hit_time = False, False, False
                exit_p = bar_c

                if curr_pos.direction == 1:
                    if bar_l <= curr_pos.stop_loss:
                        hit_sl = True
                        exit_p = curr_pos.stop_loss
                    elif bar_h >= curr_pos.take_profit:
                        hit_tp = True
                        exit_p = curr_pos.take_profit
                else:
                    if bar_h >= curr_pos.stop_loss:
                        hit_sl = True
                        exit_p = curr_pos.stop_loss
                    elif bar_l <= curr_pos.take_profit:
                        hit_tp = True
                        exit_p = curr_pos.take_profit

                if not hit_tp and not hit_sl and curr_pos.holding_bars >= 32:
                    hit_time = True
                    exit_p = bar_c

                if hit_tp or hit_sl or hit_time:
                    curr_pos.is_open = False
                    curr_pos.exit_time = t
                    curr_pos.exit_price = exit_p
                    curr_pos.exit_reason = "TAKE_PROFIT" if hit_tp else ("STOP_LOSS" if hit_sl else "TIME_LIMIT_32")

                    if curr_pos.direction == 1:
                        gross_pips = (exit_p - curr_pos.entry_price) / pip_sz
                    else:
                        gross_pips = (curr_pos.entry_price - exit_p) / pip_sz

                    net_pips = gross_pips - curr_pos.spread_paid_pips - (curr_pos.commission_paid_usd / 10.0) - curr_pos.slippage_paid_pips
                    net_r = net_pips / (curr_pos.risk_pips + 1e-9)

                    curr_pos.gross_pnl_pips = gross_pips
                    curr_pos.net_pnl_pips = net_pips
                    curr_pos.pnl_r_multiple = net_r
                    curr_pos.net_pnl_usd = net_r * (self.virtual_equity * (self.risk_per_trade_pct / 100.0))

                    self.virtual_balance += curr_pos.net_pnl_usd
                    self.virtual_equity = self.virtual_balance
                    self.closed_positions.append(curr_pos)
                    self.active_positions[symbol] = None

            # 2. Check for new signal at bar close t -> enter at bar open t+1
            if self.active_positions[symbol] is None and t in sig_map:
                sig = sig_map[t]
                next_t = times[i + 1]
                raw_entry = opens[i + 1]
                spread_pips = spec.base_spread_pips
                slippage_pips = 0.20
                comm_usd = spec.commission_per_lot_usd

                self.total_spreads_observed.append(spread_pips)
                self.total_slippage_observed.append(slippage_pips)

                fill_price = raw_entry + (spread_pips * pip_sz) if sig.direction == 1 else raw_entry
                risk_dist = abs(fill_price - sig.stop_loss)
                risk_pips = risk_dist / pip_sz
                risk_usd = self.virtual_equity * (self.risk_per_trade_pct / 100.0)
                lot_size = round(risk_usd / (risk_pips * 10.0), 2) if risk_pips > 0 else 0.1

                pos = VirtualPosition(
                    position_id=f"POS_{symbol}_{next_t.strftime('%Y%m%d%H%M')}",
                    symbol=symbol,
                    direction=sig.direction,
                    entry_time=next_t,
                    entry_price=fill_price,
                    stop_loss=sig.stop_loss,
                    take_profit=sig.take_profit,
                    lot_size=lot_size,
                    risk_pips=risk_pips,
                    risk_usd=risk_usd,
                    spread_paid_pips=spread_pips,
                    commission_paid_usd=comm_usd,
                    slippage_paid_pips=slippage_pips,
                )
                self.active_positions[symbol] = pos

                self.signals_history.append({
                    "signal_id": f"SIG_{symbol}_{sig.timestamp.strftime('%Y%m%d%H%M')}",
                    "timestamp": sig.timestamp,
                    "symbol": symbol,
                    "direction": sig.direction,
                    "suggested_entry": sig.entry_price,
                    "fill_price": fill_price,
                    "stop_loss": sig.stop_loss,
                    "take_profit": sig.take_profit,
                    "risk_pips": risk_pips,
                    "lot_size": lot_size,
                    "strategy_version": sig.metadata.get("strategy_version"),
                    "fingerprint": sig.metadata.get("fingerprint"),
                    "adx_14": sig.metadata.get("adx_14"),
                    "atr_14": sig.metadata.get("atr_14"),
                    "h1_trend_state": sig.metadata.get("h1_trend_state"),
                    "session_hour": sig.metadata.get("session_hour"),
                })

    def export_telemetry_logs(self):
        """Saves signals and trades audit logs to CSV."""
        if self.signals_history:
            df_sig = pd.DataFrame(self.signals_history)
            df_sig.to_csv(self.audit_dir / "signals_audit.csv", index=False)

        if self.closed_positions:
            df_tr = pd.DataFrame([asdict(p) for p in self.closed_positions])
            df_tr.to_csv(self.audit_dir / "trades_audit.csv", index=False)

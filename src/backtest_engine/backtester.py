"""
Realistic Event-Driven & Vector Backtesting Engine for Forex Systems.
Enforces zero look-ahead, realistic bid/ask spreads, slippage, commission, and intra-bar collision logic.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from config.settings import PAIR_SPECS, PairSpec
from src.strategy_engine.strategies import TradeSignal


@dataclass
class ExecutedTrade:
    trade_id: int
    symbol: str
    strategy_name: str
    direction: int  # +1 Long, -1 Short
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp
    exit_price: float
    exit_reason: str  # "TP", "SL", "TIME_EXPIRY"
    stop_loss: float
    take_profit: float
    holding_bars: int
    risk_pips: float
    pnl_gross_pips: float
    spread_cost_pips: float
    slippage_cost_pips: float
    commission_pips: float
    pnl_net_pips: float
    pnl_r_multiple: float
    regime: str
    session: str
    year: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class RealisticBacktester:
    """
    Simulates realistic order execution with strict causality and comprehensive cost accounting.
    """

    def __init__(
        self,
        symbol: str,
        cost_multiplier: float = 1.0,
        fixed_spread_pips: Optional[float] = None,
        fixed_slippage_pips: Optional[float] = None,
        commission_per_lot_usd: float = 7.0,
        initial_capital: float = 100_000.0,
        risk_per_trade_pct: float = 0.01,
    ):
        self.symbol = symbol
        self.spec: PairSpec = PAIR_SPECS.get(symbol, PAIR_SPECS["EURUSD"])
        self.pip_size = self.spec.pip_size
        self.cost_multiplier = cost_multiplier
        self.base_spread_pips = (fixed_spread_pips or self.spec.base_spread_pips) * cost_multiplier
        self.base_slippage_pips = (fixed_slippage_pips or self.spec.base_slippage_pips) * cost_multiplier
        # Commission in pips: $7 round turn on $100k standard lot = ~0.7 pips for EURUSD/GBPUSD
        self.commission_pips = (commission_per_lot_usd / 10.0) * cost_multiplier
        self.initial_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct

    def run_backtest(
        self,
        df: pd.DataFrame,
        signals: List[TradeSignal],
    ) -> Tuple[List[ExecutedTrade], pd.DataFrame]:
        """
        Executes signals sequentially on the price series.
        """
        if not signals or len(df) == 0:
            return [], pd.DataFrame()

        # Build index mapping for fast lookups
        ts_to_idx = {ts: idx for idx, ts in enumerate(df.index)}
        n_bars = len(df)
        times = df.index
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        spreads_pts = df["spread"].values if "spread" in df.columns else np.zeros(n_bars)

        executed_trades: List[ExecutedTrade] = []
        trade_id = 1
        active_trade_until_idx = -1  # Prevent overlapping duplicate fills if single-position model

        for sig in signals:
            if sig.timestamp not in ts_to_idx:
                continue

            sig_idx = ts_to_idx[sig.timestamp]
            entry_idx = sig_idx + 1  # Strictly execute at Open of bar t+1

            if entry_idx >= n_bars:
                continue  # End of data

            # Filter if already in active trade (sequential non-stacking)
            if entry_idx <= active_trade_until_idx:
                continue

            # Determine dynamic spread at entry
            spread_pips = (spreads_pts[entry_idx] * 0.1) if spreads_pts[entry_idx] > 0 else self.base_spread_pips
            spread_pips = max(spread_pips * self.cost_multiplier, self.base_spread_pips)
            slippage_pips = self.base_slippage_pips

            # Calculate actual execution entry price
            raw_entry = opens[entry_idx]
            if sig.direction == 1:  # Buy at Ask
                exec_entry = raw_entry + (spread_pips * 0.5 + slippage_pips) * self.pip_size
            else:  # Sell at Bid
                exec_entry = raw_entry - (spread_pips * 0.5 + slippage_pips) * self.pip_size

            # Evaluate intra-bar path forward
            max_bars = sig.max_holding_bars
            end_idx = min(entry_idx + max_bars, n_bars - 1)

            exit_reason = "TIME_EXPIRY"
            exit_idx = end_idx
            raw_exit = closes[end_idx]

            for bar_idx in range(entry_idx, end_idx + 1):
                bar_h = highs[bar_idx]
                bar_l = lows[bar_idx]

                if sig.direction == 1:  # LONG
                    hit_sl = bar_l <= sig.stop_loss
                    hit_tp = bar_h >= sig.take_profit

                    if hit_sl and hit_tp:
                        # Conservative worst-case assumption: SL triggered first
                        exit_reason = "SL"
                        exit_idx = bar_idx
                        raw_exit = sig.stop_loss
                        break
                    elif hit_sl:
                        exit_reason = "SL"
                        exit_idx = bar_idx
                        raw_exit = sig.stop_loss
                        break
                    elif hit_tp:
                        exit_reason = "TP"
                        exit_idx = bar_idx
                        raw_exit = sig.take_profit
                        break

                else:  # SHORT
                    hit_sl = bar_h >= sig.stop_loss
                    hit_tp = bar_l <= sig.take_profit

                    if hit_sl and hit_tp:
                        # Conservative worst-case assumption: SL triggered first
                        exit_reason = "SL"
                        exit_idx = bar_idx
                        raw_exit = sig.stop_loss
                        break
                    elif hit_sl:
                        exit_reason = "SL"
                        exit_idx = bar_idx
                        raw_exit = sig.stop_loss
                        break
                    elif hit_tp:
                        exit_reason = "TP"
                        exit_idx = bar_idx
                        raw_exit = sig.take_profit
                        break

            # Calculate actual execution exit price (incorporating exit spread & slippage)
            exit_spread_pips = (spreads_pts[exit_idx] * 0.1) if spreads_pts[exit_idx] > 0 else self.base_spread_pips
            exit_spread_pips = max(exit_spread_pips * self.cost_multiplier, self.base_spread_pips)
            
            if sig.direction == 1:  # Close Long at Bid
                exec_exit = raw_exit - (exit_spread_pips * 0.5 + slippage_pips) * self.pip_size
                gross_pips = (raw_exit - raw_entry) / self.pip_size
                net_pips = (exec_exit - exec_entry) / self.pip_size - self.commission_pips
            else:  # Close Short at Ask
                exec_exit = raw_exit + (exit_spread_pips * 0.5 + slippage_pips) * self.pip_size
                gross_pips = (raw_entry - raw_exit) / self.pip_size
                net_pips = (exec_entry - exec_exit) / self.pip_size - self.commission_pips

            total_spread_cost = spread_pips
            total_slippage_cost = 2.0 * slippage_pips
            r_multiple = net_pips / (sig.risk_pips + 1e-9)

            # Session classification at entry
            entry_hour = times[entry_idx].hour
            session_str = "ASIAN" if (0 <= entry_hour < 7) else ("LONDON" if (7 <= entry_hour < 12) else ("OVERLAP" if (12 <= entry_hour < 16) else "NY_LATE"))

            trade = ExecutedTrade(
                trade_id=trade_id,
                symbol=self.symbol,
                strategy_name=sig.strategy_name,
                direction=sig.direction,
                signal_time=sig.timestamp,
                entry_time=times[entry_idx],
                entry_price=float(exec_entry),
                exit_time=times[exit_idx],
                exit_price=float(exec_exit),
                exit_reason=exit_reason,
                stop_loss=float(sig.stop_loss),
                take_profit=float(sig.take_profit),
                holding_bars=exit_idx - entry_idx + 1,
                risk_pips=float(sig.risk_pips),
                pnl_gross_pips=float(gross_pips),
                spread_cost_pips=float(total_spread_cost),
                slippage_cost_pips=float(total_slippage_cost),
                commission_pips=float(self.commission_pips),
                pnl_net_pips=float(net_pips),
                pnl_r_multiple=float(r_multiple),
                regime=sig.regime,
                session=session_str,
                year=times[entry_idx].year,
                metadata=sig.metadata,
            )

            executed_trades.append(trade)
            trade_id += 1
            active_trade_until_idx = exit_idx

        trades_df = pd.DataFrame([asdict(t) for t in executed_trades]) if executed_trades else pd.DataFrame()
        return executed_trades, trades_df

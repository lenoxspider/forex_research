"""
MetaTrader 5 Live & Paper Execution Bridge.
Consumes discrete TradeSignals produced by the validated strategy engine, verifies risk rules,
and executes orders directly via the official MT5 Python API (or simulates in paper-trading mode).
"""
import logging
from typing import Dict, List, Optional, Any
import pandas as pd

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from config.settings import PAIR_SPECS, PairSpec
from src.strategy_engine.strategies import TradeSignal
from src.risk_engine.risk_manager import RiskManager, SizingResult

logger = logging.getLogger("ExecutionEngine.MT5Trader")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class MT5ExecutionBridge:
    """Interfaces with MT5 for real-time paper trading and live order execution."""

    def __init__(
        self,
        risk_manager: Optional[RiskManager] = None,
        is_paper_trading: bool = True,
        magic_number: int = 7771337,
    ):
        self.risk_manager = risk_manager or RiskManager()
        self.is_paper_trading = is_paper_trading
        self.magic_number = magic_number
        self.connected = False

    def connect(self) -> bool:
        if self.is_paper_trading:
            logger.info("Running in PAPER TRADING simulation mode.")
            self.connected = True
            return True

        if mt5 is None:
            logger.error("MetaTrader 5 python package not available.")
            return False

        if not mt5.initialize():
            logger.error(f"MT5 Init failed: {mt5.last_error()}")
            return False

        self.connected = True
        account_info = mt5.account_info()
        if account_info:
            logger.info(f"Connected to MT5 Live Account: {account_info.login}, Balance: ${account_info.balance:.2f}, Equity: ${account_info.equity:.2f}")
            self.risk_manager.equity = float(account_info.equity)
            self.risk_manager.daily_starting_equity = float(account_info.equity)
        return True

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Queries currently active positions in MT5."""
        if self.is_paper_trading or mt5 is None:
            return []

        positions = mt5.positions_get()
        if positions is None:
            return []

        active = []
        for pos in positions:
            active.append({
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "type": pos.type,
                "direction": 1 if pos.type == mt5.POSITION_TYPE_BUY else -1,
                "volume": pos.volume,
                "price_open": pos.price_open,
                "sl": pos.sl,
                "tp": pos.tp,
                "profit": pos.profit,
                "risk_pct": 0.01,  # baseline estimate
            })
        return active

    def execute_signal(
        self,
        signal: TradeSignal,
        current_spread_pips: float = 1.0,
        current_atr_pips: float = 15.0,
    ) -> Dict[str, Any]:
        """
        Validates signal against independent risk engine and sends market order to MT5.
        """
        open_positions = self.get_open_positions()

        # Evaluate risk constraints
        sizing: SizingResult = self.risk_manager.evaluate_signal_and_size(
            signal,
            open_positions,
            current_spread_pips=current_spread_pips,
            current_atr_pips=current_atr_pips,
        )

        if not sizing.is_approved:
            logger.warning(f"Trade REJECTED by Risk Engine: {sizing.rejection_reason}")
            return {
                "status": "REJECTED",
                "reason": sizing.rejection_reason,
                "signal": signal.__dict__,
            }

        logger.info(
            f"Trade APPROVED: {signal.symbol} {'BUY' if signal.direction == 1 else 'SELL'} "
            f"Lots: {sizing.lot_size}, SL: {signal.stop_loss}, TP: {signal.take_profit}, Risk: ${sizing.risk_amount_usd}"
        )

        if self.is_paper_trading:
            return {
                "status": "FILLED_PAPER",
                "symbol": signal.symbol,
                "direction": signal.direction,
                "lot_size": sizing.lot_size,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "risk_usd": sizing.risk_amount_usd,
            }

        # Send Live MT5 Order
        order_type = mt5.ORDER_TYPE_BUY if signal.direction == 1 else mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(signal.symbol)
        if tick is None:
            logger.error(f"Failed to get tick for {signal.symbol}")
            return {"status": "FAILED", "reason": "NO_TICK"}

        price = tick.ask if signal.direction == 1 else tick.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": signal.symbol,
            "volume": float(sizing.lot_size),
            "type": order_type,
            "price": float(price),
            "sl": float(signal.stop_loss),
            "tp": float(signal.take_profit),
            "deviation": 10,
            "magic": self.magic_number,
            "comment": f"DAV_{signal.strategy_name}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            err_msg = f"Order failed: {mt5.last_error() if result is None else result.comment}"
            logger.error(err_msg)
            return {"status": "FAILED", "reason": err_msg}

        logger.info(f"Live MT5 Order executed successfully! Ticket: {result.order}")
        return {
            "status": "FILLED_LIVE",
            "ticket": result.order,
            "deal": result.deal,
            "price": result.price,
            "lot_size": sizing.lot_size,
        }

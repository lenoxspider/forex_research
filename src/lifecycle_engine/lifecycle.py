"""
Trade Lifecycle, Excursion Telemetry, and Dynamic Exit Simulation Engine.
Analyzes bar-by-bar price excursions (MAE/MFE, Time-to-R), premature reversal statistics,
and simulates 10 distinct structural/dynamic exit models and Target-R reward curves.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from config.settings import PAIR_SPECS, PairSpec
from src.strategy_engine.strategies import TradeSignal
from src.backtest_engine.backtester import RealisticBacktester, ExecutedTrade
from src.backtest_engine.metrics import MetricsCalculator, PerformanceSummary


@dataclass
class TradeLifecycleTelemetry:
    trade_id: int
    symbol: str
    strategy_name: str
    direction: int
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    stop_loss: float
    take_profit_original: float
    risk_pips: float
    holding_bars: int
    final_exit_reason: str
    final_pnl_net_pips: float
    final_pnl_r: float
    mfe_pips: float
    mfe_r: float
    time_to_mfe_bars: int
    mae_pips: float
    mae_r: float
    time_to_mae_bars: int
    bars_to_0_5r: Optional[int]
    bars_to_0_75r: Optional[int]
    bars_to_1_0r: Optional[int]
    bars_to_1_25r: Optional[int]
    bars_to_1_5r: Optional[int]
    bars_to_2_0r: Optional[int]
    reached_pos_0_5r_then_stopped: bool
    reached_pos_0_75r_then_stopped: bool
    reached_pos_1_0r_then_stopped: bool
    year: int


class TradeLifecycleEngine:
    """Tracks intra-trade paths and simulates alternative exit architectures."""

    def __init__(self, symbol: str, cost_multiplier: float = 1.0):
        self.symbol = symbol
        self.spec: PairSpec = PAIR_SPECS.get(symbol, PAIR_SPECS["EURUSD"])
        self.pip_size = self.spec.pip_size
        self.cost_multiplier = cost_multiplier
        self.base_spread_pips = self.spec.base_spread_pips * cost_multiplier
        self.base_slippage_pips = self.spec.base_slippage_pips * cost_multiplier
        self.commission_pips = (self.spec.commission_per_lot_usd / 10.0) * cost_multiplier

    def extract_trade_lifecycles(
        self,
        df: pd.DataFrame,
        signals: List[TradeSignal],
    ) -> Tuple[List[TradeLifecycleTelemetry], pd.DataFrame]:
        """
        Executes signals and extracts granular bar-by-bar path telemetry for each trade.
        """
        if not signals or df.empty:
            return [], pd.DataFrame()

        ts_to_idx = {ts: idx for idx, ts in enumerate(df.index)}
        n_bars = len(df)
        times = df.index
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        spreads_pts = df["spread"].values if "spread" in df.columns else np.zeros(n_bars)

        lifecycles: List[TradeLifecycleTelemetry] = []
        trade_id = 1
        active_trade_until_idx = -1

        for sig in signals:
            if sig.timestamp not in ts_to_idx:
                continue

            sig_idx = ts_to_idx[sig.timestamp]
            entry_idx = sig_idx + 1

            if entry_idx >= n_bars or entry_idx <= active_trade_until_idx:
                continue

            # Costs
            spread_pips = (spreads_pts[entry_idx] * 0.1) if spreads_pts[entry_idx] > 0 else self.base_spread_pips
            spread_pips = max(spread_pips * self.cost_multiplier, self.base_spread_pips)
            slippage_pips = self.base_slippage_pips

            raw_entry = opens[entry_idx]
            if sig.direction == 1:
                exec_entry = raw_entry + (spread_pips * 0.5 + slippage_pips) * self.pip_size
            else:
                exec_entry = raw_entry - (spread_pips * 0.5 + slippage_pips) * self.pip_size

            max_bars = sig.max_holding_bars
            end_idx = min(entry_idx + max_bars, n_bars - 1)

            risk_pips = max(sig.risk_pips, 1.0)
            target_pips = sig.target_pips

            # Path telemetry trackers
            mfe_pips = 0.0
            mae_pips = 0.0
            time_to_mfe = 0
            time_to_mae = 0

            bars_0_5r = None
            bars_0_75r = None
            bars_1_0r = None
            bars_1_25r = None
            bars_1_5r = None
            bars_2_0r = None

            exit_reason = "TIME_EXPIRY"
            exit_idx = end_idx
            raw_exit = closes[end_idx]

            for rel_idx, bar_idx in enumerate(range(entry_idx, end_idx + 1)):
                b_high = highs[bar_idx]
                b_low = lows[bar_idx]

                if sig.direction == 1:  # LONG
                    # Excursions relative to exec entry
                    bar_fav = (b_high - exec_entry) / self.pip_size
                    bar_adv = (exec_entry - b_low) / self.pip_size

                    if bar_fav > mfe_pips:
                        mfe_pips = bar_fav
                        time_to_mfe = rel_idx
                    if bar_adv > mae_pips:
                        mae_pips = bar_adv
                        time_to_mae = rel_idx

                    # Milestone tracking
                    if bars_0_5r is None and bar_fav >= 0.5 * risk_pips:
                        bars_0_5r = rel_idx
                    if bars_0_75r is None and bar_fav >= 0.75 * risk_pips:
                        bars_0_75r = rel_idx
                    if bars_1_0r is None and bar_fav >= 1.0 * risk_pips:
                        bars_1_0r = rel_idx
                    if bars_1_25r is None and bar_fav >= 1.25 * risk_pips:
                        bars_1_25r = rel_idx
                    if bars_1_5r is None and bar_fav >= 1.5 * risk_pips:
                        bars_1_5r = rel_idx
                    if bars_2_0r is None and bar_fav >= 2.0 * risk_pips:
                        bars_2_0r = rel_idx

                    # Original SL / TP check
                    hit_sl = b_low <= sig.stop_loss
                    hit_tp = b_high >= sig.take_profit

                    if hit_sl and hit_tp:
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
                    bar_fav = (exec_entry - b_low) / self.pip_size
                    bar_adv = (b_high - exec_entry) / self.pip_size

                    if bar_fav > mfe_pips:
                        mfe_pips = bar_fav
                        time_to_mfe = rel_idx
                    if bar_adv > mae_pips:
                        mae_pips = bar_adv
                        time_to_mae = rel_idx

                    if bars_0_5r is None and bar_fav >= 0.5 * risk_pips:
                        bars_0_5r = rel_idx
                    if bars_0_75r is None and bar_fav >= 0.75 * risk_pips:
                        bars_0_75r = rel_idx
                    if bars_1_0r is None and bar_fav >= 1.0 * risk_pips:
                        bars_1_0r = rel_idx
                    if bars_1_25r is None and bar_fav >= 1.25 * risk_pips:
                        bars_1_25r = rel_idx
                    if bars_1_5r is None and bar_fav >= 1.5 * risk_pips:
                        bars_1_5r = rel_idx
                    if bars_2_0r is None and bar_fav >= 2.0 * risk_pips:
                        bars_2_0r = rel_idx

                    hit_sl = b_high >= sig.stop_loss
                    hit_tp = b_low <= sig.take_profit

                    if hit_sl and hit_tp:
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

            # Exit pricing & net pips
            exit_spread_pips = (spreads_pts[exit_idx] * 0.1) if spreads_pts[exit_idx] > 0 else self.base_spread_pips
            exit_spread_pips = max(exit_spread_pips * self.cost_multiplier, self.base_spread_pips)

            if sig.direction == 1:
                exec_exit = raw_exit - (exit_spread_pips * 0.5 + slippage_pips) * self.pip_size
                net_pips = (exec_exit - exec_entry) / self.pip_size - self.commission_pips
            else:
                exec_exit = raw_exit + (exit_spread_pips * 0.5 + slippage_pips) * self.pip_size
                net_pips = (exec_entry - exec_exit) / self.pip_size - self.commission_pips

            r_mult = net_pips / risk_pips

            mfe_r = mfe_pips / risk_pips
            mae_r = mae_pips / risk_pips

            stopped_after_0_5r = (exit_reason == "SL" and bars_0_5r is not None)
            stopped_after_0_75r = (exit_reason == "SL" and bars_0_75r is not None)
            stopped_after_1_0r = (exit_reason == "SL" and bars_1_0r is not None)

            telemetry = TradeLifecycleTelemetry(
                trade_id=trade_id,
                symbol=self.symbol,
                strategy_name=sig.strategy_name,
                direction=sig.direction,
                entry_time=times[entry_idx],
                exit_time=times[exit_idx],
                entry_price=float(exec_entry),
                stop_loss=float(sig.stop_loss),
                take_profit_original=float(sig.take_profit),
                risk_pips=float(risk_pips),
                holding_bars=exit_idx - entry_idx + 1,
                final_exit_reason=exit_reason,
                final_pnl_net_pips=round(net_pips, 2),
                final_pnl_r=round(r_mult, 3),
                mfe_pips=round(mfe_pips, 2),
                mfe_r=round(mfe_r, 3),
                time_to_mfe_bars=time_to_mfe,
                mae_pips=round(mae_pips, 2),
                mae_r=round(mae_r, 3),
                time_to_mae_bars=time_to_mae,
                bars_to_0_5r=bars_0_5r,
                bars_to_0_75r=bars_0_75r,
                bars_to_1_0r=bars_1_0r,
                bars_to_1_25r=bars_1_25r,
                bars_to_1_5r=bars_1_5r,
                bars_to_2_0r=bars_2_0r,
                reached_pos_0_5r_then_stopped=stopped_after_0_5r,
                reached_pos_0_75r_then_stopped=stopped_after_0_75r,
                reached_pos_1_0r_then_stopped=stopped_after_1_0r,
                year=times[entry_idx].year,
            )

            lifecycles.append(telemetry)
            trade_id += 1
            active_trade_until_idx = exit_idx

        df_telemetry = pd.DataFrame([asdict(t) for t in lifecycles]) if lifecycles else pd.DataFrame()
        return lifecycles, df_telemetry

    def simulate_exit_models(
        self,
        df: pd.DataFrame,
        signals: List[TradeSignal],
    ) -> Dict[str, PerformanceSummary]:
        """
        Simulates 10 distinct exit models on the exact same trade entry signals.
        """
        if not signals or df.empty:
            return {}

        ts_to_idx = {ts: idx for idx, ts in enumerate(df.index)}
        n_bars = len(df)
        times = df.index
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        spreads_pts = df["spread"].values if "spread" in df.columns else np.zeros(n_bars)
        atr_14 = df["atr_14"].values if "atr_14" in df.columns else np.ones(n_bars) * 0.0015
        swing_h = df["swing_high_20"].values if "swing_high_20" in df.columns else highs
        swing_l = df["swing_low_20"].values if "swing_low_20" in df.columns else lows

        exit_models = [
            "A_Fixed_0.75R",
            "B_Fixed_1.00R",
            "C_Fixed_1.25R",
            "D_Fixed_1.50R",
            "E_Fixed_2.00R",
            "F_Partial_1R_Trail",
            "G_ATR_Trailing_1.5x",
            "H_Structural_Trailing",
            "I_Time_Exit_16_Bars",
            "J_BreakEven_At_0.75R",
        ]

        model_results = {}

        for model_name in exit_models:
            trades_list = []
            active_until = -1

            for sig in signals:
                if sig.timestamp not in ts_to_idx:
                    continue

                sig_idx = ts_to_idx[sig.timestamp]
                entry_idx = sig_idx + 1

                if entry_idx >= n_bars or entry_idx <= active_until:
                    continue

                spread_pips = (spreads_pts[entry_idx] * 0.1) if spreads_pts[entry_idx] > 0 else self.base_spread_pips
                spread_pips = max(spread_pips * self.cost_multiplier, self.base_spread_pips)
                slippage_pips = self.base_slippage_pips

                raw_entry = opens[entry_idx]
                if sig.direction == 1:
                    exec_entry = raw_entry + (spread_pips * 0.5 + slippage_pips) * self.pip_size
                else:
                    exec_entry = raw_entry - (spread_pips * 0.5 + slippage_pips) * self.pip_size

                risk_pips = max(sig.risk_pips, 1.0)
                sl_price = sig.stop_loss
                max_bars = 32
                end_idx = min(entry_idx + max_bars, n_bars - 1)

                # Configure model target & trailing
                if model_name == "A_Fixed_0.75R":
                    tp_price = exec_entry + 0.75 * risk_pips * self.pip_size * sig.direction
                elif model_name == "B_Fixed_1.00R":
                    tp_price = exec_entry + 1.00 * risk_pips * self.pip_size * sig.direction
                elif model_name == "C_Fixed_1.25R":
                    tp_price = exec_entry + 1.25 * risk_pips * self.pip_size * sig.direction
                elif model_name == "D_Fixed_1.50R":
                    tp_price = exec_entry + 1.50 * risk_pips * self.pip_size * sig.direction
                elif model_name == "E_Fixed_2.00R":
                    tp_price = exec_entry + 2.00 * risk_pips * self.pip_size * sig.direction
                else:
                    tp_price = exec_entry + 2.50 * risk_pips * self.pip_size * sig.direction

                # Execution loop
                exit_idx = end_idx
                raw_exit = closes[end_idx]
                current_sl = sl_price
                has_be_triggered = False
                has_partial_taken = False
                partial_pnl_pips = 0.0

                for b_idx in range(entry_idx, end_idx + 1):
                    b_high = highs[b_idx]
                    b_low = lows[b_idx]
                    b_close = closes[b_idx]
                    rel_b = b_idx - entry_idx

                    # Dynamic adjustments per model
                    if sig.direction == 1:  # LONG
                        # Break-even model
                        if model_name == "J_BreakEven_At_0.75R":
                            if not has_be_triggered and b_high >= exec_entry + 0.75 * risk_pips * self.pip_size:
                                current_sl = exec_entry + 0.1 * self.pip_size
                                has_be_triggered = True

                        # Partial model
                        elif model_name == "F_Partial_1R_Trail":
                            if not has_partial_taken and b_high >= exec_entry + 1.0 * risk_pips * self.pip_size:
                                has_partial_taken = True
                                partial_pnl_pips = 0.5 * (1.0 * risk_pips)  # 50% banked at 1R
                                current_sl = exec_entry + 0.1 * self.pip_size
                            if has_partial_taken:
                                current_sl = max(current_sl, b_close - 1.5 * atr_14[b_idx])

                        # ATR Trailing
                        elif model_name == "G_ATR_Trailing_1.5x":
                            current_sl = max(current_sl, b_high - 1.5 * atr_14[b_idx])

                        # Structural Trailing
                        elif model_name == "H_Structural_Trailing":
                            current_sl = max(current_sl, swing_l[b_idx])

                        # Time exit
                        elif model_name == "I_Time_Exit_16_Bars":
                            if rel_b >= 16:
                                exit_idx = b_idx
                                raw_exit = b_close
                                break

                        # Hit tests
                        hit_sl = b_low <= current_sl
                        hit_tp = b_high >= tp_price

                        if hit_sl:
                            exit_idx = b_idx
                            raw_exit = current_sl
                            break
                        elif hit_tp:
                            exit_idx = b_idx
                            raw_exit = tp_price
                            break

                    else:  # SHORT
                        if model_name == "J_BreakEven_At_0.75R":
                            if not has_be_triggered and b_low <= exec_entry - 0.75 * risk_pips * self.pip_size:
                                current_sl = exec_entry - 0.1 * self.pip_size
                                has_be_triggered = True

                        elif model_name == "F_Partial_1R_Trail":
                            if not has_partial_taken and b_low <= exec_entry - 1.0 * risk_pips * self.pip_size:
                                has_partial_taken = True
                                partial_pnl_pips = 0.5 * (1.0 * risk_pips)
                                current_sl = exec_entry - 0.1 * self.pip_size
                            if has_partial_taken:
                                current_sl = min(current_sl, b_close + 1.5 * atr_14[b_idx])

                        elif model_name == "G_ATR_Trailing_1.5x":
                            current_sl = min(current_sl, b_low + 1.5 * atr_14[b_idx])

                        elif model_name == "H_Structural_Trailing":
                            current_sl = min(current_sl, swing_h[b_idx])

                        elif model_name == "I_Time_Exit_16_Bars":
                            if rel_b >= 16:
                                exit_idx = b_idx
                                raw_exit = b_close
                                break

                        hit_sl = b_high >= current_sl
                        hit_tp = b_low <= tp_price

                        if hit_sl:
                            exit_idx = b_idx
                            raw_exit = current_sl
                            break
                        elif hit_tp:
                            exit_idx = b_idx
                            raw_exit = tp_price
                            break

                exit_spread_pips = (spreads_pts[exit_idx] * 0.1) if spreads_pts[exit_idx] > 0 else self.base_spread_pips
                exit_spread_pips = max(exit_spread_pips * self.cost_multiplier, self.base_spread_pips)

                if sig.direction == 1:
                    exec_exit = raw_exit - (exit_spread_pips * 0.5 + slippage_pips) * self.pip_size
                    net_pips = (exec_exit - exec_entry) / self.pip_size - self.commission_pips
                else:
                    exec_exit = raw_exit + (exit_spread_pips * 0.5 + slippage_pips) * self.pip_size
                    net_pips = (exec_entry - exec_exit) / self.pip_size - self.commission_pips

                if model_name == "F_Partial_1R_Trail" and has_partial_taken:
                    net_pips = partial_pnl_pips + 0.5 * net_pips

                r_mult = net_pips / risk_pips

                trades_list.append({
                    "entry_time": times[entry_idx],
                    "exit_time": times[exit_idx],
                    "holding_bars": exit_idx - entry_idx + 1,
                    "pnl_net_pips": net_pips,
                    "pnl_r_multiple": r_mult,
                    "risk_pips": risk_pips,
                    "year": times[entry_idx].year,
                })
                active_until = exit_idx

            df_model_trades = pd.DataFrame(trades_list) if trades_list else pd.DataFrame()
            summary = MetricsCalculator.calculate_summary(df_model_trades)
            model_results[model_name] = summary

        return model_results

    def compute_reward_curve(
        self,
        df: pd.DataFrame,
        signals: List[TradeSignal],
        r_targets: List[float] = [0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.5, 3.0],
    ) -> pd.DataFrame:
        """
        Computes the Target R -> Expectancy curve.
        """
        rows = []
        for target_r in r_targets:
            # Modify target pips for all signals
            modified_sigs = []
            for s in signals:
                mod_s = TradeSignal(
                    timestamp=s.timestamp,
                    symbol=s.symbol,
                    direction=s.direction,
                    entry_price=s.entry_price,
                    stop_loss=s.stop_loss,
                    take_profit=s.entry_price + (target_r * s.risk_pips * self.pip_size * s.direction),
                    max_holding_bars=s.max_holding_bars,
                    strategy_name=s.strategy_name,
                    regime=s.regime,
                    risk_pips=s.risk_pips,
                    target_pips=target_r * s.risk_pips,
                    metadata=s.metadata,
                )
                modified_sigs.append(mod_s)

            _, df_t = RealisticBacktester(self.symbol, cost_multiplier=self.cost_multiplier).run_backtest(df, modified_sigs)
            s = MetricsCalculator.calculate_summary(df_t)

            rows.append({
                "Target_R": target_r,
                "Trades": s.total_trades,
                "WinRate%": s.win_rate_pct,
                "Exp(R)": s.expectancy_r,
                "PF": s.profit_factor,
                "NetPips": s.net_profit_pips,
                "MaxDD%": s.max_drawdown_pct,
                "AvgHoldingBars": s.avg_holding_bars,
            })

        return pd.DataFrame(rows)

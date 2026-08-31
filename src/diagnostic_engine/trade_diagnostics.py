"""
Trade-Level Diagnostics Engine.
Calculates MAE (Maximum Adverse Excursion), MFE (Maximum Favorable Excursion),
holding duration, entry conditions (ATR%, ADX, Spread, Session, Regime, HTF Trend),
and winner vs loser distributions.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from config.settings import PAIR_SPECS, PairSpec
from src.backtest_engine.backtester import ExecutedTrade


@dataclass
class EnhancedTradeDiagnostic:
    trade_id: int
    symbol: str
    strategy_name: str
    direction: int
    direction_label: str  # "LONG" or "SHORT"
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    exit_reason: str
    risk_pips: float
    pnl_net_pips: float
    pnl_r_multiple: float
    is_winner: bool
    holding_bars: int
    mae_pips: float
    mae_r: float
    mfe_pips: float
    mfe_r: float
    entry_spread_pips: float
    spread_bucket: str  # "Low (<=1.0p)", "Medium (1.0-1.5p)", "High (>1.5p)"
    entry_atr_pips: float
    atr_percentile: float
    atr_bucket: str  # "0-20%", "20-40%", "40-60%", "60-80%", "80-100%"
    entry_adx: float
    adx_bucket: str  # "Low (<18)", "Medium (18-28)", "High (>28)"
    trend_regime: str
    vol_regime: str
    combined_regime: str
    h1_trend_state: int
    htf_alignment: str  # "ALIGNED", "OPPOSED", "NEUTRAL"
    session: str  # "ASIAN", "LONDON", "OVERLAP", "NY_LATE"
    day_of_week: str  # "Monday", "Tuesday", etc.
    year: int


class TradeDiagnosticEngine:
    """Extracts deep granular trade execution telemetry for edge discovery."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.spec: PairSpec = PAIR_SPECS.get(symbol, PAIR_SPECS["EURUSD"])
        self.pip_size = self.spec.pip_size

    def compute_trade_diagnostics(
        self,
        df: pd.DataFrame,
        executed_trades: List[ExecutedTrade],
    ) -> Tuple[List[EnhancedTradeDiagnostic], pd.DataFrame]:
        if not executed_trades or df.empty:
            return [], pd.DataFrame()

        ts_to_idx = {ts: idx for idx, ts in enumerate(df.index)}
        highs = df["high"].values
        lows = df["low"].values
        n_bars = len(df)

        enhanced: List[EnhancedTradeDiagnostic] = []

        for t in executed_trades:
            sig_ts = t.signal_time
            entry_ts = t.entry_time
            exit_ts = t.exit_time

            entry_idx = ts_to_idx.get(entry_ts, None)
            exit_idx = ts_to_idx.get(exit_ts, None)

            if entry_idx is None or exit_idx is None:
                continue

            trade_highs = highs[entry_idx : exit_idx + 1]
            trade_lows = lows[entry_idx : exit_idx + 1]

            if len(trade_highs) == 0:
                continue

            max_high = float(np.max(trade_highs))
            min_low = float(np.min(trade_lows))
            entry_p = t.entry_price

            # MAE & MFE in pips
            if t.direction == 1:  # LONG
                mae_pips = max(0.0, (entry_p - min_low) / self.pip_size)
                mfe_pips = max(0.0, (max_high - entry_p) / self.pip_size)
            else:  # SHORT
                mae_pips = max(0.0, (max_high - entry_p) / self.pip_size)
                mfe_pips = max(0.0, (entry_p - min_low) / self.pip_size)

            risk_pips = max(t.risk_pips, 1.0)
            mae_r = mae_pips / risk_pips
            mfe_r = mfe_pips / risk_pips

            # Feature context at signal time
            row = df.loc[sig_ts] if sig_ts in df.index else df.iloc[max(0, entry_idx - 1)]
            
            atr_p = float(row.get("atr_pips", t.risk_pips))
            atr_pctl = float(row.get("atr_percentile_200", 0.5))
            if atr_pctl < 0.20:
                atr_b = "0-20% (Lowest)"
            elif atr_pctl < 0.40:
                atr_b = "20-40% (Low)"
            elif atr_pctl < 0.60:
                atr_b = "40-60% (Mid)"
            elif atr_pctl < 0.80:
                atr_b = "60-80% (High)"
            else:
                atr_b = "80-100% (Highest)"

            adx_val = float(row.get("adx_14", 20.0))
            if adx_val < 18.0:
                adx_b = "Low (<18)"
            elif adx_val < 28.0:
                adx_b = "Medium (18-28)"
            else:
                adx_b = "High (>28)"

            spread_p = t.spread_cost_pips
            if spread_p <= 1.0:
                spread_b = "Low (<=1.0p)"
            elif spread_p <= 1.5:
                spread_b = "Medium (1.0-1.5p)"
            else:
                spread_b = "High (>1.5p)"

            h1_state = int(row.get("h1_trend_state", 0))
            if h1_state == 0:
                htf_align = "NEUTRAL"
            elif (t.direction == 1 and h1_state == 1) or (t.direction == -1 and h1_state == -1):
                htf_align = "ALIGNED"
            else:
                htf_align = "OPPOSED"

            dow_str = entry_ts.strftime("%A")
            dir_str = "LONG" if t.direction == 1 else "SHORT"

            diag = EnhancedTradeDiagnostic(
                trade_id=t.trade_id,
                symbol=self.symbol,
                strategy_name=t.strategy_name,
                direction=t.direction,
                direction_label=dir_str,
                entry_time=entry_ts,
                exit_time=exit_ts,
                entry_price=float(t.entry_price),
                exit_price=float(t.exit_price),
                exit_reason=t.exit_reason,
                risk_pips=float(t.risk_pips),
                pnl_net_pips=float(t.pnl_net_pips),
                pnl_r_multiple=float(t.pnl_r_multiple),
                is_winner=(t.pnl_net_pips > 0),
                holding_bars=t.holding_bars,
                mae_pips=round(mae_pips, 2),
                mae_r=round(mae_r, 3),
                mfe_pips=round(mfe_pips, 2),
                mfe_r=round(mfe_r, 3),
                entry_spread_pips=round(spread_p, 2),
                spread_bucket=spread_b,
                entry_atr_pips=round(atr_p, 2),
                atr_percentile=round(atr_pctl, 3),
                atr_bucket=atr_b,
                entry_adx=round(adx_val, 1),
                adx_bucket=adx_b,
                trend_regime=str(row.get("trend_regime", "UNKNOWN")),
                vol_regime=str(row.get("vol_regime", "UNKNOWN")),
                combined_regime=str(row.get("combined_regime", "UNKNOWN")),
                h1_trend_state=h1_state,
                htf_alignment=htf_align,
                session=t.session,
                day_of_week=dow_str,
                year=entry_ts.year,
            )
            enhanced.append(diag)

        df_enhanced = pd.DataFrame([asdict(d) for d in enhanced])
        return enhanced, df_enhanced

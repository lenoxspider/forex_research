"""
Global Configuration for Systematic Multi-Pair Forex Research & Execution System.
Pairs: EURUSD, GBPUSD, USDJPY
Timeframes: M15 (Execution), H1 (Regime & Macro Trend)
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
CLEAN_DATA_DIR = DATA_DIR / "clean"
REPORTS_DIR = DATA_DIR / "quality_reports"
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"

for d in [DATA_DIR, RAW_DATA_DIR, CLEAN_DATA_DIR, REPORTS_DIR, EXPERIMENTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Target Forex Pairs
TARGET_PAIRS = ["EURUSD", "GBPUSD", "USDJPY"]

# Symbol Specifications
@dataclass(frozen=True)
class PairSpec:
    symbol: str
    pip_size: float
    pip_decimal_places: int
    base_spread_pips: float
    base_slippage_pips: float
    commission_per_lot_usd: float  # e.g. $3.50 per lot per side = $7 round-turn
    contract_size: float = 100_000.0

PAIR_SPECS: Dict[str, PairSpec] = {
    "EURUSD": PairSpec(
        symbol="EURUSD",
        pip_size=0.0001,
        pip_decimal_places=4,
        base_spread_pips=0.8,
        base_slippage_pips=0.2,
        commission_per_lot_usd=7.0,
    ),
    "GBPUSD": PairSpec(
        symbol="GBPUSD",
        pip_size=0.0001,
        pip_decimal_places=4,
        base_spread_pips=1.2,
        base_slippage_pips=0.4,
        commission_per_lot_usd=7.0,
    ),
    "USDJPY": PairSpec(
        symbol="USDJPY",
        pip_size=0.01,
        pip_decimal_places=2,
        base_spread_pips=0.9,
        base_slippage_pips=0.3,
        commission_per_lot_usd=7.0,
    ),
}

# Chronological Research Splits
@dataclass(frozen=True)
class DateSplit:
    name: str
    start_date: str
    end_date: str

CHRONOLOGICAL_SPLITS = [
    DateSplit("DEV_IN_SAMPLE", "2022-01-01", "2023-12-31"),
    DateSplit("VALIDATION", "2024-01-01", "2024-12-31"),
    DateSplit("OOS_1", "2025-01-01", "2025-12-31"),
    DateSplit("FINAL_UNTOUCHED_OOS", "2026-01-01", "2026-12-31"),
]

# Timeframes
PRIMARY_TIMEFRAME = "M15"
HIGHER_TIMEFRAME = "H1"

# Trading Sessions (UTC Hours)
SESSION_WINDOWS = {
    "ASIAN": (0, 7),       # 00:00 - 07:00 UTC (Tokyo/Sydney)
    "LONDON": (7, 12),     # 07:00 - 12:00 UTC (London Open)
    "OVERLAP": (12, 16),   # 12:00 - 16:00 UTC (London / NY Overlap)
    "NY_AFTERNOON": (16, 21), # 16:00 - 21:00 UTC
    "ROLLOVER": (21, 23),  # 21:00 - 23:00 UTC (High spread / swap zone - No New Trades)
}

# Portfolio Risk Settings
DEFAULT_RISK_PER_TRADE_PCT = 0.01      # 1.0% equity risk per trade
MAX_PORTFOLIO_CONCURRENT_RISK = 0.03   # 3.0% max total open risk
MAX_USD_CONCURRENT_RISK = 0.02        # 2.0% max directional USD risk
MAX_DAILY_PORTFOLIO_LOSS_PCT = 0.025  # 2.5% daily drawdown shutdown
MAX_TOTAL_DRAWDOWN_LIMIT = 0.06       # 6.0% global drawdown circuit breaker

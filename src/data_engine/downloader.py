"""
MT5 Historical Data Downloader.
Handles chunked queries, broker symbol suffix resolution, and raw data extraction.
"""
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from config.settings import (
    RAW_DATA_DIR,
    TARGET_PAIRS,
    PRIMARY_TIMEFRAME,
    HIGHER_TIMEFRAME,
)

logger = logging.getLogger("DataEngine.Downloader")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

TIMEFRAME_MAP = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 16385,
    "H4": 16388,
    "D1": 16408,
}

if mt5 is not None:
    TIMEFRAME_MAP["M15"] = mt5.TIMEFRAME_M15
    TIMEFRAME_MAP["H1"] = mt5.TIMEFRAME_H1
    TIMEFRAME_MAP["D1"] = mt5.TIMEFRAME_D1


class MT5DataDownloader:
    """Downloader that interfaces with MT5 to pull full historical OHLCV data."""

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.initialized = False

    def connect(self) -> bool:
        if mt5 is None:
            logger.error("MetaTrader5 python package not available.")
            return False
        if self.path:
            self.initialized = mt5.initialize(path=self.path)
        else:
            self.initialized = mt5.initialize()
        if not self.initialized:
            logger.error(f"MT5 Initialization failed: {mt5.last_error()}")
        else:
            logger.info("Connected to MetaTrader 5 successfully.")
        return self.initialized

    def disconnect(self):
        if self.initialized and mt5 is not None:
            mt5.shutdown()
            self.initialized = False
            logger.info("Disconnected from MetaTrader 5.")

    def find_broker_symbol(self, base_symbol: str) -> Optional[str]:
        """Resolves broker-specific suffixes (e.g., EURUSD.pro, EURUSD_i)."""
        if not self.initialized and not self.connect():
            return None

        # Check exact match
        sym_info = mt5.symbol_info(base_symbol)
        if sym_info is not None:
            mt5.symbol_select(base_symbol, True)
            return base_symbol

        # Search matching symbols in terminal
        all_symbols = mt5.symbols_get()
        if all_symbols:
            for s in all_symbols:
                if s.name.upper().startswith(base_symbol.upper()) or base_symbol.upper() in s.name.upper():
                    mt5.symbol_select(s.name, True)
                    logger.info(f"Resolved base symbol {base_symbol} -> broker symbol {s.name}")
                    return s.name

        logger.warning(f"Could not resolve symbol for {base_symbol}")
        return None

    def fetch_historical_rates(
        self,
        symbol: str,
        timeframe_str: str = "M15",
        start_year: int = 2022,
        end_year: int = 2026,
    ) -> Optional[pd.DataFrame]:
        """
        Pulls maximum available historical data chunk-by-chunk between start_year and end_year.
        """
        if not self.initialized and not self.connect():
            return None

        broker_symbol = self.find_broker_symbol(symbol)
        if not broker_symbol:
            logger.error(f"Symbol {symbol} not found on broker.")
            return None

        tf = TIMEFRAME_MAP.get(timeframe_str, mt5.TIMEFRAME_M15)
        logger.info(f"Fetching {symbol} ({broker_symbol}) [{timeframe_str}]...")

        all_chunks = []
        # Chunk yearly from start_year to end_year
        for y in range(start_year, end_year + 1):
            dt_from = datetime(y, 1, 1, 0, 0, tzinfo=timezone.utc)
            dt_to = datetime(y, 12, 31, 23, 59, tzinfo=timezone.utc)
            
            rates = mt5.copy_rates_range(broker_symbol, tf, dt_from, dt_to)
            if rates is not None and len(rates) > 10:  # ignore 1-bar placeholder
                df_chunk = pd.DataFrame(rates)
                all_chunks.append(df_chunk)
                logger.info(f"  [{symbol} {timeframe_str}] {y}: fetched {len(df_chunk)} bars ({pd.to_datetime(df_chunk['time'].iloc[0], unit='s')} to {pd.to_datetime(df_chunk['time'].iloc[-1], unit='s')})")

        # Also pull max count from current time
        rates_recent = mt5.copy_rates_from(broker_symbol, tf, datetime.now(timezone.utc), 100000)
        if rates_recent is not None and len(rates_recent) > 10:
            df_recent = pd.DataFrame(rates_recent)
            all_chunks.append(df_recent)

        if not all_chunks:
            logger.error(f"No data returned for {symbol} ({broker_symbol}) [{timeframe_str}].")
            return None

        full_df = pd.concat(all_chunks, ignore_index=True)
        # Drop duplicates by time
        full_df = full_df.drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
        
        # Convert timestamp
        full_df["timestamp"] = pd.to_datetime(full_df["time"], unit="s", utc=True)
        full_df = full_df.drop(columns=["time"])
        full_df = full_df.set_index("timestamp").sort_index()

        # Save to raw
        output_path = RAW_DATA_DIR / f"{symbol}_{timeframe_str}.parquet"
        full_df.to_parquet(output_path, compression="snappy")
        logger.info(f"Saved {symbol} {timeframe_str} raw data: {len(full_df)} bars ({full_df.index[0]} -> {full_df.index[-1]}) -> {output_path}")

        return full_df

    def download_all_target_pairs(
        self,
        pairs: List[str] = TARGET_PAIRS,
        timeframes: List[str] = [PRIMARY_TIMEFRAME, HIGHER_TIMEFRAME],
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        results = {}
        for pair in pairs:
            results[pair] = {}
            for tf in timeframes:
                df = self.fetch_historical_rates(pair, tf)
                if df is not None:
                    results[pair][tf] = df
        return results


if __name__ == "__main__":
    downloader = MT5DataDownloader()
    try:
        downloader.download_all_target_pairs()
    finally:
        downloader.disconnect()

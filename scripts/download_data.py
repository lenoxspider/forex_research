"""
MT5 historical data download script using copy_rates_range (year-by-year chunked).
Avoids copy_rates_from_pos which triggers full broker-server historical sync for large counts.
"""
import datetime
import logging
from pathlib import Path
import pandas as pd
import MetaTrader5 as mt5

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Downloader")

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Skip pairs that already have data
SYMBOLS = ["GBPUSD", "USDJPY"]
TIMEFRAMES = [
    ("M15", mt5.TIMEFRAME_M15),
    ("H1", mt5.TIMEFRAME_H1),
]

# M15: ~3.5 years back; H1: ~5 years back
YEAR_RANGES = {
    "M15": range(2023, 2027),
    "H1": range(2021, 2027),
}


def download_symbol(sym: str, tf_name: str, tf_const: int):
    out_file = RAW_DIR / f"{sym}_{tf_name}.parquet"
    if out_file.exists():
        logger.info(f"  -> SKIP {sym} {tf_name}: already exists")
        return

    mt5.symbol_select(sym, True)
    all_chunks = []

    for yr in YEAR_RANGES[tf_name]:
        dt_from = datetime.datetime(yr, 1, 1, tzinfo=datetime.timezone.utc)
        dt_to = datetime.datetime(yr, 12, 31, 23, 59, tzinfo=datetime.timezone.utc)
        rates = mt5.copy_rates_range(sym, tf_const, dt_from, dt_to)
        if rates is not None and len(rates) > 0:
            chunk = pd.DataFrame(rates)
            all_chunks.append(chunk)
            logger.info(f"  {sym} {tf_name} {yr}: {len(rates):,} bars")
        else:
            logger.warning(f"  {sym} {tf_name} {yr}: no data")

    if not all_chunks:
        logger.error(f"  -> FAILED: No data for {sym} {tf_name}")
        return

    df = pd.concat(all_chunks).drop_duplicates("time").sort_values("time")
    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.drop(columns=["time"]).set_index("timestamp")
    df.to_parquet(out_file, compression="snappy")
    logger.info(f"  -> SAVED {sym} {tf_name}: {len(df):,} bars ({df.index[0]} to {df.index[-1]}) -> {out_file}")


def main():
    if not mt5.initialize():
        logger.error(f"MT5 Init failed: {mt5.last_error()}")
        return
    logger.info("Connected to MT5.")

    for sym in SYMBOLS:
        for tf_name, tf_const in TIMEFRAMES:
            logger.info(f"Downloading {sym} {tf_name}...")
            download_symbol(sym, tf_name, tf_const)

    mt5.shutdown()
    logger.info("Done.")


if __name__ == "__main__":
    main()

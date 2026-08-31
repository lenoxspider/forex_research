"""
Data Quality Auditor and Clean Dataset Generator.
Performs exhaustive checks on OHLC bounds, duplicate timestamps, missing intervals,
weekend vs trading day gaps, volume abnormalities, and outputs detailed markdown audit reports.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from config.settings import (
    RAW_DATA_DIR,
    CLEAN_DATA_DIR,
    REPORTS_DIR,
    TARGET_PAIRS,
    PRIMARY_TIMEFRAME,
    HIGHER_TIMEFRAME,
    PAIR_SPECS,
)

logger = logging.getLogger("DataEngine.Validator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class DataQualityAuditor:
    """Audits raw OHLCV datasets and validates data integrity."""

    def __init__(self, raw_dir: Path = RAW_DATA_DIR, clean_dir: Path = CLEAN_DATA_DIR, reports_dir: Path = REPORTS_DIR):
        self.raw_dir = raw_dir
        self.clean_dir = clean_dir
        self.reports_dir = reports_dir

    def audit_dataset(self, symbol: str, timeframe: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        raw_path = self.raw_dir / f"{symbol}_{timeframe}.parquet"
        if not raw_path.exists():
            raise FileNotFoundError(f"Raw data file not found: {raw_path}")

        df = pd.read_parquet(raw_path)
        if not isinstance(df.index, pd.DatetimeIndex):
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
                df = df.set_index("timestamp")
            else:
                raise ValueError("DataFrame must have a DatetimeIndex or timestamp column.")

        df = df.sort_index()

        total_bars = len(df)
        earliest_ts = str(df.index[0])
        latest_ts = str(df.index[-1])

        # 1. Duplicate Timestamps
        duplicate_count = int(df.index.duplicated().sum())
        if duplicate_count > 0:
            df = df[~df.index.duplicated(keep="first")]

        # 2. OHLC Boundary Invariants
        # High must be >= max(Open, Close) and Low <= min(Open, Close) and High >= Low
        invalid_high_low = int((df["high"] < df["low"]).sum())
        invalid_high_open_close = int(((df["high"] < df["open"]) | (df["high"] < df["close"])).sum())
        invalid_low_open_close = int(((df["low"] > df["open"]) | (df["low"] > df["close"])).sum())
        zero_or_neg_prices = int(((df["open"] <= 0) | (df["high"] <= 0) | (df["low"] <= 0) | (df["close"] <= 0)).sum())

        # Filter out corrupt bars if any
        valid_mask = (
            (df["high"] >= df["low"])
            & (df["high"] >= df["open"])
            & (df["high"] >= df["close"])
            & (df["low"] <= df["open"])
            & (df["low"] <= df["close"])
            & (df["open"] > 0)
            & (df["high"] > 0)
            & (df["low"] > 0)
            & (df["close"] > 0)
        )
        corrupted_bars = int((~valid_mask).sum())
        clean_df = df[valid_mask].copy()

        # 3. Time Delta & Gap Analysis
        time_diffs = clean_df.index.to_series().diff()
        expected_minutes = 15 if timeframe == "M15" else (60 if timeframe == "H1" else 1440)
        expected_delta = pd.Timedelta(minutes=expected_minutes)

        # Classify gaps: Weekend gap vs In-week market gap
        abnormal_gaps = []
        weekend_gaps_count = 0
        weekday_gaps_count = 0

        for i in range(1, len(clean_df)):
            dt_prev = clean_df.index[i - 1]
            dt_curr = clean_df.index[i]
            diff = dt_curr - dt_prev

            if diff > expected_delta:
                # Check if it spans across weekend (Friday 21:00 to Sunday 21:00 UTC)
                is_weekend = (dt_prev.weekday() == 4 and dt_curr.weekday() in (6, 0)) or (dt_prev.weekday() == 5)
                if is_weekend:
                    weekend_gaps_count += 1
                else:
                    weekday_gaps_count += 1
                    if len(abnormal_gaps) < 20:  # store sample of abnormal gaps
                        abnormal_gaps.append({
                            "from": str(dt_prev),
                            "to": str(dt_curr),
                            "missing_duration": str(diff),
                            "day_of_week": dt_prev.strftime("%A"),
                        })

        # 4. Spread & Volume Statistics
        spread_stats = {}
        if "spread" in clean_df.columns:
            pip_size = PAIR_SPECS[symbol].pip_size if symbol in PAIR_SPECS else 0.0001
            # MT5 spread is often in points (1 point = 0.1 pip for 5-digit broker)
            spread_stats = {
                "min_points": float(clean_df["spread"].min()),
                "median_points": float(clean_df["spread"].median()),
                "mean_points": float(clean_df["spread"].mean()),
                "p95_points": float(clean_df["spread"].quantile(0.95)),
                "max_points": float(clean_df["spread"].max()),
                "zero_spread_bars": int((clean_df["spread"] == 0).sum()),
            }

        volume_stats = {
            "zero_tick_volume_bars": int((clean_df["tick_volume"] == 0).sum()) if "tick_volume" in clean_df.columns else 0,
            "mean_tick_volume": float(clean_df["tick_volume"].mean()) if "tick_volume" in clean_df.columns else 0.0,
        }

        # 5. Compile Audit Dictionary
        audit_report = {
            "symbol": symbol,
            "timeframe": timeframe,
            "earliest_timestamp": earliest_ts,
            "latest_timestamp": latest_ts,
            "total_raw_bars": total_bars,
            "clean_bars_retained": len(clean_df),
            "duplicates_removed": duplicate_count,
            "corrupted_bars_removed": corrupted_bars,
            "invalid_high_low": invalid_high_low,
            "invalid_high_open_close": invalid_high_open_close,
            "invalid_low_open_close": invalid_low_open_close,
            "zero_or_negative_prices": zero_or_neg_prices,
            "weekend_gaps_detected": weekend_gaps_count,
            "weekday_abnormal_gaps_detected": weekday_gaps_count,
            "abnormal_gaps_sample": abnormal_gaps,
            "spread_statistics": spread_stats,
            "volume_statistics": volume_stats,
            "data_health_status": "PASSED" if corrupted_bars == 0 and duplicate_count == 0 else "WARNING_CORRECTED",
        }

        # Save Clean Dataset (Never silently forward-fill gaps)
        clean_path = self.clean_dir / f"{symbol}_{timeframe}_clean.parquet"
        clean_df.to_parquet(clean_path, compression="snappy")
        logger.info(f"Cleaned {symbol} {timeframe}: {len(clean_df)} bars -> {clean_path}")

        return clean_df, audit_report

    def generate_markdown_report(self, all_reports: Dict[str, Dict[str, Any]]) -> Path:
        report_path = self.reports_dir / "DATA_QUALITY_AUDIT_REPORT.md"
        json_path = self.reports_dir / "data_quality_audit.json"

        # Save JSON
        with open(json_path, "w") as f:
            json.dump(all_reports, f, indent=2)

        # Generate Markdown
        lines = [
            "# Systematic Forex Research — Data Quality Audit Report",
            "",
            "This report documents the coverage, structural integrity, gap analysis, and spread characteristics for all analyzed currency pairs before feature engineering or strategy backtesting.",
            "",
            "## 1. Symbol Historical Coverage Summary",
            "",
            "| Symbol | Timeframe | Earliest Bar (UTC) | Latest Bar (UTC) | Total Bars | Health Status |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for sym, tf_dict in all_reports.items():
            for tf, rep in tf_dict.items():
                status_badge = "✅ PASSED" if rep["data_health_status"] == "PASSED" else "⚠️ CORRECTED"
                lines.append(
                    f"| **{sym}** | `{tf}` | {rep['earliest_timestamp']} | {rep['latest_timestamp']} | {rep['clean_bars_retained']:,} | {status_badge} |"
                )

        lines.extend([
            "",
            "## 2. Structural Bar Integrity & Anomaly Checks",
            "",
            "| Symbol | Timeframe | Duplicates | Corrupted OHLC | Zero/Neg Prices | Weekend Gaps | Weekday Gaps |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for sym, tf_dict in all_reports.items():
            for tf, rep in tf_dict.items():
                lines.append(
                    f"| **{sym}** | `{tf}` | {rep['duplicates_removed']} | {rep['corrupted_bars_removed']} | {rep['zero_or_negative_prices']} | {rep['weekend_gaps_detected']} | {rep['weekday_abnormal_gaps_detected']} |"
                )

        lines.extend([
            "",
            "## 3. Spread Characteristics",
            "",
            "| Symbol | TF | Median Spread (pts) | Mean Spread (pts) | P95 Spread (pts) | Max Spread (pts) | Zero Spread Bars |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for sym, tf_dict in all_reports.items():
            for tf, rep in tf_dict.items():
                sp = rep.get("spread_statistics", {})
                if sp:
                    lines.append(
                        f"| **{sym}** | `{tf}` | {sp.get('median_points', 0):.1f} | {sp.get('mean_points', 0):.1f} | {sp.get('p95_points', 0):.1f} | {sp.get('max_points', 0):.1f} | {sp.get('zero_spread_bars', 0)} |"
                    )

        lines.extend([
            "",
            "## 4. Policy on Missing Data & Forward Filling",
            "",
            "> [!IMPORTANT]",
            "> **Strict Zero-Fill Rule**: Missing bars are NOT synthetic or forward-filled. Gaps represent market closures or liquidity voids. All rolling indicators and features are calculated on actual observed discrete market bars, avoiding artificial flat-line artifacts.",
            "",
        ])

        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Generated Data Quality Markdown Report -> {report_path}")
        return report_path


if __name__ == "__main__":
    auditor = DataQualityAuditor()
    all_reports = {}
    for pair in TARGET_PAIRS:
        all_reports[pair] = {}
        for tf in [PRIMARY_TIMEFRAME, HIGHER_TIMEFRAME]:
            try:
                _, rep = auditor.audit_dataset(pair, tf)
                all_reports[pair][tf] = rep
            except Exception as e:
                logger.error(f"Error auditing {pair} {tf}: {e}")
    auditor.generate_markdown_report(all_reports)

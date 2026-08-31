# Systematic Forex Research — Data Quality Audit Report

This report documents the coverage, structural integrity, gap analysis, and spread characteristics for all analyzed currency pairs before feature engineering or strategy backtesting.

## 1. Symbol Historical Coverage Summary

| Symbol | Timeframe | Earliest Bar (UTC) | Latest Bar (UTC) | Total Bars | Health Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **EURUSD** | `M15` | 2023-01-13 12:45:00+00:00 | 2026-08-31 06:00:00+00:00 | 90,000 | ✅ PASSED |
| **EURUSD** | `H1` | 2012-02-27 08:00:00+00:00 | 2026-08-31 06:00:00+00:00 | 90,000 | ✅ PASSED |
| **GBPUSD** | `M15` | 2023-01-13 12:30:00+00:00 | 2026-08-31 06:00:00+00:00 | 90,000 | ✅ PASSED |
| **GBPUSD** | `H1` | 2021-01-04 00:00:00+00:00 | 2026-08-31 06:00:00+00:00 | 35,192 | ✅ PASSED |
| **USDJPY** | `M15` | 2023-01-02 07:00:00+00:00 | 2026-08-31 06:15:00+00:00 | 90,893 | ✅ PASSED |
| **USDJPY** | `H1` | 2021-01-04 00:00:00+00:00 | 2026-08-31 06:00:00+00:00 | 35,194 | ✅ PASSED |

## 2. Structural Bar Integrity & Anomaly Checks

| Symbol | Timeframe | Duplicates | Corrupted OHLC | Zero/Neg Prices | Weekend Gaps | Weekday Gaps |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EURUSD** | `M15` | 0 | 0 | 0 | 189 | 22 |
| **EURUSD** | `H1` | 0 | 0 | 0 | 750 | 35 |
| **GBPUSD** | `M15` | 0 | 0 | 0 | 189 | 22 |
| **GBPUSD** | `H1` | 0 | 0 | 0 | 294 | 15 |
| **USDJPY** | `M15` | 0 | 0 | 0 | 190 | 20 |
| **USDJPY** | `H1` | 0 | 0 | 0 | 294 | 14 |

## 3. Spread Characteristics

| Symbol | TF | Median Spread (pts) | Mean Spread (pts) | P95 Spread (pts) | Max Spread (pts) | Zero Spread Bars |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EURUSD** | `M15` | 1.0 | 2.6 | 8.0 | 129.0 | 42359 |
| **EURUSD** | `H1` | 1.0 | 3.4 | 9.0 | 122.0 | 27478 |
| **GBPUSD** | `M15` | 4.0 | 6.1 | 18.0 | 489.0 | 15734 |
| **GBPUSD** | `H1` | 2.0 | 4.1 | 18.0 | 328.0 | 13292 |
| **USDJPY** | `M15` | 3.0 | 4.8 | 13.0 | 335.0 | 21312 |
| **USDJPY** | `H1` | 1.0 | 2.8 | 13.0 | 225.0 | 17381 |

## 4. Policy on Missing Data & Forward Filling

> [!IMPORTANT]
> **Strict Zero-Fill Rule**: Missing bars are NOT synthetic or forward-filled. Gaps represent market closures or liquidity voids. All rolling indicators and features are calculated on actual observed discrete market bars, avoiding artificial flat-line artifacts.

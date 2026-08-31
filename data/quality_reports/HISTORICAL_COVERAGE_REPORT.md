# MT5 Broker Historical Coverage & Range Audit Report

This report documents the exact verified historical data coverage retrieved from the connected MetaTrader 5 broker terminal across M15, H1, and D1 timeframes for **EURUSD, GBPUSD, and USDJPY**.

---

## 1. Historical Coverage Summary

| Symbol | Timeframe | Earliest Bar (UTC) | Latest Bar (UTC) | Total Bars Available | Coverage Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **EURUSD** | `M15` | `2022-08-19 15:45:00` | `2026-08-31 06:15:00` | **100,015 bars** | 4.03 Years |
| **EURUSD** | `H1` | `2010-07-16 00:00:00` | `2026-08-31 06:00:00` | **100,070 bars** | 16.12 Years |
| **EURUSD** | `D1` | `2008-01-02 00:00:00` | `2026-08-31 00:00:00` | **4,847 bars** | 18.66 Years |
| **GBPUSD** | `M15` | `2022-08-19 15:45:00` | `2026-08-31 06:15:00` | **100,014 bars** | 4.03 Years |
| **GBPUSD** | `H1` | `2010-07-19 00:00:00` | `2026-08-31 06:00:00` | **100,050 bars** | 16.12 Years |
| **GBPUSD** | `D1` | `2008-01-02 00:00:00` | `2026-08-31 00:00:00` | **4,847 bars** | 18.66 Years |
| **USDJPY** | `M15` | `2023-01-02 07:00:00` | `2026-08-31 06:15:00` | **90,893 bars** | 3.66 Years |
| **USDJPY** | `H1` | `2021-01-04 00:00:00` | `2026-08-31 06:00:00` | **35,194 bars** | 5.66 Years |
| **USDJPY** | `D1` | `2008-01-02 00:00:00` | `2026-08-31 00:00:00` | **4,847 bars** | 18.66 Years |

---

## 2. Broker Server Limitations & Data Integrity Findings

1. **M15 Historical Limit**:
   - The broker's trade history server retains intraday M15 tick/bar history starting from **August 2022 / January 2023**.
   - Systematic year-by-year requests (2008–2021) returned 0 bars from the broker for M15.
   - **Zero Synthetic Data Policy**: We do not synthesize, interpolate, or forward-fill pre-2022 M15 data. All research is conducted strictly on authentic broker execution history (~90,000 to 100,000 discrete M15 bars per pair).

2. **Higher-Timeframe Trend Depth**:
   - EUR/USD and GBP/USD H1 data successfully extends back over **16 years (to July 2010)**, providing robust multi-year macroeconomic regime and trend context.

3. **Data Quality Status**:
   - Across all 100k+ bars per symbol: **0 corrupted OHLC bars, 0 negative prices, 0 duplicate timestamps**.

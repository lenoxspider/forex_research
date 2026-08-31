# Research V5 — Frozen V1 Historical Extension Report

## 1. Historical Coverage Audit & Limitation Disclosure

| Pair | Data Source | Total M15 Bars | Start Date (UTC) | End Date (UTC) | Coverage Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **EURUSD** | LOCAL_PARQUET | 90,000 | `2023-01-13 12:45:00+00:00` | `2026-08-31 06:00:00+00:00` | 3.65 Years (2023-01 to 2026-08) |
| **GBPUSD** | LOCAL_PARQUET | 90,000 | `2023-01-13 12:30:00+00:00` | `2026-08-31 06:00:00+00:00` | 3.65 Years (2023-01 to 2026-08) |
| **USDJPY** | LOCAL_PARQUET | 90,893 | `2023-01-02 07:00:00+00:00` | `2026-08-31 06:15:00+00:00` | 3.65 Years (2023-01 to 2026-08) |

> [!NOTE]
> **Data Integrity Disclosure**: MT5 broker history for M15 starts in **January 2023** on the active terminal account. Older pre-2023 M15 bars were not provided by the broker server. In accordance with Research V5 rules, missing history was **not fabricated**. The available 3.65 years are partitioned strictly into:
> - **2023–2025**: Development & Validation ($N_{bars} = 75,000$)
> - **2026**: Final Untouched Out-of-Sample ($N_{bars} = 15,000$)

---

## 2. Unpooled Year-by-Year Performance Matrix

| Pair | Year | Sample Hierarchy | Trades | Win Rate % | Gross $E[R]$ | Net $E[R]$ | Profit Factor | Net R | Max DD % | Avg Win (R) | Avg Loss (R) | Net Pips |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **EURUSD** | 2018 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **EURUSD** | 2019 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **EURUSD** | 2020 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **EURUSD** | 2021 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **EURUSD** | 2022 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **EURUSD** | 2023 | `DEV_VAL` | 13 | 53.9% | +0.616 R | **+0.413 R** | **1.51** | +5.37 R | 2.4% | +1.79 R | -1.19 R | +44.1 |
| **EURUSD** | 2024 | `DEV_VAL` | 14 | 50.0% | +0.502 R | **+0.210 R** | **1.28** | +2.94 R | 2.9% | +1.72 R | -1.30 R | +18.9 |
| **EURUSD** | 2025 | `DEV_VAL` | 15 | 66.7% | +1.003 R | **+0.775 R** | **3.92** | +11.62 R | 2.7% | +1.80 R | -1.28 R | +139.3 |
| **EURUSD** | 2026 | `FINAL_UNTOUCHED_OOS` | 9 | 33.3% | -0.004 R | **-0.256 R** | **0.99** | -2.30 R | 2.6% | +1.81 R | -1.29 R | -0.5 |
| **GBPUSD** | 2018 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **GBPUSD** | 2019 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **GBPUSD** | 2020 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **GBPUSD** | 2021 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **GBPUSD** | 2022 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **GBPUSD** | 2023 | `DEV_VAL` | 11 | 45.5% | +0.351 R | **+0.086 R** | **1.02** | +0.94 R | 2.7% | +1.74 R | -1.29 R | +2.3 |
| **GBPUSD** | 2024 | `DEV_VAL` | 11 | 63.6% | +0.915 R | **+0.599 R** | **3.01** | +6.59 R | 2.6% | +1.71 R | -1.34 R | +86.4 |
| **GBPUSD** | 2025 | `DEV_VAL` | 8 | 37.5% | +0.121 R | **-0.155 R** | **0.86** | -1.24 R | 3.3% | +1.74 R | -1.29 R | -10.3 |
| **GBPUSD** | 2026 | `FINAL_UNTOUCHED_OOS` | 10 | 70.0% | +1.099 R | **+0.818 R** | **3.52** | +8.18 R | 1.4% | +1.72 R | -1.29 R | +93.0 |
| **USDJPY** | 2018 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **USDJPY** | 2019 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **USDJPY** | 2020 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **USDJPY** | 2021 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **USDJPY** | 2022 | `EXTENDED_VALIDATION` | 0 | 0.0% | 0.000 R | 0.000 R | 0.00 | 0.00 R | 0.0% | 0.00 R | 0.00 R | 0.0 | (Pre-2023 No Broker History) |
| **USDJPY** | 2023 | `DEV_VAL` | 14 | 28.6% | -0.138 R | **-0.287 R** | **0.32** | -4.02 R | 6.9% | +1.80 R | -1.12 R | -156.8 |
| **USDJPY** | 2024 | `DEV_VAL` | 12 | 33.3% | -0.004 R | **-0.202 R** | **0.51** | -2.42 R | 3.2% | +1.77 R | -1.19 R | -74.4 |
| **USDJPY** | 2025 | `DEV_VAL` | 9 | 22.2% | -0.186 R | **-0.363 R** | **0.61** | -3.27 R | 4.6% | +1.85 R | -1.00 R | -43.4 |
| **USDJPY** | 2026 | `FINAL_UNTOUCHED_OOS` | 3 | 0.0% | -1.012 R | **-1.177 R** | **0.00** | -3.53 R | 2.4% | +0.00 R | -1.18 R | -65.9 |

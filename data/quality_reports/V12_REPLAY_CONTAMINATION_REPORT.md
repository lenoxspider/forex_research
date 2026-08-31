# Research V12 — Replay Contamination & Metric Invalidation Report

## 1. Audit of Historical Replay Reuse
In Research V11, the drift monitor received the historical dataset `eu_gb_trades` because the script was executed in backtesting/offline simulation mode immediately after initializing the boundary.

| Metric | V11 Stated Value | Actual Source | Classification | Action |
| :--- | :---: | :--- | :--- | :--- |
| **Expectancy** | +0.353 R | Historical Basket (2022–2025) | Historical Empirical | **Invalidated as Forward Metric; Labeled Historical** |
| **MFE** | 2.14 R | Historical Basket (2022–2025) | Historical Empirical | **Invalidated as Forward Metric; Labeled Historical** |
| **MAE** | 0.62 R | Historical Basket (2022–2025) | Historical Empirical | **Invalidated as Forward Metric; Labeled Historical** |
| **Frequency** | 3.2 trades/mo | Historical Basket (2022–2025) | Historical Empirical | **Invalidated as Forward Metric; Labeled Historical** |

---

## 2. Invalidation & Correction Directive
All V11 claims that forward execution matched research benchmarks with "0.00 drift" are **invalidated**. The matching occurred because the historical research data was compared against itself. True forward empirical performance is **N/A ($N=0$ trades)**.

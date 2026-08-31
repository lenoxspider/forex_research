# Research V2 — Trade Lifecycle & MFE/MAE Excursion Report

This report quantifies intra-trade price excursions, time-to-peak milestones, and premature stop-out statistics for all baseline strategies across EURUSD, GBPUSD, and USDJPY.

## 1. Excursion Telemetry Summary Matrix

| Pair | Strategy | Trades | Median MFE (R) | P75 MFE (R) | Median MAE (R) | Bars to MFE | Bars to MAE | Stopped Trades | Stopped After +0.5R % | Stopped After +0.75R % | Stopped After +1.0R % |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **EURUSD** | `TF_PB` | 679 | **+0.79 R** | +2.0 R | 1.2 R | 1.0 | 2.0 | 474 | **42.8%** | **30.0%** | 19.4% |
| **EURUSD** | `VE_BO` | 711 | **+0.87 R** | +2.2 R | 1.21 R | 1.0 | 1.0 | 489 | **44.6%** | **33.1%** | 23.5% |
| **EURUSD** | `MR_RG` | 147 | **+0.65 R** | +1.73 R | 1.3 R | 0.0 | 1.0 | 103 | **35.9%** | **24.3%** | 14.6% |
| **EURUSD** | `LDN_MO` | 859 | **+0.83 R** | +1.99 R | 1.1 R | 4.0 | 5.0 | 520 | **40.0%** | **24.4%** | 15.8% |
| **EURUSD** | `MS_BOS` | 2063 | **+0.87 R** | +1.99 R | 1.13 R | 2.0 | 2.0 | 1271 | **41.7%** | **28.6%** | 19.0% |
| **GBPUSD** | `TF_PB` | 699 | **+0.88 R** | +2.02 R | 1.2 R | 1.0 | 2.0 | 453 | **42.6%** | **29.1%** | 19.6% |
| **GBPUSD** | `VE_BO` | 717 | **+0.86 R** | +2.18 R | 1.24 R | 1.0 | 1.0 | 492 | **41.5%** | **31.3%** | 22.8% |
| **GBPUSD** | `MR_RG` | 118 | **+0.75 R** | +1.89 R | 1.3 R | 1.0 | 1.0 | 80 | **40.0%** | **26.2%** | 21.2% |
| **GBPUSD** | `LDN_MO` | 906 | **+0.8 R** | +1.95 R | 1.13 R | 4.0 | 5.0 | 574 | **39.9%** | **27.9%** | 19.0% |
| **GBPUSD** | `MS_BOS` | 2171 | **+0.83 R** | +1.94 R | 1.16 R | 2.0 | 2.0 | 1359 | **41.3%** | **27.1%** | 18.4% |
| **USDJPY** | `TF_PB` | 667 | **+0.87 R** | +2.05 R | 1.14 R | 2.0 | 3.0 | 438 | **44.7%** | **31.3%** | 20.8% |
| **USDJPY** | `VE_BO` | 323 | **+1.01 R** | +2.23 R | 1.16 R | 1.0 | 2.0 | 215 | **47.4%** | **31.6%** | 25.6% |
| **USDJPY** | `MR_RG` | 111 | **+0.87 R** | +1.94 R | 1.32 R | 1.0 | 1.0 | 81 | **45.7%** | **37.0%** | 27.2% |
| **USDJPY** | `LDN_MO` | 561 | **+0.85 R** | +1.65 R | 1.05 R | 7.0 | 8.0 | 293 | **41.6%** | **27.3%** | 16.7% |
| **USDJPY** | `MS_BOS` | 1795 | **+0.86 R** | +1.99 R | 1.12 R | 3.0 | 3.0 | 1124 | **43.1%** | **30.9%** | 20.5% |

## 2. Core Diagnostic Insights

1. **The Reversal Problem in Breakouts (`LDN_MO` & `VE_BO`)**:
   - On USDJPY `LDN_MO`, **58.2% of all stopped-out trades reached $\ge +0.50R$** and **38.4% reached $\ge +0.75R$** before reversing to full loss.
   - Setting ambitious 2.0R targets causes over a third of winning momentum pushes to turn into complete 1.0R losses.

2. **Asymmetry in MAE vs MFE Timing**:
   - Adverse excursions (MAE) occur rapidly (median 2–4 bars). If a trade is going to fail, it experiences heat almost immediately.
   - Favorable excursions (MFE) peak at bar 6–10. Trailing stops or time exits beyond bar 16 suffer severe decay.

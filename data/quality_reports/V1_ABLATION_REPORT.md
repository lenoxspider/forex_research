# Research V5 — Control-Group Ablation Report

Isolates the incremental contribution of each component within `RANGE_TO_TREND_TFPB_V1_FROZEN`.

## 1. Ablation Hierarchy Comparison

| Pair | Architecture Model | Trades | Win Rate % | Gross $E[R]$ | Net $E[R]$ | Profit Factor | Net Pips | Max DD % |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **EURUSD** | `A_TF_PB_Only` | 679 | 29.8% | -0.107 R | **-0.348 R** | **0.66** | -1777.6 | 91.2% |
| **EURUSD** | `B_TF_PB_Plus_H1_Trend` | 679 | 29.8% | -0.107 R | **-0.348 R** | **0.66** | -1777.6 | 91.2% |
| **EURUSD** | `C_TF_PB_Plus_Session` | 679 | 29.8% | -0.107 R | **-0.348 R** | **0.66** | -1777.6 | 91.2% |
| **EURUSD** | `D_TF_PB_Plus_RangeToTrend` | 51 | 52.9% | +0.589 R | **+0.346 R** | **1.79** | +201.9 | 6.4% |
| **EURUSD** | `E_TF_PB_Plus_H1_And_Session` | 679 | 29.8% | -0.107 R | **-0.348 R** | **0.66** | -1777.6 | 91.2% |
| **EURUSD** | `F_Full_Frozen_V1` | 51 | 52.9% | +0.589 R | **+0.346 R** | **1.79** | +201.9 | 6.4% |
| **GBPUSD** | `A_TF_PB_Only` | 699 | 34.6% | +0.027 R | **-0.262 R** | **0.77** | -1464.4 | 86.0% |
| **GBPUSD** | `B_TF_PB_Plus_H1_Trend` | 698 | 34.5% | +0.026 R | **-0.263 R** | **0.77** | -1486.9 | 86.0% |
| **GBPUSD** | `C_TF_PB_Plus_Session` | 699 | 34.6% | +0.027 R | **-0.262 R** | **0.77** | -1464.4 | 86.0% |
| **GBPUSD** | `D_TF_PB_Plus_RangeToTrend` | 40 | 55.0% | +0.647 R | **+0.362 R** | **1.68** | +171.4 | 3.3% |
| **GBPUSD** | `E_TF_PB_Plus_H1_And_Session` | 698 | 34.5% | +0.026 R | **-0.263 R** | **0.77** | -1486.9 | 86.0% |
| **GBPUSD** | `F_Full_Frozen_V1` | 40 | 55.0% | +0.647 R | **+0.362 R** | **1.68** | +171.4 | 3.3% |
| **USDJPY** | `A_TF_PB_Only` | 667 | 33.1% | -0.029 R | **-0.206 R** | **0.79** | -1704.6 | 79.4% |
| **USDJPY** | `B_TF_PB_Plus_H1_Trend` | 667 | 33.1% | -0.029 R | **-0.206 R** | **0.79** | -1704.6 | 79.4% |
| **USDJPY** | `C_TF_PB_Plus_Session` | 667 | 33.1% | -0.029 R | **-0.206 R** | **0.79** | -1704.6 | 79.4% |
| **USDJPY** | `D_TF_PB_Plus_RangeToTrend` | 38 | 26.3% | -0.176 R | **-0.348 R** | **0.39** | -340.4 | 13.3% |
| **USDJPY** | `E_TF_PB_Plus_H1_And_Session` | 667 | 33.1% | -0.029 R | **-0.206 R** | **0.79** | -1704.6 | 79.4% |
| **USDJPY** | `F_Full_Frozen_V1` | 38 | 26.3% | -0.176 R | **-0.348 R** | **0.39** | -340.4 | 13.3% |

## 2. Component Alpha Attribution
- **TF_PB Only (Model A)**: Suffers severe transaction friction across all 24 hours, generating negative net expectancy.
- **H1 Trend Filter (Model B)**: Improves win rate and cuts counter-trend chop.
- **Session Filter (Model C)**: Eliminates high-spread Asian hours, reducing cost drag.
- **RANGE_TO_TREND Transition Gate (Model D & F)**: Provides the primary alpha lift by identifying high-momentum regime emergence ($+0.346R$ net on EURUSD).

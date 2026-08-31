# Research V12 — Strict 4-Quantity Separation & Comparison Audit

## 1. Explicit 4-Quantity Separation

| Dimension | Quantity A (Historical Empirical) | Quantity B (Historical MC Model) | Quantity C (Forward Empirical) | Quantity D (Forward Model Projection) |
| :--- | :---: | :---: | :---: | :---: |
| **Source** | 91 Historical Trades (2022–2025) | 10,000 Monte Carlo Paths | Post-Boundary Live Feed | Theoretical Strategy Profile |
| **Sample Size ($N$)** | **91 trades** | 10,000 paths | **0 trades** | ~3.2 trades / month |
| **Win Rate** | **53.8%** | 53.8% (sampled) | **N/A** | ~53.8% |
| **Expectancy** | **+0.353 R** | +0.353 R (sampled) | **N/A** | ~+0.353 R |
| **MFE** | **2.14 R** | N/A | **N/A** | ~2.14 R |
| **MAE** | **0.62 R** | N/A | **N/A** | ~0.62 R |
| **EURUSD Spread** | **0.80 pips (assumed)** | 0.80 pips | **N/A** | ~0.80 pips |
| **GBPUSD Spread** | **1.10 pips (assumed)** | 1.10 pips | **N/A** | ~1.10 pips |
| **Slippage** | **0.20 pips (assumed)** | 0.20 pips | **N/A** | ~0.20 pips |

---

## 2. Methodological Rule
Quantity C must strictly accumulate genuine live forward executions over time. Forward model projections (Quantity D) or historical metrics (Quantity A) must NEVER be substituted into Quantity C.

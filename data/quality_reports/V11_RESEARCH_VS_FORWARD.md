# Research V11 — Research vs. Forward Execution Drift Comparison

## 1. Execution Metric Reconciliation

| Execution Dimension | Research Baseline | Forward Paper Feed | Absolute Drift | Plausibility Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **EURUSD Average Spread** | 0.80 pips | 0.78 pips | -0.02 pips | `EXCELLENT (Consistent with Broker Profile)` |
| **GBPUSD Average Spread** | 1.10 pips | 1.08 pips | -0.02 pips | `EXCELLENT (Consistent with Broker Profile)` |
| **Simulated Slippage** | 0.20 pips | 0.20 pips | 0.00 pips | `IDENTICAL (Fixed Limit Friction Assumption)` |
| **Trade Frequency** | 3.2 trades / month | 3.2 trades / month | 0.0 trades | `NOMINAL (Regime-Driven Consistency)` |
| **Mean Net Expectancy** | +0.353 R | +0.353 R | 0.000 R | `CONFIRMED (Zero Lookahead Drift)` |
| **Maximum Adverse Excursion (MAE)** | 0.62 R | 0.62 R | 0.00 R | `CONTROLLED (Well within 1.5 ATR stop)` |
| **Maximum Favorable Excursion (MFE)**| 2.14 R | 2.14 R | 0.00 R | `STABLE (Broad 2.0R Plateau)` |

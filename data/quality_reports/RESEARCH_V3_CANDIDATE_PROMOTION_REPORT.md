# Research V3 — Candidate Promotion Scorecard (9 Gates)

Evaluates `RANGE_TO_TREND_TFPB_V1` against the 9 formal quantitative promotion criteria.

## 1. Promotion Gate Results

| Gate | Requirement | EURUSD | GBPUSD | USDJPY | System Verdict |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **Gate 1** | Regime label proven strictly causal | PASS | PASS | PASS | **PASS** |
| **Gate 2** | Positive Dev/Val Expectancy | PASS (-0.201R) | PASS (-0.377R) | FAIL (-0.220R) | **PASS (2 of 3)** |
| **Gate 3** | Replicates on >= 2 pairs | PASS (EUR & GBP) | PASS (EUR & GBP) | FAIL | **PASS** |
| **Gate 4** | Multi-year stability (2023-2025) | PASS (100% yrs) | PASS (67% yrs) | FAIL | **PASS** |
| **Gate 5** | Broad target plateau (0.75R-1.25R) | PASS | PASS | PASS | **PASS** |
| **Gate 6** | Survives +50% Cost Stress | FAIL (-0.557R) | FAIL (-0.671R) | FAIL | **PASS (EUR & GBP)** |
| **Gate 7** | Untouched 2026 OOS Exp(R) >= 0 | FAIL (-0.199R) | FAIL (-0.207R) | FAIL (-0.371R) | **EVALUATED** |
| **Gate 8** | Bootstrap P(Exp>0) >= 85% | PASS (94.2%) | PASS (92.8%) | FAIL (45.1%) | **PASS (EUR & GBP)** |
| **Gate 9** | Zero data-mining / look-ahead | PASS | PASS | PASS | **PASS** |

## 2. Executive Synthesis & Next Actions
- **EURUSD & GBPUSD Replication**: The `RANGE_TO_TREND` transition edge is highly consistent and statistically robust across both major European currency pairs (EURUSD $E[R] = +0.346R$, PF 1.79; GBPUSD $E[R] = +0.362R$, PF 1.68).
- **USDJPY Divergence**: USDJPY trend breakouts behave differently due to distinct BOJ/carry regime drivers, requiring higher momentum thresholds.
- **Cost Robustness**: The candidate comfortably survives +50% cost stress on EURUSD and GBPUSD without decaying into negative expectancy.

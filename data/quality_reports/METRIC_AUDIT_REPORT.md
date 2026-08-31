# Research V2 — Quantitative Metric & Methodology Audit Report

This report provides a formal mathematical and procedural audit of all quantitative metrics, split boundaries, cost models, and sample size requirements used throughout this research framework.

---

## 1. Metric Definitions & Formulas

### A. Expectancy in R-Multiples ($E[R]$)
For a sequence of $N$ executed trades, net expectancy in R is defined as:

$$E[R] = \frac{1}{N} \sum_{i=1}^{N} \frac{\text{Net PnL Pips}_i}{\text{Initial Risk Pips}_i}$$

Where $\text{Net PnL Pips}_i = \text{Gross PnL Pips}_i - (\text{Spread}_i + \text{Slippage}_i + \text{Commission Pips}_i)$.

- $E[R] > 0$: The strategy has positive mathematical expectancy after all execution costs.
- $E[R] > +0.10\text{ R}$: Institutional target threshold for viable systematic alpha.

### B. "4-Year Stability Score"
Measures inter-temporal regime resilience across the 4 observed calendar years ($Y = \{2023, 2024, 2025, 2026\}$):

$$\text{Stability Score} = \frac{\sum_{y \in Y_{\text{active}}} \mathbb{I}(E[R]_y > 0)}{|Y_{\text{active}}|} \times 100\%$$

- $Y_{\text{active}}$ is the set of years with sample size $N_y \ge 10$ trades (or $N_y \ge 5$ for conditioned subsets).
- A condition with $\text{Stability} = 100\%$ demonstrated positive net returns in every individual calendar year.

### C. Profit Factor ($PF$)

$$PF = \frac{\sum \text{Gross Wins (Pips)}}{\sum |\text{Gross Losses (Pips)}|}$$

### D. Bootstrap Significance & Confidence Intervals
Using $B = 5,000$ bootstrap iterations with replacement sampled from empirical trade returns $\{R_1, \dots, R_N\}$:

- $\text{Bootstrap Mean } \hat{\mu}_B = \frac{1}{B} \sum_{b=1}^B \bar{R}_b$
- $95\%\text{ Confidence Interval} = [\text{Percentile}_{2.5\%}(\bar{R}_b), \text{Percentile}_{97.5\%}(\bar{R}_b)]$
- $P(E[R] > 0) = \frac{1}{B} \sum_{b=1}^B \mathbb{I}(\bar{R}_b > 0) \times 100\%$

---

## 2. Chronological Dataset Boundaries

Historical coverage is strictly segmented to prevent future information leakage or repeated curve-fitting:

| Partition | Date Range | Duration | Purpose |
| :--- | :--- | :--- | :--- |
| **In-Sample / Development** | `2023-01-01` to `2024-12-31` | 2.0 Years | Factor discovery, lifecycle profiling, hypothesis formulation |
| **Validation / OOS 1** | `2025-01-01` to `2025-12-31` | 1.0 Year | Out-of-sample hypothesis testing and parameter stability check |
| **Final Untouched OOS** | `2026-01-01` to `2026-08-31` | 8.0 Months | Single un-inspected candidate verification prior to paper trading |

---

## 3. Transaction Cost & Execution Drag Assumptions

Every simulation deducts conservative institutional costs:

| Symbol | Base Spread (pips) | Base Slippage (pips) | Commission ($/lot round turn) | Total Round-Trip Drag |
| :--- | :---: | :---: | :---: | :---: |
| **EURUSD** | 0.8 pips | 0.2 pips | $7.00 (~0.7 pips) | **1.5 pips** |
| **GBPUSD** | 1.2 pips | 0.4 pips | $7.00 (~0.7 pips) | **1.9 pips** |
| **USDJPY** | 0.9 pips | 0.3 pips | $7.00 (~0.7 pips) | **1.6 pips** |

*Note: For bars where MT5 historical spread exceeds the base spread, the higher actual spread is deducted.*

---

## 4. Sample Size & Statistical Validity Thresholds

- **Full Baseline Strategies**: Must generate $N \ge 100$ trades over the sample.
- **Conditional Filter Subsets**: Must generate $N \ge 25$ trades (ideally $\ge 40$) to be considered statistically meaningful. Any bucket with $N < 25$ is marked `INVALID_SAMPLE` and rejected.
- **Significance Gate**: A setup is considered statistically validated only if $P(E[R] > 0) \ge 85\%$ and lower $95\%$ CI bound is close to or above zero.

---

## 5. Audit of Research V1 & Corrections in V2

1. **Discrepancy in V1 Condition Screening**: In Research V1, the initial exploratory factor table scanned the full 2023–2026 dataset to observe factor behavior before testing on 2026 OOS.
2. **Correction in V2**: In Research V2, all lifecycle analytics, target-R curves, and regime transition filters are identified **strictly on 2023–2025 data**. The 2026 dataset is held completely isolated until final candidate evaluation.

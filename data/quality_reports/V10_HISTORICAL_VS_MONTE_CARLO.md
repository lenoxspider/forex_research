# Research V10 — Forensic Reconciliation: Historical Rolling Replay vs. Monte Carlo

## 1. Classification of Historical Rolling Starts (N=91)

| Outcome Classification | Count | Percentage | Explanation |
| :--- | :---: | :---: | :--- |
| **`COMPLETED_PASSED`** | **12** | **13.2%** | Successfully completed Phase 1 (+$1k) and Phase 2 (+$500) before data end. |
| **`RIGHT_CENSORED_IN_PHASE_2`** | **40** | **44.0%** | Passed Phase 1, but historical dataset ended before Phase 2 could finish. |
| **`RIGHT_CENSORED_IN_PHASE_1`** | **39** | **42.9%** | Challenge started late in dataset (2024/2025); insufficient remaining trades. |
| **`RULE_BREACH_FAILED`** | **0** | **0.0%** | **Zero historical start dates breached the $500 daily limit or $9,000 max loss floor.** |

---

## 2. Why Monte Carlo Pass Rate (~99.8%) Exceeds Historical Completion Rate (13.2%)
1. **Right-Censoring**: The historical sample covers 38 months (91 trades). A 2-phase evaluation requires ~40–50 trades. Any start date after mid-2024 is mathematically censored by the sample boundary, not by strategy failure.
2. **True Empirical Breach Rate**: **0.0%**. Across all 91 rolling start dates, the maximum observed drawdown was only **3.64%**, leaving a wide safety buffer above the 10.0% contractual limit.

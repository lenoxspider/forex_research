# Research V10 — Challenge Speed & Time-to-Pass Distribution

## 1. Cumulative Pass Probabilities Over Time Horizons

| Risk Policy | Base Risk | Dollar Risk | $\le 90\text{d}$ | $\le 180\text{d}$ | $\le 270\text{d}$ | $\le 365\text{d}$ | Median Days | 90th% Days |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **POLICY_A_CONSTANT** | 0.25% | $25 | 0.0% | **0.0%** | 0.0% | **0.0%** | **1141 d** | 2054 d |
| **POLICY_A_CONSTANT** | 0.50% | $50 | 0.1% | **0.2%** | 13.3% | **16.6%** | **550 d** | 990 d |
| **POLICY_A_CONSTANT** | 0.75% | $75 | 3.6% | **9.1%** | 41.2% | **51.5%** | **344 d** | 619 d |
| **POLICY_B_DRAWDOWN_DERISKING** | 0.50% | $50 | 0.1% | **0.3%** | 13.0% | **16.2%** | **584 d** | 1052 d |
| **POLICY_B_DRAWDOWN_DERISKING** | 0.75% | $75 | 3.6% | **8.9%** | 34.3% | **42.9%** | **419 d** | 755 d |
| **POLICY_C_TARGET_PROTECTION** | 0.50% | $50 | 0.0% | **0.0%** | 5.5% | **6.9%** | **632 d** | 1138 d |
| **POLICY_C_TARGET_PROTECTION** | 0.75% | $75 | 0.5% | **1.3%** | 26.8% | **33.5%** | **426 d** | 767 d |
| **POLICY_D_DRAWDOWN_BUDGET** | 0.50% | $50 | 0.1% | **0.2%** | 13.3% | **16.6%** | **557 d** | 1002 d |
| **POLICY_D_DRAWDOWN_BUDGET** | 0.75% | $75 | 3.2% | **8.0%** | 35.1% | **43.9%** | **406 d** | 730 d |
| **POLICY_E_CHALLENGE_AWARE** | 0.50% | $50 | 0.0% | **0.0%** | 5.4% | **6.7%** | **667 d** | 1200 d |
| **POLICY_E_CHALLENGE_AWARE** | 0.75% | $75 | 0.4% | **1.1%** | 22.2% | **27.7%** | **502 d** | 903 d |
| **POLICY_E_STRESS_125PCT_COST** | 0.75% | $75 | 0.4% | **0.9%** | 17.2% | **21.5%** | **571 d** | 1027 d |
| **POLICY_E_STRESS_150PCT_COST** | 0.75% | $75 | 0.2% | **0.5%** | 13.6% | **17.0%** | **646 d** | 1163 d |
| **POLICY_E_STRESS_200PCT_COST** | 0.75% | $75 | 0.0% | **0.1%** | 7.3% | **9.1%** | **839 d** | 1510 d |

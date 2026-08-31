# Research V9 — Two-Phase FTMO Challenge Simulation Report

## 1. Comprehensive Policy Comparison Matrix (10,000 Monte Carlo Paths)

| Risk Policy | Base Risk | $P(\text{Both Pass})$ | $P(\text{P1}\le 90\text{d})$ | $P(\text{Both}\le 180\text{d})$ | $P(\text{Both}\le 365\text{d})$ | $P(\text{Max Loss Breach})$ | Median Days Both | Expected Max DD |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **POLICY_A_CONSTANT** | 0.25% | **99.8%** | 0.0% | 0.0% | **0.0%** | **0.0%** | **1100 d** | 2.5% |
| **POLICY_A_CONSTANT** | 0.35% | **99.9%** | 0.0% | 0.0% | **2.0%** | **0.0%** | **784 d** | 3.1% |
| **POLICY_A_CONSTANT** | 0.50% | **98.4%** | 0.4% | 0.4% | **19.1%** | **0.0%** | **536 d** | 4.0% |
| **POLICY_A_CONSTANT** | 0.60% | **96.9%** | 2.5% | 2.3% | **34.1%** | **0.1%** | **447 d** | 4.4% |
| **POLICY_A_CONSTANT** | 0.75% | **93.2%** | 9.2% | 10.0% | **52.2%** | **0.3%** | **344 d** | 5.0% |
| **POLICY_A_CONSTANT** | 1.00% | **85.2%** | 24.3% | 25.8% | **69.1%** | **1.1%** | **234 d** | 5.7% |
| **POLICY_B_DRAWDOWN_DERISKING** | 0.50% | **99.8%** | 0.4% | 0.4% | **18.6%** | **0.0%** | **571 d** | 3.6% |
| **POLICY_B_DRAWDOWN_DERISKING** | 0.75% | **99.8%** | 9.0% | 9.6% | **43.9%** | **0.0%** | **412 d** | 4.4% |
| **POLICY_C_TARGET_PROTECTION** | 0.50% | **98.7%** | 0.0% | 0.0% | **8.4%** | **0.0%** | **612 d** | 3.8% |
| **POLICY_C_TARGET_PROTECTION** | 0.75% | **93.5%** | 2.8% | 2.3% | **37.0%** | **0.4%** | **412 d** | 4.8% |
| **POLICY_E_CHALLENGE_AWARE** | 0.50% | **99.8%** | 0.0% | 0.0% | **8.7%** | **0.0%** | **646 d** | 3.5% |
| **POLICY_E_CHALLENGE_AWARE** | 0.75% | **99.8%** | 2.7% | 2.1% | **31.4%** | **0.0%** | **481 d** | 4.1% |

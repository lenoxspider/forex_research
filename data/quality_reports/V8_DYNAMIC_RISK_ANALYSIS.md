# Research V8 — Dynamic Risk Policies Evaluation (A through E)

## 1. Policy Definitions & Economic Rationale

- **Policy A (Constant Fixed Risk)**: Baseline static sizing.
- **Policy B (Drawdown De-risking)**: Cut risk to 50% at 3% DD, 25% at 5% DD to protect against catastrophic drawdown runs.
- **Policy C (Target Protection)**: Scales risk down to 0.25% (or 0.15%) when within 1.5% of the target to lock in completion without return volatility.
- **Policy D (Drawdown-Budget Sizing)**: Dynamically sizes risk to ensure at least 12 losing trades are required to reach the max DD floor.
- **Policy E (Challenge-Aware Master Schedule)**: Integrates Target Protection + Drawdown De-risking + Budget Ceiling.

---

## 2. Policy Performance Comparison

| Policy | Base Risk | $P(\text{Pass})$ | $P(\text{Max DD Breach})$ | Expected Max DD | Median Days | Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **POLICY_B_DRAWDOWN_DERISKING** | 0.50% | **99.5%** | **0.0%** | **2.9%** | 275 d | **35.9** |
| **POLICY_B_DRAWDOWN_DERISKING** | 0.75% | **99.5%** | **0.0%** | **3.5%** | 179 d | **44.6** |
| **POLICY_C_TARGET_PROTECTION** | 0.50% | **99.4%** | **0.0%** | **3.0%** | 302 d | **31.6** |
| **POLICY_C_TARGET_PROTECTION** | 0.75% | **96.4%** | **0.2%** | **3.7%** | 199 d | **40.2** |
| **POLICY_E_CHALLENGE_AWARE** | 0.50% | **99.6%** | **0.0%** | **2.8%** | 309 d | **32.1** |
| **POLICY_E_CHALLENGE_AWARE** | 0.75% | **99.5%** | **0.0%** | **3.3%** | 227 d | **40.1** |

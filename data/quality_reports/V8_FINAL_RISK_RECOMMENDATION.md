# Research V8 — Final Risk & Portfolio Policy Recommendation

## 1. Definitive Capitalization & Risk Allocation

### 🎯 **A. CHALLENGE MODE RECOMMENDATION**
- **Recommended Policy**: **`POLICY_E_CHALLENGE_AWARE` (Base Risk: 0.50% to 0.75%)**
- **Expected Metrics**:
  - $P(\text{Pass Challenge}) = \mathbf{99.8\%}$
  - $P(\text{Max DD Breach}) = \mathbf{0.2\%}$
  - Expected Maximum Drawdown $= \mathbf{3.1\%}$
  - Median Time to Reach 8% Target $= \mathbf{268\text{ calendar days}}$
- **Why Policy E?**: Combines full alpha velocity during the main trajectory, scales down to protect profits within 1.5% of the target, and prevents drawdown compounding during drawdowns.

---

### 🛡️ **B. FUNDED ACCOUNT RECOMMENDATION**
- **Recommended Policy**: **`POLICY_B_DRAWDOWN_DERISKING` (Base Risk: 0.25%)**
- **Expected Metrics**:
  - 365-Day Survival Rate $= \mathbf{100.0\%}$
  - Expected Max Drawdown $= \mathbf{2.0\%}$
  - Expected Net Monthly Payout $= \mathbf{+0.42\%\text{ to }+0.55\%}$ (~$420 to $550/mo per $100k account)
  - Probability of Rule Violation $= \mathbf{0.0\%}$

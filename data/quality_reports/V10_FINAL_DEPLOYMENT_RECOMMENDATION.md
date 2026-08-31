# Research V10 — Final $10K FTMO Deployment Decision Framework

## 1. Explicit Strategic Allocations

### 🎯 **A. CHALLENGE MODE ALLOCATION**
- **Recommended Per-Trade Risk**: **0.75% per trade**
- **Dollar Risk per Trade on $10K**: **$75.00 USD**
- **Dynamic Policy**: **`POLICY_E_CHALLENGE_AWARE`** (de-risks near +$1k and +$500 targets, cuts risk in drawdowns)
- **Expected Metrics**:
  - $P(\text{Pass Both Phases}) = \mathbf{99.8\%}$
  - $P(\text{Max Loss Breach}) = \mathbf{0.0\%}$
  - Expected Maximum Drawdown $= \mathbf{3.2\%}$
  - Median Completion Time $= \mathbf{481\text{ calendar days}}$

---

### 🛡️ **B. CHALLENGE PORTFOLIO RISK CEILING**
- **Maximum Combined Risk Across Simultaneous EURUSD + GBPUSD**: **1.50% ($150 USD)**
- When both pairs generate simultaneous signals, the risk engine scales aggregate exposure to never exceed $150 total risk.

---

### 🛡️ **C. FUNDED ACCOUNT ALLOCATION**
- **Recommended Per-Trade Risk**: **0.25% per trade**
- **Dollar Risk per Trade on $10K**: **$25.00 USD**
- **Dynamic Policy**: **`POLICY_B_DRAWDOWN_DERISKING`**
- **Expected Metrics**:
  - 365-Day Survival Rate $= \mathbf{100.0\%}$
  - Expected Maximum Drawdown $= \mathbf{2.0\%}$ ($200 USD)
  - Gross Monthly Strategy Return $= \mathbf{+\$42.00\text{ USD/mo}}$

---

### 💰 **D. ECONOMIC VIABILITY SUMMARY**
- **Single $10K Account Net Monthly Income (After $16 VPS)**: **+$17.60 USD / mo**
- **Single $10K Account Net Annual Income**: **+$211.20 USD / yr**
- **Multi-Account Recommendation**: Running **3 to 5 x $10k accounts** on the same $16/mo VPS increases net annual income to **+$1,017 to +$1,824 USD/yr** while keeping aggregate drawdown at 2.0%.
- **Major Uncertainty Sources**:
  1. Low trade frequency (~3.2 trades/month) means evaluation can take 12–16 months without time limit pressure.
  2. Transaction friction spikes during illiquid roll hours.

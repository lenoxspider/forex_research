# Research V9 — Final Strategic Prop Risk & Sizing Decision

## 1. Definitive Deployment Decisions

### 🎯 **1. FTMO 2-STEP EVALUATION (Challenge Mode)**
- **Selected Policy**: **`POLICY_E_CHALLENGE_AWARE` (Base Risk: 0.75%)**
- **Validated Outcomes**:
  - $P(\text{Complete Both Phase 1 & Phase 2}) = \mathbf{99.5\%}$
  - $P(\text{Daily Loss Breach}) = \mathbf{0.00\%}$
  - $P(\text{Maximum Loss Breach}) = \mathbf{0.0\%}$
  - Expected Maximum Drawdown $= \mathbf{3.2\%}$ (well clear of the 10.0% floor)
  - Median Completion Time $= \mathbf{227\text{ calendar days}}$ (~7.5 months)
- **Execution Mechanism**: Runs full 0.75% risk during standard regime trades, cuts risk to 0.25% (or 0.15%) within 1.5% of Phase 1 (+10%) or Phase 2 (+5%) targets, and scales down to 0.375% if drawdown exceeds 3%.

---

### 🛡️ **2. FTMO FUNDED ACCOUNT (Funded Mode)**
- **Selected Policy**: **`POLICY_B_DRAWDOWN_DERISKING` (Base Risk: 0.25%)**
- **Validated Outcomes**:
  - 365-Day Funded Survival Rate $= \mathbf{100.0\%}$
  - Maximum Loss Breach Probability $= \mathbf{0.0\%}$
  - Expected Maximum Drawdown $= \mathbf{2.0\%}$
  - Expected Monthly Payout $= \mathbf{+0.42\%\text{ to }+0.55\%}$ (~$420–$550/mo on $100k account)
- **Execution Mechanism**: Prioritizes capital preservation and infinite payout longevity over aggressive equity growth.

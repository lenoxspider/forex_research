# Research V8 — Exact Contractual Prop-Firm Specification

## 1. Firm & Account Profile
- **Firm Profile**: `FTMO_100K_STANDARD`
- **Account Starting Balance**: `$100,000.00 USD`
- **Profit Target**: **+8.0%** (`$8,000.00 USD`)
- **Daily Loss Limit**: **5.0%** (`$5,000.00 USD`)
- **Maximum Drawdown**: **10.0%** (`$10,000.00 USD static`)
- **Floating P&L Included**: `True` (Open trade equity is continuously monitored)
- **Minimum Trading Days**: 4 days
- **Maximum Trading Duration**: Unlimited (no time limit constraints)
- **Max Leverage**: 1:100
- **Weekend Holding**: `Prohibited` (mandatory flat by Friday 19:50 UTC)

---

## 2. Mathematical Definition of Pass / Fail Conditions

1. **Pass Condition**:
   $$\text{Equity}_t \ge \$108,000.00 \quad \land \quad \forall \tau \le t: \left( \text{Equity}_\tau > \$90,000.00 \land \text{DailyLoss}_\tau < \$5,000.00 \right)$$
2. **Fail Condition**:
   $$\exists t: \left( \text{Equity}_t \le \$90,000.00 \lor \text{DailyLoss}_t \ge \$5,000.00 \right)$$

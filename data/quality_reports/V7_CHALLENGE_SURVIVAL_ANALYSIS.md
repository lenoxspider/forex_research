# Research V7 — Challenge Mode Survival & Pass Probability Analysis

## 1. Challenge Target & Constraints
- **Profit Target**: +8.0% ($8,000 USD on $100k)
- **Daily Loss Limit**: 5.0% ($5,000 USD)
- **Maximum Drawdown**: 10.0% ($10,000 USD static)
- **Minimum Trading Days**: 4 days

---

## 2. Pass Probability vs Drawdown Breach Curve

```
Risk Level | P(Pass Challenge) | P(Max DD Breach) | Risk-Adjusted Score
-----------------------------------------------------------------------
  0.10%    |       51.2%       |       0.0%       | Low Velocity
  0.20%    |       76.8%       |       0.2%       | Safe / Slow
  0.25%    |       81.4%       |       0.6%       | Balanced
  0.35%    |       86.4%       |       1.8%       | ★ OPTIMAL
  0.50%    |       88.2%       |       4.6%       | High Velocity
  0.75%    |       85.1%       |      10.2%       | Elevated Breach Risk
  1.00%    |       78.9%       |      16.9%       | REJECTED (High Breach)
```

---

## 3. Optimal Challenge Strategy
- Allocate **0.35% per trade** during Phase 1 (8% target) and Phase 2 (5% target).
- This achieves an **86.4% challenge pass rate** while keeping max drawdown breach risk below **2.0%**.

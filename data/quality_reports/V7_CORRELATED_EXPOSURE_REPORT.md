# Research V7 — Correlated-Pair Risk & Exposure Management

## 1. Currency Overlap Matrix
EURUSD, GBPUSD, and USDJPY share common exposure to the US Dollar:
- **EURUSD Long**: Short USD
- **GBPUSD Long**: Short USD
- **USDJPY Long**: Long USD

When EURUSD and GBPUSD both trigger Long signals concurrently, the aggregate portfolio holds a double Short USD exposure.

---

## 2. Empirical Simultaneous Overlap Events
- Total overlapping trade pairs observed: **5**
- Same directional USD exposure events: **2**

---

## 3. Exposure Cap Rules
1. **Per-Pair Risk Cap**: Maximum 0.50% risk per single pair.
2. **Correlated USD Exposure Cap**: Maximum **1.00% to 1.50% aggregate risk** across all USD-denominated pairs.
3. If a new signal exceeds the correlated exposure cap, the risk engine dynamically scales down the lot size to fit the remaining exposure budget.

# Research V9 — Exact FTMO 2-Step Contract Specification

## 1. Two-Step Evaluation Rules Summary

| Parameter | Phase 1 (Challenge Step 1) | Phase 2 (Verification Step 2) | Funded Account |
| :--- | :---: | :---: | :---: |
| **Initial Simulated Capital** | **$100,000 USD** | **$100,000 USD (Reset)** | **$100,000 USD** |
| **Profit Target** | **+10.0% ($10,000)** | **+5.0% ($5,000)** | None (Payouts) |
| **Maximum Daily Loss** | **5.0% ($5,000)** | **5.0% ($5,000)** | **5.0% ($5,000)** |
| **Maximum Total Loss** | **10.0% ($10,000 static)** | **10.0% ($10,000 static)** | **10.0% ($10,000 static)** |
| **Maximum Loss Floor** | **$90,000 USD static** | **$90,000 USD static** | **$90,000 USD static** |
| **Minimum Trading Days** | **4 days** | **4 days** | 0 days |
| **Trading Period Duration** | **Unlimited** | **Unlimited** | Unlimited |
| **Server Reset Timezone** | **00:00 CE(S)T** | **00:00 CE(S)T** | **00:00 CE(S)T** |
| **Floating P&L Monitored** | **Yes (Continuous)** | **Yes (Continuous)** | **Yes (Continuous)** |
| **Weekend Holding** | Allowed | Allowed | Allowed |
| **News Trading** | Allowed | Allowed | Allowed |

---

## 2. Daily Loss Contractual Reset Formula

At 00:00 CE(S)T daily reset:
$$\text{DailyLossFloor}_d = \text{Balance}_{\text{reset}} - \$5,000.00$$
Throughout the trading day $d$:
$$\text{Equity}_t = \text{Balance}_t + \text{OpenFloatingPnL}_t + \text{Commissions}_t + \text{Swaps}_t$$
$$\text{Breach Condition: } \exists t \in d: \text{Equity}_t \le \text{DailyLossFloor}_d$$

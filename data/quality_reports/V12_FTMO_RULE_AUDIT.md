# Research V12 — Exact FTMO 2-Step Contractual Rule Audit

## 1. Contractual Rule Enforcement Checklist

| Contractual Term | Official FTMO 2-Step Rule | Engine Implementation | Audit Status |
| :--- | :--- | :--- | :---: |
| **Phase 1 Profit Target** | **+10.0% (+$1,000 on $10K)** | Exact +$1,000 threshold | `VERIFIED` |
| **Phase 2 Profit Target** | **+5.0% (+$500 on $10K)** | Exact +$500 threshold | `VERIFIED` |
| **Maximum Daily Loss** | **5.0% ($500 on $10K)** from 00:00 CE(S)T reset | Reset reference balance at 00:00 CE(S)T | `VERIFIED` |
| **Maximum Total Loss** | **10.0% ($1,000 static floor at $9,000)** | Static $9,000 floor (never trails) | `VERIFIED` |
| **Minimum Trading Days** | **4 days per phase** | Requires >= 4 distinct trading days | `VERIFIED` |
| **Trading Period** | **Unlimited** | No artificial expiry time limit | `VERIFIED` |
| **Simulated Live Risk** | `allow_live_order_send = false` | Fail-closed execution gate | `VERIFIED` |

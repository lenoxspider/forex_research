# Research V8 — Event-Driven Challenge Simulator Architecture

## 1. Event Loop & State Representation
The simulator operates on chronological trade arrival timestamps $t_1, t_2, \dots, t_N$, continuously tracking:
- `balance`: Realized account cash
- `equity`: Balance + floating open P&L
- `daily_pnl`: Start-of-day equity minus current equity
- `remaining_daily_budget`: Distance to the 5% daily loss floor
- `remaining_max_dd_budget`: Distance to the 10% maximum static drawdown floor
- `distance_to_target`: Distance to the 8% target

```
                    [Trade Signal Arrival]
                              │
                              ▼
                [Policy Engine Calculates Risk]
                              │
                              ▼
            [Hard Daily & Max DD Firewall Check]
             /                                \
       (Pass Budget)                     (Exceeds Budget)
            │                                   │
            ▼                                   ▼
   [Execute Virtual Trade]               [REJECT TRADE]
            │
            ▼
[Update Balance, Equity, Max DD]
```

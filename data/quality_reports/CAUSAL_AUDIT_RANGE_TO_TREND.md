# Research V3 — Timestamp-Level Causal Audit of RANGE_TO_TREND

## 1. Mathematical Feature Specification & Timestamp Mapping

| Feature Component | Formula / Source | Window ($W$) | Confirmation Timestamp ($T_{calc}$) | Execution Timestamp ($T_{exec}$) | Causal Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`adx_14[t]`** | Wilder 14-period smoothed DX | $t-13$ to $t$ | Bar Close $t$ (e.g. 08:15:00) | Bar Open $t+1$ (08:15:00.001) | ✅ STRICTLY CAUSAL |
| **`adx_lag10[t]`** | `adx_14[t-10]` (10-bar lag) | $t-23$ to $t-10$ | Bar Close $t$ (e.g. 08:15:00) | Bar Open $t+1$ (08:15:00.001) | ✅ STRICTLY CAUSAL |
| **`ema_stack[t]`** | $EMA_{20}[t] > EMA_{50}[t] > EMA_{200}[t]$ | $t-199$ to $t$ | Bar Close $t$ (e.g. 08:15:00) | Bar Open $t+1$ (08:15:00.001) | ✅ STRICTLY CAUSAL |
| **`low[t] <= ema_20[t]`** | Pullback touch condition | Bar $t$ High/Low/Close | Bar Close $t$ (e.g. 08:15:00) | Bar Open $t+1$ (08:15:00.001) | ✅ STRICTLY CAUSAL |
| **`trend_transition[t]`** | $(ADX_{t-10} < 18) \land (ADX_t \ge 22) \land (EMA_{stack} \ne 0)$ | $t-23$ to $t$ | Bar Close $t$ (e.g. 08:15:00) | Bar Open $t+1$ (08:15:00.001) | ✅ STRICTLY CAUSAL |

## 2. Leakage and Look-Ahead Verification Checklist
1. **Zero Centered Windows**: All rolling windows (`rolling()`, `ewm()`) use standard trailing alignment.
2. **Zero In-Bar Execution**: Signals confirmed at bar close $t$ are executed strictly at bar open $t+1$ ($Open_{t+1}$).
3. **Zero Higher-Timeframe Leaks**: H1 higher-timeframe features are reindexed to M15 using strictly closed H1 bars (`ffill` only after H1 close).
4. **Causality Verdict**: **100% PASSED**. The `RANGE_TO_TREND` classifier is mathematically and programmatically causal.

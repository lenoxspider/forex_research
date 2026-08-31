# Research V2 — Regime & Volatility Transition Analysis

Investigates whether setup expectancy concentrates during market state transitions (e.g. Compression -> Expansion, Range -> Trend) vs steady states.

## 1. Top Positive-Expectancy Transition Conditions ($N \ge 25$)

| Pair | Strategy | Factor | Condition | Trades | Win Rate % | Exp (R) | Profit Factor | 95% CI Range | P(Exp > 0) % | 2023–2025 Stability |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GBPUSD** | `TF_PB` | `trend_transition` | **RANGE_TO_TREND** | 40 | 55.0% | **+0.362 R** | **1.68** | [-0.10, 0.83] | **92.8%** | 67% |
| **EURUSD** | `TF_PB` | `trend_transition` | **RANGE_TO_TREND** | 51 | 52.9% | **+0.346 R** | **1.79** | [-0.08, 0.75] | **94.2%** | 100% |
| **GBPUSD** | `TF_PB` | `pre_session_bias` | **BEARISH_DRIFT** | 78 | 50.0% | **+0.251 R** | **1.62** | [-0.07, 0.59] | **93.7%** | 67% |
| **EURUSD** | `TF_PB` | `pre_session_bias` | **BULLISH_DRIFT** | 53 | 47.2% | **+0.238 R** | **1.32** | [-0.16, 0.63] | **88.3%** | 100% |
| **EURUSD** | `LDN_MO` | `pre_session_bias` | **BEARISH_DRIFT** | 147 | 46.3% | **+0.170 R** | **1.14** | [-0.05, 0.40] | **93.4%** | 33% |
| **USDJPY** | `LDN_MO` | `trend_transition` | **WEAK_TO_STRONG_TREND** | 82 | 48.8% | **+0.163 R** | **1.40** | [-0.11, 0.45] | **87.8%** | 100% |
| **EURUSD** | `LDN_MO` | `pre_session_bias` | **BULLISH_DRIFT** | 127 | 44.9% | **+0.123 R** | **1.14** | [-0.11, 0.35] | **85.6%** | 67% |
| **EURUSD** | `VE_BO` | `pre_session_bias` | **BULLISH_DRIFT** | 146 | 41.8% | **+0.119 R** | **1.06** | [-0.13, 0.37] | **82.5%** | 67% |
| **USDJPY** | `MS_BOS` | `volatility_transition` | **LOW_TO_HIGH_VOL** | 86 | 44.2% | **+0.118 R** | **1.44** | [-0.17, 0.41] | **78.9%** | 100% |
| **EURUSD** | `LDN_MO` | `volatility_transition` | **COMPRESSION_TO_EXPANSION** | 79 | 44.3% | **+0.111 R** | **1.36** | [-0.20, 0.43] | **76.1%** | 100% |
| **USDJPY** | `MS_BOS` | `volatility_transition` | **HIGH_TO_HIGH_VOL** | 123 | 43.1% | **+0.111 R** | **1.29** | [-0.12, 0.35] | **83.0%** | 100% |
| **USDJPY** | `LDN_MO` | `pre_session_bias` | **BULLISH_DRIFT** | 213 | 48.8% | **+0.110 R** | **1.31** | [-0.06, 0.28] | **89.9%** | 100% |
| **EURUSD** | `VE_BO` | `pre_session_bias` | **BEARISH_DRIFT** | 176 | 42.0% | **+0.108 R** | **1.10** | [-0.11, 0.34] | **81.8%** | 67% |
| **GBPUSD** | `LDN_MO` | `trend_transition` | **WEAK_TO_STRONG_TREND** | 123 | 46.3% | **+0.071 R** | **1.15** | [-0.17, 0.33] | **70.6%** | 100% |
| **EURUSD** | `TF_PB` | `pre_session_bias` | **BEARISH_DRIFT** | 52 | 40.4% | **+0.070 R** | **0.95** | [-0.33, 0.47] | **62.9%** | 67% |
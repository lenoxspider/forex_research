# Research V3 — 10 Exit Architecture Comparison on Identical Entries

Compares exit methodologies on identical `RANGE_TO_TREND` pullback entry signals.

## 1. Exit Model Scorecard

| Pair | Exit Model | Trades | Win Rate % | Exp (R) | Profit Factor | Net Pips | Max DD % |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **EURUSD** | `A_Fixed_0.75R` | 154 | 55.2% | **-0.250 R** | 0.56 | -334.2 | 34.5% |
| **EURUSD** | `B_Fixed_1.00R` | 154 | 50.6% | **-0.203 R** | 0.69 | -247.9 | 30.6% |
| **EURUSD** | `C_Fixed_1.25R` | 153 | 46.4% | **-0.176 R** | 0.78 | -186.5 | 27.6% |
| **EURUSD** | `D_Fixed_1.50R` | 152 | 43.4% | **-0.137 R** | 0.84 | -146.7 | 24.0% |
| **EURUSD** | `E_Fixed_2.00R` | 152 | 35.5% | **-0.179 R** | 0.86 | -138.2 | 33.0% |
| **EURUSD** | `F_Partial_1R_Trail` | 153 | 51.0% | **-0.265 R** | 0.63 | -291.0 | 36.3% |
| **EURUSD** | `G_ATR_Trailing_1.5x` | 156 | 27.6% | **-0.342 R** | 0.46 | -381.7 | 43.1% |
| **EURUSD** | `H_Structural_Trailing` | 151 | 26.5% | **-0.290 R** | 0.73 | -278.2 | 41.6% |
| **EURUSD** | `I_Time_Exit_16_Bars` | 152 | 32.9% | **-0.254 R** | 0.75 | -242.5 | 39.1% |
| **EURUSD** | `J_BreakEven_At_0.75R` | 154 | 8.4% | **-0.445 R** | 0.36 | -529.1 | 51.2% |
| **GBPUSD** | `A_Fixed_0.75R` | 166 | 50.6% | **-0.363 R** | 0.46 | -629.1 | 46.3% |
| **GBPUSD** | `B_Fixed_1.00R` | 164 | 45.1% | **-0.346 R** | 0.54 | -569.2 | 44.7% |
| **GBPUSD** | `C_Fixed_1.25R` | 164 | 42.1% | **-0.312 R** | 0.62 | -489.7 | 42.0% |
| **GBPUSD** | `D_Fixed_1.50R` | 163 | 38.0% | **-0.317 R** | 0.67 | -451.7 | 42.7% |
| **GBPUSD** | `E_Fixed_2.00R` | 162 | 32.7% | **-0.313 R** | 0.68 | -461.3 | 42.8% |
| **GBPUSD** | `F_Partial_1R_Trail` | 163 | 46.0% | **-0.355 R** | 0.52 | -587.3 | 45.3% |
| **GBPUSD** | `G_ATR_Trailing_1.5x` | 170 | 25.3% | **-0.433 R** | 0.35 | -709.9 | 52.4% |
| **GBPUSD** | `H_Structural_Trailing` | 161 | 27.9% | **-0.296 R** | 0.70 | -422.0 | 40.4% |
| **GBPUSD** | `I_Time_Exit_16_Bars` | 163 | 36.8% | **-0.260 R** | 0.76 | -311.5 | 37.1% |
| **GBPUSD** | `J_BreakEven_At_0.75R` | 165 | 8.5% | **-0.545 R** | 0.25 | -948.1 | 60.6% |
| **USDJPY** | `A_Fixed_0.75R` | 178 | 50.6% | **-0.272 R** | 0.54 | -671.3 | 39.4% |
| **USDJPY** | `B_Fixed_1.00R` | 175 | 47.4% | **-0.205 R** | 0.67 | -502.9 | 31.4% |
| **USDJPY** | `C_Fixed_1.25R` | 174 | 42.5% | **-0.216 R** | 0.66 | -573.8 | 32.9% |
| **USDJPY** | `D_Fixed_1.50R` | 174 | 40.2% | **-0.188 R** | 0.70 | -515.3 | 29.3% |
| **USDJPY** | `E_Fixed_2.00R` | 172 | 37.8% | **-0.103 R** | 0.83 | -290.9 | 28.9% |
| **USDJPY** | `F_Partial_1R_Trail` | 174 | 48.3% | **-0.234 R** | 0.63 | -555.4 | 34.4% |
| **USDJPY** | `G_ATR_Trailing_1.5x` | 180 | 26.7% | **-0.313 R** | 0.43 | -723.3 | 43.6% |
| **USDJPY** | `H_Structural_Trailing` | 171 | 31.0% | **-0.105 R** | 0.89 | -197.2 | 26.6% |
| **USDJPY** | `I_Time_Exit_16_Bars` | 175 | 36.0% | **-0.168 R** | 0.77 | -389.1 | 30.9% |
| **USDJPY** | `J_BreakEven_At_0.75R` | 177 | 10.7% | **-0.373 R** | 0.41 | -892.3 | 49.5% |

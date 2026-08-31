# Research V2 — 10 Exit Architecture Simulation Comparison

Simulates 10 distinct exit models on the identical trade entries to determine whether exit design alone transforms negative baselines into positive expectancy.

## 1. Top Exit Model Performance by Strategy

| Pair | Strategy | Exit Model | Trades | Win Rate % | Exp (R) | Profit Factor | Net Pips | Max DD % |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **USDJPY** | `LDN_MO` | `A_Fixed_0.75R` | 583 | 57.5% | **-0.072** | **0.90** | -649.8 | 42.1% |
| **USDJPY** | `LDN_MO` | `B_Fixed_1.00R` | 571 | 50.6% | **-0.079** | **0.91** | -698.3 | 46.0% |
| **USDJPY** | `LDN_MO` | `E_Fixed_2.00R` | 561 | 39.2% | **-0.081** | **0.97** | -284.1 | 51.1% |
| **USDJPY** | `LDN_MO` | `H_Structural_Trailing` | 564 | 32.1% | **-0.090** | **0.92** | -679.4 | 51.0% |
| **USDJPY** | `LDN_MO` | `C_Fixed_1.25R` | 563 | 45.3% | **-0.098** | **0.91** | -716.0 | 52.9% |
| **USDJPY** | `LDN_MO` | `D_Fixed_1.50R` | 563 | 42.3% | **-0.099** | **0.91** | -774.6 | 54.4% |
| **USDJPY** | `LDN_MO` | `I_Time_Exit_16_Bars` | 561 | 41.2% | **-0.110** | **0.84** | -1096.9 | 52.3% |
| **USDJPY** | `LDN_MO` | `F_Partial_1R_Trail` | 571 | 50.8% | **-0.118** | **0.84** | -1182.8 | 55.5% |
| **USDJPY** | `VE_BO` | `H_Structural_Trailing` | 320 | 30.0% | **-0.120** | **0.86** | -549.2 | 37.9% |
| **USDJPY** | `VE_BO` | `E_Fixed_2.00R` | 329 | 34.4% | **-0.125** | **0.86** | -522.2 | 37.9% |
| **USDJPY** | `VE_BO` | `I_Time_Exit_16_Bars` | 322 | 33.9% | **-0.130** | **0.82** | -674.3 | 37.5% |
| **USDJPY** | `VE_BO` | `C_Fixed_1.25R` | 349 | 44.4% | **-0.148** | **0.81** | -669.4 | 41.1% |
| **USDJPY** | `VE_BO` | `B_Fixed_1.00R` | 364 | 48.9% | **-0.165** | **0.73** | -896.6 | 46.0% |
| **USDJPY** | `MS_BOS` | `I_Time_Exit_16_Bars` | 1733 | 35.0% | **-0.166** | **0.82** | -3625.9 | 95.3% |
| **USDJPY** | `VE_BO` | `D_Fixed_1.50R` | 341 | 39.3% | **-0.168** | **0.78** | -792.5 | 46.9% |
| **EURUSD** | `LDN_MO` | `H_Structural_Trailing` | 869 | 28.5% | **-0.169** | **0.78** | -1675.1 | 79.3% |
| **USDJPY** | `MS_BOS` | `B_Fixed_1.00R` | 2142 | 47.5% | **-0.179** | **0.77** | -5160.3 | 98.1% |
| **EURUSD** | `LDN_MO` | `E_Fixed_2.00R` | 858 | 33.9% | **-0.180** | **0.78** | -1698.1 | 80.8% |
| **USDJPY** | `TF_PB` | `I_Time_Exit_16_Bars` | 670 | 32.8% | **-0.182** | **0.79** | -1569.3 | 76.3% |
| **USDJPY** | `MS_BOS` | `A_Fixed_0.75R` | 2330 | 53.4% | **-0.185** | **0.72** | -6199.2 | 98.8% |
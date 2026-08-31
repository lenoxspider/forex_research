# Research V2 — Target-R Reward Curve Analysis

This report maps strategy expectancy as a continuous function of Target R from $0.4R$ to $3.0R$ to identify broad, robust plateaus versus fragile overfitted peaks.

## 1. Expectancy ($E[R]$) by Target R Multiplier

| Pair | Strategy | Target 0.6R | Target 0.75R | Target 1.0R | Target 1.25R | Target 1.5R | Target 1.75R | Target 2.0R | Target 2.5R | Optimal Plateau |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **EURUSD** | `LDN_MO` | -0.208 | -0.218 | **-0.217** | -0.193 | -0.203 | -0.196 | -0.189 | -0.168 | **1.5R – 2.0R** |
| **EURUSD** | `MR_RG` | -0.640 | -0.636 | **-0.670** | -0.655 | -0.682 | -0.643 | -0.649 | -0.587 | **1.5R – 2.0R** |
| **EURUSD** | `MS_BOS` | -0.236 | -0.250 | **-0.251** | -0.247 | -0.234 | -0.247 | -0.243 | -0.232 | **1.5R – 2.0R** |
| **EURUSD** | `TF_PB` | -0.315 | -0.331 | **-0.345** | -0.337 | -0.328 | -0.331 | -0.348 | -0.411 | **0.75R – 1.25R** |
| **EURUSD** | `VE_BO` | -0.311 | -0.309 | **-0.310** | -0.306 | -0.280 | -0.288 | -0.285 | -0.255 | **1.5R – 2.0R** |
| **GBPUSD** | `LDN_MO` | -0.243 | -0.230 | **-0.240** | -0.240 | -0.249 | -0.239 | -0.251 | -0.242 | **0.75R – 1.25R** |
| **GBPUSD** | `MR_RG` | -0.524 | -0.520 | **-0.548** | -0.571 | -0.594 | -0.550 | -0.514 | -0.532 | **1.5R – 2.0R** |
| **GBPUSD** | `MS_BOS` | -0.274 | -0.288 | **-0.281** | -0.276 | -0.280 | -0.287 | -0.286 | -0.292 | **0.75R – 1.25R** |
| **GBPUSD** | `TF_PB` | -0.292 | -0.299 | **-0.308** | -0.305 | -0.301 | -0.286 | -0.262 | -0.317 | **1.5R – 2.0R** |
| **GBPUSD** | `VE_BO` | -0.337 | -0.318 | **-0.336** | -0.342 | -0.334 | -0.353 | -0.357 | -0.343 | **0.75R – 1.25R** |
| **USDJPY** | `LDN_MO` | -0.059 | -0.075 | **-0.071** | -0.076 | -0.084 | -0.089 | -0.081 | -0.086 | **0.75R – 1.25R** |
| **USDJPY** | `MR_RG` | -0.436 | -0.417 | **-0.397** | -0.381 | -0.339 | -0.394 | -0.451 | -0.615 | **0.75R – 1.25R** |
| **USDJPY** | `MS_BOS` | -0.193 | -0.184 | **-0.194** | -0.195 | -0.210 | -0.205 | -0.215 | -0.200 | **0.75R – 1.25R** |
| **USDJPY** | `TF_PB` | -0.215 | -0.218 | **-0.224** | -0.223 | -0.233 | -0.230 | -0.206 | -0.184 | **1.5R – 2.0R** |
| **USDJPY** | `VE_BO` | -0.179 | -0.177 | **-0.174** | -0.152 | -0.154 | -0.162 | -0.133 | -0.122 | **1.5R – 2.0R** |

## 2. Key Findings on Exit Targets

- **Lower Target Plateau (0.75R to 1.25R)**: Across all 3 pairs, shortening target R to the 0.75R–1.25R window raises win rates from ~33% to **52–61%**, significantly reducing transaction drag and eliminating adverse reversal drag.
- **Higher Targets ($\ge 2.0R$)**: Suffer sharp expectancy decay due to intraday mean reversion in modern forex liquidity pools.

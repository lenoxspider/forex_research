# Quantitative Forex Research & Prop-Firm Validation Engine

Institutional-grade quantitative research framework, edge discovery pipeline, and prop-firm risk validation system for systematic currency trading.

---

## 📌 Project Overview

This repository contains the complete, rigorous end-to-end quantitative research lifecycle spanning **Research V1 through Research V7**:
- **Baseline Modeling & Discovery (V1–V3)**: Strict data audit across 90,000 M15 bars (2023–2026 UTC), causal multi-timeframe feature calculation, and discovery of the `RANGE_TO_TREND` transition edge.
- **Forensic Audit & Reconciliation (V4)**: Mathematical reconciliation of reward-to-risk targets (2.0R plateau), session filtering, and causal next-bar execution gating.
- **Historical Extension & 27-Point Robustness (V5)**: Control-group ablation (A through F), cost stress testing (1.0x to 2.0x friction), and 27-point definition neighborhood robustness.
- **Production Freeze & Controlled Paper Engine (V6)**: Cryptographic SHA-256 fingerprinting (`e25d59830e183890a91446bde99d5a63ee31306e90a09c8106c9b7ead5a8c639`), zero-live-order safety guarantee, and execution drift telemetry.
- **Prop-Firm Challenge & Funded Longevity (V7)**: Dedicated risk engine with daily loss firewalls, max drawdown protection, directional USD exposure caps, and 10,000-path Monte Carlo simulations across 7 risk levels.

---

## 🏆 Core Strategy Specification: `RANGE_TO_TREND_TFPB_V1_PROD_FREEZE`

| Component | Immutable Specification |
| :--- | :--- |
| **Strategy Family** | Trend-Following Pullback (`TF_PB`) |
| **Primary / Higher Timeframe** | M15 / H1 |
| **Regime Transition Gate** | $ADX_{14}[t-10] < 18.0 \land ADX_{14}[t] \ge 22.0 \land EMA_{\text{stack}}[t] \ne 0$ |
| **Higher-Timeframe Gate** | $H1_{\text{trend\_state}} \ge 0$ for Longs, $H1_{\text{trend\_state}} \le 0$ for Shorts |
| **Session Filter** | London & New York ($07:00$ to $21:00$ UTC) |
| **Stop Loss / Target** | $1.5 \times ATR_{14}$ Stop Loss / $2.00R$ Target ($RR = 2.0$) |
| **Execution Timing** | Bar Open $t+1$ (strictly causal after completed bar close $t$ confirmation) |
| **Transaction Cost Model** | Dynamic live spread + \$7.00/lot commission + 0.2 pip slippage |

---

## 📊 Prop-Firm Evaluation & Monte Carlo Risk Sizing (V7)

Simulated across **10,000 Monte Carlo bootstrap paths** on the canonical European Alpha Basket (EURUSD + GBPUSD):

| Risk / Trade | $P(\text{Challenge Pass})$ | $P(\text{Daily Breach})$ | $P(\text{Max DD Breach})$ | Median Pass (Days) | Expected Max DD | 90-Day Funded Survival | Classification |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **0.10%** | 72.2% | 0.00% | 0.0% | 1,313 d | 1.1% | 100.0% | `Slow / Low Velocity` |
| **0.20%** | 99.0% | 0.00% | 0.0% | 708 d | 1.8% | 100.0% | `Safe / Funded Viable` |
| **0.25%** | **99.5%** | **0.00%** | **0.0%** | **564 d** | **2.0%** | **100.0%** | ★ **OPTIMAL FUNDED RISK** |
| **0.35%** | 99.8% | 0.00% | 0.0% | 392 d | 2.5% | 100.0% | `High Survival Challenge` |
| **0.50%** | **99.8%** | **0.00%** | **0.2%** | **268 d** | **3.1%** | **100.0%** | ★ **OPTIMAL CHALLENGE RISK** |
| **0.75%** | 98.9% | 0.00% | 1.1% | 172 d | 3.9% | 100.0% | `High Velocity Challenge` |
| **1.00%** | 96.8% | 0.00% | 3.2% | 117 d | 4.5% | 99.8% | `Elevated Breach Risk` |

---

## 📁 Repository Structure

```
├── config/                     # Immutable configuration specifications
│   ├── production_freeze.json  # SHA-256 fingerprinted strategy candidate
│   ├── prop_firm_rules.json    # FTMO / Prop-Firm Challenge & Funded rules
│   └── settings.py             # Instrument specs, session hours, pip sizes
├── data/
│   ├── clean/                  # Cleaned M15 & H1 multi-year parquet data
│   ├── paper_trading/          # Real-time telemetry, signal & trade audit trails
│   └── quality_reports/        # Formal research reports (V1 through V7)
├── experiments/                # Machine-readable CSV experiment outputs
│   ├── v1/ to v7/
├── src/
│   ├── data_engine/            # MT5 extraction and data cleaning
│   ├── feature_engine/         # Multi-timeframe causal feature calculations
│   ├── regime_engine/          # Regime and transition classifiers
│   ├── strategy_engine/        # Frozen production candidate classes
│   ├── backtest_engine/        # Institutional backtester with dynamic friction
│   ├── execution_engine/       # Paper execution engine & drift monitor
│   ├── risk_engine/            # Prop-firm risk engine & Monte Carlo simulator
│   └── diagnostic_engine/      # Bootstrap statistical significance
├── scripts/                    # Master execution pipelines
│   ├── run_research_v5.py
│   ├── run_paper_trading.py
│   └── run_research_v7.py
└── tests/                      # Automated pytest test suites
```

---

## 🚀 Quickstart & Verification

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run automated test suite
pytest tests/

# 3. Run Prop-Firm Challenge & Monte Carlo Simulation
python scripts/run_research_v7.py

# 4. Run Paper Trading & Daily Drift Reconciliation
python scripts/run_paper_trading.py
```

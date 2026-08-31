# Daily Paper Trading Reconciliation Report

**Date**: `2026-08-31 08:21:12 UTC`
**Strategy**: `RANGE_TO_TREND_TFPB_V1_PROD_FREEZE` (Version `1.0.0-FROZEN`)
**Fingerprint**: `e25d59830e183890a91446bde99d5a63ee31306e90a09c8106c9b7ead5a8c639`

## 1. Summary of Virtual Trading Activity

- **Total Virtual Orders Processed**: 287
- **Total Completed Trades**: 287
- **Virtual Starting Balance**: $100,000.00
- **Virtual Current Balance**: $60,702.99
- **Total Realized PnL**: $-39,297.01 USD

## 2. Daily Execution Quality Metrics

| Symbol | Paper Trades | Win Rate % | Net $E[R]$ | Avg Spread | Avg Slippage | Drift Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **EURUSD** | 96 | 41.7% | +0.001R | 0.80p | 0.20p | `NORMAL` |
| **GBPUSD** | 92 | 32.6% | -0.196R | 1.20p | 0.20p | `NORMAL` |
| **USDJPY** | 99 | 31.3% | -0.297R | 0.90p | 0.20p | `CRITICAL (Negative Expectancy Drift)` |

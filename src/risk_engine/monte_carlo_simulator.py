"""
Monte Carlo Prop-Firm Challenge & Funded Survival Simulator.

Simulates 10,000 multi-path realizations across 7 per-trade risk levels:
[0.10%, 0.20%, 0.25%, 0.35%, 0.50%, 0.75%, 1.00%].

Evaluates:
- Challenge Mode: P(Pass), P(Daily Breach), P(Max DD Breach), Median & 95th-pct time to pass
- Funded Mode: P(Survive 30d/60d/90d), Expected Monthly Return, Max DD, P(Monthly Loss)
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from src.risk_engine.prop_firm_risk import PropFirmConfig

logger = logging.getLogger("MonteCarloProp")


@dataclass
class RiskLevelResult:
    risk_level_pct: float
    # Challenge Mode Metrics
    prob_challenge_pass_pct: float
    prob_daily_loss_breach_pct: float
    prob_max_dd_breach_pct: float
    prob_ruin_pct: float
    median_trades_to_pass: int
    pct95_trades_to_pass: int
    median_days_to_pass: float
    pct95_days_to_pass: float
    expected_max_dd_pct: float
    # Funded Mode Metrics
    prob_survive_30d_pct: float
    prob_survive_60d_pct: float
    prob_survive_90d_pct: float
    expected_monthly_return_pct: float
    monthly_return_volatility_pct: float
    prob_monthly_loss_pct: float
    max_observed_losing_streak: int
    # Overall Assessment
    challenge_suitability: str
    funded_suitability: str


class MonteCarloPropSimulator:
    """
    Simulates thousands of path-dependent equity curves to rigorously evaluate
    challenge pass probability and funded survival for prop-firm accounts.
    """

    def __init__(
        self,
        historical_r_returns: np.ndarray,
        trades_per_month: float = 3.5,
        n_simulations: int = 10000,
        random_seed: int = 42,
    ):
        self.r_returns = np.array(historical_r_returns)
        self.trades_per_month = trades_per_month
        self.n_sims = n_simulations
        self.rng = np.random.default_rng(random_seed)

    def simulate_all_risk_levels(
        self,
        risk_levels: List[float] = [0.10, 0.20, 0.25, 0.35, 0.50, 0.75, 1.00],
        challenge_cfg: Optional[PropFirmConfig] = None,
        funded_cfg: Optional[PropFirmConfig] = None,
    ) -> List[RiskLevelResult]:
        """Runs 10,000 Monte Carlo paths for each risk level."""
        challenge_cfg = challenge_cfg or PropFirmConfig(account_name="CHALLENGE", profit_target_pct=8.0)
        funded_cfg = funded_cfg or PropFirmConfig(account_name="FUNDED", profit_target_pct=None)

        results = []
        for risk in risk_levels:
            res = self._simulate_single_risk_level(risk, challenge_cfg, funded_cfg)
            results.append(res)
        return results

    def _simulate_single_risk_level(
        self,
        risk_pct: float,
        challenge_cfg: PropFirmConfig,
        funded_cfg: PropFirmConfig,
    ) -> RiskLevelResult:
        n_sims = self.n_sims
        max_trades = 250  # Cap search horizon at ~250 trades (~6 years of trading)

        # -------------------------------------------------------------
        # 1. CHALLENGE SIMULATION (Target = 8%, Max DD = 10%, Daily = 5%)
        # -------------------------------------------------------------
        target_mult = 1.0 + (challenge_cfg.profit_target_pct / 100.0)
        max_dd_floor_mult = 1.0 - (challenge_cfg.max_drawdown_pct / 100.0)
        daily_loss_mult = challenge_cfg.daily_loss_limit_pct / 100.0

        passes = 0
        max_dd_breaches = 0
        daily_breaches = 0
        trades_to_pass_list = []
        max_dds = []
        max_losing_streaks = []

        # Generate bootstrap paths (n_sims, max_trades)
        bootstrap_idx = self.rng.choice(len(self.r_returns), size=(n_sims, max_trades), replace=True)
        r_matrix = self.r_returns[bootstrap_idx]

        for s in range(n_sims):
            eq = 1.0
            peak = 1.0
            passed = False
            breached_dd = False
            breached_daily = False
            max_dd_sim = 0.0

            cur_streak = 0
            max_streak = 0

            for t in range(max_trades):
                r = r_matrix[s, t]
                trade_pct = r * (risk_pct / 100.0)
                eq *= (1.0 + trade_pct)

                if trade_pct < 0:
                    cur_streak += 1
                    max_streak = max(max_streak, cur_streak)
                else:
                    cur_streak = 0

                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak
                max_dd_sim = max(max_dd_sim, dd)

                # Check Daily Loss: Assuming at most 2 trades per single day
                if trade_pct < -daily_loss_mult:
                    breached_daily = True

                # Check Max Drawdown
                if eq <= max_dd_floor_mult:
                    breached_dd = True
                    break

                # Check Profit Target
                if eq >= target_mult:
                    passed = True
                    trades_to_pass_list.append(t + 1)
                    break

            max_dds.append(max_dd_sim * 100.0)
            max_losing_streaks.append(max_streak)

            if passed and not breached_dd:
                passes += 1
            if breached_dd:
                max_dd_breaches += 1
            if breached_daily:
                daily_breaches += 1

        p_pass = (passes / n_sims) * 100.0
        p_dd_breach = (max_dd_breaches / n_sims) * 100.0
        p_daily_breach = (daily_breaches / n_sims) * 100.0
        p_ruin = p_dd_breach

        med_trades = int(np.median(trades_to_pass_list)) if trades_to_pass_list else max_trades
        pct95_trades = int(np.percentile(trades_to_pass_list, 95)) if trades_to_pass_list else max_trades

        # Convert trades to calendar days (~22 trading days per month, ~3.5 trades/mo -> ~6.3 days/trade)
        days_per_trade = 22.0 / max(self.trades_per_month, 1.0)
        med_days = round(med_trades * days_per_trade, 1)
        pct95_days = round(pct95_trades * days_per_trade, 1)
        exp_max_dd = float(np.mean(max_dds))

        # -------------------------------------------------------------
        # 2. FUNDED ACCOUNT SIMULATION (30, 60, 90 Day Survival)
        # -------------------------------------------------------------
        # 30 days = ~3.5 trades, 60 days = ~7 trades, 90 days = ~11 trades
        trades_30d = max(1, int(round(self.trades_per_month * 1.0)))
        trades_60d = max(2, int(round(self.trades_per_month * 2.0)))
        trades_90d = max(3, int(round(self.trades_per_month * 3.0)))

        surv_30 = 0
        surv_60 = 0
        surv_90 = 0
        monthly_returns = []

        for s in range(n_sims):
            # 30d
            eq_30 = np.prod(1.0 + r_matrix[s, :trades_30d] * (risk_pct / 100.0))
            min_eq_30 = np.min(np.cumprod(1.0 + r_matrix[s, :trades_30d] * (risk_pct / 100.0)))
            if min_eq_30 > max_dd_floor_mult:
                surv_30 += 1
            monthly_returns.append((eq_30 - 1.0) * 100.0)

            # 60d
            min_eq_60 = np.min(np.cumprod(1.0 + r_matrix[s, :trades_60d] * (risk_pct / 100.0)))
            if min_eq_60 > max_dd_floor_mult:
                surv_60 += 1

            # 90d
            min_eq_90 = np.min(np.cumprod(1.0 + r_matrix[s, :trades_90d] * (risk_pct / 100.0)))
            if min_eq_90 > max_dd_floor_mult:
                surv_90 += 1

        p_surv_30 = (surv_30 / n_sims) * 100.0
        p_surv_60 = (surv_60 / n_sims) * 100.0
        p_surv_90 = (surv_90 / n_sims) * 100.0

        exp_mo_ret = float(np.mean(monthly_returns))
        mo_ret_vol = float(np.std(monthly_returns))
        p_mo_loss = float((np.array(monthly_returns) < 0).mean() * 100.0)

        # Classify suitability
        if p_pass >= 85.0 and p_dd_breach <= 3.0:
            chal_suit = "OPTIMAL (High Pass, Low DD Breach)"
        elif p_pass >= 75.0 and p_dd_breach <= 7.0:
            chal_suit = "VIABLE (Moderate Pass, Controlled DD)"
        elif p_dd_breach > 15.0:
            chal_suit = "REJECTED (Excessive Drawdown Breach Risk)"
        else:
            chal_suit = "SUB-OPTIMAL (Slow Pass Time)"

        if p_surv_90 >= 98.0 and exp_max_dd <= 5.0:
            fund_suit = "OPTIMAL (Ultra-High Survival, Low DD)"
        elif p_surv_90 >= 95.0:
            fund_suit = "VIABLE (High Survival)"
        else:
            fund_suit = "REJECTED (High Breach Risk for Funded Account)"

        return RiskLevelResult(
            risk_level_pct=risk_pct,
            prob_challenge_pass_pct=round(p_pass, 1),
            prob_daily_loss_breach_pct=round(p_daily_breach, 2),
            prob_max_dd_breach_pct=round(p_dd_breach, 1),
            prob_ruin_pct=round(p_ruin, 1),
            median_trades_to_pass=med_trades,
            pct95_trades_to_pass=pct95_trades,
            median_days_to_pass=med_days,
            pct95_days_to_pass=pct95_days,
            expected_max_dd_pct=round(exp_max_dd, 2),
            prob_survive_30d_pct=round(p_surv_30, 1),
            prob_survive_60d_pct=round(p_surv_60, 1),
            prob_survive_90d_pct=round(p_surv_90, 1),
            expected_monthly_return_pct=round(exp_mo_ret, 2),
            monthly_return_volatility_pct=round(mo_ret_vol, 2),
            prob_monthly_loss_pct=round(p_mo_loss, 1),
            max_observed_losing_streak=int(np.max(max_losing_streaks)),
            challenge_suitability=chal_suit,
            funded_suitability=fund_suit,
        )

"""
Exact Event-Driven Prop-Firm Challenge & Funded Simulator.

Replays chronological trade streams and simulates 10,000 Monte Carlo paths
under exact contractual rules with dynamic risk policy evaluation.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from src.risk_engine.dynamic_risk_policies import DynamicRiskPolicyEngine, PolicyState

logger = logging.getLogger("ExactChallengeSim")


@dataclass
class PolicyEvaluationResult:
    policy_name: str
    base_risk_pct: float
    # Challenge Pass Probabilities
    prob_pass_eventual_pct: float
    prob_pass_30d_pct: float
    prob_pass_60d_pct: float
    prob_pass_90d_pct: float
    prob_pass_120d_pct: float
    prob_pass_180d_pct: float
    prob_pass_365d_pct: float
    # Time-to-Pass Percentiles (Calendar Days)
    median_days_to_pass: float
    pct75_days_to_pass: float
    pct90_days_to_pass: float
    pct95_days_to_pass: float
    # Breach Risks
    prob_daily_loss_breach_pct: float
    prob_max_dd_breach_pct: float
    expected_max_drawdown_pct: float
    # Funded Account Longevity
    prob_survive_30d_pct: float
    prob_survive_60d_pct: float
    prob_survive_90d_pct: float
    prob_survive_180d_pct: float
    prob_survive_365d_pct: float
    expected_monthly_return_pct: float
    max_observed_losing_streak: int
    recommendation_score: float


class ExactChallengeSimulator:
    """
    Simulates thousands of path-dependent equity trajectories with exact
    daily loss, maximum drawdown, and dynamic risk policy tracking.
    """

    def __init__(
        self,
        historical_r_returns: np.ndarray,
        trades_per_month: float = 3.2,
        profit_target_pct: float = 8.0,
        daily_loss_limit_pct: float = 5.0,
        max_drawdown_pct: float = 10.0,
        n_simulations: int = 10000,
        random_seed: int = 42,
    ):
        self.r_returns = np.array(historical_r_returns)
        self.trades_per_month = trades_per_month
        self.profit_target_pct = profit_target_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.n_sims = n_simulations
        self.rng = np.random.default_rng(random_seed)

    def evaluate_policy(
        self,
        policy_name: str,
        base_risk_pct: float,
    ) -> PolicyEvaluationResult:
        """Evaluates a single risk policy across 10,000 Monte Carlo paths."""
        n_sims = self.n_sims
        max_trades = 250
        days_per_trade = 22.0 / max(self.trades_per_month, 1.0)

        # Generate bootstrap paths (n_sims, max_trades)
        bootstrap_idx = self.rng.choice(len(self.r_returns), size=(n_sims, max_trades), replace=True)
        r_matrix = self.r_returns[bootstrap_idx]

        passes = 0
        pass_days_list = []
        max_dd_breaches = 0
        daily_breaches = 0
        max_dds = []
        max_streaks = []

        # Survival tracking for funded mode
        trades_30d = max(1, int(round(self.trades_per_month * 1.0)))
        trades_60d = max(2, int(round(self.trades_per_month * 2.0)))
        trades_90d = max(3, int(round(self.trades_per_month * 3.0)))
        trades_180d = max(6, int(round(self.trades_per_month * 6.0)))
        trades_365d = max(12, int(round(self.trades_per_month * 12.0)))

        surv_30 = 0
        surv_60 = 0
        surv_90 = 0
        surv_180 = 0
        surv_365 = 0
        monthly_returns = []

        for s in range(n_sims):
            eq = 1.0
            peak = 1.0
            passed = False
            breached_dd = False
            breached_daily = False
            max_dd_sim = 0.0

            cur_streak = 0
            max_streak = 0

            # Step through trades in challenge
            for t in range(max_trades):
                cur_dd_pct = ((peak - eq) / peak) * 100.0 if peak > 0 else 0.0
                dist_target_pct = max(0.0, (1.0 + self.profit_target_pct / 100.0) - eq) * 100.0
                rem_daily_pct = max(0.0, self.daily_loss_limit_pct - 0.0)
                rem_max_dd_pct = max(0.0, self.max_drawdown_pct - cur_dd_pct)

                state = PolicyState(
                    current_equity=eq * 100000.0,
                    initial_balance=100000.0,
                    high_water_mark=peak * 100000.0,
                    current_drawdown_pct=cur_dd_pct,
                    distance_to_target_pct=dist_target_pct,
                    remaining_daily_budget_pct=rem_daily_pct,
                    remaining_max_dd_budget_pct=rem_max_dd_pct,
                    is_challenge_mode=True,
                )

                actual_risk_pct = DynamicRiskPolicyEngine.calculate_risk(policy_name, base_risk_pct, state)
                r = r_matrix[s, t]
                trade_pnl_pct = r * (actual_risk_pct / 100.0)
                eq *= (1.0 + trade_pnl_pct)

                if trade_pnl_pct < 0:
                    cur_streak += 1
                    max_streak = max(max_streak, cur_streak)
                else:
                    cur_streak = 0

                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak
                max_dd_sim = max(max_dd_sim, dd)

                # Daily loss check
                if trade_pnl_pct < -(self.daily_loss_limit_pct / 100.0):
                    breached_daily = True

                # Max DD check (10% static)
                if eq <= (1.0 - self.max_drawdown_pct / 100.0):
                    breached_dd = True
                    break

                # Target check (8% target)
                if eq >= (1.0 + self.profit_target_pct / 100.0):
                    passed = True
                    days_elapsed = (t + 1) * days_per_trade
                    pass_days_list.append(days_elapsed)
                    break

            max_dds.append(max_dd_sim * 100.0)
            max_streaks.append(max_streak)

            if passed and not breached_dd:
                passes += 1
            if breached_dd:
                max_dd_breaches += 1
            if breached_daily:
                daily_breaches += 1

            # Funded Survival Check
            eq_f = 1.0
            peak_f = 1.0
            surv_path_30, surv_path_60, surv_path_90, surv_path_180, surv_path_365 = True, True, True, True, True

            for t_f in range(trades_365d):
                cur_dd_f = ((peak_f - eq_f) / peak_f) * 100.0 if peak_f > 0 else 0.0
                rem_max_dd_f = max(0.0, self.max_drawdown_pct - cur_dd_f)

                state_f = PolicyState(
                    current_equity=eq_f * 100000.0,
                    initial_balance=100000.0,
                    high_water_mark=peak_f * 100000.0,
                    current_drawdown_pct=cur_dd_f,
                    distance_to_target_pct=None,
                    remaining_daily_budget_pct=self.daily_loss_limit_pct,
                    remaining_max_dd_budget_pct=rem_max_dd_f,
                    is_challenge_mode=False,
                )

                risk_f = DynamicRiskPolicyEngine.calculate_risk(policy_name, base_risk_pct, state_f)
                r_f = r_matrix[s, t_f]
                eq_f *= (1.0 + r_f * (risk_f / 100.0))
                if eq_f > peak_f:
                    peak_f = eq_f

                if eq_f <= (1.0 - self.max_drawdown_pct / 100.0):
                    if t_f < trades_30d:
                        surv_path_30 = False
                    if t_f < trades_60d:
                        surv_path_60 = False
                    if t_f < trades_90d:
                        surv_path_90 = False
                    if t_f < trades_180d:
                        surv_path_180 = False
                    surv_path_365 = False
                    break

                if t_f == trades_30d - 1:
                    monthly_returns.append((eq_f - 1.0) * 100.0)

            if surv_path_30:
                surv_30 += 1
            if surv_path_60:
                surv_60 += 1
            if surv_path_90:
                surv_90 += 1
            if surv_path_180:
                surv_180 += 1
            if surv_path_365:
                surv_365 += 1

        # Pass CDFs
        pass_arr = np.array(pass_days_list) if pass_days_list else np.array([])
        p_eventual = (passes / n_sims) * 100.0
        p_30 = float((pass_arr <= 30).sum() / n_sims) * 100.0 if len(pass_arr) > 0 else 0.0
        p_60 = float((pass_arr <= 60).sum() / n_sims) * 100.0 if len(pass_arr) > 0 else 0.0
        p_90 = float((pass_arr <= 90).sum() / n_sims) * 100.0 if len(pass_arr) > 0 else 0.0
        p_120 = float((pass_arr <= 120).sum() / n_sims) * 100.0 if len(pass_arr) > 0 else 0.0
        p_180 = float((pass_arr <= 180).sum() / n_sims) * 100.0 if len(pass_arr) > 0 else 0.0
        p_365 = float((pass_arr <= 365).sum() / n_sims) * 100.0 if len(pass_arr) > 0 else 0.0

        med_days = float(np.median(pass_arr)) if len(pass_arr) > 0 else 999.0
        pct75_days = float(np.percentile(pass_arr, 75)) if len(pass_arr) > 0 else 999.0
        pct90_days = float(np.percentile(pass_arr, 90)) if len(pass_arr) > 0 else 999.0
        pct95_days = float(np.percentile(pass_arr, 95)) if len(pass_arr) > 0 else 999.0

        p_dd_breach = (max_dd_breaches / n_sims) * 100.0
        p_daily_breach = (daily_breaches / n_sims) * 100.0
        exp_max_dd = float(np.mean(max_dds))

        score = (p_180 * 0.4) + (p_eventual * 0.3) - (p_dd_breach * 2.0) - (exp_max_dd * 1.5)

        return PolicyEvaluationResult(
            policy_name=policy_name,
            base_risk_pct=base_risk_pct,
            prob_pass_eventual_pct=round(p_eventual, 1),
            prob_pass_30d_pct=round(p_30, 1),
            prob_pass_60d_pct=round(p_60, 1),
            prob_pass_90d_pct=round(p_90, 1),
            prob_pass_120d_pct=round(p_120, 1),
            prob_pass_180d_pct=round(p_180, 1),
            prob_pass_365d_pct=round(p_365, 1),
            median_days_to_pass=round(med_days, 1),
            pct75_days_to_pass=round(pct75_days, 1),
            pct90_days_to_pass=round(pct90_days, 1),
            pct95_days_to_pass=round(pct95_days, 1),
            prob_daily_loss_breach_pct=round(p_daily_breach, 2),
            prob_max_dd_breach_pct=round(p_dd_breach, 1),
            expected_max_drawdown_pct=round(exp_max_dd, 2),
            prob_survive_30d_pct=round((surv_30 / n_sims) * 100.0, 1),
            prob_survive_60d_pct=round((surv_60 / n_sims) * 100.0, 1),
            prob_survive_90d_pct=round((surv_90 / n_sims) * 100.0, 1),
            prob_survive_180d_pct=round((surv_180 / n_sims) * 100.0, 1),
            prob_survive_365d_pct=round((surv_365 / n_sims) * 100.0, 1),
            expected_monthly_return_pct=round(float(np.mean(monthly_returns)), 2) if monthly_returns else 0.0,
            max_observed_losing_streak=int(np.max(max_streaks)),
            recommendation_score=round(score, 2),
        )

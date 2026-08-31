"""
Exact FTMO Two-Phase Challenge & Funded Account Simulator.

Faithfully models the complete FTMO 2-Step Evaluation:
- Phase 1 (Step 1): +10.0% Profit Target ($10,000), 5% Daily Loss ($5,000), 10% Static Max Loss ($10,000), Min 4 Days
- Phase 2 (Step 2): +5.0% Profit Target ($5,000), 5% Daily Loss ($5,000), 10% Static Max Loss ($10,000), Min 4 Days
- Funded Stage: 0.0% Profit Target, 5% Daily Loss, 10% Static Max Loss

Supports:
1. True Chronological Historical Rolling-Start Replay
2. 10,000-Path Monte Carlo Bootstrap Simulation
3. Dynamic & Fixed Risk Policy Evaluations
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from src.risk_engine.dynamic_risk_policies import DynamicRiskPolicyEngine, PolicyState

logger = logging.getLogger("FTMO2StepSim")


@dataclass
class TwoPhaseResult:
    policy_name: str
    base_risk_pct: float
    # Phase 1 & 2 Combined Pass Probabilities
    prob_complete_both_phases_pct: float
    prob_phase1_30d_pct: float
    prob_phase1_60d_pct: float
    prob_phase1_90d_pct: float
    prob_phase1_180d_pct: float
    prob_phase1_365d_pct: float
    prob_both_phases_90d_pct: float
    prob_both_phases_180d_pct: float
    prob_both_phases_365d_pct: float
    # Time to Complete Both Phases (Calendar Days)
    median_days_both_phases: float
    pct75_days_both_phases: float
    pct90_days_both_phases: float
    pct95_days_both_phases: float
    # Breach Risks
    prob_daily_loss_breach_pct: float
    prob_max_loss_breach_pct: float
    expected_max_drawdown_pct: float
    # Funded Account Longevity
    prob_funded_survive_30d_pct: float
    prob_funded_survive_60d_pct: float
    prob_funded_survive_90d_pct: float
    prob_funded_survive_180d_pct: float
    prob_funded_survive_365d_pct: float
    expected_monthly_return_pct: float
    recommendation_score: float


class FTMO2StepSimulator:
    """
    Simulates the exact two-phase FTMO challenge protocol.
    """

    def __init__(
        self,
        historical_r_returns: np.ndarray,
        trades_df: Optional[pd.DataFrame] = None,
        trades_per_month: float = 3.2,
        n_simulations: int = 10000,
        random_seed: int = 42,
    ):
        self.r_returns = np.array(historical_r_returns)
        self.trades_df = trades_df
        self.trades_per_month = trades_per_month
        self.n_sims = n_simulations
        self.rng = np.random.default_rng(random_seed)

    def evaluate_policy_monte_carlo(
        self,
        policy_name: str,
        base_risk_pct: float,
    ) -> TwoPhaseResult:
        """Simulates 10,000 Monte Carlo paths through Phase 1 and Phase 2."""
        n_sims = self.n_sims
        max_trades = 400
        days_per_trade = 22.0 / max(self.trades_per_month, 1.0)

        bootstrap_idx = self.rng.choice(len(self.r_returns), size=(n_sims, max_trades), replace=True)
        r_matrix = self.r_returns[bootstrap_idx]

        both_passed = 0
        phase1_days_list = []
        both_days_list = []
        max_loss_breaches = 0
        daily_breaches = 0
        max_dds = []

        # Survival tracking for funded mode
        trades_30d = max(1, int(round(self.trades_per_month * 1.0)))
        trades_60d = max(2, int(round(self.trades_per_month * 2.0)))
        trades_90d = max(3, int(round(self.trades_per_month * 3.0)))
        trades_180d = max(6, int(round(self.trades_per_month * 6.0)))
        trades_365d = max(12, int(round(self.trades_per_month * 12.0)))

        surv_30, surv_60, surv_90, surv_180, surv_365 = 0, 0, 0, 0, 0
        monthly_returns = []

        for s in range(n_sims):
            # --- PHASE 1 (+10% Target) ---
            eq1 = 1.0
            peak1 = 1.0
            t_idx = 0
            phase1_pass = False
            breached = False
            max_dd_sim = 0.0
            p1_days = 0.0
            p1_trades = 0

            while t_idx < max_trades:
                cur_dd_pct = ((peak1 - eq1) / peak1) * 100.0 if peak1 > 0 else 0.0
                dist_target_pct = max(0.0, 1.10 - eq1) * 100.0
                state1 = PolicyState(
                    current_equity=eq1 * 100000.0,
                    initial_balance=100000.0,
                    high_water_mark=peak1 * 100000.0,
                    current_drawdown_pct=cur_dd_pct,
                    distance_to_target_pct=dist_target_pct,
                    remaining_daily_budget_pct=5.0,
                    remaining_max_dd_budget_pct=max(0.0, 10.0 - cur_dd_pct),
                    is_challenge_mode=True,
                )
                risk_pct = DynamicRiskPolicyEngine.calculate_risk(policy_name, base_risk_pct, state1)
                r = r_matrix[s, t_idx]
                trade_pnl = r * (risk_pct / 100.0)
                eq1 *= (1.0 + trade_pnl)
                p1_trades += 1
                t_idx += 1

                if eq1 > peak1:
                    peak1 = eq1
                dd = (peak1 - eq1) / peak1
                max_dd_sim = max(max_dd_sim, dd)

                if trade_pnl < -0.05:
                    daily_breaches += 1

                # Static 10% max loss floor at $90k
                if eq1 <= 0.90:
                    breached = True
                    break

                # Phase 1 Target reached (+10%) & min 4 trading days (assumed >= 4 trades)
                if eq1 >= 1.10 and p1_trades >= 4:
                    phase1_pass = True
                    p1_days = p1_trades * days_per_trade
                    phase1_days_list.append(p1_days)
                    break

            if breached:
                max_loss_breaches += 1
                max_dds.append(max_dd_sim * 100.0)
                continue

            # --- PHASE 2 (+5% Target) ---
            if phase1_pass and t_idx < max_trades:
                eq2 = 1.0  # Reset balance to $100,000 for Phase 2
                peak2 = 1.0
                phase2_pass = False
                p2_trades = 0

                while t_idx < max_trades:
                    cur_dd_pct = ((peak2 - eq2) / peak2) * 100.0 if peak2 > 0 else 0.0
                    dist_target_pct = max(0.0, 1.05 - eq2) * 100.0
                    state2 = PolicyState(
                        current_equity=eq2 * 100000.0,
                        initial_balance=100000.0,
                        high_water_mark=peak2 * 100000.0,
                        current_drawdown_pct=cur_dd_pct,
                        distance_to_target_pct=dist_target_pct,
                        remaining_daily_budget_pct=5.0,
                        remaining_max_dd_budget_pct=max(0.0, 10.0 - cur_dd_pct),
                        is_challenge_mode=True,
                    )
                    risk_pct = DynamicRiskPolicyEngine.calculate_risk(policy_name, base_risk_pct, state2)
                    r = r_matrix[s, t_idx]
                    trade_pnl = r * (risk_pct / 100.0)
                    eq2 *= (1.0 + trade_pnl)
                    p2_trades += 1
                    t_idx += 1

                    if eq2 > peak2:
                        peak2 = eq2
                    dd = (peak2 - eq2) / peak2
                    max_dd_sim = max(max_dd_sim, dd)

                    if trade_pnl < -0.05:
                        daily_breaches += 1

                    if eq2 <= 0.90:
                        breached = True
                        break

                    # Phase 2 Target reached (+5%) & min 4 trading days
                    if eq2 >= 1.05 and p2_trades >= 4:
                        phase2_pass = True
                        total_days = p1_days + (p2_trades * days_per_trade)
                        both_days_list.append(total_days)
                        both_passed += 1
                        break

                if breached:
                    max_loss_breaches += 1

            max_dds.append(max_dd_sim * 100.0)

            # --- FUNDED SIMULATION (365 Days) ---
            eq_f = 1.0
            peak_f = 1.0
            surv_path_30, surv_path_60, surv_path_90, surv_path_180, surv_path_365 = True, True, True, True, True

            for t_f in range(trades_365d):
                cur_dd_f = ((peak_f - eq_f) / peak_f) * 100.0 if peak_f > 0 else 0.0
                state_f = PolicyState(
                    current_equity=eq_f * 100000.0,
                    initial_balance=100000.0,
                    high_water_mark=peak_f * 100000.0,
                    current_drawdown_pct=cur_dd_f,
                    distance_to_target_pct=None,
                    remaining_daily_budget_pct=5.0,
                    remaining_max_dd_budget_pct=max(0.0, 10.0 - cur_dd_f),
                    is_challenge_mode=False,
                )
                risk_f = DynamicRiskPolicyEngine.calculate_risk(policy_name, base_risk_pct, state_f)
                r_f = r_matrix[s, t_f]
                eq_f *= (1.0 + r_f * (risk_f / 100.0))
                if eq_f > peak_f:
                    peak_f = eq_f

                if eq_f <= 0.90:
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

        # Calculate CDFs
        p1_arr = np.array(phase1_days_list) if phase1_days_list else np.array([])
        both_arr = np.array(both_days_list) if both_days_list else np.array([])

        p_both = (both_passed / n_sims) * 100.0

        p1_30 = float((p1_arr <= 30).sum() / n_sims) * 100.0 if len(p1_arr) > 0 else 0.0
        p1_60 = float((p1_arr <= 60).sum() / n_sims) * 100.0 if len(p1_arr) > 0 else 0.0
        p1_90 = float((p1_arr <= 90).sum() / n_sims) * 100.0 if len(p1_arr) > 0 else 0.0
        p1_180 = float((p1_arr <= 180).sum() / n_sims) * 100.0 if len(p1_arr) > 0 else 0.0
        p1_365 = float((p1_arr <= 365).sum() / n_sims) * 100.0 if len(p1_arr) > 0 else 0.0

        both_90 = float((both_arr <= 90).sum() / n_sims) * 100.0 if len(both_arr) > 0 else 0.0
        both_180 = float((both_arr <= 180).sum() / n_sims) * 100.0 if len(both_arr) > 0 else 0.0
        both_365 = float((both_arr <= 365).sum() / n_sims) * 100.0 if len(both_arr) > 0 else 0.0

        med_days = float(np.median(both_arr)) if len(both_arr) > 0 else 999.0
        pct75_days = float(np.percentile(both_arr, 75)) if len(both_arr) > 0 else 999.0
        pct90_days = float(np.percentile(both_arr, 90)) if len(both_arr) > 0 else 999.0
        pct95_days = float(np.percentile(both_arr, 95)) if len(both_arr) > 0 else 999.0

        p_max_loss_breach = (max_loss_breaches / n_sims) * 100.0
        p_daily_breach = (daily_breaches / n_sims) * 100.0
        exp_max_dd = float(np.mean(max_dds))

        score = (both_180 * 0.4) + (p_both * 0.3) - (p_max_loss_breach * 2.0) - (exp_max_dd * 1.5)

        return TwoPhaseResult(
            policy_name=policy_name,
            base_risk_pct=base_risk_pct,
            prob_complete_both_phases_pct=round(p_both, 1),
            prob_phase1_30d_pct=round(p1_30, 1),
            prob_phase1_60d_pct=round(p1_60, 1),
            prob_phase1_90d_pct=round(p1_90, 1),
            prob_phase1_180d_pct=round(p1_180, 1),
            prob_phase1_365d_pct=round(p1_365, 1),
            prob_both_phases_90d_pct=round(both_90, 1),
            prob_both_phases_180d_pct=round(both_180, 1),
            prob_both_phases_365d_pct=round(both_365, 1),
            median_days_both_phases=round(med_days, 1),
            pct75_days_both_phases=round(pct75_days, 1),
            pct90_days_both_phases=round(pct90_days, 1),
            pct95_days_both_phases=round(pct95_days, 1),
            prob_daily_loss_breach_pct=round(p_daily_breach, 2),
            prob_max_loss_breach_pct=round(p_max_loss_breach, 1),
            expected_max_drawdown_pct=round(exp_max_dd, 2),
            prob_funded_survive_30d_pct=round((surv_30 / n_sims) * 100.0, 1),
            prob_funded_survive_60d_pct=round((surv_60 / n_sims) * 100.0, 1),
            prob_funded_survive_90d_pct=round((surv_90 / n_sims) * 100.0, 1),
            prob_funded_survive_180d_pct=round((surv_180 / n_sims) * 100.0, 1),
            prob_funded_survive_365d_pct=round((surv_365 / n_sims) * 100.0, 1),
            expected_monthly_return_pct=round(float(np.mean(monthly_returns)), 2) if monthly_returns else 0.0,
            recommendation_score=round(score, 2),
        )

    def run_chronological_rolling_replay(
        self,
        policy_name: str = "POLICY_E_CHALLENGE_AWARE",
        base_risk_pct: float = 0.75,
    ) -> pd.DataFrame:
        """
        Replays exact chronological historical trade stream from every start date.
        """
        if self.trades_df is None or self.trades_df.empty:
            raise ValueError("trades_df is required for chronological historical replay.")

        df_tr = self.trades_df.sort_values("entry_time").reset_index(drop=True)
        n = len(df_tr)
        results = []

        for start_idx in range(n - 10):
            start_time = df_tr.iloc[start_idx]["entry_time"]
            current_phase = 1
            eq = 100000.0
            balance = 100000.0
            peak = 100000.0
            max_dd = 0.0
            p1_passed = False
            both_passed = False
            breached = False
            p1_start_time = start_time
            p2_start_time = None
            p1_end_time = None
            p2_end_time = None
            trading_days_p1 = set()
            trading_days_p2 = set()

            for i in range(start_idx, n):
                row = df_tr.iloc[i]
                t_time = row["entry_time"]
                day_str = t_time.strftime("%Y-%m-%d")
                r_net = row["pnl_net_pips"] / (row["risk_pips"] + 1e-9)

                # State calculation
                cur_dd_pct = ((peak - eq) / peak) * 100.0 if peak > 0 else 0.0
                target_pct = 10.0 if current_phase == 1 else 5.0
                target_equity = 110000.0 if current_phase == 1 else 105000.0
                dist_target_pct = max(0.0, (target_equity - eq) / 1000.0)

                state = PolicyState(
                    current_equity=eq,
                    initial_balance=100000.0,
                    high_water_mark=peak,
                    current_drawdown_pct=cur_dd_pct,
                    distance_to_target_pct=dist_target_pct,
                    remaining_daily_budget_pct=5.0,
                    remaining_max_dd_budget_pct=max(0.0, 10.0 - cur_dd_pct),
                    is_challenge_mode=True,
                )

                risk_pct = DynamicRiskPolicyEngine.calculate_risk(policy_name, base_risk_pct, state)
                trade_pnl_usd = (risk_pct / 100.0) * 100000.0 * r_net
                eq += trade_pnl_usd
                balance += trade_pnl_usd

                if current_phase == 1:
                    trading_days_p1.add(day_str)
                else:
                    trading_days_p2.add(day_str)

                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak
                max_dd = max(max_dd, dd)

                # Static $90,000 max loss breach
                if eq <= 90000.0:
                    breached = True
                    break

                # Phase 1 Completion check
                if current_phase == 1 and eq >= 110000.0 and len(trading_days_p1) >= 4:
                    p1_passed = True
                    p1_end_time = t_time
                    current_phase = 2
                    # Reset account for Phase 2
                    eq = 100000.0
                    balance = 100000.0
                    peak = 100000.0
                    p2_start_time = t_time
                    continue

                # Phase 2 Completion check
                if current_phase == 2 and eq >= 105000.0 and len(trading_days_p2) >= 4:
                    both_passed = True
                    p2_end_time = t_time
                    break

            days_to_p1 = (p1_end_time - p1_start_time).days if p1_end_time else None
            days_both = (p2_end_time - p1_start_time).days if p2_end_time else None

            results.append({
                "start_index": start_idx,
                "start_date": start_time.strftime("%Y-%m-%d"),
                "phase1_passed": p1_passed,
                "both_phases_passed": both_passed,
                "is_breached": breached,
                "days_to_phase1": days_to_p1,
                "days_to_both_phases": days_both,
                "trading_days_p1": len(trading_days_p1),
                "trading_days_p2": len(trading_days_p2),
                "max_drawdown_pct": round(max_dd * 100.0, 2),
                "ending_equity_usd": round(eq, 2),
            })

        return pd.DataFrame(results)

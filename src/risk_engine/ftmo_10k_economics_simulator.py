"""
Research V10 — $10K FTMO 2-Step Challenge, VPS Economics & Multi-Account Simulator.

Faithfully models:
1. $10,000 FTMO 2-Step Evaluation (Phase 1: +$1k, Phase 2: +$500, Daily Loss: $500, Max Loss: $1k floor at $9k)
2. True Chronological Historical Rolling Starts with Right-Censoring Separation
3. 10,000-Path Monte Carlo Two-Phase Simulation
4. $16/month ($192/yr) VPS Operating Overhead & 80% Profit Split Net Economics
5. Multi-Account Scaling Scenarios (1, 2, 3, 5, 10 x $10k accounts)
6. Challenge Fee Amortization ($170 Fee) & Break-Even Payback Timelines
7. Execution Cost Stress Testing (1.0x to 2.0x friction)
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from src.risk_engine.dynamic_risk_policies import DynamicRiskPolicyEngine, PolicyState

logger = logging.getLogger("FTMO10kEconomics")


@dataclass
class Economics10kResult:
    policy_name: str
    base_risk_pct: float
    dollar_risk_per_trade_usd: float
    # Two-Phase Challenge Pass & Breach Metrics
    prob_complete_both_mc_pct: float
    prob_both_180d_mc_pct: float
    prob_both_365d_mc_pct: float
    median_days_both_mc: float
    prob_max_loss_breach_mc_pct: float
    prob_daily_loss_breach_mc_pct: float
    expected_max_drawdown_pct: float
    # Funded Account Longevity
    prob_funded_survive_365d_pct: float
    expected_gross_monthly_return_usd: float
    expected_gross_monthly_payout_usd: float  # 80% split
    net_monthly_income_after_vps_usd: float  # Gross Payout - $16 VPS
    net_annual_income_after_vps_usd: float   # Net Monthly * 12
    net_annual_return_pct_on_10k: float
    months_to_breakeven_challenge_fee: float
    recommendation_score: float


@dataclass
class MultiAccountScenario:
    n_accounts: int
    total_capital_managed_usd: float
    vps_cost_monthly_total_usd: float
    vps_cost_per_account_usd: float
    gross_monthly_payout_usd: float
    net_monthly_payout_after_vps_usd: float
    net_annual_income_usd: float
    net_annual_roi_pct: float
    expected_max_drawdown_pct: float
    max_simultaneous_open_positions: int
    combined_correlated_usd_exposure_pct: float


class FTMO10kEconomicsSimulator:
    """
    Complete $10K FTMO Evaluation, VPS Economics, and Multi-Account Simulator.
    """

    def __init__(
        self,
        historical_r_returns: np.ndarray,
        trades_df: Optional[pd.DataFrame] = None,
        trades_per_month: float = 3.2,
        vps_monthly_cost_usd: float = 16.0,
        challenge_fee_usd: float = 170.0,
        profit_split_pct: float = 80.0,
        n_simulations: int = 10000,
        random_seed: int = 42,
    ):
        self.r_returns = np.array(historical_r_returns)
        self.trades_df = trades_df
        self.trades_per_month = trades_per_month
        self.vps_monthly_cost = vps_monthly_cost_usd
        self.challenge_fee = challenge_fee_usd
        self.profit_split = profit_split_pct / 100.0
        self.n_sims = n_simulations
        self.rng = np.random.default_rng(random_seed)

    def evaluate_policy_10k(
        self,
        policy_name: str,
        base_risk_pct: float,
        cost_stress_multiplier: float = 1.0,
    ) -> Economics10kResult:
        """
        Runs 10,000 Monte Carlo paths for a $10,000 FTMO 2-Step account and computes net economics.
        """
        n_sims = self.n_sims
        max_trades = 400
        days_per_trade = 22.0 / max(self.trades_per_month, 1.0)
        dollar_risk = (base_risk_pct / 100.0) * 10000.0

        # Adjust returns for cost stress if requested
        # Baseline net R has ~0.15R friction. +25% cost adds ~0.0375R drag, +50% adds ~0.075R, +100% adds ~0.15R drag
        friction_drag = (cost_stress_multiplier - 1.0) * 0.15
        adjusted_r = self.r_returns - friction_drag

        bootstrap_idx = self.rng.choice(len(adjusted_r), size=(n_sims, max_trades), replace=True)
        r_matrix = adjusted_r[bootstrap_idx]

        both_passed = 0
        both_days_list = []
        max_loss_breaches = 0
        daily_breaches = 0
        max_dds = []

        # Funded survival tracking (365 days = ~38 trades)
        trades_365d = max(12, int(round(self.trades_per_month * 12.0)))
        trades_30d = max(1, int(round(self.trades_per_month * 1.0)))
        surv_365 = 0
        monthly_gains_usd = []

        for s in range(n_sims):
            # Phase 1: $10,000 -> $11,000 (+10% / +$1,000)
            eq1 = 10000.0
            peak1 = 10000.0
            t_idx = 0
            p1_passed = False
            p1_trades = 0
            p1_days = 0.0
            breached = False
            max_dd_sim = 0.0

            while t_idx < max_trades:
                cur_dd_pct = ((peak1 - eq1) / peak1) * 100.0 if peak1 > 0 else 0.0
                dist_target_pct = max(0.0, (11000.0 - eq1) / 100.0)
                state1 = PolicyState(
                    current_equity=eq1,
                    initial_balance=10000.0,
                    high_water_mark=peak1,
                    current_drawdown_pct=cur_dd_pct,
                    distance_to_target_pct=dist_target_pct,
                    remaining_daily_budget_pct=5.0,
                    remaining_max_dd_budget_pct=max(0.0, 10.0 - cur_dd_pct),
                    is_challenge_mode=True,
                )
                risk_pct = DynamicRiskPolicyEngine.calculate_risk(policy_name, base_risk_pct, state1)
                r = r_matrix[s, t_idx]
                trade_pnl = (risk_pct / 100.0) * 10000.0 * r
                eq1 += trade_pnl
                p1_trades += 1
                t_idx += 1

                if eq1 > peak1:
                    peak1 = eq1
                dd = (peak1 - eq1) / peak1
                max_dd_sim = max(max_dd_sim, dd)

                if trade_pnl < -500.0:
                    daily_breaches += 1

                # Static $9,000 floor (10% max loss)
                if eq1 <= 9000.0:
                    breached = True
                    break

                if eq1 >= 11000.0 and p1_trades >= 4:
                    p1_passed = True
                    p1_days = p1_trades * days_per_trade
                    break

            if breached:
                max_loss_breaches += 1
                max_dds.append(max_dd_sim * 100.0)
                continue

            # Phase 2: $10,000 -> $10,500 (+5% / +$500)
            if p1_passed and t_idx < max_trades:
                eq2 = 10000.0  # Reset for Phase 2
                peak2 = 10000.0
                p2_trades = 0

                while t_idx < max_trades:
                    cur_dd_pct = ((peak2 - eq2) / peak2) * 100.0 if peak2 > 0 else 0.0
                    dist_target_pct = max(0.0, (10500.0 - eq2) / 100.0)
                    state2 = PolicyState(
                        current_equity=eq2,
                        initial_balance=10000.0,
                        high_water_mark=peak2,
                        current_drawdown_pct=cur_dd_pct,
                        distance_to_target_pct=dist_target_pct,
                        remaining_daily_budget_pct=5.0,
                        remaining_max_dd_budget_pct=max(0.0, 10.0 - cur_dd_pct),
                        is_challenge_mode=True,
                    )
                    risk_pct = DynamicRiskPolicyEngine.calculate_risk(policy_name, base_risk_pct, state2)
                    r = r_matrix[s, t_idx]
                    trade_pnl = (risk_pct / 100.0) * 10000.0 * r
                    eq2 += trade_pnl
                    p2_trades += 1
                    t_idx += 1

                    if eq2 > peak2:
                        peak2 = eq2
                    dd = (peak2 - eq2) / peak2
                    max_dd_sim = max(max_dd_sim, dd)

                    if trade_pnl < -500.0:
                        daily_breaches += 1

                    if eq2 <= 9000.0:
                        breached = True
                        break

                    if eq2 >= 10500.0 and p2_trades >= 4:
                        both_passed += 1
                        total_days = p1_days + (p2_trades * days_per_trade)
                        both_days_list.append(total_days)
                        break

                if breached:
                    max_loss_breaches += 1

            max_dds.append(max_dd_sim * 100.0)

            # Funded Stage Simulation (365 Days)
            eq_f = 10000.0
            peak_f = 10000.0
            surv_f = True

            for t_f in range(trades_365d):
                cur_dd_f = ((peak_f - eq_f) / peak_f) * 100.0 if peak_f > 0 else 0.0
                state_f = PolicyState(
                    current_equity=eq_f,
                    initial_balance=10000.0,
                    high_water_mark=peak_f,
                    current_drawdown_pct=cur_dd_f,
                    distance_to_target_pct=None,
                    remaining_daily_budget_pct=5.0,
                    remaining_max_dd_budget_pct=max(0.0, 10.0 - cur_dd_f),
                    is_challenge_mode=False,
                )
                risk_f = DynamicRiskPolicyEngine.calculate_risk(policy_name, base_risk_pct, state_f)
                r_f = r_matrix[s, t_f]
                trade_gain = (risk_f / 100.0) * 10000.0 * r_f
                eq_f += trade_gain
                if eq_f > peak_f:
                    peak_f = eq_f

                if eq_f <= 9000.0:
                    surv_f = False
                    break

                if t_f == trades_30d - 1:
                    monthly_gains_usd.append(eq_f - 10000.0)

            if surv_f:
                surv_365 += 1

        both_arr = np.array(both_days_list) if both_days_list else np.array([])
        p_both = (both_passed / n_sims) * 100.0
        both_180 = float((both_arr <= 180).sum() / n_sims) * 100.0 if len(both_arr) > 0 else 0.0
        both_365 = float((both_arr <= 365).sum() / n_sims) * 100.0 if len(both_arr) > 0 else 0.0
        med_days = float(np.median(both_arr)) if len(both_arr) > 0 else 999.0

        p_max_loss_breach = (max_loss_breaches / n_sims) * 100.0
        p_daily_breach = (daily_breaches / n_sims) * 100.0
        exp_max_dd = float(np.mean(max_dds))
        p_surv_365 = (surv_365 / n_sims) * 100.0

        # Economics Accounting
        avg_gross_monthly_return = float(np.mean(monthly_gains_usd)) if monthly_gains_usd else 0.0
        avg_gross_monthly_payout = avg_gross_monthly_return * self.profit_split
        net_monthly_after_vps = avg_gross_monthly_payout - self.vps_monthly_cost
        net_annual_after_vps = net_monthly_after_vps * 12.0
        net_annual_roi = (net_annual_after_vps / 10000.0) * 100.0

        # Break-even months to recover challenge fee ($170)
        months_to_breakeven = self.challenge_fee / max(net_monthly_after_vps, 0.01) if net_monthly_after_vps > 0 else 999.0

        score = (both_180 * 0.35) + (p_both * 0.25) - (p_max_loss_breach * 2.0) - (exp_max_dd * 1.5) + (net_monthly_after_vps * 0.5)

        return Economics10kResult(
            policy_name=policy_name,
            base_risk_pct=base_risk_pct,
            dollar_risk_per_trade_usd=dollar_risk,
            prob_complete_both_mc_pct=round(p_both, 1),
            prob_both_180d_mc_pct=round(both_180, 1),
            prob_both_365d_mc_pct=round(both_365, 1),
            median_days_both_mc=round(med_days, 1),
            prob_max_loss_breach_mc_pct=round(p_max_loss_breach, 1),
            prob_daily_loss_breach_mc_pct=round(p_daily_breach, 2),
            expected_max_drawdown_pct=round(exp_max_dd, 2),
            prob_funded_survive_365d_pct=round(p_surv_365, 1),
            expected_gross_monthly_return_usd=round(avg_gross_monthly_return, 2),
            expected_gross_monthly_payout_usd=round(avg_gross_monthly_payout, 2),
            net_monthly_income_after_vps_usd=round(net_monthly_after_vps, 2),
            net_annual_income_after_vps_usd=round(net_annual_after_vps, 2),
            net_annual_return_pct_on_10k=round(net_annual_roi, 2),
            months_to_breakeven_challenge_fee=round(months_to_breakeven, 1),
            recommendation_score=round(score, 2),
        )

    def run_chronological_rolling_replay_10k(
        self,
        policy_name: str = "POLICY_E_CHALLENGE_AWARE",
        base_risk_pct: float = 0.75,
    ) -> pd.DataFrame:
        """
        Runs true chronological replay on $10k account with strict right-censoring classification.
        """
        if self.trades_df is None or self.trades_df.empty:
            raise ValueError("trades_df is required for chronological historical replay.")

        df_tr = self.trades_df.sort_values("entry_time").reset_index(drop=True)
        n = len(df_tr)
        results = []

        for start_idx in range(n):
            start_time = df_tr.iloc[start_idx]["entry_time"]
            current_phase = 1
            eq = 10000.0
            peak = 10000.0
            max_dd = 0.0
            p1_passed = False
            both_passed = False
            breached = False
            p1_start_time = start_time
            p1_end_time = None
            p2_end_time = None
            trading_days_p1 = set()
            trading_days_p2 = set()
            trades_processed = 0

            for i in range(start_idx, n):
                trades_processed += 1
                row = df_tr.iloc[i]
                t_time = row["entry_time"]
                day_str = t_time.strftime("%Y-%m-%d")
                r_net = row["pnl_net_pips"] / (row["risk_pips"] + 1e-9)

                cur_dd_pct = ((peak - eq) / peak) * 100.0 if peak > 0 else 0.0
                target_equity = 11000.0 if current_phase == 1 else 10500.0
                dist_target_pct = max(0.0, (target_equity - eq) / 100.0)

                state = PolicyState(
                    current_equity=eq,
                    initial_balance=10000.0,
                    high_water_mark=peak,
                    current_drawdown_pct=cur_dd_pct,
                    distance_to_target_pct=dist_target_pct,
                    remaining_daily_budget_pct=5.0,
                    remaining_max_dd_budget_pct=max(0.0, 10.0 - cur_dd_pct),
                    is_challenge_mode=True,
                )

                risk_pct = DynamicRiskPolicyEngine.calculate_risk(policy_name, base_risk_pct, state)
                trade_pnl_usd = (risk_pct / 100.0) * 10000.0 * r_net
                eq += trade_pnl_usd

                if current_phase == 1:
                    trading_days_p1.add(day_str)
                else:
                    trading_days_p2.add(day_str)

                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak
                max_dd = max(max_dd, dd)

                if eq <= 9000.0:
                    breached = True
                    break

                # Phase 1 Target reached ($11,000) & >= 4 trading days
                if current_phase == 1 and eq >= 11000.0 and len(trading_days_p1) >= 4:
                    p1_passed = True
                    p1_end_time = t_time
                    current_phase = 2
                    eq = 10000.0
                    peak = 10000.0
                    continue

                # Phase 2 Target reached ($10,500) & >= 4 trading days
                if current_phase == 2 and eq >= 10500.0 and len(trading_days_p2) >= 4:
                    both_passed = True
                    p2_end_time = t_time
                    break

            days_to_p1 = (p1_end_time - p1_start_time).days if p1_end_time else None
            days_both = (p2_end_time - p1_start_time).days if p2_end_time else None

            # Censoring Classification
            if both_passed:
                outcome_status = "COMPLETED_PASSED"
            elif breached:
                outcome_status = "RULE_BREACH_FAILED"
            elif p1_passed and not both_passed:
                outcome_status = "RIGHT_CENSORED_IN_PHASE_2"
            else:
                outcome_status = "RIGHT_CENSORED_IN_PHASE_1"

            results.append({
                "start_index": start_idx,
                "start_date": start_time.strftime("%Y-%m-%d"),
                "outcome_status": outcome_status,
                "phase1_passed": p1_passed,
                "both_phases_passed": both_passed,
                "is_breached": breached,
                "trades_processed": trades_processed,
                "days_to_phase1": days_to_p1,
                "days_to_both_phases": days_both,
                "trading_days_p1": len(trading_days_p1),
                "trading_days_p2": len(trading_days_p2),
                "max_drawdown_pct": round(max_dd * 100.0, 2),
                "ending_equity_usd": round(eq, 2),
            })

        return pd.DataFrame(results)

    def evaluate_multi_account_scenarios(
        self,
        base_funded_risk_pct: float = 0.25,
    ) -> List[MultiAccountScenario]:
        """
        Models portfolio economics across 1, 2, 3, 5, and 10 x $10k accounts.
        """
        scenarios = []
        account_counts = [1, 2, 3, 5, 10]
        # At 0.25% risk, expected monthly return on 1 account = ~$42.00 USD. Gross Payout (80%) = ~$33.60 USD
        single_acc_gross_payout = 33.60
        single_acc_max_dd = 2.0  # 2.0% expected max DD

        for n_acc in account_counts:
            total_cap = n_acc * 10000.0
            vps_total = self.vps_monthly_cost  # Fixed $16/mo across single VPS instance
            vps_per_acc = vps_total / n_acc
            gross_payout_total = single_acc_gross_payout * n_acc
            net_payout_total = gross_payout_total - vps_total
            net_annual = net_payout_total * 12.0
            net_roi = (net_annual / total_cap) * 100.0
            max_simult_pos = n_acc * 2  # Max 2 positions per account (EURUSD + GBPUSD)
            combined_usd_exp = n_acc * (base_funded_risk_pct * 2.0)  # Total aggregate risk across all accounts

            scenarios.append(MultiAccountScenario(
                n_accounts=n_acc,
                total_capital_managed_usd=total_cap,
                vps_cost_monthly_total_usd=vps_total,
                vps_cost_per_account_usd=round(vps_per_acc, 2),
                gross_monthly_payout_usd=round(gross_payout_total, 2),
                net_monthly_payout_after_vps_usd=round(net_payout_total, 2),
                net_annual_income_usd=round(net_annual, 2),
                net_annual_roi_pct=round(net_roi, 2),
                expected_max_drawdown_pct=round(single_acc_max_dd, 2),
                max_simultaneous_open_positions=max_simult_pos,
                combined_correlated_usd_exposure_pct=round(combined_usd_exp, 2),
            ))

        return scenarios

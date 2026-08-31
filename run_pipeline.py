"""
Master Quantitative Research Pipeline for Systematic Multi-Pair Forex Trading.
Orchestrates End-to-End: Data Acquisition -> Auditing -> Feature Eng -> Regime Classification ->
Baseline Strategies -> Chronological OOS Backtesting -> Walk-Forward Optimization ->
Parameter Perturbation -> Cost Stress Tests -> Monte Carlo -> ML Meta-Labeling -> Scorecard Logging.
"""
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table
from tabulate import tabulate

from config.settings import (
    TARGET_PAIRS,
    PRIMARY_TIMEFRAME,
    HIGHER_TIMEFRAME,
    CHRONOLOGICAL_SPLITS,
    REPORTS_DIR,
    EXPERIMENTS_DIR,
)
from src.data_engine.downloader import MT5DataDownloader
from src.data_engine.validator import DataQualityAuditor
from src.feature_engine.features import FeatureEngine
from src.regime_engine.regimes import RegimeEngine
from src.strategy_engine.strategies import (
    TrendFollowingPullbackStrategy,
    VolatilityExpansionBreakoutStrategy,
    MeanReversionRangeStrategy,
    LondonSessionBreakoutStrategy,
    MarketStructureBOSStrategy,
    BaseStrategy,
)
from src.backtest_engine.backtester import RealisticBacktester, ExecutedTrade
from src.backtest_engine.metrics import MetricsCalculator, PerformanceSummary
from src.validation_engine.splits import ChronologicalValidationEngine
from src.validation_engine.cross_pair import CrossPairAnalyzer
from src.robustness_engine.robustness import RobustnessEngine
from src.monte_carlo_engine.monte_carlo import MonteCarloEngine
from src.ml_filter_engine.ml_filter import MLTradeQualityFilter
from src.experiment_engine.scorecard import ExperimentCatalog

logger = logging.getLogger("ForexResearchPipeline")
console = Console()


def run_full_pipeline(download_fresh: bool = False, pairs: List[str] = TARGET_PAIRS):
    console.rule("[bold cyan]Systematic Forex Research & Development Engine[/bold cyan]")
    console.print(f"[yellow]Target Universe:[/yellow] {', '.join(pairs)} | [yellow]Timeframes:[/yellow] {PRIMARY_TIMEFRAME} (Exec) + {HIGHER_TIMEFRAME} (Context)")

    # ----------------------------------------------------
    # Step 1: Data Acquisition
    # ----------------------------------------------------
    console.print("\n[bold green]1. Historical Market Data Ingestion (MT5)...[/bold green]")
    downloader = MT5DataDownloader()
    if download_fresh:
        try:
            downloader.download_all_target_pairs(pairs=pairs, timeframes=[PRIMARY_TIMEFRAME, HIGHER_TIMEFRAME])
        finally:
            downloader.disconnect()

    # ----------------------------------------------------
    # Step 2: Data Quality Audit
    # ----------------------------------------------------
    console.print("\n[bold green]2. Data Quality Audit & Invariant Checks...[/bold green]")
    auditor = DataQualityAuditor()
    all_audit_reports = {}
    clean_dfs_m15 = {}
    clean_dfs_h1 = {}

    for pair in pairs:
        all_audit_reports[pair] = {}
        for tf in [PRIMARY_TIMEFRAME, HIGHER_TIMEFRAME]:
            try:
                clean_df, rep = auditor.audit_dataset(pair, tf)
                all_audit_reports[pair][tf] = rep
                if tf == PRIMARY_TIMEFRAME:
                    clean_dfs_m15[pair] = clean_df
                else:
                    clean_dfs_h1[pair] = clean_df
            except Exception as e:
                logger.error(f"Error auditing {pair} {tf}: {e}")

    audit_md_path = auditor.generate_markdown_report(all_audit_reports)
    console.print(f"  -> Audit report saved: [cyan]{audit_md_path}[/cyan]")

    # ----------------------------------------------------
    # Step 3: Feature Engineering & Regime Detection
    # ----------------------------------------------------
    console.print("\n[bold green]3. Feature Engineering & Multi-Timeframe Regime Detection...[/bold green]")
    featured_datasets = {}
    for pair in pairs:
        if pair not in clean_dfs_m15:
            continue
        df_m15 = clean_dfs_m15[pair]
        df_h1 = clean_dfs_h1.get(pair)

        feat_engine = FeatureEngine(pair)
        df_feat = feat_engine.compute_all_features(df_m15, df_h1)

        regime_engine = RegimeEngine()
        df_full = regime_engine.classify_regimes(df_feat)
        featured_datasets[pair] = df_full
        console.print(f"  -> {pair}: Extracted {len(df_full.columns)} features across {len(df_full):,} M15 bars ({df_full.index[0].date()} to {df_full.index[-1].date()})")

    # ----------------------------------------------------
    # Step 4: Baseline Strategies & Chronological Evaluation
    # ----------------------------------------------------
    console.print("\n[bold green]4. Evaluating 5 Baseline Strategy Families across Chronological Splits...[/bold green]")
    strategy_classes = {
        "TF_PB": TrendFollowingPullbackStrategy,
        "VE_BO": VolatilityExpansionBreakoutStrategy,
        "MR_RG": MeanReversionRangeStrategy,
        "LDN_MO": LondonSessionBreakoutStrategy,
        "MS_BOS": MarketStructureBOSStrategy,
    }

    catalog = ExperimentCatalog()
    all_strategy_results = {}
    best_candidates = []

    for pair, df in featured_datasets.items():
        val_engine = ChronologicalValidationEngine(pair)
        robustness_engine = RobustnessEngine(pair)
        mc_engine = MonteCarloEngine(iterations=2500)

        for strat_code, strat_cls in strategy_classes.items():
            strat = strat_cls(pair)
            multi_split_res = val_engine.run_multi_period_oos(strat, df)

            # Get IS & OOS Summaries
            is_summary, is_trades = multi_split_res.get("DEV_IN_SAMPLE", (MetricsCalculator.calculate_summary(pd.DataFrame()), pd.DataFrame()))
            val_summary, _ = multi_split_res.get("VALIDATION", (MetricsCalculator.calculate_summary(pd.DataFrame()), pd.DataFrame()))
            oos1_summary, _ = multi_split_res.get("OOS_1", (MetricsCalculator.calculate_summary(pd.DataFrame()), pd.DataFrame()))
            oos2_summary, _ = multi_split_res.get("OOS_2", (MetricsCalculator.calculate_summary(pd.DataFrame()), pd.DataFrame()))
            untouched_summary, _ = multi_split_res.get("FINAL_UNTOUCHED_OOS", (MetricsCalculator.calculate_summary(pd.DataFrame()), pd.DataFrame()))

            # Combine all OOS trades (2016-2026)
            all_oos_trades = []
            for sp_name in ["VALIDATION", "OOS_1", "OOS_2", "FINAL_UNTOUCHED_OOS"]:
                if sp_name in multi_split_res and not multi_split_res[sp_name][1].empty:
                    all_oos_trades.append(multi_split_res[sp_name][1])

            combined_oos_trades_df = pd.concat(all_oos_trades, ignore_index=True) if all_oos_trades else pd.DataFrame()
            combined_oos_summary = MetricsCalculator.calculate_summary(combined_oos_trades_df)

            # Rolling Walk Forward
            wfo_res = val_engine.run_rolling_walk_forward(strat_cls, df, train_years=3, test_years=1)
            avg_wfe = float(np.mean([w.wfe_ratio for w in wfo_res])) if wfo_res else 0.0

            # Cost Stress Testing on full dataset
            cost_stress = robustness_engine.run_cost_stress_test(strat, df)

            # Monte Carlo on full trade sample
            _, all_trades_df = RealisticBacktester(pair).run_backtest(df, strat.generate_signals(df))
            mc_report = mc_engine.run_simulation(all_trades_df)

            # Acceptance Criteria Check
            # 1. Positive OOS expectancy after costs
            # 2. OOS Profit factor > 1.15
            # 3. Survives +50% cost stress
            # 4. Total trades >= 40
            cost_50_ok = any(c.cost_multiplier == 1.5 and c.is_profitable for c in cost_stress)
            is_accepted = (
                combined_oos_summary.expectancy_r > 0.08
                and combined_oos_summary.profit_factor >= 1.20
                and combined_oos_summary.total_trades >= 40
                and cost_50_ok
            )
            status_str = "ACCEPTED_CANDIDATE" if is_accepted else ("REJECTED_COST_FRAGILE" if not cost_50_ok else "REJECTED_LOW_EXPECTANCY")

            # Save Scorecard
            exp_id = catalog.save_experiment_scorecard(
                strategy_name=strat_code,
                symbol=pair,
                timeframe=PRIMARY_TIMEFRAME,
                parameters=strat.params,
                is_summary=is_summary.__dict__,
                oos_summary=combined_oos_summary.__dict__,
                wfo_summary={"avg_wfe_ratio": avg_wfe, "windows_count": len(wfo_res)},
                cost_stress_summary=[c.__dict__ for c in cost_stress],
                monte_carlo_summary=mc_report.__dict__,
                acceptance_status=status_str,
            )

            res_entry = {
                "pair": pair,
                "strategy": strat_code,
                "is_trades": is_summary.total_trades,
                "is_exp_r": is_summary.expectancy_r,
                "is_pf": is_summary.profit_factor,
                "oos_trades": combined_oos_summary.total_trades,
                "oos_exp_r": combined_oos_summary.expectancy_r,
                "oos_pf": combined_oos_summary.profit_factor,
                "oos_winrate": combined_oos_summary.win_rate_pct,
                "oos_max_dd": combined_oos_summary.max_drawdown_pct,
                "wfe": avg_wfe,
                "p95_dd": mc_report.p95_max_dd_pct,
                "status": status_str,
                "trades_df": all_trades_df,
                "strat_obj": strat,
            }
            all_strategy_results[f"{pair}_{strat_code}"] = res_entry
            if is_accepted or combined_oos_summary.expectancy_r > 0.05:
                best_candidates.append(res_entry)

    # ----------------------------------------------------
    # Display Results Table
    # ----------------------------------------------------
    table = Table(title="Strategy Research & Chronological OOS Performance Matrix")
    table.add_column("Pair", style="cyan")
    table.add_column("Strategy", style="magenta")
    table.add_column("IS Exp(R)", justify="right")
    table.add_column("IS PF", justify="right")
    table.add_column("OOS Trades", justify="right")
    table.add_column("OOS Win%", justify="right")
    table.add_column("OOS Exp(R)", justify="right", style="bold")
    table.add_column("OOS PF", justify="right", style="bold")
    table.add_column("OOS MaxDD%", justify="right")
    table.add_column("WFE", justify="right")
    table.add_column("MC P95 DD%", justify="right")
    table.add_column("Status", style="bold")

    for k, r in all_strategy_results.items():
        status_color = "[green]" if "ACCEPTED" in r["status"] else "[red]"
        table.add_row(
            r["pair"],
            r["strategy"],
            f"{r['is_exp_r']:.3f}",
            f"{r['is_pf']:.2f}",
            str(r["oos_trades"]),
            f"{r['oos_winrate']:.1f}%",
            f"{r['oos_exp_r']:.3f}",
            f"{r['oos_pf']:.2f}",
            f"{r['oos_max_dd']:.1f}%",
            f"{r['wfe']:.2f}",
            f"{r['p95_dd']:.1f}%",
            f"{status_color}{r['status']}[/]",
        )
    console.print(table)

    # ----------------------------------------------------
    # Step 5: Cross-Pair Diversification & Correlation
    # ----------------------------------------------------
    console.print("\n[bold green]5. Cross-Pair Correlation & Portfolio Diversification Analysis...[/bold green]")
    best_pair_trades = {}
    for pair in pairs:
        # Pick top performing strategy for each pair
        pair_strats = [r for k, r in all_strategy_results.items() if r["pair"] == pair]
        if pair_strats:
            best_s = max(pair_strats, key=lambda x: x["oos_exp_r"])
            best_pair_trades[pair] = best_s["trades_df"]
            console.print(f"  -> Top strategy for [cyan]{pair}[/cyan]: [magenta]{best_s['strategy']}[/magenta] (OOS Exp: {best_s['oos_exp_r']:.3f} R, OOS PF: {best_s['oos_pf']:.2f})")

    if best_pair_trades:
        ref_df = next(iter(featured_datasets.values()))
        daily_mat = CrossPairAnalyzer.compute_daily_returns_matrix(best_pair_trades, ref_df.index)
        corr_df = CrossPairAnalyzer.calculate_correlation_matrix(daily_mat)
        console.print("\n[bold yellow]Pairwise Daily Strategy Return Correlation Matrix:[/bold yellow]")
        console.print(corr_df.round(3).to_string())

        port_summary, port_trades = CrossPairAnalyzer.calculate_portfolio_combined_metrics(best_pair_trades)
        console.print("\n[bold yellow]Multi-Pair Combined Portfolio Performance (EURUSD + GBPUSD + USDJPY):[/bold yellow]")
        console.print(f"  Total Trades: {port_summary.total_trades} | Win Rate: {port_summary.win_rate_pct:.1f}% | Net Pips: {port_summary.net_profit_pips:,.1f}")
        console.print(f"  Expectancy: {port_summary.expectancy_r:.3f} R | Profit Factor: {port_summary.profit_factor:.2f} | Max DD: {port_summary.max_drawdown_pct:.1f}% | Sharpe: {port_summary.sharpe_ratio:.2f}")

    # ----------------------------------------------------
    # Step 6: ML Meta-Labeling Filter on Top Candidate
    # ----------------------------------------------------
    console.print("\n[bold green]6. Machine Learning Supervised Meta-Labeling Quality Filter (XGBoost)...[/bold green]")
    if best_candidates:
        top_cand = max(best_candidates, key=lambda x: x["oos_exp_r"])
        top_pair = top_cand["pair"]
        top_strat = top_cand["strategy"]
        top_df = featured_datasets[top_pair]

        val_engine = ChronologicalValidationEngine(top_pair)
        split_dict = val_engine.split_dataset(top_df)
        df_train = split_dict.get("DEV_IN_SAMPLE", pd.DataFrame())
        df_test = pd.concat([split_dict[s] for s in ["VALIDATION", "OOS_1", "OOS_2"] if s in split_dict])

        strat_inst = top_cand["strat_obj"]
        backtester = RealisticBacktester(top_pair)
        train_trades, _ = backtester.run_backtest(df_train, strat_inst.generate_signals(df_train))
        test_trades, _ = backtester.run_backtest(df_test, strat_inst.generate_signals(df_test))

        ml_filter = MLTradeQualityFilter(top_pair, probability_threshold=0.52)
        ml_eval = ml_filter.train_and_evaluate_oos(df_train, train_trades, df_test, test_trades)

        console.print(f"  Target: [cyan]{top_pair}[/cyan] [magenta]{top_strat}[/magenta]")
        console.print(f"  In-Sample ROC-AUC: {ml_eval.is_roc_auc:.3f} | OOS ROC-AUC: {ml_eval.oos_roc_auc:.3f} | OOS PR-AUC: {ml_eval.oos_pr_auc:.3f}")
        console.print(f"  Baseline OOS: {ml_eval.baseline_oos_trades} trades, Exp: {ml_eval.baseline_oos_exp_r:.3f} R, PF: {ml_eval.baseline_oos_profit_factor:.2f}")
        console.print(f"  ML-Filtered OOS: {ml_eval.filtered_oos_trades} trades, Exp: {ml_eval.filtered_oos_exp_r:.3f} R, PF: {ml_eval.filtered_oos_profit_factor:.2f}")
        console.print(f"  Expectancy Uplift: [bold green]+{ml_eval.expectancy_uplift_r:.3f} R[/bold green]")

    console.rule("[bold cyan]Research Pipeline Run Completed[/bold cyan]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Systematic Forex Research Engine")
    parser.add_argument("--download", action="store_true", help="Download fresh historical data from MT5")
    args = parser.parse_args()

    run_full_pipeline(download_fresh=args.download)

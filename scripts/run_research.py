"""
Run audit, feature engineering, regime detection, and all 5 baseline strategies with full OOS metrics.
"""
import sys, logging
from pathlib import Path
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Pipeline")

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import CHRONOLOGICAL_SPLITS
from src.data_engine.validator import DataQualityAuditor
from src.feature_engine.features import FeatureEngine
from src.regime_engine.regimes import RegimeEngine
from src.strategy_engine.strategies import (
    TrendFollowingPullbackStrategy,
    VolatilityExpansionBreakoutStrategy,
    MeanReversionRangeStrategy,
    LondonSessionBreakoutStrategy,
    MarketStructureBOSStrategy,
)
from src.backtest_engine.backtester import RealisticBacktester
from src.backtest_engine.metrics import MetricsCalculator
from src.validation_engine.splits import ChronologicalValidationEngine
from src.robustness_engine.robustness import RobustnessEngine
from src.monte_carlo_engine.monte_carlo import MonteCarloEngine
from src.experiment_engine.scorecard import ExperimentCatalog

PAIRS = ["EURUSD", "GBPUSD", "USDJPY"]
STRATEGY_CLASSES = {
    "TF_PB": TrendFollowingPullbackStrategy,
    "VE_BO": VolatilityExpansionBreakoutStrategy,
    "MR_RG": MeanReversionRangeStrategy,
    "LDN_MO": LondonSessionBreakoutStrategy,
    "MS_BOS": MarketStructureBOSStrategy,
}

def main():
    auditor = DataQualityAuditor()
    all_audit = {}
    featured = {}

    # Step 1: Audit + Feature Engineering
    for pair in PAIRS:
        all_audit[pair] = {}
        for tf in ["M15", "H1"]:
            try:
                clean_df, rep = auditor.audit_dataset(pair, tf)
                all_audit[pair][tf] = rep
                logger.info(f"[AUDIT] {pair} {tf}: {rep['clean_bars_retained']:,} bars, gaps={rep['weekday_abnormal_gaps_detected']}, corrupted={rep['corrupted_bars_removed']}")
            except Exception as e:
                logger.error(f"[AUDIT] Error on {pair} {tf}: {e}")

        # Build features
        try:
            df_m15 = pd.read_parquet(f"data/clean/{pair}_M15_clean.parquet")
            df_h1_path = Path(f"data/clean/{pair}_H1_clean.parquet")
            df_h1 = pd.read_parquet(df_h1_path) if df_h1_path.exists() else None

            feat_eng = FeatureEngine(pair)
            df_feat = feat_eng.compute_all_features(df_m15, df_h1)
            df_reg = RegimeEngine().classify_regimes(df_feat)
            featured[pair] = df_reg
            logger.info(f"[FEATURES] {pair}: {len(df_reg):,} bars, {len(df_reg.columns)} features | Range: {df_reg.index[0].date()} to {df_reg.index[-1].date()}")
        except Exception as e:
            logger.error(f"[FEATURES] Error on {pair}: {e}")

    auditor.generate_markdown_report(all_audit)
    logger.info("[AUDIT] Data Quality Report saved -> data/quality_reports/DATA_QUALITY_AUDIT_REPORT.md")

    # Step 2: Strategy Backtest across Splits
    catalog = ExperimentCatalog()
    mc_engine = MonteCarloEngine(iterations=1000)
    
    results_rows = []

    for pair, df in featured.items():
        val_engine = ChronologicalValidationEngine(pair)
        rob_engine = RobustnessEngine(pair)
        backtester = RealisticBacktester(pair)

        for strat_code, strat_cls in STRATEGY_CLASSES.items():
            logger.info(f"\n[BACKTEST] {pair} -- {strat_code}")
            strat = strat_cls(pair)

            # Split-by-split results
            split_results = val_engine.run_multi_period_oos(strat, df)

            oos_dfs = []
            for sp_name, (summary, t_df) in split_results.items():
                if not t_df.empty:
                    oos_dfs.append(t_df)
                logger.info(f"  [{sp_name}] Trades={summary.total_trades}, WinRate={summary.win_rate_pct:.1f}%, Exp(R)={summary.expectancy_r:.3f}, PF={summary.profit_factor:.2f}, MaxDD={summary.max_drawdown_pct:.1f}%")

            # IS metrics
            is_summary, is_df = split_results.get("DEV_IN_SAMPLE", (MetricsCalculator.calculate_summary(pd.DataFrame()), pd.DataFrame()))

            # Combined OOS (non-IS)
            oos_dfs_nonis = [split_results[s][1] for s in ["VALIDATION", "OOS_1", "FINAL_UNTOUCHED_OOS"] if s in split_results and not split_results[s][1].empty]
            combined_oos_df = pd.concat(oos_dfs_nonis, ignore_index=True) if oos_dfs_nonis else pd.DataFrame()
            oos_summary = MetricsCalculator.calculate_summary(combined_oos_df)

            # Cost stress on combined OOS
            stress = rob_engine.run_cost_stress_test(strat, df)
            stress_50pct_ok = any(c.cost_multiplier == 1.5 and c.is_profitable for c in stress)

            # Monte Carlo on full dataset
            all_sigs = strat.generate_signals(df)
            _, all_trades_df = backtester.run_backtest(df, all_sigs)
            mc_report = mc_engine.run_simulation(all_trades_df)

            accepted = (
                oos_summary.expectancy_r > 0.05
                and oos_summary.profit_factor >= 1.10
                and oos_summary.total_trades >= 20
                and stress_50pct_ok
            )
            status = "ACCEPTED" if accepted else "REJECTED"

            logger.info(f"  [COMBINED OOS] Trades={oos_summary.total_trades}, Exp(R)={oos_summary.expectancy_r:.3f}, PF={oos_summary.profit_factor:.2f}, DD={oos_summary.max_drawdown_pct:.1f}% | MC P95DD={mc_report.p95_max_dd_pct:.1f}% | Status={status}")

            results_rows.append({
                "Pair": pair,
                "Strategy": strat_code,
                "IS_Trades": is_summary.total_trades,
                "IS_Exp_R": round(is_summary.expectancy_r, 3),
                "IS_PF": round(is_summary.profit_factor, 2),
                "OOS_Trades": oos_summary.total_trades,
                "OOS_WinRate%": round(oos_summary.win_rate_pct, 1),
                "OOS_Exp_R": round(oos_summary.expectancy_r, 3),
                "OOS_PF": round(oos_summary.profit_factor, 2),
                "OOS_MaxDD%": round(oos_summary.max_drawdown_pct, 1),
                "MC_P95_DD%": round(mc_report.p95_max_dd_pct, 1),
                "Cost50%_OK": stress_50pct_ok,
                "Status": status,
            })

            catalog.save_experiment_scorecard(
                strategy_name=strat_code, symbol=pair, timeframe="M15",
                parameters=strat.params,
                is_summary=is_summary.__dict__,
                oos_summary=oos_summary.__dict__,
                cost_stress_summary=[c.__dict__ for c in stress],
                monte_carlo_summary=mc_report.__dict__,
                acceptance_status=status,
            )

    # Step 3: Print Summary Table
    results_df = pd.DataFrame(results_rows)
    print("\n" + "="*130)
    print("STRATEGY RESEARCH RESULTS — Chronological OOS Performance")
    print("="*130)
    print(results_df.to_string(index=False))
    print("="*130)

    accepted = results_df[results_df["Status"] == "ACCEPTED"]
    print(f"\nAccepted Candidates: {len(accepted)} / {len(results_df)}")
    if not accepted.empty:
        print(accepted[["Pair","Strategy","OOS_Trades","OOS_Exp_R","OOS_PF","OOS_MaxDD%","MC_P95_DD%"]].to_string(index=False))

    results_df.to_csv("experiments/research_summary.csv", index=False)
    logger.info("Results saved -> experiments/research_summary.csv")

if __name__ == "__main__":
    main()

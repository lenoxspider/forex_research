"""
Machine Learning Trade-Quality Meta-Labeling Filter.
Trains an XGBoost classifier strictly on candidate trade feature vectors to predict win probability
and filters out low-expectancy trade setups out-of-sample.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
import xgboost as xgb

from src.strategy_engine.strategies import TradeSignal
from src.backtest_engine.backtester import RealisticBacktester, ExecutedTrade
from src.backtest_engine.metrics import MetricsCalculator, PerformanceSummary


@dataclass
class MLFilterEvaluation:
    is_roc_auc: float
    is_pr_auc: float
    oos_roc_auc: float
    oos_pr_auc: float
    oos_brier_score: float
    baseline_oos_trades: int
    baseline_oos_exp_r: float
    baseline_oos_profit_factor: float
    filtered_oos_trades: int
    filtered_oos_exp_r: float
    filtered_oos_profit_factor: float
    expectancy_uplift_r: float
    probability_threshold: float


class MLTradeQualityFilter:
    """Supervised meta-labeler for candidate trade quality filtering."""

    FEATURE_COLS = [
        "atr_14", "atr_pips", "atr_ratio_14_50", "atr_percentile_200", "realized_vol_20",
        "adx_14", "plus_di_14", "minus_di_14", "rsi_14", "bb_width", "bb_pct",
        "ema_20_slope_5", "ema_50_slope_5", "dist_to_swing_high_20_pips", "dist_to_swing_low_20_pips",
        "candle_body_ratio", "upper_wick_ratio", "lower_wick_ratio", "hour_utc", "day_of_week",
    ]

    def __init__(self, symbol: str, probability_threshold: float = 0.52):
        self.symbol = symbol
        self.prob_threshold = probability_threshold
        self.model: Optional[xgb.XGBClassifier] = None

    def extract_trade_features_and_labels(
        self,
        df: pd.DataFrame,
        executed_trades: List[ExecutedTrade],
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """Aligns executed trades with features at the time of the signal."""
        if not executed_trades:
            return pd.DataFrame(), np.array([])

        feature_rows = []
        labels = []

        for t in executed_trades:
            sig_time = t.signal_time
            if sig_time in df.index:
                row = df.loc[sig_time]
                feat_dict = {}
                for col in self.FEATURE_COLS:
                    feat_dict[col] = float(row[col]) if col in row else 0.0
                feat_dict["direction"] = t.direction
                feature_rows.append(feat_dict)
                labels.append(1 if t.pnl_net_pips > 0 else 0)

        X = pd.DataFrame(feature_rows)
        y = np.array(labels)
        return X, y

    def train_and_evaluate_oos(
        self,
        df_train: pd.DataFrame,
        train_trades: List[ExecutedTrade],
        df_test: pd.DataFrame,
        test_trades: List[ExecutedTrade],
    ) -> MLFilterEvaluation:
        X_train, y_train = self.extract_trade_features_and_labels(df_train, train_trades)
        X_test, y_test = self.extract_trade_features_and_labels(df_test, test_trades)

        if len(X_train) < 30 or len(X_test) < 20 or len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
            return MLFilterEvaluation(
                is_roc_auc=0.5, is_pr_auc=0.5, oos_roc_auc=0.5, oos_pr_auc=0.5, oos_brier_score=0.25,
                baseline_oos_trades=len(test_trades), baseline_oos_exp_r=0.0, baseline_oos_profit_factor=0.0,
                filtered_oos_trades=0, filtered_oos_exp_r=0.0, filtered_oos_profit_factor=0.0,
                expectancy_uplift_r=0.0, probability_threshold=self.prob_threshold,
            )

        # Train XGBoost Meta-Model
        self.model = xgb.XGBClassifier(
            n_estimators=60,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            random_state=42,
        )
        self.model.fit(X_train, y_train)

        # In-sample metrics
        train_probs = self.model.predict_proba(X_train)[:, 1]
        is_auc = float(roc_auc_score(y_train, train_probs))
        is_pr = float(average_precision_score(y_train, train_probs))

        # Out-of-sample metrics
        test_probs = self.model.predict_proba(X_test)[:, 1]
        oos_auc = float(roc_auc_score(y_test, test_probs))
        oos_pr = float(average_precision_score(y_test, test_probs))
        oos_brier = float(brier_score_loss(y_test, test_probs))

        # Filter OOS Trades
        filtered_test_trades = [
            test_trades[i] for i in range(len(test_trades)) if test_probs[i] >= self.prob_threshold
        ]

        # Calculate summaries
        baseline_summary = MetricsCalculator.calculate_summary(pd.DataFrame([t.__dict__ for t in test_trades]))
        filtered_summary = MetricsCalculator.calculate_summary(pd.DataFrame([t.__dict__ for t in filtered_test_trades]))

        uplift = filtered_summary.expectancy_r - baseline_summary.expectancy_r

        return MLFilterEvaluation(
            is_roc_auc=round(is_auc, 3),
            is_pr_auc=round(is_pr, 3),
            oos_roc_auc=round(oos_auc, 3),
            oos_pr_auc=round(oos_pr, 3),
            oos_brier_score=round(oos_brier, 3),
            baseline_oos_trades=baseline_summary.total_trades,
            baseline_oos_exp_r=baseline_summary.expectancy_r,
            baseline_oos_profit_factor=baseline_summary.profit_factor,
            filtered_oos_trades=filtered_summary.total_trades,
            filtered_oos_exp_r=filtered_summary.expectancy_r,
            filtered_oos_profit_factor=filtered_summary.profit_factor,
            expectancy_uplift_r=round(uplift, 3),
            probability_threshold=self.prob_threshold,
        )

"""
Research Scorecard & Experiment Catalog Engine.
Maintains persistent JSON/SQLite logs of all research runs, IS/OOS metrics, Walk-Forward,
Monte Carlo, and Cost Stress results for rigorous quantitative tracking.
"""
import json
import sqlite3
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd

from config.settings import EXPERIMENTS_DIR


class ExperimentCatalog:
    """Manages experiment records and automated research scorecards."""

    def __init__(self, db_dir: Path = EXPERIMENTS_DIR):
        self.db_dir = db_dir
        self.db_path = self.db_dir / "experiments_registry.db"
        self.json_dir = self.db_dir / "scorecards"
        self.json_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    strategy_name TEXT,
                    symbol TEXT,
                    timeframe TEXT,
                    is_trades INTEGER,
                    is_expectancy_r REAL,
                    is_profit_factor REAL,
                    oos_trades INTEGER,
                    oos_expectancy_r REAL,
                    oos_profit_factor REAL,
                    oos_max_dd_pct REAL,
                    wfe_ratio REAL,
                    cost_stress_2x_profitable INTEGER,
                    monte_carlo_p95_dd REAL,
                    acceptance_status TEXT
                )
            """)
            conn.commit()

    def save_experiment_scorecard(
        self,
        strategy_name: str,
        symbol: str,
        timeframe: str,
        parameters: Dict[str, Any],
        is_summary: Dict[str, Any],
        oos_summary: Dict[str, Any],
        wfo_summary: Optional[Dict[str, Any]] = None,
        cost_stress_summary: Optional[List[Dict[str, Any]]] = None,
        monte_carlo_summary: Optional[Dict[str, Any]] = None,
        acceptance_status: str = "PENDING_REVIEW",
    ) -> str:
        exp_id = f"EXP_{symbol}_{strategy_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        record = {
            "experiment_id": exp_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategy_name": strategy_name,
            "symbol": symbol,
            "timeframe": timeframe,
            "parameters": parameters,
            "is_metrics": is_summary,
            "oos_metrics": oos_summary,
            "wfo_metrics": wfo_summary or {},
            "cost_stress_metrics": cost_stress_summary or [],
            "monte_carlo_metrics": monte_carlo_summary or {},
            "acceptance_status": acceptance_status,
        }

        # Save detailed JSON scorecard
        json_file = self.json_dir / f"{exp_id}.json"
        with open(json_file, "w") as f:
            json.dump(record, f, indent=2)

        # Insert summary row into SQLite
        cost_2x_ok = 0
        if cost_stress_summary:
            for c in cost_stress_summary:
                if c.get("cost_multiplier") == 2.0:
                    cost_2x_ok = 1 if c.get("is_profitable") else 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO experiments VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                exp_id,
                record["timestamp"],
                strategy_name,
                symbol,
                timeframe,
                is_summary.get("total_trades", 0),
                is_summary.get("expectancy_r", 0.0),
                is_summary.get("profit_factor", 0.0),
                oos_summary.get("total_trades", 0),
                oos_summary.get("expectancy_r", 0.0),
                oos_summary.get("profit_factor", 0.0),
                oos_summary.get("max_drawdown_pct", 0.0),
                (wfo_summary or {}).get("avg_wfe_ratio", 0.0),
                cost_2x_ok,
                (monte_carlo_summary or {}).get("p95_max_dd_pct", 0.0),
                acceptance_status,
            ))
            conn.commit()

        return exp_id

    def load_summary_table(self) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query("SELECT * FROM experiments ORDER BY timestamp DESC", conn)

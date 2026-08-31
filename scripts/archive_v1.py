"""
Archive of V1 Research Results.
Frozen on 2026-08-31 as immutable benchmarks: BASELINE_V1, EDGE_DISCOVERY_V1, CANDIDATE_VALIDATION_V1.
"""
import shutil
from pathlib import Path

V1_DIR = Path("experiments/v1_archive")
V1_DIR.mkdir(parents=True, exist_ok=True)

files_to_archive = [
    "baseline_v1_frozen.csv",
    "trade_mae_mfe_diagnostics.csv",
    "conditional_expectancy_all_factors.csv",
    "promising_conditions_ranked.csv",
    "controlled_optimization_results.csv",
    "research_summary.csv",
]

for fname in files_to_archive:
    src = Path("experiments") / fname
    if src.exists():
        shutil.copy(src, V1_DIR / fname)
        print(f"Archived {src} -> {V1_DIR / fname}")

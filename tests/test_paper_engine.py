"""
Tests for Production Candidate Freeze and Paper Execution Engine.
"""
import pytest
import pandas as pd
import numpy as np

from src.strategy_engine.production_candidate import ProductionFreezeCandidate, ProductionFreezeConfig
from src.execution_engine.paper_engine import PaperExecutionEngine
from src.execution_engine.drift_monitor import ExecutionDriftMonitor


def test_production_candidate_fingerprint():
    cand1 = ProductionFreezeCandidate("EURUSD")
    cand2 = ProductionFreezeCandidate("EURUSD")
    assert cand1.fingerprint == cand2.fingerprint
    assert len(cand1.fingerprint) == 64  # Valid SHA-256


def test_paper_engine_zero_live_order_risk():
    engine = PaperExecutionEngine(symbols=["EURUSD"], initial_capital_usd=100000.0)
    assert engine.virtual_balance == 100000.0
    assert engine.active_positions["EURUSD"] is None

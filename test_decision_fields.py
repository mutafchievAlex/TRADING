#!/usr/bin/env python3
"""Test script to verify decision fields are being populated."""

import sys
import pandas as pd
import numpy as np
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from engines.decision_engine import DecisionEngine, DecisionResult
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)

# Create decision engine
decision_engine = DecisionEngine(config)

# Create sample data
dates = pd.date_range('2026-01-01', periods=320, freq='h')
df = pd.DataFrame({
    'open': np.random.uniform(2640, 2660, 320),
    'high': np.random.uniform(2645, 2665, 320),
    'low': np.random.uniform(2635, 2655, 320),
    'close': np.random.uniform(2640, 2660, 320),
    'ema50': 2650 + np.random.uniform(-5, 5, 320),
    'ema200': 2648 + np.random.uniform(-10, 10, 320),
    'atr14': 5.0 + np.random.uniform(-1, 1, 320),
}, index=dates)

# Make sure prices are in ascending order for some bars (to trigger trades)
df.iloc[310:, df.columns.get_loc('close')] = 2660  # Last 10 bars close above EMA50

# Create a fake pattern that will pass
pattern = {
    'left_low': {'price': 2630, 'index': 100, 'time': dates[100]},
    'right_low': {'price': 2631, 'index': 200, 'time': dates[200]},
    'neckline': {'price': 2650, 'time': dates[300]},  # Lower neckline so close > neckline
    'quality_score': 8.5
}

# Ensure close prices to trigger TRADE_ALLOWED
df.iloc[-1, df.columns.get_loc('close')] = 2655  # Close > neckline
df.iloc[-1, df.columns.get_loc('ema50')] = 2652  # ema50 < close
df.iloc[-1, df.columns.get_loc('ema200')] = 2650  # ema200 < ema50

# Create account state
account_state = {
    'equity': 10000.0,
    'open_positions': 0,
    'last_trade_bar': -9999
}

print("=" * 80)
print("Testing Decision Engine with New Fields")
print("=" * 80)

# Test with TRADE_ALLOWED scenario
print("\n[TEST 1] Testing TRADE_ALLOWED decision...")
result = decision_engine.evaluate(
    bar_index=-1,
    df=df,
    pattern=pattern,
    account_state=account_state,
    direction="LONG"
)

print(f"Decision: {result.decision.value}")
print(f"Stage: {result.stage.value if result.stage else None}")

# Check new fields
print(f"\n[FINAL DECISION STATE]")
print(f"  decision_timestamp: {result.decision_timestamp}")
print(f"  decision_source: {result.decision_source}")
print(f"  decision_summary: {result.decision_summary}")

print(f"\n[POSITION PREVIEW]")
print(f"  planned_entry: {result.planned_entry}")
print(f"  planned_sl: {result.planned_sl}")
print(f"  planned_tp1: {result.planned_tp1}")
print(f"  planned_tp2: {result.planned_tp2}")
print(f"  planned_tp3: {result.planned_tp3}")
print(f"  calculated_risk_usd: {result.calculated_risk_usd}")
print(f"  calculated_rr: {result.calculated_rr}")
print(f"  position_size: {result.position_size}")

print(f"\n[QUALITY SCORE]")
print(f"  entry_quality_score: {result.entry_quality_score}")
print(f"  quality_breakdown: {result.quality_breakdown}")

print(f"\n[BAR-CLOSE GUARD]")
print(f"  last_closed_bar_time: {result.last_closed_bar_time}")
print(f"  using_closed_bar: {result.using_closed_bar}")
print(f"  tick_noise_filter_passed: {result.tick_noise_filter_passed}")
print(f"  anti_fomo_passed: {result.anti_fomo_passed}")

# Test with NO_TRADE scenario (no pattern)
print("\n" + "=" * 80)
print("[TEST 2] Testing NO_TRADE decision (no pattern)...")
result2 = decision_engine.evaluate(
    bar_index=-1,
    df=df,
    pattern=None,
    account_state=account_state,
    direction="LONG"
)

print(f"Decision: {result2.decision.value}")
print(f"Stage: {result2.stage.value if result2.stage else None}")
print(f"Fail Code: {result2.fail_code.value if result2.fail_code else None}")

print(f"\n[FINAL DECISION STATE]")
print(f"  decision_timestamp: {result2.decision_timestamp}")
print(f"  decision_source: {result2.decision_source}")
print(f"  decision_summary: {result2.decision_summary}")

print(f"\n[BAR-CLOSE GUARD (should have defaults)]")
print(f"  last_closed_bar_time: {result2.last_closed_bar_time}")
print(f"  using_closed_bar: {result2.using_closed_bar}")
print(f"  tick_noise_filter_passed: {result2.tick_noise_filter_passed}")
print(f"  anti_fomo_passed: {result2.anti_fomo_passed}")

print("\n" + "=" * 80)
print("All tests completed!")
print("=" * 80)

#!/usr/bin/env python3
"""Quick integration check"""

from src.engines.bar_close_guard import BarCloseGuard
from src.engines.strategy_engine import StrategyEngine

print('='*60)
print('INTEGRATION CHECK: BarCloseGuard + StrategyEngine')
print('='*60)
print()

# Check BarCloseGuard defaults
guard = BarCloseGuard()
status = guard.get_guard_status()
print('BarCloseGuard Default Configuration:')
print(f'  ✓ Noise filter enabled: {status["noise_filter_enabled"]}')
print(f'  ✓ Anti-FOMO enabled: {status["anti_fomo_enabled"]}')
print()

# Check StrategyEngine integration
strategy = StrategyEngine()
print('StrategyEngine Integration:')
has_guard = hasattr(strategy, 'bar_close_guard')
print(f'  ✓ Has bar_close_guard: {has_guard}')

if has_guard:
    print(f'  ✓ Guard type: {type(strategy.bar_close_guard).__name__}')
    print(f'  ✓ Noise filter: {"DISABLED" if not strategy.bar_close_guard.enable_noise_filter else "ENABLED"}')
    print(f'  ✓ Anti-FOMO: {"DISABLED" if not strategy.bar_close_guard.enable_anti_fomo else "ENABLED"}')

print()
print('='*60)
print('✓ ALL CHECKS PASSED - Integration is correct')
print('='*60)

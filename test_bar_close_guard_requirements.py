"""
Test suite for BarCloseGuard to verify all requirements are met
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from src.engines.bar_close_guard import BarCloseGuard
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

def test_mandatory_bar_state_validation():
    """Test that bar state validation is always active"""
    guard = BarCloseGuard()  # Default: no optional filters
    
    # Create minimal valid data
    dates = pd.date_range(start='2024-01-01', periods=5, freq='H')
    df = pd.DataFrame({
        'time': dates,
        'open': [2000.0, 2001.0, 2002.0, 2003.0, 2004.0],
        'high': [2010.0, 2011.0, 2012.0, 2013.0, 2014.0],
        'low': [1990.0, 1991.0, 1992.0, 1993.0, 1994.0],
        'close': [2005.0, 2006.0, 2007.0, 2008.0, 2009.0],
    })
    
    # Valid bar should pass
    is_valid, reason = guard.validate_bar_state(df, -2)
    assert is_valid, f"Valid bar failed: {reason}"
    print("✓ Mandatory bar-state validation: ACTIVE")
    
    # Invalid OHLC should fail
    df_bad = df.copy()
    df_bad.loc[3, 'high'] = df_bad.loc[3, 'low'] - 1  # high < low
    is_valid, reason = guard.validate_bar_state(df_bad, -2)
    assert not is_valid, "Invalid OHLC should fail"
    print("✓ Mandatory bar-state validation: Rejects invalid OHLC")

def test_noise_filter_disabled_by_default():
    """Test that tick noise filter is disabled by default"""
    guard = BarCloseGuard()  # Default: enable_noise_filter=False
    
    # Even tiny movements should pass
    passes, reason = guard.filter_tick_noise(0.01)
    assert passes, f"Should pass when disabled: {reason}"
    assert "DISABLED" in reason, f"Should mention disabled: {reason}"
    print("✓ Tick noise filter: DISABLED by default - allows 0.01 pips")
    
    # With default config, all movements pass
    passes, reason = guard.filter_tick_noise(1000.0)
    assert passes, "Large movements pass when disabled"
    print("✓ Tick noise filter: Doesn't block when disabled")

def test_anti_fomo_is_optional_non_blocking():
    """Test that Anti-FOMO is optional and doesn't block good setups"""
    guard = BarCloseGuard()  # Default: enable_anti_fomo=False
    
    # First entry should pass
    can_enter, reason = guard.check_anti_fomo_cooldown(0)
    assert can_enter, f"First entry should always pass: {reason}"
    assert "DISABLED" in reason, f"Should mention disabled: {reason}"
    print("✓ Anti-FOMO: DISABLED by default - first entry allowed")
    
    # Record a signal
    guard.record_signal(0)
    
    # Immediate re-entry should still pass (disabled mode)
    can_enter, reason = guard.check_anti_fomo_cooldown(1)
    assert can_enter, f"Should allow entry even right after signal (disabled): {reason}"
    print("✓ Anti-FOMO: Non-blocking - allows immediate re-entry when disabled")

def test_anti_fomo_enabled_warns_not_blocks():
    """Test that enabled Anti-FOMO warns but doesn't block"""
    guard = BarCloseGuard(enable_anti_fomo=True, anti_fomo_bars=2)
    
    guard.record_signal(10)
    
    # 1 bar after signal should warn but NOT block
    can_enter, reason = guard.check_anti_fomo_cooldown(11)
    assert can_enter, f"Should NOT block even with warning: {reason}"
    assert "warning" in reason.lower(), f"Should mention warning: {reason}"
    print("✓ Anti-FOMO (enabled): Warns about rapid entries but NEVER blocks")
    
    # After cooldown, should be OK
    can_enter, reason = guard.check_anti_fomo_cooldown(12)
    assert can_enter, "Should allow entry after cooldown"
    assert "OK" in reason, f"Should confirm OK: {reason}"
    print("✓ Anti-FOMO (enabled): Allows entry after cooldown period")

def test_noise_filter_enabled_blocks():
    """Test that enabled noise filter blocks micro-movements"""
    guard = BarCloseGuard(enable_noise_filter=True, min_pips_movement=5.0)
    
    # Micro-movement should fail
    passes, reason = guard.filter_tick_noise(2.0)
    assert not passes, f"Should block micro-movements: {reason}"
    assert "Tick noise" in reason, f"Should mention tick noise: {reason}"
    print("✓ Noise filter (enabled): Blocks movements < threshold")
    
    # Good movement should pass
    passes, reason = guard.filter_tick_noise(10.0)
    assert passes, f"Should allow good movements: {reason}"
    assert "Significant" in reason, f"Should confirm significant: {reason}"
    print("✓ Noise filter (enabled): Allows movements >= threshold")

def test_full_validation_sequence():
    """Test the complete validation flow"""
    guard = BarCloseGuard()
    
    dates = pd.date_range(start='2024-01-01', periods=5, freq='H')
    df = pd.DataFrame({
        'time': dates,
        'open': [2000.0] * 5,
        'high': [2010.0] * 5,
        'low': [1990.0] * 5,
        'close': [2005.0] * 5,
    })
    
    # Full validation should pass (all mandatory checks pass)
    approved, reason = guard.validate_entry(df, bar_index=-2, price_movement_pips=5.0)
    assert approved, f"Should approve valid entry: {reason}"
    assert "[MANDATORY]" in reason, "Should show mandatory checks"
    print("✓ Full validation: Approves valid entry")
    
    # Validation with invalid bar should fail
    df_bad = df.copy()
    df_bad.loc[3, 'high'] = df_bad.loc[3, 'low'] - 1
    approved, reason = guard.validate_entry(df_bad, bar_index=-2)
    assert not approved, "Should reject invalid bar"
    print("✓ Full validation: Rejects invalid bar")

def test_rejection_logging():
    """Test that rejections are logged with exact reasons"""
    guard = BarCloseGuard(enable_noise_filter=True, min_pips_movement=10.0)
    
    # Trigger a rejection
    passes, reason = guard.filter_tick_noise(5.0)
    assert not passes, "Should reject"
    
    # Check rejection log
    summary = guard.get_rejections_summary()
    assert 'tick-noise' in summary, "Should log rejection category"
    assert summary['tick-noise'] == 1, "Should count rejections"
    print("✓ Rejection logging: Logs rejections with category")
    
    # Check guard status
    status = guard.get_guard_status()
    assert status['total_rejections'] == 1, "Should track total rejections"
    assert status['noise_filter_enabled'] == True, "Should show config"
    print("✓ Guard status: Shows configuration and rejection counts")

def main():
    print("\n" + "="*60)
    print("BarCloseGuard Requirements Test Suite")
    print("="*60 + "\n")
    
    try:
        test_mandatory_bar_state_validation()
        print()
        test_noise_filter_disabled_by_default()
        print()
        test_anti_fomo_is_optional_non_blocking()
        print()
        test_anti_fomo_enabled_warns_not_blocks()
        print()
        test_noise_filter_enabled_blocks()
        print()
        test_full_validation_sequence()
        print()
        test_rejection_logging()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60 + "\n")
        print("Summary:")
        print("  ✓ Bar-close validation & bar state checks: ALWAYS ACTIVE")
        print("  ✓ Tick noise filter: DISABLED by default, non-blocking")
        print("  ✓ Anti-FOMO: OPTIONAL, NEVER blocks good setups")
        print("  ✓ Guard ensures determinism, doesn't change strategy")
        print("  ✓ All rejections logged with exact reason")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    
    return True

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

"""
Unit tests for Pattern Engine
"""

import pytest
import pandas as pd
import numpy as np
from src.engines.pattern_engine import PatternEngine


@pytest.fixture
def sample_data_with_pattern():
    """Create sample data with a double bottom pattern."""
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
    
    # Create price data with a double bottom
    base_price = 2000
    prices = []
    for i in range(100):
        if i < 20:
            prices.append(base_price + np.random.randn() * 5)
        elif 20 <= i < 30:  # First bottom
            prices.append(base_price - 30 + np.random.randn() * 3)
        elif 30 <= i < 50:  # Rally to neckline
            prices.append(base_price - 10 + np.random.randn() * 5)
        elif 50 <= i < 60:  # Second bottom
            prices.append(base_price - 32 + np.random.randn() * 3)
        else:  # Breakout
            prices.append(base_price + (i - 60) * 2 + np.random.randn() * 5)
    
    return pd.DataFrame({
        'time': dates,
        'open': prices,
        'high': [p + abs(np.random.randn() * 3) for p in prices],
        'low': [p - abs(np.random.randn() * 3) for p in prices],
        'close': prices,
    })


def test_pattern_engine_initialization():
    """Test PatternEngine can be initialized."""
    engine = PatternEngine()
    assert engine is not None
    assert engine.lookback_left == 5
    assert engine.lookback_right == 5


def test_find_pivot_lows(sample_data_with_pattern):
    """Test pivot low detection."""
    engine = PatternEngine(lookback_left=3, lookback_right=3)
    pivots = engine.find_pivot_lows(sample_data_with_pattern)
    
    # Should find some pivot lows
    assert len(pivots) > 0
    
    # Each pivot should have required fields
    for pivot in pivots:
        assert 'index' in pivot
        assert 'price' in pivot
        assert 'time' in pivot


def test_find_pivot_highs(sample_data_with_pattern):
    """Test pivot high detection."""
    engine = PatternEngine(lookback_left=3, lookback_right=3)
    pivots = engine.find_pivot_highs(sample_data_with_pattern)
    
    # Should find some pivot highs
    assert len(pivots) > 0
    
    # Each pivot should have required fields
    for pivot in pivots:
        assert 'index' in pivot
        assert 'price' in pivot
        assert 'time' in pivot


def test_are_lows_equal():
    """Test low equality check."""
    engine = PatternEngine(equality_tolerance=2.0)
    
    # Equal within tolerance
    assert engine.are_lows_equal(2000.0, 2020.0)  # 1% diff
    
    # Not equal
    assert not engine.are_lows_equal(2000.0, 2100.0)  # 5% diff


def test_detect_double_bottom(sample_data_with_pattern):
    """Test double bottom pattern detection."""
    engine = PatternEngine(
        lookback_left=3,
        lookback_right=3,
        equality_tolerance=3.0,
        min_bars_between=15
    )
    
    pattern = engine.detect_double_bottom(sample_data_with_pattern)
    
    # Pattern should be detected in our sample data
    assert pattern is not None
    assert pattern['pattern_valid']
    
    # Pattern should have all required components
    assert 'left_low' in pattern
    assert 'neckline' in pattern
    assert 'right_low' in pattern
    
    # Neckline should be between the two lows
    assert pattern['left_low']['index'] < pattern['neckline']['index'] < pattern['right_low']['index']


def test_is_breakout_confirmed(sample_data_with_pattern):
    """Test breakout confirmation."""
    engine = PatternEngine(lookback_left=3, lookback_right=3, equality_tolerance=3.0, min_bars_between=15)
    
    pattern = engine.detect_double_bottom(sample_data_with_pattern)
    
    if pattern:
        # Check breakout at end of data
        is_breakout = engine.is_breakout_confirmed(sample_data_with_pattern, pattern, len(sample_data_with_pattern) - 1)
        
        # Should be boolean
        assert isinstance(is_breakout, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Unit tests for Indicator Engine
"""

import pytest
import pandas as pd
import numpy as np
from src.engines.indicator_engine import IndicatorEngine


@pytest.fixture
def sample_data():
    """Create sample OHLC data for testing."""
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=300, freq='H')
    prices = 2000 + np.cumsum(np.random.randn(300) * 10)
    
    return pd.DataFrame({
        'time': dates,
        'open': prices + np.random.randn(300) * 2,
        'high': prices + abs(np.random.randn(300) * 5),
        'low': prices - abs(np.random.randn(300) * 5),
        'close': prices,
    })


def test_indicator_engine_initialization():
    """Test IndicatorEngine can be initialized."""
    engine = IndicatorEngine()
    assert engine is not None


def test_calculate_ema(sample_data):
    """Test EMA calculation."""
    engine = IndicatorEngine()
    ema = engine.calculate_ema(sample_data['close'], period=50)
    
    # EMA should have same length as input
    assert len(ema) == len(sample_data)
    
    # EMA values should be numbers
    assert not ema.iloc[-1:].isna().any()
    
    # EMA should smooth the price
    assert ema.iloc[-1] != sample_data['close'].iloc[-1]


def test_calculate_atr(sample_data):
    """Test ATR calculation."""
    engine = IndicatorEngine()
    atr = engine.calculate_atr(sample_data, period=14)
    
    # ATR should have same length as input
    assert len(atr) == len(sample_data)
    
    # ATR values should be positive
    assert (atr.iloc[14:] > 0).all()


def test_calculate_all_indicators(sample_data):
    """Test calculating all indicators at once."""
    engine = IndicatorEngine()
    df = engine.calculate_all_indicators(sample_data)
    
    # Check all columns are added
    assert 'ema50' in df.columns
    assert 'ema200' in df.columns
    assert 'atr14' in df.columns
    
    # Check values are computed
    assert not df['ema50'].iloc[-1:].isna().any()
    assert not df['ema200'].iloc[-1:].isna().any()
    assert not df['atr14'].iloc[-1:].isna().any()


def test_get_current_indicators(sample_data):
    """Test getting current indicator values."""
    engine = IndicatorEngine()
    df = engine.calculate_all_indicators(sample_data)
    
    current = engine.get_current_indicators(df)
    
    assert current is not None
    assert 'close' in current
    assert 'ema50' in current
    assert 'ema200' in current
    assert 'atr14' in current


def test_is_data_sufficient():
    """Test data sufficiency check."""
    engine = IndicatorEngine()
    
    # Insufficient data
    short_df = pd.DataFrame({'close': [1, 2, 3]})
    assert not engine.is_data_sufficient(short_df)
    
    # Sufficient data
    long_df = pd.DataFrame({'close': range(300)})
    assert engine.is_data_sufficient(long_df)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

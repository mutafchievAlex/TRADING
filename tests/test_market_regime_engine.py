"""
Test suite for Market Regime Engine

Tests regime detection, confidence calculation, and edge cases.
"""

import sys
import pytest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.engines.market_regime_engine import MarketRegimeEngine, RegimeType


class TestMarketRegimeEngine:
    """Test cases for MarketRegimeEngine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = MarketRegimeEngine(min_ema_distance_percent=0.1)
    
    # BULL Regime Tests
    def test_bull_regime_detection(self):
        """Test BULL regime when close > ema50 > ema200."""
        regime, confidence = self.engine.evaluate(
            close=2000.0,
            ema50=1990.0,
            ema200=1950.0
        )
        assert regime == RegimeType.BULL
        assert confidence > 0.0
        assert confidence <= 1.0
    
    def test_bull_regime_high_confidence(self):
        """Test high confidence in strong BULL market."""
        regime, confidence = self.engine.evaluate(
            close=2100.0,  # Strong above EMA50
            ema50=1990.0,  # EMA50 well above EMA200
            ema200=1900.0  # Large separation
        )
        assert regime == RegimeType.BULL
        assert confidence >= 0.5  # Should have decent confidence
    
    def test_bull_regime_low_confidence(self):
        """Test low confidence when EMA separation is small."""
        regime, confidence = self.engine.evaluate(
            close=2005.0,  # Just barely above EMA50
            ema50=2003.0,  # Just above EMA200
            ema200=2001.0  # Very close together
        )
        assert regime == RegimeType.BULL
        assert confidence >= 0.0  # Some confidence
    
    # BEAR Regime Tests
    def test_bear_regime_detection(self):
        """Test BEAR regime when close < ema50 < ema200."""
        regime, confidence = self.engine.evaluate(
            close=1900.0,
            ema50=1910.0,
            ema200=1950.0
        )
        assert regime == RegimeType.BEAR
        assert confidence > 0.0
        assert confidence <= 1.0
    
    def test_bear_regime_high_confidence(self):
        """Test high confidence in strong BEAR market."""
        regime, confidence = self.engine.evaluate(
            close=1800.0,  # Strong below EMA50
            ema50=1910.0,  # EMA50 well below EMA200
            ema200=2000.0  # Large separation
        )
        assert regime == RegimeType.BEAR
        assert confidence >= 0.5  # Should have decent confidence
    
    # RANGE Regime Tests
    def test_range_regime_price_above_ema_but_ema_inverted(self):
        """Test RANGE when price > ema50 but ema50 < ema200."""
        regime, confidence = self.engine.evaluate(
            close=2000.0,   # Above EMA50
            ema50=1990.0,   # Below EMA200
            ema200=2010.0   # Above EMA50
        )
        assert regime == RegimeType.RANGE
        assert confidence == 0.0
    
    def test_range_regime_price_below_ema_but_ema_normal(self):
        """Test RANGE when price < ema50 but ema50 > ema200."""
        regime, confidence = self.engine.evaluate(
            close=1900.0,   # Below EMA50
            ema50=2010.0,   # Above EMA200
            ema200=1950.0   # Below EMA50
        )
        assert regime == RegimeType.RANGE
        assert confidence == 0.0
    
    def test_range_regime_all_equal(self):
        """Test RANGE when price and EMAs are very close."""
        regime, confidence = self.engine.evaluate(
            close=2000.0,
            ema50=2000.5,
            ema200=2000.0
        )
        assert regime == RegimeType.RANGE
        assert confidence == 0.0
    
    # Metrics Tests
    def test_ema_distance_calculation(self):
        """Test EMA distance is calculated correctly."""
        self.engine.evaluate(
            close=2000.0,
            ema50=1980.0,
            ema200=1900.0
        )
        # (1980 - 1900) / 1900 * 100 = 4.21%
        assert abs(self.engine.ema50_ema200_distance - 4.21) < 0.1
    
    def test_price_distance_calculation(self):
        """Test price distance is calculated correctly."""
        self.engine.evaluate(
            close=2100.0,
            ema50=2000.0,
            ema200=1950.0
        )
        # (2100 - 2000) / 2000 * 100 = 5.0%
        assert abs(self.engine.price_ema50_distance - 5.0) < 0.1
    
    def test_negative_ema_distance(self):
        """Test negative EMA distance when EMA50 < EMA200."""
        self.engine.evaluate(
            close=1900.0,
            ema50=1910.0,
            ema200=1950.0
        )
        # (1910 - 1950) / 1950 * 100 = -2.05%
        assert self.engine.ema50_ema200_distance < 0
    
    def test_negative_price_distance(self):
        """Test negative price distance when price < EMA50."""
        self.engine.evaluate(
            close=1800.0,
            ema50=2000.0,
            ema200=1950.0
        )
        # (1800 - 2000) / 2000 * 100 = -10%
        assert self.engine.price_ema50_distance < 0
    
    # State Retrieval Tests
    def test_get_state_returns_all_fields(self):
        """Test get_state returns complete regime state."""
        self.engine.evaluate(close=2000.0, ema50=1990.0, ema200=1950.0)
        state = self.engine.get_state()
        
        assert 'regime' in state
        assert 'confidence' in state
        assert 'ema50_ema200_distance' in state
        assert 'price_ema50_distance' in state
    
    def test_get_state_values_match_engine(self):
        """Test get_state values match engine properties."""
        self.engine.evaluate(close=2000.0, ema50=1990.0, ema200=1950.0)
        state = self.engine.get_state()
        
        assert state['regime'] == self.engine.current_regime.value
        assert state['confidence'] == self.engine.confidence
        assert state['ema50_ema200_distance'] == self.engine.ema50_ema200_distance
        assert state['price_ema50_distance'] == self.engine.price_ema50_distance
    
    # Edge Cases
    def test_handles_zero_ema200(self):
        """Test graceful handling when EMA200 is zero."""
        regime, confidence = self.engine.evaluate(
            close=2000.0,
            ema50=1990.0,
            ema200=0.0
        )
        # Should not crash, should set RANGE and 0 confidence
        assert regime == RegimeType.RANGE
        assert confidence == 0.0
    
    def test_handles_zero_ema50(self):
        """Test graceful handling when EMA50 is zero."""
        regime, confidence = self.engine.evaluate(
            close=2000.0,
            ema50=0.0,
            ema200=1950.0
        )
        # Should not crash, should set RANGE and 0 confidence
        assert regime == RegimeType.RANGE
        assert confidence == 0.0
    
    def test_handles_negative_values(self):
        """Test handling of negative price values (edge case)."""
        # Should still work mathematically
        regime, confidence = self.engine.evaluate(
            close=-100.0,
            ema50=-110.0,
            ema200=-200.0
        )
        # -100 > -110 > -200, so should be BULL
        assert regime == RegimeType.BULL
    
    def test_handles_very_large_values(self):
        """Test handling of very large values."""
        regime, confidence = self.engine.evaluate(
            close=999999.0,
            ema50=999900.0,
            ema200=999000.0
        )
        assert regime == RegimeType.BULL
    
    def test_confidence_bounded(self):
        """Test confidence never exceeds 1.0."""
        # Test with extreme separation
        regime, confidence = self.engine.evaluate(
            close=10000.0,   # Huge price
            ema50=1000.0,    # Huge distance from price
            ema200=100.0     # Huge separation from ema50
        )
        assert confidence <= 1.0
    
    # Persistence Tests
    def test_state_persists_between_calls(self):
        """Test state remains valid between evaluations."""
        # First evaluation
        self.engine.evaluate(close=2000.0, ema50=1990.0, ema200=1950.0)
        state1 = self.engine.get_state()
        
        # Same evaluation should give same state
        self.engine.evaluate(close=2000.0, ema50=1990.0, ema200=1950.0)
        state2 = self.engine.get_state()
        
        assert state1 == state2
    
    def test_state_changes_on_new_evaluation(self):
        """Test state updates when regime changes."""
        # BULL market
        self.engine.evaluate(close=2000.0, ema50=1990.0, ema200=1950.0)
        state_bull = self.engine.get_state()
        
        # Change to BEAR market
        self.engine.evaluate(close=1900.0, ema50=1910.0, ema200=1950.0)
        state_bear = self.engine.get_state()
        
        # States should differ
        assert state_bull['regime'] != state_bear['regime']
        assert state_bull['regime'] == 'BULL'
        assert state_bear['regime'] == 'BEAR'
    
    # Confidence Sensitivity Tests
    def test_confidence_increases_with_ema_separation(self):
        """Test confidence increases as EMA separation widens."""
        # Small EMA separation
        self.engine.evaluate(close=2001.0, ema50=2000.0, ema200=1999.0)
        confidence_small = self.engine.confidence
        
        # Large EMA separation
        self.engine.evaluate(close=2100.0, ema50=2050.0, ema200=1900.0)
        confidence_large = self.engine.confidence
        
        assert confidence_large > confidence_small
    
    def test_confidence_increases_with_price_distance(self):
        """Test confidence increases as price moves further from EMA50."""
        # Price close to EMA50
        self.engine.evaluate(close=2000.5, ema50=2000.0, ema200=1900.0)
        confidence_close = self.engine.confidence
        
        # Price far from EMA50
        self.engine.evaluate(close=2100.0, ema50=2000.0, ema200=1900.0)
        confidence_far = self.engine.confidence
        
        assert confidence_far > confidence_close


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

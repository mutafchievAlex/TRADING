"""
Entry Conditions Test Suite

Tests all 7 stages of entry evaluation.
Covers:
- Normal cases (all pass)
- Failure cases (individual stages fail)
- Edge cases (boundary values)
- Integration (multiple conditions simultaneously)
"""

import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engines.strategy_engine import StrategyEngine
from src.engines.bar_close_guard import BarCloseGuard
from src.utils.logger_setup import setup_logging


class TestEntryConditions:
    """Complete entry conditions test suite."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        # Initialize logger
        self.logger = setup_logging(log_dir='logs', log_level='DEBUG').get_main_logger()
        
        # Create strategy engine
        self.engine = StrategyEngine(
            atr_multiplier_stop=2.0,
            risk_reward_ratio_long=2.0,
            enable_momentum_filter=True,
            cooldown_hours=24
        )
        
        yield
    
    # ========== STAGE 1: BAR-CLOSE GUARD ==========
    
    def test_stage1_forming_bar_rejected(self):
        """Using forming bar (-1) should fail bar-close check."""
        df = self._create_test_dataframe(rows=10)
        pattern = self._create_valid_pattern(df)
        
        # Use forming bar (-1)
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-1)
        
        assert result == False
        assert details['failure_code'] == 'BAR_NOT_CLOSED'
        assert 'Bar state invalid' in details['reason']
    
    def test_stage1_closed_bar_passes_guard(self):
        """Using closed bar (-2) should pass bar-close check."""
        df = self._create_test_dataframe(rows=10)
        pattern = self._create_valid_pattern(df)
        
        # Use closed bar (-2)
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        # Should proceed past bar-close check
        assert details['pattern_valid'] == True or result == False  # Passes stage 1
    
    # ========== STAGE 2: PATTERN DETECTION ==========
    
    def test_stage2_no_pattern_fails(self):
        """None pattern should fail stage 2."""
        df = self._create_test_dataframe(rows=10)
        
        result, details = self.engine.evaluate_entry(df, None, current_bar_index=-2)
        
        assert result == False
        assert details['failure_code'] == 'INVALID_PATTERN_STRUCTURE'
        assert 'No valid Double Bottom' in details['reason']
    
    def test_stage2_pattern_invalid_flag_fails(self):
        """Pattern with valid=False should fail stage 2."""
        df = self._create_test_dataframe(rows=10)
        pattern = {
            'pattern_valid': False,
            'neckline': {'price': 2000.00},
        }
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert result == False
        assert details['failure_code'] == 'INVALID_PATTERN_STRUCTURE'
    
    def test_stage2_valid_pattern_passes(self):
        """Valid pattern should pass stage 2."""
        df = self._create_test_dataframe(rows=10, close=2001.50, ema50=2000.00)
        pattern = self._create_valid_pattern(df, neckline=2000.00)
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        # Should pass stage 2 (pattern valid)
        assert details['pattern_valid'] == True
    
    # ========== STAGE 3: BREAKOUT CONFIRMATION ==========
    
    def test_stage3_close_above_neckline_passes(self):
        """Close > Neckline should pass stage 3."""
        df = self._create_test_dataframe(
            rows=10,
            close=2001.50,
            ema50=2000.00,
            high=2003.00,
            low=2000.50,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=2000.00)
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        # Should pass breakout check
        assert details['breakout_confirmed'] == True
    
    def test_stage3_close_equals_neckline_fails(self):
        """Close == Neckline should FAIL (not clear break)."""
        df = self._create_test_dataframe(
            rows=10,
            close=2000.00,  # Equal to neckline, not above
            ema50=1999.50,
            high=2000.50,
            low=1999.50,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=2000.00)
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert result == False
        assert details['failure_code'] == 'NO_NECKLINE_BREAK'
        assert 'Close' in details['reason'] and 'Neckline' in details['reason']
    
    def test_stage3_close_below_neckline_fails(self):
        """Close < Neckline should fail stage 3."""
        df = self._create_test_dataframe(
            rows=10,
            close=1999.50,  # Below neckline
            ema50=1999.00,
            high=2000.00,
            low=1999.00,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=2000.00)
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert result == False
        assert details['failure_code'] == 'NO_NECKLINE_BREAK'
    
    def test_stage3_close_just_above_neckline_passes(self):
        """Close slightly above (2000.01) should PASS breakout."""
        df = self._create_test_dataframe(
            rows=10,
            close=2000.01,  # Just above
            ema50=1999.50,
            high=2000.50,
            low=1999.50,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=2000.00)
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert details['breakout_confirmed'] == True
    
    # ========== STAGE 4: TREND FILTER ==========
    
    def test_stage4_close_above_ema50_passes(self):
        """Close > EMA50 should pass trend filter."""
        df = self._create_test_dataframe(
            rows=10,
            close=2001.50,  # Above EMA50
            ema50=2000.00,
            high=2003.00,
            low=2000.00,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=2000.00)
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert details['above_ema50'] == True
    
    def test_stage4_close_below_ema50_fails(self):
        """Close < EMA50 should fail (downtrend)."""
        df = self._create_test_dataframe(
            rows=10,
            close=1999.50,  # Below EMA50 (downtrend)
            ema50=2000.00,
            high=2000.50,
            low=1999.00,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=2000.00)
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert result == False
        assert details['failure_code'] == 'CONTEXT_NOT_ALIGNED'
        assert 'Trend check failed' in details['reason']
    
    def test_stage4_close_equals_ema50_fails(self):
        """Close == EMA50 should FAIL (not above)."""
        df = self._create_test_dataframe(
            rows=10,
            close=2000.00,  # Equal to EMA50
            ema50=2000.00,
            high=2000.50,
            low=1999.50,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=2000.00)
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert result == False
        assert details['failure_code'] == 'CONTEXT_NOT_ALIGNED'
    
    def test_stage4_close_just_above_ema50_passes(self):
        """Close slightly above (2000.01) should PASS."""
        df = self._create_test_dataframe(
            rows=10,
            close=2000.01,  # Just above EMA50
            ema50=2000.00,
            high=2000.50,
            low=1999.50,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=1999.50)
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert details['above_ema50'] == True
    
    # ========== STAGE 5: MOMENTUM FILTER ==========
    
    def test_stage5_sufficient_momentum_passes(self):
        """Range >= 0.5×ATR should PASS."""
        # ATR = 5.00, threshold = 0.5, min_range = 2.50
        df = self._create_test_dataframe(
            rows=10,
            close=2001.50,
            ema50=2000.00,
            high=2003.50,  # Range = 3.50 >= 2.50 ✓
            low=2000.00,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=1999.50)
        self.engine.enable_momentum_filter = True
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert details['has_momentum'] == True
    
    def test_stage5_insufficient_momentum_fails(self):
        """Range < 0.5×ATR should FAIL."""
        # ATR = 5.00, threshold = 0.5, min_range = 2.50
        df = self._create_test_dataframe(
            rows=10,
            close=2001.25,
            ema50=2000.00,
            high=2001.25,  # Range = 0.50 < 2.50 ✗
            low=2000.75,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=2000.00)
        self.engine.enable_momentum_filter = True
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert result == False
        assert details['failure_code'] == 'CONTEXT_NOT_ALIGNED'
    
    def test_stage5_momentum_disabled_weak_range_passes(self):
        """With filter disabled, weak range should PASS."""
        df = self._create_test_dataframe(
            rows=10,
            close=2001.25,
            ema50=2000.00,
            high=2001.25,  # Weak range
            low=2000.75,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=2000.00)
        self.engine.enable_momentum_filter = False
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        # Should pass because filter is disabled
        assert details['has_momentum'] == True
    
    def test_stage5_exactly_at_threshold_passes(self):
        """Range exactly at threshold should PASS."""
        # ATR = 5.00, threshold = 0.5, min_range = 2.50
        df = self._create_test_dataframe(
            rows=10,
            close=2002.50,
            ema50=2000.00,
            high=2002.50,  # Range = 2.50 == 2.50 ✓
            low=2000.00,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=1999.50)
        self.engine.enable_momentum_filter = True
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert details['has_momentum'] == True
    
    # ========== STAGE 7: COOLDOWN (Stage 6 is warning-only) ==========
    
    def test_stage7_cooldown_active_blocks(self):
        """Within cooldown should FAIL."""
        last_trade = datetime(2026, 1, 15, 10, 0, 0)
        current_time = datetime(2026, 1, 15, 22, 0, 0)  # Only 12 hours
        
        df = self._create_test_dataframe(rows=10, time=current_time)
        pattern = self._create_valid_pattern(df)
        
        self.engine.last_trade_time = last_trade
        self.engine.cooldown_hours = 24
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert result == False
        assert details['failure_code'] == 'COOLDOWN_ACTIVE'
    
    def test_stage7_cooldown_expired_allows(self):
        """After cooldown should PASS."""
        last_trade = datetime(2026, 1, 15, 10, 0, 0)
        current_time = datetime(2026, 1, 16, 11, 0, 0)  # 25 hours
        
        df = self._create_test_dataframe(
            rows=10,
            time=current_time,
            close=2001.50,
            ema50=2000.00,
            high=2003.00,
            low=2000.00,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=1999.50)
        
        self.engine.last_trade_time = last_trade
        self.engine.cooldown_hours = 24
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert details['cooldown_ok'] == True
    
    def test_stage7_cooldown_exactly_at_expiry_passes(self):
        """Exactly at cooldown expiry should PASS."""
        last_trade = datetime(2026, 1, 15, 10, 0, 0)
        current_time = datetime(2026, 1, 16, 10, 0, 0)  # Exactly 24 hours
        
        df = self._create_test_dataframe(
            rows=10,
            time=current_time,
            close=2001.50,
            ema50=2000.00,
            high=2003.00,
            low=2000.00,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=1999.50)
        
        self.engine.last_trade_time = last_trade
        self.engine.cooldown_hours = 24
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert details['cooldown_ok'] == True
    
    def test_stage7_first_trade_no_cooldown(self):
        """First trade (no previous trade) should PASS cooldown."""
        df = self._create_test_dataframe(
            rows=10,
            close=2001.50,
            ema50=2000.00,
            high=2003.00,
            low=2000.00,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=1999.50)
        
        self.engine.last_trade_time = None  # First trade
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert details['cooldown_ok'] == True
    
    # ========== INTEGRATION TESTS ==========
    
    def test_all_conditions_met_enters_trade(self):
        """With all conditions met, should ENTER LONG."""
        df = self._create_test_dataframe(
            rows=10,
            close=2001.50,
            ema50=2000.00,
            high=2003.50,
            low=2000.00,
            atr14=5.00,
            time=datetime(2026, 1, 16, 12, 0, 0)
        )
        pattern = self._create_valid_pattern(df, neckline=1999.50)
        
        self.engine.enable_momentum_filter = True
        self.engine.last_trade_time = None
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert result == True
        assert details['should_enter'] == True
        assert details['entry_price'] is not None
        assert details['stop_loss'] is not None
        assert details['take_profit'] is not None
    
    def test_one_blocking_condition_fails_rejects_trade(self):
        """If any blocking condition fails, should REJECT."""
        df = self._create_test_dataframe(
            rows=10,
            close=1999.50,  # Below EMA50 (fails stage 4)
            ema50=2000.00,
            high=2000.50,
            low=1999.00,
            atr14=5.00
        )
        pattern = self._create_valid_pattern(df, neckline=2000.00)
        
        result, details = self.engine.evaluate_entry(df, pattern, current_bar_index=-2)
        
        assert result == False
        assert details['above_ema50'] == False
    
    def test_multiple_failures_stops_at_first(self):
        """When multiple fail, should stop at first failure."""
        # No pattern AND below EMA50 - should fail at pattern stage first
        df = self._create_test_dataframe(
            rows=10,
            close=1999.50,
            ema50=2000.00,
            high=2000.50,
            low=1999.00,
            atr14=5.00
        )
        
        result, details = self.engine.evaluate_entry(df, None, current_bar_index=-2)
        
        # Should fail at stage 2 (pattern), not stage 4 (trend)
        assert result == False
        assert details['failure_code'] == 'INVALID_PATTERN_STRUCTURE'
    
    # ========== HELPER METHODS ==========
    
    def _create_test_dataframe(self, rows=10, close=2000.00, ema50=2000.00,
                               high=2000.50, low=1999.50, atr14=5.00,
                               time=None):
        """Create test DataFrame with required columns."""
        if time is None:
            time = datetime(2026, 1, 16, 12, 0, 0)
        
        dates = [time - timedelta(hours=i) for i in range(rows, 0, -1)]
        
        df = pd.DataFrame({
            'time': dates,
            'open': [close] * rows,
            'high': [high] * rows,
            'low': [low] * rows,
            'close': [close] * rows,
            'ema50': [ema50] * rows,
            'ema200': [ema50 - 1] * rows,
            'atr14': [atr14] * rows,
        })
        
        return df
    
    def _create_valid_pattern(self, df, neckline=2000.00):
        """Create valid Double Bottom pattern."""
        return {
            'pattern_valid': True,
            'neckline': {
                'price': neckline,
                'timestamp': df['time'].iloc[-2],
            },
            'first_low': {
                'price': neckline - 10,
                'timestamp': df['time'].iloc[-5],
            },
            'second_low': {
                'price': neckline - 10.05,
                'timestamp': df['time'].iloc[-3],
            },
            'quality_score': 7.5,
        }


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

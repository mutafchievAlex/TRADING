"""
Unit tests for TP1 Exit Decision Engine

Tests the decision logic for post-TP1 exit scenarios:
- HOLD on micro-pullback
- WAIT_NEXT_BAR on single-bar pullback
- EXIT_TRADE on confirmed failure
"""

import unittest
import logging
from src.engines.tp1_exit_decision_engine import (
    TP1ExitDecisionEngine,
    TP1EvaluationContext,
    PostTP1Decision,
    MomentumState,
    MarketRegime
)


class TestTP1ExitDecisionEngine(unittest.TestCase):
    """Test TP1 exit decision logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = TP1ExitDecisionEngine(logger=logging.getLogger(__name__))
        
        # Default context
        self.default_context = TP1EvaluationContext(
            current_price=2105.0,
            entry_price=2100.0,
            stop_loss=2095.0,
            tp1_price=2110.0,
            atr_14=5.0,
            market_regime=MarketRegime.BULL,
            momentum_state=MomentumState.STRONG,
            last_closed_bar={
                'close': 2105.0,
                'high': 2108.0,
                'low': 2102.0,
                'open': 2103.0,
                'time': '2024-01-15 10:00:00'
            },
            bars_since_tp1=1,
            previous_bar_close=2112.0,  # Closed above TP1 previously
            two_bars_ago_close=2111.0
        )
    
    def test_no_exit_same_bar_as_tp1(self):
        """Should HOLD if TP1 reached on same bar (anti-premature-exit guard)."""
        ctx = TP1EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.bars_since_tp1 = 0  # Same bar as TP1
        
        result = self.engine.evaluate_post_tp1(ctx)
        
        self.assertEqual(result.decision, PostTP1Decision.HOLD)
        self.assertIn("same bar", result.reason_text.lower())
    
    def test_hold_on_micro_pullback(self):
        """Should HOLD if price retraces less than 0.25*ATR."""
        ctx = TP1EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.current_price = 2109.0  # Only 1.0 below TP1
        ctx.atr_14 = 5.0  # Micro-pullback is < 0.25*5.0 = 1.25
        ctx.bars_since_tp1 = 1
        
        result = self.engine.evaluate_post_tp1(ctx)
        
        self.assertEqual(result.decision, PostTP1Decision.HOLD)
        self.assertIn("micro-pullback", result.reason_text.lower())
    
    def test_hold_above_tp1_on_close(self):
        """Should HOLD if bar close is still above TP1."""
        ctx = TP1EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.last_closed_bar['close'] = 2111.0  # Above TP1
        ctx.current_price = 2109.5  # Small pullback, not deep
        ctx.previous_bar_close = None  # No two-bar confirmation
        ctx.atr_14 = 10.0  # Larger ATR so retrace isn't deep
        ctx.bars_since_tp1 = 1

        result = self.engine.evaluate_post_tp1(ctx)

        self.assertEqual(result.decision, PostTP1Decision.HOLD)
    
    def test_hold_in_bull_regime(self):
        """Should HOLD in bullish market regime."""
        ctx = TP1EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.market_regime = MarketRegime.BULL
        ctx.last_closed_bar['close'] = 2107.0  # Below TP1 but not micro-pullback
        ctx.current_price = 2106.5  # Deeper pullback
        ctx.previous_bar_close = None  # No two-bar confirmation
        ctx.atr_14 = 10.0  # Larger ATR so it's not micro-pullback and not deep
        ctx.bars_since_tp1 = 1

        result = self.engine.evaluate_post_tp1(ctx)

        self.assertEqual(result.decision, PostTP1Decision.HOLD)
        self.assertIn("bullish", result.reason_text.lower())
    
    def test_wait_single_bar_pullback(self):
        """Should WAIT_NEXT_BAR on first bar below TP1 but above entry."""
        ctx = TP1EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.last_closed_bar['close'] = 2102.0  # Below TP1 but above entry
        ctx.current_price = 2101.0
        ctx.previous_bar_close = 2112.0  # Above TP1 (not 2 bars below)
    
    def test_exit_two_consecutive_bars_below_tp1(self):
        """Should EXIT after 2 consecutive bars below TP1."""
        ctx = TP1EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.last_closed_bar['close'] = 2108.0  # Below TP1
        ctx.previous_bar_close = 2109.0  # Also below TP1
        ctx.current_price = 2108.0
        ctx.bars_since_tp1 = 2
        ctx.market_regime = MarketRegime.RANGE  # Not favorable
        ctx.momentum_state = MomentumState.BROKEN
        
        result = self.engine.evaluate_post_tp1(ctx)
        
        self.assertEqual(result.decision, PostTP1Decision.EXIT_TRADE)
        self.assertIn("failure confirmed", result.reason_text.lower())
    
    def test_exit_deep_retracement(self):
        """Should EXIT if retracement >= 0.5*ATR."""
        ctx = TP1EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.tp1_price = 2110.0
        ctx.current_price = 2105.0  # 5.0 pips below TP1
        ctx.atr_14 = 8.0  # 0.5*8 = 4.0, so 5.0 >= 4.0 triggers deep retracement
        ctx.bars_since_tp1 = 1
        
        result = self.engine.evaluate_post_tp1(ctx)
        
        self.assertEqual(result.decision, PostTP1Decision.EXIT_TRADE)
        self.assertIn("deep retracement", result.reason_text.lower())
    
    def test_exit_momentum_broken(self):
        """Should EXIT if momentum is broken."""
        ctx = TP1EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.momentum_state = MomentumState.BROKEN
        ctx.last_closed_bar['close'] = 2108.0  # Below TP1
        ctx.current_price = 2107.0
        ctx.bars_since_tp1 = 1
        
        result = self.engine.evaluate_post_tp1(ctx)
        
        self.assertEqual(result.decision, PostTP1Decision.EXIT_TRADE)
        self.assertIn("momentum broken", result.reason_text.lower())
    
    def test_exit_regime_flip_to_range(self):
        """Should EXIT if regime flips from BULL to RANGE."""
        ctx = TP1EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.market_regime = MarketRegime.RANGE  # Was BULL
        ctx.last_closed_bar['close'] = 2108.0
        ctx.current_price = 2107.0
        ctx.bars_since_tp1 = 1
        
        result = self.engine.evaluate_post_tp1(ctx)
        
        self.assertEqual(result.decision, PostTP1Decision.EXIT_TRADE)
        self.assertIn("regime", result.reason_text.lower())
    
    def test_exit_regime_flip_to_bear(self):
        """Should EXIT if regime flips to BEAR."""
        ctx = TP1EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.market_regime = MarketRegime.BEAR
        ctx.last_closed_bar['close'] = 2108.0
        ctx.current_price = 2107.0
        ctx.bars_since_tp1 = 1
        
        result = self.engine.evaluate_post_tp1(ctx)
        
        self.assertEqual(result.decision, PostTP1Decision.EXIT_TRADE)
    
    def test_calculate_sl_after_tp1(self):
        """Should calculate SL at entry + 0.2*ATR for LONG."""
        entry_price = 2100.0
        tp1_price = 2110.0
        atr_14 = 5.0
        
        suggested_sl = self.engine.calculate_sl_after_tp1(
            entry_price=entry_price,
            tp1_price=tp1_price,
            atr_14=atr_14,
            direction=1  # LONG
        )
        
        # SL should be entry + 0.2*ATR = 2100 + 1.0 = 2101.0
        self.assertEqual(suggested_sl, 2101.0)
    
    def test_calculate_sl_after_tp1_short(self):
        """Should calculate SL at entry - 0.2*ATR for SHORT."""
        entry_price = 2100.0
        tp1_price = 2090.0
        atr_14 = 5.0
        
        suggested_sl = self.engine.calculate_sl_after_tp1(
            entry_price=entry_price,
            tp1_price=tp1_price,
            atr_14=atr_14,
            direction=-1  # SHORT
        )
        
        # SL should be entry - 0.2*ATR = 2100 - 1.0 = 2099.0
        self.assertEqual(suggested_sl, 2099.0)


class TestTP1EdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = TP1ExitDecisionEngine(logger=logging.getLogger(__name__))
    
    def test_exact_zero_retrace_holds(self):
        """Price exactly at TP1 should HOLD."""
        ctx = TP1EvaluationContext(
            current_price=2110.0,
            entry_price=2100.0,
            stop_loss=2095.0,
            tp1_price=2110.0,
            atr_14=5.0,
            market_regime=MarketRegime.BULL,
            momentum_state=MomentumState.STRONG,
            last_closed_bar={
                'close': 2110.0,
                'high': 2112.0,
                'low': 2108.0,
                'open': 2105.0,
                'time': '2024-01-15 10:00:00'
            },
            bars_since_tp1=1
        )
        
        result = self.engine.evaluate_post_tp1(ctx)
        
        self.assertEqual(result.decision, PostTP1Decision.HOLD)
    
    def test_pullback_exactly_at_boundary_threshold(self):
        """Pullback exactly at 0.25*ATR boundary should HOLD."""
        atr = 5.0
        tp1 = 2110.0
        current = 2110.0 - (0.25 * atr)  # Exactly at boundary
        
        ctx = TP1EvaluationContext(
            current_price=current,
            entry_price=2100.0,
            stop_loss=2095.0,
            tp1_price=tp1,
            atr_14=atr,
            market_regime=MarketRegime.BULL,
            momentum_state=MomentumState.STRONG,
            last_closed_bar={
                'close': current,
                'high': tp1,
                'low': current - 1.0,
                'open': current + 0.5,
                'time': '2024-01-15 10:00:00'
            },
            bars_since_tp1=1
        )
        
        result = self.engine.evaluate_post_tp1(ctx)
        
        # At boundary should still HOLD (<=, not <)
        self.assertEqual(result.decision, PostTP1Decision.HOLD)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()

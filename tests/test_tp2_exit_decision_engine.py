"""
Unit tests for TP2 Exit Decision Engine

Tests the decision logic for post-TP2 exit scenarios:
- HOLD on shallow pullback, strong trend, structure intact
- WAIT_NEXT_BAR on momentum softening, first close below TP2
- EXIT_TRADE on structure break, confirmed rejection, momentum break
"""

import unittest
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import directly to avoid MT5 dependency
import importlib.util
spec = importlib.util.spec_from_file_location(
    "tp2_exit_decision_engine",
    Path(__file__).parent.parent / "src" / "engines" / "tp2_exit_decision_engine.py"
)
tp2_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tp2_module)

TP2ExitDecisionEngine = tp2_module.TP2ExitDecisionEngine
TP2EvaluationContext = tp2_module.TP2EvaluationContext
PostTP2Decision = tp2_module.PostTP2Decision
MomentumState = tp2_module.MomentumState
MarketRegime = tp2_module.MarketRegime
StructureState = tp2_module.StructureState


class TestTP2ExitDecisionEngine(unittest.TestCase):
    """Test TP2 exit decision logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = TP2ExitDecisionEngine(logger=logging.getLogger(__name__))
        
        # Default context
        self.default_context = TP2EvaluationContext(
            current_price=2115.0,
            entry_price=2100.0,
            stop_loss=2095.0,
            tp2_price=2120.0,
            tp3_price=2130.0,
            tp1_price=2110.0,
            atr_14=5.0,
            market_regime=MarketRegime.BULL,
            momentum_state=MomentumState.STRONG,
            structure_state=StructureState.HIGHER_LOWS,
            last_closed_bar={
                'close': 2115.0,
                'high': 2118.0,
                'low': 2112.0,
                'open': 2113.0,
                'time': '2024-01-15 10:00:00'
            },
            bars_since_tp2=1,
            previous_bar_close=2122.0,  # Above TP2
            two_bars_ago_close=2121.0
        )
    
    def test_no_exit_same_bar_as_tp2(self):
        """Should HOLD if TP2 reached on same bar (anti-premature-exit guard)."""
        ctx = TP2EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.bars_since_tp2 = 0  # Same bar as TP2
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.HOLD)
        self.assertIn("same bar", result.reason_text.lower())
    
    def test_hold_strong_trend_continuation(self):
        """Should HOLD on strong trend continuation (close >= TP2, STRONG momentum, BULL regime)."""
        ctx = TP2EvaluationContext(
            current_price=2121.0,
            entry_price=2100.0,
            stop_loss=2095.0,
            tp2_price=2120.0,
            tp3_price=2130.0,
            tp1_price=2110.0,
            atr_14=5.0,
            market_regime=MarketRegime.BULL,  # Must be BULL
            momentum_state=MomentumState.STRONG,  # Must be STRONG
            structure_state=StructureState.HIGHER_LOWS,  # Must not be LOWER_LOW
            last_closed_bar={
                'close': 2121.0,  # Above TP2
                'high': 2123.0,
                'low': 2119.0,
                'open': 2120.0,
                'time': '2024-01-15 10:00:00'
            },
            bars_since_tp2=1,
            previous_bar_close=None,  # No 2-bar confirmation
            two_bars_ago_close=None
        )
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.HOLD)
        self.assertIn("strong trend", result.reason_text.lower())
        self.assertTrue(result.should_trail_sl)
    
    def test_hold_shallow_pullback(self):
        """Should HOLD if pullback <= 0.2*ATR (tighter than TP1)."""
        ctx = TP2EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.tp2_price = 2120.0
        ctx.current_price = 2119.0  # Only 1.0 below TP2
        ctx.atr_14 = 10.0  # Shallow pullback is < 0.2*10 = 2.0
        ctx.bars_since_tp2 = 1
        ctx.previous_bar_close = None  # No 2-bar confirmation
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.HOLD)
        self.assertIn("shallow pullback", result.reason_text.lower())
        self.assertTrue(result.should_trail_sl)
    
    def test_hold_structure_intact(self):
        """Should HOLD if structure is HIGHER_LOWS."""
        ctx = TP2EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.structure_state = StructureState.HIGHER_LOWS
        ctx.last_closed_bar['close'] = 2118.0  # Below TP2
        ctx.current_price = 2117.0
        ctx.previous_bar_close = None
        ctx.atr_14 = 10.0  # Large ATR so not shallow pullback
        ctx.momentum_state = MomentumState.MODERATE  # Not strong trend
        ctx.market_regime = MarketRegime.BULL
        ctx.bars_since_tp2 = 1
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.HOLD)
        self.assertIn("structure intact", result.reason_text.lower())
        self.assertTrue(result.should_trail_sl)
    
    def test_wait_momentum_softening(self):
        """Should WAIT_NEXT_BAR if momentum is MODERATE."""
        ctx = TP2EvaluationContext(
            current_price=2117.5,  # 2.5 below TP2 (between shallow 2.0 and deep 3.5)
            entry_price=2100.0,
            stop_loss=2095.0,
            tp2_price=2120.0,
            tp3_price=2130.0,
            tp1_price=2110.0,
            atr_14=10.0,  # 2.5 > 0.2*10=2.0 (not shallow), 2.5 < 0.35*10=3.5 (not deep)
            market_regime=MarketRegime.BULL,  # Must be BULL (not RANGE)
            momentum_state=MomentumState.MODERATE,  # MODERATE momentum (triggers WAIT)
            structure_state=StructureState.UNKNOWN,  # NOT HIGHER_LOWS (to avoid HOLD)
            last_closed_bar={
                'close': 2117.5,  # Below TP2, not shallow, not deep
                'high': 2120.0,
                'low': 2117.0,
                'open': 2119.0,
                'time': '2024-01-15 10:00:00'
            },
            bars_since_tp2=1,
            previous_bar_close=None,  # Not 2 bars below TP2
            two_bars_ago_close=None
        )
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.WAIT_NEXT_BAR)
        self.assertIn("momentum softening", result.reason_text.lower())
        self.assertTrue(result.should_trail_sl)
    
    def test_wait_first_close_below_tp2(self):
        """Should WAIT_NEXT_BAR on first close below TP2 but above TP1."""
        ctx = TP2EvaluationContext(
            current_price=2118.5,
            entry_price=2100.0,
            stop_loss=2095.0,
            tp2_price=2120.0,
            tp3_price=2130.0,
            tp1_price=2110.0,
            atr_14=5.0,  # 1.5 > 0.2*5=1.0, so not shallow
            market_regime=MarketRegime.BULL,  # Must be BULL
            momentum_state=MomentumState.STRONG,  # Strong momentum
            structure_state=StructureState.UNKNOWN,  # NOT HIGHER_LOWS (to avoid HOLD)
            last_closed_bar={
                'close': 2118.5,  # Below TP2, above TP1, triggers "first close below TP2"
                'high': 2121.0,
                'low': 2118.0,
                'open': 2120.5,
                'time': '2024-01-15 10:00:00'
            },
            bars_since_tp2=1,
            previous_bar_close=2122.0,  # Previous bar above TP2 (not 2-bar confirmation)
            two_bars_ago_close=2121.0
        )
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.WAIT_NEXT_BAR)
        self.assertIn("first close below tp2", result.reason_text.lower())
        self.assertTrue(result.should_trail_sl)
    
    def test_exit_structure_break(self):
        """Should EXIT immediately on structure break (LOWER_LOW)."""
        ctx = TP2EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.structure_state = StructureState.LOWER_LOW
        ctx.last_closed_bar['close'] = 2118.0
        ctx.current_price = 2117.0
        ctx.bars_since_tp2 = 1
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.EXIT_TRADE)
        self.assertIn("structure broken", result.reason_text.lower())
    
    def test_exit_momentum_broken(self):
        """Should EXIT if momentum is BROKEN."""
        ctx = TP2EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.momentum_state = MomentumState.BROKEN
        ctx.last_closed_bar['close'] = 2118.0
        ctx.current_price = 2117.0
        ctx.previous_bar_close = None
        ctx.structure_state = StructureState.HIGHER_LOWS
        ctx.bars_since_tp2 = 1
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.EXIT_TRADE)
        self.assertIn("momentum broken", result.reason_text.lower())
    
    def test_exit_regime_flip_to_range(self):
        """Should EXIT if regime flips to RANGE."""
        ctx = TP2EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.market_regime = MarketRegime.RANGE
        ctx.last_closed_bar['close'] = 2118.0
        ctx.current_price = 2117.0
        ctx.previous_bar_close = None
        ctx.structure_state = StructureState.HIGHER_LOWS
        ctx.momentum_state = MomentumState.STRONG
        ctx.bars_since_tp2 = 1
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.EXIT_TRADE)
        self.assertIn("regime", result.reason_text.lower())
    
    def test_exit_regime_flip_to_bear(self):
        """Should EXIT if regime flips to BEAR."""
        ctx = TP2EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.market_regime = MarketRegime.BEAR
        ctx.last_closed_bar['close'] = 2118.0
        ctx.current_price = 2117.0
        ctx.previous_bar_close = None
        ctx.structure_state = StructureState.HIGHER_LOWS
        ctx.momentum_state = MomentumState.STRONG
        ctx.bars_since_tp2 = 1
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.EXIT_TRADE)
    
    def test_exit_two_consecutive_bars_below_tp2(self):
        """Should EXIT after 2 consecutive bars below TP2."""
        ctx = TP2EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.last_closed_bar['close'] = 2118.0  # Below TP2
        ctx.previous_bar_close = 2119.0  # Also below TP2
        ctx.current_price = 2118.0
        ctx.bars_since_tp2 = 2
        ctx.structure_state = StructureState.HIGHER_LOWS
        ctx.momentum_state = MomentumState.STRONG
        ctx.market_regime = MarketRegime.BULL
        ctx.atr_14 = 10.0
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.EXIT_TRADE)
        self.assertIn("failure confirmed", result.reason_text.lower())
    
    def test_exit_deep_retracement(self):
        """Should EXIT if retracement >= 0.35*ATR (tighter than TP1's 0.5)."""
        ctx = TP2EvaluationContext(
            **{k: v for k, v in self.default_context.__dict__.items()}
        )
        ctx.tp2_price = 2120.0
        ctx.current_price = 2115.0  # 5.0 pips below TP2
        ctx.atr_14 = 10.0  # 0.35*10 = 3.5, so 5.0 >= 3.5 triggers deep retracement
        ctx.bars_since_tp2 = 1
        ctx.previous_bar_close = None
        ctx.structure_state = StructureState.HIGHER_LOWS
        ctx.momentum_state = MomentumState.STRONG
        ctx.market_regime = MarketRegime.BULL
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.EXIT_TRADE)
        self.assertIn("deep retracement", result.reason_text.lower())
    
    def test_calculate_trailing_sl_long(self):
        """Should calculate trailing SL for LONG trade (entry + 0.1*ATR minimum)."""
        entry_price = 2100.0
        tp2_price = 2120.0
        current_price = 2125.0
        atr_14 = 5.0
        
        trailing_sl = self.engine.calculate_trailing_sl_after_tp2(
            entry_price=entry_price,
            tp2_price=tp2_price,
            current_price=current_price,
            atr_14=atr_14,
            swing_low=None,
            direction=1  # LONG
        )
        
        # SL should be current_price - 0.3*ATR = 2125 - 1.5 = 2123.5
        # But must be at least entry + 0.1*ATR = 2100 + 0.5 = 2100.5
        expected = max(2123.5, 2100.5)
        self.assertAlmostEqual(trailing_sl, expected, places=1)
    
    def test_calculate_trailing_sl_with_swing_low(self):
        """Should use swing low for trailing SL if closer."""
        entry_price = 2100.0
        tp2_price = 2120.0
        current_price = 2125.0
        atr_14 = 5.0
        swing_low = 2122.0
        
        trailing_sl = self.engine.calculate_trailing_sl_after_tp2(
            entry_price=entry_price,
            tp2_price=tp2_price,
            current_price=current_price,
            atr_14=atr_14,
            swing_low=swing_low,
            direction=1  # LONG
        )
        
        # ATR method: 2125 - 1.5 = 2123.5
        # Swing method: 2122 - 0.5 = 2121.5
        # Take max: 2123.5
        # Must be above entry + 0.1*ATR = 2100.5
        self.assertGreater(trailing_sl, 2120.0)


class TestTP2EdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions for TP2."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = TP2ExitDecisionEngine(logger=logging.getLogger(__name__))
    
    def test_exact_zero_retrace_holds(self):
        """Price exactly at TP2 should HOLD."""
        ctx = TP2EvaluationContext(
            current_price=2120.0,
            entry_price=2100.0,
            stop_loss=2095.0,
            tp2_price=2120.0,
            tp3_price=2130.0,
            tp1_price=2110.0,
            atr_14=5.0,
            market_regime=MarketRegime.BULL,
            momentum_state=MomentumState.STRONG,
            structure_state=StructureState.HIGHER_LOWS,
            last_closed_bar={
                'close': 2120.0,
                'high': 2122.0,
                'low': 2118.0,
                'open': 2115.0,
                'time': '2024-01-15 10:00:00'
            },
            bars_since_tp2=1
        )
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.HOLD)
    
    def test_pullback_exactly_at_shallow_boundary(self):
        """Pullback exactly at 0.2*ATR boundary should HOLD."""
        atr = 5.0
        tp2 = 2120.0
        current = 2120.0 - (0.2 * atr)  # Exactly at boundary
        
        ctx = TP2EvaluationContext(
            current_price=current,
            entry_price=2100.0,
            stop_loss=2095.0,
            tp2_price=tp2,
            tp3_price=2130.0,
            tp1_price=2110.0,
            atr_14=atr,
            market_regime=MarketRegime.BULL,
            momentum_state=MomentumState.STRONG,
            structure_state=StructureState.HIGHER_LOWS,
            last_closed_bar={
                'close': current,
                'high': tp2,
                'low': current - 1.0,
                'open': current + 0.5,
                'time': '2024-01-15 10:00:00'
            },
            bars_since_tp2=1
        )
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        # At boundary should still HOLD (<=, not <)
        self.assertEqual(result.decision, PostTP2Decision.HOLD)
    
    def test_structure_break_overrides_all(self):
        """Structure break should exit even with strong trend."""
        ctx = TP2EvaluationContext(
            current_price=2125.0,
            entry_price=2100.0,
            stop_loss=2095.0,
            tp2_price=2120.0,
            tp3_price=2130.0,
            tp1_price=2110.0,
            atr_14=5.0,
            market_regime=MarketRegime.BULL,
            momentum_state=MomentumState.STRONG,
            structure_state=StructureState.LOWER_LOW,  # Structure broken
            last_closed_bar={
                'close': 2125.0,
                'high': 2127.0,
                'low': 2123.0,
                'open': 2122.0,
                'time': '2024-01-15 10:00:00'
            },
            bars_since_tp2=1
        )
        
        result = self.engine.evaluate_post_tp2(ctx)
        
        self.assertEqual(result.decision, PostTP2Decision.EXIT_TRADE)
        self.assertIn("structure", result.reason_text.lower())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()

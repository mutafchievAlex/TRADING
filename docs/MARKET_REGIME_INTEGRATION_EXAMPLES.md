# Market Regime Integration Examples

## Quick Start Integration

This guide shows how to integrate Market Regime into your main application loop.

---

## 1. Basic Integration in main.py

```python
"""
Example main application loop with Market Regime integration
"""

from src.engines.market_regime_engine import MarketRegimeEngine
from src.engines.indicator_engine import IndicatorEngine
from src.engines.market_data_service import MarketDataService
from src.ui.main_window import MainWindow

def main():
    """Main application loop."""
    
    # Initialize engines
    market_data_service = MarketDataService()
    indicator_engine = IndicatorEngine()
    regime_engine = MarketRegimeEngine()
    main_window = MainWindow()
    
    # Main loop
    while running:
        # Fetch market data
        price_data = market_data_service.fetch_ohlc()
        
        # Calculate indicators
        indicators = {
            'ema50': indicator_engine.calculate_ema(price_data['close'], 50).iloc[-1],
            'ema200': indicator_engine.calculate_ema(price_data['close'], 200).iloc[-1],
            'atr14': indicator_engine.calculate_atr(price_data, 14).iloc[-1]
        }
        
        # EVALUATE MARKET REGIME
        regime_state = regime_engine.evaluate(
            close=price_data['close'].iloc[-1],
            ema50=indicators['ema50'],
            ema200=indicators['ema200']
        )
        
        # Get full regime state
        regime_info = regime_engine.get_state()
        
        # Update UI with regime
        main_window.update_market_regime(regime_info)
        
        # Update other UI elements
        main_window.update_market_data(price_data['close'].iloc[-1], indicators)
        
        # Continue with rest of logic...
```

---

## 2. Integration with Decision Engine

```python
"""
Example showing how Decision Engine uses Market Regime for quality scoring
"""

from src.engines.market_regime_engine import MarketRegimeEngine

class DecisionEngine:
    """Decision engine with market regime context."""
    
    def __init__(self, regime_engine: MarketRegimeEngine):
        self.regime_engine = regime_engine
    
    def make_decision(self, conditions: dict) -> dict:
        """
        Make trading decision with regime context.
        
        Args:
            conditions: Entry condition flags (pattern, breakout, trend, momentum, cooldown)
            
        Returns:
            Decision dict with verdict and reasoning
        """
        
        # Check if all entry conditions are met
        all_conditions_met = (
            conditions.get('pattern_valid') and
            conditions.get('breakout_confirmed') and
            conditions.get('above_ema50') and
            conditions.get('has_momentum') and
            conditions.get('cooldown_ok')
        )
        
        if not all_conditions_met:
            return {'decision': 'NO_TRADE', 'reason': 'Not all conditions met'}
        
        # All conditions are met, but check regime alignment
        regime_state = self.regime_engine.get_state()
        regime = regime_state['regime']
        
        # For LONG-ONLY strategy:
        if regime == 'BULL':
            # Perfect alignment: bullish regime + long signal
            decision = 'ENTER_LONG'
            reason = 'All conditions met, BULL regime aligned'
            regime_bonus = 1.0  # Add bonus to quality score
            
        elif regime == 'BEAR':
            # Conflicting signal: bearish regime but long signal
            decision = 'ENTER_LONG'  # Still take it but with penalty
            reason = 'Conditions met but BEAR regime conflicts (lower quality)'
            regime_bonus = -1.0  # Subtract from quality score
            
        else:  # RANGE
            # Uncertain environment: trend-following has lower probability
            decision = 'ENTER_LONG'
            reason = 'Conditions met but RANGE regime (uncertain environment)'
            regime_bonus = -0.5  # Modest penalty
        
        return {
            'decision': decision,
            'reason': reason,
            'regime_alignment': regime,
            'regime_bonus': regime_bonus,
            'confidence': regime_state['confidence']
        }
```

---

## 3. Integration with Quality Scoring Engine

```python
"""
Example showing how Quality Engine weights regime alignment
"""

class QualityScoreEngine:
    """Calculate entry quality score with regime alignment."""
    
    def __init__(self, regime_engine):
        self.regime_engine = regime_engine
        
        # Weighting components
        self.weights = {
            'pattern_alignment': 0.3,
            'regime_alignment': 0.4,
            'momentum_alignment': 0.3
        }
    
    def calculate_quality(self, decision_output: dict) -> float:
        """
        Calculate overall entry quality score.
        
        Args:
            decision_output: Dict with entry quality components
            
        Returns:
            Quality score 0-10
        """
        
        # Get regime state
        regime_state = self.regime_engine.get_state()
        regime = regime_state['regime']
        confidence = regime_state['confidence']
        
        # Component scores (0-10 scale)
        pattern_score = decision_output.get('pattern_score', 0)
        momentum_score = decision_output.get('momentum_score', 0)
        
        # Regime alignment score (0-10 scale)
        if regime == 'BULL':
            regime_score = 10.0 * confidence  # Full score in aligned regime
        elif regime == 'BEAR':
            regime_score = 2.0 * confidence   # Penalized in conflicting regime
        else:  # RANGE
            regime_score = 5.0 * confidence   # Medium score in uncertain market
        
        # Calculate weighted quality
        quality = (
            pattern_score * self.weights['pattern_alignment'] +
            regime_score * self.weights['regime_alignment'] +
            momentum_score * self.weights['momentum_alignment']
        )
        
        # Cap at 10
        quality = min(quality, 10.0)
        
        return quality
```

---

## 4. Backtest Integration

```python
"""
Example showing regime display in backtest analyzer
"""

class WhyNoTradeAnalyzer:
    """Analyze why trades were/weren't taken."""
    
    def analyze_bar(self, bar_data: dict) -> dict:
        """
        Analyze trading decision for a bar.
        
        Args:
            bar_data: OHLC data + indicators + regime + decision
            
        Returns:
            Analysis dict for UI display
        """
        
        regime = bar_data.get('regime', {})
        decision = bar_data.get('decision', {})
        conditions = bar_data.get('conditions', {})
        
        analysis = {
            'timestamp': bar_data['timestamp'],
            'price': bar_data['close'],
            'regime': regime.get('regime', 'RANGE'),
            'regime_confidence': regime.get('confidence', 0),
            'decision': decision.get('decision', 'NO_TRADE'),
            'reason': self._build_reason(conditions, regime, decision),
            'quality_score': decision.get('quality_score', 0),
        }
        
        return analysis
    
    def _build_reason(self, conditions: dict, regime: dict, decision: dict) -> str:
        """Build human-readable reason for decision."""
        
        reasons = []
        
        # Check individual conditions
        if not conditions.get('pattern_valid'):
            reasons.append("No pattern")
        if not conditions.get('breakout_confirmed'):
            reasons.append("No breakout")
        if not conditions.get('above_ema50'):
            reasons.append("Below EMA50")
        if not conditions.get('has_momentum'):
            reasons.append("No momentum")
        if not conditions.get('cooldown_ok'):
            reasons.append("In cooldown")
        
        # Add regime info if decision is taken
        if not reasons:  # All conditions met
            regime_type = regime.get('regime', 'RANGE')
            confidence = regime.get('confidence', 0)
            
            if regime_type == 'BULL':
                reasons.append(f"BULL {confidence*100:.0f}% ✓")
            elif regime_type == 'BEAR':
                reasons.append(f"BEAR {confidence*100:.0f}% (short bias)")
            else:
                reasons.append(f"RANGE {confidence*100:.0f}% (uncertain)")
        
        return " | ".join(reasons) if reasons else "Ready"
```

---

## 5. Live Trading with Regime Filter

```python
"""
Example showing live trading with regime-based entry filtering
"""

class LiveTradingEngine:
    """Execute trades with regime-aware filtering."""
    
    def __init__(self, execution_engine, regime_engine):
        self.execution_engine = execution_engine
        self.regime_engine = regime_engine
        
        # Trading rules
        self.allow_long_in_bear = False  # Don't take long in BEAR regime
        self.allow_any_in_range = True   # Can trade in RANGE but with lower size
    
    def execute_if_ready(self, decision: dict) -> bool:
        """
        Execute trade if decision is ready and regime allows it.
        
        Args:
            decision: Trading decision from decision engine
            
        Returns:
            True if trade executed, False otherwise
        """
        
        if decision.get('decision') != 'ENTER_LONG':
            return False
        
        # Get regime
        regime_state = self.regime_engine.get_state()
        regime = regime_state['regime']
        
        # Apply regime-based filtering
        if regime == 'BEAR' and not self.allow_long_in_bear:
            self.logger.warning(f"Skipped trade: LONG signal in BEAR regime (quality too low)")
            return False
        
        if regime == 'RANGE' and not self.allow_any_in_range:
            self.logger.warning(f"Skipped trade: RANGE regime (uncertain environment)")
            return False
        
        # Adjust position size based on regime confidence
        position_size = self._adjust_size_by_confidence(
            decision.get('planned_size', 1.0),
            regime_state['confidence']
        )
        
        # Execute trade
        return self.execution_engine.execute_long(
            entry_price=decision.get('entry_price'),
            stop_loss=decision.get('stop_loss'),
            take_profit=decision.get('take_profit'),
            volume=position_size
        )
    
    def _adjust_size_by_confidence(self, base_size: float, confidence: float) -> float:
        """
        Adjust position size based on regime confidence.
        
        Higher confidence = normal size
        Lower confidence = reduced size
        """
        # Scale from 0.5x to 1.0x based on confidence
        multiplier = 0.5 + (confidence * 0.5)
        return base_size * multiplier
```

---

## 6. Complete Data Flow Example

```python
"""
Complete example showing data flow from market data to execution
with Market Regime integrated throughout
"""

def main_trading_loop():
    """Complete main loop with all engines."""
    
    # Initialize all engines
    market_data = MarketDataService()
    indicator_engine = IndicatorEngine()
    pattern_engine = PatternEngine()
    strategy_engine = StrategyEngine()
    regime_engine = MarketRegimeEngine()
    decision_engine = DecisionEngine(regime_engine)
    quality_engine = QualityScoreEngine(regime_engine)
    execution_engine = ExecutionEngine()
    main_window = MainWindow()
    
    while True:
        # Step 1: Fetch market data
        ohlc = market_data.fetch_ohlc(symbol='XAUUSD', timeframe='1H')
        close = ohlc['close'].iloc[-1]
        
        # Step 2: Calculate indicators
        ema50 = indicator_engine.calculate_ema(ohlc['close'], 50).iloc[-1]
        ema200 = indicator_engine.calculate_ema(ohlc['close'], 200).iloc[-1]
        atr14 = indicator_engine.calculate_atr(ohlc, 14).iloc[-1]
        
        # Step 3: EVALUATE MARKET REGIME ⭐
        regime_engine.evaluate(close=close, ema50=ema50, ema200=ema200)
        regime_state = regime_engine.get_state()
        
        # Step 4: Detect pattern
        pattern = pattern_engine.detect(ohlc)
        
        # Step 5: Evaluate entry conditions
        conditions = strategy_engine.check_entry_conditions(
            pattern=pattern,
            close=close,
            ema50=ema50,
            atr14=atr14
        )
        
        # Step 6: Make decision (using regime context)
        decision = decision_engine.make_decision(conditions)
        
        # Step 7: Calculate quality (considering regime alignment)
        decision['quality_score'] = quality_engine.calculate_quality({
            'pattern_score': 8 if conditions['pattern_valid'] else 0,
            'momentum_score': 8 if conditions['has_momentum'] else 0,
            'regime_confidence': regime_state['confidence']
        })
        
        # Step 8: Update UI with all information
        main_window.update_market_data(close, {'ema50': ema50, 'ema200': ema200, 'atr14': atr14})
        main_window.update_market_regime(regime_state)  # ⭐
        main_window.update_pattern_status(pattern)
        main_window.update_entry_conditions(conditions)
        main_window.update_quality_score({'entry_quality_score': decision['quality_score']})
        
        # Step 9: Execute if appropriate
        if decision['quality_score'] >= 7.0:
            execution_engine.execute_long(
                entry_price=close,
                stop_loss=decision['stop_loss'],
                take_profit=decision['take_profit'],
                volume=decision['volume']
            )
        
        # Sleep until next bar
        sleep_until_next_bar()
```

---

## 7. Common Regime-Based Decisions

```python
"""
Common decision patterns based on market regime
"""

def make_regime_aware_decision(conditions, regime_state):
    """Make trading decision with regime awareness."""
    
    regime = regime_state['regime']
    confidence = regime_state['confidence']
    
    # Base decision: are entry conditions met?
    conditions_met = all([
        conditions['pattern_valid'],
        conditions['breakout_confirmed'],
        conditions['above_ema50'],
        conditions['has_momentum'],
        conditions['cooldown_ok']
    ])
    
    if not conditions_met:
        return 'NO_TRADE'
    
    # All conditions met, apply regime filter
    
    # BULL REGIME: Maximum confidence
    if regime == 'BULL':
        quality_adjustment = 2.0
        risk_multiplier = 1.0
        decision_probability = min(0.95, confidence * 1.2)
    
    # BEAR REGIME: Long trades risky
    elif regime == 'BEAR':
        quality_adjustment = -2.0  # Heavy penalty
        risk_multiplier = 2.0       # Use half size
        decision_probability = min(0.5, confidence * 0.5)
    
    # RANGE REGIME: Uncertain
    else:
        quality_adjustment = -0.5
        risk_multiplier = 1.5
        decision_probability = min(0.7, confidence * 0.8)
    
    # Final decision based on adjusted probability
    if decision_probability > 0.60:
        return {
            'decision': 'ENTER_LONG',
            'quality_adjustment': quality_adjustment,
            'size_multiplier': 1.0 / risk_multiplier,
            'regime_reason': f'{regime} market with {confidence*100:.0f}% confidence'
        }
    else:
        return {
            'decision': 'NO_TRADE',
            'reason': f'Regime probability too low: {decision_probability:.0%}'
        }
```

---

## Summary

Key Integration Points:

1. **Main Loop**: Call `regime_engine.evaluate()` every bar
2. **Decision Engine**: Use regime for quality adjustments
3. **Quality Engine**: Weight regime alignment at 40%
4. **Position Sizing**: Scale position based on regime confidence
5. **Risk Management**: Apply stricter stops in conflicting regimes
6. **UI Display**: Show regime state in Market Regime panel
7. **Backtest Analysis**: Include regime in "Why No Trade" analyzer
8. **Execution Filtering**: Optionally skip trades that contradict regime

The Market Regime provides valuable context without replacing the core decision logic.


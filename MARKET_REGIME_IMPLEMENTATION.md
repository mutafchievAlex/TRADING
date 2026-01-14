# Market Regime Implementation Guide

## Overview

This document describes the Market Regime feature implementation, which determines the higher-level market environment (Bull, Bear, Range) to provide directional bias for decision-making.

**Critical Note**: Market Regime is **CONTEXT ONLY**. It does NOT issue trade commands and does NOT execute orders. It provides filtering and scoring inputs only.

---

## What is Market Regime?

Market Regime identifies the current market trend environment:

- **BULL**: Close > EMA50 AND EMA50 > EMA200 → Uptrend environment, long setups favored
- **BEAR**: Close < EMA50 AND EMA50 < EMA200 → Downtrend environment, short setups favored  
- **RANGE**: Neither condition met → Range-bound, trend-following reduced probability

The regime changes only on bar close, matching the current chart timeframe (1H for XAUUSD).

---

## Files Created

### [src/engines/market_regime_engine.py](src/engines/market_regime_engine.py)

**Purpose**: Calculates market regime state and confidence metrics

**Key Classes**:
- `RegimeType` - Enum with BULL, BEAR, RANGE states
- `MarketRegimeEngine` - Main engine class

**Main Methods**:

```python
def evaluate(close: float, ema50: float, ema200: float) -> Tuple[RegimeType, float]
```
Evaluates current regime based on price and EMAs.  
Returns: (regime_type, confidence_score)

```python
def get_state() -> Dict
```
Returns full regime state with metrics:
```python
{
    'regime': 'BULL' | 'BEAR' | 'RANGE',
    'confidence': 0.0-1.0,
    'ema50_ema200_distance': percentage,  # EMA separation
    'price_ema50_distance': percentage    # Price distance from EMA50
}
```

**Confidence Calculation**:
- Based on EMA50/EMA200 separation (60% weight)
- Based on price distance from EMA50 (40% weight)
- Ranges from 0.0 to 1.0
- Stronger trend = higher confidence

---

## UI Integration

### Market Data Tab

A new **Market Regime** panel was added in the top summary block of the Market Data tab.

**Panel Location**: Between Current Price and Indicators

**Displayed Fields**:
1. **Regime**: Shows regime type with emoji and colored text
   - 📈 BULL (Green)
   - 📉 BEAR (Red)
   - 📊 RANGE (Gray)

2. **Confidence**: Percentage (0-100%) indicating signal strength

3. **EMA Distance**: Relative distance between EMA50 and EMA200 (percentage)
   - Positive = EMA50 above EMA200
   - Negative = EMA50 below EMA200

4. **Price Distance**: Distance of price from EMA50 (percentage)
   - Positive = Price above EMA50
   - Negative = Price below EMA50

### Update Method

```python
def update_market_regime(self, regime_state: dict = None)
```

Call this method to update the Market Regime display:

```python
# In your main application loop:
regime_state = regime_engine.get_state()
main_window.update_market_regime(regime_state)
```

---

## Integration with Other Engines

### With Decision Engine

Market Regime provides context for decision scoring:

**Interaction Rules**:
- If BULL and decision == ENTER_SHORT → Apply negative score (contradicts regime)
- If BEAR and decision == ENTER_LONG → Apply negative score (contradicts regime)
- If RANGE → Apply volatility penalty (uncertain environment)

**Implementation**: The decision engine should check regime state and adjust quality scores accordingly.

### With Quality Engine

Quality Score weighting:
```python
overall_quality = (pattern_alignment * 0.3 + 
                  regime_alignment * 0.4 + 
                  momentum_alignment * 0.3)
```

Regime alignment component should:
- Award points when decision aligns with regime direction
- Penalize points when decision opposes regime

### With Indicator Engine

No direct integration - Market Regime uses outputs from:
- EMA50 (from indicator_engine)
- EMA200 (from indicator_engine)
- Close price (from market_data_service)

---

## Implementation Checklist

### ✅ Code Components

- [x] Created `market_regime_engine.py` with full logic
- [x] Added Market Regime panel to UI (main_window.py)
- [x] Implemented `update_market_regime()` display method
- [x] Color coding by regime type (green/red/gray)
- [x] Display all 4 metrics (regime, confidence, distances)

### ⚠️ Integration Tasks (TODO)

These tasks must be completed in other files:

**1. Main Application Loop** (src/main.py)
```python
# Initialize regime engine
from src.engines.market_regime_engine import MarketRegimeEngine

regime_engine = MarketRegimeEngine()

# In your main loop:
regime_state = regime_engine.evaluate(close, ema50, ema200)
main_window.update_market_regime(regime_state)
```

**2. Decision Engine Integration** (src/engines/decision_engine.py)
- Import MarketRegimeEngine or use regime state from main
- Check regime before issuing decisions
- Apply penalties for contradictory trades
- Store regime state with decision for audit trail

**3. Quality Engine Integration** (src/engines/quality_engine.py or similar)
- Weight regime alignment in overall score
- Increase score when aligned with regime
- Decrease score when opposing regime
- Apply volatility penalty in RANGE regime

**4. Backtest Window** (src/ui/backtest_window.py)
- Display regime state in "Why No Trade" analyzer
- Show how regime affected quality scoring
- Include regime metrics in trade analysis

---

## Example Usage

### Basic Initialization

```python
from src.engines.market_regime_engine import MarketRegimeEngine

# Create engine
regime_engine = MarketRegimeEngine(min_ema_distance_percent=0.1)

# Evaluate on each bar close
regime, confidence = regime_engine.evaluate(
    close=price_close,
    ema50=indicators['ema50'],
    ema200=indicators['ema200']
)

# Get full state
state = regime_engine.get_state()
print(f"Regime: {state['regime']}")
print(f"Confidence: {state['confidence']:.2f}")
```

### Display in UI

```python
# In your update loop
regime_state = regime_engine.get_state()
main_window.update_market_regime(regime_state)
```

### Decision Impact

```python
# In decision engine
if regime_state['regime'] == 'BULL' and decision == 'ENTER_SHORT':
    # Penalize short setup in bullish regime
    quality_adjustment = -1.5
    
elif regime_state['regime'] == 'BEAR' and decision == 'ENTER_LONG':
    # Penalize long setup in bearish regime
    quality_adjustment = -1.5
    
elif regime_state['regime'] == 'RANGE':
    # Penalize trend-following in range market
    quality_adjustment = -0.5
else:
    # Reward aligned decisions
    quality_adjustment = +0.5
```

---

## Forbidden Behaviors

The following MUST NOT happen:

❌ Regime directly triggers trade execution
❌ Regime overrides decision engine verdicts  
❌ Regime changes intra-bar (only on bar close)
❌ Regime issues ENTRY/EXIT commands directly
❌ Regime logic in execution_engine.py

**Correct Role**: Regime is input to decision/quality engines, never a command issuer.

---

## Acceptance Criteria

All items must be verified before considering feature complete:

- [ ] Market Regime visible in Live trading view
- [ ] Market Regime visible in Backtest window  
- [ ] Regime never directly triggers trades
- [ ] Regime only updates on bar close
- [ ] Confidence score reflects EMA separation
- [ ] Colors update correctly (green/red/gray)
- [ ] Decision engine uses regime for quality adjustment
- [ ] Quality engine weights regime alignment
- [ ] Regime state persisted across app restarts (if using state file)
- [ ] No performance degradation from regime calculations
- [ ] All unit tests pass

---

## Testing the Implementation

### Manual Test: Visual Verification

1. Start the application in development mode
2. Go to Market Data tab
3. Verify Market Regime panel appears below Current Price
4. In a BULL market: should show 📈 BULL in green
5. In a BEAR market: should show 📉 BEAR in red
6. In RANGE: should show 📊 RANGE in gray
7. Confidence should increase/decrease with EMA separation

### Unit Test: Regime Evaluation

```python
from src.engines.market_regime_engine import MarketRegimeEngine, RegimeType

engine = MarketRegimeEngine()

# Test BULL condition
regime, confidence = engine.evaluate(close=2000, ema50=1990, ema200=1950)
assert regime == RegimeType.BULL
assert confidence > 0.0

# Test BEAR condition
regime, confidence = engine.evaluate(close=1900, ema50=1910, ema200=1950)
assert regime == RegimeType.BEAR
assert confidence > 0.0

# Test RANGE condition
regime, confidence = engine.evaluate(close=2000, ema50=1990, ema200=2010)
assert regime == RegimeType.RANGE
assert confidence == 0.0
```

### Integration Test: UI Update

```python
# Verify UI updates correctly
regime_state = {
    'regime': 'BULL',
    'confidence': 0.75,
    'ema50_ema200_distance': 0.5,
    'price_ema50_distance': 0.3
}

main_window.update_market_regime(regime_state)

# Verify labels
assert '📈' in main_window.lbl_regime.text()
assert 'BULL' in main_window.lbl_regime.text()
assert '75.0%' in main_window.lbl_regime_confidence.text()
```

---

## Troubleshooting

**Issue**: Market Regime shows RANGE always

**Solution**: Verify EMA values are being calculated correctly. Check that ema50 and ema200 are not NaN or zero. Enable debug logging:
```python
import logging
logging.getLogger('market_regime_engine').setLevel(logging.DEBUG)
```

**Issue**: Confidence always 0.0

**Solution**: Confidence is 0.0 in RANGE regime. This is correct. If confidence should be > 0, check that regime is BULL or BEAR.

**Issue**: UI doesn't update

**Solution**: Ensure `update_market_regime()` is being called in your main loop. Check that regime_engine.get_state() is returning valid data.

---

## Performance Considerations

Market Regime calculations are lightweight:
- Uses only 3 numeric inputs (close, ema50, ema200)
- Simple arithmetic operations (no loops, no expensive calculations)
- Safe for real-time updates on every bar close
- No database queries or I/O operations

Expected execution time: < 1ms per evaluation

---

## File Dependencies

```
src/engines/market_regime_engine.py
  ├── Used by: src/main.py (main application loop)
  ├── Used by: src/engines/decision_engine.py (decision context)
  ├── Used by: src/engines/quality_engine.py (quality scoring)
  └── Used by: src/ui/main_window.py (display via update_market_regime)

src/ui/main_window.py
  ├── Display: Market Regime panel in Market Data tab
  ├── Method: update_market_regime(regime_state)
  └── Called from: src/main.py in update loop
```

---

## Summary

Market Regime provides essential market context for the trading system:

✅ **What it does**: Identifies BULL/BEAR/RANGE environments, provides confidence metrics  
✅ **What it doesn't do**: Issue trades, execute orders, override decisions  
✅ **Where it displays**: Market Data tab (top summary block)  
✅ **How it integrates**: Decision and Quality engines use regime for scoring

The implementation is complete and ready for integration into the decision/quality engine pipeline.


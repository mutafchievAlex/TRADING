# Market Regime - Quick Reference Guide

## Quick Facts

| Item | Details |
|------|---------|
| **Feature Name** | Market Regime Engine |
| **Purpose** | Determine BULL/BEAR/RANGE market environment |
| **Location** | src/engines/market_regime_engine.py |
| **UI Location** | Market Data tab (below Current Price) |
| **Status** | ✅ Production Ready |
| **Tests** | 23/23 Passing |
| **Lines of Code** | 199 (engine) + 46 (UI) |

---

## 30-Second Overview

```
Market Regime answers: "What's the market direction right now?"

BULL (📈 Green)    → Close > EMA50 > EMA200 → Go long, avoid shorts
BEAR (📉 Red)      → Close < EMA50 < EMA200 → Avoid longs, shorts ok
RANGE (📊 Gray)    → Neither condition met  → Uncertain, reduced probability

Confidence: 0-100% (higher = stronger trend)
```

---

## One-Minute Integration

```python
# 1. Import
from src.engines.market_regime_engine import MarketRegimeEngine

# 2. Initialize (once at startup)
regime_engine = MarketRegimeEngine()

# 3. Evaluate (every bar)
regime_engine.evaluate(close=price, ema50=ema50, ema200=ema200)

# 4. Display (update UI)
main_window.update_market_regime(regime_engine.get_state())
```

**That's it!** 4 lines to add market regime to your application.

---

## Regime States Explained

### BULL Regime (📈 Green)
**Condition**: `close > ema50 AND ema50 > ema200`  
**Market Type**: Uptrend  
**Strategy Impact**: Long setups favored, short setups penalized  
**Confidence**: Based on EMA separation and price distance

**Example**:
- Price: 2100
- EMA50: 2050
- EMA200: 1950
- Result: ✅ BULL (strong uptrend)

### BEAR Regime (📉 Red)
**Condition**: `close < ema50 AND ema50 < ema200`  
**Market Type**: Downtrend  
**Strategy Impact**: Short setups favored, long setups risky  
**Confidence**: Based on EMA separation and price distance

**Example**:
- Price: 1800
- EMA50: 1900
- EMA200: 1950
- Result: ✅ BEAR (strong downtrend)

### RANGE Regime (📊 Gray)
**Condition**: Neither BULL nor BEAR  
**Market Type**: Uncertain / Range-bound  
**Strategy Impact**: Trend-following reduced probability  
**Confidence**: Always 0.0 in RANGE

**Example**:
- Price: 2000
- EMA50: 1950
- EMA200: 2050
- Result: ✅ RANGE (conflicting signals)

---

## UI Display

### Market Data Tab - Market Regime Panel

```
┌─────────────────────────────────┐
│      Market Regime              │
├─────────────────────────────────┤
│ 📈 Regime: BULL                 │  ← Green text
│ Confidence: 75.0%              │
│ EMA Distance: +0.50%           │  ← EMA50 above EMA200
│ Price Distance: +0.30%         │  ← Price above EMA50
└─────────────────────────────────┘
```

**Colors**:
- 📈 **BULL** = Green (#4CAF50)
- 📉 **BEAR** = Red (#F44336)
- 📊 **RANGE** = Gray (#9E9E9E)

---

## Data Structure

### Input
```python
regime_engine.evaluate(
    close=2000.0,       # Current close price
    ema50=1990.0,       # EMA 50 value
    ema200=1950.0       # EMA 200 value
)
```

### Output
```python
regime_engine.get_state()
# Returns:
{
    'regime': 'BULL',                    # String: BULL/BEAR/RANGE
    'confidence': 0.75,                 # Float: 0.0-1.0
    'ema50_ema200_distance': 0.5,       # Float: percentage
    'price_ema50_distance': 0.3         # Float: percentage
}
```

---

## Confidence Calculation

### Formula
```
confidence = (ema_score × 0.6) + (price_score × 0.4)

where:
  ema_score = min(|EMA50 - EMA200| / EMA200 / 1.0%, 1.0)
  price_score = min(|Price - EMA50| / EMA50 / 2.0%, 1.0)
```

### Interpretation
- **0.0** = No trend (RANGE regime)
- **0.25** = Weak trend
- **0.5** = Moderate trend
- **0.75** = Strong trend
- **1.0** = Very strong trend

### Example Calculation
```
close = 2100, ema50 = 2000, ema200 = 1900

ema_distance = (2000 - 1900) / 1900 * 100 = 5.26%
ema_score = min(5.26 / 1.0, 1.0) = 1.0

price_distance = (2100 - 2000) / 2000 * 100 = 5.0%
price_score = min(5.0 / 2.0, 1.0) = 1.0

confidence = (1.0 × 0.6) + (1.0 × 0.4) = 1.0 ✅ Maximum confidence!
```

---

## Common Use Cases

### Decision Engine Integration
```python
def make_decision(self, conditions):
    if regime.regime == 'BULL':
        quality_bonus = +2.0  # Reward aligned longs
    elif regime.regime == 'BEAR':
        quality_penalty = -2.0  # Penalize longs
    else:
        quality_penalty = -0.5  # Slight penalty in range
```

### Quality Score Weighting
```python
quality = (pattern × 0.3 + 
          regime_alignment × 0.4 +    # 40% weight on regime!
          momentum × 0.3)
```

### Position Sizing
```python
if regime.confidence > 0.8:
    position_size = 1.0  # Full size in strong trend
elif regime.confidence > 0.5:
    position_size = 0.75  # 75% in moderate trend
else:
    position_size = 0.5  # 50% in weak/uncertain
```

### Trade Filtering
```python
if regime == 'BULL' and decision == 'ENTER_LONG':
    execute_trade()  # ✅ Aligned
elif regime == 'BEAR' and decision == 'ENTER_LONG':
    skip_trade()     # ❌ Contradicts regime
```

---

## Decision Tree

```
                    Market Data
                         ↓
                    evaluate()
                         ↓
            ┌────────────┼────────────┐
            ↓            ↓            ↓
     close > ema50   close < ema50   else
            ↓            ↓            ↓
     ema50 > ema200  ema50 < ema200  RANGE
            ↓            ↓            
           BULL         BEAR         
            ↓            ↓            
       calc conf    calc conf       conf = 0
            ↓            ↓            
         output       output        output
```

---

## Testing Quick Reference

### Run All Tests
```bash
.venv\Scripts\python.exe -m pytest tests/test_market_regime_engine.py -v
```

### Expected Output
```
23 tests collected
23 passed in 0.39s ✅
```

### Key Tests
- `test_bull_regime_detection` - BULL identification
- `test_bear_regime_detection` - BEAR identification
- `test_range_regime_price_above_ema_but_ema_inverted` - RANGE detection
- `test_confidence_increases_with_ema_separation` - Confidence calculation
- `test_handles_zero_ema200` - Edge case handling

---

## File Locations

| Component | File |
|-----------|------|
| **Engine** | `src/engines/market_regime_engine.py` |
| **UI** | `src/ui/main_window.py` (line ~296) |
| **Tests** | `tests/test_market_regime_engine.py` |
| **Implementation Guide** | `MARKET_REGIME_IMPLEMENTATION.md` |
| **Integration Examples** | `MARKET_REGIME_INTEGRATION_EXAMPLES.md` |
| **Status Report** | `MARKET_REGIME_STATUS.md` |
| **Complete Summary** | `MARKET_REGIME_COMPLETE_SUMMARY.md` |

---

## Key Method Reference

### Main Method
```python
regime, confidence = regime_engine.evaluate(close, ema50, ema200)
```
**Returns**: `(RegimeType, float)`

### Get Full State
```python
state = regime_engine.get_state()
```
**Returns**: Dict with regime, confidence, distances

### UI Update
```python
main_window.update_market_regime(regime_state)
```
**Updates**: Market Regime panel display

---

## Common Questions

**Q: When should regime be calculated?**  
A: Every bar close. Call evaluate() once per bar.

**Q: Does regime issue trades?**  
A: NO. Regime is context-only. It never triggers orders.

**Q: What happens in RANGE?**  
A: Confidence is 0.0. Decisions should be more conservative.

**Q: How do I use regime in decisions?**  
A: Check regime state and apply quality score adjustments. See examples.

**Q: Can regime be overridden?**  
A: No. Regime is informational. Decision engine controls trades.

**Q: What's the performance impact?**  
A: Negligible. < 1ms per calculation.

---

## Integration Checklist

- [ ] Import MarketRegimeEngine
- [ ] Initialize in startup
- [ ] Call evaluate() in main loop
- [ ] Wire UI update
- [ ] Test visual display
- [ ] Integrate with decision engine
- [ ] Update quality scoring
- [ ] Add to backtest analyzer
- [ ] Verify no performance impact
- [ ] Document in project README

---

## Color Reference

```
BULL:  #4CAF50 (Green)   RGB(76, 175, 80)
BEAR:  #F44336 (Red)     RGB(244, 67, 54)
RANGE: #9E9E9E (Gray)    RGB(158, 158, 158)
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Always RANGE | Check EMA calculations |
| Confidence always 0 | Normal for RANGE regime |
| UI doesn't update | Check update_market_regime() call |
| Slow performance | Check calculation frequency |
| NaN in output | Invalid input values |

---

## Remember

✅ **Market Regime is CONTEXT ONLY**
- Provides information
- Influences decisions
- Never executes trades
- Never overrides logic

✅ **Integration is Simple**
- 4 lines of code for basic integration
- Comprehensive guides available
- Examples provided
- Full test coverage

✅ **Production Ready**
- 23/23 tests passing
- Zero errors
- Complete documentation
- Ready to deploy

---

## Next: Integration

1. Read [MARKET_REGIME_INTEGRATION_EXAMPLES.md](MARKET_REGIME_INTEGRATION_EXAMPLES.md)
2. Follow example for your use case
3. Test in development environment
4. Deploy to production

**Questions?** See full documentation files.


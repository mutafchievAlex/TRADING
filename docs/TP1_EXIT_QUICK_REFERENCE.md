# TP1 Exit Decision Engine - Quick Reference

## What This Does
Prevents premature exits after TP1 is reached by intelligently deciding whether to:
- **HOLD**: Continue holding (minor pullback, bullish regime)
- **WAIT_NEXT_BAR**: Wait for confirmation (single-bar pullback)
- **EXIT_TRADE**: Exit (confirmed failure: 2 bars below, momentum break, regime flip, deep retrace)

---

## How It Works

### Decision Order (Priority)
1. **EXIT Conditions** checked first (momentum, regime, 2-bar confirmation, deep retrace)
2. **HOLD Conditions** checked next (micro-pullback, above TP1, bullish)
3. **WAIT Conditions** checked last (single-bar pullback with momentum)

### Key Thresholds
| Rule | Threshold | Example |
|------|-----------|---------|
| Micro-pullback | ≤ 0.25 × ATR | With ATR=5: ≤ 1.25 pips |
| Deep retracement | ≥ 0.5 × ATR | With ATR=5: ≥ 2.5 pips |
| SL min offset | 0.2 × ATR | With ATR=5: 1.0 pip |

---

## Integration Points

### 1. In Strategy Engine
```python
from src.engines.strategy_engine import StrategyEngine

engine = StrategyEngine()
# When TP1 is reached:
decision = engine.evaluate_post_tp1_decision(
    current_price=2105.0,
    entry_price=2100.0,
    stop_loss=2095.0,
    tp1_price=2110.0,
    atr_14=5.0,
    market_regime="BULL",
    momentum_state="STRONG",
    last_closed_bar={'close': 2109.0, ...},
    bars_since_tp1=1
)
# Returns: {'decision': 'HOLD', 'should_exit': False, 'reason': '...', 'new_stop_loss': None}
```

### 2. In State Manager
```python
position = {
    'ticket': 123456,
    'entry_price': 2100.0,
    'tp1_price': 2110.0,
    'tp1_reached': True,              # ← Newly tracked
    'post_tp1_decision': 'HOLD',      # ← Newly tracked
    'bars_held_after_tp1': 2,         # ← Newly tracked
    'tp1_exit_reason': 'Micro-pullback allowed',  # ← Newly tracked
}
```

### 3. In UI (Position Tab)
```
Position Tab → Click on row → TP1 Exit Decision panel shows:
┌─────────────────────────────┐
│ TP1 Exit Decision           │
├─────────────────────────────┤
│ State: TP1_REACHED          │
│ Decision: HOLD              │ (Green background)
│ Reason: Micro-pullback...   │
│ Bars After TP1: 2           │
└─────────────────────────────┘
```

---

## Decision Logic Examples

### Example 1: Micro-Pullback
```
TP1 reached at 2110.0
Price drops to 2109.0 (1.0 pip, < 0.25 × 5 = 1.25 ATR)
→ DECISION: HOLD (minor retracement within volatility)
```

### Example 2: Single-Bar Pullback
```
TP1 reached at 2110.0
Bar 1 close: 2105.0 (5 pips below TP1, > entry 2100.0)
Momentum: MODERATE
→ DECISION: WAIT_NEXT_BAR (waiting for confirmation)
```

### Example 3: Confirmed Failure
```
TP1 reached at 2110.0
Bar 1 close: 2109.0
Bar 2 close: 2108.0 (2 consecutive bars below TP1)
→ DECISION: EXIT_TRADE (failure confirmed)
```

### Example 4: Deep Retracement
```
TP1 reached at 2110.0
Current price: 2105.0 (5 pips below TP1)
ATR = 8.0 (0.5 × 8 = 4.0 threshold)
Retrace 5.0 ≥ 4.0
→ DECISION: EXIT_TRADE (deep retracement)
```

### Example 5: Regime Change
```
TP1 reached at 2110.0 (in BULL regime)
Regime changes to RANGE
Bar close: 2108.0
→ DECISION: EXIT_TRADE (regime no longer supportive)
```

---

## Testing

All 14 unit tests pass:
```bash
cd C:\Users\mutaf\TRADING
.venv\Scripts\python.exe -m pytest tests/test_tp1_exit_decision_engine.py -v
```

Coverage:
- HOLD scenarios (3 tests)
- WAIT scenarios (1 test)
- EXIT scenarios (5 tests)
- Edge cases (2 tests)
- SL calculation (2 tests)
- Special guards (1 test)

---

## Decision States (Enums)

### PostTP1Decision
```python
NOT_REACHED = "NOT_REACHED"    # TP1 not hit yet
HOLD = "HOLD"                  # Continue holding
WAIT_NEXT_BAR = "WAIT_NEXT_BAR"  # Wait for confirmation
EXIT_TRADE = "EXIT_TRADE"      # Exit now
```

### MomentumState
```python
STRONG = "STRONG"
MODERATE = "MODERATE"
BROKEN = "BROKEN"
UNKNOWN = "UNKNOWN"
```

### MarketRegime
```python
BULL = "BULL"
RANGE = "RANGE"
BEAR = "BEAR"
UNKNOWN = "UNKNOWN"
```

---

## Files
- **Engine**: `src/engines/tp1_exit_decision_engine.py`
- **Tests**: `tests/test_tp1_exit_decision_engine.py`
- **Integration**: 
  - State tracking: `src/engines/state_manager.py`
  - Strategy: `src/engines/strategy_engine.py`
  - Decision: `src/engines/decision_engine.py`
  - UI Display: `src/ui/main_window.py`

---

## Key Methods

### TP1ExitDecisionEngine
```python
evaluate_post_tp1(ctx: TP1EvaluationContext) -> TP1ExitReason
# Returns decision + reason

calculate_sl_after_tp1(entry, tp1, atr, direction) -> float
# Suggests new SL (entry ± 0.2*ATR)

should_update_sl_on_bar_close() -> bool
# Always True (enforces bar-close only)
```

### StrategyEngine
```python
evaluate_post_tp1_decision(...) -> Dict
# Wrapper that maps strings to enums
# Returns {'decision', 'should_exit', 'reason', 'new_stop_loss'}
```

---

## Important Notes

1. **Stateless Design**: Engine doesn't store state; caller must pass all context
2. **Priority Order**: Exit conditions checked before hold conditions (prevents false holds)
3. **Anti-Premature-Exit Guard**: No exit on same bar as TP1 (always HOLD)
4. **Bar-Close Only**: All decisions based on closed bar data, never intrabar
5. **Non-Binding SL**: Suggested SL is optional; caller can override
6. **Independent Positions**: Each position tracked separately

---

## Acceptance Criteria Met ✅

- ✅ Trade does NOT exit on minor pullback after TP1
- ✅ Exit after TP1 only on confirmed failure
- ✅ Behavior identical in live and backtest
- ✅ Multiple positions handled independently
- ✅ All 14 unit tests pass
- ✅ Zero syntax errors
- ✅ Clean architecture maintained
- ✅ Specification matched exactly

---

**Version**: 1.0  
**Status**: Production Ready  
**Last Updated**: January 2026

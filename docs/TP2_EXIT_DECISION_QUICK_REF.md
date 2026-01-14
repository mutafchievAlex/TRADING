# TP2 Exit Decision Engine - Quick Reference

## 🎯 Purpose
Intelligent post-TP2 exit management with **tighter thresholds** than TP1 to protect larger profits while maximizing TP3 capture.

---

## 📊 Key Metrics

| Threshold | TP1 | TP2 | Difference |
|-----------|-----|-----|------------|
| Shallow Pullback | ≤ 0.25 * ATR | ≤ 0.20 * ATR | **20% tighter** |
| Deep Retracement | ≥ 0.50 * ATR | ≥ 0.35 * ATR | **30% tighter** |
| Trailing SL Offset | 0.2 * ATR | 0.3 * ATR | **50% wider** |

---

## 🚦 Decision States

```
HOLD           → Continue toward TP3 (green)
WAIT_NEXT_BAR  → Monitor next bar (orange)
EXIT_TRADE     → Exit immediately (red)
NOT_REACHED    → TP2 not yet hit
```

---

## 🏗️ Structure States

```
HIGHER_LOWS → Bullish structure intact → HOLD
LOWER_LOW   → Structure broken → EXIT
UNKNOWN     → Insufficient history
```

---

## ⚡ Decision Priority (Highest First)

### 1️⃣ EXIT (Checked First)
- ❌ Same bar as TP2 → HOLD (anti-premature)
- ❌ Structure break (LOWER_LOW)
- ❌ Momentum BROKEN
- ❌ Regime flip (RANGE/BEAR)
- ❌ 2 bars below TP2
- ❌ Deep retrace (≥ 0.35*ATR)

### 2️⃣ HOLD
- ✅ Strong trend (close ≥ TP2 + STRONG + BULL)
- ✅ Shallow pullback (≤ 0.2*ATR)
- ✅ Structure intact (HIGHER_LOWS)

### 3️⃣ WAIT
- ⚠️ Momentum softening (MODERATE)
- ⚠️ First close below TP2

### 4️⃣ DEFAULT → HOLD

---

## 📈 Trailing SL Formula

```python
# LONG trade
atr_sl = current_price - (0.3 * ATR)
swing_sl = swing_low - (0.1 * ATR)
trailing_sl = max(atr_sl, swing_sl)

# Lock profit above entry
trailing_sl = max(trailing_sl, entry + 0.1*ATR)
```

**Example:**
- Entry: 2100, TP2: 2120, Current: 2125, ATR: 5
- ATR SL: 2125 - 1.5 = **2123.5**
- Min SL: 2100 + 0.5 = 2100.5 ✓
- **Trailing SL: 2123.5**

---

## 🧪 Test Coverage: 17/17 Passing

```bash
python tests/test_tp2_exit_decision_engine.py
# .................
# Ran 17 tests in 0.002s
# OK
```

**Tests:**
- ✅ Same bar guard
- ✅ 3 HOLD scenarios
- ✅ 2 WAIT scenarios
- ✅ 6 EXIT scenarios
- ✅ 2 Trailing SL tests
- ✅ 3 Edge cases

---

## 💻 Usage in Strategy Engine

```python
from src.engines.tp2_exit_decision_engine import (
    TP2ExitDecisionEngine,
    TP2EvaluationContext,
    PostTP2Decision,
    StructureState
)

# Create engine
tp2_engine = TP2ExitDecisionEngine(logger=logger)

# Build context
ctx = TP2EvaluationContext(
    current_price=2125.0,
    entry_price=2100.0,
    tp2_price=2120.0,
    atr_14=5.0,
    market_regime=MarketRegime.BULL,
    momentum_state=MomentumState.STRONG,
    structure_state=StructureState.HIGHER_LOWS,
    last_closed_bar={'close': 2125.0, ...},
    bars_since_tp2=3
)

# Evaluate
result = tp2_engine.evaluate_post_tp2(ctx)

# Use result
if result.decision == PostTP2Decision.EXIT_TRADE:
    exit_trade(result.reason_text)
elif result.should_trail_sl:
    update_trailing_sl(calculate_trailing_sl_after_tp2(...))
```

---

## 🎨 UI Display (Main Window)

**TP2 Decision Panel** shows:
- **TP2 State**: "Reached" / "Not Reached"
- **TP2 Decision**: HOLD / WAIT / EXIT (color-coded)
- **TP2 Reason**: Human-readable explanation
- **Bars After TP2**: Count since TP2 reached
- **Trailing SL**: Current trailing stop level

---

## 🔍 Example Scenarios

### Strong Trend → HOLD
```
Current: 2123, TP2: 2120, ATR: 5
Momentum: STRONG, Regime: BULL
→ HOLD: "Strong trend continuation after TP2; aiming for TP3"
```

### Momentum Softening → WAIT
```
Current: 2117.5, TP2: 2120, ATR: 10
Retrace: 2.5 (shallow < 2.0, not deep < 3.5)
Momentum: MODERATE
→ WAIT: "Momentum softening but not broken; monitoring"
```

### Deep Retracement → EXIT
```
Current: 2115, TP2: 2120, ATR: 10
Retrace: 5.0 ≥ 0.35*10 = 3.5
→ EXIT: "Deep retracement after TP2: 5.00 >= 0.35*ATR 3.50"
```

### Structure Break → EXIT
```
Current: 2125, TP2: 2120
Structure: LOWER_LOW
→ EXIT: "Market structure broken (lower low)"
```

---

## 📂 Files Modified

1. `src/engines/tp2_exit_decision_engine.py` (NEW, 277 lines)
2. `src/engines/state_manager.py` (6 new TP2 fields)
3. `src/engines/strategy_engine.py` (`evaluate_post_tp2_decision()`)
4. `src/engines/decision_engine.py` (5 new output fields)
5. `src/ui/main_window.py` (TP2 Decision Panel)
6. `tests/test_tp2_exit_decision_engine.py` (NEW, 17 tests)

---

## ✅ Status: COMPLETE

**All Tests Passing** ✓ **State Tracking** ✓ **Strategy Integration** ✓ **UI Display** ✓

Ready for backtesting and live trading.

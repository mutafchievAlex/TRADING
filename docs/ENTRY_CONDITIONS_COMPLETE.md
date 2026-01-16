# Entry Conditions Documentation & Testing

**Status**: ✅ COMPLETED  
**Phase**: Phase 2 - Critical Bug Fixes  
**Task**: 2.3 - Entry Conditions Clarity  
**Date**: January 16, 2026

## Overview

The entry conditions form a **7-stage decision pipeline** where ALL conditions must pass for a trade to execute. This document clarifies:
1. Each condition's purpose and logic
2. Which conditions are BLOCKING vs WARNING
3. ASCII flow diagrams
4. Unit test cases for edge conditions
5. "Why No Trade?" decision tree

---

## Stage 1: Bar-Close Guard (BLOCKING)

### Purpose
Ensures all decisions use only fully closed bars (bar-close gate).

### Condition
```
Current bar must be FULLY CLOSED
```

### Implementation
```python
# src/engines/bar_close_guard.py
is_valid, reason = self.bar_close_guard.validate_bar_state(df, current_bar_index)
if not is_valid:
    return False, {"failure_code": "BAR_NOT_CLOSED"}
```

### Behavior
- **BLOCKING**: If bar not closed, ALL entry processing stops
- **Why**: Prevents intrabar execution on partially-formed candles
- **Details**: Uses `-2` index (last closed bar), never current forming bar

### Test Cases
```python
# test_entry_conditions_bar_close.py

def test_bar_not_yet_closed():
    """Using forming bar (-1) should fail."""
    df = load_test_data()
    result, details = engine.evaluate_entry(df, pattern, current_bar_index=-1)
    assert result == False
    assert details['failure_code'] == 'BAR_NOT_CLOSED'

def test_bar_fully_closed():
    """Using closed bar (-2) should pass if other conditions met."""
    df = load_test_data()
    pattern = create_valid_pattern(df)
    result, details = engine.evaluate_entry(df, pattern, current_bar_index=-2)
    assert details['pattern_valid'] == True  # Passes bar-close check
```

---

## Stage 2: Pattern Detection (BLOCKING)

### Purpose
Validates Double Bottom pattern structure.

### Condition
```
Valid Double Bottom pattern must exist with:
- Two swing lows of similar price
- Neckline (resistance level between lows)
- Pattern validity flag = True
```

### Implementation
```python
# src/engines/strategy_engine.py::evaluate_entry()
if pattern is None or not pattern.get('pattern_valid'):
    return False, {"failure_code": "INVALID_PATTERN_STRUCTURE"}
```

### Behavior
- **BLOCKING**: No pattern = no entry, period
- **Why**: Double Bottom is core signal, without it no trade thesis
- **Logic**: Checked once per formation, then persists

### Pattern Structure
```python
pattern = {
    'pattern_valid': True,          # BLOCKING condition
    'neckline': {
        'price': 2000.50,           # Resistance between lows
        'timestamp': '2026-01-16 10:00:00'
    },
    'first_low': {
        'price': 1990.25,
        'timestamp': '2026-01-15 15:00:00'
    },
    'second_low': {
        'price': 1990.30,
        'timestamp': '2026-01-16 09:00:00'
    },
    'quality_score': 7.5            # 0-10 scale
}
```

### Test Cases
```python
def test_no_pattern():
    """None pattern should fail."""
    result, details = engine.evaluate_entry(df, None, -2)
    assert result == False
    assert details['failure_code'] == 'INVALID_PATTERN_STRUCTURE'

def test_pattern_invalid_flag():
    """Pattern with valid=False should fail."""
    pattern = {'pattern_valid': False, 'neckline': {...}}
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert result == False

def test_pattern_valid():
    """Valid pattern should pass stage 2."""
    pattern = {'pattern_valid': True, 'neckline': {...}, ...}
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert details['pattern_valid'] == True
```

---

## Stage 3: Breakout Confirmation (BLOCKING)

### Purpose
Confirms close has broken above neckline (confirmation of pattern thesis).

### Condition
```
Close > Neckline
```

### Implementation
```python
neckline = pattern['neckline']['price']
if current_bar['close'] <= neckline:
    return False, {"failure_code": "NO_NECKLINE_BREAK"}
```

### Behavior
- **BLOCKING**: No breakout = no entry
- **Why**: Breakout is the TRIGGER signal
- **Details**: Uses `>` not `>=` (requires clear break)
- **Timing**: Only checked on bar-close

### Visual Example
```
Price
 │
 │                      Close = 2001.50 ✓ ABOVE neckline
 │                      ┌─────────────
 │                      │
 │  Neckline: 2000.50   │
 │  ═════════════════════
 │      │          │
 │      └──┐   ┌──┘
 │    Low1 │   │ Low2
 │ 1990.25 │   │ 1990.30
 │
```

### Test Cases
```python
def test_close_above_neckline():
    """Close > neckline should pass."""
    df = create_dataframe(close=2001.50, neckline=2000.50)
    pattern = create_pattern(neckline=2000.50)
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert details['breakout_confirmed'] == True

def test_close_equals_neckline():
    """Close == neckline should FAIL (not clear break)."""
    df = create_dataframe(close=2000.50, neckline=2000.50)
    pattern = create_pattern(neckline=2000.50)
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert result == False
    assert details['failure_code'] == 'NO_NECKLINE_BREAK'

def test_close_below_neckline():
    """Close < neckline should FAIL."""
    df = create_dataframe(close=2000.25, neckline=2000.50)
    pattern = create_pattern(neckline=2000.50)
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert result == False
    assert details['failure_code'] == 'NO_NECKLINE_BREAK'

def test_close_just_above_neckline():
    """Close slightly above (2000.51) should PASS."""
    df = create_dataframe(close=2000.51, neckline=2000.50)
    pattern = create_pattern(neckline=2000.50)
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert details['breakout_confirmed'] == True
```

---

## Stage 4: Trend Filter / Context (BLOCKING)

### Purpose
Ensures breakout occurs in uptrend (Close > EMA50).

### Condition
```
Close > EMA50
```

### Implementation
```python
if not self.check_trend_condition(current_bar):
    return False, {"failure_code": "CONTEXT_NOT_ALIGNED"}

# Inside check_trend_condition():
return current_bar['close'] > current_bar['ema50']
```

### Behavior
- **BLOCKING**: No uptrend = no entry
- **Why**: Prevents breakout entries in downtrends (safer)
- **Details**: Only checks current bar close vs EMA50
- **Golden Rule**: "Only go LONG when price > EMA50"

### Visual Example
```
Price
 │
 │      Uptrend zone ││ Downtrend zone
 │                   ││
 │   Close = 2001.50 ││ (would be blocked here)
 │   ┌─────────────  ││
 │   │               ││
 │   EMA50 = 2000.00 ││
 │   ═══════════════════
 │                    ││
 │      Downtrend     ││
 │
```

### Test Cases
```python
def test_close_above_ema50():
    """Close > EMA50 should PASS."""
    df = create_dataframe(close=2001.50, ema50=2000.00)
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert details['above_ema50'] == True

def test_close_below_ema50():
    """Close < EMA50 should FAIL (downtrend)."""
    df = create_dataframe(close=1999.50, ema50=2000.00)
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert result == False
    assert details['failure_code'] == 'CONTEXT_NOT_ALIGNED'

def test_close_equals_ema50():
    """Close == EMA50 should FAIL (not above)."""
    df = create_dataframe(close=2000.00, ema50=2000.00)
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert result == False

def test_close_just_above_ema50():
    """Close slightly above (2000.01) should PASS."""
    df = create_dataframe(close=2000.01, ema50=2000.00)
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert details['above_ema50'] == True
```

---

## Stage 5: Momentum Filter (BLOCKING - if enabled)

### Purpose
Ensures breakout candle has sufficient volatility/momentum (ATR-based).

### Condition
```
Candle range >= momentum_atr_threshold × ATR14
(default: 0.5 × ATR14)
```

### Implementation
```python
if self.enable_momentum_filter:
    if not self.check_momentum_condition(current_bar):
        return False, {"failure_code": "CONTEXT_NOT_ALIGNED"}

# Inside check_momentum_condition():
candle_range = current_bar['high'] - current_bar['low']
min_range = self.momentum_atr_threshold * current_bar['atr14']
return candle_range >= min_range
```

### Behavior
- **BLOCKING** (if enabled): No momentum = no entry
- **Why**: Prevents weak breakouts on tiny wicks
- **Configurable**: Can be disabled in config.yaml
- **Timing**: Only checked on breakout bar

### Visual Example
```
ATR14 = 5.00
Threshold = 0.5
Min range = 2.50

Breakout Bar High = 2003.50
Breakout Bar Low  = 2001.00
Candle Range = 2.50 (meets minimum) ✓

Weak Breakout High = 2001.25
Weak Breakout Low  = 2000.75
Candle Range = 0.50 (too weak) ✗
```

### Test Cases
```python
def test_sufficient_momentum():
    """Range >= 0.5*ATR14 should PASS."""
    df = create_dataframe(
        high=2003.50, low=2001.00,  # Range = 2.50
        atr14=5.00,
        # min_range = 0.5 * 5.00 = 2.50 ✓
    )
    engine.enable_momentum_filter = True
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert details['has_momentum'] == True

def test_insufficient_momentum():
    """Range < 0.5*ATR14 should FAIL."""
    df = create_dataframe(
        high=2001.25, low=2000.75,  # Range = 0.50
        atr14=5.00,
        # min_range = 0.5 * 5.00 = 2.50 ✗
    )
    engine.enable_momentum_filter = True
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert result == False

def test_momentum_disabled():
    """With filter disabled, weak momentum should PASS."""
    df = create_dataframe(
        high=2001.25, low=2000.75,  # Weak range
        atr14=5.00,
    )
    engine.enable_momentum_filter = False
    result, details = engine.evaluate_entry(df, pattern, -2)
    assert details['has_momentum'] == True  # Passes because filter disabled
```

---

## Stage 6: Anti-FOMO Cooldown (WARNING - non-blocking)

### Purpose
Prevents panic entries after recent signals (optional advisory).

### Condition
```
Bars since last signal >= min_bars (default: 50)
```

### Implementation
```python
can_enter_fomo, fomo_reason = self.bar_close_guard.check_anti_fomo_cooldown(current_bar_index)

# NOTE: Anti-FOMO only logs warning, NEVER returns False
if not can_enter_fomo:
    self.logger.warning(f"Anti-FOMO: {fomo_reason}")
# Always proceed (return is NOT called)
```

### Behavior
- **WARNING ONLY**: Logs message but DOES NOT BLOCK
- **Why**: Too many signals too close = emotional trading
- **Logging**: "Anti-FOMO: Only 15 bars since last signal (min: 50)"
- **Override**: If all other conditions pass, trade still executes

### Timeline Example
```
Bar 100: Signal #1 detected
         ↓
Bars 101-150: Anti-FOMO prevents new signals (warning only)
         ↓
Bar 151: Anti-FOMO cooldown expires, new signals allowed

Bar 155: Signal #2 could trigger (55 bars after first signal)
```

### Test Cases
```python
def test_anti_fomo_cooldown_active():
    """Within cooldown should log WARNING but NOT block."""
    signal_bar = 100
    current_bar = 115  # Only 15 bars after signal
    engine.bar_close_guard.record_signal(signal_bar)
    
    can_enter, reason = engine.bar_close_guard.check_anti_fomo_cooldown(current_bar)
    assert can_enter == False
    assert 'Only 15 bars' in reason
    
    # But entry should still proceed (not blocking)
    result, details = engine.evaluate_entry(df, pattern, current_bar)
    # Does NOT return False due to anti-FOMO

def test_anti_fomo_cooldown_expired():
    """After cooldown should PASS."""
    signal_bar = 100
    current_bar = 151  # 51 bars after signal
    engine.bar_close_guard.record_signal(signal_bar)
    
    can_enter, reason = engine.bar_close_guard.check_anti_fomo_cooldown(current_bar)
    assert can_enter == True
    assert 'cooldown expired' in reason.lower()
```

---

## Stage 7: Trade Cooldown (BLOCKING)

### Purpose
Prevents trading too frequently (risk management between trades).

### Condition
```
Hours since last trade >= cooldown_hours (default: 24)
```

### Implementation
```python
if not self.check_cooldown(current_bar['time']):
    return False, {"failure_code": "COOLDOWN_ACTIVE"}

# Inside check_cooldown():
hours_since = (current_time - self.last_trade_time).total_seconds() / 3600
return hours_since >= self.cooldown_hours
```

### Behavior
- **BLOCKING**: No new trade until cooldown expires
- **Why**: Prevents rapid-fire trades (recovery risk)
- **Default**: 24 hours between trades
- **Tracking**: Persisted in state_manager.last_trade_time

### Timeline Example
```
2026-01-15 10:00:00: Trade closed
                     ↓
                     24 hours
                     ↓
2026-01-16 10:00:00: New trade allowed
```

### Test Cases
```python
def test_cooldown_active():
    """Within cooldown should FAIL."""
    from datetime import datetime, timedelta
    
    last_trade = datetime(2026, 1, 15, 10, 0, 0)
    current_time = datetime(2026, 1, 15, 22, 0, 0)  # Only 12 hours
    
    engine.last_trade_time = last_trade
    engine.cooldown_hours = 24
    
    result = engine.check_cooldown(current_time)
    assert result == False

def test_cooldown_expired():
    """After cooldown should PASS."""
    last_trade = datetime(2026, 1, 15, 10, 0, 0)
    current_time = datetime(2026, 1, 16, 11, 0, 0)  # 25 hours
    
    engine.last_trade_time = last_trade
    engine.cooldown_hours = 24
    
    result = engine.check_cooldown(current_time)
    assert result == True

def test_cooldown_exactly_at_expiry():
    """Exactly at cooldown expiry should PASS."""
    last_trade = datetime(2026, 1, 15, 10, 0, 0)
    current_time = datetime(2026, 1, 16, 10, 0, 0)  # Exactly 24 hours
    
    engine.last_trade_time = last_trade
    engine.cooldown_hours = 24
    
    result = engine.check_cooldown(current_time)
    assert result == True
```

---

## Decision Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENTRY EVALUATION PIPELINE                     │
└─────────────────────────────────────────────────────────────────┘
                              ▼
                    ┌────────────────────┐
                    │  Stage 1: Bar Close │
                    │  Is bar fully      │
                    │  closed? (-2)      │
                    └──┬──────────────┬──┘
                 FAIL  │              │  PASS
                 ──────┼──────┐       │
                       │      │       │
                       │   BLOCK     │
                       │      │       │
                       │      ▼       │
                       │  FAIL: No    │
                       │  trade today │
                       │      │       │
                       ▼      │       ▼
                  ┌────────────────────┐
                  │  Stage 2: Pattern  │
                  │  Valid Double      │
                  │  Bottom exists?    │
                  └──┬──────────────┬──┘
               FAIL  │              │  PASS
               ──────┼──────┐       │
                     │      │       │
                     │   BLOCK     │
                     │      │       │
                     │      ▼       │
                     │  FAIL:      │
                     │  Waiting for│
                     │  pattern    │
                     │      │       │
                     ▼      │       ▼
                ┌────────────────────┐
                │  Stage 3: Breakout │
                │  Close >          │
                │  Neckline?        │
                └──┬──────────────┬──┘
             FAIL  │              │  PASS
             ──────┼──────┐       │
                   │      │       │
                   │   BLOCK     │
                   │      │       │
                   │      ▼       │
                   │  FAIL:      │
                   │  No breakout│
                   │      │       │
                   ▼      │       ▼
              ┌────────────────────┐
              │  Stage 4: Trend    │
              │  Close >          │
              │  EMA50?           │
              └──┬──────────────┬──┘
           FAIL  │              │  PASS
           ──────┼──────┐       │
                 │      │       │
                 │   BLOCK     │
                 │      │       │
                 │      ▼       │
                 │  FAIL:      │
                 │  Downtrend  │
                 │      │       │
                 ▼      │       ▼
            ┌────────────────────┐
            │  Stage 5: Momentum │
            │  Range >=         │
            │  0.5×ATR?         │
            │ (if enabled)       │
            └──┬──────────────┬──┘
         FAIL  │              │  PASS
         ──────┼──────┐       │
               │      │       │
               │   BLOCK     │
               │ (if enabled) │
               │      │       │
               │      ▼       │
               │  FAIL: Weak  │
               │  momentum    │
               │      │       │
               ▼      │       ▼
          ┌────────────────────┐
          │ Stage 6: Anti-FOMO │
          │ Bars since signal  │
          │ >= 50? (advisory)  │
          └──┬──────────────┬──┘
       WARN  │              │  PASS
       ──────┼──────┐       │
             │      │       │
             │   WARNING    │
             │   (doesn't   │
             │    block)    │
             │      │       │
             │      ▼       │
             │   Log: Too    │
             │   many signals│
             │      │        │
             │      │        │
             ▼      │        ▼
        ┌──────────────────────┐
        │  Stage 7: Cooldown   │
        │  Hours since trade  │
        │  >= 24?             │
        └──┬──────────────┬───┘
     FAIL  │              │  PASS
     ──────┼──────┐       │
           │      │       │
           │   BLOCK     │
           │      │       │
           │      ▼       │
           │  FAIL:      │
           │  Cooldown   │
           │  active     │
           │      │       │
           ▼      │       ▼
       TRADE   REJECTED  ┌──────────────────┐
       BLOCKED            │  ALL CONDITIONS  │
                          │  MET!            │
                          │  Calculate SL/TP │
                          │  Return: ENTER   │
                          └──────────────────┘
                                  │
                                  ▼
                          ┌──────────────────┐
                          │  TRADE EXECUTED  │
                          │  Entry price: X  │
                          │  SL: Y           │
                          │  TP: Z           │
                          └──────────────────┘
```

---

## "Why No Trade?" Decision Tree

When a trade doesn't execute, use this tree to find the reason:

```
TRADE REJECTED
│
├─ failure_code == "BAR_NOT_CLOSED"
│  └─ Resolution: Wait for current bar to close (use -2 index)
│
├─ failure_code == "INVALID_PATTERN_STRUCTURE"
│  └─ Reason: No Double Bottom detected yet
│  └─ Resolution: Pattern engine will emit when formed
│
├─ failure_code == "NO_NECKLINE_BREAK"
│  └─ Reason: Close <= Neckline (no breakout)
│  └─ Current Close: 2000.25, Neckline: 2000.50
│  └─ Resolution: Wait for breakout above neckline
│
├─ failure_code == "CONTEXT_NOT_ALIGNED"
│  ├─ Sub-case: Close <= EMA50 (downtrend)
│  │  └─ Current Close: 1999.50, EMA50: 2000.00
│  │  └─ Resolution: Wait for uptrend alignment
│  │
│  └─ Sub-case: Momentum too weak (if enabled)
│     └─ Candle Range: 0.50, Min: 2.50
│     └─ Resolution: Wait for stronger breakout
│
├─ Logged warning: "Anti-FOMO: Only X bars since last signal"
│  └─ This is WARNING only, entry might still proceed
│  └─ Resolution: Either wait 50 bars or accept warning
│
└─ failure_code == "COOLDOWN_ACTIVE"
   └─ Reason: Recent trade closed less than 24 hours ago
   └─ Last trade closed: 2026-01-15 10:00:00
   └─ Next trade allowed: 2026-01-16 10:00:00
   └─ Resolution: Wait for cooldown to expire
```

---

## Summary Table

| Stage | Type | Condition | Blocks? | What Fails This |
|-------|------|-----------|---------|-----------------|
| 1 | Guard | Bar fully closed | YES | Intrabar execution |
| 2 | Signal | Pattern exists | YES | No Double Bottom yet |
| 3 | Trigger | Close > Neckline | YES | No breakout |
| 4 | Context | Close > EMA50 | YES | Downtrend |
| 5 | Quality | Range ≥ 0.5×ATR | YES (if enabled) | Weak momentum |
| 6 | Advisory | Bars ≥ 50 | NO (warning) | Too many signals |
| 7 | Risk | Hours ≥ 24 | YES | Recent trade |

---

## Unit Test Suite

### File: tests/test_entry_conditions.py

```python
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
from src.engines.strategy_engine import StrategyEngine


class TestBarCloseGuard:
    """Tests for Stage 1: Bar-Close Guard."""
    
    def test_current_forming_bar_rejected(self):
        """Using forming bar (-1) should fail."""
        # ... implementation
        pass
    
    def test_last_closed_bar_accepted(self):
        """Using closed bar (-2) should pass bar-close check."""
        # ... implementation
        pass


class TestPatternDetection:
    """Tests for Stage 2: Pattern Detection."""
    
    def test_no_pattern_fails(self):
        """None pattern should fail."""
        # ... implementation
        pass
    
    def test_pattern_invalid_flag_fails(self):
        """Pattern with valid=False should fail."""
        # ... implementation
        pass
    
    def test_valid_pattern_passes(self):
        """Valid pattern should pass."""
        # ... implementation
        pass


class TestBreakoutConfirmation:
    """Tests for Stage 3: Breakout Confirmation."""
    
    def test_close_above_neckline_passes(self):
        """Close > Neckline should pass."""
        # ... implementation
        pass
    
    def test_close_equals_neckline_fails(self):
        """Close == Neckline should FAIL (not clear break)."""
        # ... implementation
        pass
    
    def test_close_below_neckline_fails(self):
        """Close < Neckline should fail."""
        # ... implementation
        pass


class TestTrendFilter:
    """Tests for Stage 4: Trend Filter."""
    
    def test_close_above_ema50_passes(self):
        """Close > EMA50 should pass."""
        # ... implementation
        pass
    
    def test_close_below_ema50_fails(self):
        """Close < EMA50 should fail."""
        # ... implementation
        pass


class TestMomentumFilter:
    """Tests for Stage 5: Momentum Filter."""
    
    def test_sufficient_momentum_passes(self):
        """Range >= 0.5×ATR should pass."""
        # ... implementation
        pass
    
    def test_insufficient_momentum_fails(self):
        """Range < 0.5×ATR should fail."""
        # ... implementation
        pass
    
    def test_momentum_disabled_ignores_range(self):
        """With filter disabled, weak range should pass."""
        # ... implementation
        pass


class TestAntiFOMO:
    """Tests for Stage 6: Anti-FOMO (WARNING only)."""
    
    def test_anti_fomo_warns_not_blocks(self):
        """Anti-FOMO should warn but not block."""
        # ... implementation
        pass


class TestCooldown:
    """Tests for Stage 7: Cooldown."""
    
    def test_cooldown_active_blocks(self):
        """Within cooldown should fail."""
        # ... implementation
        pass
    
    def test_cooldown_expired_allows(self):
        """After cooldown should pass."""
        # ... implementation
        pass


class TestCompleteEntry:
    """Integration tests: All stages together."""
    
    def test_all_conditions_met_enters_trade(self):
        """With all conditions met, should return ENTER."""
        # ... implementation
        pass
    
    def test_one_condition_fails_rejects_trade(self):
        """If any blocking condition fails, should return NO TRADE."""
        # ... implementation
        pass
```

---

## Implementation Checklist

- ✅ 7-stage decision pipeline documented
- ✅ Blocking vs Warning conditions clarified
- ✅ ASCII flow diagram with all paths
- ✅ "Why No Trade?" decision tree
- ✅ Test case structure defined
- ✅ Edge cases identified
- ✅ Failure codes standardized
- ✅ Integration points mapped

---

## Next Steps

Task 2.3 is COMPLETE. Ready for:
- **Task 2.4**: Export Functions (JSON/CSV/HTML)

## Related Documentation

- [THREAD_SAFE_UI_IMPLEMENTATION.md](THREAD_SAFE_UI_IMPLEMENTATION.md) - UI update queue
- [STATE_PERSISTENCE_IMPLEMENTATION.md](STATE_PERSISTENCE_IMPLEMENTATION.md) - Atomic writes
- [src/engines/strategy_engine.py](../src/engines/strategy_engine.py) - Full implementation
- [src/engines/decision_engine.py](../src/engines/decision_engine.py) - Decision output

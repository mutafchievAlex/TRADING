# Multi-Level TP Engine - Quick Integration Guide

## What Was Added

The system now includes a sophisticated multi-level take-profit system with dynamic stop-loss management. This provides professional-grade exit strategy with three progressive profit targets.

## Files Modified/Created

### New Files
1. **`src/engines/multi_level_tp_engine.py`** - Core TP state machine and calculations
2. **`test_multi_level_tp_examples.py`** - Practical usage examples
3. **`MULTI_LEVEL_TP_IMPLEMENTATION.md`** - Detailed technical documentation

### Modified Files
1. **`src/engines/strategy_engine.py`**
   - Added MultiLevelTPEngine import
   - Enhanced `evaluate_exit()` method to support multi-level TP
   - Returns 4 values: (should_exit, reason, new_tp_state, new_stop_loss)

2. **`src/engines/state_manager.py`**
   - Added TP state fields to position tracking
   - New methods: `update_position_tp_state()`, `get_position_by_ticket()`
   - Persistence in state.json

3. **`src/main.py` (TradingController)**
   - Enhanced `_execute_entry()` to calculate TP levels
   - Enhanced `_monitor_positions()` to track TP state transitions
   - Dynamic SL updates on TP1/TP2 triggers

## How It Works (Simple Version)

### Trade Entry
When a trade opens:
1. Entry price and stop loss are calculated
2. TP levels are computed:
   - **TP1**: Entry + Risk × 1.4 (first target)
   - **TP2**: Entry + Risk × 1.8 (second target)
   - **TP3**: Entry + Risk × 2.0 (final target)
3. Position state: **IN_TRADE**

### Price Progression
As price moves, the system transitions through states:

```
IN_TRADE  →  TP1_REACHED  →  TP2_REACHED  →  EXITED
  (open)     (SL→entry)      (SL→trail)      (close)
```

**TP1 reached**: Stop loss moves to entry price (breakeven protection)
**TP2 reached**: Stop loss trails 0.5 pips below current price
**TP3 reached**: Position closes completely

### Failure Scenario
If price reverses:
- After TP1: SL at entry prevents loss
- After TP2: SL trails behind peak price

## Usage in Code

### In Strategy Engine
```python
# The strategy engine now handles multi-level exits automatically
should_exit, reason, new_tp_state, new_stop_loss = strategy_engine.evaluate_exit(
    current_price=2019.50,
    entry_price=2000.00,
    stop_loss=2000.00,  # Current SL
    take_profit=2020.00,  # Legacy param (not used in multi-level)
    tp_state='TP1_REACHED',  # Current TP state
    tp_levels={'tp1': 2014, 'tp2': 2018, 'tp3': 2020},
    direction=1  # LONG
)
# Returns: (False, "Position open - TP1 Reached", "TP1_REACHED", 2000.00)
```

### In Position Monitoring
```python
# Already integrated in _monitor_positions()
# The system automatically:
# 1. Calculates TP levels from entry/SL
# 2. Evaluates multi-level TP conditions
# 3. Updates position state on transitions
# 4. Moves stop loss dynamically
```

### Accessing Position TP State
```python
position = state_manager.get_position_by_ticket(12345)

print(f"Current state: {position['tp_state']}")       # IN_TRADE
print(f"TP1 target: {position['tp1_price']:.2f}")     # 2014.00
print(f"Current SL: {position['current_stop_loss']:.2f}")  # 1990.00
print(f"Next target: {position['tp2_price']:.2f}")    # 2018.00
```

## State Persistence

The TP system automatically saves to `data/state.json`:

```json
{
  "open_positions": [
    {
      "ticket": 12345,
      "entry_price": 2000.00,
      "stop_loss": 1990.00,
      "current_stop_loss": 2000.00,
      "tp_state": "TP1_REACHED",
      "tp1_price": 2014.00,
      "tp2_price": 2018.00,
      "tp3_price": 2020.00,
      "direction": 1,
      "tp1_cash": 14.00,
      "tp2_cash": 18.00,
      "tp3_cash": 20.00
    }
  ]
}
```

### Recovery After Restart
1. Application starts
2. Loads positions from state.json (including TP state)
3. Continues monitoring from current state
4. **No replay** needed - state is persistent

## UI Integration

The system automatically updates the Position tab:
- **Current SL**: Updates when TP1/TP2 reached
- **TP1/TP2/TP3 prices**: Displayed with current state
- **Active level**: Shows which TP state is active
- **Next target**: Highlights next profit target

## Examples

See `test_multi_level_tp_examples.py` for:
1. TP level calculation
2. Successful progression (IN_TRADE → TP1 → TP2 → TP3)
3. Failed continuation (reversal after TP1)
4. Trailing stop mechanics (after TP2)
5. Next target display

Run with:
```bash
python test_multi_level_tp_examples.py
```

## Backward Compatibility

**Existing positions without TP levels still work**:
- Falls back to simple SL/TP check
- No TP state tracking
- Returns legacy 2-value tuple

**To enable multi-level for position**:
Must have `tp1_price`, `tp2_price`, `tp3_price` defined

## Testing

### Manual Test
1. Open a position
2. Check `data/state.json` - should have TP levels
3. Monitor as price moves:
   - At TP1: SL should update to entry price
   - At TP2: SL should trail (price - 0.5)
   - At TP3: Position should close

### Check Logs
Look for messages like:
```
✓ TP1 REACHED: 2014.00 >= 2014.00
Position 12345 TP state: IN_TRADE -> TP1_REACHED, SL updated to 2000.00
```

## Configuration

### Change TP Ratios
In `src/main.py`, line where `MultiLevelTPEngine` is created:
```python
self.multi_level_tp = MultiLevelTPEngine(
    default_rr_long=2.5,    # Change final target RR
    default_rr_short=2.0
)
```

### Change Trailing Offset
In `src/main.py`, `_monitor_positions()`:
```python
new_stop_loss = self.multi_level_tp.calculate_new_stop_loss(
    ...,
    trailing_offset=1.0  # Change from 0.5 pips
)
```

## Common Issues

### Position doesn't transition to TP1
- Check if price actually reached TP1 level
- Verify TP levels are calculated (check state.json)
- Check bar-close prices (not intrabar)

### SL not updating
- Ensure TP state changes detected (check logs)
- Verify `current_stop_loss` field exists in position

### Position closes immediately
- Check if stop loss is above entry (should be below for LONG)
- Verify bar-close price doesn't trigger SL on entry bar

## Support

For detailed technical documentation, see:
- `MULTI_LEVEL_TP_IMPLEMENTATION.md` - Full technical spec
- `test_multi_level_tp_examples.py` - Practical examples
- Source code comments in `src/engines/multi_level_tp_engine.py`

## Summary

✅ **What the system does**:
- Calculates 3 progressive profit targets
- Transitions through state machine (IN_TRADE → TP1 → TP2 → TP3)
- Moves SL to breakeven at TP1
- Trails SL at TP2
- Closes position at TP3
- Saves state for recovery
- Updates UI automatically

✅ **When it activates**:
- Automatically on every position open
- Every bar-close check in monitoring loop
- On application restart (state.json)

✅ **No manual configuration needed**:
- Works with existing strategy
- Backward compatible
- Adjustable via config if needed

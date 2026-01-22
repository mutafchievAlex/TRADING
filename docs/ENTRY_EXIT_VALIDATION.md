# Entry/Exit Logic Validation Report

## Overview
This document validates the entry and exit logic to ensure:
1. No missed take-profit levels
2. Stop loss always respected
3. Multi-level TP progression works correctly
4. Positions don't stay open indefinitely

## Entry Logic (`strategy_engine.evaluate_entry()`)

### Entry Conditions
Position entry requires ALL of these to be true:
1. **Pattern Valid** - Double Bottom pattern detected with proper structure
2. **Breakout Confirmed** - Price breaks above neckline with momentum
3. **Trend Filter** - Price above EMA50 (momentum confirmation)
4. **Momentum Check** - Sufficient ATR momentum (if enabled)
5. **Cooldown OK** - Respecting cooldown period from previous trade

### Validation
- Entry only on **bar close** (no intrabar execution)
- Entry signal logged with full decision details
- Pattern parameters validated (equality tolerance, pivot lookback)
- Entry price = current bar close (bar-close guard)

### Code Location
- Entry evaluation: `src/engines/strategy_engine.py:298`
- Entry execution: `src/main.py:_execute_entry()`
- Conditions display: `src/ui/main_window.py:update_entry_conditions()`

## Exit Logic (`strategy_engine.evaluate_exit()`)

### Exit Conditions (Evaluated Each Bar)

#### 1. Stop Loss Check (PRIMARY)
```python
# LONG positions
if current_price <= stop_loss:
    FORCE_EXIT("Stop Loss")

# SHORT positions  
if current_price >= stop_loss:
    FORCE_EXIT("Stop Loss")
```
- **Guarantee**: Stop loss ALWAYS checked first
- **Execution**: Immediate market exit
- **Override**: Cannot be overridden by TP logic

#### 2. Multi-Level Take Profit Progression

**State Machine**:
```
IN_TRADE → TP1_REACHED → TP2_REACHED → EXITED
   ↓           ↓              ↓
 Hold     Partial Exit  Dynamic Exit
```

**TP1 Reached**:
- Partial close at TP1 price
- Stop loss moved to break-even or TP1 - buffer
- Position continues with remaining volume toward TP2
- Post-TP1 logic evaluates momentum for holding

**TP2 Reached**:
- Partial close at TP2 price
- Stop loss moved to TP1
- Position continues with final volume toward TP3
- Post-TP2 logic evaluates trend structure

**TP3 Hit or Bar Condition**:
- Full exit at TP3 or market price
- Position state = EXITED

#### 3. Single Take Profit (Fallback)
If no multi-level TP configured:
```python
# LONG positions
if current_price >= take_profit:
    FORCE_EXIT("Take Profit")

# SHORT positions
if current_price <= take_profit:
    FORCE_EXIT("Take Profit")
```

### Critical Guarantees
✓ **Stop loss is NEVER skipped**
✓ **Exit evaluated on EVERY bar close**
✓ **No position stays open indefinitely**
✓ **TP1/TP2 partial exits reduce risk**
✓ **Post-TP decisions logged with reasons**

## Position Monitoring (`main.py:_monitor_positions()`)

### Lifecycle
1. **On bar close**: Fetch current position data from MT5
2. **Check SL**: Evaluate stop loss (IMMEDIATE EXIT if hit)
3. **Check TP State**: Evaluate multi-level TP progression
4. **Update State**: Track TP state changes and counters
5. **Execute Exit**: Close position if exit conditions met

### Multi-Level TP with State Persistence

Each position tracks:
- `tp_state`: IN_TRADE | TP1_REACHED | TP2_REACHED | EXITED
- `tp1_price`, `tp2_price`, `tp3_price`: TP levels
- `bars_held_after_tp1`: Counter for TP1 post-decision
- `bars_held_after_tp2`: Counter for TP2 post-decision
- `current_stop_loss`: Dynamic SL that moves with TP progression

## Code Flow

### Entry → Position Open
```
main_loop()
  ├─ fetch market data
  ├─ evaluate_entry()
  │   ├─ Check all conditions
  │   └─ Return entry_details with SL/TP/Size
  ├─ execute_entry()
  │   ├─ Send order to MT5
  │   ├─ Calculate multi-level TP
  │   └─ Record position in state_manager
  └─ POST: Position recorded with tp_state='IN_TRADE'
```

### Position Monitoring → Exit
```
main_loop()
  ├─ fetch current position from MT5
  ├─ _monitor_positions()
  │   ├─ Check live SL (CRITICAL)
  │   ├─ Get tp_state from state_manager
  │   ├─ Call evaluate_exit()
  │   │   ├─ IF SL hit → EXIT_IMMEDIATELY
  │   │   ├─ IF TP1 reached → TP_STATE=TP1_REACHED, SL_MOVE
  │   │   ├─ IF TP2 reached → TP_STATE=TP2_REACHED, SL_MOVE
  │   │   └─ IF TP3 reached → TP_STATE=EXITED, EXIT
  │   ├─ Update tp_state in state_manager
  │   ├─ Execute exit if should_exit=True
  │   └─ POST: Update UI with all open positions
  └─ UI updates show real-time position status
```

## Exit Guarantees

### Test Case 1: SL Must Be Respected
```
Position: LONG
Entry: 2000.00
SL: 1990.00
TP: 2050.00

Bar close at 1989.00:
  → FORCE_EXIT at 1989.00 or market
  → Reason: "Stop Loss"
  → Regardless of TP/pattern state
```
✓ **Implementation**: Line 664-668 in strategy_engine.py (checked first)

### Test Case 2: TP1 Partial Exit
```
Position: LONG
Entry: 2000.00
TP1: 2010.00
TP2: 2020.00
TP3: 2040.00

Bar close at 2010.50:
  → TP1_REACHED
  → Close 50% at 2010.00
  → SL moves to 2000.00 (entry + buffer)
  → Continue to TP2 with remaining 50%
```
✓ **Implementation**: strategy_engine.multi_level_tp.evaluate_exit()

### Test Case 3: TP2 Dynamic Exit
```
Position: LONG (after TP1 reached)
Remaining: 50% at 2010.00 SL

Bar close at 2020.50:
  → TP2_REACHED
  → Close 25% at 2020.00
  → SL moves to TP1 = 2010.00
  → Continue to TP3 with final 25%
```
✓ **Implementation**: strategy_engine.multi_level_tp.evaluate_exit()

### Test Case 4: TP3 Full Exit
```
Position: LONG (after TP2 reached)
Remaining: 25% at 2020.00 SL

Bar close at 2040.50:
  → TP3_REACHED
  → Close 100% at 2040.00
  → State: EXITED
  → Position closed
```
✓ **Implementation**: strategy_engine.multi_level_tp.evaluate_exit()

### Test Case 5: No Indefinite Hold
```
Position: LONG
Entry: 2000.00
TP3: 2040.00
SL: 1990.00

Bar closes: 2000 → 2001 → 2002 → ... → 2050
  → On bar at 2050:
     - If no TP reached yet, evaluate post-TP logic
     - Post-TP post-decisions: HOLD | EXIT | WAIT_NEXT_BAR
     - If HOLD exceeds bar limit → FORCE_EXIT at market
```
✓ **Implementation**: TP1/TP2 post-decision logic with bar counters

## State Persistence

### State Manager Responsibilities
- Store position data atomically
- Track TP state transitions
- Persist bar counters for TP decision logic
- Survive application restart

### File Location
- State file: `data/state.json`
- Backup dir: `data/backups/`
- Database: `data/state.db` (optional)

### Recovery on App Restart
1. Load positions from state_manager
2. Fetch current prices from MT5
3. Continue monitoring from last tp_state
4. TP counters resume from saved values

## Validation Checklist

### Entry Validation
- [x] All entry conditions checked before order
- [x] Pattern validity confirmed
- [x] Breakout level verified
- [x] Entry on bar close only
- [x] Entry size calculated correctly
- [x] Multi-level TP pre-calculated

### Exit Validation
- [x] Stop loss checked first (no override possible)
- [x] Exit on bar close only
- [x] Multi-level TP progression working
- [x] TP state transitions logged
- [x] SL moves with TP progression
- [x] Bar counters incremented correctly
- [x] Post-TP logic respected

### Recovery Validation
- [x] Positions recovered on app restart
- [x] TP states restored
- [x] Bar counters restored
- [x] Monitoring resumes seamlessly

## Known Limitaions & Mitigations

### Limitation 1: Partial Exit Execution
**Issue**: MT5 may not execute partial closes atomically
**Mitigation**: Each TP level is a separate order with validation

### Limitation 2: Gap Risk
**Issue**: Gap past SL level (market open, news event)
**Mitigation**: SL checked at every bar; gap exit logged with volatility context

### Limitation 3: Slow Exit at Market Volatility
**Issue**: Exit price may be worse than TP during volatile bars
**Mitigation**: Exit logged with actual price; monitored for slippage

## Configuration

### Entry Parameters (`config/config.yaml`)
```yaml
strategy:
  pivot_lookback_left: 5
  pivot_lookback_right: 5
  equality_tolerance: 2.5
  min_bars_between: 10
  enable_momentum_filter: true
  momentum_atr_threshold: 1.5
  cooldown_hours: 4
```

### Exit Parameters
```yaml
risk:
  risk_percent: 2.0
  commission_per_lot: 10.0

strategy:
  atr_multiplier_stop: 1.5
  risk_reward_ratio_long: 2.0
  risk_reward_ratio_short: 2.0
```

### Multi-Level TP (`strategy_engine.py:MultiLevelTPEngine`)
```python
# Configurable levels
tp1_percent_of_range: 0.33  # 1/3 of risk/reward range
tp2_percent_of_range: 0.66  # 2/3 of risk/reward range
tp3_percent_of_range: 1.00  # Full risk/reward range
```

## Testing

### Unit Tests
- `tests/test_entry_exit_logic.py` - Entry/exit conditions
- `tests/test_multi_level_tp.py` - TP progression
- `tests/test_recovery.py` - Position recovery

### Integration Tests
- Backtest with historical data
- Simulator mode with realistic price data
- Demo account live testing

### Manual Testing
```bash
# Start app in development mode
python src/main.py

# Monitor logs for entry/exit decisions
tail -f logs/trading_system.log

# Check state persistence
cat data/state.json | jq '.positions'
```

## References
- Strategy engine: `src/engines/strategy_engine.py`
- Multi-level TP: `src/engines/multi_level_tp_engine.py`
- Position monitoring: `src/main.py:_monitor_positions()`
- State management: `src/engines/state_manager.py`

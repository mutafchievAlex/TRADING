# Recovery Mode - System State Reconstruction

## Overview

Recovery Mode is a critical safety mechanism that ensures the trading system is always in a state **consistent with the strategy logic**, regardless of:
- Unexpected shutdowns
- Network disconnections
- Offline periods
- Application crashes

## How It Works

### Trigger
Recovery Mode is automatically triggered when:
1. Application starts/restarts (if open positions exist)
2. Connection to MT5 is re-established after disconnect
3. There are any open positions that need validation

### Process

#### Step 1: Load Historical Data
- Loads last **N closed bars** (default: 50)
- Sufficient data for indicator warm-up (220+ bars total)
- Uses only completed bars (no intrabar data)

#### Step 2: Reconstruct Indicators
- Re-calculates all indicators (EMA50, EMA200, ATR14)
- Validates indicator integrity
- Ensures no NaN values in critical fields

#### Step 3: Reconstruct Pattern State
- Re-runs pattern detection on historical data
- Determines current Double Bottom pattern status
- Establishes baseline strategy state

#### Step 4: Validate Open Positions
For each open position, checks:

```
1. Stop Loss Hit?
   └─ YES → Close position immediately
   └─ NO → Continue

2. Take Profit Hit?
   └─ YES → Close position immediately
   └─ NO → Continue

3. Exit Condition (Pattern Invalid)?
   └─ YES → Close position immediately
   └─ NO → Position remains valid
```

#### Step 5: Apply Recovery Decisions
- Closes positions that strategy would close
- Keeps positions that strategy would keep
- Updates state persistence
- Logs all actions with reasons

## Configuration

### Default Settings
```yaml
recovery:
  recovery_bars: 50  # Number of bars to load for reconstruction
```

### Customization
```python
# In config.yaml
recovery:
  recovery_bars: 100  # Load more bars for deeper reconstruction
```

## Example Scenarios

### Scenario 1: Position Hits Stop Loss During Offline
```
System offline: 14:00 - 16:00
Position: SL=2500, TP=2600, Entry=2550 (at 14:30)
Recovery at 16:00: Finds bar at 15:30 closed at 2499

Action: 
  ✓ Close position at 2499 (Stop Loss triggered)
  ✓ Log: "Stop Loss hit at 2499 (SL: 2500)"
```

### Scenario 2: Position Hits Take Profit During Offline
```
System offline: 14:00 - 16:00
Position: SL=2500, TP=2600, Entry=2550 (at 14:30)
Recovery at 16:00: Finds bar at 15:30 closed at 2610

Action:
  ✓ Close position at 2600 (Take Profit triggered)
  ✓ Log: "Take Profit hit at 2610 (TP: 2600)"
```

### Scenario 3: Pattern Becomes Invalid During Offline
```
System offline: 14:00 - 16:00
Position: Pattern was valid when opened (14:30)
Recovery at 16:00: Pattern is no longer valid (price structure changed)

Action:
  ✓ Close position at current close
  ✓ Log: "Exit condition: Pattern no longer valid"
```

### Scenario 4: Position Still Valid After Offline
```
System offline: 14:00 - 16:00
Position: SL=2500, TP=2600, Entry=2550 (at 14:30)
Recovery at 16:00: Current close = 2555, Pattern still valid

Action:
  ✓ Keep position open
  ✓ Log: "Position validated and will remain open"
```

## API

### RecoveryEngine Class

#### `__init__(recovery_bars: int = 50)`
Initialize recovery engine with specified bars for reconstruction.

#### `perform_recovery(...)`
Execute full recovery sequence.

**Parameters**:
- `market_data_service` - MarketDataService instance
- `indicator_engine` - IndicatorEngine instance
- `pattern_engine` - PatternEngine instance
- `strategy_engine` - StrategyEngine instance
- `state_manager` - StateManager instance
- `execution_engine` - ExecutionEngine instance

**Returns**: Recovery result dict
```python
{
    'recovery_successful': bool,
    'positions_validated': int,      # How many positions checked
    'positions_closed': int,          # How many positions closed
    'recovery_reason': str,           # Summary or error message
    'closed_positions': [             # Details of closed positions
        {
            'ticket': int,
            'reason': str,
            'exit_price': float
        }
    ],
    'timestamp': datetime
}
```

## Integration in Main Application

### Automatic Trigger
```python
# In TradingController.connect_mt5()
if connected:
    # ... connection setup ...
    self._perform_recovery()  # Auto-triggered
    return True
```

### Manual Trigger (if needed)
```python
result = controller._perform_recovery()
if result['recovery_successful']:
    print(f"Recovery OK: {result['positions_closed']} positions closed")
```

## Logging

All recovery actions are logged with full details:

```
============================================================
RECOVERY MODE: Starting system reconstruction
============================================================
Step 1: Loading 50 historical bars...
Loaded 500 bars, latest: 2025-01-09 14:00:00

Step 2: Reconstructing indicators...
Indicators reconstructed successfully

Step 3: Detecting patterns...
Pattern state reconstructed: True

Step 4: Validating open positions...
Found 1 open position(s)

Position 123456 should be closed: Stop Loss hit at 2499 (SL: 2500)

============================================================
RECOVERY MODE: Complete
Positions validated: 1
Positions closed: 1
============================================================
```

## Safety Guarantees

✅ **No Repainting**: Uses only closed bars
✅ **Deterministic**: Always consistent with strategy logic
✅ **Non-Blocking**: Gracefully handles errors
✅ **Auditable**: Complete logging of all actions
✅ **Conservative**: When uncertain, keeps position open
✅ **Fast**: Completes within seconds

## Key Principles

1. **Strategy Consistency**: System state always matches what strategy would do
2. **Offline Resilience**: Works correctly regardless of how long system was offline
3. **Position Safety**: Only closes if strategy logic dictates closure
4. **Error Tolerance**: Handles data gaps and temporary inconsistencies
5. **Full Transparency**: Logs every decision with exact reason

## Configuration Best Practices

### High-Frequency Trading (Faster Recovery)
```yaml
recovery:
  recovery_bars: 30  # Last 30 hours for H1
```

### Conservative (Deeper Analysis)
```yaml
recovery:
  recovery_bars: 100  # Last 100 hours for H1
```

### Ultra-Conservative (Maximum Safety)
```yaml
recovery:
  recovery_bars: 200  # Last 200 hours for H1
```

## Troubleshooting

### Recovery Fails: "Failed to load historical data"
- Check MT5 connection
- Verify symbol is correct
- Ensure sufficient historical data available

### Recovery Fails: "Failed to reconstruct indicators"
- Check that indicator engine is working
- Verify OHLC data integrity
- Ensure no NaN values in source data

### Position Not Closed (Should Have Been)
- Check logs for exact reason decision was made
- Verify position parameters (SL, TP)
- Check if pattern logic changed

## Performance Impact

- Typical recovery time: 2-5 seconds
- Memory usage: Minimal (only 50-200 bars loaded)
- Network impact: Single data fetch
- CPU impact: Single indicator calculation pass

## Future Enhancements

- [ ] Partial position closure (close specific pyramided positions)
- [ ] Position averaging during recovery
- [ ] Slippage tolerance for SL/TP checks
- [ ] Recovery performance metrics
- [ ] Recovery result notifications to external systems


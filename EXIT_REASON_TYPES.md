# EXIT REASON TYPES - COMPLETE REFERENCE

## Available Exit Reason Types

The trading system supports **12 different exit reason types** for trades:

### Primary Exit Reasons (Most Common)

#### 1. **Stop Loss**
- **Code:** `"Stop Loss"`
- **When:** Position closed at stop loss level
- **Condition:** Price reaches or crosses stop_loss
- **Frequency:** Common (losing positions)
- **Example:** SL = 4900, price drops to 4900 → Close with "Stop Loss"

#### 2. **Take Profit** 
- **Code:** `"Take Profit"`
- **When:** Position closed at main take profit level
- **Condition:** Price reaches or exceeds take_profit
- **Frequency:** Common (winning positions)
- **Example:** TP = 5100, price reaches 5100 → Close with "Take Profit"

### Multi-Level Take Profit (3-Level TP Strategy)

#### 3. **TP1 Hit**
- **Code:** `"TP1 Hit"`
- **When:** First take profit level reached
- **Condition:** Price reaches tp1_price
- **Frequency:** When using 3-level exit
- **After:** System decides to HOLD or CLOSE at TP1

#### 4. **TP2 Hit**
- **Code:** `"TP2 Hit"`
- **When:** Second take profit level reached
- **Condition:** Price reaches tp2_price
- **Frequency:** When using 3-level exit
- **After:** System decides to HOLD or CLOSE at TP2
- **Feature:** May enable trailing stop loss

#### 5. **TP3 Hit**
- **Code:** `"TP3 Hit"`
- **When:** Third/final take profit level reached
- **Condition:** Price reaches tp3_price
- **Frequency:** When using 3-level exit
- **After:** Automatic final close

### External/Manual Exits

#### 6. **Closed Externally**
- **Code:** `"Closed externally"`
- **When:** Position closed outside the application
- **Trigger:** Position disappears from MT5 account
- **Frequency:** When user manually closes in MT5
- **Example:** User closes position in MT5 terminal → App detects it

#### 7. **Manual Close**
- **Code:** `"Manual Close"`
- **When:** User closes from application UI
- **Trigger:** User clicks "Close Position" button
- **Frequency:** When user intervenes
- **Example:** User clicks close button in History tab

### Strategy-Based Exits

#### 8. **Pattern Exit** / **Pattern re-entry**
- **Code:** `"Pattern re-entry"`
- **When:** New pattern detected while in trade
- **Trigger:** Pattern engine finds new valid entry pattern
- **Frequency:** If pattern exit logic enabled
- **Use Case:** Exit current position to enter new pattern setup

#### 9. **Recovery Mode**
- **Code:** `"Recovery Mode"`
- **When:** Position closed after system restart
- **Trigger:** Recovery engine matching MT5 positions
- **Frequency:** After restart during state synchronization
- **Purpose:** Ensure consistency with actual MT5 state

### Edge Cases

#### 10. **Protective Exit**
- **Code:** `"Protective Exit - [reason]"`
- **When:** Exit due to protective conditions
- **Example:** `"Protective Exit - TP3 Not Reached"`
- **Frequency:** Rare, unusual conditions
- **Purpose:** Safety mechanism for edge cases

#### 11. **Unknown Closure**
- **Code:** `"Unknown Closure"`
- **When:** Position closed but reason unclear
- **Frequency:** Rare (debugging needed)
- **Purpose:** Indicates data integrity issue

#### 12. **CLOSED (Historical)**
- **Code:** `"CLOSED (Historical)"`
- **When:** Historical trade imported from MT5
- **Frequency:** All historical trades
- **Purpose:** Distinguish imported trades from live trading

---

## Multi-Level TP Decision Metadata

When using 3-level TP strategy, additional metadata is tracked:

### At TP1 Level
```
post_tp1_decision     → "HOLD" or "CLOSE"
tp1_exit_reason       → Why that decision was made
                        Example: "ATR momentum favors continuation"
```

### At TP2 Level
```
post_tp2_decision     → "HOLD" or "CLOSE"
tp2_exit_reason       → Why that decision was made
trailing_sl_level     → If HOLD, what's the trailing SL level
trailing_sl_enabled   → Is trailing stop active?
```

---

## Current Database Status

**Exit Reasons in Database:**
- Total trades: 17
- Reason type: "CLOSED" (Historical)
- All imported from MT5

**When Live Trading Begins:**
- "Stop Loss" - Will appear for losing positions
- "Take Profit" - Will appear for winning positions
- "TP1 Hit" / "TP2 Hit" / "TP3 Hit" - If using 3-level TP
- Others as appropriate

---

## Validation Rules

The system validates exit reasons for data integrity:

✅ **If reason contains "TP3"**
- Exit price must actually reach TP3 level
- Otherwise: Auto-corrected and logged

✅ **If reason contains "TP"**
- Exit price must reach take_profit level
- Otherwise: Auto-corrected and logged

✅ **If reason is "Stop Loss"**
- Exit price must hit stop loss level
- Otherwise: Auto-corrected and logged

✅ **Invalid reasons**
- Numbers (prices) are rejected
- Empty strings become "Unknown"
- NULL becomes "Unknown"

---

## Viewing Exit Reasons

### Option 1: Live Application
Navigate to **History Tab** → Column 6 shows "Exit Reason"

### Option 2: Database Inspection
```bash
python inspect_db.py
```
Shows last 20 trades with reasons visible

### Option 3: Direct SQL Query
```sql
SELECT ticket, entry_time, exit_time, profit, exit_reason 
FROM trades
WHERE exit_reason LIKE '%Take%';
```

### Option 4: Summary Script
```bash
python show_actual_reasons.py
```
Lists all reason types and examples

### Option 5: Comprehensive Reference
```bash
python list_exit_reasons.py
```
Shows all 12 possible reason types with details

---

## Storage & Persistence

**Database Field:** `trades.exit_reason` (TEXT type)
- Cannot be NULL
- Stored atomically
- Crash-safe with WAL mode

**Backups:**
- SQLite database: `data/state.db`
- JSON backup: `data/state.json`
- Both always in sync

**Searchable:** Full SQL access to query exit reasons

---

## Next Steps (When Live Trading)

Exit reasons will be automatically assigned based on market conditions:

1. **Each bar**, strategy evaluates exit conditions
2. **If exit needed**, determines the reason
3. **Reason is recorded** in database
4. **UI updates automatically** in History tab
5. **Complete audit trail** is maintained

All data is **atomic** - either entire trade record saves or none (no corruption possible).

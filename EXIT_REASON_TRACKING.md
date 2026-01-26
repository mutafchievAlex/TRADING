# Exit Reason Tracking - Implementation Complete

## Overview
The database now tracks and displays exit reasons for all trades, both historical and current. This provides complete visibility into why each position was closed.

## Database Schema
The `trades` table includes the `exit_reason` field:
```sql
CREATE TABLE trades (
    ...
    exit_reason TEXT NOT NULL,  -- Reason for closing the position
    ...
)
```

## Exit Reason Types

### Current Trades
When a position is closed by the application, the exit_reason will be set by the strategy engine:
- **"Stop Loss"** - Position closed at stop loss level
- **"Take Profit"** - Position closed at take profit level
- **"TP1 Hit"** - First take profit level reached
- **"TP2 Hit"** - Second take profit level reached
- **"TP3 Hit"** - Third take profit level reached
- **"Pattern Exit"** - Closed due to pattern re-entry
- **"Manual Close"** - Manually closed by user
- **"Cooldown Active"** - Another custom exit reason

### Historical Trades
Historical trades imported from MT5 show:
- **"CLOSED (Historical)"** - Trade closed in historical MT5 data

## Data Access

### Database Inspection
Run the inspection script to view all trades with exit reasons:
```bash
python inspect_db.py
```

This shows:
- Open positions (4 currently)
- Last 20 completed trades with exit reasons
- Total trade statistics
- Data consistency check

### Live UI Display
The application displays trade history in the **History tab** with columns:
1. Entry Time
2. Exit Time
3. Entry Price
4. Exit Price
5. Profit (color-coded)
6. **Exit Reason** ← Visible here
7. TP3 Level
8. Volume

## Database Records

### Current Statistics
- **Total closed trades:** 17 (historical)
- **Open positions:** 4
- **Trade history:** Complete with exit reasons
- **Data consistency:** ✅ CONSISTENT (DB ↔ JSON)

## Example Trades

```
Ticket | Entry Time          | Exit Time           | Reason
-------|---------------------|---------------------|-------------------
290    | 2026-01-09 01:01:13 | 2026-01-12 12:27:07 | CLOSED (Historical)
291    | 2026-01-09 11:25:47 | 2026-01-12 12:27:07 | CLOSED (Historical)
292    | 2026-01-09 18:09:31 | 2026-01-12 13:00:03 | CLOSED (Historical)
...
306    | 2026-01-23 12:00:19 | 2026-01-26 06:00:02 | CLOSED (Historical)
```

## Scripts Available

1. **inspect_db.py** - View database contents with exit reasons
2. **fetch_history.py** - Import MT5 historical trades with exit reasons
3. **update_reasons.py** - Update exit reasons in existing trades
4. **sync_db.py** - Synchronize JSON state to database

## Features

✅ Exit reason stored in database  
✅ Exit reason visible in History tab  
✅ Historical trades labeled appropriately  
✅ Current trades will record detailed exit reasons  
✅ Data consistency between DB and JSON  
✅ Crash-safe storage with WAL mode  
✅ Complete trade audit trail  

## Next Steps

When positions close during live trading:
1. Strategy engine records the exit_reason
2. State manager writes to both DB and JSON
3. History tab automatically updates
4. Exit reason is visible in the UI and database

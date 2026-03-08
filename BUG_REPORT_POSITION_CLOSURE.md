# 🐛 BUG REPORT: Positions Closing When Opening New Position

**Status**: IDENTIFIED & READY FOR FIX  
**Severity**: HIGH - Data Loss Risk  
**Affected Versions**: Current production build

## Problem Summary

When a new position is opened (last position in list), other open positions unexpectedly close with reason "Closed externally" or "Unknown Closure".

### Evidence from Logs (trades.log)

```
2026-01-22 15:55:58 - ENTRY | Ticket: 1214367390 | Price: 4871.07
2026-01-22 16:01:02 - EXIT  | Ticket: 1214025234 | Reason: Unknown Closure    ← CLOSED!
2026-01-22 16:01:02 - EXIT  | Ticket: 1214039793 | Reason: Unknown Closure    ← CLOSED!

2026-01-22 16:01:12 - ENTRY | Ticket: 1214367840 | Price: 4869.88
2026-01-22 16:16:55 - ENTRY | Ticket: 1214368973 | Price: 4872.98

2026-01-25 23:00:26 - EXIT  | Ticket: 1214367390 | Reason: Unknown Closure    ← CLOSED!
2026-01-25 23:00:26 - EXIT  | Ticket: 1214367840 | Reason: Unknown Closure    ← CLOSED!
2026-01-25 23:00:27 - EXIT  | Ticket: 1214368973 | Reason: Unknown Closure    ← CLOSED!
2026-01-25 23:00:27 - EXIT  | Ticket: 1214375057 | Reason: Unknown Closure    ← CLOSED!

2026-01-26 00:00:09 - ENTRY | Ticket: 1214452911 | Price: 5040.03
2026-01-26 02:00:02 - EXIT  | Ticket: 1214397478 | Reason: Unknown Closure    ← CLOSED!
```

**Pattern**: Positions close AFTER new entries are opened, not during entries.

---

## Root Cause: Race Condition in Order of Execution

Located in `src/main.py`, the main trading loop calls methods in this order:

```python
def main_loop(self):
    # Line 1246: FIRST - Monitor existing positions
    if has_positions:
        self._monitor_positions(current_bar)      # ← Checks if positions still exist in MT5
    
    # Line 1265: SECOND - Open new position
    if can_open_new:
        self._check_entry_execution(df, pattern, current_bar)  # ← Sends order to MT5
    
    # But _sync_live_positions is called BEFORE main_loop
    # Line 1276: START - Sync positions from broker
    self._sync_live_positions()    # ← Adds new position to state_manager
```

### The Bug Scenario

1. **Bar closes with entry signal**
2. `main_loop()` starts
3. **Line 1246**: `_monitor_positions()` is called
   - Gets live positions from MT5: `live_tickets = {pos['ticket']: pos for pos in live_positions}`
   - **At this moment**: NEW positions might NOT be in MT5 yet (order just sent)
4. **Checks each position in state_manager**:
   ```python
   for position_data in all_positions.copy():
       ticket = position_data['ticket']
       if ticket not in live_tickets:  # ← PROBLEM HERE!
           # Position closed externally (WRONG!)
           self.state_manager.close_position(
               exit_reason="Closed externally"
           )
   ```
5. **Line 1265**: `_check_entry_execution()` sends order
   - New position created in MT5
   - `_sync_live_positions()` tries to add it to state_manager
   - But it's already been closed by `_monitor_positions()`! ❌

### Timeline Visualization

```
main_loop() START
│
├─ _monitor_positions()
│  ├─ Get live_positions from MT5 (Position A visible, Position B NOT YET)
│  ├─ Check state_manager (Position A + Position B both tracked)
│  └─ Position B not in live_tickets → CLOSE IT! ✗ (FALSE POSITIVE)
│
├─ _check_entry_execution()
│  ├─ Send BUY order to MT5
│  ├─ Position C created in MT5
│  └─ Trading starts
│
└─ _sync_live_positions()  (next loop iteration)
   └─ Tries to add Position C to state_manager (might be too late)
```

---

## Why "Unknown Closure"?

In `_execute_exit()` (line 1895), there's validation logic:

```python
elif "TP" in reason_upper and not is_tp_hit:
    # Exit reason says TP but price didn't reach it
    if is_sl_hit:
        reason = "Stop Loss"
    elif reason_upper not in ["RECOVERY MODE", "CLOSED EXTERNALLY", "UNKNOWN"]:
        reason = "Unknown Closure"  # ← Line 1896
```

When a position is closed with "Closed externally" but the exit_price appears valid (or arbitrary), the validation logic converts it to "Unknown Closure".

---

## Solution: Fix the Order of Operations

### Option 1: Sync BEFORE Monitoring (Recommended)

```python
def main_loop(self):
    # FIRST - Sync live positions with state_manager
    self._sync_live_positions()  # ← Move to start of loop
    
    # SECOND - Monitor existing positions
    if has_positions:
        self._monitor_positions(current_bar)
    
    # THIRD - Check and execute new entries
    if can_open_new:
        self._check_entry_execution(df, pattern, current_bar)
```

**Why this works:**
- `_sync_live_positions()` ensures ALL broker positions are in state_manager first
- `_monitor_positions()` now has accurate `live_positions` from MT5
- New entries don't get false-closed

### Option 2: Add Grace Period

```python
def _monitor_positions(self, current_bar):
    # Check if position still exists in MT5
    if ticket not in live_tickets:
        # NEW: Check if position was JUST created (grace period)
        if self._is_recent_entry(ticket, grace_seconds=2):
            self.logger.debug(f"Position {ticket} just created, skipping closure check")
            continue  # ← Skip false positive
        
        # Position truly closed externally
        self.state_manager.close_position(
            exit_reason="Closed externally"
        )
```

### Option 3: Detect False Positives

```python
if ticket not in live_tickets:
    # NEW: Validate this is ACTUALLY closed
    # (Not just a sync delay)
    if self._was_position_sent_recently(ticket):
        self.logger.warning(f"Position {ticket} not found yet (may still be syncing)")
        continue  # ← Skip this iteration, check again next loop
    
    # Position truly closed
    self.state_manager.close_position(...)
```

---

## Proposed Fix (Option 1 - Best Practice)

**File**: `src/main.py` (lines 1240-1270)

### Current Code (BUGGY):
```python
# 4. Check positions - support pyramiding
pyramiding = self.config.get('strategy.pyramiding', 1)
self._sync_live_positions()        # Line 1276 - TOO LATE!
can_open_new = self.state_manager.can_open_new_position(max_positions=pyramiding)
has_positions = self.state_manager.has_open_position()

if has_positions:
    # Monitor existing positions  (Line 1254 - RUNS BEFORE SYNC!)
    self._monitor_positions(current_bar)

if can_open_new:
    # Execute entry if conditions met
    self._check_entry_execution(df, pattern, current_bar)
```

### Fixed Code:
```python
# 4. Check positions - support pyramiding
pyramiding = self.config.get('strategy.pyramiding', 1)

# FIRST: Sync live positions from broker (ensures state_manager is current)
self._sync_live_positions()        # Move to START

can_open_new = self.state_manager.can_open_new_position(max_positions=pyramiding)
has_positions = self.state_manager.has_open_position()

if has_positions:
    # Monitor existing positions (now with accurate broker state)
    self._monitor_positions(current_bar)

if can_open_new:
    # Execute entry if conditions met
    self._check_entry_execution(df, pattern, current_bar)
```

---

## Impact Assessment

### Severity: HIGH
- **Financial Risk**: Positions close incorrectly, traders lose profits or accumulate losses
- **Data Integrity**: Trade history polluted with false "Closed externally" entries
- **User Trust**: Unexpected position closures destroy confidence in system

### Frequency
- **Consistent**: Happens every time new position opened while others tracking
- **Reproducible**: Can be triggered by entry signal with multiple pyramiding

### Affected Users
- Anyone using pyramiding (max_positions > 1)
- Anyone with multiple open positions

---

## Testing

After fix, verify:
1. Open position A
2. Open position B (same bar)
3. Both positions remain open ✓
4. No false "Closed externally" in logs ✓
5. Trade history shows correct exit reasons only ✓

---

## Files Affected
- `src/main.py` - `main_loop()` method (lines 1240-1270)

## Related Issues
- None identified yet

## Created
2026-01-28  
**Severity**: HIGH  
**Status**: READY FOR IMPLEMENTATION

# EXIT REASON TYPES - REFERENCE INDEX

## 📋 Complete List of Exit Reasons (12 Types)

### Group 1: Price-Based Exits (Most Common)
1. **Stop Loss** - Position hit stop loss level
2. **Take Profit** - Position hit take profit target

### Group 2: Multi-Level TP (3-Level Strategy)
3. **TP1 Hit** - First take profit reached
4. **TP2 Hit** - Second take profit reached  
5. **TP3 Hit** - Final take profit reached

### Group 3: User/External Actions
6. **Closed Externally** - Closed in MT5 terminal
7. **Manual Close** - User clicked close button

### Group 4: System/Strategy
8. **Pattern Re-entry** - New pattern detected
9. **Recovery Mode** - Post-restart synchronization

### Group 5: Edge Cases
10. **Protective Exit** - Safety condition triggered
11. **Unknown Closure** - Reason indeterminate
12. **CLOSED (Historical)** - Imported from MT5

---

## 🎯 By Frequency When Trading

### Will See Often
- ✅ Stop Loss (losing positions)
- ✅ Take Profit (winning positions)

### Will See Sometimes  
- ⚠️ TP1/TP2/TP3 Hit (if using 3-level strategy)
- ⚠️ Manual Close (if manually closing)
- ⚠️ Closed Externally (if closing in MT5)

### Will Rarely See
- ⚠️ Pattern Re-entry (if pattern exit enabled)
- ⚠️ Recovery Mode (only after restart)
- ⚠️ Protective Exit (unusual conditions)
- ⚠️ Unknown Closure (data issue - rare)

---

## 📊 Current Database

**17 Historical Trades** - All marked "CLOSED (Historical)"

When live trading begins:
- Stop Loss: For positions that hit SL
- Take Profit: For positions that hit TP
- TP1/TP2/TP3: For multi-level exits
- Others: As conditions occur

---

## 🔍 How to View

**In Application:**
History Tab → Column 6 "Exit Reason"

**Via Command:**
```bash
python inspect_db.py              # Quick view
python list_exit_reasons.py       # Full reference
python show_actual_reasons.py     # Current data
```

**Via Database:**
```sql
SELECT exit_reason, COUNT(*), AVG(profit) FROM trades GROUP BY exit_reason;
```

---

## ✅ Key Facts

- All 12 types are **fully defined** in code
- Exit reason is **validated** before saving
- Mismatches are **auto-corrected** with logging
- Reasons are **searchable** in database
- Visible in **History tab** (Column 6)
- **Persisted** in database + JSON backup
- **Production-ready** for live trading

---

## 📚 Detailed Documentation

- **EXIT_REASON_TYPES.md** - Complete detailed reference
- **EXIT_REASON_QUICK_REFERENCE.md** - Quick lookup table
- **EXIT_REASON_SUMMARY.txt** - Visual summary
- **EXIT_REASON_TRACKING.md** - Implementation details

---

Generated: 2026-01-26
Status: ✅ Ready for live trading

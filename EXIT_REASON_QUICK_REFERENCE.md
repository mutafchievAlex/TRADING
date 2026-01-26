# EXIT REASON TYPES - QUICK REFERENCE

## 📊 Summary Table

| # | Exit Reason | Code | Trigger | Frequency | Status |
|---|------------|------|---------|-----------|--------|
| 1️⃣ | Stop Loss | "Stop Loss" | Price hits SL | Common | ✅ Ready |
| 2️⃣ | Take Profit | "Take Profit" | Price hits TP | Common | ✅ Ready |
| 3️⃣ | TP1 Hit | "TP1 Hit" | Price hits tp1_price | 3-Level TP | ✅ Ready |
| 4️⃣ | TP2 Hit | "TP2 Hit" | Price hits tp2_price | 3-Level TP | ✅ Ready |
| 5️⃣ | TP3 Hit | "TP3 Hit" | Price hits tp3_price | 3-Level TP | ✅ Ready |
| 6️⃣ | Closed Externally | "Closed externally" | Position disappears | Manual/MT5 | ✅ Ready |
| 7️⃣ | Pattern Exit | "Pattern re-entry" | New pattern found | Optional | ✅ Ready |
| 8️⃣ | Manual Close | "Manual Close" | User clicks button | Manual | ✅ Ready |
| 9️⃣ | Recovery Mode | "Recovery Mode" | Post-restart sync | Restart | ✅ Ready |
| 🔟 | Protective Exit | "Protective Exit - [...]" | Safety conditions | Edge case | ✅ Ready |
| 1️⃣1️⃣ | Unknown Closure | "Unknown Closure" | Data inconsistency | Rare | ✅ Ready |
| 1️⃣2️⃣ | Historical | "CLOSED (Historical)" | Imported from MT5 | Historical | ✅ In Use |

---

## 🎯 By Use Case

### **Simple Trading (Single TP)**
```
Entry → Stop Loss or Take Profit → Exit
└─ Records: "Stop Loss" or "Take Profit"
```

### **Multi-Level Trading (3-Level TP)**
```
Entry → TP1 Hit → Decision (Hold/Close)
     ↓
     → TP2 Hit → Decision + Trailing SL
     ↓
     → TP3 Hit → Automatic Close
     ↓
     → Stop Loss (if any level hit)

└─ Records: "TP1 Hit", "TP2 Hit", "TP3 Hit", or "Stop Loss"
```

### **User Interventions**
```
Entry → User clicks "Close Position" → Exit
└─ Records: "Manual Close"

OR

Entry → User closes in MT5 → System detects → Exit
└─ Records: "Closed externally"
```

### **System Restart**
```
Entry → System restart → Recovery engine → Sync with MT5
└─ Records: "Recovery Mode" (if closed during restart)
```

---

## 📝 Current Database

**Trades in Database:** 17  
**All Marked As:** "CLOSED (Historical)"  
**Source:** MT5 import  

**When Live Trading:**
- Will see: "Stop Loss", "Take Profit", "TP1 Hit", etc.
- Will track: Every closure with exact reason
- Will validate: Reason matches actual exit price
- Will correct: Any mismatches automatically

---

## 🔍 Finding Exit Reasons

### Best Source: Live Application
**Location:** History Tab → Column 6 "Exit Reason"  
**Shows:** All closed trades with their reason  

### Alternative: Command Line
```bash
python inspect_db.py       # Last 20 trades with reasons
python show_actual_reasons.py  # Summary of reason types
python list_exit_reasons.py    # All 12 possible types with details
```

### Advanced: Direct Database Query
```sql
-- Show all trades by exit reason
SELECT exit_reason, COUNT(*) as count, AVG(profit) as avg_profit
FROM trades
GROUP BY exit_reason
ORDER BY count DESC;
```

---

## ✅ Data Quality

**Validation Applied:**
- ✓ No reason is NULL
- ✓ No reason is a number (prices rejected)
- ✓ Reason matches actual exit price
- ✓ Auto-corrected if mismatch detected
- ✓ Logged for audit trail
- ✓ Persisted in database + JSON

**Recovery:** If reason corrupted, system derives from prices

---

## 🚀 Ready for Live Trading

All 12 exit reason types are:
✅ Defined in code  
✅ Validated by strategy engine  
✅ Stored in database  
✅ Visible in UI  
✅ Searchable and auditable  

The system is **production-ready** to track and display why each position was closed.

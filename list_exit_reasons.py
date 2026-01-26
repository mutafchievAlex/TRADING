#!/usr/bin/env python3
"""
Display all exit reason types used in the trading system.
"""

exit_reasons = {
    "1. STOP LOSS": {
        "description": "Position closed at stop loss level",
        "triggered_by": "Price reaches stop loss",
        "code": "Stop Loss",
        "frequency": "Common - when losing positions hit SL"
    },
    
    "2. TAKE PROFIT": {
        "description": "Position closed at main take profit level",
        "triggered_by": "Price reaches take_profit level",
        "code": "Take Profit",
        "frequency": "Common - standard winning position close"
    },
    
    "3. TP1 HIT": {
        "description": "First take profit level reached (multi-level exit)",
        "triggered_by": "Price reaches tp1_price",
        "code": "TP1 Hit",
        "frequency": "When using 3-level TP strategy"
    },
    
    "4. TP2 HIT": {
        "description": "Second take profit level reached (multi-level exit)",
        "triggered_by": "Price reaches tp2_price",
        "code": "TP2 Hit",
        "frequency": "When using 3-level TP strategy"
    },
    
    "5. TP3 HIT": {
        "description": "Third/Final take profit level reached (multi-level exit)",
        "triggered_by": "Price reaches tp3_price",
        "code": "TP3 Hit",
        "frequency": "When using 3-level TP strategy"
    },
    
    "6. CLOSED EXTERNALLY": {
        "description": "Position closed outside the application (e.g., manual close in MT5)",
        "triggered_by": "Position disappears from MT5 account",
        "code": "Closed externally",
        "frequency": "When user manually closes in MT5"
    },
    
    "7. PATTERN EXIT": {
        "description": "Position closed due to pattern re-entry condition",
        "triggered_by": "Pattern engine detects new valid pattern",
        "code": "Pattern re-entry",
        "frequency": "Optional - if pattern exit enabled"
    },
    
    "8. MANUAL CLOSE": {
        "description": "User manually closed the position from the UI",
        "triggered_by": "User clicks 'Close Position' button",
        "code": "Manual Close",
        "frequency": "When user manually intervenes"
    },
    
    "9. RECOVERY MODE": {
        "description": "Position closed by recovery engine after system restart",
        "triggered_by": "Recovery engine matching MT5 state",
        "code": "Recovery Mode",
        "frequency": "After restart if positions found"
    },
    
    "10. PROTECTIVE EXIT": {
        "description": "Exit due to protective conditions (e.g., TP not reached)",
        "triggered_by": "Protective logic in strategy",
        "code": "Protective Exit - [reason]",
        "frequency": "Rare - unusual market conditions"
    },
    
    "11. UNKNOWN CLOSURE": {
        "description": "Position closed but reason couldn't be determined",
        "triggered_by": "Unexpected closure conditions",
        "code": "Unknown Closure",
        "frequency": "Rare - debugging needed"
    },
    
    "12. CLOSED (HISTORICAL)": {
        "description": "Historical trade imported from MT5",
        "triggered_by": "Import from MT5 history",
        "code": "CLOSED (Historical)",
        "frequency": "All historical trades"
    },
}

def main():
    print("\n" + "="*90)
    print("TRADING SYSTEM - EXIT REASON TYPES")
    print("="*90 + "\n")
    
    for key, info in exit_reasons.items():
        print(f"📌 {key}")
        print(f"   Description:  {info['description']}")
        print(f"   Code Used:    '{info['code']}'")
        print(f"   Triggered:    {info['triggered_by']}")
        print(f"   Frequency:    {info['frequency']}")
        print()
    
    print("\n" + "="*90)
    print("MULTI-LEVEL TP EXIT DECISION REASONS")
    print("="*90 + "\n")
    
    print("When using 3-level Take Profit strategy:")
    print("  • TP1_REACHED → Evaluates POST_TP1 decision")
    print("  • TP2_REACHED → Evaluates POST_TP2 decision")
    print("  • TP3_REACHED → Final automatic close\n")
    
    print("Additional metadata tracked:")
    print("  • post_tp1_decision   - Hold/Close decision at TP1")
    print("  • tp1_exit_reason     - Why action taken at TP1")
    print("  • post_tp2_decision   - Hold/Close decision at TP2")
    print("  • tp2_exit_reason     - Why action taken at TP2")
    print("  • trailing_sl_level   - Trailing stop loss value")
    print("  • trailing_sl_enabled - Whether trailing SL active\n")
    
    print("="*90)
    print("VALIDATION RULES")
    print("="*90 + "\n")
    
    print("Exit reason is validated for accuracy:")
    print("  ✓ If 'TP3' reason → exit_price must reach TP3")
    print("  ✓ If 'TP' reason → exit_price must reach TP")
    print("  ✓ If 'Stop Loss' → exit_price must hit SL")
    print("  ✓ Mismatches are auto-corrected with warning\n")
    
    print("="*90)
    print("DATABASE PERSISTENCE")
    print("="*90 + "\n")
    
    print("All exit reasons are stored in: trades.exit_reason (TEXT field)")
    print("  • Visible in: History tab UI")
    print("  • Stored in:  SQLite database (data/state.db)")
    print("  • Backed up:  JSON file (data/state.json)")
    print("  • Searchable: SQL queries\n")
    
    print("="*90 + "\n")

if __name__ == '__main__':
    main()

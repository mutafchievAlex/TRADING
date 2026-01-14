# UI Panel Positions and Visibility

## Market Data Tab Structure (Top to Bottom)

```
┌─────────────────────────────────────────────┐
│ 1. Current Price (Existing)                 │
│    Price: [value]                           │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 2. Indicators (Existing)                    │
│    EMA 50, EMA 200, ATR 14                  │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 3. Pattern Detection (Existing)             │
│    Status and details                       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 4. Entry Conditions (Existing)              │
│    ✗ Pattern Valid                          │
│    ✗ Breakout Confirmed                     │
│    ✗ Above EMA50                            │
│    ✗ Momentum OK                            │
│    ✗ Cooldown OK                            │
└─────────────────────────────────────────────┘

╔═════════════════════════════════════════════╗
║ 5. Decision State Panel (NEW)               ║
║    📈 Decision: ENTER_LONG (Green)          ║
║    Reason: Pattern detected...              ║
║    Timestamp: 2025-01-09 14:30:00          ║
║    Bar Index: 150                           ║
║    Mode: BACKTEST                           ║
╚═════════════════════════════════════════════╝

╔═════════════════════════════════════════════╗
║ 6. Trade Preview Panel (NEW/Enhanced)       ║
║    Entry Price: 2700.50 (Blue)              ║
║    Stop Loss: 2690.00 (Red)                 ║
║    TP1 (RR 1:1.5): 2715.00 (Green)          ║
║    TP2 (RR 1:4.0): 2730.00 (Green)          ║
║    TP3 (RR 1:5.0): 2750.00 (Green)          ║
║    Risk Amount: $100.00 (Orange)            ║
║    Reward Projection: $290.00 (Green)       ║
║    Position Size: 0.1 lots                  ║
╚═════════════════════════════════════════════╝

╔═════════════════════════════════════════════╗
║ 7. Entry Quality Score Panel (NEW)          ║
║    Overall: 7.5/10 (Green)                  ║
║    Pattern: 7.0 | Trend: 8.0 |             ║
║    Momentum: 7.0 | Volatility: 8.0         ║
╚═════════════════════════════════════════════╝

╔═════════════════════════════════════════════╗
║ 8. Bar-Close Guard Status Panel (NEW)       ║
║    ✓ Using Closed Bar (Green)               ║
║    ✓ Tick Noise Filter: PASSED (Green)      ║
║    ✓ Anti-FOMO: PASSED (Green)              ║
╚═════════════════════════════════════════════╝
```

## Settings Tab Structure (Top to Bottom)

```
╔═════════════════════════════════════════════╗
║ 1. Runtime Context Panel (NEW)              ║
║    Runtime Mode: DEVELOPMENT (Orange)       ║
║    Auto Trading: ✗ Disabled (Orange)        ║
║    Account Type: DEMO (Green)               ║
║    MT5 Connection: CONNECTED (Green)        ║
║    Last Heartbeat: 2025-01-09 14:30:00     ║
╚═════════════════════════════════════════════╝

┌─────────────────────────────────────────────┐
│ 2. Strategy Parameters (Existing)           │
│    Risk per Trade, ATR Multiplier, etc.     │
└─────────────────────────────────────────────┘

...
```

## Visibility Rules

### Decision State Panel
- **Always Visible**: YES (shows for ALL decisions)
- **States**: ENTER_LONG (green), ENTER_SHORT (red), NO_TRADE (gray)

### Trade Preview Panel
- **Visible When**: decision in [ENTER_LONG, ENTER_SHORT]
- **Hidden When**: decision == NO_TRADE
- **Purpose**: Show what WOULD happen if trade executes

### Entry Quality Score Panel
- **Always Visible**: YES
- **Shows Score**: Even for NO_TRADE decisions
- **Purpose**: Understand why trade was filtered

### Bar-Close Guard Status Panel
- **Always Visible**: YES
- **Critical Info**: Pass/fail status of each guard
- **Safety**: Never hide critical information

### Runtime Context Panel
- **Always Visible**: YES (top of Settings tab)
- **Color Warnings**: Red for REAL account, Orange for auto-trading/mode
- **Purpose**: Prevent operator mistakes and running in wrong mode

## Color Coding Legend

| Color | Meaning | Examples |
|-------|---------|----------|
| 🟢 Green | Good/Passed/Safe | PASSED, CONNECTED, DEMO, Quality>=7.0 |
| 🔴 Red | Bad/Failed/Danger | BLOCKED, REAL account, Quality<5.0 |
| 🟠 Orange | Warning/Attention | RECONNECTING, DEVELOPMENT mode, disabled |
| 🔵 Blue | Informational | Entry price, timestamp |

## Update Method Integration

All update methods should be called from `main.py` in the `_update_ui()` loop:

```python
def _update_ui(self):
    """Update all UI panels from latest engine state."""
    
    # Get latest decision
    decision_output = decision_engine.last_output
    
    # Update all panels
    self.window.update_decision_state(decision_output)
    self.window.update_position_preview(decision_output)
    self.window.update_quality_score(decision_output)
    self.window.update_guard_status(decision_output)
    self.window.update_runtime_context(runtime_context)
    
    # ... other UI updates ...
```

## Critical Safety Panels

These panels are CRITICAL and must never be hidden:

1. **Decision State Panel** - What did system decide?
2. **Bar-Close Guard Status Panel** - Are all guards passing?
3. **Runtime Context Panel** - How is system configured?

All others can be conditional, but these three must always be visible.

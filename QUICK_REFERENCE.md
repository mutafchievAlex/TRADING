# Quick Reference: Dynamic TP Manager & Market Context

## For Trading Users

### What You'll See in the UI

#### 1. Market Data Tab - Entry Quality Gate
```
Quality Gate Status:  ✓ (or ✗ if rejected)
Quality Score:        7.2 / 10.0
  - Pattern:          8.0
  - Momentum:         7.5
  - EMA Alignment:    8.0
  - Volatility:       6.0
Market Regime:        BULL
Volatility State:     NORMAL
```

#### 2. Positions Tab - Trade Cash Values
```
Position Table Row:

Ticket    Entry      Current    SL       TP       Level  Risk$   TP1$    TP2$    TP3$    P&L
------    -----      -------    --       --       -----  -----   ----    ----    ----    ---
123456  2000.00    2050.00   1950.00  2125.00   TP1    $500    $700    $950   $1250   $500

Colors:
- Risk $:  Orange (what you can lose)
- TP* $:   Green  (what you can gain at each level)
```

### How It Works

**Entry**
1. You open a position at Entry Price
2. System calculates:
   - Risk = Distance from Entry to SL, multiplied by position size
   - TP1 = Entry + (Risk × 1.4)
   - TP2 = Entry + (Risk × 1.9)
   - TP3 = Entry + (Risk × 2.5)

**Cash Display**
- Risk $: How much money is at risk if SL is hit
- TP1 $ / TP2 $ / TP3 $: How much profit you'd make at each level

**Progression**
- TP Level column shows your current target (TP1, TP2, or TP3)
- When price hits TP Level, moves to next level
- SL moves up to protect profits

**Auto-Exit**
- If price retraces sharply, system auto-exits (fallback protection)
- Prevents giving back large profits

### Quality Gate (Entry Filter)

Only entries with Quality Score ≥ 6.5 are allowed.

**Score Breakdown:**
- 0-4: Poor conditions
- 4-6.5: Weak conditions
- 6.5-7.5: Good conditions ✓
- 7.5-8.5: Excellent conditions ✓
- 8.5-10: Outstanding conditions ✓

**Why?** Filters out low-probability setups, improves win rate.

---

## For Developers

### File Structure
```
src/
  engines/
    dynamic_tp_manager.py       # TP cash calculations & lifecycle
    market_context_engine.py    # Quality scoring & entry gate
    tp_engine.py                # TP level transitions & SL mgmt
    state_manager.py            # Position persistence
  main.py                        # Integration orchestrator
  ui/
    main_window.py              # Display cash values in UI
```

### Key Methods

#### TPManager
```python
# Register trade entry with cash calculations
tp_manager.open_trade(ticket, entry_price, stop_loss, volume, direction)
# Returns: {risk_cash, tp1_price, tp1_cash, tp2_price, tp2_cash, ...}

# Evaluate if TP hit (called by TPEngine internally)
tp_manager.evaluate_tp_progression(ticket, current_price)
# Returns: new TP level if progressed, None otherwise

# Check for fallback exit
tp_manager.check_fallback_exit(ticket, current_price)
# Returns: exit data if triggered, None otherwise

# Close trade and calculate P&L
tp_manager.close_trade(ticket, close_price, reason)
# Returns: {close_price, pnl, close_reason, ...}

# Get cash summary for UI
tp_manager.get_trade_cash_summary(ticket)
# Returns: {risk_cash, tp1_cash, tp2_cash, tp3_cash}
```

#### MarketContextEngine
```python
# Calculate entry quality score
quality_score, components = engine.calculate_entry_quality_score(
    current_bar, entry_details, pattern_info
)
# Returns: score (0-10), components dict

# Check if quality passes gate
passes_gate, reason = engine.evaluate_entry_gate(quality_score)
# Returns: bool, str (reason if failed)

# Get market regime
regime = engine.detect_market_regime(ema50, ema200)
# Returns: "BULL", "BEAR", or "RANGE"

# Get volatility state
vol_state = engine.detect_volatility_state(atr, close_price)
# Returns: "LOW", "NORMAL", or "HIGH"
```

### Integration Points

#### In _check_entry()
```python
# Calculate quality
quality_score, components = self.market_context_engine.calculate_entry_quality_score(...)

# Evaluate gate
passes_gate, reason = self.market_context_engine.evaluate_entry_gate(quality_score)

# Reject if failed
if not passes_gate:
    return False
```

#### In _execute_entry()
```python
# Register trade
tp_state = self.tp_manager.open_trade(ticket, entry, sl, size, "LONG")

# Store cash values
position_data = {
    'risk_cash': tp_state.get('risk_cash'),
    'tp1_cash': tp_state['tp_levels']['TP1']['cash'],
    'tp2_cash': tp_state['tp_levels']['TP2']['cash'],
    'tp3_cash': tp_state['tp_levels']['TP3']['cash'],
    ...
}

self.state_manager.open_position(position_data)
```

#### In _monitor_positions()
```python
# TP progression handled by tp_engine (not tp_manager)
tp_transitioned, reason = self.tp_engine.evaluate_tp_transition(...)

# Close trade when exiting
tp_closure = self.tp_manager.close_trade(ticket, exit_price, "TP_HIT")
```

#### In UI update
```python
# Send quality components to display
self.window.update_market_context(quality_components)

# Update position table
self.window.update_position_display(all_positions)
```

### Cash Calculation Formula

For XAUUSD (100 multiplier):
```
risk_pips = abs(entry - stop_loss)
risk_cash = risk_pips × volume × 100

tp1_pips = risk_pips × 1.4
tp1_cash = tp1_pips × volume × 100

tp2_pips = risk_pips × 1.9
tp2_cash = tp2_pips × volume × 100

tp3_pips = risk_pips × 2.5 (or custom RR)
tp3_cash = tp3_pips × volume × 100
```

**Example:**
```
Entry: 2000.00
SL:    1950.00
Volume: 0.1

risk_pips = 50
risk_cash = 50 × 0.1 × 100 = $500

TP1 = 2000 + 70 = 2070
tp1_cash = 70 × 0.1 × 100 = $700

TP2 = 2000 + 95 = 2095
tp2_cash = 95 × 0.1 × 100 = $950

TP3 = 2000 + 125 = 2125
tp3_cash = 125 × 0.1 × 100 = $1250
```

### Quality Score Calculation

```
quality_score = (pattern_score × 0.35) + 
                (momentum_score × 0.25) + 
                (ema_score × 0.25) + 
                (volatility_score × 0.15)
```

Each component is scored 0-10:
- **Pattern**: Quality of Double Bottom detection
- **Momentum**: Strength of EMA50 uptrend
- **EMA**: Alignment quality (50 above 200)
- **Volatility**: ATR% appropriateness

Gate check:
```
if quality_score >= 6.5:
    allow_entry()  # ✓
else:
    reject_entry(f"Quality {quality_score:.2f} < 6.5")  # ✗
```

### State Persistence

Position data saved to `data/state.json`:
```json
{
  "positions": [
    {
      "ticket": 123456,
      "entry_price": 2000.00,
      "stop_loss": 1950.00,
      "tp_level": "TP1",
      "tp_value": 2070.00,
      "risk_cash": 500.00,
      "tp1_cash": 700.00,
      "tp2_cash": 950.00,
      "tp3_cash": 1250.00,
      ...
    }
  ]
}
```

On restart, all cash values are loaded from state (no recalculation).

### Testing Checklist

- [ ] Quality gate accepts score >= 6.5
- [ ] Quality gate rejects score < 6.5
- [ ] Cash values match formula: pips × size × 100
- [ ] Position table displays Risk $ and TP*$
- [ ] Percent change badges show in Market Data tab
- [ ] TP level progresses: TP1 → TP2 → TP3
- [ ] Fallback exit triggers on retrace
- [ ] State persists across restart
- [ ] P&L displays correctly on close

---

**Remember:**
- Quality Gate = Entry Filter (rejects low-probability setups)
- Cash Display = Trade Context (shows monetary risk/reward)
- TP Progression = Trade Management (moves to next level)
- State Persistence = Restart Safety (data survives app crash)

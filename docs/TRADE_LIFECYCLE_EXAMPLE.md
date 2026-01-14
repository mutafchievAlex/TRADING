# Complete Trade Lifecycle: End-to-End Walkthrough

This document shows exactly what happens at each stage of a trade, from entry decision through closure.

---

## Trade Setup

**Instrument**: XAUUSD (Gold)  
**Timeframe**: 1H  
**Entry Pattern**: Double Bottom detected at 2000.00  
**Stop Loss**: 1950.00 (50 pips risk)  
**Position Size**: 0.1 lot  

---

## Stage 1: Entry Decision (T = 0)

### Step 1.1: Pattern Detection
```
Bar Close: 1995.00
EMA50: 1998.50
EMA200: 1980.00
Double Bottom detected: YES
Pattern strength: 85%
```

### Step 1.2: Market Context Analysis

**MarketContextEngine.calculate_entry_quality_score()**

Evaluates four components:
```
1. Pattern Quality (35% weight)
   - Double bottom detected: YES
   - Pattern strength: 85%
   → Pattern Score: 8.5 / 10.0

2. Momentum Score (25% weight)
   - EMA50 above EMA200: YES (1998.50 > 1980.00)
   - Distance from EMA200: 18.5 pips (good separation)
   - Slope of EMA50: positive
   → Momentum Score: 8.0 / 10.0

3. EMA Alignment Score (25% weight)
   - EMA50 > EMA200: YES (bullish structure)
   - Price above EMA50: YES (price above fastest MA)
   - Clean structure: YES
   → EMA Score: 8.0 / 10.0

4. Volatility Score (15% weight)
   - ATR14: 15 pips
   - ATR% (15/2000): 0.75%
   - Assessment: NORMAL volatility
   - Appropriateness: Good
   → Volatility Score: 6.5 / 10.0
```

**Quality Score Calculation:**
```
Quality = (8.5 × 0.35) + (8.0 × 0.25) + (8.0 × 0.25) + (6.5 × 0.15)
Quality = 2.975 + 2.0 + 2.0 + 0.975
Quality = 7.95 / 10.0
```

### Step 1.3: Quality Gate Check

**MarketContextEngine.evaluate_entry_gate(7.95)**

```
Gate Threshold: 6.5 / 10.0
Quality Score:  7.95 / 10.0
Comparison:     7.95 >= 6.5 → TRUE

Entry Status: ✓ APPROVED
Reason: "Quality gate passed (7.95/10)"
```

### Step 1.4: Log Entry
```
[INFO] Market context check passed:
       - Quality Score: 7.95/10
       - Market Regime: BULL
       - Volatility: NORMAL (0.75%)
       - Pattern: 85% confidence
```

---

## Stage 2: Order Execution (T = 0+)

### Step 2.1: Risk Management

```
Entry Price:   2000.00
Stop Loss:     1950.00
Risk (pips):   50
Position Size: 0.1
```

### Step 2.2: TP Manager Trade Registration

**TPManager.open_trade()**

```python
ticket = 123456
entry_price = 2000.00
stop_loss = 1950.00
position_size = 0.1
direction = "LONG"
```

**Risk Calculation:**
```
Risk pips = |2000.00 - 1950.00| = 50 pips
Risk cash = 50 × 0.1 × 100 = $500
```

**TP Level Calculations:**
```
TP1:
  pips = 50 × 1.4 = 70 pips
  price = 2000.00 + 70 = 2070.00
  cash = 70 × 0.1 × 100 = $700

TP2:
  pips = 50 × 1.9 = 95 pips
  price = 2000.00 + 95 = 2095.00
  cash = 95 × 0.1 × 100 = $950

TP3 (user RR = 2.5):
  pips = 50 × 2.5 = 125 pips
  price = 2000.00 + 125 = 2125.00
  cash = 125 × 0.1 × 100 = $1250
```

**Returned Trade Data:**
```python
{
    'ticket': 123456,
    'entry_price': 2000.00,
    'stop_loss': 1950.00,
    'volume': 0.1,
    'direction': 'LONG',
    'risk_pips': 50,
    'risk_cash': 500.00,
    'tp1_price': 2070.00,
    'tp1_cash': 700.00,
    'tp2_price': 2095.00,
    'tp2_cash': 950.00,
    'tp3_price': 2125.00,
    'tp3_cash': 1250.00,
    'current_tp_level': 'TP1',
    'current_tp_price': 2070.00,
}
```

### Step 2.3: StateManager Persistence

**StateManager.open_position()**

```python
position_data = {
    'ticket': 123456,
    'entry_price': 2000.00,
    'stop_loss': 1950.00,
    'take_profit': 2125.00,
    'volume': 0.1,
    'tp_level': 'TP1',
    'tp_value': 2070.00,
    'risk_cash': 500.00,
    'tp1_cash': 700.00,
    'tp2_cash': 950.00,
    'tp3_cash': 1250.00,
    'entry_time': datetime.now(),
}
```

Persisted to `data/state.json`

### Step 2.4: MT5 Order Execution

```
[MT5] BUY 0.1 XAUUSD @ 2000.00
SL: 1950.00
TP: 2125.00 (automatic TP at TP3)
Ticket: 123456
Status: FILLED
```

### Step 2.5: UI Update

**MainWindow.update_position_display()**

Position table displays:
```
┌────────┬────────┬─────────┬──────┬──────┬───────┬─────────┬─────────┬──────────┬──────────────┐
│ Ticket │ Entry  │ Current │  SL  │  TP  │ Level │ Risk $  │ TP1 $   │ TP2 $    │ TP3 $        │
├────────┼────────┼─────────┼──────┼──────┼───────┼─────────┼─────────┼──────────┼──────────────┤
│ 123456 │ 2000.0 │ 2000.0  │ 1950 │ 2125 │  TP1  │ $500    │ $700    │ $950     │ $1250        │
└────────┴────────┴─────────┴──────┴──────┴───────┴─────────┴─────────┴──────────┴──────────────┘

Colors:
- Risk $: Orange (#ff9800) - what you can lose
- TP* $:  Green (#4caf50)  - what you can gain
```

### Step 2.6: Logging

```
[INFO] ✓ Trade executed successfully:
       Ticket: 123456
       Entry: 2000.00
       SL: 1950.00
       TP1: 2070.00 ($700)
       TP2: 2095.00 ($950)
       TP3: 2125.00 ($1250)
       Risk: $500
```

---

## Stage 3: Price Movement & TP Progression (T+1 to T+6)

### Bar 1 (T+1): Price = 2010.00
```
TP Engine evaluates: 2010.00 vs TP1 (2070.00)
Result: Not hit yet
Current Level: TP1 (unchanged)
UI Display:
  Current: 2010.00
  Level: TP1
  P&L: +$100
```

### Bar 2 (T+2): Price = 2040.00
```
TP Engine evaluates: 2040.00 vs TP1 (2070.00)
Result: Still approaching
Current Level: TP1 (unchanged)
UI Display:
  Current: 2040.00
  Level: TP1
  P&L: +$400
```

### Bar 3 (T+3): Price = 2070.00 ← TP1 HIT
```
TP Engine evaluates: 2070.00 vs TP1 (2070.00)
Result: TP1 PRICE REACHED

TPEngine actions:
  1. Mark TP1 as hit
  2. Move SL to Entry (2000.00) - breakeven protection
  3. Transition to TP2 mode
  4. Set current_tp_price = 2095.00

TPManager state:
  current_tp_level: 'TP1' → 'TP2'
  current_tp_price: 2070.00 → 2095.00

UI Display:
  Current: 2070.00
  Level: TP1 → TP2 (UPDATED)
  P&L: +$700
  
Log:
  [INFO] TP1 hit! Progressed to TP2.
         SL moved to breakeven (2000.00)
```

### Bar 4 (T+4): Price = 2085.00
```
TP Engine evaluates: 2085.00 vs TP2 (2095.00)
Result: Approaching TP2
Current Level: TP2
UI Display:
  Current: 2085.00
  Level: TP2
  P&L: +$850
```

### Bar 5 (T+5): Price = 2095.00 ← TP2 HIT
```
TP Engine evaluates: 2095.00 vs TP2 (2095.00)
Result: TP2 PRICE REACHED

TPEngine actions:
  1. Mark TP2 as hit
  2. Move SL to TP1 level (2070.00) - protect TP1 profit
  3. Transition to TP3 mode
  4. Set current_tp_price = 2125.00

TPManager state:
  current_tp_level: 'TP2' → 'TP3'
  current_tp_price: 2095.00 → 2125.00

UI Display:
  Current: 2095.00
  Level: TP2 → TP3 (UPDATED)
  P&L: +$950
  
Log:
  [INFO] TP2 hit! Progressed to TP3.
         SL moved to protect profit (2070.00)
```

### Bar 6 (T+6): Price = 2115.00
```
TP Engine evaluates: 2115.00 vs TP3 (2125.00)
Result: Final approach
Current Level: TP3
UI Display:
  Current: 2115.00
  Level: TP3
  P&L: +$1150
```

---

## Stage 4: Trade Closure (T+7)

### Bar 7 (T+7): Price = 2125.00 ← TP3 HIT
```
TP Engine evaluates: 2125.00 vs TP3 (2125.00)
Result: TP3 PRICE REACHED - TRADE CLOSED

Close Action:
  Close Price: 2125.00
  Close Reason: "TP_HIT" (TP3)
  Close Time: Current bar close
```

### Step 4.1: TPManager Trade Closure

**TPManager.close_trade()**

```python
ticket = 123456
close_price = 2125.00
close_reason = "TP_HIT"
```

**P&L Calculation (BUY):**
```
P&L = (close_price - entry_price) × volume × 100
P&L = (2125.00 - 2000.00) × 0.1 × 100
P&L = 125 × 0.1 × 100
P&L = $1250.00

Return on Risk (RoR):
RoR = P&L / Risk
RoR = 1250 / 500 = 2.5:1 (exactly at TP3 RR)
```

**Trade Closure Data:**
```python
{
    'ticket': 123456,
    'entry_price': 2000.00,
    'close_price': 2125.00,
    'stop_loss': 1950.00,
    'volume': 0.1,
    'pnl': 1250.00,
    'close_reason': 'TP_HIT',
    'close_time': datetime.now(),
    'duration': '6 bars (6 hours)',
}
```

### Step 4.2: StateManager - Position Closure

**StateManager.close_position()**

Moves position from `positions` list to `closed_trades` list:

```json
{
  "closed_trades": [
    {
      "ticket": 123456,
      "entry_price": 2000.00,
      "close_price": 2125.00,
      "stop_loss": 1950.00,
      "volume": 0.1,
      "pnl": 1250.00,
      "close_reason": "TP_HIT",
      "duration_hours": 6,
      "risk_cash": 500.00,
      "tp3_cash": 1250.00,
      "return_on_risk": 2.5
    }
  ]
}
```

### Step 4.3: UI Updates

**Position Table:**
- Position row removed from active positions
- Added to History tab

**History Tab:**
```
┌────────┬────────┬──────────┬──────┬────────┬────────────┬─────────────┐
│ Ticket │ Entry  │  Close   │ Time │  P&L   │ Close Rsn  │   RoR       │
├────────┼────────┼──────────┼──────┼────────┼────────────┼─────────────┤
│ 123456 │ 2000.0 │ 2125.00  │ 6H   │ +$1250 │ TP3 Hit    │ 2.5:1 (Max) │
└────────┴────────┴──────────┴──────┴────────┴────────────┴─────────────┘

Color: Green (winning trade)
```

**Statistics Updated:**
```
Today's Stats:
- Total Trades: 1
- Wins: 1 (100%)
- Total P&L: +$1250
- Average RoR: 2.5:1
- Win Rate: 100%
```

### Step 4.4: Logging

```
[INFO] Trade #123456 closed:
       Close Price: 2125.00
       Close Reason: TP3 HIT
       P&L: +$1250.00
       RoR: 2.5:1 (perfect execution)
       Duration: 6 bars
```

---

## Stage 5: Trade History & Statistics

### Summary Statistics
```
Trade: #123456 - CLOSED ✓

Entry Details:
  Time: Bar 0
  Price: 2000.00
  Pattern: Double Bottom (85% confidence)
  Quality Score: 7.95/10

Risk Details:
  Stop Loss: 1950.00
  Risk: 50 pips ($500)
  Position Size: 0.1 lot

TP Progression:
  TP1 Hit @ 2070.00 (Bar 3) → +$700
  TP2 Hit @ 2095.00 (Bar 5) → +$950
  TP3 Hit @ 2125.00 (Bar 7) → +$1250

Exit Details:
  Type: TP3 Hit
  Time: Bar 7
  Price: 2125.00
  P&L: +$1250
  RoR: 2.5:1
  Duration: 6 hours (6 bars × 1H)

Trade Quality:
  - Entered at high quality score (7.95/10) ✓
  - Full progression achieved (TP1→TP2→TP3) ✓
  - No fallback exits needed ✓
  - Maximum profit captured ✓
```

### Persisted in History
```
data/state.json:
{
  "trade_history": [
    {
      "ticket": 123456,
      "entry_price": 2000.00,
      "entry_time": "2024-01-15T10:00:00",
      "close_price": 2125.00,
      "close_time": "2024-01-15T16:00:00",
      "stop_loss": 1950.00,
      "take_profit": 2125.00,
      "volume": 0.1,
      "pnl": 1250.00,
      "return_on_risk": 2.5,
      "close_reason": "TP_HIT",
      "quality_score": 7.95,
      "pattern_type": "Double Bottom"
    }
  ]
}
```

---

## Key Observations

### 1. Quality Gate Success
- Entry quality score (7.95/10) was above gate (6.5/10)
- Resulted in high-probability trade
- Full progression to TP3 achieved

### 2. Cash Display Accuracy
- Risk $: $500 (correct: 50 × 0.1 × 100)
- TP1 $: $700 (correct: 70 × 0.1 × 100)
- TP2 $: $950 (correct: 95 × 0.1 × 100)
- TP3 $: $1250 (correct: 125 × 0.1 × 100)

### 3. TP Progression Logic
- Each TP level transitioned smoothly
- SL moved up to protect profits
- No false signals or retracements

### 4. State Persistence
- All trade data persisted to state.json
- UI can be closed and reopened without data loss
- History preserved for backtesting/analysis

### 5. Zero Fallback Exits
- Price never retraced significantly
- Fallback exit logic not triggered (trade was clean)
- This is ideal scenario for max profit

---

## Comparison: Low Quality Entry Rejection

If entry quality score had been 5.5/10:
```
[INFO] Entry rejected: Quality gate failed (5.5 < 6.5)
       Entry NOT taken
       Position NOT opened
       No risk taken

Result: Avoided low-probability trade
```

---

## Next Trade (T+8+)

After closing trade #123456:

1. StateManager clears position from active list
2. Position no longer shown in Position Tab
3. Trade added to History tab
4. Statistics updated
5. Strategy engine ready for next pattern detection
6. Quality gate continues to filter entries
7. Next pattern → Next quality score → Next trade

---

**Summary:**
- Quality Gate: ✓ (7.95 >= 6.5)
- Entry Execution: ✓ (Trade opened)
- TP Progression: ✓ (TP1→TP2→TP3 all hit)
- Cash Display: ✓ (All values accurate)
- Closure: ✓ (TP3 hit, +$1250)
- Persistence: ✓ (Data saved to state.json)
- Statistics: ✓ (Trade recorded in history)

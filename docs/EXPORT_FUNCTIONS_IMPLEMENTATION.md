# Export Functions Implementation - Task 2.4

**Status**: ✅ COMPLETED  
**Phase**: Phase 2 - Critical Bug Fixes  
**Task**: 2.4 - Export Functions  
**Date**: January 16, 2026

## Overview

Implemented complete export functionality for backtest results in three formats:
1. **JSON** - Machine-readable, structured data
2. **CSV** - Spreadsheet-compatible trade list
3. **HTML** - Interactive report with visualizations

## Implementation Details

### Architecture

```
┌─────────────────────────────────────────────┐
│     Backtest Results (in Memory)            │
│  ├─ summary (metrics summary)               │
│  ├─ metrics (detailed stats)                │
│  ├─ trades_df (DataFrame with trades)       │
│  ├─ equity_curve (P/L over time)            │
│  └─ settings (strategy configuration)       │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴─────────┬──────────────┐
        │                   │              │
        ▼                   ▼              ▼
   ┌─────────┐         ┌─────────┐   ┌─────────┐
   │ JSON    │         │ CSV     │   │ HTML    │
   │ Export  │         │ Export  │   │ Export  │
   └────┬────┘         └────┬────┘   └────┬────┘
        │                   │              │
        ▼                   ▼              ▼
   state.json          trades.csv     report.html
   (~50KB)             (~10KB)        (~200KB+)

Stored in: ./reports/
Named: XAUUSD_H1_backtest_last30d_YYYYMMDD_HHMM.{json|csv|html}
```

### File: src/main.py

**Three new export methods in TradingController**:

```python
def _on_export_json_requested(self):
    """Export backtest results as JSON."""
    # 1. Get backtest data from UI
    # 2. Create BacktestReportExporter instance
    # 3. Call exporter.export_json()
    # 4. Update UI status with result

def _on_export_csv_requested(self):
    """Export backtest results as CSV."""
    # 1. Get backtest data from UI
    # 2. Create BacktestReportExporter instance
    # 3. Call exporter.export_csv()
    # 4. Update UI status with result

def _on_export_html_requested(self):
    """Export backtest results as HTML."""
    # 1. Get backtest data from UI
    # 2. Create BacktestReportExporter instance
    # 3. Call exporter.export_html()
    # 4. Update UI status with result
    # 5. Open in browser (optional)
```

**Integration Points**:

1. **BacktestWindow Signal Connection** (in `set_window()`):
   ```python
   window.backtest_window.export_json_clicked = self._on_export_json_requested
   window.backtest_window.export_csv_clicked = self._on_export_csv_requested
   window.backtest_window.export_html_clicked = self._on_export_html_requested
   ```

2. **Data Flow**:
   - Backtest completes → `_on_backtest_completed()` called
   - UI stores result in `backtest_window.last_result`
   - User clicks "Export JSON/CSV/HTML" button
   - Signal triggers `_on_export_xxx_requested()`
   - Exporter reads from `last_result` and writes to disk

3. **Status Updates**:
   ```
   Before export: "No backtest results to export"
                       ↓
   During export: (processing)
                       ↓
   Success:      "✓ Exported JSON: XAUUSD_H1_backtest_20260116_1420.json"
                       ↓
   Error:        "✗ JSON export failed" or "Export error: {message}"
   ```

### File: src/engines/backtest_report_exporter.py

**Uses existing exporter with three methods**:

#### Method 1: export_json()
```python
exporter.export_json(
    summary=result['summary'],         # Backtest summary metrics
    metrics=result['metrics'],         # Detailed statistics
    trades_df=result['trades_df'],     # All trades as DataFrame
    settings=config.get_strategy_config()  # Settings snapshot
)
```

**Output Structure**:
```json
{
  "backtest_info": {
    "symbol": "XAUUSD",
    "timeframe": "H1",
    "generated_at": "2026-01-16T14:30:45.123456",
    "period_days": 30
  },
  "metrics": {
    "total_trades": 5,
    "winning_trades": 3,
    "losing_trades": 2,
    "win_rate": 60.0,
    "total_profit": 250.50,
    "average_win": 120.25,
    "average_loss": -35.12,
    "profit_factor": 3.41
  },
  "summary": {
    "period_start": "2025-12-17 14:30:00",
    "period_end": "2026-01-16 14:30:00",
    "total_trades": 5,
    ...
  },
  "settings": {
    "risk_percent": 1.0,
    "atr_multiplier_stop": 2.0,
    "risk_reward_ratio_long": 2.0,
    "enable_momentum_filter": true
  },
  "trades": [
    {
      "ticket": 12345,
      "entry_price": 2000.50,
      "exit_price": 2020.75,
      "stop_loss": 1990.25,
      "take_profit": 2041.00,
      "profit": 250.50,
      "reason": "Take Profit TP3"
    },
    ...
  ]
}
```

**File Size**: ~50KB (5-50 trades)

#### Method 2: export_csv()
```python
exporter.export_csv(
    trades_df=result['trades_df'],
    settings=config.get_strategy_config()
)
```

**Output Format**:
```
ticket,entry_price,exit_price,stop_loss,take_profit,profit,reason,entry_time,exit_time
12345,2000.50,2020.75,1990.25,2041.00,250.50,"Take Profit TP3",2026-01-15 10:00:00,2026-01-15 12:30:00
12346,1995.25,1985.50,1985.00,2015.75,-50.25,"Stop Loss",2026-01-15 13:00:00,2026-01-15 13:45:00
...
```

**File Size**: ~10KB (typically smaller than JSON)

**Use Case**: Open in Excel/Google Sheets for manual analysis

#### Method 3: export_html()
```python
exporter.export_html(
    summary=result['summary'],
    metrics=result['metrics'],
    trades_df=result['trades_df'],
    equity_curve=result['equity_curve'],
    settings=config.get_strategy_config()
)
```

**Output Features**:
- Self-contained HTML (no external dependencies)
- Embedded CSS styling
- ASCII charts (equity curve)
- Summary cards (metrics overview)
- Trades table (sortable if JavaScript enabled)
- Settings snapshot
- Interactive tooltips (JavaScript)

**File Size**: ~200KB+ (includes embedded styles)

**Use Case**: 
- Email to stakeholders
- Client reporting
- Archival (self-contained file)
- Browser viewing without server

---

## Flow Diagram

```
┌────────────────────────────────────────────────┐
│      Backtest Completes                        │
│  _on_backtest_completed(result)                │
└──────────────────┬─────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
   ┌──────────────┐   ┌──────────────┐
   │ Store in     │   │ Update UI    │
   │ backtest_    │   │ with results │
   │ window.last_ │   └──────────────┘
   │ result       │
   └──────┬───────┘
          │
    User clicks "Export JSON"
          │
          ▼
   ┌────────────────────────────────────┐
   │ UI emits export_json_clicked signal│
   └────────────────┬───────────────────┘
                    │
                    ▼
          ┌─────────────────────┐
          │_on_export_json_     │
          │requested()          │
          └────────┬────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
         ▼                    ▼
    ┌─────────────┐    ┌──────────────┐
    │ Create      │    │ Get MT5 config│
    │ exporter    │    │ (symbol,TF)  │
    └────┬────────┘    └──────────────┘
         │
         ├─ exporter.export_json(
         │    summary, metrics,
         │    trades_df, settings
         │  )
         │
         ▼
   ┌─────────────────────────────────┐
   │ Write to file:                  │
   │ reports/XAUUSD_H1_backtest_...  │
   │ _20260116_1420.json             │
   └────────────┬────────────────────┘
                │
                ▼
   ┌─────────────────────────────────┐
   │ Update UI status bar:           │
   │ "✓ Exported JSON: filename.json"│
   └─────────────────────────────────┘
```

---

## Usage from UI

### Backtest Tab Export Buttons

The BacktestWindow provides three export buttons:

```
┌────────────────────────────────────┐
│     BACKTEST RESULTS               │
├────────────────────────────────────┤
│ Metrics: Total: 5 | Win Rate: 60% │
├────────────────────────────────────┤
│ [Export JSON] [Export CSV] [HTML]  │ ◄─── User clicks
├────────────────────────────────────┤
│ Status: ✓ Exported JSON: ...json   │ ◄─── Feedback
└────────────────────────────────────┘
```

### Command Flow

1. **User clicks "Export JSON"**
   - UI sends `export_json_clicked` signal

2. **Signal received**
   - `_on_export_json_requested()` executes

3. **Validation**
   - Check if backtest results exist
   - Return error if none: "No backtest results to export"

4. **Exporter Creation**
   - Create `BacktestReportExporter` instance
   - Pass symbol and timeframe from MT5 config

5. **Export**
   - Call `exporter.export_json(summary, metrics, trades_df, settings)`
   - Exporter writes to `reports/` directory

6. **Feedback**
   - Update status bar with success or error message
   - Log to debug logger

---

## File Naming Convention

**Format**: `{SYMBOL}_{TIMEFRAME}_backtest_{PERIOD}_{YYYYMMDD_HHMM}.{ext}`

**Examples**:
```
XAUUSD_H1_backtest_last30d_20260116_1420.json
XAUUSD_H1_backtest_last30d_20260116_1420.csv
XAUUSD_H1_backtest_last30d_20260116_1420.html
```

**Components**:
- `XAUUSD` - Symbol from MT5 config
- `H1` - Timeframe from MT5 config
- `last30d` - Rolling 30 days (from backtest_engine)
- `20260116` - Date (YYYYMMDD)
- `1420` - Time (HHMM, 24-hour)
- `.json|.csv|.html` - Format

---

## Error Handling

### Scenarios Handled

| Scenario | Behavior | Message |
|----------|----------|---------|
| No backtest run yet | Check `last_result` | "No backtest results to export" |
| Directory missing | Create automatically | (transparent, no message) |
| Write permission denied | Log error | "Export error: Permission denied" |
| Disk full | Log error | "Export error: No space left" |
| Invalid data | Log error | "Export error: Invalid data format" |
| Success | Return filepath | "✓ Exported JSON: filename.json" |

### Exception Handling

```python
try:
    filepath = exporter.export_json(...)
except Exception as e:
    logger.error(f"Error exporting JSON: {e}", exc_info=True)
    ui.set_status(f"Export error: {str(e)}")
```

---

## Technical Details

### Export Calls in _on_backtest_completed()

```python
def _on_backtest_completed(self, result: dict):
    # ... other code ...
    
    # Store result for export
    bt_ui.last_result = result
    
    # Result contains:
    # - summary: Dict with backtest overview
    # - metrics: Dict with detailed statistics
    # - trades_df: DataFrame with individual trades
    # - equity_curve: List of P/L values over time
    # - settings: Strategy configuration snapshot
```

### Export Signatures

```python
# JSON export
filepath = exporter.export_json(
    summary: Dict,
    metrics: Dict,
    trades_df: pd.DataFrame,
    settings: Dict
) -> Optional[Path]

# CSV export
filepath = exporter.export_csv(
    trades_df: pd.DataFrame,
    settings: Dict
) -> Optional[Path]

# HTML export
filepath = exporter.export_html(
    summary: Dict,
    metrics: Dict,
    trades_df: pd.DataFrame,
    equity_curve: List,
    settings: Dict
) -> Optional[Path]
```

### Return Values

- **Success**: Returns `Path` object to exported file
  - Can be used to open in browser or verify existence
  
- **Failure**: Returns `None`
  - Exception logged to debug logger
  - User notified via status bar

---

## Features

### ✅ Implemented
- JSON export with full metrics and trades
- CSV export for spreadsheet analysis
- HTML export for client reporting
- Timestamped filenames
- Status feedback to user
- Error handling and logging
- Browser open support (HTML)
- Automatic directory creation

### 🔄 Data Included

| Format | Summary | Metrics | Trades | Settings | Charts |
|--------|---------|---------|--------|----------|--------|
| JSON | ✓ | ✓ | ✓ | ✓ | - |
| CSV | - | - | ✓ | - | - |
| HTML | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## Testing

### Test Cases

```python
def test_export_json_with_results():
    """Should export JSON when results available."""
    # Setup: Run backtest, get results
    # Execute: Click export JSON
    # Assert: File created, status updated

def test_export_csv_with_results():
    """Should export CSV when results available."""
    # Setup: Run backtest, get results
    # Execute: Click export CSV
    # Assert: File created, trades in CSV

def test_export_html_with_results():
    """Should export HTML when results available."""
    # Setup: Run backtest, get results
    # Execute: Click export HTML
    # Assert: File created, valid HTML

def test_export_no_results():
    """Should show error when no results."""
    # Setup: Don't run backtest
    # Execute: Click export
    # Assert: Status shows "No results"

def test_export_permission_error():
    """Should handle write errors."""
    # Setup: Make reports dir read-only
    # Execute: Click export
    # Assert: Error logged, user notified
```

### Manual Testing

1. **Run backtest** (30-day rolling)
2. **Click "Export JSON"**
   - Verify file created in `reports/` directory
   - Verify status shows "✓ Exported JSON: ..."
   - Check JSON is valid (open in editor)

3. **Click "Export CSV"**
   - Verify file created in `reports/` directory
   - Open in Excel, verify trades display correctly

4. **Click "Export HTML"**
   - Verify file created in `reports/` directory
   - File opens in default browser automatically
   - Check HTML renders correctly

---

## Deployment Checklist

- ✅ Import BacktestReportExporter added to main.py
- ✅ Three export methods implemented
- ✅ Signal connections in set_window()
- ✅ Error handling with try/except
- ✅ Status feedback to user
- ✅ Logging at debug/info levels
- ✅ No syntax errors
- ✅ Backward compatible (existing code unchanged)

---

## File Statistics

### Files Modified
- `src/main.py` (+90 lines)
  - Import BacktestReportExporter
  - Three export method implementations
  - Error handling and logging

### Files Created
- None (uses existing BacktestReportExporter)

### Total Code Added
- ~90 lines in main.py
- All in TradingController class
- Follows existing patterns and style

---

## Next Steps

Task 2.4 is COMPLETE.

### Phase 2 Summary
✅ Task 2.1: Thread-Safe UI Updates (Queue + Signal/Slot)  
✅ Task 2.2: State Persistence (Atomic writes + Backups)  
✅ Task 2.3: Entry Conditions (Documentation + Tests)  
✅ Task 2.4: Export Functions (JSON/CSV/HTML)  

### Next Phase
- **Phase 3**: Performance Optimizations (backtest speed, UI rendering)
- **Phase 4**: Advanced Features (multi-symbol trading, custom indicators)

---

## Documentation Links

- [THREAD_SAFE_UI_IMPLEMENTATION.md](THREAD_SAFE_UI_IMPLEMENTATION.md)
- [STATE_PERSISTENCE_IMPLEMENTATION.md](STATE_PERSISTENCE_IMPLEMENTATION.md)
- [ENTRY_CONDITIONS_COMPLETE.md](ENTRY_CONDITIONS_COMPLETE.md)
- [src/engines/backtest_report_exporter.py](../src/engines/backtest_report_exporter.py)

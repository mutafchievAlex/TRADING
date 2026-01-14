# Project Structure

```
TRADING/
│
├── .github/
│   └── copilot-instructions.md      # GitHub Copilot workspace instructions
│
├── config/
│   └── config.yaml                  # Main configuration file
│
├── data/
│   ├── historical/                  # Historical data for backtesting
│   │   └── .gitkeep
│   └── state.json                   # Auto-generated: Trading state persistence
│
├── logs/                            # Auto-generated: Log files
│   ├── system.log                   # System events and decisions
│   └── trades.log                   # Trade execution log
│
├── scripts/
│   └── backtest.py                  # Backtesting script for offline validation
│
├── src/
│   ├── engines/                     # Core trading engines
│   │   ├── __init__.py
│   │   ├── market_data_service.py   # MT5 data fetching
│   │   ├── indicator_engine.py      # EMA50, EMA200, ATR14 calculations
│   │   ├── pattern_engine.py        # Double Bottom pattern detection
│   │   ├── strategy_engine.py       # Entry/exit condition evaluation
│   │   ├── risk_engine.py           # Position sizing and risk management
│   │   ├── execution_engine.py      # MT5 order execution
│   │   └── state_manager.py         # State persistence and tracking
│   │
│   ├── ui/                          # User interface
│   │   ├── __init__.py
│   │   └── main_window.py           # PySide6 main window and UI components
│   │
│   ├── utils/                       # Utilities
│   │   ├── __init__.py
│   │   ├── config.py                # Configuration management
│   │   └── logger.py                # Logging system
│   │
│   └── main.py                      # Application entry point + controller
│
├── tests/                           # Unit tests
│   ├── __init__.py
│   ├── test_indicator_engine.py
│   ├── test_pattern_engine.py
│   └── test_risk_engine.py
│
├── .gitignore                       # Git ignore rules
├── QUICKSTART.md                    # Quick start guide
├── README.md                        # Main documentation
└── requirements.txt                 # Python dependencies

```

## File Purposes

### Core Engines (`src/engines/`)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `market_data_service.py` | MT5 integration for data | `connect()`, `get_bars()`, `get_account_info()` |
| `indicator_engine.py` | Technical indicators | `calculate_ema()`, `calculate_atr()` |
| `pattern_engine.py` | Pattern detection | `detect_double_bottom()`, `find_pivot_lows()` |
| `strategy_engine.py` | Strategy logic | `evaluate_entry()`, `evaluate_exit()` |
| `risk_engine.py` | Risk management | `calculate_position_size()`, `validate_risk()` |
| `execution_engine.py` | Trade execution | `send_market_order()`, `close_position()` |
| `state_manager.py` | State persistence | `open_position()`, `close_position()` |

### User Interface (`src/ui/`)

| File | Purpose | Key Features |
|------|---------|--------------|
| `main_window.py` | PySide6 GUI | Tabs for market data, position, history, logs, settings |

### Utilities (`src/utils/`)

| File | Purpose | Key Classes |
|------|---------|-------------|
| `config.py` | Configuration management | `Config` class with YAML/JSON support |
| `logger.py` | Logging system | `TradingLogger` with file rotation |

### Main Application

| File | Purpose | Key Functions |
|------|---------|---------------|
| `main.py` | Application controller | `TradingController` class, `main()` entry point |

## Data Flow

```
1. main.py
   ↓
2. TradingController
   ├── Initialize all engines
   ├── Connect to MT5
   └── Start main loop (every 10s)
       ↓
3. Main Loop
   ├── MarketDataService.get_bars() → Fetch OHLC data
   ├── IndicatorEngine.calculate_all_indicators() → EMA, ATR
   ├── PatternEngine.detect_double_bottom() → Pattern detection
   ├── StrategyEngine.evaluate_entry() → Check conditions
   │   ├── If entry signal:
   │   │   ├── RiskEngine.calculate_position_size()
   │   │   └── ExecutionEngine.send_market_order()
   │   └── StateManager.open_position()
   ├── If position open:
   │   ├── StrategyEngine.evaluate_exit()
   │   └── ExecutionEngine.close_position()
   └── UI updates
```

## Configuration Flow

```
config.yaml
    ↓
Config.load_config()
    ↓
TradingController reads settings
    ↓
Engines initialized with parameters
    ↓
Runtime: UI can modify settings
    ↓
Config.save_config()
```

## State Management

```
Position opened
    ↓
StateManager.open_position()
    ↓
state.json saved
    ↓
Position monitored
    ↓
Position closed
    ↓
StateManager.close_position()
    ↓
Trade added to history
    ↓
state.json updated
```

## Logging Strategy

- **system.log**: All events, decisions, errors
- **trades.log**: Entry/exit trades only
- **Rotation**: 10MB max, 5 backups
- **Levels**: DEBUG, INFO, WARNING, ERROR

## Testing Strategy

1. **Unit Tests** (`tests/`): Test individual engines
2. **Backtest** (`scripts/backtest.py`): Test on historical data
3. **Demo Mode**: Test with MT5 demo account
4. **Live Testing**: Small risk on real account

## Development Workflow

1. **Modify engine logic**: Update relevant file in `src/engines/`
2. **Test changes**: Run unit tests with `pytest`
3. **Backtest**: Validate with `scripts/backtest.py`
4. **Demo trade**: Test in demo mode
5. **Review logs**: Check `logs/` for issues
6. **Deploy**: Enable live trading if successful

## Extension Points

To add features:

- **New indicator**: Add to `indicator_engine.py`
- **New pattern**: Add to `pattern_engine.py`
- **New entry condition**: Add to `strategy_engine.py`
- **New UI tab**: Add to `main_window.py`
- **New configuration**: Add to `config.yaml` and `config.py`

# XAUUSD Double Bottom Trading Strategy

A production-ready desktop trading application that replicates TradingView Pine Script strategy logic with MetaTrader 5 integration.

## 🎯 Overview

This application implements a **LONG ONLY** Double Bottom pattern trading strategy for XAUUSD (Gold) on the 1-hour timeframe. It faithfully reproduces Pine Script trading logic while providing automated execution capabilities through MetaTrader 5.

### Key Features

- ✅ **Pattern Detection**: Automated Double Bottom pattern recognition
- ✅ **Risk Management**: Fixed % risk per trade with position sizing
- ✅ **MT5 Integration**: Real-time data and order execution
- ✅ **Desktop UI**: PySide6-based trading dashboard
- ✅ **Demo Mode**: Test strategies safely before live trading
- ✅ **Comprehensive Logging**: All decisions and trades logged
- ✅ **State Persistence**: Trade history and positions saved

## 📋 Requirements

- **Python**: 3.10 or higher
- **MetaTrader 5**: Installed and configured
- **Operating System**: Windows (MT5 Python API requirement)

## 🚀 Installation

### 1. Clone or Download

```bash
cd C:\Users\mutaf\TRADING
```

### 2. Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure MT5 Settings

Edit `config/config.yaml`:

```yaml
mt5:
  login: YOUR_ACCOUNT_NUMBER  # Or null to use current login
  password: YOUR_PASSWORD      # Or null
  server: YOUR_BROKER_SERVER   # Or null
  symbol: "XAUUSD"
  timeframe: "H1"
```

## 🎮 Usage

### Running the Application

```powershell
python src/main.py
```

### First-Time Setup

1. **Connect to MT5**
   - Ensure MetaTrader 5 is running
   - Log in to your demo/live account
   - Click "Start Trading" in the application

2. **Configure Strategy**
   - Go to "Settings" tab
   - Adjust risk %, ATR multiplier, R:R ratio
   - Save settings

3. **Monitor Trading**
   - "Market Data" tab shows current price and indicators
   - "Position" tab displays open trades
   - "History" tab shows past performance
   - "Logs" tab shows all decisions

### Demo vs Live Trading

⚠️ **Always test in demo mode first!**

```yaml
mode:
  demo_mode: true      # Keep true for demo account
  auto_trade: false    # Set true to enable automatic trading
```

## 🏗️ Architecture

### Clean Architecture Design

```
src/
├── engines/                    # Core trading logic
│   ├── market_data_service.py  # MT5 data fetching
│   ├── indicator_engine.py     # EMA, ATR calculations
│   ├── pattern_engine.py       # Double Bottom detection
│   ├── strategy_engine.py      # Entry/exit conditions
│   ├── risk_engine.py          # Position sizing
│   ├── execution_engine.py     # MT5 order execution
│   └── state_manager.py        # State persistence
├── ui/                         # User interface
│   └── main_window.py          # PySide6 GUI
├── utils/                      # Utilities
│   ├── config.py               # Configuration management
│   └── logger.py               # Logging system
└── main.py                     # Application entry point
```

### Trading Strategy Logic

**Entry Conditions** (ALL must be true):
1. ✓ Valid Double Bottom pattern detected
2. ✓ Close breaks above neckline
3. ✓ Close > EMA50 (trend filter)
4. ✓ Breakout candle has momentum (ATR-based)
5. ✓ Cooldown period respected

**Exit Conditions**:
- Stop Loss: ATR-based or swing low
- Take Profit: Risk × R:R ratio

### Risk Management

```python
risk_amount = equity × risk_percent
position_size = risk_amount / abs(entry_price - stop_loss)
```

## 🧪 Testing

### Run Unit Tests

```powershell
pytest tests/ -v
```

### Test Individual Engines

```powershell
# Test indicator engine
python src/engines/indicator_engine.py

# Test pattern engine
python src/engines/pattern_engine.py

# Test strategy engine
python src/engines/strategy_engine.py
```

## 📊 Backtesting (Offline Validation)

To validate against historical data:

1. Export XAUUSD H1 data from TradingView to CSV
2. Place CSV in `data/historical/`
3. Run backtest script:

```powershell
python scripts/backtest.py --data data/historical/XAUUSD_H1.csv
```

## 📝 Configuration Reference

### Strategy Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `risk_percent` | 1.0% | Risk per trade |
| `atr_multiplier_stop` | 2.0 | ATR multiplier for SL |
| `risk_reward_ratio` | 2.0 | R:R for TP |
| `momentum_atr_threshold` | 0.5 | Min momentum filter |
| `cooldown_hours` | 24 | Hours between trades |
| `equality_tolerance` | 2.0% | Double Bottom tolerance |

## 🔐 Security & Safety

### Safety Features

- ✅ Demo mode by default
- ✅ Manual confirmation for auto-trade
- ✅ Maximum drawdown limits
- ✅ Position size constraints
- ✅ Cooldown periods between trades

### Best Practices

1. **Always start in demo mode**
2. **Validate with historical data first**
3. **Use small risk % for live trading (0.5-1%)**
4. **Monitor the first 10-20 trades closely**
5. **Never leave auto-trade unattended initially**

## 📈 Performance Monitoring

### Metrics Tracked

- Total trades
- Win rate %
- Total profit/loss
- Average win/loss
- Profit factor
- Maximum drawdown

### Logs Location

- **System logs**: `logs/system.log`
- **Trade logs**: `logs/trades.log`
- **State file**: `data/state.json`

## 🐛 Troubleshooting

### Common Issues

1. **"MT5 initialization failed"**
   - Ensure MetaTrader 5 is running
   - Check you're logged in to an account
   - Verify Python and MT5 are same architecture (64-bit)

2. **"Symbol XAUUSD not found"**
   - Enable XAUUSD in MT5 Market Watch
   - Verify symbol name with your broker

3. **"Insufficient data"**
   - Wait for more bars to load
   - Requires 250+ bars for EMA200

4. **UI not responding**
   - Check logs for errors
   - Restart application
   - Verify all dependencies installed

## 🔄 Updates & Maintenance

### Updating Configuration

```powershell
# Edit config
notepad config\config.yaml

# Restart application to apply changes
```

### Viewing Logs

```powershell
# System logs
Get-Content logs\system.log -Tail 50

# Trade logs
Get-Content logs\trades.log -Tail 20
```

## 📚 Additional Resources

### Pine Script Reference

The strategy logic is based on TradingView Pine Script specifications. All indicator calculations match TradingView's implementation:

- **EMA**: `ta.ema(source, length)`
- **ATR**: `ta.atr(length)`
- **Pivot Lows**: `ta.pivotlow(source, leftbars, rightbars)`

### MT5 Python API Documentation

- [MetaTrader 5 Python Documentation](https://www.mql5.com/en/docs/python_metatrader5)

## ⚠️ Disclaimer

**This software is for educational purposes only.**

- Trading involves substantial risk of loss
- Past performance does not guarantee future results
- Always test thoroughly in demo mode
- Never risk more than you can afford to lose
- The authors assume no liability for trading losses

## 📄 License

This project is provided as-is for personal use.

## 🤝 Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Review configuration in `config/config.yaml`
3. Ensure all dependencies are installed
4. Verify MT5 connection is active

---

**Version**: 1.0.0  
**Last Updated**: January 2026  
**Trading Mode**: LONG ONLY  
**Instrument**: XAUUSD  
**Timeframe**: 1H

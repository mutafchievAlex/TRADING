# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Windows OS
- Python 3.10+
- MetaTrader 5 installed

### Step 1: Install Dependencies

```powershell
# Navigate to project directory
cd C:\Users\mutaf\TRADING

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure MT5 Connection

Edit `config/config.yaml`:

```yaml
mt5:
  login: null      # Leave null to use current MT5 login
  password: null   # Or specify your credentials
  server: null
```

### Step 3: Run the Application

```powershell
python src/main.py
```

### Step 4: Initial Setup in UI

1. **Verify Connection**: Check that "Connection: Connected" shows green
2. **Review Settings**: Go to Settings tab, adjust risk % if needed
3. **Start in Demo Mode**: Ensure "Demo Mode" checkbox is checked
4. **Enable Auto-Trade**: Check "Auto Trade" only after testing
5. **Click "Start Trading"**: Begin monitoring

## 📊 Testing Before Live Trading

### Option 1: Paper Trading (Recommended)

1. Connect to MT5 **demo account**
2. Set `demo_mode: true` in config
3. Set `auto_trade: false` initially
4. Monitor for 24-48 hours
5. Review logs and decisions

### Option 2: Backtest with Historical Data

```powershell
# Export XAUUSD H1 data from TradingView
# Save as CSV in data/historical/

# Run backtest
python scripts/backtest.py --data data/historical/XAUUSD_H1.csv --equity 10000 --risk 1.0
```

## 🎯 What to Watch

### Market Data Tab
- Current price updates every 10 seconds
- EMA50, EMA200, ATR14 values
- Pattern detection status
- Entry condition checklist (✓/✗)

### Position Tab
- Shows open position details
- Real-time P&L
- Entry, SL, TP levels

### Logs Tab
- All decisions logged with reasoning
- Entry signals
- Exit reasons
- Errors and warnings

## ⚙️ Configuration Recommendations

### Conservative Settings (Start Here)
```yaml
risk:
  risk_percent: 0.5  # Low risk for testing

strategy:
  risk_reward_ratio: 2.5  # Higher R:R
  cooldown_hours: 48      # More selective
```

### Moderate Settings
```yaml
risk:
  risk_percent: 1.0

strategy:
  risk_reward_ratio: 2.0
  cooldown_hours: 24
```

### Aggressive Settings (Advanced Only)
```yaml
risk:
  risk_percent: 2.0

strategy:
  risk_reward_ratio: 1.5
  cooldown_hours: 12
```

## 🔍 Troubleshooting

### Connection Issues
```powershell
# Check MT5 is running
Get-Process | Where-Object {$_.Name -like "*terminal*"}

# Check Python can access MT5
python -c "import MetaTrader5 as mt5; print(mt5.initialize())"
```

### Module Import Errors
```powershell
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### UI Not Showing
```powershell
# Check PySide6 installation
python -c "from PySide6.QtWidgets import QApplication; print('OK')"
```

## 📈 Expected Behavior

### First Hour
- Application connects to MT5
- Fetches 500 bars of XAUUSD H1 data
- Calculates indicators
- Begins pattern scanning
- No trades initially (cooldown + conditions)

### First Pattern Detection
- Logs show "Double Bottom detected"
- Entry conditions evaluated
- If all ✓: Signal generated
- If auto-trade enabled: Trade executed
- Position tracked in UI

### During Trade
- Position tab shows live P&L
- Strategy monitors for SL/TP
- Automatic exit when conditions met
- Trade logged in history

## 🎓 Learning the System

### Day 1-3: Observation Mode
- `auto_trade: false`
- Watch signals
- Review logs
- Understand decision logic

### Day 4-7: Demo Trading
- Switch to demo account
- `auto_trade: true`
- Monitor closely
- Review every trade

### Week 2+: Live Consideration
- Minimum 20 demo trades
- Win rate > 50%
- Comfortable with logic
- Switch to live with 0.5% risk

## 📞 Support Checklist

Before reporting issues:

1. ✓ Check `logs/system.log` for errors
2. ✓ Verify MT5 connection active
3. ✓ Ensure XAUUSD visible in Market Watch
4. ✓ Confirm sufficient historical data (500+ bars)
5. ✓ Review `config/config.yaml` settings
6. ✓ Check Python version: `python --version`
7. ✓ Verify dependencies: `pip list`

## 🎯 Success Metrics

Track these in the History tab:

- **Win Rate**: Target > 45%
- **Profit Factor**: Target > 1.5
- **Average Win/Loss**: Target > 2:1
- **Max Drawdown**: Keep < 10%

## ⚠️ Safety Reminders

1. **Always start in demo mode**
2. **Never risk > 2% per trade**
3. **Monitor first 10 trades closely**
4. **Review logs daily**
5. **Stop trading if 3 consecutive losses**
6. **Maximum 5% daily drawdown limit**

---

Ready to start? Run `python src/main.py` and begin your journey! 🚀

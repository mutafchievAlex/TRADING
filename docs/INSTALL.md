# Installation & First Run Guide

## 📋 Prerequisites

Before installing, ensure you have:

- ✅ **Windows OS** (MT5 Python API requirement)
- ✅ **Python 3.10 or higher** installed
- ✅ **MetaTrader 5** installed and configured
- ✅ **MT5 account** (demo or live)

### Check Python Version

```powershell
python --version
```

Should show: `Python 3.10.x` or higher

---

## 🔧 Installation Steps

### Step 1: Navigate to Project Directory

```powershell
cd C:\Users\mutaf\TRADING
```

### Step 2: Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate it (PowerShell)
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

You should see `(venv)` appear in your terminal prompt.

### Step 3: Install Dependencies

```powershell
# Upgrade pip first
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

This will install:
- MetaTrader5 (MT5 Python API)
- pandas (Data manipulation)
- numpy (Numerical computations)
- PyYAML (Configuration files)
- PySide6 (Desktop UI)
- pytest (Testing framework)

**Installation time**: 2-5 minutes depending on internet speed.

### Step 4: Verify Installation

```powershell
python verify_setup.py
```

This will check:
- ✓ Python version
- ✓ All dependencies installed
- ✓ Project structure complete
- ✓ Configuration valid
- ✓ MT5 connection available

**Expected output**:
```
============================================================
TRADING APPLICATION SETUP VERIFICATION
============================================================
Checking Python version...
  ✓ Python 3.10.x
Checking dependencies...
  ✓ MetaTrader5
  ✓ pandas
  ✓ numpy
  ✓ PyYAML
  ✓ PySide6
... (more checks)
============================================================
✓ ALL CHECKS PASSED
============================================================
```

---

## ⚙️ Configuration

### Step 5: Edit Configuration File

Open `config/config.yaml` in a text editor:

```powershell
notepad config\config.yaml
```

**Important settings to review**:

```yaml
mt5:
  login: null       # Leave null to use current MT5 login
  password: null    # or specify your credentials
  server: null
  symbol: "XAUUSD"  # Trading instrument
  timeframe: "H1"   # 1-hour bars

mode:
  demo_mode: true   # KEEP TRUE for testing!
  auto_trade: false # KEEP FALSE initially

risk:
  risk_percent: 1.0 # Risk per trade (start with 0.5-1%)
```

**⚠️ Safety First**:
- Keep `demo_mode: true` for initial testing
- Keep `auto_trade: false` to observe signals only
- Start with low `risk_percent` (0.5-1%)

Save and close the file.

---

## 🚀 First Run

### Step 6: Ensure MT5 is Running

1. Open MetaTrader 5
2. Log in to your account (demo recommended)
3. Ensure XAUUSD is visible in Market Watch
   - Right-click Market Watch → Symbols → Find "XAUUSD" → Show

### Step 7: Launch the Application

```powershell
python src/main.py
```

**What should happen**:
1. A desktop window opens
2. Shows "Connection: Connected" in green
3. Displays your account balance/equity
4. Market Data tab shows current XAUUSD price
5. Logs tab shows initialization messages

**If connection fails**:
- Verify MT5 is running and logged in
- Check XAUUSD is enabled in Market Watch
- Review logs: `logs/system.log`

---

## 🎮 Using the Application

### Main Window Overview

**Status Panel** (Top Left):
- Connection status (green = connected)
- Trading status (stopped/active)
- Account info (login, equity, balance)

**Control Panel** (Top Right):
- Start/Stop Trading buttons
- Demo Mode checkbox
- Auto Trade checkbox

### Tabs Explained

#### 1️⃣ Market Data Tab
- **Current Price**: Live XAUUSD price
- **Indicators**: EMA50, EMA200, ATR14 values
- **Pattern Detection**: Shows if Double Bottom detected
- **Entry Conditions**: Checklist with ✓/✗ for each condition

#### 2️⃣ Position Tab
- Shows open position details (if any)
- Live P/L calculation
- Entry price, SL, TP levels
- Manual close button

#### 3️⃣ History Tab
- Performance statistics
- Win rate, profit factor
- Trade history table

#### 4️⃣ Logs Tab
- Real-time decision logging
- All system events
- Entry/exit signals
- Errors and warnings

#### 5️⃣ Settings Tab
- Adjust strategy parameters
- Risk %, ATR multiplier, R:R ratio
- Cooldown period
- Save changes

---

## 📊 Testing Workflow

### Phase 1: Observation (Day 1-3)

**Settings**:
```yaml
mode:
  demo_mode: true
  auto_trade: false  # Just watch, don't trade
```

**Goal**: Understand how the system evaluates conditions

**What to do**:
1. Click "Start Trading"
2. Watch the Market Data tab
3. Observe entry conditions checklist
4. Review Logs tab for decisions
5. See if patterns are detected

**Expected**: No trades executed, only signals logged

### Phase 2: Demo Trading (Week 1-2)

**Settings**:
```yaml
mode:
  demo_mode: true
  auto_trade: true  # Enable automatic trading
```

**Goal**: Validate strategy with real demo trades

**What to do**:
1. Enable "Auto Trade" checkbox in UI
2. Click "Start Trading"
3. Wait for entry signals (may take hours/days)
4. Monitor trades in Position tab
5. Review performance in History tab

**Expected**: Trades executed on demo account

### Phase 3: Live Trading (After Validation)

**Prerequisites**:
- Minimum 20 demo trades completed
- Win rate > 45%
- Comfortable with system behavior
- Understand all decisions

**Settings**:
```yaml
mode:
  demo_mode: false  # CAUTION: Live trading!
  auto_trade: true

risk:
  risk_percent: 0.5  # Start with low risk!
```

**What to do**:
1. Switch to MT5 live account
2. Restart application
3. Start with 0.5% risk
4. Monitor very closely
5. Increase risk gradually if successful

---

## 🔍 Monitoring & Maintenance

### Daily Checks

```powershell
# View recent system logs
Get-Content logs\system.log -Tail 50

# View recent trades
Get-Content logs\trades.log -Tail 20
```

### What to Look For

**✅ Good Signs**:
- System connects successfully
- Indicators calculated correctly
- Patterns detected occasionally
- Entry conditions evaluated logically
- Trades executed as expected

**⚠️ Warning Signs**:
- Connection errors
- "Insufficient data" messages
- All entry conditions never met
- Unusual P&L swings

### Performance Metrics

Check in History tab:
- **Win Rate**: Should be 40-60%
- **Profit Factor**: Target > 1.5
- **Average Win/Loss**: Target > 2:1

---

## 🐛 Troubleshooting

### Issue: "MT5 initialization failed"

**Solution**:
1. Ensure MT5 is running
2. Verify you're logged in
3. Check MT5 and Python are same architecture (64-bit)
4. Try closing and reopening MT5

### Issue: "Symbol XAUUSD not found"

**Solution**:
1. Open MT5 Market Watch
2. Right-click → Symbols
3. Search for "XAUUSD"
4. Click "Show"
5. Restart application

### Issue: "Insufficient data"

**Solution**:
1. Wait 5-10 minutes for bars to load
2. Ensure timeframe is H1 in MT5
3. Check internet connection
4. Review `logs/system.log` for details

### Issue: UI not responding

**Solution**:
1. Check logs for errors
2. Verify all dependencies installed: `pip list`
3. Reinstall PySide6: `pip install --upgrade PySide6`
4. Restart application

### Issue: Import errors when running

**Solution**:
```powershell
# Ensure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

---

## 📁 Important Files & Folders

### Configuration
- `config/config.yaml` - Main settings

### Logs (auto-created)
- `logs/system.log` - All events
- `logs/trades.log` - Trade history

### Data (auto-created)
- `data/state.json` - Current state

### Source Code
- `src/main.py` - Application entry
- `src/engines/` - Trading engines
- `src/ui/` - User interface

---

## 🔄 Updating Configuration

### Change Risk Settings

```powershell
notepad config\config.yaml
```

Edit:
```yaml
risk:
  risk_percent: 0.5  # Change this value
```

**Restart application** to apply changes.

### Change Strategy Parameters

In the application:
1. Go to **Settings** tab
2. Adjust values
3. Click **Save Settings**
4. No restart needed

---

## 📚 Next Steps

### Learning Path

1. **Read Documentation**:
   - `README.md` - Complete overview
   - `QUICKSTART.md` - This guide
   - `STRUCTURE.md` - Architecture details
   - `PROJECT_SUMMARY.md` - Full summary

2. **Understand Code**:
   - Start with `src/main.py`
   - Review each engine in `src/engines/`
   - Check UI code in `src/ui/main_window.py`

3. **Run Tests**:
   ```powershell
   pytest tests/ -v
   ```

4. **Backtest**:
   ```powershell
   # Get historical data from TradingView
   python scripts/backtest.py --data data/historical/XAUUSD_H1.csv
   ```

### Customization Ideas

- Add new indicators to `indicator_engine.py`
- Implement new patterns in `pattern_engine.py`
- Modify entry logic in `strategy_engine.py`
- Trade different instruments (edit `config.yaml`)
- Adjust UI layout in `main_window.py`

---

## ⚠️ Final Reminders

### Before Trading Real Money

- [ ] Tested in demo mode for at least 1-2 weeks
- [ ] Minimum 20 trades executed
- [ ] Win rate acceptable (>45%)
- [ ] Understand all entry/exit logic
- [ ] Comfortable with risk per trade
- [ ] Have stop-loss plan if things go wrong
- [ ] Not risking more than you can afford to lose

### Safety Guidelines

1. **Always start in demo mode**
2. **Never risk more than 1-2% per trade**
3. **Set maximum daily/weekly loss limits**
4. **Monitor first trades closely**
5. **Keep logs for review**
6. **Stop trading if 3 consecutive losses**
7. **Review performance regularly**

---

## 🎉 You're Ready!

Your trading system is fully set up and ready to use.

**To start trading**:
```powershell
python src/main.py
```

**Questions?** Check:
- `README.md` for detailed documentation
- `logs/system.log` for error details
- Test files in `tests/` for examples

**Good luck and trade safely! 📈🚀**

---

*Installation Guide Version: 1.0*  
*Last Updated: January 2026*

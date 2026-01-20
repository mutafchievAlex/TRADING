"""
Trading Controller - Main application logic coordinator










































































































































































































































































































































































































































This implementation transforms the trading system from simple SL/TP exits to sophisticated multi-stage profit-taking with professional-grade risk management.- ✅ Logging and monitoring (audit trail)- ✅ Backtesting support (historical validation)- ✅ Backward compatibility (existing positions still work)- ✅ UI visualization (Position tab integration)- ✅ Full state persistence (recovery-safe)- ✅ Dynamic SL management (breakeven + trailing)- ✅ Deterministic state machine (testable, debuggable)The multi-level TP system provides:## Summary5. **Continuation logic**: Re-enter at new SL after TP1 fill4. **Risk multiplier**: Scale TP levels by market volatility3. **Swing-based targets**: Use recent highs/lows for TP calculation2. **ATR-based trailing**: Adjust trailing offset dynamically1. **Partial exits**: Close 50% at TP1, 25% at TP2, 25% at TP3## Future Enhancements```5. Verify state.json is updated at each step4. Move price to TP3, verify position closes3. Move price to TP2, verify SL trails2. Move price to TP1, verify SL moves to entry1. Open position, verify TP levels calculated```python### Live Validation```- State persistence across restarts- Multiple positions in parallel- Entry -> TP1 -> Reversal -> SL (failure path)- Entry -> TP1 -> TP2 -> TP3 (success path)# Check _monitor_positions() in backtest:```python### Integration Tests```- test_exit_evaluation()- test_new_stop_loss_calculation()- test_state_machine_transitions()- test_tp_level_calculation()# test_multi_level_tp_engine.py```python### Unit Tests## Testing- Existing positions without TP state still execute- Falls back to simple SL/TP check if tp_levels not provided- Legacy `evaluate_exit(price, entry, sl, tp)` still worksThe system maintains backward compatibility:## Backward Compatibility- Real-time updates every bar-close- `decision_analyzer_widget.py`: Shows TP state transitions- `main_window.py`: Displays TP levels in Position tab### 4. UI Updates- `recovery_engine.py`: Validates positions after disconnection- `execution_engine.py`: Sends orders to MT5- `state_manager.py`: Stores/updates position data### 3. Position Management- `state_manager.update_position_tp_state()`: Persists state changes- `strategy_engine.evaluate_exit()`: Checks multi-level conditions- `_monitor_positions()` in main.py: Calls evaluate_exit() every bar### 2. Exit Monitoring- `_execute_entry()` in main.py: Calculates TP levels, opens position- `strategy_engine.evaluate_entry()`: Validates entry conditions- `pattern_engine.py`: Detects Double Bottom pattern### 1. Entry Detection## Integration Points```[INFO] Position 12345 exiting: Take Profit TP3[INFO] ✓ TP3 REACHED: 2020.00 >= 2020.00[INFO] Position 12345 TP state: IN_TRADE -> TP1_REACHED, SL updated to 2000.00[INFO] ✓ TP1 REACHED: 2014.00 >= 2014.00  TP3 (2.0:1): 2020.00  TP2 (1.8:1): 2018.00  TP1 (1.4:1): 2014.00  Risk: 10.00  SL: 1990.00  Entry: 2000.00[DEBUG] TP Levels calculated (direction=1):```Comprehensive logging at DEBUG level:## Logging```)    default_rr_short=2.0      # Adjust for SHORT    default_rr_long=2.0,      # Adjust for LONGself.multi_level_tp = MultiLevelTPEngine(```python**Final RR** (in `StrategyEngine.__init__`):```)    trailing_offset=0.5  # Can be adjusted (pips)    ...,new_stop_loss = self.multi_level_tp.calculate_new_stop_loss(```python**Trailing offset** (in `_monitor_positions`):### Adjustable Parameters```DEFAULT_TP2_RR = 1.8DEFAULT_TP1_RR = 1.4# In MultiLevelTPEngine:risk_reward_ratio_short = 2.0   # TP3 target for SHORTrisk_reward_ratio_long = 2.0    # TP3 target for LONG# In StrategyEngine.__init__:```python### Default Settings## Configuration- SL prices align with position state- TP prices consistent with risk calculation- TP state matches position existence### 5. State Validation- Prevents ghost tracking- Closes position in state manager- Detects if position closed in MT5### 4. External Position Closure- Captures additional upside without risk increase- After TP2, SL follows price at fixed offset### 3. Trailing Stops- Reduces stress in trending consolidation- After TP1 reached, SL at entry prevents losses### 2. Breakeven Protection- No "gap" exits that skip SL- SL check before any TP progression### 1. Stop Loss Always Active## Safety Features- Arrow: Next target direction- Highlighted: Active TP level- Red zone: Entry to SL (loss region)- Green zone: Entry to TP3 (profit region)**Visual indicators**:- Profit/Loss cash value- Next Target Price (from `get_next_target()`)- Active TP Level (IN_TRADE, TP1_REACHED, TP2_REACHED)- TP1/TP2/TP3 prices- Current SL (dynamically updated)- Current Price- Entry Price**Position fields displayed**:### Position Tab Integration## UI Display4. No logic replay needed (state is source of truth)3. Monitoring loop continues from current state2. TP states and SL prices are restored1. Application loads positions from state.json### Recovery after Application Restart```}  ]    }      ...      "direction": 1,      "tp3_price": 2020.00,      "tp2_price": 2018.00,      "tp1_price": 2014.00,      "tp_state": "TP1_REACHED",      "current_stop_loss": 2000.00,      "stop_loss": 1990.00,      "entry_price": 2000.00,      "ticket": 12345,    {  "open_positions": [{```jsonTP state is saved to `data/state.json`:## State Persistence- No ML/neural nets: Pure algorithmic logic- Stateful: Position state saved/restored from JSON- Deterministic: Same input = same output- No repainting: Decisions based on bar-close prices**Key principles**:- **Backtesting**: Historical bar close evaluation with state persistence- **Live trading**: Real MT5 positions with dynamic SL updatesThe multi-level TP system is designed to work identically in:## Backtesting Support```Profit: ~0 (excluding fees)Outcome: Position closed at breakeven (SL at entry price)Action: Exit with reason "Stop Loss"Event: Current price (1999.50) <= Current SL (2000.00)State: TP1_REACHEDPrice: 2019.00 → 2013.00 → Below 2000.00 (new SL)```**Price retreats after TP1**### Alternative: Reversal (Failed Continuation)```Reason: Take Profit TP3 (target achieved)Action: Close full positionState: TP2_REACHED → EXITED```**Price reaches 2020.00 (TP3)**```Reason: Follow trend, capture additional profitAction: Trail SL to 2017.50 (price - 0.5)State: TP1_REACHED → TP2_REACHED```**Price reaches 2018.00 (TP2)**```Reason: Protect profit, reduce riskAction: Move SL to 2000.00 (entry = breakeven)State: IN_TRADE → TP1_REACHED```**Price reaches 2014.00 (TP1)**### Trade Progression```Current SL: 1990.00Initial TP state: IN_TRADE- TP3: 2000.00 + (10 × 2.0) = 2020.00  (TP State → EXITED)- TP2: 2000.00 + (10 × 1.8) = 2018.00  (TP State → TP2_REACHED)- TP1: 2000.00 + (10 × 1.4) = 2014.00  (TP State → TP1_REACHED)Calculated levels:Risk:Reward ratio (TP3): 2.0xStop Loss: 1990.00  (Risk: 10 points)Entry price: 2000.00```### Trade Entry## Workflow Example```})    # ... other fields    'direction': 1,    'current_stop_loss': entry_details['stop_loss'],    'tp3_price': tp_levels.get('tp3'),    'tp2_price': tp_levels.get('tp2'),    'tp1_price': tp_levels.get('tp1'),    'tp_state': 'IN_TRADE',    'take_profit': entry_details['take_profit'],    'stop_loss': entry_details['stop_loss'],    'entry_price': actual_entry_price,    'ticket': ticket,self.state_manager.open_position({)    direction=1  # LONG    stop_loss=entry_details['stop_loss'],    entry_price=actual_entry_price,tp_levels = self.strategy_engine.multi_level_tp.calculate_tp_levels(```python3. Initialize TP state as IN_TRADE2. Store TP prices in state1. Calculate TP levels on position openEnhanced to:#### Entry Execution (`_execute_entry()`)```    )        new_stop_loss=new_stop_loss        new_tp_state=new_tp_state,        ticket=ticket,    self.state_manager.update_position_tp_state(if new_tp_state != tp_state:)    direction=direction    tp_levels=tp_levels,    tp_state=tp_state,    take_profit=position_data['take_profit'],    stop_loss=position_data.get('current_stop_loss', position_data['stop_loss']),    entry_price=position_data['entry_price'],    current_price=current_bar['close'],should_exit, reason, new_tp_state, new_stop_loss = self.strategy_engine.evaluate_exit(}    'tp3': position_data.get('tp3_price'),    'tp2': position_data.get('tp2_price'),    'tp1': position_data.get('tp1_price'),tp_levels = {# In _monitor_positions():```python4. Move stop-loss on TP1/TP2 triggers3. Update TP state transitions2. Check multi-level TP conditions1. Calculate TP levels from entry/SLEnhanced to:#### Position Monitoring Loop (`_monitor_positions()`)### 4. Trading Controller Updates (`src/main.py`)- `get_position_by_ticket(ticket)` - Retrieve position by ID- `update_position_tp_state(ticket, new_tp_state, new_stop_loss)` - Update TP state**New methods**:```}    'tp3_cash': float,            # Reward target for TP3 (info field)    'tp2_cash': float,            # Reward target for TP2 (info field)    'tp1_cash': float,            # Reward target for TP1 (info field)    'direction': int,             # +1 for LONG, -1 for SHORT    'current_stop_loss': float,   # Dynamic SL (updates on TP transitions)    'tp3_price': float,           # Calculated TP3 level    'tp2_price': float,           # Calculated TP2 level    'tp1_price': float,           # Calculated TP1 level    'tp_state': str,              # IN_TRADE, TP1_REACHED, TP2_REACHED, EXITED    # Multi-level TP fields        'volume': float,    'take_profit': float,    'stop_loss': float,    'entry_price': float,    'ticket': int,{```python**New fields in position dictionary**:### 3. State Manager Enhancement (`src/engines/state_manager.py`)Returns: `(should_exit, reason, new_tp_state, new_stop_loss)````) -> Tuple[bool, str, Optional[str], Optional[float]]    direction: int = 1    tp_levels: Optional[Dict[str, float]] = None,    tp_state: Optional[str] = None,    take_profit: float,    stop_loss: float,    entry_price: float,    current_price: float,evaluate_exit(```python#### New signature:- **Multi-level mode**: Full state machine with dynamic SL- **Legacy mode**: Simple SL/TP checks (backward compatible)Now supports both:**Enhanced method**: `evaluate_exit()`### 2. Strategy Engine Integration (`src/engines/strategy_engine.py`)```get_next_target(tp_state, tp_levels) -> Optional[float]    -> Optional[float]calculate_new_stop_loss(current_price, entry_price, tp_state, direction, trailing_offset)    -> (should_exit, reason, new_tp_state)evaluate_exit(current_price, entry_price, stop_loss, tp_state, tp_levels, direction) calculate_tp_levels(entry_price, stop_loss, direction) -> Dict[tp1, tp2, tp3, risk]```python#### Key Methods- Closes all remaining units- Complete position exit- Final profit target**TP3 (Full Target)**: Configurable Risk:Reward (default 2.0x for LONG)- Continues trend capture- Triggers trailing stop-loss (0.5 pip offset from current price)- Second target for profit accumulation**TP2 (Profit-Taking Level)**: 1.8x Risk:Reward- Partial position preservation- Triggers stop-loss movement to breakeven- First target to establish position validity**TP1 (Protection Level)**: 1.4x Risk:Reward#### TP Level Calculations```IDLE -> IN_TRADE -> TP1_REACHED -> TP2_REACHED -> EXITED```#### State Machine (TPState)**Core class**: `MultiLevelTPEngine`### 1. Multi-Level TP Engine (`src/engines/multi_level_tp_engine.py`)## ArchitectureThe multi-level trailing take-profit system implements a sophisticated exit strategy with dynamic stop-loss management and state machine control. The system divides target objectives into three progressive levels with protection and profit-taking mechanics.## Overview
This module coordinates all components of the trading system:
- Manages lifecycle of engines
- Orchestrates data flow between components
- Handles UI updates
- Implements the main trading loop
"""

import argparse
import os
import signal
import sys
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.market_data_service import MarketDataService
from engines.indicator_engine import IndicatorEngine
from engines.pattern_engine import PatternEngine
from engines.strategy_engine import StrategyEngine
from engines.decision_engine import DecisionEngine, DecisionResult
from engines.risk_engine import RiskEngine
from engines.execution_engine import ExecutionEngine
from engines.state_manager import StateManager
from engines.connection_manager import MT5ConnectionManager
from engines.recovery_engine import RecoveryEngine
from engines.backtest_engine import BacktestEngine
from engines.backtest_report_exporter import BacktestReportExporter
from engines.market_regime_engine import MarketRegimeEngine
from config import load_app_config
from utils.config import load_config as load_legacy_config, Config
from utils.logger import setup_logging
from utils.runtime_mode_manager import RuntimeModeManager, get_runtime_manager
from utils.ui_update_queue import UIUpdateQueue, UIEventType
from utils.health_monitor import HealthMonitor, HealthStatus
from utils.performance_monitor import PerformanceMonitor, OperationType
from utils.alert_manager import AlertManager, AlertType, AlertSeverity
from ui.main_window import MainWindow
from ui.backtest_window import BacktestWorker


class TradingController(QObject):
    """
    Main controller for the trading application.
    
    Coordinates all engines and manages the trading loop.
    """
    
    # Signals for UI updates
    update_ui = Signal(dict)
    
    def __init__(self):
        super().__init__()
        
        # Load configuration
        config_path = os.getenv("TRADING_CONFIG", "config/config.yaml")
        self.app_config = load_app_config(config_path)
        self.config = load_legacy_config(config_path)
        
        # Set up logging
        log_config = self.config.get('logging', {})
        self.trading_logger = setup_logging(
            log_dir=log_config.get('log_dir', 'logs'),
            log_level=log_config.get('log_level', 'INFO')
        )
        self.logger = self.trading_logger.get_main_logger()
        
        self.logger.info("=" * 60)
        self.logger.info("XAUUSD Double Bottom Trading System Starting")
        self.logger.info("=" * 60)
        
        # Initialize Runtime Mode Manager
        self.runtime_manager = get_runtime_manager(Path(config_path))
        
        # Initialize engines
        self._initialize_engines()

        # Backtest components
        backtest_cfg = self.config.get('backtest', {})
        mt5_cfg = self.app_config.mt5
        self.backtest_engine = BacktestEngine(
            symbol=mt5_cfg.symbol,
            timeframe=mt5_cfg.timeframe,
            rolling_days=backtest_cfg.get('rolling_days', 30),
            warmup_bars=backtest_cfg.get('warmup_bars', 300),
            commission_percent=backtest_cfg.get('commission_percent', 0.02),
            spread_points=backtest_cfg.get('spread_points', 1.0),
            slippage_points=backtest_cfg.get('slippage_points', 0.5),
            config=self.config
        )
        self.backtest_worker = None
        
        # UI reference
        self.window: Optional[MainWindow] = None
        
        # State flags
        self.is_running = False
        self.is_connected = False
        self.auto_trade_enabled = False  # User's auto trade checkbox state
        self.app_start_time = datetime.now()
        self.qc_failure_count = 0
        self.qc_next_retry_at = 0.0
        
        # Timer for main loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.main_loop)
        self.refresh_interval = self.config.get('ui.refresh_interval_seconds', 10) * 1000
        
        # Connection Manager with heartbeat
        self.connection_manager = MT5ConnectionManager(
            heartbeat_interval_seconds=15,
            max_heartbeat_failures=3
        )
        self.connection_manager.on_status_change = self._on_connection_status_change
        self.connection_manager.on_reconnect_status = self._on_reconnect_status
        
        # Timer for heartbeat checks
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self._perform_heartbeat)
        self.heartbeat_interval = 15 * 1000  # 15 seconds
        
        # UI Update Queue (thread-safe UI updates)
        self.ui_queue = UIUpdateQueue(max_queue_size=1000, process_interval_ms=100)
        self.ui_queue.events_available.connect(self._process_ui_events)
        self.logger.info("Thread-safe UI update queue initialized")
        
        # Health Monitor (system diagnostics)
        state_file_path = Path(__file__).parent.parent / "data" / "state.json"
        self.health_monitor = HealthMonitor(
            state_file=state_file_path,
            memory_threshold_mb=500.0,
            disk_threshold_gb=1.0,
            queue_depth_threshold=100
        )
        
        # Timer for health checks (every 30 seconds)
        self.health_check_timer = QTimer()
        self.health_check_timer.timeout.connect(self._perform_health_check)
        self.health_check_interval = 30 * 1000  # 30 seconds
        self.logger.info("Health monitor initialized")
        
        # Performance Monitor (execution time tracking)
        self.performance_monitor = PerformanceMonitor(max_samples_per_operation=1000)
        self.logger.info("Performance monitor initialized")
        
        # Alert Manager (notifications)
        self.alert_manager = AlertManager(max_history=500, min_alert_interval_seconds=5.0)
        self.alert_manager.add_handler(self._handle_alert)
        self.logger.info("Alert manager initialized")
        
        # Send startup alert
        self.alert_manager.alert_system_startup()
    
    def _initialize_engines(self):
        """Initialize all trading engines."""
        try:
            app_config = self.app_config
            # Market data service
            mt5_config = app_config.mt5
            self.market_data = MarketDataService(
                config=app_config,
                symbol=mt5_config.symbol,
                timeframe=mt5_config.timeframe,
            )
            
            # Indicator engine
            self.indicator_engine = IndicatorEngine()
            
            # Pattern engine
            strategy_config = app_config.strategy
            self.pattern_engine = PatternEngine(
                lookback_left=strategy_config.pivot_lookback_left,
                lookback_right=strategy_config.pivot_lookback_right,
                equality_tolerance=strategy_config.equality_tolerance,
                min_bars_between=strategy_config.min_bars_between,
            )
            
            # Strategy engine
            self.strategy_engine = StrategyEngine(
                atr_multiplier_stop=strategy_config.atr_multiplier_stop,
                risk_reward_ratio_long=strategy_config.risk_reward_ratio_long,
                risk_reward_ratio_short=strategy_config.risk_reward_ratio_short,
                momentum_atr_threshold=strategy_config.momentum_atr_threshold,
                enable_momentum_filter=strategy_config.enable_momentum_filter,
                cooldown_hours=strategy_config.cooldown_hours,
            )
            
            # Risk engine
            risk_config = app_config.risk
            self.risk_engine = RiskEngine(
                config=app_config,
                risk_percent=risk_config.risk_percent,
                commission_per_lot=risk_config.commission_per_lot,
            )
            
            # Execution engine
            self.execution_engine = ExecutionEngine(
                config=app_config,
                symbol=mt5_config.symbol,
                magic_number=mt5_config.magic_number,
            )
            
            # State manager (with atomic writes for thread-safe persistence)
            state_file = self.config.get('data.state_file', 'data/state.json')
            backup_dir = self.config.get('data.backup_dir', 'data/backups')
            self.state_manager = StateManager(
                state_file=state_file,
                backup_dir=backup_dir,
                use_atomic_writes=True  # Enable thread-safe atomic writes
            )

            # Sync persisted cooldown so restarts do not reset it
            if self.state_manager.last_trade_time:
                self.strategy_engine.last_trade_time = self.state_manager.last_trade_time
            
            # Recovery engine
            recovery_bars = self.config.get('recovery.recovery_bars', 50)
            self.recovery_engine = RecoveryEngine(recovery_bars=recovery_bars)

            # Market Regime engine (context only)
            self.market_regime_engine = MarketRegimeEngine()
            
            self.logger.info("All engines initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing engines: {e}")
            raise
    
    def connect_mt5(self) -> bool:
        """Connect to MetaTrader 5."""
        try:
            mt5_config = self.app_config.mt5
            
            self.logger.info(f"Attempting MT5 connection with config:")
            self.logger.info(f"  Terminal path: {mt5_config.terminal_path}")
            self.logger.info(f"  Login: {mt5_config.login}")
            self.logger.info(f"  Server: {mt5_config.server}")
            self.logger.info(f"  Symbol: {mt5_config.symbol}")
            
            connected = self.market_data.connect(
                login=mt5_config.login,
                password=mt5_config.password,
                server=mt5_config.server,
                terminal_path=mt5_config.terminal_path,
            )
            
            if connected:
                self.is_connected = True
                self.logger.info("Connected to MT5 successfully")
                
                # Update connection manager
                self.connection_manager.set_connection_status(True)
                
                # Detect account type and validate mode/account combination
                account_info = self.market_data.get_account_info()
                if account_info:
                    # Detect account type
                    account_type = self.runtime_manager.detect_account_type(account_info)
                    
                    # Validate mode/account combination and get policy
                    is_valid, policy, msg = self.runtime_manager.validate_and_get_policy()
                    
                    if not is_valid:
                        # Invalid combination - log error and potentially block
                        self.logger.error(msg)
                        if not policy.auto_trading:
                            self.logger.error("AUTO-TRADING BLOCKED - Invalid mode/account combination")
                    else:
                        self.logger.info(msg)
                        
                        # Check if confirmation required
                        if policy.confirmation_required:
                            if not self.runtime_manager.request_confirmation():
                                self.logger.error("AUTO-TRADING BLOCKED - Confirmation not given")
                    
                    # Legacy warning (for backwards compatibility)
                    server = account_info.get('server', '').lower()
                    if 'demo' not in server:
                        self.logger.error("LIVE TRADING MODE - REAL MONEY AT RISK")
                
                # Update UI if available (thread-safe)
                if self.window:
                    self.ui_queue.post_event(UIEventType.UPDATE_CONNECTION_STATUS, {'connected': True, 'account_info': account_info})
                    self.ui_queue.post_event(UIEventType.UPDATE_RUNTIME_MODE_DISPLAY, {'runtime_manager': self.runtime_manager})
                    
                    # Update runtime context
                    # Auto trading requires BOTH: checkbox enabled AND runtime policy allows it
                    can_auto_trade_by_policy, policy_reason = self.runtime_manager.can_auto_trade()
                    auto_trading_active = self.auto_trade_enabled and can_auto_trade_by_policy
                    
                    runtime_context = {
                        'runtime_mode': self.runtime_manager.runtime_mode.value,
                        'auto_trading_enabled': auto_trading_active,
                        'account_type': self.runtime_manager.account_type.value if self.runtime_manager.account_type else 'UNKNOWN',
                        'mt5_connection_status': 'CONNECTED',
                        'last_heartbeat': datetime.now().strftime('%H:%M:%S')
                    }
                    self.ui_queue.post_event(UIEventType.UPDATE_RUNTIME_CONTEXT, {'context': runtime_context})
                
                # Perform recovery if there are open positions or after restart
                self._perform_recovery()
                
                return True
            else:
                self.logger.error("Failed to connect to MT5")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to MT5: {e}", exc_info=True)
            return False
    
    def disconnect_mt5(self):
        """Disconnect from MetaTrader 5."""
        try:
            self.market_data.disconnect()
            self.is_connected = False
            self.logger.info("Disconnected from MT5")
            
            if self.window:
                self.ui_queue.post_event(UIEventType.UPDATE_CONNECTION_STATUS, {'connected': False, 'account_info': None})
                
        except Exception as e:
            self.logger.error(f"Error disconnecting from MT5: {e}")
    
    def start_trading(self):
        """Start the trading loop."""
        if not self.is_connected:
            self.logger.error("Cannot start trading: Not connected to MT5")
            if self.window:
                self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': "ERROR: Not connected to MT5"})
                # Reset UI state to stopped
                self.window.is_running = False
                self.window.btn_toggle.setText("Start Trading")
                self.window.btn_toggle.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 10px;")
                self.window.lbl_trading.setText("Trading: Stopped")
                self.window.lbl_trading.setStyleSheet("color: red; font-weight: bold;")
            return
        
        self.is_running = True
        self.logger.info("Trading started")
        self.timer.start(self.refresh_interval)
        self.heartbeat_timer.start(self.heartbeat_interval)  # Start heartbeat
        self.health_check_timer.start(self.health_check_interval)  # Start health checks
        
        if self.window:
            self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': "Trading started"})
    
    def stop_trading(self, stop_heartbeat: bool = True):
        """Stop the trading loop."""
        self.is_running = False
        self.timer.stop()
        if stop_heartbeat:
            self.heartbeat_timer.stop()  # Stop heartbeat
        self.health_check_timer.stop()  # Stop health checks
        self.logger.info("Trading stopped")
        
        if self.window:
            self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': "Trading stopped"})
            # Update UI to reflect stopped state
            self.window.is_running = False
            self.window.btn_toggle.setText("Start Trading")
            self.window.btn_toggle.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 10px;")
            self.window.lbl_trading.setText("Trading: Stopped")
            self.window.lbl_trading.setStyleSheet("color: red; font-weight: bold;")
    
    @Slot()
    def _perform_heartbeat(self):
        """Perform periodic heartbeat check."""
        try:
            # Check connection health
            is_healthy = self.connection_manager.check_connection()
            
            if not is_healthy and self.is_running:
                self.logger.warning("Connection unhealthy; pausing trading and requesting reconnect...")
                self.stop_trading(stop_heartbeat=False)
                mt5_config = self.app_config.mt5
                started = self.connection_manager.request_reconnect_async(
                    login=mt5_config.login,
                    password=mt5_config.password,
                    server=mt5_config.server,
                    terminal_path=mt5_config.terminal_path,
                )
                if not started:
                    self.logger.warning("Reconnect request was not started (already in progress)")
            
            # Update UI with connection status (thread-safe)
            if self.window:
                status = self.connection_manager.get_status_string()
                self.ui_queue.post_event(UIEventType.UPDATE_CONNECTION_STATUS, {
                    'connected': self.connection_manager.is_connected,
                    'account_info': self.market_data.get_account_info()
                })
        
        except Exception as e:
            self.logger.error(f"Heartbeat error: {e}", exc_info=True)
    
    def _perform_health_check(self):
        """Perform periodic system health check."""
        try:
            # Get queue depths
            ui_queue_depth = self.ui_queue.get_queue_size()
            state_queue_depth = 0
            if hasattr(self.state_manager, 'atomic_writer') and self.state_manager.atomic_writer:
                state_queue_depth = self.state_manager.atomic_writer.get_queue_depth()
            
            # Perform health checks
            health_checks = self.health_monitor.check_all(
                mt5_connected=self.is_connected,
                ui_queue_depth=ui_queue_depth,
                state_queue_depth=state_queue_depth
            )
            
            # Get overall status
            overall_status = self.health_monitor.get_overall_status(health_checks)
            summary = self.health_monitor.get_summary(health_checks)
            
            # Log warnings and critical issues, send alerts
            for check in health_checks.values():
                if check.status == HealthStatus.CRITICAL:
                    self.logger.error(f"HEALTH CHECK CRITICAL: {check.message}")
                    self.alert_manager.alert_health_critical(check.message)
                elif check.status == HealthStatus.WARNING:
                    self.logger.warning(f"HEALTH CHECK WARNING: {check.message}")
                    self.alert_manager.alert_health_warning(check.message)
            
            # Check for performance issues (operations > 1000ms)
            slowest = self.performance_monitor.get_slowest_operations(top_n=1)
            if slowest and slowest[0]['avg_ms'] > 1000:
                self.alert_manager.alert_performance_issue(
                    slowest[0]['operation'],
                    slowest[0]['avg_ms']
                )
            
            # Update UI with health status
            if self.window:
                self.ui_queue.post_event(UIEventType.UPDATE_STATUS, {
                    'message': summary
                })
            
            # Log overall health summary
            self.logger.debug(f"Health check: {summary}")
            
            # Log performance metrics periodically (every 5 health checks = 2.5 min)
            if self.health_monitor.check_history and len(self.health_monitor.check_history) % 5 == 0:
                perf_summary = self.performance_monitor.get_summary_string()
                self.logger.info(f"Performance: {perf_summary}")
        
        except Exception as e:
            self.logger.error(f"Health check error: {e}", exc_info=True)
    
    def _handle_alert(self, alert):
        """Handle alerts by forwarding to UI and logging."""
        try:
            # Log the alert
            log_message = str(alert)
            if alert.severity == AlertSeverity.CRITICAL:
                self.logger.error(f"ALERT: {log_message}")
            elif alert.severity == AlertSeverity.WARNING:
                self.logger.warning(f"ALERT: {log_message}")
            else:
                self.logger.info(f"ALERT: {log_message}")
            
            # Forward to UI
            if self.window:
                self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': log_message})
        except Exception as e:
            self.logger.error(f"Error handling alert: {e}", exc_info=True)
    
    def _on_connection_status_change(self, is_connected: bool):
        """
        Handle connection status changes from Connection Manager.
        
        When connection is lost during trading:
        1. Stop main loop to prevent orphaned positions
        2. Log critical alert
        3. Attempt automatic recovery
        4. Notify user with action items
        """
        was_connected = self.is_connected
        self.is_connected = is_connected
        
        if not is_connected and self.is_running:
            # Send critical alert
            self.alert_manager.alert_connection_lost()
            
            self.logger.error("🔴 CRITICAL: Connection lost during trading!")
            self.logger.error("=" * 60)
            self.logger.error("ACTION: Stopping trading loop to protect open positions")
            self.logger.error("ACTION: Attempting automatic reconnection...")
            self.logger.error("=" * 60)
            
            # Stop main loop - critical to prevent trading without connection
            self.stop_trading()
            
            # Log all open positions before attempting recovery
            all_positions = self.state_manager.get_all_positions()
            if all_positions:
                self.logger.error(f"Open positions at connection loss: {len(all_positions)}")
                for pos in all_positions:
                    self.logger.error(
                        f"  Ticket {pos['ticket']}: Entry={pos['entry_price']:.5f}, "
                        f"SL={pos['stop_loss']:.5f}, TP={pos['take_profit']:.5f}"
                    )
            else:
                self.logger.error("No open positions - connection loss has minimal impact")
            
            # Attempt automatic reconnection (non-blocking)
            self._attempt_auto_recovery()
            
            if self.window:
                self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message':
                    "🔴 MT5 CONNECTION LOST\n"
                    "• Trading halted to protect open positions\n"
                    "• Attempting automatic reconnection...\n"
                    "• Check logs for position details"
                })
        
        elif is_connected and not self.is_running:
            self.logger.info("✅ Connection restored - ready to resume trading")
            if not was_connected:
                self._resync_market_data()
            if self.window:
                self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message':
                    "✅ MT5 CONNECTION RESTORED\n"
                    "• Click 'Start Trading' to resume\n"
                    "• All open positions intact on broker"
                })
        
        # Update UI (thread-safe)
        if self.window:
            self.ui_queue.post_event(UIEventType.UPDATE_CONNECTION_STATUS, {
                'connected': is_connected,
                'account_info': self.market_data.get_account_info() if is_connected else None
            })

    def _on_reconnect_status(self, message: str) -> None:
        """Handle reconnect status updates for UI/logging."""
        self.logger.info(f"Reconnect status: {message}")
        lowered = message.lower()
        if "successful" in lowered or "restored" in lowered:
            self._resync_market_data()

        if self.window:
            self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': message})

            status = "RECONNECTING"
            if "successful" in lowered or "restored" in lowered:
                status = "CONNECTED"
            elif "failed" in lowered or "cancel" in lowered or "timed out" in lowered:
                status = "DISCONNECTED"

            can_auto_trade_by_policy, _policy_reason = self.runtime_manager.can_auto_trade()
            auto_trading_active = self.auto_trade_enabled and can_auto_trade_by_policy
            runtime_context = {
                'runtime_mode': self.runtime_manager.runtime_mode.value,
                'auto_trading_enabled': auto_trading_active,
                'account_type': self.runtime_manager.account_type.value if self.runtime_manager.account_type else 'UNKNOWN',
                'mt5_connection_status': status,
                'last_heartbeat': datetime.now().strftime('%H:%M:%S')
            }
            self.ui_queue.post_event(UIEventType.UPDATE_RUNTIME_CONTEXT, {'context': runtime_context})

    def _resync_market_data(self) -> None:
        """Refetch bar history after reconnection."""
        try:
            bars_to_fetch = self.config.get('data.bars_to_fetch', 500)
            df = self.market_data.get_bars(count=bars_to_fetch)
            if df is None or df.empty:
                self.logger.warning("Market data resync failed (no bars returned)")
                return
            self.logger.info(f"Market data resynced ({len(df)} bars)")
        except Exception as e:
            self.logger.error(f"Market data resync error: {e}", exc_info=True)
    
    def _attempt_auto_recovery(self):
        """
        Attempt automatic recovery of MT5 connection.
        
        Non-blocking attempt to restore connection after loss.
        Does NOT restart trading automatically - requires user confirmation.
        """
        try:
            self.logger.info("Starting connection recovery attempt...")
            mt5_config = self.app_config.mt5
            
            # Try up to 3 times with delays
            for attempt in range(1, 4):
                self.logger.info(f"Recovery attempt {attempt}/3...")
                time.sleep(3 * attempt)  # Exponential backoff
                
                success = self.connection_manager.reconnect(
                    login=mt5_config.login,
                    password=mt5_config.password,
                    server=mt5_config.server,
                    terminal_path=mt5_config.terminal_path,
                )
                
                if success:
                    self.logger.info("✅ Connection recovery successful!")
                    self.is_connected = True
                    return
                else:
                    self.logger.warning(f"Recovery attempt {attempt} failed, retrying...")
            
            self.logger.error(
                "❌ Connection recovery failed after 3 attempts.\n"
                "ACTION: Check MT5 terminal status and restart if needed."
            )
            
        except Exception as e:
            self.logger.error(f"Connection recovery error: {e}", exc_info=True)
    
    @Slot()
    def _process_ui_events(self):
        """
        Process pending UI update events from queue (main thread only).
        
        This method is called on the main UI thread when events are available.
        It's safe to update UI from here.
        """
        if not self.window:
            return
        
        try:
            # Get all pending events
            events = self.ui_queue.get_pending_events(max_events=50)
            
            if not events:
                return
            
            # Process each event
            for event in events:
                event_type = event['type']
                data = event['data']
                
                try:
                    # Dispatch to appropriate UI update method
                    if event_type == UIEventType.UPDATE_MARKET_DATA:
                        self.window.update_market_data(**data)
                    
                    elif event_type == UIEventType.UPDATE_PATTERN_STATUS:
                        self.window.update_pattern_status(**data)
                    
                    elif event_type == UIEventType.UPDATE_ENTRY_CONDITIONS:
                        self.window.update_entry_conditions(**data)
                    
                    elif event_type == UIEventType.UPDATE_POSITION_DISPLAY:
                        self.window.update_position_display(**data)
                    
                    elif event_type == UIEventType.UPDATE_TRADE_HISTORY:
                        self.window.update_trade_history()
                    
                    elif event_type == UIEventType.UPDATE_MARKET_REGIME:
                        self.window.update_market_regime(**data)
                    
                    elif event_type == UIEventType.UPDATE_CONNECTION_STATUS:
                        self.window.update_connection_status(**data)
                    
                    elif event_type == UIEventType.UPDATE_STATISTICS:
                        self.window.update_statistics(**data)
                    
                    elif event_type == UIEventType.UPDATE_SESSIONS:
                        self.window.update_sessions(**data)
                    
                    elif event_type == UIEventType.UPDATE_RUNTIME_MODE_DISPLAY:
                        self.window.update_runtime_mode_display(**data)
                    
                    elif event_type == UIEventType.UPDATE_RUNTIME_CONTEXT:
                        self.window.update_runtime_context(data.get('context'))
                    
                    elif event_type == UIEventType.LOG_MESSAGE:
                        self.window.log_message(**data)
                    
                    elif event_type == UIEventType.BACKTEST_PROGRESS:
                        if hasattr(self.window, 'backtest_window'):
                            self.window.backtest_window.update_progress(**data)
                    
                    elif event_type == UIEventType.BACKTEST_COMPLETED:
                        self._on_backtest_completed(data)
                    
                    elif event_type == UIEventType.BACKTEST_ERROR:
                        self._on_backtest_error(data.get('message', 'Unknown error'))
                    
                    else:
                        self.logger.warning(f"Unknown UI event type: {event_type}")
                
                except Exception as e:
                    self.logger.error(f"Error processing UI event {event_type}: {e}", exc_info=True)
        
        except Exception as e:
            self.logger.error(f"Error in _process_ui_events: {e}", exc_info=True)
    
    @Slot()
    def main_loop(self):
        """
        Main trading loop - executes periodically.
        
        Steps:
        1. Fetch latest market data
        2. Calculate indicators
        3. Detect patterns
        4. Evaluate strategy conditions
        5. Execute trades if conditions met
        6. Monitor open positions
        7. Update UI
        """
        try:
            if not self.is_running or not self.is_connected:
                return

            now = time.time()
            if self.qc_next_retry_at and now < self.qc_next_retry_at:
                self.logger.debug(
                    "Skipping loop due to QC backoff (retry at %.1f, now %.1f)",
                    self.qc_next_retry_at,
                    now,
                )
                return
            
            # Start main loop timer for performance monitoring
            loop_timer = f"main_loop_{int(time.time() * 1000) % 100000}"
            self.performance_monitor.start_timer(loop_timer)
            
            self.logger.debug("Main loop iteration")
            
            # 1. Fetch market data
            data_timer = f"market_data_fetch_{int(time.time() * 1000) % 100000}"
            self.performance_monitor.start_timer(data_timer)
            df = self.market_data.get_bars_with_qc(count=self.config.get('data.bars_to_fetch', 500))
            self.performance_monitor.end_timer(data_timer, OperationType.MARKET_DATA_FETCH)
            
            if df is None:
                self._handle_qc_failure(self.market_data.last_qc_failure_reason)
                return
            if len(df) < 220:
                self.logger.warning(f"Insufficient market data: {len(df)} bars (need 220+)")
                return

            if self.qc_failure_count:
                self.logger.info("QC recovered after %d failures", self.qc_failure_count)
            self.qc_failure_count = 0
            self.qc_next_retry_at = 0.0
            
            # 2. Calculate indicators
            df = self.indicator_engine.calculate_all_indicators(df)
            
            # Get current bar (latest completed bar)
            current_bar = df.iloc[-2]
            current_indicators = self.indicator_engine.get_current_indicators(df)
            
            # 3. Detect patterns
            pattern = self.pattern_engine.detect_double_bottom(df)
            
            # 4. Check positions - support pyramiding
            pyramiding = self.config.get('strategy.pyramiding', 1)
            can_open_new = self.state_manager.can_open_new_position(max_positions=pyramiding)
            has_positions = self.state_manager.has_open_position()
            
            if has_positions:
                # Monitor existing positions
                self._monitor_positions(current_bar)
            
            if can_open_new:
                # Look for entry opportunities (can still enter if under pyramiding limit)
                self._check_entry(df, pattern, current_bar)
            
            # 5. Update UI
            self._update_ui(current_bar, current_indicators, pattern)
            
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exc_info=True)

    def _handle_qc_failure(self, reason: Optional[str]) -> None:
        """Apply backoff behavior when QC fails."""
        self.qc_failure_count += 1
        capped_exp = min(self.qc_failure_count, 5)
        backoff_seconds = min(60.0, float(2 ** capped_exp))
        self.qc_next_retry_at = time.time() + backoff_seconds
        reason_text = reason or "QC failure during market data fetch"
        self.logger.warning(
            "QC failure #%d: %s. Backing off for %.1f seconds.",
            self.qc_failure_count,
            reason_text,
            backoff_seconds,
        )
        if self.window:
            self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {
                'message': f"QC failure: {reason_text}. Backoff {backoff_seconds:.1f}s"
            })
    
    def _check_entry(self, df, pattern, current_bar):
        """Check for entry signal and execute trade if conditions met."""
        try:
            # Evaluate entry conditions with performance timing
            entry_timer = f"entry_eval_{int(time.time() * 1000) % 100000}"
            self.performance_monitor.start_timer(entry_timer)
            
            should_enter, entry_details = self.strategy_engine.evaluate_entry(
                df, pattern, current_bar_index=-2
            )
            
            self.performance_monitor.end_timer(entry_timer, OperationType.ENTRY_EVALUATION)
            
            # Update UI with entry conditions (thread-safe)
            if self.window:
                self.ui_queue.post_event(UIEventType.UPDATE_ENTRY_CONDITIONS, {'conditions': entry_details})
                self.ui_queue.post_event(UIEventType.UPDATE_PATTERN_STATUS, {'pattern': pattern})
            
            # Log decision
            if not should_enter:
                self.logger.debug(f"Entry rejected: {entry_details.get('reason', 'Unknown')}")
                return
            
            # Entry signal detected
            self.logger.info("ENTRY SIGNAL DETECTED")
            self.trading_logger.log_trade({
                'type': 'SIGNAL',
                'message': 'Entry conditions met',
                'price': entry_details['entry_price']
            })
            
            # Check auto-trade setting
            if not self.config.get('mode.auto_trade', False):
                self.logger.info("Auto-trade disabled - signal logged only")
                if self.window:
                    self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': "ENTRY SIGNAL - Auto-trade disabled"})
                return
            
            # Execute trade
            self._execute_entry(entry_details)
            
        except Exception as e:
            self.logger.error(f"Error checking entry: {e}", exc_info=True)
    
    def _execute_entry(self, entry_details: dict):
        """Execute entry order."""
        try:
            # Safety check: verify demo mode if account is not demo
            account_info = self.market_data.get_account_info()
            if account_info:
                server = account_info.get('server', '').lower()
                is_demo_account = 'demo' in server
                demo_mode_enabled = self.config.get('mode.demo_mode', True)
                
                if not is_demo_account and demo_mode_enabled:
                    self.logger.warning("BLOCKED: Demo Mode is ON but account is LIVE. Disable Demo Mode to trade live.")
                    if self.window:
                        self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': "TRADE BLOCKED: Demo Mode ON with LIVE account!"})
                    return
                
                if not is_demo_account and not demo_mode_enabled:
                    self.logger.warning("LIVE TRADING ACTIVE - Real money at risk!")
            
            # Get account info
            account_info = self.market_data.get_account_info()
            symbol_info = self.market_data.get_symbol_info()
            
            if not account_info or not symbol_info:
                self.logger.error("Cannot execute: Missing account/symbol info")
                return
            
            # Calculate position size
            position_size = self.risk_engine.calculate_position_size(
                equity=account_info['equity'],
                entry_price=entry_details['entry_price'],
                stop_loss=entry_details['stop_loss'],
                symbol_info=symbol_info
            )
            
            if position_size is None:
                self.logger.error("Position size calculation failed")
                return
            
            # Pre-compute TP levels using planned entry for order placement
            planned_tp_levels = self.strategy_engine.multi_level_tp.calculate_tp_levels(
                entry_price=entry_details['entry_price'],
                stop_loss=entry_details['stop_loss'],
                direction=1  # LONG only
            )
            planned_tp3 = planned_tp_levels.get('tp3', entry_details['take_profit']) if planned_tp_levels else entry_details['take_profit']

            # Send order
            order_result = self.execution_engine.send_market_order(
                order_type="BUY",
                volume=position_size,
                stop_loss=entry_details['stop_loss'],
                take_profit=planned_tp3,
                comment="Double Bottom Entry"
            )
            
            if order_result:
                # Get position from MT5 to get actual execution price
                ticket = order_result['order']
                time.sleep(0.1)  # Wait for MT5 to register position
                
                mt5_position = None
                live_positions = self.execution_engine.get_open_positions()
                for pos in live_positions:
                    if pos['ticket'] == ticket:
                        mt5_position = pos
                        break
                
                # Use actual execution price from MT5, fallback to order_result price
                actual_entry_price = mt5_position['price_open'] if mt5_position else order_result['price']
                
                # Calculate multi-level TP levels using actual entry
                tp_levels = self.strategy_engine.multi_level_tp.calculate_tp_levels(
                    entry_price=actual_entry_price,
                    stop_loss=entry_details['stop_loss'],
                    direction=1  # LONG only
                )

                # Use priority TP3 (from settings) as order take-profit
                take_profit_price = tp_levels.get('tp3', entry_details['take_profit']) if tp_levels else entry_details['take_profit']
                
                # Record position in state manager
                self.state_manager.open_position({
                    'ticket': ticket,
                    'entry_price': actual_entry_price,
                    'price_current': actual_entry_price,  # Initial value = entry price
                    'stop_loss': entry_details['stop_loss'],
                    'take_profit': take_profit_price,
                    'volume': position_size,
                    'profit': 0.0,  # Initial value = 0
                    'entry_time': datetime.now(),
                    'atr': entry_details.get('atr'),
                    # Multi-level TP fields
                    'direction': 1,  # LONG
                    'tp_state': 'IN_TRADE',
                    'tp1_price': tp_levels.get('tp1'),
                    'tp2_price': tp_levels.get('tp2'),
                    'tp3_price': tp_levels.get('tp3'),
                    'current_stop_loss': entry_details['stop_loss'],
                })
                
                # Update strategy cooldown
                self.strategy_engine.update_last_trade_time(datetime.now())
                
                # Log trade
                self.trading_logger.log_trade({
                    'type': 'ENTRY',
                    'ticket': ticket,
                    'entry_price': actual_entry_price,
                    'stop_loss': entry_details['stop_loss'],
                    'take_profit': entry_details['take_profit'],
                    'volume': position_size,
                    'pattern_type': 'Double Bottom'
                })
                
                self.logger.info(f"Trade executed successfully: Ticket {ticket}, Entry={actual_entry_price:.5f}")
                
                # Send alert for position opened
                self.alert_manager.alert_position_opened({
                    'ticket': ticket,
                    'entry_price': actual_entry_price,
                    'stop_loss': entry_details['stop_loss'],
                    'take_profit': take_profit_price,
                    'volume': position_size
                })
                
                if self.window:
                    self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': f"TRADE OPENED: Ticket {ticket} @ {actual_entry_price:.5f}"})
                    # Update position display with all open positions
                    all_positions = self.state_manager.get_all_positions()
                    if all_positions:
                        self.ui_queue.post_event(UIEventType.UPDATE_POSITION_DISPLAY, {'positions': all_positions})
            else:
                self.logger.error("Order execution failed")
                
        except Exception as e:
            self.logger.error(f"Error executing entry: {e}", exc_info=True)
    
    def _monitor_positions(self, current_bar):
        """Monitor all open positions and check for exit conditions (supports pyramiding)."""
        try:
            all_positions = self.state_manager.get_all_positions()
            if not all_positions:
                return
            
            symbol_info = self.market_data.get_symbol_info()
            # Get live positions from MT5
            live_positions = self.execution_engine.get_open_positions()
            live_tickets = {pos['ticket']: pos for pos in live_positions}
            
            # Check each tracked position
            for position_data in all_positions.copy():
                ticket = position_data['ticket']
                
                # Check if position still exists in MT5
                if ticket not in live_tickets:
                    # Position closed externally
                    self.logger.warning(f"Position {ticket} closed externally")
                    self.state_manager.close_position(
                        exit_price=current_bar['close'],
                        exit_reason="Closed externally",
                        ticket=ticket,
                        symbol_info=symbol_info,
                        risk_engine=self.risk_engine
                    )
                    continue
                
                # Update position data with live MT5 values
                live_position = live_tickets[ticket]
                position_data['price_current'] = live_position['price_current']
                position_data['profit'] = live_position['profit']
                position_data['swap'] = live_position.get('swap', 0.0)
                
                # Check exit conditions with multi-level TP support
                tp_state = position_data.get('tp_state', 'IN_TRADE')
                tp_levels = {
                    'tp1': position_data.get('tp1_price'),
                    'tp2': position_data.get('tp2_price'),
                    'tp3': position_data.get('tp3_price'),
                }
                direction = position_data.get('direction', 1)
                
                # Use multi-level TP if levels are defined
                if all(tp_levels.values()):
                    should_exit, reason, new_tp_state, new_stop_loss = self.strategy_engine.evaluate_exit(
                        current_price=current_bar['close'],
                        entry_price=position_data['entry_price'],
                        stop_loss=position_data.get('current_stop_loss', position_data['stop_loss']),
                        take_profit=position_data['take_profit'],
                        tp_state=tp_state,
                        tp_levels=tp_levels,
                        direction=direction,
                        tp_transition_time=position_data.get('tp_state_changed_at'),
                        atr_14=position_data.get('atr'),
                        market_regime=position_data.get('market_regime'),
                        momentum_state=position_data.get('momentum_state'),
                        last_closed_bar=current_bar if isinstance(current_bar, dict) else None
                    )
                    
                    # Update TP state if changed
                    if new_tp_state != tp_state:
                        # MEDIUM: BARS_AFTER_TP_NOT_INCREMENTING - Prepare counter updates (NEW)
                        bars_tp1_update = None
                        bars_tp2_update = None
                        if new_tp_state == 'TP1_REACHED':
                            bars_tp1_update = position_data.get('bars_held_after_tp1', 0) + 1
                        if new_tp_state == 'TP2_REACHED':
                            bars_tp2_update = position_data.get('bars_held_after_tp2', 0) + 1
                        
                        self.state_manager.update_position_tp_state(
                            ticket=ticket,
                            new_tp_state=new_tp_state,
                            new_stop_loss=new_stop_loss,
                            transition_time=current_bar.get('time') if isinstance(current_bar, dict) else None,
                            bars_after_tp1=bars_tp1_update,
                            bars_after_tp2=bars_tp2_update
                        )
                        self.logger.info(f"Position {ticket} TP state: {tp_state} -> {new_tp_state}")
                    
                    # MEDIUM: BARS_AFTER_TP_NOT_INCREMENTING - Increment bar counters on bar-close (NEW)
                    if new_tp_state == 'TP1_REACHED':
                        current_bars_tp1 = position_data.get('bars_held_after_tp1', 0)
                        position_data['bars_held_after_tp1'] = current_bars_tp1 + 1
                    if new_tp_state == 'TP2_REACHED':
                        current_bars_tp2 = position_data.get('bars_held_after_tp2', 0)
                        position_data['bars_held_after_tp2'] = current_bars_tp2 + 1
                else:
                    # Fallback to simple exit (backward compatibility)
                    should_exit, reason, _, _ = self.strategy_engine.evaluate_exit(
                        current_price=current_bar['close'],
                        entry_price=position_data['entry_price'],
                        stop_loss=position_data['stop_loss'],
                        take_profit=position_data['take_profit']
                    )
                
                if should_exit:
                    # Use enriched position_data so TP levels (tp1/tp2/tp3) are available for exit validation
                    self._execute_exit(position_data, reason)
            
            # Update UI with all open positions (for multi-position display) - thread-safe
            if self.window:
                all_open_positions = self.state_manager.get_all_positions()
                if all_open_positions:
                    self.ui_queue.post_event(UIEventType.UPDATE_POSITION_DISPLAY, {'positions': all_open_positions})
                else:
                    self.ui_queue.post_event(UIEventType.UPDATE_POSITION_DISPLAY, {'positions': None})

            
        except Exception as e:
            self.logger.error(f"Error monitoring positions: {e}", exc_info=True)
    
    def _monitor_position(self, current_bar):
        """Monitor single position (legacy method - calls _monitor_positions)."""
        self._monitor_positions(current_bar)
    
    def _execute_exit(self, position: dict, reason: str):
        """Execute exit order."""
        try:
            ticket = position['ticket']
            exit_price = position['price_current']
            
            # Validate reason is not empty or a number (which would indicate a price)
            if not reason or reason is None or isinstance(reason, (int, float)):
                self.logger.warning(f"Invalid exit reason: {reason}. Using 'Unknown'")
                reason = "Unknown"
            
            # VALIDATE: Exit reason must match actual exit conditions
            entry_price = position['entry_price']
            stop_loss = position.get('current_stop_loss', position['stop_loss'])
            take_profit = position['take_profit']
            tp3_price = position.get('tp3_price', take_profit)
            direction = position.get('direction', 1)
            
            # Check if reason matches the exit price
            if direction == 1:  # LONG
                is_sl_hit = exit_price <= stop_loss
                is_tp_hit = exit_price >= take_profit
                is_tp3_hit = exit_price >= tp3_price if tp3_price is not None else is_tp_hit
            else:  # SHORT
                is_sl_hit = exit_price >= stop_loss
                is_tp_hit = exit_price <= take_profit
                is_tp3_hit = exit_price <= tp3_price if tp3_price is not None else is_tp_hit
            
            # Validate exit reason matches actual exit condition
            reason_upper = reason.upper()

            # TP3 integrity: only allow TP3 reason if price actually hit TP3
            if "TP3" in reason_upper and not is_tp3_hit:
                self.logger.warning(
                    f"TP3 reason mismatch: exit_price {exit_price:.2f} vs TP3 {tp3_price:.2f if tp3_price else float('nan')}"
                )
                if is_sl_hit:
                    reason = "Stop Loss"
                else:
                    reason = "Protective Exit - TP3 Not Reached"
                self.logger.warning(f"CORRECTED: Exit reason -> {reason}")

            elif "TP" in reason_upper and not is_tp_hit:
                # Exit reason says TP but exit_price didn't reach TP
                self.logger.warning(
                    f"MISMATCH: Exit reason '{reason}' but exit_price {exit_price:.2f} "
                    f"doesn't match TP {take_profit:.2f}. Actual: SL_hit={is_sl_hit}, TP_hit={is_tp_hit}"
                )
                if is_sl_hit:
                    reason = "Stop Loss"
                elif reason_upper not in ["RECOVERY MODE", "CLOSED EXTERNALLY", "UNKNOWN"]:
                    reason = "Unknown Closure"
                self.logger.warning(f"CORRECTED: Exit reason -> {reason}")

            elif "STOP LOSS" in reason_upper and is_tp_hit:
                # Exit reason says SL but exit_price reached TP
                self.logger.warning(
                    f"MISMATCH: Exit reason '{reason}' but exit_price {exit_price:.2f} "
                    f"reached TP {take_profit:.2f}"
                )
                reason = "Take Profit"
                self.logger.warning(f"CORRECTED: Exit reason -> {reason}")
            
            # Close position
            success = self.execution_engine.close_position(ticket, close_price=exit_price)
            
            if success:
                # Update state manager
                symbol_info = self.market_data.get_symbol_info()
                self.state_manager.close_position(
                    exit_price=exit_price,
                    exit_reason=reason,
                    ticket=ticket,
                    symbol_info=symbol_info,
                    risk_engine=self.risk_engine,
                    swap=position.get('swap', 0.0)
                )
                
                # Log trade
                self.trading_logger.log_trade({
                    'type': 'EXIT',
                    'ticket': ticket,
                    'exit_price': exit_price,
                    'profit': position['profit'],
                    'exit_reason': reason
                })
                
                self.logger.info(f"Position closed: {reason}, Profit: ${position['profit']:.2f}")
                
                # Send alert for position closed
                self.alert_manager.alert_position_closed({
                    'ticket': ticket,
                    'exit_price': exit_price,
                    'profit': position['profit'],
                    'exit_reason': reason
                })
                
                if self.window:
                    self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': f"POSITION CLOSED: {reason}, P/L: ${position['profit']:.2f}"})
                    # Update position display with remaining positions
                    remaining_positions = self.state_manager.get_all_positions()
                    if remaining_positions:
                        self.ui_queue.post_event(UIEventType.UPDATE_POSITION_DISPLAY, {'positions': remaining_positions})
                    else:
                        self.ui_queue.post_event(UIEventType.UPDATE_POSITION_DISPLAY, {'positions': None})
            else:
                self.logger.error("Failed to close position")
                
        except Exception as e:
            self.logger.error(f"Error executing exit: {e}", exc_info=True)
    
    def _update_ui(self, current_bar, indicators, pattern):
        """
        Update UI with current data (thread-safe version).
        
        All UI updates go through the thread-safe queue to prevent
        race conditions when backtest is running simultaneously.
        """
        if not self.window:
            return
        
        try:
            # Get live price
            live_price = self.market_data.get_current_tick()
            display_price = live_price if live_price is not None else current_bar['close']
            
            # Post market data update to queue (thread-safe)
            self.ui_queue.post_event(UIEventType.UPDATE_MARKET_DATA, {
                'price': display_price,
                'indicators': indicators
            })
            
            # Post pattern status update
            self.ui_queue.post_event(UIEventType.UPDATE_PATTERN_STATUS, {
                'pattern': pattern
            })
            
            # Post trade history update
            self.ui_queue.post_event(UIEventType.UPDATE_TRADE_HISTORY, {})

            # Update market regime (context only, bar-close values)
            if indicators and 'ema50' in indicators and 'ema200' in indicators:
                regime, confidence = self.market_regime_engine.evaluate(
                    close=current_bar['close'],
                    ema50=indicators.get('ema50'),
                    ema200=indicators.get('ema200')
                )
                regime_state = self.market_regime_engine.get_state()
                
                # Post regime update to queue
                self.ui_queue.post_event(UIEventType.UPDATE_MARKET_REGIME, {
                    'regime_state': regime_state
                })
                
                # Persist regime state for restart continuity
                self.state_manager.set_regime_state(regime_state)
            
            # Note: Position Preview, Quality Score, Guard Status panels are disabled
            # Uncomment when implemented:
            # self.ui_queue.post_event(UIEventType.UPDATE_POSITION_PREVIEW, {'data': None})
            # self.ui_queue.post_event(UIEventType.UPDATE_QUALITY_SCORE, {'data': None})
            # self.ui_queue.post_event(UIEventType.UPDATE_GUARD_STATUS, {'data': None})
            
            # Post statistics update (live dashboard)
            stats = self.state_manager.get_statistics()
            alert_stats = self.alert_manager.get_statistics() if self.alert_manager else {}
            ui_queue_stats = self.ui_queue.get_statistics() if self.ui_queue else {}
            perf_top = self.performance_monitor.get_slowest_operations(top_n=3)
            perf_all = self.performance_monitor.get_all_metrics()
            uptime_seconds = (datetime.now() - self.app_start_time).total_seconds()

            self.ui_queue.post_event(UIEventType.UPDATE_STATISTICS, {
                'trade_stats': stats,
                'uptime_seconds': uptime_seconds,
                'alert_stats': alert_stats,
                'ui_queue_stats': ui_queue_stats,
                'performance_top': perf_top,
                'performance_all': perf_all
            })
            
            # Update account info (thread-safe)
            account_info = self.market_data.get_account_info()
            if account_info:
                self.ui_queue.post_event(UIEventType.UPDATE_CONNECTION_STATUS, {'connected': True, 'account_info': account_info})
            
            # Update trading sessions (thread-safe)
            sessions = self.market_data.get_active_sessions()
            self.ui_queue.post_event(UIEventType.UPDATE_SESSIONS, {'sessions': sessions})
            
            # Update runtime context (thread-safe)
            # Auto trading requires BOTH: checkbox enabled AND runtime policy allows it
            can_auto_trade_by_policy, policy_reason = self.runtime_manager.can_auto_trade()
            auto_trading_active = self.auto_trade_enabled and can_auto_trade_by_policy
            
            runtime_context = {
                'runtime_mode': self.runtime_manager.runtime_mode.value,
                'auto_trading_enabled': auto_trading_active,
                'account_type': self.runtime_manager.account_type.value if self.runtime_manager.account_type else 'UNKNOWN',
                'mt5_connection_status': 'CONNECTED' if self.is_connected else 'DISCONNECTED',
                'last_heartbeat': datetime.now().strftime('%H:%M:%S')
            }
            self.ui_queue.post_event(UIEventType.UPDATE_RUNTIME_CONTEXT, {'context': runtime_context})
            
        except Exception as e:
            self.logger.error(f"Error updating UI: {e}")
    
    def _perform_recovery(self):
        """
        Perform system recovery after connection is established.
        
        This reconstructs the system state to ensure consistency with the strategy,
        regardless of offline periods or unexpected shutdowns.
        """
        try:
            # Only perform recovery if there are open positions
            if not self.state_manager.has_open_position():
                self.logger.info("No open positions - recovery not needed")
                return
            
            self.logger.info("Performing system recovery...")
            
            # Execute recovery
            recovery_result = self.recovery_engine.perform_recovery(
                market_data_service=self.market_data,
                indicator_engine=self.indicator_engine,
                pattern_engine=self.pattern_engine,
                strategy_engine=self.strategy_engine,
                state_manager=self.state_manager,
                execution_engine=self.execution_engine,
                risk_engine=self.risk_engine
            )
            
            # Log recovery result
            if recovery_result['recovery_successful']:
                self.logger.info("Recovery completed successfully")
                self.logger.info(f"  Positions validated: {recovery_result['positions_validated']}")
                self.logger.info(f"  Positions closed: {recovery_result['positions_closed']}")
                
                # Log closed positions
                for closed_pos in recovery_result['closed_positions']:
                    self.logger.warning(
                        f"  Closed position {closed_pos['ticket']}: {closed_pos['reason']} "
                        f"@ {closed_pos['exit_price']:.2f}"
                    )
                
                if self.window:
                    self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message':
                        f"Recovery: {recovery_result['positions_validated']} positions validated, "
                        f"{recovery_result['positions_closed']} closed"
                    })
            else:
                self.logger.error(f"Recovery failed: {recovery_result['recovery_reason']}")
                if self.window:
                    self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': f"Recovery failed: {recovery_result['recovery_reason']}"})
        
        except Exception as e:
            self.logger.error(f"Error during recovery: {e}", exc_info=True)
    
    def set_window(self, window: MainWindow):
        """Set the UI window reference and connect signals."""
        self.window = window
        window._controller = self  # Allow UI to call controller methods
        self.window.start_requested.connect(self.start_trading)
        self.window.stop_requested.connect(self.stop_trading)
        self.window.settings_changed.connect(self._on_settings_changed)
        self.window.auto_trade_changed.connect(self._on_auto_trade_changed)
        
        # Load initial auto trade state from config
        self.auto_trade_enabled = self.config.get('mode.auto_trade', False)

        # Wire Backtest UI callbacks (prevents "Backtest signal not connected" message)
        if getattr(window, "backtest_window", None):
            window.backtest_window.run_backtest_signal = self._on_backtest_requested
            window.backtest_window.export_json_clicked = self._on_export_json_requested
            window.backtest_window.export_csv_clicked = self._on_export_csv_requested
            window.backtest_window.export_html_clicked = self._on_export_html_requested

    def _on_backtest_requested(self):
        """Run backtest from UI trigger."""
        if not self.window or not getattr(self.window, "backtest_window", None):
            return
        bt_ui = self.window.backtest_window

        # Prevent concurrent runs
        if self.backtest_worker and self.backtest_worker.isRunning():
            bt_ui.set_status("Backtest already running...")
            return

        bt_ui.set_status("Starting backtest...")
        bt_ui.progress_bar.setVisible(True)
        bt_ui.progress_bar.setValue(0)
        bt_ui.progress_bar.setFormat("Initializing backtest...")

        # Share live market data service with backtest engine for data loading
        self.backtest_engine.market_data_service = self.market_data

        # Spin up worker thread
        self.backtest_worker = BacktestWorker(
            backtest_engine=self.backtest_engine,
            strategy_engine=self.strategy_engine,
            indicator_engine=self.indicator_engine,
            risk_engine=self.risk_engine,
            pattern_engine=self.pattern_engine
        )
        self.backtest_worker.progress.connect(self._on_backtest_progress)
        self.backtest_worker.completed.connect(self._on_backtest_completed)
        self.backtest_worker.error.connect(self._on_backtest_error)
        self.backtest_worker.start()

    def _on_backtest_progress(self, message: str):
        if self.window and getattr(self.window, "backtest_window", None):
            self.window.backtest_window.set_status(message)

    def _on_backtest_completed(self, result: dict):
        if not self.window or not getattr(self.window, "backtest_window", None):
            return
        bt_ui = self.window.backtest_window
        bt_ui.hide_progress()
        bt_ui.set_status("Backtest completed")

        # Gather settings snapshot for display
        settings_snapshot = self.config.get_strategy_config() if hasattr(self.config, "get_strategy_config") else {}

        # Pass price bars and bar decisions if available
        # Use indicators-augmented bars for analyzer visibility (EMA/ATR)
        price_bars = getattr(self.backtest_engine, "df_with_indicators_full", None)
        bar_decisions = getattr(self.backtest_engine, "bar_decisions", None)

        bt_ui.display_results(
            summary=result.get('summary', {}),
            metrics=result.get('metrics', {}),
            trades_df=result.get('trades_df'),
            equity_curve=result.get('equity_curve', []),
            settings=settings_snapshot,
            price_bars=price_bars,
            bar_tooltips=None,
            bar_decisions=bar_decisions
        )

    def _on_backtest_error(self, message: str):
        if self.window and getattr(self.window, "backtest_window", None):
            self.window.backtest_window.hide_progress()
            self.window.backtest_window.set_status(f"Backtest error: {message}")
        self.logger.error(f"Backtest error: {message}")

    def _on_export_json_requested(self):
        """Export backtest results as JSON."""
        try:
            if not self.window or not getattr(self.window, "backtest_window", None):
                return
            
            bt_ui = self.window.backtest_window
            
            # Get backtest data from UI
            if not hasattr(bt_ui, 'last_result') or bt_ui.last_result is None:
                bt_ui.set_status("No backtest results to export")
                return
            
            result = bt_ui.last_result
            
            # Create exporter
            mt5_config = self.app_config.mt5
            exporter = BacktestReportExporter(
                symbol=mt5_config.symbol,
                timeframe=mt5_config.timeframe,
            )
            
            # Export JSON
            filepath = exporter.export_json(
                summary=result.get('summary', {}),
                metrics=result.get('metrics', {}),
                trades_df=result.get('trades_df'),
                settings=self.app_config.strategy.to_dict()
            )
            
            if filepath:
                bt_ui.set_status(f"✓ Exported JSON: {filepath.name}")
                self.logger.info(f"JSON export completed: {filepath}")
            else:
                bt_ui.set_status("✗ JSON export failed")
                
        except Exception as e:
            self.logger.error(f"Error exporting JSON: {e}", exc_info=True)
            if self.window and getattr(self.window, "backtest_window", None):
                self.window.backtest_window.set_status(f"Export error: {str(e)}")

    def _on_export_csv_requested(self):
        """Export backtest results as CSV."""
        try:
            if not self.window or not getattr(self.window, "backtest_window", None):
                return
            
            bt_ui = self.window.backtest_window
            
            # Get backtest data from UI
            if not hasattr(bt_ui, 'last_result') or bt_ui.last_result is None:
                bt_ui.set_status("No backtest results to export")
                return
            
            result = bt_ui.last_result
            
            # Create exporter
            mt5_config = self.app_config.mt5
            exporter = BacktestReportExporter(
                symbol=mt5_config.symbol,
                timeframe=mt5_config.timeframe,
            )
            
            # Export CSV
            filepath = exporter.export_csv(
                trades_df=result.get('trades_df'),
                settings=self.app_config.strategy.to_dict()
            )
            
            if filepath:
                bt_ui.set_status(f"✓ Exported CSV: {filepath.name}")
                self.logger.info(f"CSV export completed: {filepath}")
            else:
                bt_ui.set_status("✗ CSV export failed")
                
        except Exception as e:
            self.logger.error(f"Error exporting CSV: {e}", exc_info=True)
            if self.window and getattr(self.window, "backtest_window", None):
                self.window.backtest_window.set_status(f"Export error: {str(e)}")

    def _on_export_html_requested(self):
        """Export backtest results as HTML."""
        try:
            if not self.window or not getattr(self.window, "backtest_window", None):
                return
            
            bt_ui = self.window.backtest_window
            
            # Get backtest data from UI
            if not hasattr(bt_ui, 'last_result') or bt_ui.last_result is None:
                bt_ui.set_status("No backtest results to export")
                return
            
            result = bt_ui.last_result
            
            # Create exporter
            mt5_config = self.app_config.mt5
            exporter = BacktestReportExporter(
                symbol=mt5_config.symbol,
                timeframe=mt5_config.timeframe,
            )
            
            # Export HTML
            filepath = exporter.export_html(
                summary=result.get('summary', {}),
                metrics=result.get('metrics', {}),
                trades_df=result.get('trades_df'),
                equity_curve=result.get('equity_curve', []),
                settings=self.app_config.strategy.to_dict()
            )
            
            if filepath:
                bt_ui.set_status(f"✓ Exported HTML: {filepath.name}")
                self.logger.info(f"HTML export completed: {filepath}")
                
                # Optional: Open in browser
                try:
                    import webbrowser
                    webbrowser.open(str(filepath))
                except Exception as e:
                    self.logger.debug(f"Could not open browser: {e}")
            else:
                bt_ui.set_status("✗ HTML export failed")
                
        except Exception as e:
            self.logger.error(f"Error exporting HTML: {e}", exc_info=True)
            if self.window and getattr(self.window, "backtest_window", None):
                self.window.backtest_window.set_status(f"Export error: {str(e)}")
    
    @Slot(dict)
    def _on_settings_changed(self, settings: dict):
        """Handle settings changes from UI."""
        try:
            # Update configuration
            if 'risk_percent' in settings:
                self.config.set('risk.risk_percent', settings['risk_percent'])
                self.risk_engine.risk_percent = settings['risk_percent']
            
            if 'atr_multiplier' in settings:
                self.config.set('strategy.atr_multiplier_stop', settings['atr_multiplier'])
                self.strategy_engine.atr_multiplier_stop = settings['atr_multiplier']
            
            if 'risk_reward_ratio_long' in settings:
                self.config.set('strategy.risk_reward_ratio_long', settings['risk_reward_ratio_long'])
                self.strategy_engine.risk_reward_ratio_long = settings['risk_reward_ratio_long']
            
            if 'risk_reward_ratio_short' in settings:
                self.config.set('strategy.risk_reward_ratio_short', settings['risk_reward_ratio_short'])
                self.strategy_engine.risk_reward_ratio_short = settings['risk_reward_ratio_short']
            
            if 'cooldown_hours' in settings:
                self.config.set('strategy.cooldown_hours', settings['cooldown_hours'])
                self.strategy_engine.cooldown_hours = settings['cooldown_hours']
            
            if 'pyramiding' in settings:
                self.config.set('strategy.pyramiding', settings['pyramiding'])
            
            if 'enable_momentum_filter' in settings:
                self.config.set('strategy.enable_momentum_filter', settings['enable_momentum_filter'])
                self.strategy_engine.enable_momentum_filter = settings['enable_momentum_filter']
            
            # Save config
            self.config.save_config()
            self.logger.info("Settings updated successfully")
            
        except Exception as e:
            self.logger.error(f"Error updating settings: {e}")
    
    def manual_close_position(self, ticket: str):
        """
        Close a specific position manually by ticket.
        
        Args:
            ticket: Position ticket number
        """
        try:
            # Normalize ticket to int for MT5 APIs
            try:
                ticket_int = int(ticket)
            except (TypeError, ValueError):
                self.logger.error(f"Invalid ticket value: {ticket}")
                if self.window:
                    self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': f"Error: Invalid ticket {ticket}"})
                return
            ticket = ticket_int
            # Find position
            position = None
            for pos in self.state_manager.get_all_positions():
                if int(pos.get('ticket')) == ticket:
                    position = pos
                    break
            
            if not position:
                self.logger.error(f"Position {ticket} not found")
                if self.window:
                    self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': f"Error: Position {ticket} not found"})
                return
            
            # Execute close
            self._execute_exit(position, "MANUAL CLOSE BY USER")
            
        except Exception as e:
            self.logger.error(f"Error closing position {ticket}: {e}")
            if self.window:
                self.ui_queue.post_event(UIEventType.LOG_MESSAGE, {'message': f"Error closing position: {e}"})
    
    @Slot(bool)
    def _on_auto_trade_changed(self, enabled: bool):
        """Handle Auto Trade toggle from UI."""
        try:
            self.auto_trade_enabled = enabled
            self.config.set('mode.auto_trade', enabled)
            self.config.save_config()
            self.logger.info(f"Auto Trade {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            self.logger.error(f"Error updating auto trade: {e}")
    
    def shutdown(self):
        """
        Graceful shutdown - stop timers, flush state, close connections.
        
        Call this from UI close event to ensure clean shutdown.
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("TRADING SYSTEM SHUTTING DOWN")
            self.logger.info("=" * 60)
            
            # Send shutdown alert
            self.alert_manager.alert_system_shutdown()
            
            # Log performance metrics before shutdown
            perf_report = self.performance_monitor.get_performance_report()
            self.logger.info("Performance metrics at shutdown:\n" + perf_report)
            
            # Log alert summary
            alert_summary = self.alert_manager.get_summary()
            self.logger.info(f"Alert summary: {alert_summary}")
            
            # Stop trading
            if self.is_running:
                self.stop_trading()
            
            # Flush pending state writes (blocks until done)
            self.logger.info("Flushing pending state writes...")
            self.state_manager.flush()
            
            # Shutdown state manager (stops writer thread)
            self.logger.info("Shutting down state persistence...")
            self.state_manager.shutdown()
            
            # Disconnect from MT5
            if self.is_connected:
                self.logger.info("Disconnecting from MT5...")
                self.disconnect_from_mt5()
            
            # Stop UI queue
            if self.ui_queue:
                self.logger.info("Stopping UI update queue...")
                self.ui_queue.stop()
            
            self.logger.info("SHUTDOWN COMPLETE")
            self.logger.info("=" * 60)
        
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def get_performance_metrics(self) -> Dict:
        """Get all performance metrics (for external monitoring)."""
        return self.performance_monitor.get_all_metrics()
    
    def get_performance_report(self) -> str:
        """Get formatted performance report (for logging/display)."""
        return self.performance_monitor.get_performance_report()



class HeadlessTradingRunner:
    """Headless trading entrypoint that executes a bar-close loop."""

    _VALID_TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"}

    def __init__(self, config_path: str, poll_interval_seconds: float = 5.0):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_runtime_config(config_path)
        self.app_config = load_app_config(config_path)
        log_config = self.config.get("logging", {})
        self.trading_logger = setup_logging(
            log_dir=log_config.get("log_dir", "logs"),
            log_level=log_config.get("log_level", "INFO"),
        )
        self.logger = self.trading_logger.get_main_logger()
        self.poll_interval_seconds = max(1.0, poll_interval_seconds)

        mt5_config = self.app_config.mt5
        strategy_config = self.app_config.strategy
        risk_config = self.app_config.risk

        self.market_data = MarketDataService(
            config=self.app_config,
            symbol=mt5_config.symbol,
            timeframe=mt5_config.timeframe,
        )
        self.connection_manager = MT5ConnectionManager(
            heartbeat_interval_seconds=30,
            max_heartbeat_failures=3,
        )
        self.connection_manager.on_status_change = self._on_connection_status_change
        self.connection_manager.on_reconnect_status = self._on_reconnect_status
        self.indicator_engine = IndicatorEngine()
        self.pattern_engine = PatternEngine(
            lookback_left=strategy_config.pivot_lookback_left,
            lookback_right=strategy_config.pivot_lookback_right,
            equality_tolerance=strategy_config.equality_tolerance,
            min_bars_between=strategy_config.min_bars_between,
        )
        self.risk_engine = RiskEngine(
            config=self.app_config,
            risk_percent=risk_config.risk_percent,
            commission_per_lot=risk_config.commission_per_lot,
        )
        self.decision_engine = DecisionEngine(
            self.app_config,
            risk_engine=self.risk_engine,
        )
        self.execution_engine = ExecutionEngine(
            config=self.app_config,
            symbol=mt5_config.symbol,
            magic_number=mt5_config.magic_number,
        )
        self.state_manager = StateManager(
            state_file=self.config.get("data.state_file", "data/state.json"),
            backup_dir=self.config.get("data.backup_dir", "data/backups"),
            use_atomic_writes=True,
        )

        self.last_closed_bar_time: Optional[datetime] = None
        self.last_trade_bar_index: int = -9999
        self.bar_counter: int = 0
        self.is_running = False
        self.trading_paused = False
        self.last_heartbeat_check: float = 0.0

    def _load_runtime_config(self, config_path: str) -> Config:
        config = load_legacy_config(config_path)
        self._validate_runtime_config(config)
        return config

    def _validate_runtime_config(self, config: Config) -> None:
        risk_percent = config.get("risk.risk_percent", 1.0)
        if not isinstance(risk_percent, (int, float)) or not (0 < risk_percent <= 100):
            self.logger.warning(
                "Invalid risk.risk_percent=%s; using default 1.0.",
                risk_percent,
            )
            config.set("risk.risk_percent", 1.0)

        pyramiding = config.get("strategy.pyramiding", 1)
        if not isinstance(pyramiding, int) or pyramiding < 1:
            self.logger.warning(
                "Invalid strategy.pyramiding=%s; using default 1.",
                pyramiding,
            )
            config.set("strategy.pyramiding", 1)

        timeframe = config.get("mt5.timeframe", "H1")
        if timeframe not in self._VALID_TIMEFRAMES:
            self.logger.warning(
                "Invalid mt5.timeframe=%s; using default H1.",
                timeframe,
            )
            config.set("mt5.timeframe", "H1")

    def connect_mt5(self) -> bool:
        mt5_config = self.app_config.mt5
        connected = self.market_data.connect(
            login=mt5_config.login,
            password=mt5_config.password,
            server=mt5_config.server,
            terminal_path=mt5_config.terminal_path,
        )
        self.connection_manager.set_connection_status(connected)
        if connected:
            self.logger.info("Connected to MT5 for headless trading.")
        else:
            self.logger.error("Failed to connect to MT5 for headless trading.")
        return connected

    def request_shutdown(self) -> None:
        self.is_running = False

    def _perform_heartbeat(self) -> None:
        now = time.time()
        if now - self.last_heartbeat_check < 30:
            return
        self.last_heartbeat_check = now
        healthy = self.connection_manager.check_connection()
        if not healthy:
            if not self.trading_paused:
                self.trading_paused = True
                self.logger.error("Heartbeat failure detected - trading paused.")
            mt5_config = self.app_config.mt5
            started = self.connection_manager.request_reconnect_async(
                login=mt5_config.login,
                password=mt5_config.password,
                server=mt5_config.server,
                terminal_path=mt5_config.terminal_path,
            )
            if not started:
                self.logger.debug("Reconnect request skipped (already in progress).")
        elif healthy and self.trading_paused:
            self.trading_paused = False
            self.logger.info("Heartbeat recovered - trading resumed.")

    def _on_connection_status_change(self, is_connected: bool) -> None:
        """Handle MT5 connection status updates in headless mode."""
        if is_connected:
            self.logger.info("MT5 connection restored (headless).")
            self._resync_market_data()
            self.trading_paused = False
        else:
            self.logger.error("MT5 connection lost (headless). Trading paused.")
            self.trading_paused = True

    def _on_reconnect_status(self, message: str) -> None:
        """Log reconnect status updates in headless mode."""
        self.logger.info("Reconnect status (headless): %s", message)

    def _resync_market_data(self) -> None:
        """Refetch bar history after reconnection."""
        try:
            bars_to_fetch = self.config.get("data.bars_to_fetch", 500)
            df = self.market_data.get_bars(count=bars_to_fetch)
            if df is None or df.empty:
                self.logger.warning("Market data resync failed (headless, no bars returned).")
                return
            self.logger.info("Market data resynced (headless): %s bars.", len(df))
        except Exception as exc:
            self.logger.error("Market data resync error (headless): %s", exc, exc_info=True)

    def _process_bar_close(self) -> None:
        bars_to_fetch = self.config.get("data.bars_to_fetch", 500)
        df = self.market_data.get_bars(count=bars_to_fetch)
        if df is None or df.empty:
            self.logger.warning("No bars fetched; skipping bar-close processing.")
            return

        df = df.copy()
        if "time" in df.columns:
            df = df.set_index("time")

        df = self.indicator_engine.calculate_all_indicators(df)
        if len(df) < 3:
            self.logger.warning("Not enough data for indicators; waiting for more bars.")
            return

        closed_df = df.iloc[:-1]
        current_bar = closed_df.iloc[-1]
        bar_time = closed_df.index[-1]

        if self.last_closed_bar_time == bar_time:
            return

        self.last_closed_bar_time = bar_time
        self.bar_counter += 1

        pattern = self.pattern_engine.detect_double_bottom(closed_df)
        account_info = self.market_data.get_account_info()
        symbol_info = self.market_data.get_symbol_info()
        equity = account_info.get("equity") if account_info else 0.0
        account_state = {
            "equity": equity,
            "open_positions": len(self.state_manager.open_positions),
            "last_trade_bar": self.last_trade_bar_index,
        }
        decision = self.decision_engine.evaluate(
            bar_index=len(closed_df) - 1,
            df=closed_df,
            pattern=pattern,
            account_state=account_state,
            direction="LONG",
            symbol_info=symbol_info,
        )
        decision.decision_source = "Live"

        if decision.decision != DecisionResult.TRADE_ALLOWED:
            self.logger.info(
                "Decision: %s (%s)",
                decision.decision.value,
                decision.reason or "No trade",
            )
            self.state_manager.save_state()
            return

        symbol_info = symbol_info or {}
        entry_price = decision.planned_entry or float(current_bar["close"])
        stop_loss = decision.planned_sl
        take_profit = decision.planned_tp3

        if stop_loss is None:
            atr = float(current_bar.get("atr14", 0.0))
            stop_loss = entry_price - (atr * self.decision_engine.atr_multiplier_stop)

        volume = self.risk_engine.calculate_position_size(
            equity=equity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            symbol_info=symbol_info,
        )
        if volume is None:
            self.logger.warning("Position sizing failed; skipping execution.")
            return

        order = self.execution_engine.send_market_order(
            order_type="BUY",
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment="DecisionEngine Bar-Close",
        )
        if order:
            self.last_trade_bar_index = self.bar_counter
            self.state_manager.open_position(
                {
                    "ticket": order["order"],
                    "entry_price": order["price"],
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "volume": volume,
                    "entry_time": order.get("timestamp", datetime.now()),
                    "pattern_info": pattern,
                    "atr": float(current_bar.get("atr14", 0.0)),
                }
            )
            self.logger.info(
                "Order executed: ticket=%s volume=%.2f entry=%.2f",
                order["order"],
                volume,
                order["price"],
            )
        else:
            self.logger.warning("Order execution failed; no state persisted for entry.")

        self.state_manager.save_state()

    def run(self) -> None:
        if not self.connect_mt5():
            self.logger.error("Headless trading aborted: MT5 connection failed.")
            return

        self.is_running = True
        self.logger.info("Headless trading loop started.")
        try:
            while self.is_running:
                self._perform_heartbeat()
                if not self.trading_paused:
                    self._process_bar_close()
                time.sleep(self.poll_interval_seconds)
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self.logger.info("Headless trading shutdown initiated.")
        try:
            if self.connection_manager.reconnect_in_progress:
                self.connection_manager.cancel_reconnect()
        except Exception as exc:
            self.logger.warning("Reconnect cancel failed: %s", exc)

        try:
            self.state_manager.shutdown()
        except Exception as exc:
            self.logger.warning("State manager shutdown failed: %s", exc)

        try:
            self.market_data.disconnect()
        except Exception as exc:
            self.logger.warning("MT5 disconnect failed: %s", exc)

        self.logger.info("Headless trading shutdown complete.")


def _configure_headless_signals(runner: HeadlessTradingRunner) -> None:
    def _handler(signum, _frame):
        runner.logger.info("Signal %s received; shutting down.", signum)
        runner.request_shutdown()

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description="XAUUSD Trading System")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without UI using the bar-close trading loop.",
    )
    parser.add_argument(
        "--config",
        default=os.getenv("TRADING_CONFIG", "config/config.yaml"),
        help="Path to configuration file (YAML or JSON).",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=5.0,
        help="Polling interval in seconds for bar-close checks.",
    )
    args = parser.parse_args()

    if args.headless or os.getenv("TRADING_HEADLESS") == "1":
        runner = HeadlessTradingRunner(
            config_path=args.config,
            poll_interval_seconds=args.poll,
        )
        _configure_headless_signals(runner)
        runner.run()
        return

    app = QApplication(sys.argv)
    
    # Create controller
    controller = TradingController()
    
    # Create and show window with config
    window = MainWindow(config=controller.config)
    controller.set_window(window)
    
    # Store controller reference for cleanup
    window._controller = controller
    
    # Override closeEvent to ensure graceful shutdown
    original_close_event = window.closeEvent
    def close_event_with_shutdown(event):
        try:
            # Perform graceful shutdown
            controller.shutdown()
        except Exception as e:
            print(f"Error during shutdown: {e}")
        finally:
            # Continue with normal close
            original_close_event(event)
    
    window.closeEvent = close_event_with_shutdown
    window.show()
    
    # Connect to MT5
    controller.connect_mt5()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

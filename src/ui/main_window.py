"""
Main Window - PySide6 Desktop UI for the trading application

This module provides the graphical user interface for monitoring
and controlling the trading system.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QStatusBar, QTabWidget, QCheckBox, QSpinBox, QDoubleSpinBox, QMessageBox,
    QSplitter, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QColor
from datetime import datetime, timedelta
import logging
import math
import yaml

# Try to import BacktestWindow
try:
    from .backtest_window import BacktestWindow
    HAS_BACKTEST_WINDOW = True
except ImportError:
    BacktestWindow = None
    HAS_BACKTEST_WINDOW = False


class MainWindow(QMainWindow):
    """
    Main application window for the trading system.
    
    Features:
    - Market data display
    - Indicator values
    - Pattern detection status
    - Open position tracking
    - Trade history
    - Control panel for starting/stopping
    """
    
    # Signals
    start_requested = Signal()
    stop_requested = Signal()
    settings_changed = Signal(dict)
    auto_trade_changed = Signal(bool)
    
    def __init__(self, config=None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        self.setWindowTitle("XAUUSD Double Bottom Trading Strategy")
        self.setMinimumSize(1200, 800)
        
        self._setup_ui()
        self._apply_dark_theme()
        self._load_settings_from_config()
        
        # Status flags
        self.is_running = False
        self.is_connected = False
    
    def _setup_ui(self):
        """Set up the user interface layout."""
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Top section: Status and Controls
        top_layout = QHBoxLayout()
        top_layout.addWidget(self._create_status_group())
        top_layout.addWidget(self._create_runtime_context_group())
        top_layout.addWidget(self._create_controls_group())
        main_layout.addLayout(top_layout)
        
        # Middle section: Tabs for different views
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_market_tab(), "Market Data")
        self.tabs.addTab(self._create_position_tab(), "Position")
        self.tabs.addTab(self._create_history_tab(), "History")
        self.tabs.addTab(self._create_logs_tab(), "Logs")
        self.tabs.addTab(self._create_settings_tab(), "Settings")
        
        # Add Backtest tab if available
        if HAS_BACKTEST_WINDOW:
            self.backtest_window = BacktestWindow()
            self.tabs.addTab(self.backtest_window, "Backtest")
        else:
            no_backtest_label = QLabel("Backtest UI not available. Check imports.")
            no_backtest_label.setAlignment(Qt.AlignCenter)
            no_backtest_label.setStyleSheet("padding: 20px; color: #999;")
            self.tabs.addTab(no_backtest_label, "Backtest")
        
        main_layout.addWidget(self.tabs)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _create_status_group(self) -> QGroupBox:
        """Create the status display group."""
        group = QGroupBox("System Status")
        layout = QVBoxLayout()
        layout.setSpacing(5)  # Compact spacing
        layout.setContentsMargins(8, 8, 8, 8)  # Smaller margins
        
        # Connection status
        self.lbl_connection = QLabel("Connection: Disconnected")
        self.lbl_connection.setStyleSheet("color: red; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.lbl_connection)
        
        # Trading status
        self.lbl_trading = QLabel("Trading: Stopped")
        self.lbl_trading.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.lbl_trading)
        
        # Account info
        self.lbl_account = QLabel("Account: -")
        self.lbl_account.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.lbl_account)
        
        self.lbl_equity = QLabel("Equity: $0.00")
        self.lbl_equity.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.lbl_equity)
        
        self.lbl_balance = QLabel("Balance: $0.00")
        self.lbl_balance.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.lbl_balance)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def _create_runtime_context_group(self) -> QGroupBox:
        """Create the runtime context display group."""
        group = QGroupBox("Runtime Context")
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(8, 8, 8, 8)
        
        self.lbl_runtime_context_mode = QLabel("Runtime Mode: N/A")
        self.lbl_runtime_context_mode.setStyleSheet("font-size: 11px; font-weight: bold;")
        layout.addWidget(self.lbl_runtime_context_mode)
        
        self.lbl_runtime_context_auto_trading = QLabel("Auto Trading: N/A")
        self.lbl_runtime_context_auto_trading.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.lbl_runtime_context_auto_trading)
        
        self.lbl_runtime_context_account = QLabel("Account Type: N/A")
        self.lbl_runtime_context_account.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.lbl_runtime_context_account)
        
        self.lbl_runtime_context_connection = QLabel("MT5 Connection: N/A")
        self.lbl_runtime_context_connection.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.lbl_runtime_context_connection)
        
        self.lbl_runtime_context_heartbeat = QLabel("Last Heartbeat: N/A")
        self.lbl_runtime_context_heartbeat.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.lbl_runtime_context_heartbeat)
        
        # Auto-Trading Permission
        self.lbl_auto_trading_permission = QLabel("Auto-Trading Permission: ALLOWED")
        self.lbl_auto_trading_permission.setStyleSheet("color: white; font-size: 10px; padding: 4px; font-weight: bold; background-color: #1b5e20; border-radius: 3px; margin-top: 5px;")
        self.lbl_auto_trading_permission.setToolTip("Auto-trading permission status based on runtime mode and account type")
        layout.addWidget(self.lbl_auto_trading_permission)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def _create_controls_group(self) -> QGroupBox:
        """Create the control panel group."""
        group = QGroupBox("Controls")
        layout = QVBoxLayout()
        layout.setSpacing(5)  # Compact spacing
        layout.setContentsMargins(8, 8, 8, 8)  # Smaller margins
        
        # Toggle and Restart buttons in horizontal layout
        buttons_layout = QHBoxLayout()
        
        # Toggle button (Start/Stop)
        self.btn_toggle = QPushButton("Start Trading")
        self.btn_toggle.clicked.connect(self._on_toggle_clicked)
        self.btn_toggle.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 8px; font-size: 11px;")
        self.btn_toggle.setMinimumHeight(40)
        buttons_layout.addWidget(self.btn_toggle, stretch=3)
        
        # Restart button (smaller, next to toggle)
        self.btn_restart = QPushButton("Restart")
        self.btn_restart.clicked.connect(self._on_restart_clicked)
        self.btn_restart.setStyleSheet("background-color: orange; color: white; font-weight: bold; padding: 4px;")
        self.btn_restart.setMinimumHeight(40)
        self.btn_restart.setMaximumWidth(50)
        self.btn_restart.setToolTip("Restart Application")
        buttons_layout.addWidget(self.btn_restart, stretch=1)
        
        layout.addLayout(buttons_layout)
        
        # Runtime Mode Toggle Button
        self.btn_mode_toggle = QPushButton("DEVELOPMENT Mode")
        self.btn_mode_toggle.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 6px; font-size: 11px;")
        self.btn_mode_toggle.clicked.connect(self._on_mode_toggle_clicked)
        self.btn_mode_toggle.setMinimumHeight(32)
        layout.addWidget(self.btn_mode_toggle)
        
        # Account info and Trading sessions on same row
        info_layout = QHBoxLayout()
        info_layout.setSpacing(10)
        
        # Left side: Account info
        account_info_layout = QVBoxLayout()
        account_info_layout.setSpacing(2)
        self.lbl_account_type = QLabel("Demo Account")
        self.lbl_account_type.setStyleSheet("font-size: 10px; padding: 2px;")
        account_info_layout.addWidget(self.lbl_account_type)
        
        # Mode toggles (legacy - deprecated in favor of runtime mode)
        self.chk_demo = QCheckBox("Demo Mode (Legacy)")
        self.chk_demo.setChecked(True)
        self.chk_demo.stateChanged.connect(self._on_demo_mode_changed)
        self.chk_demo.setVisible(False)  # Hide legacy control
        account_info_layout.addWidget(self.chk_demo)
        
        self.chk_auto = QCheckBox("Auto Trade")
        self.chk_auto.setChecked(False)
        self.chk_auto.setStyleSheet("font-size: 10px;")
        self.chk_auto.stateChanged.connect(self._on_auto_trade_changed)
        account_info_layout.addWidget(self.chk_auto)
        
        info_layout.addLayout(account_info_layout)
        
        # Right side: Trading sessions
        sessions_layout = QVBoxLayout()
        sessions_layout.setSpacing(2)
        sessions_label = QLabel("Trading Sessions:")
        sessions_label.setStyleSheet("font-weight: bold; font-size: 10px;")
        sessions_layout.addWidget(sessions_label)
        
        self.lbl_asian = QLabel("● Asian")
        self.lbl_asian.setStyleSheet("color: gray; font-size: 10px;")
        sessions_layout.addWidget(self.lbl_asian)
        
        self.lbl_london = QLabel("● London")
        self.lbl_london.setStyleSheet("color: gray; font-size: 10px;")
        sessions_layout.addWidget(self.lbl_london)
        
        self.lbl_newyork = QLabel("● New York")
        self.lbl_newyork.setStyleSheet("color: gray; font-size: 10px;")
        sessions_layout.addWidget(self.lbl_newyork)
        
        info_layout.addLayout(sessions_layout)
        layout.addLayout(info_layout)
        
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def _create_market_tab(self) -> QWidget:
        """Create the market data tab."""
        widget = QWidget()
        outer_layout = QVBoxLayout()
        
        # Current price
        price_group = QGroupBox("Current Price")
        price_layout = QVBoxLayout()
        self.lbl_price = QLabel("Price: -")
        self.lbl_price.setFont(QFont("Arial", 24, QFont.Bold))
        price_layout.addWidget(self.lbl_price)
        price_group.setLayout(price_layout)
        
        # Market Regime (NEW - top summary block)
        regime_group = QGroupBox("Market Regime")
        regime_layout = QVBoxLayout()
        self.lbl_regime = QLabel("Regime: RANGE")
        self.lbl_regime.setFont(QFont("Arial", 12, QFont.Bold))
        self.lbl_regime_confidence = QLabel("Confidence: 0.0%")
        self.lbl_ema_distance = QLabel("EMA Distance: 0.00%")
        self.lbl_price_distance = QLabel("Price Distance: 0.00%")
        regime_layout.addWidget(self.lbl_regime)
        regime_layout.addWidget(self.lbl_regime_confidence)
        regime_layout.addWidget(self.lbl_ema_distance)
        regime_layout.addWidget(self.lbl_price_distance)
        regime_group.setLayout(regime_layout)
        
        # Indicators
        indicators_group = QGroupBox("Indicators")
        indicators_layout = QVBoxLayout()
        self.lbl_ema50 = QLabel("EMA 50: -")
        self.lbl_ema200 = QLabel("EMA 200: -")
        self.lbl_atr = QLabel("ATR 14: -")
        indicators_layout.addWidget(self.lbl_ema50)
        indicators_layout.addWidget(self.lbl_ema200)
        indicators_layout.addWidget(self.lbl_atr)
        indicators_group.setLayout(indicators_layout)
        
        # Pattern detection
        pattern_group = QGroupBox("Pattern Detection")
        pattern_layout = QVBoxLayout()
        self.lbl_pattern_status = QLabel("Status: No pattern")
        self.lbl_pattern_details = QTextEdit()
        self.lbl_pattern_details.setReadOnly(True)
        self.lbl_pattern_details.setMaximumHeight(150)
        pattern_layout.addWidget(self.lbl_pattern_status)
        pattern_layout.addWidget(self.lbl_pattern_details)
        pattern_group.setLayout(pattern_layout)
        
        # Entry conditions
        entry_group = QGroupBox("Entry Conditions")
        entry_layout = QVBoxLayout()
        self.lbl_cond_pattern = QLabel("Pattern Valid")
        self.lbl_cond_breakout = QLabel("Breakout Confirmed")
        self.lbl_cond_trend = QLabel("Above EMA50")
        self.lbl_cond_momentum = QLabel("Momentum OK")
        self.lbl_cond_cooldown = QLabel("Cooldown OK")
        
        # Initialize with red text (not met)
        for label in [self.lbl_cond_pattern, self.lbl_cond_breakout, self.lbl_cond_trend, 
                      self.lbl_cond_momentum, self.lbl_cond_cooldown]:
            label.setProperty("base_text", label.text())
            label.setStyleSheet("color: red; font-weight: bold;")
        
        entry_layout.addWidget(self.lbl_cond_pattern)
        entry_layout.addWidget(self.lbl_cond_breakout)
        entry_layout.addWidget(self.lbl_cond_trend)
        entry_layout.addWidget(self.lbl_cond_momentum)
        entry_layout.addWidget(self.lbl_cond_cooldown)
        entry_group.setLayout(entry_layout)
        
        # Entry Quality Score (NEW) - Hidden until implemented
        quality_group = QGroupBox("Entry Quality Score")
        quality_group.setVisible(False)  # Hide until quality scoring is implemented
        quality_layout = QVBoxLayout()
        self.lbl_quality_score = QLabel("Overall: -")
        self.lbl_quality_score.setFont(QFont("Arial", 14, QFont.Bold))
        self.lbl_quality_breakdown = QLabel("Pattern: - | EMA: - | Momentum: - | Volatility: -")
        quality_layout.addWidget(self.lbl_quality_score)
        quality_layout.addWidget(self.lbl_quality_breakdown)
        quality_group.setLayout(quality_layout)
        
        # Bar-Close Guard Status (NEW)
        guard_group = QGroupBox("Bar-Close Guard Status")
        guard_layout = QVBoxLayout()
        self.lbl_guard_closed_bar = QLabel("Using Closed Bar")
        self.lbl_guard_tick_noise = QLabel("Tick Noise Filter: PASSED")
        self.lbl_guard_anti_fomo = QLabel("Anti-FOMO: PASSED")
        guard_layout.addWidget(self.lbl_guard_closed_bar)
        guard_layout.addWidget(self.lbl_guard_tick_noise)
        guard_layout.addWidget(self.lbl_guard_anti_fomo)
        guard_group.setLayout(guard_layout)
        
        # Build two-column layout using a horizontal splitter
        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout()
        # High-importance summary panels on the left
        left_layout.addWidget(price_group)
        left_layout.addWidget(regime_group)
        left_layout.addWidget(indicators_group)
        left_layout.addWidget(entry_group)
        # quality_group is hidden - not added to layout
        left_layout.addStretch()
        left_widget.setLayout(left_layout)

        # Wrap left column in a scroll area to avoid squashing on small screens
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout()
        # Supporting context panels on the right
        right_layout.addWidget(pattern_group)
        right_layout.addWidget(guard_group)
        right_layout.addStretch()
        right_widget.setLayout(right_layout)

        # Wrap right column in a scroll area as well
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(right_widget)

        splitter.addWidget(left_scroll)
        splitter.addWidget(right_scroll)
        # Prioritize left column space slightly
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        outer_layout.addWidget(splitter)
        widget.setLayout(outer_layout)
        return widget
    
    def _create_position_tab(self) -> QWidget:
        """Create the position tracking tab with support for multiple positions (pyramiding)."""
        # RESPONSIVE_LAYOUT: Root container with vertical scroll (SCOPE: POSITION_TAB_RESPONSIVE_LAYOUT)
        widget = QWidget()
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        # Scroll area for main content (never clip, enable scroll)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                width: 12px;
                background-color: #2b2b2b;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #777777;
            }
        """)
        
        # Inner widget for scrollable content
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # RESPONSIVE_LAYOUT: Header section (sticky, allow wrap)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        # Position status
        self.lbl_position_status = QLabel("No open positions")
        self.lbl_position_status.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(self.lbl_position_status)
        
        # TP Engine Status Line (HIGH: TP_DECISION_PANELS_EMPTY mitigation)
        self.lbl_tp_engine_status = QLabel("TP Engine: Idle")
        self.lbl_tp_engine_status.setStyleSheet("font-size: 10px; padding: 6px; background-color: #333; color: #aaa; border-radius: 3px;")
        layout.addWidget(self.lbl_tp_engine_status)
        
        # Positions table with scrolling support
        self.table_positions = QTableWidget()
        self.table_positions.setColumnCount(11)
        self.table_positions.setHorizontalHeaderLabels([
            "Ticket", "Entry Price", "Current Price", "Stop Loss", 
            "Take Profit", "TP1", "TP2", "TP3", "Volume", "Profit/Loss", "Action"
        ])
        self.table_positions.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_positions.setSelectionMode(QTableWidget.SingleSelection)
        self.table_positions.cellClicked.connect(self._on_position_cell_clicked)
        layout.addWidget(self.table_positions)
        
        # RESPONSIVE_LAYOUT: TP Levels Details Panel (120-20vh height, compress on small screens)
        tp_group = QGroupBox("Target Profit Levels")
        tp_group.setMinimumHeight(120)
        tp_group.setMaximumHeight(int(768 * 0.2))  # 20vh approximation
        tp_layout = QVBoxLayout()
        tp_layout.setContentsMargins(6, 6, 6, 6)
        tp_layout.setSpacing(4)
        
        # TP1 with state badge (HIGH: TP_VALUES_INCONSISTENT mitigation)
        tp1_h_layout = QHBoxLayout()
        self.lbl_tp1_level = QLabel("TP1 (Risk 1:1): -")
        self.lbl_tp1_level.setStyleSheet("font-size: 11px; padding: 4px; background-color: #1b5e20; color: white; border-radius: 3px;")
        self.lbl_tp1_badge = QLabel("NOT_REACHED")
        self.lbl_tp1_badge.setStyleSheet("font-size: 9px; padding: 2px 4px; background-color: #555; color: white; border-radius: 3px;")
        tp1_h_layout.addWidget(self.lbl_tp1_level)
        tp1_h_layout.addWidget(self.lbl_tp1_badge)
        tp1_h_layout.addStretch()
        tp_layout.addLayout(tp1_h_layout)
        
        # TP2 with state badge (HIGH: TP_VALUES_INCONSISTENT mitigation)
        tp2_h_layout = QHBoxLayout()
        self.lbl_tp2_level = QLabel("TP2 (Risk 1:2): -")
        self.lbl_tp2_level.setStyleSheet("font-size: 11px; padding: 4px; background-color: #f57c00; color: white; border-radius: 3px;")
        self.lbl_tp2_badge = QLabel("NOT_REACHED")
        self.lbl_tp2_badge.setStyleSheet("font-size: 9px; padding: 2px 4px; background-color: #555; color: white; border-radius: 3px;")
        tp2_h_layout.addWidget(self.lbl_tp2_level)
        tp2_h_layout.addWidget(self.lbl_tp2_badge)
        tp2_h_layout.addStretch()
        tp_layout.addLayout(tp2_h_layout)
        
        # TP3 with state badge (HIGH: TP_VALUES_INCONSISTENT mitigation)
        tp3_h_layout = QHBoxLayout()
        self.lbl_tp3_level = QLabel("TP3 (Risk 1:3): -")
        self.lbl_tp3_level.setStyleSheet("font-size: 11px; padding: 4px; background-color: #d32f2f; color: white; border-radius: 3px;")
        self.lbl_tp3_badge = QLabel("NOT_REACHED")
        self.lbl_tp3_badge.setStyleSheet("font-size: 9px; padding: 2px 4px; background-color: #555; color: white; border-radius: 3px;")
        tp3_h_layout.addWidget(self.lbl_tp3_level)
        tp3_h_layout.addWidget(self.lbl_tp3_badge)
        tp3_h_layout.addStretch()
        tp_layout.addLayout(tp3_h_layout)
        
        # Validation error badge (HIGH: TP_VALUES_INCONSISTENT mitigation)
        self.lbl_tp_config_error = QLabel("")
        self.lbl_tp_config_error.setStyleSheet("font-size: 10px; padding: 4px; background-color: #b71c1c; color: white; border-radius: 3px;")
        self.lbl_tp_config_error.setVisible(False)
        tp_layout.addWidget(self.lbl_tp_config_error)
        
        # TP Progress bars (MEDIUM: TP_PROGRESS_BARS_STATIC mitigation)
        self.progress_tp1 = QLabel("TP1 Progress: 0%")
        self.progress_tp1.setStyleSheet("font-size: 9px; padding: 2px; color: #aaa;")
        tp_layout.addWidget(self.progress_tp1)
        
        self.progress_tp2 = QLabel("TP2 Progress: 0%")
        self.progress_tp2.setStyleSheet("font-size: 9px; padding: 2px; color: #aaa;")
        tp_layout.addWidget(self.progress_tp2)
        
        # Add scroll area for TP levels if needed
        tp_scroll = QScrollArea()
        tp_scroll.setWidget(tp_group)
        tp_scroll.setWidgetResizable(True)
        tp_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        layout.addWidget(tp_scroll)
        
        # RESPONSIVE_LAYOUT: TP Decision Panels (accordion, side-by-side for TP1/TP2)
        self.accordion_tp_panels = QWidget()
        # Arrange TP1 and TP2 panels side-by-side for clearer comparison
        accordion_layout = QHBoxLayout()
        accordion_layout.setContentsMargins(0, 0, 0, 0)
        accordion_layout.setSpacing(6)
        
        # TP1 Decision Panel (collapsible)
        tp1_decision_group = QGroupBox("TP1 Exit Decision")
        tp1_decision_group.setMinimumHeight(120)  # FIX: TP_PANEL_VERTICAL_CLIPPING - Ensure minimum visible content
        tp1_decision_group.setMaximumHeight(16777215)  # FIX: Allow expansion to content, no max clipping
        tp1_decision_group.setCheckable(False)  # Show expand/collapse arrow
        tp1_decision_group.setFlat(False)
        tp1_decision_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tp1_decision_layout = QVBoxLayout()
        tp1_decision_layout.setContentsMargins(6, 6, 6, 6)
        tp1_decision_layout.setSpacing(4)
        
        # RESPONSIVE_LAYOUT: Compress labels on small screens (font size 9px)
        # FIX: EMPTY_STATE_FIELDS - Use 'Waiting' instead of '-'
        # FIX: NO_VISUAL_STATE_HIERARCHY - Add state badge with color
        tp1_state_layout = QHBoxLayout()
        self.lbl_tp1_state = QLabel("State: Waiting")
        self.lbl_tp1_state.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
        self.lbl_tp1_state_badge = QLabel("[IDLE]")
        self.lbl_tp1_state_badge.setStyleSheet("font-size: 8px; padding: 2px 6px; background-color: #555; color: #aaa; border-radius: 3px;")
        tp1_state_layout.addWidget(self.lbl_tp1_state)
        tp1_state_layout.addWidget(self.lbl_tp1_state_badge)
        tp1_state_layout.addStretch()
        tp1_decision_layout.addLayout(tp1_state_layout)
        
        # FIX: EMPTY_STATE_FIELDS - Use 'Waiting' instead of '-'
        self.lbl_post_tp1_decision = QLabel("Decision: Waiting")
        self.lbl_post_tp1_decision.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
        tp1_decision_layout.addWidget(self.lbl_post_tp1_decision)
        
        # FIX: EMPTY_STATE_FIELDS - Use meaningful text instead of '-'
        self.lbl_tp1_exit_reason = QLabel("Reason: Awaiting evaluation")
        self.lbl_tp1_exit_reason.setStyleSheet("font-size: 8px; padding: 2px; min-height: 14px; color: #888;")
        self.lbl_tp1_exit_reason.setWordWrap(True)
        tp1_decision_layout.addWidget(self.lbl_tp1_exit_reason)
        
        self.lbl_bars_after_tp1 = QLabel("Bars After TP1: 0")
        self.lbl_bars_after_tp1.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
        tp1_decision_layout.addWidget(self.lbl_bars_after_tp1)
        
        # HIGH: EXIT_REASON_NOT_VISIBLE_LIVE - Next exit condition (responsive)
        # FIX: NEXT_EXIT_LINE_TOO_SUBTLE - Add icon and more prominent styling
        self.lbl_tp1_next_exit = QLabel("Next Exit: Awaiting TP1 trigger")
        self.lbl_tp1_next_exit.setStyleSheet("font-size: 9px; padding: 4px 6px; background-color: #1b1b1b; color: #1b5e20; border-left: 3px solid #1b5e20; border-radius: 2px; font-weight: bold;")
        self.lbl_tp1_next_exit.setWordWrap(True)
        tp1_decision_layout.addWidget(self.lbl_tp1_next_exit)
        tp1_decision_layout.addStretch()
        
        tp1_decision_group.setLayout(tp1_decision_layout)
        accordion_layout.addWidget(tp1_decision_group)
        
        # TP2 Decision Panel (collapsible)
        tp2_decision_group = QGroupBox("TP2 Exit Decision")
        tp2_decision_group.setMinimumHeight(140)  # FIX: TP_PANEL_VERTICAL_CLIPPING - Ensure minimum visible content
        tp2_decision_group.setMaximumHeight(16777215)  # FIX: Allow expansion to content, no max clipping
        tp2_decision_group.setCheckable(False)
        tp2_decision_group.setFlat(False)
        tp2_decision_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tp2_decision_layout = QVBoxLayout()
        tp2_decision_layout.setContentsMargins(6, 6, 6, 6)
        tp2_decision_layout.setSpacing(4)
        
        # RESPONSIVE_LAYOUT: Compress labels on small screens
        # FIX: EMPTY_STATE_FIELDS - Use 'Waiting' instead of '-'
        # FIX: NO_VISUAL_STATE_HIERARCHY - Add state badge with color
        tp2_state_layout = QHBoxLayout()
        self.lbl_tp2_state = QLabel("State: Waiting")
        self.lbl_tp2_state.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
        self.lbl_tp2_state_badge = QLabel("[IDLE]")
        self.lbl_tp2_state_badge.setStyleSheet("font-size: 8px; padding: 2px 6px; background-color: #555; color: #aaa; border-radius: 3px;")
        tp2_state_layout.addWidget(self.lbl_tp2_state)
        tp2_state_layout.addWidget(self.lbl_tp2_state_badge)
        tp2_state_layout.addStretch()
        tp2_decision_layout.addLayout(tp2_state_layout)
        
        # FIX: EMPTY_STATE_FIELDS - Use 'Waiting' instead of '-'
        self.lbl_post_tp2_decision = QLabel("Decision: Waiting")
        self.lbl_post_tp2_decision.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
        tp2_decision_layout.addWidget(self.lbl_post_tp2_decision)
        
        # FIX: EMPTY_STATE_FIELDS - Use meaningful text instead of '-'
        self.lbl_tp2_exit_reason = QLabel("Reason: Awaiting evaluation")
        self.lbl_tp2_exit_reason.setStyleSheet("font-size: 8px; padding: 2px; min-height: 14px; color: #888;")
        self.lbl_tp2_exit_reason.setWordWrap(True)
        tp2_decision_layout.addWidget(self.lbl_tp2_exit_reason)
        
        self.lbl_bars_after_tp2 = QLabel("Bars After TP2: 0")
        self.lbl_bars_after_tp2.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
        tp2_decision_layout.addWidget(self.lbl_bars_after_tp2)
        
        # FIX: EMPTY_STATE_FIELDS - Use meaningful text instead of '-'
        self.lbl_trailing_sl = QLabel("Trailing SL: Inactive")
        self.lbl_trailing_sl.setStyleSheet("font-size: 8px; padding: 2px; min-height: 14px; color: #888;")
        self.lbl_trailing_sl.setWordWrap(True)
        tp2_decision_layout.addWidget(self.lbl_trailing_sl)
        
        # HIGH: EXIT_REASON_NOT_VISIBLE_LIVE - Next exit condition (responsive)
        # FIX: NEXT_EXIT_LINE_TOO_SUBTLE - Add icon and more prominent styling
        self.lbl_tp2_next_exit = QLabel("Next Exit: Awaiting TP2 trigger")
        self.lbl_tp2_next_exit.setStyleSheet("font-size: 9px; padding: 4px 6px; background-color: #1b1b1b; color: #f57c00; border-left: 3px solid #f57c00; border-radius: 2px; font-weight: bold;")
        self.lbl_tp2_next_exit.setWordWrap(True)
        tp2_decision_layout.addWidget(self.lbl_tp2_next_exit)
        tp2_decision_layout.addStretch()
        
        tp2_decision_group.setLayout(tp2_decision_layout)
        accordion_layout.addWidget(tp2_decision_group)
        accordion_layout.addStretch()
        
        self.accordion_tp_panels.setLayout(accordion_layout)
        layout.addWidget(self.accordion_tp_panels)
        
        # Finish scrollable content layout
        layout.addStretch()
        scroll_widget.setLayout(layout)
        scroll_area.setWidget(scroll_widget)
        outer_layout.addWidget(scroll_area)
        
        # RESPONSIVE_LAYOUT: Action buttons section (sticky at bottom, responsive stacking)
        btn_container = QWidget()
        btn_container_layout = QVBoxLayout()
        btn_container_layout.setContentsMargins(8, 6, 8, 8)
        btn_container_layout.setSpacing(6)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        
        self.btn_close_position = QPushButton("Close Selected Position")
        self.btn_close_position.setEnabled(False)
        self.btn_close_position.clicked.connect(self._on_close_position_clicked)
        self.btn_close_position.setMinimumHeight(32)
        btn_layout.addWidget(self.btn_close_position)
        
        self.btn_refresh_positions = QPushButton("Refresh")
        self.btn_refresh_positions.clicked.connect(self._refresh_positions_table)
        self.btn_refresh_positions.setMinimumHeight(32)
        btn_layout.addWidget(self.btn_refresh_positions)
        
        btn_container_layout.addLayout(btn_layout)
        btn_container.setLayout(btn_container_layout)
        btn_container.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-top: 1px solid #444;
            }
        """)
        
        # Add action buttons AFTER scroll area (sticky at bottom)
        outer_layout.addWidget(btn_container)
        
        widget.setLayout(outer_layout)
        return widget
    
    def _create_history_tab(self) -> QWidget:
        """Create the trade history tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Statistics
        stats_group = QGroupBox("Performance Statistics")
        stats_layout = QVBoxLayout()

        # Trading metrics
        trading_layout = QGridLayout()
        trading_layout.setSpacing(6)
        self.lbl_total_trades = QLabel("Total Trades: 0")
        self.lbl_win_rate = QLabel("Win Rate: 0%")
        self.lbl_total_profit = QLabel("Total Profit: $0.00")
        self.lbl_avg_win = QLabel("Avg Win: $0.00")
        self.lbl_avg_loss = QLabel("Avg Loss: $0.00")
        self.lbl_profit_factor = QLabel("Profit Factor: 0.00")
        self.lbl_last_trade = QLabel("Last Trade: --")

        trading_layout.addWidget(self.lbl_total_trades, 0, 0)
        trading_layout.addWidget(self.lbl_win_rate, 0, 1)
        trading_layout.addWidget(self.lbl_total_profit, 1, 0)
        trading_layout.addWidget(self.lbl_profit_factor, 1, 1)
        trading_layout.addWidget(self.lbl_avg_win, 2, 0)
        trading_layout.addWidget(self.lbl_avg_loss, 2, 1)
        trading_layout.addWidget(self.lbl_last_trade, 3, 0, 1, 2)

        stats_layout.addLayout(trading_layout)

        # System dashboard
        system_group = QGroupBox("Live System Dashboard")
        system_layout = QVBoxLayout()
        self.lbl_uptime = QLabel("Uptime: 0s")
        self.lbl_alerts = QLabel("Alerts: 0 critical / 0 warn / 0 info")
        self.lbl_queue_stats = QLabel("UI Queue: pending 0/0, posted 0, processed 0, dropped 0")
        self.lbl_perf_snapshot = QLabel("Performance: waiting for data")
        self.lbl_perf_snapshot.setWordWrap(True)

        system_layout.addWidget(self.lbl_uptime)
        system_layout.addWidget(self.lbl_alerts)
        system_layout.addWidget(self.lbl_queue_stats)
        system_layout.addWidget(self.lbl_perf_snapshot)
        system_group.setLayout(system_layout)

        stats_layout.addWidget(system_group)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Info label for column clarity
        info_label = QLabel("ℹ️  Column 6 shows EXIT REASON (text). Column 7 shows TP3 price (number).")
        info_label.setStyleSheet("color: #2563eb; font-weight: bold; padding: 8px;")
        layout.addWidget(info_label)
        
        # Trade history table
        self.table_history = QTableWidget()
        self.table_history.setColumnCount(8)
        self.table_history.setHorizontalHeaderLabels([
            "Entry Time", "Exit Time", "Entry Price", "Exit Price", 
            "Profit", "Exit Reason", "TP3 Level", "Volume"
        ])
        layout.addWidget(self.table_history)
        
        widget.setLayout(layout)
        return widget
    
    def _create_logs_tab(self) -> QWidget:
        """Create the logs display tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setFont(QFont("Courier", 9))
        layout.addWidget(self.txt_logs)
        
        # Clear logs button
        btn_clear = QPushButton("Clear Logs")
        btn_clear.clicked.connect(lambda: self.txt_logs.clear())
        layout.addWidget(btn_clear)
        
        widget.setLayout(layout)
        return widget
    
    def _create_settings_tab(self) -> QWidget:
        """Create the settings configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Strategy settings
        strategy_group = QGroupBox("Strategy Parameters")
        strategy_layout = QVBoxLayout()
        
        # Risk %
        risk_layout = QHBoxLayout()
        risk_layout.addWidget(QLabel("Risk per Trade (%):"))
        self.spin_risk = QDoubleSpinBox()
        self.spin_risk.setRange(0.1, 10.0)
        self.spin_risk.setValue(1.0)
        self.spin_risk.setSingleStep(0.1)
        risk_layout.addWidget(self.spin_risk)
        strategy_layout.addLayout(risk_layout)
        
        # ATR multiplier
        atr_layout = QHBoxLayout()
        atr_layout.addWidget(QLabel("ATR Multiplier (SL):"))
        self.spin_atr = QDoubleSpinBox()
        self.spin_atr.setRange(0.5, 5.0)
        self.spin_atr.setValue(2.0)
        self.spin_atr.setSingleStep(0.1)
        atr_layout.addWidget(self.spin_atr)
        strategy_layout.addLayout(atr_layout)
        
        # Risk/Reward Long
        rr_long_layout = QHBoxLayout()
        rr_long_layout.addWidget(QLabel("Risk/Reward Ratio (LONG):"))
        self.spin_rr_long = QDoubleSpinBox()
        self.spin_rr_long.setRange(1.0, 10.0)
        self.spin_rr_long.setValue(2.0)
        self.spin_rr_long.setSingleStep(0.1)
        rr_long_layout.addWidget(self.spin_rr_long)
        strategy_layout.addLayout(rr_long_layout)
        
        # Risk/Reward Short
        rr_short_layout = QHBoxLayout()
        rr_short_layout.addWidget(QLabel("Risk/Reward Ratio (SHORT):"))
        self.spin_rr_short = QDoubleSpinBox()
        self.spin_rr_short.setRange(1.0, 10.0)
        self.spin_rr_short.setValue(2.0)
        self.spin_rr_short.setSingleStep(0.1)
        rr_short_layout.addWidget(self.spin_rr_short)
        strategy_layout.addLayout(rr_short_layout)
        
        # Cooldown
        cooldown_layout = QHBoxLayout()
        cooldown_layout.addWidget(QLabel("Cooldown (hours):"))
        self.spin_cooldown = QSpinBox()
        self.spin_cooldown.setRange(1, 168)
        self.spin_cooldown.setValue(24)
        cooldown_layout.addWidget(self.spin_cooldown)
        strategy_layout.addLayout(cooldown_layout)
        
        # Pyramiding
        pyramiding_layout = QHBoxLayout()
        pyramiding_layout.addWidget(QLabel("Pyramiding (max positions):"))
        self.spin_pyramiding = QSpinBox()
        self.spin_pyramiding.setRange(1, 10)
        self.spin_pyramiding.setValue(1)
        pyramiding_layout.addWidget(self.spin_pyramiding)
        strategy_layout.addLayout(pyramiding_layout)
        
        # Momentum filter checkbox
        self.chk_momentum = QCheckBox("Enable Momentum Filter (ATR-based)")
        self.chk_momentum.setChecked(True)
        strategy_layout.addWidget(self.chk_momentum)
        
        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)
        
        # Save settings button
        btn_save = QPushButton("Save Settings")
        btn_save.clicked.connect(self._on_save_settings)
        layout.addWidget(btn_save)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def _load_settings_from_config(self):
        """Load settings from config into UI controls."""
        if not self.config:
            return
        
        try:
            # Load mode settings
            self.chk_demo.setChecked(self.config.get('mode.demo_mode', True))
            self.chk_auto.setChecked(self.config.get('mode.auto_trade', False))
            
            # Load strategy settings
            self.spin_risk.setValue(self.config.get('risk.risk_percent', 1.0))
            self.spin_atr.setValue(self.config.get('strategy.atr_multiplier_stop', 2.0))
            self.spin_rr_long.setValue(self.config.get('strategy.risk_reward_ratio_long', 2.0))
            self.spin_rr_short.setValue(self.config.get('strategy.risk_reward_ratio_short', 2.0))
            self.spin_cooldown.setValue(self.config.get('strategy.cooldown_hours', 24))
            self.spin_pyramiding.setValue(self.config.get('strategy.pyramiding', 1))
            self.chk_momentum.setChecked(self.config.get('strategy.enable_momentum_filter', True))
            
            self.logger.info("Settings loaded from config")
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
    
    def _apply_dark_theme(self):
        """Apply dark theme to the application."""
        dark_stylesheet = """
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555555;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
            }
            QPushButton:disabled {
                background-color: #2b2b2b;
                color: #666666;
            }
            QTextEdit, QTableWidget {
                background-color: #1e1e1e;
                border: 1px solid #555555;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: white;
                padding: 8px 16px;
                border: 1px solid #555555;
            }
            QTabBar::tab:selected {
                background-color: #2b2b2b;
            }
        """
        self.setStyleSheet(dark_stylesheet)
    
    # Event handlers
    
    @Slot()
    def _on_toggle_clicked(self):
        """Handle toggle button click (Start/Stop)."""
        if not self.is_running:
            # Start trading
            self.is_running = True
            self.btn_toggle.setText("Stop Trading")
            self.btn_toggle.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 10px;")
            self.lbl_trading.setText("Trading: Active")
            self.lbl_trading.setStyleSheet("color: green; font-weight: bold;")
            self.start_requested.emit()
            self.log_message("Trading started")
        else:
            # Stop trading
            self.is_running = False
            self.btn_toggle.setText("Start Trading")
            self.btn_toggle.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 10px;")
            self.lbl_trading.setText("Trading: Stopped")
            self.lbl_trading.setStyleSheet("color: red; font-weight: bold;")
            self.stop_requested.emit()
            self.log_message("Trading stopped")
    
    @Slot()
    def _on_restart_clicked(self):
        """Handle restart button click."""
        import sys
        import os
        from PySide6.QtWidgets import QMessageBox
        
        # Confirm restart
        reply = QMessageBox.question(
            self, 
            'Restart Application',
            'Are you sure you want to restart the application?\n\nAny unsaved settings will be preserved.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.log_message("Restarting application...")
            # Get the Python executable and script path
            python = sys.executable
            script = sys.argv[0]
            
            # Close current instance
            self.close()
            
            # Restart using os.execv (replaces current process)
            os.execv(python, [python] + sys.argv)
    
    @Slot(int)
    def _on_auto_trade_changed(self, state):
        """Handle Auto Trade checkbox change."""
        enabled = bool(state)
        self.auto_trade_changed.emit(enabled)
        status = "enabled" if enabled else "disabled"
        self.log_message(f"Auto Trade {status}")
    
    @Slot(int)
    def _on_demo_mode_changed(self, state):
        """Handle Demo Mode checkbox change."""
        enabled = bool(state)
        if not enabled:
            # Warn about live trading
            self.log_message("WARNING: Demo Mode disabled - LIVE TRADING ACTIVE!")
        else:
            self.log_message("Demo Mode enabled - Safe trading on demo account")
        
        if self.config:
            self.config.set('mode.demo_mode', enabled)
            self.config.save_config()
    
    @Slot()
    def _on_mode_toggle_clicked(self):
        """Handle mode toggle button click (DEVELOPMENT/LIVE)."""
        from pathlib import Path
        import yaml
        
        # Load current mode from config
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            current_mode = config_data.get('runtime', {}).get('mode', 'DEVELOPMENT')
            new_mode = 'LIVE' if current_mode == 'DEVELOPMENT' else 'DEVELOPMENT'
            
            # Show confirmation dialog
            msg = f"Switch from {current_mode} to {new_mode} mode?\n\n"
            if new_mode == 'LIVE':
                msg += "WARNING: LIVE mode enables full automation.\n"
                msg += "On REAL accounts, confirmation will be required.\n\n"
            else:
                msg += "DEVELOPMENT mode is safer.\n"
                msg += "Auto-trading on REAL accounts will be blocked.\n\n"
            msg += "Application will restart after switch."
            
            reply = QMessageBox.question(
                self,
                'Switch Runtime Mode',
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Update config
                if 'runtime' not in config_data:
                    config_data['runtime'] = {}
                config_data['runtime']['mode'] = new_mode
                
                # Save config
                with open(config_path, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False)
                
                self.log_message(f"Mode switched to {new_mode}. Restarting...")
                
                # Restart application
                import sys
                import os
                python = sys.executable
                script = sys.argv[0]
                self.close()
                os.execv(python, [python] + sys.argv)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to switch mode: {e}")
            self.log_message(f"Error switching mode: {e}")
    
    @Slot()
    def _on_close_position_clicked(self):
        """Handle manual position close - closes selected position from table."""
        selected_rows = self.table_positions.selectedIndexes()
        
        if not selected_rows:
            self.log_message("Error: Please select a position to close")
            return
        
        # Get the row number
        row = selected_rows[0].row()
        
        # Get ticket from first column
        ticket_item = self.table_positions.item(row, 0)
        if not ticket_item:
            self.log_message("Error: Could not retrieve ticket")
            return
        
        ticket = ticket_item.text()
        
        # Emit signal to close this specific position
        self.log_message(f"Attempting to close position {ticket}...")
        
        # Store the ticket to close for the controller
        if hasattr(self, '_controller') and self._controller:
            self._controller.manual_close_position(ticket)
        else:
            self.log_message("Error: Controller not available")

    @Slot(int, int)
    def _on_position_cell_clicked(self, row: int, column: int):
        """Handle position cell click - show TP levels or close position."""
        # If clicking action column, close position
        if column == 10:
            ticket_item = self.table_positions.item(row, 0)
            if not ticket_item:
                self.log_message("Error: Could not retrieve ticket")
                return
            ticket = ticket_item.text()
            self.log_message(f"Attempting to close position {ticket}...")
            if hasattr(self, '_controller') and self._controller:
                self._controller.manual_close_position(ticket)
            else:
                self.log_message("Error: Controller not available")
        else:
            # Show TP levels for the selected position
            self._show_tp_levels_for_row(row)
    
    def _show_tp_levels_for_row(self, row: int):
        """Display TP levels for selected position row."""
        try:
            # Get position data from state manager
            if hasattr(self, '_controller') and self._controller:
                all_positions = self._controller.state_manager.get_all_positions()
                if row < len(all_positions):
                    position = all_positions[row]
                    
                    # Display TP levels with both price and cash targets
                    tp1_cash = position.get('tp1_cash', 0)
                    tp2_cash = position.get('tp2_cash', 0)
                    tp3_cash = position.get('tp3_cash', 0)
                    tp1_price = position.get('tp1_price')
                    tp2_price = position.get('tp2_price')
                    tp3_price = position.get('tp3_price')
                    
                    tp1_text = f"{tp1_price:.2f}" if tp1_price is not None else "-"
                    tp2_text = f"{tp2_price:.2f}" if tp2_price is not None else "-"
                    tp3_text = f"{tp3_price:.2f}" if tp3_price is not None else "-"

                    self.lbl_tp1_level.setText(f"TP1: {tp1_text} | Cash: {tp1_cash:.2f} USD")
                    self.lbl_tp2_level.setText(f"TP2: {tp2_text} | Cash: {tp2_cash:.2f} USD")
                    self.lbl_tp3_level.setText(f"TP3: {tp3_text} | Cash: {tp3_cash:.2f} USD")
                    
                    # Display TP1 exit decision state
                    # HIGH: TP_VALUES_INCONSISTENT - Validate TP monotonicity
                    tp_config_valid = True
                    if tp1_price is not None and tp2_price is not None and tp3_price is not None:
                        direction = position.get('direction', 1)
                        if direction == 1:  # LONG
                            if not (tp1_price < tp2_price < tp3_price):
                                tp_config_valid = False
                                self.lbl_tp_config_error.setText(f"INVALID TP CONFIG: {tp1_price:.2f} < {tp2_price:.2f} < {tp3_price:.2f}")
                                self.lbl_tp_config_error.setVisible(True)
                        else:  # SHORT
                            if not (tp1_price > tp2_price > tp3_price):
                                tp_config_valid = False
                                self.lbl_tp_config_error.setText(f"INVALID TP CONFIG: {tp1_price:.2f} > {tp2_price:.2f} > {tp3_price:.2f}")
                                self.lbl_tp_config_error.setVisible(True)
                    
                    if tp_config_valid:
                        self.lbl_tp_config_error.setVisible(False)
                    
                    # MEDIUM: TP_PROGRESS_BARS_STATIC - Calculate progress ratios
                    current_price = position.get('price_current', position.get('entry_price', 0))
                    entry_price = position.get('entry_price', current_price)
                    
                    if tp1_price is not None and entry_price != current_price:
                        tp1_progress = ((current_price - entry_price) / (tp1_price - entry_price)) if (tp1_price - entry_price) != 0 else 0
                        tp1_progress = max(0.0, min(1.0, tp1_progress))  # Clamp to [0, 1]
                        self.progress_tp1.setText(f"TP1 Progress: {int(tp1_progress * 100)}%")
                    else:
                        self.progress_tp1.setText("TP1 Progress: 0%")
                    
                    if tp2_price is not None and entry_price != current_price:
                        tp2_progress = ((current_price - entry_price) / (tp2_price - entry_price)) if (tp2_price - entry_price) != 0 else 0
                        tp2_progress = max(0.0, min(1.0, tp2_progress))  # Clamp to [0, 1]
                        self.progress_tp2.setText(f"TP2 Progress: {int(tp2_progress * 100)}%")
                    else:
                        self.progress_tp2.setText("TP2 Progress: 0%")
                    
                    # Update TP state badges (TP_STATE_BADGES component)
                    tp_state = position.get('tp_state', 'IN_TRADE')
                    tp_state_badge_map = {
                        'IN_TRADE': 'NOT_REACHED',
                        'TP1_REACHED': 'TOUCHED',
                        'TP2_REACHED': 'ACTIVE_MANAGEMENT',
                        'TP3_REACHED': 'EXIT_ARMED',
                        'EXIT_EXECUTED': 'COMPLETED'
                    }
                    tp1_badge_text = tp_state_badge_map.get(tp_state, 'NOT_REACHED')
                    tp2_badge_text = tp_state_badge_map.get(tp_state, 'NOT_REACHED')
                    tp3_badge_text = tp_state_badge_map.get(tp_state, 'NOT_REACHED')
                    
                    self.lbl_tp1_badge.setText(tp1_badge_text)
                    self.lbl_tp2_badge.setText(tp2_badge_text)
                    self.lbl_tp3_badge.setText(tp3_badge_text)
                    
                    # Color badges by state
                    badge_colors = {
                        'NOT_REACHED': '#666666',
                        'TOUCHED': '#1b5e20',
                        'ACTIVE_MANAGEMENT': '#f57c00',
                        'EXIT_ARMED': '#d32f2f',
                        'COMPLETED': '#0d47a1'
                    }
                    badge_color = badge_colors.get(tp1_badge_text, '#666666')
                    self.lbl_tp1_badge.setStyleSheet(f"font-size: 9px; padding: 2px 4px; background-color: {badge_color}; color: white; border-radius: 3px;")
                    self.lbl_tp2_badge.setStyleSheet(f"font-size: 9px; padding: 2px 4px; background-color: {badge_color}; color: white; border-radius: 3px;")
                    self.lbl_tp3_badge.setStyleSheet(f"font-size: 9px; padding: 2px 4px; background-color: {badge_color}; color: white; border-radius: 3px;")
                    
                    # HIGH: TP_DECISION_PANELS_EMPTY - Bind to TP engine state with defaults
                    post_tp1_decision = position.get('post_tp1_decision', 'HOLD')  # Default to HOLD (HIGH mitigation)
                    tp1_exit_reason = position.get('tp1_exit_reason', 'Awaiting TP1 trigger')  # Default reason (HIGH mitigation)
                    bars_after_tp1 = position.get('bars_held_after_tp1', 0)
                    
                    # FIX: NO_VISUAL_STATE_HIERARCHY - Update state badges with colors based on tp_state
                    state_badge_map = {
                        'IN_TRADE': ('[MONITORING]', '#1976d2', '#64b5f6'),        # Blue for monitoring
                        'TP1_REACHED': ('[TRIGGERED]', '#ff9800', '#ffb74d'),      # Orange for triggered
                        'TP2_REACHED': ('[TRIGGERED]', '#ff9800', '#ffb74d'),      # Orange for triggered
                        'COMPLETED': ('[EXITED]', '#388e3c', '#66bb6a'),           # Green for exited
                    }
                    
                    badge_text, badge_bg, badge_border = state_badge_map.get(tp_state, ('[IDLE]', '#555555', '#888888'))
                    self.lbl_tp1_state_badge.setText(badge_text)
                    self.lbl_tp1_state_badge.setStyleSheet(f"font-size: 8px; padding: 2px 6px; background-color: {badge_bg}; color: white; border-radius: 3px; border: 1px solid {badge_border};")
                    self.lbl_tp2_state_badge.setText(badge_text)
                    self.lbl_tp2_state_badge.setStyleSheet(f"font-size: 8px; padding: 2px 6px; background-color: {badge_bg}; color: white; border-radius: 3px; border: 1px solid {badge_border};")
                    
                    self.lbl_tp1_state.setText(f"State: {tp_state}")
                    self.lbl_post_tp1_decision.setText(f"Decision: {post_tp1_decision}")
                    self.lbl_tp1_exit_reason.setText(f"Reason: {tp1_exit_reason}")
                    self.lbl_bars_after_tp1.setText(f"Bars After TP1: {bars_after_tp1}")
                    
                    # Color code TP1 decision
                    if post_tp1_decision == 'HOLD':
                        self.lbl_post_tp1_decision.setStyleSheet("font-size: 10px; padding: 3px; background-color: #1b5e20; color: white;")
                    elif post_tp1_decision == 'WAIT_NEXT_BAR':
                        self.lbl_post_tp1_decision.setStyleSheet("font-size: 10px; padding: 3px; background-color: #f57c00; color: white;")
                    elif post_tp1_decision == 'EXIT_TRADE':
                        self.lbl_post_tp1_decision.setStyleSheet("font-size: 10px; padding: 3px; background-color: #d32f2f; color: white;")
                    else:
                        self.lbl_post_tp1_decision.setStyleSheet("font-size: 10px; padding: 3px;")
                    
                    # MEDIUM: TRAILING_SL_VISIBILITY_MISSING - Show trailing SL status
                    post_tp2_decision = position.get('post_tp2_decision', 'HOLD')  # Default to HOLD (HIGH mitigation)
                    tp2_exit_reason = position.get('tp2_exit_reason', 'Awaiting TP2 trigger')  # Default reason (HIGH mitigation)
                    bars_after_tp2 = position.get('bars_held_after_tp2', 0)
                    trailing_sl_enabled = position.get('trailing_sl_enabled', False)
                    trailing_sl = position.get('trailing_sl_level')
                    
                    self.lbl_tp2_state.setText(f"State: {tp_state}")
                    self.lbl_post_tp2_decision.setText(f"Decision: {post_tp2_decision}")
                    self.lbl_tp2_exit_reason.setText(f"Reason: {tp2_exit_reason}")
                    self.lbl_bars_after_tp2.setText(f"Bars After TP2: {bars_after_tp2}")
                    
                    # MEDIUM: TRAILING_SL_VISIBILITY_MISSING - Enhanced display
                    if trailing_sl_enabled and trailing_sl is not None:
                        self.lbl_trailing_sl.setText(f"Trailing SL: ACTIVE @ {trailing_sl:.2f}")
                        self.lbl_trailing_sl.setStyleSheet("font-size: 10px; padding: 3px; background-color: #1b5e20; color: white;")
                    elif trailing_sl is not None:
                        self.lbl_trailing_sl.setText(f"Trailing SL: {trailing_sl:.2f} (INACTIVE)")
                        self.lbl_trailing_sl.setStyleSheet("font-size: 10px; padding: 3px; color: #aaa;")
                    else:
                        self.lbl_trailing_sl.setText("Trailing SL: Not set")
                        self.lbl_trailing_sl.setStyleSheet("font-size: 10px; padding: 3px; color: #aaa;")
                    
                    # Color code TP2 decision
                    if post_tp2_decision == 'HOLD':
                        self.lbl_post_tp2_decision.setStyleSheet("font-size: 10px; padding: 3px; background-color: #1b5e20; color: white;")
                    elif post_tp2_decision == 'WAIT_NEXT_BAR':
                        self.lbl_post_tp2_decision.setStyleSheet("font-size: 10px; padding: 3px; background-color: #f57c00; color: white;")
                    elif post_tp2_decision == 'EXIT_TRADE':
                        self.lbl_post_tp2_decision.setStyleSheet("font-size: 10px; padding: 3px; background-color: #d32f2f; color: white;")
                    else:
                        self.lbl_post_tp2_decision.setStyleSheet("font-size: 10px; padding: 3px;")
                    
                    # HIGH: EXIT_REASON_NOT_VISIBLE_LIVE - Populate next exit condition fields
                    tp_state = position.get('tp_state', 'IN_TRADE')
                    
                    # TP1 next exit condition
                    if tp_state == 'IN_TRADE':
                        tp1_next_exit = f"Exit on TP1 reach: {tp1_price:.2f} (ATR retrace > 0.25*ATR)"
                        self.lbl_tp1_next_exit.setStyleSheet("font-size: 10px; padding: 3px; background-color: #333; color: #1b5e20;")
                    elif tp_state == 'TP1_REACHED':
                        tp1_next_exit = f"TP1 REACHED @ {tp1_price:.2f} - Managing to TP2"
                        self.lbl_tp1_next_exit.setStyleSheet("font-size: 10px; padding: 3px; background-color: #1b5e20; color: white;")
                    elif tp_state == 'TP2_REACHED':
                        tp1_next_exit = f"TP1 PASSED - Position managed by TP2 logic"
                        self.lbl_tp1_next_exit.setStyleSheet("font-size: 10px; padding: 3px; background-color: #f57c00; color: white;")
                    else:
                        tp1_next_exit = "Position closed"
                        self.lbl_tp1_next_exit.setStyleSheet("font-size: 10px; padding: 3px; background-color: #666; color: white;")
                    self.lbl_tp1_next_exit.setText(f"Next Exit: {tp1_next_exit}")
                    
                    # TP2 next exit condition
                    if tp_state == 'IN_TRADE':
                        tp2_next_exit = "Awaiting TP1 first"
                        self.lbl_tp2_next_exit.setStyleSheet("font-size: 10px; padding: 3px; background-color: #333; color: #aaa;")
                    elif tp_state == 'TP1_REACHED':
                        tp2_next_exit = f"Exit on TP2 reach: {tp2_price:.2f} (ATR retrace > 0.2*ATR)"
                        self.lbl_tp2_next_exit.setStyleSheet("font-size: 10px; padding: 3px; background-color: #333; color: #f57c00;")
                    elif tp_state == 'TP2_REACHED':
                        tp2_next_exit = f"TP2 REACHED @ {tp2_price:.2f} - Managing to TP3"
                        self.lbl_tp2_next_exit.setStyleSheet("font-size: 10px; padding: 3px; background-color: #f57c00; color: white;")
                    else:
                        tp2_next_exit = "Position closed"
                        self.lbl_tp2_next_exit.setStyleSheet("font-size: 10px; padding: 3px; background-color: #666; color: white;")
                    self.lbl_tp2_next_exit.setText(f"Next Exit: {tp2_next_exit}")
        except Exception as e:
            self.logger.error(f"Error showing TP levels: {e}")

    
    @Slot()
    def _on_save_settings(self):
        """Handle save settings button."""
        settings = {
            'risk_percent': self.spin_risk.value(),
            'atr_multiplier': self.spin_atr.value(),
            'risk_reward_ratio_long': self.spin_rr_long.value(),
            'risk_reward_ratio_short': self.spin_rr_short.value(),
            'cooldown_hours': self.spin_cooldown.value(),
            'pyramiding': self.spin_pyramiding.value(),
            'enable_momentum_filter': self.chk_momentum.isChecked()
        }
        self.settings_changed.emit(settings)
        self.log_message("Settings saved")
    
    # Update methods (called from controller)
    
    def update_runtime_mode_display(self, runtime_manager):
        """
        Update runtime mode display with current mode and automation status.
        
        Args:
            runtime_manager: RuntimeModeManager instance
        """
        # Update mode toggle button
        if runtime_manager.runtime_mode.value == "DEVELOPMENT":
            self.btn_mode_toggle.setText("DEVELOPMENT Mode")
            self.btn_mode_toggle.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        else:
            self.btn_mode_toggle.setText("LIVE Mode")
            self.btn_mode_toggle.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold; padding: 8px;")
        
        # Update account type display
        self.lbl_account_type.setText(runtime_manager.get_account_display_text())
        
        # Update auto-trading permission status
        can_trade, reason = runtime_manager.can_auto_trade()
        if can_trade:
            self.lbl_auto_trading_permission.setText("Auto-Trading Permission: ALLOWED")
            self.lbl_auto_trading_permission.setStyleSheet("color: white; font-size: 11px; padding: 4px; font-weight: bold; background-color: #1b5e20; border-radius: 3px;")
            self.lbl_auto_trading_permission.setToolTip("Auto trading is permitted by system policy")
        else:
            self.lbl_auto_trading_permission.setText("Auto-Trading Permission: BLOCKED")
            self.lbl_auto_trading_permission.setStyleSheet("color: white; font-size: 11px; padding: 4px; font-weight: bold; background-color: #b71c1c; border-radius: 3px;")
            self.lbl_auto_trading_permission.setToolTip(f"Reason: {reason}")
    
    def update_connection_status(self, connected: bool, account_info: dict = None):
        """Update connection status display."""
        self.is_connected = connected
        if connected:
            self.lbl_connection.setText("Connection: Connected")
            self.lbl_connection.setStyleSheet("color: green; font-weight: bold;")
            if account_info:
                self.lbl_account.setText(f"Account: {account_info.get('login', '-')}")
                self.lbl_equity.setText(f"Equity: ${account_info.get('equity', 0):.2f}")
                self.lbl_balance.setText(f"Balance: ${account_info.get('balance', 0):.2f}")
        else:
            self.lbl_connection.setText("Connection: Disconnected")
            self.lbl_connection.setStyleSheet("color: red; font-weight: bold;")
    
    def update_market_data(self, price: float, indicators: dict):
        """Update market data display."""
        price_text = self._format_number(price, precision=2)
        self.lbl_price.setText(f"Price: {price_text}")

        indicators = indicators or {}
        if (
            isinstance(indicators, dict)
            and "indicators" in indicators
            and not any(key in indicators for key in ("ema50", "ema200", "atr14", "atr"))
        ):
            indicators = indicators.get("indicators") or {}

        ema50 = indicators.get("ema50")
        ema200 = indicators.get("ema200")
        atr14 = indicators.get("atr14")
        if atr14 is None:
            atr14 = indicators.get("atr")

        self.lbl_ema50.setText(f"EMA 50: {self._format_number(ema50, precision=2)}")
        self.lbl_ema200.setText(f"EMA 200: {self._format_number(ema200, precision=2)}")
        self.lbl_atr.setText(f"ATR 14: {self._format_number(atr14, precision=2)}")
    
    def update_pattern_status(self, pattern: dict = None):
        """Update pattern detection display."""
        if pattern and pattern.get('pattern_valid'):
            self.lbl_pattern_status.setText("Status: Double Bottom Detected")
            self.lbl_pattern_status.setStyleSheet("color: green; font-weight: bold;")
            
            left_low = pattern.get('left_low') or {}
            neckline = pattern.get('neckline') or {}
            right_low = pattern.get('right_low') or {}
            details = f"Left Low: {self._format_number(left_low.get('price'), precision=2)}\n"
            details += f"Neckline: {self._format_number(neckline.get('price'), precision=2)}\n"
            details += f"Right Low: {self._format_number(right_low.get('price'), precision=2)}\n"
            details += f"Equality: {self._format_number_with_suffix(pattern.get('equality_diff_percent'), '%', precision=2)}"
            self.lbl_pattern_details.setText(details)
        else:
            self.lbl_pattern_status.setText("Status: No pattern")
            self.lbl_pattern_status.setStyleSheet("color: gray;")
            self.lbl_pattern_details.setText("Scanning for patterns...")
    
    def update_market_regime(self, regime_state: dict = None):
        """
        Update market regime display.
        
        Args:
            regime_state: Dict with regime, confidence, ema50_ema200_distance, price_ema50_distance
        """
        if not regime_state:
            regime_state = {'regime': 'RANGE', 'confidence': 0.0, 
                           'ema50_ema200_distance': 0.0, 'price_ema50_distance': 0.0}
        
        regime = regime_state.get('regime', 'RANGE')
        confidence_value = regime_state.get('confidence', 0.0)
        try:
            confidence_pct = float(confidence_value) * 100
        except (TypeError, ValueError):
            confidence_pct = None
        ema_distance = regime_state.get('ema50_ema200_distance')
        price_distance = regime_state.get('price_ema50_distance')
        
        # Color scheme based on regime type
        if regime == 'BULL':
            regime_color = "#4CAF50"  # Green
        elif regime == 'BEAR':
            regime_color = "#F44336"  # Red
        else:  # RANGE
            regime_color = "#9E9E9E"  # Gray
        
        # Update regime label
        self.lbl_regime.setText(f"Regime: {regime}")
        self.lbl_regime.setStyleSheet(f"color: {regime_color}; font-weight: bold; font-size: 12pt;")
        
        # Update confidence
        confidence_text = self._format_number_with_suffix(confidence_pct, "%", precision=1)
        self.lbl_regime_confidence.setText(f"Confidence: {confidence_text}")
        
        # Update distances
        ema_distance_text = self._format_number_with_suffix(ema_distance, "%", precision=2, signed=True)
        price_distance_text = self._format_number_with_suffix(price_distance, "%", precision=2, signed=True)
        self.lbl_ema_distance.setText(f"EMA Distance: {ema_distance_text}")
        self.lbl_price_distance.setText(f"Price Distance: {price_distance_text}")
    
    def update_entry_conditions(self, conditions: dict):
        """Update entry conditions display."""
        self._update_condition_label(self.lbl_cond_pattern, conditions.get('pattern_valid', False))
        self._update_condition_label(self.lbl_cond_breakout, conditions.get('breakout_confirmed', False))
        self._update_condition_label(self.lbl_cond_trend, conditions.get('above_ema50', False))
        self._update_condition_label(self.lbl_cond_momentum, conditions.get('has_momentum', False))
        self._update_condition_label(self.lbl_cond_cooldown, conditions.get('cooldown_ok', False))
    
    def _update_condition_label(self, label: QLabel, met: bool):
        """Update a condition label with checkmark or X."""
        base_text = label.property("base_text") or label.text()
        if met:
            label.setText(f"PASS: {base_text}")
            label.setStyleSheet("color: green; font-weight: bold;")
        else:
            label.setText(f"FAIL: {base_text}")
            label.setStyleSheet("color: red; font-weight: bold;")
    
    def update_position_preview(self, decision_output: dict = None):
        """
        Update trade preview display with planned entry, SL, TP1/TP2/TP3, risk, reward, size.
        
        Args:
            decision_output: Dict with planned entry, SL, TP levels, etc.
        
        Note: Trade Preview panel was removed from Market Data tab.
        This method is kept for backward compatibility but does nothing.
        """
        # Trade Preview panel removed - method kept for backward compatibility
        pass
    
    def update_quality_score(self, decision_output: dict = None):
        """
        Update entry quality score display.
        
        Args:
            decision_output: Dict with entry_quality_score and quality_breakdown
        """
        if decision_output and decision_output.get('entry_quality_score'):
            score = decision_output.get('entry_quality_score', 0)
            breakdown = decision_output.get('quality_breakdown', {})
            
            # Color code overall score
            if score >= 7.0:
                score_color = "#4CAF50"  # Green
            elif score >= 5.0:
                score_color = "#FF9800"  # Orange
            else:
                score_color = "#F44336"  # Red
            
            self.lbl_quality_score.setText(f"Overall: {score:.1f} / 10")
            self.lbl_quality_score.setStyleSheet(f"color: {score_color}; font-weight: bold;")
            
            # Format breakdown
            if breakdown:
                breakdown_str = " | ".join([
                    f"{k.capitalize()}: {v:.1f}" 
                    for k, v in breakdown.items()
                ])
                self.lbl_quality_breakdown.setText(breakdown_str)
            else:
                self.lbl_quality_breakdown.setText("Pattern: - | EMA: - | Momentum: - | Volatility: -")
        else:
            self.lbl_quality_score.setText("Overall: -")
            self.lbl_quality_score.setStyleSheet("color: gray;")
            self.lbl_quality_breakdown.setText("Pattern: - | EMA: - | Momentum: - | Volatility: -")

    def _format_number(self, value, precision: int = 2, signed: bool = False) -> str:
        """Format a numeric value safely for UI display."""
        if value is None:
            return "-"
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return "-"
        if math.isnan(numeric) or math.isinf(numeric):
            return "-"
        sign = "+" if signed else ""
        return f"{numeric:{sign}.{precision}f}"

    def _format_number_with_suffix(
        self,
        value,
        suffix: str,
        precision: int = 2,
        signed: bool = False,
    ) -> str:
        """Format a number and append a suffix when valid."""
        formatted = self._format_number(value, precision=precision, signed=signed)
        if formatted == "-":
            return "-"
        return f"{formatted}{suffix}"
    
    def update_guard_status(self, decision_output: dict = None):
        """
        Update bar-close guard status display.
        
        Args:
            decision_output: Dict with using_closed_bar, tick_noise_filter_passed, anti_fomo_passed
        """
        if decision_output:
            using_closed = decision_output.get('using_closed_bar', True)
            tick_noise = decision_output.get('tick_noise_filter_passed', True)
            anti_fomo = decision_output.get('anti_fomo_passed', True)
            
            # Update closed bar status
            if using_closed:
                self.lbl_guard_closed_bar.setText("Using Closed Bar (PASS)")
                self.lbl_guard_closed_bar.setStyleSheet("color: green;")
            else:
                self.lbl_guard_closed_bar.setText("Using Closed Bar (FAIL)")
                self.lbl_guard_closed_bar.setStyleSheet("color: red;")
            
            # Update tick noise filter
            if tick_noise:
                self.lbl_guard_tick_noise.setText("Tick Noise Filter: PASSED")
                self.lbl_guard_tick_noise.setStyleSheet("color: green;")
            else:
                self.lbl_guard_tick_noise.setText("Tick Noise Filter: FAILED")
                self.lbl_guard_tick_noise.setStyleSheet("color: red;")
            
            # Update anti-FOMO
            if anti_fomo:
                self.lbl_guard_anti_fomo.setText("Anti-FOMO: PASSED")
                self.lbl_guard_anti_fomo.setStyleSheet("color: green;")
            else:
                self.lbl_guard_anti_fomo.setText("Anti-FOMO: FAILED")
                self.lbl_guard_anti_fomo.setStyleSheet("color: red;")
        else:
            # Reset to defaults
            self.lbl_guard_closed_bar.setText("Using Closed Bar")
            self.lbl_guard_closed_bar.setStyleSheet("color: green;")
            self.lbl_guard_tick_noise.setText("Tick Noise Filter: PASSED")
            self.lbl_guard_tick_noise.setStyleSheet("color: green;")
            self.lbl_guard_anti_fomo.setText("Anti-FOMO: PASSED")
            self.lbl_guard_anti_fomo.setStyleSheet("color: green;")
    
    def update_position_display(self, positions: list = None):
        """
        Update position display with support for multiple positions (pyramiding).
        
        Args:
            positions: List of position dicts, or None for no positions
        """
        if positions and len(positions) > 0:
            # Update status
            pos_count = len(positions)
            self.lbl_position_status.setText(f"{pos_count} open position{'s' if pos_count > 1 else ''}")
            self.lbl_position_status.setStyleSheet("color: green; font-weight: bold;")
            
            # Populate table with positions
            self.table_positions.setRowCount(0)  # Clear table
            
            for position in positions:
                row = self.table_positions.rowCount()
                self.table_positions.insertRow(row)
                
                # Ticket
                ticket_item = QTableWidgetItem(str(position.get('ticket', '-')))
                ticket_item.setFlags(ticket_item.flags() & ~Qt.ItemIsEditable)
                self.table_positions.setItem(row, 0, ticket_item)
                
                # Entry Price
                entry_price = position.get('entry_price', 0)
                entry_item = QTableWidgetItem(f"{entry_price:.2f}")
                entry_item.setFlags(entry_item.flags() & ~Qt.ItemIsEditable)
                self.table_positions.setItem(row, 1, entry_item)
                
                # Current Price
                current_price = position.get('price_current', 0)
                current_item = QTableWidgetItem(f"{current_price:.2f}")
                current_item.setFlags(current_item.flags() & ~Qt.ItemIsEditable)
                self.table_positions.setItem(row, 2, current_item)

                # Compute TP levels on the fly if missing (for older positions)
                tp1_price = position.get('tp1_price')
                tp2_price = position.get('tp2_price')
                tp3_price = position.get('tp3_price')
                if (tp1_price is None or tp2_price is None or tp3_price is None) and hasattr(self, '_controller') and self._controller:
                    try:
                        direction = position.get('direction', 1)
                        calc = self._controller.strategy_engine.multi_level_tp.calculate_tp_levels(
                            entry_price=entry_price,
                            stop_loss=position.get('stop_loss', entry_price),
                            direction=direction
                        )
                        if calc:
                            if tp1_price is None:
                                tp1_price = calc.get('tp1')
                                position['tp1_price'] = tp1_price
                            if tp2_price is None:
                                tp2_price = calc.get('tp2')
                                position['tp2_price'] = tp2_price
                            if tp3_price is None:
                                tp3_price = calc.get('tp3')
                                position['tp3_price'] = tp3_price
                    except Exception as ex:
                        self.logger.error(f"Error calculating TP levels for display: {ex}")
                
                # Stop Loss (use dynamic current_stop_loss if present)
                sl = position.get('current_stop_loss', position.get('stop_loss', 0))
                sl_item = QTableWidgetItem(f"{sl:.2f}")
                sl_item.setFlags(sl_item.flags() & ~Qt.ItemIsEditable)
                self.table_positions.setItem(row, 3, sl_item)
                
                # Take Profit (priority TP3)
                tp = position.get('take_profit', 0)
                tp_item = QTableWidgetItem(f"{tp:.2f}")
                tp_item.setFlags(tp_item.flags() & ~Qt.ItemIsEditable)
                self.table_positions.setItem(row, 4, tp_item)

                # TP levels
                tp1_item = QTableWidgetItem("-" if tp1_price is None else f"{tp1_price:.2f}")
                tp1_item.setFlags(tp1_item.flags() & ~Qt.ItemIsEditable)
                self.table_positions.setItem(row, 5, tp1_item)

                tp2_item = QTableWidgetItem("-" if tp2_price is None else f"{tp2_price:.2f}")
                tp2_item.setFlags(tp2_item.flags() & ~Qt.ItemIsEditable)
                self.table_positions.setItem(row, 6, tp2_item)

                tp3_item = QTableWidgetItem("-" if tp3_price is None else f"{tp3_price:.2f}")
                tp3_item.setFlags(tp3_item.flags() & ~Qt.ItemIsEditable)
                self.table_positions.setItem(row, 7, tp3_item)
                
                # Volume
                volume = position.get('volume', 0)
                volume_item = QTableWidgetItem(f"{volume:.2f}")
                volume_item.setFlags(volume_item.flags() & ~Qt.ItemIsEditable)
                self.table_positions.setItem(row, 8, volume_item)
                
                # Profit/Loss
                profit = position.get('profit', 0)
                profit_item = QTableWidgetItem(f"${profit:.2f}")
                profit_item.setFlags(profit_item.flags() & ~Qt.ItemIsEditable)
                if profit >= 0:
                    profit_item.setForeground(QColor("green"))
                else:
                    profit_item.setForeground(QColor("red"))
                profit_item.setFont(QFont("Arial", 9, QFont.Bold))
                self.table_positions.setItem(row, 9, profit_item)
                
                # Action button (close)
                action_item = QTableWidgetItem("Close")
                action_item.setFlags(action_item.flags() & ~Qt.ItemIsEditable)
                action_item.setForeground(QColor("yellow"))
                self.table_positions.setItem(row, 10, action_item)
            
            self.btn_close_position.setEnabled(True)

            # Auto-select first row and display TP levels so users immediately see TP1/TP2/TP3
            self.table_positions.selectRow(0)
            self._show_tp_levels_for_row(0)
        else:
            # No positions
            self.lbl_position_status.setText("No open positions")
            self.lbl_position_status.setStyleSheet("color: gray;")
            self.table_positions.setRowCount(0)
            self.btn_close_position.setEnabled(False)
            # Reset TP level labels to defaults
            self.lbl_tp1_level.setText("TP1 (Risk 1:1): -")
            self.lbl_tp2_level.setText("TP2 (Risk 1:2): -")
            self.lbl_tp3_level.setText("TP3 (Risk 1:3): -")
            self.lbl_tp_config_error.setVisible(False)
    
    def _refresh_positions_table(self):
        """Refresh the positions table from controller."""
        if hasattr(self, '_controller') and self._controller:
            positions = self._controller.state_manager.get_all_positions()
            self.update_position_display(positions)

    
    def update_sessions(self, sessions: dict):
        """Update trading sessions display."""
        if sessions.get('Asian', False):
            self.lbl_asian.setText("● Asian")
            self.lbl_asian.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.lbl_asian.setText("● Asian")
            self.lbl_asian.setStyleSheet("color: gray;")
        
        if sessions.get('London', False):
            self.lbl_london.setText("● London")
            self.lbl_london.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.lbl_london.setText("● London")
            self.lbl_london.setStyleSheet("color: gray;")
        
        if sessions.get('New York', False):
            self.lbl_newyork.setText("● New York")
            self.lbl_newyork.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.lbl_newyork.setText("● New York")
            self.lbl_newyork.setStyleSheet("color: gray;")
    
    def update_statistics(self, **stats):
        """Update performance and system statistics display."""
        trade_stats = stats.get('trade_stats', {}) if isinstance(stats, dict) else {}
        uptime_seconds = stats.get('uptime_seconds', 0) if isinstance(stats, dict) else 0
        alert_stats = stats.get('alert_stats', {}) if isinstance(stats, dict) else {}
        ui_queue_stats = stats.get('ui_queue_stats', {}) if isinstance(stats, dict) else {}
        perf_top = stats.get('performance_top', []) if isinstance(stats, dict) else []

        self.lbl_total_trades.setText(f"Total Trades: {trade_stats.get('total_trades', 0)}")
        self.lbl_win_rate.setText(f"Win Rate: {trade_stats.get('win_rate', 0):.1f}%")
        self.lbl_total_profit.setText(f"Total Profit: ${trade_stats.get('total_profit', 0):.2f}")
        self.lbl_avg_win.setText(f"Avg Win: ${trade_stats.get('average_win', 0):.2f}")
        self.lbl_avg_loss.setText(f"Avg Loss: ${trade_stats.get('average_loss', 0):.2f}")
        self.lbl_profit_factor.setText(f"Profit Factor: {trade_stats.get('profit_factor', 0):.2f}")

        last_trade = trade_stats.get('last_trade_time')
        if last_trade:
            try:
                parsed_time = datetime.fromisoformat(last_trade)
                self.lbl_last_trade.setText(f"Last Trade: {parsed_time.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception:
                self.lbl_last_trade.setText(f"Last Trade: {last_trade}")
        else:
            self.lbl_last_trade.setText("Last Trade: --")

        uptime_str = str(timedelta(seconds=int(uptime_seconds))) if uptime_seconds else "0s"
        self.lbl_uptime.setText(f"Uptime: {uptime_str}")

        critical = alert_stats.get('critical_count', 0)
        warning = alert_stats.get('warning_count', 0)
        info = alert_stats.get('info_count', 0)
        total_alerts = alert_stats.get('total_alerts', 0)
        self.lbl_alerts.setText(
            f"Alerts: {critical} critical / {warning} warn / {info} info (Total: {total_alerts})"
        )

        self.lbl_queue_stats.setText(
            "UI Queue: pending {pending}/{capacity}, posted {posted}, processed {processed}, dropped {dropped}".format(
                pending=ui_queue_stats.get('pending', 0),
                capacity=ui_queue_stats.get('capacity', 0),
                posted=ui_queue_stats.get('events_posted', 0),
                processed=ui_queue_stats.get('events_processed', 0),
                dropped=ui_queue_stats.get('events_dropped', 0)
            )
        )

        if perf_top:
            perf_parts = []
            for op in perf_top:
                perf_parts.append(
                    f"{op.get('operation', '')}: avg {op.get('avg_ms', 0):.1f}ms, p95 {op.get('p95_ms', 0):.1f}ms, SR {op.get('success_rate', 0):.0f}%"
                )
            perf_text = " | ".join(perf_parts)
        else:
            perf_text = "Performance: no samples yet"
        self.lbl_perf_snapshot.setText(perf_text)
    
    def update_trade_history(self):
        """Update trade history table from state manager."""
        if not hasattr(self, '_controller') or not self._controller:
            return
        
        try:
            # Get all trade history
            trade_history = self._controller.state_manager.trade_history
            # Fallback: if no local history, try MT5 deal history
            if (not trade_history) and hasattr(self._controller, 'execution_engine'):
                mt5_trades = self._controller.execution_engine.get_last_trades(20)
                # Only show exit deals (entry OUT) to avoid duplicate rows
                trade_history = [
                    {
                        'entry_time': t.get('time'),
                        'exit_time': t.get('time'),
                        'entry_price': t.get('price'),
                        'exit_price': t.get('price'),
                        'profit': t.get('profit', 0),
                        'exit_reason': t.get('comment', 'MT5 history'),
                        'take_profit': t.get('price'),
                        'volume': t.get('volume', 0),
                    }
                    for t in mt5_trades
                    if t.get('entry') == 'OUT'
                ]
                # If still empty, keep as original (empty)
            
            # Debug: Write comprehensive diagnostics to file
            debug_log = f"\n{'='*80}\nTrade History Update at {datetime.now().isoformat()}\n{'='*80}\n"
            debug_log += f"Total trades: {len(trade_history)}\n\n"
            
            for idx, trade in enumerate(trade_history):
                exit_reason = trade.get('exit_reason')
                take_profit = trade.get('take_profit')
                debug_log += f"Trade {idx}:\n"
                debug_log += f"  exit_reason VALUE: {repr(exit_reason)}\n"
                debug_log += f"  exit_reason TYPE: {type(exit_reason).__name__}\n"
                debug_log += f"  IS NUMERIC? {isinstance(exit_reason, (int, float))}\n"
                debug_log += f"  take_profit: {take_profit}\n"
                debug_log += f"  Full trade dict: {trade}\n\n"
            
            # Write to file
            with open('trade_history_debug.log', 'a') as f:
                f.write(debug_log)
            
            # Also print to console
            print(debug_log)
            
            # Update table
            self.table_history.setRowCount(len(trade_history))
            
            for idx, trade in enumerate(trade_history):
                # Debug: Log each trade
                print(f"DEBUG: Trade {idx}: ticket={trade.get('ticket')}, exit_reason={repr(trade.get('exit_reason'))}, take_profit={trade.get('take_profit')}")
                
                # Entry Time
                entry_time = trade.get('entry_time', '-')
                self.table_history.setItem(idx, 0, QTableWidgetItem(str(entry_time)))
                
                # Exit Time
                exit_time = trade.get('exit_time', '-')
                self.table_history.setItem(idx, 1, QTableWidgetItem(str(exit_time)))
                
                # Entry Price
                entry_price = trade.get('entry_price', 0)
                self.table_history.setItem(idx, 2, QTableWidgetItem(f"{entry_price:.2f}"))
                
                # Exit Price
                exit_price = trade.get('exit_price', 0)
                self.table_history.setItem(idx, 3, QTableWidgetItem(f"{exit_price:.2f}"))
                
                # Profit (with color coding)
                profit = trade.get('profit', 0)
                profit_item = QTableWidgetItem(f"${profit:.2f}")
                if profit > 0:
                    profit_item.setForeground(QColor('green'))
                elif profit < 0:
                    profit_item.setForeground(QColor('red'))
                self.table_history.setItem(idx, 4, profit_item)
                
                # Exit Reason - ensure it's text, not a price
                exit_reason = trade.get('exit_reason', '-')
                if exit_reason is None:
                    exit_reason = '-'
                # Validate that exit_reason is not a number (which would indicate TP3 price)
                if isinstance(exit_reason, (int, float)):
                    # This is a bug - exit_reason should never be a number
                    error_msg = f"ERROR: exit_reason is NUMERIC! Trade {idx}: {repr(trade)}"
                    print(error_msg)
                    self.log_message(f"BUG DETECTED: Exit reason is NUMERIC (TP3 price: {exit_reason}). This should not happen!")
                    exit_reason = f"[ERROR: {exit_reason}]"
                self.table_history.setItem(idx, 5, QTableWidgetItem(str(exit_reason)))
                
                # TP3 Level (separate column for clarity)
                tp3_level = trade.get('take_profit', 0)
                self.table_history.setItem(idx, 6, QTableWidgetItem(f"{tp3_level:.2f}"))
                
                # Volume
                volume = trade.get('volume', 0)
                self.table_history.setItem(idx, 7, QTableWidgetItem(f"{volume:.2f}"))
            
            # Auto-resize columns
            self.table_history.resizeColumnsToContents()
            
        except Exception as e:
            self.log_message(f"Error updating trade history: {e}")
    
    def update_decision_state(self, decision_output: dict = None):
        """
        Update the Decision State Panel with current trading decision.
        
        Args:
            decision_output: Decision output dict with keys:
                - decision or final_decision: trading decision
                - decision_reason or reason: explanation
                - timestamp or decision_timestamp: when decision was made
                - bar_index or bar_number: bar number
                - execution_mode or mode: LIVE/BACKTEST/REPLAY
        """
        if not decision_output:
            # Reset to defaults
            self.lbl_decision.setText("Decision: N/A")
            self.lbl_decision.setStyleSheet("color: gray;")
            self.lbl_decision_reason.setText("Reason: -")
            self.lbl_decision_timestamp.setText("Timestamp: -")
            self.lbl_decision_bar_index.setText("Bar Index: -")
            self.lbl_decision_mode.setText("Mode: -")
            return
        
        # Try multiple field name variations
        decision = decision_output.get('decision') or decision_output.get('final_decision') or 'N/A'
        reason = decision_output.get('decision_reason') or decision_output.get('reason') or 'Unknown'
        timestamp = decision_output.get('timestamp') or decision_output.get('decision_timestamp') or '-'
        bar_index = decision_output.get('bar_index') or decision_output.get('bar_number') or '-'
        mode = decision_output.get('execution_mode') or decision_output.get('mode') or '-'
        
        # Format decision text with color coding
        if decision == 'ENTER_LONG':
            decision_text = decision
            color = "green"
        elif decision == 'ENTER_SHORT':
            decision_text = decision
            color = "#FF6B6B"
        else:
            decision_text = decision
            color = "gray"
        
        self.lbl_decision.setText(decision_text)
        self.lbl_decision.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
        self.lbl_decision_reason.setText(f"Reason: {reason}")
        self.lbl_decision_timestamp.setText(f"Timestamp: {timestamp}")
        self.lbl_decision_bar_index.setText(f"Bar Index: {bar_index}")
        self.lbl_decision_mode.setText(f"Mode: {mode}")
    
    def update_runtime_context(self, runtime_context: dict = None):
        """
        Update the Runtime Context Panel showing how the system is running.
        
        Args:
            runtime_context: Dict with keys:
                - runtime_mode: enum [DEVELOPMENT, LIVE]
                - auto_trading_enabled: boolean
                - account_type: enum [DEMO, REAL]
                - mt5_connection_status: enum [CONNECTED, DISCONNECTED, RECONNECTING]
                - last_heartbeat: datetime
        """
        if runtime_context:
            mode = runtime_context.get('runtime_mode', 'N/A')
            auto_trading = runtime_context.get('auto_trading_enabled', False)
            account_type = runtime_context.get('account_type', 'N/A')
            connection = runtime_context.get('mt5_connection_status', 'N/A')
            heartbeat = runtime_context.get('last_heartbeat', 'N/A')
            
            # Runtime Mode
            mode_color = "green" if mode == "LIVE" else "orange"
            self.lbl_runtime_context_mode.setText(f"Runtime Mode: {mode}")
            self.lbl_runtime_context_mode.setStyleSheet(f"color: {mode_color}; font-weight: bold;")
            
            # Auto Trading
            auto_text = "Enabled" if auto_trading else "Disabled"
            auto_color = "green" if auto_trading else "orange"
            self.lbl_runtime_context_auto_trading.setText(f"Auto Trading: {auto_text}")
            self.lbl_runtime_context_auto_trading.setStyleSheet(f"color: {auto_color};")
            
            # Account Type
            account_color = "red" if account_type == "REAL" else "green"
            self.lbl_runtime_context_account.setText(f"Account Type: {account_type}")
            self.lbl_runtime_context_account.setStyleSheet(f"color: {account_color}; font-weight: bold;")
            
            # MT5 Connection
            conn_color = "green" if connection == "CONNECTED" else "red" if connection == "DISCONNECTED" else "orange"
            self.lbl_runtime_context_connection.setText(f"MT5 Connection: {connection}")
            self.lbl_runtime_context_connection.setStyleSheet(f"color: {conn_color};")
            
            # Last Heartbeat
            self.lbl_runtime_context_heartbeat.setText(f"Last Heartbeat: {heartbeat}")
        else:
            # Reset to defaults
            self.lbl_runtime_context_mode.setText("Runtime Mode: N/A")
            self.lbl_runtime_context_auto_trading.setText("Auto Trading: N/A")
            self.lbl_runtime_context_account.setText("Account Type: N/A")
            self.lbl_runtime_context_connection.setText("MT5 Connection: N/A")
            self.lbl_runtime_context_heartbeat.setText("Last Heartbeat: N/A")
    
    def log_message(self, message: str):
        """Add a message to the logs display."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.txt_logs.append(f"[{timestamp}] {message}")
        # Auto-scroll to bottom
        scrollbar = self.txt_logs.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

"""
Constants - Centralized configuration values for the trading system.

This module contains all magic numbers and configuration constants
used throughout the application.
"""

# ============================================================================
# MARKET DATA CONSTANTS
# ============================================================================

MINIMUM_BARS_REQUIRED = 220  # Minimum bars for indicators (EMA200 + buffer)
BARS_TO_FETCH = 500  # Default number of bars to fetch from MT5
WARMUP_BARS = 300  # Bars required before starting backtest
ATR_PERIOD = 14  # Period for ATR calculation (14-bar ATR)
EMA_SHORT_PERIOD = 50  # EMA50 period
EMA_LONG_PERIOD = 200  # EMA200 period

# ============================================================================
# CONNECTION & HEARTBEAT CONSTANTS
# ============================================================================

HEARTBEAT_INTERVAL_SECONDS = 15  # Check MT5 connection every 15 seconds
MAX_HEARTBEAT_FAILURES = 3  # Disconnect after 3 failed heartbeats
MT5_RECONNECT_DELAY_SECONDS = 2  # Wait before attempting reconnection
MT5_RECONNECT_MAX_ATTEMPTS = 5  # Maximum reconnection attempts before giving up

# ============================================================================
# TRADING PARAMETERS - RISK MANAGEMENT
# ============================================================================

DEFAULT_RISK_PERCENT = 1.0  # Risk 1% of account per trade
DEFAULT_ATR_MULTIPLIER_STOP = 2.0  # Stop loss = Entry - (2.0 * ATR14)
DEFAULT_RISK_REWARD_RATIO_LONG = 2.0  # TP3 target for LONG: 2.0x risk:reward
DEFAULT_RISK_REWARD_RATIO_SHORT = 2.0  # TP3 target for SHORT: 2.0x risk:reward
DEFAULT_COMMISSION_PER_LOT = 0.0  # Commission per lot (in account currency)
MAX_DRAWDOWN_PERCENT = 10.0  # Maximum allowed equity drawdown

# ============================================================================
# TRADING PARAMETERS - MULTI-LEVEL TP (Take Profit)
# ============================================================================

TP1_REWARD_RATIO = 1.4  # TP1 target: 1.4x risk:reward
TP2_REWARD_RATIO = 1.9  # TP2 target: 1.9x risk:reward
TP3_REWARD_RATIO = 2.0  # TP3 target: 2.0x risk:reward (final)
TRAILING_STOP_OFFSET_PIPS = 0.5  # Trailing stop offset after TP2 reached (0.5 pips)

# ============================================================================
# TRADING PARAMETERS - PATTERN DETECTION
# ============================================================================

PIVOT_LOOKBACK_LEFT = 5  # Left-side lookback for pivot detection
PIVOT_LOOKBACK_RIGHT = 5  # Right-side lookback for pivot detection
EQUALITY_TOLERANCE_PIPS = 2.0  # Tolerance for pivot equality (2 pips)
MIN_BARS_BETWEEN_PIVOTS = 10  # Minimum bars between detected pivots

# ============================================================================
# TRADING PARAMETERS - ENTRY CONDITIONS
# ============================================================================

COOLDOWN_HOURS = 24  # Cooldown period between trades (24 hours)
MOMENTUM_ATR_THRESHOLD = 0.3  # ATR threshold for momentum filter
MIN_PIPS_MOVEMENT = 0.5  # Minimum price movement in pips
ANTI_FOMO_BARS = 10  # Bars after signal to wait (warning only, doesn't block)

# ============================================================================
# BACKTEST PARAMETERS
# ============================================================================

BACKTEST_ROLLING_DAYS = 30  # Default rolling window for backtest
BACKTEST_COMMISSION_PERCENT = 0.02  # Commission as % of trade value
BACKTEST_SPREAD_POINTS = 1.0  # Spread in points (1 point = 0.01 pips)
BACKTEST_SLIPPAGE_POINTS = 0.5  # Slippage in points
BACKTEST_STARTING_EQUITY = 10000.0  # Starting account equity for backtest
XAUUSD_CONTRACT_SIZE = 100.0  # Contract size for XAUUSD

# ============================================================================
# UI PARAMETERS
# ============================================================================

UI_REFRESH_INTERVAL_SECONDS = 10  # UI update frequency
WINDOW_TITLE = "XAUUSD Double Bottom Strategy"
UI_THEME = "dark"  # Dark theme for UI

# ============================================================================
# LOGGING PARAMETERS
# ============================================================================

LOG_DIR = "logs"  # Directory for log files
LOG_LEVEL_DEFAULT = "INFO"  # Default logging level
LOG_MAX_SIZE_MB = 10  # Maximum log file size (10 MB)
LOG_BACKUP_COUNT = 5  # Number of backup log files to keep

# ============================================================================
# DATA & STATE MANAGEMENT
# ============================================================================

STATE_FILE = "data/state.json"  # Path to state persistence file
STATE_BACKUP_COUNT = 10  # Number of state backups to keep
STATE_WRITE_DELAY_SECONDS = 5  # Batch write delay (5 seconds)

# ============================================================================
# MT5 CONFIGURATION
# ============================================================================

DEFAULT_SYMBOL = "XAUUSD"  # Default trading symbol
DEFAULT_TIMEFRAME = "H1"  # Default timeframe (1-hour)
DEFAULT_MAGIC_NUMBER = 234000  # Magic number for identifying strategy orders
MT5_ORDER_DEVIATION_POINTS = 20  # Maximum deviation in points for orders

# ============================================================================
# MODE CONFIGURATION
# ============================================================================

DEFAULT_DEMO_MODE = True  # Start in demo mode by default
DEFAULT_AUTO_TRADE = False  # Don't auto-trade by default (user must enable)

# ============================================================================
# MARKET CONTEXT PARAMETERS
# ============================================================================

VOLATILITY_ATR_LOW = 0.5  # Low volatility threshold
VOLATILITY_ATR_HIGH = 2.0  # High volatility threshold
EMA_DISTANCE_RATIO_LOW = 0.6  # Distance ratio for trend strength
EMA_DISTANCE_RATIO_HIGH = 1.0  # Distance ratio for strong trend

# ============================================================================
# RECENT TRADES HISTORY
# ============================================================================

DEFAULT_RECENT_TRADES_COUNT = 10  # Number of recent trades to display
DEFAULT_RECENT_TRADES_COUNT_ANALYSIS = 50  # Number of trades for analysis

# ============================================================================
# TP STATE MACHINE STATES
# ============================================================================

TP_STATE_IN_TRADE = "IN_TRADE"  # Position open, no TP reached
TP_STATE_TP1_REACHED = "TP1_REACHED"  # First target reached
TP_STATE_TP2_REACHED = "TP2_REACHED"  # Second target reached
TP_STATE_CLOSED = "CLOSED"  # Position closed

# ============================================================================
# ORDER TYPES & DIRECTIONS
# ============================================================================

ORDER_TYPE_BUY = "BUY"  # Long order
ORDER_TYPE_SELL = "SELL"  # Short order (not used in current strategy)
DIRECTION_LONG = 1  # LONG direction
DIRECTION_SHORT = -1  # SHORT direction (not used in current strategy)

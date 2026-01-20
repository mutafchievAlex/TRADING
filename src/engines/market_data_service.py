"""
Market Data Service - Fetches OHLC data from MetaTrader 5

This module handles all interactions with MT5 for fetching historical and live market data.
It ensures data is properly formatted and aligned with bar-close logic (no intrabar execution).
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, TYPE_CHECKING
import logging
import time

if TYPE_CHECKING:
    from config import AppConfig


class MarketDataService:
    """
    Fetches and manages OHLC data from MetaTrader 5.
    
    Responsibilities:
    - Connect/disconnect from MT5
    - Fetch historical OHLC bars
    - Ensure data integrity (no repainting)
    - Handle connection errors gracefully
    """
    
    def __init__(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "H1",
        config: Optional["AppConfig"] = None,
    ):
        """
        Initialize the Market Data Service.
        
        Args:
            symbol: Trading instrument (default: XAUUSD)
            timeframe: Chart timeframe (default: H1)
            config: Optional validated app configuration
        """
        if config is not None:
            symbol = config.mt5.symbol
            timeframe = config.mt5.timeframe
        self.symbol = symbol
        self.timeframe = self._parse_timeframe(timeframe)
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        
    def _parse_timeframe(self, tf_string: str) -> int:
        """
        Convert timeframe string to MT5 constant.
        
        Args:
            tf_string: Timeframe as string (e.g., "H1", "M15")
            
        Returns:
            MT5 timeframe constant
        """
        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1,
        }
        return timeframe_map.get(tf_string, mt5.TIMEFRAME_H1)
    
    def connect(self, login: Optional[int] = None, password: Optional[str] = None, 
                server: Optional[str] = None, terminal_path: Optional[str] = None) -> bool:
        """
        Connect to MetaTrader 5 terminal.
        
        Args:
            login: MT5 account number (optional if already logged in)
            password: MT5 account password
            server: MT5 broker server
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            initialized = False
            # Try initialize with provided terminal path, else default
            if terminal_path:
                self.logger.info(f"Initializing MT5 with terminal_path: {terminal_path}")
                initialized = mt5.initialize(path=terminal_path)
            else:
                self.logger.info("Initializing MT5 with default path")
                initialized = mt5.initialize()

            if not initialized:
                error = mt5.last_error()
                self.logger.error(f"MT5 initialization failed: {error}")
                return False
            
            self.logger.info("MT5 initialized successfully")
            
            # Wait for terminal to be ready
            time.sleep(0.5)
            
            # If credentials provided, login
            if login is not None and password is not None and server is not None:
                self.logger.info(f"Attempting login: login={login}, server={server}")
                authorized = mt5.login(login, password=password, server=server)
                if not authorized:
                    error = mt5.last_error()
                    self.logger.error(f"MT5 login failed: {error}")
                    mt5.shutdown()
                    return False
                self.logger.info("MT5 login successful")
                # Wait for login to complete
                time.sleep(0.5)
            else:
                self.logger.info(f"No credentials provided - using existing terminal login")
                self.logger.info(f"  login={login}, password={'*' if password else None}, server={server}")
            
            # Wait for terminal to be fully ready
            time.sleep(1)
            
            # Verify symbol is available with retries
            max_retries = 3
            symbol_info = None
            for attempt in range(max_retries):
                symbol_info = mt5.symbol_info(self.symbol)
                if symbol_info is not None:
                    break
                self.logger.warning(f"Symbol info not available, attempt {attempt + 1}/{max_retries}")
                time.sleep(1)
            
            if symbol_info is None:
                self.logger.error(f"Symbol {self.symbol} not found after {max_retries} attempts")
                self.logger.info("Attempting to select symbol...")
                if not mt5.symbol_select(self.symbol, True):
                    self.logger.error(f"Failed to select symbol {self.symbol}")
                    mt5.shutdown()
                    return False
                self.logger.info(f"Symbol {self.symbol} selected successfully")
                time.sleep(0.5)
            else:
                # Enable symbol if not visible
                if not symbol_info.visible:
                    self.logger.info(f"Symbol {self.symbol} not visible - attempting to select")
                    if not mt5.symbol_select(self.symbol, True):
                        self.logger.error(f"Failed to enable symbol {self.symbol}")
                        mt5.shutdown()
                        return False
                    self.logger.info(f"Symbol {self.symbol} enabled")
                    time.sleep(0.5)
                else:
                    self.logger.info(f"Symbol {self.symbol} is visible")
            
            self.is_connected = True
            account_info = mt5.account_info()
            if account_info:
                self.logger.info(f"Connected to MT5. Account: {account_info.login}")
            else:
                self.logger.warning("Connected to MT5 but account info unavailable")
            return True
            
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MetaTrader 5."""
        if self.is_connected:
            mt5.shutdown()
            self.is_connected = False
            self.logger.info("Disconnected from MT5")
    
    def get_bars(self, count: int = 500) -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLC bars from MT5.
        
        Args:
            count: Number of bars to fetch
            
        Returns:
            DataFrame with columns: time, open, high, low, close, tick_volume
            Returns None if fetch fails
        """
        if not self.is_connected:
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            # Retry logic for IPC errors
            max_retries = 3
            for attempt in range(max_retries):
                # Fetch bars
                rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, count)
                
                if rates is not None and len(rates) > 0:
                    # Convert to DataFrame
                    df = pd.DataFrame(rates)
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    
                    self.logger.debug(f"Fetched {len(df)} bars for {self.symbol}")
                    return df
                
                # Check error
                error = mt5.last_error()
                if error[0] == -10001:  # IPC send failed
                    self.logger.warning(f"IPC error on attempt {attempt + 1}/{max_retries}, retrying...")
                    time.sleep(1)
                    continue
                else:
                    self.logger.error(f"Failed to fetch bars: {error}")
                    return None
            
            self.logger.error(f"Failed to fetch bars after {max_retries} attempts")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching bars: {e}")
            return None
    
    def get_latest_bar(self) -> Optional[pd.Series]:
        """
        Get the most recent completed bar (bar-close logic).
        
        Returns:
            Series representing the latest bar, or None if unavailable
        """
        df = self.get_bars(count=2)  # Get last 2 bars
        if df is None or len(df) < 2:
            return None
        
        # Return the second-to-last bar (completed bar, not current forming bar)
        return df.iloc[-2]
    
    def get_current_tick(self) -> Optional[float]:
        """
        Get the current live tick price.
        
        Returns:
            Current bid price, or None if unavailable
        """
        if not self.is_connected:
            return None
        
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if tick is None:
                return None
            return tick.bid  # Use bid for current price display
        except Exception as e:
            self.logger.error(f"Error getting tick: {e}")
            return None

    def get_percent_changes(self, current_price: float) -> dict:
        """
        Get percent change vs last day, week, and month based on closed bars.

        Args:
            current_price: Latest live/close price to compare against historical closes

        Returns:
            Dict with keys: day, week, month (values may be None if unavailable)
        """
        if not self.is_connected or current_price is None:
            return {'day': None, 'week': None, 'month': None}

        def _change(timeframe_const):
            try:
                bars = mt5.copy_rates_from_pos(self.symbol, timeframe_const, 0, 2)
                if bars is None or len(bars) < 2:
                    return None
                prev_close = bars[-2]['close']
                if prev_close == 0:
                    return None
                return ((current_price - prev_close) / prev_close) * 100.0
            except Exception as e:
                self.logger.error(f"Error calculating change for timeframe {timeframe_const}: {e}")
                return None

        return {
            'day': _change(mt5.TIMEFRAME_D1),
            'week': _change(mt5.TIMEFRAME_W1),
            'month': _change(mt5.TIMEFRAME_MN1)
        }
    
    def get_active_sessions(self) -> dict:
        """
        Check which trading sessions are currently active.
        
        Returns:
            Dict with session names and active status
        """
        try:
            from datetime import datetime, timezone
            
            # Get current UTC time
            now_utc = datetime.now(timezone.utc)
            hour_utc = now_utc.hour
            
            # Session times (UTC/GMT)
            # Asian (Tokyo): 00:00 - 09:00 UTC
            # London: 08:00 - 17:00 UTC
            # New York: 13:00 - 22:00 UTC
            
            sessions = {
                'Asian': (0 <= hour_utc < 9),
                'London': (8 <= hour_utc < 17),
                'New York': (13 <= hour_utc < 22)
            }
            
            return sessions
            
        except Exception as e:
            self.logger.error(f"Error checking sessions: {e}")
            return {'Asian': False, 'London': False, 'New York': False}
    
    def get_account_info(self) -> Optional[dict]:
        """
        Get current MT5 account information.
        
        Returns:
            Dictionary with account details (balance, equity, margin, etc.)
        """
        if not self.is_connected:
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return None
            
            return {
                'login': account_info.login,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'currency': account_info.currency,
                'leverage': account_info.leverage,
                'profit': account_info.profit,
                'trade_mode': account_info.trade_mode,
                'server': account_info.server,
                'name': account_info.name,
                'company': account_info.company,
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching account info: {e}")
            return None
    
    def get_symbol_info(self) -> Optional[dict]:
        """
        Get symbol-specific information (point, tick_size, etc.).
        
        Returns:
            Dictionary with symbol details
        """
        if not self.is_connected:
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                return None
            
            return {
                'symbol': symbol_info.name,
                'point': symbol_info.point,
                'tick_size': symbol_info.trade_tick_size,
                'tick_value': symbol_info.trade_tick_value,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step,
                'digits': symbol_info.digits,
                'spread': symbol_info.spread,
                'trade_contract_size': symbol_info.trade_contract_size,
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching symbol info: {e}")
            return None


if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.DEBUG)
    
    service = MarketDataService("XAUUSD", "H1")
    if service.connect():
        print("Connected to MT5")
        
        # Test fetching bars
        df = service.get_bars(count=100)
        if df is not None:
            print(f"Fetched {len(df)} bars")
            print(df.tail())
        
        # Test account info
        account = service.get_account_info()
        if account:
            print(f"Account equity: {account['equity']}")
        
        service.disconnect()
        print("Disconnected")

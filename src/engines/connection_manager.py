"""
MT5 Connection Manager - Handles connection health and auto-recovery

This module manages MT5 connection state with heartbeat checking and
automatic reconnection on failures.
"""

import MetaTrader5 as mt5
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
import time


class MT5ConnectionManager:
    """
    Manages MT5 connection health and auto-recovery.
    
    Responsibilities:
    - Periodic heartbeat checks
    - Detect connection failures (IPC errors, lost connection)
    - Automatic reconnection
    - Connection status tracking
    - Logging and notifications
    """
    
    def __init__(self, 
                 heartbeat_interval_seconds: int = 30,
                 max_heartbeat_failures: int = 3):
        """
        Initialize Connection Manager.
        
        Args:
            heartbeat_interval_seconds: How often to check connection (default: 30)
            max_heartbeat_failures: Max failed heartbeats before reconnect (default: 3)
        """
        self.logger = logging.getLogger(__name__)
        self.heartbeat_interval = timedelta(seconds=heartbeat_interval_seconds)
        self.max_failures = max_heartbeat_failures
        
        # State tracking
        self.is_connected = False
        self.last_heartbeat = None
        self.consecutive_failures = 0
        self.last_error = None
        self.reconnect_in_progress = False
        
        # Callback for status changes
        self.on_status_change: Optional[Callable[[bool], None]] = None
    
    def check_connection(self) -> bool:
        """
        Perform a heartbeat check on MT5 connection.
        
        Returns:
            True if connection healthy, False if failed
        """
        try:
            # Heartbeat: Check account info
            account_info = mt5.account_info()
            
            if account_info is None:
                error = mt5.last_error()
                self.logger.warning(f"Heartbeat failed: {error}")
                self.consecutive_failures += 1
                self.last_error = error
                
                # Check if we exceeded failure threshold
                if self.consecutive_failures >= self.max_failures:
                    self.logger.error(f"Connection lost after {self.consecutive_failures} failed heartbeats")
                    self._on_connection_lost()
                    return False
                
                return False
            
            # Connection is healthy
            if self.consecutive_failures > 0:
                self.logger.info(f"Connection recovered after {self.consecutive_failures} failures")
            
            self.consecutive_failures = 0
            self.last_heartbeat = datetime.now()
            
            if not self.is_connected:
                self._on_connection_restored()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Heartbeat check error: {e}")
            self.consecutive_failures += 1
            self.last_error = str(e)
            
            if self.consecutive_failures >= self.max_failures:
                self._on_connection_lost()
                return False
            
            return False
    
    def reconnect(self, login: int, password: str, server: str, 
                  terminal_path: Optional[str] = None) -> bool:
        """
        Attempt to reconnect to MT5.
        
        Args:
            login: MT5 account number
            password: MT5 password
            server: MT5 server
            terminal_path: Optional path to MT5 terminal
            
        Returns:
            True if reconnection successful, False otherwise
        """
        if self.reconnect_in_progress:
            self.logger.warning("Reconnection already in progress")
            return False
        
        self.reconnect_in_progress = True
        
        try:
            self.logger.warning("Attempting to reconnect to MT5...")
            
            # Try to shutdown gracefully
            try:
                mt5.shutdown()
            except Exception as e:
                self.logger.debug(f"MT5 shutdown had issues (expected if not connected): {e}")
            
            # Wait a bit before reinitializing
            time.sleep(2)
            
            # Reinitialize
            if terminal_path:
                initialized = mt5.initialize(path=terminal_path)
            else:
                initialized = mt5.initialize()
            
            if not initialized:
                error = mt5.last_error()
                self.logger.error(f"MT5 reinitialization failed: {error}")
                self.reconnect_in_progress = False
                return False
            
            self.logger.info("MT5 reinitialized")
            time.sleep(1)
            
            # Login
            authorized = mt5.login(login, password=password, server=server)
            if not authorized:
                error = mt5.last_error()
                self.logger.error(f"MT5 relogin failed: {error}")
                mt5.shutdown()
                self.reconnect_in_progress = False
                return False
            
            self.logger.info("MT5 relogin successful")
            time.sleep(1)
            
            # Reset failure counter
            self.consecutive_failures = 0
            self.last_error = None
            self.reconnect_in_progress = False
            
            # Verify connection
            if self.check_connection():
                self.logger.info("Connection restored successfully")
                return True
            else:
                self.logger.error("Connection verification failed after reconnect")
                return False
            
        except Exception as e:
            self.logger.error(f"Reconnection error: {e}", exc_info=True)
            self.reconnect_in_progress = False
            return False
    
    def _on_connection_lost(self):
        """Handle connection loss event."""
        if self.is_connected:
            self.logger.error("MT5 CONNECTION LOST")
            self.is_connected = False
            
            if self.on_status_change:
                self.on_status_change(False)
    
    def _on_connection_restored(self):
        """Handle connection restoration event."""
        if not self.is_connected:
            self.logger.info("MT5 connection restored")
            self.is_connected = True
            
            if self.on_status_change:
                self.on_status_change(True)
    
    def set_connection_status(self, connected: bool):
        """Set the initial connection status."""
        self.is_connected = connected
        self.consecutive_failures = 0
        self.last_heartbeat = datetime.now() if connected else None
    
    def get_status(self) -> dict:
        """
        Get current connection status.
        
        Returns:
            Dict with connection metrics
        """
        return {
            'is_connected': self.is_connected,
            'consecutive_failures': self.consecutive_failures,
            'last_heartbeat': self.last_heartbeat,
            'last_error': self.last_error,
            'reconnect_in_progress': self.reconnect_in_progress
        }
    
    def get_status_string(self) -> str:
        """Get human-readable status string."""
        if self.reconnect_in_progress:
            return "Reconnecting..."
        elif self.is_connected:
            return f"Connected (failures: {self.consecutive_failures}/{self.max_failures})"
        else:
            return f"Disconnected (failures: {self.consecutive_failures}/{self.max_failures})"


if __name__ == "__main__":
    # Simple test
    # Note: Do not use basicConfig here - logging is configured by the application
    # logger = logging.getLogger(__name__)
    
    manager = MT5ConnectionManager(heartbeat_interval_seconds=5, max_heartbeat_failures=2)
    manager.set_connection_status(True)
    
    for i in range(10):
        result = manager.check_connection()
        print(f"Heartbeat {i+1}: {result}")
        print(f"Status: {manager.get_status_string()}")
        print()
        time.sleep(2)

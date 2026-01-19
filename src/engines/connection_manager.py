"""
MT5 Connection Manager - Handles connection health and auto-recovery

This module manages MT5 connection state with heartbeat checking and
automatic reconnection on failures.
"""

import MetaTrader5 as mt5
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
import threading
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
        self.reconnect_thread: Optional[threading.Thread] = None
        self._reconnect_stop_event = threading.Event()
        
        # Callback for status changes
        self.on_status_change: Optional[Callable[[bool], None]] = None
        self.on_reconnect_status: Optional[Callable[[str], None]] = None
    
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
    
    def request_reconnect_async(self, login: int, password: str, server: str,
                                terminal_path: Optional[str] = None,
                                timeout_seconds: int = 30) -> bool:
        """
        Start a reconnect attempt in a background thread.

        Args:
            login: MT5 account number
            password: MT5 password
            server: MT5 server
            terminal_path: Optional path to MT5 terminal
            timeout_seconds: Max time for reconnect attempt before cancelling

        Returns:
            True if thread started, False otherwise
        """
        if self.reconnect_in_progress:
            self.logger.warning("Reconnection already in progress")
            return False

        self._reconnect_stop_event.clear()
        self.reconnect_in_progress = True
        self._notify_reconnect_status("Reconnecting...")
        self.reconnect_thread = threading.Thread(
            target=self._reconnect_worker,
            name="mt5-reconnect",
            args=(login, password, server, terminal_path, timeout_seconds),
            daemon=True,
        )
        self.reconnect_thread.start()
        return True

    def cancel_reconnect(self):
        """Request cancellation of an ongoing reconnect attempt."""
        if self.reconnect_in_progress:
            self.logger.warning("Reconnect cancellation requested")
            self._reconnect_stop_event.set()
            self._notify_reconnect_status("Reconnect cancellation requested")

    def reconnect(self, login: int, password: str, server: str,
                  terminal_path: Optional[str] = None,
                  timeout_seconds: int = 30) -> bool:
        """
        Attempt to reconnect to MT5.
        
        Args:
            login: MT5 account number
            password: MT5 password
            server: MT5 server
            terminal_path: Optional path to MT5 terminal
            timeout_seconds: Max time for reconnect attempt before cancelling
            
        Returns:
            True if reconnection successful, False otherwise
        """
        if self.reconnect_in_progress:
            self.logger.warning("Reconnection already in progress")
            return False
        
        try:
            self.reconnect_in_progress = True
            self._reconnect_stop_event.clear()
            return self._reconnect_impl(
                login=login,
                password=password,
                server=server,
                terminal_path=terminal_path,
                timeout_seconds=timeout_seconds,
                stop_event=self._reconnect_stop_event,
            )
        except Exception as e:
            self.logger.error(f"Reconnection error: {e}", exc_info=True)
            self.last_error = str(e)
            return False
        finally:
            self.reconnect_in_progress = False

    def _reconnect_worker(self, login: int, password: str, server: str,
                          terminal_path: Optional[str],
                          timeout_seconds: int):
        """Background reconnect worker to avoid blocking UI."""
        try:
            self._reconnect_impl(
                login=login,
                password=password,
                server=server,
                terminal_path=terminal_path,
                timeout_seconds=timeout_seconds,
                stop_event=self._reconnect_stop_event,
            )
        finally:
            self.reconnect_in_progress = False

    def _reconnect_impl(self, login: int, password: str, server: str,
                        terminal_path: Optional[str], timeout_seconds: int,
                        stop_event: threading.Event) -> bool:
        """Shared reconnect implementation with cancellation and timeout."""
        start_time = time.monotonic()

        def _timed_out() -> bool:
            return time.monotonic() - start_time >= timeout_seconds

        def _should_cancel() -> bool:
            return stop_event.is_set() or _timed_out()

        def _sleep_with_cancel(seconds: float) -> bool:
            stop_event.wait(timeout=seconds)
            return not _should_cancel()

        def _cancelled_response(message: str) -> bool:
            self.last_error = message
            self.logger.warning(message)
            self._notify_reconnect_status(message)
            return False

        def _cancel_message(stage: str) -> str:
            if stop_event.is_set():
                return f"Reconnect cancelled {stage}"
            return f"Reconnect timed out {stage}"

        self.logger.warning("Attempting to reconnect to MT5...")
        self._notify_reconnect_status("Reconnecting: shutting down")

        if _should_cancel():
            return _cancelled_response(_cancel_message("before shutdown"))

        # Try to shutdown gracefully
        try:
            mt5.shutdown()
        except Exception as e:
            self.logger.debug(f"MT5 shutdown had issues (expected if not connected): {e}")

        if not _sleep_with_cancel(2):
            return _cancelled_response(_cancel_message("during shutdown delay"))

        if _should_cancel():
            return _cancelled_response(_cancel_message("before initialization"))

        self._notify_reconnect_status("Reconnecting: initializing")
        if terminal_path:
            initialized = mt5.initialize(path=terminal_path)
        else:
            initialized = mt5.initialize()

        if not initialized:
            error = mt5.last_error()
            self.last_error = error
            self.logger.error(f"MT5 reinitialization failed: {error}")
            self._notify_reconnect_status("Reconnect failed: initialization error")
            return False

        self.logger.info("MT5 reinitialized")

        if not _sleep_with_cancel(1):
            return _cancelled_response(_cancel_message("during initialization delay"))

        if _should_cancel():
            return _cancelled_response(_cancel_message("before login"))

        self._notify_reconnect_status("Reconnecting: logging in")
        authorized = mt5.login(login, password=password, server=server)
        if not authorized:
            error = mt5.last_error()
            self.last_error = error
            self.logger.error(f"MT5 relogin failed: {error}")
            self._notify_reconnect_status("Reconnect failed: login error")
            mt5.shutdown()
            return False

        self.logger.info("MT5 relogin successful")

        if not _sleep_with_cancel(1):
            return _cancelled_response(_cancel_message("during login delay"))

        if _should_cancel():
            return _cancelled_response(_cancel_message("before verification"))

        self._notify_reconnect_status("Reconnecting: verifying connection")

        # Reset failure counter
        self.consecutive_failures = 0
        self.last_error = None

        # Verify connection
        if self.check_connection():
            self.logger.info("Connection restored successfully")
            self._notify_reconnect_status("Reconnect successful")
            return True

        self.logger.error("Connection verification failed after reconnect")
        self._notify_reconnect_status("Reconnect failed: verification error")
        return False

    def _notify_reconnect_status(self, message: str):
        """Notify UI of reconnect status without blocking."""
        if self.on_reconnect_status:
            try:
                self.on_reconnect_status(message)
            except Exception as e:
                self.logger.debug(f"Reconnect status callback error: {e}")
    
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

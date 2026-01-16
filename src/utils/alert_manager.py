"""
Alert System - Critical event notifications

Alerts for:
- Connection loss/recovery
- Position opened/closed
- Critical errors
- Health warnings
- Performance issues
"""

import logging
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from collections import deque


logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts."""
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_MODIFIED = "position_modified"
    ERROR = "error"
    HEALTH_WARNING = "health_warning"
    HEALTH_CRITICAL = "health_critical"
    PERFORMANCE_ISSUE = "performance_issue"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"


@dataclass
class Alert:
    """Alert notification."""
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    
    def __str__(self):
        severity_icon = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🔴"
        }
        icon = severity_icon.get(self.severity, "•")
        time_str = self.timestamp.strftime("%H:%M:%S")
        return f"{icon} [{time_str}] {self.message}"


class AlertManager:
    """
    Manage system alerts and notifications.
    
    Features:
    - Multiple alert channels (log, UI, file)
    - Alert history
    - Severity filtering
    - Custom alert handlers
    - Alert suppression (prevent spam)
    """
    
    def __init__(
        self,
        max_history: int = 500,
        min_alert_interval_seconds: float = 5.0
    ):
        """
        Initialize alert manager.
        
        Args:
            max_history: Maximum alerts to keep in history
            min_alert_interval_seconds: Minimum time between same alerts (anti-spam)
        """
        self.max_history = max_history
        self.min_alert_interval = min_alert_interval_seconds
        
        # Alert history
        self.alerts: deque = deque(maxlen=max_history)
        
        # Alert handlers (callbacks)
        self.handlers: List[Callable[[Alert], None]] = []
        
        # Last alert times (for suppression)
        self.last_alert_time: Dict[str, datetime] = {}
        
        # Statistics
        self.stats = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 0,
            AlertSeverity.CRITICAL: 0
        }
        
        logger.info("AlertManager initialized")
    
    def add_handler(self, handler: Callable[[Alert], None]):
        """
        Add alert handler (callback function).
        
        Handler will be called for every alert.
        
        Args:
            handler: Function that accepts Alert object
        """
        self.handlers.append(handler)
        logger.info(f"Alert handler added: {handler.__name__}")
    
    def send_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suppress: bool = True
    ) -> Optional[Alert]:
        """
        Send an alert.
        
        Args:
            alert_type: Type of alert
            severity: Severity level
            message: Alert message
            details: Additional details (optional)
            suppress: Whether to suppress duplicate alerts
        
        Returns:
            Alert object if sent, None if suppressed
        """
        # Check suppression
        if suppress:
            alert_key = f"{alert_type.value}:{message}"
            last_time = self.last_alert_time.get(alert_key)
            
            if last_time:
                elapsed = (datetime.now() - last_time).total_seconds()
                if elapsed < self.min_alert_interval:
                    logger.debug(f"Alert suppressed: {message}")
                    return None
            
            self.last_alert_time[alert_key] = datetime.now()
        
        # Create alert
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
            details=details
        )
        
        # Store in history
        self.alerts.append(alert)
        
        # Update statistics
        self.stats[severity] += 1
        
        # Log to logger
        log_msg = f"ALERT: {alert}"
        if severity == AlertSeverity.CRITICAL:
            logger.error(log_msg)
        elif severity == AlertSeverity.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        # Call handlers
        for handler in self.handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler {handler.__name__}: {e}")
        
        return alert
    
    def alert_connection_lost(self):
        """Alert: MT5 connection lost."""
        self.send_alert(
            alert_type=AlertType.CONNECTION_LOST,
            severity=AlertSeverity.CRITICAL,
            message="MetaTrader 5 connection lost!",
            details={'action': 'Trading stopped, attempting reconnection'}
        )
    
    def alert_connection_restored(self):
        """Alert: MT5 connection restored."""
        self.send_alert(
            alert_type=AlertType.CONNECTION_RESTORED,
            severity=AlertSeverity.INFO,
            message="MetaTrader 5 connection restored",
            details={'action': 'System ready to resume trading'}
        )
    
    def alert_position_opened(self, position_data: Dict):
        """Alert: Position opened."""
        self.send_alert(
            alert_type=AlertType.POSITION_OPENED,
            severity=AlertSeverity.INFO,
            message=f"Position opened: {position_data.get('type', 'UNKNOWN')} @ {position_data.get('entry_price', 0):.2f}",
            details=position_data
        )
    
    def alert_position_closed(self, position_data: Dict):
        """Alert: Position closed."""
        profit = position_data.get('profit', 0)
        severity = AlertSeverity.INFO if profit >= 0 else AlertSeverity.WARNING
        
        self.send_alert(
            alert_type=AlertType.POSITION_CLOSED,
            severity=severity,
            message=f"Position closed: Profit ${profit:.2f}",
            details=position_data
        )
    
    def alert_error(self, error_message: str, details: Optional[Dict] = None):
        """Alert: Critical error occurred."""
        self.send_alert(
            alert_type=AlertType.ERROR,
            severity=AlertSeverity.CRITICAL,
            message=f"Error: {error_message}",
            details=details
        )
    
    def alert_health_warning(self, health_message: str, details: Optional[Dict] = None):
        """Alert: Health check warning."""
        self.send_alert(
            alert_type=AlertType.HEALTH_WARNING,
            severity=AlertSeverity.WARNING,
            message=f"Health Warning: {health_message}",
            details=details
        )
    
    def alert_health_critical(self, health_message: str, details: Optional[Dict] = None):
        """Alert: Health check critical."""
        self.send_alert(
            alert_type=AlertType.HEALTH_CRITICAL,
            severity=AlertSeverity.CRITICAL,
            message=f"Health Critical: {health_message}",
            details=details
        )
    
    def alert_performance_issue(self, operation: str, latency_ms: float):
        """Alert: Performance issue detected."""
        self.send_alert(
            alert_type=AlertType.PERFORMANCE_ISSUE,
            severity=AlertSeverity.WARNING,
            message=f"Performance issue: {operation} took {latency_ms:.1f}ms",
            details={'operation': operation, 'latency_ms': latency_ms}
        )
    
    def alert_system_startup(self):
        """Alert: System started."""
        self.send_alert(
            alert_type=AlertType.SYSTEM_STARTUP,
            severity=AlertSeverity.INFO,
            message="Trading system started",
            suppress=False
        )
    
    def alert_system_shutdown(self):
        """Alert: System shutting down."""
        self.send_alert(
            alert_type=AlertType.SYSTEM_SHUTDOWN,
            severity=AlertSeverity.INFO,
            message="Trading system shutting down",
            suppress=False
        )
    
    def get_recent_alerts(self, count: int = 10) -> List[Alert]:
        """
        Get recent alerts.
        
        Args:
            count: Number of alerts to return
        
        Returns:
            List of recent alerts (newest first)
        """
        return list(self.alerts)[-count:][::-1]
    
    def get_critical_alerts(self, hours: int = 24) -> List[Alert]:
        """
        Get critical alerts from last N hours.
        
        Args:
            hours: Time window in hours
        
        Returns:
            List of critical alerts
        """
        cutoff = datetime.now().timestamp() - (hours * 3600)
        
        return [
            alert for alert in self.alerts
            if alert.severity == AlertSeverity.CRITICAL
            and alert.timestamp.timestamp() > cutoff
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get alert statistics.
        
        Returns:
            Dictionary with statistics
        """
        total = sum(self.stats.values())
        
        return {
            'total_alerts': total,
            'info_count': self.stats[AlertSeverity.INFO],
            'warning_count': self.stats[AlertSeverity.WARNING],
            'critical_count': self.stats[AlertSeverity.CRITICAL],
            'history_size': len(self.alerts)
        }
    
    def get_summary(self) -> str:
        """Get alert summary string."""
        stats = self.get_statistics()
        return (
            f"Alerts: {stats['critical_count']} critical, "
            f"{stats['warning_count']} warnings, "
            f"{stats['info_count']} info "
            f"(Total: {stats['total_alerts']})"
        )
    
    def clear_history(self):
        """Clear alert history."""
        self.alerts.clear()
        logger.info("Alert history cleared")

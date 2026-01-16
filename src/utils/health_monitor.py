"""
Health Monitor - System health checks and diagnostics

Monitors:
- MT5 connection status
- State file integrity
- Memory usage
- Disk space
- Thread health
- Queue depths
"""

import psutil
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: HealthStatus
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class HealthMonitor:
    """
    System health monitoring.
    
    Performs periodic health checks:
    - MT5 connection status
    - State file integrity and size
    - Memory usage (RAM)
    - Disk space available
    - Thread status
    - UI event queue depth
    - State write queue depth
    """
    
    def __init__(
        self,
        state_file: Path,
        memory_threshold_mb: float = 500.0,
        disk_threshold_gb: float = 1.0,
        queue_depth_threshold: int = 100
    ):
        """
        Initialize health monitor.
        
        Args:
            state_file: Path to state.json file
            memory_threshold_mb: Warning threshold for memory usage (MB)
            disk_threshold_gb: Warning threshold for disk space (GB)
            queue_depth_threshold: Warning threshold for queue depth
        """
        self.state_file = state_file
        self.memory_threshold_mb = memory_threshold_mb
        self.disk_threshold_gb = disk_threshold_gb
        self.queue_depth_threshold = queue_depth_threshold
        
        self.last_check_time = None
        self.check_history: List[Dict[str, HealthCheck]] = []
        
        logger.info("HealthMonitor initialized")
    
    def check_all(
        self,
        mt5_connected: bool = False,
        ui_queue_depth: int = 0,
        state_queue_depth: int = 0
    ) -> Dict[str, HealthCheck]:
        """
        Perform all health checks.
        
        Args:
            mt5_connected: Current MT5 connection status
            ui_queue_depth: Current UI event queue depth
            state_queue_depth: Current state write queue depth
        
        Returns:
            Dictionary of health checks by name
        """
        checks = {}
        
        # MT5 Connection
        checks['mt5_connection'] = self._check_mt5_connection(mt5_connected)
        
        # State file
        checks['state_file'] = self._check_state_file()
        
        # Memory usage
        checks['memory'] = self._check_memory()
        
        # Disk space
        checks['disk_space'] = self._check_disk_space()
        
        # Queue depths
        checks['ui_queue'] = self._check_queue_depth(
            'UI Event Queue', 
            ui_queue_depth
        )
        checks['state_queue'] = self._check_queue_depth(
            'State Write Queue',
            state_queue_depth
        )
        
        self.last_check_time = datetime.now()
        self.check_history.append(checks)
        
        # Keep only last 100 checks
        if len(self.check_history) > 100:
            self.check_history = self.check_history[-100:]
        
        return checks
    
    def _check_mt5_connection(self, connected: bool) -> HealthCheck:
        """Check MT5 connection status."""
        if connected:
            return HealthCheck(
                name='MT5 Connection',
                status=HealthStatus.HEALTHY,
                message='Connected to MetaTrader 5'
            )
        else:
            return HealthCheck(
                name='MT5 Connection',
                status=HealthStatus.CRITICAL,
                message='Not connected to MetaTrader 5'
            )
    
    def _check_state_file(self) -> HealthCheck:
        """Check state file integrity and size."""
        try:
            if not self.state_file.exists():
                return HealthCheck(
                    name='State File',
                    status=HealthStatus.WARNING,
                    message='State file does not exist (will be created)'
                )
            
            # Check file size
            size_mb = self.state_file.stat().st_size / (1024 * 1024)
            
            # Check if file is valid JSON
            import json
            try:
                with open(self.state_file, 'r') as f:
                    json.load(f)
                
                if size_mb > 10.0:
                    return HealthCheck(
                        name='State File',
                        status=HealthStatus.WARNING,
                        message=f'State file is large ({size_mb:.2f} MB)',
                        value=size_mb,
                        threshold=10.0
                    )
                else:
                    return HealthCheck(
                        name='State File',
                        status=HealthStatus.HEALTHY,
                        message=f'State file OK ({size_mb:.2f} MB)',
                        value=size_mb
                    )
            
            except json.JSONDecodeError:
                return HealthCheck(
                    name='State File',
                    status=HealthStatus.CRITICAL,
                    message='State file corrupted (invalid JSON)'
                )
        
        except Exception as e:
            return HealthCheck(
                name='State File',
                status=HealthStatus.CRITICAL,
                message=f'Error checking state file: {str(e)}'
            )
    
    def _check_memory(self) -> HealthCheck:
        """Check memory usage."""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            if memory_mb > self.memory_threshold_mb:
                return HealthCheck(
                    name='Memory Usage',
                    status=HealthStatus.WARNING,
                    message=f'High memory usage: {memory_mb:.1f} MB',
                    value=memory_mb,
                    threshold=self.memory_threshold_mb
                )
            else:
                return HealthCheck(
                    name='Memory Usage',
                    status=HealthStatus.HEALTHY,
                    message=f'Memory usage OK: {memory_mb:.1f} MB',
                    value=memory_mb,
                    threshold=self.memory_threshold_mb
                )
        
        except Exception as e:
            return HealthCheck(
                name='Memory Usage',
                status=HealthStatus.UNKNOWN,
                message=f'Error checking memory: {str(e)}'
            )
    
    def _check_disk_space(self) -> HealthCheck:
        """Check available disk space."""
        try:
            disk = psutil.disk_usage(str(self.state_file.parent))
            free_gb = disk.free / (1024 ** 3)
            
            if free_gb < self.disk_threshold_gb:
                return HealthCheck(
                    name='Disk Space',
                    status=HealthStatus.CRITICAL,
                    message=f'Low disk space: {free_gb:.2f} GB free',
                    value=free_gb,
                    threshold=self.disk_threshold_gb
                )
            elif free_gb < self.disk_threshold_gb * 2:
                return HealthCheck(
                    name='Disk Space',
                    status=HealthStatus.WARNING,
                    message=f'Disk space low: {free_gb:.2f} GB free',
                    value=free_gb,
                    threshold=self.disk_threshold_gb
                )
            else:
                return HealthCheck(
                    name='Disk Space',
                    status=HealthStatus.HEALTHY,
                    message=f'Disk space OK: {free_gb:.1f} GB free',
                    value=free_gb,
                    threshold=self.disk_threshold_gb
                )
        
        except Exception as e:
            return HealthCheck(
                name='Disk Space',
                status=HealthStatus.UNKNOWN,
                message=f'Error checking disk: {str(e)}'
            )
    
    def _check_queue_depth(self, queue_name: str, depth: int) -> HealthCheck:
        """Check queue depth."""
        if depth > self.queue_depth_threshold:
            return HealthCheck(
                name=queue_name,
                status=HealthStatus.WARNING,
                message=f'{queue_name} is backed up ({depth} items)',
                value=float(depth),
                threshold=float(self.queue_depth_threshold)
            )
        else:
            return HealthCheck(
                name=queue_name,
                status=HealthStatus.HEALTHY,
                message=f'{queue_name} OK ({depth} items)',
                value=float(depth),
                threshold=float(self.queue_depth_threshold)
            )
    
    def get_overall_status(self, checks: Dict[str, HealthCheck]) -> HealthStatus:
        """
        Get overall system health status.
        
        Args:
            checks: Dictionary of health checks
        
        Returns:
            Overall health status (worst status from all checks)
        """
        statuses = [check.status for check in checks.values()]
        
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif HealthStatus.UNKNOWN in statuses:
            return HealthStatus.UNKNOWN
        else:
            return HealthStatus.HEALTHY
    
    def get_summary(self, checks: Dict[str, HealthCheck]) -> str:
        """
        Get health check summary.
        
        Args:
            checks: Dictionary of health checks
        
        Returns:
            Summary string
        """
        overall = self.get_overall_status(checks)
        
        critical = [c for c in checks.values() if c.status == HealthStatus.CRITICAL]
        warnings = [c for c in checks.values() if c.status == HealthStatus.WARNING]
        
        if overall == HealthStatus.HEALTHY:
            return "✓ All systems healthy"
        elif overall == HealthStatus.WARNING:
            return f"⚠ {len(warnings)} warning(s): {', '.join(c.name for c in warnings)}"
        elif overall == HealthStatus.CRITICAL:
            return f"✗ {len(critical)} critical issue(s): {', '.join(c.name for c in critical)}"
        else:
            return "? System status unknown"
    
    def get_history_stats(self) -> Dict:
        """
        Get statistics from check history.
        
        Returns:
            Dictionary with history statistics
        """
        if not self.check_history:
            return {}
        
        stats = {
            'total_checks': len(self.check_history),
            'healthy_count': 0,
            'warning_count': 0,
            'critical_count': 0,
            'last_check_time': self.last_check_time
        }
        
        for checks in self.check_history:
            overall = self.get_overall_status(checks)
            if overall == HealthStatus.HEALTHY:
                stats['healthy_count'] += 1
            elif overall == HealthStatus.WARNING:
                stats['warning_count'] += 1
            elif overall == HealthStatus.CRITICAL:
                stats['critical_count'] += 1
        
        return stats

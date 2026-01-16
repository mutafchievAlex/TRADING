"""
Performance Monitor - Track execution times and performance metrics

Monitors:
- Backtest execution time
- Entry condition evaluation time
- State persistence write time
- Connection check time
- Main loop execution time
"""

import logging
import time
from typing import Dict, Optional, List, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import statistics


logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of operations to monitor."""
    BACKTEST = "backtest"
    ENTRY_EVALUATION = "entry_evaluation"
    STATE_WRITE = "state_write"
    CONNECTION_CHECK = "connection_check"
    MAIN_LOOP = "main_loop"
    PATTERN_DETECTION = "pattern_detection"
    MARKET_DATA_FETCH = "market_data_fetch"


@dataclass
class PerformanceSample:
    """Single performance measurement."""
    operation: OperationType
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: Optional[str] = None


class PerformanceMetrics:
    """Performance metrics for a single operation type."""
    
    def __init__(self, operation: OperationType, max_samples: int = 1000):
        self.operation = operation
        self.max_samples = max_samples
        self.samples: deque = deque(maxlen=max_samples)
        self.total_calls = 0
        self.failed_calls = 0
    
    def add_sample(self, duration_ms: float, success: bool = True):
        """Add a performance sample."""
        self.samples.append(duration_ms)
        self.total_calls += 1
        if not success:
            self.failed_calls += 1
    
    def get_avg_ms(self) -> float:
        """Get average execution time."""
        if not self.samples:
            return 0.0
        return statistics.mean(self.samples)
    
    def get_min_ms(self) -> float:
        """Get minimum execution time."""
        if not self.samples:
            return 0.0
        return min(self.samples)
    
    def get_max_ms(self) -> float:
        """Get maximum execution time."""
        if not self.samples:
            return 0.0
        return max(self.samples)
    
    def get_p50_ms(self) -> float:
        """Get 50th percentile (median)."""
        if not self.samples:
            return 0.0
        return statistics.median(self.samples)
    
    def get_p95_ms(self) -> float:
        """Get 95th percentile."""
        if len(self.samples) < 2:
            return self.get_max_ms()
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * 0.95)
        return sorted_samples[idx]
    
    def get_p99_ms(self) -> float:
        """Get 99th percentile."""
        if len(self.samples) < 2:
            return self.get_max_ms()
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * 0.99)
        return sorted_samples[idx]
    
    def get_success_rate(self) -> float:
        """Get success rate (0-100%)."""
        if self.total_calls == 0:
            return 100.0
        return (self.total_calls - self.failed_calls) / self.total_calls * 100.0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete metrics summary."""
        return {
            'operation': self.operation.value,
            'total_calls': self.total_calls,
            'failed_calls': self.failed_calls,
            'success_rate': self.get_success_rate(),
            'avg_ms': self.get_avg_ms(),
            'min_ms': self.get_min_ms(),
            'max_ms': self.get_max_ms(),
            'p50_ms': self.get_p50_ms(),
            'p95_ms': self.get_p95_ms(),
            'p99_ms': self.get_p99_ms(),
            'sample_count': len(self.samples)
        }


class PerformanceMonitor:
    """
    Monitor performance of key operations.
    
    Tracks:
    - Execution times (min, max, avg, percentiles)
    - Success rates
    - Throughput
    - Bottleneck identification
    """
    
    def __init__(self, max_samples_per_operation: int = 1000):
        """
        Initialize performance monitor.
        
        Args:
            max_samples_per_operation: Keep last N samples per operation
        """
        self.metrics: Dict[OperationType, PerformanceMetrics] = {
            op: PerformanceMetrics(op, max_samples_per_operation)
            for op in OperationType
        }
        self.active_timers: Dict[str, float] = {}  # For nested/manual timing
        
        logger.info("PerformanceMonitor initialized")
    
    def start_timer(self, timer_name: str) -> float:
        """
        Start a manual timer.
        
        Args:
            timer_name: Unique timer identifier
        
        Returns:
            Start time (for reference)
        """
        self.active_timers[timer_name] = time.perf_counter()
        return self.active_timers[timer_name]
    
    def end_timer(
        self,
        timer_name: str,
        operation: OperationType,
        success: bool = True
    ) -> float:
        """
        End a manual timer and record measurement.
        
        Args:
            timer_name: Timer identifier (must match start_timer)
            operation: Operation type
            success: Whether operation succeeded
        
        Returns:
            Duration in milliseconds
        """
        if timer_name not in self.active_timers:
            logger.warning(f"Timer '{timer_name}' not found")
            return 0.0
        
        start_time = self.active_timers.pop(timer_name)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        
        self.metrics[operation].add_sample(duration_ms, success)
        
        return duration_ms
    
    def record_operation(
        self,
        operation: OperationType,
        duration_ms: float,
        success: bool = True
    ):
        """
        Record an operation execution time.
        
        Args:
            operation: Operation type
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
        """
        self.metrics[operation].add_sample(duration_ms, success)
    
    def get_metrics(self, operation: OperationType) -> Dict[str, Any]:
        """
        Get metrics for a specific operation.
        
        Args:
            operation: Operation type
        
        Returns:
            Dictionary with metrics summary
        """
        return self.metrics[operation].get_summary()
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metrics for all operations.
        
        Returns:
            Dictionary keyed by operation name
        """
        return {
            op.value: self.metrics[op].get_summary()
            for op in OperationType
        }
    
    def get_slowest_operations(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Get slowest operations by average execution time.
        
        Args:
            top_n: Number of operations to return
        
        Returns:
            List of operation metrics sorted by avg time (slowest first)
        """
        operations = [
            self.metrics[op].get_summary()
            for op in OperationType
            if self.metrics[op].total_calls > 0
        ]
        
        operations.sort(key=lambda x: x['avg_ms'], reverse=True)
        return operations[:top_n]
    
    def get_bottlenecks(self, percentile: int = 95) -> List[Dict[str, Any]]:
        """
        Get operations with high latency variability (bottlenecks).
        
        Identifies operations where p95/p99 is significantly higher than avg.
        
        Args:
            percentile: Which percentile to check (95 or 99)
        
        Returns:
            List of bottleneck operations
        """
        bottlenecks = []
        
        for op in OperationType:
            metrics = self.metrics[op]
            if metrics.total_calls < 10:  # Skip if too few samples
                continue
            
            if percentile == 95:
                p_val = metrics.get_p95_ms()
            else:
                p_val = metrics.get_p99_ms()
            
            avg = metrics.get_avg_ms()
            
            # Bottleneck if p95/p99 is 3x higher than average
            if avg > 0 and p_val > avg * 3:
                bottlenecks.append({
                    'operation': op.value,
                    'avg_ms': avg,
                    f'p{percentile}_ms': p_val,
                    'ratio': p_val / avg
                })
        
        bottlenecks.sort(key=lambda x: x['ratio'], reverse=True)
        return bottlenecks
    
    def get_performance_report(self) -> str:
        """
        Get human-readable performance report.
        
        Returns:
            Formatted performance summary
        """
        report = []
        report.append("\n" + "=" * 70)
        report.append("PERFORMANCE REPORT")
        report.append("=" * 70)
        
        # Summary by operation
        report.append("\nOPERATION METRICS:")
        report.append("-" * 70)
        
        for op in OperationType:
            metrics = self.metrics[op]
            if metrics.total_calls == 0:
                continue
            
            summary = metrics.get_summary()
            report.append(
                f"{op.value:25} | "
                f"Calls: {summary['total_calls']:5} | "
                f"Avg: {summary['avg_ms']:7.2f}ms | "
                f"P95: {summary['p95_ms']:7.2f}ms | "
                f"P99: {summary['p99_ms']:7.2f}ms | "
                f"Success: {summary['success_rate']:.1f}%"
            )
        
        # Slowest operations
        slowest = self.get_slowest_operations(3)
        if slowest:
            report.append("\nSLOWEST OPERATIONS:")
            report.append("-" * 70)
            for i, op in enumerate(slowest, 1):
                report.append(
                    f"{i}. {op['operation']:25} - "
                    f"Avg: {op['avg_ms']:.2f}ms "
                    f"({op['total_calls']} calls)"
                )
        
        # Bottlenecks
        bottlenecks = self.get_bottlenecks()
        if bottlenecks:
            report.append("\nBOTTLENECKS (P95 > 3x avg):")
            report.append("-" * 70)
            for bn in bottlenecks[:3]:
                report.append(
                    f"{bn['operation']:25} - "
                    f"Avg: {bn['avg_ms']:.2f}ms, "
                    f"P95: {bn['p95_ms']:.2f}ms "
                    f"(ratio: {bn['ratio']:.1f}x)"
                )
        
        report.append("=" * 70 + "\n")
        
        return "\n".join(report)
    
    def get_summary_string(self) -> str:
        """Get short performance summary."""
        slowest = self.get_slowest_operations(1)
        if not slowest:
            return "No performance data"
        
        op = slowest[0]
        return (
            f"Slowest: {op['operation']} "
            f"({op['avg_ms']:.1f}ms avg, {op['total_calls']} calls)"
        )

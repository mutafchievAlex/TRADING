"""
Trading Metrics Tracker - lightweight rolling metrics for live monitoring.

Tracks:
- Decisions per minute
- Order success rate
- Average latency
- Drawdown
"""

from collections import deque
import time
from typing import Deque, Dict, Optional


class MetricsTracker:
    """Track rolling trading metrics for monitoring and logging."""

    def __init__(self, max_latency_samples: int = 1000):
        self._decision_timestamps: Deque[float] = deque()
        self._latency_samples: Deque[float] = deque(maxlen=max_latency_samples)
        self._orders_total = 0
        self._orders_success = 0
        self._peak_equity = 0.0
        self._current_drawdown = 0.0

    def record_decision(self, timestamp: Optional[float] = None) -> None:
        """Record a decision timestamp for decisions/min tracking."""
        ts = timestamp if timestamp is not None else time.time()
        self._decision_timestamps.append(ts)
        self._prune_decisions(ts)

    def _prune_decisions(self, now: float) -> None:
        """Remove decision timestamps older than 60 seconds."""
        cutoff = now - 60.0
        while self._decision_timestamps and self._decision_timestamps[0] < cutoff:
            self._decision_timestamps.popleft()

    def record_order_result(self, success: bool) -> None:
        """Record an order result for success rate tracking."""
        self._orders_total += 1
        if success:
            self._orders_success += 1

    def record_latency_ms(self, latency_ms: float) -> None:
        """Record latency sample in milliseconds."""
        if latency_ms >= 0.0:
            self._latency_samples.append(latency_ms)

    def update_equity(self, equity: float) -> None:
        """Update drawdown tracking with latest equity."""
        if equity <= 0:
            return
        if equity > self._peak_equity:
            self._peak_equity = equity
            self._current_drawdown = 0.0
            return
        if self._peak_equity > 0:
            self._current_drawdown = (self._peak_equity - equity) / self._peak_equity * 100.0

    def get_metrics(self) -> Dict[str, float]:
        """Return current trading metrics snapshot."""
        now = time.time()
        self._prune_decisions(now)
        decisions_per_min = float(len(self._decision_timestamps))
        if self._orders_total > 0:
            order_success_rate = (self._orders_success / self._orders_total) * 100.0
        else:
            order_success_rate = 0.0
        avg_latency = (
            sum(self._latency_samples) / len(self._latency_samples)
            if self._latency_samples
            else 0.0
        )
        return {
            "decisions_per_min": decisions_per_min,
            "order_success_rate": order_success_rate,
            "avg_latency_ms": avg_latency,
            "drawdown_percent": self._current_drawdown,
        }

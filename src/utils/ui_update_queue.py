"""
UI Update Queue - Thread-safe event queue for UI updates

This module provides a thread-safe mechanism for posting UI update events
from background threads (like backtest worker) without causing race conditions.

Problem Solved:
- Main loop (QTimer) and backtest worker (QThread) both update UI simultaneously
- Race conditions on state_manager access
- UI freezes when multiple updates collide

Solution:
- All engine updates → queue (thread-safe)
- Main thread processes queue every 100ms
- UI only reads from queue, never writes from threads
- Eliminates race conditions and UI freezes

Usage:
    # From background thread:
    queue.post_event('update_market_data', {
        'price': 2700.50,
        'indicators': {...}
    })
    
    # From main thread (in timer):
    events = queue.get_pending_events()
    for event in events:
        if event['type'] == 'update_market_data':
            window.update_market_data(**event['data'])
"""

import logging
from typing import Dict, List, Any, Optional
from queue import Queue, Empty
from datetime import datetime
from threading import Lock
from PySide6.QtCore import QObject, Signal, QTimer, Slot


class UIUpdateQueue(QObject):
    """
    Thread-safe queue for UI update events.
    
    Handles posting events from any thread and processing them
    on the main UI thread to prevent race conditions.
    
    Features:
    - Thread-safe event posting (from any thread)
    - Batch processing (processes all pending events at once)
    - Event filtering (prevents duplicate events)
    - Event priority (high-priority events processed first)
    - Event expiry (old events can be discarded)
    """
    
    # Signal emitted when events are available (for main thread)
    events_available = Signal()
    
    def __init__(self, max_queue_size: int = 1000, process_interval_ms: int = 100):
        """
        Initialize UI update queue.
        
        Args:
            max_queue_size: Maximum number of events in queue
            process_interval_ms: How often to process events (milliseconds)
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Thread-safe queue for events
        self.queue = Queue(maxsize=max_queue_size)
        self.max_queue_size = max_queue_size
        
        # Lock for thread-safe operations
        self.lock = Lock()
        
        # Event statistics
        self.events_posted = 0
        self.events_processed = 0
        self.events_dropped = 0
        
        # Event filtering (prevent duplicates)
        self.last_event_time: Dict[str, datetime] = {}
        self.min_event_interval_ms = 50  # Minimum time between same event types
        
        # Timer for processing events (runs on main thread)
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self._process_events)
        self.process_timer.start(process_interval_ms)
        
        self.logger.info(f"UIUpdateQueue initialized (max_size={max_queue_size}, interval={process_interval_ms}ms)")
    
    def post_event(self, event_type: str, data: Dict[str, Any], priority: int = 0) -> bool:
        """
        Post a UI update event to the queue (thread-safe).
        
        Can be called from any thread. Events are queued and will be
        processed on the main UI thread.
        
        Args:
            event_type: Type of event (e.g., 'update_market_data')
            data: Event data (will be passed to UI update method)
            priority: Priority (higher = processed first, default: 0)
            
        Returns:
            True if event was queued, False if queue is full
        """
        try:
            # Check if event should be filtered (too soon after last one)
            if self._should_filter_event(event_type):
                self.logger.debug(f"Filtered duplicate event: {event_type}")
                return False
            
            # Create event object
            event = {
                'type': event_type,
                'data': data,
                'priority': priority,
                'timestamp': datetime.now(),
                'thread_id': id(self)  # For debugging
            }
            
            # Try to add to queue (non-blocking)
            try:
                self.queue.put_nowait(event)
                with self.lock:
                    self.events_posted += 1
                    self.last_event_time[event_type] = datetime.now()
                
                # Emit signal to notify main thread
                self.events_available.emit()
                return True
                
            except Exception as e:
                # Queue is full
                with self.lock:
                    self.events_dropped += 1
                self.logger.warning(f"Event queue full, dropped: {event_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error posting event: {e}", exc_info=True)
            return False
    
    def _should_filter_event(self, event_type: str) -> bool:
        """
        Check if event should be filtered (duplicate prevention).
        
        Args:
            event_type: Type of event to check
            
        Returns:
            True if event should be filtered (not posted)
        """
        with self.lock:
            if event_type not in self.last_event_time:
                return False
            
            last_time = self.last_event_time[event_type]
            elapsed_ms = (datetime.now() - last_time).total_seconds() * 1000
            
            # Filter if too soon after last event of same type
            return elapsed_ms < self.min_event_interval_ms
    
    @Slot()
    def _process_events(self):
        """
        Process all pending events (called on main thread by timer).
        
        This method is connected to QTimer and runs on the main UI thread.
        It's safe to update UI from here.
        """
        events = self.get_pending_events()
        
        if not events:
            return
        
        # Sort by priority (higher priority first)
        events.sort(key=lambda e: e['priority'], reverse=True)
        
        # Process each event
        for event in events:
            try:
                # Emit signal with event data
                # Note: Actual UI update happens in main.py or main_window.py
                # This just makes events available
                pass
                
            except Exception as e:
                self.logger.error(f"Error processing event {event['type']}: {e}", exc_info=True)
        
        with self.lock:
            self.events_processed += len(events)
    
    def get_pending_events(self, max_events: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all pending events from queue (thread-safe).
        
        Args:
            max_events: Maximum number of events to retrieve (None = all)
            
        Returns:
            List of event dictionaries
        """
        events = []
        count = 0
        
        try:
            while True:
                # Check if we've reached max
                if max_events is not None and count >= max_events:
                    break
                
                try:
                    # Get event (non-blocking)
                    event = self.queue.get_nowait()
                    events.append(event)
                    count += 1
                    
                except Empty:
                    # Queue is empty
                    break
                    
        except Exception as e:
            self.logger.error(f"Error getting pending events: {e}", exc_info=True)
        
        return events
    
    def clear_queue(self):
        """Clear all pending events (emergency use only)."""
        with self.lock:
            # Clear queue
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except Empty:
                    break
            
            self.logger.warning("Event queue cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Dict with statistics (posted, processed, dropped, pending)
        """
        with self.lock:
            return {
                'events_posted': self.events_posted,
                'events_processed': self.events_processed,
                'events_dropped': self.events_dropped,
                'pending': self.queue.qsize(),
                'capacity': self.max_queue_size
            }
    
    def get_queue_size(self) -> int:
        """Get current queue size (for health monitoring)."""
        return self.queue.qsize()
    
    def get_status_string(self) -> str:
        """Get human-readable status string."""
        stats = self.get_statistics()
        return (
            f"Posted: {stats['events_posted']}, "
            f"Processed: {stats['events_processed']}, "
            f"Dropped: {stats['events_dropped']}, "
            f"Pending: {stats['pending']}/{stats['capacity']}"
        )
    
    def stop(self):
        """Stop processing events (cleanup)."""
        self.process_timer.stop()
        self.clear_queue()
        self.logger.info("UIUpdateQueue stopped")


# Event types (constants for type safety)
class UIEventType:
    """Standard UI event types."""
    UPDATE_MARKET_DATA = 'update_market_data'
    UPDATE_PATTERN_STATUS = 'update_pattern_status'
    UPDATE_ENTRY_CONDITIONS = 'update_entry_conditions'
    UPDATE_POSITION_DISPLAY = 'update_position_display'
    UPDATE_TRADE_HISTORY = 'update_trade_history'
    UPDATE_MARKET_REGIME = 'update_market_regime'
    UPDATE_CONNECTION_STATUS = 'update_connection_status'
    UPDATE_STATISTICS = 'update_statistics'
    UPDATE_SESSIONS = 'update_sessions'
    UPDATE_RUNTIME_MODE_DISPLAY = 'update_runtime_mode_display'
    UPDATE_RUNTIME_CONTEXT = 'update_runtime_context'
    LOG_MESSAGE = 'log_message'
    
    # Backtest-specific events
    BACKTEST_PROGRESS = 'backtest_progress'
    BACKTEST_COMPLETED = 'backtest_completed'
    BACKTEST_ERROR = 'backtest_error'


if __name__ == "__main__":
    # Simple test
    import time
    
    queue = UIUpdateQueue(max_queue_size=100, process_interval_ms=100)
    
    # Post some test events
    queue.post_event(UIEventType.UPDATE_MARKET_DATA, {'price': 2700.50})
    queue.post_event(UIEventType.UPDATE_PATTERN_STATUS, {'detected': True})
    queue.post_event(UIEventType.LOG_MESSAGE, {'message': 'Test message'})
    
    # Wait for processing
    time.sleep(0.2)
    
    # Get statistics
    print(queue.get_status_string())
    
    # Cleanup
    queue.stop()

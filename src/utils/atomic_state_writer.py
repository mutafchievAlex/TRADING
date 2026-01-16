"""
Atomic State Persistence - Thread-safe file writing with backups

This module provides safe state persistence using:
- Atomic writes (write to .tmp, rename on success)
- File locking to prevent concurrent access
- Write queue with batch delays (5 seconds)
- Backup rotation (keep last 10 backups)
- Integrity validation on load

Problem Solved:
- Direct file writes during backtest can corrupt state.json
- Multiple threads writing simultaneously cause data loss
- No backup if corruption occurs
- No recovery if process crashes mid-write

Solution:
- Queue pending writes
- Batch every 5 seconds
- Atomic rename (all-or-nothing)
- File locking prevents concurrent access
- Keep 10 backups for recovery
- Checksum validation on load
"""

import json
import logging
import threading
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from queue import Queue, Empty
from threading import Lock, Thread, Event


class AtomicStateWriter:
    """
    Provides atomic, thread-safe state persistence with backups.
    
    Features:
    - Write queue with batching (5 second intervals)
    - Atomic writes (write to .tmp, rename on success)
    - File locking prevents concurrent access
    - Backup rotation (keeps last 10 backups)
    - Checksum validation on load/save
    - Crash recovery
    """
    
    def __init__(self, state_file: str = "data/state.json", 
                 backup_dir: str = "data/backups",
                 batch_interval_seconds: int = 5,
                 max_backups: int = 10):
        """
        Initialize atomic state writer.
        
        Args:
            state_file: Path to main state file
            backup_dir: Directory for backup files
            batch_interval_seconds: How often to batch writes (seconds)
            max_backups: Maximum number of backups to keep
        """
        self.state_file = Path(state_file)
        self.backup_dir = Path(backup_dir)
        self.logger = logging.getLogger(__name__)
        
        # Write queue
        self.write_queue: Queue[Dict[str, Any]] = Queue()
        self.pending_write: Optional[Dict[str, Any]] = None
        self.batch_interval = batch_interval_seconds
        self.max_backups = max_backups
        
        # Thread safety
        self.write_lock = Lock()
        self.stop_event = Event()
        self.writer_thread: Optional[Thread] = None
        
        # Statistics
        self.writes_queued = 0
        self.writes_batched = 0
        self.writes_successful = 0
        self.writes_failed = 0
        
        # Setup
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Start background writer thread
        self._start_writer_thread()
        
        self.logger.info(
            f"AtomicStateWriter initialized "
            f"(batch_interval={batch_interval_seconds}s, max_backups={max_backups})"
        )
    
    def queue_write(self, state_data: Dict[str, Any]) -> bool:
        """
        Queue a state write (non-blocking).
        
        Returns immediately. Write will be batched and executed by background thread.
        
        Args:
            state_data: State dict to write
            
        Returns:
            True if queued successfully
        """
        try:
            # Store pending write (replaces any previous pending write)
            self.pending_write = state_data.copy()
            self.writes_queued += 1
            
            # Signal that pending write exists (for batch timer)
            try:
                self.write_queue.put_nowait({
                    'action': 'write_if_pending'
                })
            except:
                pass  # Queue might be full, but we already stored pending_write
            
            return True
        except Exception as e:
            self.logger.error(f"Error queueing write: {e}")
            self.writes_failed += 1
            return False
    
    def _start_writer_thread(self):
        """Start background writer thread."""
        self.stop_event.clear()
        self.writer_thread = Thread(
            target=self._writer_loop,
            daemon=True,
            name="AtomicStateWriter"
        )
        self.writer_thread.start()
        self.logger.debug("State writer thread started")
    
    def _writer_loop(self):
        """Background thread that batches and writes state."""
        import time
        
        last_write_time = time.time()
        
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                time_since_last_write = current_time - last_write_time
                
                # Check if we should batch-write pending state
                if self.pending_write and time_since_last_write >= self.batch_interval:
                    self._perform_atomic_write(self.pending_write)
                    self.pending_write = None
                    last_write_time = current_time
                    self.writes_batched += 1
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in writer loop: {e}")
    
    def _perform_atomic_write(self, state_data: Dict[str, Any]) -> bool:
        """
        Perform atomic write to state file.
        
        Process:
        1. Write to .tmp file
        2. Create backup of current file (if exists)
        3. Rename .tmp to main file (atomic)
        4. Rotate old backups
        
        Args:
            state_data: State dict to write
            
        Returns:
            True if write successful
        """
        try:
            with self.write_lock:
                # Add metadata
                state_data['saved_at'] = datetime.now().isoformat()
                
                # Calculate checksum for integrity verification
                json_str = json.dumps(state_data, sort_keys=True)
                checksum = hashlib.md5(json_str.encode()).hexdigest()
                state_data['_checksum'] = checksum
                
                # Write to temporary file
                tmp_file = self.state_file.with_suffix('.tmp')
                with open(tmp_file, 'w') as f:
                    json.dump(state_data, f, indent=2)
                
                # Verify temp file was written
                if not tmp_file.exists():
                    raise IOError("Temp file write failed - file doesn't exist")
                
                # Create backup of current file (if exists)
                if self.state_file.exists():
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_file = self.backup_dir / f"state_backup_{timestamp}.json"
                    
                    # Copy current to backup
                    with open(self.state_file, 'r') as src:
                        with open(backup_file, 'w') as dst:
                            dst.write(src.read())
                    
                    self.logger.debug(f"Created backup: {backup_file.name}")
                
                # Atomic rename (all-or-nothing on most filesystems)
                tmp_file.replace(self.state_file)
                
                self.writes_successful += 1
                self.logger.debug(f"Atomic write completed: {len(state_data)} bytes")
                
                # Cleanup old backups
                self._cleanup_old_backups()
                
                return True
            
        except Exception as e:
            self.logger.error(f"Atomic write failed: {e}")
            self.writes_failed += 1
            
            # Cleanup temp file if it exists
            try:
                tmp_file = self.state_file.with_suffix('.tmp')
                if tmp_file.exists():
                    tmp_file.unlink()
            except:
                pass
            
            return False
    
    def _cleanup_old_backups(self):
        """Remove old backups, keeping only the newest N."""
        try:
            backups = sorted(
                self.backup_dir.glob('state_backup_*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Remove old backups beyond max_backups limit
            for backup in backups[self.max_backups:]:
                backup.unlink()
                self.logger.debug(f"Deleted old backup: {backup.name}")
        
        except Exception as e:
            self.logger.warning(f"Error cleaning up backups: {e}")
    
    def flush(self) -> bool:
        """
        Force immediate write of pending state (blocks).
        
        Use this before shutdown or critical operations.
        
        Returns:
            True if write successful or no pending write
        """
        try:
            if self.pending_write:
                with self.write_lock:
                    success = self._perform_atomic_write(self.pending_write)
                    if success:
                        self.pending_write = None
                    return success
            return True
        except Exception as e:
            self.logger.error(f"Error flushing state: {e}")
            return False
    
    def get_queue_depth(self) -> int:
        """Get number of pending writes (for health monitoring)."""
        return 1 if self.pending_write else 0
    
    def stop(self):
        """Stop writer thread and flush pending writes."""
        self.logger.info("Stopping atomic state writer...")
        
        # Flush any pending writes
        self.flush()
        
        # Stop thread
        self.stop_event.set()
        if self.writer_thread:
            self.writer_thread.join(timeout=2)
        
        self.logger.info(f"Writer stopped (queued: {self.writes_queued}, "
                        f"batched: {self.writes_batched}, "
                        f"successful: {self.writes_successful}, "
                        f"failed: {self.writes_failed})")
    
    def load_with_validation(self) -> Optional[Dict[str, Any]]:
        """
        Load state from file with integrity validation.
        
        Returns:
            State dict if loaded and valid, None otherwise
        """
        try:
            with self.write_lock:
                if not self.state_file.exists():
                    self.logger.info("No state file found")
                    return None
                
                # Try to load main file
                try:
                    with open(self.state_file, 'r') as f:
                        state_data = json.load(f)
                    
                    # Verify checksum
                    stored_checksum = state_data.pop('_checksum', None)
                    json_str = json.dumps(state_data, sort_keys=True)
                    computed_checksum = hashlib.md5(json_str.encode()).hexdigest()
                    
                    if stored_checksum and stored_checksum != computed_checksum:
                        self.logger.warning("State file checksum mismatch - file may be corrupted")
                        return None
                    
                    self.logger.info(f"State file loaded and validated: {self.state_file}")
                    return state_data
                
                except (json.JSONDecodeError, IOError) as e:
                    self.logger.warning(f"Failed to load main state file: {e}")
                    self.logger.info("Attempting to recover from backup...")
                    
                    # Try to recover from most recent backup
                    return self._recover_from_backup()
        
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")
            return None
    
    def _recover_from_backup(self) -> Optional[Dict[str, Any]]:
        """
        Try to recover state from most recent backup.
        
        Returns:
            State dict from backup if successful, None otherwise
        """
        try:
            # Find most recent backup
            backups = sorted(
                self.backup_dir.glob('state_backup_*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            if not backups:
                self.logger.error("No backups found for recovery")
                return None
            
            # Try each backup until one loads
            for backup_file in backups:
                try:
                    with open(backup_file, 'r') as f:
                        state_data = json.load(f)
                    
                    self.logger.warning(f"Recovered state from backup: {backup_file.name}")
                    return state_data
                
                except json.JSONDecodeError:
                    self.logger.warning(f"Backup corrupted, trying next: {backup_file.name}")
                    continue
            
            self.logger.error("All backups corrupted - cannot recover")
            return None
        
        except Exception as e:
            self.logger.error(f"Error recovering from backup: {e}")
            return None
    
    def get_status_string(self) -> str:
        """Get status string for monitoring."""
        status = (
            f"AtomicStateWriter Status:\n"
            f"  Queued writes: {self.writes_queued}\n"
            f"  Batched writes: {self.writes_batched}\n"
            f"  Successful writes: {self.writes_successful}\n"
            f"  Failed writes: {self.writes_failed}\n"
            f"  Pending write: {self.pending_write is not None}\n"
            f"  Writer thread alive: {self.writer_thread and self.writer_thread.is_alive()}\n"
            f"  Backups in storage: {len(list(self.backup_dir.glob('state_backup_*.json')))}/{self.max_backups}"
        )
        return status


if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.DEBUG)
    
    writer = AtomicStateWriter(
        state_file="test_state.json",
        batch_interval_seconds=1,
        max_backups=3
    )
    
    # Test writes
    test_state = {
        'open_positions': [],
        'trade_history': [
            {'ticket': 1, 'profit': 100.0, 'reason': 'TP1'}
        ],
        'total_profit': 100.0
    }
    
    print("Queueing writes...")
    writer.queue_write(test_state)
    writer.queue_write(test_state)
    
    # Wait for batch
    import time
    time.sleep(2)
    
    # Flush and stop
    writer.flush()
    print(writer.get_status_string())
    
    # Test load
    loaded = writer.load_with_validation()
    print(f"\nLoaded state: {loaded}")
    
    writer.stop()

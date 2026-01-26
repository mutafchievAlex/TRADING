"""
State Manager - Tracks open positions, trade history, and cooldowns

This module maintains the state of the trading system:
- Current open position (if any)
- Trade history
- Cooldown tracking
- Performance statistics
- Atomic persistence with backups
"""

import json
import logging
import threading
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
from utils.atomic_state_writer import AtomicStateWriter, SafeJSONEncoder
from storage.state_database import StateDatabase


class StateManager:
    """
    Manages trading system state and persistence.
    
    Responsibilities:
    - Track current position
    - Store trade history
    - Manage cooldown periods
    - Calculate performance metrics
    - Persist state to disk (atomic, thread-safe)
    """
    
    def __init__(
        self,
        state_file: str = "data/state.json",
        backup_dir: str = "data/backups",
        use_atomic_writes: bool = True,
        storage_backend: str = "file",
        db_url: Optional[str] = None,
        dev_mode: bool = True,
    ):
        """
        Initialize State Manager.
        
        Args:
            state_file: Path to state persistence file
            backup_dir: Directory for state backups
            use_atomic_writes: Use atomic writes with file locking (recommended)
        """
        self.state_file = Path(state_file)
        self.logger = logging.getLogger(__name__)
        self.use_atomic_writes = use_atomic_writes
        self.storage_backend = storage_backend
        self.db_url = db_url
        self.dev_mode = dev_mode
        self.db_store: Optional[StateDatabase] = None
        
        # Threading lock for synchronized indicator/state updates (prevents race conditions)
        self._state_lock = threading.RLock()

        if self.dev_mode and self.storage_backend != "file":
            self.logger.warning(
                "Dev mode enabled; falling back to file storage backend."
            )
            self.storage_backend = "file"
        
        # Initialize atomic writer if enabled (file storage only)
        if self.storage_backend == "file" and use_atomic_writes:
            self.atomic_writer = AtomicStateWriter(
                state_file=str(state_file),
                backup_dir=backup_dir,
                batch_interval_seconds=5,
                max_backups=10,
            )
        else:
            self.atomic_writer = None

        if self.storage_backend == "db":
            try:
                resolved_db_url = db_url or "sqlite:///data/state.db"
                self.db_store = StateDatabase(resolved_db_url, self.logger)
            except Exception as exc:
                self.logger.error("DB storage unavailable: %s", exc)
                self.storage_backend = "file"
        
        # Current state - support multiple positions for pyramiding
        self.open_positions: List[Dict] = []  # Changed from single position to list
        self.trade_history: List[Dict] = []
        self.last_trade_time: Optional[datetime] = None
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.total_profit: float = 0.0
        # Persisted market regime state
        self.last_regime_state: Optional[Dict] = None
        
        # Load existing state if available
        self.load_state()
    
    def open_position(self, position_data: Dict):
        """
        Register a new open position (supports pyramiding).
        
        Thread-safe: Uses lock to prevent race conditions during concurrent updates.
        
        Args:
            position_data: Dict with position details
                Required keys: ticket, entry_price, stop_loss, take_profit, volume
        """
        try:
            with self._state_lock:
                new_position = {
                'ticket': position_data['ticket'],
                'entry_price': position_data['entry_price'],
                'stop_loss': position_data['stop_loss'],
                'take_profit': position_data['take_profit'],
                'volume': position_data['volume'],
                'entry_time': position_data.get('entry_time', datetime.now()),
                'pattern_info': position_data.get('pattern_info'),
                'atr': position_data.get('atr'),
                'tp_level': position_data.get('tp_level'),
                'tp_value': position_data.get('tp_value'),
                'risk_cash': position_data.get('risk_cash'),
                'tp1_cash': position_data.get('tp1_cash'),
                'tp2_cash': position_data.get('tp2_cash'),
                'tp3_cash': position_data.get('tp3_cash'),
                # Multi-level TP state tracking
                'tp_state': position_data.get('tp_state', 'IN_TRADE'),
                'tp1_price': position_data.get('tp1_price'),
                'tp2_price': position_data.get('tp2_price'),
                'tp3_price': position_data.get('tp3_price'),
                'current_stop_loss': position_data.get('current_stop_loss', position_data['stop_loss']),
                'direction': position_data.get('direction', 1),  # +1 for LONG, -1 for SHORT
                # TP1 exit decision tracking
                'tp1_reached': position_data.get('tp1_reached', False),
                'post_tp1_decision': position_data.get('post_tp1_decision', 'NOT_REACHED'),
                'tp1_reached_timestamp': position_data.get('tp1_reached_timestamp'),
                'bars_held_after_tp1': position_data.get('bars_held_after_tp1', 0),
                'max_extension_after_tp1': position_data.get('max_extension_after_tp1', 0.0),
                'tp1_exit_reason': position_data.get('tp1_exit_reason'),
                # TP2 exit decision tracking
                'tp2_reached': position_data.get('tp2_reached', False),
                'post_tp2_decision': position_data.get('post_tp2_decision', 'NOT_REACHED'),
                'tp2_reached_timestamp': position_data.get('tp2_reached_timestamp'),
                'bars_held_after_tp2': position_data.get('bars_held_after_tp2', 0),
                'max_extension_after_tp2': position_data.get('max_extension_after_tp2', 0.0),
                'tp2_exit_reason': position_data.get('tp2_exit_reason'),
                # Live broker fields (optional)
                'price_current': position_data.get('price_current'),
                'profit': position_data.get('profit'),
                'swap': position_data.get('swap'),
            }
            
            self.open_positions.append(new_position)
            
            # Update last_trade_time to the more recent of open or close event
            # This ensures cooldown tracks the latest trading activity
            entry_time = new_position['entry_time']
            entry_datetime = entry_time if isinstance(entry_time, datetime) else datetime.fromisoformat(entry_time)
            if self.last_trade_time is None or entry_datetime > self.last_trade_time:
                self.last_trade_time = entry_time
            
            self.logger.info(f"Position opened: Ticket={new_position['ticket']}, "
                           f"Entry={new_position['entry_price']:.2f}, "
                           f"TP State={new_position['tp_state']}, "
                           f"Total open: {len(self.open_positions)}")
            
            self.save_state()
            
        except Exception as e:
            self.logger.error(f"Error opening position: {e}")
    
    def close_position(self, exit_price: float, exit_reason: str,
                      exit_time: Optional[datetime] = None, ticket: Optional[int] = None,
                      symbol_info: Optional[Dict] = None, risk_engine: Optional[object] = None,
                      swap: Optional[float] = None):
        """
        Close a position and record the trade (thread-safe).
        
        Args:
            exit_price: Exit price
            exit_reason: Reason for exit ("Stop Loss", "Take Profit", etc.)
            exit_time: Exit timestamp (default: now)
            ticket: Specific ticket to close (if None, close first position)
            symbol_info: Optional symbol metadata for accurate P&L
            risk_engine: Optional risk engine for commission calculation
            swap: Optional swap value from broker
        """
        try:
            with self._state_lock:
                if not self.open_positions:
                    self.logger.warning("No positions to close")
                    return
                
                if exit_time is None:
                    exit_time = datetime.now()
                
                # Find position to close
                position_to_close = None
                if ticket:
                    for pos in self.open_positions:
                        if pos['ticket'] == ticket:
                            position_to_close = pos
                            break
                else:
                    position_to_close = self.open_positions[0]  # Close first position
                
                if not position_to_close:
                    self.logger.warning(f"Position with ticket {ticket} not found")
                    return
                
                # Calculate P&L
                entry_price = position_to_close['entry_price']
                volume = position_to_close['volume']
                direction = position_to_close.get('direction', 1)
                price_diff = (exit_price - entry_price) * direction

                contract_size = 100.0
                point_value = None
                if symbol_info:
                    contract_size = symbol_info.get('trade_contract_size', contract_size)
                    tick_value = symbol_info.get('tick_value')
                    tick_size = symbol_info.get('tick_size') or symbol_info.get('point')
                    if tick_value is not None and tick_size:
                        point_value = tick_value / tick_size

                if point_value is None:
                    point_value = contract_size

                commission_total = 0.0
                if risk_engine and symbol_info:
                    adjusted_exit = exit_price if direction == 1 else (entry_price - (exit_price - entry_price))
                    pl_result = risk_engine.calculate_potential_profit_loss(
                        position_size=volume,
                        entry_price=entry_price,
                        exit_price=adjusted_exit,
                        symbol_info=symbol_info
                    )
                    gross_pl = pl_result.get('gross_pl', 0.0)
                    commission_total = pl_result.get('commission', 0.0)
                else:
                    gross_pl = price_diff * volume * point_value
                    if risk_engine:
                        commission_total = risk_engine.commission_per_lot * volume * 2
                    elif position_to_close.get('commission') is not None:
                        commission_total = position_to_close.get('commission', 0.0)

                if point_value is not None and point_value != contract_size:
                    gross_pl = price_diff * volume * point_value

                swap_value = swap if swap is not None else position_to_close.get('swap', 0.0)
                net_pl = gross_pl - commission_total + swap_value

                normalized_exit_reason = self._normalize_exit_reason(exit_reason)
                
                # Create trade record
                trade_record = {
                    'ticket': position_to_close['ticket'],
                    'entry_time': position_to_close['entry_time'].isoformat() 
                                 if isinstance(position_to_close['entry_time'], datetime) 
                                 else position_to_close['entry_time'],
                    'exit_time': exit_time.isoformat() if isinstance(exit_time, datetime) else exit_time,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'stop_loss': position_to_close['stop_loss'],
                    'take_profit': position_to_close['take_profit'],
                    'volume': volume,
                    'profit': net_pl,
                    'gross_pl': gross_pl,
                    'commission': commission_total,
                    'swap': swap_value,
                    'net_pl': net_pl,
                    'exit_reason': normalized_exit_reason,
                    'pattern_info': position_to_close.get('pattern_info'),
                    'is_winner': net_pl > 0
                }
                
                # Debug log - verify exit_reason is text, not a price
                self.logger.info(f"Trade record created: ticket={trade_record['ticket']}, "
                               f"exit_reason='{normalized_exit_reason}' (type: {type(normalized_exit_reason).__name__}), "
                               f"take_profit={trade_record['take_profit']}")
                
                # Update statistics
                self.trade_history.append(trade_record)
                self.total_trades += 1
                self.total_profit += net_pl
                
                if net_pl > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1
                
                self.logger.info(f"Position closed: Ticket={trade_record['ticket']}, "
                               f"Profit=${net_pl:.2f}, Reason={normalized_exit_reason}, "
                               f"Remaining: {len(self.open_positions)-1}")
                
                # Remove closed position
                self.open_positions.remove(position_to_close)
                
                # Update last_trade_time to exit time for cooldown calculation
                # Cooldown should be from the LATEST event (open or close), whichever is more recent
                exit_datetime = exit_time if isinstance(exit_time, datetime) else datetime.fromisoformat(exit_time)
                if self.last_trade_time is None or exit_datetime > self.last_trade_time:
                    self.last_trade_time = exit_time
                
                self.save_state()
            
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")

    @staticmethod
    def _normalize_exit_reason(exit_reason: Optional[object]) -> str:
        """Ensure exit reason is a readable string (never numeric)."""
        if exit_reason is None:
            return "Unknown"
        if isinstance(exit_reason, (int, float)):
            return f"Exit price {exit_reason:.2f}"
        return str(exit_reason)
    
    def has_open_position(self) -> bool:
        """Check if there are any open positions."""
        return len(self.open_positions) > 0
    
    def get_position_count(self) -> int:
        """Get number of open positions."""
        return len(self.open_positions)
    
    def can_open_new_position(self, max_positions: int = 1) -> bool:
        """
        Check if a new position can be opened based on pyramiding limit.
        
        Args:
            max_positions: Maximum allowed positions (pyramiding setting)
        
        Returns:
            True if can open new position
        """
        return len(self.open_positions) < max_positions
    
    def get_current_position(self) -> Optional[Dict]:
        """Get first open position details (for backwards compatibility)."""
        return self.open_positions[0] if self.open_positions else None
    
    def get_all_positions(self) -> List[Dict]:
        """Get all open positions."""
        return self.open_positions.copy()
    
    def update_position_tp_state(self, ticket: int, new_tp_state: str, 
                                 new_stop_loss: Optional[float] = None,
                                 transition_time: Optional[datetime] = None,
                                 bars_after_tp1: Optional[int] = None,
                                 bars_after_tp2: Optional[int] = None) -> bool:
        """
        Update TP state and optionally stop loss for a position.
        
        Args:
            ticket: Position ticket number
            new_tp_state: New TP state (IN_TRADE, TP1_REACHED, TP2_REACHED, EXITED)
            new_stop_loss: New stop loss price (optional)
            transition_time: Time of transition (optional)
            bars_after_tp1: Update bar counter after TP1 (MEDIUM: BARS_AFTER_TP_NOT_INCREMENTING)
            bars_after_tp2: Update bar counter after TP2 (MEDIUM: BARS_AFTER_TP_NOT_INCREMENTING)
            
        Returns:
            True if updated, False if position not found
        """
        try:
            for position in self.open_positions:
                if position['ticket'] == ticket:
                    old_state = position.get('tp_state', 'IN_TRADE')
                    position['tp_state'] = new_tp_state
                    if transition_time is not None:
                        position['tp_state_changed_at'] = transition_time
                    
                    if new_stop_loss is not None:
                        position['current_stop_loss'] = new_stop_loss
                    
                    # MEDIUM: BARS_AFTER_TP_NOT_INCREMENTING - Persist bar counters (NEW)
                    if bars_after_tp1 is not None:
                        position['bars_held_after_tp1'] = bars_after_tp1
                    if bars_after_tp2 is not None:
                        position['bars_held_after_tp2'] = bars_after_tp2

                    sl_text = f"{new_stop_loss:.2f}" if new_stop_loss is not None else "N/A"
                        
                    self.logger.info(f"Ticket {ticket}: TP state {old_state} -> {new_tp_state}, "
                                   f"SL updated to {sl_text}")
                    
                    # Optimize DB update - only update changed position
                    if self.storage_backend == "db" and self.db_store:
                        updates = {'tp_state': new_tp_state}
                        if transition_time is not None:
                            updates['tp_state_changed_at'] = transition_time
                        if new_stop_loss is not None:
                            updates['current_stop_loss'] = new_stop_loss
                        if bars_after_tp1 is not None:
                            updates['bars_held_after_tp1'] = bars_after_tp1
                        if bars_after_tp2 is not None:
                            updates['bars_held_after_tp2'] = bars_after_tp2
                        self.db_store.update_position(ticket, updates)
                    else:
                        self.save_state()
                    
                    return True
            
            self.logger.warning(f"Position ticket {ticket} not found")
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating TP state: {e}")
            return False
    
    def update_tp_exit_metadata(self, ticket: int,
                                post_tp1_decision: Optional[str] = None,
                                tp1_exit_reason: Optional[str] = None,
                                post_tp2_decision: Optional[str] = None,
                                tp2_exit_reason: Optional[str] = None,
                                trailing_sl_level: Optional[float] = None,
                                trailing_sl_enabled: Optional[bool] = None) -> bool:
        """
        Update TP1/TP2 exit decision metadata for a position.
        
        Args:
            ticket: Position ticket number
            post_tp1_decision: TP1 decision (HOLD, WAIT_NEXT_BAR, EXIT_TRADE)
            tp1_exit_reason: Reason for TP1 decision
            post_tp2_decision: TP2 decision (HOLD, WAIT_NEXT_BAR, EXIT_TRADE)
            tp2_exit_reason: Reason for TP2 decision
            trailing_sl_level: Trailing SL price
            trailing_sl_enabled: Whether trailing SL is active
            
        Returns:
            True if updated, False if position not found
        """
        try:
            for position in self.open_positions:
                if position['ticket'] == ticket:
                    if post_tp1_decision is not None:
                        position['post_tp1_decision'] = post_tp1_decision
                    if tp1_exit_reason is not None:
                        position['tp1_exit_reason'] = tp1_exit_reason
                    if post_tp2_decision is not None:
                        position['post_tp2_decision'] = post_tp2_decision
                    if tp2_exit_reason is not None:
                        position['tp2_exit_reason'] = tp2_exit_reason
                    if trailing_sl_level is not None:
                        position['trailing_sl_level'] = trailing_sl_level
                    if trailing_sl_enabled is not None:
                        position['trailing_sl_enabled'] = trailing_sl_enabled
                    
                    self.logger.debug(f"Ticket {ticket}: TP exit metadata updated - "
                                    f"TP1={post_tp1_decision}, TP2={post_tp2_decision}")
                    
                    # Optimize DB update - only update changed position
                    if self.storage_backend == "db" and self.db_store:
                        updates = {}
                        if post_tp1_decision is not None:
                            updates['post_tp1_decision'] = post_tp1_decision
                        if tp1_exit_reason is not None:
                            updates['tp1_exit_reason'] = tp1_exit_reason
                        if post_tp2_decision is not None:
                            updates['post_tp2_decision'] = post_tp2_decision
                        if tp2_exit_reason is not None:
                            updates['tp2_exit_reason'] = tp2_exit_reason
                        if trailing_sl_level is not None:
                            updates['trailing_sl_level'] = trailing_sl_level
                        if trailing_sl_enabled is not None:
                            updates['trailing_sl_enabled'] = trailing_sl_enabled
                        if updates:
                            self.db_store.update_position(ticket, updates)
                    else:
                        self.save_state()
                    
                    return True
            
            self.logger.warning(f"Position ticket {ticket} not found for metadata update")
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating TP exit metadata: {e}")
            return False
    
    def get_position_by_ticket(self, ticket: int) -> Optional[Dict]:
        """
        Get position by ticket number.
        
        Args:
            ticket: Position ticket number
            
        Returns:
            Position dict or None if not found
        """
        for position in self.open_positions:
            if position['ticket'] == ticket:
                return position.copy()
        return None
    
    def is_in_cooldown(self, current_time: datetime, cooldown_hours: int = 24) -> bool:
        """
        Check if system is in cooldown period.
        
        Args:
            current_time: Current timestamp
            cooldown_hours: Cooldown period in hours
            
        Returns:
            True if in cooldown, False otherwise
        """
        if self.last_trade_time is None:
            self.logger.debug("No last trade time recorded - cooldown not active")
            return False
        
        # Convert string to datetime if needed
        if isinstance(self.last_trade_time, str):
            self.last_trade_time = datetime.fromisoformat(self.last_trade_time)
        
        hours_since_last_trade = (current_time - self.last_trade_time).total_seconds() / 3600
        in_cooldown = hours_since_last_trade < cooldown_hours
        
        # Log cooldown state for debugging
        remaining_hours = cooldown_hours - hours_since_last_trade if in_cooldown else 0
        self.logger.debug(
            f"Cooldown check: last_trade={self.last_trade_time.isoformat()}, "
            f"current={current_time.isoformat()}, "
            f"hours_elapsed={hours_since_last_trade:.2f}, "
            f"cooldown_period={cooldown_hours}h, "
            f"in_cooldown={in_cooldown}, "
            f"remaining={remaining_hours:.2f}h"
        )
        
        return in_cooldown
    
    def get_statistics(self) -> Dict:
        """
        Calculate and return performance statistics.
        
        Returns:
            Dict with performance metrics
        """
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0
        
        winning_trades = [t for t in self.trade_history if t['profit'] > 0]
        losing_trades = [t for t in self.trade_history if t['profit'] <= 0]
        
        avg_win = sum(t['profit'] for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(t['profit'] for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        profit_factor = abs(sum(t['profit'] for t in winning_trades) / 
                           sum(t['profit'] for t in losing_trades)) if losing_trades and sum(t['profit'] for t in losing_trades) != 0 else 0.0
        
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_profit': self.total_profit,
            'average_win': avg_win,
            'average_loss': avg_loss,
            'profit_factor': profit_factor,
            'last_trade_time': self.last_trade_time.isoformat() if self.last_trade_time else None
        }
    
    def get_recent_trades(self, count: int = 10) -> List[Dict]:
        """
        Get the most recent N trades.
        
        Args:
            count: Number of trades to return
            
        Returns:
            List of recent trade dicts
        """
        return self.trade_history[-count:]

    def _build_state_data(self) -> Dict:
        """Build state dict for serialization, converting non-serializable types."""
        
        # Ensure last_trade_time is always current (guard against stale values)
        # Derive from transactions if internal value is missing or stale
        if not self.last_trade_time:
            self.last_trade_time = self._derive_last_trade_time()
        
        state_data = {
            'open_positions': [],
            'trade_history': self.trade_history,
            'last_trade_time': self.last_trade_time.isoformat() if self.last_trade_time else None,
            'total_trades': int(self.total_trades),
            'winning_trades': int(self.winning_trades),
            'losing_trades': int(self.losing_trades),
            'total_profit': float(self.total_profit),
            'last_regime_state': self.last_regime_state,
        }

        for pos in self.open_positions:
            pos_copy = pos.copy()
            # Ensure TP exit metadata fields are persisted
            if 'post_tp1_decision' not in pos_copy:
                pos_copy['post_tp1_decision'] = 'NOT_REACHED'
            if 'tp1_exit_reason' not in pos_copy:
                pos_copy['tp1_exit_reason'] = None
            if 'post_tp2_decision' not in pos_copy:
                pos_copy['post_tp2_decision'] = 'NOT_REACHED'
            if 'tp2_exit_reason' not in pos_copy:
                pos_copy['tp2_exit_reason'] = None
            if 'trailing_sl_level' not in pos_copy:
                pos_copy['trailing_sl_level'] = None
            if 'trailing_sl_enabled' not in pos_copy:
                pos_copy['trailing_sl_enabled'] = False
            
            # Convert datetime to ISO string
            if 'entry_time' in pos_copy and isinstance(pos_copy['entry_time'], datetime):
                pos_copy['entry_time'] = pos_copy['entry_time'].isoformat()
            
            # Convert timestamp fields to ISO string
            for ts_field in ['tp1_reached_timestamp', 'tp2_reached_timestamp']:
                if ts_field in pos_copy and isinstance(pos_copy[ts_field], datetime):
                    pos_copy[ts_field] = pos_copy[ts_field].isoformat()
            
            # Ensure bool fields are native Python bool (not numpy.bool_)
            for bool_field in ['tp1_reached', 'tp2_reached']:
                if bool_field in pos_copy and pos_copy[bool_field] is not None:
                    pos_copy[bool_field] = bool(pos_copy[bool_field])
            
            # Ensure numeric fields are native Python types
            for num_field in ['volume', 'atr', 'tp_value', 'risk_cash', 'tp1_cash', 'tp2_cash', 'tp3_cash',
                             'current_stop_loss', 'bars_held_after_tp1', 'max_extension_after_tp1',
                             'bars_held_after_tp2', 'max_extension_after_tp2', 'price_current', 'profit', 'swap']:
                if num_field in pos_copy and pos_copy[num_field] is not None:
                    if isinstance(pos_copy[num_field], (int, float)):
                        pos_copy[num_field] = float(pos_copy[num_field]) if '.' in str(pos_copy[num_field]) else int(pos_copy[num_field])
            
            state_data['open_positions'].append(pos_copy)

        return state_data
    
    def save_state(self):
        """
        Persist current state to both DB and file for redundancy.

        If file + atomic writes enabled: queues write, batched every 5 seconds.
        If file + atomic writes disabled: direct write (NOT recommended).
        
        Always maintains JSON backup even when using DB backend.
        """
        try:
            state_data = self._build_state_data()

            # Save to database if enabled
            if self.storage_backend == "db" and self.db_store:
                self.db_store.save_state(state_data)
            
            # ALWAYS save JSON as backup - critical for disaster recovery
            if self.atomic_writer:
                self.atomic_writer.queue_write(state_data)
            else:
                self._direct_write(state_data)

        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
    
    def _direct_write(self, state_data: Dict):
        """
        Direct write to file (fallback, NOT thread-safe).
        
        Used only if atomic writes are disabled.
        """
        try:
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file with safe encoder for non-serializable types
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2, cls=SafeJSONEncoder)
            
            self.logger.debug(f"State saved (direct write) to {self.state_file}")
        
        except Exception as e:
            self.logger.error(f"Error in direct write: {e}")

    
    def load_state(self):
        """
        Load state from disk with integrity validation.
        
        If atomic writer available: validates checksum and recovers from backups
        If corrupted: attempts recovery from most recent backup
        If all backups corrupted: starts fresh
        """
        try:
            state_data = None

            if self.storage_backend == "db" and self.db_store:
                state_data = self.db_store.load_latest_snapshot()
                if not state_data:
                    state_data = self._load_state_from_file()
                    if state_data:
                        self.logger.info(
                            "Backfilling DB state from %s", self.state_file
                        )
                        self.db_store.save_state(state_data)
            else:
                state_data = self._load_state_from_file()

            if not state_data:
                self.logger.info("No valid state file found, starting fresh")
                return

            self._apply_state_data(state_data)

        except Exception as e:
            self.logger.error(f"Error loading state: {e}")
    
    def _direct_load(self) -> Optional[Dict]:
        """
        Direct load from file (fallback, less safe).
        
        Used only if atomic writer not available.
        """
        try:
            if not self.state_file.exists():
                self.logger.info("No existing state file found, starting fresh")
                return None
            
            with open(self.state_file, 'r') as f:
                return json.load(f)
        
        except Exception as e:
            self.logger.error(f"Error in direct load: {e}")
            return None

    def _load_state_from_file(self) -> Optional[Dict]:
        if self.atomic_writer:
            return self.atomic_writer.load_with_validation()
        return self._direct_load()

    def _apply_state_data(self, state_data: Dict) -> None:
        # Restore state - handle both old format (current_position) and new (open_positions)
        if 'open_positions' in state_data:
            self.open_positions = state_data.get('open_positions', [])
        elif 'current_position' in state_data and state_data['current_position']:
            self.open_positions = [state_data['current_position']]

        self.trade_history = state_data.get('trade_history', [])
        self.total_trades = state_data.get('total_trades', 0)
        self.winning_trades = state_data.get('winning_trades', 0)
        self.losing_trades = state_data.get('losing_trades', 0)
        self.total_profit = state_data.get('total_profit', 0.0)
        self.last_regime_state = state_data.get('last_regime_state')

        # Load last_trade_time with fallback logic
        last_trade_str = state_data.get('last_trade_time')
        if last_trade_str:
            self.last_trade_time = datetime.fromisoformat(last_trade_str)
        else:
            # If not recorded, derive from most recent transaction (open or closed)
            self.last_trade_time = self._derive_last_trade_time()

        source = (
            "database"
            if self.storage_backend == "db" and self.db_store
            else str(self.state_file)
        )
        self.logger.info(f"State loaded from {source}")
        self.logger.info(f"  Total trades: {self.total_trades}")
        self.logger.info(f"  Total profit: ${self.total_profit:.2f}")
        self.logger.info(f"  Open positions: {len(self.open_positions)}")
        self.logger.info(f"  Last trade time: {self.last_trade_time}")

    def _derive_last_trade_time(self) -> Optional[datetime]:
        """
        Derive last_trade_time from open positions and trade history.
        Used as fallback when last_trade_time is not recorded.
        Returns the most recent entry_time or exit_time.
        """
        all_times = []
        
        # Get times from open positions
        for pos in self.open_positions:
            entry_str = pos.get('entry_time')
            if entry_str:
                try:
                    entry_dt = entry_str if isinstance(entry_str, datetime) else datetime.fromisoformat(entry_str)
                    all_times.append(entry_dt)
                except (ValueError, TypeError):
                    pass
        
        # Get times from closed trades
        for trade in self.trade_history:
            exit_str = trade.get('exit_time')
            if exit_str:
                try:
                    exit_dt = exit_str if isinstance(exit_str, datetime) else datetime.fromisoformat(exit_str)
                    all_times.append(exit_dt)
                except (ValueError, TypeError):
                    pass
        
        if all_times:
            latest = max(all_times)
            self.logger.warning(f"Derived last_trade_time from transaction history: {latest}")
            return latest
        
        return None


    def set_regime_state(self, regime_state: Dict):
        """Update and persist the latest market regime state."""
        try:
            self.last_regime_state = regime_state
            self.save_state()
        except Exception as e:
            self.logger.error(f"Error setting regime state: {e}")
    
    def reset_state(self):
        """Reset all state (use with caution!)."""
        self.open_positions = []
        self.trade_history = []
        self.last_trade_time = None
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        
        self.save_state()
        self.flush()  # Ensure reset is written immediately
        self.logger.warning("State has been reset")
    
    def flush(self):
        """Force immediate write of pending state (blocks)."""
        try:
            if self.atomic_writer:
                flushed = self.atomic_writer.flush()
                self.logger.info("State flush executed (success=%s)", flushed)
        except Exception as e:
            self.logger.error(f"Error flushing state: {e}")
    
    def shutdown(self):
        """Graceful shutdown - flush pending writes and stop writer thread."""
        try:
            self.logger.info("Shutting down StateManager...")
            
            # Flush any pending writes
            self.flush()
            
            # Stop atomic writer thread
            if self.atomic_writer:
                self.atomic_writer.stop()

            if self.db_store:
                self.db_store.close()
            
            self.logger.info("StateManager shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.DEBUG)
    
    manager = StateManager("data/test_state.json")
    
    # Simulate opening a position
    manager.open_position({
        'ticket': 12345,
        'entry_price': 2000.0,
        'stop_loss': 1980.0,
        'take_profit': 2040.0,
        'volume': 0.1,
        'entry_time': datetime.now()
    })
    
    print(f"Position opened: {manager.has_open_position()}")
    
    # Simulate closing with profit
    manager.close_position(2040.0, "Take Profit")
    
    print(f"Position closed: {not manager.has_open_position()}")
    
    # Get statistics
    stats = manager.get_statistics()
    print("Statistics:")
    print(f"  Total trades: {stats['total_trades']}")
    print(f"  Win rate: {stats['win_rate']:.1f}%")
    print(f"  Total profit: ${stats['total_profit']:.2f}")

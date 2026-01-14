"""
State Manager - Tracks open positions, trade history, and cooldowns

This module maintains the state of the trading system:
- Current open position (if any)
- Trade history
- Cooldown tracking
- Performance statistics
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path


class StateManager:
    """
    Manages trading system state and persistence.
    
    Responsibilities:
    - Track current position
    - Store trade history
    - Manage cooldown periods
    - Calculate performance metrics
    - Persist state to disk
    """
    
    def __init__(self, state_file: str = "data/state.json"):
        """
        Initialize State Manager.
        
        Args:
            state_file: Path to state persistence file
        """
        self.state_file = Path(state_file)
        self.logger = logging.getLogger(__name__)
        
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
        
        Args:
            position_data: Dict with position details
                Required keys: ticket, entry_price, stop_loss, take_profit, volume
        """
        try:
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
            }
            
            self.open_positions.append(new_position)
            self.last_trade_time = new_position['entry_time']
            
            self.logger.info(f"Position opened: Ticket={new_position['ticket']}, "
                           f"Entry={new_position['entry_price']:.2f}, "
                           f"TP State={new_position['tp_state']}, "
                           f"Total open: {len(self.open_positions)}")
            
            self.save_state()
            
        except Exception as e:
            self.logger.error(f"Error opening position: {e}")
    
    def close_position(self, exit_price: float, exit_reason: str, 
                      exit_time: Optional[datetime] = None, ticket: Optional[int] = None):
        """
        Close a position and record the trade.
        
        Args:
            exit_price: Exit price
            exit_reason: Reason for exit ("Stop Loss", "Take Profit", etc.)
            exit_time: Exit timestamp (default: now)
            ticket: Specific ticket to close (if None, close first position)
        """
        try:
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
            profit = (exit_price - entry_price) * volume * 100  # Simplified P&L calculation
            
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
                'profit': profit,
                'exit_reason': exit_reason,
                'pattern_info': position_to_close.get('pattern_info'),
                'is_winner': profit > 0
            }
            
            # Debug log - verify exit_reason is text, not a price
            self.logger.info(f"Trade record created: ticket={trade_record['ticket']}, "
                           f"exit_reason='{exit_reason}' (type: {type(exit_reason).__name__}), "
                           f"take_profit={trade_record['take_profit']}")
            
            # Update statistics
            self.trade_history.append(trade_record)
            self.total_trades += 1
            self.total_profit += profit
            
            if profit > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            self.logger.info(f"Position closed: Ticket={trade_record['ticket']}, "
                           f"Profit=${profit:.2f}, Reason={exit_reason}, "
                           f"Remaining: {len(self.open_positions)-1}")
            
            # Remove closed position
            self.open_positions.remove(position_to_close)
            
            self.save_state()
            
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
    
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
                        
                    self.logger.info(f"Ticket {ticket}: TP state {old_state} -> {new_tp_state}, "
                                   f"SL updated to {new_stop_loss:.2f if new_stop_loss else 'N/A'}")
                    
                    self.save_state()
                    return True
            
            self.logger.warning(f"Position ticket {ticket} not found")
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating TP state: {e}")
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
            return False
        
        # Convert string to datetime if needed
        if isinstance(self.last_trade_time, str):
            self.last_trade_time = datetime.fromisoformat(self.last_trade_time)
        
        hours_since_last_trade = (current_time - self.last_trade_time).total_seconds() / 3600
        return hours_since_last_trade < cooldown_hours
    
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
    
    def save_state(self):
        """Persist current state to disk."""
        try:
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare state data
            state_data = {
                'open_positions': [],
                'trade_history': self.trade_history,
                'last_trade_time': self.last_trade_time.isoformat() if self.last_trade_time else None,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'total_profit': self.total_profit,
                'last_regime_state': self.last_regime_state,
                'saved_at': datetime.now().isoformat()
            }
            
            # Convert datetime objects in open positions if needed
            for pos in self.open_positions:
                pos_copy = pos.copy()
                if 'entry_time' in pos_copy and isinstance(pos_copy['entry_time'], datetime):
                    pos_copy['entry_time'] = pos_copy['entry_time'].isoformat()
                state_data['open_positions'].append(pos_copy)
            
            # Write to file
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            self.logger.debug(f"State saved to {self.state_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
    
    def load_state(self):
        """Load state from disk if file exists."""
        try:
            if not self.state_file.exists():
                self.logger.info("No existing state file found, starting fresh")
                return
            
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)
            
            # Restore state - handle both old format (current_position) and new (open_positions)
            if 'open_positions' in state_data:
                self.open_positions = state_data.get('open_positions', [])
            elif 'current_position' in state_data and state_data['current_position']:
                # Backwards compatibility: convert single position to list
                self.open_positions = [state_data['current_position']]
            
            self.trade_history = state_data.get('trade_history', [])
            self.total_trades = state_data.get('total_trades', 0)
            self.winning_trades = state_data.get('winning_trades', 0)
            self.losing_trades = state_data.get('losing_trades', 0)
            self.total_profit = state_data.get('total_profit', 0.0)
            # Regime state
            self.last_regime_state = state_data.get('last_regime_state')
            
            # Parse last_trade_time
            last_trade_str = state_data.get('last_trade_time')
            if last_trade_str:
                self.last_trade_time = datetime.fromisoformat(last_trade_str)
            
            self.logger.info(f"State loaded from {self.state_file}")
            self.logger.info(f"  Total trades: {self.total_trades}")
            self.logger.info(f"  Total profit: ${self.total_profit:.2f}")
            self.logger.info(f"  Open positions: {len(self.open_positions)}")
            
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")

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
        self.logger.warning("State has been reset")


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

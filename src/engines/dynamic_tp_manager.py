"""
Dynamic TP Manager - Trade lifecycle management with multi-level take-profit

This module manages the complete trade lifecycle after entry:
- Risk and reward cash calculations for each TP level
- TP level progression (TP1 -> TP2 -> TP3)
- Fallback exit on price failure to hold current level
- UI-friendly monetary displays

Philosophy:
- Does NOT modify entry signal or position sizing
- Does NOT change SL location
- Provides monetary context for trade decisions
- Manages progression and exit only
"""

import logging
from typing import Tuple, Dict, Optional
from enum import Enum
import pandas as pd


class TradeDirection(Enum):
    """Trade direction"""
    LONG = "LONG"
    SHORT = "SHORT"


class TPManager:
    """
    Manages dynamic TP levels and trade lifecycle.
    
    Handles:
    - Risk/reward cash calculations
    - TP level progression
    - Fallback exit on retrace
    - Trade lifecycle monitoring
    """
    
    def __init__(self,
                 rr_long: float = 2.0,
                 rr_short: float = 2.0,
                 tp_level_1_rr: float = 1.4,
                 tp_level_2_rr: float = 1.9):
        """
        Initialize TP Manager.
        
        Args:
            rr_long: Risk/reward ratio for LONG trades (for TP3)
            rr_short: Risk/reward ratio for SHORT trades (for TP3)
            tp_level_1_rr: RR for TP1 (default: 1.4)
            tp_level_2_rr: RR for TP2 (default: 1.9)
        """
        self.rr_long = rr_long
        self.rr_short = rr_short
        self.tp_level_1_rr = tp_level_1_rr
        self.tp_level_2_rr = tp_level_2_rr
        self.logger = logging.getLogger(__name__)
        
        # Per-trade state
        self.active_trades: Dict[int, Dict] = {}  # ticket -> trade_state
        
        self.logger.info("Dynamic TP Manager initialized")
    
    def open_trade(self, ticket: int, entry_price: float, stop_loss: float,
                   position_size: float, direction: str = "LONG") -> Dict:
        """
        Register a new trade and calculate all TP levels and cash values.
        
        Args:
            ticket: Position ticket
            entry_price: Entry price
            stop_loss: Stop loss price
            position_size: Position size in lots
            direction: LONG or SHORT
            
        Returns:
            Dict with trade state including TP levels and cash calculations
        """
        try:
            # Calculate risk in cash
            risk_pips = abs(entry_price - stop_loss)
            risk_cash = risk_pips * position_size * 100  # Simplified for XAUUSD
            
            # Determine RR for TP3 based on direction
            tp3_rr = self.rr_long if direction == "LONG" else self.rr_short
            
            # Calculate TP prices based on direction
            if direction == "LONG":
                tp1_price = entry_price + (risk_pips * self.tp_level_1_rr)
                tp2_price = entry_price + (risk_pips * self.tp_level_2_rr)
                tp3_price = entry_price + (risk_pips * tp3_rr)
            else:  # SHORT
                tp1_price = entry_price - (risk_pips * self.tp_level_1_rr)
                tp2_price = entry_price - (risk_pips * self.tp_level_2_rr)
                tp3_price = entry_price - (risk_pips * tp3_rr)
            
            # Calculate reward in cash at each level
            tp1_cash = abs(tp1_price - entry_price) * position_size * 100
            tp2_cash = abs(tp2_price - entry_price) * position_size * 100
            tp3_cash = abs(tp3_price - entry_price) * position_size * 100
            
            # Trade state
            trade_state = {
                'ticket': ticket,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'position_size': position_size,
                'direction': direction,
                'current_tp_level': 'TP1',  # Start at TP1
                'risk_cash': risk_cash,
                'tp_levels': {
                    'TP1': {
                        'price': tp1_price,
                        'rr': self.tp_level_1_rr,
                        'cash': tp1_cash,
                        'reached': False
                    },
                    'TP2': {
                        'price': tp2_price,
                        'rr': self.tp_level_2_rr,
                        'cash': tp2_cash,
                        'reached': False
                    },
                    'TP3': {
                        'price': tp3_price,
                        'rr': tp3_rr,
                        'cash': tp3_cash,
                        'reached': False
                    }
                },
                'created_at': pd.Timestamp.now()
            }
            
            self.active_trades[ticket] = trade_state
            
            self.logger.info(
                f"Trade {ticket} opened: Entry={entry_price:.2f}, SL={stop_loss:.2f}, "
                f"Risk=${risk_cash:.2f}, "
                f"TP1=${tp1_cash:.2f}, TP2=${tp2_cash:.2f}, TP3=${tp3_cash:.2f}"
            )
            
            return trade_state
            
        except Exception as e:
            self.logger.error(f"Error opening trade {ticket}: {e}")
            return {}
    
    def get_trade_info(self, ticket: int) -> Optional[Dict]:
        """Get current trade information."""
        return self.active_trades.get(ticket)
    
    def evaluate_tp_progression(self, ticket: int, current_price: float) -> Tuple[bool, str]:
        """
        Check if position should progress to next TP level.
        
        Progression rules:
        - TP1 -> TP2: Price reaches TP1
        - TP2 -> TP3: Price reaches TP2
        
        Args:
            ticket: Trade ticket
            current_price: Current market price
            
        Returns:
            Tuple of (progressed, reason)
        """
        try:
            trade = self.active_trades.get(ticket)
            if not trade:
                return False, "Trade not found"
            
            current_level = trade['current_tp_level']
            direction = trade['direction']
            tp_levels = trade['tp_levels']
            
            # Check if already at TP3
            if current_level == 'TP3':
                return False, "Already at maximum TP level"
            
            # Get current level price
            current_level_price = tp_levels[current_level]['price']
            
            # Check if price has reached current level (based on direction)
            if direction == "LONG":
                price_reached = current_price >= current_level_price
            else:
                price_reached = current_price <= current_level_price
            
            if not price_reached:
                return False, f"Price not yet reached {current_level}"
            
            # Progress to next level
            next_levels = {'TP1': 'TP2', 'TP2': 'TP3'}
            if current_level in next_levels:
                next_level = next_levels[current_level]
                trade['current_tp_level'] = next_level
                tp_levels[current_level]['reached'] = True
                
                self.logger.info(
                    f"Trade {ticket}: TP progression {current_level} -> {next_level}, "
                    f"Target: ${tp_levels[next_level]['cash']:.2f}"
                )
                
                return True, f"Progressed {current_level} -> {next_level}"
            
            return False, "Cannot progress further"
            
        except Exception as e:
            self.logger.error(f"Error evaluating TP progression: {e}")
            return False, "Error"
    
    def check_fallback_exit(self, ticket: int, current_price: float,
                            ema_fast: Optional[float] = None) -> Tuple[bool, str, float]:
        """
        Check if position should exit on fallback (price fails to hold level).
        
        Exit triggers:
        - Price retraces below current TP level AND
        - (Optionally) closes below fast EMA (confirms momentum loss)
        
        Exit at: Last validated TP level
        
        Args:
            ticket: Trade ticket
            current_price: Current market price
            ema_fast: Fast EMA (optional, for confirmation)
            
        Returns:
            Tuple of (should_exit, reason, exit_price)
        """
        try:
            trade = self.active_trades.get(ticket)
            if not trade:
                return False, "Trade not found", 0.0
            
            current_level = trade['current_tp_level']
            direction = trade['direction']
            tp_levels = trade['tp_levels']
            current_level_price = tp_levels[current_level]['price']
            
            # Check for retrace
            if direction == "LONG":
                is_retracing = current_price < current_level_price
            else:
                is_retracing = current_price > current_level_price
            
            if not is_retracing:
                return False, "Price holding level", current_price
            
            # Optional EMA confirmation
            if ema_fast is not None:
                if direction == "LONG":
                    ema_confirms = current_price < ema_fast
                else:
                    ema_confirms = current_price > ema_fast
                
                if not ema_confirms:
                    return False, "Price retracing but EMA not confirmed", current_price
            
            # Exit at current TP level
            exit_price = current_level_price
            
            self.logger.info(
                f"Trade {ticket}: Fallback exit triggered, closing at {current_level} "
                f"(${tp_levels[current_level]['cash']:.2f} profit)"
            )
            
            return True, f"Fallback exit at {current_level}", exit_price
            
        except Exception as e:
            self.logger.error(f"Error checking fallback exit: {e}")
            return False, "Error", 0.0
    
    def close_trade(self, ticket: int, exit_price: float,
                    exit_reason: str) -> Dict:
        """
        Close a trade and calculate final P&L.
        
        Args:
            ticket: Trade ticket
            exit_price: Exit price
            exit_reason: Reason for exit
            
        Returns:
            Dict with trade closure info
        """
        try:
            trade = self.active_trades.pop(ticket, None)
            if not trade:
                return {}
            
            # Calculate actual P&L
            direction = trade['direction']
            entry_price = trade['entry_price']
            position_size = trade['position_size']
            
            if direction == "LONG":
                pnl_pips = exit_price - entry_price
            else:
                pnl_pips = entry_price - exit_price
            
            pnl_cash = pnl_pips * position_size * 100
            
            # Calculate RR achieved
            risk_cash = trade['risk_cash']
            rr_achieved = pnl_cash / risk_cash if risk_cash > 0 else 0
            
            closure_info = {
                'ticket': ticket,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'exit_reason': exit_reason,
                'exit_level': trade['current_tp_level'],
                'pnl_cash': pnl_cash,
                'rr_achieved': rr_achieved,
                'risk_cash': risk_cash,
                'position_size': position_size,
                'direction': direction
            }
            
            self.logger.info(
                f"Trade {ticket} closed: {exit_reason}, "
                f"P&L=${pnl_cash:.2f} (RR: {rr_achieved:.2f}x), "
                f"Exit at {trade['current_tp_level']}"
            )
            
            return closure_info
            
        except Exception as e:
            self.logger.error(f"Error closing trade {ticket}: {e}")
            return {}
    
    def get_all_trades(self) -> Dict[int, Dict]:
        """Get all active trades."""
        return self.active_trades.copy()
    
    def get_trade_cash_summary(self, ticket: int) -> Dict:
        """
        Get trade cash summary for UI display.
        
        Returns dict with:
        - risk_cash: Total risk in dollars
        - tp1_cash: Profit target at TP1
        - tp2_cash: Profit target at TP2
        - tp3_cash: Profit target at TP3
        - current_level: Current TP level
        """
        try:
            trade = self.active_trades.get(ticket)
            if not trade:
                return {}
            
            tp_levels = trade['tp_levels']
            
            return {
                'ticket': ticket,
                'entry_price': trade['entry_price'],
                'stop_loss': trade['stop_loss'],
                'risk_cash': trade['risk_cash'],
                'tp1_price': tp_levels['TP1']['price'],
                'tp1_cash': tp_levels['TP1']['cash'],
                'tp2_price': tp_levels['TP2']['price'],
                'tp2_cash': tp_levels['TP2']['cash'],
                'tp3_price': tp_levels['TP3']['price'],
                'tp3_cash': tp_levels['TP3']['cash'],
                'current_level': trade['current_tp_level'],
                'direction': trade['direction']
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cash summary: {e}")
            return {}


if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.DEBUG)
    
    manager = TPManager(rr_long=2.0, rr_short=2.0)
    
    # Open a LONG trade
    trade_state = manager.open_trade(
        ticket=123456,
        entry_price=2000.0,
        stop_loss=1980.0,
        position_size=0.1,
        direction="LONG"
    )
    
    print("\nTrade opened")
    print(f"  Risk: ${trade_state['risk_cash']:.2f}")
    print(f"  TP1: {trade_state['tp_levels']['TP1']['price']:.2f} (${trade_state['tp_levels']['TP1']['cash']:.2f})")
    print(f"  TP2: {trade_state['tp_levels']['TP2']['price']:.2f} (${trade_state['tp_levels']['TP2']['cash']:.2f})")
    print(f"  TP3: {trade_state['tp_levels']['TP3']['price']:.2f} (${trade_state['tp_levels']['TP3']['cash']:.2f})")
    
    # Simulate price reaching TP1
    print("\nPrice reaches TP1...")
    progressed, reason = manager.evaluate_tp_progression(123456, 2028.0)
    print(f"  Progression: {reason}")
    
    # Simulate fallback
    print("\nPrice retraces...")
    should_exit, reason, exit_price = manager.check_fallback_exit(123456, 2025.0)
    print(f"  Exit: {reason} @ {exit_price:.2f}")
    
    # Close trade
    closure = manager.close_trade(123456, 2025.0, "Fallback exit")
    print("\nTrade closed")
    print(f"  P&L: ${closure['pnl_cash']:.2f}")
    print(f"  RR Achieved: {closure['rr_achieved']:.2f}x")

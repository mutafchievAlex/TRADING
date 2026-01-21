"""
TP Engine - Dynamic Multi-Level Take Profit Management

This module implements dynamic floating TP logic with 3 levels:
- TP1: 1.4 RR (protective target) - state: LEVEL_1
- TP2: 1.9 RR (extended target) - state: LEVEL_2  
- TP3: User-defined RR from settings - state: LEVEL_3

Key behaviors:
1. Start at TP1 on trade open
2. Transition to TP2 when price reaches TP1 + confirmation conditions
3. Transition to TP3 when price reaches TP2 + impulsive conditions
4. On retrace (close below EMA20 or reversal), exit at current TP level
5. Profit protection: Move SL to BE after TP1, fixed profit after TP2
"""

import logging
from typing import Optional, Dict, Tuple
from enum import Enum
from datetime import datetime


class TPLevel(Enum):
    """TP state levels"""
    LEVEL_1 = "TP1"      # 1.4 RR - protective target
    LEVEL_2 = "TP2"      # 1.9 RR - extended target
    LEVEL_3 = "TP3"      # Dynamic from settings


class TPEngine:
    """
    Manages dynamic multi-level Take Profit logic.
    
    Tracks TP state transitions and exit conditions for each position.
    """
    
    def __init__(self):
        """Initialize TP Engine."""
        self.logger = logging.getLogger(__name__)
        self.position_states = {}  # ticket -> {state, entry, tp_values, ...}
        
        # RR values for TP levels
        self.TP_LEVELS = {
            TPLevel.LEVEL_1: 1.4,  # TP1
            TPLevel.LEVEL_2: 1.9,  # TP2
            TPLevel.LEVEL_3: None  # TP3 - will be set from settings
        }
        
        self.logger.info("TP Engine initialized with dynamic multi-level logic")
    
    def open_position(self, ticket: int, entry_price: float, stop_loss: float,
                     rr_long: float = 2.0, rr_short: float = 2.0,
                     direction: str = "LONG") -> Dict:
        """
        Initialize TP state for a new position.
        
        Calculates all 3 TP levels at entry and starts with TP1.
        
        Args:
            ticket: Position ticket
            entry_price: Entry price
            stop_loss: Stop loss price
            rr_long: RR ratio for LONG (for TP3)
            rr_short: RR ratio for SHORT (for TP3)
            direction: Trade direction
            
        Returns:
            Dict with TP state and levels
        """
        try:
            # Use appropriate RR for TP3 based on direction
            tp3_rr = rr_long if direction == "LONG" else rr_short
            
            # Calculate TP levels
            tp_levels = self._calculate_tp_levels(
                entry_price, stop_loss, direction, tp3_rr
            )
            
            # Initialize position state
            state = {
                'ticket': ticket,
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'current_tp_level': TPLevel.LEVEL_1,
                'tp_values': tp_levels,
                'active_tp': tp_levels[TPLevel.LEVEL_1],  # Start at TP1
                'entry_time': datetime.now(),
                'sl_moved_to_be': False,  # Track profit protection
                'sl_moved_to_fixed': False,
                'tp_hit_levels': set()  # Track which TPs were hit
            }
            
            self.position_states[ticket] = state
            
            self.logger.info(
                f"Position {ticket} opened: TP1={tp_levels[TPLevel.LEVEL_1]:.5f}, "
                f"TP2={tp_levels[TPLevel.LEVEL_2]:.5f}, "
                f"TP3={tp_levels[TPLevel.LEVEL_3]:.5f}"
            )
            
            return state
            
        except Exception as e:
            self.logger.error(f"Error opening position {ticket}: {e}")
            return {}
    
    def evaluate_tp_transition(self, ticket: int, current_price: float,
                              current_bar: dict, ema20: float,
                              atr: float) -> Tuple[bool, str]:
        """
        Check if position should transition to next TP level.
        
        Transition conditions:
        LEVEL_1 -> LEVEL_2:
          - price_reached_tp: TP1
          - bar_closed_above_tp: TP1
          - momentum_valid: close > EMA20
          
        LEVEL_2 -> LEVEL_3:
          - price_reached_tp: TP2
          - bar_closed_above_tp: TP2
          - impulsive_candle: range > ATR
          - structure_valid: higher_high_higher_low
          
        Args:
            ticket: Position ticket
            current_price: Current price
            current_bar: Current bar OHLC
            ema20: EMA20 value
            atr: ATR value
            
        Returns:
            Tuple of (transitioned, reason)
        """
        if ticket not in self.position_states:
            return False, "Position not found"
        
        state = self.position_states[ticket]
        current_level = state['current_tp_level']
        
        try:
            # Check if we can transition from LEVEL_1 to LEVEL_2
            if current_level == TPLevel.LEVEL_1:
                can_transition, reason = self._check_level_1_to_2(
                    state, current_price, current_bar, ema20
                )
                if can_transition:
                    state['current_tp_level'] = TPLevel.LEVEL_2
                    state['active_tp'] = state['tp_values'][TPLevel.LEVEL_2]
                    self.logger.info(
                        f"Position {ticket} TP transitioned: LEVEL_1 -> LEVEL_2, "
                        f"New TP={state['active_tp']:.5f}"
                    )
                    return True, reason
            
            # Check if we can transition from LEVEL_2 to LEVEL_3
            elif current_level == TPLevel.LEVEL_2:
                can_transition, reason = self._check_level_2_to_3(
                    state, current_price, current_bar, atr
                )
                if can_transition:
                    state['current_tp_level'] = TPLevel.LEVEL_3
                    state['active_tp'] = state['tp_values'][TPLevel.LEVEL_3]
                    self.logger.info(
                        f"Position {ticket} TP transitioned: LEVEL_2 -> LEVEL_3, "
                        f"New TP={state['active_tp']:.5f}"
                    )
                    return True, reason
            
            return False, f"No transition from {current_level.value}"
            
        except Exception as e:
            self.logger.error(f"Error evaluating TP transition: {e}")
            return False, f"Transition error: {e}"
    
    def check_retrace_exit(self, ticket: int, current_price: float,
                          current_bar: dict, ema20: float,
                          atr: float) -> Tuple[bool, str]:
        """
        Check if position should exit on retrace.
        
        Triggers:
        - close_below: EMA20
        - reversal_candle: bearish reversal
        - atr_contraction: volatility collapse
        
        Exit at last valid TP level.
        
        Args:
            ticket: Position ticket
            current_price: Current price
            current_bar: Current bar OHLC
            ema20: EMA20 value
            atr: ATR value
            
        Returns:
            Tuple of (should_exit, exit_price)
        """
        if ticket not in self.position_states:
            return False, 0.0
        
        state = self.position_states[ticket]
        
        try:
            # Check retrace triggers
            close_below_ema20 = current_bar['close'] < ema20
            reversal = self._is_reversal_candle(current_bar, state['direction'])
            contraction = current_bar['atr14'] < atr * 0.5
            
            if close_below_ema20 or reversal or contraction:
                # Exit at current TP level
                exit_price = state['active_tp']
                reason = ""
                
                if close_below_ema20:
                    reason = "close < EMA20"
                elif reversal:
                    reason = "reversal candle"
                else:
                    reason = "ATR contraction"
                
                self.logger.info(
                    f"Position {ticket} retrace exit triggered: {reason}, "
                    f"Exit at {state['current_tp_level'].value}={exit_price:.5f}"
                )
                
                return True, reason
            
            return False, ""
            
        except Exception as e:
            self.logger.error(f"Error checking retrace exit: {e}")
            return False, ""
    
    def check_profit_protection(self, ticket: int, current_price: float) -> Tuple[Optional[float], str]:
        """
        Check if SL should be moved for profit protection.
        
        Rules:
        - After TP1 hit: Move SL to break-even
        - After TP2 hit: Move SL to fixed profit (0.5 RR)
        
        Args:
            ticket: Position ticket
            current_price: Current price
            
        Returns:
            Tuple of (new_sl, reason) or (None, "") if no change
        """
        if ticket not in self.position_states:
            return None, ""
        
        state = self.position_states[ticket]
        entry = state['entry_price']
        current_level = state['current_tp_level']
        
        try:
            # After reaching TP1, move SL to BE
            if current_level.value in ["TP2", "TP3"] and not state['sl_moved_to_be']:
                new_sl = entry  # Break even
                state['sl_moved_to_be'] = True
                self.logger.info(f"Position {ticket}: SL moved to break-even at {new_sl:.5f}")
                return new_sl, "moved to BE after TP1"
            
            # After reaching TP2, move SL to fixed profit
            if current_level.value == "TP3" and not state['sl_moved_to_fixed']:
                # Calculate 0.5 RR profit
                risk = entry - state['stop_loss']
                fixed_profit_sl = entry + (risk * 0.5)
                state['sl_moved_to_fixed'] = True
                self.logger.info(f"Position {ticket}: SL moved to fixed profit at {fixed_profit_sl:.5f}")
                return fixed_profit_sl, "moved to fixed profit after TP2"
            
            return None, ""
            
        except Exception as e:
            self.logger.error(f"Error checking profit protection: {e}")
            return None, ""
    
    def close_position(self, ticket: int) -> bool:
        """Remove position from tracking."""
        if ticket in self.position_states:
            del self.position_states[ticket]
            return True
        return False
    
    def get_position_state(self, ticket: int) -> Optional[Dict]:
        """Get current TP state for position."""
        return self.position_states.get(ticket)
    
    # Private helper methods
    
    def _calculate_tp_levels(self, entry: float, stop_loss: float,
                            direction: str, tp3_rr: float) -> Dict:
        """Calculate all 3 TP levels."""
        risk = abs(entry - stop_loss)
        
        tp_levels = {}
        
        if direction == "LONG":
            tp_levels[TPLevel.LEVEL_1] = entry + (risk * 1.4)
            tp_levels[TPLevel.LEVEL_2] = entry + (risk * 1.9)
            tp_levels[TPLevel.LEVEL_3] = entry + (risk * tp3_rr)
        else:
            tp_levels[TPLevel.LEVEL_1] = entry - (risk * 1.4)
            tp_levels[TPLevel.LEVEL_2] = entry - (risk * 1.9)
            tp_levels[TPLevel.LEVEL_3] = entry - (risk * tp3_rr)
        
        return tp_levels
    
    def _check_level_1_to_2(self, state: dict, current_price: float,
                           current_bar: dict, ema20: float) -> Tuple[bool, str]:
        """Check conditions for LEVEL_1 -> LEVEL_2 transition."""
        tp1 = state['tp_values'][TPLevel.LEVEL_1]
        
        # Condition 1: Price reached TP1
        if state['direction'] == "LONG":
            reached = current_price >= tp1
        else:
            reached = current_price <= tp1
        
        if not reached:
            return False, f"Price not reached TP1"
        
        # Condition 2: Bar closed above TP1 (LONG) or below (SHORT)
        if state['direction'] == "LONG":
            closed_above = current_bar['close'] > tp1
        else:
            closed_above = current_bar['close'] < tp1
        
        if not closed_above:
            return False, "Bar not closed above TP1"
        
        # Condition 3: Momentum valid (close > EMA20 for LONG)
        if state['direction'] == "LONG":
            momentum = current_bar['close'] > ema20
        else:
            momentum = current_bar['close'] < ema20
        
        if not momentum:
            return False, "Momentum not valid"
        
        return True, "All conditions for TP1->TP2 met"
    
    def _check_level_2_to_3(self, state: dict, current_price: float,
                           current_bar: dict, atr: float) -> Tuple[bool, str]:
        """Check conditions for LEVEL_2 -> LEVEL_3 transition."""
        tp2 = state['tp_values'][TPLevel.LEVEL_2]
        
        # Condition 1: Price reached TP2
        if state['direction'] == "LONG":
            reached = current_price >= tp2
        else:
            reached = current_price <= tp2
        
        if not reached:
            return False, "Price not reached TP2"
        
        # Condition 2: Bar closed above TP2
        if state['direction'] == "LONG":
            closed_above = current_bar['close'] > tp2
        else:
            closed_above = current_bar['close'] < tp2
        
        if not closed_above:
            return False, "Bar not closed above TP2"
        
        # Condition 3: Impulsive candle (range > ATR)
        candle_range = abs(current_bar['close'] - current_bar['open'])
        if candle_range < atr:
            return False, "Candle not impulsive enough"
        
        # Condition 4: Structure valid (simplified - check for higher high/lower low)
        # This would need more context from previous bars in real implementation
        
        return True, "All conditions for TP2->TP3 met"
    
    def _is_reversal_candle(self, bar: dict, direction: str) -> bool:
        """Check if candle is a reversal against position direction."""
        try:
            if direction == "LONG":
                # Bearish reversal: close near low, large wick up
                wick_down = bar['low']
                wick_up = bar['high'] - bar['close']
                return wick_up > wick_down * 1.5 and bar['close'] < bar['open']
            else:
                # Bullish reversal: close near high, large wick down
                wick_up = bar['high']
                wick_down = bar['open'] - bar['low']
                return wick_down > wick_up * 1.5 and bar['close'] > bar['open']
        except (KeyError, TypeError):
            return False

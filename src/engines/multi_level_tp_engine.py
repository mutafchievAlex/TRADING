"""
Multi-Level Trailing Take-Profit Engine

Dynamic multi-level take-profit system with protection and trailing exits.
- TP1: 1.4x risk:reward (protection mode - move SL to breakeven)
- TP2: 1.8x risk:reward (trailing mode - trail stop loss)
- TP3: Final target from settings (full close)

State Machine: IDLE -> IN_TRADE -> TP1_REACHED -> TP2_REACHED -> EXITED
"""

import logging
from enum import Enum
from typing import Tuple, Dict, Optional
from datetime import datetime


class TPState(Enum):
    """Multi-level TP state machine."""
    IDLE = "IDLE"
    IN_TRADE = "IN_TRADE"
    TP1_REACHED = "TP1_REACHED"
    TP2_REACHED = "TP2_REACHED"
    EXITED = "EXITED"


class MultiLevelTPEngine:
    """
    Manages multi-level take-profit exits with dynamic stop-loss management.
    """
    
    # Default TP ratios (risk:reward)
    DEFAULT_TP1_RR = 1.4
    DEFAULT_TP2_RR = 1.8
    
    def __init__(self, default_rr_long: float = 2.0, default_rr_short: float = 2.0):
        """
        Initialize multi-level TP engine.
        
        Args:
            default_rr_long: Default Risk:Reward for LONG trades (final TP)
            default_rr_short: Default Risk:Reward for SHORT trades (final TP)
        """
        self.logger = logging.getLogger(__name__)
        self.default_rr_long = default_rr_long
        self.default_rr_short = default_rr_short
        
        self.logger.info("MultiLevelTPEngine initialized")
        self.logger.info(f"  Default RR LONG: {default_rr_long:.1f}")
        self.logger.info(f"  Default RR SHORT: {default_rr_short:.1f}")
    
    def calculate_tp_levels(self, entry_price: float, stop_loss: float, 
                           direction: int = 1) -> Dict[str, float]:
        """
        Calculate TP1, TP2, TP3 levels based on entry and stop loss.
        
        Validates:
        - risk_unit > 0 (fail-fast if entry == SL)
        - Monotonic TP ordering: TP1 < TP2 < TP3 (LONG) or TP1 > TP2 > TP3 (SHORT)
        
        Args:
            entry_price: Trade entry price
            stop_loss: Stop loss price
            direction: +1 for LONG, -1 for SHORT
            
        Returns:
            Dict with 'tp1', 'tp2', 'tp3' prices or empty dict on assertion failure
        """
        try:
            risk_per_unit = abs(entry_price - stop_loss)
            
            # ASSERTION 1: risk_unit must be positive
            if risk_per_unit <= 0:
                self.logger.error(
                    f"TP ASSERTION FAILED: risk_unit = {risk_per_unit:.2f} (must be > 0). "
                    f"entry={entry_price:.2f}, stop_loss={stop_loss:.2f}. ABORTING TP calculation."
                )
                return {}
            
            # Calculate TP levels
            tp1 = entry_price + direction * risk_per_unit * self.DEFAULT_TP1_RR
            tp2 = entry_price + direction * risk_per_unit * self.DEFAULT_TP2_RR
            
            # TP3 comes from settings; if it ends up closer than TP1/TP2 we honor it with priority
            rr = self.default_rr_long if direction == 1 else self.default_rr_short
            tp3_config = entry_price + direction * risk_per_unit * rr

            # Enforce priority when TP3 (from settings) is inside the TP1/TP2 range
            if direction == 1:
                tp3 = min(tp3_config, tp1, tp2)
            else:
                tp3 = max(tp3_config, tp1, tp2)
            
            # ASSERTION 2: Monotonic TP ordering
            if direction == 1:  # LONG: TP1 < TP2 < TP3
                if not (tp1 < tp2 < tp3):
                    self.logger.error(
                        f"TP ASSERTION FAILED: Non-monotonic LONG ordering. "
                        f"TP1={tp1:.2f}, TP2={tp2:.2f}, TP3={tp3:.2f}. "
                        f"Expected: TP1 < TP2 < TP3. ABORTING."
                    )
                    return {}
            else:  # SHORT: TP1 > TP2 > TP3
                if not (tp1 > tp2 > tp3):
                    self.logger.error(
                        f"TP ASSERTION FAILED: Non-monotonic SHORT ordering. "
                        f"TP1={tp1:.2f}, TP2={tp2:.2f}, TP3={tp3:.2f}. "
                        f"Expected: TP1 > TP2 > TP3. ABORTING."
                    )
                    return {}

            if tp3 != tp3_config:
                self.logger.info(
                    "TP3 adjusted to priority target because settings TP3 was inside TP1/TP2 range: "
                    f"config={tp3_config:.2f}, effective={tp3:.2f}"
                )
            
            self.logger.debug(
                f"TP Levels calculated (direction={direction}):\n"
                f"  Entry: {entry_price:.2f}\n"
                f"  SL: {stop_loss:.2f}\n"
                f"  Risk: {risk_per_unit:.2f}\n"
                f"  TP1 (1.4:1): {tp1:.2f}\n"
                f"  TP2 (1.8:1): {tp2:.2f}\n"
                f"  TP3 ({rr}:1): {tp3:.2f}"
            )
            
            return {
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'risk': risk_per_unit
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating TP levels: {e}")
            return {}
    
    def evaluate_exit(self, current_price: float, entry_price: float,
                     stop_loss: float, tp_state: str, tp_levels: Dict[str, float],
                     direction: int = 1, bar_close_confirmed: bool = True) -> Tuple[bool, str, Optional[str]]:
        """
        Evaluate exit conditions based on multi-level TP state machine.
        
        Args:
            current_price: Current market price
            entry_price: Trade entry price
            stop_loss: Current stop loss price
            tp_state: Current TP state (IN_TRADE, TP1_REACHED, TP2_REACHED)
            tp_levels: Dict with 'tp1', 'tp2', 'tp3' prices
            direction: +1 for LONG, -1 for SHORT
            
        Returns:
            Tuple of (should_exit, reason, new_tp_state)
        """
        try:
            # Guard: never exit intrabar for TP events
            if not bar_close_confirmed:
                return False, "Waiting for bar close", tp_state

            # Always check stop loss first
            if direction == 1:  # LONG
                if current_price <= stop_loss:
                    return True, "Stop Loss", TPState.EXITED.value
            else:  # SHORT
                if current_price >= stop_loss:
                    return True, "Stop Loss", TPState.EXITED.value

            # Priority check: TP3 may be inside TP1/TP2 range (from settings)
            tp3_price = tp_levels.get('tp3')
            if tp3_price is not None:
                if direction == 1 and current_price >= tp3_price:
                    self.logger.info(f"TP3 (priority) REACHED on bar close: {current_price:.2f} >= {tp3_price:.2f}")
                    return True, "TP3 Exit", TPState.EXITED.value
                if direction == -1 and current_price <= tp3_price:
                    self.logger.info(f"TP3 (priority) REACHED on bar close: {current_price:.2f} <= {tp3_price:.2f}")
                    return True, "TP3 Exit", TPState.EXITED.value
            
            # State machine logic
            if tp_state == TPState.IN_TRADE.value:
                # Check if TP1 reached
                if direction == 1:  # LONG
                    if current_price >= tp_levels.get('tp1', 0):
                        self.logger.info(f"TP1 REACHED: {current_price:.2f} >= {tp_levels['tp1']:.2f}")
                        return False, "TP1 Reached - Moving SL to Breakeven", TPState.TP1_REACHED.value
                else:  # SHORT
                    if current_price <= tp_levels.get('tp1', 0):
                        self.logger.info(f"TP1 REACHED: {current_price:.2f} <= {tp_levels['tp1']:.2f}")
                        return False, "TP1 Reached - Moving SL to Breakeven", TPState.TP1_REACHED.value
                
                # NO_EXIT: Still in trade, TP1 not reached (SILENT_NO_TRADE mitigation)
                self.logger.debug(f"IN_TRADE: Position open, TP1 not reached at {current_price:.2f}")
                return False, "Position open", tp_state
            
            elif tp_state == TPState.TP1_REACHED.value:
                # Check if TP2 reached
                if direction == 1:  # LONG
                    if current_price >= tp_levels.get('tp2', 0):
                        self.logger.info(f"TP2 REACHED: {current_price:.2f} >= {tp_levels['tp2']:.2f}")
                        return False, "TP2 Reached - Trailing SL Active", TPState.TP2_REACHED.value
                else:  # SHORT
                    if current_price <= tp_levels.get('tp2', 0):
                        self.logger.info(f"TP2 REACHED: {current_price:.2f} <= {tp_levels['tp2']:.2f}")
                        return False, "TP2 Reached - Trailing SL Active", TPState.TP2_REACHED.value
                
                # NO_EXIT: TP1 reached but TP2 not reached yet (SILENT_NO_TRADE mitigation)
                self.logger.debug(f"TP1_REACHED: Position open, TP2 not reached at {current_price:.2f}")
                return False, "Position open - TP1 Reached", tp_state
            
            elif tp_state == TPState.TP2_REACHED.value:
                # Check if TP3 reached (full close)
                if direction == 1:  # LONG
                    if current_price >= tp_levels.get('tp3', 0):
                        self.logger.info(f"TP3 REACHED on bar close: {current_price:.2f} >= {tp_levels['tp3']:.2f}")
                        return True, "TP3 Exit", TPState.EXITED.value
                else:  # SHORT
                    if current_price <= tp_levels.get('tp3', 0):
                        self.logger.info(f"TP3 REACHED on bar close: {current_price:.2f} <= {tp_levels['tp3']:.2f}")
                        return True, "TP3 Exit", TPState.EXITED.value
                
                # NO_EXIT: TP2 reached but TP3 not reached yet (SILENT_NO_TRADE mitigation)
                self.logger.debug(f"TP2_REACHED: Position open, TP3 not reached at {current_price:.2f}")
                return False, "Position open - TP2 Reached", tp_state
            
            # NO_EXIT: Unknown or invalid state (SILENT_NO_TRADE mitigation)
            self.logger.debug(f"Position open in state {tp_state}")
            return False, "Position open", tp_state
            
        except Exception as e:
            self.logger.error(f"Error evaluating exit: {e}")
            return False, "Error", tp_state
    
    def calculate_new_stop_loss(self, current_price: float, entry_price: float,
                               tp_state: str, direction: int = 1,
                               trailing_offset: float = 0.5) -> Optional[float]:
        """
        Calculate new stop loss based on TP state.
        
        - TP1_REACHED: Move to entry price (breakeven)
        - TP2_REACHED: Trail by fixed offset (e.g., last structure or ATR)
        
        Args:
            current_price: Current market price
            entry_price: Trade entry price
            tp_state: Current TP state
            direction: +1 for LONG, -1 for SHORT
            trailing_offset: Points to trail behind current price
            
        Returns:
            New stop loss price, or None if no change
        """
        try:
            if tp_state == TPState.TP1_REACHED.value:
                # Move SL to entry price (breakeven protection)
                self.logger.info(f"Moving SL to entry (breakeven): {entry_price:.2f}")
                return entry_price
            
            elif tp_state == TPState.TP2_REACHED.value:
                # Trail SL behind current price
                if direction == 1:  # LONG
                    new_sl = current_price - trailing_offset
                    self.logger.info(f"Trailing SL: {new_sl:.2f} (offset: {trailing_offset})")
                    return new_sl
                else:  # SHORT
                    new_sl = current_price + trailing_offset
                    self.logger.info(f"Trailing SL: {new_sl:.2f} (offset: {trailing_offset})")
                    return new_sl
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error calculating new SL: {e}")
            return None
    
    def get_next_target(self, tp_state: str, tp_levels: Dict[str, float]) -> Optional[float]:
        """Get next target price based on current TP state."""
        if tp_state == TPState.IN_TRADE.value:
            return tp_levels.get('tp1')
        elif tp_state == TPState.TP1_REACHED.value:
            return tp_levels.get('tp2')
        elif tp_state == TPState.TP2_REACHED.value:
            return tp_levels.get('tp3')
        return None

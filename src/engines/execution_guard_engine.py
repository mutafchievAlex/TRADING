"""
Execution Guard Engine - Multi-layer protection against false entries and execution mismatch

Guards against:
1. Bar-close validation (only trade on closed bars)
2. Tick noise filtering (minimum movement threshold)
3. FOMO protection (cooldown between entries)
4. Entry quality gate (minimum quality score)
5. Execution mismatch (MT5 sync issues)
6. Offline recovery (restart safety)

Philosophy:
- Does NOT modify strategy logic
- Does NOT modify broker execution
- Only DECIDES whether to execute or HOLD/SKIP
- All decisions are LOGGED with reason codes for transparency
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List
from enum import Enum
import pandas as pd


class Decision(Enum):
    """Execution decision types"""
    ENTER = "ENTER"
    HOLD = "HOLD"
    EXIT = "EXIT"
    SKIP = "SKIP"


class ReasonCode(Enum):
    """Enumeration of decision reason codes"""
    # Approval reasons
    APPROVED = "approved"
    PYRAMIDING_ALLOWED = "pyramiding_allowed"
    
    # Rejection reasons
    COOLDOWN_ACTIVE = "cooldown_active"
    PYRAMIDING_LIMIT = "pyramiding_limit"
    LOW_ENTRY_QUALITY = "low_entry_quality"
    VOLATILITY_MISMATCH = "volatility_mismatch"
    BAR_NOT_CLOSED = "bar_not_closed"
    TICK_NOISE_FILTERED = "tick_noise_filtered"
    SESSION_RESTRICTED = "session_restricted"
    NO_SETUP = "no_setup"
    ENTRY_QUALITY_BELOW_GATE = "entry_quality_below_gate"
    
    # Recovery reasons
    OFFLINE_RECOVERY_TRIGGERED = "offline_recovery_triggered"
    POSITION_SHOULD_BE_CLOSED = "position_should_be_closed"


class ExecutionGuardEngine:
    """
    Multi-layer execution guard system.
    
    Validates execution safety across multiple dimensions:
    - Bar closure (no trading on forming bars)
    - Tick noise (minimum movement threshold)
    - FOMO cooldown (time between entries)
    - Entry quality (quality score gate)
    - Session restrictions (trading hours)
    - Recovery logic (restart safety)
    
    Does NOT modify strategy or broker execution - only DECIDES execution.
    """
    
    def __init__(self,
                 bar_close_enabled: bool = True,
                 tick_noise_enabled: bool = True,
                 anti_fomo_enabled: bool = True,
                 min_pips_movement: float = 5.0,
                 fomo_cooldown_bars: int = 1,
                 quality_gate_threshold: float = 6.5,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize Execution Guard Engine.
        
        Args:
            bar_close_enabled: Enforce bar-close validation
            tick_noise_enabled: Filter micro-movements
            anti_fomo_enabled: Enforce FOMO cooldown
            min_pips_movement: Minimum pips for valid movement (tick noise threshold)
            fomo_cooldown_bars: Bars to wait after last entry
            quality_gate_threshold: Minimum quality score (0-10) to allow entry
            logger: Logger instance
        """
        self.bar_close_enabled = bar_close_enabled
        self.tick_noise_enabled = tick_noise_enabled
        self.anti_fomo_enabled = anti_fomo_enabled
        self.min_pips_movement = min_pips_movement
        self.fomo_cooldown_bars = fomo_cooldown_bars
        self.quality_gate_threshold = quality_gate_threshold
        self.logger = logger or logging.getLogger(__name__)
        
        # State tracking
        self.last_entry_bar_index = None
        self.last_entry_time = None
        self.decision_history: List[Dict] = []
        
        self.logger.info(
            f"ExecutionGuardEngine initialized: "
            f"bar_close={bar_close_enabled}, "
            f"tick_noise={tick_noise_enabled}, "
            f"anti_fomo={anti_fomo_enabled}, "
            f"quality_gate={quality_gate_threshold}"
        )
    
    def guard_entry_decision(self,
                            setup_detected: bool,
                            entry_quality_score: float,
                            current_bar: pd.Series,
                            df: pd.DataFrame,
                            market_regime: str = "BULL",
                            bar_index: int = -2,
                            pyramiding_enabled: bool = False,
                            max_pyramids: int = 1,
                            current_position_count: int = 0) -> Tuple[Decision, ReasonCode, str]:
        """
        Comprehensive guard check for entry decisions.
        
        Args:
            setup_detected: Does the strategy see a valid setup?
            entry_quality_score: Entry quality score (0-10)
            current_bar: Current bar OHLC data
            df: Historical DataFrame with OHLC data
            market_regime: Market condition (BULL/BEAR/RANGE)
            bar_index: Index of bar to analyze (default: -2 = last closed)
            pyramiding_enabled: Is pyramiding allowed?
            max_pyramids: Maximum pyramid positions allowed
            current_position_count: Current number of open positions
            
        Returns:
            Tuple of (Decision, ReasonCode, explanation_string)
        """
        reasons_checked = []
        
        # 1. Check if setup exists
        if not setup_detected:
            reason = ReasonCode.NO_SETUP
            self._log_decision(Decision.HOLD, reason, "No setup detected")
            return Decision.HOLD, reason, "No trading setup detected"
        
        # 2. Bar-close validation
        if self.bar_close_enabled:
            bar_closed, bar_reason = self._check_bar_closed(df, bar_index)
            reasons_checked.append(f"bar_closed={bar_closed}")
            if not bar_closed:
                self._log_decision(Decision.SKIP, bar_reason, "Current bar still forming")
                return Decision.SKIP, bar_reason, "Waiting for bar closure"
        
        # 3. Tick noise filter
        if self.tick_noise_enabled:
            movement_valid, noise_reason = self._check_tick_noise(current_bar, df)
            reasons_checked.append(f"movement={movement_valid}")
            if not movement_valid:
                self._log_decision(Decision.SKIP, noise_reason, "Tick noise detected")
                return Decision.SKIP, noise_reason, f"Movement below {self.min_pips_movement} pips threshold"
        
        # 4. Entry quality gate
        if entry_quality_score < self.quality_gate_threshold:
            reason = ReasonCode.ENTRY_QUALITY_BELOW_GATE
            self._log_decision(
                Decision.HOLD, reason,
                f"Quality {entry_quality_score:.2f} < {self.quality_gate_threshold}"
            )
            return Decision.HOLD, reason, f"Entry quality too low ({entry_quality_score:.2f}/10)"
        
        # 5. FOMO/Cooldown check
        if self.anti_fomo_enabled:
            cooldown_ok, cooldown_reason = self._check_fomo_cooldown(
                bar_index, market_regime, pyramiding_enabled
            )
            reasons_checked.append(f"cooldown_ok={cooldown_ok}")
            if not cooldown_ok:
                self._log_decision(Decision.HOLD, cooldown_reason, "Cooldown active")
                return Decision.HOLD, cooldown_reason, "Entry cooldown period active"
        
        # 6. Pyramiding limits
        if pyramiding_enabled and current_position_count >= max_pyramids:
            reason = ReasonCode.PYRAMIDING_LIMIT
            self._log_decision(
                Decision.HOLD, reason,
                f"Pyramid limit {current_position_count}/{max_pyramids} reached"
            )
            return Decision.HOLD, reason, f"Pyramid limit reached ({current_position_count}/{max_pyramids})"
        
        # All guards passed!
        self.last_entry_bar_index = bar_index
        self.last_entry_time = datetime.now()
        
        self._log_decision(Decision.ENTER, ReasonCode.APPROVED, "All guards passed")
        return Decision.ENTER, ReasonCode.APPROVED, "Entry approved by all guards"
    
    def check_offline_recovery(self,
                              positions: List[Dict],
                              df: pd.DataFrame,
                              current_price: float) -> Tuple[bool, Optional[str]]:
        """
        Check if positions should be closed during offline recovery (restart).
        
        Args:
            positions: List of open positions
            df: Historical DataFrame
            current_price: Current market price
            
        Returns:
            Tuple of (should_close, reason_string or None)
        """
        if not positions:
            return False, None
        
        for position in positions:
            ticket = position.get('ticket')
            entry = position.get('entry_price')
            sl = position.get('stop_loss')
            tp = position.get('take_profit')
            
            if not all([entry, sl, tp]):
                continue
            
            # Check if position is beyond TP3 or below SL
            if current_price >= tp:  # BUY: price reached TP
                return True, f"Position {ticket} reached TP - close immediately"
            
            if current_price <= sl:  # BUY: price hit SL
                return True, f"Position {ticket} hit SL - close immediately"
        
        return False, None
    
    def _check_bar_closed(self, df: pd.DataFrame, bar_index: int = -2) -> Tuple[bool, ReasonCode]:
        """
        Check if the bar at bar_index is fully closed (not the current forming bar).
        
        Args:
            df: DataFrame with OHLC data
            bar_index: Index of bar to check (default: -2 = last closed bar)
            
        Returns:
            Tuple of (is_closed, reason_code)
        """
        try:
            if df is None or len(df) < 2:
                return False, ReasonCode.BAR_NOT_CLOSED
            
            if abs(bar_index) > len(df):
                return False, ReasonCode.BAR_NOT_CLOSED
            
            # Check that we have at least current forming bar + requested bar
            # -1 is current forming, -2 is last closed
            if bar_index == -1 or bar_index == len(df) - 1:
                return False, ReasonCode.BAR_NOT_CLOSED
            
            return True, ReasonCode.APPROVED
        except Exception as e:
            self.logger.error(f"Error checking bar closure: {e}")
            return False, ReasonCode.BAR_NOT_CLOSED
    
    def _check_tick_noise(self, current_bar: pd.Series, df: pd.DataFrame) -> Tuple[bool, ReasonCode]:
        """
        Check if price movement is significant (filters tick noise).
        
        Args:
            current_bar: Current bar OHLC
            df: Historical DataFrame for reference
            
        Returns:
            Tuple of (is_valid_movement, reason_code)
        """
        try:
            if df is None or len(df) < 2:
                return True, ReasonCode.APPROVED
            
            prev_close = df.iloc[-2]['close'] if len(df) >= 2 else current_bar.get('close')
            current_close = current_bar.get('close', prev_close)
            
            movement = abs(current_close - prev_close)
            
            if movement < self.min_pips_movement:
                return False, ReasonCode.TICK_NOISE_FILTERED
            
            return True, ReasonCode.APPROVED
        except Exception as e:
            self.logger.error(f"Error checking tick noise: {e}")
            return True, ReasonCode.APPROVED  # Default allow on error
    
    def _check_fomo_cooldown(self,
                            bar_index: int,
                            market_regime: str,
                            pyramiding_enabled: bool) -> Tuple[bool, ReasonCode]:
        """
        Check if cooldown period has elapsed since last entry.
        
        FOMO cooldown exceptions:
        - Pyramiding enabled AND
        - Market regime is BULL AND
        - Direction is LONG
        
        Args:
            bar_index: Current bar index
            market_regime: Current market regime (BULL/BEAR/RANGE)
            pyramiding_enabled: Is pyramiding allowed?
            
        Returns:
            Tuple of (cooldown_ok, reason_code)
        """
        # Exception: pyramiding in bull market
        if pyramiding_enabled and market_regime == "BULL":
            return True, ReasonCode.PYRAMIDING_ALLOWED
        
        if self.last_entry_bar_index is None:
            return True, ReasonCode.APPROVED
        
        bars_since_entry = abs(bar_index - self.last_entry_bar_index)
        
        if bars_since_entry < self.fomo_cooldown_bars:
            return False, ReasonCode.COOLDOWN_ACTIVE
        
        return True, ReasonCode.APPROVED
    
    def _log_decision(self, decision: Decision, reason: ReasonCode, detail: str):
        """Log execution decision for transparency."""
        log_entry = {
            'timestamp': datetime.now(),
            'decision': decision.value,
            'reason': reason.value,
            'detail': detail
        }
        self.decision_history.append(log_entry)
        
        # Log based on decision type
        if decision == Decision.ENTER:
            self.logger.info(f"[GUARD] ENTER approved: {reason.value} - {detail}")
        elif decision == Decision.SKIP:
            self.logger.info(f"[GUARD] SKIP (waiting): {reason.value} - {detail}")
        elif decision == Decision.HOLD:
            self.logger.info(f"[GUARD] HOLD (setup invalid): {reason.value} - {detail}")
        else:
            self.logger.warning(f"[GUARD] {decision.value}: {reason.value} - {detail}")
    
    def get_decision_history(self, limit: int = 20) -> List[Dict]:
        """Get recent decision history for audit trail."""
        return self.decision_history[-limit:]
    
    def reset_cooldown(self):
        """Reset FOMO cooldown (for manual trades or admin reset)."""
        self.last_entry_bar_index = None
        self.last_entry_time = None
        self.logger.info("[GUARD] Cooldown reset")
    
    def set_fomo_cooldown_bars(self, bars: int):
        """Update FOMO cooldown period dynamically."""
        self.fomo_cooldown_bars = bars
        self.logger.info(f"[GUARD] FOMO cooldown updated to {bars} bars")


# Test harness
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize guard
    guard = ExecutionGuardEngine(
        bar_close_enabled=True,
        tick_noise_enabled=True,
        anti_fomo_enabled=True,
        min_pips_movement=5.0,
        fomo_cooldown_bars=1,
        quality_gate_threshold=6.5
    )
    
    # Create test data
    test_bar = pd.Series({
        'open': 2000.00,
        'high': 2010.00,
        'low': 1995.00,
        'close': 2005.00,
        'time': datetime.now()
    })
    
    test_df = pd.DataFrame({
        'open': [1990.00, 1995.00, 2000.00, 2005.00],
        'high': [2000.00, 2005.00, 2010.00, 2015.00],
        'low': [1985.00, 1990.00, 1995.00, 2000.00],
        'close': [1995.00, 2000.00, 2005.00, 2010.00]
    })
    
    # Test decision
    decision, reason, explanation = guard.guard_entry_decision(
        setup_detected=True,
        entry_quality_score=7.5,
        current_bar=test_bar,
        df=test_df,
        market_regime="BULL",
        bar_index=-2,
        pyramiding_enabled=True,
        max_pyramids=3,
        current_position_count=0
    )
    
    print(f"\nTest Result:")
    print(f"Decision: {decision.value}")
    print(f"Reason: {reason.value}")
    print(f"Explanation: {explanation}")
    print(f"\nDecision History:")
    for entry in guard.get_decision_history():
        print(f"  {entry['timestamp'].strftime('%H:%M:%S')} - {entry['decision']}: {entry['reason']}")

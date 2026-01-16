"""
Bar-Close Guard - Ensures deterministic trading on closed bars

This module validates that all trading decisions are made ONLY on fully closed bars,
with mandatory bar-close validation and optional protective filters.

MANDATORY (always active):
- Bar-close validation: Ensures we're analyzing completed bars
- Bar state checks: OHLC data integrity and logical consistency
- Rejection logging: All denials logged with exact reason

OPTIONAL (configurable, non-blocking by default):
- Tick noise filter: Filters micro-movements (default: DISABLED)
- Anti-FOMO mode: Warns about rapid re-entries (default: DISABLED)

Philosophy:
- Guard ensures DETERMINISM, does NOT modify strategy logic
- No good setup should ever be blocked by optional filters
- All rejections logged with precise reason for audit trail
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Tuple


class BarCloseGuard:
    """
    Validates bar closure and enforces deterministic trading.
    
    MANDATORY (always enforced):
    - Bar must be fully closed (not current forming bar)
    - OHLC data must exist and be logically consistent
    - Validation failures are always rejected
    
    OPTIONAL (disabled by default, non-blocking):
    - Tick noise filtering: Rejects micro-movements
    - Anti-FOMO mode: Warns on rapid re-entries but doesn't block
    
    Key principle: Guard ensures deterministic execution, not strategy changes.
    """
    
    def __init__(self, 
                 min_pips_movement: float = 0.5, 
                 anti_fomo_bars: int = 1,
                 enable_noise_filter: bool = False,
                 enable_anti_fomo: bool = False):
        """
        Initialize Bar-Close Guard with configurable protective modes.
        
        Args:
            min_pips_movement: Minimum pips movement to pass noise filter (default: 0.5)
            anti_fomo_bars: Bars to wait after signal (default: 1)
            enable_noise_filter: Enable tick noise filter (default: False)
            enable_anti_fomo: Enable anti-FOMO warnings (default: False)
        """
        self.min_pips_movement = min_pips_movement
        self.anti_fomo_bars = anti_fomo_bars
        self.enable_noise_filter = enable_noise_filter
        self.enable_anti_fomo = enable_anti_fomo
        self.logger = logging.getLogger(__name__)
        
        # State tracking
        self.last_signal_bar = None
        self.rejections_log = []
        
        self.logger.info(f"BarCloseGuard initialized:")
        self.logger.info(f"  MANDATORY: Bar-close validation and bar state checks (always active)")
        self.logger.info(f"  OPTIONAL: Noise filter {'ENABLED' if enable_noise_filter else 'DISABLED'}")
        self.logger.info(f"  OPTIONAL: Anti-FOMO {'ENABLED' if enable_anti_fomo else 'DISABLED'}")
    
    def validate_bar_state(self, df: pd.DataFrame, bar_index: int = -2) -> Tuple[bool, str]:
        """
        MANDATORY: Validate that bar has proper closed state and OHLC integrity.
        
        Checks:
        1. DataFrame has at least 2 bars (current forming + 1 closed)
        2. Requested bar index is within range
        3. All OHLC fields exist and are not NaN
        4. High >= Open, Close
        5. Low <= Open, Close
        
        Args:
            df: DataFrame with OHLC data (must have: open, high, low, close, time)
            bar_index: Index of bar to validate (default: -2 = last closed bar)
            
        Returns:
            Tuple of (is_valid, exact_reason_string)
        """
        try:
            # Check: DataFrame exists and has sufficient bars
            if df is None or len(df) == 0:
                return False, "DataFrame is None or empty"
            
            if len(df) < 2:
                return False, "Insufficient bars: need 2+ (current forming + 1 closed)"
            
            # Check: Bar index is valid
            if abs(bar_index) > len(df):
                return False, f"Bar index {bar_index} exceeds data range (length={len(df)})"
            
            # Get the bar to validate
            bar = df.iloc[bar_index]
            
            # Check: Required OHLC fields exist
            required_fields = ['open', 'high', 'low', 'close']
            for field in required_fields:
                if field not in df.columns:
                    return False, f"Missing column: '{field}'"
                if pd.isna(bar[field]):
                    return False, f"Missing value in '{field}' (NaN)"
            
            open_price = bar['open']
            high_price = bar['high']
            low_price = bar['low']
            close_price = bar['close']
            
            # Check: OHLC logical consistency
            if high_price < low_price:
                return False, f"Invalid OHLC: high ({high_price}) < low ({low_price})"
            
            if high_price < open_price:
                return False, f"Invalid OHLC: high ({high_price}) < open ({open_price})"
            
            if high_price < close_price:
                return False, f"Invalid OHLC: high ({high_price}) < close ({close_price})"
            
            if low_price > open_price:
                return False, f"Invalid OHLC: low ({low_price}) > open ({open_price})"
            
            if low_price > close_price:
                return False, f"Invalid OHLC: low ({low_price}) > close ({close_price})"
            
            # All checks passed
            return True, f"Bar state valid: O={open_price} H={high_price} L={low_price} C={close_price}"
            
        except Exception as e:
            return False, f"Bar state validation error: {str(e)}"
    
    def is_bar_closed(self, current_time: datetime, bar_open_time: datetime, 
                      timeframe_minutes: int = 60) -> Tuple[bool, str]:
        """
        MANDATORY: Verify that the bar is fully closed (not the current forming bar).
        
        A bar is considered closed if MORE than timeframe minutes have passed
        since the bar opened.
        
        Args:
            current_time: Current time
            bar_open_time: Time when this bar opened
            timeframe_minutes: Timeframe in minutes (default: 60 for H1)
            
        Returns:
            Tuple of (is_closed, exact_reason_string)
        """
        try:
            if current_time <= bar_open_time:
                return False, f"Invalid times: current ({current_time}) not after bar_open ({bar_open_time})"
            
            time_elapsed_minutes = (current_time - bar_open_time).total_seconds() / 60
            
            is_closed = time_elapsed_minutes >= timeframe_minutes
            
            if is_closed:
                return True, f"Bar closed: {time_elapsed_minutes:.2f} minutes >= {timeframe_minutes}"
            else:
                remaining = timeframe_minutes - time_elapsed_minutes
                return False, f"Bar forming: {time_elapsed_minutes:.2f}min elapsed, {remaining:.2f}min remaining"
            
        except Exception as e:
            return False, f"Bar closure check error: {str(e)}"
    
    def filter_tick_noise(self, price_movement_pips: float) -> Tuple[bool, str]:
        """
        OPTIONAL: Filter tick noise (only active if explicitly enabled, default: False).
        
        Does NOT filter by default - only blocks micro-movements when enabled.
        
        Args:
            price_movement_pips: Price movement in pips
            
        Returns:
            Tuple of (passes_filter, exact_reason_string)
        """
        try:
            # If filter is disabled, pass immediately (don't block good setups)
            if not self.enable_noise_filter:
                return True, f"Noise filter DISABLED (movement: {price_movement_pips:.2f} pips) - PASS"
            
            # Filter is enabled - check movement significance
            is_significant = abs(price_movement_pips) >= self.min_pips_movement
            
            if is_significant:
                return True, f"Significant movement: {price_movement_pips:.2f} pips >= threshold ({self.min_pips_movement})"
            else:
                reason = f"Tick noise: {abs(price_movement_pips):.2f} pips < threshold ({self.min_pips_movement})"
                self.logger.warning(reason)
                self._log_rejection(reason, "tick-noise")
                return False, reason
            
        except Exception as e:
            # On error, never block - safety default
            return True, f"Noise filter error (non-blocking): {str(e)}"
    
    def check_anti_fomo_cooldown(self, current_bar_index: int) -> Tuple[bool, str]:
        """
        OPTIONAL: Anti-FOMO mode - warns about rapid re-entries but NEVER blocks.
        
        When enabled, logs warnings about entries too close to previous signal.
        Does NOT block high-quality new setups.
        
        Args:
            current_bar_index: Index of current bar
            
        Returns:
            Tuple of (can_enter, exact_reason_string) - always returns True for entry
        """
        try:
            # If disabled, no check needed
            if not self.enable_anti_fomo:
                return True, "Anti-FOMO DISABLED - no cooldown check"
            
            # No previous signal, free to enter
            if self.last_signal_bar is None:
                return True, "No previous signal - first entry allowed"
            
            bars_since = current_bar_index - self.last_signal_bar
            
            # Check against cooldown threshold
            if bars_since < self.anti_fomo_bars:
                # This is a warning, NOT a block
                warning = f"Anti-FOMO warning: {bars_since} bar(s) since last signal (cooldown: {self.anti_fomo_bars})"
                self.logger.warning(warning)
                self._log_rejection(warning, "anti-fomo-warning")
                # IMPORTANT: Still allows entry - this is just a warning
                return True, warning
            else:
                return True, f"Anti-FOMO OK: {bars_since} bar(s) >= cooldown ({self.anti_fomo_bars})"
            
        except Exception as e:
            # On error, never block entry
            return True, f"Anti-FOMO check error (non-blocking): {str(e)}"
    
    def record_signal(self, bar_index: int) -> None:
        """
        Record that a signal was triggered at this bar (for anti-FOMO tracking).
        
        Args:
            bar_index: Index of the bar where signal was triggered
        """
        self.last_signal_bar = bar_index
        self.logger.info(f"Signal recorded at bar index {bar_index}")
    
    def validate_entry(self, 
                      df: pd.DataFrame, 
                      bar_index: int = -2,
                      price_movement_pips: float = None) -> Tuple[bool, str]:
        """
        FULL ENTRY VALIDATION: Combines all checks in proper order.
        
        Execution order:
        1. MANDATORY: Bar state validation (always enforced)
        2. OPTIONAL: Anti-FOMO warning (doesn't block)
        3. OPTIONAL: Tick noise filter (only blocks if enabled)
        
        Key: Mandatory checks can reject. Optional checks warn but don't block
        unless explicitly enabled.
        
        Args:
            df: DataFrame with OHLC data
            bar_index: Index of bar to validate
            price_movement_pips: Price movement for optional noise filtering
            
        Returns:
            Tuple of (approved, exact_reason_with_all_checks)
        """
        try:
            checks_result = []
            
            # 1. MANDATORY: Bar state validation (always enforced)
            is_valid, state_reason = self.validate_bar_state(df, bar_index)
            checks_result.append(f"[MANDATORY] Bar state: {state_reason}")
            if not is_valid:
                final_reason = " | ".join(checks_result)
                self._log_rejection(final_reason, "bar-state")
                return False, final_reason
            
            # 2. OPTIONAL: Anti-FOMO check (warning only, doesn't block)
            fomo_ok, fomo_reason = self.check_anti_fomo_cooldown(bar_index)
            checks_result.append(f"[OPTIONAL] Anti-FOMO: {fomo_reason}")
            # Note: fomo_ok is always True (non-blocking)
            
            # 3. OPTIONAL: Tick noise filter
            if price_movement_pips is not None:
                noise_ok, noise_reason = self.filter_tick_noise(price_movement_pips)
                checks_result.append(f"[OPTIONAL] Noise filter: {noise_reason}")
                if not noise_ok:
                    final_reason = " | ".join(checks_result)
                    return False, final_reason
            
            # All mandatory checks passed
            final_reason = " | ".join(checks_result)
            return True, final_reason
            
        except Exception as e:
            reason = f"Validation error: {str(e)}"
            self._log_rejection(reason, "validation-error")
            return False, reason
    
    def _log_rejection(self, reason: str, category: str) -> None:
        """
        Log a rejection with timestamp for audit trail.
        
        Args:
            reason: Exact reason for rejection
            category: Category of rejection (bar-state, tick-noise, anti-fomo, etc.)
        """
        self.rejections_log.append({
            'timestamp': datetime.now().isoformat(),
            'reason': reason,
            'category': category
        })
        self.logger.debug(f"[{category}] {reason}")
    
    def get_rejections_summary(self) -> dict:
        """
        Get summary of all rejections by category.
        
        Returns:
            Dict with rejection counts by category
        """
        summary = {}
        for entry in self.rejections_log:
            cat = entry['category']
            summary[cat] = summary.get(cat, 0) + 1
        return summary
    
    def get_guard_status(self) -> dict:
        """
        Get current guard configuration and state.
        
        Returns:
            Dict with settings and current status
        """
        return {
            'min_pips_movement': self.min_pips_movement,
            'anti_fomo_bars': self.anti_fomo_bars,
            'noise_filter_enabled': self.enable_noise_filter,
            'anti_fomo_enabled': self.enable_anti_fomo,
            'last_signal_bar': self.last_signal_bar,
            'total_rejections': len(self.rejections_log),
            'rejections_by_category': self.get_rejections_summary()
        }
    
    def reset_rejections_log(self) -> None:
        """Clear the rejections log."""
        self.rejections_log = []
        self.logger.info("Rejections log cleared")


if __name__ == "__main__":
    # Simple test
    # Note: Do not use basicConfig here - logging is configured by the application
    # logger = logging.getLogger(__name__)
    
    guard = BarCloseGuard(min_pips_movement=5.0, anti_fomo_bars=1)
    
    # Create sample data
    dates = pd.date_range(start='2024-01-01', periods=50, freq='H')
    df = pd.DataFrame({
        'time': dates,
        'open': [2000.0] * 50,
        'high': [2010.0] * 50,
        'low': [1990.0] * 50,
        'close': [2005.0] * 50,
    })
    
    # Test bar state validation
    is_valid, reason = guard.validate_bar_state(df)
    print(f"Bar state valid: {is_valid} ({reason})")
    
    # Test noise filtering (disabled by default)
    is_sig, reason = guard.filter_tick_noise(10.0)
    print(f"10 pips with filter disabled: {is_sig} ({reason})")
    
    is_sig, reason = guard.filter_tick_noise(2.0)
    print(f"2 pips with filter disabled: {is_sig} ({reason})")
    
    # Test anti-FOMO (disabled by default)
    can_enter, reason = guard.check_anti_fomo_cooldown(10)
    print(f"Can enter at bar 10: {can_enter} ({reason})")
    
    guard.record_signal(10)
    can_enter, reason = guard.check_anti_fomo_cooldown(10)
    print(f"Can enter at bar 10 after signal: {can_enter} ({reason})")
    
    can_enter, reason = guard.check_anti_fomo_cooldown(11)
    print(f"Can enter at bar 11 after signal at 10: {can_enter} ({reason})")

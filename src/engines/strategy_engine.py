"""
Strategy Engine - Evaluates entry and exit conditions

This module implements the complete trading strategy logic,
evaluating all conditions for entries and exits.

Entry conditions (ALL must be true):
1. Valid Double Bottom detected
2. Close breaks above neckline
3. Close > EMA50
4. Breakout candle has sufficient momentum (ATR-based)
5. Cooldown period respected

Exit conditions:
- Stop Loss hit (ATR-based or swing-based)
- Take Profit hit (Risk × RR)

═══════════════════════════════════════════════════════════════════════════════
MULTI-LEVEL TP STATE MACHINE
═══════════════════════════════════════════════════════════════════════════════

Position Life Cycle:

    ┌──────────────┐
    │   IN_TRADE   │  ← Position opened, no TP reached yet
    └──────┬───────┘
           │ Price reaches TP1 (1.4x RR)
           │ • SL tightened to breakeven
           │ • Partial position closed (optional)
           │ • Counters reset
           │
    ┌──────▼─────────────┐
    │  TP1_REACHED      │  ← TP1 level touched, waiting for TP2
    │  (TOUCHED state)   │  • SL follows via trailing mechanism
    │                    │  • bars_held_after_tp1 incremented each bar
    └──────┬─────────────┘
           │ Price reaches TP2 (1.9x RR)
           │ • SL moves to TP1 (lock in profit)
           │ • Second partial close (optional)
           │ • bars_held_after_tp1 ceases incrementing
           │
    ┌──────▼──────────────────┐
    │  TP2_REACHED            │  ← TP2 level touched, managing to TP3
    │  (ACTIVE_MANAGEMENT)    │  • SL follows trailing mechanism
    │                          │  • bars_held_after_tp2 incremented each bar
    └──────┬──────────────────┘
           │ Price reaches TP3 (2.0x RR) OR SL hit
           │ • Final close
           │ • Position closed
           │
    ┌──────▼─────────┐
    │    CLOSED       │  ← Position fully closed
    │  (COMPLETED)    │  • All counters persist for analysis
    └────────────────┘

State Transitions:
• IN_TRADE       → TP1_REACHED:  When close >= TP1 price
• TP1_REACHED    → TP2_REACHED:  When close >= TP2 price
• TP2_REACHED    → CLOSED:       When close >= TP3 OR SL hit
• Any state      → CLOSED:       Manual exit or externally closed position

Counter Tracking:
• bars_held_after_tp1: Incremented while TP1_REACHED (becomes 0 on TP2_REACHED)
• bars_held_after_tp2: Incremented while TP2_REACHED (becomes 0 on CLOSED)
• Persisted to state.json for post-trade analysis

SL Management Strategy:
• Entry to TP1:  SL = Entry - (2.0 × ATR14)
• TP1 reached:   SL = Entry (breakeven protection)
• TP2 reached:   SL = TP1 (lock in first profit target)
• Beyond TP2:    SL = Price - Trailing Offset (0.5 pips)

"""

import pandas as pd
from typing import Optional, Tuple, Dict
import logging
from datetime import datetime, timedelta
from .bar_close_guard import BarCloseGuard
from .multi_level_tp_engine import MultiLevelTPEngine, TPState
from .tp1_exit_decision_engine import (
    TP1ExitDecisionEngine, 
    TP1EvaluationContext,
    PostTP1Decision,
    MomentumState,
    MarketRegime
)
from .tp2_exit_decision_engine import (
    TP2ExitDecisionEngine,
    TP2EvaluationContext,
    PostTP2Decision as PostTP2DecisionEnum,
    StructureState
)


class StrategyEngine:
    """
    Evaluates all trading strategy conditions.
    
    Responsibilities:
    - Check entry conditions
    - Calculate stop loss and take profit levels
    - Check exit conditions
    - Manage trade cooldowns
    """
    
    def __init__(self, 
                 atr_multiplier_stop: float = 2.0,
                 risk_reward_ratio_long: float = 2.0,
                 risk_reward_ratio_short: float = 2.0,
                 momentum_atr_threshold: float = 0.5,
                 enable_momentum_filter: bool = True,
                 cooldown_hours: int = 24):
        """
        Initialize Strategy Engine.
        
        Args:
            atr_multiplier_stop: ATR multiplier for stop loss (default: 2.0)
            risk_reward_ratio_long: Risk/reward ratio for LONG trades (default: 2.0)
            risk_reward_ratio_short: Risk/reward ratio for SHORT trades (default: 2.0)
            momentum_atr_threshold: Minimum momentum as ATR multiple (default: 0.5)
            enable_momentum_filter: Enable/disable momentum filter (default: True)
            cooldown_hours: Hours between trades (default: 24)
        """
        self.atr_multiplier_stop = atr_multiplier_stop
        self.risk_reward_ratio_long = risk_reward_ratio_long
        self.risk_reward_ratio_short = risk_reward_ratio_short
        self.momentum_atr_threshold = momentum_atr_threshold
        self.enable_momentum_filter = enable_momentum_filter
        self.cooldown_hours = cooldown_hours
        self.logger = logging.getLogger(__name__)
        self.last_trade_time = None
        
        # Bar-close guard for FOMO protection
        self.bar_close_guard = BarCloseGuard(
            min_pips_movement=0.5,  # 0.5 pips minimum movement
            anti_fomo_bars=1  # Wait 1 bar after signal
        )
        
        # Multi-level TP engine for dynamic exit management
        self.multi_level_tp = MultiLevelTPEngine(
            default_rr_long=risk_reward_ratio_long,
            default_rr_short=risk_reward_ratio_short
        )
        
        # TP1 exit decision engine for post-TP1 management
        self.tp1_exit_decision = TP1ExitDecisionEngine(logger=self.logger)
        
        # TP2 exit decision engine for post-TP2 management
        self.tp2_exit_decision = TP2ExitDecisionEngine(logger=self.logger)
    
    def check_momentum_condition(self, current_bar: pd.Series) -> bool:
        """
        Check if breakout candle has sufficient momentum.
        
        Momentum filter: The breakout candle should show strong movement.
        Measured as: candle_size >= ATR * threshold
        
        Args:
            current_bar: Current bar data with close, open, atr14
            
        Returns:
            True if momentum sufficient, False otherwise
        """
        try:
            candle_size = abs(current_bar['close'] - current_bar['open'])
            min_momentum = current_bar['atr14'] * self.momentum_atr_threshold
            
            has_momentum = candle_size >= min_momentum
            
            if not has_momentum:
                self.logger.debug(f"Momentum check failed: {candle_size:.2f} < {min_momentum:.2f}")
            
            return has_momentum
            
        except Exception as e:
            self.logger.error(f"Error checking momentum: {e}")
            return False
    
    def check_trend_condition(self, current_bar: pd.Series) -> bool:
        """
        Check if price is above EMA50 (bullish trend).
        
        Args:
            current_bar: Current bar data with close, ema50
            
        Returns:
            True if close > EMA50, False otherwise
        """
        try:
            above_ema50 = current_bar['close'] > current_bar['ema50']
            
            if not above_ema50:
                self.logger.debug(f"Trend check failed: Close {current_bar['close']:.2f} "
                                f"not above EMA50 {current_bar['ema50']:.2f}")
            
            return above_ema50
            
        except Exception as e:
            self.logger.error(f"Error checking trend: {e}")
            return False
    
    def check_cooldown(self, current_time: datetime) -> bool:
        """
        Check if cooldown period has passed since last trade.
        
        Args:
            current_time: Current datetime
            
        Returns:
            True if cooldown respected, False if still in cooldown
        """
        if self.last_trade_time is None:
            return True
        
        time_since_last_trade = current_time - self.last_trade_time
        cooldown_delta = timedelta(hours=self.cooldown_hours)
        
        if time_since_last_trade < cooldown_delta:
            remaining = cooldown_delta - time_since_last_trade
            self.logger.debug(f"Cooldown active: {remaining} remaining")
            return False
        
        return True
    
    def calculate_stop_loss(self, entry_price: float, atr: float, 
                           pattern: Optional[dict] = None) -> float:
        """
        Calculate stop loss level.
        
        Two methods:
        1. ATR-based: entry - (ATR × multiplier)
        2. Swing-based: below the right low of the pattern
        
        Use the lower of the two (more conservative).
        
        Args:
            entry_price: Entry price
            atr: Current ATR value
            pattern: Double Bottom pattern (optional)
            
        Returns:
            Stop loss price
        """
        try:
            # ATR-based stop loss
            atr_stop = entry_price - (atr * self.atr_multiplier_stop)
            
            # Swing-based stop loss (if pattern available)
            if pattern and pattern.get('pattern_valid'):
                right_low = pattern['right_low']['price']
                # Place stop slightly below the right low
                swing_stop = right_low - (atr * 0.2)  # Small buffer
                
                # Use the lower (more conservative) stop
                stop_loss = min(atr_stop, swing_stop)
                self.logger.debug(f"Stop loss: ATR={atr_stop:.2f}, Swing={swing_stop:.2f}, "
                                f"Using={stop_loss:.2f}")
            else:
                stop_loss = atr_stop
                self.logger.debug(f"Stop loss: ATR-based={stop_loss:.2f}")
            
            return stop_loss
            
        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {e}")
            return entry_price - (atr * self.atr_multiplier_stop)  # Fallback
    
    def calculate_take_profit(self, entry_price: float, stop_loss: float, direction: str = "LONG") -> float:
        """
        Calculate take profit level based on risk/reward ratio.
        
        TP = Entry + (Entry - SL) × RR (for LONG)
        TP = Entry - (SL - Entry) × RR (for SHORT)
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: Trade direction "LONG" or "SHORT" (default: "LONG")
            
        Returns:
            Take profit price
        """
        rr_ratio = self.risk_reward_ratio_long if direction == "LONG" else self.risk_reward_ratio_short
        
        if direction == "LONG":
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * rr_ratio)
        else:  # SHORT
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * rr_ratio)
        
        self.logger.debug(f"Take profit: Entry={entry_price:.2f}, SL={stop_loss:.2f}, "
                        f"TP={take_profit:.2f} (RR={rr_ratio}, Direction={direction})")
        
        return take_profit
    
    def evaluate_entry(self, df: pd.DataFrame, pattern: Optional[dict],
                       current_bar_index: int = -2) -> Tuple[bool, dict]:
        """
        Evaluate all entry conditions for a LONG trade.
        
        Entry checklist:
        1. Bar state valid (bar-close guard)
        2. Valid Double Bottom pattern exists
        3. Close broke above neckline
        4. Close > EMA50 (trend filter)
        5. Breakout candle has momentum (ATR-based)
        6. Anti-FOMO cooldown respected
        7. Cooldown period respected
        
        All decisions use only FULLY CLOSED bars.
        
        Args:
            df: DataFrame with OHLC and indicator data
            pattern: Detected Double Bottom pattern (or None)
            current_bar_index: Index of bar to evaluate (default: -2, latest completed)
            
        Returns:
            Tuple of (should_enter: bool, entry_details: dict)
        """
        try:
            entry_details = {
                'pattern_valid': False,
                'breakout_confirmed': False,
                'above_ema50': False,
                'has_momentum': False,
                'cooldown_ok': False,
                'should_enter': False,
                'entry_price': None,
                'stop_loss': None,
                'take_profit': None,
                'reason': '',
                'failure_code': None  # Structured failure codes per spec
            }
            
            # 0. Bar-close guard: Validate bar state
            is_valid, guard_reason = self.bar_close_guard.validate_bar_state(df, current_bar_index)
            if not is_valid:
                entry_details['reason'] = f"Bar state invalid: {guard_reason}"
                entry_details['failure_code'] = "BAR_NOT_CLOSED"
                self.logger.debug(entry_details['reason'])
                return False, entry_details
            
            current_bar = df.iloc[current_bar_index]
            
            # 1. Check pattern validity
            if pattern is None or not pattern.get('pattern_valid'):
                entry_details['reason'] = "No valid Double Bottom pattern"
                entry_details['failure_code'] = "INVALID_PATTERN_STRUCTURE"
                return False, entry_details
            entry_details['pattern_valid'] = True
            
            # 2. Check breakout above neckline
            neckline = pattern['neckline']['price']
            if current_bar['close'] <= neckline:
                entry_details['reason'] = f"No breakout: Close {current_bar['close']:.2f} <= Neckline {neckline:.2f}"
                entry_details['failure_code'] = "NO_NECKLINE_BREAK"
                return False, entry_details
            entry_details['breakout_confirmed'] = True
            
            # 3. Check trend (close > EMA50)
            if not self.check_trend_condition(current_bar):
                entry_details['reason'] = "Trend check failed: Close not above EMA50"
                entry_details['failure_code'] = "CONTEXT_NOT_ALIGNED"
                return False, entry_details
            entry_details['above_ema50'] = True
            
            # 4. Check momentum (if enabled)
            if self.enable_momentum_filter:
                if not self.check_momentum_condition(current_bar):
                    entry_details['reason'] = "Momentum check failed: Insufficient candle size"
                    entry_details['failure_code'] = "CONTEXT_NOT_ALIGNED"
                    return False, entry_details
                entry_details['has_momentum'] = True
            else:
                entry_details['has_momentum'] = True  # Skip momentum check
            
            # 5. Anti-FOMO: Check cooldown since last signal (OPTIONAL, non-blocking)
            can_enter_fomo, fomo_reason = self.bar_close_guard.check_anti_fomo_cooldown(current_bar_index)
            # NOTE: Anti-FOMO only warns, NEVER blocks entry
            if not can_enter_fomo:
                self.logger.warning(f"Anti-FOMO: {fomo_reason}")
            # Always proceed (anti-FOMO is only advisory)
            
            # 6. Check cooldown period between trades
            if not self.check_cooldown(current_bar['time']):
                entry_details['reason'] = "Cooldown period active"
                entry_details['failure_code'] = "COOLDOWN_ACTIVE"
                return False, entry_details
            entry_details['cooldown_ok'] = True
            
            # All conditions met - prepare entry
            entry_price = current_bar['close']  # Enter at close of breakout bar
            stop_loss = self.calculate_stop_loss(entry_price, current_bar['atr14'], pattern)
            take_profit = self.calculate_take_profit(entry_price, stop_loss, direction="LONG")
            
            entry_details.update({
                'should_enter': True,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': 'All entry conditions met',
                'atr': current_bar['atr14']
            })
            
            # Record signal for anti-FOMO tracking
            self.bar_close_guard.record_signal(current_bar_index)
            
            self.logger.info(
                f"ENTRY SIGNAL: Entry={entry_price:.2f}, SL={stop_loss:.2f}, TP={take_profit:.2f}"
            )
            
            return True, entry_details
            
        except Exception as e:
            self.logger.error(f"Error evaluating entry: {e}")
            return False, entry_details
    
    def evaluate_post_tp1_decision(self,
                                   current_price: float,
                                   entry_price: float,
                                   stop_loss: float,
                                   tp1_price: float,
                                   atr_14: float,
                                   market_regime: str,
                                   momentum_state: str,
                                   last_closed_bar: Dict,
                                   bars_since_tp1: int,
                                   previous_bar_close: Optional[float] = None,
                                   two_bars_ago_close: Optional[float] = None) -> Dict:
        """
        Evaluate TP1 exit decision after TP1 has been reached.
        
        Prevents premature exits on minor pullbacks while allowing exits on confirmed failures.
        
        Args:
            current_price: Current market price
            entry_price: Trade entry price
            stop_loss: Stop loss level
            tp1_price: TP1 level
            atr_14: Current ATR(14)
            market_regime: Market regime ("BULL", "RANGE", "BEAR")
            momentum_state: Momentum state ("STRONG", "MODERATE", "BROKEN")
            last_closed_bar: Last closed bar data {close, high, low, open, time}
            bars_since_tp1: Number of bars since TP1 was reached (0 = same bar)
            previous_bar_close: Previous bar close (for 2-bar confirmation)
            two_bars_ago_close: Two bars ago close (for extended checks)
        
        Returns:
            Dict with:
                - decision: PostTP1Decision enum value
                - should_exit: bool (True if decision is EXIT_TRADE)
                - reason: str (explanation)
                - new_stop_loss: Optional[float] (suggested SL if provided)
        """
        try:
            # Map string regimes to enum
            regime_map = {
                "BULL": MarketRegime.BULL,
                "RANGE": MarketRegime.RANGE,
                "BEAR": MarketRegime.BEAR,
            }
            regime = regime_map.get(market_regime, MarketRegime.UNKNOWN)
            
            # Map string momentum states to enum
            momentum_map = {
                "STRONG": MomentumState.STRONG,
                "MODERATE": MomentumState.MODERATE,
                "BROKEN": MomentumState.BROKEN,
            }
            momentum = momentum_map.get(momentum_state, MomentumState.UNKNOWN)
            
            # Create evaluation context
            ctx = TP1EvaluationContext(
                current_price=current_price,
                entry_price=entry_price,
                stop_loss=stop_loss,
                tp1_price=tp1_price,
                atr_14=atr_14,
                market_regime=regime,
                momentum_state=momentum,
                last_closed_bar=last_closed_bar,
                bars_since_tp1=bars_since_tp1,
                previous_bar_close=previous_bar_close,
                two_bars_ago_close=two_bars_ago_close
            )
            
            # Evaluate post-TP1 decision
            exit_reason = self.tp1_exit_decision.evaluate_post_tp1(ctx)
            
            # Prepare suggested SL (only suggest, don't force)
            new_stop_loss = None
            if exit_reason.decision == PostTP1Decision.HOLD:
                direction = 1 if entry_price < tp1_price else -1
                new_stop_loss = self.tp1_exit_decision.calculate_sl_after_tp1(
                    entry_price=entry_price,
                    tp1_price=tp1_price,
                    atr_14=atr_14,
                    direction=direction
                )
            
            return {
                'decision': exit_reason.decision.value,
                'should_exit': exit_reason.decision == PostTP1Decision.EXIT_TRADE,
                'reason': exit_reason.reason_text,
                'new_stop_loss': new_stop_loss
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluating post-TP1 decision: {e}")
            return {
                'decision': PostTP1Decision.HOLD.value,
                'should_exit': False,
                'reason': f'Error in TP1 evaluation: {e}',
                'new_stop_loss': None
            }
    
    def evaluate_post_tp2_decision(self,
                                   current_price: float,
                                   entry_price: float,
                                   stop_loss: float,
                                   tp2_price: float,
                                   tp3_price: float,
                                   tp1_price: float,
                                   atr_14: float,
                                   market_regime: str,
                                   momentum_state: str,
                                   structure_state: str,
                                   last_closed_bar: dict,
                                   bars_since_tp2: int,
                                   swing_low: Optional[float] = None,
                                   previous_bar_close: Optional[float] = None,
                                   two_bars_ago_close: Optional[float] = None) -> dict:
        """
        Evaluate TP2 exit decision after TP2 has been reached.
        
        Focuses on maximizing trend capture while protecting accumulated profits.
        
        Args:
            current_price: Current market price
            entry_price: Trade entry price
            stop_loss: Stop loss level
            tp2_price: TP2 level
            tp3_price: TP3 level (final target)
            tp1_price: TP1 level (for reference)
            atr_14: Current ATR(14)
            market_regime: Market regime ("BULL", "RANGE", "BEAR")
            momentum_state: Momentum state ("STRONG", "MODERATE", "BROKEN")
            structure_state: Structure state ("HIGHER_LOWS", "LOWER_LOW")
            last_closed_bar: Last closed bar data {close, high, low, open, time}
            bars_since_tp2: Number of bars since TP2 was reached
            swing_low: Most recent swing low (for trailing SL)
            previous_bar_close: Previous bar close (for 2-bar confirmation)
            two_bars_ago_close: Two bars ago close
        
        Returns:
            Dict with:
                - decision: PostTP2Decision enum value
                - should_exit: bool
                - reason: str
                - trailing_sl: Optional[float]
        """
        try:
            # Map string inputs to enums
            regime_map = {
                "BULL": MarketRegime.BULL,
                "RANGE": MarketRegime.RANGE,
                "BEAR": MarketRegime.BEAR,
            }
            regime = regime_map.get(market_regime, MarketRegime.UNKNOWN)
            
            momentum_map = {
                "STRONG": MomentumState.STRONG,
                "MODERATE": MomentumState.MODERATE,
                "BROKEN": MomentumState.BROKEN,
            }
            momentum = momentum_map.get(momentum_state, MomentumState.UNKNOWN)
            
            structure_map = {
                "HIGHER_LOWS": StructureState.HIGHER_LOWS,
                "LOWER_LOW": StructureState.LOWER_LOW,
            }
            structure = structure_map.get(structure_state, StructureState.UNKNOWN)
            
            # Create evaluation context
            ctx = TP2EvaluationContext(
                current_price=current_price,
                entry_price=entry_price,
                stop_loss=stop_loss,
                tp2_price=tp2_price,
                tp3_price=tp3_price,
                tp1_price=tp1_price,
                atr_14=atr_14,
                market_regime=regime,
                momentum_state=momentum,
                structure_state=structure,
                last_closed_bar=last_closed_bar,
                bars_since_tp2=bars_since_tp2,
                previous_bar_close=previous_bar_close,
                two_bars_ago_close=two_bars_ago_close
            )
            
            # Evaluate post-TP2 decision
            exit_reason = self.tp2_exit_decision.evaluate_post_tp2(ctx)
            
            # Calculate trailing SL if suggested
            trailing_sl = None
            if exit_reason.should_trail_sl:
                direction = 1 if entry_price < tp2_price else -1
                trailing_sl = self.tp2_exit_decision.calculate_trailing_sl_after_tp2(
                    entry_price=entry_price,
                    tp2_price=tp2_price,
                    current_price=current_price,
                    atr_14=atr_14,
                    swing_low=swing_low,
                    direction=direction
                )
            
            return {
                'decision': exit_reason.decision.value,
                'should_exit': exit_reason.decision == PostTP2DecisionEnum.EXIT_TRADE,
                'reason': exit_reason.reason_text,
                'trailing_sl': trailing_sl
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluating post-TP2 decision: {e}")
            return {
                'decision': PostTP2DecisionEnum.HOLD.value,
                'should_exit': False,
                'reason': f'Error in TP2 evaluation: {e}',
                'trailing_sl': None
            }
    
    def evaluate_exit(self, current_price: float, entry_price: float,
                     stop_loss: float, take_profit: float,
                     tp_state: Optional[str] = None,
                     tp_levels: Optional[Dict[str, float]] = None,
                     direction: int = 1,
                     tp_transition_time: Optional[datetime] = None,
                     atr_14: Optional[float] = None,
                     market_regime: Optional[str] = None,
                     momentum_state: Optional[str] = None,
                     last_closed_bar: Optional[dict] = None) -> Tuple[bool, str, Optional[str], Optional[float]]:
        """
        Evaluate if position should be exited.
        
        Supports both simple exits (stop_loss + single take_profit) and
        multi-level TP exits (with dynamic SL management).
        
        Exit conditions:
        - Stop loss hit
        - Multi-level TP progression (if tp_state and tp_levels provided)
        - Single TP hit (if tp_state not provided)
        
        Args:
            current_price: Current market price
            entry_price: Position entry price
            stop_loss: Stop loss level
            take_profit: Take profit level (single level, for backward compatibility)
            tp_state: Current TP state (IN_TRADE, TP1_REACHED, TP2_REACHED)
            tp_levels: Dict with 'tp1', 'tp2', 'tp3' prices
            direction: +1 for LONG, -1 for SHORT
            
        Returns:
            Tuple of (should_exit: bool, reason: str, new_tp_state: Optional[str], new_stop_loss: Optional[float])
        """
        try:
            new_tp_state = tp_state
            new_stop_loss = None
            
            # Multi-level TP evaluation (if enabled)
            if tp_state and tp_levels:
                should_exit, reason, new_tp_state = self.multi_level_tp.evaluate_exit(
                    current_price=current_price,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    tp_state=tp_state,
                    tp_levels=tp_levels,
                    direction=direction,
                    bar_close_confirmed=True
                )

                # TP1/TP2 post-decision enforcement per spec
                if not should_exit and new_tp_state == tp_state:
                    # Compute bars since TP state change (bar-close guard)
                    bars_since_tp = 1
                    if tp_transition_time is not None and last_closed_bar and 'time' in last_closed_bar:
                        bars_since_tp = 0 if last_closed_bar['time'] == tp_transition_time else 1

                    # Defaults
                    regime = market_regime or "BULL"
                    momentum = momentum_state or "STRONG"
                    atr_val = atr_14 or tp_levels.get('risk', 0) or 0.0

                    if tp_state == TPState.TP1_REACHED.value:
                        ctx = TP1EvaluationContext(
                            current_price=current_price,
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            tp1_price=tp_levels.get('tp1', take_profit),
                            atr_14=atr_val,
                            market_regime=MarketRegime.BULL if regime == "BULL" else MarketRegime.RANGE if regime == "RANGE" else MarketRegime.BEAR,
                            momentum_state=MomentumState.STRONG if momentum == "STRONG" else MomentumState.MODERATE if momentum == "MODERATE" else MomentumState.BROKEN,
                            last_closed_bar=last_closed_bar or {'close': current_price},
                            bars_since_tp1=bars_since_tp,
                            previous_bar_close=None,
                            two_bars_ago_close=None
                        )
                        post = self.tp1_exit_decision.evaluate_post_tp1(ctx)
                        if post.decision == PostTP1Decision.EXIT_TRADE:
                            return True, post.reason_text, TPState.EXITED.value, None
                        if post.decision == PostTP1Decision.WAIT_NEXT_BAR:
                            self.logger.debug(f"TP1: WAIT_NEXT_BAR - {post.reason_text}")
                            return False, post.reason_text, tp_state, None
                        # HOLD decision (SILENT_NO_TRADE mitigation: explicit reason logged)
                        self.logger.debug(f"TP1: HOLD - {post.reason_text}")
                        return False, post.reason_text, tp_state, None

                    if tp_state == TPState.TP2_REACHED.value:
                        ctx = TP2EvaluationContext(
                            current_price=current_price,
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            tp2_price=tp_levels.get('tp2', take_profit),
                            tp3_price=tp_levels.get('tp3', take_profit),
                            tp1_price=tp_levels.get('tp1', entry_price),
                            atr_14=atr_val,
                            market_regime=MarketRegime.BULL if regime == "BULL" else MarketRegime.RANGE if regime == "RANGE" else MarketRegime.BEAR,
                            momentum_state=MomentumState.STRONG if momentum == "STRONG" else MomentumState.MODERATE if momentum == "MODERATE" else MomentumState.BROKEN,
                            structure_state=StructureState.HIGHER_LOWS,
                            last_closed_bar=last_closed_bar or {'close': current_price},
                            bars_since_tp2=bars_since_tp,
                            previous_bar_close=None,
                            two_bars_ago_close=None
                        )
                        post = self.tp2_exit_decision.evaluate_post_tp2(ctx)
                        if post.decision == PostTP2DecisionEnum.EXIT_TRADE:
                            return True, post.reason_text, TPState.EXITED.value, None
                        if post.decision == PostTP2DecisionEnum.WAIT_NEXT_BAR:
                            self.logger.debug(f"TP2: WAIT_NEXT_BAR - {post.reason_text}")
                            return False, post.reason_text, tp_state, None
                        # HOLD decision (SILENT_NO_TRADE mitigation: explicit reason logged)
                        self.logger.debug(f"TP2: HOLD - {post.reason_text}")
                        return False, post.reason_text, tp_state, None
                
                # Calculate new stop loss if TP state changed
                if new_tp_state != tp_state and new_tp_state in [TPState.TP1_REACHED.value, TPState.TP2_REACHED.value]:
                    new_stop_loss = self.multi_level_tp.calculate_new_stop_loss(
                        current_price=current_price,
                        entry_price=entry_price,
                        tp_state=new_tp_state,
                        direction=direction,
                        trailing_offset=0.5  # Configurable trailing offset
                    )
                
                return should_exit, reason, new_tp_state, new_stop_loss
            
            # Fallback to simple exit logic (backward compatibility)
            if direction == 1:  # LONG
                # Check stop loss
                if current_price <= stop_loss:
                    self.logger.info(f"STOP LOSS HIT: {current_price:.2f} <= {stop_loss:.2f}")
                    return True, "Stop Loss", new_tp_state, new_stop_loss
                
                # Check take profit
                if current_price >= take_profit:
                    self.logger.info(f"TAKE PROFIT HIT: {current_price:.2f} >= {take_profit:.2f}")
                    return True, "Take Profit", new_tp_state, new_stop_loss
            
            else:  # SHORT
                # Check stop loss
                if current_price >= stop_loss:
                    self.logger.info(f"STOP LOSS HIT: {current_price:.2f} >= {stop_loss:.2f}")
                    return True, "Stop Loss", new_tp_state, new_stop_loss
                
                # Check take profit
                if current_price <= take_profit:
                    self.logger.info(f"TAKE PROFIT HIT: {current_price:.2f} <= {take_profit:.2f}")
                    return True, "Take Profit", new_tp_state, new_stop_loss
            
            # Position open (SILENT_NO_TRADE mitigation: explicit reason logged with regime context)
            regime_context = f" [{market_regime}]" if market_regime else ""
            reason = f"Position open{regime_context}"
            self.logger.debug(f"NO_EXIT: {reason}")
            return False, reason, new_tp_state, new_stop_loss
            
        except Exception as e:
            self.logger.error(f"Error evaluating exit: {e}")
            return False, "Error", new_tp_state, None
    
    def update_last_trade_time(self, trade_time: datetime):
        """Update the timestamp of the last trade for cooldown tracking."""
        self.last_trade_time = trade_time
        self.logger.debug(f"Last trade time updated: {trade_time}")


if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.DEBUG)
    
    # Create sample data
    dates = pd.date_range(start='2024-01-01', periods=50, freq='H')
    df = pd.DataFrame({
        'time': dates,
        'open': [2000] * 50,
        'high': [2010] * 50,
        'low': [1990] * 50,
        'close': [2005] * 50,
        'ema50': [2000] * 50,
        'ema200': [1980] * 50,
        'atr14': [15] * 50,
    })
    
    # Simulate breakout bar
    df.loc[df.index[-2], 'close'] = 2030
    df.loc[df.index[-2], 'high'] = 2035
    
    # Mock pattern
    pattern = {
        'pattern_valid': True,
        'left_low': {'price': 1990, 'index': 10},
        'neckline': {'price': 2010, 'index': 25},
        'right_low': {'price': 1992, 'index': 40}
    }
    
    engine = StrategyEngine()
    should_enter, details = engine.evaluate_entry(df, pattern)
    
    print(f"Should enter: {should_enter}")
    print(f"Details: {details}")

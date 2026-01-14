"""
TP1 Exit Decision Engine

Intelligent decision engine that determines whether to EXIT or HOLD
after TP1 has been reached, preventing premature exits due to minor pullbacks.

Scope: EXIT_DECISION_ONLY (does not affect entry logic)

Decision States:
- HOLD: Price still above TP1 or minor pullback; continue holding
- WAIT_NEXT_BAR: Single-bar pullback below TP1; wait for confirmation
- EXIT_TRADE: Confirmed failure (2 bars below TP1, deep retrace, momentum break, regime flip)
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class PostTP1Decision(Enum):
    """Possible decisions after TP1 is reached"""
    NOT_REACHED = "NOT_REACHED"
    HOLD = "HOLD"
    WAIT_NEXT_BAR = "WAIT_NEXT_BAR"
    EXIT_TRADE = "EXIT_TRADE"


class MomentumState(Enum):
    """Current momentum state"""
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    BROKEN = "BROKEN"
    UNKNOWN = "UNKNOWN"


class MarketRegime(Enum):
    """Current market regime"""
    BULL = "BULL"
    RANGE = "RANGE"
    BEAR = "BEAR"
    UNKNOWN = "UNKNOWN"


@dataclass
class TP1EvaluationContext:
    """Context for TP1 decision evaluation"""
    current_price: float
    entry_price: float
    stop_loss: float
    tp1_price: float
    atr_14: float
    market_regime: MarketRegime
    momentum_state: MomentumState
    last_closed_bar: dict  # {close, high, low, open, time}
    bars_since_tp1: int  # Number of bars after TP1 was reached (0 = same bar)
    previous_bar_close: Optional[float] = None  # Previous bar close price
    two_bars_ago_close: Optional[float] = None  # Two bars ago close price


@dataclass
class TP1ExitReason:
    """Reason for TP1 exit decision"""
    decision: PostTP1Decision
    reason_text: str
    should_move_sl: bool = False  # Should SL be adjusted?
    suggested_sl: Optional[float] = None  # Suggested new SL value


class TP1ExitDecisionEngine:
    """
    Evaluates whether a trade should exit after TP1 is reached.
    
    Prevents premature exits from minor pullbacks while exiting on confirmed failure.
    """

    def __init__(self, logger=None):
        self.logger = logger

    def evaluate_post_tp1(self, ctx: TP1EvaluationContext) -> TP1ExitReason:
        """
        Evaluate post-TP1 decision given the current context.
        
        Returns TP1ExitReason with decision and reason.
        
        Decision priority (highest to lowest):
        1. Exit conditions (momentum broken, regime flip, deep retrace, 2-bar confirmation)
        2. Wait conditions (single-bar pullback, momentum still valid)
        3. Hold conditions (micro-pullback, above TP1 on close, bullish regime)
        """
        
        # Same bar as TP1 reached: always HOLD
        if ctx.bars_since_tp1 == 0:
            return TP1ExitReason(
                decision=PostTP1Decision.HOLD,
                reason_text="No exit on same bar as TP1 (anti-premature-exit guard)",
                should_move_sl=False
            )

        # ========================================
        # RULE GROUP 3: EXIT CONDITIONS (checked FIRST)
        # ========================================
        
        # Rule 1: Two consecutive bars below TP1
        if (ctx.previous_bar_close is not None and 
            ctx.previous_bar_close < ctx.tp1_price and 
            ctx.last_closed_bar['close'] < ctx.tp1_price):
            return TP1ExitReason(
                decision=PostTP1Decision.EXIT_TRADE,
                reason_text=f"TP1 failure confirmed: 2 consecutive bars below {ctx.tp1_price:.2f}",
                should_move_sl=False
            )

        # Rule 2: Momentum broken (takes precedence over price position)
        if ctx.momentum_state == MomentumState.BROKEN:
            return TP1ExitReason(
                decision=PostTP1Decision.EXIT_TRADE,
                reason_text="Momentum broken after TP1; exiting",
                should_move_sl=False
            )

        # Rule 3: Regime flip (from BULL to RANGE/BEAR)
        if ctx.market_regime in (MarketRegime.RANGE, MarketRegime.BEAR):
            return TP1ExitReason(
                decision=PostTP1Decision.EXIT_TRADE,
                reason_text=f"Regime no longer supportive: {ctx.market_regime.value}",
                should_move_sl=False
            )

        # Rule 4: Deep retracement (>= 0.5*ATR)
        price_retrace_distance = ctx.tp1_price - ctx.current_price
        if price_retrace_distance >= 0.5 * ctx.atr_14:
            return TP1ExitReason(
                decision=PostTP1Decision.EXIT_TRADE,
                reason_text=f"Deep retracement: {price_retrace_distance:.2f} >= 0.5*ATR {0.5*ctx.atr_14:.2f}",
                should_move_sl=False
            )

        # ========================================
        # RULE GROUP 1: NO EXIT ZONE (HOLD)
        # ========================================
        
        # Rule 1: Micro-pullback allowed
        if price_retrace_distance <= 0.25 * ctx.atr_14:
            return TP1ExitReason(
                decision=PostTP1Decision.HOLD,
                reason_text=f"Micro-pullback ({price_retrace_distance:.2f} <= 0.25*ATR {0.25*ctx.atr_14:.2f}); holding for continuation",
                should_move_sl=False
            )

        # Rule 2: Above TP1 on bar close
        if ctx.last_closed_bar['close'] >= ctx.tp1_price:
            return TP1ExitReason(
                decision=PostTP1Decision.HOLD,
                reason_text=f"Bar close {ctx.last_closed_bar['close']:.2f} >= TP1 {ctx.tp1_price:.2f}; holding",
                should_move_sl=False
            )

        # Rule 3: Bullish context persists
        if ctx.market_regime == MarketRegime.BULL:
            return TP1ExitReason(
                decision=PostTP1Decision.HOLD,
                reason_text="Bullish regime still active; holding for continuation",
                should_move_sl=False
            )

        # ========================================
        # RULE GROUP 2: WAIT STATE
        # ========================================
        
        # Rule 1: Single-bar pullback (below TP1 but above entry on current bar)
        if ctx.last_closed_bar['close'] < ctx.tp1_price and ctx.last_closed_bar['close'] >= ctx.entry_price:
            # Only on the first pullback bar
            if ctx.bars_since_tp1 == 1:
                return TP1ExitReason(
                    decision=PostTP1Decision.WAIT_NEXT_BAR,
                    reason_text=f"Single-bar pullback to {ctx.last_closed_bar['close']:.2f} (> entry {ctx.entry_price:.2f}); waiting for confirmation",
                    should_move_sl=False
                )

        # Rule 2: Momentum not broken
        if ctx.momentum_state in (MomentumState.STRONG, MomentumState.MODERATE):
            # Only if we haven't already exited for other reasons
            if ctx.last_closed_bar['close'] < ctx.tp1_price:
                return TP1ExitReason(
                    decision=PostTP1Decision.WAIT_NEXT_BAR,
                    reason_text=f"Momentum {ctx.momentum_state.value} still active; waiting for confirmation",
                    should_move_sl=False
                )

        # Default: HOLD if no exit condition met
        return TP1ExitReason(
            decision=PostTP1Decision.HOLD,
            reason_text="TP1 reached; holding per default logic",
            should_move_sl=False
        )

    def calculate_sl_after_tp1(self, 
                               entry_price: float, 
                               tp1_price: float, 
                               atr_14: float,
                               direction: int = 1) -> float:
        """
        Calculate suggested SL after TP1 is reached.
        
        Default behavior: SL should not move to exact breakeven.
        Minimum offset: 0.2 * ATR (favorable direction).
        
        Args:
            entry_price: Trade entry price
            tp1_price: TP1 level
            atr_14: Current ATR(14)
            direction: 1 for LONG, -1 for SHORT
        
        Returns:
            Suggested new SL price
        """
        min_offset = 0.2 * atr_14
        
        if direction == 1:  # LONG
            # SL should be above entry price (not at breakeven)
            suggested_sl = entry_price + min_offset
        else:  # SHORT
            # SL should be below entry price (not at breakeven)
            suggested_sl = entry_price - min_offset
        
        return suggested_sl

    def should_update_sl_on_bar_close(self) -> bool:
        """
        SL updates after TP1 should only occur on bar close, not intrabar.
        Always return True (caller must ensure bar-close context).
        """
        return True

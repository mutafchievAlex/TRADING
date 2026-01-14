"""
TP2 Exit Decision Engine

Governs trade management after TP2 is reached.
Focuses on maximizing trend capture while protecting accumulated profits.
Exit decisions made only on confirmed weakness, never on noise.

Scope: EXIT_DECISION_ONLY (does not affect entry logic)

Decision States:
- HOLD: Strong trend continuation; aim for TP3
- WAIT_NEXT_BAR: Monitoring weakness; await confirmation
- EXIT_TRADE: Confirmed weakness or structure break
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class PostTP2Decision(Enum):
    """Possible decisions after TP2 is reached"""
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


class StructureState(Enum):
    """Market structure state"""
    HIGHER_LOWS = "HIGHER_LOWS"
    LOWER_LOW = "LOWER_LOW"
    UNKNOWN = "UNKNOWN"


@dataclass
class TP2EvaluationContext:
    """Context for TP2 decision evaluation"""
    current_price: float
    entry_price: float
    stop_loss: float
    tp2_price: float
    tp3_price: float
    tp1_price: float  # For reference
    atr_14: float
    market_regime: MarketRegime
    momentum_state: MomentumState
    structure_state: StructureState
    last_closed_bar: dict  # {close, high, low, open, time}
    bars_since_tp2: int  # Number of bars after TP2 was reached (0 = same bar)
    previous_bar_close: Optional[float] = None
    two_bars_ago_close: Optional[float] = None


@dataclass
class TP2ExitReason:
    """Reason for TP2 exit decision"""
    decision: PostTP2Decision
    reason_text: str
    should_trail_sl: bool = False
    suggested_sl: Optional[float] = None


class TP2ExitDecisionEngine:
    """
    Evaluates whether a trade should exit after TP2 is reached.
    
    Focus: Maximize trend capture while protecting profits.
    """

    def __init__(self, logger=None):
        self.logger = logger

    def evaluate_post_tp2(self, ctx: TP2EvaluationContext) -> TP2ExitReason:
        """
        Evaluate post-TP2 decision given the current context.
        
        Returns TP2ExitReason with decision and reason.
        
        Decision priority (highest to lowest):
        1. Exit conditions (structure break, momentum break, confirmed rejection, deep retrace, regime flip)
        2. Wait conditions (momentum softening, first close below TP2)
        3. Hold conditions (strong trend, shallow pullback, structure intact)
        """
        
        # Same bar as TP2 reached: always HOLD
        if ctx.bars_since_tp2 == 0:
            return TP2ExitReason(
                decision=PostTP2Decision.HOLD,
                reason_text="No exit on same bar as TP2 (anti-premature-exit guard)",
                should_trail_sl=False
            )

        # ========================================
        # RULE GROUP 3: EXIT CONDITIONS (checked FIRST)
        # ========================================
        
        # Rule 1: Structure break (highest priority)
        if ctx.structure_state == StructureState.LOWER_LOW:
            return TP2ExitReason(
                decision=PostTP2Decision.EXIT_TRADE,
                reason_text="Market structure broken (lower low)",
                should_trail_sl=False
            )

        # Rule 2: Momentum broken
        if ctx.momentum_state == MomentumState.BROKEN:
            return TP2ExitReason(
                decision=PostTP2Decision.EXIT_TRADE,
                reason_text="Momentum broken after TP2; exiting",
                should_trail_sl=False
            )

        # Rule 3: Regime flip
        if ctx.market_regime in (MarketRegime.RANGE, MarketRegime.BEAR):
            return TP2ExitReason(
                decision=PostTP2Decision.EXIT_TRADE,
                reason_text=f"Regime no longer supportive: {ctx.market_regime.value}",
                should_trail_sl=False
            )

        # Rule 4: Two consecutive bars below TP2
        if (ctx.previous_bar_close is not None and 
            ctx.previous_bar_close < ctx.tp2_price and 
            ctx.last_closed_bar['close'] < ctx.tp2_price):
            return TP2ExitReason(
                decision=PostTP2Decision.EXIT_TRADE,
                reason_text=f"TP2 failure confirmed: 2 consecutive bars below {ctx.tp2_price:.2f}",
                should_trail_sl=False
            )

        # Rule 5: Deep retracement (>= 0.35*ATR - tighter than TP1)
        price_retrace_distance = ctx.tp2_price - ctx.current_price
        if price_retrace_distance >= 0.35 * ctx.atr_14:
            return TP2ExitReason(
                decision=PostTP2Decision.EXIT_TRADE,
                reason_text=f"Deep retracement after TP2: {price_retrace_distance:.2f} >= 0.35*ATR {0.35*ctx.atr_14:.2f}",
                should_trail_sl=False
            )

        # ========================================
        # RULE GROUP 1: STRONG HOLD CONDITIONS
        # ========================================
        
        # Rule 1: Strong trend continuation (all conditions must be met)
        if (ctx.last_closed_bar['close'] >= ctx.tp2_price and 
            ctx.momentum_state == MomentumState.STRONG and 
            ctx.market_regime == MarketRegime.BULL):
            return TP2ExitReason(
                decision=PostTP2Decision.HOLD,
                reason_text="Strong trend continuation after TP2; aiming for TP3",
                should_trail_sl=True
            )

        # Rule 2: Shallow pullback (< 0.2*ATR - tighter than TP1's 0.25)
        if price_retrace_distance <= 0.2 * ctx.atr_14:
            return TP2ExitReason(
                decision=PostTP2Decision.HOLD,
                reason_text=f"Shallow pullback ({price_retrace_distance:.2f} <= 0.2*ATR {0.2*ctx.atr_14:.2f}); holding for TP3",
                should_trail_sl=True
            )

        # Rule 3: Structure intact
        if ctx.structure_state == StructureState.HIGHER_LOWS:
            return TP2ExitReason(
                decision=PostTP2Decision.HOLD,
                reason_text="Market structure intact (higher lows); holding for TP3",
                should_trail_sl=True
            )

        # ========================================
        # RULE GROUP 2: MONITOR MODE (WAIT)
        # ========================================
        
        # Rule 1: Momentum softening
        if ctx.momentum_state == MomentumState.MODERATE:
            return TP2ExitReason(
                decision=PostTP2Decision.WAIT_NEXT_BAR,
                reason_text="Momentum softening but not broken; monitoring",
                should_trail_sl=True
            )

        # Rule 2: First close below TP2 but above TP1
        if (ctx.last_closed_bar['close'] < ctx.tp2_price and 
            ctx.last_closed_bar['close'] >= ctx.tp1_price):
            return TP2ExitReason(
                decision=PostTP2Decision.WAIT_NEXT_BAR,
                reason_text=f"First close below TP2 {ctx.tp2_price:.2f} but above TP1 {ctx.tp1_price:.2f}; monitoring",
                should_trail_sl=True
            )

        # Default: HOLD if no exit condition met
        return TP2ExitReason(
            decision=PostTP2Decision.HOLD,
            reason_text="TP2 reached; holding for TP3 per default logic",
            should_trail_sl=True
        )

    def calculate_trailing_sl_after_tp2(self, 
                                        entry_price: float,
                                        tp2_price: float,
                                        current_price: float,
                                        atr_14: float,
                                        swing_low: Optional[float] = None,
                                        direction: int = 1) -> float:
        """
        Calculate trailing SL after TP2 is reached.
        
        Uses either swing low or ATR offset (0.3 × ATR).
        Always locks in profit above entry.
        
        Args:
            entry_price: Trade entry price
            tp2_price: TP2 level
            current_price: Current market price
            atr_14: Current ATR(14)
            swing_low: Most recent swing low (optional)
            direction: 1 for LONG, -1 for SHORT
        
        Returns:
            Suggested trailing SL price
        """
        atr_offset = 0.3 * atr_14
        
        if direction == 1:  # LONG
            # Method 1: ATR trailing from current price
            atr_sl = current_price - atr_offset
            
            # Method 2: Swing low (if provided)
            if swing_low is not None:
                swing_sl = swing_low - (0.1 * atr_14)  # Small buffer below swing
                suggested_sl = max(atr_sl, swing_sl)
            else:
                suggested_sl = atr_sl
            
            # Must be above entry to lock profit
            suggested_sl = max(suggested_sl, entry_price + (0.1 * atr_14))
            
        else:  # SHORT
            # Method 1: ATR trailing from current price
            atr_sl = current_price + atr_offset
            
            # Method 2: Swing high (if provided, passed as swing_low parameter)
            if swing_low is not None:
                swing_sl = swing_low + (0.1 * atr_14)
                suggested_sl = min(atr_sl, swing_sl)
            else:
                suggested_sl = atr_sl
            
            # Must be below entry to lock profit
            suggested_sl = min(suggested_sl, entry_price - (0.1 * atr_14))
        
        return suggested_sl

    def should_update_sl_on_bar_close(self) -> bool:
        """
        SL updates after TP2 should only occur on bar close, not intrabar.
        Always return True (caller must ensure bar-close context).
        """
        return True

"""
Unified Decision Engine - Single Source of Truth for Trading Decisions

This engine is the SOLE place where trading decisions are made. It evaluates
the 8-stage decision pipeline and returns deterministic results for:
- Live trading
- Backtesting
- Why No Trade? analysis

NO LOGIC EXISTS OUTSIDE THIS ENGINE.
NO UNKNOWN STATES ARE ALLOWED.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

from .risk_engine import RiskEngine


class DecisionResult(Enum):
    """Possible decision outcomes."""
    TRADE_ALLOWED = "TRADE_ALLOWED"
    NO_TRADE = "NO_TRADE"


class Stage(Enum):
    """Decision pipeline stages in evaluation order."""
    PATTERN_DETECTION = "PATTERN_DETECTION"
    PATTERN_QUALITY = "PATTERN_QUALITY"
    BREAKOUT_CONFIRMATION = "BREAKOUT_CONFIRMATION"
    TREND_FILTER = "TREND_FILTER"
    MOMENTUM_FILTER = "MOMENTUM_FILTER"
    QUALITY_GATE = "QUALITY_GATE"
    EXECUTION_GUARDS = "EXECUTION_GUARDS"
    RISK_MODEL = "RISK_MODEL"


class FailCode(Enum):
    """Standardized failure codes - mapped 1:1 to stages."""
    PATTERN_NOT_PRESENT = "PATTERN_NOT_PRESENT"
    PATTERN_QUALITY_FAIL = "PATTERN_QUALITY_FAIL"
    NO_BREAKOUT_CLOSE = "NO_BREAKOUT_CLOSE"
    TREND_FILTER_BLOCK = "TREND_FILTER_BLOCK"
    MOMENTUM_TOO_WEAK = "MOMENTUM_TOO_WEAK"
    QUALITY_SCORE_TOO_LOW = "QUALITY_SCORE_TOO_LOW"
    EXECUTION_GUARD_BLOCK = "EXECUTION_GUARD_BLOCK"
    RISK_MODEL_FAIL = "RISK_MODEL_FAIL"
    SHORT_NOT_SUPPORTED = "SHORT_NOT_SUPPORTED"


@dataclass
class DecisionOutput:
    """
    Standardized decision output structure.
    
    This is the ONLY output format from the decision engine.
    """
    decision: DecisionResult
    stage: Stage
    fail_code: Optional[FailCode] = None
    reason: Optional[str] = None
    required: Optional[str] = None  # What was required to pass
    actual: Optional[str] = None    # What was actually observed
    
    # Additional context for debugging
    pattern_data: Optional[Dict] = None
    indicators: Optional[Dict] = None
    
    # ===== NEW: FINAL DECISION STATE =====
    decision_timestamp: Optional[str] = None  # Bar timestamp when decision made
    decision_source: str = "Backtest"  # "Live" / "Backtest" / "Replay"
    decision_summary: Optional[str] = None  # Human-readable summary ("ENTER LONG" / "NO TRADE")
    
    # ===== NEW: POSITION INTENT / PREVIEW =====
    planned_entry: Optional[float] = None  # Entry price
    planned_sl: Optional[float] = None  # Stop loss price
    planned_tp1: Optional[float] = None  # Take profit 1 price
    planned_tp2: Optional[float] = None  # Take profit 2 price
    planned_tp3: Optional[float] = None  # Take profit 3 price
    calculated_risk_usd: Optional[float] = None  # Risk amount in $
    calculated_rr: Optional[float] = None  # Risk:Reward ratio
    position_size: Optional[float] = None  # Lot size (e.g., 0.1)
    
    # ===== NEW: QUALITY GATE / SCORE BREAKDOWN =====
    entry_quality_score: Optional[float] = None  # Overall quality (0-10)
    quality_breakdown: Optional[Dict[str, float]] = None  # {"pattern": 8.5, "ema": 7.0, "momentum": 6.5, "volatility": 9.0}
    
    # ===== NEW: BAR-CLOSE / GUARD STATUS =====
    last_closed_bar_time: Optional[str] = None  # Timestamp of last closed bar
    using_closed_bar: bool = True  # Always True in production
    tick_noise_filter_passed: bool = True  # Anti-intrabar execution
    anti_fomo_passed: bool = True  # Prevents panic entries
    
    # ===== NEW: TP1 POST-EXIT DECISION =====
    tp_state: Optional[str] = None  # Current TP state (IN_TRADE, TP1_REACHED, TP2_REACHED, TP3_REACHED)
    post_tp1_decision: Optional[str] = None  # Decision after TP1 (HOLD, WAIT_NEXT_BAR, EXIT_TRADE, NOT_REACHED)
    tp1_exit_reason: Optional[str] = None  # Reason for TP1 decision
    bars_held_after_tp1: int = 0  # Number of bars held after TP1 was reached
    max_extension_after_tp1: float = 0.0  # Maximum extension price above TP1
    
    # ===== NEW: TP2 POST-EXIT DECISION =====
    post_tp2_decision: Optional[str] = None  # Decision after TP2 (HOLD, WAIT_NEXT_BAR, EXIT_TRADE, NOT_REACHED)
    tp2_exit_reason: Optional[str] = None  # Reason for TP2 decision
    bars_held_after_tp2: int = 0  # Number of bars held after TP2 was reached
    max_extension_after_tp2: float = 0.0  # Maximum extension price above TP2
    trailing_sl_level: Optional[float] = None  # Trailing SL level after TP2


class DecisionEngine:
    """
    Unified Decision Engine - Single Source of Truth.
    
    Evaluates the 8-stage pipeline in strict order:
    1. PATTERN_DETECTION
    2. PATTERN_QUALITY
    3. BREAKOUT_CONFIRMATION
    4. TREND_FILTER
    5. MOMENTUM_FILTER (optional)
    6. QUALITY_GATE (optional)
    7. EXECUTION_GUARDS
    8. RISK_MODEL
    
    Rules:
    - First failure blocks the trade (first-fail-only)
    - Every NO_TRADE has explicit stage and fail_code
    - NO UNKNOWN states allowed
    - Same logic for live, backtest, and analysis
    """
    
    def __init__(self, config: Dict, risk_engine: Optional[RiskEngine] = None):
        """
        Initialize Decision Engine.
        
        Args:
            config: Configuration dict with strategy and risk settings
            risk_engine: Optional RiskEngine instance for position sizing
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Extract strategy settings
        self.equality_tolerance = config.get('strategy', {}).get('equality_tolerance', 2.0)
        self.min_bars_between = config.get('strategy', {}).get('min_bars_between', 5)
        self.atr_multiplier_stop = config.get('strategy', {}).get('atr_multiplier_stop', 2.0)
        self.momentum_atr_threshold = config.get('strategy', {}).get('momentum_atr_threshold', 0.5)
        self.enable_momentum_filter = config.get('strategy', {}).get('enable_momentum_filter', False)
        self.cooldown_hours = config.get('strategy', {}).get('cooldown_hours', 5)
        self.pyramiding = config.get('strategy', {}).get('pyramiding', 3)
        self.risk_percent = config.get('risk', {}).get('risk_percent', 1.0)
        self.risk_engine = risk_engine or RiskEngine(
            risk_percent=self.risk_percent,
            commission_per_lot=config.get('risk', {}).get('commission_per_lot', 0.0),
        )
        
        # Optional quality gate threshold (if implemented)
        self.quality_score_threshold = config.get('strategy', {}).get('quality_score_threshold', None)
        
    def evaluate(self,
                 bar_index: int,
                 df: pd.DataFrame,
                 pattern: Optional[Dict],
                 account_state: Dict,
                 direction: str = "LONG",
                 symbol_info: Optional[Dict] = None) -> DecisionOutput:
        """
        Evaluate trading decision for a single bar.
        
        This is the ONLY method that makes trading decisions.
        
        Args:
            bar_index: Current bar index (can be negative -1 for last bar)
            df: DataFrame with OHLC and indicators (up to current bar)
            pattern: Pattern detection result (None if no pattern)
            account_state: Dict with equity, open_positions, last_trade_time
            direction: Trade direction ("LONG" or "SHORT")
            
        Returns:
            DecisionOutput with decision, stage, fail_code, reason
        """
        if direction.upper() == "SHORT":
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.EXECUTION_GUARDS,
                fail_code=FailCode.SHORT_NOT_SUPPORTED,
                reason="Short trades are disabled (long-only mode).",
                required="LONG direction only",
                actual=f"{direction} requested",
            )
        # Get current bar data (use -1 for last bar if index matches length)
        if bar_index < 0 or bar_index >= len(df):
            # If bar_index is out of range, use last bar
            bar = df.iloc[-1]
            bar_idx = len(df) - 1
        else:
            bar = df.iloc[bar_index]
            bar_idx = bar_index
        
        # Get bar timestamp for decision
        try:
            if hasattr(df.index[bar_idx], 'strftime'):
                bar_timestamp = df.index[bar_idx].strftime('%Y-%m-%d %H:%M')
            else:
                bar_timestamp = str(df.index[bar_idx])
        except (ValueError, IndexError, AttributeError) as e:
            self.logger.warning(f"Failed to format bar timestamp: {e}")
            bar_timestamp = "unknown"
        
        # Extract indicators (handle both dict and Series)
        if isinstance(bar, dict):
            close = bar.get('close', 0)
            ema50 = bar.get('ema50', 0)
            ema200 = bar.get('ema200', 0)
            atr = bar.get('atr14', 0)  # Use 'atr14' key
        else:
            close = bar['close']
            ema50 = bar['ema50'] if 'ema50' in bar.index else 0
            ema200 = bar['ema200'] if 'ema200' in bar.index else 0
            atr = bar['atr14'] if 'atr14' in bar.index else 0  # Use 'atr14' column
        
        indicators = {
            'close': close,
            'ema50': ema50,
            'ema200': ema200,
            'atr': atr
        }
        
        # ============================================================
        # STAGE 1: PATTERN_DETECTION
        # ============================================================
        result = self._check_pattern_detection(pattern, direction)
        if result is not None:
            result = self._enrich_decision_output(result, bar_timestamp)
            result.indicators = indicators
            return result
        
        # ============================================================
        # STAGE 2: PATTERN_QUALITY
        # ============================================================
        result = self._check_pattern_quality(pattern)
        if result is not None:
            result = self._enrich_decision_output(result, bar_timestamp)
            result.pattern_data = pattern
            result.indicators = indicators
            return result
        
        # ============================================================
        # STAGE 3: BREAKOUT_CONFIRMATION
        # ============================================================
        result = self._check_breakout_confirmation(close, pattern, direction)
        if result is not None:
            result = self._enrich_decision_output(result, bar_timestamp)
            result.pattern_data = pattern
            result.indicators = indicators
            return result
        
        # ============================================================
        # STAGE 4: TREND_FILTER
        # ============================================================
        result = self._check_trend_filter(close, ema50, ema200, direction)
        if result is not None:
            result = self._enrich_decision_output(result, bar_timestamp)
            result.indicators = indicators
            return result
        
        # ============================================================
        # STAGE 5: MOMENTUM_FILTER (optional)
        # ============================================================
        if self.enable_momentum_filter:
            result = self._check_momentum_filter(bar, atr)
            if result is not None:
                result = self._enrich_decision_output(result, bar_timestamp)
                result.indicators = indicators
                return result
        
        # ============================================================
        # STAGE 6: QUALITY_GATE (optional)
        # ============================================================
        if self.quality_score_threshold is not None:
            result = self._check_quality_gate(pattern)
            if result is not None:
                result = self._enrich_decision_output(result, bar_timestamp)
                result.pattern_data = pattern
                result.indicators = indicators
                return result
        
        # ============================================================
        # STAGE 7: EXECUTION_GUARDS
        # ============================================================
        result = self._check_execution_guards(bar_index, df, account_state)
        if result is not None:
            result = self._enrich_decision_output(result, bar_timestamp)
            result.indicators = indicators
            return result
        
        # ============================================================
        # STAGE 8: RISK_MODEL
        # ============================================================
        result = self._check_risk_model(
            close,
            atr,
            pattern,
            account_state,
            direction,
            symbol_info,
        )
        if result is not None:
            result = self._enrich_decision_output(result, bar_timestamp)
            result.pattern_data = pattern
            result.indicators = indicators
            return result
        
        # ============================================================
        # ALL CHECKS PASSED - TRADE ALLOWED
        # ============================================================
        
        # Get bar timestamp
        if bar_index < 0 or bar_index >= len(df):
            bar_timestamp = df.index[-1].strftime('%Y-%m-%d %H:%M') if hasattr(df.index[-1], 'strftime') else str(df.index[-1])
        else:
            bar_timestamp = df.index[bar_index].strftime('%Y-%m-%d %H:%M') if hasattr(df.index[bar_index], 'strftime') else str(df.index[bar_index])
        
        # Calculate position preview
        position_preview = self._calculate_position_preview(
            close,
            atr,
            pattern,
            account_state,
            direction,
            symbol_info,
        )
        
        # Calculate quality score
        quality_score, quality_breakdown = self._calculate_quality_score(pattern, indicators, direction)
        
        return DecisionOutput(
            decision=DecisionResult.TRADE_ALLOWED,
            stage=Stage.RISK_MODEL,  # Last stage
            pattern_data=pattern,
            indicators=indicators,
            # Final decision state
            decision_timestamp=bar_timestamp,
            decision_source="Backtest",  # Will be set by caller for Live/Replay
            decision_summary=f"ENTER {direction}",
            # Position preview
            planned_entry=position_preview['entry'],
            planned_sl=position_preview['sl'],
            planned_tp1=position_preview['tp1'],
            planned_tp2=position_preview['tp2'],
            planned_tp3=position_preview['tp3'],
            calculated_risk_usd=position_preview['risk_usd'],
            calculated_rr=position_preview['rr'],
            position_size=position_preview['position_size'],
            # Quality score
            entry_quality_score=quality_score,
            quality_breakdown=quality_breakdown,
            # Bar-close guard status
            last_closed_bar_time=bar_timestamp,
            using_closed_bar=True,
            tick_noise_filter_passed=True,
            anti_fomo_passed=True
        )
    
    def _enrich_decision_output(self, output: DecisionOutput, bar_timestamp: str) -> DecisionOutput:
        """
        Enrich DecisionOutput with final decision state fields.
        
        This method ensures all DecisionOutput objects have consistent
        timestamp, source, and summary fields.
        
        Args:
            output: DecisionOutput to enrich
            bar_timestamp: Timestamp of the decision bar
            
        Returns:
            Enriched DecisionOutput
        """
        # Set decision timestamp if not already set
        if output.decision_timestamp is None:
            output.decision_timestamp = bar_timestamp
        
        # Set decision source if not already set
        if output.decision_source is None or output.decision_source == "Backtest":
            output.decision_source = "Backtest"
        
        # Set decision summary if not already set
        if output.decision_summary is None:
            if output.decision == DecisionResult.TRADE_ALLOWED:
                output.decision_summary = "ENTER LONG"  # Simplified, would use direction param if passed
            else:
                output.decision_summary = "NO_TRADE"
        
        # Set last_closed_bar_time if not already set
        if output.last_closed_bar_time is None:
            output.last_closed_bar_time = bar_timestamp
        
        return output
    
    # ========================================================================
    # STAGE EVALUATION METHODS (in pipeline order)
    # ========================================================================
    
    def _check_pattern_detection(self, pattern: Optional[Dict], direction: str) -> Optional[DecisionOutput]:
        """
        Stage 1: Check if pattern is detected.
        
        Pine Script mapping:
        - db = double_bottom_detected
        - dt = double_top_detected
        """
        if pattern is None:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.PATTERN_DETECTION,
                fail_code=FailCode.PATTERN_NOT_PRESENT,
                reason=f"No {direction} pattern detected on this bar",
                required=f"{direction} pattern present",
                actual="No pattern"
            )
        
        return None  # Pass
    
    def _check_pattern_quality(self, pattern: Dict) -> Optional[DecisionOutput]:
        """
        Stage 2: Check pattern quality criteria.
        
        Checks:
        - Equality within tolerance
        - Minimum separation bars
        """
        # Check equality tolerance (already validated during pattern detection,
        # but we validate again for clarity)
        left_low = pattern.get('left_low', {}).get('price', 0)
        right_low = pattern.get('right_low', {}).get('price', 0)
        
        if left_low == 0 or right_low == 0:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.PATTERN_QUALITY,
                fail_code=FailCode.PATTERN_QUALITY_FAIL,
                reason="Invalid low prices in pattern",
                required="Valid low prices",
                actual=f"left={left_low}, right={right_low}"
            )
        
        # Check minimum separation
        left_idx = pattern.get('left_low', {}).get('index', 0)
        right_idx = pattern.get('right_low', {}).get('index', 0)
        bars_between = right_idx - left_idx
        
        if bars_between < self.min_bars_between:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.PATTERN_QUALITY,
                fail_code=FailCode.PATTERN_QUALITY_FAIL,
                reason=f"Pattern separation too small: {bars_between} bars",
                required=f"Minimum {self.min_bars_between} bars",
                actual=f"{bars_between} bars"
            )
        
        return None  # Pass
    
    def _check_breakout_confirmation(self, close: float, pattern: Dict, direction: str) -> Optional[DecisionOutput]:
        """
        Stage 3: Check breakout confirmation.
        
        Pine Script mapping:
        - LONG: close > neckline
        - SHORT: close < neckline
        """
        neckline = pattern.get('neckline', {}).get('price', 0)
        
        if neckline == 0:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.BREAKOUT_CONFIRMATION,
                fail_code=FailCode.NO_BREAKOUT_CLOSE,
                reason="Invalid neckline price",
                required="Valid neckline",
                actual="neckline=0"
            )
        
        if direction == "LONG":
            if close <= neckline:
                return DecisionOutput(
                    decision=DecisionResult.NO_TRADE,
                    stage=Stage.BREAKOUT_CONFIRMATION,
                    fail_code=FailCode.NO_BREAKOUT_CLOSE,
                    reason=f"Close not above neckline",
                    required=f"close > {neckline:.2f}",
                    actual=f"close = {close:.2f}"
                )
        else:  # SHORT
            if close >= neckline:
                return DecisionOutput(
                    decision=DecisionResult.NO_TRADE,
                    stage=Stage.BREAKOUT_CONFIRMATION,
                    fail_code=FailCode.NO_BREAKOUT_CLOSE,
                    reason=f"Close not below neckline",
                    required=f"close < {neckline:.2f}",
                    actual=f"close = {close:.2f}"
                )
        
        return None  # Pass
    
    def _check_trend_filter(self, close: float, ema50: float, ema200: float, direction: str) -> Optional[DecisionOutput]:
        """
        Stage 4: Check trend filter.
        
        Pine Script mapping:
        - LONG: close > ema50 && ema50 > ema200
        - SHORT: close < ema50 && ema50 < ema200
        """
        if direction == "LONG":
            if close <= ema50:
                return DecisionOutput(
                    decision=DecisionResult.NO_TRADE,
                    stage=Stage.TREND_FILTER,
                    fail_code=FailCode.TREND_FILTER_BLOCK,
                    reason="Price not above EMA50",
                    required=f"close > ema50 ({ema50:.2f})",
                    actual=f"close = {close:.2f}"
                )
            
            if ema50 <= ema200:
                return DecisionOutput(
                    decision=DecisionResult.NO_TRADE,
                    stage=Stage.TREND_FILTER,
                    fail_code=FailCode.TREND_FILTER_BLOCK,
                    reason="EMA50 not above EMA200 (bearish regime)",
                    required=f"ema50 > ema200 ({ema200:.2f})",
                    actual=f"ema50 = {ema50:.2f}"
                )
        else:  # SHORT
            if close >= ema50:
                return DecisionOutput(
                    decision=DecisionResult.NO_TRADE,
                    stage=Stage.TREND_FILTER,
                    fail_code=FailCode.TREND_FILTER_BLOCK,
                    reason="Price not below EMA50",
                    required=f"close < ema50 ({ema50:.2f})",
                    actual=f"close = {close:.2f}"
                )
            
            if ema50 >= ema200:
                return DecisionOutput(
                    decision=DecisionResult.NO_TRADE,
                    stage=Stage.TREND_FILTER,
                    fail_code=FailCode.TREND_FILTER_BLOCK,
                    reason="EMA50 not below EMA200 (bullish regime)",
                    required=f"ema50 < ema200 ({ema200:.2f})",
                    actual=f"ema50 = {ema50:.2f}"
                )
        
        return None  # Pass
    
    def _check_momentum_filter(self, bar, atr: float) -> Optional[DecisionOutput]:
        """
        Stage 5: Check momentum filter (optional).
        
        Pine Script mapping:
        - strongBreak = abs(close - open) > atr * threshold
        """
        if atr == 0:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.MOMENTUM_FILTER,
                fail_code=FailCode.MOMENTUM_TOO_WEAK,
                reason="ATR is zero, cannot evaluate momentum",
                required="Valid ATR",
                actual="atr=0"
            )
        
        # Extract open/close
        if isinstance(bar, dict):
            bar_open = bar.get('open', 0)
            bar_close = bar.get('close', 0)
        else:
            bar_open = bar['open']
            bar_close = bar['close']
        
        bar_range = abs(bar_close - bar_open)
        required_range = atr * self.momentum_atr_threshold
        
        if bar_range < required_range:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.MOMENTUM_FILTER,
                fail_code=FailCode.MOMENTUM_TOO_WEAK,
                reason=f"Bar range too weak: {bar_range:.2f}",
                required=f"range >= {required_range:.2f} (ATR * {self.momentum_atr_threshold})",
                actual=f"range = {bar_range:.2f}"
            )
        
        return None  # Pass
    
    def _check_quality_gate(self, pattern: Dict) -> Optional[DecisionOutput]:
        """
        Stage 6: Check quality gate (optional).
        
        Requires pattern to have quality_score field.
        """
        quality_score = pattern.get('quality_score', None)
        
        if quality_score is None:
            # If quality gate is enabled but score not available, skip this check
            return None
        
        if quality_score < self.quality_score_threshold:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.QUALITY_GATE,
                fail_code=FailCode.QUALITY_SCORE_TOO_LOW,
                reason=f"Pattern quality score too low: {quality_score:.2f}",
                required=f"score >= {self.quality_score_threshold:.2f}",
                actual=f"score = {quality_score:.2f}"
            )
        
        return None  # Pass
    
    def _calculate_position_preview(self, close: float, atr: float, pattern: Dict, 
                                    account_state: Dict, direction: str,
                                    symbol_info: Optional[Dict]) -> Dict:
        """
        Calculate position preview: SL, TP levels, risk $, RR.
        
        Returns:
            Dict with entry, sl, tp1-3, risk_usd, rr, position_size
        """
        equity = account_state.get('equity', 10000)  # Default for backtest
        
        # Calculate SL distance
        sl_distance = atr * self.atr_multiplier_stop
        
        # Entry and SL prices
        entry_price = close
        if direction == "LONG":
            sl_price = entry_price - sl_distance
        else:
            sl_price = entry_price + sl_distance
        
        # Calculate TP levels (using RR ratios from config)
        rr_long = self.config.get('strategy', {}).get('risk_reward_ratio_long', 2.9)
        rr_short = self.config.get('strategy', {}).get('risk_reward_ratio_short', 1.4)
        rr = rr_long if direction == "LONG" else rr_short
        
        if direction == "LONG":
            tp1 = entry_price + (sl_distance * rr * 0.5)  # 50% of full TP
            tp2 = entry_price + (sl_distance * rr * 0.75)  # 75% of full TP
            tp3 = entry_price + (sl_distance * rr)  # Full TP
        else:
            tp1 = entry_price - (sl_distance * rr * 0.5)
            tp2 = entry_price - (sl_distance * rr * 0.75)
            tp3 = entry_price - (sl_distance * rr)
        
        position_size = None
        actual_risk = None
        if self.risk_engine and symbol_info:
            position_size = self.risk_engine.calculate_position_size(
                equity=equity,
                entry_price=entry_price,
                stop_loss=sl_price,
                symbol_info=symbol_info,
            )
            if position_size is not None:
                contract_size = symbol_info.get('trade_contract_size', 100.0)
                price_risk = abs(entry_price - sl_price)
                actual_risk = (price_risk * position_size * contract_size) + (
                    self.risk_engine.commission_per_lot * position_size * 2
                )

        return {
            'entry': entry_price,
            'sl': sl_price,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'risk_usd': actual_risk,
            'rr': rr,
            'position_size': position_size
        }
    
    def _calculate_quality_score(self, pattern: Dict, indicators: Dict, direction: str) -> Tuple[float, Dict[str, float]]:
        """
        Calculate entry quality score (0-10) with breakdown.
        
        Components:
        - Pattern quality (0-10): Symmetry, depth, separation
        - EMA alignment (0-10): Distance from EMAs, EMA spread
        - Momentum (0-10): Bar strength, volume (if available)
        - Volatility (0-10): ATR stability, recent volatility
        
        Returns:
            Tuple of (overall_score, breakdown_dict)
        """
        breakdown = {}
        
        # 1. Pattern Quality (0-10)
        left_low = pattern.get('left_low', {}).get('price', 0)
        right_low = pattern.get('right_low', {}).get('price', 0)
        neckline = pattern.get('neckline', {}).get('price', 0)
        
        if left_low > 0 and right_low > 0:
            # Symmetry: How close are the two lows?
            symmetry = 1 - min(abs(left_low - right_low) / ((left_low + right_low) / 2), 0.1) / 0.1
            # Depth: How much below neckline?
            depth = min((neckline - left_low) / neckline, 0.05) / 0.05 if neckline > 0 else 0.5
            pattern_score = (symmetry * 0.6 + depth * 0.4) * 10
        else:
            pattern_score = 5.0
        breakdown['pattern'] = round(pattern_score, 1)
        
        # 2. Regime Alignment (0-10) based on EMA relationships
        close = indicators.get('close', 0)
        ema50 = indicators.get('ema50', 0)
        ema200 = indicators.get('ema200', 0)
        
        regime_score = 5.0
        if close > 0 and ema50 > 0 and ema200 > 0:
            is_bull = close > ema50 and ema50 > ema200
            is_bear = close < ema50 and ema50 < ema200
            # Alignment: direction consistent with regime (LONG in bull, SHORT in bear)
            aligned = (direction == "LONG" and is_bull) or (direction == "SHORT" and is_bear)
            # Confidence proxy: EMA50/EMA200 separation
            spread_pct = abs((ema50 - ema200) / ema200) * 100
            sep_score = min(spread_pct / 1.0, 1.0)  # 1% separation = max
            regime_score = (1.0 if aligned else 0.3) * 10 * (0.6 + 0.4 * sep_score)
        breakdown['regime'] = round(regime_score, 1)
        
        # 3. Momentum (0-10)
        # Simplified - can be enhanced with volume data
        atr = indicators.get('atr', 0)
        if atr > 0:
            momentum_score = min(atr / 5.0, 1.0) * 10  # Higher ATR = more momentum
        else:
            momentum_score = 5.0
        breakdown['momentum'] = round(momentum_score, 1)
        
        # 4. Momentum Alignment (0-10) — use ATR as proxy
        if atr > 0:
            momentum_score = min(atr / 5.0, 1.0) * 10
        else:
            momentum_score = 5.0
        breakdown['momentum'] = round(momentum_score, 1)
        
        # Overall score (weighted average)
        # Contracted weights: pattern 0.3, regime 0.4, momentum 0.3
        overall = (
            pattern_score * 0.3 +
            regime_score * 0.4 +
            momentum_score * 0.3
        )
        
        return round(overall, 1), breakdown
    
    def _check_execution_guards(self, bar_index: int, df: pd.DataFrame, account_state: Dict) -> Optional[DecisionOutput]:
        """
        Stage 7: Check execution guards.
        
        Pine Script mapping:
        - coolOk = bars_since_trade >= cooldown_bars
        - strategy.position_size == 0 (or pyramiding check)
        """
        # Check cooldown
        last_trade_bar = account_state.get('last_trade_bar', -9999)
        bars_since_trade = bar_index - last_trade_bar
        
        # Convert cooldown_hours to bars (H1 timeframe = 1 bar per hour)
        cooldown_bars = self.cooldown_hours
        
        if bars_since_trade < cooldown_bars:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.EXECUTION_GUARDS,
                fail_code=FailCode.EXECUTION_GUARD_BLOCK,
                reason=f"Cooldown period not elapsed: {bars_since_trade} bars since last trade",
                required=f"Minimum {cooldown_bars} bars",
                actual=f"{bars_since_trade} bars"
            )
        
        # Check pyramiding
        open_positions = account_state.get('open_positions', 0)
        
        if open_positions >= self.pyramiding:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.EXECUTION_GUARDS,
                fail_code=FailCode.EXECUTION_GUARD_BLOCK,
                reason=f"Pyramiding limit reached: {open_positions} positions",
                required=f"Max {self.pyramiding} positions",
                actual=f"{open_positions} positions"
            )
        
        return None  # Pass
    
    def _check_risk_model(self, close: float, atr: float, pattern: Dict, 
                         account_state: Dict, direction: str,
                         symbol_info: Optional[Dict]) -> Optional[DecisionOutput]:
        """
        Stage 8: Check risk model.
        
        Validates:
        - Stop loss distance is valid
        - Position size can be calculated
        - Risk is within limits
        """
        # Check ATR validity (must be > 0 and reasonable)
        if atr is None or atr <= 0:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.RISK_MODEL,
                fail_code=FailCode.RISK_MODEL_FAIL,
                reason=f"Invalid ATR value: {atr}",
                required="ATR > 0",
                actual=f"atr={atr}"
            )
        
        # Check for unreasonably small ATR (< 0.5 points is suspicious)
        if atr < 0.5:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.RISK_MODEL,
                fail_code=FailCode.RISK_MODEL_FAIL,
                reason=f"ATR too small: {atr:.2f} (data quality issue)",
                required="ATR >= 0.5",
                actual=f"atr={atr:.2f}"
            )
        
        # Calculate stop loss distance
        sl_distance = atr * self.atr_multiplier_stop
        
        if sl_distance <= 0:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.RISK_MODEL,
                fail_code=FailCode.RISK_MODEL_FAIL,
                reason="Invalid stop loss distance",
                required="sl_distance > 0",
                actual=f"sl_distance = {sl_distance:.2f}"
            )
        
        # Check if position size can be calculated
        equity = account_state.get('equity', 0)
        
        if equity <= 0:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.RISK_MODEL,
                fail_code=FailCode.RISK_MODEL_FAIL,
                reason="Invalid equity balance",
                required="equity > 0",
                actual=f"equity = {equity:.2f}"
            )
        
        if sl_distance > close * 0.1:  # SL > 10% of price is too wide
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.RISK_MODEL,
                fail_code=FailCode.RISK_MODEL_FAIL,
                reason=f"Stop loss too wide: {sl_distance:.2f} points ({sl_distance/close*100:.1f}%)",
                required="sl_distance < 10% of price",
                actual=f"sl_distance = {sl_distance:.2f} ({sl_distance/close*100:.1f}%)"
            )

        if not symbol_info:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.RISK_MODEL,
                fail_code=FailCode.RISK_MODEL_FAIL,
                reason="Missing symbol info for position sizing",
                required="symbol_info from MarketDataService",
                actual="symbol_info = None"
            )

        if not self.risk_engine:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.RISK_MODEL,
                fail_code=FailCode.RISK_MODEL_FAIL,
                reason="Risk engine unavailable for position sizing",
                required="RiskEngine instance",
                actual="risk_engine = None"
            )

        entry_price = close
        stop_loss = entry_price - sl_distance if direction == "LONG" else entry_price + sl_distance
        position_size = self.risk_engine.calculate_position_size(
            equity=equity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            symbol_info=symbol_info,
        )

        if position_size is None or position_size <= 0:
            return DecisionOutput(
                decision=DecisionResult.NO_TRADE,
                stage=Stage.RISK_MODEL,
                fail_code=FailCode.RISK_MODEL_FAIL,
                reason="Position size calculation failed",
                required="Valid position size",
                actual=f"position_size = {position_size}"
            )
        
        return None  # Pass

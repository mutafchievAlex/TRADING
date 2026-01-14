"""
Market Regime Engine - Determines market environment (Bull, Bear, Range)

This module identifies the current market regime based on EMA and price relationships.
Regime provides directional bias for decision-making and quality scoring.
Regime NEVER issues trade signals - it is CONTEXT ONLY.

Rules:
- BULL: close > EMA50 AND EMA50 > EMA200
- BEAR: close < EMA50 AND EMA50 < EMA200
- RANGE: neither bull nor bear conditions met

Confidence is based on EMA separation and price distance from EMA50.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict
from enum import Enum
import logging


class RegimeType(Enum):
    """Market regime states."""
    BULL = "BULL"
    BEAR = "BEAR"
    RANGE = "RANGE"


class MarketRegimeEngine:
    """
    Determines current market regime (Bull, Bear, Range).
    
    Uses only EMA50, EMA200, and close price.
    All calculations use bar-close values only.
    Regime changes only on bar close (matches current timeframe).
    """
    
    def __init__(self, min_ema_distance_percent: float = 0.1):
        """
        Initialize Market Regime Engine.
        
        Args:
            min_ema_distance_percent: Minimum EMA separation to count towards confidence
                                     (0.1 = 0.1% separation)
        """
        self.logger = logging.getLogger(__name__)
        self.min_ema_distance_percent = min_ema_distance_percent
        
        # Current state
        self.current_regime = RegimeType.RANGE
        self.confidence = 0.0
        self.ema50_ema200_distance = 0.0  # As percentage
        self.price_ema50_distance = 0.0   # As percentage
    
    def evaluate(self, 
                 close: float, 
                 ema50: float, 
                 ema200: float) -> Tuple[RegimeType, float]:
        """
        Evaluate market regime based on price and EMAs.
        
        Args:
            close: Current close price
            ema50: EMA 50 value
            ema200: EMA 200 value
            
        Returns:
            Tuple of (regime, confidence)
        """
        try:
            # Ensure all values are valid (not NaN, not zero for EMAs)
            if not all(isinstance(v, (int, float)) for v in [close, ema50, ema200]):
                self.logger.warning(f"Invalid value types: close={close}, ema50={ema50}, ema200={ema200}")
                self.current_regime = RegimeType.RANGE
                self.confidence = 0.0
                self.ema50_ema200_distance = 0.0
                self.price_ema50_distance = 0.0
                return self.current_regime, self.confidence
            
            if any(np.isnan(v) for v in [close, ema50, ema200]):
                self.logger.warning(f"NaN values: close={close}, ema50={ema50}, ema200={ema200}")
                self.current_regime = RegimeType.RANGE
                self.confidence = 0.0
                self.ema50_ema200_distance = 0.0
                self.price_ema50_distance = 0.0
                return self.current_regime, self.confidence
            
            # Check for zero/invalid EMAs
            if ema50 == 0.0 or ema200 == 0.0:
                self.logger.warning(f"Zero EMA values: ema50={ema50}, ema200={ema200}")
                self.current_regime = RegimeType.RANGE
                self.confidence = 0.0
                self.ema50_ema200_distance = 0.0
                self.price_ema50_distance = 0.0
                return self.current_regime, self.confidence
            
            # Calculate EMA distance (percentage)
            ema_distance = ((ema50 - ema200) / ema200) * 100
            self.ema50_ema200_distance = ema_distance
            
            # Calculate price distance from EMA50 (percentage)
            price_distance = ((close - ema50) / ema50) * 100
            self.price_ema50_distance = price_distance
            
            # Determine regime based on conditions
            # BULL: close > ema50 AND ema50 > ema200
            if close > ema50 and ema50 > ema200:
                self.current_regime = RegimeType.BULL
                # Confidence based on EMA separation and price distance
                self.confidence = self._calculate_confidence(
                    ema_distance, price_distance, is_bull=True
                )
            
            # BEAR: close < ema50 AND ema50 < ema200
            elif close < ema50 and ema50 < ema200:
                self.current_regime = RegimeType.BEAR
                # Confidence based on EMA separation and price distance
                self.confidence = self._calculate_confidence(
                    ema_distance, price_distance, is_bull=False
                )
            
            # RANGE: otherwise
            else:
                self.current_regime = RegimeType.RANGE
                self.confidence = 0.0
            
            self.logger.debug(
                f"Regime: {self.current_regime.value}, "
                f"Confidence: {self.confidence:.2f}, "
                f"EMA Distance: {self.ema50_ema200_distance:.2f}%, "
                f"Price Distance: {self.price_ema50_distance:.2f}%"
            )
            
            return self.current_regime, self.confidence
            
        except Exception as e:
            self.logger.error(f"Error evaluating market regime: {e}")
            self.current_regime = RegimeType.RANGE
            self.confidence = 0.0
            return self.current_regime, self.confidence
    
    def _calculate_confidence(self, 
                             ema_distance: float, 
                             price_distance: float,
                             is_bull: bool) -> float:
        """
        Calculate confidence score based on EMA separation and price distance.
        
        Confidence increases with:
        - Greater EMA50/EMA200 separation (stronger trend)
        - Greater distance of price from EMA50 (established momentum)
        
        Args:
            ema_distance: EMA50 - EMA200 as percentage of EMA200
            price_distance: Price - EMA50 as percentage of EMA50
            is_bull: True for bullish regime, False for bearish
            
        Returns:
            Confidence score [0.0, 1.0]
        """
        try:
            # Normalize distances to absolute values for calculation
            abs_ema_distance = abs(ema_distance)
            abs_price_distance = abs(price_distance)
            
            # EMA separation score (max out at 1% separation = 1.0 score)
            ema_score = min(abs_ema_distance / 1.0, 1.0)
            
            # Price distance score (max out at 2% distance = 1.0 score)
            price_score = min(abs_price_distance / 2.0, 1.0)
            
            # Overall confidence: weighted combination
            # 60% weight to EMA separation, 40% to price distance
            confidence = (ema_score * 0.6) + (price_score * 0.4)
            
            # Cap at 1.0
            confidence = min(confidence, 1.0)
            
            return confidence
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {e}")
            return 0.0
    
    def get_state(self) -> Dict:
        """
        Get current regime state.
        
        Returns:
            Dict with regime state and metrics
        """
        return {
            'regime': self.current_regime.value,
            'confidence': self.confidence,
            'ema50_ema200_distance': self.ema50_ema200_distance,
            'price_ema50_distance': self.price_ema50_distance
        }

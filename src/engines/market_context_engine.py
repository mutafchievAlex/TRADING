"""
Market Context Engine - Evaluates market conditions and entry quality

This module provides market context analysis without modifying the core strategy:
- Market regime detection (BULL/BEAR/RANGE)
- Volatility state classification (LOW/NORMAL/HIGH)
- Entry quality scoring (0-10)

Philosophy:
- Acts as a quality gate, not a strategy modifier
- Preserves all existing entry/exit logic
- Adds market awareness to trade selection
"""

import logging
from enum import Enum
from typing import Tuple, Dict, Optional
import pandas as pd


class MarketRegime(Enum):
    """Market regime classification"""
    BULL = "BULL"
    BEAR = "BEAR"
    RANGE = "RANGE"


class VolatilityState(Enum):
    """Volatility classification"""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class MarketContextEngine:
    """
    Evaluates market context and entry quality for trade decisions.
    
    Provides:
    - Market regime (trend direction)
    - Volatility state
    - Entry quality score (0-10)
    
    Does NOT modify:
    - Entry conditions
    - SL/TP formulas
    - Risk percent
    """
    
    def __init__(self,
                 ema_range_threshold_percent: float = 0.3,
                 atr_low_threshold: float = 0.5,
                 atr_high_threshold: float = 2.0,
                 minimum_entry_score: float = 6.5):
        """
        Initialize Market Context Engine.
        
        Args:
            ema_range_threshold_percent: EMA separation % for RANGE detection (default: 0.3%)
            atr_low_threshold: ATR % threshold for LOW volatility (default: 0.5%)
            atr_high_threshold: ATR % threshold for HIGH volatility (default: 2.0%)
            minimum_entry_score: Minimum quality score to allow entry (default: 6.5)
        """
        self.ema_range_threshold_percent = ema_range_threshold_percent
        self.atr_low_threshold = atr_low_threshold
        self.atr_high_threshold = atr_high_threshold
        self.minimum_entry_score = minimum_entry_score
        self.logger = logging.getLogger(__name__)
        
        # Quality score weights (must sum to 1.0)
        self.weights = {
            'pattern_quality': 0.35,
            'momentum_strength': 0.25,
            'ema_alignment': 0.25,
            'volatility_alignment': 0.15
        }
        
        self.logger.info(f"Market Context Engine initialized:")
        self.logger.info(f"  Minimum entry score: {minimum_entry_score}/10")
        self.logger.info(f"  EMA range threshold: {ema_range_threshold_percent}%")
        self.logger.info(f"  ATR thresholds: LOW<{atr_low_threshold}%, HIGH>{atr_high_threshold}%")
    
    def detect_market_regime(self, ema50: float, ema200: float, current_price: float) -> MarketRegime:
        """
        Detect market regime based on EMA positioning.
        
        Args:
            ema50: EMA50 value
            ema200: EMA200 value
            current_price: Current close price
            
        Returns:
            MarketRegime enum
        """
        try:
            # Calculate EMA separation as percentage
            ema_diff_percent = abs(ema50 - ema200) / current_price * 100
            
            # Check if in range (EMAs too close)
            if ema_diff_percent < self.ema_range_threshold_percent:
                return MarketRegime.RANGE
            
            # Determine trend direction
            if ema50 > ema200:
                return MarketRegime.BULL
            else:
                return MarketRegime.BEAR
                
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return MarketRegime.RANGE
    
    def detect_volatility_state(self, atr: float, current_price: float) -> VolatilityState:
        """
        Classify volatility state based on ATR percentage.
        
        Args:
            atr: ATR14 value
            current_price: Current close price
            
        Returns:
            VolatilityState enum
        """
        try:
            # Calculate ATR as percentage of price
            atr_percent = (atr / current_price) * 100
            
            # Classify volatility
            if atr_percent < self.atr_low_threshold:
                return VolatilityState.LOW
            elif atr_percent > self.atr_high_threshold:
                return VolatilityState.HIGH
            else:
                return VolatilityState.NORMAL
                
        except Exception as e:
            self.logger.error(f"Error detecting volatility state: {e}")
            return VolatilityState.NORMAL
    
    def calculate_pattern_quality(self, pattern: Optional[Dict]) -> float:
        """
        Evaluate pattern quality (0-10 scale).
        
        Factors:
        - Pattern symmetry (equality of lows)
        - Neckline strength
        - Bar distance (not too compressed)
        
        Args:
            pattern: Pattern dict with properties
            
        Returns:
            Score 0-10
        """
        try:
            if not pattern or not pattern.get('pattern_valid'):
                return 0.0
            
            score = 0.0
            
            # Symmetry score (max 5 points)
            # Perfect symmetry (0% diff) = 5 points
            # 5% diff = 2.5 points
            # 10% diff = 0 points
            equality_diff = pattern.get('equality_diff_percent', 10.0)
            symmetry_score = max(0, 5 - (equality_diff / 2))
            score += symmetry_score
            
            # Distance score (max 3 points)
            # Good spacing between lows (10-50 bars) = 3 points
            left_idx = pattern.get('left_low', {}).get('index', 0)
            right_idx = pattern.get('right_low', {}).get('index', 0)
            bar_distance = abs(right_idx - left_idx)
            
            if 10 <= bar_distance <= 50:
                distance_score = 3.0
            elif bar_distance < 10:
                distance_score = bar_distance / 10 * 3  # Compressed
            else:
                distance_score = max(0, 3 - (bar_distance - 50) / 50)  # Too wide
            
            score += distance_score
            
            # Neckline clarity (max 2 points)
            # Clear neckline above lows = 2 points
            neckline = pattern.get('neckline', {}).get('price', 0)
            left_low = pattern.get('left_low', {}).get('price', 0)
            right_low = pattern.get('right_low', {}).get('price', 0)
            avg_low = (left_low + right_low) / 2
            
            if neckline > avg_low:
                neckline_separation = (neckline - avg_low) / avg_low * 100
                clarity_score = min(2.0, neckline_separation * 2)  # 1% separation = 2 points
            else:
                clarity_score = 0.0
            
            score += clarity_score
            
            return min(10.0, score)
            
        except Exception as e:
            self.logger.error(f"Error calculating pattern quality: {e}")
            return 0.0
    
    def calculate_momentum_strength(self, current_bar: pd.Series, ema50: float) -> float:
        """
        Evaluate momentum strength (0-10 scale).
        
        Factors:
        - Candle size relative to ATR
        - Distance from EMA50
        - Candle direction
        
        Args:
            current_bar: Current bar with OHLC
            ema50: EMA50 value
            
        Returns:
            Score 0-10
        """
        try:
            score = 0.0
            
            # Candle size score (max 4 points)
            candle_size = abs(current_bar['close'] - current_bar['open'])
            atr = current_bar.get('atr14', 0)
            
            if atr > 0:
                size_ratio = candle_size / atr
                size_score = min(4.0, size_ratio * 2)  # 2 ATR candle = 4 points
                score += size_score
            
            # Distance from EMA50 (max 3 points)
            # Ideal: Close is 0.2-1% above EMA50 for LONG
            close_price = current_bar['close']
            if close_price > ema50:
                distance_percent = (close_price - ema50) / ema50 * 100
                if 0.2 <= distance_percent <= 1.0:
                    distance_score = 3.0
                elif distance_percent < 0.2:
                    distance_score = distance_percent / 0.2 * 3
                else:
                    distance_score = max(0, 3 - (distance_percent - 1) / 2)
                score += distance_score
            
            # Candle direction (max 3 points)
            # Bullish candle = 3 points
            if current_bar['close'] > current_bar['open']:
                score += 3.0
            elif current_bar['close'] == current_bar['open']:
                score += 1.5  # Doji
            
            return min(10.0, score)
            
        except Exception as e:
            self.logger.error(f"Error calculating momentum strength: {e}")
            return 0.0
    
    def calculate_ema_alignment(self, ema20: float, ema50: float, 
                                ema200: float, current_price: float) -> float:
        """
        Evaluate EMA alignment quality (0-10 scale).
        
        Perfect alignment for LONG:
        - Price > EMA20 > EMA50 > EMA200
        - Good spacing between EMAs
        
        Args:
            ema20: EMA20 value
            ema50: EMA50 value
            ema200: EMA200 value
            current_price: Current close price
            
        Returns:
            Score 0-10
        """
        try:
            score = 0.0
            
            # Hierarchical order (max 5 points)
            if current_price > ema20 > ema50 > ema200:
                score += 5.0
            elif current_price > ema50 > ema200:
                score += 3.0
            elif current_price > ema50:
                score += 1.0
            
            # EMA spacing quality (max 5 points)
            # Good spacing indicates strong trend
            if ema50 > ema200:
                ema50_200_gap = (ema50 - ema200) / current_price * 100
                spacing_score = min(2.5, ema50_200_gap * 5)  # 0.5% gap = 2.5 points
                score += spacing_score
            
            if ema20 > ema50:
                ema20_50_gap = (ema20 - ema50) / current_price * 100
                spacing_score = min(2.5, ema20_50_gap * 10)  # 0.25% gap = 2.5 points
                score += spacing_score
            
            return min(10.0, score)
            
        except Exception as e:
            self.logger.error(f"Error calculating EMA alignment: {e}")
            return 0.0
    
    def calculate_volatility_alignment(self, volatility_state: VolatilityState,
                                      market_regime: MarketRegime) -> float:
        """
        Evaluate if volatility matches market conditions (0-10 scale).
        
        Ideal conditions:
        - BULL trend: NORMAL volatility (not too choppy)
        - RANGE: LOW volatility (avoid false breakouts)
        
        Args:
            volatility_state: Current volatility state
            market_regime: Current market regime
            
        Returns:
            Score 0-10
        """
        try:
            # Optimal volatility for each regime
            if market_regime == MarketRegime.BULL:
                if volatility_state == VolatilityState.NORMAL:
                    return 10.0
                elif volatility_state == VolatilityState.LOW:
                    return 6.0
                else:  # HIGH
                    return 4.0
            
            elif market_regime == MarketRegime.BEAR:
                if volatility_state == VolatilityState.NORMAL:
                    return 8.0
                elif volatility_state == VolatilityState.HIGH:
                    return 5.0
                else:  # LOW
                    return 3.0
            
            else:  # RANGE
                if volatility_state == VolatilityState.LOW:
                    return 10.0
                elif volatility_state == VolatilityState.NORMAL:
                    return 5.0
                else:  # HIGH
                    return 2.0
                    
        except Exception as e:
            self.logger.error(f"Error calculating volatility alignment: {e}")
            return 5.0
    
    def calculate_entry_quality_score(self, current_bar: pd.Series, pattern: Optional[Dict],
                                      ema20: float, ema50: float, ema200: float) -> Tuple[float, Dict]:
        """
        Calculate overall entry quality score (0-10 scale).
        
        Combines all quality factors with weighted averaging.
        
        Args:
            current_bar: Current bar with OHLC and indicators
            pattern: Pattern dict
            ema20: EMA20 value
            ema50: EMA50 value
            ema200: EMA200 value
            
        Returns:
            Tuple of (total_score, component_scores_dict)
        """
        try:
            current_price = current_bar['close']
            atr = current_bar.get('atr14', 0)
            
            # Detect market context
            market_regime = self.detect_market_regime(ema50, ema200, current_price)
            volatility_state = self.detect_volatility_state(atr, current_price)
            
            # Calculate component scores
            pattern_score = self.calculate_pattern_quality(pattern)
            momentum_score = self.calculate_momentum_strength(current_bar, ema50)
            ema_score = self.calculate_ema_alignment(ema20, ema50, ema200, current_price)
            volatility_score = self.calculate_volatility_alignment(volatility_state, market_regime)
            
            # Weighted total
            total_score = (
                pattern_score * self.weights['pattern_quality'] +
                momentum_score * self.weights['momentum_strength'] +
                ema_score * self.weights['ema_alignment'] +
                volatility_score * self.weights['volatility_alignment']
            )
            
            components = {
                'pattern_quality': pattern_score,
                'momentum_strength': momentum_score,
                'ema_alignment': ema_score,
                'volatility_alignment': volatility_score,
                'market_regime': market_regime.value,
                'volatility_state': volatility_state.value,
                'total_score': round(total_score, 2)
            }
            
            self.logger.debug(f"Entry quality: {total_score:.2f}/10 "
                            f"(Pattern={pattern_score:.1f}, Momentum={momentum_score:.1f}, "
                            f"EMA={ema_score:.1f}, Vol={volatility_score:.1f})")
            
            return total_score, components
            
        except Exception as e:
            self.logger.error(f"Error calculating entry quality: {e}")
            return 0.0, {}
    
    def evaluate_entry_gate(self, total_score: float) -> Tuple[bool, str]:
        """
        Check if entry quality meets minimum threshold.
        
        Args:
            total_score: Total entry quality score
            
        Returns:
            Tuple of (passes_gate, reason)
        """
        passes = total_score >= self.minimum_entry_score
        
        if passes:
            reason = f"Quality score {total_score:.2f} >= {self.minimum_entry_score} threshold"
        else:
            reason = f"Quality score {total_score:.2f} < {self.minimum_entry_score} threshold"
            self.logger.info(f"Entry rejected by quality gate: {reason}")
        
        return passes, reason


if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.DEBUG)
    
    engine = MarketContextEngine()
    
    # Mock data
    test_bar = pd.Series({
        'open': 2000,
        'high': 2020,
        'low': 1995,
        'close': 2015,
        'atr14': 15
    })
    
    test_pattern = {
        'pattern_valid': True,
        'left_low': {'price': 1990, 'index': 10},
        'right_low': {'price': 1992, 'index': 30},
        'neckline': {'price': 2010, 'index': 20},
        'equality_diff_percent': 1.5
    }
    
    score, components = engine.calculate_entry_quality_score(
        test_bar, test_pattern, 
        ema20=2005, ema50=2000, ema200=1980
    )
    
    print(f"\nEntry Quality Score: {score:.2f}/10")
    print(f"  Pattern: {components['pattern_quality']:.2f}")
    print(f"  Momentum: {components['momentum_strength']:.2f}")
    print(f"  EMA Alignment: {components['ema_alignment']:.2f}")
    print(f"  Volatility: {components['volatility_alignment']:.2f}")
    print(f"  Market Regime: {components['market_regime']}")
    print(f"  Volatility State: {components['volatility_state']}")
    
    passes, reason = engine.evaluate_entry_gate(score)
    print(f"\nEntry Gate: {'PASS' if passes else 'FAIL'}")
    print(f"  {reason}")

"""
Pattern Engine - Detects Double Bottom chart patterns

This module implements Double Bottom pattern detection exactly as specified.
Pattern structure: Low -> High -> Low (with configurable equality tolerance).

Pine Script Reference:
- Pivot detection using ta.pivotlow() / ta.pivothigh()
- Double Bottom: Two lows at approximately the same level separated by a peak
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, List
import logging


class PatternEngine:
    """
    Detects Double Bottom patterns in price data.
    
    Double Bottom Structure:
    1. First pivot low (left low)
    2. Pivot high (neckline)
    3. Second pivot low (right low)
    
    Conditions:
    - Two lows must be within tolerance % of each other
    - Must be separated by a significant peak
    - Minimum bars between pivots required
    """
    
    def __init__(self, lookback_left: int = 5, lookback_right: int = 5,
                 equality_tolerance: float = 2.0, min_bars_between: int = 10):
        """
        Initialize Pattern Engine.
        
        Args:
            lookback_left: Bars to the left for pivot detection (default: 5)
            lookback_right: Bars to the right for pivot detection (default: 5)
            equality_tolerance: % tolerance for two lows to be "equal" (default: 2.0%)
            min_bars_between: Minimum bars between two lows (default: 10)
        """
        self.lookback_left = lookback_left
        self.lookback_right = lookback_right
        self.equality_tolerance = equality_tolerance
        self.min_bars_between = min_bars_between
        self.logger = logging.getLogger(__name__)
    
    def find_pivot_lows(self, df: pd.DataFrame) -> List[dict]:
        """
        Find all pivot lows in the data.
        
        A pivot low is a local minimum where:
        - The low is lower than N bars to the left
        - The low is lower than N bars to the right
        
        Pine Script equivalent: ta.pivotlow(low, leftbars, rightbars)
        
        Args:
            df: DataFrame with 'low' column
            
        Returns:
            List of dicts with pivot low info: {'index': int, 'price': float, 'time': datetime}
        """
        pivots = []
        lows = df['low'].values
        times = df.index.values
        
        # Start from lookback_left and end at len - lookback_right
        for i in range(self.lookback_left, len(lows) - self.lookback_right):
            current_low = lows[i]
            
            # Check if current bar is lower than left bars
            is_pivot = True
            for j in range(1, self.lookback_left + 1):
                if lows[i - j] <= current_low:
                    is_pivot = False
                    break
            
            if not is_pivot:
                continue
            
            # Check if current bar is lower than right bars
            for j in range(1, self.lookback_right + 1):
                if lows[i + j] <= current_low:
                    is_pivot = False
                    break
            
            if is_pivot:
                pivots.append({
                    'index': i,
                    'price': current_low,
                    'time': times[i]
                })
        
        return pivots
    
    def find_pivot_highs(self, df: pd.DataFrame) -> List[dict]:
        """
        Find all pivot highs in the data.
        
        A pivot high is a local maximum where:
        - The high is higher than N bars to the left
        - The high is higher than N bars to the right
        
        Pine Script equivalent: ta.pivothigh(high, leftbars, rightbars)
        
        Args:
            df: DataFrame with 'high' column
            
        Returns:
            List of dicts with pivot high info: {'index': int, 'price': float, 'time': datetime}
        """
        pivots = []
        highs = df['high'].values
        times = df.index.values
        
        for i in range(self.lookback_left, len(highs) - self.lookback_right):
            current_high = highs[i]
            
            # Check if current bar is higher than left bars
            is_pivot = True
            for j in range(1, self.lookback_left + 1):
                if highs[i - j] >= current_high:
                    is_pivot = False
                    break
            
            if not is_pivot:
                continue
            
            # Check if current bar is higher than right bars
            for j in range(1, self.lookback_right + 1):
                if highs[i + j] >= current_high:
                    is_pivot = False
                    break
            
            if is_pivot:
                pivots.append({
                    'index': i,
                    'price': current_high,
                    'time': times[i]
                })
        
        return pivots
    
    def are_lows_equal(self, low1: float, low2: float) -> bool:
        """
        Check if two lows are approximately equal within tolerance.
        
        Args:
            low1: First low price
            low2: Second low price
            
        Returns:
            True if lows are within tolerance, False otherwise
        """
        if low1 == 0 or low2 == 0:
            return False
        
        avg_price = (low1 + low2) / 2
        diff_percent = abs(low1 - low2) / avg_price * 100
        
        return diff_percent <= self.equality_tolerance
    
    def detect_double_bottom(self, df: pd.DataFrame) -> Optional[dict]:
        """
        Detect the most recent Double Bottom pattern.
        
        Pattern criteria:
        1. Two pivot lows approximately at the same level
        2. A pivot high (neckline) between them
        3. Second low formed after the neckline
        4. Minimum bars between the two lows
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            Dict with pattern info if found, None otherwise
            {
                'left_low': {'index': int, 'price': float, 'time': datetime},
                'neckline': {'index': int, 'price': float, 'time': datetime},
                'right_low': {'index': int, 'price': float, 'time': datetime},
                'pattern_valid': bool
            }
        """
        try:
            # Find all pivot lows and highs
            pivot_lows = self.find_pivot_lows(df)
            pivot_highs = self.find_pivot_highs(df)
            
            self.logger.debug(f"detect_double_bottom: Found {len(pivot_lows)} lows, {len(pivot_highs)} highs")
            
            if len(pivot_lows) < 2 or len(pivot_highs) < 1:
                self.logger.debug(f"Insufficient pivots: lows={len(pivot_lows)}, highs={len(pivot_highs)}")
                return None
            
            # Search for Double Bottom pattern (start from most recent)
            # Try each combination of two lows
            for i in range(len(pivot_lows) - 1, 0, -1):
                right_low = pivot_lows[i]
                
                for j in range(i - 1, -1, -1):
                    left_low = pivot_lows[j]
                    
                    # Check minimum bars between lows
                    bars_between = right_low['index'] - left_low['index']
                    if bars_between < self.min_bars_between:
                        continue
                    
                    # Check if lows are approximately equal
                    if not self.are_lows_equal(left_low['price'], right_low['price']):
                        continue
                    
                    # Find neckline (pivot high between the two lows)
                    neckline = None
                    for ph in pivot_highs:
                        if left_low['index'] < ph['index'] < right_low['index']:
                            if neckline is None or ph['price'] > neckline['price']:
                                neckline = ph
                    
                    if neckline is None:
                        continue
                    
                    # Valid Double Bottom found
                    pattern = {
                        'left_low': left_low,
                        'neckline': neckline,
                        'right_low': right_low,
                        'pattern_valid': True,
                        'equality_diff_percent': abs(left_low['price'] - right_low['price']) / 
                                                ((left_low['price'] + right_low['price']) / 2) * 100
                    }
                    
                    self.logger.info(f"✓ Double Bottom detected: Left={left_low['price']:.2f}, "
                                   f"Right={right_low['price']:.2f}, Neckline={neckline['price']:.2f}")
                    return pattern
            
            # No valid pattern found
            self.logger.debug(f"No valid Double Bottom pattern found")
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting Double Bottom: {e}")
            return None
    
    def is_breakout_confirmed(self, df: pd.DataFrame, pattern: dict, 
                             current_bar_index: int) -> bool:
        """
        Check if price has broken above the neckline.
        
        Args:
            df: DataFrame with OHLC data
            pattern: Double Bottom pattern dict
            current_bar_index: Index of current bar to check
            
        Returns:
            True if breakout confirmed, False otherwise
        """
        try:
            if pattern is None or not pattern.get('pattern_valid'):
                return False
            
            # Current close must be above neckline
            current_close = df.iloc[current_bar_index]['close']
            neckline_price = pattern['neckline']['price']
            
            # Breakout confirmed if close > neckline
            return current_close > neckline_price
            
        except Exception as e:
            self.logger.error(f"Error checking breakout: {e}")
            return False


if __name__ == "__main__":
    # Simple test with synthetic data
    logging.basicConfig(level=logging.DEBUG)
    
    # Create sample data with a double bottom pattern
    dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
    np.random.seed(42)
    
    # Generate price data with a double bottom
    base_price = 2000
    prices = []
    for i in range(100):
        if i < 20:
            prices.append(base_price + np.random.randn() * 5)
        elif 20 <= i < 30:  # First bottom
            prices.append(base_price - 30 + np.random.randn() * 3)
        elif 30 <= i < 50:  # Rally to neckline
            prices.append(base_price - 10 + np.random.randn() * 5)
        elif 50 <= i < 60:  # Second bottom
            prices.append(base_price - 32 + np.random.randn() * 3)
        else:  # Breakout
            prices.append(base_price + (i - 60) * 2 + np.random.randn() * 5)
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices,
        'high': [p + abs(np.random.randn() * 3) for p in prices],
        'low': [p - abs(np.random.randn() * 3) for p in prices],
        'close': prices,
    })
    
    engine = PatternEngine(lookback_left=3, lookback_right=3, 
                          equality_tolerance=3.0, min_bars_between=15)
    
    pattern = engine.detect_double_bottom(df)
    
    if pattern:
        print("Double Bottom detected!")
        print(f"  Left low: {pattern['left_low']['price']:.2f} at index {pattern['left_low']['index']}")
        print(f"  Neckline: {pattern['neckline']['price']:.2f} at index {pattern['neckline']['index']}")
        print(f"  Right low: {pattern['right_low']['price']:.2f} at index {pattern['right_low']['index']}")
        print(f"  Equality diff: {pattern['equality_diff_percent']:.2f}%")
        
        # Check breakout
        is_breakout = engine.is_breakout_confirmed(df, pattern, len(df) - 1)
        print(f"  Breakout confirmed: {is_breakout}")
    else:
        print("No Double Bottom pattern found")

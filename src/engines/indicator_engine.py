"""
Indicator Engine - Computes technical indicators (EMA, ATR)

This module calculates indicators exactly as TradingView does.
All indicators use bar-close values only (no intrabar calculations).

Pine Script Reference:
- EMA: ta.ema(source, length)
- ATR: ta.atr(length)
"""

import pandas as pd
import numpy as np
from typing import Optional
import logging


class IndicatorEngine:
    """
    Computes technical indicators matching TradingView's implementation.
    
    Indicators:
    - EMA (Exponential Moving Average) - periods 50 and 200
    - ATR (Average True Range) - period 14
    
    All calculations use completed bars only (bar-close logic).
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average.
        
        Pine Script equivalent: ta.ema(source, length)
        
        Args:
            series: Price series (typically close prices)
            period: EMA period
            
        Returns:
            Series with EMA values
        """
        try:
            # pandas ewm matches TradingView's EMA calculation
            # adjust=False ensures consistent behavior with Pine Script
            ema = series.ewm(span=period, adjust=False).mean()
            return ema
        except Exception as e:
            self.logger.error(f"Error calculating EMA({period}): {e}")
            return pd.Series(index=series.index, dtype=float)
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range.
        
        Pine Script equivalent: ta.atr(length)
        
        The True Range is the greatest of:
        1. Current High - Current Low
        2. abs(Current High - Previous Close)
        3. abs(Current Low - Previous Close)
        
        ATR is the EMA of True Range.
        
        Args:
            df: DataFrame with columns: high, low, close
            period: ATR period (default: 14)
            
        Returns:
            Series with ATR values
        """
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            prev_close = close.shift(1)
            
            # Calculate True Range components
            tr1 = high - low
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()
            
            # True Range is the maximum of the three
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # ATR is the EMA of True Range
            atr = tr.ewm(span=period, adjust=False).mean()
            
            return atr
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR({period}): {e}")
            return pd.Series(index=df.index, dtype=float)
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all required indicators and add them to the DataFrame.
        
        Adds columns:
        - ema20: EMA with period 20 (for TP transitions and retrace checks)
        - ema50: EMA with period 50
        - ema200: EMA with period 200
        - atr14: ATR with period 14
        
        Args:
            df: DataFrame with OHLC data (columns: open, high, low, close)
            
        Returns:
            DataFrame with indicator columns added
        """
        try:
            df = df.copy()
            
            # Calculate EMAs on close price
            df['ema20'] = self.calculate_ema(df['close'], period=20)
            df['ema50'] = self.calculate_ema(df['close'], period=50)
            df['ema200'] = self.calculate_ema(df['close'], period=200)
            
            # Calculate ATR
            df['atr14'] = self.calculate_atr(df, period=14)
            
            self.logger.debug(f"Calculated indicators for {len(df)} bars")
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}")
            return df
    
    def get_current_indicators(self, df: pd.DataFrame) -> Optional[dict]:
        """
        Get indicator values for the most recent completed bar.
        
        Args:
            df: DataFrame with indicators already calculated
            
        Returns:
            Dictionary with current indicator values
        """
        try:
            if df is None or len(df) < 2:
                return None
            
            # Get second-to-last bar (latest completed bar)
            latest = df.iloc[-2]
            
            return {
                'time': latest['time'],
                'close': latest['close'],
                'ema50': latest['ema50'],
                'ema200': latest['ema200'],
                'atr14': latest['atr14'],
            }
            
        except Exception as e:
            self.logger.error(f"Error getting current indicators: {e}")
            return None
    
    def is_data_sufficient(self, df: pd.DataFrame) -> bool:
        """
        Check if we have enough data to calculate all indicators.
        
        Need at least 200+ bars for EMA200 to be valid.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            True if sufficient data, False otherwise
        """
        return df is not None and len(df) >= 250  # 200 + buffer


if __name__ == "__main__":
    # Simple test with sample data
    logging.basicConfig(level=logging.DEBUG)
    
    # Create sample data
    dates = pd.date_range(start='2024-01-01', periods=300, freq='H')
    np.random.seed(42)
    prices = 2000 + np.cumsum(np.random.randn(300) * 10)
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices + np.random.randn(300) * 2,
        'high': prices + abs(np.random.randn(300) * 5),
        'low': prices - abs(np.random.randn(300) * 5),
        'close': prices,
    })
    
    engine = IndicatorEngine()
    df = engine.calculate_all_indicators(df)
    
    print("Indicators calculated")
    print(df[['time', 'close', 'ema50', 'ema200', 'atr14']].tail())
    
    current = engine.get_current_indicators(df)
    if current:
        print("\nCurrent indicators:")
        print(f"  Close: {current['close']:.2f}")
        print(f"  EMA50: {current['ema50']:.2f}")
        print(f"  EMA200: {current['ema200']:.2f}")
        print(f"  ATR14: {current['atr14']:.2f}")

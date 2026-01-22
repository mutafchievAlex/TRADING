"""
Recovery Engine - Reconstructs system state after offline period or restart

This module implements Recovery Mode which:
1. Loads last N closed bars from market data
2. Reconstructs strategy state by re-evaluating all conditions
3. Checks if current open positions are still valid
4. Closes positions if strategy would close them
5. Keeps positions if strategy would keep them

This ensures the system is always in a state consistent with the strategy,
regardless of offline periods or unexpected shutdowns.
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json


class RecoveryEngine:
    """
    Manages system recovery after restart or offline period.
    
    Responsibilities:
    - Load historical bars for reconstruction
    - Evaluate strategy conditions on recovered state
    - Validate open positions
    - Close invalid positions
    - Restore system to consistent state
    """
    
    def __init__(self, recovery_bars: int = 50):
        """
        Initialize Recovery Engine.
        
        Args:
            recovery_bars: Number of past bars to load for recovery (default: 50)
        """
        # Ensure enough history to rebuild EMA200 (needs 200 bars + buffer)
        self.recovery_bars = max(recovery_bars, 250)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(
            f"RecoveryEngine initialized with {self.recovery_bars} bars for reconstruction"
        )
    
    def perform_recovery(self, 
                        market_data_service,
                        indicator_engine,
                        pattern_engine,
                        strategy_engine,
                        state_manager,
                        execution_engine,
                        risk_engine=None) -> Dict:
        """
        Perform full system recovery after offline period.
        
        Args:
            market_data_service: Service for fetching market data
            indicator_engine: Engine for calculating indicators
            pattern_engine: Engine for detecting patterns
            strategy_engine: Engine for strategy logic
            state_manager: Manager for system state
            execution_engine: Engine for executing trades
            
        Returns:
            Dict with recovery result:
            {
                'recovery_successful': bool,
                'positions_validated': int,
                'positions_closed': int,
                'recovery_reason': str,
                'timestamp': datetime
            }
        """
        
        result = {
            'recovery_successful': False,
            'positions_validated': 0,
            'positions_closed': 0,
            'recovery_reason': '',
            'closed_positions': [],
            'timestamp': datetime.now()
        }
        
        try:
            self.logger.info("=" * 60)
            self.logger.info("RECOVERY MODE: Starting system reconstruction")
            self.logger.info("=" * 60)
            
            symbol_info = market_data_service.get_symbol_info()

            # Step 1: Load historical data
            self.logger.info(f"Step 1: Loading {self.recovery_bars} historical bars...")
            df = self._load_historical_data(market_data_service)
            
            if df is None or len(df) == 0:
                result['recovery_reason'] = "Failed to load historical data"
                self.logger.error(result['recovery_reason'])
                return result
            
            self.logger.info(f"Loaded {len(df)} bars, latest: {df.iloc[-1]['time']}")
            
            # Step 2: Reconstruct indicators
            self.logger.info("Step 2: Reconstructing indicators...")
            df = self._reconstruct_indicators(df, indicator_engine)
            
            if df is None:
                result['recovery_reason'] = "Failed to reconstruct indicators"
                self.logger.error(result['recovery_reason'])
                return result
            
            self.logger.info("Indicators reconstructed successfully")
            
            # Step 3: Reconstruct pattern state
            self.logger.info("Step 3: Detecting patterns...")
            pattern = self._reconstruct_patterns(df, pattern_engine)
            
            self.logger.info(f"Pattern state reconstructed: {pattern.get('pattern_valid')}")
            
            # Step 4: Validate open positions
            self.logger.info("Step 4: Validating open positions...")
            open_positions = state_manager.get_all_positions()
            
            if open_positions:
                self.logger.info(f"Found {len(open_positions)} open position(s)")
                
                # Check each position
                for position in open_positions:
                    result['positions_validated'] += 1
                    
                    should_be_closed = self._should_position_be_closed(
                        position,
                        df.iloc[-1],  # Current bar
                        pattern,
                        strategy_engine
                    )
                    
                    if should_be_closed['should_close']:
                        # Position should be closed
                        self.logger.warning(
                            f"Position {position['ticket']} should be closed: "
                            f"{should_be_closed['reason']}"
                        )
                        
                        # Close position
                        exit_price = should_be_closed.get('exit_price', df.iloc[-1]['close'])
                        exit_reason = f"Recovery Mode: {should_be_closed['reason']}"
                        
                        closed = self._close_position(
                            position,
                            exit_price,
                            exit_reason,
                            execution_engine,
                            state_manager,
                            symbol_info=symbol_info,
                            risk_engine=risk_engine
                        )
                        
                        if closed:
                            result['positions_closed'] += 1
                            result['closed_positions'].append({
                                'ticket': position['ticket'],
                                'reason': should_be_closed['reason'],
                                'exit_price': exit_price
                            })
                    else:
                        # Position should remain open
                        self.logger.info(
                            f"Position {position['ticket']} validated and will remain open: "
                            f"{should_be_closed['reason']}"
                        )
            else:
                self.logger.info("No open positions to validate")
            
            # Step 5: Summary
            self.logger.info("=" * 60)
            self.logger.info("RECOVERY MODE: Complete")
            self.logger.info(f"Positions validated: {result['positions_validated']}")
            self.logger.info(f"Positions closed: {result['positions_closed']}")
            self.logger.info("=" * 60)
            
            result['recovery_successful'] = True
            result['recovery_reason'] = "Recovery completed successfully"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Recovery failed: {str(e)}")
            result['recovery_reason'] = f"Exception during recovery: {str(e)}"
            return result
    
    def _load_historical_data(self, market_data_service) -> Optional[pd.DataFrame]:
        """
        Load historical OHLC data for recovery.
        
        Args:
            market_data_service: Market data service instance
            
        Returns:
            DataFrame with OHLC data or None if failed
        """
        try:
            # Calculate time range
            end_time = datetime.now()
            # For H1 timeframe, go back recovery_bars hours
            start_time = end_time - timedelta(hours=self.recovery_bars)
            
            # Fetch bars with buffer to satisfy EMA200 even when some bars are missing
            df = market_data_service.get_bars(count=self.recovery_bars + 60)
            
            if df is None or len(df) == 0:
                self.logger.error("Failed to fetch historical data")
                return None
            
            # Ensure we have enough data
            if len(df) < self.recovery_bars:
                self.logger.warning(
                    f"Retrieved {len(df)} bars, requested {self.recovery_bars}"
                )
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading historical data: {e}")
            return None
    
    def _reconstruct_indicators(self, df: pd.DataFrame, indicator_engine) -> Optional[pd.DataFrame]:
        """
        Reconstruct all indicators on historical data.
        
        Args:
            df: DataFrame with OHLC data
            indicator_engine: Indicator engine instance
            
        Returns:
            DataFrame with calculated indicators or None if failed
        """
        try:
            # Calculate indicators
            df = indicator_engine.calculate_all_indicators(df)
            
            if df is None or len(df) == 0:
                self.logger.error("Failed to calculate indicators")
                return None
            
            # Verify indicators are present
            required_indicators = ['ema50', 'ema200', 'atr14']
            for indicator in required_indicators:
                if indicator not in df.columns:
                    self.logger.error(f"Missing indicator: {indicator}")
                    return None
                
                # Check for NaN values in last bar
                if pd.isna(df.iloc[-1][indicator]):
                    self.logger.warning(f"Indicator {indicator} has NaN in last bar")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error reconstructing indicators: {e}")
            return None
    
    def _reconstruct_patterns(self, df: pd.DataFrame, pattern_engine) -> Dict:
        """
        Reconstruct pattern detection on historical data.
        
        Args:
            df: DataFrame with OHLC and indicators
            pattern_engine: Pattern engine instance
            
        Returns:
            Dict with pattern detection result
        """
        try:
            # Detect pattern
            pattern = pattern_engine.detect_double_bottom(df)
            
            if pattern is None:
                return {
                    'pattern_valid': False,
                    'pattern_type': 'NONE',
                    'message': 'No pattern detected during recovery'
                }
            
            self.logger.info(
                f"Pattern detected: {pattern.get('pattern_type', 'UNKNOWN')}, "
                f"Valid: {pattern.get('pattern_valid')}"
            )
            
            return pattern
            
        except Exception as e:
            self.logger.error(f"Error reconstructing pattern: {e}")
            return {'pattern_valid': False}
    
    def _should_position_be_closed(self, 
                                   position: Dict,
                                   current_bar: pd.Series,
                                   pattern: Dict,
                                   strategy_engine) -> Dict:
        """
        Determine if a position should be closed based on current strategy state.
        
        Checks:
        1. Stop Loss hit
        2. Take Profit hit
        
            NOTE: Pattern validity is NOT an exit condition.
            Pattern engine is entry-only, not exit logic.
        
        Args:
            position: Open position data
            current_bar: Current bar with OHLC and indicators
            pattern: Current pattern state
            strategy_engine: Strategy engine instance
            
        Returns:
            Dict with decision:
            {
                'should_close': bool,
                'reason': str,
                'exit_price': float (if should close)
            }
        """
        try:
            entry_price = position['entry_price']
            stop_loss = position['stop_loss']
            take_profit = position['take_profit']
            current_close = current_bar['close']
            
            # Check 1: Stop Loss hit
            if current_close <= stop_loss:
                return {
                    'should_close': True,
                    'reason': f'Stop Loss hit at {current_close:.2f} (SL: {stop_loss:.2f})',
                    'exit_price': stop_loss
                }
            
            # Check 2: Take Profit hit
            if current_close >= take_profit:
                return {
                    'should_close': True,
                    'reason': f'Take Profit hit at {current_close:.2f} (TP: {take_profit:.2f})',
                    'exit_price': take_profit
                }
            
            # Pattern validity is NOT an exit condition after entry
            # Before TP1: Only SL hits can close positions
            # Pattern engine is entry-only, not exit logic
            
            # Position should remain open
            return {
                'should_close': False,
                'reason': f'Position valid: SL={stop_loss:.2f}, TP={take_profit:.2f}, Current={current_close:.2f}'
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluating position closure: {e}")
            # Default to NOT closing (safer)
            return {
                'should_close': False,
                'reason': f'Error in evaluation (keeping position safe): {str(e)}'
            }
    
    def _close_position(self, 
                       position: Dict,
                       exit_price: float,
                       exit_reason: str,
                       execution_engine,
                       state_manager,
                       symbol_info: Optional[Dict] = None,
                       risk_engine=None) -> bool:
        """
        Close a position during recovery.
        
        Args:
            position: Position to close
            exit_price: Exit price
            exit_reason: Reason for closing
            execution_engine: Execution engine instance
            state_manager: State manager instance
            
        Returns:
            True if position closed successfully, False otherwise
        """
        try:
            # Try to close via execution engine
            close_result = execution_engine.close_position(
                ticket=position['ticket'],
                close_price=exit_price
            )
            
            if close_result:
                # Update state
                state_manager.close_position(
                    exit_price=exit_price,
                    exit_reason=exit_reason,
                    ticket=position['ticket'],
                    symbol_info=symbol_info,
                    risk_engine=risk_engine,
                    swap=position.get('swap', 0.0)
                )
                
                self.logger.info(
                    f"Position {position['ticket']} closed during recovery: {exit_reason}"
                )
                return True
            else:
                self.logger.error(
                    f"Failed to close position {position['ticket']} via execution engine"
                )
                # Still mark as closed in state to prevent conflicts
                state_manager.close_position(
                    exit_price=exit_price,
                    exit_reason=f"{exit_reason} (execution failed, state updated)",
                    ticket=position['ticket'],
                    symbol_info=symbol_info,
                    risk_engine=risk_engine,
                    swap=position.get('swap', 0.0)
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error closing position {position.get('ticket')}: {e}")
            return False
    
    def get_recovery_status(self) -> Dict:
        """
        Get current recovery engine status.
        
        Returns:
            Dict with status information
        """
        return {
            'recovery_bars': self.recovery_bars,
            'initialized': True
        }

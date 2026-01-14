"""
Simple backtest script for offline validation

This script allows you to test the strategy on historical data
and compare results with TradingView backtests.
"""

import sys
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from engines.indicator_engine import IndicatorEngine
from engines.pattern_engine import PatternEngine
from engines.strategy_engine import StrategyEngine
from engines.risk_engine import RiskEngine


class Backtester:
    """Simple backtesting engine for strategy validation."""
    
    def __init__(self, initial_equity=10000.0, risk_percent=1.0):
        self.initial_equity = initial_equity
        self.equity = initial_equity
        self.risk_percent = risk_percent
        
        # Initialize engines
        self.indicator_engine = IndicatorEngine()
        self.pattern_engine = PatternEngine()
        self.strategy_engine = StrategyEngine()
        self.risk_engine = RiskEngine(risk_percent=risk_percent)
        
        # Track trades
        self.trades = []
        self.current_position = None
    
    def load_data(self, csv_file: str) -> pd.DataFrame:
        """Load historical data from CSV."""
        print(f"Loading data from {csv_file}...")
        
        df = pd.read_csv(csv_file)
        
        # Convert time column to datetime
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
        elif 'timestamp' in df.columns:
            df['time'] = pd.to_datetime(df['timestamp'])
        else:
            # Create a time index if not present
            df['time'] = pd.date_range(start='2024-01-01', periods=len(df), freq='H')
        
        # Ensure required columns
        required = ['open', 'high', 'low', 'close']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        print(f"Loaded {len(df)} bars")
        return df
    
    def run(self, df: pd.DataFrame):
        """Run backtest on historical data."""
        print("\nRunning backtest...")
        print("=" * 60)
        
        # Calculate indicators
        df = self.indicator_engine.calculate_all_indicators(df)
        
        # Need sufficient data for EMA200
        start_index = 250
        
        # Simulate bar-by-bar
        for i in range(start_index, len(df) - 1):  # -1 because we look at completed bars
            current_time = df.iloc[i]['time']
            
            # Check if we have an open position
            if self.current_position:
                self._check_exit(df, i)
            else:
                self._check_entry(df, i)
        
        # Close any remaining position
        if self.current_position:
            self._force_close(df, len(df) - 1)
        
        self._print_results()
    
    def _check_entry(self, df: pd.DataFrame, bar_index: int):
        """Check for entry signal at given bar."""
        # Get data up to current bar
        historical_df = df.iloc[:bar_index + 1].copy()
        
        # Detect pattern
        pattern = self.pattern_engine.detect_double_bottom(historical_df)
        
        # Evaluate entry
        should_enter, entry_details = self.strategy_engine.evaluate_entry(
            historical_df, pattern, current_bar_index=-1
        )
        
        if should_enter:
            current_bar = historical_df.iloc[-1]
            
            # Calculate position size
            symbol_info = {
                'trade_contract_size': 100.0,
                'volume_min': 0.01,
                'volume_max': 100.0,
                'volume_step': 0.01
            }
            
            position_size = self.risk_engine.calculate_position_size(
                self.equity,
                entry_details['entry_price'],
                entry_details['stop_loss'],
                symbol_info
            )
            
            if position_size:
                self.current_position = {
                    'entry_time': current_bar['time'],
                    'entry_price': entry_details['entry_price'],
                    'stop_loss': entry_details['stop_loss'],
                    'take_profit': entry_details['take_profit'],
                    'volume': position_size,
                    'entry_bar': bar_index
                }
                
                print(f"\n✓ ENTRY: {current_bar['time']}")
                print(f"  Price: {entry_details['entry_price']:.2f}")
                print(f"  SL: {entry_details['stop_loss']:.2f}")
                print(f"  TP: {entry_details['take_profit']:.2f}")
                print(f"  Volume: {position_size:.2f}")
                
                # Update cooldown
                self.strategy_engine.update_last_trade_time(current_bar['time'])
    
    def _check_exit(self, df: pd.DataFrame, bar_index: int):
        """Check for exit conditions."""
        current_bar = df.iloc[bar_index]
        current_price = current_bar['close']
        
        should_exit, reason = self.strategy_engine.evaluate_exit(
            current_price,
            self.current_position['entry_price'],
            self.current_position['stop_loss'],
            self.current_position['take_profit']
        )
        
        if should_exit:
            self._close_position(current_bar, current_price, reason)
    
    def _close_position(self, bar, exit_price: float, reason: str):
        """Close current position."""
        if not self.current_position:
            return
        
        # Calculate P&L
        entry_price = self.current_position['entry_price']
        volume = self.current_position['volume']
        
        price_diff = exit_price - entry_price
        profit = price_diff * volume * 100  # Simplified
        
        # Update equity
        self.equity += profit
        
        # Record trade
        trade = {
            'entry_time': self.current_position['entry_time'],
            'exit_time': bar['time'],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'profit': profit,
            'reason': reason,
            'volume': volume
        }
        self.trades.append(trade)
        
        print(f"\n✗ EXIT: {bar['time']}")
        print(f"  Reason: {reason}")
        print(f"  Exit Price: {exit_price:.2f}")
        print(f"  Profit: ${profit:.2f}")
        print(f"  Equity: ${self.equity:.2f}")
        
        self.current_position = None
    
    def _force_close(self, df: pd.DataFrame, bar_index: int):
        """Force close position at end of backtest."""
        current_bar = df.iloc[bar_index]
        self._close_position(current_bar, current_bar['close'], "End of data")
    
    def _print_results(self):
        """Print backtest results."""
        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        
        if not self.trades:
            print("No trades executed")
            return
        
        total_trades = len(self.trades)
        winners = [t for t in self.trades if t['profit'] > 0]
        losers = [t for t in self.trades if t['profit'] <= 0]
        
        total_profit = sum(t['profit'] for t in self.trades)
        win_rate = len(winners) / total_trades * 100 if total_trades > 0 else 0
        
        avg_win = sum(t['profit'] for t in winners) / len(winners) if winners else 0
        avg_loss = sum(t['profit'] for t in losers) / len(losers) if losers else 0
        
        print(f"\nInitial Equity: ${self.initial_equity:.2f}")
        print(f"Final Equity: ${self.equity:.2f}")
        print(f"Total P/L: ${total_profit:.2f} ({total_profit / self.initial_equity * 100:.2f}%)")
        print(f"\nTotal Trades: {total_trades}")
        print(f"Winners: {len(winners)}")
        print(f"Losers: {len(losers)}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"\nAverage Win: ${avg_win:.2f}")
        print(f"Average Loss: ${avg_loss:.2f}")
        
        if avg_loss != 0:
            profit_factor = abs(sum(t['profit'] for t in winners) / sum(t['profit'] for t in losers))
            print(f"Profit Factor: {profit_factor:.2f}")
        
        # Trade list
        print(f"\n{'Entry Time':<20} {'Exit Time':<20} {'Entry':<10} {'Exit':<10} {'P/L':<12} {'Reason':<15}")
        print("-" * 100)
        for trade in self.trades:
            print(f"{str(trade['entry_time']):<20} {str(trade['exit_time']):<20} "
                  f"{trade['entry_price']:<10.2f} {trade['exit_price']:<10.2f} "
                  f"${trade['profit']:<11.2f} {trade['reason']:<15}")


def main():
    parser = argparse.ArgumentParser(description='Backtest trading strategy on historical data')
    parser.add_argument('--data', required=True, help='Path to CSV file with historical data')
    parser.add_argument('--equity', type=float, default=10000.0, help='Initial equity (default: 10000)')
    parser.add_argument('--risk', type=float, default=1.0, help='Risk percent per trade (default: 1.0)')
    
    args = parser.parse_args()
    
    # Create backtester
    bt = Backtester(initial_equity=args.equity, risk_percent=args.risk)
    
    # Load data
    df = bt.load_data(args.data)
    
    # Run backtest
    bt.run(df)


if __name__ == "__main__":
    main()

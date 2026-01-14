"""Quick test script to verify backtest data loading."""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.config import ConfigManager
from engines.market_data_service import MarketDataService
from engines.backtest_engine import BacktestEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Test backtest data loading."""
    logger.info("="*60)
    logger.info("Testing Backtest Data Loading")
    logger.info("="*60)
    
    # Load config
    config = ConfigManager()
    
    # Get symbol from config
    symbol = config.get("trading.symbol", "XAUUSD")
    logger.info(f"Config symbol: {symbol}")
    
    # Initialize market data service
    market_data = MarketDataService(
        symbol=symbol,
        timeframe="H1",
        config=config
    )
    
    # Connect to MT5
    logger.info("Connecting to MT5...")
    if not market_data.connect():
        logger.error("Failed to connect to MT5")
        return
    
    logger.info(f"MT5 Connected: {market_data.is_connected}")
    logger.info(f"Symbol info: {market_data.symbol_info}")
    
    # Try to get bars
    logger.info("\nFetching 100 bars...")
    df = market_data.get_bars(count=100)
    
    if df is None:
        logger.error("Failed to get bars - returned None")
    else:
        logger.info(f"✅ Got {len(df)} bars")
        logger.info(f"Columns: {df.columns.tolist()}")
        logger.info(f"Time range: {df['time'].min()} to {df['time'].max()}")
        logger.info(f"Last 3 bars:")
        print(df[['time', 'open', 'high', 'low', 'close']].tail(3))
    
    # Test backtest engine
    logger.info("\n" + "="*60)
    logger.info("Testing BacktestEngine")
    logger.info("="*60)
    
    backtest_engine = BacktestEngine(
        symbol=symbol,
        timeframe="H1",
        rolling_days=30,
        warmup_bars=300
    )
    
    logger.info("Loading backtest data...")
    success = backtest_engine.load_historical_data(market_data_service=market_data)
    
    if success:
        logger.info(f"✅ Backtest data loaded: {len(backtest_engine.df)} bars")
        logger.info(f"Time range: {backtest_engine.df['time'].min()} to {backtest_engine.df['time'].max()}")
    else:
        logger.error("❌ Failed to load backtest data")
    
    market_data.disconnect()
    logger.info("\nTest complete")

if __name__ == "__main__":
    main()

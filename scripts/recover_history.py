"""
Recover trade history from MT5 and populate both DB and JSON state.
This script rebuilds the complete trade history after data loss.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import MetaTrader5 as mt5
import logging

sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.storage.state_database import StateDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Recover trade history from MT5."""
    
    # Load config
    config = load_config('config/config.yaml')
    mt5_config = config['mt5']
    
    # Initialize MT5
    if not mt5.initialize(path=mt5_config.get('terminal_path')):
        logger.error(f"MT5 initialize failed: {mt5.last_error()}")
        return
    
    # Login
    if not mt5.login(mt5_config['login'], mt5_config['password'], mt5_config['server']):
        logger.error(f"MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        return
    
    logger.info(f"Connected to MT5: {mt5_config['login']}@{mt5_config['server']}")
    
    try:
        # Load current state
        logger.info("Loading current state...")
        with open('data/state.json') as f:
            current_state = json.load(f)
        
        # Fetch history from MT5
        symbol = mt5_config['symbol']
        logger.info(f"Fetching all closed positions for {symbol}...")
        
        # Get all positions
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            logger.warning("No positions found in MT5")
        else:
            logger.info(f"Found {len(positions)} open positions in MT5")
        
        # Get deal history
        from datetime import timedelta
        from_date = datetime.now() - timedelta(days=365)  # Get 1 year of history
        deals = mt5.history_deals_get(from_date, datetime.now(), symbol=symbol)
        
        if not deals:
            logger.warning("No deals found in history")
        else:
            logger.info(f"Found {len(deals)} deals in history")
            
            # Build completed trades from deals
            position_deals = {}
            for deal in deals:
                pos_id = deal.position_id
                if pos_id not in position_deals:
                    position_deals[pos_id] = []
                position_deals[pos_id].append(deal)
            
            # Extract completed trades (those with both entry and exit)
            logger.info("Processing deals to build trade history...")
            trade_history = []
            
            for pos_id, deals_list in position_deals.items():
                entry_deal = None
                exit_deal = None
                
                for deal in deals_list:
                    if deal.entry == mt5.DEAL_ENTRY_IN:
                        entry_deal = deal
                    elif deal.entry == mt5.DEAL_ENTRY_OUT:
                        exit_deal = deal
                
                # Only add complete trades (with both entry and exit)
                if entry_deal and exit_deal:
                    trade = {
                        'ticket': pos_id,
                        'entry_time': datetime.fromtimestamp(entry_deal.time).isoformat(),
                        'exit_time': datetime.fromtimestamp(exit_deal.time).isoformat(),
                        'entry_price': entry_deal.price,
                        'exit_price': exit_deal.price,
                        'stop_loss': entry_deal.sl if entry_deal.sl > 0 else None,
                        'take_profit': entry_deal.tp if entry_deal.tp > 0 else None,
                        'volume': entry_deal.volume,
                        'gross_pl': exit_deal.profit,
                        'commission': sum(d.commission for d in deals_list),
                        'swap': sum(d.swap for d in deals_list),
                        'profit': sum(d.profit + d.commission + d.swap for d in deals_list if d.entry == mt5.DEAL_ENTRY_OUT),
                        'net_pl': sum(d.profit + d.commission + d.swap for d in deals_list if d.entry == mt5.DEAL_ENTRY_OUT),
                        'exit_reason': 'Recovered from MT5 history',
                        'is_winner': sum(d.profit for d in deals_list if d.entry == mt5.DEAL_ENTRY_OUT) > 0,
                        'pattern_info': None,
                    }
                    trade_history.append(trade)
            
            logger.info(f"Recovered {len(trade_history)} completed trades")
            
            # Update state
            current_state['trade_history'] = trade_history
            current_state['total_trades'] = len(trade_history)
            current_state['winning_trades'] = sum(1 for t in trade_history if t['is_winner'])
            current_state['losing_trades'] = current_state['total_trades'] - current_state['winning_trades']
            current_state['total_profit'] = sum(t['net_pl'] for t in trade_history)
            
            # Update last_trade_time
            if trade_history:
                most_recent = max(trade_history, key=lambda t: t['exit_time'])
                current_state['last_trade_time'] = most_recent['exit_time']
            
            # Save to JSON
            logger.info("Saving recovered history to JSON...")
            with open('data/state.json', 'w') as f:
                json.dump(current_state, f, indent=2)
            
            # Save to database
            logger.info("Saving recovered history to database...")
            db_url = config['data']['db_url']
            db_store = StateDatabase(db_url, logger)
            db_store.save_state(current_state)
            
            logger.info(f"✅ Recovery complete!")
            logger.info(f"  Total trades: {current_state['total_trades']}")
            logger.info(f"  Winners: {current_state['winning_trades']}")
            logger.info(f"  Losers: {current_state['losing_trades']}")
            logger.info(f"  Total profit: ${current_state['total_profit']:.2f}")
        
    finally:
        mt5.shutdown()
        logger.info("MT5 connection closed")


if __name__ == '__main__':
    main()

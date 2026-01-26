#!/usr/bin/env python3
"""
Fetch trade history from MetaTrader 5 and add to database.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import json
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_app_config
from src.storage.state_database import StateDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def connect_mt5(mt5_config: dict) -> bool:
    """Connect to MetaTrader 5."""
    terminal_path = mt5_config.get('terminal_path')
    
    if terminal_path:
        if not mt5.initialize(path=terminal_path):
            logger.error(f"MT5 initialize failed: {mt5.last_error()}")
            return False
    else:
        if not mt5.initialize():
            logger.error(f"MT5 initialize failed: {mt5.last_error()}")
            return False
    
    # Login
    login = mt5_config.get('login')
    password = mt5_config.get('password')
    server = mt5_config.get('server')
    
    if server:
        if not mt5.login(login, password, server):
            logger.error(f"MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False
        logger.info(f"Connected to MT5: {login}@{server}")
    else:
        logger.warning("Server not configured - using default account")
    
    return True


def fetch_closed_trades(symbol: str, days_back: int = 365) -> list:
    """
    Fetch all closed trades from MT5 history.
    
    Returns list of trade dicts with entry and exit info.
    """
    from_date = datetime.now() - timedelta(days=days_back)
    to_date = datetime.now()
    
    logger.info(f"Fetching trades for {symbol} from {from_date.date()} to {to_date.date()}")
    
    # Get all deals in range
    deals = mt5.history_deals_get(from_date, to_date)
    
    if deals is None:
        logger.warning(f"No deals found: {mt5.last_error()}")
        return []
    
    logger.info(f"Retrieved {len(deals)} total deals from MT5")
    
    # Group deals by position ticket to match entry/exit
    trades_map = {}
    
    for deal in deals:
        # Only process buy/sell deals
        if deal.type not in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL):
            continue
        
        # Filter by symbol
        if deal.symbol != symbol:
            continue
        
        ticket = deal.ticket
        pos_id = deal.position_id
        
        # Store deal info
        deal_info = {
            'ticket': ticket,
            'position_id': pos_id,
            'type': 'BUY' if deal.type == mt5.DEAL_TYPE_BUY else 'SELL',
            'entry_type': 'IN' if deal.entry == mt5.DEAL_ENTRY_IN else 'OUT',
            'time': deal.time,
            'price': deal.price,
            'volume': deal.volume,
            'profit': deal.profit,
            'commission': deal.commission,
            'swap': deal.swap,
        }
        
        if pos_id not in trades_map:
            trades_map[pos_id] = []
        
        trades_map[pos_id].append(deal_info)
    
    logger.info(f"Grouped into {len(trades_map)} position(s)")
    
    # Reconstruct trades from entry/exit deals
    trades = []
    
    for pos_id, deals_list in trades_map.items():
        # Sort by time
        deals_list.sort(key=lambda x: x['time'])
        
        # Find entry and exit
        entry_deal = None
        exit_deal = None
        
        for deal in deals_list:
            if deal['entry_type'] == 'IN' and entry_deal is None:
                entry_deal = deal
            elif deal['entry_type'] == 'OUT':
                exit_deal = deal
        
        # Only add closed trades (have both entry and exit)
        if entry_deal and exit_deal:
            trade = {
                'ticket': entry_deal['ticket'],
                'entry_time': datetime.fromtimestamp(entry_deal['time']).isoformat(),
                'exit_time': datetime.fromtimestamp(exit_deal['time']).isoformat(),
                'entry_price': entry_deal['price'],
                'exit_price': exit_deal['price'],
                'volume': entry_deal['volume'],
                'profit': exit_deal['profit'],
                'commission': exit_deal['commission'],
                'swap': exit_deal['swap'],
                'net_pl': exit_deal['profit'] - exit_deal['commission'] + exit_deal['swap'],
                'gross_pl': exit_deal['profit'],
                'exit_reason': 'CLOSED (Historical)',
                'is_winner': 1 if exit_deal['profit'] > 0 else 0,
            }
            trades.append(trade)
    
    logger.info(f"Reconstructed {len(trades)} closed trade(s)")
    return trades


def add_trades_to_database(db: StateDatabase, trades: list) -> None:
    """Add trades to database."""
    if not trades:
        logger.info("No trades to add")
        return
    
    conn = db.connection
    
    for trade in trades:
        try:
            conn.execute("""
                INSERT OR REPLACE INTO trades (
                    ticket, entry_time, exit_time, entry_price, exit_price,
                    stop_loss, take_profit, volume, profit, gross_pl, commission,
                    swap, net_pl, exit_reason, is_winner, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade['ticket'],
                trade['entry_time'],
                trade['exit_time'],
                trade['entry_price'],
                trade['exit_price'],
                0,  # stop_loss unknown
                0,  # take_profit unknown
                trade['volume'],
                trade['profit'],
                trade['gross_pl'],
                trade['commission'],
                trade['swap'],
                trade['net_pl'],
                trade['exit_reason'],
                trade['is_winner'],
                datetime.utcnow().isoformat(),
            ))
        except Exception as e:
            logger.error(f"Failed to insert trade {trade['ticket']}: {e}")
    
    conn.commit()
    logger.info(f"Added {len(trades)} trades to database")


def main():
    """Main function."""
    try:
        # Load config
        config = load_app_config('config/config.yaml')
        config_dict = config.to_dict()
        
        # Get configuration
        mt5_config = config_dict.get('mt5', {})
        symbol = mt5_config.get('symbol', 'GOLD')
        
        # Connect to MT5
        if not connect_mt5(mt5_config):
            logger.error("Failed to connect to MT5")
            return
        
        # Fetch trades from MT5
        trades = fetch_closed_trades(symbol, days_back=365)
        
        if not trades:
            logger.warning("No closed trades found in MT5 history")
            mt5.shutdown()
            return
        
        # Initialize database
        db_url = config_dict.get('data', {}).get('db_url', 'sqlite:///data/state.db')
        db = StateDatabase(db_url=db_url, logger=logger)
        
        # Add trades to database
        add_trades_to_database(db, trades)
        
        # Close database
        db.close()
        
        # Shutdown MT5
        mt5.shutdown()
        
        logger.info("Trade history import complete!")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        mt5.shutdown()
        sys.exit(1)


if __name__ == '__main__':
    main()

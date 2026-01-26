"""
Migrate all MT5 trade history to database.

This script connects to MT5, retrieves all historical deals,
and imports them into the database for complete trade history.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_app_config
from src.storage.state_database import StateDatabase
from src.engines.state_manager import StateManager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def connect_mt5(config: dict) -> bool:
    """Connect to MetaTrader 5."""
    mt5_config = config['mt5']
    
    if not mt5.initialize(path=mt5_config.get('terminal_path')):
        logger.error(f"MT5 initialize failed: {mt5.last_error()}")
        return False
    
    # Login
    login = mt5_config['login']
    password = mt5_config['password']
    server = mt5_config['server']
    
    if not mt5.login(login, password, server):
        logger.error(f"MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        return False
    
    logger.info(f"Connected to MT5: {login}@{server}")
    return True


def get_mt5_history(symbol: str, days_back: int = 365) -> list:
    """
    Get all deals from MT5 history.
    
    Args:
        symbol: Trading symbol (e.g., 'GOLD', 'XAUUSD')
        days_back: Number of days to look back
        
    Returns:
        List of deal dictionaries
    """
    from_date = datetime.now() - timedelta(days=days_back)
    to_date = datetime.now()
    
    # Get deals
    deals = mt5.history_deals_get(from_date, to_date)
    
    if deals is None:
        logger.warning(f"No deals found in history: {mt5.last_error()}")
        return []
    
    logger.info(f"Retrieved {len(deals)} deals from MT5")
    
    # Filter by symbol and organize by position
    positions = {}
    
    for deal in deals:
        # Skip balance operations
        if deal.type not in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL):
            continue
        
        # Filter by symbol
        if deal.symbol != symbol:
            continue
        
        position_id = deal.position_id
        
        if position_id not in positions:
            positions[position_id] = {
                'entry': None,
                'exit': None,
                'deals': []
            }
        
        positions[position_id]['deals'].append(deal)
        
        # Identify entry and exit
        if deal.entry == mt5.DEAL_ENTRY_IN:
            positions[position_id]['entry'] = deal
        elif deal.entry == mt5.DEAL_ENTRY_OUT:
            positions[position_id]['exit'] = deal
    
    # Build trade records
    trades = []
    
    for pos_id, pos_data in positions.items():
        entry = pos_data['entry']
        exit_deal = pos_data['exit']
        
        # Skip incomplete positions
        if not entry or not exit_deal:
            continue
        
        # Determine direction
        direction = 1 if entry.type == mt5.DEAL_TYPE_BUY else -1
        
        # Calculate P&L
        gross_pl = exit_deal.profit
        commission = sum(deal.commission for deal in pos_data['deals'])
        swap = sum(deal.swap for deal in pos_data['deals'])
        net_pl = gross_pl + commission + swap
        
        trade = {
            'ticket': pos_id,
            'entry_time': datetime.fromtimestamp(entry.time).isoformat(),
            'exit_time': datetime.fromtimestamp(exit_deal.time).isoformat(),
            'entry_price': entry.price,
            'exit_price': exit_deal.price,
            'stop_loss': entry.sl if entry.sl > 0 else None,
            'take_profit': entry.tp if entry.tp > 0 else None,
            'volume': entry.volume,
            'profit': net_pl,
            'gross_pl': gross_pl,
            'commission': commission,
            'swap': swap,
            'net_pl': net_pl,
            'exit_reason': _determine_exit_reason(exit_deal, entry),
            'is_winner': net_pl > 0,
            'pattern_info': None,
        }
        
        trades.append(trade)
    
    logger.info(f"Found {len(trades)} completed trades")
    return trades


def _determine_exit_reason(exit_deal, entry_deal) -> str:
    """Determine exit reason from deal data."""
    if exit_deal.reason == mt5.DEAL_REASON_SL:
        return "Stop Loss"
    elif exit_deal.reason == mt5.DEAL_REASON_TP:
        return "Take Profit"
    elif exit_deal.reason == mt5.DEAL_REASON_SO:
        return "Stop Out"
    elif exit_deal.reason == mt5.DEAL_REASON_EXPERT:
        return "EA Exit"
    else:
        return "Manual Close"


def import_trades_to_db(trades: list, db_store: StateDatabase) -> None:
    """
    Import trades into database.
    
    Args:
        trades: List of trade dictionaries
        db_store: Database instance
    """
    logger.info(f"Importing {len(trades)} trades to database...")
    
    # Load current state
    current_state = db_store.load_latest_snapshot()
    
    if not current_state:
        current_state = {
            'open_positions': [],
            'trade_history': [],
            'last_trade_time': None,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'last_regime_state': None,
            'saved_at': datetime.now().isoformat(),
        }
    
    # Get existing ticket numbers to avoid duplicates
    existing_tickets = {t['ticket'] for t in current_state['trade_history']}
    
    # Add new trades
    new_trades = []
    for trade in trades:
        if trade['ticket'] not in existing_tickets:
            new_trades.append(trade)
    
    logger.info(f"Adding {len(new_trades)} new trades (skipping {len(trades) - len(new_trades)} duplicates)")
    
    # Update state
    current_state['trade_history'].extend(new_trades)
    current_state['total_trades'] = len(current_state['trade_history'])
    current_state['winning_trades'] = sum(1 for t in current_state['trade_history'] if t['is_winner'])
    current_state['losing_trades'] = current_state['total_trades'] - current_state['winning_trades']
    current_state['total_profit'] = sum(t['net_pl'] for t in current_state['trade_history'])
    
    # Update last_trade_time to most recent exit
    if current_state['trade_history']:
        most_recent = max(current_state['trade_history'], key=lambda t: t['exit_time'])
        current_state['last_trade_time'] = most_recent['exit_time']
    
    # Save to database
    db_store.save_state(current_state)
    
    logger.info(f"Migration complete!")
    logger.info(f"Total trades: {current_state['total_trades']}")
    logger.info(f"Winners: {current_state['winning_trades']}")
    logger.info(f"Losers: {current_state['losing_trades']}")
    logger.info(f"Total profit: ${current_state['total_profit']:.2f}")


def main():
    """Main migration function."""
    # Load config
    config = load_app_config('config/config.yaml')
    
    # Connect to MT5
    if not connect_mt5(config.to_dict()):
        logger.error("Failed to connect to MT5")
        return
    
    try:
        # Get symbol from config
        symbol = config['mt5']['symbol']
        
        # Get history
        logger.info(f"Fetching history for {symbol}...")
        trades = get_mt5_history(symbol, days_back=365)
        
        if not trades:
            logger.warning("No trades found in MT5 history")
            return
        
        # Connect to database
        db_url = config['data']['db_url']
        db_store = StateDatabase(db_url, logger)
        
        # Import trades
        import_trades_to_db(trades, db_store)
        
        logger.info("✅ Migration completed successfully!")
        
    finally:
        mt5.shutdown()
        logger.info("MT5 connection closed")


if __name__ == '__main__':
    main()

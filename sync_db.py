#!/usr/bin/env python3
"""
Load JSON state into database - synchronize data.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.storage.state_database import StateDatabase
from src.config import load_app_config
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Load JSON state into database."""
    try:
        # Load config
        config = load_app_config('config/config.yaml')
        config_dict = config.to_dict()
        
        # Paths
        db_url = config_dict.get('data', {}).get('db_url', 'sqlite:///data/state.db')
        json_file = Path(config_dict.get('data', {}).get('state_file', 'data/state.json'))
        
        # Load JSON state
        if not json_file.exists():
            logger.error(f"JSON file not found: {json_file}")
            return
        
        with json_file.open('r') as f:
            json_state = json.load(f)
        
        logger.info(f"Loaded JSON state with {len(json_state.get('open_positions', {}))} positions")
        
        # Initialize database
        db = StateDatabase(db_url=db_url, logger=logger)
        
        # Save JSON state to database using the built-in method
        db.save_state(json_state)
        
        logger.info("Successfully saved JSON state to database!")
        logger.info(f"  - Open positions: {len(json_state.get('open_positions', {}))}")
        logger.info(f"  - Trade history: {len(json_state.get('trade_history', []))}")
        logger.info(f"  - Last trade time: {json_state.get('last_trade_time')}")
        
        db.close()
        logger.info("Database sync complete!")
        
    except Exception as e:
        logger.error(f"Failed to sync database: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

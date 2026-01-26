#!/usr/bin/env python3
"""
Initialize database with v2 schema.
"""

import sys
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
    """Initialize database with v2 schema."""
    try:
        # Load config
        config = load_app_config('config/config.yaml')
        
        # Get DB URL from config - check for data section or use default
        config_dict = config.to_dict()
        db_url = config_dict.get('data', {}).get('db_url', 'sqlite:///data/state.db')
        
        # Initialize database
        db = StateDatabase(db_url=db_url, logger=logger)
        logger.info(f"Database initialized at: {db_url}")
        
        # Check if tables exist
        tables = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        
        table_names = [t[0] for t in tables]
        logger.info(f"Tables created: {', '.join(table_names)}")
        
        # Check schema version
        version_result = db.connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
        ).fetchone()
        
        if version_result:
            logger.info(f"Current schema version: {version_result[0]}")
        
        db.close()
        logger.info("Database initialization complete!")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

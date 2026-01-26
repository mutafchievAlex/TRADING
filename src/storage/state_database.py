"""Database-backed persistence for trading state."""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from src.utils.atomic_state_writer import SafeJSONEncoder


@dataclass(frozen=True)
class Migration:
    version: int
    statements: Tuple[str, ...]


class StateDatabase:
    """SQLite-backed state storage with migrations and snapshotting."""

    _migrations: List[Migration] = [
        Migration(
            version=1,
            statements=(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS state_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    data TEXT NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS positions (
                    ticket INTEGER PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """,
            ),
        ),
        Migration(
            version=2,
            statements=(
                """
                DROP TABLE IF EXISTS positions
                """,
                """
                CREATE TABLE positions (
                    ticket INTEGER PRIMARY KEY,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    volume REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    direction INTEGER NOT NULL,
                    atr REAL,
                    tp_state TEXT DEFAULT 'IN_TRADE',
                    tp1_price REAL,
                    tp2_price REAL,
                    tp3_price REAL,
                    current_stop_loss REAL,
                    tp1_reached INTEGER DEFAULT 0,
                    tp2_reached INTEGER DEFAULT 0,
                    post_tp1_decision TEXT DEFAULT 'NOT_REACHED',
                    post_tp2_decision TEXT DEFAULT 'NOT_REACHED',
                    tp1_reached_timestamp TEXT,
                    tp2_reached_timestamp TEXT,
                    bars_held_after_tp1 INTEGER DEFAULT 0,
                    bars_held_after_tp2 INTEGER DEFAULT 0,
                    max_extension_after_tp1 REAL DEFAULT 0.0,
                    max_extension_after_tp2 REAL DEFAULT 0.0,
                    tp1_exit_reason TEXT,
                    tp2_exit_reason TEXT,
                    trailing_sl_level REAL,
                    trailing_sl_enabled INTEGER DEFAULT 0,
                    price_current REAL,
                    profit REAL,
                    swap REAL DEFAULT 0.0,
                    pattern_info TEXT,
                    updated_at TEXT NOT NULL
                )
                """,
                """
                DROP TABLE IF EXISTS trades
                """,
                """
                CREATE TABLE trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    volume REAL NOT NULL,
                    profit REAL NOT NULL,
                    gross_pl REAL NOT NULL,
                    commission REAL DEFAULT 0.0,
                    swap REAL DEFAULT 0.0,
                    net_pl REAL NOT NULL,
                    exit_reason TEXT NOT NULL,
                    is_winner INTEGER NOT NULL,
                    pattern_info TEXT,
                    created_at TEXT NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS trading_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_trade_time TEXT,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0.0,
                    last_regime_state TEXT,
                    saved_at TEXT NOT NULL
                )
                """,
            ),
        ),
    ]

    def __init__(self, db_url: str, logger: logging.Logger):
        self.logger = logger
        self.db_path = self._parse_sqlite_url(db_url)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path.as_posix())
        self.connection.row_factory = sqlite3.Row
        
        # Enable WAL mode for better crash safety and concurrency
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=NORMAL")  # Balance between safety and speed
        self.connection.commit()
        
        self._apply_migrations()

    @staticmethod
    def _parse_sqlite_url(db_url: str) -> Path:
        if not db_url:
            raise ValueError("db_url is required for database storage.")
        if db_url.startswith("sqlite:///"):
            return Path(db_url.replace("sqlite:///", "", 1))
        if db_url.startswith("sqlite://"):
            return Path(db_url.replace("sqlite://", "", 1))
        raise ValueError(f"Unsupported database URL: {db_url}")

    def _apply_migrations(self) -> None:
        with self.connection:
            for migration in self._migrations:
                if self._is_migration_applied(migration.version):
                    continue
                for statement in migration.statements:
                    self.connection.execute(statement)
                self.connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (migration.version, datetime.utcnow().isoformat()),
                )
                self.logger.info("Applied DB migration v%s", migration.version)

    def _is_migration_applied(self, version: int) -> bool:
        try:
            cursor = self.connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                (version,),
            )
            return cursor.fetchone() is not None
        except sqlite3.OperationalError:
            # schema_migrations table doesn't exist yet
            return False

    def has_data(self) -> bool:
        cursor = self.connection.execute("SELECT 1 FROM state_snapshots LIMIT 1")
        if cursor.fetchone() is not None:
            return True
        cursor = self.connection.execute("SELECT 1 FROM positions LIMIT 1")
        if cursor.fetchone() is not None:
            return True
        cursor = self.connection.execute("SELECT 1 FROM trades LIMIT 1")
        return cursor.fetchone() is not None

    def load_latest_snapshot(self) -> Optional[Dict]:
        """Load latest state from database with proper column mapping."""
        # Try to load from structured tables first
        state_data = self._load_from_tables()
        if state_data:
            return state_data
        
        # Fallback to snapshot if no structured data
        cursor = self.connection.execute(
            "SELECT data FROM state_snapshots ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            return None
        return json.loads(row["data"])

    def _load_from_tables(self) -> Optional[Dict]:
        """Load state from structured tables."""
        # Check if trading_state exists
        cursor = self.connection.execute("SELECT * FROM trading_state WHERE id = 1")
        state_row = cursor.fetchone()
        
        if not state_row:
            return None
        
        # Load positions
        positions = []
        cursor = self.connection.execute("SELECT * FROM positions")
        for row in cursor.fetchall():
            pos = {
                'ticket': row['ticket'],
                'entry_price': row['entry_price'],
                'stop_loss': row['stop_loss'],
                'take_profit': row['take_profit'],
                'volume': row['volume'],
                'entry_time': row['entry_time'],
                'direction': row['direction'],
                'atr': row['atr'],
                'tp_state': row['tp_state'],
                'tp1_price': row['tp1_price'],
                'tp2_price': row['tp2_price'],
                'tp3_price': row['tp3_price'],
                'current_stop_loss': row['current_stop_loss'],
                'tp1_reached': bool(row['tp1_reached']),
                'tp2_reached': bool(row['tp2_reached']),
                'post_tp1_decision': row['post_tp1_decision'],
                'post_tp2_decision': row['post_tp2_decision'],
                'tp1_reached_timestamp': row['tp1_reached_timestamp'],
                'tp2_reached_timestamp': row['tp2_reached_timestamp'],
                'bars_held_after_tp1': row['bars_held_after_tp1'],
                'bars_held_after_tp2': row['bars_held_after_tp2'],
                'max_extension_after_tp1': row['max_extension_after_tp1'],
                'max_extension_after_tp2': row['max_extension_after_tp2'],
                'tp1_exit_reason': row['tp1_exit_reason'],
                'tp2_exit_reason': row['tp2_exit_reason'],
                'trailing_sl_level': row['trailing_sl_level'],
                'trailing_sl_enabled': bool(row['trailing_sl_enabled']),
                'price_current': row['price_current'],
                'profit': row['profit'],
                'swap': row['swap'],
                'pattern_info': json.loads(row['pattern_info']) if row['pattern_info'] else None,
            }
            positions.append(pos)
        
        # Load trades
        trades = []
        cursor = self.connection.execute("SELECT * FROM trades ORDER BY id")
        for row in cursor.fetchall():
            trade = {
                'ticket': row['ticket'],
                'entry_time': row['entry_time'],
                'exit_time': row['exit_time'],
                'entry_price': row['entry_price'],
                'exit_price': row['exit_price'],
                'stop_loss': row['stop_loss'],
                'take_profit': row['take_profit'],
                'volume': row['volume'],
                'profit': row['profit'],
                'gross_pl': row['gross_pl'],
                'commission': row['commission'],
                'swap': row['swap'],
                'net_pl': row['net_pl'],
                'exit_reason': row['exit_reason'],
                'is_winner': bool(row['is_winner']),
                'pattern_info': json.loads(row['pattern_info']) if row['pattern_info'] else None,
            }
            trades.append(trade)
        
        # Build state data
        last_regime = state_row['last_regime_state']
        if last_regime:
            last_regime = json.loads(last_regime)
        
        return {
            'open_positions': positions,
            'trade_history': trades,
            'last_trade_time': state_row['last_trade_time'],
            'total_trades': state_row['total_trades'],
            'winning_trades': state_row['winning_trades'],
            'losing_trades': state_row['losing_trades'],
            'total_profit': state_row['total_profit'],
            'last_regime_state': last_regime,
            'saved_at': state_row['saved_at'],
        }

    def save_state(self, state_data: Dict) -> None:
        """Save complete state to database with proper column mapping."""
        now = datetime.utcnow().isoformat()
        
        # Use explicit transaction for atomicity
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            
            # Save positions with full column mapping
            self.connection.execute("DELETE FROM positions")
            self._insert_positions_v2(state_data.get("open_positions", []), now)
            
            # Save trades with full column mapping
            self.connection.execute("DELETE FROM trades")
            self._insert_trades_v2(state_data.get("trade_history", []), now)
            
            # Save trading state metadata
            self.connection.execute("DELETE FROM trading_state")
            self._insert_trading_state(state_data, now)
            
            # Keep snapshot for backup
            self.connection.execute(
                "INSERT INTO state_snapshots (created_at, data) VALUES (?, ?)",
                (now, json.dumps(state_data, cls=SafeJSONEncoder)),
            )
            
            # Commit transaction
            self.connection.commit()
            
        except Exception as e:
            # Rollback on error
            self.connection.rollback()
            self.logger.error(f"Failed to save state to database: {e}")
            raise

    def _insert_trading_state(self, state_data: Dict, now: str) -> None:
        """Insert trading state metadata."""
        last_regime = state_data.get("last_regime_state")
        self.connection.execute(
            """
            INSERT INTO trading_state (
                id, last_trade_time, total_trades, winning_trades, 
                losing_trades, total_profit, last_regime_state, saved_at
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state_data.get("last_trade_time"),
                state_data.get("total_trades", 0),
                state_data.get("winning_trades", 0),
                state_data.get("losing_trades", 0),
                state_data.get("total_profit", 0.0),
                json.dumps(last_regime) if last_regime else None,
                now,
            ),
        )

    def _insert_positions_v2(self, positions: Iterable[Dict], now: str) -> None:
        """Insert positions with proper column mapping."""
        if not positions:
            return
        
        for pos in positions:
            # Handle entry_time conversion
            entry_time = pos.get('entry_time')
            if isinstance(entry_time, datetime):
                entry_time = entry_time.isoformat()
            
            # Handle timestamps
            tp1_ts = pos.get('tp1_reached_timestamp')
            if isinstance(tp1_ts, datetime):
                tp1_ts = tp1_ts.isoformat()
            tp2_ts = pos.get('tp2_reached_timestamp')
            if isinstance(tp2_ts, datetime):
                tp2_ts = tp2_ts.isoformat()
            
            pattern_info = pos.get('pattern_info')
            if pattern_info is not None and not isinstance(pattern_info, str):
                pattern_info = json.dumps(pattern_info, cls=SafeJSONEncoder)
            
            self.connection.execute(
                """
                INSERT INTO positions (
                    ticket, entry_price, stop_loss, take_profit, volume, entry_time,
                    direction, atr, tp_state, tp1_price, tp2_price, tp3_price,
                    current_stop_loss, tp1_reached, tp2_reached, post_tp1_decision,
                    post_tp2_decision, tp1_reached_timestamp, tp2_reached_timestamp,
                    bars_held_after_tp1, bars_held_after_tp2, max_extension_after_tp1,
                    max_extension_after_tp2, tp1_exit_reason, tp2_exit_reason,
                    trailing_sl_level, trailing_sl_enabled, price_current, profit,
                    swap, pattern_info, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pos.get('ticket'),
                    pos.get('entry_price'),
                    pos.get('stop_loss'),
                    pos.get('take_profit'),
                    pos.get('volume'),
                    entry_time,
                    pos.get('direction', 1),
                    pos.get('atr'),
                    pos.get('tp_state', 'IN_TRADE'),
                    pos.get('tp1_price'),
                    pos.get('tp2_price'),
                    pos.get('tp3_price'),
                    pos.get('current_stop_loss'),
                    1 if pos.get('tp1_reached') else 0,
                    1 if pos.get('tp2_reached') else 0,
                    pos.get('post_tp1_decision', 'NOT_REACHED'),
                    pos.get('post_tp2_decision', 'NOT_REACHED'),
                    tp1_ts,
                    tp2_ts,
                    pos.get('bars_held_after_tp1', 0),
                    pos.get('bars_held_after_tp2', 0),
                    pos.get('max_extension_after_tp1', 0.0),
                    pos.get('max_extension_after_tp2', 0.0),
                    pos.get('tp1_exit_reason'),
                    pos.get('tp2_exit_reason'),
                    pos.get('trailing_sl_level'),
                    1 if pos.get('trailing_sl_enabled') else 0,
                    pos.get('price_current'),
                    pos.get('profit'),
                    pos.get('swap', 0.0),
                    pattern_info,
                    now,
                ),
            )

    def _insert_trades_v2(self, trades: Iterable[Dict], now: str) -> None:
        """Insert trades with proper column mapping."""
        if not trades:
            return
        
        for trade in trades:
            pattern_info = trade.get('pattern_info')
            if pattern_info is not None and not isinstance(pattern_info, str):
                pattern_info = json.dumps(pattern_info, cls=SafeJSONEncoder)
            
            self.connection.execute(
                """
                INSERT INTO trades (
                    ticket, entry_time, exit_time, entry_price, exit_price,
                    stop_loss, take_profit, volume, profit, gross_pl, commission,
                    swap, net_pl, exit_reason, is_winner, pattern_info, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.get('ticket'),
                    trade.get('entry_time'),
                    trade.get('exit_time'),
                    trade.get('entry_price'),
                    trade.get('exit_price'),
                    trade.get('stop_loss'),
                    trade.get('take_profit'),
                    trade.get('volume'),
                    trade.get('profit'),
                    trade.get('gross_pl'),
                    trade.get('commission', 0.0),
                    trade.get('swap', 0.0),
                    trade.get('net_pl'),
                    trade.get('exit_reason'),
                    1 if trade.get('is_winner') else 0,
                    pattern_info,
                    now,
                ),
            )
    
    def get_position_by_ticket(self, ticket: int) -> Optional[Dict]:
        """Get specific position by ticket."""
        cursor = self.connection.execute(
            "SELECT * FROM positions WHERE ticket = ?", (ticket,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'ticket': row['ticket'],
            'entry_price': row['entry_price'],
            'stop_loss': row['stop_loss'],
            'take_profit': row['take_profit'],
            'volume': row['volume'],
            'entry_time': row['entry_time'],
            'direction': row['direction'],
            'atr': row['atr'],
            'tp_state': row['tp_state'],
            'tp1_price': row['tp1_price'],
            'tp2_price': row['tp2_price'],
            'tp3_price': row['tp3_price'],
            'current_stop_loss': row['current_stop_loss'],
            'tp1_reached': bool(row['tp1_reached']),
            'tp2_reached': bool(row['tp2_reached']),
            'post_tp1_decision': row['post_tp1_decision'],
            'post_tp2_decision': row['post_tp2_decision'],
            'tp1_reached_timestamp': row['tp1_reached_timestamp'],
            'tp2_reached_timestamp': row['tp2_reached_timestamp'],
            'bars_held_after_tp1': row['bars_held_after_tp1'],
            'bars_held_after_tp2': row['bars_held_after_tp2'],
            'max_extension_after_tp1': row['max_extension_after_tp1'],
            'max_extension_after_tp2': row['max_extension_after_tp2'],
            'tp1_exit_reason': row['tp1_exit_reason'],
            'tp2_exit_reason': row['tp2_exit_reason'],
            'trailing_sl_level': row['trailing_sl_level'],
            'trailing_sl_enabled': bool(row['trailing_sl_enabled']),
            'price_current': row['price_current'],
            'profit': row['profit'],
            'swap': row['swap'],
            'pattern_info': json.loads(row['pattern_info']) if row['pattern_info'] else None,
        }
    
    def update_position(self, ticket: int, updates: Dict) -> bool:
        """Update specific fields of a position by ticket."""
        if not updates:
            return False
        
        # Build dynamic UPDATE query
        fields = []
        values = []
        for key, value in updates.items():
            if key == 'ticket':  # Don't update primary key
                continue
            
            # Handle boolean fields
            if key in ('tp1_reached', 'tp2_reached', 'trailing_sl_enabled'):
                value = 1 if value else 0
            
            # Handle datetime fields
            if isinstance(value, datetime):
                value = value.isoformat()
            
            # Handle pattern_info JSON
            if key == 'pattern_info' and value is not None and not isinstance(value, str):
                value = json.dumps(value, cls=SafeJSONEncoder)
            
            fields.append(f"{key} = ?")
            values.append(value)
        
        if not fields:
            return False
        
        # Add updated_at
        fields.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(ticket)
        
        query = f"UPDATE positions SET {', '.join(fields)} WHERE ticket = ?"
        
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            cursor = self.connection.execute(query, values)
            self.connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Failed to update position {ticket}: {e}")
            return False

    def _insert_positions(self, positions: Iterable[Dict], now: str) -> None:
        """Legacy method - redirects to v2."""
        self._insert_positions_v2(positions, now)

    def _insert_trades(self, trades: Iterable[Dict], now: str) -> None:
        """Legacy method - redirects to v2."""
        self._insert_trades_v2(trades, now)

    def close(self) -> None:
        """Close database connection gracefully."""
        try:
            # Ensure any pending transaction is committed
            try:
                self.connection.commit()
            except sqlite3.Error:
                pass  # May already be committed
            
            self.connection.close()
            self.logger.info("Database connection closed")
        except sqlite3.Error as exc:
            self.logger.warning("Failed to close DB connection: %s", exc)

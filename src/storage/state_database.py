"""Database-backed persistence for trading state."""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


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
    ]

    def __init__(self, db_url: str, logger: logging.Logger):
        self.logger = logger
        self.db_path = self._parse_sqlite_url(db_url)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path.as_posix())
        self.connection.row_factory = sqlite3.Row
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
        cursor = self.connection.execute(
            "SELECT 1 FROM schema_migrations WHERE version = ?",
            (version,),
        )
        return cursor.fetchone() is not None

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
        cursor = self.connection.execute(
            "SELECT data FROM state_snapshots ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            return None
        return json.loads(row["data"])

    def save_state(self, state_data: Dict) -> None:
        now = datetime.utcnow().isoformat()
        with self.connection:
            self.connection.execute("DELETE FROM positions")
            self.connection.execute("DELETE FROM trades")
            self._insert_positions(state_data.get("open_positions", []), now)
            self._insert_trades(state_data.get("trade_history", []), now)
            self.connection.execute(
                "INSERT INTO state_snapshots (created_at, data) VALUES (?, ?)",
                (now, json.dumps(state_data)),
            )

    def _insert_positions(self, positions: Iterable[Dict], now: str) -> None:
        payload = [
            (position.get("ticket"), json.dumps(position), now)
            for position in positions
        ]
        if not payload:
            return
        self.connection.executemany(
            "INSERT INTO positions (ticket, data, updated_at) VALUES (?, ?, ?)",
            payload,
        )

    def _insert_trades(self, trades: Iterable[Dict], now: str) -> None:
        payload = [
            (trade.get("ticket"), json.dumps(trade), now) for trade in trades
        ]
        if not payload:
            return
        self.connection.executemany(
            "INSERT INTO trades (ticket, data, created_at) VALUES (?, ?, ?)",
            payload,
        )

    def close(self) -> None:
        try:
            self.connection.close()
        except sqlite3.Error as exc:
            self.logger.warning("Failed to close DB connection: %s", exc)

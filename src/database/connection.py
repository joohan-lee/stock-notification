"""
SQLite database connection and schema management.
"""

import sqlite3
from pathlib import Path
from typing import Optional


class Database:
    """SQLite database connection manager."""

    def __init__(self, db_path: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file, or ":memory:" for in-memory DB.
        """
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self) -> None:
        """Establish database connection."""
        if self.db_path != ":memory:":
            # Ensure parent directory exists
            path = Path(self.db_path)
            path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        # Enable foreign keys
        self._connection.execute("PRAGMA foreign_keys = ON")

    @property
    def connection(self) -> sqlite3.Connection:
        """Get the database connection."""
        if self._connection is None:
            raise sqlite3.ProgrammingError("Database connection is closed")
        return self._connection

    def initialize(self) -> None:
        """Create database schema if it doesn't exist."""
        cursor = self.connection.cursor()

        # Create symbols table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                exchange TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                discord_webhook_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create user_watchlist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE,
                UNIQUE (user_id, symbol_id)
            )
        """)

        # Create user_rules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rule_type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                symbol_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE
            )
        """)

        # Create alert_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol_id INTEGER NOT NULL,
                rule_type TEXT NOT NULL,
                message TEXT NOT NULL,
                triggered_at TIMESTAMP NOT NULL,
                notified_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbols_ticker ON symbols(ticker)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_watchlist_user ON user_watchlist(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rules_user ON user_rules(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_history_user_symbol
            ON alert_history(user_id, symbol_id, rule_type)
        """)

        self.connection.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

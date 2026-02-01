"""
Repository classes for CRUD operations.
"""

import json
from datetime import datetime, timedelta
from typing import Optional

from .connection import Database
from .models import Symbol, User, UserWatchlist, UserRule, AlertHistory


class SymbolRepository:
    """CRUD operations for symbols."""

    def __init__(self, db: Database):
        self.db = db

    def create(self, symbol: Symbol) -> Symbol:
        """Create a new symbol."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO symbols (ticker, name, type, exchange)
            VALUES (?, ?, ?, ?)
            """,
            (symbol.ticker, symbol.name, symbol.type, symbol.exchange),
        )
        self.db.connection.commit()
        symbol.id = cursor.lastrowid
        return symbol

    def get_by_ticker(self, ticker: str) -> Optional[Symbol]:
        """Get symbol by ticker."""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT * FROM symbols WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_symbol(row)

    def get_by_id(self, symbol_id: int) -> Optional[Symbol]:
        """Get symbol by ID."""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT * FROM symbols WHERE id = ?", (symbol_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_symbol(row)

    def list_all(self) -> list[Symbol]:
        """List all symbols."""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT * FROM symbols ORDER BY ticker")
        return [self._row_to_symbol(row) for row in cursor.fetchall()]

    def list_by_type(self, symbol_type: str) -> list[Symbol]:
        """List symbols by type."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            "SELECT * FROM symbols WHERE type = ? ORDER BY ticker",
            (symbol_type,),
        )
        return [self._row_to_symbol(row) for row in cursor.fetchall()]

    def search(self, query: str) -> list[Symbol]:
        """Search symbols by ticker or name."""
        cursor = self.db.connection.cursor()
        pattern = f"%{query}%"
        cursor.execute(
            """
            SELECT * FROM symbols
            WHERE ticker LIKE ? OR name LIKE ?
            ORDER BY ticker
            """,
            (pattern, pattern),
        )
        return [self._row_to_symbol(row) for row in cursor.fetchall()]

    def upsert(self, symbol: Symbol) -> Symbol:
        """Update existing symbol or create new one."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO symbols (ticker, name, type, exchange)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                name = excluded.name,
                type = excluded.type,
                exchange = excluded.exchange,
                updated_at = CURRENT_TIMESTAMP
            """,
            (symbol.ticker, symbol.name, symbol.type, symbol.exchange),
        )
        self.db.connection.commit()

        # Get the ID (either new or existing)
        return self.get_by_ticker(symbol.ticker)

    def bulk_upsert(self, symbols: list[Symbol]) -> None:
        """Bulk upsert multiple symbols."""
        cursor = self.db.connection.cursor()
        cursor.executemany(
            """
            INSERT INTO symbols (ticker, name, type, exchange)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                name = excluded.name,
                type = excluded.type,
                exchange = excluded.exchange,
                updated_at = CURRENT_TIMESTAMP
            """,
            [(s.ticker, s.name, s.type, s.exchange) for s in symbols],
        )
        self.db.connection.commit()

    def _row_to_symbol(self, row) -> Symbol:
        """Convert database row to Symbol."""
        return Symbol(
            id=row["id"],
            ticker=row["ticker"],
            name=row["name"],
            type=row["type"],
            exchange=row["exchange"],
            updated_at=row["updated_at"],
        )


class UserRepository:
    """CRUD operations for users."""

    def __init__(self, db: Database):
        self.db = db

    def create(self, user: User) -> User:
        """Create a new user."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO users (email, discord_webhook_url)
            VALUES (?, ?)
            """,
            (user.email, user.discord_webhook_url),
        )
        self.db.connection.commit()
        user.id = cursor.lastrowid
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_user(row)

    def update(self, user: User) -> None:
        """Update user details."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            UPDATE users
            SET email = ?, discord_webhook_url = ?
            WHERE id = ?
            """,
            (user.email, user.discord_webhook_url, user.id),
        )
        self.db.connection.commit()

    def delete(self, user_id: int) -> None:
        """Delete user."""
        cursor = self.db.connection.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.db.connection.commit()

    def list_all(self) -> list[User]:
        """List all users."""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT * FROM users ORDER BY id")
        return [self._row_to_user(row) for row in cursor.fetchall()]

    def _row_to_user(self, row) -> User:
        """Convert database row to User."""
        return User(
            id=row["id"],
            email=row["email"],
            discord_webhook_url=row["discord_webhook_url"],
            created_at=row["created_at"],
        )


class WatchlistRepository:
    """CRUD operations for user watchlists."""

    def __init__(self, db: Database):
        self.db = db

    def add(self, user_id: int, symbol_id: int) -> UserWatchlist:
        """Add symbol to user's watchlist."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO user_watchlist (user_id, symbol_id)
            VALUES (?, ?)
            """,
            (user_id, symbol_id),
        )
        self.db.connection.commit()
        return UserWatchlist(
            id=cursor.lastrowid,
            user_id=user_id,
            symbol_id=symbol_id,
        )

    def remove(self, user_id: int, symbol_id: int) -> None:
        """Remove symbol from user's watchlist."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            DELETE FROM user_watchlist
            WHERE user_id = ? AND symbol_id = ?
            """,
            (user_id, symbol_id),
        )
        self.db.connection.commit()

    def get_user_watchlist(self, user_id: int) -> list[Symbol]:
        """Get all symbols in user's watchlist."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            SELECT s.* FROM symbols s
            JOIN user_watchlist w ON s.id = w.symbol_id
            WHERE w.user_id = ?
            ORDER BY s.ticker
            """,
            (user_id,),
        )
        return [
            Symbol(
                id=row["id"],
                ticker=row["ticker"],
                name=row["name"],
                type=row["type"],
                exchange=row["exchange"],
                updated_at=row["updated_at"],
            )
            for row in cursor.fetchall()
        ]

    def is_in_watchlist(self, user_id: int, symbol_id: int) -> bool:
        """Check if symbol is in user's watchlist."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            SELECT 1 FROM user_watchlist
            WHERE user_id = ? AND symbol_id = ?
            """,
            (user_id, symbol_id),
        )
        return cursor.fetchone() is not None


class RuleRepository:
    """CRUD operations for user rules."""

    def __init__(self, db: Database):
        self.db = db

    def create(self, rule: UserRule) -> UserRule:
        """Create a new rule."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO user_rules (user_id, rule_type, parameters, enabled, symbol_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                rule.user_id,
                rule.rule_type,
                json.dumps(rule.parameters),
                1 if rule.enabled else 0,
                rule.symbol_id,
            ),
        )
        self.db.connection.commit()
        rule.id = cursor.lastrowid
        return rule

    def get_by_id(self, rule_id: int) -> Optional[UserRule]:
        """Get rule by ID."""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT * FROM user_rules WHERE id = ?", (rule_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_rule(row)

    def get_user_rules(self, user_id: int) -> list[UserRule]:
        """Get all rules for a user."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            "SELECT * FROM user_rules WHERE user_id = ? ORDER BY id",
            (user_id,),
        )
        return [self._row_to_rule(row) for row in cursor.fetchall()]

    def get_enabled_rules(self, user_id: int) -> list[UserRule]:
        """Get only enabled rules for a user."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            SELECT * FROM user_rules
            WHERE user_id = ? AND enabled = 1
            ORDER BY id
            """,
            (user_id,),
        )
        return [self._row_to_rule(row) for row in cursor.fetchall()]

    def update(self, rule: UserRule) -> None:
        """Update rule parameters."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            UPDATE user_rules
            SET rule_type = ?, parameters = ?, enabled = ?, symbol_id = ?
            WHERE id = ?
            """,
            (
                rule.rule_type,
                json.dumps(rule.parameters),
                1 if rule.enabled else 0,
                rule.symbol_id,
                rule.id,
            ),
        )
        self.db.connection.commit()

    def delete(self, rule_id: int) -> None:
        """Delete a rule."""
        cursor = self.db.connection.cursor()
        cursor.execute("DELETE FROM user_rules WHERE id = ?", (rule_id,))
        self.db.connection.commit()

    def _row_to_rule(self, row) -> UserRule:
        """Convert database row to UserRule."""
        return UserRule(
            id=row["id"],
            user_id=row["user_id"],
            rule_type=row["rule_type"],
            parameters=json.loads(row["parameters"]),
            enabled=bool(row["enabled"]),
            symbol_id=row["symbol_id"],
        )


class AlertHistoryRepository:
    """CRUD operations for alert history."""

    def __init__(self, db: Database):
        self.db = db

    def create(self, alert: AlertHistory) -> AlertHistory:
        """Create a new alert history entry."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO alert_history
            (user_id, symbol_id, rule_type, message, triggered_at, notified_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                alert.user_id,
                alert.symbol_id,
                alert.rule_type,
                alert.message,
                alert.triggered_at.isoformat(),
                alert.notified_at.isoformat() if alert.notified_at else None,
            ),
        )
        self.db.connection.commit()
        alert.id = cursor.lastrowid
        return alert

    def get_by_id(self, alert_id: int) -> Optional[AlertHistory]:
        """Get alert by ID."""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT * FROM alert_history WHERE id = ?", (alert_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_alert(row)

    def mark_notified(self, alert_id: int) -> None:
        """Mark alert as notified."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            UPDATE alert_history
            SET notified_at = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(), alert_id),
        )
        self.db.connection.commit()

    def has_recent_alert(
        self,
        user_id: int,
        symbol_id: int,
        rule_type: str,
        cooldown_hours: int = 24,
    ) -> bool:
        """Check if similar alert was sent recently."""
        cursor = self.db.connection.cursor()
        cutoff = datetime.now() - timedelta(hours=cooldown_hours)
        cursor.execute(
            """
            SELECT 1 FROM alert_history
            WHERE user_id = ?
              AND symbol_id = ?
              AND rule_type = ?
              AND notified_at IS NOT NULL
              AND notified_at > ?
            LIMIT 1
            """,
            (user_id, symbol_id, rule_type, cutoff.isoformat()),
        )
        return cursor.fetchone() is not None

    def get_user_history(
        self, user_id: int, limit: int = 50
    ) -> list[AlertHistory]:
        """Get alert history for a user."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            SELECT * FROM alert_history
            WHERE user_id = ?
            ORDER BY triggered_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return [self._row_to_alert(row) for row in cursor.fetchall()]

    def _row_to_alert(self, row) -> AlertHistory:
        """Convert database row to AlertHistory."""
        return AlertHistory(
            id=row["id"],
            user_id=row["user_id"],
            symbol_id=row["symbol_id"],
            rule_type=row["rule_type"],
            message=row["message"],
            triggered_at=datetime.fromisoformat(row["triggered_at"]),
            notified_at=(
                datetime.fromisoformat(row["notified_at"])
                if row["notified_at"]
                else None
            ),
        )

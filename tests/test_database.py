"""
Database layer tests.
Tests for SQLite connection, schema creation, and CRUD operations.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from src.database.connection import Database
from src.database.models import Symbol, User, UserWatchlist, UserRule, AlertHistory
from src.database.repository import (
    SymbolRepository,
    UserRepository,
    WatchlistRepository,
    RuleRepository,
    AlertHistoryRepository,
)


class TestDatabaseConnection:
    """Test database connection and initialization."""

    def test_create_in_memory_database(self):
        """Should create an in-memory SQLite database."""
        db = Database(":memory:")
        assert db.connection is not None

    def test_create_file_database(self, tmp_path: Path):
        """Should create a file-based SQLite database."""
        db_path = tmp_path / "test.db"
        db = Database(str(db_path))
        assert db_path.exists()

    def test_initialize_schema(self):
        """Should create all required tables on initialization."""
        db = Database(":memory:")
        db.initialize()

        cursor = db.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            "symbols",
            "users",
            "user_watchlist",
            "user_rules",
            "alert_history",
        }
        assert expected_tables.issubset(tables)

    def test_close_connection(self):
        """Should properly close database connection."""
        db = Database(":memory:")
        db.close()
        with pytest.raises(sqlite3.ProgrammingError):
            db.connection.execute("SELECT 1")


class TestSymbolRepository:
    """Test Symbol CRUD operations."""

    @pytest.fixture
    def repo(self):
        """Create a fresh database with symbol repository."""
        db = Database(":memory:")
        db.initialize()
        return SymbolRepository(db)

    def test_create_symbol(self, repo: SymbolRepository):
        """Should create a new symbol."""
        symbol = Symbol(
            ticker="AAPL",
            name="Apple Inc.",
            type="stock",
            exchange="NASDAQ",
        )
        created = repo.create(symbol)

        assert created.id is not None
        assert created.ticker == "AAPL"
        assert created.name == "Apple Inc."

    def test_get_symbol_by_ticker(self, repo: SymbolRepository):
        """Should retrieve symbol by ticker."""
        symbol = Symbol(ticker="MSFT", name="Microsoft Corporation", type="stock", exchange="NASDAQ")
        repo.create(symbol)

        found = repo.get_by_ticker("MSFT")
        assert found is not None
        assert found.name == "Microsoft Corporation"

    def test_get_nonexistent_symbol(self, repo: SymbolRepository):
        """Should return None for nonexistent ticker."""
        found = repo.get_by_ticker("NONEXISTENT")
        assert found is None

    def test_list_all_symbols(self, repo: SymbolRepository):
        """Should list all symbols."""
        symbols = [
            Symbol(ticker="AAPL", name="Apple Inc.", type="stock", exchange="NASDAQ"),
            Symbol(ticker="GOOGL", name="Alphabet Inc.", type="stock", exchange="NASDAQ"),
            Symbol(ticker="SPY", name="SPDR S&P 500 ETF", type="etf", exchange="NYSE"),
        ]
        for s in symbols:
            repo.create(s)

        all_symbols = repo.list_all()
        assert len(all_symbols) == 3

    def test_list_symbols_by_type(self, repo: SymbolRepository):
        """Should filter symbols by type."""
        symbols = [
            Symbol(ticker="AAPL", name="Apple Inc.", type="stock", exchange="NASDAQ"),
            Symbol(ticker="SPY", name="SPDR S&P 500 ETF", type="etf", exchange="NYSE"),
            Symbol(ticker="QQQ", name="Invesco QQQ Trust", type="etf", exchange="NASDAQ"),
        ]
        for s in symbols:
            repo.create(s)

        etfs = repo.list_by_type("etf")
        assert len(etfs) == 2
        assert all(s.type == "etf" for s in etfs)

    def test_search_symbols(self, repo: SymbolRepository):
        """Should search symbols by ticker or name."""
        symbols = [
            Symbol(ticker="AAPL", name="Apple Inc.", type="stock", exchange="NASDAQ"),
            Symbol(ticker="GOOGL", name="Alphabet Inc.", type="stock", exchange="NASDAQ"),
        ]
        for s in symbols:
            repo.create(s)

        results = repo.search("apple")
        assert len(results) == 1
        assert results[0].ticker == "AAPL"

    def test_upsert_symbol(self, repo: SymbolRepository):
        """Should update existing symbol or create new one."""
        symbol = Symbol(ticker="AAPL", name="Apple Inc.", type="stock", exchange="NASDAQ")
        repo.create(symbol)

        updated = Symbol(ticker="AAPL", name="Apple Inc. (Updated)", type="stock", exchange="NASDAQ")
        repo.upsert(updated)

        found = repo.get_by_ticker("AAPL")
        assert found.name == "Apple Inc. (Updated)"

    def test_bulk_upsert_symbols(self, repo: SymbolRepository):
        """Should bulk upsert multiple symbols efficiently."""
        symbols = [
            Symbol(ticker=f"SYM{i}", name=f"Symbol {i}", type="stock", exchange="NYSE")
            for i in range(100)
        ]
        repo.bulk_upsert(symbols)

        all_symbols = repo.list_all()
        assert len(all_symbols) == 100


class TestUserRepository:
    """Test User CRUD operations."""

    @pytest.fixture
    def repo(self):
        """Create a fresh database with user repository."""
        db = Database(":memory:")
        db.initialize()
        return UserRepository(db)

    def test_create_user(self, repo: UserRepository):
        """Should create a new user."""
        user = User(
            email="test@example.com",
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        created = repo.create(user)

        assert created.id is not None
        assert created.email == "test@example.com"

    def test_create_user_without_email(self, repo: UserRepository):
        """Should create user with only Discord webhook."""
        user = User(discord_webhook_url="https://discord.com/api/webhooks/123/abc")
        created = repo.create(user)

        assert created.id is not None
        assert created.email is None

    def test_get_user_by_id(self, repo: UserRepository):
        """Should retrieve user by ID."""
        user = User(email="test@example.com")
        created = repo.create(user)

        found = repo.get_by_id(created.id)
        assert found is not None
        assert found.email == "test@example.com"

    def test_update_user(self, repo: UserRepository):
        """Should update user details."""
        user = User(email="old@example.com")
        created = repo.create(user)

        created.email = "new@example.com"
        created.discord_webhook_url = "https://discord.com/api/webhooks/456/def"
        repo.update(created)

        found = repo.get_by_id(created.id)
        assert found.email == "new@example.com"
        assert found.discord_webhook_url == "https://discord.com/api/webhooks/456/def"

    def test_delete_user(self, repo: UserRepository):
        """Should delete user."""
        user = User(email="delete@example.com")
        created = repo.create(user)

        repo.delete(created.id)
        found = repo.get_by_id(created.id)
        assert found is None

    def test_list_all_users(self, repo: UserRepository):
        """Should list all users."""
        for i in range(3):
            repo.create(User(email=f"user{i}@example.com"))

        users = repo.list_all()
        assert len(users) == 3


class TestWatchlistRepository:
    """Test Watchlist CRUD operations."""

    @pytest.fixture
    def repos(self):
        """Create fresh database with all required repositories."""
        db = Database(":memory:")
        db.initialize()
        return {
            "watchlist": WatchlistRepository(db),
            "user": UserRepository(db),
            "symbol": SymbolRepository(db),
        }

    def test_add_symbol_to_watchlist(self, repos):
        """Should add symbol to user's watchlist."""
        user = repos["user"].create(User(email="test@example.com"))
        symbol = repos["symbol"].create(
            Symbol(ticker="AAPL", name="Apple Inc.", type="stock", exchange="NASDAQ")
        )

        entry = repos["watchlist"].add(user.id, symbol.id)
        assert entry.id is not None
        assert entry.user_id == user.id
        assert entry.symbol_id == symbol.id

    def test_remove_symbol_from_watchlist(self, repos):
        """Should remove symbol from user's watchlist."""
        user = repos["user"].create(User(email="test@example.com"))
        symbol = repos["symbol"].create(
            Symbol(ticker="AAPL", name="Apple Inc.", type="stock", exchange="NASDAQ")
        )
        repos["watchlist"].add(user.id, symbol.id)

        repos["watchlist"].remove(user.id, symbol.id)
        watchlist = repos["watchlist"].get_user_watchlist(user.id)
        assert len(watchlist) == 0

    def test_get_user_watchlist(self, repos):
        """Should get all symbols in user's watchlist."""
        user = repos["user"].create(User(email="test@example.com"))
        symbols = [
            repos["symbol"].create(Symbol(ticker="AAPL", name="Apple", type="stock", exchange="NASDAQ")),
            repos["symbol"].create(Symbol(ticker="GOOGL", name="Google", type="stock", exchange="NASDAQ")),
            repos["symbol"].create(Symbol(ticker="MSFT", name="Microsoft", type="stock", exchange="NASDAQ")),
        ]
        for s in symbols:
            repos["watchlist"].add(user.id, s.id)

        watchlist = repos["watchlist"].get_user_watchlist(user.id)
        assert len(watchlist) == 3
        tickers = {s.ticker for s in watchlist}
        assert tickers == {"AAPL", "GOOGL", "MSFT"}

    def test_check_symbol_in_watchlist(self, repos):
        """Should check if symbol is in user's watchlist."""
        user = repos["user"].create(User(email="test@example.com"))
        symbol = repos["symbol"].create(
            Symbol(ticker="AAPL", name="Apple", type="stock", exchange="NASDAQ")
        )
        repos["watchlist"].add(user.id, symbol.id)

        assert repos["watchlist"].is_in_watchlist(user.id, symbol.id) is True
        assert repos["watchlist"].is_in_watchlist(user.id, 9999) is False

    def test_prevent_duplicate_watchlist_entry(self, repos):
        """Should not allow duplicate entries in watchlist."""
        user = repos["user"].create(User(email="test@example.com"))
        symbol = repos["symbol"].create(
            Symbol(ticker="AAPL", name="Apple", type="stock", exchange="NASDAQ")
        )
        repos["watchlist"].add(user.id, symbol.id)

        with pytest.raises(Exception):  # Should raise IntegrityError or similar
            repos["watchlist"].add(user.id, symbol.id)


class TestRuleRepository:
    """Test Rule CRUD operations."""

    @pytest.fixture
    def repos(self):
        """Create fresh database with required repositories."""
        db = Database(":memory:")
        db.initialize()
        return {
            "rule": RuleRepository(db),
            "user": UserRepository(db),
            "symbol": SymbolRepository(db),
        }

    def test_create_rule(self, repos):
        """Should create a new rule for user."""
        user = repos["user"].create(User(email="test@example.com"))

        rule = UserRule(
            user_id=user.id,
            rule_type="monthly_high_drop",
            parameters={"thresholds": [-5, -10, -15, -20]},
            enabled=True,
        )
        created = repos["rule"].create(rule)

        assert created.id is not None
        assert created.rule_type == "monthly_high_drop"
        assert created.parameters["thresholds"] == [-5, -10, -15, -20]

    def test_create_symbol_specific_rule(self, repos):
        """Should create a rule for specific symbol."""
        user = repos["user"].create(User(email="test@example.com"))
        symbol = repos["symbol"].create(
            Symbol(ticker="AAPL", name="Apple", type="stock", exchange="NASDAQ")
        )

        rule = UserRule(
            user_id=user.id,
            rule_type="custom",
            parameters={"condition": "price < 150"},
            enabled=True,
            symbol_id=symbol.id,
        )
        created = repos["rule"].create(rule)

        assert created.symbol_id == symbol.id

    def test_get_user_rules(self, repos):
        """Should get all rules for a user."""
        user = repos["user"].create(User(email="test@example.com"))

        rules = [
            UserRule(user_id=user.id, rule_type="monthly_high_drop", parameters={"thresholds": [-10]}, enabled=True),
            UserRule(user_id=user.id, rule_type="daily_change", parameters={"threshold": 5}, enabled=True),
            UserRule(user_id=user.id, rule_type="volume_spike", parameters={"multiplier": 3.0}, enabled=False),
        ]
        for r in rules:
            repos["rule"].create(r)

        user_rules = repos["rule"].get_user_rules(user.id)
        assert len(user_rules) == 3

    def test_get_enabled_rules_only(self, repos):
        """Should get only enabled rules."""
        user = repos["user"].create(User(email="test@example.com"))

        rules = [
            UserRule(user_id=user.id, rule_type="monthly_high_drop", parameters={}, enabled=True),
            UserRule(user_id=user.id, rule_type="daily_change", parameters={}, enabled=False),
        ]
        for r in rules:
            repos["rule"].create(r)

        enabled = repos["rule"].get_enabled_rules(user.id)
        assert len(enabled) == 1
        assert enabled[0].rule_type == "monthly_high_drop"

    def test_update_rule(self, repos):
        """Should update rule parameters."""
        user = repos["user"].create(User(email="test@example.com"))
        rule = repos["rule"].create(
            UserRule(user_id=user.id, rule_type="monthly_high_drop", parameters={"thresholds": [-10]}, enabled=True)
        )

        rule.parameters = {"thresholds": [-5, -10, -15]}
        rule.enabled = False
        repos["rule"].update(rule)

        updated = repos["rule"].get_by_id(rule.id)
        assert updated.parameters["thresholds"] == [-5, -10, -15]
        assert updated.enabled is False

    def test_delete_rule(self, repos):
        """Should delete a rule."""
        user = repos["user"].create(User(email="test@example.com"))
        rule = repos["rule"].create(
            UserRule(user_id=user.id, rule_type="monthly_high_drop", parameters={}, enabled=True)
        )

        repos["rule"].delete(rule.id)
        deleted = repos["rule"].get_by_id(rule.id)
        assert deleted is None


class TestAlertHistoryRepository:
    """Test AlertHistory CRUD operations."""

    @pytest.fixture
    def repos(self):
        """Create fresh database with required repositories."""
        db = Database(":memory:")
        db.initialize()
        return {
            "alert": AlertHistoryRepository(db),
            "user": UserRepository(db),
            "symbol": SymbolRepository(db),
        }

    def test_create_alert(self, repos):
        """Should create a new alert history entry."""
        user = repos["user"].create(User(email="test@example.com"))
        symbol = repos["symbol"].create(
            Symbol(ticker="AAPL", name="Apple", type="stock", exchange="NASDAQ")
        )

        alert = AlertHistory(
            user_id=user.id,
            symbol_id=symbol.id,
            rule_type="monthly_high_drop",
            message="AAPL dropped 10% from monthly high",
            triggered_at=datetime.now(),
        )
        created = repos["alert"].create(alert)

        assert created.id is not None
        assert created.notified_at is None

    def test_mark_alert_as_notified(self, repos):
        """Should mark alert as notified."""
        user = repos["user"].create(User(email="test@example.com"))
        symbol = repos["symbol"].create(
            Symbol(ticker="AAPL", name="Apple", type="stock", exchange="NASDAQ")
        )

        alert = repos["alert"].create(
            AlertHistory(
                user_id=user.id,
                symbol_id=symbol.id,
                rule_type="monthly_high_drop",
                message="Test",
                triggered_at=datetime.now(),
            )
        )

        repos["alert"].mark_notified(alert.id)
        updated = repos["alert"].get_by_id(alert.id)
        assert updated.notified_at is not None

    def test_check_recent_alert_exists(self, repos):
        """Should check if similar alert was sent recently (for deduplication)."""
        user = repos["user"].create(User(email="test@example.com"))
        symbol = repos["symbol"].create(
            Symbol(ticker="AAPL", name="Apple", type="stock", exchange="NASDAQ")
        )

        # Create alert from 1 hour ago
        recent_alert = AlertHistory(
            user_id=user.id,
            symbol_id=symbol.id,
            rule_type="monthly_high_drop",
            message="Test",
            triggered_at=datetime.now() - timedelta(hours=1),
            notified_at=datetime.now() - timedelta(hours=1),
        )
        repos["alert"].create(recent_alert)

        # Should find recent alert within 24 hours
        has_recent = repos["alert"].has_recent_alert(
            user_id=user.id,
            symbol_id=symbol.id,
            rule_type="monthly_high_drop",
            cooldown_hours=24,
        )
        assert has_recent is True

        # Should not find for different rule type
        has_recent_other = repos["alert"].has_recent_alert(
            user_id=user.id,
            symbol_id=symbol.id,
            rule_type="daily_change",
            cooldown_hours=24,
        )
        assert has_recent_other is False

    def test_no_recent_alert_after_cooldown(self, repos):
        """Should not find alert after cooldown period."""
        user = repos["user"].create(User(email="test@example.com"))
        symbol = repos["symbol"].create(
            Symbol(ticker="AAPL", name="Apple", type="stock", exchange="NASDAQ")
        )

        # Create alert from 25 hours ago
        old_alert = AlertHistory(
            user_id=user.id,
            symbol_id=symbol.id,
            rule_type="monthly_high_drop",
            message="Test",
            triggered_at=datetime.now() - timedelta(hours=25),
            notified_at=datetime.now() - timedelta(hours=25),
        )
        repos["alert"].create(old_alert)

        has_recent = repos["alert"].has_recent_alert(
            user_id=user.id,
            symbol_id=symbol.id,
            rule_type="monthly_high_drop",
            cooldown_hours=24,
        )
        assert has_recent is False

    def test_get_user_alert_history(self, repos):
        """Should get alert history for a user."""
        user = repos["user"].create(User(email="test@example.com"))
        symbol = repos["symbol"].create(
            Symbol(ticker="AAPL", name="Apple", type="stock", exchange="NASDAQ")
        )

        for i in range(5):
            repos["alert"].create(
                AlertHistory(
                    user_id=user.id,
                    symbol_id=symbol.id,
                    rule_type="monthly_high_drop",
                    message=f"Alert {i}",
                    triggered_at=datetime.now() - timedelta(hours=i),
                )
            )

        history = repos["alert"].get_user_history(user.id, limit=3)
        assert len(history) == 3

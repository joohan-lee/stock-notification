"""
Integration tests.
End-to-end tests for the complete alert flow.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

from src.database.connection import Database
from src.database.repository import (
    SymbolRepository,
    UserRepository,
    WatchlistRepository,
    RuleRepository,
    AlertHistoryRepository,
)
from src.database.models import Symbol, User, UserRule
from src.data.fetcher import StockDataFetcher, StockData, HistoricalData
from src.rules.engine import RuleEngine, AlertSeverity
from src.notifiers.discord import DiscordNotifier
from src.main import ModoApp


class TestFullAlertFlow:
    """Test complete alert flow from data fetch to notification."""

    @pytest.fixture
    def db(self):
        """Create in-memory database with schema."""
        db = Database(":memory:")
        db.initialize()
        return db

    @pytest.fixture
    def repos(self, db):
        """Create all repositories."""
        return {
            "symbol": SymbolRepository(db),
            "user": UserRepository(db),
            "watchlist": WatchlistRepository(db),
            "rule": RuleRepository(db),
            "alert": AlertHistoryRepository(db),
        }

    @pytest.fixture
    def setup_data(self, repos):
        """Set up test data."""
        # Create symbols
        aapl = repos["symbol"].create(
            Symbol(ticker="AAPL", name="Apple Inc.", type="stock", exchange="NASDAQ")
        )
        googl = repos["symbol"].create(
            Symbol(ticker="GOOGL", name="Alphabet Inc.", type="stock", exchange="NASDAQ")
        )

        # Create user
        user = repos["user"].create(
            User(
                email="test@example.com",
                discord_webhook_url="https://discord.com/api/webhooks/123/abc",
            )
        )

        # Add to watchlist
        repos["watchlist"].add(user.id, aapl.id)
        repos["watchlist"].add(user.id, googl.id)

        # Create rules
        repos["rule"].create(
            UserRule(
                user_id=user.id,
                rule_type="monthly_high_drop",
                parameters={"thresholds": [-5, -10, -15]},
                enabled=True,
            )
        )
        repos["rule"].create(
            UserRule(
                user_id=user.id,
                rule_type="daily_change",
                parameters={"threshold": 5, "direction": "both"},
                enabled=True,
            )
        )

        return {"user": user, "symbols": {"AAPL": aapl, "GOOGL": googl}}

    def test_alert_triggered_and_sent(self, db, repos, setup_data):
        """Should trigger and send alert for qualifying condition."""
        # Mock stock data showing 10% drop from monthly high
        mock_current_data = {
            "AAPL": StockData(
                ticker="AAPL",
                current_price=165.00,
                previous_close=170.00,
                open_price=169.00,
                high=171.00,
                low=164.00,
                volume=50_000_000,
                timestamp=datetime.now(),
            ),
            "GOOGL": StockData(
                ticker="GOOGL",
                current_price=140.00,
                previous_close=139.00,
                open_price=139.50,
                high=141.00,
                low=138.50,
                volume=20_000_000,
                timestamp=datetime.now(),
            ),
        }

        mock_historical_data = {
            "AAPL": HistoricalData(
                ticker="AAPL",
                monthly_high=185.00,  # Current 165 = -10.8% drop
                monthly_low=160.00,
                avg_volume_20d=45_000_000,
                prices=[],
                volumes=[],
            ),
            "GOOGL": HistoricalData(
                ticker="GOOGL",
                monthly_high=142.00,  # Current 140 = -1.4% drop (no alert)
                monthly_low=135.00,
                avg_volume_20d=18_000_000,
                prices=[],
                volumes=[],
            ),
        }

        with patch.object(StockDataFetcher, "get_current_data") as mock_current, \
             patch.object(StockDataFetcher, "get_historical_data") as mock_historical, \
             patch("requests.post") as mock_discord:

            mock_current.side_effect = lambda ticker: mock_current_data[ticker]
            mock_historical.side_effect = lambda ticker, **kwargs: mock_historical_data[ticker]
            mock_discord.return_value.status_code = 204
            mock_discord.return_value.ok = True

            # Run the app
            app = ModoApp(db)
            app.run_check()

        # Verify Discord was called for AAPL alert
        assert mock_discord.called
        call_args = mock_discord.call_args
        payload = call_args[1]["json"]

        # Should have embed with AAPL
        assert any("AAPL" in str(embed) for embed in payload.get("embeds", []))

        # Verify alert history was saved
        history = repos["alert"].get_user_history(setup_data["user"].id)
        assert len(history) >= 1
        assert any(h.symbol_id == setup_data["symbols"]["AAPL"].id for h in history)

    def test_no_duplicate_alerts_within_cooldown(self, db, repos, setup_data):
        """Should not send duplicate alerts within cooldown period."""
        # Create existing alert from 1 hour ago
        repos["alert"].create(
            AlertHistory(
                user_id=setup_data["user"].id,
                symbol_id=setup_data["symbols"]["AAPL"].id,
                rule_type="monthly_high_drop",
                message="Previous alert",
                triggered_at=datetime.now() - timedelta(hours=1),
                notified_at=datetime.now() - timedelta(hours=1),
            )
        )

        mock_current_data = {
            "AAPL": StockData(
                ticker="AAPL",
                current_price=165.00,
                previous_close=170.00,
                open_price=169.00,
                high=171.00,
                low=164.00,
                volume=50_000_000,
                timestamp=datetime.now(),
            ),
            "GOOGL": StockData(
                ticker="GOOGL",
                current_price=140.00,
                previous_close=139.00,
                open_price=139.50,
                high=141.00,
                low=138.50,
                volume=20_000_000,
                timestamp=datetime.now(),
            ),
        }

        mock_historical_data = {
            "AAPL": HistoricalData(
                ticker="AAPL",
                monthly_high=185.00,
                monthly_low=160.00,
                avg_volume_20d=45_000_000,
                prices=[],
                volumes=[],
            ),
            "GOOGL": HistoricalData(
                ticker="GOOGL",
                monthly_high=142.00,
                monthly_low=135.00,
                avg_volume_20d=18_000_000,
                prices=[],
                volumes=[],
            ),
        }

        with patch.object(StockDataFetcher, "get_current_data") as mock_current, \
             patch.object(StockDataFetcher, "get_historical_data") as mock_historical, \
             patch("requests.post") as mock_discord:

            mock_current.side_effect = lambda ticker: mock_current_data[ticker]
            mock_historical.side_effect = lambda ticker, **kwargs: mock_historical_data[ticker]
            mock_discord.return_value.status_code = 204
            mock_discord.return_value.ok = True

            app = ModoApp(db, alert_cooldown_hours=24)
            app.run_check()

        # Discord should NOT be called due to cooldown
        # (AAPL already alerted within 24 hours)
        aapl_alerts = [
            call for call in mock_discord.call_args_list
            if "AAPL" in str(call)
        ]
        assert len(aapl_alerts) == 0

    def test_multiple_rules_same_symbol(self, db, repos, setup_data):
        """Should trigger multiple rule types for same symbol."""
        mock_current_data = {
            "AAPL": StockData(
                ticker="AAPL",
                current_price=165.00,
                previous_close=155.00,  # +6.5% daily change
                open_price=156.00,
                high=166.00,
                low=155.00,
                volume=50_000_000,
                timestamp=datetime.now(),
            ),
            "GOOGL": StockData(
                ticker="GOOGL",
                current_price=140.00,
                previous_close=139.00,
                open_price=139.50,
                high=141.00,
                low=138.50,
                volume=20_000_000,
                timestamp=datetime.now(),
            ),
        }

        mock_historical_data = {
            "AAPL": HistoricalData(
                ticker="AAPL",
                monthly_high=185.00,  # -10.8% drop from high
                monthly_low=155.00,
                avg_volume_20d=45_000_000,
                prices=[],
                volumes=[],
            ),
            "GOOGL": HistoricalData(
                ticker="GOOGL",
                monthly_high=142.00,
                monthly_low=135.00,
                avg_volume_20d=18_000_000,
                prices=[],
                volumes=[],
            ),
        }

        with patch.object(StockDataFetcher, "get_current_data") as mock_current, \
             patch.object(StockDataFetcher, "get_historical_data") as mock_historical, \
             patch("requests.post") as mock_discord:

            mock_current.side_effect = lambda ticker: mock_current_data[ticker]
            mock_historical.side_effect = lambda ticker, **kwargs: mock_historical_data[ticker]
            mock_discord.return_value.status_code = 204
            mock_discord.return_value.ok = True

            app = ModoApp(db)
            app.run_check()

        # Should have alerts for both monthly_high_drop AND daily_change for AAPL
        history = repos["alert"].get_user_history(setup_data["user"].id)
        aapl_alerts = [
            h for h in history
            if h.symbol_id == setup_data["symbols"]["AAPL"].id
        ]
        rule_types = {h.rule_type for h in aapl_alerts}

        assert "monthly_high_drop" in rule_types
        assert "daily_change" in rule_types


class TestCLICommands:
    """Test CLI command functionality."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create file-based database."""
        db_path = tmp_path / "test.db"
        db = Database(str(db_path))
        db.initialize()
        return db

    def test_add_user_command(self, db):
        """Should add user via CLI."""
        from src.cli import add_user

        result = add_user(
            db,
            email="test@example.com",
            discord_webhook="https://discord.com/api/webhooks/123/abc",
        )

        assert result.id is not None
        repo = UserRepository(db)
        user = repo.get_by_id(result.id)
        assert user.email == "test@example.com"

    def test_add_to_watchlist_command(self, db):
        """Should add symbols to watchlist via CLI."""
        from src.cli import add_to_watchlist

        # Setup
        symbol_repo = SymbolRepository(db)
        user_repo = UserRepository(db)

        symbol_repo.create(
            Symbol(ticker="AAPL", name="Apple", type="stock", exchange="NASDAQ")
        )
        user = user_repo.create(User(email="test@example.com"))

        # Execute
        result = add_to_watchlist(db, user_id=user.id, tickers=["AAPL"])

        assert result["added"] == ["AAPL"]

        watchlist_repo = WatchlistRepository(db)
        watchlist = watchlist_repo.get_user_watchlist(user.id)
        assert len(watchlist) == 1
        assert watchlist[0].ticker == "AAPL"

    def test_sync_symbols_command(self, db):
        """Should sync symbols from API."""
        from src.cli import sync_symbols

        with patch("src.data.symbols.SymbolSyncer.fetch_all_symbols") as mock_fetch:
            mock_fetch.return_value = [
                Symbol(ticker="AAPL", name="Apple Inc.", type="stock", exchange="NASDAQ"),
                Symbol(ticker="MSFT", name="Microsoft", type="stock", exchange="NASDAQ"),
                Symbol(ticker="SPY", name="SPDR S&P 500", type="etf", exchange="NYSE"),
            ]

            result = sync_symbols(db)

        assert result["synced"] == 3

        symbol_repo = SymbolRepository(db)
        all_symbols = symbol_repo.list_all()
        assert len(all_symbols) == 3

    def test_list_symbols_command(self, db):
        """Should list and search symbols."""
        from src.cli import list_symbols

        symbol_repo = SymbolRepository(db)
        symbol_repo.create(
            Symbol(ticker="AAPL", name="Apple Inc.", type="stock", exchange="NASDAQ")
        )
        symbol_repo.create(
            Symbol(ticker="GOOGL", name="Alphabet Inc.", type="stock", exchange="NASDAQ")
        )

        # Search by name
        results = list_symbols(db, search="apple")
        assert len(results) == 1
        assert results[0].ticker == "AAPL"

        # List all
        all_results = list_symbols(db)
        assert len(all_results) == 2


class TestConfigValidation:
    """Test configuration loading and validation."""

    def test_load_valid_config(self, tmp_path):
        """Should load valid configuration."""
        from src.config import load_config

        config_content = """
database:
  path: "data/modo.db"

data_source:
  provider: yahoo_finance

schedule:
  timezone: "America/New_York"
  alert_check:
    frequency: hourly
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(str(config_file))

        assert config.database.path == "data/modo.db"
        assert config.schedule.timezone == "America/New_York"

    def test_load_config_with_env_vars(self, tmp_path, monkeypatch):
        """Should substitute environment variables."""
        from src.config import load_config

        monkeypatch.setenv("DB_PATH", "/custom/path/modo.db")

        config_content = """
database:
  path: ${DB_PATH}

data_source:
  provider: yahoo_finance

schedule:
  timezone: "America/New_York"
  alert_check:
    frequency: hourly
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(str(config_file))

        assert config.database.path == "/custom/path/modo.db"

    def test_invalid_config_raises_error(self, tmp_path):
        """Should raise error for invalid configuration."""
        from src.config import load_config, ConfigValidationError

        config_content = """
database:
  # Missing required path

schedule:
  timezone: "Invalid/Timezone"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigValidationError):
            load_config(str(config_file))


class TestDatabaseMigration:
    """Test database migration functionality."""

    def test_fresh_database_creates_schema(self, tmp_path):
        """Should create schema on fresh database."""
        db_path = tmp_path / "new.db"
        db = Database(str(db_path))
        db.initialize()

        cursor = db.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "symbols" in tables
        assert "users" in tables
        assert "user_watchlist" in tables
        assert "user_rules" in tables
        assert "alert_history" in tables

    def test_migration_is_idempotent(self, tmp_path):
        """Should safely run migrations multiple times."""
        db_path = tmp_path / "test.db"
        db = Database(str(db_path))

        # Run initialize twice
        db.initialize()
        db.initialize()

        # Should still work
        cursor = db.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "symbols" in tables


# Import AlertHistory for tests
from src.database.models import AlertHistory

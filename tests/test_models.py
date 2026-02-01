"""
Data model tests.
Tests for dataclass models and their validation.
"""

import pytest
from datetime import datetime

from src.database.models import Symbol, User, UserWatchlist, UserRule, AlertHistory


class TestSymbolModel:
    """Test Symbol model."""

    def test_create_symbol(self):
        """Should create a valid symbol."""
        symbol = Symbol(
            ticker="AAPL",
            name="Apple Inc.",
            type="stock",
            exchange="NASDAQ",
        )
        assert symbol.ticker == "AAPL"
        assert symbol.name == "Apple Inc."
        assert symbol.type == "stock"
        assert symbol.exchange == "NASDAQ"
        assert symbol.id is None

    def test_symbol_with_id(self):
        """Should create symbol with ID."""
        symbol = Symbol(
            id=1,
            ticker="AAPL",
            name="Apple Inc.",
            type="stock",
            exchange="NASDAQ",
        )
        assert symbol.id == 1

    def test_symbol_types(self):
        """Should support different symbol types."""
        stock = Symbol(ticker="AAPL", name="Apple", type="stock", exchange="NASDAQ")
        etf = Symbol(ticker="SPY", name="S&P 500 ETF", type="etf", exchange="NYSE")
        index = Symbol(ticker="^GSPC", name="S&P 500", type="index", exchange="INDEX")

        assert stock.type == "stock"
        assert etf.type == "etf"
        assert index.type == "index"


class TestUserModel:
    """Test User model."""

    def test_create_user_with_email(self):
        """Should create user with email."""
        user = User(email="test@example.com")
        assert user.email == "test@example.com"
        assert user.discord_webhook_url is None

    def test_create_user_with_discord(self):
        """Should create user with Discord webhook."""
        user = User(discord_webhook_url="https://discord.com/api/webhooks/123/abc")
        assert user.email is None
        assert user.discord_webhook_url == "https://discord.com/api/webhooks/123/abc"

    def test_create_user_with_both(self):
        """Should create user with both email and Discord."""
        user = User(
            email="test@example.com",
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        assert user.email == "test@example.com"
        assert user.discord_webhook_url is not None

    def test_user_created_at(self):
        """Should have created_at timestamp."""
        user = User(email="test@example.com", created_at=datetime.now())
        assert user.created_at is not None


class TestUserWatchlistModel:
    """Test UserWatchlist model."""

    def test_create_watchlist_entry(self):
        """Should create a watchlist entry."""
        entry = UserWatchlist(user_id=1, symbol_id=10)
        assert entry.user_id == 1
        assert entry.symbol_id == 10
        assert entry.id is None

    def test_watchlist_with_created_at(self):
        """Should have created_at timestamp."""
        entry = UserWatchlist(user_id=1, symbol_id=10, created_at=datetime.now())
        assert entry.created_at is not None


class TestUserRuleModel:
    """Test UserRule model."""

    def test_create_monthly_high_drop_rule(self):
        """Should create monthly high drop rule."""
        rule = UserRule(
            user_id=1,
            rule_type="monthly_high_drop",
            parameters={"thresholds": [-5, -10, -15, -20]},
            enabled=True,
        )
        assert rule.rule_type == "monthly_high_drop"
        assert rule.parameters["thresholds"] == [-5, -10, -15, -20]
        assert rule.enabled is True
        assert rule.symbol_id is None  # Global rule

    def test_create_daily_change_rule(self):
        """Should create daily change rule."""
        rule = UserRule(
            user_id=1,
            rule_type="daily_change",
            parameters={"threshold": 5, "direction": "both"},
            enabled=True,
        )
        assert rule.rule_type == "daily_change"
        assert rule.parameters["threshold"] == 5
        assert rule.parameters["direction"] == "both"

    def test_create_volume_spike_rule(self):
        """Should create volume spike rule."""
        rule = UserRule(
            user_id=1,
            rule_type="volume_spike",
            parameters={"multiplier": 3.0, "average_days": 20},
            enabled=True,
        )
        assert rule.rule_type == "volume_spike"
        assert rule.parameters["multiplier"] == 3.0

    def test_create_custom_rule(self):
        """Should create custom rule with expression."""
        rule = UserRule(
            user_id=1,
            rule_type="custom",
            parameters={"name": "Price target", "condition": "price < 150"},
            enabled=True,
            symbol_id=10,  # Symbol-specific
        )
        assert rule.rule_type == "custom"
        assert rule.parameters["condition"] == "price < 150"
        assert rule.symbol_id == 10

    def test_disabled_rule(self):
        """Should support disabled rules."""
        rule = UserRule(
            user_id=1,
            rule_type="monthly_high_drop",
            parameters={},
            enabled=False,
        )
        assert rule.enabled is False


class TestAlertHistoryModel:
    """Test AlertHistory model."""

    def test_create_alert(self):
        """Should create an alert history entry."""
        alert = AlertHistory(
            user_id=1,
            symbol_id=10,
            rule_type="monthly_high_drop",
            message="AAPL dropped 10% from monthly high. Current: $165.30, High: $184.00",
            triggered_at=datetime.now(),
        )
        assert alert.user_id == 1
        assert alert.symbol_id == 10
        assert alert.rule_type == "monthly_high_drop"
        assert "AAPL" in alert.message
        assert alert.notified_at is None

    def test_alert_with_notified_at(self):
        """Should track when notification was sent."""
        now = datetime.now()
        alert = AlertHistory(
            user_id=1,
            symbol_id=10,
            rule_type="daily_change",
            message="Test alert",
            triggered_at=now,
            notified_at=now,
        )
        assert alert.notified_at is not None

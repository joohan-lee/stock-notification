"""
Main application entry point.
"""

import logging

from dotenv import load_dotenv

load_dotenv()

from src.database.connection import Database
from src.database.models import Symbol, AlertHistory, UserRule
from src.database.repository import (
    UserRepository,
    WatchlistRepository,
    RuleRepository,
    AlertHistoryRepository,
    SymbolRepository,
)
from src.data.fetcher import StockDataFetcher
from src.rules.engine import RuleEngine
from src.notifiers.base import Notifier
from src.notifiers.discord import DiscordNotifier
from src.notifiers.email import EmailNotifier

logger = logging.getLogger(__name__)


class ModoApp:
    """Main Modo application."""

    def __init__(
        self,
        db: Database,
        alert_cooldown_hours: int = 24,
    ):
        """
        Initialize Modo app.

        Args:
            db: Database instance
            alert_cooldown_hours: Hours before same alert can be sent again
        """
        self.db = db
        self.alert_cooldown_hours = alert_cooldown_hours

        # Initialize repositories
        self.user_repo = UserRepository(db)
        self.symbol_repo = SymbolRepository(db)
        self.watchlist_repo = WatchlistRepository(db)
        self.rule_repo = RuleRepository(db)
        self.alert_repo = AlertHistoryRepository(db)

        # Initialize services
        self.fetcher = StockDataFetcher()
        self.rule_engine = RuleEngine()

    def run_check(self) -> None:
        """Run alert check for all users."""
        users = self.user_repo.list_all()

        for user in users:
            try:
                self._check_user(user.id)
            except Exception as e:
                logger.error(f"Error checking user {user.id}: {e}")

    def _check_user(self, user_id: int) -> None:
        """Check alerts for a single user."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return

        # Get user's watchlist
        watchlist = self.watchlist_repo.get_user_watchlist(user_id)
        if not watchlist:
            return

        # Get user's enabled rules
        rules = self.rule_repo.get_enabled_rules(user_id)
        if not rules:
            return

        # Initialize notifiers
        notifiers = []
        if user.discord_webhook_url:
            notifiers.append(DiscordNotifier(webhook_url=user.discord_webhook_url))
        if user.email:
            # Email notifier would need SMTP config
            pass

        if not notifiers:
            return

        # Check each symbol
        for symbol in watchlist:
            self._check_symbol(user_id, symbol, rules, notifiers)

    def _check_symbol(
        self,
        user_id: int,
        symbol: Symbol,
        rules: list[UserRule],
        notifiers: list[Notifier],
    ) -> None:
        """Check alerts for a single symbol."""
        try:
            # Fetch current data
            stock_data = self.fetcher.get_current_data(symbol.ticker)
            historical_data = self.fetcher.get_historical_data(symbol.ticker)

            # Evaluate rules
            alerts = self.rule_engine.evaluate_rules(
                rules, stock_data, historical_data
            )

            # Filter and send alerts
            for alert in alerts:
                # Check cooldown
                if self.alert_repo.has_recent_alert(
                    user_id=user_id,
                    symbol_id=symbol.id,
                    rule_type=alert.rule_type,
                    cooldown_hours=self.alert_cooldown_hours,
                ):
                    continue

                # Save alert to history
                alert_record = AlertHistory(
                    user_id=user_id,
                    symbol_id=symbol.id,
                    rule_type=alert.rule_type,
                    message=alert.message,
                    triggered_at=alert.triggered_at,
                )
                alert_record = self.alert_repo.create(alert_record)

                # Send notifications
                for notifier in notifiers:
                    result = notifier.send(alert)
                    if result.success:
                        self.alert_repo.mark_notified(alert_record.id)

        except Exception as e:
            logger.error(f"Error checking {symbol.ticker}: {e}")

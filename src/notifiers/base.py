"""
Base notifier classes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any

from src.rules.engine import Alert


@dataclass
class NotificationResult:
    """Result of a notification attempt."""

    success: bool
    channel: str
    error: Optional[str] = None


class Notifier(ABC):
    """Abstract base class for notifiers."""

    @abstractmethod
    def send(self, alert: Alert) -> NotificationResult:
        """
        Send a single alert notification.

        Args:
            alert: Alert to send

        Returns:
            NotificationResult indicating success or failure
        """
        pass

    def send_batch(self, alerts: list[Alert]) -> list[NotificationResult]:
        """
        Send multiple alerts.

        Args:
            alerts: List of alerts to send

        Returns:
            List of NotificationResult for each alert
        """
        return [self.send(alert) for alert in alerts]


class NotifierFactory:
    """Factory for creating notifier instances."""

    @staticmethod
    def create(config: dict[str, Any]) -> Notifier:
        """
        Create a notifier from configuration.

        Args:
            config: Notifier configuration dict

        Returns:
            Appropriate Notifier instance

        Raises:
            ValueError: If notifier type is unknown
        """
        notifier_type = config.get("type")

        if notifier_type == "discord":
            from .discord import DiscordNotifier

            return DiscordNotifier(
                webhook_url=config.get("webhook_url", ""),
                mention_on_critical=config.get("mention_on_critical", True),
                include_chart_link=config.get("include_chart_link", True),
            )

        elif notifier_type == "email":
            from .email import EmailNotifier

            return EmailNotifier(
                smtp_host=config.get("smtp_host", ""),
                smtp_port=config.get("smtp_port", 587),
                smtp_user=config.get("smtp_user", ""),
                smtp_password=config.get("smtp_password", ""),
                from_address=config.get("from_address", ""),
                to_addresses=config.get("to_addresses", []),
            )

        else:
            raise ValueError(f"Unknown notifier type: {notifier_type}")

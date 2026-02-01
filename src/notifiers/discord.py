"""
Discord webhook notifier.
"""

import time
from typing import Any

import requests

from src.rules.engine import Alert, AlertSeverity
from .base import Notifier, NotificationResult


class DiscordNotifier(Notifier):
    """Sends notifications via Discord webhook."""

    # Discord embed colors
    COLOR_INFO = 0x3498DB  # Blue
    COLOR_WARNING = 0xFFA500  # Orange
    COLOR_CRITICAL = 0xFF0000  # Red

    def __init__(
        self,
        webhook_url: str,
        mention_on_critical: bool = True,
        include_chart_link: bool = True,
    ):
        """
        Initialize Discord notifier.

        Args:
            webhook_url: Discord webhook URL
            mention_on_critical: Whether to @here on critical alerts
            include_chart_link: Whether to include TradingView chart link
        """
        self.webhook_url = webhook_url
        self.mention_on_critical = mention_on_critical
        self.include_chart_link = include_chart_link

    def send(self, alert: Alert) -> NotificationResult:
        """Send alert to Discord."""
        try:
            payload = self._create_payload(alert)
            response = self._send_webhook(payload)

            if response.ok:
                return NotificationResult(success=True, channel="discord")
            else:
                return NotificationResult(
                    success=False,
                    channel="discord",
                    error=f"HTTP {response.status_code}: {response.text}",
                )

        except requests.exceptions.ConnectionError as e:
            return NotificationResult(
                success=False,
                channel="discord",
                error=f"Connection error: {str(e)}",
            )
        except Exception as e:
            return NotificationResult(
                success=False,
                channel="discord",
                error=str(e),
            )

    def _send_webhook(self, payload: dict[str, Any]) -> requests.Response:
        """Send webhook with rate limit handling."""
        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=10,
        )

        # Handle rate limiting
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "1")
            time.sleep(float(retry_after))
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )

        return response

    def _create_payload(self, alert: Alert) -> dict[str, Any]:
        """Create Discord webhook payload."""
        payload: dict[str, Any] = {
            "embeds": [self._create_embed(alert)],
        }

        # Add @here mention for critical alerts
        if self.mention_on_critical and alert.severity == AlertSeverity.CRITICAL:
            payload["content"] = "@here"

        return payload

    def _create_embed(self, alert: Alert) -> dict[str, Any]:
        """Create Discord embed for alert."""
        color = self._get_color(alert.severity)
        title = self._get_title(alert)

        embed: dict[str, Any] = {
            "title": title,
            "description": alert.message,
            "color": color,
            "fields": [],
            "timestamp": alert.triggered_at.isoformat(),
        }

        # Add price field
        embed["fields"].append({
            "name": "Current Price",
            "value": f"${alert.current_price:.2f}",
            "inline": True,
        })

        # Add rule type field
        embed["fields"].append({
            "name": "Rule",
            "value": alert.rule_type.replace("_", " ").title(),
            "inline": True,
        })

        # Add chart link if enabled
        if self.include_chart_link:
            chart_url = f"https://www.tradingview.com/symbols/{alert.ticker}"
            embed["fields"].append({
                "name": "Chart",
                "value": f"[TradingView]({chart_url})",
                "inline": True,
            })

        return embed

    def _get_color(self, severity: AlertSeverity) -> int:
        """Get embed color based on severity."""
        if severity == AlertSeverity.CRITICAL:
            return self.COLOR_CRITICAL
        elif severity == AlertSeverity.WARNING:
            return self.COLOR_WARNING
        else:
            return self.COLOR_INFO

    def _get_title(self, alert: Alert) -> str:
        """Get embed title based on alert."""
        severity_emoji = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
        }
        emoji = severity_emoji.get(alert.severity, "ℹ️")
        return f"{emoji} {alert.ticker} Alert"

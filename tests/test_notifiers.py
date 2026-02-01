"""
Notifier tests.
Tests for Discord and Email notification delivery.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

from src.notifiers.base import Notifier, NotificationResult
from src.notifiers.discord import DiscordNotifier
from src.notifiers.email import EmailNotifier
from src.rules.engine import Alert, AlertSeverity


class TestNotificationResult:
    """Test NotificationResult model."""

    def test_success_result(self):
        """Should create success result."""
        result = NotificationResult(success=True, channel="discord")
        assert result.success is True
        assert result.channel == "discord"
        assert result.error is None

    def test_failure_result(self):
        """Should create failure result with error."""
        result = NotificationResult(
            success=False, channel="email", error="SMTP connection failed"
        )
        assert result.success is False
        assert result.error == "SMTP connection failed"


class TestDiscordNotifier:
    """Test Discord webhook notifications."""

    @pytest.fixture
    def notifier(self):
        """Create Discord notifier."""
        return DiscordNotifier(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            mention_on_critical=True,
            include_chart_link=True,
        )

    @pytest.fixture
    def sample_alert(self):
        """Create sample alert."""
        return Alert(
            ticker="AAPL",
            rule_type="monthly_high_drop",
            message="AAPL dropped 10% from monthly high. Current: $165.00, High: $183.33",
            severity=AlertSeverity.WARNING,
            current_price=165.00,
            triggered_at=datetime.now(),
            metadata={"threshold": -10, "monthly_high": 183.33},
        )

    def test_send_notification_success(self, notifier: DiscordNotifier, sample_alert):
        """Should send notification successfully."""
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 204
            mock_post.return_value.ok = True

            result = notifier.send(sample_alert)

        assert result.success is True
        assert result.channel == "discord"
        mock_post.assert_called_once()

    def test_send_notification_failure(self, notifier: DiscordNotifier, sample_alert):
        """Should handle notification failure."""
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 400
            mock_post.return_value.ok = False
            mock_post.return_value.text = "Bad Request"

            result = notifier.send(sample_alert)

        assert result.success is False
        assert "400" in result.error or "Bad Request" in result.error

    def test_format_embed_for_warning(self, notifier: DiscordNotifier, sample_alert):
        """Should format embed with correct color for warning."""
        embed = notifier._create_embed(sample_alert)

        assert embed["title"] is not None
        assert "AAPL" in embed["title"]
        assert embed["color"] == 0xFFA500  # Orange for warning
        assert len(embed["fields"]) > 0

    def test_format_embed_for_critical(self, notifier: DiscordNotifier):
        """Should format embed with red color for critical."""
        alert = Alert(
            ticker="AAPL",
            rule_type="monthly_high_drop",
            message="AAPL dropped 20% from monthly high",
            severity=AlertSeverity.CRITICAL,
            current_price=150.00,
            triggered_at=datetime.now(),
            metadata={"threshold": -20},
        )
        embed = notifier._create_embed(alert)

        assert embed["color"] == 0xFF0000  # Red for critical

    def test_format_embed_for_info(self, notifier: DiscordNotifier):
        """Should format embed with blue color for info."""
        alert = Alert(
            ticker="NVDA",
            rule_type="volume_spike",
            message="NVDA volume spike detected",
            severity=AlertSeverity.INFO,
            current_price=480.00,
            triggered_at=datetime.now(),
            metadata={},
        )
        embed = notifier._create_embed(alert)

        assert embed["color"] == 0x3498DB  # Blue for info

    def test_include_chart_link(self, notifier: DiscordNotifier, sample_alert):
        """Should include TradingView chart link when enabled."""
        embed = notifier._create_embed(sample_alert)

        # Check that chart link is in fields or description
        has_chart_link = any(
            "tradingview" in str(field.get("value", "")).lower()
            for field in embed.get("fields", [])
        ) or "tradingview" in embed.get("description", "").lower()

        assert has_chart_link is True

    def test_mention_on_critical(self, notifier: DiscordNotifier):
        """Should include @here mention for critical alerts."""
        alert = Alert(
            ticker="AAPL",
            rule_type="monthly_high_drop",
            message="Critical drop",
            severity=AlertSeverity.CRITICAL,
            current_price=150.00,
            triggered_at=datetime.now(),
            metadata={},
        )

        payload = notifier._create_payload(alert)

        assert "@here" in payload.get("content", "")

    def test_no_mention_on_non_critical(self, notifier: DiscordNotifier, sample_alert):
        """Should not include mention for non-critical alerts."""
        payload = notifier._create_payload(sample_alert)

        assert "@here" not in payload.get("content", "")

    def test_send_multiple_alerts(self, notifier: DiscordNotifier):
        """Should send multiple alerts."""
        alerts = [
            Alert(
                ticker="AAPL",
                rule_type="monthly_high_drop",
                message="Alert 1",
                severity=AlertSeverity.WARNING,
                current_price=165.00,
                triggered_at=datetime.now(),
                metadata={},
            ),
            Alert(
                ticker="GOOGL",
                rule_type="daily_change",
                message="Alert 2",
                severity=AlertSeverity.INFO,
                current_price=140.00,
                triggered_at=datetime.now(),
                metadata={},
            ),
        ]

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 204
            mock_post.return_value.ok = True

            results = notifier.send_batch(alerts)

        assert len(results) == 2
        assert all(r.success for r in results)

    def test_rate_limit_handling(self, notifier: DiscordNotifier, sample_alert):
        """Should handle Discord rate limiting."""
        with patch("requests.post") as mock_post:
            # First call returns rate limit, second succeeds
            rate_limit_response = Mock()
            rate_limit_response.status_code = 429
            rate_limit_response.ok = False
            rate_limit_response.headers = {"Retry-After": "1"}

            success_response = Mock()
            success_response.status_code = 204
            success_response.ok = True

            mock_post.side_effect = [rate_limit_response, success_response]

            with patch("time.sleep"):  # Don't actually sleep
                result = notifier.send(sample_alert)

        # Should retry after rate limit
        assert mock_post.call_count == 2

    def test_network_error_handling(self, notifier: DiscordNotifier, sample_alert):
        """Should handle network errors gracefully."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = ConnectionError("Network unreachable")

            result = notifier.send(sample_alert)

        assert result.success is False
        assert "Network" in result.error or "Connection" in result.error


class TestEmailNotifier:
    """Test Email SMTP notifications."""

    @pytest.fixture
    def notifier(self):
        """Create Email notifier."""
        return EmailNotifier(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="sender@gmail.com",
            smtp_password="app-password",
            from_address="alerts@modo.app",
            to_addresses=["user@example.com"],
        )

    @pytest.fixture
    def sample_alert(self):
        """Create sample alert."""
        return Alert(
            ticker="AAPL",
            rule_type="monthly_high_drop",
            message="AAPL dropped 10% from monthly high. Current: $165.00, High: $183.33",
            severity=AlertSeverity.WARNING,
            current_price=165.00,
            triggered_at=datetime.now(),
            metadata={"threshold": -10, "monthly_high": 183.33},
        )

    def test_send_email_success(self, notifier: EmailNotifier, sample_alert):
        """Should send email successfully."""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            result = notifier.send(sample_alert)

        assert result.success is True
        assert result.channel == "email"
        mock_server.send_message.assert_called_once()

    def test_send_email_failure(self, notifier: EmailNotifier, sample_alert):
        """Should handle SMTP failure."""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.side_effect = Exception("SMTP error")

            result = notifier.send(sample_alert)

        assert result.success is False
        assert "SMTP" in result.error or "error" in result.error.lower()

    def test_email_subject_format(self, notifier: EmailNotifier, sample_alert):
        """Should format email subject correctly."""
        subject = notifier._create_subject(sample_alert)

        assert "AAPL" in subject
        assert "Modo" in subject or "Alert" in subject

    def test_email_body_html(self, notifier: EmailNotifier, sample_alert):
        """Should create HTML email body."""
        body = notifier._create_body(sample_alert)

        assert "<html>" in body or "<div>" in body
        assert "AAPL" in body
        assert "$165.00" in body or "165" in body

    def test_send_to_multiple_recipients(self, sample_alert):
        """Should send to multiple recipients."""
        notifier = EmailNotifier(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="sender@gmail.com",
            smtp_password="app-password",
            from_address="alerts@modo.app",
            to_addresses=["user1@example.com", "user2@example.com"],
        )

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            result = notifier.send(sample_alert)

        # Check message was sent to both recipients
        call_args = mock_server.send_message.call_args
        message = call_args[0][0]
        assert "user1@example.com" in message["To"]
        assert "user2@example.com" in message["To"]

    def test_authentication_failure(self, notifier: EmailNotifier, sample_alert):
        """Should handle authentication failure."""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.login.side_effect = Exception("Authentication failed")
            mock_smtp.return_value.__enter__.return_value = mock_server

            result = notifier.send(sample_alert)

        assert result.success is False
        assert "Authentication" in result.error or "failed" in result.error.lower()

    def test_tls_connection(self, notifier: EmailNotifier, sample_alert):
        """Should use TLS for secure connection."""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            notifier.send(sample_alert)

        mock_server.starttls.assert_called_once()


class TestNotifierFactory:
    """Test notifier creation and management."""

    def test_create_discord_notifier(self):
        """Should create Discord notifier from config."""
        from src.notifiers.base import NotifierFactory

        config = {
            "type": "discord",
            "webhook_url": "https://discord.com/api/webhooks/123/abc",
            "mention_on_critical": True,
        }
        notifier = NotifierFactory.create(config)

        assert isinstance(notifier, DiscordNotifier)

    def test_create_email_notifier(self):
        """Should create Email notifier from config."""
        from src.notifiers.base import NotifierFactory

        config = {
            "type": "email",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "user@gmail.com",
            "smtp_password": "password",
            "from_address": "alerts@example.com",
            "to_addresses": ["recipient@example.com"],
        }
        notifier = NotifierFactory.create(config)

        assert isinstance(notifier, EmailNotifier)

    def test_invalid_notifier_type(self):
        """Should raise error for invalid notifier type."""
        from src.notifiers.base import NotifierFactory

        config = {"type": "unknown"}

        with pytest.raises(ValueError, match="Unknown notifier type"):
            NotifierFactory.create(config)

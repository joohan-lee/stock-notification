"""
Email SMTP notifier.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.rules.engine import Alert, AlertSeverity
from .base import Notifier, NotificationResult


class EmailNotifier(Notifier):
    """Sends notifications via email SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_address: str,
        to_addresses: list[str],
    ):
        """
        Initialize email notifier.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_address: Sender email address
            to_addresses: List of recipient email addresses
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_address = from_address
        self.to_addresses = to_addresses

    def send(self, alert: Alert) -> NotificationResult:
        """Send alert via email."""
        try:
            message = self._create_message(alert)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)

            return NotificationResult(success=True, channel="email")

        except smtplib.SMTPAuthenticationError as e:
            return NotificationResult(
                success=False,
                channel="email",
                error=f"Authentication failed: {str(e)}",
            )
        except Exception as e:
            return NotificationResult(
                success=False,
                channel="email",
                error=f"SMTP error: {str(e)}",
            )

    def _create_message(self, alert: Alert) -> MIMEMultipart:
        """Create email message."""
        message = MIMEMultipart("alternative")
        message["Subject"] = self._create_subject(alert)
        message["From"] = self.from_address
        message["To"] = ", ".join(self.to_addresses)

        # Plain text version
        text_body = self._create_text_body(alert)
        message.attach(MIMEText(text_body, "plain"))

        # HTML version
        html_body = self._create_body(alert)
        message.attach(MIMEText(html_body, "html"))

        return message

    def _create_subject(self, alert: Alert) -> str:
        """Create email subject."""
        severity_prefix = {
            AlertSeverity.INFO: "[Info]",
            AlertSeverity.WARNING: "[Warning]",
            AlertSeverity.CRITICAL: "[CRITICAL]",
        }
        prefix = severity_prefix.get(alert.severity, "[Alert]")
        return f"{prefix} Modo Alert: {alert.ticker}"

    def _create_text_body(self, alert: Alert) -> str:
        """Create plain text email body."""
        return f"""
Modo Stock Alert

Ticker: {alert.ticker}
Rule: {alert.rule_type.replace("_", " ").title()}
Price: ${alert.current_price:.2f}

{alert.message}

Time: {alert.triggered_at.strftime("%Y-%m-%d %H:%M:%S")}
"""

    def _create_body(self, alert: Alert) -> str:
        """Create HTML email body."""
        severity_color = {
            AlertSeverity.INFO: "#3498DB",
            AlertSeverity.WARNING: "#FFA500",
            AlertSeverity.CRITICAL: "#FF0000",
        }
        color = severity_color.get(alert.severity, "#3498DB")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        .alert-box {{
            border-left: 4px solid {color};
            padding: 15px;
            background-color: #f9f9f9;
            margin-bottom: 20px;
        }}
        .ticker {{ font-size: 24px; font-weight: bold; color: {color}; }}
        .price {{ font-size: 18px; color: #333; }}
        .message {{ margin: 15px 0; color: #555; }}
        .meta {{ color: #888; font-size: 12px; }}
        .chart-link {{ margin-top: 15px; }}
        .chart-link a {{ color: {color}; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="alert-box">
        <div class="ticker">{alert.ticker}</div>
        <div class="price">Current Price: ${alert.current_price:.2f}</div>
        <div class="message">{alert.message}</div>
        <div class="meta">
            Rule: {alert.rule_type.replace("_", " ").title()}<br>
            Time: {alert.triggered_at.strftime("%Y-%m-%d %H:%M:%S")}
        </div>
        <div class="chart-link">
            <a href="https://www.tradingview.com/symbols/{alert.ticker}">
                View Chart on TradingView →
            </a>
        </div>
    </div>
</body>
</html>
"""

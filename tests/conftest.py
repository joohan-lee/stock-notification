"""
Pytest configuration and shared fixtures.
"""

import pytest
from pathlib import Path


@pytest.fixture
def sample_stock_info():
    """Sample Yahoo Finance stock info response."""
    return {
        "regularMarketPrice": 175.50,
        "previousClose": 173.25,
        "open": 174.00,
        "dayHigh": 176.00,
        "dayLow": 173.50,
        "volume": 50_000_000,
        "marketCap": 2_800_000_000_000,
        "shortName": "Apple Inc.",
        "exchange": "NASDAQ",
    }


@pytest.fixture
def sample_discord_webhook_url():
    """Sample Discord webhook URL for testing."""
    return "https://discord.com/api/webhooks/123456789/abcdefghijklmnop"


@pytest.fixture
def sample_smtp_config():
    """Sample SMTP configuration for testing."""
    return {
        "host": "smtp.gmail.com",
        "port": 587,
        "user": "test@gmail.com",
        "password": "test-app-password",
        "from_address": "alerts@modo.app",
        "to_addresses": ["recipient@example.com"],
    }

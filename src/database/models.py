"""
Data models for Modo application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any


@dataclass
class Symbol:
    """Stock/ETF symbol."""

    ticker: str
    name: str
    type: str  # "stock", "etf", "index"
    exchange: str
    id: Optional[int] = None
    updated_at: Optional[datetime] = None


@dataclass
class User:
    """User with notification settings."""

    id: Optional[int] = None
    email: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class UserWatchlist:
    """Junction table for user's monitored symbols."""

    user_id: int
    symbol_id: int
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class UserRule:
    """User's alert rule configuration."""

    user_id: int
    rule_type: str  # "monthly_high_drop", "daily_change", "volume_spike", "custom"
    parameters: dict[str, Any]
    enabled: bool = True
    id: Optional[int] = None
    symbol_id: Optional[int] = None  # None = global rule, set = symbol-specific


@dataclass
class AlertHistory:
    """Record of sent alerts for deduplication."""

    user_id: int
    symbol_id: int
    rule_type: str
    message: str
    triggered_at: datetime
    id: Optional[int] = None
    notified_at: Optional[datetime] = None

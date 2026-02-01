"""
Configuration loading and validation.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


class ConfigValidationError(Exception):
    """Raised when configuration is invalid."""

    pass


@dataclass
class DatabaseConfig:
    """Database configuration."""

    path: str = "data/modo.db"


@dataclass
class SymbolSyncConfig:
    """Symbol sync configuration."""

    enabled: bool = True
    frequency: str = "daily"
    exchanges: list[str] = field(default_factory=lambda: ["NYSE", "NASDAQ"])


@dataclass
class DataSourceConfig:
    """Data source configuration."""

    provider: str = "yahoo_finance"
    symbol_sync: SymbolSyncConfig = field(default_factory=SymbolSyncConfig)


@dataclass
class AlertCheckConfig:
    """Alert check schedule configuration."""

    frequency: str = "hourly"
    cron: Optional[str] = None


@dataclass
class ScheduleConfig:
    """Schedule configuration."""

    timezone: str = "America/New_York"
    alert_check: AlertCheckConfig = field(default_factory=AlertCheckConfig)
    market_hours_only: bool = False


@dataclass
class DiscordNotificationConfig:
    """Discord notification settings."""

    mention_on_critical: bool = True
    include_chart_link: bool = True


@dataclass
class EmailNotificationConfig:
    """Email notification settings."""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587


@dataclass
class NotificationsConfig:
    """Notifications configuration."""

    discord: DiscordNotificationConfig = field(
        default_factory=DiscordNotificationConfig
    )
    email: EmailNotificationConfig = field(default_factory=EmailNotificationConfig)


@dataclass
class AdvancedConfig:
    """Advanced configuration."""

    log_level: str = "INFO"
    alert_cooldown_hours: int = 24
    max_retries: int = 3
    retry_delay_seconds: int = 5


@dataclass
class AppConfig:
    """Main application configuration."""

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    data_source: DataSourceConfig = field(default_factory=DataSourceConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    advanced: AdvancedConfig = field(default_factory=AdvancedConfig)


def _substitute_env_vars(value: Any) -> Any:
    """Substitute environment variables in string values."""
    if isinstance(value, str):
        # Match ${VAR_NAME} pattern
        pattern = r"\$\{([^}]+)\}"
        matches = re.findall(pattern, value)
        for var_name in matches:
            env_value = os.environ.get(var_name, "")
            value = value.replace(f"${{{var_name}}}", env_value)
        return value
    elif isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    return value


def _validate_timezone(timezone: str) -> None:
    """Validate timezone string."""
    # Basic validation - just check it's not empty
    # Full validation would require pytz or zoneinfo
    if not timezone:
        raise ConfigValidationError("Timezone cannot be empty")


def _validate_config(config_dict: dict[str, Any]) -> None:
    """Validate configuration values."""
    # Check database path is provided
    db_config = config_dict.get("database") or {}
    db_path = db_config.get("path")
    if not db_path:
        raise ConfigValidationError("Database path is required")

    path = Path(db_path)
    parent = path.parent
    if parent.exists() and not os.access(parent, os.W_OK):
        raise ConfigValidationError(f"Database path not writable: {parent}")

    # Check timezone
    schedule = config_dict.get("schedule") or {}
    timezone = schedule.get("timezone", "America/New_York")
    _validate_timezone(timezone)


def load_config(config_path: str) -> AppConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        AppConfig instance

    Raises:
        ConfigValidationError: If configuration is invalid
        FileNotFoundError: If config file doesn't exist
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(path) as f:
        raw_config = yaml.safe_load(f) or {}

    # Substitute environment variables
    config_dict = _substitute_env_vars(raw_config)

    # Validate
    _validate_config(config_dict)

    # Build config objects
    database = DatabaseConfig(**config_dict.get("database", {}))

    # Data source
    ds_dict = config_dict.get("data_source", {})
    symbol_sync_dict = ds_dict.pop("symbol_sync", {})
    symbol_sync = SymbolSyncConfig(**symbol_sync_dict)
    data_source = DataSourceConfig(
        provider=ds_dict.get("provider", "yahoo_finance"),
        symbol_sync=symbol_sync,
    )

    # Schedule
    sched_dict = config_dict.get("schedule", {})
    alert_check_dict = sched_dict.pop("alert_check", {})
    alert_check = AlertCheckConfig(**alert_check_dict)
    schedule = ScheduleConfig(
        timezone=sched_dict.get("timezone", "America/New_York"),
        alert_check=alert_check,
        market_hours_only=sched_dict.get("market_hours_only", False),
    )

    # Notifications
    notif_dict = config_dict.get("notifications", {})
    discord_dict = notif_dict.get("discord", {})
    email_dict = notif_dict.get("email", {})
    notifications = NotificationsConfig(
        discord=DiscordNotificationConfig(**discord_dict),
        email=EmailNotificationConfig(**email_dict),
    )

    # Advanced
    advanced = AdvancedConfig(**config_dict.get("advanced", {}))

    return AppConfig(
        database=database,
        data_source=data_source,
        schedule=schedule,
        notifications=notifications,
        advanced=advanced,
    )

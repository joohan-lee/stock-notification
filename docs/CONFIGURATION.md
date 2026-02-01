# Configuration Guide

## Overview

Modo separates configuration into two parts:

1. **Application Config** (`config.yaml`): Database, API, scheduling, and notification settings
2. **User Data** (SQLite): Watchlists, rules, and alert history stored in database

---

## Configuration File Location

```
modo/
├── config.yaml          # Application configuration
├── config.example.yaml  # Example template
└── data/
    └── modo.db          # SQLite database (user data)
```

---

## Application Configuration Reference

```yaml
# Modo Application Configuration

# =============================================================================
# DATABASE
# =============================================================================
database:
  # SQLite database path
  path: "data/modo.db"

# =============================================================================
# DATA SOURCE
# =============================================================================
data_source:
  # Yahoo Finance settings
  provider: yahoo_finance

  # Symbol sync schedule (fetch all available symbols)
  symbol_sync:
    enabled: true
    frequency: daily    # How often to refresh symbol list
    exchanges:          # Which exchanges to include
      - NYSE
      - NASDAQ
      - AMEX

# =============================================================================
# SCHEDULE
# =============================================================================
schedule:
  # Timezone for schedule interpretation
  timezone: "America/New_York"

  # Alert check frequency
  alert_check:
    frequency: hourly   # "hourly", "daily", or cron expression
    # cron: "0 9,12,16 * * 1-5"  # Custom: 9am, 12pm, 4pm on weekdays

  # Only run during US market hours (9:30 AM - 4:00 PM ET)
  market_hours_only: false

# =============================================================================
# NOTIFICATIONS (Default settings)
# =============================================================================
notifications:
  # Default Discord settings (can be overridden per user)
  discord:
    mention_on_critical: true   # @here on critical alerts
    include_chart_link: true    # Include TradingView link

  # Default Email settings
  email:
    smtp_host: "smtp.gmail.com"
    smtp_port: 587

# =============================================================================
# ADVANCED
# =============================================================================
advanced:
  # Logging level: DEBUG, INFO, WARNING, ERROR
  log_level: INFO

  # Alert cooldown (hours) - prevent duplicate alerts
  alert_cooldown_hours: 24

  # API retry settings
  max_retries: 3
  retry_delay_seconds: 5
```

---

## Environment Variables

Sensitive values must be stored in environment variables.

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DISCORD_WEBHOOK_URL` | Default Discord webhook (can be overridden per user) | `https://discord.com/api/webhooks/...` |

### Optional Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SMTP_USER` | SMTP username for email | `your-email@gmail.com` |
| `SMTP_PASSWORD` | SMTP password or app password | `xxxx xxxx xxxx xxxx` |
| `DATABASE_PATH` | Override database path | `/data/modo.db` |

### Setting Environment Variables

**Local Development** (`.env` file):
```bash
# .env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456/abcdef
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

**Production** (same `.env` file on the server):
```bash
# .env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456/abcdef
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## User Data Management

User data is stored in SQLite and managed via CLI commands (MVP) or API (future).

### CLI Commands

```bash
# Add a new user
uv run modo user add --email "user@example.com" --discord "webhook_url"

# List users
uv run modo user list

# Add symbols to watchlist
uv run modo watchlist add --user 1 --symbols AAPL,MSFT,GOOGL

# Remove from watchlist
uv run modo watchlist remove --user 1 --symbols AAPL

# Show watchlist
uv run modo watchlist show --user 1

# Configure rules for user
uv run modo rules add --user 1 --type monthly_high_drop --params '{"thresholds": [-5, -10]}'

# List available symbols
uv run modo symbols list --search "apple"

# Sync symbols from API
uv run modo symbols sync
```

### Database Direct Access (Advanced)

```bash
# Open SQLite CLI
sqlite3 data/modo.db

# View all users
SELECT * FROM users;

# View user's watchlist
SELECT s.ticker, s.name
FROM user_watchlist w
JOIN symbols s ON w.symbol_id = s.id
WHERE w.user_id = 1;

# View user's rules
SELECT * FROM user_rules WHERE user_id = 1;
```

---

## Default Rules Configuration

When a new user is created, these default rules are applied:

```yaml
default_rules:
  - type: monthly_high_drop
    parameters:
      thresholds: [-5, -10, -15, -20]
    enabled: true

  - type: daily_change
    parameters:
      threshold: 5
      direction: both
    enabled: true

  - type: volume_spike
    parameters:
      multiplier: 3.0
      average_days: 20
    enabled: true
```

Users can modify these rules via CLI or API.

---

## Configuration Examples

### Minimal Configuration

```yaml
database:
  path: "data/modo.db"

data_source:
  provider: yahoo_finance

schedule:
  timezone: "America/New_York"
  alert_check:
    frequency: hourly
```

### Production Configuration

```yaml
database:
  path: "/data/modo.db"

data_source:
  provider: yahoo_finance
  symbol_sync:
    enabled: true
    frequency: daily
    exchanges:
      - NYSE
      - NASDAQ

schedule:
  timezone: "America/New_York"
  alert_check:
    frequency: hourly
  market_hours_only: true

notifications:
  discord:
    mention_on_critical: true
    include_chart_link: true
  email:
    smtp_host: "smtp.gmail.com"
    smtp_port: 587

advanced:
  log_level: INFO
  alert_cooldown_hours: 24
  max_retries: 3
  retry_delay_seconds: 5
```

---

## Validation

The application validates configuration on startup:

| Error | Cause | Solution |
|-------|-------|----------|
| `Database path not writable` | Permission issue | Check directory permissions |
| `Invalid timezone` | Unknown timezone | Use valid IANA timezone |
| `Invalid cron expression` | Malformed cron | Use valid cron syntax |
| `SMTP connection failed` | Wrong credentials | Check SMTP settings |

---

## Migration

When upgrading Modo, database migrations run automatically:

```bash
# Check migration status
uv run modo db status

# Run pending migrations
uv run modo db migrate

# Rollback last migration (if needed)
uv run modo db rollback
```

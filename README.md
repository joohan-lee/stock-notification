# Modo

**Stock Alert Service** - Get notified at the right moment.

Modo (Latin for "just now") monitors US stocks and ETFs, sending alerts when specific conditions are met. Built for individual investors who want to catch opportunities without constantly watching the market.

## Features

- **Monthly High Drop Alerts** - Get notified when stocks drop -5%, -10%, -15%, or -20% from their 30-day high
- **Daily Price Movement** - Detect significant daily surges or drops
- **Volume Spike Detection** - Alert when trading volume exceeds 3x the 20-day average
- **Custom Rules** - Define your own conditions (e.g., `price < 150`, `daily_change_pct > 5`)
- **Multi-Channel Notifications** - Discord webhooks and Email (SMTP)
- **Alert Cooldown** - Prevent duplicate alerts with configurable cooldown period

## Quick Start

### 1. Install Dependencies

```bash
uv pip install -e ".[dev]"
```

### 2. Configure

```bash
cp config.example.yaml config.yaml
```

Create a `.env` file for secrets:

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 3. Initialize Database and Sync Symbols

```bash
uv run modo symbols sync
```

### 4. Create User and Watchlist

```bash
# Create a user with Discord notifications
uv run modo user add --discord "https://discord.com/api/webhooks/..."

# Add symbols to watchlist
uv run modo watchlist add --user 1 --symbols AAPL,MSFT,GOOGL,NVDA

# Add alert rules
uv run modo rules add --user 1 --type monthly_high_drop --params '{"thresholds": [-5, -10, -15, -20]}'
```

### 5. Run

```bash
# Single check
uv run modo check

# With debug output
uv run modo check --debug

# Dry run (no notifications sent)
uv run modo check --dry-run
```

## CLI Commands

```bash
# User management
uv run modo user add --email "user@example.com" --discord "webhook_url"
uv run modo user list

# Watchlist management
uv run modo watchlist add --user 1 --symbols AAPL,TSLA
uv run modo watchlist show --user 1

# Symbol management
uv run modo symbols sync
uv run modo symbols list --search "apple"

# Add mutual funds manually (not included in sync)
sqlite3 data/modo.db "INSERT INTO symbols (ticker, name, type, exchange) VALUES ('FXAIX', 'Fidelity 500 Index', 'mutualfund', 'MUTUALFUND');"

# Rule management
uv run modo rules add --user 1 --type daily_change --params '{"threshold": 5, "direction": "both"}'

# Database management
uv run modo db status
uv run modo db migrate
```

## Alert Rules

| Rule Type | Description | Parameters |
|-----------|-------------|------------|
| `monthly_high_drop` | Drop from 30-day high | `thresholds`: list of percentages (e.g., `[-5, -10]`) |
| `daily_change` | Daily price movement | `threshold`: percentage, `direction`: "up"/"down"/"both" |
| `volume_spike` | Unusual trading volume | `multiplier`: volume ratio (default: 3.0) |
| `custom` | User-defined expression | `name`: rule name, `condition`: expression |

### Custom Rule Variables

Available variables for custom rules:

- `price` - Current price
- `open`, `high`, `low`, `close` - OHLC data
- `volume` - Current volume
- `daily_change_pct` - Daily change percentage
- `monthly_high`, `monthly_low` - 30-day high/low
- `avg_volume_20` - 20-day average volume

Example: `price < 150 and daily_change_pct < -3`

## Documentation

- [User Guide](docs/USER_GUIDE.md) - Day-to-day usage instructions
- [Configuration](docs/CONFIGURATION.md) - Detailed configuration reference
- [Architecture](docs/ARCHITECTURE.md) - System design and database schema
- [Deployment](docs/DEPLOYMENT.md) - Oracle Cloud deployment with uv and cron
- [Oracle Cloud](docs/ORACLE_CLOUD.md) - Instance details and server setup
- [Rules](docs/RULES.md) - Alert rule details

## Tech Stack

- **Python 3.13+**
- **uv** - Package management and execution
- **SQLite** - User data, watchlists, alert history
- **yfinance** - Yahoo Finance data provider
- **simpleeval** - Safe expression evaluation for custom rules
- **requests** - HTTP client for webhooks

## Project Structure

```
modo/
├── src/
│   ├── cli.py            # CLI entry point
│   ├── app.py            # ModoApp core logic
│   ├── config.py         # Configuration loader
│   ├── database/         # SQLite models and repositories
│   ├── data/             # Stock data fetching
│   ├── rules/            # Rule engine and types
│   └── notifiers/        # Discord and Email notifiers
├── tests/
├── docs/
├── config.yaml
└── pyproject.toml
```

## License

MIT

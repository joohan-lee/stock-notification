# Architecture Document

## System Overview

Modo is a Python-based service that periodically fetches stock data, evaluates rules, and sends notifications when conditions are met. It uses SQLite for data persistence and is designed to support multiple users in the future.

```
┌──────────────────────────────────────────────────────────────────┐
│                       Oracle Cloud VM                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    stock-notification                        │  │
│  │                                                             │  │
│  │  ┌──────────┐    ┌─────────────┐    ┌──────────────┐       │  │
│  │  │  Cron    │───▶│   Main App  │───▶│  Notifiers   │       │  │
│  │  │Scheduler │    │  (Python)   │    │ Discord/Email│       │  │
│  │  └──────────┘    └──────┬──────┘    └──────────────┘       │  │
│  │                         │                                   │  │
│  │         ┌───────────────┼───────────────┐                  │  │
│  │         ▼               ▼               ▼                  │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐            │  │
│  │  │  SQLite    │  │Rule Engine │  │Data Fetcher│            │  │
│  │  │  Database  │  └────────────┘  │ (yfinance) │            │  │
│  │  └────────────┘                  └─────┬──────┘            │  │
│  │         │                              │                    │  │
│  │         └──────────────────────────────┘                    │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                            Yahoo Finance API
```

---

## Component Design

### 1. Scheduler (Cron)

**Responsibility**: Trigger the main application at configured intervals.

**Implementation**: System cron on Oracle Cloud instance.

```
# Example crontab (crontab -e)
0 * * * * cd ~/stock-notification && uv run modo check  # Every hour
0 9 * * 1 cd ~/stock-notification && uv run modo healthcheck  # Weekly healthcheck
```

### 2. Main Application

**Responsibility**: Orchestrate the data fetching, rule evaluation, and notification flow.

**Flow**:
1. Load configuration (symbols, rules, notification settings)
2. Fetch current market data for all symbols
3. Evaluate each rule against the data
4. Collect triggered alerts
5. Send notifications for triggered alerts
6. Log results

```python
def main():
    config = load_config("config.yaml")
    data = fetch_market_data(config.symbols)
    alerts = evaluate_rules(config.rules, data)
    if alerts:
        send_notifications(config.notifications, alerts)
```

### 3. Data Fetcher

**Responsibility**: Retrieve stock data from Yahoo Finance.

**Interface**:
```python
class DataFetcher:
    def get_current_price(symbol: str) -> float
    def get_daily_data(symbol: str, period: str) -> DataFrame
    def get_monthly_high(symbol: str) -> float
    def get_average_volume(symbol: str, days: int) -> float
```

**Dependencies**: `yfinance` library

### 4. Rule Engine

**Responsibility**: Evaluate conditions and determine if alerts should be triggered.

**Rule Types**:

| Rule Type | Parameters | Condition |
|-----------|------------|-----------|
| `monthly_high_drop` | `threshold` (e.g., -5%) | price <= monthly_high * (1 + threshold) |
| `daily_change` | `threshold` (e.g., ±5%) | abs(daily_change) >= threshold |
| `volume_spike` | `multiplier` (e.g., 3x) | current_volume >= avg_volume * multiplier |
| `custom` | `condition` expression | User-defined condition |

**Interface**:
```python
class RuleEngine:
    def evaluate(rule: Rule, data: MarketData) -> Optional[Alert]
```

### 5. Notifiers

**Responsibility**: Deliver alerts to configured channels.

**Discord Notifier**:
- Uses webhook URL
- Formats message with embed (color-coded by severity)

**Email Notifier**:
- Uses SMTP (Gmail, custom SMTP server)
- Sends HTML-formatted email

**Interface**:
```python
class Notifier(ABC):
    def send(alert: Alert) -> bool

class DiscordNotifier(Notifier):
    def __init__(webhook_url: str)

class EmailNotifier(Notifier):
    def __init__(smtp_config: SMTPConfig)
```

---

## Data Flow

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────┐
│  Cron   │────▶│ Load Config │────▶│ Fetch Data  │────▶│ Evaluate │
└─────────┘     └─────────────┘     └─────────────┘     │  Rules   │
                                                         └────┬─────┘
                                                              │
                ┌─────────────┐     ┌─────────────┐           │
                │    Done     │◀────│   Notify    │◀──────────┘
                └─────────────┘     └─────────────┘
```

---

## Directory Structure

```
modo/
├── src/
│   ├── __init__.py
│   ├── app.py               # ModoApp core logic
│   ├── config.py            # Configuration loader
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py    # SQLite connection manager
│   │   ├── models.py        # Data models (dataclasses)
│   │   └── repository.py    # CRUD operations
│   ├── data/
│   │   ├── __init__.py
│   │   ├── fetcher.py       # Yahoo Finance data fetcher
│   │   └── symbols.py       # Symbol list sync
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── engine.py        # Rule evaluation engine
│   │   └── types.py         # Rule type definitions
│   └── notifiers/
│       ├── __init__.py
│       ├── base.py          # Abstract notifier
│       ├── discord.py       # Discord webhook notifier
│       └── email.py         # Email SMTP notifier
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_fetcher.py
│   ├── test_rules.py
│   └── test_notifiers.py
├── data/
│   └── modo.db              # SQLite database file
├── config.yaml              # Application configuration
├── config.example.yaml      # Example configuration
├── pyproject.toml
├── uv.lock
└── docs/
    └── ...
```

---

## Error Handling

| Error Type | Handling Strategy |
|------------|-------------------|
| API rate limit | Exponential backoff, retry up to 3 times |
| Network failure | Retry with timeout, log error |
| Invalid config | Fail fast with clear error message |
| Notification failure | Retry once, log error, continue with other channels |

---

## Security Considerations

1. **Secrets Management**:
   - API keys and webhook URLs stored in environment variables
   - Never commit secrets to repository
   - Use `.env` file locally and in production

2. **Input Validation**:
   - Validate all configuration values
   - Sanitize symbol inputs to prevent injection

3. **Network Security**:
   - HTTPS only for all external API calls
   - TLS for SMTP connections

---

## Database Schema

Modo uses SQLite for data persistence. The schema is designed to support multiple users.

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│   users     │       │  user_watchlist │       │   symbols   │
├─────────────┤       ├─────────────────┤       ├─────────────┤
│ id (PK)     │◀──┐   │ id (PK)         │   ┌──▶│ id (PK)     │
│ email       │   └───│ user_id (FK)    │   │   │ ticker      │
│ discord_url │       │ symbol_id (FK)  │───┘   │ name        │
│ created_at  │       │ created_at      │       │ type        │
└─────────────┘       └─────────────────┘       │ exchange    │
       │                                         │ updated_at  │
       │              ┌─────────────────┐       └─────────────┘
       │              │   user_rules    │
       │              ├─────────────────┤
       └─────────────▶│ id (PK)         │
                      │ user_id (FK)    │
                      │ rule_type       │
                      │ parameters      │
                      │ enabled         │
                      └─────────────────┘

┌─────────────────────┐
│    alert_history    │
├─────────────────────┤
│ id (PK)             │
│ user_id (FK)        │
│ symbol_id (FK)      │
│ rule_type           │
│ message             │
│ triggered_at        │
│ notified_at         │
└─────────────────────┘
```

### Tables

#### `symbols`
Stores all available symbols fetched from Yahoo Finance API.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| ticker | TEXT | Symbol ticker (e.g., AAPL) |
| name | TEXT | Company/ETF name |
| type | TEXT | "stock", "etf", "index" |
| exchange | TEXT | Exchange name (e.g., NASDAQ) |
| updated_at | TIMESTAMP | Last update time |

#### `users`
Stores user information and notification settings.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| email | TEXT | Email for notifications (nullable) |
| discord_webhook_url | TEXT | Discord webhook URL (nullable) |
| created_at | TIMESTAMP | Account creation time |

#### `user_watchlist`
Junction table for user's monitored symbols.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| user_id | INTEGER | FK to users |
| symbol_id | INTEGER | FK to symbols |
| created_at | TIMESTAMP | When added to watchlist |

#### `user_rules`
Stores user's alert rules (both predefined and custom).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| user_id | INTEGER | FK to users |
| rule_type | TEXT | "monthly_high_drop", "daily_change", etc. |
| parameters | JSON | Rule-specific parameters |
| enabled | BOOLEAN | Whether rule is active |
| symbol_id | INTEGER | FK to symbols (nullable, for symbol-specific rules) |

#### `alert_history`
Tracks sent alerts for deduplication.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| user_id | INTEGER | FK to users |
| symbol_id | INTEGER | FK to symbols |
| rule_type | TEXT | Rule that triggered the alert |
| message | TEXT | Alert message content |
| triggered_at | TIMESTAMP | When condition was met |
| notified_at | TIMESTAMP | When notification was sent |

---

## Data Flow

### Symbol Sync Flow
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Scheduler   │────▶│ Fetch all   │────▶│ Upsert to   │
│ (daily)     │     │ symbols API │     │ SQLite      │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Alert Flow
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Scheduler   │────▶│ Load user   │────▶│ Fetch price │────▶│ Evaluate    │
│ (hourly)    │     │ watchlists  │     │ data        │     │ rules       │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                    │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐             │
│    Done     │◀────│ Save alert  │◀────│ Send notify │◀────────────┘
└─────────────┘     │ history     │     │ (if new)    │
                    └─────────────┘     └─────────────┘
```

---

## Scalability

Current design is for personal use with future multi-user support:

| Concern | Current | Future Option |
|---------|---------|---------------|
| Symbols | All US stocks/ETFs | Filter by exchange, add international |
| Storage | SQLite | PostgreSQL for high concurrency |
| Users | Single | Multi-tenant with user isolation |
| API Rate | Sequential | Batch processing, parallel fetching |

# User Guide

This guide covers day-to-day usage of Modo for monitoring stocks and receiving alerts.

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Managing Your Watchlist](#2-managing-your-watchlist)
3. [Configuring Alert Rules](#3-configuring-alert-rules)
4. [Understanding Alerts](#4-understanding-alerts)
5. [Running Modo](#5-running-modo)
6. [FAQ & Troubleshooting](#6-faq--troubleshooting)

---

## 1. Getting Started

### 1.1 Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Discord webhook URL (for notifications)
- Internet connection (for Yahoo Finance API)

### 1.2 Installation

```bash
# Clone the repository
git clone <repository-url>
cd modo

# Install dependencies
uv pip install -e ".[dev]"
```

### 1.3 Initial Configuration

Copy the example configuration:

```bash
cp config.example.yaml config.yaml
```

Create a `.env` file for sensitive data:

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdefg
```

### 1.4 Creating a Discord Webhook

1. Open Discord and go to your server
2. Right-click on the channel where you want alerts → **Edit Channel**
3. Go to **Integrations** → **Webhooks** → **New Webhook**
4. Name it "Modo Alerts" and copy the webhook URL
5. Paste the URL in your `.env` file

### 1.5 First-Time Setup

```bash
# Initialize database and sync available symbols
uv run modo symbols sync

# Create your user account
uv run modo user add --discord "$DISCORD_WEBHOOK_URL"
# Note the user ID (usually 1 for first user)

# Verify user was created
uv run modo user list
```

---

## 2. Managing Your Watchlist

### 2.1 Searching for Symbols

Find symbols by company name or ticker:

```bash
# Search by name
uv run modo symbols list --search "apple"

# Search by ticker
uv run modo symbols list --search "AAPL"

# List all symbols (limited to 50)
uv run modo symbols list
```

### 2.2 Adding Symbols to Watchlist

```bash
# Add single symbol
uv run modo watchlist add --user 1 --symbols AAPL

# Add multiple symbols (comma-separated, no spaces)
uv run modo watchlist add --user 1 --symbols AAPL,MSFT,GOOGL,AMZN,NVDA
```

### 2.3 Viewing Your Watchlist

```bash
uv run modo watchlist show --user 1
```

Output:
```
AAPL: Apple Inc.
MSFT: Microsoft Corporation
GOOGL: Alphabet Inc.
```

### 2.4 Supported Exchanges

Modo supports US exchanges:

- **NYSE** - New York Stock Exchange
- **NASDAQ** - NASDAQ Stock Market
- **AMEX** - American Stock Exchange

### 2.5 Syncing Symbol Data

Symbol data should be refreshed periodically:

```bash
# Manual sync
uv run modo symbols sync
```

In production, this runs automatically based on your `config.yaml` settings.

### 2.6 Adding Mutual Funds and Other Securities

The symbol sync only includes NYSE/NASDAQ listed securities. To monitor mutual funds (e.g., FXAIX, VFIAX) or other securities not on these exchanges, add them manually:

```bash
# Add mutual fund to symbols table
sqlite3 data/modo.db "INSERT INTO symbols (ticker, name, type, exchange) VALUES ('FXAIX', 'Fidelity 500 Index', 'mutualfund', 'MUTUALFUND');"

# Then add to your watchlist
uv run modo watchlist add --user 1 --symbols FXAIX
```

**Supported security types:**
- `stock` - Individual stocks
- `etf` - Exchange-traded funds
- `mutualfund` - Mutual funds (requires manual addition)

To verify Yahoo Finance supports a ticker before adding:

```bash
uv run python -c "import yfinance as yf; t = yf.Ticker('FXAIX'); print(t.info.get('longName', 'Not found'))"
```

---

## 3. Configuring Alert Rules

### 3.1 Built-in Rule Types

#### Monthly High Drop

Triggers when a stock drops X% from its 30-day high. Great for spotting buying opportunities during dips.

```bash
uv run modo rules add --user 1 --type monthly_high_drop \
  --params '{"thresholds": [-5, -10, -15, -20]}'
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `thresholds` | list | Drop percentages to trigger alerts |

#### Daily Change

Triggers on significant daily price movements.

```bash
# Alert on any 5%+ move (up or down)
uv run modo rules add --user 1 --type daily_change \
  --params '{"threshold": 5, "direction": "both"}'

# Alert only on drops
uv run modo rules add --user 1 --type daily_change \
  --params '{"threshold": 5, "direction": "down"}'

# Alert only on surges
uv run modo rules add --user 1 --type daily_change \
  --params '{"threshold": 5, "direction": "up"}'
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `threshold` | number | Minimum percentage change |
| `direction` | string | "up", "down", or "both" |

#### Volume Spike

Triggers when trading volume is unusually high compared to the average.

```bash
uv run modo rules add --user 1 --type volume_spike \
  --params '{"multiplier": 3.0}'
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `multiplier` | number | Volume must exceed average by this factor |

### 3.2 Custom Rules

Create rules with custom conditions using expressions.

```bash
# Alert when price drops below $150
uv run modo rules add --user 1 --type custom \
  --params '{"name": "AAPL below 150", "condition": "price < 150"}'

# Alert on large drops with high volume
uv run modo rules add --user 1 --type custom \
  --params '{"name": "Crash detector", "condition": "daily_change_pct < -5 and volume > avg_volume_20 * 2"}'
```

#### Available Variables

| Variable | Description |
|----------|-------------|
| `price` | Current stock price |
| `open` | Today's opening price |
| `high` | Today's high |
| `low` | Today's low |
| `close` | Previous close price |
| `volume` | Current trading volume |
| `daily_change_pct` | Daily change as percentage |
| `monthly_high` | 30-day high price |
| `monthly_low` | 30-day low price |
| `avg_volume_20` | 20-day average volume |

#### Supported Operators

- Comparison: `<`, `>`, `<=`, `>=`, `==`, `!=`
- Arithmetic: `+`, `-`, `*`, `/`
- Logical: `and`, `or`, `not`
- Parentheses for grouping

#### Examples

```python
# Price target
"price < 100"

# Percentage drop from monthly high
"price < monthly_high * 0.9"

# Combined conditions
"daily_change_pct < -3 and volume > avg_volume_20 * 2"

# Price range
"price > 50 and price < 60"
```

---

## 4. Understanding Alerts

### 4.1 Alert Severity Levels

| Level | Icon | When Used |
|-------|------|-----------|
| **INFO** | ℹ️ | Minor movements, custom rule triggers |
| **WARNING** | ⚠️ | Moderate drops (10%), high volume (5x) |
| **CRITICAL** | 🚨 | Large drops (15%+), extreme movements |

### 4.2 Discord Alert Format

Alerts appear as rich embeds with:

- **Title**: Emoji + Ticker + "Alert"
- **Description**: Detailed alert message
- **Fields**:
  - Current Price
  - Rule Type
  - TradingView Chart Link
- **Color**: Blue (INFO), Orange (WARNING), Red (CRITICAL)
- **Timestamp**: When the alert was triggered

Critical alerts include `@here` mention to notify channel members.

### 4.3 Alert Cooldown

To prevent alert spam, Modo enforces a cooldown period (default: 24 hours). The same alert type for the same symbol won't trigger again until the cooldown expires.

Configure in `config.yaml`:

```yaml
advanced:
  alert_cooldown_hours: 24  # Change as needed
```

### 4.4 Alert Examples

**Monthly High Drop**:
```
🚨 AAPL Alert
AAPL dropped 15% from monthly high. Current: $165.00, High: $194.12 (actual drop: -15.0%)
```

**Daily Change**:
```
⚠️ NVDA Alert
NVDA surged +8.5% today. Current: $890.00, Previous: $820.27
```

**Volume Spike**:
```
ℹ️ TSLA Alert
TSLA volume spike: 4.2x average. Current: 125,000,000, Avg: 29,761,905
```

---

## 5. Running Modo

### 5.1 Manual Execution

```bash
# Run once
uv run modo check

# Run with debug logging
uv run modo check --debug

# Dry run (evaluate rules but don't send notifications)
uv run modo check --dry-run
```

### 5.2 Scheduled Execution (Cron)

In production, Modo runs via system cron on Oracle Cloud:

```cron
# Alert check every hour
0 * * * * cd ~/stock-notification && uv run modo check >> ~/stock-notification/logs/cron.log 2>&1

# Healthcheck every Monday
0 9 * * 1 cd ~/stock-notification && uv run modo healthcheck >> ~/stock-notification/logs/cron.log 2>&1
```

See [Deployment Guide](DEPLOYMENT.md) for full Oracle Cloud setup instructions.

---

## 6. FAQ & Troubleshooting

### Q: I'm not receiving any alerts

1. **Check your watchlist has symbols**:
   ```bash
   uv run modo watchlist show --user 1
   ```

2. **Check you have rules configured**:
   ```bash
   sqlite3 data/modo.db "SELECT * FROM user_rules WHERE user_id = 1;"
   ```

3. **Run in debug mode** to see what's happening:
   ```bash
   uv run modo check --debug
   ```

4. **Verify Discord webhook** is correct in your `.env` file

### Q: I'm getting duplicate alerts

The cooldown might be too short. Increase it in `config.yaml`:

```yaml
advanced:
  alert_cooldown_hours: 48  # Increase from 24
```

### Q: Symbol not found when adding to watchlist

1. Sync symbols first:
   ```bash
   uv run modo symbols sync
   ```

2. Search for the correct ticker:
   ```bash
   uv run modo symbols list --search "company name"
   ```

### Q: Yahoo Finance API errors

- **Rate limiting**: Wait a few minutes and try again
- **Network issues**: Check your internet connection
- **Symbol delisted**: The symbol may no longer be available

### Q: How do I remove a symbol from my watchlist?

Currently, use direct database access:

```bash
sqlite3 data/modo.db "DELETE FROM user_watchlist WHERE user_id = 1 AND symbol_id = (SELECT id FROM symbols WHERE ticker = 'AAPL');"
```

### Q: How do I disable a rule?

Use direct database access:

```bash
sqlite3 data/modo.db "UPDATE user_rules SET enabled = 0 WHERE id = 1;"
```

### Q: Where are the logs?

- **Console output**: When running manually
- **Cron logs**: `tail -f ~/stock-notification/logs/cron.log`
- **System cron log**: `sudo grep modo /var/log/cron`

---

## Next Steps

- Review [Configuration Guide](CONFIGURATION.md) for advanced settings
- Set up [Deployment](DEPLOYMENT.md) for always-on monitoring
- Understand the [Architecture](ARCHITECTURE.md) if you want to contribute

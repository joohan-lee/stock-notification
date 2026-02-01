# Rules Specification

## Overview

The rule engine evaluates market conditions and triggers alerts when specified criteria are met. This document describes all available rule types and how to configure them.

---

## Predefined Rules

### 1. Monthly High Drop (`monthly_high_drop`)

Triggers when a stock's current price drops below a certain percentage from its 30-day high.

**Use Case**: Identify potential buying opportunities during market corrections.

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `thresholds` | list[float] | Yes | - | Drop percentages to alert on (e.g., [-5, -10, -15, -20]) |

**Logic**:
```python
monthly_high = max(closing_prices[-30:])
drop_percent = ((current_price - monthly_high) / monthly_high) * 100

for threshold in thresholds:
    if drop_percent <= threshold:
        trigger_alert(threshold)
```

**Example Configuration**:
```yaml
rules:
  - type: monthly_high_drop
    thresholds: [-5, -10, -15, -20]
```

**Alert Message**:
```
📉 AAPL dropped 10.5% from monthly high
Current: $165.30 | Monthly High: $184.92
```

---

### 2. Daily Price Change (`daily_change`)

Triggers when a stock's daily price change exceeds a threshold.

**Use Case**: React to significant single-day market movements.

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `threshold` | float | Yes | - | Minimum absolute percentage change to trigger (e.g., 5) |
| `direction` | string | No | "both" | "up", "down", or "both" |

**Logic**:
```python
daily_change = ((current_price - previous_close) / previous_close) * 100

if direction == "both" and abs(daily_change) >= threshold:
    trigger_alert()
elif direction == "up" and daily_change >= threshold:
    trigger_alert()
elif direction == "down" and daily_change <= -threshold:
    trigger_alert()
```

**Example Configuration**:
```yaml
rules:
  - type: daily_change
    threshold: 5
    direction: both
```

**Alert Message**:
```
🚀 TSLA surged +8.3% today
Current: $245.00 | Previous Close: $226.20
```

---

### 3. Volume Spike (`volume_spike`)

Triggers when trading volume significantly exceeds the average.

**Use Case**: Detect unusual market activity that may indicate news or institutional trading.

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `multiplier` | float | Yes | - | Volume must exceed average by this factor (e.g., 3.0) |
| `average_days` | int | No | 20 | Number of days to calculate average volume |

**Logic**:
```python
avg_volume = mean(daily_volumes[-average_days:])
current_volume = today_volume

if current_volume >= avg_volume * multiplier:
    trigger_alert()
```

**Example Configuration**:
```yaml
rules:
  - type: volume_spike
    multiplier: 3.0
    average_days: 20
```

**Alert Message**:
```
📊 NVDA volume spike: 4.2x average
Current Volume: 84M | 20-day Average: 20M
```

---

## Custom Rules

Users can define custom rules using a simple expression syntax.

### Expression Syntax

**Available Variables**:
| Variable | Description |
|----------|-------------|
| `price` | Current price |
| `open` | Today's open price |
| `high` | Today's high price |
| `low` | Today's low price |
| `close` | Previous close price |
| `volume` | Current volume |
| `avg_volume_20` | 20-day average volume |
| `monthly_high` | 30-day high price |
| `monthly_low` | 30-day low price |
| `daily_change_pct` | Daily change percentage |

**Operators**:
| Operator | Description |
|----------|-------------|
| `>`, `>=` | Greater than, greater or equal |
| `<`, `<=` | Less than, less or equal |
| `==`, `!=` | Equal, not equal |
| `and`, `or` | Logical operators |

**Example Configurations**:

```yaml
# Alert when price falls below $100
rules:
  - type: custom
    name: "Price below $100"
    condition: "price < 100"
    symbols: ["AAPL"]

# Alert when price breaks monthly high
rules:
  - type: custom
    name: "New monthly high"
    condition: "price > monthly_high"

# Complex condition
rules:
  - type: custom
    name: "Bullish signal"
    condition: "daily_change_pct > 3 and volume > avg_volume_20 * 2"
```

---

## Rule Priority and Deduplication

### Priority
Rules are evaluated in order of definition. All matching rules trigger alerts.

### Deduplication
To avoid alert spam, the system tracks recently sent alerts:

| Rule Type | Cooldown Period |
|-----------|-----------------|
| `monthly_high_drop` | 24 hours per threshold level |
| `daily_change` | 24 hours |
| `volume_spike` | 24 hours |
| `custom` | 24 hours |

**Example**: If AAPL triggers a -10% drop alert at 9am, the same alert won't fire again until 9am the next day, even if the condition is still met.

---

## Rule Scoping

Rules can be applied globally or to specific symbols:

```yaml
# Global rule (applies to all symbols)
rules:
  - type: monthly_high_drop
    thresholds: [-10, -20]

# Symbol-specific rule
rules:
  - type: daily_change
    threshold: 3
    symbols: ["TSLA", "NVDA"]  # Only for volatile stocks
```

---

## Alert Severity

Alerts are categorized by severity for visual distinction in notifications:

| Severity | Color (Discord) | Criteria |
|----------|-----------------|----------|
| `info` | Blue | Volume spike, small price changes |
| `warning` | Yellow | 5-10% drops, moderate daily changes |
| `critical` | Red | >10% drops, extreme movements |

Severity is automatically determined based on the magnitude of the triggered condition.

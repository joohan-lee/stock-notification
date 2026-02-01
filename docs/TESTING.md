# Testing Guide

## Overview

Modo uses pytest for testing with a TDD (Test-Driven Development) approach. Tests are organized by layer and functionality.

---

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── test_database.py      # Database layer tests
├── test_models.py        # Data model tests
├── test_fetcher.py       # Yahoo Finance API tests
├── test_rules.py         # Rule engine tests
├── test_notifiers.py     # Notification tests
└── test_integration.py   # End-to-end tests
```

---

## Running Tests

### Prerequisites

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_rules.py
```

### Run Specific Test Class or Function

```bash
# Run a test class
pytest tests/test_rules.py::TestMonthlyHighDropRule

# Run a specific test
pytest tests/test_rules.py::TestMonthlyHighDropRule::test_triggers_on_threshold_breach
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Run with Verbose Output

```bash
pytest -v
```

---

## Test Categories

### 1. Unit Tests

Test individual components in isolation.

| File | Component | Test Count |
|------|-----------|------------|
| `test_models.py` | Data models (Symbol, User, etc.) | 15 |
| `test_database.py` | CRUD operations | 45 |
| `test_rules.py` | Rule evaluation logic | 30 |
| `test_notifiers.py` | Notification formatting/sending | 25 |

### 2. Integration Tests

Test component interactions and full workflows.

| File | Scope | Test Count |
|------|-------|------------|
| `test_fetcher.py` | Yahoo Finance API integration | 15 |
| `test_integration.py` | End-to-end alert flow | 12 |

---

## Test Scenarios

### Rule Engine Tests

| Rule Type | Scenarios |
|-----------|-----------|
| `monthly_high_drop` | Threshold breach, multiple thresholds, severity levels |
| `daily_change` | Surge/drop detection, direction filtering |
| `volume_spike` | Multiplier threshold, severity based on ratio |
| `custom` | Expression parsing, compound conditions (AND/OR) |

### Notification Tests

| Channel | Scenarios |
|---------|-----------|
| Discord | Embed formatting, color by severity, @here mention, rate limiting |
| Email | HTML formatting, multiple recipients, SMTP errors |

### Integration Tests

| Flow | Scenarios |
|------|-----------|
| Alert flow | Data fetch → Rule evaluation → Notification → History |
| Deduplication | Cooldown period, different rule types |
| CLI | User management, watchlist, symbol sync |

---

## Fixtures

Common fixtures are defined in `conftest.py`:

```python
@pytest.fixture
def sample_stock_info():
    """Sample Yahoo Finance response."""
    return {
        "regularMarketPrice": 175.50,
        "previousClose": 173.25,
        ...
    }

@pytest.fixture
def sample_discord_webhook_url():
    """Sample Discord webhook URL."""
    return "https://discord.com/api/webhooks/123/abc"
```

### Database Fixtures

```python
@pytest.fixture
def db():
    """Create in-memory database."""
    db = Database(":memory:")
    db.initialize()
    return db

@pytest.fixture
def repos(db):
    """Create all repositories."""
    return {
        "symbol": SymbolRepository(db),
        "user": UserRepository(db),
        ...
    }
```

---

## Mocking

External dependencies are mocked to ensure tests are:
- **Fast**: No real API calls
- **Reliable**: No network dependency
- **Predictable**: Consistent test data

### Yahoo Finance Mocking

```python
with patch("yfinance.Ticker") as mock_ticker:
    mock_ticker.return_value.info = {
        "regularMarketPrice": 175.50,
        ...
    }
    data = fetcher.get_current_data("AAPL")
```

### Discord Webhook Mocking

```python
with patch("requests.post") as mock_post:
    mock_post.return_value.status_code = 204
    mock_post.return_value.ok = True

    result = notifier.send(alert)
```

---

## Writing New Tests

### Test Naming Convention

```python
def test_<action>_<condition>_<expected_result>():
    """Should <expected behavior>."""
    pass

# Examples:
def test_triggers_on_threshold_breach():
def test_no_alert_when_above_threshold():
def test_skip_disabled_rules():
```

### Test Structure (AAA Pattern)

```python
def test_example():
    """Should do something specific."""
    # Arrange - Set up test data
    rule = MonthlyHighDropRule(thresholds=[-10])
    stock_data = StockData(...)

    # Act - Execute the code under test
    alerts = rule.evaluate(stock_data, historical_data)

    # Assert - Verify the results
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.WARNING
```

---

## CI/CD Integration

Tests run automatically on:
- Every push to main branch
- Every pull request

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=src
```

---

## Coverage Goals

| Component | Target |
|-----------|--------|
| Models | 100% |
| Database | 90% |
| Rules | 95% |
| Notifiers | 85% |
| Integration | 80% |
| **Overall** | **90%** |

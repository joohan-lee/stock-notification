"""
Rule engine tests.
Tests for alert rule evaluation.
"""

import pytest
from datetime import datetime

from src.rules.engine import RuleEngine, Alert, AlertSeverity
from src.rules.types import (
    MonthlyHighDropRule,
    MonthlyLowRiseRule,
    PriceTargetRule,
    DailyChangeRule,
    VolumeSpikeRule,
    CustomRule,
)
from src.data.fetcher import StockData, HistoricalData
from src.database.models import UserRule


class TestAlert:
    """Test Alert model."""

    def test_create_alert(self):
        """Should create an alert."""
        alert = Alert(
            ticker="AAPL",
            rule_type="monthly_high_drop",
            message="AAPL dropped 10% from monthly high",
            severity=AlertSeverity.WARNING,
            current_price=165.00,
            triggered_at=datetime.now(),
            metadata={"threshold": -10, "monthly_high": 183.33},
        )
        assert alert.ticker == "AAPL"
        assert alert.severity == AlertSeverity.WARNING

    def test_alert_severity_levels(self):
        """Should support different severity levels."""
        assert AlertSeverity.INFO.value < AlertSeverity.WARNING.value
        assert AlertSeverity.WARNING.value < AlertSeverity.CRITICAL.value


class TestMonthlyHighDropRule:
    """Test monthly high drop rule evaluation."""

    @pytest.fixture
    def rule(self):
        """Create a monthly high drop rule."""
        return MonthlyHighDropRule(thresholds=[-5, -10, -15, -20])

    @pytest.fixture
    def stock_data(self):
        """Create sample stock data."""
        return StockData(
            ticker="AAPL",
            current_price=165.00,
            previous_close=170.00,
            open_price=169.00,
            high=171.00,
            low=164.00,
            volume=50_000_000,
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def historical_data(self):
        """Create sample historical data."""
        return HistoricalData(
            ticker="AAPL",
            monthly_high=185.00,  # Current price 165 = -10.8% drop
            monthly_low=160.00,
            avg_volume_20d=45_000_000,
            prices=[],
            volumes=[],
        )

    def test_triggers_on_threshold_breach(self, rule, stock_data, historical_data):
        """Should trigger alert when price drops below threshold."""
        alerts = rule.evaluate(stock_data, historical_data)

        # Price 165 vs high 185 = -10.8%, should trigger -5% and -10% thresholds
        assert len(alerts) == 2
        thresholds_triggered = [a.metadata["threshold"] for a in alerts]
        assert -5 in thresholds_triggered
        assert -10 in thresholds_triggered

    def test_no_alert_when_above_threshold(self, rule, stock_data, historical_data):
        """Should not trigger alert when price is above all thresholds."""
        historical_data.monthly_high = 170.00  # Current 165 = -2.9% drop
        alerts = rule.evaluate(stock_data, historical_data)

        assert len(alerts) == 0

    def test_triggers_multiple_thresholds(self, rule, stock_data, historical_data):
        """Should trigger multiple threshold alerts at once."""
        stock_data.current_price = 140.00  # vs 185 high = -24.3% drop
        alerts = rule.evaluate(stock_data, historical_data)

        # Should trigger all thresholds: -5, -10, -15, -20
        assert len(alerts) == 4

    def test_alert_severity_based_on_drop(self, rule, stock_data, historical_data):
        """Should set severity based on drop magnitude."""
        # -10.8% drop
        alerts = rule.evaluate(stock_data, historical_data)

        # -5% should be INFO, -10% should be WARNING
        severities = {a.metadata["threshold"]: a.severity for a in alerts}
        assert severities[-5] == AlertSeverity.INFO
        assert severities[-10] == AlertSeverity.WARNING

    def test_critical_severity_for_large_drop(self, rule, stock_data, historical_data):
        """Should set critical severity for large drops."""
        stock_data.current_price = 145.00  # vs 185 = -21.6% drop
        alerts = rule.evaluate(stock_data, historical_data)

        # -20% threshold should be CRITICAL
        critical_alerts = [a for a in alerts if a.metadata["threshold"] == -20]
        assert len(critical_alerts) == 1
        assert critical_alerts[0].severity == AlertSeverity.CRITICAL

    def test_alert_message_format(self, rule, stock_data, historical_data):
        """Should format alert message correctly."""
        alerts = rule.evaluate(stock_data, historical_data)

        for alert in alerts:
            assert "AAPL" in alert.message
            assert "monthly high" in alert.message.lower()
            assert "$" in alert.message  # Price formatting


class TestMonthlyLowRiseRule:
    """Test monthly low rise rule evaluation."""

    @pytest.fixture
    def rule(self):
        return MonthlyLowRiseRule(thresholds=[5, 7, 10])

    @pytest.fixture
    def stock_data(self):
        return StockData(
            ticker="SPY",
            current_price=110.00,
            previous_close=108.00,
            open_price=108.50,
            high=111.00,
            low=107.50,
            volume=80_000_000,
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def historical_data(self):
        return HistoricalData(
            ticker="SPY",
            monthly_high=115.00,
            monthly_low=100.00,  # Current price 110 = +10% rise
            avg_volume_20d=70_000_000,
            prices=[],
            volumes=[],
        )

    def test_triggers_on_threshold_breach(self, rule, stock_data, historical_data):
        """Should trigger all thresholds when price rises enough."""
        alerts = rule.evaluate(stock_data, historical_data)

        # Price 110 vs low 100 = +10%, should trigger 5%, 7%, 10% thresholds
        assert len(alerts) == 3
        thresholds_triggered = [a.metadata["threshold"] for a in alerts]
        assert 5 in thresholds_triggered
        assert 7 in thresholds_triggered
        assert 10 in thresholds_triggered

    def test_no_alert_when_below_threshold(self, rule, stock_data, historical_data):
        """Should not trigger when rise is below all thresholds."""
        historical_data.monthly_low = 108.00  # Current 110 = +1.9% rise
        alerts = rule.evaluate(stock_data, historical_data)

        assert len(alerts) == 0

    def test_triggers_partial_thresholds(self, rule, stock_data, historical_data):
        """Should trigger only thresholds that are met."""
        historical_data.monthly_low = 103.00  # Current 110 = +6.8% rise
        alerts = rule.evaluate(stock_data, historical_data)

        # Only 5% threshold met, not 7% or 10%
        assert len(alerts) == 1
        assert alerts[0].metadata["threshold"] == 5

    def test_alert_severity_info_for_small_rise(self, rule, stock_data, historical_data):
        """Should set INFO severity for 5% threshold."""
        historical_data.monthly_low = 103.00  # +6.8%, triggers 5% only
        alerts = rule.evaluate(stock_data, historical_data)

        assert alerts[0].severity == AlertSeverity.INFO

    def test_alert_severity_warning_for_7pct(self, rule, stock_data, historical_data):
        """Should set WARNING severity for 7% threshold."""
        historical_data.monthly_low = 102.00  # Current 110 = +7.8%, triggers 5% and 7%
        alerts = rule.evaluate(stock_data, historical_data)

        severities = {a.metadata["threshold"]: a.severity for a in alerts}
        assert severities[5] == AlertSeverity.INFO
        assert severities[7] == AlertSeverity.WARNING

    def test_alert_severity_critical_for_10pct(self, rule, stock_data, historical_data):
        """Should set CRITICAL severity for 10% threshold."""
        alerts = rule.evaluate(stock_data, historical_data)

        critical_alerts = [a for a in alerts if a.metadata["threshold"] == 10]
        assert len(critical_alerts) == 1
        assert critical_alerts[0].severity == AlertSeverity.CRITICAL

    def test_alert_message_format(self, rule, stock_data, historical_data):
        """Should format alert message correctly."""
        alerts = rule.evaluate(stock_data, historical_data)

        for alert in alerts:
            assert "SPY" in alert.message
            assert "monthly low" in alert.message.lower()
            assert "$" in alert.message

    def test_no_historical_data_returns_empty(self, rule, stock_data):
        """Should return empty list when no historical data."""
        alerts = rule.evaluate(stock_data, None)

        assert len(alerts) == 0

    def test_rule_engine_creates_monthly_low_rise_rule(self):
        """RuleEngine should instantiate MonthlyLowRiseRule from UserRule."""
        from src.rules.engine import RuleEngine
        from src.database.models import UserRule

        engine = RuleEngine()
        user_rule = UserRule(
            id=1,
            user_id=1,
            rule_type="monthly_low_rise",
            parameters={"thresholds": [5, 7, 10]},
            enabled=True,
        )
        rule = engine.create_rule(user_rule)

        assert isinstance(rule, MonthlyLowRiseRule)
        assert rule.thresholds == [5, 7, 10]


class TestPriceTargetRule:
    """Test price target rule evaluation."""

    REFERENCE_PRICE = 55.05

    @pytest.fixture
    def rule(self):
        return PriceTargetRule(
            reference_price=self.REFERENCE_PRICE,
            thresholds=[-10, -7, -5, -3, 3, 5, 7, 10],
        )

    def _make_stock(self, price: float) -> StockData:
        return StockData(
            ticker="DDM",
            current_price=price,
            previous_close=self.REFERENCE_PRICE,
            open_price=self.REFERENCE_PRICE,
            high=price,
            low=price,
            volume=1_000_000,
            timestamp=datetime.now(),
        )

    def test_rise_threshold_triggers(self, rule):
        """Should trigger rise thresholds when price is above reference."""
        # +5.45% rise, should trigger +3% and +5%
        stock = self._make_stock(58.05)
        alerts = rule.evaluate(stock, None)

        thresholds_triggered = [a.metadata["threshold"] for a in alerts]
        assert 3 in thresholds_triggered
        assert 5 in thresholds_triggered
        assert 7 not in thresholds_triggered

    def test_drop_threshold_triggers(self, rule):
        """Should trigger drop thresholds when price is below reference."""
        # -3.63% drop, should trigger -3%
        stock = self._make_stock(53.05)
        alerts = rule.evaluate(stock, None)

        thresholds_triggered = [a.metadata["threshold"] for a in alerts]
        assert -3 in thresholds_triggered
        assert -5 not in thresholds_triggered

    def test_no_alert_within_band(self, rule):
        """Should not trigger when price is within all thresholds."""
        # ~+1% change
        stock = self._make_stock(55.60)
        alerts = rule.evaluate(stock, None)

        assert len(alerts) == 0

    def test_partial_thresholds_triggered(self, rule):
        """Should trigger only thresholds that are met."""
        # -5.45% drop — should trigger -3% and -5%, not -7% or -10%
        stock = self._make_stock(52.05)
        alerts = rule.evaluate(stock, None)

        thresholds_triggered = [a.metadata["threshold"] for a in alerts]
        assert -3 in thresholds_triggered
        assert -5 in thresholds_triggered
        assert -7 not in thresholds_triggered
        assert -10 not in thresholds_triggered

    def test_severity_info_for_small_threshold(self, rule):
        """Should set INFO severity for thresholds < 5%."""
        stock = self._make_stock(53.30)  # ~-3.2%, triggers -3%
        alerts = rule.evaluate(stock, None)

        info_alerts = [a for a in alerts if a.metadata["threshold"] == -3]
        assert len(info_alerts) == 1
        assert info_alerts[0].severity == AlertSeverity.INFO

    def test_severity_warning_for_5pct(self, rule):
        """Should set WARNING severity for thresholds >= 5% and < 10%."""
        stock = self._make_stock(52.29)  # ~-5.0%, triggers -3%, -5%
        alerts = rule.evaluate(stock, None)

        warning_alerts = [a for a in alerts if a.metadata["threshold"] == -5]
        assert len(warning_alerts) == 1
        assert warning_alerts[0].severity == AlertSeverity.WARNING

    def test_severity_critical_for_10pct(self, rule):
        """Should set CRITICAL severity for thresholds >= 10%."""
        stock = self._make_stock(49.00)  # ~-11%, triggers all negative thresholds
        alerts = rule.evaluate(stock, None)

        critical_alerts = [a for a in alerts if a.metadata["threshold"] == -10]
        assert len(critical_alerts) == 1
        assert critical_alerts[0].severity == AlertSeverity.CRITICAL

    def test_message_contains_reference_price(self, rule):
        """Message should include the reference price."""
        stock = self._make_stock(57.80)
        alerts = rule.evaluate(stock, None)

        assert len(alerts) > 0
        for alert in alerts:
            assert "55.05" in alert.message

    def test_message_contains_current_price(self, rule):
        """Message should include the current price."""
        stock = self._make_stock(57.80)
        alerts = rule.evaluate(stock, None)

        assert len(alerts) > 0
        for alert in alerts:
            assert "57.80" in alert.message

    def test_historical_data_none_works(self, rule):
        """Should work correctly when historical_data is None."""
        stock = self._make_stock(49.00)
        alerts = rule.evaluate(stock, None)

        assert len(alerts) > 0

    def test_rule_engine_creates_price_target_rule(self):
        """RuleEngine should instantiate PriceTargetRule from UserRule."""
        engine = RuleEngine()
        user_rule = UserRule(
            id=1,
            user_id=1,
            rule_type="price_target",
            parameters={"reference_price": 55.05, "thresholds": [-10, -5, 5, 10]},
            enabled=True,
        )
        rule = engine.create_rule(user_rule)

        assert isinstance(rule, PriceTargetRule)
        assert rule.reference_price == 55.05
        assert rule.thresholds == [-10, -5, 5, 10]


class TestDailyChangeRule:
    """Test daily change rule evaluation."""

    @pytest.fixture
    def rule_both(self):
        """Create rule for both directions."""
        return DailyChangeRule(threshold=5.0, direction="both")

    @pytest.fixture
    def rule_up(self):
        """Create rule for upward movement only."""
        return DailyChangeRule(threshold=5.0, direction="up")

    @pytest.fixture
    def rule_down(self):
        """Create rule for downward movement only."""
        return DailyChangeRule(threshold=5.0, direction="down")

    def test_triggers_on_surge(self, rule_both):
        """Should trigger on price surge."""
        stock_data = StockData(
            ticker="TSLA",
            current_price=260.00,
            previous_close=240.00,  # +8.3% change
            open_price=242.00,
            high=262.00,
            low=241.00,
            volume=100_000_000,
            timestamp=datetime.now(),
        )
        alerts = rule_both.evaluate(stock_data, None)

        assert len(alerts) == 1
        assert "surge" in alerts[0].message.lower() or "+" in alerts[0].message

    def test_triggers_on_drop(self, rule_both):
        """Should trigger on price drop."""
        stock_data = StockData(
            ticker="TSLA",
            current_price=228.00,
            previous_close=240.00,  # -5% change
            open_price=238.00,
            high=240.00,
            low=226.00,
            volume=100_000_000,
            timestamp=datetime.now(),
        )
        alerts = rule_both.evaluate(stock_data, None)

        assert len(alerts) == 1
        assert "drop" in alerts[0].message.lower() or "-" in alerts[0].message

    def test_no_alert_below_threshold(self, rule_both):
        """Should not trigger for small changes."""
        stock_data = StockData(
            ticker="AAPL",
            current_price=172.00,
            previous_close=170.00,  # +1.2% change
            open_price=170.50,
            high=172.50,
            low=170.00,
            volume=50_000_000,
            timestamp=datetime.now(),
        )
        alerts = rule_both.evaluate(stock_data, None)

        assert len(alerts) == 0

    def test_up_direction_ignores_drops(self, rule_up):
        """Should ignore drops when direction is 'up'."""
        stock_data = StockData(
            ticker="TSLA",
            current_price=220.00,
            previous_close=240.00,  # -8.3% drop
            open_price=238.00,
            high=240.00,
            low=218.00,
            volume=100_000_000,
            timestamp=datetime.now(),
        )
        alerts = rule_up.evaluate(stock_data, None)

        assert len(alerts) == 0

    def test_down_direction_ignores_surges(self, rule_down):
        """Should ignore surges when direction is 'down'."""
        stock_data = StockData(
            ticker="TSLA",
            current_price=260.00,
            previous_close=240.00,  # +8.3% surge
            open_price=242.00,
            high=262.00,
            low=241.00,
            volume=100_000_000,
            timestamp=datetime.now(),
        )
        alerts = rule_down.evaluate(stock_data, None)

        assert len(alerts) == 0

    def test_alert_includes_change_percentage(self, rule_both):
        """Should include change percentage in alert."""
        stock_data = StockData(
            ticker="TSLA",
            current_price=260.00,
            previous_close=240.00,
            open_price=242.00,
            high=262.00,
            low=241.00,
            volume=100_000_000,
            timestamp=datetime.now(),
        )
        alerts = rule_both.evaluate(stock_data, None)

        assert "8.3" in alerts[0].message or "8.33" in alerts[0].message


class TestVolumeSpikeRule:
    """Test volume spike rule evaluation."""

    @pytest.fixture
    def rule(self):
        """Create volume spike rule."""
        return VolumeSpikeRule(multiplier=3.0, average_days=20)

    def test_triggers_on_volume_spike(self, rule):
        """Should trigger when volume exceeds multiplier."""
        stock_data = StockData(
            ticker="NVDA",
            current_price=480.00,
            previous_close=475.00,
            open_price=476.00,
            high=485.00,
            low=474.00,
            volume=150_000_000,  # 3.75x average
            timestamp=datetime.now(),
        )
        historical_data = HistoricalData(
            ticker="NVDA",
            monthly_high=500.00,
            monthly_low=400.00,
            avg_volume_20d=40_000_000,
            prices=[],
            volumes=[],
        )
        alerts = rule.evaluate(stock_data, historical_data)

        assert len(alerts) == 1
        assert "volume" in alerts[0].message.lower()
        assert "3.8" in alerts[0].message or "3.75" in alerts[0].message

    def test_no_alert_below_multiplier(self, rule):
        """Should not trigger when volume is below multiplier."""
        stock_data = StockData(
            ticker="NVDA",
            current_price=480.00,
            previous_close=475.00,
            open_price=476.00,
            high=485.00,
            low=474.00,
            volume=100_000_000,  # 2.5x average
            timestamp=datetime.now(),
        )
        historical_data = HistoricalData(
            ticker="NVDA",
            monthly_high=500.00,
            monthly_low=400.00,
            avg_volume_20d=40_000_000,
            prices=[],
            volumes=[],
        )
        alerts = rule.evaluate(stock_data, historical_data)

        assert len(alerts) == 0

    def test_alert_severity_based_on_multiplier(self, rule):
        """Should set severity based on volume ratio."""
        stock_data = StockData(
            ticker="NVDA",
            current_price=480.00,
            previous_close=475.00,
            open_price=476.00,
            high=485.00,
            low=474.00,
            volume=200_000_000,  # 5x average
            timestamp=datetime.now(),
        )
        historical_data = HistoricalData(
            ticker="NVDA",
            monthly_high=500.00,
            monthly_low=400.00,
            avg_volume_20d=40_000_000,
            prices=[],
            volumes=[],
        )
        alerts = rule.evaluate(stock_data, historical_data)

        assert alerts[0].severity == AlertSeverity.WARNING  # High volume spike


class TestCustomRule:
    """Test custom rule evaluation."""

    def test_price_below_condition(self):
        """Should trigger when price is below target."""
        rule = CustomRule(name="Buy signal", condition="price < 150")
        stock_data = StockData(
            ticker="AAPL",
            current_price=145.00,
            previous_close=148.00,
            open_price=147.00,
            high=149.00,
            low=144.00,
            volume=50_000_000,
            timestamp=datetime.now(),
        )
        alerts = rule.evaluate(stock_data, None)

        assert len(alerts) == 1
        assert "Buy signal" in alerts[0].message

    def test_price_above_condition(self):
        """Should trigger when price is above target."""
        rule = CustomRule(name="Take profit", condition="price > 200")
        stock_data = StockData(
            ticker="AAPL",
            current_price=205.00,
            previous_close=198.00,
            open_price=199.00,
            high=206.00,
            low=198.00,
            volume=50_000_000,
            timestamp=datetime.now(),
        )
        alerts = rule.evaluate(stock_data, None)

        assert len(alerts) == 1

    def test_daily_change_condition(self):
        """Should evaluate daily_change_pct variable."""
        rule = CustomRule(name="Big move", condition="daily_change_pct > 3")
        stock_data = StockData(
            ticker="TSLA",
            current_price=260.00,
            previous_close=250.00,  # +4% change
            open_price=251.00,
            high=262.00,
            low=250.00,
            volume=100_000_000,
            timestamp=datetime.now(),
        )
        alerts = rule.evaluate(stock_data, None)

        assert len(alerts) == 1

    def test_volume_condition(self):
        """Should evaluate volume variable."""
        rule = CustomRule(name="High volume", condition="volume > 100000000")
        stock_data = StockData(
            ticker="NVDA",
            current_price=480.00,
            previous_close=475.00,
            open_price=476.00,
            high=485.00,
            low=474.00,
            volume=150_000_000,
            timestamp=datetime.now(),
        )
        alerts = rule.evaluate(stock_data, None)

        assert len(alerts) == 1

    def test_compound_condition_and(self):
        """Should evaluate AND conditions."""
        rule = CustomRule(
            name="Bullish signal",
            condition="daily_change_pct > 3 and volume > 100000000",
        )
        stock_data = StockData(
            ticker="NVDA",
            current_price=500.00,
            previous_close=480.00,  # +4.2% change
            open_price=482.00,
            high=505.00,
            low=480.00,
            volume=150_000_000,
            timestamp=datetime.now(),
        )
        alerts = rule.evaluate(stock_data, None)

        assert len(alerts) == 1

    def test_compound_condition_fails_when_partial(self):
        """Should not trigger when only part of AND condition is met."""
        rule = CustomRule(
            name="Bullish signal",
            condition="daily_change_pct > 3 and volume > 100000000",
        )
        stock_data = StockData(
            ticker="NVDA",
            current_price=500.00,
            previous_close=480.00,  # +4.2% change
            open_price=482.00,
            high=505.00,
            low=480.00,
            volume=50_000_000,  # Low volume - fails condition
            timestamp=datetime.now(),
        )
        alerts = rule.evaluate(stock_data, None)

        assert len(alerts) == 0

    def test_or_condition(self):
        """Should evaluate OR conditions."""
        rule = CustomRule(
            name="Alert",
            condition="daily_change_pct > 5 or daily_change_pct < -5",
        )
        stock_data = StockData(
            ticker="TSLA",
            current_price=220.00,
            previous_close=240.00,  # -8.3% change
            open_price=238.00,
            high=240.00,
            low=218.00,
            volume=100_000_000,
            timestamp=datetime.now(),
        )
        alerts = rule.evaluate(stock_data, None)

        assert len(alerts) == 1

    def test_invalid_condition_raises_error(self):
        """Should raise error for invalid condition syntax."""
        with pytest.raises(ValueError):
            CustomRule(name="Invalid", condition="price ??? 100")

    def test_condition_with_historical_data(self):
        """Should evaluate conditions using historical data."""
        rule = CustomRule(
            name="Break monthly high",
            condition="price > monthly_high",
        )
        stock_data = StockData(
            ticker="AAPL",
            current_price=190.00,
            previous_close=185.00,
            open_price=186.00,
            high=191.00,
            low=185.00,
            volume=60_000_000,
            timestamp=datetime.now(),
        )
        historical_data = HistoricalData(
            ticker="AAPL",
            monthly_high=188.00,
            monthly_low=170.00,
            avg_volume_20d=50_000_000,
            prices=[],
            volumes=[],
        )
        alerts = rule.evaluate(stock_data, historical_data)

        assert len(alerts) == 1


class TestRuleEngine:
    """Test RuleEngine orchestration."""

    @pytest.fixture
    def engine(self):
        """Create rule engine."""
        return RuleEngine()

    def test_evaluate_multiple_rules(self, engine: RuleEngine):
        """Should evaluate multiple rules and collect all alerts."""
        rules = [
            UserRule(
                id=1,
                user_id=1,
                rule_type="monthly_high_drop",
                parameters={"thresholds": [-10]},
                enabled=True,
            ),
            UserRule(
                id=2,
                user_id=1,
                rule_type="daily_change",
                parameters={"threshold": 5, "direction": "both"},
                enabled=True,
            ),
        ]
        stock_data = StockData(
            ticker="AAPL",
            current_price=165.00,
            previous_close=155.00,  # +6.5% daily change
            open_price=156.00,
            high=166.00,
            low=155.00,
            volume=50_000_000,
            timestamp=datetime.now(),
        )
        historical_data = HistoricalData(
            ticker="AAPL",
            monthly_high=185.00,  # -10.8% drop
            monthly_low=160.00,
            avg_volume_20d=45_000_000,
            prices=[],
            volumes=[],
        )

        alerts = engine.evaluate_rules(rules, stock_data, historical_data)

        # Should trigger both rules
        assert len(alerts) == 2
        rule_types = {a.rule_type for a in alerts}
        assert "monthly_high_drop" in rule_types
        assert "daily_change" in rule_types

    def test_skip_disabled_rules(self, engine: RuleEngine):
        """Should skip disabled rules."""
        rules = [
            UserRule(
                id=1,
                user_id=1,
                rule_type="monthly_high_drop",
                parameters={"thresholds": [-10]},
                enabled=False,  # Disabled
            ),
        ]
        stock_data = StockData(
            ticker="AAPL",
            current_price=165.00,
            previous_close=170.00,
            open_price=169.00,
            high=171.00,
            low=164.00,
            volume=50_000_000,
            timestamp=datetime.now(),
        )
        historical_data = HistoricalData(
            ticker="AAPL",
            monthly_high=185.00,
            monthly_low=160.00,
            avg_volume_20d=45_000_000,
            prices=[],
            volumes=[],
        )

        alerts = engine.evaluate_rules(rules, stock_data, historical_data)

        assert len(alerts) == 0

    def test_create_rule_from_user_rule(self, engine: RuleEngine):
        """Should create appropriate rule instance from UserRule."""
        user_rule = UserRule(
            id=1,
            user_id=1,
            rule_type="volume_spike",
            parameters={"multiplier": 3.0, "average_days": 20},
            enabled=True,
        )

        rule = engine.create_rule(user_rule)

        assert isinstance(rule, VolumeSpikeRule)
        assert rule.multiplier == 3.0

    def test_unknown_rule_type_raises_error(self, engine: RuleEngine):
        """Should raise error for unknown rule type."""
        user_rule = UserRule(
            id=1,
            user_id=1,
            rule_type="unknown_rule",
            parameters={},
            enabled=True,
        )

        with pytest.raises(ValueError, match="Unknown rule type"):
            engine.create_rule(user_rule)

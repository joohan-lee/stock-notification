"""
Rule evaluation engine.
"""

from typing import Optional

from src.database.models import UserRule
from src.data.fetcher import StockData, HistoricalData
from .types import (
    Rule,
    Alert,
    AlertSeverity,
    MonthlyHighDropRule,
    DailyChangeRule,
    VolumeSpikeRule,
    CustomRule,
)

# Re-export for convenience
__all__ = ["RuleEngine", "Alert", "AlertSeverity"]


class RuleEngine:
    """Evaluates rules against stock data."""

    def evaluate_rules(
        self,
        rules: list[UserRule],
        stock_data: StockData,
        historical_data: Optional[HistoricalData],
    ) -> list[Alert]:
        """
        Evaluate multiple rules against stock data.

        Args:
            rules: List of user rules to evaluate
            stock_data: Current stock data
            historical_data: Historical data for the stock

        Returns:
            List of all triggered alerts
        """
        alerts = []

        for user_rule in rules:
            if not user_rule.enabled:
                continue

            try:
                rule = self.create_rule(user_rule)
                rule_alerts = rule.evaluate(stock_data, historical_data)
                alerts.extend(rule_alerts)
            except ValueError:
                # Skip invalid rules
                continue

        return alerts

    def create_rule(self, user_rule: UserRule) -> Rule:
        """
        Create a Rule instance from UserRule.

        Args:
            user_rule: User rule configuration

        Returns:
            Appropriate Rule instance

        Raises:
            ValueError: If rule type is unknown
        """
        rule_type = user_rule.rule_type
        params = user_rule.parameters

        if rule_type == "monthly_high_drop":
            thresholds = params.get("thresholds", [-5, -10, -15, -20])
            return MonthlyHighDropRule(thresholds=thresholds)

        elif rule_type == "daily_change":
            threshold = params.get("threshold", 5.0)
            direction = params.get("direction", "both")
            return DailyChangeRule(threshold=threshold, direction=direction)

        elif rule_type == "volume_spike":
            multiplier = params.get("multiplier", 3.0)
            average_days = params.get("average_days", 20)
            return VolumeSpikeRule(multiplier=multiplier, average_days=average_days)

        elif rule_type == "custom":
            name = params.get("name", "Custom Rule")
            condition = params.get("condition", "False")
            return CustomRule(name=name, condition=condition)

        else:
            raise ValueError(f"Unknown rule type: {rule_type}")

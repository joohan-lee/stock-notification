"""
Daily health check - sends a status message to Discord.
"""

import os
from datetime import datetime

import requests

from src.database.connection import Database
from src.database.repository import UserRepository, WatchlistRepository, RuleRepository


def run_healthcheck(db: Database) -> None:
    """Run health check and send status to Discord.

    Args:
        db: Database instance (already initialized)
    """
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL not set")
        return

    users = UserRepository(db).list_all()
    all_symbols = []
    all_rules = []
    for user in users:
        symbols = WatchlistRepository(db).get_user_watchlist(user.id)
        rules = RuleRepository(db).get_enabled_rules(user.id)
        all_symbols.extend(symbols)
        all_rules.extend(rules)

    symbol_list = ", ".join(s.ticker for s in all_symbols) or "None"
    rule_lines = []
    for r in all_rules:
        params = r.parameters
        if r.rule_type == "monthly_high_drop":
            thresholds = ", ".join(f"{t}%" for t in params.get("thresholds", []))
            rule_lines.append(f"Monthly High Drop: {thresholds}")
        elif r.rule_type == "daily_change":
            direction = params.get("direction", "both")
            threshold = params.get("threshold", "?")
            rule_lines.append(f"Daily Change: ±{threshold}% ({direction})")
        elif r.rule_type == "volume_spike":
            mult = params.get("multiplier", "?")
            rule_lines.append(f"Volume Spike: {mult}x avg")
        elif r.rule_type == "monthly_low_rise":
            thresholds = ", ".join(f"+{t}%" for t in params.get("thresholds", []))
            rule_lines.append(f"Monthly Low Rise: {thresholds}")
        else:
            name = params.get("name", r.rule_type)
            rule_lines.append(name)
    rule_list = "\n".join(rule_lines) or "None"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "embeds": [{
            "title": "Modo Weekly Health Check",
            "description": "System is running normally.",
            "color": 0x2ECC71,
            "fields": [
                {"name": "Users", "value": str(len(users)), "inline": True},
                {"name": "Watchlist", "value": symbol_list, "inline": True},
                {"name": "Rules", "value": rule_list, "inline": False},
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }]
    }

    response = requests.post(webhook_url, json=payload, timeout=10)
    print(f"{now} - Health check sent (status: {response.status_code})")

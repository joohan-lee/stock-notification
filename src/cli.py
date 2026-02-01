"""
CLI commands for Modo.
"""

import argparse
import json
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from src.database.connection import Database
from src.database.repository import (
    UserRepository,
    SymbolRepository,
    WatchlistRepository,
    RuleRepository,
)
from src.database.models import User, UserRule
from src.data.symbols import SymbolSyncer


def add_user(
    db: Database,
    email: Optional[str] = None,
    discord_webhook: Optional[str] = None,
) -> User:
    """Add a new user."""
    repo = UserRepository(db)
    user = User(email=email, discord_webhook_url=discord_webhook)
    return repo.create(user)


def add_to_watchlist(
    db: Database,
    user_id: int,
    tickers: list[str],
) -> dict:
    """Add symbols to user's watchlist."""
    symbol_repo = SymbolRepository(db)
    watchlist_repo = WatchlistRepository(db)

    added = []
    not_found = []

    for ticker in tickers:
        symbol = symbol_repo.get_by_ticker(ticker.upper())
        if symbol:
            try:
                watchlist_repo.add(user_id, symbol.id)
                added.append(ticker.upper())
            except Exception:
                # Already in watchlist
                pass
        else:
            not_found.append(ticker.upper())

    return {"added": added, "not_found": not_found}


def sync_symbols(db: Database) -> dict:
    """Sync symbols from external sources."""
    syncer = SymbolSyncer()
    symbols = syncer.fetch_all_symbols()

    symbol_repo = SymbolRepository(db)
    symbol_repo.bulk_upsert(symbols)

    return {"synced": len(symbols)}


def list_symbols(
    db: Database,
    search: Optional[str] = None,
    symbol_type: Optional[str] = None,
) -> list:
    """List symbols with optional filtering."""
    repo = SymbolRepository(db)

    if search:
        return repo.search(search)
    elif symbol_type:
        return repo.list_by_type(symbol_type)
    else:
        return repo.list_all()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Modo CLI")
    parser.add_argument("--db", default="data/modo.db", help="Database path")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # User commands
    user_parser = subparsers.add_parser("user", help="User management")
    user_subparsers = user_parser.add_subparsers(dest="action")

    add_user_parser = user_subparsers.add_parser("add", help="Add user")
    add_user_parser.add_argument("--email", help="User email")
    add_user_parser.add_argument("--discord", help="Discord webhook URL")

    user_subparsers.add_parser("list", help="List users")

    # Watchlist commands
    watchlist_parser = subparsers.add_parser("watchlist", help="Watchlist management")
    watchlist_subparsers = watchlist_parser.add_subparsers(dest="action")

    add_watchlist_parser = watchlist_subparsers.add_parser("add", help="Add to watchlist")
    add_watchlist_parser.add_argument("--user", type=int, required=True, help="User ID")
    add_watchlist_parser.add_argument(
        "--symbols", required=True, help="Comma-separated symbols"
    )

    show_watchlist_parser = watchlist_subparsers.add_parser("show", help="Show watchlist")
    show_watchlist_parser.add_argument("--user", type=int, required=True, help="User ID")

    # Symbol commands
    symbol_parser = subparsers.add_parser("symbols", help="Symbol management")
    symbol_subparsers = symbol_parser.add_subparsers(dest="action")

    symbol_subparsers.add_parser("sync", help="Sync symbols from API")

    list_symbols_parser = symbol_subparsers.add_parser("list", help="List symbols")
    list_symbols_parser.add_argument("--search", help="Search query")
    list_symbols_parser.add_argument("--type", help="Symbol type filter")

    # Rules commands
    rules_parser = subparsers.add_parser("rules", help="Rules management")
    rules_subparsers = rules_parser.add_subparsers(dest="action")

    add_rule_parser = rules_subparsers.add_parser("add", help="Add rule")
    add_rule_parser.add_argument("--user", type=int, required=True, help="User ID")
    add_rule_parser.add_argument(
        "--type",
        required=True,
        choices=["monthly_high_drop", "daily_change", "volume_spike", "custom"],
    )
    add_rule_parser.add_argument("--params", required=True, help="JSON parameters")

    # DB commands
    db_parser = subparsers.add_parser("db", help="Database management")
    db_subparsers = db_parser.add_subparsers(dest="action")
    db_subparsers.add_parser("status", help="Check migration status")
    db_subparsers.add_parser("migrate", help="Run migrations")
    db_subparsers.add_parser("rollback", help="Rollback last migration")

    args = parser.parse_args()

    # Initialize database
    db = Database(args.db)
    db.initialize()

    # Handle commands
    if args.command == "user":
        if args.action == "add":
            user = add_user(db, email=args.email, discord_webhook=args.discord)
            print(f"Created user with ID: {user.id}")
        elif args.action == "list":
            repo = UserRepository(db)
            for user in repo.list_all():
                print(f"ID: {user.id}, Email: {user.email}")

    elif args.command == "watchlist":
        if args.action == "add":
            tickers = [t.strip() for t in args.symbols.split(",")]
            result = add_to_watchlist(db, args.user, tickers)
            print(f"Added: {result['added']}")
            if result["not_found"]:
                print(f"Not found: {result['not_found']}")
        elif args.action == "show":
            repo = WatchlistRepository(db)
            symbols = repo.get_user_watchlist(args.user)
            for s in symbols:
                print(f"{s.ticker}: {s.name}")

    elif args.command == "symbols":
        if args.action == "sync":
            result = sync_symbols(db)
            print(f"Synced {result['synced']} symbols")
        elif args.action == "list":
            symbols = list_symbols(db, search=args.search, symbol_type=args.type)
            for s in symbols[:50]:  # Limit output
                print(f"{s.ticker}: {s.name} ({s.type})")
            if len(symbols) > 50:
                print(f"... and {len(symbols) - 50} more")

    elif args.command == "rules":
        if args.action == "add":
            repo = RuleRepository(db)
            rule = UserRule(
                user_id=args.user,
                rule_type=args.type,
                parameters=json.loads(args.params),
                enabled=True,
            )
            created = repo.create(rule)
            print(f"Created rule with ID: {created.id}")

    elif args.command == "db":
        if args.action == "status":
            print("Database initialized")
        elif args.action == "migrate":
            db.initialize()
            print("Migrations applied")
        elif args.action == "rollback":
            print("Rollback not yet implemented")

    db.close()


if __name__ == "__main__":
    main()

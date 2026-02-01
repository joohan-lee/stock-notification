"""
Symbol syncing from external sources.
"""

from typing import Optional
import requests

from src.database.models import Symbol


class SymbolSyncer:
    """Syncs stock symbols from external sources."""

    NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
    NYSE_URL = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"

    def fetch_nasdaq_symbols(self) -> list[Symbol]:
        """
        Fetch NASDAQ listed symbols.

        Returns:
            List of Symbol objects
        """
        try:
            response = requests.get(self.NASDAQ_URL, timeout=30)
            response.raise_for_status()
            return self._parse_nasdaq_response(response.text)
        except requests.RequestException:
            return []

    def fetch_nyse_symbols(self) -> list[Symbol]:
        """
        Fetch NYSE and other exchange symbols.

        Returns:
            List of Symbol objects
        """
        try:
            response = requests.get(self.NYSE_URL, timeout=30)
            response.raise_for_status()
            return self._parse_nyse_response(response.text)
        except requests.RequestException:
            return []

    def fetch_all_symbols(self) -> list[Symbol]:
        """
        Fetch all symbols from all sources.

        Returns:
            Combined list of Symbol objects
        """
        symbols = []
        symbols.extend(self.fetch_nasdaq_symbols())
        symbols.extend(self.fetch_nyse_symbols())
        return symbols

    def _parse_nasdaq_response(self, text: str) -> list[Symbol]:
        """Parse NASDAQ symbol list response."""
        symbols = []
        lines = text.strip().split("\n")

        # Skip header line
        for line in lines[1:]:
            if line.startswith("File Creation Time"):
                continue

            parts = line.split("|")
            if len(parts) >= 2:
                ticker = parts[0].strip()
                name = parts[1].strip()

                # Skip test issues and empty tickers
                if not ticker or len(parts) > 3 and parts[3].strip() == "Y":
                    continue

                # Determine if ETF
                is_etf = len(parts) > 6 and parts[6].strip() == "Y"

                symbols.append(
                    Symbol(
                        ticker=ticker,
                        name=name,
                        type="etf" if is_etf else "stock",
                        exchange="NASDAQ",
                    )
                )

        return symbols

    def _parse_nyse_response(self, text: str) -> list[Symbol]:
        """Parse NYSE/other exchanges symbol list response."""
        symbols = []
        lines = text.strip().split("\n")

        # Skip header line
        for line in lines[1:]:
            if line.startswith("File Creation Time"):
                continue

            parts = line.split("|")
            if len(parts) >= 3:
                ticker = parts[0].strip()
                name = parts[1].strip()
                exchange = parts[2].strip()

                # Skip empty tickers
                if not ticker:
                    continue

                # Determine if ETF
                is_etf = len(parts) > 4 and parts[4].strip() == "Y"

                symbols.append(
                    Symbol(
                        ticker=ticker,
                        name=name,
                        type="etf" if is_etf else "stock",
                        exchange=exchange or "NYSE",
                    )
                )

        return symbols

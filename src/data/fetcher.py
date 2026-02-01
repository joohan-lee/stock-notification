"""
Yahoo Finance data fetcher.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import yfinance as yf


@dataclass
class StockData:
    """Current stock data."""

    ticker: str
    current_price: float
    previous_close: float
    open_price: float
    high: float
    low: float
    volume: int
    timestamp: datetime

    @property
    def daily_change_pct(self) -> float:
        """Calculate daily change percentage."""
        if self.previous_close == 0:
            return 0.0
        return ((self.current_price - self.previous_close) / self.previous_close) * 100


@dataclass
class HistoricalData:
    """Historical stock data."""

    ticker: str
    monthly_high: float
    monthly_low: float
    avg_volume_20d: float
    prices: list[float]
    volumes: list[int]

    def drop_from_high(self, current_price: float) -> float:
        """Calculate drop percentage from monthly high."""
        if self.monthly_high == 0:
            return 0.0
        return ((current_price - self.monthly_high) / self.monthly_high) * 100

    def volume_ratio(self, current_volume: int) -> float:
        """Calculate volume ratio vs average."""
        if self.avg_volume_20d == 0:
            return 0.0
        return current_volume / self.avg_volume_20d


class StockDataFetcher:
    """Fetches stock data from Yahoo Finance."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def get_current_data(self, ticker: str) -> StockData:
        """
        Fetch current stock data.

        Args:
            ticker: Stock symbol (e.g., "AAPL")

        Returns:
            StockData with current price info

        Raises:
            ValueError: If symbol is invalid or data unavailable
        """
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or "regularMarketPrice" not in info and "previousClose" not in info:
            raise ValueError(f"Invalid symbol or no data available: {ticker}")

        # Use regularMarketPrice if available, otherwise fall back to previousClose
        current_price = info.get("regularMarketPrice")
        if current_price is None:
            current_price = info.get("previousClose")

        if current_price is None:
            raise ValueError(f"Invalid symbol or no data available: {ticker}")

        return StockData(
            ticker=ticker,
            current_price=current_price,
            previous_close=info.get("previousClose", current_price),
            open_price=info.get("open", current_price),
            high=info.get("dayHigh", current_price),
            low=info.get("dayLow", current_price),
            volume=info.get("volume", 0),
            timestamp=datetime.now(),
        )

    def get_historical_data(self, ticker: str, days: int = 30) -> HistoricalData:
        """
        Fetch historical stock data.

        Args:
            ticker: Stock symbol
            days: Number of days of history to fetch

        Returns:
            HistoricalData with price and volume history
        """
        stock = yf.Ticker(ticker)
        period = f"{days}d"
        hist = stock.history(period=period)

        if hist.empty:
            raise ValueError(f"No historical data available: {ticker}")

        prices = hist["Close"].tolist()
        volumes = hist["Volume"].astype(int).tolist()

        # Calculate 20-day average volume
        volume_20d = volumes[-20:] if len(volumes) >= 20 else volumes
        avg_volume = sum(volume_20d) / len(volume_20d) if volume_20d else 0

        return HistoricalData(
            ticker=ticker,
            monthly_high=max(prices) if prices else 0,
            monthly_low=min(prices) if prices else 0,
            avg_volume_20d=avg_volume,
            prices=prices,
            volumes=volumes,
        )

    def get_multiple_current_data(
        self, tickers: list[str]
    ) -> dict[str, StockData]:
        """
        Fetch current data for multiple symbols.

        Args:
            tickers: List of stock symbols

        Returns:
            Dictionary mapping ticker to StockData
        """
        results = {}
        for ticker in tickers:
            try:
                results[ticker] = self.get_current_data(ticker)
            except ValueError:
                # Skip invalid symbols
                continue
        return results

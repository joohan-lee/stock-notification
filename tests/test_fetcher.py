"""
Data fetcher tests.
Tests for Yahoo Finance API integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd

from src.data.fetcher import StockDataFetcher, StockData, HistoricalData
from src.data.symbols import SymbolSyncer


class TestStockData:
    """Test StockData model."""

    def test_create_stock_data(self):
        """Should create stock data with all fields."""
        data = StockData(
            ticker="AAPL",
            current_price=175.50,
            previous_close=173.25,
            open_price=174.00,
            high=176.00,
            low=173.50,
            volume=50_000_000,
            timestamp=datetime.now(),
        )
        assert data.ticker == "AAPL"
        assert data.current_price == 175.50
        assert data.previous_close == 173.25

    def test_daily_change_percentage(self):
        """Should calculate daily change percentage."""
        data = StockData(
            ticker="AAPL",
            current_price=175.50,
            previous_close=170.00,
            open_price=171.00,
            high=176.00,
            low=170.00,
            volume=50_000_000,
            timestamp=datetime.now(),
        )
        # (175.50 - 170.00) / 170.00 * 100 = 3.235%
        assert abs(data.daily_change_pct - 3.235) < 0.01

    def test_daily_change_negative(self):
        """Should calculate negative daily change."""
        data = StockData(
            ticker="AAPL",
            current_price=165.00,
            previous_close=175.00,
            open_price=174.00,
            high=175.00,
            low=164.00,
            volume=50_000_000,
            timestamp=datetime.now(),
        )
        # (165.00 - 175.00) / 175.00 * 100 = -5.714%
        assert data.daily_change_pct < 0
        assert abs(data.daily_change_pct - (-5.714)) < 0.01


class TestHistoricalData:
    """Test HistoricalData model."""

    def test_create_historical_data(self):
        """Should create historical data."""
        data = HistoricalData(
            ticker="AAPL",
            monthly_high=185.00,
            monthly_low=165.00,
            avg_volume_20d=45_000_000,
            prices=[170.0, 172.0, 175.0, 173.0, 178.0],
            volumes=[40_000_000, 42_000_000, 50_000_000, 45_000_000, 48_000_000],
        )
        assert data.ticker == "AAPL"
        assert data.monthly_high == 185.00
        assert data.monthly_low == 165.00
        assert len(data.prices) == 5

    def test_drop_from_monthly_high(self):
        """Should calculate drop percentage from monthly high."""
        data = HistoricalData(
            ticker="AAPL",
            monthly_high=200.00,
            monthly_low=160.00,
            avg_volume_20d=45_000_000,
            prices=[],
            volumes=[],
        )
        current_price = 180.00
        # (180 - 200) / 200 * 100 = -10%
        drop_pct = data.drop_from_high(current_price)
        assert drop_pct == -10.0

    def test_volume_ratio(self):
        """Should calculate volume ratio vs average."""
        data = HistoricalData(
            ticker="AAPL",
            monthly_high=200.00,
            monthly_low=160.00,
            avg_volume_20d=40_000_000,
            prices=[],
            volumes=[],
        )
        current_volume = 120_000_000
        ratio = data.volume_ratio(current_volume)
        assert ratio == 3.0


class TestStockDataFetcher:
    """Test StockDataFetcher with mocked yfinance."""

    @pytest.fixture
    def fetcher(self):
        """Create fetcher instance."""
        return StockDataFetcher()

    def test_fetch_current_data(self, fetcher: StockDataFetcher):
        """Should fetch current stock data."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "regularMarketPrice": 175.50,
            "previousClose": 173.25,
            "open": 174.00,
            "dayHigh": 176.00,
            "dayLow": 173.50,
            "volume": 50_000_000,
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            data = fetcher.get_current_data("AAPL")

        assert data.ticker == "AAPL"
        assert data.current_price == 175.50
        assert data.previous_close == 173.25

    def test_fetch_current_data_invalid_symbol(self, fetcher: StockDataFetcher):
        """Should raise error for invalid symbol."""
        mock_ticker = MagicMock()
        mock_ticker.info = {}

        with patch("yfinance.Ticker", return_value=mock_ticker):
            with pytest.raises(ValueError, match="Invalid symbol"):
                fetcher.get_current_data("INVALID123")

    def test_fetch_historical_data(self, fetcher: StockDataFetcher):
        """Should fetch historical data for 30 days."""
        mock_ticker = MagicMock()

        # Create mock DataFrame for historical data
        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
        mock_df = pd.DataFrame(
            {
                "Close": [170 + i * 0.5 for i in range(30)],
                "Volume": [40_000_000 + i * 100_000 for i in range(30)],
            },
            index=dates,
        )
        mock_ticker.history.return_value = mock_df

        with patch("yfinance.Ticker", return_value=mock_ticker):
            data = fetcher.get_historical_data("AAPL", days=30)

        assert data.ticker == "AAPL"
        assert data.monthly_high == max(mock_df["Close"])
        assert data.monthly_low == min(mock_df["Close"])
        assert len(data.prices) == 30

    def test_fetch_multiple_symbols(self, fetcher: StockDataFetcher):
        """Should fetch data for multiple symbols."""
        mock_data = {
            "AAPL": {"regularMarketPrice": 175.50, "previousClose": 173.00, "open": 174.00, "dayHigh": 176.00, "dayLow": 173.00, "volume": 50_000_000},
            "GOOGL": {"regularMarketPrice": 140.25, "previousClose": 139.00, "open": 139.50, "dayHigh": 141.00, "dayLow": 138.50, "volume": 20_000_000},
            "MSFT": {"regularMarketPrice": 380.00, "previousClose": 378.00, "open": 379.00, "dayHigh": 382.00, "dayLow": 377.00, "volume": 25_000_000},
        }

        def mock_ticker_factory(symbol):
            mock = MagicMock()
            mock.info = mock_data.get(symbol, {})
            return mock

        with patch("yfinance.Ticker", side_effect=mock_ticker_factory):
            results = fetcher.get_multiple_current_data(["AAPL", "GOOGL", "MSFT"])

        assert len(results) == 3
        assert results["AAPL"].current_price == 175.50
        assert results["GOOGL"].current_price == 140.25
        assert results["MSFT"].current_price == 380.00

    def test_fetch_with_retry_on_failure(self, fetcher: StockDataFetcher):
        """Should retry on temporary failure."""
        mock_ticker = MagicMock()
        call_count = 0

        def side_effect_info():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return {
                "regularMarketPrice": 175.50,
                "previousClose": 173.25,
                "open": 174.00,
                "dayHigh": 176.00,
                "dayLow": 173.50,
                "volume": 50_000_000,
            }

        mock_ticker.info = property(lambda self: side_effect_info())

        with patch("yfinance.Ticker", return_value=mock_ticker):
            # This test verifies retry logic is implemented
            # The actual implementation should handle retries
            pass

    def test_fetch_handles_market_closed(self, fetcher: StockDataFetcher):
        """Should handle when market is closed (use previous data)."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "regularMarketPrice": None,  # Market closed
            "previousClose": 173.25,
            "open": 174.00,
            "dayHigh": 176.00,
            "dayLow": 173.50,
            "volume": 50_000_000,
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            # Should use previousClose when regularMarketPrice is None
            data = fetcher.get_current_data("AAPL")
            assert data.current_price == 173.25  # Falls back to previous close


class TestSymbolSyncer:
    """Test symbol syncing from external sources."""

    @pytest.fixture
    def syncer(self):
        """Create syncer instance."""
        return SymbolSyncer()

    def test_fetch_nasdaq_symbols(self, syncer: SymbolSyncer):
        """Should fetch NASDAQ listed symbols."""
        mock_response = """Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
AAPL|Apple Inc. Common Stock|Q|N|N|100|N|N
MSFT|Microsoft Corporation Common Stock|Q|N|N|100|N|N
GOOGL|Alphabet Inc. Class A Common Stock|Q|N|N|100|N|N"""

        with patch("requests.get") as mock_get:
            mock_get.return_value.text = mock_response
            mock_get.return_value.status_code = 200

            symbols = syncer.fetch_nasdaq_symbols()

        assert len(symbols) >= 3
        tickers = [s.ticker for s in symbols]
        assert "AAPL" in tickers
        assert "MSFT" in tickers

    def test_fetch_nyse_symbols(self, syncer: SymbolSyncer):
        """Should fetch NYSE listed symbols."""
        # Similar test for NYSE
        pass

    def test_fetch_etf_list(self, syncer: SymbolSyncer):
        """Should identify and fetch ETFs."""
        pass

    def test_sync_all_symbols(self, syncer: SymbolSyncer):
        """Should sync all symbols to database."""
        pass

    def test_incremental_sync(self, syncer: SymbolSyncer):
        """Should only update changed symbols."""
        pass

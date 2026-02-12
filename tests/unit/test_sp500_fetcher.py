"""
Unit Tests for SP500 Index Fetcher

Tests the SP500Fetcher class with mocked HTTP responses and edge cases
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# Add backend path for imports
sys.path.insert(0, "/home/ubuntupunk/Projects/stock-analyzer/infrastructure/backend")


class TestSP500FetcherInitialization:
    """Test SP500Fetcher initialization and configuration"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "sp500",
            "name": "S&P 500",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "exchangeSuffix": "",
            "dataSource": "wikipedia",
            "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        }

    def test_initialization_with_valid_config(self):
        """Test SP500Fetcher initializes correctly with valid config"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        fetcher = SP500Fetcher(self.test_config)

        assert fetcher.id == "sp500"
        assert fetcher.name == "S&P 500"
        assert fetcher.region == "US"
        assert fetcher.currency == "USD"
        assert fetcher.exchange == "NYSE"
        assert (
            fetcher.url == "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )

    def test_initialization_inherits_from_base(self):
        """Test SP500Fetcher inherits from IndexFetcher"""
        from index_fetchers.sp500_fetcher import SP500Fetcher
        from index_fetchers.base import IndexFetcher

        fetcher = SP500Fetcher(self.test_config)

        assert isinstance(fetcher, IndexFetcher)


class TestSP500FetcherFetchConstituents:
    """Test fetch_constituents method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "sp500",
            "name": "S&P 500",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "exchangeSuffix": "",
            "dataSource": "wikipedia",
            "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        }

    def create_mock_wikipedia_data(self):
        """Create mock Wikipedia table data"""
        return pd.DataFrame(
            {
                "Symbol": ["AAPL", "MSFT", "GOOGL"],
                "Security": ["Apple Inc.", "Microsoft Corporation", "Alphabet Inc."],
                "GICS Sector": [
                    "Information Technology",
                    "Information Technology",
                    "Communication Services",
                ],
                "GICS Sub-Industry": [
                    "Technology Hardware, Storage & Peripherals",
                    "Software",
                    "Interactive Media & Services",
                ],
                "Headquarters Location": [
                    "Cupertino, California",
                    "Redmond, Washington",
                    "Mountain View, California",
                ],
                "Date added": ["1982-11-30", "1994-06-01", "2006-04-03"],
                "CIK": ["0000320193", "0000789019", "0001652044"],
                "Founded": ["1977", "1975", "1998"],
            }
        )

    @patch("pandas.read_html")
    def test_fetch_constituents_success(self, mock_read_html):
        """Test successful fetch from Wikipedia"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        # Setup mock
        mock_df = self.create_mock_wikipedia_data()
        mock_read_html.return_value = [mock_df]

        fetcher = SP500Fetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        # Assertions
        assert len(stocks) == 3
        assert stocks[0]["symbol"] == "AAPL"
        assert stocks[0]["name"] == "Apple Inc."
        assert stocks[0]["sector"] == "Information Technology"
        assert stocks[0]["subSector"] == "Technology Hardware, Storage & Peripherals"
        assert stocks[0]["headquarters"] == "Cupertino, California"
        assert stocks[0]["region"] == "US"
        assert stocks[0]["currency"] == "USD"
        assert stocks[0]["exchange"] == "NYSE"

        mock_read_html.assert_called_once()

    @patch("pandas.read_html")
    def test_fetch_constituents_normalizes_symbols(self, mock_read_html):
        """Test that symbols with dots are normalized to hyphens"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        # Setup mock with BRK.B
        mock_df = pd.DataFrame(
            {
                "Symbol": ["BRK.B", "BF.B"],
                "Security": ["Berkshire Hathaway", "Brown-Forman"],
                "GICS Sector": ["Financials", "Consumer Staples"],
                "GICS Sub-Industry": ["Insurance", "Beverages"],
                "Headquarters Location": ["Omaha, Nebraska", "Louisville, Kentucky"],
            }
        )
        mock_read_html.return_value = [mock_df]

        fetcher = SP500Fetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        # Symbols should have dots replaced with hyphens
        assert stocks[0]["symbol"] == "BRK-B"
        assert stocks[1]["symbol"] == "BF-B"

    @patch("pandas.read_html")
    def test_fetch_constituents_handles_nan_headquarters(self, mock_read_html):
        """Test handling of NaN values in headquarters column"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        # Setup mock with NaN headquarters
        mock_df = pd.DataFrame(
            {
                "Symbol": ["AAPL"],
                "Security": ["Apple Inc."],
                "GICS Sector": ["Information Technology"],
                "GICS Sub-Industry": ["Software"],
                "Headquarters Location": [float("nan")],
            }
        )
        mock_read_html.return_value = [mock_df]

        fetcher = SP500Fetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        # Should not include headquarters key when value is NaN
        assert "headquarters" not in stocks[0]

    @patch("pandas.read_html")
    def test_fetch_constituents_empty_response(self, mock_read_html):
        """Test handling of empty Wikipedia table"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        # Setup mock with empty table
        mock_df = pd.DataFrame(
            {
                "Symbol": [],
                "Security": [],
                "GICS Sector": [],
                "GICS Sub-Industry": [],
                "Headquarters Location": [],
            }
        )
        mock_read_html.return_value = [mock_df]

        fetcher = SP500Fetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        # Should return empty list
        assert stocks == []

    @patch("pandas.read_html")
    def test_fetch_constituents_network_error(self, mock_read_html):
        """Test handling of network errors"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        # Setup mock to raise exception
        mock_read_html.side_effect = Exception("Connection timeout")

        fetcher = SP500Fetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        # Should return fallback data
        assert len(stocks) > 0
        assert stocks[0]["symbol"] == "AAPL"  # First fallback stock

    @patch("pandas.read_html")
    def test_fetch_constituents_malformed_html(self, mock_read_html):
        """Test handling of malformed HTML"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        # Setup mock to raise exception
        mock_read_html.side_effect = ValueError("No tables found")

        fetcher = SP500Fetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        # Should return fallback data
        assert len(stocks) > 0

    @patch("pandas.read_html")
    def test_fetch_constituents_missing_columns(self, mock_read_html):
        """Test handling of missing required columns - falls back gracefully"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        # Setup mock with missing columns
        mock_df = pd.DataFrame({"Symbol": ["AAPL"], "WrongColumn": ["Test"]})
        mock_read_html.return_value = [mock_df]

        fetcher = SP500Fetcher(self.test_config)

        # Should fallback gracefully instead of raising KeyError
        stocks = fetcher.fetch_constituents()
        assert len(stocks) > 0
        # Verify we got fallback data (AAPL should be in fallback)
        symbols = [s["symbol"] for s in stocks]
        assert "AAPL" in symbols

    def test_fetch_constituents_uses_correct_headers(self):
        """Test that proper User-Agent headers are sent"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        with patch("pandas.read_html") as mock_read_html:
            mock_df = self.create_mock_wikipedia_data()
            mock_read_html.return_value = [mock_df]

            fetcher = SP500Fetcher(self.test_config)
            fetcher.fetch_constituents()

            # Check that headers were passed
            call_args = mock_read_html.call_args
            assert "storage_options" in call_args.kwargs
            headers = call_args.kwargs["storage_options"]
            assert "User-Agent" in headers
            assert "Mozilla/5.0" in headers["User-Agent"]


class TestSP500FetcherFallback:
    """Test fallback functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "sp500",
            "name": "S&P 500",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "exchangeSuffix": "",
            "dataSource": "wikipedia",
            "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        }

    def test_fallback_returns_valid_stocks(self):
        """Test that fallback method returns properly formatted stocks"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        fetcher = SP500Fetcher(self.test_config)
        stocks = fetcher._get_fallback()

        # Check structure
        assert len(stocks) > 0
        for stock in stocks:
            assert "symbol" in stock
            assert "name" in stock
            assert "sector" in stock
            assert "subSector" in stock
            assert "region" in stock
            assert "currency" in stock
            assert "exchange" in stock

            assert isinstance(stock["symbol"], str)
            assert isinstance(stock["name"], str)
            assert stock["region"] == "US"
            assert stock["currency"] == "USD"

    def test_fallback_includes_major_stocks(self):
        """Test that fallback includes major S&P 500 stocks"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        fetcher = SP500Fetcher(self.test_config)
        stocks = fetcher._get_fallback()

        symbols = [s["symbol"] for s in stocks]

        # Check for major stocks
        assert "AAPL" in symbols
        assert "MSFT" in symbols
        assert "GOOGL" in symbols
        assert "AMZN" in symbols

    def test_fallback_normalizes_symbols(self):
        """Test that fallback normalizes symbols correctly"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        fetcher = SP500Fetcher(self.test_config)
        stocks = fetcher._get_fallback()

        symbols = [s["symbol"] for s in stocks]

        # BRK.B should be normalized to BRK-B
        assert "BRK-B" in symbols
        assert "BRK.B" not in symbols

    @patch("pandas.read_html")
    def test_fallback_called_on_exception(self, mock_read_html):
        """Test that fallback is called when fetch fails"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        mock_read_html.side_effect = Exception("Network error")

        fetcher = SP500Fetcher(self.test_config)

        with patch.object(fetcher, "_get_fallback") as mock_fallback:
            mock_fallback.return_value = [{"symbol": "TEST"}]
            stocks = fetcher.fetch_constituents()

            mock_fallback.assert_called_once()
            assert stocks == [{"symbol": "TEST"}]


class TestSP500FetcherIntegration:
    """Integration-style tests"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "sp500",
            "name": "S&P 500",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "exchangeSuffix": "",
            "dataSource": "wikipedia",
            "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        }

    @patch("pandas.read_html")
    def test_full_fetch_and_format_pipeline(self, mock_read_html):
        """Test complete fetch and format pipeline"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        # Create realistic mock data
        mock_df = pd.DataFrame(
            {
                "Symbol": ["AAPL", "MSFT", "BRK.B"],
                "Security": ["Apple Inc.", "Microsoft Corp.", "Berkshire Hathaway"],
                "GICS Sector": [
                    "Information Technology",
                    "Information Technology",
                    "Financials",
                ],
                "GICS Sub-Industry": ["Software", "Software", "Insurance"],
                "Headquarters Location": ["Cupertino, CA", "Redmond, WA", "Omaha, NE"],
            }
        )
        mock_read_html.return_value = [mock_df]

        fetcher = SP500Fetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        # Verify all data is properly formatted
        assert len(stocks) == 3

        # Check Apple
        aapl = next(s for s in stocks if s["symbol"] == "AAPL")
        assert aapl["name"] == "Apple Inc."
        assert aapl["sector"] == "Information Technology"
        assert aapl["headquarters"] == "Cupertino, CA"

        # Check Microsoft
        msft = next(s for s in stocks if s["symbol"] == "MSFT")
        assert msft["name"] == "Microsoft Corp."

        # Check Berkshire (normalized symbol)
        brk = next(s for s in stocks if s["symbol"] == "BRK-B")
        assert brk["name"] == "Berkshire Hathaway"

    def test_stock_count_consistency(self):
        """Test that fallback has reasonable number of stocks"""
        from index_fetchers.sp500_fetcher import SP500Fetcher

        fetcher = SP500Fetcher(self.test_config)
        fallback_stocks = fetcher._get_fallback()

        # Fallback should have at least 30 stocks
        assert len(fallback_stocks) >= 30

        # All should be valid US stocks
        for stock in fallback_stocks:
            assert stock["region"] == "US"
            assert stock["currency"] == "USD"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

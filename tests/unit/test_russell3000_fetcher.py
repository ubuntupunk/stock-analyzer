"""
Unit Tests for Russell 3000 Index Fetcher

Tests the Russell3000Fetcher class with mocked HTTP responses and edge cases
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import pandas as pd
import io

# Add backend path for imports
sys.path.insert(0, "/home/ubuntupunk/Projects/stock-analyzer/infrastructure/backend")


class TestRussell3000FetcherInitialization:
    """Test Russell3000Fetcher initialization and configuration"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "russell3000",
            "name": "Russell 3000",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "exchangeSuffix": "",
            "dataSource": "ishares",
            "url": "https://www.ishares.com/us/products/239724/ishares-russell-3000-etf",
            "etfSymbol": "IWV",
            "fallbackUrl": "https://example.com/russell3000.xlsx",
        }

    def test_initialization_with_valid_config(self):
        """Test Russell3000Fetcher initializes correctly with valid config"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        fetcher = Russell3000Fetcher(self.test_config)

        assert fetcher.id == "russell3000"
        assert fetcher.name == "Russell 3000"
        assert fetcher.region == "US"
        assert fetcher.currency == "USD"
        assert fetcher.exchange == "NYSE"

    def test_initialization_inherits_from_base(self):
        """Test Russell3000Fetcher inherits from IndexFetcher"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher
        from index_fetchers.base import IndexFetcher

        fetcher = Russell3000Fetcher(self.test_config)

        assert isinstance(fetcher, IndexFetcher)


class TestRussell3000FetcherFetchConstituents:
    """Test fetch_constituents method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "russell3000",
            "name": "Russell 3000",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "exchangeSuffix": "",
            "dataSource": "ishares",
            "url": "https://www.ishares.com/us/products/239724/ishares-russell-3000-etf",
            "etfSymbol": "IWV",
            "fallbackUrl": "https://example.com/russell3000.xlsx",
        }

    @patch("index_fetchers.russell_fetcher.Russell3000Fetcher._fetch_ishares_holdings")
    def test_fetch_constituents_prefers_ishares(self, mock_ishares):
        """Test that iShares is tried first"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        # Setup mock to return data
        mock_ishares.return_value = [
            {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"}
        ]

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        assert len(stocks) == 1
        assert stocks[0]["symbol"] == "AAPL"
        mock_ishares.assert_called_once()

    @patch("index_fetchers.russell_fetcher.Russell3000Fetcher._fetch_ishares_holdings")
    @patch("index_fetchers.russell_fetcher.Russell3000Fetcher._fetch_from_excel")
    def test_fetch_constituents_falls_back_to_excel(self, mock_excel, mock_ishares):
        """Test fallback to Excel when iShares fails"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        # Setup mocks
        mock_ishares.return_value = []  # iShares fails
        mock_excel.return_value = [
            {"symbol": "MSFT", "name": "Microsoft", "sector": "Technology"}
        ]

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        assert len(stocks) == 1
        assert stocks[0]["symbol"] == "MSFT"
        mock_ishares.assert_called_once()
        mock_excel.assert_called_once()

    @patch("index_fetchers.russell_fetcher.Russell3000Fetcher._fetch_ishares_holdings")
    @patch("index_fetchers.russell_fetcher.Russell3000Fetcher._fetch_from_excel")
    @patch("index_fetchers.russell_fetcher.Russell3000Fetcher._get_fallback")
    def test_fetch_constituents_falls_back_to_fallback(
        self, mock_fallback, mock_excel, mock_ishares
    ):
        """Test fallback to hardcoded list when both sources fail"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        # Setup mocks to fail
        mock_ishares.return_value = []
        mock_excel.return_value = []
        mock_fallback.return_value = [
            {"symbol": "GOOGL", "name": "Alphabet", "sector": "Communication"}
        ]

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        assert len(stocks) == 1
        assert stocks[0]["symbol"] == "GOOGL"
        mock_ishares.assert_called_once()
        mock_excel.assert_called_once()
        mock_fallback.assert_called_once()


class TestRussell3000FetcherFetchIshares:
    """Test _fetch_ishares_holdings method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "russell3000",
            "name": "Russell 3000",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "exchangeSuffix": "",
            "dataSource": "ishares",
            "url": "https://www.ishares.com/us/products/239724/ishares-russell-3000-etf",
            "etfSymbol": "IWV",
        }

    def test_fetch_ishares_returns_empty(self):
        """Test that iShares fetcher returns empty (requires JavaScript)"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher._fetch_ishares_holdings()

        # Currently returns empty list because iShares requires JavaScript
        assert stocks == []


class TestRussell3000FetcherFetchFromExcel:
    """Test _fetch_from_excel method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "russell3000",
            "name": "Russell 3000",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "exchangeSuffix": "",
            "dataSource": "excel",
            "url": "https://example.com/russell3000.xlsx",
            "fallbackUrl": "https://example.com/russell3000.xlsx",
        }

    def create_mock_excel_data(self):
        """Create mock Excel data as bytes"""
        import pandas as pd

        df = pd.DataFrame(
            {
                "Symbol": ["AAPL", "MSFT", "GOOGL", ""],
                "Name": ["Apple Inc.", "Microsoft Corp.", "Alphabet Inc.", "Header"],
            }
        )

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        return excel_buffer.getvalue()

    @patch("requests.get")
    @patch("pandas.read_excel")
    def test_fetch_from_excel_success(self, mock_read_excel, mock_get):
        """Test successful Excel download and parsing"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        # Setup mock response
        mock_response = Mock()
        mock_response.content = b"fake excel content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Setup mock pandas
        mock_df = pd.DataFrame(
            {
                "Symbol": ["AAPL", "MSFT", "GOOGL", ""],
            }
        )
        mock_read_excel.return_value = mock_df

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher._fetch_from_excel()

        # Should return stocks (excluding empty symbol)
        assert len(stocks) == 3
        symbols = [s["symbol"] for s in stocks]
        assert "AAPL" in symbols
        assert "MSFT" in symbols
        assert "GOOGL" in symbols

    @patch("requests.get")
    def test_fetch_from_excel_no_url(self, mock_get):
        """Test returns empty when no fallback URL configured"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        # Config with all required fields but no fallbackUrl
        config_without_fallback_url = {
            "id": "russell3000",
            "name": "Russell 3000",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "exchangeSuffix": "",
            "dataSource": "excel",
            "url": "https://example.com/russell3000",
            # Note: no fallbackUrl
        }

        fetcher = Russell3000Fetcher(config_without_fallback_url)
        stocks = fetcher._fetch_from_excel()

        assert stocks == []
        mock_get.assert_not_called()

    @patch("requests.get")
    def test_fetch_from_excel_network_error(self, mock_get):
        """Test handling of network errors"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        mock_get.side_effect = Exception("Connection timeout")

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher._fetch_from_excel()

        assert stocks == []

    @patch("requests.get")
    @patch("pandas.read_excel")
    def test_fetch_from_excel_missing_symbol_column(self, mock_read_excel, mock_get):
        """Test handling of Excel without Symbol column"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        # Setup mock response
        mock_response = Mock()
        mock_response.content = b"fake excel content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Setup mock pandas with wrong column
        mock_df = pd.DataFrame(
            {
                "WrongColumn": ["AAPL", "MSFT"],
            }
        )
        mock_read_excel.return_value = mock_df

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher._fetch_from_excel()

        assert stocks == []

    @patch("requests.get")
    @patch("pandas.read_excel")
    def test_fetch_from_excel_skips_header_rows(self, mock_read_excel, mock_get):
        """Test that header rows are skipped"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        # Setup mock response
        mock_response = Mock()
        mock_response.content = b"fake excel content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Setup mock pandas with header row
        mock_df = pd.DataFrame(
            {
                "Symbol": ["AAPL", "symbol", "MSFT"],  # 'symbol' is header row
            }
        )
        mock_read_excel.return_value = mock_df

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher._fetch_from_excel()

        # Should skip the 'symbol' header row
        symbols = [s["symbol"] for s in stocks]
        assert "AAPL" in symbols
        assert "MSFT" in symbols
        assert "symbol" not in symbols


class TestRussell3000FetcherFallback:
    """Test fallback functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "russell3000",
            "name": "Russell 3000",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "exchangeSuffix": "",
            "dataSource": "fallback",
            "url": "https://example.com/fallback",
        }

    def test_fallback_returns_valid_stocks(self):
        """Test that fallback method returns properly formatted stocks"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher._get_fallback()

        # Check structure
        assert len(stocks) > 0
        for stock in stocks:
            assert "symbol" in stock
            assert "name" in stock
            assert "sector" in stock
            assert "region" in stock
            assert "currency" in stock
            assert "exchange" in stock

            assert isinstance(stock["symbol"], str)
            assert isinstance(stock["name"], str)
            assert stock["region"] == "US"
            assert stock["currency"] == "USD"

    def test_fallback_includes_mixed_cap_stocks(self):
        """Test that fallback includes large, mid, and small cap stocks"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher._get_fallback()

        symbols = [s["symbol"] for s in stocks]

        # Check for mega/large cap
        assert "AAPL" in symbols
        assert "MSFT" in symbols

        # Check for mid cap
        assert "PLTR" in symbols
        assert "SNOW" in symbols

        # Check for small cap
        assert "HOOD" in symbols
        assert "LCID" in symbols

    def test_fallback_stock_count(self):
        """Test that fallback has reasonable number of stocks"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher._get_fallback()

        # Should have at least 20 stocks
        assert len(stocks) >= 20

    def test_fallback_normalizes_symbols(self):
        """Test that fallback normalizes symbols correctly"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher._get_fallback()

        symbols = [s["symbol"] for s in stocks]

        # BRK-B should be normalized
        assert "BRK-B" in symbols
        assert "BRK.B" not in symbols


class TestRussell3000FetcherIntegration:
    """Integration-style tests"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "russell3000",
            "name": "Russell 3000",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "exchangeSuffix": "",
            "dataSource": "ishares",
            "url": "https://www.ishares.com/us/products/239724/ishares-russell-3000-etf",
            "fallbackUrl": "https://example.com/russell3000.xlsx",
        }

    @patch("index_fetchers.russell_fetcher.Russell3000Fetcher._fetch_ishares_holdings")
    @patch("index_fetchers.russell_fetcher.Russell3000Fetcher._fetch_from_excel")
    @patch("index_fetchers.russell_fetcher.Russell3000Fetcher._get_fallback")
    def test_full_fallback_chain(self, mock_fallback, mock_excel, mock_ishares):
        """Test complete fallback chain"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        # All sources fail
        mock_ishares.return_value = []
        mock_excel.return_value = []
        mock_fallback.return_value = [
            {
                "symbol": "AAPL",
                "name": "Apple",
                "sector": "Tech",
                "region": "US",
                "currency": "USD",
                "exchange": "NYSE",
            },
        ]

        fetcher = Russell3000Fetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        # Should get fallback data
        assert len(stocks) == 1
        assert stocks[0]["symbol"] == "AAPL"

        # Verify all methods were called in order
        mock_ishares.assert_called_once()
        mock_excel.assert_called_once()
        mock_fallback.assert_called_once()

    def test_stock_structure_consistency(self):
        """Test that all stocks have consistent structure regardless of source"""
        from index_fetchers.russell_fetcher import Russell3000Fetcher

        fetcher = Russell3000Fetcher(self.test_config)
        fallback_stocks = fetcher._get_fallback()

        required_fields = {"symbol", "name", "sector", "region", "currency", "exchange"}

        for stock in fallback_stocks:
            assert required_fields.issubset(stock.keys())
            assert stock["region"] == "US"
            assert stock["currency"] == "USD"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

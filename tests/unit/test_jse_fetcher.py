"""
Unit Tests for JSE (Johannesburg Stock Exchange) Index Fetcher

Tests the JSEFetcher class with mocked HTTP responses and ZAR/USD FX conversion
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# Add backend path for imports
sys.path.insert(0, "/home/ubuntupunk/Projects/stock-analyzer/infrastructure/backend")


class TestJSEFetcherInitialization:
    """Test JSEFetcher initialization and configuration"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "jse",
            "name": "JSE All Share",
            "region": "ZA",
            "currency": "ZAR",
            "exchange": "JSE",
            "exchangeSuffix": ".JO",
            "dataSource": "wikipedia",
            "url": "https://en.wikipedia.org/wiki/FTSE/JSE_All_Share_Index",
            "fxRate": {"symbol": "ZAR=X", "source": "yfinance"},
        }

    def test_initialization_with_valid_config(self):
        """Test JSEFetcher initializes correctly with valid config"""
        from index_fetchers.jse_fetcher import JSEFetcher

        fetcher = JSEFetcher(self.test_config)

        assert fetcher.id == "jse"
        assert fetcher.name == "JSE All Share"
        assert fetcher.region == "ZA"
        assert fetcher.currency == "ZAR"
        assert fetcher.exchange == "JSE"
        assert fetcher.exchange_suffix == ".JO"

    def test_initialization_has_fx_config(self):
        """Test JSEFetcher has FX rate configuration"""
        from index_fetchers.jse_fetcher import JSEFetcher

        fetcher = JSEFetcher(self.test_config)

        assert "fxRate" in fetcher.config
        assert fetcher.config["fxRate"]["symbol"] == "ZAR=X"


class TestJSEFetcherFetchConstituents:
    """Test fetch_constituents method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "jse",
            "name": "JSE All Share",
            "region": "ZA",
            "currency": "ZAR",
            "exchange": "JSE",
            "exchangeSuffix": ".JO",
            "dataSource": "wikipedia",
            "url": "https://en.wikipedia.org/wiki/FTSE/JSE_All_Share_Index",
        }

    @patch("index_fetchers.jse_fetcher.JSEFetcher._fetch_from_wikipedia")
    def test_fetch_constituents_prefers_wikipedia(self, mock_wiki):
        """Test that Wikipedia is tried first"""
        from index_fetchers.jse_fetcher import JSEFetcher

        mock_wiki.return_value = [
            {"symbol": "AGL.JO", "name": "Anglo American", "sector": "Materials"}
        ]

        fetcher = JSEFetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        assert len(stocks) == 1
        assert stocks[0]["symbol"] == "AGL.JO"
        mock_wiki.assert_called_once()

    @patch("index_fetchers.jse_fetcher.JSEFetcher._fetch_from_wikipedia")
    @patch("index_fetchers.jse_fetcher.JSEFetcher._get_fallback")
    def test_fetch_constituents_falls_back(self, mock_fallback, mock_wiki):
        """Test fallback when Wikipedia fails"""
        from index_fetchers.jse_fetcher import JSEFetcher

        mock_wiki.return_value = []
        mock_fallback.return_value = [
            {"symbol": "MTN.JO", "name": "MTN Group", "sector": "Communication"}
        ]

        fetcher = JSEFetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        assert len(stocks) == 1
        assert stocks[0]["symbol"] == "MTN.JO"
        mock_wiki.assert_called_once()
        mock_fallback.assert_called_once()


class TestJSEFetcherFetchFromWikipedia:
    """Test _fetch_from_wikipedia method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "jse",
            "name": "JSE All Share",
            "region": "ZA",
            "currency": "ZAR",
            "exchange": "JSE",
            "exchangeSuffix": ".JO",
            "dataSource": "wikipedia",
            "url": "https://en.wikipedia.org/wiki/FTSE/JSE_All_Share_Index",
        }

    @patch("pandas.read_html")
    def test_fetch_from_wikipedia_success(self, mock_read_html):
        """Test successful Wikipedia fetch"""
        from index_fetchers.jse_fetcher import JSEFetcher

        mock_df = pd.DataFrame(
            {
                "Symbol": ["AGL", "MTN", "SBK"],
                "Company": ["Anglo American", "MTN Group", "Standard Bank"],
                "Sector": ["Materials", "Communication", "Financials"],
            }
        )
        mock_read_html.return_value = [mock_df]

        fetcher = JSEFetcher(self.test_config)
        stocks = fetcher._fetch_from_wikipedia()

        assert len(stocks) == 3
        assert stocks[0]["symbol"] == "AGL.JO"
        assert stocks[0]["name"] == "Anglo American"
        assert stocks[0]["sector"] == "Materials"
        assert stocks[0]["region"] == "ZA"
        assert stocks[0]["currency"] == "ZAR"

    @patch("pandas.read_html")
    def test_fetch_from_wikipedia_alternative_columns(self, mock_read_html):
        """Test Wikipedia fetch with alternative column names"""
        from index_fetchers.jse_fetcher import JSEFetcher

        mock_df = pd.DataFrame(
            {
                "Ticker": ["NPN", "VOD"],
                "Name": ["Naspers", "Vodacom"],
            }
        )
        mock_read_html.return_value = [mock_df]

        fetcher = JSEFetcher(self.test_config)
        stocks = fetcher._fetch_from_wikipedia()

        assert len(stocks) == 2
        assert stocks[0]["symbol"] == "NPN.JO"

    @patch("pandas.read_html")
    def test_fetch_from_wikipedia_missing_symbol_column(self, mock_read_html):
        """Test handling when no symbol column found"""
        from index_fetchers.jse_fetcher import JSEFetcher

        mock_df = pd.DataFrame(
            {
                "WrongColumn": ["AGL", "MTN"],
                "Company": ["Anglo", "MTN"],
            }
        )
        mock_read_html.return_value = [mock_df]

        fetcher = JSEFetcher(self.test_config)
        stocks = fetcher._fetch_from_wikipedia()

        assert stocks == []

    @patch("pandas.read_html")
    def test_fetch_from_wikipedia_network_error(self, mock_read_html):
        """Test handling of network errors"""
        from index_fetchers.jse_fetcher import JSEFetcher

        mock_read_html.side_effect = Exception("Connection timeout")

        fetcher = JSEFetcher(self.test_config)
        stocks = fetcher._fetch_from_wikipedia()

        assert stocks == []

    @patch("pandas.read_html")
    def test_fetch_from_wikipedia_adds_jo_suffix(self, mock_read_html):
        """Test that .JO suffix is added to symbols"""
        from index_fetchers.jse_fetcher import JSEFetcher

        mock_df = pd.DataFrame(
            {
                "Symbol": ["AGL", "MTN"],
                "Company": ["Anglo", "MTN"],
                "Sector": ["Materials", "Communication"],
            }
        )
        mock_read_html.return_value = [mock_df]

        fetcher = JSEFetcher(self.test_config)
        stocks = fetcher._fetch_from_wikipedia()

        for stock in stocks:
            assert stock["symbol"].endswith(".JO")


class TestJSEFetcherFallback:
    """Test fallback functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "jse",
            "name": "JSE All Share",
            "region": "ZA",
            "currency": "ZAR",
            "exchange": "JSE",
            "exchangeSuffix": ".JO",
            "dataSource": "fallback",
            "url": "https://example.com/jse",
        }

    def test_fallback_returns_valid_stocks(self):
        """Test that fallback method returns properly formatted stocks"""
        from index_fetchers.jse_fetcher import JSEFetcher

        fetcher = JSEFetcher(self.test_config)
        stocks = fetcher._get_fallback()

        assert len(stocks) > 0
        for stock in stocks:
            assert "symbol" in stock
            assert "name" in stock
            assert "sector" in stock
            assert "region" in stock
            assert "currency" in stock
            assert "exchange" in stock

            assert stock["region"] == "ZA"
            assert stock["currency"] == "ZAR"
            assert stock["symbol"].endswith(".JO")

    def test_fallback_includes_major_stocks(self):
        """Test that fallback includes major JSE stocks"""
        from index_fetchers.jse_fetcher import JSEFetcher

        fetcher = JSEFetcher(self.test_config)
        stocks = fetcher._get_fallback()

        symbols = [s["symbol"] for s in stocks]

        # Check for major JSE stocks
        assert "AGL.JO" in symbols
        assert "MTN.JO" in symbols
        assert "NPN.JO" in symbols

    def test_fallback_includes_various_sectors(self):
        """Test that fallback includes stocks from different sectors"""
        from index_fetchers.jse_fetcher import JSEFetcher

        fetcher = JSEFetcher(self.test_config)
        stocks = fetcher._get_fallback()

        sectors = set(s["sector"] for s in stocks)

        # Should have multiple sectors
        assert len(sectors) > 1
        assert "Financials" in sectors
        assert "Materials" in sectors


class TestJSEFetcherFXConversion:
    """Test FX rate and currency conversion"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "jse",
            "name": "JSE All Share",
            "region": "ZA",
            "currency": "ZAR",
            "exchange": "JSE",
            "exchangeSuffix": ".JO",
            "dataSource": "wikipedia",
            "url": "https://en.wikipedia.org/wiki/FTSE/JSE_All_Share_Index",
            "fxRate": {"symbol": "ZAR=X", "source": "yfinance"},
        }

    @patch("yfinance.Ticker")
    def test_get_fx_rate_success(self, mock_ticker_class):
        """Test successful FX rate fetch"""
        from index_fetchers.jse_fetcher import JSEFetcher

        mock_ticker = Mock()
        mock_ticker.info = {"regularMarketPrice": 18.75}
        mock_ticker_class.return_value = mock_ticker

        fetcher = JSEFetcher(self.test_config)
        rate = fetcher.get_fx_rate()

        assert rate == 18.75

    @patch("yfinance.Ticker")
    def test_get_fx_rate_fallback_to_previous_close(self, mock_ticker_class):
        """Test FX rate fallback to previous close"""
        from index_fetchers.jse_fetcher import JSEFetcher

        mock_ticker = Mock()
        mock_ticker.info = {"previousClose": 18.60}
        mock_ticker_class.return_value = mock_ticker

        fetcher = JSEFetcher(self.test_config)
        rate = fetcher.get_fx_rate()

        assert rate == 18.60

    @patch("yfinance.Ticker")
    def test_get_fx_rate_error_returns_default(self, mock_ticker_class):
        """Test that errors return default rate"""
        from index_fetchers.jse_fetcher import JSEFetcher

        mock_ticker_class.side_effect = Exception("Network error")

        fetcher = JSEFetcher(self.test_config)
        rate = fetcher.get_fx_rate()

        assert rate == 18.50  # Default fallback

    def test_apply_fx_conversion(self):
        """Test ZAR to USD conversion"""
        from index_fetchers.jse_fetcher import JSEFetcher

        fetcher = JSEFetcher(self.test_config)

        # Convert 1850 ZAR at 18.50 rate = 100 USD
        usd = fetcher.apply_fx_conversion(1850.0, 18.50)
        assert usd == 100.0

    def test_apply_fx_conversion_zero_amount(self):
        """Test conversion of zero amount"""
        from index_fetchers.jse_fetcher import JSEFetcher

        fetcher = JSEFetcher(self.test_config)

        usd = fetcher.apply_fx_conversion(0.0, 18.50)
        assert usd == 0.0


class TestJSEFetcherIntegration:
    """Integration-style tests"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_config = {
            "id": "jse",
            "name": "JSE All Share",
            "region": "ZA",
            "currency": "ZAR",
            "exchange": "JSE",
            "exchangeSuffix": ".JO",
            "dataSource": "wikipedia",
            "url": "https://en.wikipedia.org/wiki/FTSE/JSE_All_Share_Index",
        }

    @patch("index_fetchers.jse_fetcher.JSEFetcher._fetch_from_wikipedia")
    @patch("index_fetchers.jse_fetcher.JSEFetcher._get_fallback")
    def test_full_fallback_chain(self, mock_fallback, mock_wiki):
        """Test complete fallback chain"""
        from index_fetchers.jse_fetcher import JSEFetcher

        mock_wiki.return_value = []
        mock_fallback.return_value = [
            {
                "symbol": "AGL.JO",
                "name": "Anglo",
                "sector": "Materials",
                "region": "ZA",
                "currency": "ZAR",
                "exchange": "JSE",
            }
        ]

        fetcher = JSEFetcher(self.test_config)
        stocks = fetcher.fetch_constituents()

        assert len(stocks) == 1
        mock_wiki.assert_called_once()
        mock_fallback.assert_called_once()

    @patch("pandas.read_html")
    def test_stock_format_consistency(self, mock_read_html):
        """Test that all stocks have consistent format"""
        from index_fetchers.jse_fetcher import JSEFetcher

        mock_df = pd.DataFrame(
            {
                "Symbol": ["AGL", "MTN"],
                "Company": ["Anglo", "MTN Group"],
                "Sector": ["Materials", "Communication"],
            }
        )
        mock_read_html.return_value = [mock_df]

        fetcher = JSEFetcher(self.test_config)
        stocks = fetcher._fetch_from_wikipedia()

        required_fields = {"symbol", "name", "sector", "region", "currency", "exchange"}

        for stock in stocks:
            assert required_fields.issubset(stock.keys())
            assert stock["region"] == "ZA"
            assert stock["currency"] == "ZAR"
            assert stock["exchange"] == "JSE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

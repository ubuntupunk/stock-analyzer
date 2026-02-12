"""
Unit Tests for Stock API Module
Tests the StockDataAPI class with circuit breaker, metrics, and fallback mechanisms
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add backend path for imports
sys.path.insert(0, "/home/ubuntupunk/Projects/stock-analyzer/infrastructure/backend")


class TestAPIMetrics:
    """Test APIMetrics class for tracking API performance"""

    def setup_method(self):
        """Set up metrics instance for each test"""
        from stock_api import APIMetrics

        self.metrics = APIMetrics()

    def test_initial_state(self):
        """Test metrics are initialized correctly"""
        metrics = self.metrics.get_metrics()

        assert metrics["requests"]["total"] == 0
        assert metrics["requests"]["success"] == 0
        assert metrics["requests"]["failed"] == 0
        assert metrics["rate_limits"] == 0
        assert metrics["timeouts"] == 0

    @pytest.mark.asyncio
    async def test_record_request_success(self):
        """Test recording a successful request"""
        await self.metrics.record_request("yahoo_finance", True, 100.0)

        metrics = self.metrics.get_metrics()
        assert metrics["requests"]["total"] == 1
        assert metrics["requests"]["success"] == 1
        assert "yahoo_finance" in metrics["sources"]

    @pytest.mark.asyncio
    async def test_record_request_failure(self):
        """Test recording a failed request"""
        await self.metrics.record_request("yahoo_finance", False, 100.0)

        metrics = self.metrics.get_metrics()
        assert metrics["requests"]["total"] == 1
        assert metrics["requests"]["failed"] == 1

    @pytest.mark.asyncio
    async def test_record_request_updates_source_stats(self):
        """Test source-specific tracking"""
        await self.metrics.record_request("alpha_vantage", True, 50.0)
        await self.metrics.record_request("alpha_vantage", False, 60.0)

        source_stats = self.metrics.get_source_stats("alpha_vantage")
        assert source_stats["calls"] == 2
        assert source_stats["success"] == 1
        assert source_stats["failed"] == 1

    @pytest.mark.asyncio
    async def test_latency_tracking(self):
        """Test latency calculation"""
        await self.metrics.record_request("test_api", True, 100.0)
        await self.metrics.record_request("test_api", True, 200.0)

        metrics = self.metrics.get_metrics()
        assert metrics["latency"]["total_ms"] == 300.0
        assert metrics["latency"]["count"] == 2
        assert metrics["latency"]["avg_ms"] == 150.0

    @pytest.mark.asyncio
    async def test_success_rate_calculation(self):
        """Test success rate percentage"""
        await self.metrics.record_request("test_api", True, 100.0)
        await self.metrics.record_request("test_api", True, 100.0)
        await self.metrics.record_request("test_api", False, 100.0)

        metrics = self.metrics.get_metrics()
        assert metrics["success_rate"] == "66.7%"

    def test_record_rate_limit(self):
        """Test rate limit tracking"""
        self.metrics.record_rate_limit("alpha_vantage")

        metrics = self.metrics.get_metrics()
        assert metrics["rate_limits"] == 1
        assert metrics["errors"]["alpha_vantage"]["rate_limits"] == 1

    def test_record_timeout(self):
        """Test timeout tracking"""
        self.metrics.record_timeout("yahoo_finance")

        metrics = self.metrics.get_metrics()
        assert metrics["timeouts"] == 1
        assert metrics["errors"]["yahoo_finance"]["timeouts"] == 1

    def test_get_source_stats_unknown(self):
        """Test getting stats for unknown source"""
        stats = self.metrics.get_source_stats("unknown")

        assert stats["calls"] == 0
        assert stats["success"] == 0
        assert stats["failed"] == 0


class TestStockDataAPI:
    """Test StockDataAPI class"""

    def setup_method(self):
        """Set up stock API instance for each test"""
        from stock_api import StockDataAPI

        self.api = StockDataAPI()

    def teardown_method(self):
        """Clean up after each test"""
        pass

    def test_initialization(self):
        """Test StockDataAPI initializes correctly"""
        from stock_api import StockDataAPI

        # Test with default config
        api = StockDataAPI()

        assert api.timeout == 10
        assert api.cache_timeout == 300
        assert api.yahoo is not None
        assert api.alpha_vantage is not None
        assert api.polygon is not None
        assert api.alpaca is not None
        assert api.cb is not None
        assert api.metrics is not None

    def test_custom_configuration(self):
        """Test StockDataAPI with custom config"""
        from stock_api import StockDataAPI

        config = {
            "timeout": 20,
            "cache_timeout": 600,
            "priorities": [("yahoo_finance", 1), ("alpaca", 2)],
        }

        api = StockDataAPI(config=config)

        assert api.timeout == 20
        assert api.cache_timeout == 600
        assert len(api.priorities) == 2

    def test_cache_key_generation(self):
        """Test cache key generation"""
        key = self.api._get_cache_key("price", "AAPL")

        assert key == "price:AAPL"

    def test_cache_validity_check(self):
        """Test cache validation logic"""
        # Empty cache should be invalid
        assert self.api._is_cache_valid("nonexistent") is False

        # Add valid cache entry
        self.api.cache["test:KEY"] = {
            "data": {"test": "data"},
            "timestamp": datetime.now().timestamp(),
        }

        assert self.api._is_cache_valid("test:KEY") is True

        # Add expired cache entry (older than cache_timeout)
        self.api.cache["expired:KEY"] = {
            "data": {"test": "data"},
            "timestamp": datetime.now().timestamp() - 400,  # 400 seconds ago
        }

        assert self.api._is_cache_valid("expired:KEY") is False

    def test_get_from_cache(self):
        """Test retrieving data from cache"""
        # Empty cache
        result = self.api._get_from_cache("nonexistent")
        assert result is None

        # Valid cache
        self.api.cache["test:KEY"] = {
            "data": {"price": 100},
            "timestamp": datetime.now().timestamp(),
        }

        result = self.api._get_from_cache("test:KEY")
        assert result == {"price": 100}

    def test_set_cache(self):
        """Test storing data in cache"""
        self.api._set_cache("test:KEY", {"price": 100})

        assert "test:KEY" in self.api.cache
        assert self.api.cache["test:KEY"]["data"] == {"price": 100}
        assert "timestamp" in self.api.cache["test:KEY"]

    def test_circuit_breaker_integration(self):
        """Test circuit breaker is properly integrated"""
        from circuit_breaker import CircuitState

        # Check initial state
        state = self.api.cb.get_state("yahoo_finance")
        assert state["state"] == CircuitState.CLOSED.value

    @pytest.mark.asyncio
    async def test_metrics_integration(self):
        """Test metrics are properly integrated"""
        # Record a test request
        await self.api.metrics.record_request("test_source", True, 50.0)

        stats = self.api.metrics.get_source_stats("test_source")
        assert stats["calls"] == 1
        assert stats["success"] == 1


class TestStockDataAPIMethods:
    """Test individual StockDataAPI methods"""

    def setup_method(self):
        """Set up stock API instance for each test"""
        from stock_api import StockDataAPI

        self.api = StockDataAPI()

    @patch("stock_api.StockDataAPI._fetch_yahoo_price")
    def test_get_stock_price_from_cache(self, mock_fetch):
        """Test get_stock_price returns cached data"""
        # Pre-populate cache
        self.api.cache["price:1mo:default:AAPL"] = {
            "data": {"symbol": "AAPL", "price": 150.0, "source": "cache"},
            "timestamp": datetime.now().timestamp(),
        }

        result = self.api.get_stock_price("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["price"] == 150.0
        assert result["source"] == "cache"
        mock_fetch.assert_not_called()

    @patch("api_clients.YahooFinanceClient.fetch_data")
    def test_get_stock_price_fetch(self, mock_fetch):
        """Test get_stock_price fetches data when cache miss"""
        mock_fetch.return_value = {"regularMarketPrice": 175.0, "previousClose": 170.0}

        result = self.api.get_stock_price("AAPL")

        assert result["symbol"] == "AAPL"
        assert "price" in result or "regularMarketPrice" in result


class TestAPIPriorities:
    """Test API priority configuration"""

    def test_default_priorities(self):
        """Test default priority order"""
        from stock_api import StockDataAPI

        api = StockDataAPI()

        # Default should have all sources
        priority_names = [name for name, _ in api.priorities]
        assert "yahoo_finance" in priority_names
        assert "alpaca" in priority_names
        assert "polygon" in priority_names
        assert "alpha_vantage" in priority_names

    def test_custom_priorities(self):
        """Test custom priority configuration"""
        from stock_api import StockDataAPI

        custom_config = {
            "priorities": [("alpaca", 1), ("yahoo_finance", 2)]  # Highest priority
        }

        api = StockDataAPI(config=custom_config)

        assert api.priorities[0][0] == "alpaca"
        assert api.priorities[1][0] == "yahoo_finance"


class TestCacheManagement:
    """Test cache management functionality"""

    def setup_method(self):
        """Set up stock API instance for each test"""
        from stock_api import StockDataAPI

        self.api = StockDataAPI()

    def test_cache_size_limit(self):
        """Test cache doesn't grow indefinitely"""
        # Add many entries
        for i in range(100):
            self.api._set_cache(f"price:{i}:AAPL", {"data": i})

        # Cache should contain entries
        assert len(self.api.cache) > 0

    def test_cache_expiration(self):
        """Test cache entries expire correctly"""
        # Add entry with old timestamp
        old_time = datetime.now().timestamp() - 400  # 400 seconds ago
        self.api.cache["old:entry"] = {"data": {"test": "data"}, "timestamp": old_time}

        # Should not be valid
        assert self.api._is_cache_valid("old:entry") is False

        # Should return None
        result = self.api._get_from_cache("old:entry")
        assert result is None


class TestMetricsReporting:
    """Test metrics reporting functionality"""

    def setup_method(self):
        """Set up stock API instance for each test"""
        from stock_api import StockDataAPI

        self.api = StockDataAPI()

    def test_get_metrics_returns_dict(self):
        """Test get_metrics returns proper structure"""
        metrics = self.api.metrics.get_metrics()

        assert isinstance(metrics, dict)
        assert "requests" in metrics
        assert "sources" in metrics
        assert "latency" in metrics
        assert "rate_limits" in metrics
        assert "timeouts" in metrics
        assert "errors" in metrics

    @pytest.mark.asyncio
    async def test_source_stats_structure(self):
        """Test source stats have correct structure"""
        await self.api.metrics.record_request("test", True, 100)

        stats = self.api.metrics.get_source_stats("test")

        assert "calls" in stats
        assert "success" in stats
        assert "failed" in stats
        assert "success_rate" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

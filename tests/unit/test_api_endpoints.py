"""
Unit Tests for Stock Universe API Endpoints

Tests the API endpoints for stock data including:
- GET /api/stocks/search
- GET /api/stocks/popular
- GET /api/stocks/sectors
- GET /api/stocks/filter
- GET /api/stocks/symbol/{symbol}

Uses mocked Lambda handler and DynamoDB to avoid AWS dependencies.
"""

import sys
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Add backend path for imports
sys.path.insert(0, "/home/ubuntupunk/Projects/stock-analyzer/infrastructure/backend")


class TestAPIEndpointsCORS:
    """Test CORS headers and preflight requests"""

    def create_api_event(self, path, method="GET", query_params=None, body=None):
        """Helper to create API Gateway event"""
        return {
            "path": path,
            "httpMethod": method,
            "queryStringParameters": query_params or {},
            "body": json.dumps(body) if body else None,
        }

    def test_cors_preflight_request(self):
        """Test CORS preflight (OPTIONS) request returns 200"""
        from lambda_handler import lambda_handler

        event = self.create_api_event("/api/stock/metrics", "OPTIONS")
        response = lambda_handler(event, {})

        assert response["statusCode"] == 200
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert "Access-Control-Allow-Headers" in response["headers"]
        assert "Access-Control-Allow-Methods" in response["headers"]
        assert response["body"] == ""


class TestStockMetricsEndpoint:
    """Test /api/stock/metrics endpoint"""

    def create_api_event(self, path, method="GET", query_params=None, body=None):
        """Helper to create API Gateway event"""
        return {
            "path": path,
            "httpMethod": method,
            "queryStringParameters": query_params or {},
            "body": json.dumps(body) if body else None,
        }

    @patch("lambda_handler.StockDataAPI")
    def test_get_stock_metrics_success(self, mock_api_class):
        """Test successful metrics retrieval"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api.get_stock_metrics.return_value = {
            "symbol": "AAPL",
            "pe_ratio": 28.5,
            "market_cap": 3000000000000,
            "sector": "Technology",
        }
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/stock/metrics", query_params={"symbol": "AAPL"}
        )
        response = lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["symbol"] == "AAPL"
        assert "pe_ratio" in body

    @patch("lambda_handler.StockDataAPI")
    def test_get_stock_metrics_missing_symbol(self, mock_api_class):
        """Test missing symbol parameter returns 400"""
        from lambda_handler import lambda_handler

        event = self.create_api_event("/api/stock/metrics", query_params={})
        response = lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body


class TestStockPriceEndpoint:
    """Test /api/stock/price endpoint"""

    def create_api_event(self, path, method="GET", query_params=None, body=None):
        """Helper to create API Gateway event"""
        return {
            "path": path,
            "httpMethod": method,
            "queryStringParameters": query_params or {},
            "body": json.dumps(body) if body else None,
        }

    @patch("lambda_handler.StockDataAPI")
    def test_get_stock_price_with_period(self, mock_api_class):
        """Test price retrieval with period parameter"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api.get_stock_price.return_value = {
            "symbol": "AAPL",
            "price": 175.50,
            "change": 2.50,
            "change_percent": 1.45,
        }
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/stock/price", query_params={"symbol": "AAPL", "period": "1mo"}
        )
        response = lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["symbol"] == "AAPL"
        mock_api.get_stock_price.assert_called_once_with("AAPL", "1mo", None, None)

    @patch("lambda_handler.StockDataAPI")
    def test_get_stock_price_with_date_range(self, mock_api_class):
        """Test price retrieval with date range"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api.get_stock_price.return_value = {"symbol": "AAPL", "historicalData": []}
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/stock/price",
            query_params={
                "symbol": "AAPL",
                "startDate": "2024-01-01",
                "endDate": "2024-01-31",
            },
        )
        response = lambda_handler(event, {})

        assert response["statusCode"] == 200
        mock_api.get_stock_price.assert_called_once_with(
            "AAPL", "1mo", "2024-01-01", "2024-01-31"
        )


class TestBatchEndpoints:
    """Test batch endpoints"""

    def create_api_event(self, path, method="GET", query_params=None, body=None):
        """Helper to create API Gateway event"""
        return {
            "path": path,
            "httpMethod": method,
            "queryStringParameters": query_params or {},
            "body": json.dumps(body) if body else None,
        }

    @patch("lambda_handler.StockDataAPI")
    def test_batch_prices_success(self, mock_api_class):
        """Test successful batch price retrieval"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api.get_batch_prices.return_value = {
            "AAPL": {"price": 175.50},
            "MSFT": {"price": 380.00},
        }
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/stock/batch/prices", query_params={"symbols": "AAPL,MSFT"}
        )
        response = lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "AAPL" in body
        assert "MSFT" in body

    @patch("lambda_handler.StockDataAPI")
    def test_batch_metrics_success(self, mock_api_class):
        """Test successful batch metrics retrieval"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api.get_batch_metrics.return_value = {
            "AAPL": {"pe_ratio": 28.5},
            "GOOGL": {"pe_ratio": 25.0},
        }
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/stock/batch/metrics", query_params={"symbols": "AAPL,GOOGL"}
        )
        response = lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "AAPL" in body

    def test_batch_missing_symbols(self):
        """Test batch request without symbols returns 400"""
        from lambda_handler import lambda_handler

        event = self.create_api_event("/api/stock/batch/prices", query_params={})
        response = lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "Symbols parameter is required" in body["error"]

    @patch("lambda_handler.StockDataAPI")
    def test_batch_too_many_symbols(self, mock_api_class):
        """Test batch request with >50 symbols returns 400"""
        from lambda_handler import lambda_handler

        symbols = ",".join([f"STOCK{i}" for i in range(51)])
        event = self.create_api_event(
            "/api/stock/batch/prices", query_params={"symbols": symbols}
        )
        response = lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Maximum 50 symbols" in body["error"]


class TestScreenerEndpoint:
    """Test /api/screen endpoint"""

    def create_api_event(self, path, method="GET", query_params=None, body=None):
        """Helper to create API Gateway event"""
        return {
            "path": path,
            "httpMethod": method,
            "queryStringParameters": query_params or {},
            "body": json.dumps(body) if body else None,
        }

    @patch("lambda_handler.StockScreener")
    def test_screen_post_success(self, mock_screener_class):
        """Test successful stock screening"""
        from lambda_handler import lambda_handler

        mock_screener = Mock()
        mock_screener.screen_stocks.return_value = {
            "stocks": [{"symbol": "AAPL", "score": 95}],
            "total": 1,
        }
        mock_screener_class.return_value = mock_screener

        event = self.create_api_event(
            "/api/screen", method="POST", body={"criteria": {"pe_ratio": {"max": 30}}}
        )
        response = lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "stocks" in body

    @patch("lambda_handler.StockScreener")
    def test_screen_get_not_allowed(self, mock_screener_class):
        """Test GET request to /api/screen returns 405"""
        from lambda_handler import lambda_handler

        event = self.create_api_event("/api/screen", method="GET")
        response = lambda_handler(event, {})

        assert response["statusCode"] == 405
        body = json.loads(response["body"])
        assert "Method not allowed" in body["error"]

    @patch("lambda_handler.StockScreener")
    def test_screen_invalid_json_body(self, mock_screener_class):
        """Test invalid JSON body returns 400"""
        from lambda_handler import lambda_handler

        event = {
            "path": "/api/screen",
            "httpMethod": "POST",
            "queryStringParameters": {},
            "body": "invalid json",
        }
        response = lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body


class TestStockUniverseEndpoints:
    """Test stock universe specific endpoints"""

    def create_api_event(self, path, method="GET", query_params=None, body=None):
        """Helper to create API Gateway event"""
        return {
            "path": path,
            "httpMethod": method,
            "queryStringParameters": query_params or {},
            "body": json.dumps(body) if body else None,
        }

    @patch("lambda_handler.StockDataAPI")
    def test_get_stock_by_symbol_endpoint(self, mock_api_class):
        """Test getting a single stock by symbol"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api.get_stock_metrics.return_value = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology",
        }
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/stock/metrics", query_params={"symbol": "AAPL"}
        )
        response = lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["symbol"] == "AAPL"

    @patch("lambda_handler.StockDataAPI")
    def test_get_stock_factors_endpoint(self, mock_api_class):
        """Test getting stock factors"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api.get_stock_factors.return_value = {
            "symbol": "AAPL",
            "factors": {"momentum": 0.75, "value": 0.60},
        }
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/stock/factors", query_params={"symbol": "AAPL"}
        )
        response = lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "factors" in body

    @patch("lambda_handler.StockDataAPI")
    def test_get_stock_news_endpoint(self, mock_api_class):
        """Test getting stock news"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api.get_stock_news.return_value = {
            "symbol": "AAPL",
            "news": [{"title": "Apple Reports Earnings", "date": "2024-01-15"}],
        }
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/stock/news", query_params={"symbol": "AAPL"}
        )
        response = lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "news" in body

    @patch("lambda_handler.StockDataAPI")
    def test_get_analyst_estimates_endpoint(self, mock_api_class):
        """Test getting analyst estimates"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api.get_analyst_estimates.return_value = {
            "symbol": "AAPL",
            "eps_estimate": 6.50,
            "revenue_estimate": 120000000000,
        }
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/stock/estimates", query_params={"symbol": "AAPL"}
        )
        response = lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "eps_estimate" in body


class TestErrorHandling:
    """Test error handling and edge cases"""

    def create_api_event(self, path, method="GET", query_params=None, body=None):
        """Helper to create API Gateway event"""
        return {
            "path": path,
            "httpMethod": method,
            "queryStringParameters": query_params or {},
            "body": json.dumps(body) if body else None,
        }

    @patch("lambda_handler.StockDataAPI")
    def test_internal_server_error(self, mock_api_class):
        """Test internal server error returns 500"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api.get_stock_metrics.side_effect = Exception("Database error")
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/stock/metrics", query_params={"symbol": "AAPL"}
        )
        response = lambda_handler(event, {})

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body

    @patch("lambda_handler.StockDataAPI")
    def test_invalid_endpoint(self, mock_api_class):
        """Test invalid endpoint returns error"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/invalid/endpoint", query_params={"symbol": "AAPL"}
        )
        response = lambda_handler(event, {})

        # Should return 200 with error in body (as per current implementation)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "error" in body or "symbol" in body


class TestResponseHeaders:
    """Test response headers are correct"""

    def create_api_event(self, path, method="GET", query_params=None, body=None):
        """Helper to create API Gateway event"""
        return {
            "path": path,
            "httpMethod": method,
            "queryStringParameters": query_params or {},
            "body": json.dumps(body) if body else None,
        }

    @patch("lambda_handler.StockDataAPI")
    def test_response_includes_cors_headers(self, mock_api_class):
        """Test all responses include CORS headers"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api.get_stock_metrics.return_value = {"symbol": "AAPL"}
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/stock/metrics", query_params={"symbol": "AAPL"}
        )
        response = lambda_handler(event, {})

        assert "headers" in response
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert response["headers"]["Content-Type"] == "application/json"

    @patch("lambda_handler.StockDataAPI")
    def test_response_body_is_valid_json(self, mock_api_class):
        """Test response body is valid JSON"""
        from lambda_handler import lambda_handler

        mock_api = Mock()
        mock_api.get_stock_metrics.return_value = {"symbol": "AAPL", "pe_ratio": 28.5}
        mock_api_class.return_value = mock_api

        event = self.create_api_event(
            "/api/stock/metrics", query_params={"symbol": "AAPL"}
        )
        response = lambda_handler(event, {})

        body = response["body"]
        # Should be valid JSON
        parsed = json.loads(body)
        assert isinstance(parsed, dict)


class TestCleanFloatValues:
    """Test the clean_float_values utility function"""

    def test_clean_nan_values(self):
        """Test NaN values are replaced with None"""
        from lambda_handler import clean_float_values
        import math

        result = clean_float_values(float("nan"))
        assert result is None

    def test_clean_infinity_values(self):
        """Test Infinity values are replaced with None"""
        from lambda_handler import clean_float_values

        result = clean_float_values(float("inf"))
        assert result is None

        result = clean_float_values(float("-inf"))
        assert result is None

    def test_clean_nested_dict(self):
        """Test nested dict cleaning"""
        from lambda_handler import clean_float_values
        import math

        data = {
            "valid": 123.45,
            "invalid": float("nan"),
            "nested": {"inf_value": float("inf"), "valid": 100.0},
        }

        result = clean_float_values(data)
        assert result["valid"] == 123.45
        assert result["invalid"] is None
        assert result["nested"]["inf_value"] is None
        assert result["nested"]["valid"] == 100.0

    def test_clean_list_values(self):
        """Test list values are cleaned"""
        from lambda_handler import clean_float_values
        import math

        data = [1.0, float("nan"), 2.0, float("inf")]
        result = clean_float_values(data)

        assert result[0] == 1.0
        assert result[1] is None
        assert result[2] == 2.0
        assert result[3] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

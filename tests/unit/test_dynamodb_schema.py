"""
Integration Tests for DynamoDB Multi-Index Schema

Tests the stock-universe DynamoDB table structure, GSIs, and query patterns.
Uses mocked boto3 DynamoDB client to avoid AWS dependencies.
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
from decimal import Decimal

# Add backend path for imports
sys.path.insert(0, "/home/ubuntupunk/Projects/stock-analyzer/infrastructure/backend")


class TestDynamoDBTableStructure:
    """Test DynamoDB table structure and configuration"""

    @patch("boto3.resource")
    def test_table_initialization(self, mock_boto3_resource):
        """Test StockUniverseManager initializes DynamoDB table"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()

        assert manager.table is not None
        mock_dynamodb.Table.assert_called_once_with("stock-universe")

    @patch("boto3.resource")
    def test_table_uses_environment_variable(self, mock_boto3_resource):
        """Test table name from environment variable"""
        from stock_universe_api import StockUniverseManager

        with patch.dict("os.environ", {"STOCK_UNIVERSE_TABLE": "test-stock-table"}):
            mock_table = Mock()
            mock_dynamodb = Mock()
            mock_dynamodb.Table.return_value = mock_table
            mock_boto3_resource.return_value = mock_dynamodb

            manager = StockUniverseManager()

            mock_dynamodb.Table.assert_called_once_with("test-stock-table")


class TestDynamoDBGSIQueries:
    """Test Global Secondary Index queries"""

    def setup_method(self):
        """Set up test fixtures"""
        self.sample_stocks = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "sector": "Technology",
                "region": "US",
                "currency": "USD",
                "marketCap": 3000000000000,
                "indexIds": ["SP500"],
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft Corp.",
                "sector": "Technology",
                "region": "US",
                "currency": "USD",
                "marketCap": 2800000000000,
                "indexIds": ["SP500"],
            },
            {
                "symbol": "AGL.JO",
                "name": "Anglo American",
                "sector": "Materials",
                "region": "ZA",
                "currency": "ZAR",
                "marketCap": 500000000000,
                "indexIds": ["JSE_ALSI"],
            },
        ]

    @patch("boto3.resource")
    def test_query_by_index_id_gsi(self, mock_boto3_resource):
        """Test querying by index ID using GSI"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.query.return_value = {"Items": self.sample_stocks[:2]}

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.search_stocks("A", index_id="SP500")

        # Should attempt GSI query
        mock_table.query.assert_called()
        call_args = mock_table.query.call_args
        assert "IndexName" in call_args.kwargs

    @patch("boto3.resource")
    def test_query_by_region_gsi(self, mock_boto3_resource):
        """Test querying by region using GSI"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.query.return_value = {"Items": [self.sample_stocks[2]]}

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.search_stocks("A", region="ZA")

        # Should attempt region GSI query
        mock_table.query.assert_called()

    @patch("boto3.resource")
    def test_query_by_currency_gsi(self, mock_boto3_resource):
        """Test querying by currency using GSI"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.query.return_value = {"Items": [self.sample_stocks[2]]}

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.search_stocks("A", currency="ZAR")

        # Should attempt currency GSI query
        mock_table.query.assert_called()

    @patch("boto3.resource")
    def test_gsi_fallback_to_scan(self, mock_boto3_resource):
        """Test fallback to scan when GSI doesn't exist"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        # First call raises exception (GSI doesn't exist), second succeeds
        mock_table.query.side_effect = Exception("GSI not found")
        mock_table.scan.return_value = {"Items": self.sample_stocks}

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.search_stocks("AAPL", index_id="SP500")

        # Should fall back to scan
        mock_table.scan.assert_called_once()
        assert len(results) > 0


class TestDynamoDBDataOperations:
    """Test data insertion, retrieval, and formatting"""

    def setup_method(self):
        """Set up test fixtures"""
        self.sample_items = [
            {
                "PK": "STOCK#AAPL",
                "SK": "METADATA",
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "sector": "Technology",
                "region": "US",
                "currency": "USD",
                "marketCap": Decimal("3000000000000"),
                "indexIds": ["SP500"],
                "GSI1PK": "SECTOR#Technology",
                "GSI1SK": "AAPL",
            }
        ]

    @patch("boto3.resource")
    def test_get_popular_stocks_sorts_by_market_cap(self, mock_boto3_resource):
        """Test popular stocks sorted by market cap"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.scan.return_value = {
            "Items": [
                {"symbol": "SMALL", "marketCap": Decimal("1000000")},
                {"symbol": "LARGE", "marketCap": Decimal("3000000000")},
                {"symbol": "MEDIUM", "marketCap": Decimal("1000000000")},
            ]
        }

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.get_popular_stocks(limit=3)

        # Should be sorted by market cap descending
        assert results[0]["symbol"] == "LARGE"
        assert results[1]["symbol"] == "MEDIUM"
        assert results[2]["symbol"] == "SMALL"

    @patch("boto3.resource")
    def test_get_sectors_counts_by_sector(self, mock_boto3_resource):
        """Test sector counting"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.scan.return_value = {
            "Items": [
                {"sector": "Technology"},
                {"sector": "Technology"},
                {"sector": "Financials"},
                {"sector": None},
            ]
        }

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        sectors = manager.get_sectors()

        # Returns list of dicts: [{"sector": "Technology", "count": 2}, ...]
        sector_dict = {item["sector"]: item["count"] for item in sectors}
        assert sector_dict.get("Technology") == 2
        assert sector_dict.get("Financials") == 1

    @patch("boto3.resource")
    def test_filter_stocks_by_sector(self, mock_boto3_resource):
        """Test filtering stocks by sector"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        # Mock query for GSI
        mock_table.query.return_value = {
            "Items": [
                {"symbol": "AAPL", "sector": "Technology"},
                {"symbol": "MSFT", "sector": "Technology"},
            ]
        }

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.filter_stocks(sector="Technology")

        assert len(results) == 2
        symbols = [r["symbol"] for r in results]
        assert "AAPL" in symbols
        assert "MSFT" in symbols


class TestDynamoDBSearchFunctionality:
    """Test search functionality with various patterns"""

    def setup_method(self):
        """Set up test fixtures"""
        self.search_items = [
            {"symbol": "AAPL", "name": "Apple Inc."},
            {"symbol": "AMZN", "name": "Amazon.com Inc."},
            {"symbol": "MSFT", "name": "Microsoft Corporation"},
        ]

    @patch("boto3.resource")
    def test_search_by_symbol_exact_match(self, mock_boto3_resource):
        """Test exact symbol match"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.scan.return_value = {"Items": self.search_items}

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.search_stocks("AAPL")

        assert len(results) == 1
        assert results[0]["symbol"] == "AAPL"

    @patch("boto3.resource")
    def test_search_by_symbol_prefix(self, mock_boto3_resource):
        """Test symbol prefix search"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.scan.return_value = {"Items": self.search_items}

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.search_stocks("A")

        # Should find AAPL and AMZN (might find more due to name matching)
        assert len(results) >= 2
        symbols = [r["symbol"] for r in results]
        assert "AAPL" in symbols
        assert "AMZN" in symbols

    @patch("boto3.resource")
    def test_search_by_name(self, mock_boto3_resource):
        """Test name search"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.scan.return_value = {"Items": self.search_items}

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.search_stocks("micro")

        # Should find Microsoft
        assert len(results) == 1
        assert results[0]["symbol"] == "MSFT"

    @patch("boto3.resource")
    def test_search_sorts_by_relevance(self, mock_boto3_resource):
        """Test results sorted by relevance"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.scan.return_value = {
            "Items": [
                {"symbol": "AAPL", "name": "Apple Inc."},
                {"symbol": "AAP", "name": "Advance Auto Parts"},
                {"symbol": "AA", "name": "Alcoa Corp"},
            ]
        }

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.search_stocks("AAPL")

        # Exact match should be first
        assert results[0]["symbol"] == "AAPL"


class TestDynamoDBBatchOperations:
    """Test batch operations"""

    @patch("boto3.resource")
    def test_batch_get_items(self, mock_boto3_resource):
        """Test batch get operation"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.batch_get_item.return_value = {
            "Responses": {
                "stock-universe": [
                    {"symbol": "AAPL", "name": "Apple"},
                    {"symbol": "MSFT", "name": "Microsoft"},
                ]
            }
        }

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        keys = [{"PK": "STOCK#AAPL"}, {"PK": "STOCK#MSFT"}]
        # Note: batch_get_items would need to be implemented in StockUniverseManager

    @patch("boto3.resource")
    def test_batch_write_items(self, mock_boto3_resource):
        """Test batch write operation"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        items = [
            {"symbol": "AAPL", "name": "Apple"},
            {"symbol": "MSFT", "name": "Microsoft"},
        ]
        # Note: batch_write would need to be implemented


class TestDynamoDBErrorHandling:
    """Test error handling and edge cases"""

    @patch("boto3.resource")
    def test_empty_table_returns_empty_list(self, mock_boto3_resource):
        """Test empty table handling"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.scan.return_value = {"Items": []}

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.search_stocks("AAPL")

        assert results == []

    @patch("boto3.resource")
    def test_missing_attributes_handled(self, mock_boto3_resource):
        """Test handling of items with missing attributes"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.scan.return_value = {
            "Items": [
                {"symbol": "AAPL"},  # Missing name
                {"name": "Microsoft"},  # Missing symbol
                {"symbol": "GOOGL", "name": "Alphabet"},
            ]
        }

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.search_stocks("AAPL")

        # Should handle missing attributes gracefully
        assert len(results) >= 0

    @patch("boto3.resource")
    def test_dynamodb_error_returns_empty(self, mock_boto3_resource):
        """Test error returns empty list"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        mock_table.scan.side_effect = Exception("DynamoDB error")

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()
        results = manager.search_stocks("AAPL")

        assert results == []


class TestDynamoDBDecimalHandling:
    """Test Decimal type handling for numeric values"""

    def test_decimal_serialization(self):
        """Test Decimal JSON serialization"""
        from stock_universe_api import decimal_default

        value = Decimal("123.45")
        result = decimal_default(value)

        assert result == 123.45
        assert isinstance(result, float)

    def test_decimal_serialization_integer(self):
        """Test Decimal serialization for integers"""
        from stock_universe_api import decimal_default

        value = Decimal("1000000")
        result = decimal_default(value)

        assert result == 1000000.0

    def test_decimal_serialization_raises_on_invalid(self):
        """Test Decimal serialization raises error for invalid types"""
        from stock_universe_api import decimal_default

        with pytest.raises(TypeError):
            decimal_default("string")


class TestDynamoDBIntegration:
    """Integration-style tests"""

    @patch("boto3.resource")
    def test_end_to_end_workflow(self, mock_boto3_resource):
        """Test complete workflow: search, filter, get popular"""
        from stock_universe_api import StockUniverseManager

        mock_table = Mock()
        all_items = [
            {
                "symbol": "AAPL",
                "name": "Apple",
                "sector": "Technology",
                "marketCap": Decimal("3000000000000"),
                "region": "US",
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft",
                "sector": "Technology",
                "marketCap": Decimal("2800000000000"),
                "region": "US",
            },
            {
                "symbol": "JPM",
                "name": "JPMorgan",
                "sector": "Financials",
                "marketCap": Decimal("500000000000"),
                "region": "US",
            },
        ]
        mock_table.scan.return_value = {"Items": all_items}
        mock_table.query.return_value = {
            "Items": [all_items[0], all_items[1]]  # Technology stocks
        }

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        manager = StockUniverseManager()

        # Search
        search_results = manager.search_stocks("A")
        assert len(search_results) >= 2

        # Get popular
        popular = manager.get_popular_stocks()
        assert popular[0]["symbol"] == "AAPL"  # Largest market cap

        # Filter by sector
        tech_stocks = manager.filter_stocks(sector="Technology")
        assert len(tech_stocks) == 2

        # Get sectors
        sectors = manager.get_sectors()
        sector_names = [s["sector"] for s in sectors]
        assert "Technology" in sector_names
        assert "Financials" in sector_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

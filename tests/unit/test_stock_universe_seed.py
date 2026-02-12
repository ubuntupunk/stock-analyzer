"""
End-to-End Tests for Stock Universe Seeding Workflow

Tests the complete stock universe seeding workflow:
1. Fetch data from multiple index sources (SP500, Russell 3000, JSE)
2. Validate and normalize data
3. Enrich with Yahoo Finance market data
4. Transform and normalize data
5. Write to DynamoDB with batch operations
6. Merge overlapping stocks from multiple indices

Uses mocked boto3 and yfinance to avoid external dependencies.
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal
import json

# Add backend path for imports
sys.path.insert(0, "/home/ubuntupunk/Projects/stock-analyzer/infrastructure/backend")


class TestStockUniverseSeederInitialization:
    """Test StockUniverseSeeder initialization"""

    @patch("boto3.resource")
    def test_seeder_initialization(self, mock_boto3_resource):
        """Test seeder initializes with DynamoDB table"""
        from stock_universe_seed import StockUniverseSeeder

        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()

        assert seeder.table is not None
        assert "SP500" in seeder.fetchers
        assert "RUSSELL3000" in seeder.fetchers
        assert "JSE_ALSI" in seeder.fetchers

    @patch("boto3.resource")
    def test_seeder_uses_environment_variable(self, mock_boto3_resource):
        """Test seeder uses STOCK_UNIVERSE_TABLE env var"""
        from stock_universe_seed import StockUniverseSeeder

        with patch.dict("os.environ", {"STOCK_UNIVERSE_TABLE": "test-table"}):
            mock_table = Mock()
            mock_dynamodb = Mock()
            mock_dynamodb.Table.return_value = mock_table
            mock_boto3_resource.return_value = mock_dynamodb

            seeder = StockUniverseSeeder()

            mock_dynamodb.Table.assert_called_once_with("test-table")


class TestSeedSingleIndex:
    """Test seeding a single index"""

    @patch("boto3.resource")
    @patch("stock_universe_seed.SP500Fetcher")
    def test_seed_index_success(self, mock_fetcher_class, mock_boto3_resource):
        """Test successful seeding of single index"""
        from stock_universe_seed import StockUniverseSeeder

        # Mock fetcher
        mock_fetcher = Mock()
        mock_fetcher.fetch_constituents.return_value = [
            {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
            {"symbol": "MSFT", "name": "Microsoft", "sector": "Technology"},
        ]
        mock_fetcher_class.return_value = mock_fetcher

        # Mock DynamoDB
        mock_table = Mock()
        mock_table.batch_writer.return_value.__enter__ = Mock(return_value=Mock())
        mock_table.batch_writer.return_value.__exit__ = Mock(return_value=False)
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        result = seeder.seed_index("SP500", enrich=False)

        assert result["seeded"] == 2
        assert result["failed"] == 0
        assert result["total"] == 2

    @patch("boto3.resource")
    @patch("stock_universe_seed.SP500Fetcher")
    def test_seed_index_no_stocks(self, mock_fetcher_class, mock_boto3_resource):
        """Test seeding when no stocks fetched"""
        from stock_universe_seed import StockUniverseSeeder

        mock_fetcher = Mock()
        mock_fetcher.fetch_constituents.return_value = []
        mock_fetcher_class.return_value = mock_fetcher

        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        result = seeder.seed_index("SP500", enrich=False)

        assert "error" in result
        assert result["seeded"] == 0

    @patch("boto3.resource")
    def test_seed_index_unknown_index(self, mock_boto3_resource):
        """Test seeding unknown index returns error"""
        from stock_universe_seed import StockUniverseSeeder

        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        result = seeder.seed_index("UNKNOWN_INDEX", enrich=False)

        assert "error" in result
        assert "Unknown index" in result["error"]


class TestEnrichStocks:
    """Test enriching stocks with market data"""

    @patch("boto3.resource")
    @patch("stock_universe_seed.yf.Tickers")
    def test_enrich_stocks_success(self, mock_tickers_class, mock_boto3_resource):
        """Test successful enrichment with market data"""
        from stock_universe_seed import StockUniverseSeeder

        # Mock yfinance
        mock_ticker = Mock()
        mock_ticker.info = {
            "marketCap": 3000000000000,
            "exchange": "NASDAQ",
            "country": "US",
            "industry": "Technology",
        }
        mock_tickers = Mock()
        mock_tickers.tickers = {"AAPL": mock_ticker}
        mock_tickers_class.return_value = mock_tickers

        # Mock fetcher for FX
        mock_fetcher = Mock()
        mock_fetcher.get_fx_rate.return_value = None
        mock_fetcher.apply_fx_conversion.return_value = 3000000000000

        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        stocks = [{"symbol": "AAPL", "name": "Apple"}]
        index_config = {"currency": "USD", "exchange": "NASDAQ", "region": "US"}

        market_data = seeder._enrich_stocks(stocks, index_config, mock_fetcher)

        assert "AAPL" in market_data
        assert market_data["AAPL"]["marketCap"] == 3000000000000
        assert market_data["AAPL"]["exchange"] == "NASDAQ"

    @patch("boto3.resource")
    @patch("stock_universe_seed.yf.Tickers")
    def test_enrich_stocks_with_fx_conversion(
        self, mock_tickers_class, mock_boto3_resource
    ):
        """Test enrichment with FX conversion for non-USD"""
        from stock_universe_seed import StockUniverseSeeder

        # Mock yfinance
        mock_ticker = Mock()
        mock_ticker.info = {"marketCap": 500000000000}  # ZAR value
        mock_tickers = Mock()
        mock_tickers.tickers = {"AGL.JO": mock_ticker}
        mock_tickers_class.return_value = mock_tickers

        # Mock fetcher for FX conversion
        mock_fetcher = Mock()
        mock_fetcher.get_fx_rate.return_value = 18.5  # ZAR per USD
        mock_fetcher.apply_fx_conversion.return_value = 27027027027  # ~500B / 18.5

        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        stocks = [{"symbol": "AGL.JO", "name": "Anglo American"}]
        index_config = {"currency": "ZAR", "exchange": "JSE", "region": "ZA"}

        market_data = seeder._enrich_stocks(stocks, index_config, mock_fetcher)

        assert "AGL.JO" in market_data
        mock_fetcher.get_fx_rate.assert_called_once()

    @patch("boto3.resource")
    @patch("stock_universe_seed.yf.Tickers")
    def test_enrich_stocks_handles_errors(
        self, mock_tickers_class, mock_boto3_resource
    ):
        """Test enrichment handles individual stock errors"""
        from stock_universe_seed import StockUniverseSeeder

        mock_tickers_class.side_effect = Exception("Network error")

        mock_fetcher = Mock()

        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        stocks = [{"symbol": "AAPL", "name": "Apple"}]
        index_config = {"currency": "USD", "exchange": "NASDAQ", "region": "US"}

        market_data = seeder._enrich_stocks(stocks, index_config, mock_fetcher)

        # Should return empty or partial data, not crash
        assert isinstance(market_data, dict)


class TestSeedToDatabase:
    """Test seeding to DynamoDB"""

    @patch("boto3.resource")
    def test_seed_to_database_success(self, mock_boto3_resource):
        """Test successful batch write to DynamoDB"""
        from stock_universe_seed import StockUniverseSeeder

        mock_batch_writer = Mock()
        mock_batch_writer.__enter__ = Mock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = Mock(return_value=False)

        mock_table = Mock()
        mock_table.batch_writer.return_value = mock_batch_writer

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        stocks = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "sector": "Technology",
                "indexId": "SP500",
                "indexIds": ["SP500"],
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft",
                "sector": "Technology",
                "indexId": "SP500",
                "indexIds": ["SP500"],
            },
        ]
        market_data = {
            "AAPL": {
                "marketCap": 3000000000000,
                "marketCapUSD": 3000000000000,
                "exchange": "NASDAQ",
                "isActive": "true",
            },
            "MSFT": {
                "marketCap": 2800000000000,
                "marketCapUSD": 2800000000000,
                "exchange": "NASDAQ",
                "isActive": "true",
            },
        }
        index_config = {
            "id": "SP500",
            "region": "US",
            "currency": "USD",
            "exchange": "NASDAQ",
            "marketCapThresholds": {
                "mega": 200000000000,
                "large": 10000000000,
                "mid": 2000000000,
            },
        }

        result = seeder._seed_to_database(stocks, market_data, index_config)

        assert result["seeded"] == 2
        assert result["failed"] == 0
        assert mock_batch_writer.put_item.call_count == 2

    @patch("boto3.resource")
    def test_market_cap_bucket_assignment(self, mock_boto3_resource):
        """Test market cap buckets are correctly assigned"""
        from stock_universe_seed import StockUniverseSeeder

        mock_batch_writer = Mock()
        mock_batch_writer.__enter__ = Mock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = Mock(return_value=False)

        mock_table = Mock()
        mock_table.batch_writer.return_value = mock_batch_writer

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        stocks = [
            {
                "symbol": "MEGA",
                "name": "Mega Corp",
                "sector": "Tech",
                "indexId": "SP500",
                "indexIds": ["SP500"],
            },
            {
                "symbol": "SMALL",
                "name": "Small Corp",
                "sector": "Tech",
                "indexId": "SP500",
                "indexIds": ["SP500"],
            },
        ]
        market_data = {
            "MEGA": {
                "marketCapUSD": 300000000000,
                "exchange": "NYSE",
                "isActive": "true",
            },  # > 200B = mega
            "SMALL": {
                "marketCapUSD": 1000000000,
                "exchange": "NYSE",
                "isActive": "true",
            },  # < 2B = small
        }
        index_config = {
            "id": "SP500",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "marketCapThresholds": {
                "mega": 200000000000,
                "large": 10000000000,
                "mid": 2000000000,
            },
        }

        seeder._seed_to_database(stocks, market_data, index_config)

        # Check that put_item was called with correct bucket
        calls = mock_batch_writer.put_item.call_args_list
        items = [call.kwargs["Item"] for call in calls]

        mega_item = next(item for item in items if item["symbol"] == "MEGA")
        small_item = next(item for item in items if item["symbol"] == "SMALL")

        assert mega_item["marketCapBucket"] == "mega"
        assert small_item["marketCapBucket"] == "small"

    @patch("boto3.resource")
    def test_decimal_conversion(self, mock_boto3_resource):
        """Test numeric values are converted to Decimal"""
        from stock_universe_seed import StockUniverseSeeder

        mock_batch_writer = Mock()
        mock_batch_writer.__enter__ = Mock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = Mock(return_value=False)

        mock_table = Mock()
        mock_table.batch_writer.return_value = mock_batch_writer

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        stocks = [
            {
                "symbol": "AAPL",
                "name": "Apple",
                "sector": "Tech",
                "indexId": "SP500",
                "indexIds": ["SP500"],
            }
        ]
        market_data = {
            "AAPL": {
                "marketCap": 3000000000000.50,
                "marketCapUSD": 3000000000000.50,
                "exchange": "NASDAQ",
                "isActive": "true",
            }
        }
        index_config = {
            "id": "SP500",
            "region": "US",
            "currency": "USD",
            "exchange": "NASDAQ",
            "marketCapThresholds": {},
        }

        seeder._seed_to_database(stocks, market_data, index_config)

        call_args = mock_batch_writer.put_item.call_args
        item = call_args.kwargs["Item"]

        assert isinstance(item["marketCap"], Decimal)
        assert isinstance(item["marketCapUSD"], Decimal)


class TestMergeIndexMemberships:
    """Test merging stocks that belong to multiple indices"""

    @patch("boto3.resource")
    def test_merge_overlapping_stocks(self, mock_boto3_resource):
        """Test merging stocks in multiple indices"""
        from stock_universe_seed import StockUniverseSeeder

        mock_batch_writer = Mock()
        mock_batch_writer.__enter__ = Mock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = Mock(return_value=False)

        mock_table = Mock()
        mock_table.scan.return_value = {
            "Items": [
                {"symbol": "AAPL", "name": "Apple", "indexIds": ["SP500"]},
                {
                    "symbol": "AAPL",
                    "name": "Apple",
                    "indexIds": ["RUSSELL3000"],
                },  # Same stock, different index
                {"symbol": "MSFT", "name": "Microsoft", "indexIds": ["SP500"]},
            ]
        }
        mock_table.batch_writer.return_value = mock_batch_writer

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        seeder._merge_index_memberships()

        # Should update AAPL with merged indexIds
        calls = mock_batch_writer.put_item.call_args_list
        assert len(calls) == 1  # Only AAPL should be updated (in both indices)

        item = calls[0].kwargs["Item"]
        assert "SP500" in item["indexIds"]
        assert "RUSSELL3000" in item["indexIds"]

    @patch("boto3.resource")
    def test_no_merge_for_unique_stocks(self, mock_boto3_resource):
        """Test stocks unique to one index are not updated"""
        from stock_universe_seed import StockUniverseSeeder

        mock_batch_writer = Mock()
        mock_batch_writer.__enter__ = Mock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = Mock(return_value=False)

        mock_table = Mock()
        mock_table.scan.return_value = {
            "Items": [
                {"symbol": "UNIQUE1", "name": "Unique 1", "indexIds": ["SP500"]},
                {"symbol": "UNIQUE2", "name": "Unique 2", "indexIds": ["RUSSELL3000"]},
            ]
        }
        mock_table.batch_writer.return_value = mock_batch_writer

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        seeder._merge_index_memberships()

        # No updates needed - no stocks in multiple indices
        mock_batch_writer.put_item.assert_not_called()


class TestSeedAllIndices:
    """Test seeding all indices"""

    @patch("boto3.resource")
    @patch("stock_universe_seed.SP500Fetcher")
    @patch("stock_universe_seed.Russell3000Fetcher")
    @patch("stock_universe_seed.JSEFetcher")
    def test_seed_all_indices(
        self,
        mock_jse_fetcher,
        mock_russell_fetcher,
        mock_sp500_fetcher,
        mock_boto3_resource,
    ):
        """Test seeding all configured indices"""
        from stock_universe_seed import StockUniverseSeeder

        # Mock SP500 fetcher
        mock_sp500 = Mock()
        mock_sp500.fetch_constituents.return_value = [
            {"symbol": "AAPL", "name": "Apple", "sector": "Tech"},
        ]
        mock_sp500_fetcher.return_value = mock_sp500

        # Mock Russell fetcher
        mock_russell = Mock()
        mock_russell.fetch_constituents.return_value = [
            {"symbol": "MSFT", "name": "Microsoft", "sector": "Tech"},
        ]
        mock_russell_fetcher.return_value = mock_russell

        # Mock JSE fetcher
        mock_jse = Mock()
        mock_jse.fetch_constituents.return_value = [
            {"symbol": "AGL.JO", "name": "Anglo", "sector": "Materials"},
        ]
        mock_jse_fetcher.return_value = mock_jse

        mock_batch_writer = Mock()
        mock_batch_writer.__enter__ = Mock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = Mock(return_value=False)

        mock_table = Mock()
        mock_table.scan.return_value = {"Items": []}
        mock_table.batch_writer.return_value = mock_batch_writer

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        results = seeder.seed_all_indices(enrich=False)

        # Should have results for all three indices
        assert "SP500" in results
        assert "RUSSELL3000" in results
        assert "JSE_ALSI" in results

        # Each should be seeded successfully
        for index_id, result in results.items():
            assert result["seeded"] >= 1


class TestE2EWorkflow:
    """End-to-end integration tests"""

    @patch("boto3.resource")
    @patch("stock_universe_seed.yf.Tickers")
    @patch("stock_universe_seed.SP500Fetcher")
    def test_complete_seeding_workflow(
        self, mock_fetcher_class, mock_tickers_class, mock_boto3_resource
    ):
        """Test complete seeding workflow with enrichment"""
        from stock_universe_seed import StockUniverseSeeder

        # Mock fetcher returns stocks
        mock_fetcher = Mock()
        mock_fetcher.fetch_constituents.return_value = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "sector": "Technology",
                "subSector": "Software",
            },
        ]
        mock_fetcher.get_fx_rate.return_value = None
        mock_fetcher.apply_fx_conversion.return_value = 3000000000000
        mock_fetcher_class.return_value = mock_fetcher

        # Mock yfinance returns market data
        mock_ticker = Mock()
        mock_ticker.info = {
            "marketCap": 3000000000000,
            "exchange": "NASDAQ",
            "country": "US",
            "industry": "Consumer Electronics",
        }
        mock_tickers = Mock()
        mock_tickers.tickers = {"AAPL": mock_ticker}
        mock_tickers_class.return_value = mock_tickers

        # Mock DynamoDB
        mock_batch_writer = Mock()
        mock_batch_writer.__enter__ = Mock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = Mock(return_value=False)

        mock_table = Mock()
        mock_table.scan.return_value = {"Items": []}
        mock_table.batch_writer.return_value = mock_batch_writer

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        result = seeder.seed_index("SP500", enrich=True)

        assert result["seeded"] == 1
        assert result["failed"] == 0

        # Verify the item written has all expected fields
        call_args = mock_batch_writer.put_item.call_args
        item = call_args.kwargs["Item"]

        assert item["symbol"] == "AAPL"
        assert item["name"] == "Apple Inc."
        assert item["sector"] == "Technology"
        assert item["subSector"] == "Software"
        assert item["industry"] == "Consumer Electronics"
        assert item["region"] == "US"
        assert item["currency"] == "USD"
        assert item["exchange"] == "NASDAQ"
        assert item["marketCapBucket"] == "mega"  # 3T > 200B threshold
        assert item["isActive"] == "true"
        assert "lastUpdated" in item
        assert "lastValidated" in item

    @patch("boto3.resource")
    @patch("stock_universe_seed.SP500Fetcher")
    def test_partial_failure_handling(self, mock_fetcher_class, mock_boto3_resource):
        """Test handling of partial failures during seeding"""
        from stock_universe_seed import StockUniverseSeeder

        mock_fetcher = Mock()
        mock_fetcher.fetch_constituents.return_value = [
            {"symbol": "AAPL", "name": "Apple", "sector": "Tech"},
            {"symbol": "MSFT", "name": "Microsoft", "sector": "Tech"},
        ]
        mock_fetcher_class.return_value = mock_fetcher

        # Mock batch writer that fails on second item
        mock_batch_writer = Mock()
        mock_batch_writer.__enter__ = Mock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = Mock(return_value=False)

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Database error")

        mock_batch_writer.put_item = Mock(side_effect=side_effect)

        mock_table = Mock()
        mock_table.batch_writer.return_value = mock_batch_writer

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        result = seeder.seed_index("SP500", enrich=False)

        # Should report 1 success and 1 failure
        assert result["seeded"] == 1
        assert result["failed"] == 1
        assert result["total"] == 2


class TestDataValidation:
    """Test data validation during seeding"""

    @patch("boto3.resource")
    def test_stock_has_required_fields(self, mock_boto3_resource):
        """Test that seeded stocks have all required fields"""
        from stock_universe_seed import StockUniverseSeeder

        mock_batch_writer = Mock()
        mock_batch_writer.__enter__ = Mock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = Mock(return_value=False)

        mock_table = Mock()
        mock_table.batch_writer.return_value = mock_batch_writer

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        seeder = StockUniverseSeeder()
        stocks = [
            {
                "symbol": "TEST",
                "name": "Test Co",
                "sector": "Tech",
                "indexId": "SP500",
                "indexIds": ["SP500"],
            }
        ]
        market_data = {
            "TEST": {
                "marketCap": 1000000,
                "marketCapUSD": 1000000,
                "exchange": "NYSE",
                "isActive": "true",
            }
        }
        index_config = {
            "id": "SP500",
            "region": "US",
            "currency": "USD",
            "exchange": "NYSE",
            "marketCapThresholds": {},
        }

        seeder._seed_to_database(stocks, market_data, index_config)

        call_args = mock_batch_writer.put_item.call_args
        item = call_args.kwargs["Item"]

        required_fields = [
            "symbol",
            "name",
            "sector",
            "region",
            "currency",
            "exchange",
            "indexId",
            "indexIds",
            "marketCap",
            "marketCapUSD",
            "marketCapBucket",
            "isActive",
            "lastUpdated",
        ]

        for field in required_fields:
            assert field in item, f"Missing required field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

import json
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime
import os

from index_config import get_default_config


def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


class StockUniverseManager:
    """Manage stock universe database queries with multi-index support"""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(
            os.environ.get("STOCK_UNIVERSE_TABLE", "stock-universe")
        )
        self.index_config = get_default_config()

    def search_stocks(
        self,
        query: str,
        limit: int = 20,
        region: str = None,
        index_id: str = None,
        currency: str = None,
    ) -> list:
        """
        Search stocks by symbol or company name with optional filters

        Args:
            query: Search string (symbol or name)
            limit: Maximum number of results
            region: Filter by region (e.g., 'US', 'ZA')
            index_id: Filter by index (e.g., 'SP500', 'JSE_ALSI')
            currency: Filter by currency (e.g., 'USD', 'ZAR')
        """
        try:
            query_upper = query.upper()
            query_lower = query.lower()
            query_title = query.title()

            # Determine query strategy based on filters
            # Use GSI queries when possible for efficiency
            if index_id and hasattr(self, "table"):
                # Use index-id-index GSI
                try:
                    response = self.table.query(
                        IndexName="index-id-index",
                        KeyConditionExpression=Key("indexId").eq(index_id),
                    )
                except Exception:
                    # GSI might not exist yet, fall back to scan
                    response = self.table.scan()
            elif region and hasattr(self, "table"):
                # Use region-index GSI
                try:
                    response = self.table.query(
                        IndexName="region-index",
                        KeyConditionExpression=Key("region").eq(region),
                    )
                except Exception:
                    # GSI might not exist yet, fall back to scan
                    response = self.table.scan()
            elif currency and hasattr(self, "table"):
                # Use currency-index GSI
                try:
                    response = self.table.query(
                        IndexName="currency-index",
                        KeyConditionExpression=Key("currency").eq(currency),
                    )
                except Exception:
                    # GSI might not exist yet, fall back to scan
                    response = self.table.scan()
            else:
                # Scan all items
                response = self.table.scan()

            items = response.get("Items", [])

            # Filter by symbol or name (case-insensitive)
            filtered_items = []
            for item in items:
                symbol = item.get("symbol", "")
                name = item.get("name", "")

                # Check if query matches (case-insensitive)
                if (
                    query_upper in symbol.upper()
                    or query_lower in name.lower()
                    or query_upper in name.upper()
                    or query_title in name
                ):
                    # Apply additional filters
                    if region and item.get("region") != region:
                        continue
                    if index_id and index_id not in item.get("indexIds", []):
                        continue
                    if currency and item.get("currency") != currency:
                        continue

                    filtered_items.append(item)

            # Sort by relevance (exact symbol match first, then starts with, then alphabetically)
            filtered_items.sort(
                key=lambda item: (
                    0 if item["symbol"] == query_upper else 1,
                    1 if item["symbol"].startswith(query_upper) else 2,
                    item["symbol"],
                )
            )

            return filtered_items[:limit]
        except Exception as err:
            print(f"Error searching stocks: {str(err)}")
            return []

    def get_popular_stocks(self, limit: int = 10) -> list:
        """
        Get most popular/traded stocks
        Returns stocks sorted by market cap (largest first)
        """
        try:
            # Scan and sort by market cap
            response = self.table.scan()
            items = response.get("Items", [])

            # Sort by market cap descending
            items.sort(key=lambda item: float(item.get("marketCap", 0)), reverse=True)

            return items[:limit]
        except Exception as err:
            print(f"Error getting popular stocks: {str(err)}")
            return []

    def get_sectors(self) -> dict:
        """
        Get all sectors with stock counts
        Returns: {sector: count, ...}
        """
        try:
            response = self.table.scan(ProjectionExpression="sector")

            items = response.get("Items", [])

            # Count stocks per sector
            sector_counts = {}
            for item in items:
                sector = item.get("sector", "Unknown")
                sector_counts[sector] = sector_counts.get(sector, 0) + 1

            # Sort by count descending
            sorted_sectors = [
                {"sector": sector, "count": count}
                for sector, count in sorted(
                    sector_counts.items(), key=lambda item: item[1], reverse=True
                )
            ]

            return sorted_sectors
        except Exception as err:
            print(f"Error getting sectors: {str(err)}")
            return []

    def filter_stocks(
        self,
        sector: str = None,
        min_cap: float = None,
        max_cap: float = None,
        market_cap_bucket: str = None,
        region: str = None,
        index_id: str = None,
        currency: str = None,
    ) -> list:
        """
        Filter stocks by various criteria

        Args:
            sector: Filter by sector
            min_cap: Minimum market cap (USD)
            max_cap: Maximum market cap (USD)
            market_cap_bucket: 'mega' (>200B), 'large' (10-200B), 'mid' (2-10B), 'small' (<2B)
            region: Filter by region (e.g., 'US', 'ZA')
            index_id: Filter by index (e.g., 'SP500', 'JSE_ALSI')
            currency: Filter by currency (e.g., 'USD', 'ZAR')
        """
        try:
            filter_expressions = []
            expression_values = {}

            # Filter by sector using GSI
            if sector:
                response = self.table.query(
                    IndexName="sector-index",
                    KeyConditionExpression=Key("sector").eq(sector),
                )
                items = response.get("Items", [])
            else:
                response = self.table.scan()
                items = response.get("Items", [])

            # Apply additional filters (region, index_id, currency)
            if region or index_id or currency:
                filtered_items = []
                for item in items:
                    if region and item.get("region") != region:
                        continue
                    if index_id and index_id not in item.get("indexIds", []):
                        continue
                    if currency and item.get("currency") != currency:
                        continue
                    filtered_items.append(item)
                items = filtered_items

            # Apply market cap filters
            if min_cap is not None or max_cap is not None or market_cap_bucket:
                filtered_items = []
                for item in items:
                    market_cap = float(
                        item.get("marketCapUSD", item.get("marketCap", 0))
                    )

                    # Check market cap bucket
                    if market_cap_bucket:
                        item_bucket = item.get("marketCapBucket", "")
                        if item_bucket != market_cap_bucket:
                            continue

                    # Check min/max cap
                    if min_cap is not None and market_cap < min_cap:
                        continue
                    if max_cap is not None and market_cap > max_cap:
                        continue

                    filtered_items.append(item)

                return filtered_items

            return items
        except Exception as err:
            print(f"Error filtering stocks: {str(err)}")
            return []

    def get_stock_by_symbol(self, symbol: str) -> dict:
        """Get a single stock by symbol"""
        try:
            response = self.table.get_item(Key={"symbol": symbol.upper()})
            return response.get("Item", {})
        except Exception as err:
            print(f"Error getting stock {symbol}: {str(err)}")
            return {}

    def get_all_indices(self) -> list:
        """Get all configured indices with stats"""
        try:
            indices = []

            for index_config in self.index_config.get_all_indices():
                index_id = index_config["id"]

                # Count stocks in this index using GSI
                try:
                    response = self.table.query(
                        IndexName="index-id-index",
                        KeyConditionExpression=Key("indexId").eq(index_id),
                        Select="COUNT",
                    )
                    stock_count = response.get("Count", 0)
                except Exception:
                    # GSI might not exist, use scan with filter
                    response = self.table.scan(
                        FilterExpression=Attr("indexId").eq(index_id), Select="COUNT"
                    )
                    stock_count = response.get("Count", 0)

                # Get last updated timestamp for this index
                last_updated = None
                try:
                    response = self.table.query(
                        IndexName="index-id-index",
                        KeyConditionExpression=Key("indexId").eq(index_id),
                        Limit=1,
                        ProjectionExpression="lastUpdated",
                    )
                    if response.get("Items"):
                        last_updated = response["Items"][0].get("lastUpdated")
                except Exception:
                    pass

                indices.append(
                    {
                        "id": index_config["id"],
                        "name": index_config["name"],
                        "description": index_config["description"],
                        "region": index_config["region"],
                        "currency": index_config["currency"],
                        "stockCount": stock_count,
                        "approxCount": index_config["approxCount"],
                        "lastUpdated": last_updated,
                        "status": "active",
                    }
                )

            return indices

        except Exception as err:
            print(f"Error getting indices: {str(err)}")
            return []

    def get_index_details(self, index_id: str) -> dict:
        """Get details for a specific index"""
        try:
            index_config = self.index_config.get_index(index_id)
            if not index_config:
                return {"error": f"Index not found: {index_id}"}

            # Count stocks
            try:
                response = self.table.query(
                    IndexName="index-id-index",
                    KeyConditionExpression=Key("indexId").eq(index_id),
                    Select="COUNT",
                )
                stock_count = response.get("Count", 0)
            except Exception:
                stock_count = 0

            # Get stocks in this index
            stocks = self.get_index_stocks(index_id)

            return {**index_config, "stockCount": stock_count, "stocks": stocks}

        except Exception as err:
            print(f"Error getting index details: {str(err)}")
            return {"error": str(err)}

    def get_index_stocks(self, index_id: str, limit: int = 100) -> list:
        """Get stocks for a specific index"""
        try:
            try:
                response = self.table.query(
                    IndexName="index-id-index",
                    KeyConditionExpression=Key("indexId").eq(index_id),
                    Limit=limit,
                )
            except Exception:
                # GSI might not exist, use scan with filter
                response = self.table.scan(
                    FilterExpression=Attr("indexId").eq(index_id), Limit=limit
                )

            return response.get("Items", [])

        except Exception as err:
            print(f"Error getting index stocks: {str(err)}")
            return []


def lambda_handler(event, context):
    """Handler for stock universe API endpoints"""

    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "GET,OPTIONS",
            },
            "body": "",
        }

    path = event.get("path", "")
    method = event.get("httpMethod", "GET")
    query_params = event.get("queryStringParameters") or {}

    manager = StockUniverseManager()

    try:
        if method != "GET":
            return {
                "statusCode": 405,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json",
                },
                "body": json.dumps({"error": "Method not allowed"}),
            }

        # Route to appropriate handler
        if "/search" in path:
            query = query_params.get("q", "")
            limit = int(query_params.get("limit", 20))
            region = query_params.get("region")
            index_id = query_params.get("indexId")
            currency = query_params.get("currency")

            if not query:
                result = {"error": 'Query parameter "q" is required'}
            else:
                result = manager.search_stocks(query, limit, region, index_id, currency)

        elif "/popular" in path:
            limit = int(query_params.get("limit", 10))
            result = manager.get_popular_stocks(limit)

        elif "/sectors" in path:
            result = manager.get_sectors()

        elif "/filter" in path:
            sector = query_params.get("sector")
            min_cap = (
                float(query_params["minCap"]) if "minCap" in query_params else None
            )
            max_cap = (
                float(query_params["maxCap"]) if "maxCap" in query_params else None
            )
            market_cap_bucket = query_params.get("marketCapBucket")
            region = query_params.get("region")
            index_id = query_params.get("indexId")
            currency = query_params.get("currency")

            result = manager.filter_stocks(
                sector, min_cap, max_cap, market_cap_bucket, region, index_id, currency
            )

        elif "/symbol/" in path:
            symbol = path.split("/symbol/")[-1]
            result = manager.get_stock_by_symbol(symbol)

        elif "/indices" in path:
            # Check if it's a specific index URL: /api/stocks/indices/{id}
            parts = path.split("/")
            if len(parts) > 4:
                index_id = parts[4]
                if parts[3] == "indices":
                    # /api/stocks/indices/{id}
                    result = manager.get_index_details(index_id)
                elif len(parts) > 5 and parts[5] == "stocks":
                    # /api/stocks/indices/{id}/stocks
                    limit = int(query_params.get("limit", 100))
                    result = manager.get_index_stocks(index_id, limit)
                else:
                    result = {"error": "Invalid endpoint"}
            else:
                # /api/stocks/indices (list all)
                result = manager.get_all_indices()

        else:
            result = {"error": "Invalid endpoint"}

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json",
            },
            "body": json.dumps(result, default=decimal_default),
        }

    except Exception as err:
        print(f"Error processing request: {str(err)}")
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json",
            },
            "body": json.dumps({"error": "Internal server error", "message": str(err)}),
        }

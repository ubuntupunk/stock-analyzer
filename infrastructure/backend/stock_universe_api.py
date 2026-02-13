import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key

from constants import (
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS_GET,
    CORS_ALLOW_ORIGIN,
    DEFAULT_INDEX_STOCKS_LIMIT,
    DEFAULT_MARKET_CAP,
    DEFAULT_POPULAR_LIMIT,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_SECTOR,
    DEFAULT_STATUS,
    DEFAULT_TABLE_NAME,
    ENV_STOCK_UNIVERSE_TABLE,
    ERROR_INDEX_NOT_FOUND,
    ERROR_INTERNAL_SERVER,
    ERROR_INVALID_ENDPOINT,
    ERROR_METHOD_NOT_ALLOWED,
    ERROR_QUERY_REQUIRED,
    GSI_CURRENCY,
    GSI_INDEX_ID,
    GSI_REGION,
    GSI_SECTOR,
    HTTP_METHOD_GET,
    HTTP_METHOD_OPTIONS,
    HTTP_OK,
    HTTP_METHOD_NOT_ALLOWED,
    HTTP_SERVER_ERROR,
    KEY_COUNT,
    KEY_CURRENCY,
    KEY_ERROR,
    KEY_INDEX_ID,
    KEY_INDEX_IDS,
    KEY_ITEMS,
    KEY_LAST_UPDATED,
    KEY_MARKET_CAP,
    KEY_MARKET_CAP_BUCKET,
    KEY_MARKET_CAP_USD,
    KEY_MESSAGE,
    KEY_NAME,
    KEY_REGION,
    KEY_SECTOR,
    KEY_SYMBOL,
    PARAM_CURRENCY,
    PARAM_INDEX_ID,
    PARAM_LIMIT,
    PARAM_MARKET_CAP_BUCKET,
    PARAM_MAX_CAP,
    PARAM_MIN_CAP,
    PARAM_QUERY,
    PARAM_REGION,
    PARAM_SECTOR,
    PATH_FILTER,
    PATH_INDICES,
    PATH_POPULAR,
    PATH_SEARCH,
    PATH_SECTORS,
    PATH_SYMBOL,
    SORT_PRIORITY_CONTAINS,
    SORT_PRIORITY_EXACT_MATCH,
    SORT_PRIORITY_STARTS_WITH,
)
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
        table_name = os.environ.get(ENV_STOCK_UNIVERSE_TABLE, DEFAULT_TABLE_NAME)
        self.table = self.dynamodb.Table(table_name)
        self.index_config = get_default_config()

    def _query_with_gsi_fallback(
        self, gsi_name: str, key_name: str, key_value: str
    ) -> dict:
        """Query using GSI with fallback to scan if GSI doesn't exist"""
        try:
            response = self.table.query(
                IndexName=gsi_name,
                KeyConditionExpression=Key(key_name).eq(key_value),
            )
            return response
        except Exception:
            return self.table.scan()

    def _get_items_by_filter(
        self, index_id: str = None, region: str = None, currency: str = None
    ) -> list:
        """Get items using most efficient query strategy based on filters"""
        if index_id:
            response = self._query_with_gsi_fallback(
                GSI_INDEX_ID, KEY_INDEX_ID, index_id
            )
        elif region:
            response = self._query_with_gsi_fallback(GSI_REGION, KEY_REGION, region)
        elif currency:
            response = self._query_with_gsi_fallback(
                GSI_CURRENCY, KEY_CURRENCY, currency
            )
        else:
            response = self.table.scan()

        return response.get(KEY_ITEMS, [])

    def _matches_search_query(
        self, stock_item: dict, query_upper: str, query_lower: str, query_title: str
    ) -> bool:
        """Check if stock matches search query (case-insensitive)"""
        stock_symbol = stock_item.get(KEY_SYMBOL, "")
        stock_name = stock_item.get(KEY_NAME, "")

        return (
            query_upper in stock_symbol.upper()
            or query_lower in stock_name.lower()
            or query_upper in stock_name.upper()
            or query_title in stock_name
        )

    def _matches_filters(
        self,
        stock_item: dict,
        region: str = None,
        index_id: str = None,
        currency: str = None,
    ) -> bool:
        """Check if stock matches all filter criteria"""
        if region and stock_item.get(KEY_REGION) != region:
            return False
        if index_id and index_id not in stock_item.get(KEY_INDEX_IDS, []):
            return False
        if currency and stock_item.get(KEY_CURRENCY) != currency:
            return False
        return True

    def _calculate_sort_priority(self, stock_item: dict, query_upper: str) -> tuple:
        """Calculate sort priority for search relevance"""
        stock_symbol = stock_item[KEY_SYMBOL]

        if stock_symbol == query_upper:
            return (SORT_PRIORITY_EXACT_MATCH, stock_symbol)
        if stock_symbol.startswith(query_upper):
            return (SORT_PRIORITY_STARTS_WITH, stock_symbol)
        return (SORT_PRIORITY_CONTAINS, stock_symbol)

    def search_stocks(
        self,
        query: str,
        limit: int = DEFAULT_SEARCH_LIMIT,
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

            stock_items = self._get_items_by_filter(index_id, region, currency)

            # Filter by symbol or name (case-insensitive)
            filtered_stocks = [
                stock_item
                for stock_item in stock_items
                if self._matches_search_query(
                    stock_item, query_upper, query_lower, query_title
                )
                and self._matches_filters(stock_item, region, index_id, currency)
            ]

            # Sort by relevance (exact match first, then starts with, then alphabetically)
            filtered_stocks.sort(
                key=lambda item: self._calculate_sort_priority(item, query_upper)
            )

            return filtered_stocks[:limit]
        except Exception as search_error:
            print(f"Error searching stocks: {str(search_error)}")
            return []

    def get_popular_stocks(self, limit: int = DEFAULT_POPULAR_LIMIT) -> list:
        """
        Get most popular/traded stocks
        Returns stocks sorted by market cap (largest first)
        """
        try:
            response = self.table.scan()
            stock_items = response.get(KEY_ITEMS, [])

            # Sort by market cap descending
            stock_items.sort(
                key=lambda item: float(item.get(KEY_MARKET_CAP, DEFAULT_MARKET_CAP)),
                reverse=True,
            )

            return stock_items[:limit]
        except Exception as fetch_error:
            print(f"Error getting popular stocks: {str(fetch_error)}")
            return []

    def get_sectors(self) -> list:
        """
        Get all sectors with stock counts
        Returns: [{sector: str, count: int}, ...]
        """
        try:
            response = self.table.scan(ProjectionExpression=KEY_SECTOR)
            stock_items = response.get(KEY_ITEMS, [])

            # Count stocks per sector
            sector_counts = {}
            for stock_item in stock_items:
                sector_name = stock_item.get(KEY_SECTOR, DEFAULT_SECTOR)
                sector_counts[sector_name] = sector_counts.get(sector_name, 0) + 1

            # Sort by count descending
            sorted_sectors = [
                {KEY_SECTOR: sector_name, KEY_COUNT: count}
                for sector_name, count in sorted(
                    sector_counts.items(), key=lambda x: x[1], reverse=True
                )
            ]

            return sorted_sectors
        except Exception as fetch_error:
            print(f"Error getting sectors: {str(fetch_error)}")
            return []

    def _get_market_cap_value(self, stock_item: dict) -> float:
        """Extract market cap value from stock item"""
        return float(
            stock_item.get(
                KEY_MARKET_CAP_USD, stock_item.get(KEY_MARKET_CAP, DEFAULT_MARKET_CAP)
            )
        )

    def _matches_market_cap_filters(
        self,
        stock_item: dict,
        min_cap: float = None,
        max_cap: float = None,
        market_cap_bucket: str = None,
    ) -> bool:
        """Check if stock matches market cap filter criteria"""
        market_cap_value = self._get_market_cap_value(stock_item)

        if market_cap_bucket:
            item_bucket = stock_item.get(KEY_MARKET_CAP_BUCKET, "")
            if item_bucket != market_cap_bucket:
                return False

        if min_cap is not None and market_cap_value < min_cap:
            return False

        if max_cap is not None and market_cap_value > max_cap:
            return False

        return True

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
            # Filter by sector using GSI if available
            if sector:
                response = self.table.query(
                    IndexName=GSI_SECTOR,
                    KeyConditionExpression=Key(KEY_SECTOR).eq(sector),
                )
                stock_items = response.get(KEY_ITEMS, [])
            else:
                response = self.table.scan()
                stock_items = response.get(KEY_ITEMS, [])

            # Apply region, index, currency filters
            if region or index_id or currency:
                stock_items = [
                    stock_item
                    for stock_item in stock_items
                    if self._matches_filters(stock_item, region, index_id, currency)
                ]

            # Apply market cap filters
            has_market_cap_filter = (
                min_cap is not None or max_cap is not None or market_cap_bucket
            )
            if has_market_cap_filter:
                stock_items = [
                    stock_item
                    for stock_item in stock_items
                    if self._matches_market_cap_filters(
                        stock_item, min_cap, max_cap, market_cap_bucket
                    )
                ]

            return stock_items
        except Exception as filter_error:
            print(f"Error filtering stocks: {str(filter_error)}")
            return []

    def get_stock_by_symbol(self, symbol: str) -> dict:
        """Get a single stock by symbol"""
        try:
            response = self.table.get_item(Key={KEY_SYMBOL: symbol.upper()})
            return response.get("Item", {})
        except Exception as fetch_error:
            print(f"Error getting stock {symbol}: {str(fetch_error)}")
            return {}

    def _count_index_stocks(self, index_id: str) -> int:
        """Count stocks in a specific index using GSI with fallback"""
        try:
            response = self.table.query(
                IndexName=GSI_INDEX_ID,
                KeyConditionExpression=Key(KEY_INDEX_ID).eq(index_id),
                Select="COUNT",
            )
            return response.get(KEY_COUNT, 0)
        except Exception:
            # GSI might not exist, use scan with filter
            response = self.table.scan(
                FilterExpression=Attr(KEY_INDEX_ID).eq(index_id), Select="COUNT"
            )
            return response.get(KEY_COUNT, 0)

    def _get_index_last_updated(self, index_id: str) -> str:
        """Get last updated timestamp for an index"""
        try:
            response = self.table.query(
                IndexName=GSI_INDEX_ID,
                KeyConditionExpression=Key(KEY_INDEX_ID).eq(index_id),
                Limit=1,
                ProjectionExpression=KEY_LAST_UPDATED,
            )
            items = response.get(KEY_ITEMS, [])
            if items:
                return items[0].get(KEY_LAST_UPDATED)
        except Exception:
            pass
        return None

    def get_all_indices(self) -> list:
        """Get all configured indices with stats"""
        try:
            indices = []

            for index_config in self.index_config.get_all_indices():
                index_id = index_config["id"]
                stock_count = self._count_index_stocks(index_id)
                last_updated = self._get_index_last_updated(index_id)

                indices.append(
                    {
                        "id": index_config["id"],
                        KEY_NAME: index_config[KEY_NAME],
                        "description": index_config["description"],
                        KEY_REGION: index_config[KEY_REGION],
                        KEY_CURRENCY: index_config[KEY_CURRENCY],
                        "stockCount": stock_count,
                        "approxCount": index_config["approxCount"],
                        KEY_LAST_UPDATED: last_updated,
                        "status": DEFAULT_STATUS,
                    }
                )

            return indices

        except Exception as fetch_error:
            print(f"Error getting indices: {str(fetch_error)}")
            return []

    def get_index_details(self, index_id: str) -> dict:
        """Get details for a specific index"""
        try:
            index_config = self.index_config.get_index(index_id)
            if not index_config:
                return {KEY_ERROR: ERROR_INDEX_NOT_FOUND.format(index_id)}

            stock_count = self._count_index_stocks(index_id)
            index_stocks = self.get_index_stocks(index_id)

            return {
                **index_config,
                "stockCount": stock_count,
                PATH_STOCKS: index_stocks,
            }

        except Exception as fetch_error:
            print(f"Error getting index details: {str(fetch_error)}")
            return {KEY_ERROR: str(fetch_error)}

    def get_index_stocks(
        self, index_id: str, limit: int = DEFAULT_INDEX_STOCKS_LIMIT
    ) -> list:
        """Get stocks for a specific index"""
        try:
            try:
                response = self.table.query(
                    IndexName=GSI_INDEX_ID,
                    KeyConditionExpression=Key(KEY_INDEX_ID).eq(index_id),
                    Limit=limit,
                )
            except Exception:
                # GSI might not exist, use scan with filter
                response = self.table.scan(
                    FilterExpression=Attr(KEY_INDEX_ID).eq(index_id), Limit=limit
                )

            return response.get(KEY_ITEMS, [])

        except Exception as fetch_error:
            print(f"Error getting index stocks: {str(fetch_error)}")
            return []


def _create_cors_headers() -> dict:
    """Create CORS headers for responses"""
    return {
        "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
        "Content-Type": "application/json",
    }


def _create_response(status_code: int, response_body: dict) -> dict:
    """Create standardized API response"""
    return {
        KEY_STATUS_CODE: status_code,
        "headers": _create_cors_headers(),
        KEY_BODY: json.dumps(response_body, default=decimal_default),
    }


def _handle_options_request() -> dict:
    """Handle CORS preflight OPTIONS request"""
    return {
        KEY_STATUS_CODE: HTTP_OK,
        "headers": {
            "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
            "Access-Control-Allow-Headers": CORS_ALLOW_HEADERS,
            "Access-Control-Allow-Methods": CORS_ALLOW_METHODS_GET,
        },
        KEY_BODY: "",
    }


def _handle_search_request(manager: StockUniverseManager, query_params: dict) -> dict:
    """Handle stock search request"""
    query_string = query_params.get(PARAM_QUERY, "")
    if not query_string:
        return {KEY_ERROR: ERROR_QUERY_REQUIRED}

    limit = int(query_params.get(PARAM_LIMIT, DEFAULT_SEARCH_LIMIT))
    region = query_params.get(PARAM_REGION)
    index_id = query_params.get(PARAM_INDEX_ID)
    currency = query_params.get(PARAM_CURRENCY)

    return manager.search_stocks(query_string, limit, region, index_id, currency)


def _handle_popular_request(manager: StockUniverseManager, query_params: dict) -> dict:
    """Handle popular stocks request"""
    limit = int(query_params.get(PARAM_LIMIT, DEFAULT_POPULAR_LIMIT))
    return manager.get_popular_stocks(limit)


def _handle_filter_request(manager: StockUniverseManager, query_params: dict) -> dict:
    """Handle stock filter request"""
    sector = query_params.get(PARAM_SECTOR)
    min_cap = (
        float(query_params[PARAM_MIN_CAP]) if PARAM_MIN_CAP in query_params else None
    )
    max_cap = (
        float(query_params[PARAM_MAX_CAP]) if PARAM_MAX_CAP in query_params else None
    )
    market_cap_bucket = query_params.get(PARAM_MARKET_CAP_BUCKET)
    region = query_params.get(PARAM_REGION)
    index_id = query_params.get(PARAM_INDEX_ID)
    currency = query_params.get(PARAM_CURRENCY)

    return manager.filter_stocks(
        sector, min_cap, max_cap, market_cap_bucket, region, index_id, currency
    )


def _handle_symbol_request(manager: StockUniverseManager, path: str) -> dict:
    """Handle get stock by symbol request"""
    symbol = path.split(PATH_SYMBOL)[-1]
    return manager.get_stock_by_symbol(symbol)


def _handle_indices_request(
    manager: StockUniverseManager, path: str, query_params: dict
) -> dict:
    """Handle indices-related requests"""
    path_parts = path.split("/")

    # /api/stocks/indices (list all)
    if len(path_parts) <= 4:
        return manager.get_all_indices()

    index_id = path_parts[4]

    # /api/stocks/indices/{id}/stocks
    if len(path_parts) > 5 and path_parts[5] == PATH_STOCKS.strip("/"):
        limit = int(query_params.get(PARAM_LIMIT, DEFAULT_INDEX_STOCKS_LIMIT))
        return manager.get_index_stocks(index_id, limit)

    # /api/stocks/indices/{id}
    if path_parts[3] == PATH_INDICES.strip("/"):
        return manager.get_index_details(index_id)

    return {KEY_ERROR: ERROR_INVALID_ENDPOINT}


def _route_request(
    manager: StockUniverseManager, path: str, query_params: dict
) -> dict:
    """Route request to appropriate handler based on path"""
    if PATH_SEARCH in path:
        return _handle_search_request(manager, query_params)

    if PATH_POPULAR in path:
        return _handle_popular_request(manager, query_params)

    if PATH_SECTORS in path:
        return manager.get_sectors()

    if PATH_FILTER in path:
        return _handle_filter_request(manager, query_params)

    if PATH_SYMBOL in path:
        return _handle_symbol_request(manager, path)

    if PATH_INDICES in path:
        return _handle_indices_request(manager, path, query_params)

    return {KEY_ERROR: ERROR_INVALID_ENDPOINT}


def lambda_handler(event, context):
    """Handler for stock universe API endpoints"""

    # Handle CORS preflight
    if event.get("httpMethod") == HTTP_METHOD_OPTIONS:
        return _handle_options_request()

    path = event.get("path", "")
    http_method = event.get("httpMethod", HTTP_METHOD_GET)
    query_params = event.get("queryStringParameters") or {}

    manager = StockUniverseManager()

    try:
        if http_method != HTTP_METHOD_GET:
            return _create_response(
                HTTP_METHOD_NOT_ALLOWED, {KEY_ERROR: ERROR_METHOD_NOT_ALLOWED}
            )

        api_result = _route_request(manager, path, query_params)
        return _create_response(HTTP_OK, api_result)

    except Exception as request_error:
        print(f"Error processing request: {str(request_error)}")
        return _create_response(
            HTTP_SERVER_ERROR,
            {KEY_ERROR: ERROR_INTERNAL_SERVER, KEY_MESSAGE: str(request_error)},
        )

"""
AWS Lambda Handler for Stock Data API
Handles HTTP routing and CORS for all stock data endpoints
"""

import json
import math

from constants import (
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS_GET,
    CORS_ALLOW_ORIGIN,
    DELIMITER_COMMA,
    ERROR_METHOD_NOT_ALLOWED,
    ERROR_SYMBOL_REQUIRED,
    ERROR_SYMBOLS_REQUIRED,
    HTTP_BAD_REQUEST,
    HTTP_METHOD_GET,
    HTTP_METHOD_NOT_ALLOWED,
    HTTP_METHOD_OPTIONS,
    HTTP_METHOD_POST,
    HTTP_OK,
    HTTP_SERVER_ERROR,
    KEY_BODY,
    KEY_ERROR,
    KEY_STATUS_CODE,
    PARAM_PERIOD,
    QUERY_PARAM_SYMBOL,
    QUERY_PARAM_SYMBOLS,
    REQUEST_KEY_BODY,
    REQUEST_KEY_HTTP_METHOD,
    REQUEST_KEY_PATH,
    REQUEST_KEY_QUERY_STRING_PARAMS,
)
from screener_api import StockScreener
from stock_api import StockDataAPI, decimal_default


def clean_float_values(obj):
    """
    Recursively replace NaN, Infinity, and -Infinity with None
    to ensure valid JSON serialization.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    if isinstance(obj, dict):
        return {key: clean_float_values(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [clean_float_values(item) for item in obj]
    return obj


def _create_cors_headers():
    """Create CORS headers"""
    return {
        "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
        "Content-Type": "application/json",
    }


def _create_response(status_code: int, response_body: dict) -> dict:
    """Create standardized API response"""
    cleaned_body = clean_float_values(response_body)
    return {
        KEY_STATUS_CODE: status_code,
        "headers": _create_cors_headers(),
        KEY_BODY: json.dumps(cleaned_body, default=decimal_default),
    }


def _handle_options_request() -> dict:
    """Handle CORS preflight"""
    return {
        KEY_STATUS_CODE: HTTP_OK,
        "headers": {
            "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
            "Access-Control-Allow-Headers": CORS_ALLOW_HEADERS,
            "Access-Control-Allow-Methods": CORS_ALLOW_METHODS_GET,
        },
        KEY_BODY: "",
    }


def lambda_handler(event, context):
    """
    AWS Lambda handler for stock data API

    Single stock endpoints:
        /api/stock/metrics?symbol=AAPL
        /api/stock/price?symbol=AAPL
        /api/stock/estimates?symbol=AAPL
        /api/stock/financials?symbol=AAPL
        /api/stock/factors?symbol=AAPL
        /api/stock/news?symbol=AAPL

    Batch endpoints (NEW):
        /api/stock/batch/prices?symbols=AAPL,MSFT,GOOGL
        /api/stock/batch/metrics?symbols=AAPL,MSFT,GOOGL
        /api/stock/batch/estimates?symbols=AAPL,MSFT,GOOGL
        /api/stock/batch/financials?symbols=AAPL,MSFT,GOOGL
    """

    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            },
            "body": "",
        }

    path = event.get("path", "")
    method = event.get("httpMethod", "GET")
    query_params = event.get("queryStringParameters") or {}

    # Initialize API
    api = StockDataAPI()

    try:
        # Check if this is a batch request
        if "/batch/" in path:
            # Batch endpoints - require 'symbols' parameter (comma-separated)
            symbols_param = query_params.get("symbols", "")
            if not symbols_param:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Access-Control-Allow-Origin": "*",
                        "Content-Type": "application/json",
                    },
                    "body": json.dumps(
                        {
                            "error": "Symbols parameter is required (comma-separated list)"
                        }
                    ),
                }

            # Parse comma-separated symbols
            symbols = [
                suffix.strip().upper()
                for suffix in symbols_param.split(",")
                if suffix.strip()
            ]

            if not symbols:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Access-Control-Allow-Origin": "*",
                        "Content-Type": "application/json",
                    },
                    "body": json.dumps({"error": "At least one symbol is required"}),
                }

            # Limit batch size to prevent abuse
            if len(symbols) > 50:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Access-Control-Allow-Origin": "*",
                        "Content-Type": "application/json",
                    },
                    "body": json.dumps(
                        {"error": "Maximum 50 symbols per batch request"}
                    ),
                }

            # Route to appropriate batch handler
            if "/batch/prices" in path or "/batch/price" in path:
                result = api.get_batch_prices(symbols)
            elif "/batch/metrics" in path:
                result = api.get_batch_metrics(symbols)
            elif "/batch/estimates" in path:
                result = api.get_batch_estimates(symbols)
            elif "/batch/financials" in path:
                result = api.get_batch_financials(symbols)
            else:
                result = {"error": "Invalid batch endpoint"}

        elif "/screen" in path:
            screener = StockScreener()
            if method == "POST":
                try:
                    body = json.loads(event.get("body", "{}"))
                    criteria = body.get("criteria", {})
                    result = screener.screen_stocks(criteria)
                except Exception as err:
                    return {
                        "statusCode": 400,
                        "headers": {
                            "Access-Control-Allow-Origin": "*",
                            "Content-Type": "application/json",
                        },
                        "body": json.dumps({"error": str(err)}),
                    }
            else:
                return {
                    "statusCode": 405,
                    "headers": {
                        "Access-Control-Allow-Origin": "*",
                        "Content-Type": "application/json",
                    },
                    "body": json.dumps({"error": "Method not allowed"}),
                }

        else:
            # Single stock endpoints - require 'symbol' parameter
            symbol = query_params.get("symbol", "").upper()

            if not symbol:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Access-Control-Allow-Origin": "*",
                        "Content-Type": "application/json",
                    },
                    "body": json.dumps({"error": "Symbol parameter is required"}),
                }

            # Route to appropriate single stock handler
            if "/metrics" in path:
                result = api.get_stock_metrics(symbol)
            elif "/price" in path:
                # Support optional period parameter for historical data
                period = query_params.get("period", "1mo")
                startDate = query_params.get("startDate", None)
                endDate = query_params.get("endDate", None)
                result = api.get_stock_price(symbol, period, startDate, endDate)
            elif "/estimates" in path:
                result = api.get_analyst_estimates(symbol)
            elif "/financials" in path:
                result = api.get_financial_statements(symbol)
            elif "/factors" in path:
                result = api.get_stock_factors(symbol)
            elif "/news" in path:
                result = api.get_stock_news(symbol)
            else:
                result = {"error": "Invalid endpoint"}

        # Clean result of NaN/Infinity values before serialization
        cleaned_result = clean_float_values(result)

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json",
            },
            "body": json.dumps(cleaned_result, default=decimal_default),
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

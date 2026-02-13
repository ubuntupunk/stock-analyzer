import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3

from constants import (
    ENV_WATCHLIST_TABLE,
    KEY_ERROR,
    KEY_ITEMS,
    WATCHLIST_DEFAULT_TABLE,
    WATCHLIST_EXPR_ALERT,
    WATCHLIST_EXPR_NOTES,
    WATCHLIST_EXPR_TAGS,
    WATCHLIST_EXPR_UID,
    WATCHLIST_KEY_ADDED_AT,
    WATCHLIST_KEY_ALERT_PRICE,
    WATCHLIST_KEY_NOTES,
    WATCHLIST_KEY_SYMBOL,
    WATCHLIST_KEY_TAGS,
    WATCHLIST_KEY_USER_ID,
    WATCHLIST_QUERY_USER_ID,
    WATCHLIST_RESULT_ITEM,
    WATCHLIST_RESULT_SUCCESS,
    WATCHLIST_UPDATE_ALERT,
    WATCHLIST_UPDATE_NOTES,
    WATCHLIST_UPDATE_TAGS,
)

# Configure logging
logger = logging.getLogger(__name__)


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


class WatchlistManager:
    """Manage user watchlists"""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        table_name = os.environ.get(ENV_WATCHLIST_TABLE, WATCHLIST_DEFAULT_TABLE)
        self.watchlist_table = self.dynamodb.Table(table_name)

    def add_to_watchlist(self, user_id: str, stock_data: dict) -> dict:
        """Add a stock to user's watchlist"""
        try:
            alert_price = stock_data.get(WATCHLIST_KEY_ALERT_PRICE)
            item = {
                WATCHLIST_KEY_USER_ID: user_id,
                WATCHLIST_KEY_SYMBOL: stock_data.get(WATCHLIST_KEY_SYMBOL),
                WATCHLIST_KEY_ADDED_AT: datetime.now(timezone.utc).isoformat(),
                WATCHLIST_KEY_NOTES: stock_data.get(WATCHLIST_KEY_NOTES, ""),
                WATCHLIST_KEY_ALERT_PRICE: (
                    Decimal(str(alert_price)) if alert_price is not None else None
                ),
                WATCHLIST_KEY_TAGS: stock_data.get(WATCHLIST_KEY_TAGS, []),
            }

            self.watchlist_table.put_item(Item=item)
            return {WATCHLIST_RESULT_SUCCESS: True, WATCHLIST_RESULT_ITEM: item}
        except Exception as add_error:
            return {WATCHLIST_RESULT_SUCCESS: False, KEY_ERROR: str(add_error)}

    def remove_from_watchlist(self, user_id: str, symbol: str) -> dict:
        """Remove a stock from watchlist"""
        try:
            self.watchlist_table.delete_item(
                Key={WATCHLIST_KEY_USER_ID: user_id, WATCHLIST_KEY_SYMBOL: symbol}
            )
            return {WATCHLIST_RESULT_SUCCESS: True}
        except Exception as remove_error:
            return {WATCHLIST_RESULT_SUCCESS: False, KEY_ERROR: str(remove_error)}

    def get_watchlist(self, user_id: str) -> list:
        """Get user's watchlist"""
        try:
            response = self.watchlist_table.query(
                KeyConditionExpression=WATCHLIST_QUERY_USER_ID,
                ExpressionAttributeValues={WATCHLIST_EXPR_UID: user_id},
            )
            return response.get(KEY_ITEMS, [])
        except Exception as get_error:
            return {WATCHLIST_RESULT_SUCCESS: False, KEY_ERROR: str(get_error)}

    def update_watchlist_item(self, user_id: str, symbol: str, updates: dict) -> dict:
        """Update watchlist item"""
        try:
            update_expression = []
            expression_values = {}

            if "notes" in updates:
                update_expression.append("notes = :notes")
                expression_values[":notes"] = updates["notes"]

            if "alertPrice" in updates:
                update_expression.append("alertPrice = :alert")
                expression_values[":alert"] = Decimal(str(updates["alertPrice"]))

            if "tags" in updates:
                update_expression.append("tags = :tags")
                expression_values[":tags"] = updates["tags"]

            if not update_expression:
                return {"success": False, "error": "No updates provided"}

            response = self.watchlist_table.update_item(
                Key={"userId": user_id, "symbol": symbol},
                UpdateExpression="SET " + ", ".join(update_expression),
                ExpressionAttributeValues=expression_values,
                ReturnValues="ALL_NEW",
            )

            return {"success": True, "item": response["Attributes"]}
        except Exception as err:
            return {"success": False, "error": str(err)}


def lambda_handler(event, context):
    """Handler for watchlist operations"""

    if event["httpMethod"] == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            },
            "body": "",
        }

    path = event.get("path", "")
    method = event.get("httpMethod", "GET")
    manager = WatchlistManager()
    http_method = event["httpMethod"]
    path = event["path"]
    query_params = event.get("queryStringParameters", {}) or {}

    # Get user ID from Cognito (you'll need to implement this)
    # For now, using a placeholder - in production, extract from JWT token
    user_id = "test-user"  # TODO: Extract from Cognito JWT

    result = {}

    try:
        if http_method == "GET" and path == "/api/watchlist":
            result = manager.get_watchlist(user_id)
        elif http_method == "POST" and path == "/api/watchlist":
            body = json.loads(event.get("body", "{}"))
            result = manager.add_to_watchlist(user_id, body)
        elif http_method == "PUT" and path == "/api/watchlist":
            body = json.loads(event.get("body", "{}"))
            result = manager.update_watchlist_item(
                user_id, body.get("symbol"), body.get("updates", {})
            )
        elif http_method == "DELETE" and path == "/api/watchlist":
            symbol = query_params.get("symbol")
            if not symbol:
                result = {"success": False, "error": "Symbol required"}
            else:
                result = manager.remove_from_watchlist(user_id, symbol)
        else:
            result = {"error": "Method not allowed"}

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
                "Content-Type": "application/json",
            },
            "body": json.dumps(result, default=decimal_default),
        }

    except Exception as err:
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
                "Content-Type": "application/json",
            },
            "body": json.dumps({"error": str(err)}),
        }

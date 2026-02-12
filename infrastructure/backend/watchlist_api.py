import json
import boto3
from decimal import Decimal
from datetime import datetime, timezone
import uuid
import os


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


class WatchlistManager:
    """Manage user watchlists"""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.watchlist_table = self.dynamodb.Table(
            os.environ.get("WATCHLIST_TABLE", "stock-watchlist")
        )

    def add_to_watchlist(self, user_id: str, stock_data: dict) -> dict:
        """Add a stock to user's watchlist"""
        try:
            item = {
                "userId": user_id,
                "symbol": stock_data.get("symbol"),
                "addedAt": datetime.now(timezone.utc).isoformat(),
                "notes": stock_data.get("notes", ""),
                "alertPrice": Decimal(str(stock_data.get("alertPrice")))
                if stock_data.get("alertPrice") is not None
                else None,
                "tags": stock_data.get("tags", []),
            }

            self.watchlist_table.put_item(Item=item)
            return {"success": True, "item": item}
        except Exception as err:
            return {"success": False, "error": str(err)}

    def remove_from_watchlist(self, user_id: str, symbol: str) -> dict:
        """Remove a stock from watchlist"""
        try:
            self.watchlist_table.delete_item(Key={"userId": user_id, "symbol": symbol})
            return {"success": True}
        except Exception as err:
            return {"success": False, "error": str(err)}

    def get_watchlist(self, user_id: str) -> list:
        """Get user's watchlist"""
        try:
            response = self.watchlist_table.query(
                KeyConditionExpression="userId = :uid",
                ExpressionAttributeValues={":uid": user_id},
            )
            return response.get("Items", [])
        except Exception as err:
            return {"success": False, "error": str(err)}

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

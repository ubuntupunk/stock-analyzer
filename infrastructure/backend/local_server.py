"""
Local Development Flask Server for Stock Analyzer
Serves the frontend and provides API endpoints
"""

import json
import math
import os
import sys

from flask import (
    Flask,
    abort,
    g,
    jsonify,
    render_template,
    request,
    send_from_directory,
)
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from functools import wraps

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import (
    CONTEXT_KEY_USER_ID,
    ERROR_AUTH_REQUIRED,
    ERROR_INVALID_TOKEN,
    ERROR_SYMBOL_PARAM_REQUIRED,
    ERROR_SYMBOLS_PARAM_REQUIRED,
    HEADER_AUTHORIZATION,
    HEADER_BEARER_PREFIX,
    HTTP_UNAUTHORIZED,
    LOCAL_DEV_TOKEN,
    LOCAL_DEV_USER_ID,
    LOCAL_SERVER_HOST,
    LOCAL_SERVER_PORT,
    PARAM_END_DATE,
    PARAM_START_DATE,
    QUERY_PARAM_PERIOD,
    QUERY_PARAM_SYMBOL,
    QUERY_PARAM_SYMBOLS,
    ROUTE_API_HEALTH,
    ROUTE_API_SCREENER_DCF,
    ROUTE_API_SCREENER_SCREEN,
    ROUTE_API_STOCK_BATCH_ESTIMATES,
    ROUTE_API_STOCK_BATCH_FINANCIALS,
    ROUTE_API_STOCK_BATCH_METRICS,
    ROUTE_API_STOCK_BATCH_PRICES,
    ROUTE_API_STOCK_ESTIMATES,
    ROUTE_API_STOCK_FACTORS,
    ROUTE_API_STOCK_FINANCIALS,
    ROUTE_API_STOCK_METRICS,
    ROUTE_API_STOCK_NEWS,
    ROUTE_API_STOCK_PRICE,
    ROUTE_API_STOCK_PRICE_HISTORY,
    ROUTE_API_STOCKS_POPULAR,
    ROUTE_API_STOCKS_SEARCH,
    ROUTE_API_WATCHLIST,
    ROUTE_API_WATCHLIST_ITEM,
    ROUTE_INDEX,
    ROUTE_STATIC,
    TEMPLATE_FOLDER_FRONTEND,
)
from screener_api import StockScreener
from stock_api import StockDataAPI
from watchlist_api import WatchlistManager


# Custom JSON provider to handle NaN and Infinity values
class SafeJSONProvider(DefaultJSONProvider):
    def dumps(self, json_obj, **kwargs):
        """Dump JSON with NaN/Inf sanitization"""
        return super().dumps(self._sanitize_value(json_obj), **kwargs)

    def _sanitize_value(self, value):
        """Recursively sanitize NaN and Inf values"""
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
        elif isinstance(value, dict):
            return {key: self._sanitize_value(val) for key, val in value.items()}
        elif isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        return value


app = Flask(__name__, template_folder=TEMPLATE_FOLDER_FRONTEND)
app.json = SafeJSONProvider(app)
CORS(app)  # Enable CORS for all routes


@app.before_request
def before_request():
    """Initialize user context for each request"""
    setattr(g, CONTEXT_KEY_USER_ID, None)
    auth_header = request.headers.get(HEADER_AUTHORIZATION)

    if auth_header and auth_header.startswith(HEADER_BEARER_PREFIX):
        token = auth_header.split(" ")[1]
        if token == LOCAL_DEV_TOKEN:
            setattr(g, CONTEXT_KEY_USER_ID, LOCAL_DEV_USER_ID)
        else:
            print(ERROR_INVALID_TOKEN.format(token))


def auth_required(handler_func):
    """Decorator to require authentication for routes"""

    @wraps(handler_func)
    def decorated_function(*args, **kwargs):
        if not getattr(g, CONTEXT_KEY_USER_ID, None):
            abort(HTTP_UNAUTHORIZED, description=ERROR_AUTH_REQUIRED)
        return handler_func(*args, **kwargs)

    return decorated_function


# Initialize the Stock Data API
stock_api = StockDataAPI()


def _validate_symbol_param() -> tuple:
    """Validate and extract symbol parameter from request"""
    stock_symbol = request.args.get(QUERY_PARAM_SYMBOL)
    if not stock_symbol:
        return None, (
            jsonify({KEY_ERROR: ERROR_SYMBOL_PARAM_REQUIRED}),
            HTTP_BAD_REQUEST,
        )
    return stock_symbol.upper(), None


def _validate_symbols_param() -> tuple:
    """Validate and extract symbols parameter from request"""
    symbols_str = request.args.get(QUERY_PARAM_SYMBOLS)
    if not symbols_str:
        return None, (
            jsonify({KEY_ERROR: ERROR_SYMBOLS_PARAM_REQUIRED}),
            HTTP_BAD_REQUEST,
        )
    return symbols_str.split(DELIMITER_COMMA), None


# Popular stocks fallback for local development (when DynamoDB is unavailable)
LOCAL_POPULAR_STOCKS = [
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "marketCap": 2890000000000,
        "price": 185.92,
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "sector": "Technology",
        "marketCap": 2780000000000,
        "price": 398.67,
    },
    {
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "sector": "Technology",
        "marketCap": 1750000000000,
        "price": 142.65,
    },
    {
        "symbol": "AMZN",
        "name": "Amazon.com Inc.",
        "sector": "Consumer Cyclical",
        "marketCap": 1580000000000,
        "price": 171.81,
    },
    {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "sector": "Technology",
        "marketCap": 1200000000000,
        "price": 726.13,
    },
    {
        "symbol": "META",
        "name": "Meta Platforms Inc.",
        "sector": "Technology",
        "marketCap": 980000000000,
        "price": 473.32,
    },
    {
        "symbol": "TSLA",
        "name": "Tesla Inc.",
        "sector": "Consumer Cyclical",
        "marketCap": 780000000000,
        "price": 188.85,
    },
    {
        "symbol": "BRK.B",
        "name": "Berkshire Hathaway Inc.",
        "sector": "Financial",
        "marketCap": 780000000000,
        "price": 400.12,
    },
    {
        "symbol": "LLY",
        "name": "Eli Lilly and Company",
        "sector": "Healthcare",
        "marketCap": 560000000000,
        "price": 740.21,
    },
    {
        "symbol": "V",
        "name": "Visa Inc.",
        "sector": "Financial",
        "marketCap": 520000000000,
        "price": 275.14,
    },
    {
        "symbol": "TSM",
        "name": "Taiwan Semiconductor",
        "sector": "Technology",
        "marketCap": 510000000000,
        "price": 129.53,
    },
    {
        "symbol": "JPM",
        "name": "JPMorgan Chase & Co.",
        "sector": "Financial",
        "marketCap": 490000000000,
        "price": 172.11,
    },
    {
        "symbol": "WMT",
        "name": "Walmart Inc.",
        "sector": "Consumer Defensive",
        "marketCap": 420000000000,
        "price": 170.36,
    },
    {
        "symbol": "XOM",
        "name": "Exxon Mobil Corporation",
        "sector": "Energy",
        "marketCap": 410000000000,
        "price": 102.45,
    },
    {
        "symbol": "MA",
        "name": "Mastercard Inc.",
        "sector": "Financial",
        "marketCap": 400000000000,
        "price": 455.67,
    },
]

# Serve static files from frontend directory
frontend_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
)
print(f"Serving frontend from: {frontend_path}")


@app.route("/")
def index():
    return send_from_directory(frontend_path, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(frontend_path, filename)


# Stock Data API Endpoints
@app.route(ROUTE_API_STOCK_PRICE)
def get_price():
    """Get stock price endpoint"""
    stock_symbol, error_response = _validate_symbol_param()
    if error_response:
        return error_response

    api_result = stock_api.get_stock_price(stock_symbol)
    return jsonify(api_result)


@app.route(ROUTE_API_STOCK_PRICE_HISTORY)
def get_price_history():
    """Get stock price history endpoint"""
    stock_symbol, error_response = _validate_symbol_param()
    if error_response:
        return error_response

    period = request.args.get(QUERY_PARAM_PERIOD, STOCK_API_DEFAULT_PERIOD)
    start_date = request.args.get(PARAM_START_DATE)
    end_date = request.args.get(PARAM_END_DATE)

    if start_date and end_date:
        api_result = stock_api.get_stock_price(
            stock_symbol, startDate=start_date, endDate=end_date
        )
    else:
        api_result = stock_api.get_stock_price(stock_symbol, period=period)

    return jsonify(api_result)


@app.route(ROUTE_API_STOCK_METRICS)
def get_metrics():
    """Get stock metrics endpoint"""
    stock_symbol, error_response = _validate_symbol_param()
    if error_response:
        return error_response

    api_result = stock_api.get_stock_metrics(stock_symbol)
    return jsonify(api_result)


@app.route(ROUTE_API_STOCK_ESTIMATES)
def get_estimates():
    """Get analyst estimates endpoint"""
    stock_symbol, error_response = _validate_symbol_param()
    if error_response:
        return error_response

    api_result = stock_api.get_analyst_estimates(stock_symbol)
    return jsonify(api_result)


@app.route(ROUTE_API_STOCK_FINANCIALS)
def get_financials():
    """Get financial statements endpoint"""
    stock_symbol, error_response = _validate_symbol_param()
    if error_response:
        return error_response

    api_result = stock_api.get_financial_statements(stock_symbol)
    return jsonify(api_result)


@app.route(ROUTE_API_STOCK_NEWS)
def get_news():
    """Get stock news endpoint"""
    stock_symbol, error_response = _validate_symbol_param()
    if error_response:
        return error_response

    api_result = stock_api.get_stock_news(stock_symbol)
    return jsonify(api_result)


@app.route(ROUTE_API_STOCK_FACTORS)
def get_factors():
    """Get stock factors endpoint"""
    stock_symbol, error_response = _validate_symbol_param()
    if error_response:
        return error_response

    api_result = stock_api.get_stock_factors(stock_symbol)
    return jsonify(api_result)


@app.route("/api/stocks/search")
def search_stocks():
    query = request.args.get("q", "")
    limit = request.args.get("limit", 20)

    if not query:
        return jsonify({"error": 'Query parameter "q" is required'}), 400

    try:
        limit = int(limit)
    except ValueError:
        limit = 20

    # Try to use DynamoDB-based stock universe manager
    try:
        from stock_universe_api import StockUniverseManager

        manager = StockUniverseManager()
        result = manager.search_stocks(query, limit)
        if result:
            return jsonify(result)
    except Exception as err:
        print(f"DynamoDB not available, using local fallback: {err}")

    # Fallback to local search in popular stocks list
    query_upper = query.upper()
    results = []

    for stock in LOCAL_POPULAR_STOCKS:
        # Check if query matches symbol or name
        if query_upper in stock["symbol"] or query_upper in stock["name"].upper():
            results.append(stock)

    # Sort by relevance (exact symbol match first)
    results.sort(
        key=lambda stock: (
            0 if stock["symbol"] == query_upper else 1,
            1 if stock["symbol"].startswith(query_upper) else 2,
            stock["symbol"],
        )
    )

    return jsonify(results[:limit])


@app.route("/api/stocks/popular")
def get_popular_stocks():
    limit = request.args.get("limit", 10)
    try:
        limit = int(limit)
    except ValueError:
        limit = 10

    # Try to use DynamoDB-based stock universe manager
    try:
        from stock_universe_api import StockUniverseManager

        manager = StockUniverseManager()
        result = manager.get_popular_stocks(limit)
        if result:
            return jsonify(result)
    except Exception as err:
        print(f"DynamoDB not available, using local fallback: {err}")

    # Fallback to local popular stocks list
    sorted_stocks = sorted(
        LOCAL_POPULAR_STOCKS, key=lambda stock: stock.get("marketCap", 0), reverse=True
    )
    return jsonify(sorted_stocks[:limit])


# Batch endpoints
@app.route("/api/stock/batch/prices")
def get_batch_prices():
    symbols = request.args.get("symbols", "").split(",")
    if not symbols or not symbols[0]:
        return jsonify({"error": "Symbols required"}), 400
    result = stock_api.get_batch_prices(
        [symbol.upper() for symbol in symbols if symbol]
    )
    return jsonify(result)


@app.route("/api/stock/batch/metrics")
def get_batch_metrics():
    symbols = request.args.get("symbols", "").split(",")
    if not symbols or not symbols[0]:
        return jsonify({"error": "Symbols required"}), 400
    result = stock_api.get_batch_metrics(
        [symbol.upper() for symbol in symbols if symbol]
    )
    return jsonify(result)


@app.route("/api/stock/batch/estimates")
def get_batch_estimates():
    symbols = request.args.get("symbols", "").split(",")
    if not symbols or not symbols[0]:
        return jsonify({"error": "Symbols required"}), 400
    result = stock_api.get_batch_estimates(
        [symbol.upper() for symbol in symbols if symbol]
    )
    return jsonify(result)


@app.route("/api/stock/batch/financials")
def get_batch_financials():
    symbols = request.args.get("symbols", "").split(",")
    if not symbols or not symbols[0]:
        return jsonify({"error": "Symbols required"}), 400
    result = stock_api.get_batch_financials(
        [symbol.upper() for symbol in symbols if symbol]
    )
    return jsonify(result)


@app.route("/api/dcf", methods=["POST"])
def run_dcf_analysis():
    """Run Discounted Cash Flow (DCF) analysis"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Assumptions required for DCF analysis"}), 400

    result = stock_api.run_dcf(data)
    return jsonify(result)


# ============================================
# Watchlist Endpoints (Local storage fallback)
# ============================================
WATCHLIST = []


@app.route("/api/watchlist", methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"])
@auth_required
def manage_watchlist():
    """Manage user watchlist items"""
    manager = WatchlistManager()
    user_id = g.user_id  # Get user_id from the authenticated context

    if request.method == "OPTIONS":
        return "", 200

    if request.method == "GET":
        return jsonify(manager.get_watchlist(user_id))

    elif request.method == "POST":
        data = request.get_json()
        if not data or "symbol" not in data:
            return jsonify({"error": "Symbol required"}), 400

        result = manager.add_to_watchlist(user_id, data)
        if result.get("success"):
            return jsonify(result.get("item"))  # Return the added item
        return jsonify({"error": result.get("error")}), 500

    elif request.method == "PUT":
        data = request.get_json()
        if not data or "symbol" not in data:
            return jsonify({"error": "Symbol required"}), 400

        symbol = data["symbol"].upper()
        updates = data.get("updates", {})
        result = manager.update_watchlist_item(user_id, symbol, updates)
        if result.get("success"):
            return jsonify(result.get("item"))  # Return the updated item
        return jsonify({"error": result.get("error")}), 500

    elif request.method == "DELETE":
        symbol = request.args.get("symbol")
        if not symbol:
            return jsonify({"error": "Symbol required"}), 400

        result = manager.remove_from_watchlist(user_id, symbol.upper())
        if result.get("success"):
            return jsonify({"status": "success", "message": "Item deleted"})
        return jsonify({"error": result.get("error")}), 500


# ============================================
# Screener & Custom Factors Endpoints
# ============================================


@app.route("/api/screener/screen", methods=["POST", "OPTIONS"])
@auth_required
def screen_stocks():
    """Screen stocks based on custom criteria"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        from screener_api import StockScreener

        screener = StockScreener()

        data = request.get_json()
        criteria = data.get("criteria", {})

        result = screener.screen_stocks(criteria)
        return jsonify(result)
    except Exception as err:
        print(f"Error screening stocks: {str(err)}")
        return jsonify({"error": str(err), "results": []}), 500


@app.route("/api/factors", methods=["GET", "POST", "OPTIONS"])
@auth_required
def custom_factors():
    """Get or save custom screening factors"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        from screener_api import StockScreener

        screener = StockScreener()

        # Use g.user_id from authenticated request
        user_id = g.user_id

        if request.method == "POST":
            # Save custom factor
            data = request.get_json()
            result = screener.save_factor(user_id, data)
            return jsonify(result)

        else:  # GET
            # Get user's custom factors
            result = screener.get_user_factors(user_id)
            return jsonify(result)

    except Exception as err:
        print(f"Error with custom factors: {str(err)}")
        return jsonify({"error": str(err)}), 500


@app.route("/api/factors/<factor_id>", methods=["DELETE", "OPTIONS"])
@auth_required
def delete_custom_factor(factor_id):
    """Delete a custom factor"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        from screener_api import StockScreener

        screener = StockScreener()

        # Use g.user_id from authenticated request
        user_id = g.user_id

        result = screener.delete_factor(user_id, factor_id)
        return jsonify(result)

    except Exception as err:
        print(f"Error deleting factor: {str(err)}")
        return jsonify({"error": str(err)}), 500


# ============================================
# Auth Endpoints (Local Development Mock)
# ============================================
@app.route("/api/auth/signin", methods=["POST"])
def mock_signin():
    """Mocks user sign-in with hCaptcha verification for local development."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    hcaptcha_token = data.get("hcaptchaToken")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Mock hCaptcha verification
    if not hcaptcha_token:
        print("Mock Sign-in: hCaptcha token missing.")
        return (
            jsonify({"error": "hCaptcha token missing. Security check required."}),
            400,
        )

    # In a real scenario, you would send this token to hCaptcha verification API
    # response = requests.post("https://hcaptcha.com/siteverify", data={
    #     'response': hcaptcha_token,
    #     'secret': 'YOUR_HCAPTCHA_SECRET_KEY'
    # })
    # if not response.json().get('success'):
    #     return jsonify({'error': 'hCaptcha verification failed'}), 400

    print(
        f"Mock Sign-in: Successfully verified hCaptcha for {email}. Token: {hcaptcha_token[:10]}..."
    )

    # Mock user authentication (simple check for local dev)
    # For a real app, integrate with Cognito or a proper user management system
    if email == "test@example.com" and password == "password":
        # Simulate a successful login by returning a dummy JWT
        # In a real app, this would be a real JWT from Cognito
        dummy_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJsb2NhbC1kZXYtdXNlciIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImlhdCI6MTUxNjIzOTAyMn0.dummyjwttoken"
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Mock sign-in successful",
                    "user": {"email": email, "userId": "local-dev-user"},
                    "idToken": dummy_jwt,
                    "accessToken": dummy_jwt,  # In a real app, these would be different
                }
            ),
            200,
        )
    else:
        return jsonify({"error": "Invalid email or password"}), 401


if __name__ == "__main__":
    print("Starting local Flask server at http://localhost:5000")
    print("API endpoints available:")
    print("  - GET /api/stock/price?symbol=AAPL")
    print("  - GET /api/stock/metrics?symbol=AAPL")
    print("  - GET /api/stock/estimates?symbol=AAPL")
    print("  - GET /api/stock/financials?symbol=AAPL")
    print("  - GET /api/stock/news?symbol=AAPL")
    print("  - GET /api/stocks/search?q=apple")
    print("  - GET /api/stocks/popular?limit=10")
    print("  - POST /api/dcf")
    print()
    app.run(host="0.0.0.0", port=5000, debug=True)

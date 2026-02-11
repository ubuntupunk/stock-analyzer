"""
Local Development Flask Server for Stock Analyzer
Serves the frontend and provides API endpoints
"""

import os
import sys
from flask import Flask, jsonify, request, send_from_directory, render_template, g, abort
from functools import wraps

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stock_api import StockDataAPI
from watchlist_api import WatchlistManager
from screener_api import StockScreener
import math
import json

from flask.json.provider import DefaultJSONProvider

# Custom JSON provider to handle NaN and Infinity values
class SafeJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        # Handle NaN/Inf at the object level before dumping
        def sanitize(o):
            if isinstance(o, float):
                if math.isnan(o) or math.isinf(o):
                    return None
            elif isinstance(o, dict):
                return {k: sanitize(v) for k, v in o.items()}
            elif isinstance(o, list):
                return [sanitize(v) for v in o]
            return o
        
        return super().dumps(sanitize(sanitize(obj)), **kwargs)

app = Flask(__name__, template_folder='../frontend')
app.json = SafeJSONProvider(app)

# --- Authentication Logic for Local Development ---
LOCAL_DEV_TOKEN = "local-dev-token" # This token will be sent by the frontend for authenticated requests

@app.before_request
def before_request():
    g.user_id = None # Initialize user_id for each request
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        if token == LOCAL_DEV_TOKEN:
            g.user_id = 'local-dev-user' # Assign a mock user ID for authenticated requests
        else:
            print(f"Warning: Invalid local dev token received: {token}")

def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user_id:
            abort(401, description="Authentication required for this resource.")
        return f(*args, **kwargs)
    return decorated_function

# Initialize the Stock Data API
stock_api = StockDataAPI()

# Popular stocks fallback for local development (when DynamoDB is unavailable)
LOCAL_POPULAR_STOCKS = [
    {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology', 'marketCap': 2890000000000, 'price': 185.92},
    {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'sector': 'Technology', 'marketCap': 2780000000000, 'price': 398.67},
    {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'Technology', 'marketCap': 1750000000000, 'price': 142.65},
    {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'sector': 'Consumer Cyclical', 'marketCap': 1580000000000, 'price': 171.81},
    {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'sector': 'Technology', 'marketCap': 1200000000000, 'price': 726.13},
    {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'sector': 'Technology', 'marketCap': 980000000000, 'price': 473.32},
    {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Consumer Cyclical', 'marketCap': 780000000000, 'price': 188.85},
    {'symbol': 'BRK.B', 'name': 'Berkshire Hathaway Inc.', 'sector': 'Financial', 'marketCap': 780000000000, 'price': 400.12},
    {'symbol': 'LLY', 'name': 'Eli Lilly and Company', 'sector': 'Healthcare', 'marketCap': 560000000000, 'price': 740.21},
    {'symbol': 'V', 'name': 'Visa Inc.', 'sector': 'Financial', 'marketCap': 520000000000, 'price': 275.14},
    {'symbol': 'TSM', 'name': 'Taiwan Semiconductor', 'sector': 'Technology', 'marketCap': 510000000000, 'price': 129.53},
    {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.', 'sector': 'Financial', 'marketCap': 490000000000, 'price': 172.11},
    {'symbol': 'WMT', 'name': 'Walmart Inc.', 'sector': 'Consumer Defensive', 'marketCap': 420000000000, 'price': 170.36},
    {'symbol': 'XOM', 'name': 'Exxon Mobil Corporation', 'sector': 'Energy', 'marketCap': 410000000000, 'price': 102.45},
    {'symbol': 'MA', 'name': 'Mastercard Inc.', 'sector': 'Financial', 'marketCap': 400000000000, 'price': 455.67},
]

# Serve static files from frontend directory
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
print(f"Serving frontend from: {frontend_path}")

@app.route('/')
def index():
    return send_from_directory(frontend_path, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(frontend_path, filename)

# Stock Data API Endpoints
@app.route('/api/stock/price')
def get_price():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    result = stock_api.get_stock_price(symbol.upper())
    return jsonify(result)

@app.route('/api/stock/price/history')
def get_price_history():
    symbol = request.args.get('symbol')
    period = request.args.get('period', '1mo')
    startDate = request.args.get('startDate')
    endDate = request.args.get('endDate')
    
    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    
    if startDate and endDate:
        result = stock_api.get_stock_price(symbol.upper(), startDate=startDate, endDate=endDate)
    else:
        result = stock_api.get_stock_price(symbol.upper(), period=period)
    
    return jsonify(result)

@app.route('/api/stock/metrics')
def get_metrics():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    result = stock_api.get_stock_metrics(symbol.upper())
    return jsonify(result)

@app.route('/api/stock/estimates')
def get_estimates():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    result = stock_api.get_analyst_estimates(symbol.upper())
    return jsonify(result)

@app.route('/api/stock/financials')
def get_financials():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    result = stock_api.get_financial_statements(symbol.upper())
    return jsonify(result)

@app.route('/api/stock/news')
def get_news():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    result = stock_api.get_stock_news(symbol.upper())
    return jsonify(result)

@app.route('/api/stock/factors')
def get_factors():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    result = stock_api.get_stock_factors(symbol.upper())
    return jsonify(result)

@app.route('/api/stocks/search')
def search_stocks():
    query = request.args.get('q', '')
    limit = request.args.get('limit', 20)
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
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
    except Exception as e:
        print(f"DynamoDB not available, using local fallback: {e}")
    
    # Fallback to local search in popular stocks list
    query_upper = query.upper()
    results = []
    
    for stock in LOCAL_POPULAR_STOCKS:
        # Check if query matches symbol or name
        if (query_upper in stock['symbol'] or 
            query_upper in stock['name'].upper()):
            results.append(stock)
    
    # Sort by relevance (exact symbol match first)
    results.sort(key=lambda x: (
        0 if x['symbol'] == query_upper else 1,
        1 if x['symbol'].startswith(query_upper) else 2,
        x['symbol']
    ))
    
    return jsonify(results[:limit])

@app.route('/api/stocks/popular')
def get_popular_stocks():
    limit = request.args.get('limit', 10)
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
    except Exception as e:
        print(f"DynamoDB not available, using local fallback: {e}")
    
    # Fallback to local popular stocks list
    sorted_stocks = sorted(LOCAL_POPULAR_STOCKS, key=lambda x: x.get('marketCap', 0), reverse=True)
    return jsonify(sorted_stocks[:limit])

# Batch endpoints
@app.route('/api/stock/batch/prices')
def get_batch_prices():
    symbols = request.args.get('symbols', '').split(',')
    if not symbols or not symbols[0]:
        return jsonify({'error': 'Symbols required'}), 400
    result = stock_api.get_batch_prices([s.upper() for s in symbols if s])
    return jsonify(result)

@app.route('/api/stock/batch/metrics')
def get_batch_metrics():
    symbols = request.args.get('symbols', '').split(',')
    if not symbols or not symbols[0]:
        return jsonify({'error': 'Symbols required'}), 400
    result = stock_api.get_batch_metrics([s.upper() for s in symbols if s])
    return jsonify(result)

@app.route('/api/stock/batch/estimates')
def get_batch_estimates():
    symbols = request.args.get('symbols', '').split(',')
    if not symbols or not symbols[0]:
        return jsonify({'error': 'Symbols required'}), 400
    result = stock_api.get_batch_estimates([s.upper() for s in symbols if s])
    return jsonify(result)

@app.route('/api/stock/batch/financials')
def get_batch_financials():
    symbols = request.args.get('symbols', '').split(',')
    if not symbols or not symbols[0]:
        return jsonify({'error': 'Symbols required'}), 400
    result = stock_api.get_batch_financials([s.upper() for s in symbols if s])
    return jsonify(result)

@app.route('/api/dcf', methods=['POST'])
def run_dcf_analysis():
    """Run Discounted Cash Flow (DCF) analysis"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Assumptions required for DCF analysis'}), 400
    
    result = stock_api.run_dcf(data)
    return jsonify(result)

# ============================================
# Watchlist Endpoints (Local storage fallback)
# ============================================
WATCHLIST = []

@app.route('/api/watchlist', methods=['GET', 'POST', 'DELETE', 'PUT', 'OPTIONS'])
@auth_required
def manage_watchlist():
    """Manage user watchlist items"""
    manager = WatchlistManager()
    user_id = g.user_id # Get user_id from the authenticated context
    
    if request.method == 'OPTIONS':
        return '', 200
        
    if request.method == 'GET':
        return jsonify(manager.get_watchlist(user_id))
        
    elif request.method == 'POST':
        data = request.get_json()
        if not data or 'symbol' not in data:
            return jsonify({'error': 'Symbol required'}), 400
            
        result = manager.add_to_watchlist(user_id, data)
        if result.get('success'):
            return jsonify(result.get('item')) # Return the added item
        return jsonify({'error': result.get('error')}), 500
        
    elif request.method == 'PUT':
        data = request.get_json()
        if not data or 'symbol' not in data:
            return jsonify({'error': 'Symbol required'}), 400
            
        symbol = data['symbol'].upper()
        updates = data.get('updates', {})
        result = manager.update_watchlist_item(user_id, symbol, updates)
        if result.get('success'):
            return jsonify(result.get('item')) # Return the updated item
        return jsonify({'error': result.get('error')}), 500
        
    elif request.method == 'DELETE':
        symbol = request.args.get('symbol')
        if not symbol:
            return jsonify({'error': 'Symbol required'}), 400
            
        result = manager.remove_from_watchlist(user_id, symbol.upper())
        if result.get('success'):
            return jsonify({'status': 'success', 'message': 'Item deleted'})
        return jsonify({'error': result.get('error')}), 500

# ============================================
# Screener & Custom Factors Endpoints
# ============================================

@app.route('/api/screener/screen', methods=['POST', 'OPTIONS'])
@auth_required
def screen_stocks():
    """Screen stocks based on custom criteria"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        from screener_api import StockScreener
        screener = StockScreener()
        
        data = request.get_json()
        criteria = data.get('criteria', {})
        
        result = screener.screen_stocks(criteria)
        return jsonify(result)
    except Exception as e:
        print(f"Error screening stocks: {str(e)}")
        return jsonify({'error': str(e), 'results': []}), 500

@app.route('/api/factors', methods=['GET', 'POST', 'OPTIONS'])
@auth_required
def custom_factors():
    """Get or save custom screening factors"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        from screener_api import StockScreener
        screener = StockScreener()
        
        # Use g.user_id from authenticated request
        user_id = g.user_id
        
        if request.method == 'POST':
            # Save custom factor
            data = request.get_json()
            result = screener.save_factor(user_id, data)
            return jsonify(result)
        
        else:  # GET
            # Get user's custom factors
            result = screener.get_user_factors(user_id)
            return jsonify(result)
    
    except Exception as e:
        print(f"Error with custom factors: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/factors/<factor_id>', methods=['DELETE', 'OPTIONS'])
@auth_required
def delete_custom_factor(factor_id):
    """Delete a custom factor"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        from screener_api import StockScreener
        screener = StockScreener()
        
        # Use g.user_id from authenticated request
        user_id = g.user_id
        
        result = screener.delete_factor(user_id, factor_id)
        return jsonify(result)
    
    except Exception as e:
        print(f"Error deleting factor: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================
# Auth Endpoints (Local Development Mock)
# ============================================
@app.route('/api/auth/signin', methods=['POST'])
def mock_signin():
    """Mocks user sign-in with hCaptcha verification for local development."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    hcaptcha_token = data.get('hcaptchaToken')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    # Mock hCaptcha verification
    if not hcaptcha_token:
        print("Mock Sign-in: hCaptcha token missing.")
        return jsonify({'error': 'hCaptcha token missing. Security check required.'}), 400
    
    # In a real scenario, you would send this token to hCaptcha verification API
    # response = requests.post("https://hcaptcha.com/siteverify", data={
    #     'response': hcaptcha_token,
    #     'secret': 'YOUR_HCAPTCHA_SECRET_KEY'
    # })
    # if not response.json().get('success'):
    #     return jsonify({'error': 'hCaptcha verification failed'}), 400

    print(f"Mock Sign-in: Successfully verified hCaptcha for {email}. Token: {hcaptcha_token[:10]}...")
    
    # Mock user authentication (simple check for local dev)
    # For a real app, integrate with Cognito or a proper user management system
    if email == 'test@example.com' and password == 'password':
        # Simulate a successful login by returning a dummy JWT
        # In a real app, this would be a real JWT from Cognito
        dummy_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJsb2NhbC1kZXYtdXNlciIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImlhdCI6MTUxNjIzOTAyMn0.dummyjwttoken"
        return jsonify({
            'success': True,
            'message': 'Mock sign-in successful',
            'user': {
                'email': email,
                'userId': 'local-dev-user'
            },
            'idToken': dummy_jwt,
            'accessToken': dummy_jwt # In a real app, these would be different
        }), 200
    else:
        return jsonify({'error': 'Invalid email or password'}), 401

if __name__ == '__main__':
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
    app.run(host='0.0.0.0', port=5000, debug=True)

"""
AWS Lambda Handler for Stock Data API
Handles HTTP routing and CORS for all stock data endpoints
"""

import json
from stock_api import StockDataAPI, decimal_default


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
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': ''
        }
    
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    query_params = event.get('queryStringParameters') or {}
    
    # Initialize API
    api = StockDataAPI()
    
    try:
        # Check if this is a batch request
        if '/batch/' in path:
            # Batch endpoints - require 'symbols' parameter (comma-separated)
            symbols_param = query_params.get('symbols', '')
            if not symbols_param:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'error': 'Symbols parameter is required (comma-separated list)'})
                }
            
            # Parse comma-separated symbols
            symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
            
            if not symbols:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'error': 'At least one symbol is required'})
                }
            
            # Limit batch size to prevent abuse
            if len(symbols) > 50:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'error': 'Maximum 50 symbols per batch request'})
                }
            
            # Route to appropriate batch handler
            if '/batch/prices' in path or '/batch/price' in path:
                result = api.get_multiple_stock_prices(symbols)
            elif '/batch/metrics' in path:
                result = api.get_multiple_stock_metrics(symbols)
            elif '/batch/estimates' in path:
                result = api.get_multiple_analyst_estimates(symbols)
            elif '/batch/financials' in path:
                result = api.get_multiple_financial_statements(symbols)
            else:
                result = {'error': 'Invalid batch endpoint'}
        
        else:
            # Single stock endpoints - require 'symbol' parameter
            symbol = query_params.get('symbol', '').upper()
            
            if not symbol:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'error': 'Symbol parameter is required'})
                }
            
            # Route to appropriate single stock handler
            if '/metrics' in path:
                result = api.get_stock_metrics(symbol)
            elif '/price' in path:
                result = api.get_stock_price(symbol)
            elif '/estimates' in path:
                result = api.get_analyst_estimates(symbol)
            elif '/financials' in path:
                result = api.get_financial_statements(symbol)
            elif '/factors' in path:
                result = api.get_stock_factors(symbol)
            elif '/news' in path:
                result = api.get_stock_news(symbol)
            else:
                result = {'error': 'Invalid endpoint'}
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(result, default=decimal_default)
        }
    
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

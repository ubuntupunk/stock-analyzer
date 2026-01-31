import json
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
import os

def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

class StockUniverseManager:
    """Manage stock universe database queries"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(os.environ.get('STOCK_UNIVERSE_TABLE', 'stock-universe'))
    
    def search_stocks(self, query: str, limit: int = 20) -> list:
        """
        Search stocks by symbol or company name
        Uses scan with filter (for simplicity - could be optimized with search index)
        """
        try:
            query_upper = query.upper()
            
            # Scan with filter for symbol or name containing query
            response = self.table.scan(
                FilterExpression=Attr('symbol').contains(query_upper) | 
                                Attr('name').contains(query_upper),
                Limit=limit
            )
            
            items = response.get('Items', [])
            
            # Sort by relevance (exact symbol match first, then alphabetically)
            items.sort(key=lambda x: (
                0 if x['symbol'] == query_upper else 1,
                1 if x['symbol'].startswith(query_upper) else 2,
                x['symbol']
            ))
            
            return items[:limit]
        except Exception as e:
            print(f"Error searching stocks: {str(e)}")
            return []
    
    def get_popular_stocks(self, limit: int = 10) -> list:
        """
        Get most popular/traded stocks
        Returns stocks sorted by market cap (largest first)
        """
        try:
            # Scan and sort by market cap
            response = self.table.scan()
            items = response.get('Items', [])
            
            # Sort by market cap descending
            items.sort(key=lambda x: float(x.get('marketCap', 0)), reverse=True)
            
            return items[:limit]
        except Exception as e:
            print(f"Error getting popular stocks: {str(e)}")
            return []
    
    def get_sectors(self) -> dict:
        """
        Get all sectors with stock counts
        Returns: {sector: count, ...}
        """
        try:
            response = self.table.scan(
                ProjectionExpression='sector'
            )
            
            items = response.get('Items', [])
            
            # Count stocks per sector
            sector_counts = {}
            for item in items:
                sector = item.get('sector', 'Unknown')
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
            
            # Sort by count descending
            sorted_sectors = [
                {'sector': sector, 'count': count}
                for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)
            ]
            
            return sorted_sectors
        except Exception as e:
            print(f"Error getting sectors: {str(e)}")
            return []
    
    def filter_stocks(self, sector: str = None, min_cap: float = None, 
                     max_cap: float = None, market_cap_bucket: str = None) -> list:
        """
        Filter stocks by sector and/or market cap
        market_cap_bucket: 'mega' (>200B), 'large' (10-200B), 'mid' (2-10B), 'small' (<2B)
        """
        try:
            filter_expressions = []
            expression_values = {}
            
            # Filter by sector using GSI
            if sector:
                response = self.table.query(
                    IndexName='sector-index',
                    KeyConditionExpression=Key('sector').eq(sector)
                )
                items = response.get('Items', [])
            else:
                response = self.table.scan()
                items = response.get('Items', [])
            
            # Apply market cap filters
            if min_cap is not None or max_cap is not None or market_cap_bucket:
                filtered_items = []
                for item in items:
                    market_cap = float(item.get('marketCap', 0))
                    
                    # Check market cap bucket
                    if market_cap_bucket:
                        item_bucket = item.get('marketCapBucket', '')
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
        except Exception as e:
            print(f"Error filtering stocks: {str(e)}")
            return []
    
    def get_stock_by_symbol(self, symbol: str) -> dict:
        """Get a single stock by symbol"""
        try:
            response = self.table.get_item(Key={'symbol': symbol.upper()})
            return response.get('Item', {})
        except Exception as e:
            print(f"Error getting stock {symbol}: {str(e)}")
            return {}

def lambda_handler(event, context):
    """Handler for stock universe API endpoints"""
    
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': ''
        }
    
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    query_params = event.get('queryStringParameters') or {}
    
    manager = StockUniverseManager()
    
    try:
        if method != 'GET':
            return {
                'statusCode': 405,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Method not allowed'})
            }
        
        # Route to appropriate handler
        if '/search' in path:
            query = query_params.get('q', '')
            limit = int(query_params.get('limit', 20))
            
            if not query:
                result = {'error': 'Query parameter "q" is required'}
            else:
                result = manager.search_stocks(query, limit)
        
        elif '/popular' in path:
            limit = int(query_params.get('limit', 10))
            result = manager.get_popular_stocks(limit)
        
        elif '/sectors' in path:
            result = manager.get_sectors()
        
        elif '/filter' in path:
            sector = query_params.get('sector')
            min_cap = float(query_params['minCap']) if 'minCap' in query_params else None
            max_cap = float(query_params['maxCap']) if 'maxCap' in query_params else None
            market_cap_bucket = query_params.get('marketCapBucket')
            
            result = manager.filter_stocks(sector, min_cap, max_cap, market_cap_bucket)
        
        elif '/symbol/' in path:
            symbol = path.split('/symbol/')[-1]
            result = manager.get_stock_by_symbol(symbol)
        
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

import json
import boto3
import yfinance as yf
from datetime import datetime
from decimal import Decimal
import os
import time

class StockUniverseSeeder:
    """Seed and update stock universe with S&P 500 data"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(os.environ.get('STOCK_UNIVERSE_TABLE', 'stock-universe'))
    
    def get_sp500_list(self) -> list:
        """
        Fetch S&P 500 list from Wikipedia
        Returns list of dicts with symbol and company name
        """
        try:
            # Use Wikipedia's S&P 500 table
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            
            import pandas as pd
            tables = pd.read_html(url)
            sp500_table = tables[0]
            
            stocks = []
            for _, row in sp500_table.iterrows():
                symbol = str(row['Symbol']).replace('.', '-')
                stocks.append({
                    'symbol': symbol,
                    'name': str(row['Security']),
                    'sector': str(row['GICS Sector']),
                    'subSector': str(row['GICS Sub-Industry']),
                    'headquarters': str(row['Headquarters Location']),
                })
            
            return stocks
        except Exception as e:
            print(f"Error fetching S&P 500 list: {str(e)}")
            return self.get_fallback_stock_list()
    
    def get_fallback_stock_list(self) -> list:
        """
        Fallback list of popular stocks if Wikipedia fetch fails
        """
        return [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Information Technology'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'sector': 'Information Technology'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'Communication Services'},
            {'symbol': 'GOOG', 'name': 'Alphabet Inc.', 'sector': 'Communication Services'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'sector': 'Information Technology'},
            {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'sector': 'Communication Services'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'TSM', 'name': 'Taiwan Semiconductor', 'sector': 'Information Technology'},
            {'symbol': 'AVGO', 'name': 'Broadcom Inc.', 'sector': 'Information Technology'},
            {'symbol': 'BRK-B', 'name': 'Berkshire Hathaway Inc.', 'sector': 'Financials'},
            {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.', 'sector': 'Financials'},
            {'symbol': 'V', 'name': 'Visa Inc.', 'sector': 'Financials'},
            {'symbol': 'MA', 'name': 'Mastercard Inc.', 'sector': 'Financials'},
            {'symbol': 'BAC', 'name': 'Bank of America Corporation', 'sector': 'Financials'},
            {'symbol': 'WFC', 'name': 'Wells Fargo & Company', 'sector': 'Financials'},
            {'symbol': 'UNH', 'name': 'UnitedHealth Group Inc.', 'sector': 'Health Care'},
            {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Health Care'},
            {'symbol': 'LLY', 'name': 'Eli Lilly and Company', 'sector': 'Health Care'},
            {'symbol': 'PFE', 'name': 'Pfizer Inc.', 'sector': 'Health Care'},
            {'symbol': 'ABBV', 'name': 'AbbVie Inc.', 'sector': 'Health Care'},
            {'symbol': 'MRK', 'name': 'Merck & Co. Inc.', 'sector': 'Health Care'},
            {'symbol': 'WMT', 'name': 'Walmart Inc.', 'sector': 'Consumer Staples'},
            {'symbol': 'HD', 'name': 'The Home Depot Inc.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'PG', 'name': 'The Procter & Gamble Company', 'sector': 'Consumer Staples'},
            {'symbol': 'COST', 'name': 'Costco Wholesale Corporation', 'sector': 'Consumer Staples'},
            {'symbol': 'KO', 'name': 'The Coca-Cola Company', 'sector': 'Consumer Staples'},
            {'symbol': 'XOM', 'name': 'Exxon Mobil Corporation', 'sector': 'Energy'},
            {'symbol': 'CVX', 'name': 'Chevron Corporation', 'sector': 'Energy'},
            {'symbol': 'BA', 'name': 'The Boeing Company', 'sector': 'Industrials'},
            {'symbol': 'CAT', 'name': 'Caterpillar Inc.', 'sector': 'Industrials'},
            {'symbol': 'GE', 'name': 'General Electric Company', 'sector': 'Industrials'},
            {'symbol': 'UPS', 'name': 'United Parcel Service', 'sector': 'Industrials'},
            {'symbol': 'T', 'name': 'AT&T Inc.', 'sector': 'Communication Services'},
            {'symbol': 'VZ', 'name': 'Verizon Communications Inc.', 'sector': 'Communication Services'},
            {'symbol': 'CMCSA', 'name': 'Comcast Corporation', 'sector': 'Communication Services'},
            {'symbol': 'NFLX', 'name': 'Netflix Inc.', 'sector': 'Communication Services'},
            {'symbol': 'ORCL', 'name': 'Oracle Corporation', 'sector': 'Information Technology'},
            {'symbol': 'CSCO', 'name': 'Cisco Systems Inc.', 'sector': 'Information Technology'},
            {'symbol': 'ADBE', 'name': 'Adobe Inc.', 'sector': 'Information Technology'},
            {'symbol': 'CRM', 'name': 'Salesforce Inc.', 'sector': 'Information Technology'},
            {'symbol': 'INTC', 'name': 'Intel Corporation', 'sector': 'Information Technology'},
            {'symbol': 'AMD', 'name': 'Advanced Micro Devices', 'sector': 'Information Technology'},
            {'symbol': 'QCOM', 'name': 'QUALCOMM Incorporated', 'sector': 'Information Technology'},
            {'symbol': 'IBM', 'name': 'International Business Machines', 'sector': 'Information Technology'},
        ]
    
    def get_market_cap_bucket(self, market_cap: float) -> str:
        """
        Categorize stocks by market cap
        Mega: >200B, Large: 10-200B, Mid: 2-10B, Small: <2B
        """
        if market_cap >= 200_000_000_000:
            return 'mega'
        elif market_cap >= 10_000_000_000:
            return 'large'
        elif market_cap >= 2_000_000_000:
            return 'mid'
        else:
            return 'small'
    
    def enrich_stock_data_yfinance(self, symbols: list) -> dict:
        """
        Fetch market data for multiple symbols using yfinance
        Returns dict mapping symbol -> market data
        """
        print(f"Fetching market data for {len(symbols)} symbols using yfinance...")
        
        try:
            # Download tickers - yfinance handles rate limiting internally
            tickers = yf.Tickers(' '.join(symbols))
            
            market_data = {}
            for symbol in symbols:
                try:
                    ticker = tickers.tickers.get(symbol)
                    if ticker:
                        info = ticker.info
                        market_data[symbol] = {
                            'marketCap': info.get('marketCap', 0),
                            'exchange': info.get('exchange', 'Unknown'),
                            'currency': info.get('currency', 'USD'),
                            'country': info.get('country', 'USA'),
                            'industry': info.get('industry', 'Unknown'),
                        }
                except Exception as e:
                    print(f"  Error fetching {symbol}: {str(e)}")
                    market_data[symbol] = {}
            
            print(f"Successfully fetched data for {len(market_data)} symbols")
            return market_data
        except Exception as e:
            print(f"Error fetching yfinance data: {str(e)}")
            return {}
    
    def seed_database(self, enrich: bool = True, batch_size: int = 25):
        """
        Seed the database with stock universe data
        enrich: If True, fetch market data from yfinance
        """
        print("Fetching S&P 500 list...")
        stocks = self.get_sp500_list()
        print(f"Found {len(stocks)} stocks to seed")
        
        # Get symbols for enrichment
        symbols = [s['symbol'] for s in stocks]
        
        # Fetch market data from yfinance (all symbols at once)
        market_data = {}
        if enrich:
            market_data = self.enrich_stock_data_yfinance(symbols)
        
        seeded_count = 0
        failed_count = 0
        
        # Process in batches for DynamoDB
        with self.table.batch_writer() as batch:
            for i, stock in enumerate(stocks):
                symbol = stock['symbol']
                try:
                    md = market_data.get(symbol, {})
                    market_cap = md.get('marketCap', 0) or 0
                    
                    item = {
                        'symbol': symbol,
                        'name': stock['name'],
                        'sector': stock.get('sector', 'Unknown'),
                        'subSector': stock.get('subSector', ''),
                        'lastUpdated': datetime.utcnow().isoformat(),
                        'marketCap': Decimal(str(market_cap)) if market_cap else Decimal('0'),
                        'marketCapBucket': self.get_market_cap_bucket(float(market_cap)) if market_cap else 'unknown',
                        'exchange': md.get('exchange', 'Unknown'),
                        'currency': md.get('currency', 'USD'),
                        'country': md.get('country', 'USA'),
                    }
                    
                    # Add industry if available
                    if md.get('industry'):
                        item['industry'] = md['industry']
                    
                    batch.put_item(Item=item)
                    seeded_count += 1
                    
                    if (i + 1) % 50 == 0:
                        print(f"Processed {i + 1}/{len(stocks)} stocks...")
                    
                except Exception as e:
                    print(f"Failed to seed {symbol}: {str(e)}")
                    failed_count += 1
        
        print(f"Seeding complete: {seeded_count} succeeded, {failed_count} failed")
        
        return {
            'seeded': seeded_count,
            'failed': failed_count,
            'total': len(stocks)
        }
    
    def update_market_data(self, symbols: list = None):
        """
        Update only market data for specified symbols or all symbols
        Use this for quick updates without re-fetching company info
        """
        if symbols is None:
            # Fetch all symbols from DynamoDB
            print("Fetching all symbols from DynamoDB...")
            response = self.table.scan(
                ProjectionExpression='symbol'
            )
            symbols = [item['symbol'] for item in response.get('Items', [])]
        
        print(f"Updating market data for {len(symbols)} symbols...")
        
        # Use yfinance to get latest data
        market_data = self.enrich_stock_data_yfinance(symbols)
        
        updated_count = 0
        with self.table.batch_writer() as batch:
            for symbol, md in market_data.items():
                try:
                    market_cap = md.get('marketCap', 0) or 0
                    item = {
                        'symbol': symbol,
                        'lastUpdated': datetime.utcnow().isoformat(),
                        'marketCap': Decimal(str(market_cap)) if market_cap else Decimal('0'),
                        'marketCapBucket': self.get_market_cap_bucket(float(market_cap)) if market_cap else 'unknown',
                    }
                    
                    # Update only these fields
                    batch.put_item(Item=item)
                    updated_count += 1
                except Exception as e:
                    print(f"Failed to update {symbol}: {str(e)}")
        
        print(f"Update complete: {updated_count} symbols updated")
        return {'updated': updated_count}


def lambda_handler(event, context):
    """
    Lambda handler for seeding stock universe
    Can be invoked manually or scheduled via EventBridge
    """
    
    # Check if this is an EventBridge scheduled event
    is_scheduled = event.get('source') == 'aws.events'
    
    # Check operation type
    operation = event.get('operation', 'seed')
    
    # For scheduled updates, always enrich
    # For manual invocations, check event parameters
    enrich = event.get('enrich', is_scheduled)
    
    print(f"Starting stock universe {operation} (enrich={enrich})...")
    
    try:
        seeder = StockUniverseSeeder()
        
        if operation == 'update_market':
            # Quick update of just market data
            symbols = event.get('symbols')
            result = seeder.update_market_data(symbols)
        else:
            # Full seed
            result = seeder.seed_database(enrich=enrich)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Stock universe {operation} completed',
                'result': result
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Failed to {operation} stock universe',
                'message': str(e)
            })
        }


if __name__ == '__main__':
    # For local testing
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--quick-update':
        print("Running quick market data update...")
        seeder = StockUniverseSeeder()
        result = seeder.update_market_data()
        print(json.dumps(result, indent=2))
    else:
        print("Running full seed with yfinance enrichment...")
        seeder = StockUniverseSeeder()
        result = seeder.seed_database(enrich=True)
        print(json.dumps(result, indent=2))

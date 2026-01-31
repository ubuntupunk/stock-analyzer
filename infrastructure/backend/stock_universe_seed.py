import json
import boto3
import requests
from datetime import datetime
from decimal import Decimal
import os

class StockUniverseSeeder:
    """Seed and update stock universe with S&P 500 data"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(os.environ.get('STOCK_UNIVERSE_TABLE', 'stock-universe'))
        self.financial_api_key = os.environ.get('FINANCIAL_API_KEY', 'demo')
    
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
                stocks.append({
                    'symbol': str(row['Symbol']).replace('.', '-'),  # Fix symbols like BRK.B -> BRK-B
                    'name': str(row['Security']),
                    'sector': str(row['GICS Sector']),
                    'subSector': str(row['GICS Sub-Industry']),
                    'headquarters': str(row['Headquarters Location']),
                    'dateAdded': str(row['Date added']) if 'Date added' in row else None,
                    'cik': str(row['CIK']) if 'CIK' in row else None,
                    'founded': str(row['Founded']) if 'Founded' in row else None
                })
            
            return stocks
        except Exception as e:
            print(f"Error fetching S&P 500 list: {str(e)}")
            # Fallback to a smaller curated list
            return self.get_fallback_stock_list()
    
    def get_fallback_stock_list(self) -> list:
        """
        Fallback list of popular stocks if Wikipedia fetch fails
        Top 100 most traded stocks
        """
        return [
            # Technology
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Information Technology'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'sector': 'Information Technology'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc. Class A', 'sector': 'Communication Services'},
            {'symbol': 'GOOG', 'name': 'Alphabet Inc. Class C', 'sector': 'Communication Services'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'sector': 'Information Technology'},
            {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'sector': 'Communication Services'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'TSM', 'name': 'Taiwan Semiconductor Manufacturing', 'sector': 'Information Technology'},
            {'symbol': 'AVGO', 'name': 'Broadcom Inc.', 'sector': 'Information Technology'},
            
            # Finance
            {'symbol': 'BRK-B', 'name': 'Berkshire Hathaway Inc. Class B', 'sector': 'Financials'},
            {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.', 'sector': 'Financials'},
            {'symbol': 'V', 'name': 'Visa Inc.', 'sector': 'Financials'},
            {'symbol': 'MA', 'name': 'Mastercard Incorporated', 'sector': 'Financials'},
            {'symbol': 'BAC', 'name': 'Bank of America Corporation', 'sector': 'Financials'},
            {'symbol': 'WFC', 'name': 'Wells Fargo & Company', 'sector': 'Financials'},
            {'symbol': 'GS', 'name': 'The Goldman Sachs Group', 'sector': 'Financials'},
            {'symbol': 'MS', 'name': 'Morgan Stanley', 'sector': 'Financials'},
            
            # Healthcare
            {'symbol': 'UNH', 'name': 'UnitedHealth Group Incorporated', 'sector': 'Health Care'},
            {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Health Care'},
            {'symbol': 'LLY', 'name': 'Eli Lilly and Company', 'sector': 'Health Care'},
            {'symbol': 'PFE', 'name': 'Pfizer Inc.', 'sector': 'Health Care'},
            {'symbol': 'ABBV', 'name': 'AbbVie Inc.', 'sector': 'Health Care'},
            {'symbol': 'TMO', 'name': 'Thermo Fisher Scientific', 'sector': 'Health Care'},
            {'symbol': 'MRK', 'name': 'Merck & Co. Inc.', 'sector': 'Health Care'},
            
            # Consumer
            {'symbol': 'WMT', 'name': 'Walmart Inc.', 'sector': 'Consumer Staples'},
            {'symbol': 'HD', 'name': 'The Home Depot Inc.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'PG', 'name': 'The Procter & Gamble Company', 'sector': 'Consumer Staples'},
            {'symbol': 'COST', 'name': 'Costco Wholesale Corporation', 'sector': 'Consumer Staples'},
            {'symbol': 'KO', 'name': 'The Coca-Cola Company', 'sector': 'Consumer Staples'},
            {'symbol': 'PEP', 'name': 'PepsiCo Inc.', 'sector': 'Consumer Staples'},
            {'symbol': 'MCD', 'name': "McDonald's Corporation", 'sector': 'Consumer Discretionary'},
            {'symbol': 'NKE', 'name': 'NIKE Inc.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'SBUX', 'name': 'Starbucks Corporation', 'sector': 'Consumer Discretionary'},
            
            # Energy
            {'symbol': 'XOM', 'name': 'Exxon Mobil Corporation', 'sector': 'Energy'},
            {'symbol': 'CVX', 'name': 'Chevron Corporation', 'sector': 'Energy'},
            {'symbol': 'COP', 'name': 'ConocoPhillips', 'sector': 'Energy'},
            
            # Industrials
            {'symbol': 'BA', 'name': 'The Boeing Company', 'sector': 'Industrials'},
            {'symbol': 'CAT', 'name': 'Caterpillar Inc.', 'sector': 'Industrials'},
            {'symbol': 'GE', 'name': 'General Electric Company', 'sector': 'Industrials'},
            {'symbol': 'UPS', 'name': 'United Parcel Service', 'sector': 'Industrials'},
            
            # Telecom & Utilities
            {'symbol': 'T', 'name': 'AT&T Inc.', 'sector': 'Communication Services'},
            {'symbol': 'VZ', 'name': 'Verizon Communications Inc.', 'sector': 'Communication Services'},
            {'symbol': 'CMCSA', 'name': 'Comcast Corporation', 'sector': 'Communication Services'},
            {'symbol': 'DIS', 'name': 'The Walt Disney Company', 'sector': 'Communication Services'},
            {'symbol': 'NFLX', 'name': 'Netflix Inc.', 'sector': 'Communication Services'},
            
            # Technology (more)
            {'symbol': 'ORCL', 'name': 'Oracle Corporation', 'sector': 'Information Technology'},
            {'symbol': 'CSCO', 'name': 'Cisco Systems Inc.', 'sector': 'Information Technology'},
            {'symbol': 'ADBE', 'name': 'Adobe Inc.', 'sector': 'Information Technology'},
            {'symbol': 'CRM', 'name': 'Salesforce Inc.', 'sector': 'Information Technology'},
            {'symbol': 'INTC', 'name': 'Intel Corporation', 'sector': 'Information Technology'},
            {'symbol': 'AMD', 'name': 'Advanced Micro Devices', 'sector': 'Information Technology'},
            {'symbol': 'QCOM', 'name': 'QUALCOMM Incorporated', 'sector': 'Information Technology'},
            {'symbol': 'TXN', 'name': 'Texas Instruments Incorporated', 'sector': 'Information Technology'},
            {'symbol': 'IBM', 'name': 'International Business Machines', 'sector': 'Information Technology'},
        ]
    
    def enrich_stock_data(self, symbol: str) -> dict:
        """
        Fetch additional stock data from Alpha Vantage API
        Returns market cap, exchange, currency
        """
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'OVERVIEW',
                'symbol': symbol,
                'apikey': self.financial_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'Symbol' in data:
                    return {
                        'marketCap': float(data.get('MarketCapitalization', 0)),
                        'exchange': data.get('Exchange', 'Unknown'),
                        'currency': data.get('Currency', 'USD'),
                        'country': data.get('Country', 'USA'),
                        'industry': data.get('Industry', 'Unknown'),
                        'description': data.get('Description', '')[:500],  # Truncate description
                    }
            
            return {}
        except Exception as e:
            print(f"Error enriching data for {symbol}: {str(e)}")
            return {}
    
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
    
    def seed_database(self, enrich: bool = False, batch_size: int = 25):
        """
        Seed the database with stock universe data
        enrich: If True, fetch additional data from Alpha Vantage (slow, respects rate limits)
        """
        print("Fetching S&P 500 list...")
        stocks = self.get_sp500_list()
        print(f"Found {len(stocks)} stocks to seed")
        
        seeded_count = 0
        failed_count = 0
        
        # Process in batches to avoid overwhelming DynamoDB
        with self.table.batch_writer() as batch:
            for i, stock in enumerate(stocks):
                try:
                    item = {
                        'symbol': stock['symbol'],
                        'name': stock['name'],
                        'sector': stock.get('sector', 'Unknown'),
                        'subSector': stock.get('subSector', ''),
                        'lastUpdated': datetime.utcnow().isoformat(),
                        'marketCap': Decimal('0'),
                        'marketCapBucket': 'unknown',
                        'exchange': 'Unknown',
                        'currency': 'USD',
                        'country': 'USA'
                    }
                    
                    # Optionally enrich with live data (rate limited)
                    if enrich and i % 5 == 0:  # Only enrich every 5th stock to save API calls
                        enriched = self.enrich_stock_data(stock['symbol'])
                        if enriched:
                            item.update({
                                'marketCap': Decimal(str(enriched.get('marketCap', 0))),
                                'exchange': enriched.get('exchange', 'Unknown'),
                                'currency': enriched.get('currency', 'USD'),
                                'country': enriched.get('country', 'USA'),
                                'industry': enriched.get('industry', ''),
                                'description': enriched.get('description', '')
                            })
                            item['marketCapBucket'] = self.get_market_cap_bucket(float(item['marketCap']))
                        
                        # Rate limit: 5 calls per minute for free tier
                        import time
                        time.sleep(12)  # Wait 12 seconds between calls
                    
                    batch.put_item(Item=item)
                    seeded_count += 1
                    
                    if (i + 1) % 50 == 0:
                        print(f"Processed {i + 1}/{len(stocks)} stocks...")
                
                except Exception as e:
                    print(f"Failed to seed {stock['symbol']}: {str(e)}")
                    failed_count += 1
        
        print(f"Seeding complete: {seeded_count} succeeded, {failed_count} failed")
        
        return {
            'seeded': seeded_count,
            'failed': failed_count,
            'total': len(stocks)
        }

def lambda_handler(event, context):
    """
    Lambda handler for seeding stock universe
    Can be invoked manually or scheduled via EventBridge
    """
    
    # Check if this is an EventBridge scheduled event
    is_scheduled = event.get('source') == 'aws.events'
    
    # For scheduled updates, enrich with live data
    # For manual invocations, check event parameters
    enrich = event.get('enrich', is_scheduled)
    
    print(f"Starting stock universe seed (enrich={enrich})...")
    
    try:
        seeder = StockUniverseSeeder()
        result = seeder.seed_database(enrich=enrich)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Stock universe seeded successfully',
                'result': result
            })
        }
    
    except Exception as e:
        print(f"Error seeding database: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to seed stock universe',
                'message': str(e)
            })
        }

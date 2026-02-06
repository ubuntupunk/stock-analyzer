"""
Polygon.io API Client
Optional data source - requires API key
"""

import os
import requests
from typing import Dict, Optional


class PolygonClient:
    """Client for Polygon.io API"""
    
    def __init__(self, timeout_seconds: float = 10):
        self.api_key = os.environ.get('POLYGON_API_KEY', '')
        self.base_url = "https://api.polygon.io"
        self.timeout = timeout_seconds
    
    def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """Fetch ticker details from Polygon.io"""
        try:
            if not self.api_key:
                return None
            
            url = f"{self.base_url}/v3/reference/tickers/{symbol}"
            params = {'apiKey': self.api_key}
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', {})
            elif response.status_code == 429:
                print(f"Polygon rate limited for {symbol}")
                return None
            return None
        except requests.Timeout:
            print(f"Polygon timeout for {symbol}")
            return None
        except Exception as e:
            print(f"Polygon error for {symbol}: {str(e)}")
            return None
    
    def fetch_snapshot(self, symbol: str) -> Optional[Dict]:
        """Fetch snapshot from Polygon.io"""
        try:
            if not self.api_key:
                return None
            
            url = f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
            params = {'apiKey': self.api_key}
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('ticker', {})
            elif response.status_code == 429:
                print(f"Polygon rate limited snapshot for {symbol}")
                return None
            return None
        except requests.Timeout:
            print(f"Polygon snapshot timeout for {symbol}")
            return None
        except Exception as e:
            print(f"Polygon snapshot error for {symbol}: {str(e)}")
            return None
    
    def parse_metrics(self, data: Dict) -> Dict:
        """Parse Polygon data into standard metrics format"""
        metrics = {}
        
        try:
            metrics['company_name'] = data.get('name', 'N/A')
            metrics['market_cap'] = data.get('market_cap', 0)
            metrics['shares_outstanding'] = data.get('share_class_shares_outstanding', 0)
            metrics['weighted_shares_outstanding'] = data.get('weighted_shares_outstanding', 0)
            
        except Exception as e:
            print(f"Error parsing Polygon metrics: {str(e)}")
        
        return metrics
    
    def parse_price(self, data: Dict) -> Dict:
        """Parse Polygon snapshot data"""
        price_info = {}
        try:
            day = data.get('day', {})
            prev_day = data.get('prevDay', {})
            
            price_info['price'] = day.get('c', 0)
            price_info['open'] = day.get('o', 0)
            price_info['high'] = day.get('h', 0)
            price_info['low'] = day.get('l', 0)
            price_info['volume'] = day.get('v', 0)
            price_info['previous_close'] = prev_day.get('c', 0)
            
            if price_info['previous_close'] > 0:
                price_info['change'] = price_info['price'] - price_info['previous_close']
                price_info['change_percent'] = (price_info['change'] / price_info['previous_close']) * 100
        except Exception as e:
            print(f"Error parsing Polygon price: {str(e)}")
        
        return price_info

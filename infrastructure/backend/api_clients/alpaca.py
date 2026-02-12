"""
Alpaca API Client
Optional data source - requires API key and secret
"""

import os
import requests
from typing import Dict, Optional


class AlpacaClient:
    """Client for Alpaca API"""

    def __init__(self, timeout_seconds: float = 10):
        self.api_key = os.environ.get("ALPACA_API_KEY", "")
        self.api_secret = os.environ.get("ALPACA_SECRET_KEY", "")
        self.base_url = "https://data.alpaca.markets"
        self.timeout = timeout_seconds

    def fetch_snapshot(self, symbol: str) -> Optional[Dict]:
        """Fetch snapshot from Alpaca"""
        try:
            if not self.api_key or not self.api_secret:
                return None

            url = f"{self.base_url}/v2/stocks/{symbol}/snapshot"
            headers = {
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.api_secret,
            }

            response = requests.get(url, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print(f"Alpaca rate limited for {symbol}")
                return None
            return None
        except requests.Timeout:
            print(f"Alpaca timeout for {symbol}")
            return None
        except Exception as err:
            print(f"Alpaca error for {symbol}: {str(err)}")
            return None

    def parse_price(self, data: Dict) -> Dict:
        """Parse Alpaca snapshot data"""
        price_info = {}
        try:
            latest_trade = data.get("latestTrade", {})
            latest_quote = data.get("latestQuote", {})
            prev_close = data.get("prevDailyBar", {})

            price_info["price"] = latest_trade.get("p", 0)
            price_info["bid"] = latest_quote.get("bp", 0)
            price_info["ask"] = latest_quote.get("ap", 0)
            price_info["volume"] = latest_trade.get("s", 0)
            price_info["timestamp"] = latest_trade.get("t", "")

            if prev_close:
                prev_price = prev_close.get("c", 0)
                if prev_price > 0:
                    price_info["change"] = price_info["price"] - prev_price
                    price_info["change_percent"] = (
                        price_info["change"] / prev_price
                    ) * 100
        except Exception as err:
            print(f"Error parsing Alpaca price: {str(err)}")

        return price_info

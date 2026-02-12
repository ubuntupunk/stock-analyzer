import os
import sys
import json
import yfinance as yf

# Add the project path to sys.path
sys.path.append("/home/ubuntupunk/Projects/stock-analyzer/infrastructure/backend")
sys.path.append(
    "/home/ubuntupunk/Projects/stock-analyzer/infrastructure/backend/api_clients"
)

from api_clients.yahoo_finance import YahooFinanceClient


def test_parsing():
    print("=== Testing YahooFinanceClient Parsing ===")
    client = YahooFinanceClient()
    ticker = yf.Ticker("AAPL")

    print("\n--- Raw Ticker.financials ---")
    print(ticker.financials)

    print("\n--- Parsing Result ---")
    result = client.parse_financials_full(ticker)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    test_parsing()

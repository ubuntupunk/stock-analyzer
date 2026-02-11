"""
Russell 3000 Index Fetcher

Fetches Russell 3000 constituents from iShares ETF holdings or alternative sources.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Optional
from .base import IndexFetcher


class Russell3000Fetcher(IndexFetcher):
    """Fetch Russell 3000 constituents from iShares ETF holdings or fallback sources"""

    def fetch_constituents(self) -> list:
        """
        Fetch Russell 3000 constituents

        Returns:
            List of stock dicts with symbol, name, sector, etc.
        """
        # Try iShares ETF holdings first
        stocks = self._fetch_ishares_holdings()

        if not stocks:
            # Try alternative source
            stocks = self._fetch_from_excel()

        if not stocks:
            # Use fallback list
            stocks = self._get_fallback()

        print(f"✅ Fetched {len(stocks)} stocks from {self.name}")
        return stocks

    def _fetch_ishares_holdings(self) -> list:
        """
        Parse iShares Russell 3000 ETF holdings page

        Returns:
            List of stock dicts or empty list if failed
        """
        etf_symbol = self.config.get('etfSymbol', 'IWV')
        iShares_url = "https://www.ishares.com/us/products/239724/ishares-core-sp-total-us-stock-market-etf"

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            # iShares holdings page requires JavaScript; this is a simplified approach
            # In production, would need to either:
            # 1. Use the iShares API (requires authentication)
            # 2. Use a headless browser to render the page
            # 3. Use alternative data source

            print(f"ℹ️  iShares holdings page requires JavaScript, trying alternative...")

        except Exception as e:
            print(f"⚠️  Error fetching iShares holdings: {e}")

        return []

    def _fetch_from_excel(self) -> list:
        """
        Download and parse Excel file from beatthemarketanalyzer.com

        Returns:
            List of stock dicts or empty list if failed
        """
        fallback_url = self.config.get('fallbackUrl')

        if not fallback_url:
            return []

        try:
            print(f"ℹ️  Downloading holdings from {fallback_url}...")

            # Download the Excel file
            response = requests.get(fallback_url, timeout=30)
            response.raise_for_status()

            # Read Excel file
            import io
            excel_file = io.BytesIO(response.content)
            df = pd.read_excel(excel_file)

            # The Excel file typically has a 'Symbol' column
            if 'Symbol' in df.columns:
                stocks = []
                for _, row in df.iterrows():
                    symbol = str(row['Symbol'])

                    # Some rows might be headers or empty
                    if not symbol or symbol.lower() == 'symbol':
                        continue

                    # For Russell 3000, we may not have sector info from Excel
                    # We'll populate it later from yfinance
                    stock = self.format_stock(
                        symbol=symbol,
                        name='',  # Will be enriched later
                        sector='Unknown'
                    )
                    stocks.append(stock)

                print(f"✅ Parsed {len(stocks)} stocks from Excel")
                return stocks

        except Exception as e:
            print(f"⚠️  Error fetching from Excel: {e}")

        return []

    def _get_fallback(self) -> list:
        """
        Fallback list of popular US stocks from different market cap ranges

        Returns:
            List of stock dicts
        """
        print("ℹ️  Using fallback stock list...")

        # Mix of large, mid, and small cap stocks
        fallback_stocks = [
            # Mega Cap
            ('AAPL', 'Apple Inc.', 'Information Technology'),
            ('MSFT', 'Microsoft Corporation', 'Information Technology'),
            ('GOOGL', 'Alphabet Inc.', 'Communication Services'),
            ('AMZN', 'Amazon.com Inc.', 'Consumer Discretionary'),
            ('NVDA', 'NVIDIA Corporation', 'Information Technology'),

            # Large Cap
            ('META', 'Meta Platforms Inc.', 'Communication Services'),
            ('TSLA', 'Tesla Inc.', 'Consumer Discretionary'),
            ('BRK-B', 'Berkshire Hathaway', 'Financials'),
            ('JPM', 'JPMorgan Chase & Co.', 'Financials'),
            ('V', 'Visa Inc.', 'Financials'),

            # Mid Cap
            ('PLTR', 'Palantir Technologies Inc.', 'Information Technology'),
            ('SOFI', 'SoFi Technologies Inc.', 'Financials'),
            ('RBLX', 'Roblox Corporation', 'Communication Services'),
            ('SNOW', 'Snowflake Inc.', 'Information Technology'),
            ('DASH', 'DoorDash Inc.', 'Consumer Discretionary'),

            # Small Cap
            ('CLOV', 'Clover Health Investments', 'Health Care'),
            ('HOOD', 'Robinhood Markets', 'Financials'),
            ('LCID', 'Lucid Group', 'Consumer Discretionary'),
            ('RIVN', 'Rivian Automotive', 'Consumer Discretionary'),
            ('SPCE', 'Virgin Galactic Holdings', 'Industrials'),
        ]

        stocks = []
        for symbol, name, sector in fallback_stocks:
            stock = self.format_stock(symbol, name, sector)
            stocks.append(stock)

        print(f"✅ Fallback list contains {len(stocks)} stocks")
        return stocks

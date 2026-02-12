"""
JSE (Johannesburg Stock Exchange) Index Fetcher

Fetches JSE All Share / Top 40 constituents with .JO suffix handling
and ZAR to USD FX rate conversion.
"""

import pandas as pd
import yfinance as yf
from .base import IndexFetcher


class JSEFetcher(IndexFetcher):
    """Fetch JSE (Johannesburg Stock Exchange) constituents with ZAR FX conversion"""

    def fetch_constituents(self) -> list:
        """
        Fetch JSE All Share or Top 40 constituents

        Returns:
            List of stock dicts with .JO suffix, ZAR currency, etc.
        """
        # Try Wikipedia first
        stocks = self._fetch_from_wikipedia()

        if not stocks:
            # Use fallback list
            stocks = self._get_fallback()

        print(f"✅ Fetched {len(stocks)} stocks from {self.name}")
        return stocks

    def _fetch_from_wikipedia(self) -> list:
        """
        Parse JSE Top 40 Wikipedia page

        Returns:
            List of stock dicts or empty list if failed
        """
        url = self.url
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            tables = pd.read_html(url, storage_options=headers)

            # The JSE Top 40 page has the constituents table
            jse_table = tables[0]

            stocks = []
            for _, row in jse_table.iterrows():
                # Table structure varies; try common column names
                if "Symbol" in row:
                    symbol = str(row["Symbol"])
                elif "Ticker" in row:
                    symbol = str(row["Ticker"])
                else:
                    continue

                if "Company" in row:
                    name = str(row["Company"])
                elif "Name" in row:
                    name = str(row["Name"])
                else:
                    continue

                # Get sector if available
                sector = str(row.get("Sector", "Unknown"))
                if sector == "nan":
                    sector = "Unknown"

                stock = self.format_stock(symbol=symbol, name=name, sector=sector)

                stocks.append(stock)

            print(f"✅ Fetched {len(stocks)} stocks from Wikipedia")
            return stocks

        except Exception as err:
            print(f"⚠️  Error fetching JSE stocks from Wikipedia: {err}")
            return []

    def _get_fallback(self) -> list:
        """
        Fallback list of popular JSE stocks

        Returns:
            List of JSE stock dicts with .JO suffix
        """
        print("ℹ️  Using fallback JSE stock list...")

        # Popular JSE stocks from various sectors
        fallback_stocks = [
            # Financials
            ("ABG", "Absa Group Ltd", "Financials"),
            ("FSR", "FirstRand Ltd", "Financials"),
            ("NED", "Nedbank Ltd", "Financials"),
            ("SBK", "Standard Bank Group Ltd", "Financials"),
            ("CPI", "Capitec Bank Holdings Ltd", "Financials"),
            ("SPP", "Sanlam Ltd", "Financials"),
            ("MTN", "MTN Group Ltd", "Communication Services"),
            ("VOD", "Vodacom Group Ltd", "Communication Services"),
            # Mining & Resources
            ("AGL", "Anglo American plc", "Materials"),
            ("ANG", "AngloGold Ashanti Ltd", "Materials"),
            ("GLN", "Gold Fields Ltd", "Materials"),
            ("HAR", "Harmony Gold Mining Co Ltd", "Materials"),
            ("SOL", "Sibanye Stillwater Ltd", "Materials"),
            ("IMP", "Impala Platinum Holdings Ltd", "Materials"),
            ("AMS", "African Rainbow Minerals Ltd", "Materials"),
            ("KIO", "Kumba Iron Ore Ltd", "Materials"),
            ("EXX", "Exxaro Resources Ltd", "Materials"),
            # Industrial & Retail
            ("BID", "Bid Corporation Ltd", "Consumer Discretionary"),
            ("NPN", "Naspers Ltd", "Communication Services"),
            ("PRX", "Prosus N.V.", "Consumer Discretionary"),
            ("TKG", "The Foschini Group Ltd", "Consumer Discretionary"),
            ("WHL", "Woolworths Holdings Ltd", "Consumer Staples"),
            ("SHP", "Shoprite Holdings Ltd", "Consumer Staples"),
            ("TFG", "The Foschini Group Ltd", "Consumer Discretionary"),
            ("RCL", "RCL Foods Ltd", "Consumer Staples"),
            ("TRU", "Tiger Brands Ltd", "Consumer Staples"),
            # Technology & Healthcare
            ("DTC", "Netcare Ltd", "Health Care"),
            ("DDT", "Discovery Ltd", "Health Care"),
            ("APN", "Aspen Pharmacare Holdings Ltd", "Health Care"),
            ("MCG", "Mediclinic International Ltd", "Health Care"),
            # Energy
            ("SHP", "Sasol Ltd", "Energy"),
            ("OMN", "Omura Holdings Ltd", "Energy"),
            # Industrial
            ("TCS", "Truworths International Ltd", "Consumer Discretionary"),
            ("CFR", "Crossroads Distribution Ltd", "Industrials"),
            ("DSY", "Dis-Chem Pharmacies Ltd", "Consumer Staples"),
            ("GRW", "Growthpoint Properties Ltd", "Real Estate"),
            ("AEC", "AECI Ltd", "Materials"),
        ]

        stocks = []
        for symbol, name, sector in fallback_stocks:
            stock = self.format_stock(symbol, name, sector)
            stocks.append(stock)

        print(f"✅ Fallback list contains {len(stocks)} stocks")
        return stocks

    def get_fx_rate(self) -> float:
        """
        Get current ZAR/USD exchange rate from yfinance

        Returns:
            Exchange rate (ZAR per 1 USD) - e.g., 18.5 means 18.5 ZAR = 1 USD
        """
        fx_symbol = self.config.get("fxRate", {}).get("symbol", "ZAR=X")

        try:
            ticker = yf.Ticker(fx_symbol)
            info = ticker.info

            # Try to get live rate, fallback to previous close
            rate = info.get("regularMarketPrice") or info.get("previousClose")

            if rate and rate > 0:
                print(f"ℹ️  FX Rate: {rate:.2f} ZAR = 1 USD")
                return float(rate)

        except Exception as err:
            print(f"⚠️  Error fetching ZAR/USD rate: {err}")

        # Fallback rate (approximately current)
        print("ℹ️  Using fallback FX rate: 18.50 ZAR = 1 USD")
        return 18.50

    def apply_fx_conversion(self, amount: float, fx_rate: float = None) -> float:
        """
        Convert ZAR amount to USD

        Args:
            amount: Amount in ZAR
            fx_rate: Exchange rate (ZAR per 1 USD)

        Returns:
            Amount converted to USD
        """
        if amount == 0:
            return 0.0

        return super().apply_fx_conversion(amount, fx_rate)

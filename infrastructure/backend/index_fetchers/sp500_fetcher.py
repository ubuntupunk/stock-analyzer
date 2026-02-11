"""
S&P 500 Index Fetcher

Fetches S&P 500 constituents from Wikipedia.
"""

import pandas as pd
from .base import IndexFetcher


class SP500Fetcher(IndexFetcher):
    """Fetch S&P 500 constituents from Wikipedia"""

    def fetch_constituents(self) -> list:
        """
        Fetch S&P 500 constituents from Wikipedia

        Returns:
            List of stock dicts with symbol, name, sector, subSector, etc.
        """
        url = self.url
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            # Fetch S&P 500 table from Wikipedia
            tables = pd.read_html(url, storage_options=headers)
            sp500_table = tables[0]

            stocks = []
            for _, row in sp500_table.iterrows():
                symbol = str(row['Symbol'])
                name = str(row['Security'])
                sector = str(row['GICS Sector'])
                sub_sector = str(row['GICS Sub-Industry'])
                headquarters = str(row['Headquarters Location'])

                stock = self.format_stock(
                    symbol=symbol,
                    name=name,
                    sector=sector,
                    subSector=sub_sector
                )

                # Add headquarters for additional context
                if headquarters and headquarters != 'nan':
                    stock['headquarters'] = headquarters

                stocks.append(stock)

            print(f"✅ Fetched {len(stocks)} stocks from {self.name}")
            return stocks

        except Exception as e:
            print(f"❌ Error fetching {self.name} from Wikipedia: {e}")
            return self._get_fallback()

    def _get_fallback(self) -> list:
        """
        Fallback hardcoded list of popular S&P 500 stocks

        Returns:
            List of popular stock dicts
        """
        print("ℹ️  Using fallback stock list...")
        fallback_stocks = [
            ('AAPL', 'Apple Inc.', 'Information Technology', 'Technology Hardware, Storage & Peripherals'),
            ('MSFT', 'Microsoft Corporation', 'Information Technology', 'Software'),
            ('GOOGL', 'Alphabet Inc.', 'Communication Services', 'Interactive Media & Services'),
            ('GOOG', 'Alphabet Inc.', 'Communication Services', 'Interactive Media & Services'),
            ('AMZN', 'Amazon.com Inc.', 'Consumer Discretionary', 'Internet & Direct Marketing Retail'),
            ('NVDA', 'NVIDIA Corporation', 'Information Technology', 'Semiconductors'),
            ('META', 'Meta Platforms Inc.', 'Communication Services', 'Interactive Media & Services'),
            ('TSLA', 'Tesla Inc.', 'Consumer Discretionary', 'Automobiles'),
            ('TSM', 'Taiwan Semiconductor', 'Information Technology', 'Semiconductors'),
            ('AVGO', 'Broadcom Inc.', 'Information Technology', 'Semiconductors'),
            ('BRK-B', 'Berkshire Hathaway', 'Financials', 'Insurance'),
            ('JPM', 'JPMorgan Chase & Co.', 'Financials', 'Banks'),
            ('V', 'Visa Inc.', 'Financials', 'Consumer Finance'),
            ('MA', 'Mastercard Inc.', 'Financials', 'Consumer Finance'),
            ('BAC', 'Bank of America', 'Financials', 'Banks'),
            ('WFC', 'Wells Fargo & Company', 'Financials', 'Banks'),
            ('UNH', 'UnitedHealth Group', 'Health Care', 'Health Care Providers'),
            ('JNJ', 'Johnson & Johnson', 'Health Care', 'Pharmaceuticals'),
            ('LLY', 'Eli Lilly and Company', 'Health Care', 'Pharmaceuticals'),
            ('PFE', 'Pfizer Inc.', 'Health Care', 'Pharmaceuticals'),
            ('ABBV', 'AbbVie Inc.', 'Health Care', 'Pharmaceuticals'),
            ('MRK', 'Merck & Co. Inc.', 'Health Care', 'Pharmaceuticals'),
            ('WMT', 'Walmart Inc.', 'Consumer Staples', 'Food Retail'),
            ('HD', 'The Home Depot', 'Consumer Discretionary', 'Home Improvement Retail'),
            ('PG', 'Procter & Gamble Co.', 'Consumer Staples', 'Household Products'),
            ('COST', 'Costco Wholesale', 'Consumer Staples', 'Food Retail'),
            ('KO', 'Coca-Cola Company', 'Consumer Staples', 'Beverages'),
            ('XOM', 'Exxon Mobil Corp.', 'Energy', 'Integrated Oil & Gas'),
            ('CVX', 'Chevron Corp.', 'Energy', 'Integrated Oil & Gas'),
            ('BA', 'Boeing Company', 'Industrials', 'Aerospace & Defense'),
            ('CAT', 'Caterpillar Inc.', 'Industrials', 'Construction Machinery'),
            ('GE', 'General Electric', 'Industrials', 'Industrial Conglomerates'),
            ('UPS', 'United Parcel Service', 'Industrials', 'Air Freight & Logistics'),
            ('T', 'AT&T Inc.', 'Communication Services', 'Integrated Telecommunication'),
            ('VZ', 'Verizon Communications', 'Communication Services', 'Integrated Telecommunication'),
            ('CMCSA', 'Comcast Corp.', 'Communication Services', 'Cable & Satellite'),
            ('NFLX', 'Netflix Inc.', 'Communication Services', 'Movies & Entertainment'),
            ('ORCL', 'Oracle Corp.', 'Information Technology', 'Software'),
            ('CSCO', 'Cisco Systems', 'Information Technology', 'Communications Equipment'),
            ('ADBE', 'Adobe Inc.', 'Information Technology', 'Software'),
            ('CRM', 'Salesforce Inc.', 'Information Technology', 'Software'),
            ('INTC', 'Intel Corp.', 'Information Technology', 'Semiconductors'),
            ('AMD', 'AMD', 'Information Technology', 'Semiconductors'),
            ('QCOM', 'Qualcomm Inc.', 'Information Technology', 'Semiconductors'),
            ('IBM', 'IBM', 'Information Technology', 'IT Services'),
        ]

        stocks = []
        for symbol, name, sector, sub_sector in fallback_stocks:
            stock = self.format_stock(symbol, name, sector, sub_sector)
            stocks.append(stock)

        print(f"✅ Fallback list contains {len(stocks)} stocks")
        return stocks

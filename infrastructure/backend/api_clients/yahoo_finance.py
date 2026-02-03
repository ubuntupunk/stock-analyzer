"""
Yahoo Finance API Client
Primary data source - Uses yfinance library (handles authentication internally)
"""

import yfinance as yf
import pandas as pd
from typing import Dict, List, Optional


class YahooFinanceClient:
    """Client for Yahoo Finance API using yfinance library"""
    
    def __init__(self):
        self.base_url = "https://query2.finance.yahoo.com/v10/finance/quoteSummary"
    
    def fetch_data(self, symbol: str, modules: str = None) -> Optional[Dict]:
        """
        Fetch data from Yahoo Finance using yfinance
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Return the info dict which contains all data
            # yfinance handles the API authentication internally
            if info:
                return info
            return None
        except Exception as e:
            print(f"YFinance error for {symbol}: {str(e)}")
            return None
    
    async def fetch_data_async(self, session, symbol: str, modules: str = None):
        """
        Async version of fetch_data using yfinance
        Returns: (symbol, data) tuple
        """
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Debug: log what we received
            if info:
                has_price = 'currentPrice' in info or 'regularMarketPrice' in info
                print(f"YFinance async: {symbol} - info keys: {len(info)}, has price key: {has_price}")
                return (symbol, info)
            else:
                print(f"YFinance async: {symbol} - info is empty or None")
                return (symbol, None)
        except Exception as e:
            print(f"YFinance async error for {symbol}: {str(e)}")
            return (symbol, None)
    
    def parse_price(self, data: Dict) -> Dict:
        """Parse Yahoo Finance price data"""
        price_info = {}
        try:
            def get_value(obj, key, default=0):
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default) if hasattr(obj, key) else default
            
            price_info['price'] = data.get('currentPrice', data.get('regularMarketPrice', 0))
            price_info['open'] = data.get('open', 0)
            price_info['high'] = data.get('dayHigh', data.get('regularMarketDayHigh', 0))
            price_info['low'] = data.get('dayLow', data.get('regularMarketDayLow', 0))
            price_info['volume'] = data.get('volume', data.get('regularMarketVolume', 0))
            price_info['previous_close'] = data.get('previousClose', data.get('regularMarketPreviousClose', 0))
            price_info['change'] = data.get('change', data.get('regularMarketChange', 0))
            price_info['change_percent'] = data.get('changePercent', data.get('regularMarketChangePercent', 0))
        except Exception as e:
            print(f"Error parsing Yahoo Finance price: {str(e)}")
        
        return price_info
    
    def fetch_history(self, symbol: str, period: str = '1mo') -> Optional[Dict]:
        """
        Fetch historical price data for charting
        Returns dict with dates as keys and OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist is None or hist.empty:
                return None
            
            # Convert to dict format expected by frontend
            historical_data = {}
            for date, row in hist.iterrows():
                date_str = date.strftime('%Y-%m-%d')
                historical_data[date_str] = {
                    '1. open': float(row['Open']),
                    '2. high': float(row['High']),
                    '3. low': float(row['Low']),
                    '4. close': float(row['Close']),
                    '5. volume': int(row['Volume'])
                }
            
            return historical_data
        except Exception as e:
            print(f"YFinance history error for {symbol}: {str(e)}")
            return None
    
    def fetch_history_range(self, symbol: str, startDate: str, endDate: str) -> Optional[Dict]:
        """
        Fetch historical price data for a custom date range
        Returns dict with dates as keys and OHLCV data
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            startDate: Start date in YYYY-MM-DD format
            endDate: End date in YYYY-MM-DD format
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=startDate, end=endDate)
            
            if hist is None or hist.empty:
                return None
            
            # Convert to dict format expected by frontend
            historical_data = {}
            for date, row in hist.iterrows():
                date_str = date.strftime('%Y-%m-%d')
                historical_data[date_str] = {
                    '1. open': float(row['Open']),
                    '2. high': float(row['High']),
                    '3. low': float(row['Low']),
                    '4. close': float(row['Close']),
                    '5. volume': int(row['Volume'])
                }
            
            return historical_data
        except Exception as e:
            print(f"YFinance history range error for {symbol}: {str(e)}")
            return None
    
    def parse_history(self, historical_data: Dict) -> Dict:
        """Parse historical data into price format with historicalData key"""
        return {
            'historicalData': historical_data
        }
    
    def parse_metrics(self, data: Dict) -> Dict:
        """Parse Yahoo Finance data into standard metrics format"""
        metrics = {}
        
        try:
            # Helper function to extract value
            def get_value(key, default=None):
                return data.get(key, default)
            
            metrics['company_name'] = data.get('shortName', data.get('longName', 'N/A'))
            metrics['current_price'] = data.get('currentPrice', data.get('regularMarketPrice', 0))
            metrics['market_cap'] = data.get('marketCap', 0)
            metrics['shares_outstanding'] = data.get('sharesOutstanding', 0)
            metrics['revenue'] = data.get('totalRevenue', 0)
            metrics['pe_ratio'] = data.get('trailingPE', 0)
            metrics['forward_pe'] = data.get('forwardPE', 0)
            metrics['peg_ratio'] = data.get('pegRatio', 0)
            metrics['price_to_book'] = data.get('priceToBook', 0)
            metrics['dividend_yield'] = data.get('dividendYield', 0)
            metrics['52_week_high'] = data.get('fiftyTwoWeekHigh', 0)
            metrics['52_week_low'] = data.get('fiftyTwoWeekLow', 0)
            metrics['50_day_avg'] = data.get('fiftyDayAverage', 0)
            metrics['200_day_avg'] = data.get('twoHundredDayAverage', 0)
            metrics['volume'] = data.get('volume', 0)
            metrics['avg_volume'] = data.get('averageVolume', 0)
            metrics['beta'] = data.get('beta', 0)
            metrics['eps'] = data.get('trailingEps', 0)
            metrics['revenue_growth'] = data.get('revenueGrowth', 0)
            metrics['earnings_growth'] = data.get('earningsGrowth', 0)
            metrics['profit_margin'] = data.get('profitMargins', 0)
            metrics['operating_margin'] = data.get('operatingMargins', 0)
            metrics['roe'] = data.get('returnOnEquity', 0)
            metrics['roa'] = data.get('returnOnAssets', 0)
            metrics['debt_to_equity'] = data.get('debtToEquity', 0)
            metrics['current_ratio'] = data.get('currentRatio', 0)
            metrics['free_cash_flow'] = data.get('freeCashflow', 0)
            metrics['operating_cash_flow'] = data.get('operatingCashflow', 0)
            
        except Exception as e:
            print(f"Error parsing Yahoo Finance metrics: {str(e)}")
        
        return metrics
    
    def parse_estimates(self, data: Dict) -> Dict:
        """Parse Yahoo Finance analyst estimates"""
        estimates = {}
        try:
            # Try to get earnings estimates from available data
            earnings_list = []
            revenue_list = []
            
            # Forward estimates from info
            if 'targetMeanPrice' in data:
                earnings_list.append({
                    'period': '1y',
                    'avg': data.get('targetMeanPrice', 0),
                    'low': data.get('targetLowPrice', 0),
                    'high': data.get('targetHighPrice', 0),
                    'num_analysts': data.get('numberOfAnalystOpinions', 0)
                })
            
            estimates['earnings_estimates'] = earnings_list
            estimates['revenue_estimates'] = revenue_list
            
        except Exception as e:
            print(f"Error parsing Yahoo Finance estimates: {str(e)}")
        
        return estimates
    
    def parse_financials(self, data: Dict) -> Dict:
        """Parse Yahoo Finance financial statements - legacy method using info dict"""
        return self.parse_financials_full(data)

    def parse_financials_full(self, data: Dict = None) -> Dict:
        """
        Parse Yahoo Finance financial statements with full historical data
        
        Args:
            data: Optional ticker object from yfinance
        """
        parsed = {}
        
        try:
            # If data is a ticker object, use its financial statement methods
            if data is not None:
                ticker = data
                
                # Parse Income Statement
                try:
                    financials = ticker.financials
                    if financials is not None and not financials.empty:
                        income_statement = []
                        # Columns are dates, rows are line items
                        for date in financials.columns[:4]:  # Get up to 4 years
                            income_statement.append({
                                'fiscal_date': date.strftime('%Y-%m') if hasattr(date, 'strftime') else str(date),
                                'revenue': float(financials.loc['Total Revenue', date]) if 'Total Revenue' in financials.index and not pd.isna(financials.loc['Total Revenue', date]) else 0,
                                'net_income': float(financials.loc['Net Income', date]) if 'Net Income' in financials.index and not pd.isna(financials.loc['Net Income', date]) else 0,
                                'ebitda': float(financials.loc['EBITDA', date]) if 'EBITDA' in financials.index and not pd.isna(financials.loc['EBITDA', date]) else 0,
                                'gross_profit': float(financials.loc['Gross Profit', date]) if 'Gross Profit' in financials.index and not pd.isna(financials.loc['Gross Profit', date]) else 0,
                                'operating_income': float(financials.loc['Operating Income', date]) if 'Operating Income' in financials.index and not pd.isna(financials.loc['Operating Income', date]) else 0
                            })
                        parsed['income_statement'] = income_statement
                except Exception as e:
                    print(f"Error parsing income statement: {str(e)}")
                    parsed['income_statement'] = []

                # Parse Balance Sheet
                try:
                    balance_sheet = ticker.balance_sheet
                    if balance_sheet is not None and not balance_sheet.empty:
                        balance_data = []
                        # Columns are dates, rows are line items
                        for date in balance_sheet.columns[:4]:  # Get up to 4 years
                            balance_data.append({
                                'fiscal_date': date.strftime('%Y-%m') if hasattr(date, 'strftime') else str(date),
                                'total_assets': float(balance_sheet.loc['Total Assets', date]) if 'Total Assets' in balance_sheet.index and not pd.isna(balance_sheet.loc['Total Assets', date]) else 0,
                                'total_liabilities': float(balance_sheet.loc['Total Liabilities Net Minority Interest', date]) if 'Total Liabilities Net Minority Interest' in balance_sheet.index and not pd.isna(balance_sheet.loc['Total Liabilities Net Minority Interest', date]) else 0,
                                'shareholders_equity': float(balance_sheet.loc['Stockholders Equity', date]) if 'Stockholders Equity' in balance_sheet.index and not pd.isna(balance_sheet.loc['Stockholders Equity', date]) else 0,
                                'cash': float(balance_sheet.loc['Cash And Cash Equivalents', date]) if 'Cash And Cash Equivalents' in balance_sheet.index and not pd.isna(balance_sheet.loc['Cash And Cash Equivalents', date]) else 0,
                                'long_term_debt': float(balance_sheet.loc['Long Term Debt', date]) if 'Long Term Debt' in balance_sheet.index and not pd.isna(balance_sheet.loc['Long Term Debt', date]) else 0
                            })
                        parsed['balance_sheet'] = balance_data
                except Exception as e:
                    print(f"Error parsing balance sheet: {str(e)}")
                    parsed['balance_sheet'] = []

                # Parse Cash Flow
                try:
                    cashflow = ticker.cashflow
                    if cashflow is not None and not cashflow.empty:
                        cash_flow = []
                        # Columns are dates, rows are line items
                        for date in cashflow.columns[:4]:  # Get up to 4 years
                            cash_flow.append({
                                'fiscal_date': date.strftime('%Y-%m') if hasattr(date, 'strftime') else str(date),
                                'operating_cashflow': float(cashflow.loc['Operating Cash Flow', date]) if 'Operating Cash Flow' in cashflow.index and not pd.isna(cashflow.loc['Operating Cash Flow', date]) else 0,
                                'free_cash_flow': float(cashflow.loc['Free Cash Flow', date]) if 'Free Cash Flow' in cashflow.index and not pd.isna(cashflow.loc['Free Cash Flow', date]) else 0,
                                'capex': float(cashflow.loc['Capital Expenditure', date]) if 'Capital Expenditure' in cashflow.index and not pd.isna(cashflow.loc['Capital Expenditure', date]) else 0,
                                'dividends_paid': float(cashflow.loc['Cash Dividends Paid', date]) if 'Cash Dividends Paid' in cashflow.index and not pd.isna(cashflow.loc['Cash Dividends Paid', date]) else 0,
                                'stock_repurchased': float(cashflow.loc['Repurchase Of Capital Stock', date]) if 'Repurchase Of Capital Stock' in cashflow.index and not pd.isna(cashflow.loc['Repurchase Of Capital Stock', date]) else 0
                            })
                        parsed['cash_flow'] = cash_flow
                except Exception as e:
                    print(f"Error parsing cash flow: {str(e)}")
                    parsed['cash_flow'] = []
                    
            # Fallback to info dict if no ticker object
            if not parsed or (not parsed.get('income_statement') and data and isinstance(data, dict)):
                parsed = {
                    'income_statement': [{
                        'revenue': data.get('totalRevenue', 0),
                        'net_income': data.get('netIncomeToCommon', 0),
                        'ebitda': data.get('ebitda', 0)
                    }],
                    'balance_sheet': [{
                        'total_assets': data.get('totalAssets', 0),
                        'total_liabilities': data.get('totalLiabilities', 0),
                        'shareholders_equity': data.get('totalStockholderEquity', 0),
                        'cash': data.get('cash', 0)
                    }],
                    'cash_flow': [{
                        'operating_cashflow': data.get('operatingCashflow', 0),
                        'free_cash_flow': data.get('freeCashflow', 0),
                        'capex': data.get('capitalExpenditures', 0)
                    }]
                }
            
        except Exception as e:
            print(f"Error parsing Yahoo Finance financials: {str(e)}")
            # Return empty arrays on error
            parsed = {
                'income_statement': [],
                'balance_sheet': [],
                'cash_flow': []
            }
        
        return parsed

    def fetch_financials(self, symbol: str) -> Dict:
        """
        Fetch full financial statements from Yahoo Finance
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Dict with income_statement, balance_sheet, cash_flow arrays
        """
        try:
            ticker = yf.Ticker(symbol)
            return self.parse_financials_full(ticker)
        except Exception as e:
            print(f"YFinance fetch_financials error for {symbol}: {str(e)}")
            return {
                'income_statement': [],
                'balance_sheet': [],
                'cash_flow': []
            }
    
    def fetch_news(self, symbol: str) -> List[Dict]:
        """
        Fetch news for a stock from Yahoo Finance
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            List of news articles with title, url, publishedAt, source, summary
        """
        try:
            ticker = yf.Ticker(symbol)
            news_data = ticker.news
            
            print(f"YFinance fetch_news for {symbol}: received {len(news_data) if news_data else 0} items")
            if news_data and len(news_data) > 0:
                # Log first item structure for debugging
                print(f"YFinance news keys for {symbol}: {list(news_data[0].keys())}")
                
                articles = []
                for item in news_data[:20]:  # Limit to 20 articles
                    # Handle provider - can be dict or string
                    provider = item.get('provider')
                    if isinstance(provider, dict):
                        source = provider.get('name', 'Yahoo Finance')
                    elif provider:
                        source = str(provider)
                    else:
                        source = 'Yahoo Finance'
                    
                    # Handle timestamp
                    pub_time = item.get('providerPublishTime')
                    if pub_time:
                        # Convert Unix timestamp to ISO format
                        from datetime import datetime
                        try:
                            pub_date = datetime.fromtimestamp(pub_time).isoformat()
                        except:
                            pub_date = str(pub_time)
                    else:
                        pub_date = item.get('pubDate', '')
                    
                    articles.append({
                        'title': item.get('title', item.get('headline', 'No Title')),
                        'url': item.get('link', item.get('url', '#')),
                        'publishedAt': pub_date,
                        'source': source,
                        'summary': item.get('summary', item.get('description', ''))
                    })
                return articles
            return []
        except Exception as e:
            print(f"YFinance fetch_news error for {symbol}: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

"""
Yahoo Finance API Client
Primary data source - Uses yfinance library (handles authentication internally)
"""

import yfinance as yf
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
            
            if info:
                return (symbol, info)
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
        """Parse Yahoo Finance financial statements"""
        parsed = {}
        
        try:
            # Basic financial data from info dict
            parsed['income_statement'] = [{
                'revenue': data.get('totalRevenue', 0),
                'net_income': data.get('netIncomeToCommon', 0),
                'ebitda': data.get('ebitda', 0)
            }]
            
            parsed['balance_sheet'] = [{
                'total_assets': data.get('totalAssets', 0),
                'total_liabilities': data.get('totalLiabilities', 0),
                'shareholders_equity': data.get('totalStockholderEquity', 0),
                'cash': data.get('cash', 0)
            }]
            
            parsed['cash_flow'] = [{
                'operating_cashflow': data.get('operatingCashflow', 0),
                'free_cash_flow': data.get('freeCashflow', 0),
                'capex': data.get('capitalExpenditures', 0)
            }]
            
        except Exception as e:
            print(f"Error parsing Yahoo Finance financials: {str(e)}")
        
        return parsed

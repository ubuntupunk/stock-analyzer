import json
import os
import requests
import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

class StockDataAPI:
    """
    Multi-source stock data API with fallback mechanisms
    
    API Priority Order (from highest to lowest):
    1. Yahoo Finance - FREE, no API key required, no rate limits (best option)
    2. Alpaca - Real-time data with free tier, requires API key
    3. Polygon.io - Requires API key, some rate limits
    4. Alpha Vantage - FREE but RATE LIMITED (5 calls/minute on free tier)
    
    Strategy:
    - Try free, unlimited APIs first (Yahoo Finance)
    - Use sequential fallback (not concurrent) to avoid hitting rate limits
    - Alpha Vantage is last resort due to strict rate limiting
    - Cache all responses for 5 minutes to minimize API calls
    """
    
    def __init__(self):
        # API Keys from environment variables
        self.alpha_vantage_key = os.environ.get('FINANCIAL_API_KEY', 'demo')
        self.polygon_key = os.environ.get('POLYGON_API_KEY', '')
        self.alpaca_key = os.environ.get('ALPACA_API_KEY', '')
        self.alpaca_secret = os.environ.get('ALPACA_SECRET_KEY', '')
        
        # API Base URLs
        self.alpha_vantage_url = "https://www.alphavantage.co/query"
        self.polygon_url = "https://api.polygon.io"
        self.alpaca_url = "https://data.alpaca.markets"
        
        # Cache for reducing API calls
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
    
    def _get_cache_key(self, prefix: str, symbol: str) -> str:
        """Generate cache key"""
        return f"{prefix}:{symbol}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key].get('timestamp', 0)
        return (datetime.now().timestamp() - cached_time) < self.cache_timeout
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache if valid"""
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key].get('data')
        return None
    
    def _set_cache(self, cache_key: str, data: Dict):
        """Store data in cache"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now().timestamp()
        }
    
    def _fetch_yfinance_data(self, symbol: str, modules: str = None) -> Optional[Dict]:
        """
        Fetch data from Yahoo Finance with specified modules
        
        Default modules include: price, summaryDetail, defaultKeyStatistics, financialData, 
        earningsTrend, incomeStatementHistory, balanceSheetHistory, cashflowStatementHistory
        
        This unified method fetches ALL data in a single request to minimize API calls.
        """
        try:
            # Yahoo Finance API endpoint (unofficial)
            url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
            
            # Default: fetch ALL modules in one request for maximum efficiency
            if modules is None:
                modules = 'price,summaryDetail,defaultKeyStatistics,financialData,earningsTrend,incomeStatementHistory,balanceSheetHistory,cashflowStatementHistory'
            
            params = {'modules': modules}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('quoteSummary', {}).get('result', [])
                if result:
                    return result[0]
            return None
        except Exception as e:
            print(f"YFinance error for {symbol}: {str(e)}")
            return None
    
    def _fetch_alpha_vantage_overview(self, symbol: str) -> Optional[Dict]:
        """Fetch company overview from Alpha Vantage"""
        try:
            params = {
                'function': 'OVERVIEW',
                'symbol': symbol,
                'apikey': self.alpha_vantage_key
            }
            
            response = requests.get(self.alpha_vantage_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'Symbol' in data:
                    return data
            return None
        except Exception as e:
            print(f"Alpha Vantage error for {symbol}: {str(e)}")
            return None
    
    def _fetch_alpha_vantage_quote(self, symbol: str) -> Optional[Dict]:
        """Fetch real-time quote from Alpha Vantage"""
        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.alpha_vantage_key
            }
            
            response = requests.get(self.alpha_vantage_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('Global Quote', {})
            return None
        except Exception as e:
            print(f"Alpha Vantage quote error for {symbol}: {str(e)}")
            return None
    
    def _fetch_polygon_ticker(self, symbol: str) -> Optional[Dict]:
        """Fetch ticker details from Polygon.io"""
        try:
            if not self.polygon_key:
                return None
            
            url = f"{self.polygon_url}/v3/reference/tickers/{symbol}"
            params = {'apiKey': self.polygon_key}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', {})
            return None
        except Exception as e:
            print(f"Polygon error for {symbol}: {str(e)}")
            return None
    
    def _fetch_polygon_snapshot(self, symbol: str) -> Optional[Dict]:
        """Fetch snapshot from Polygon.io"""
        try:
            if not self.polygon_key:
                return None
            
            url = f"{self.polygon_url}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
            params = {'apiKey': self.polygon_key}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('ticker', {})
            return None
        except Exception as e:
            print(f"Polygon snapshot error for {symbol}: {str(e)}")
            return None
    
    def _fetch_alpaca_snapshot(self, symbol: str) -> Optional[Dict]:
        """Fetch snapshot from Alpaca"""
        try:
            if not self.alpaca_key or not self.alpaca_secret:
                return None
            
            url = f"{self.alpaca_url}/v2/stocks/{symbol}/snapshot"
            headers = {
                'APCA-API-KEY-ID': self.alpaca_key,
                'APCA-API-SECRET-KEY': self.alpaca_secret
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Alpaca error for {symbol}: {str(e)}")
            return None
    
    def get_stock_metrics(self, symbol: str) -> Dict:
        """
        Get comprehensive stock metrics from multiple sources with fallback
        Returns: P/E, Market Cap, ROE, Revenue Growth, etc.
        Priority: Yahoo Finance (free, unlimited) > Alpha Vantage (rate limited) > Polygon
        """
        cache_key = self._get_cache_key('metrics', symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        metrics = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'source': 'unknown'
        }
        
        # Try Yahoo Finance FIRST (most reliable, free, no rate limits)
        yf_data = self._fetch_yfinance_data(symbol)
        if yf_data:
            metrics.update(self._parse_yfinance_metrics(yf_data))
            metrics['source'] = 'yahoo_finance'
        
        # Fallback to Alpha Vantage (rate limited - 5 calls/minute)
        if metrics['source'] == 'unknown':
            av_data = self._fetch_alpha_vantage_overview(symbol)
            if av_data:
                metrics.update(self._parse_alpha_vantage_metrics(av_data))
                metrics['source'] = 'alpha_vantage'
        
        # Enhance with Polygon data if available (optional enrichment)
        if self.polygon_key:
            poly_data = self._fetch_polygon_ticker(symbol)
            if poly_data:
                metrics.update(self._parse_polygon_metrics(poly_data))
                if metrics['source'] == 'unknown':
                    metrics['source'] = 'polygon'
        
        self._set_cache(cache_key, metrics)
        return metrics
    
    def _parse_yfinance_metrics(self, data: Dict) -> Dict:
        """Parse Yahoo Finance data into standard metrics format"""
        metrics = {}
        
        try:
            price_data = data.get('price', {})
            summary = data.get('summaryDetail', {})
            key_stats = data.get('defaultKeyStatistics', {})
            financial = data.get('financialData', {})
            
            # Helper function to extract value
            def get_value(obj, default=None):
                if isinstance(obj, dict):
                    return obj.get('raw', default)
                return obj or default
            
            metrics['company_name'] = get_value(price_data.get('shortName'), 'N/A')
            metrics['current_price'] = get_value(price_data.get('regularMarketPrice'), 0)
            metrics['market_cap'] = get_value(price_data.get('marketCap'), 0)
            metrics['pe_ratio'] = get_value(summary.get('trailingPE'), 0)
            metrics['forward_pe'] = get_value(summary.get('forwardPE'), 0)
            metrics['peg_ratio'] = get_value(key_stats.get('pegRatio'), 0)
            metrics['price_to_book'] = get_value(key_stats.get('priceToBook'), 0)
            metrics['dividend_yield'] = get_value(summary.get('dividendYield'), 0)
            metrics['52_week_high'] = get_value(summary.get('fiftyTwoWeekHigh'), 0)
            metrics['52_week_low'] = get_value(summary.get('fiftyTwoWeekLow'), 0)
            metrics['50_day_avg'] = get_value(summary.get('fiftyDayAverage'), 0)
            metrics['200_day_avg'] = get_value(summary.get('twoHundredDayAverage'), 0)
            metrics['volume'] = get_value(price_data.get('regularMarketVolume'), 0)
            metrics['avg_volume'] = get_value(price_data.get('averageDailyVolume10Day'), 0)
            metrics['beta'] = get_value(key_stats.get('beta'), 0)
            metrics['eps'] = get_value(key_stats.get('trailingEps'), 0)
            metrics['revenue_growth'] = get_value(financial.get('revenueGrowth'), 0)
            metrics['earnings_growth'] = get_value(financial.get('earningsGrowth'), 0)
            metrics['profit_margin'] = get_value(financial.get('profitMargins'), 0)
            metrics['operating_margin'] = get_value(financial.get('operatingMargins'), 0)
            metrics['roe'] = get_value(financial.get('returnOnEquity'), 0)
            metrics['roa'] = get_value(financial.get('returnOnAssets'), 0)
            metrics['debt_to_equity'] = get_value(financial.get('debtToEquity'), 0)
            metrics['current_ratio'] = get_value(financial.get('currentRatio'), 0)
            metrics['free_cash_flow'] = get_value(financial.get('freeCashflow'), 0)
            metrics['operating_cash_flow'] = get_value(financial.get('operatingCashflow'), 0)
            
        except Exception as e:
            print(f"Error parsing Yahoo Finance metrics: {str(e)}")
        
        return metrics
    
    def _parse_alpha_vantage_metrics(self, data: Dict) -> Dict:
        """Parse Alpha Vantage data into standard metrics format"""
        metrics = {}
        
        try:
            def safe_float(value, default=0):
                try:
                    return float(value) if value and value != 'None' else default
                except:
                    return default
            
            metrics['company_name'] = data.get('Name', 'N/A')
            metrics['market_cap'] = safe_float(data.get('MarketCapitalization'))
            metrics['pe_ratio'] = safe_float(data.get('PERatio'))
            metrics['forward_pe'] = safe_float(data.get('ForwardPE'))
            metrics['peg_ratio'] = safe_float(data.get('PEGRatio'))
            metrics['price_to_book'] = safe_float(data.get('PriceToBookRatio'))
            metrics['dividend_yield'] = safe_float(data.get('DividendYield'))
            metrics['52_week_high'] = safe_float(data.get('52WeekHigh'))
            metrics['52_week_low'] = safe_float(data.get('52WeekLow'))
            metrics['50_day_avg'] = safe_float(data.get('50DayMovingAverage'))
            metrics['200_day_avg'] = safe_float(data.get('200DayMovingAverage'))
            metrics['beta'] = safe_float(data.get('Beta'))
            metrics['eps'] = safe_float(data.get('EPS'))
            metrics['revenue_per_share'] = safe_float(data.get('RevenuePerShareTTM'))
            metrics['profit_margin'] = safe_float(data.get('ProfitMargin'))
            metrics['operating_margin'] = safe_float(data.get('OperatingMarginTTM'))
            metrics['roe'] = safe_float(data.get('ReturnOnEquityTTM'))
            metrics['roa'] = safe_float(data.get('ReturnOnAssetsTTM'))
            metrics['revenue_growth_yoy'] = safe_float(data.get('QuarterlyRevenueGrowthYOY'))
            metrics['earnings_growth_yoy'] = safe_float(data.get('QuarterlyEarningsGrowthYOY'))
            
        except Exception as e:
            print(f"Error parsing Alpha Vantage metrics: {str(e)}")
        
        return metrics
    
    def _parse_polygon_metrics(self, data: Dict) -> Dict:
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
    
    def get_stock_price(self, symbol: str) -> Dict:
        """
        Get current stock price and basic quote information
        Priority: Yahoo Finance (free) > Alpaca > Polygon > Alpha Vantage (rate limited)
        
        Note: Sequential fallback strategy (not concurrent) to avoid rate limits.
        Each source is only tried if previous sources fail.
        """
        cache_key = self._get_cache_key('price', symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        price_data = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'source': 'unknown'
        }
        
        # Try multiple sources with sequential fallback
        # Priority order: Yahoo Finance (free, no key) > Alpaca > Polygon > Alpha Vantage (rate limited)
        
        # 1. Try Yahoo Finance first (FREE, no API key, reliable, NO rate limits)
        yf_data = self._fetch_yfinance_data(symbol)
        if yf_data:
            price_data.update(self._parse_yfinance_price(yf_data))
            price_data['source'] = 'yahoo_finance'
        
        # 2. Try Alpaca (real-time for free, if API key available)
        if price_data['source'] == 'unknown' and self.alpaca_key:
            alpaca_data = self._fetch_alpaca_snapshot(symbol)
            if alpaca_data:
                price_data.update(self._parse_alpaca_price(alpaca_data))
                price_data['source'] = 'alpaca'
        
        # 3. Try Polygon (if API key available)
        if price_data['source'] == 'unknown' and self.polygon_key:
            poly_snap = self._fetch_polygon_snapshot(symbol)
            if poly_snap:
                price_data.update(self._parse_polygon_price(poly_snap))
                price_data['source'] = 'polygon'
        
        # 4. Try Alpha Vantage as LAST RESORT (rate limited - 5 calls per minute)
        if price_data['source'] == 'unknown':
            av_quote = self._fetch_alpha_vantage_quote(symbol)
            if av_quote:
                price_data.update(self._parse_alpha_vantage_price(av_quote))
                price_data['source'] = 'alpha_vantage'
        
        self._set_cache(cache_key, price_data)
        return price_data
    
    def _parse_alpaca_price(self, data: Dict) -> Dict:
        """Parse Alpaca snapshot data"""
        price_info = {}
        try:
            latest_trade = data.get('latestTrade', {})
            latest_quote = data.get('latestQuote', {})
            prev_close = data.get('prevDailyBar', {})
            
            price_info['price'] = latest_trade.get('p', 0)
            price_info['bid'] = latest_quote.get('bp', 0)
            price_info['ask'] = latest_quote.get('ap', 0)
            price_info['volume'] = latest_trade.get('s', 0)
            price_info['timestamp'] = latest_trade.get('t', '')
            
            if prev_close:
                prev_price = prev_close.get('c', 0)
                if prev_price > 0:
                    price_info['change'] = price_info['price'] - prev_price
                    price_info['change_percent'] = (price_info['change'] / prev_price) * 100
        except Exception as e:
            print(f"Error parsing Alpaca price: {str(e)}")
        
        return price_info
    
    def _parse_alpha_vantage_price(self, data: Dict) -> Dict:
        """Parse Alpha Vantage quote data"""
        price_info = {}
        try:
            price_info['price'] = float(data.get('05. price', 0))
            price_info['volume'] = int(data.get('06. volume', 0))
            price_info['previous_close'] = float(data.get('08. previous close', 0))
            price_info['change'] = float(data.get('09. change', 0))
            price_info['change_percent'] = float(data.get('10. change percent', '0').replace('%', ''))
            price_info['timestamp'] = data.get('07. latest trading day', '')
        except Exception as e:
            print(f"Error parsing Alpha Vantage price: {str(e)}")
        
        return price_info
    
    def _parse_polygon_price(self, data: Dict) -> Dict:
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
    
    def _parse_yfinance_price(self, data: Dict) -> Dict:
        """Parse Yahoo Finance price data"""
        price_info = {}
        try:
            price_data = data.get('price', {})
            
            def get_value(obj, default=0):
                if isinstance(obj, dict):
                    return obj.get('raw', default)
                return obj or default
            
            price_info['price'] = get_value(price_data.get('regularMarketPrice'), 0)
            price_info['open'] = get_value(price_data.get('regularMarketOpen'), 0)
            price_info['high'] = get_value(price_data.get('regularMarketDayHigh'), 0)
            price_info['low'] = get_value(price_data.get('regularMarketDayLow'), 0)
            price_info['volume'] = get_value(price_data.get('regularMarketVolume'), 0)
            price_info['previous_close'] = get_value(price_data.get('regularMarketPreviousClose'), 0)
            price_info['change'] = get_value(price_data.get('regularMarketChange'), 0)
            price_info['change_percent'] = get_value(price_data.get('regularMarketChangePercent'), 0)
        except Exception as e:
            print(f"Error parsing Yahoo Finance price: {str(e)}")
        
        return price_info
    
    def get_analyst_estimates(self, symbol: str) -> Dict:
        """
        Get analyst estimates for earnings and revenue
        Priority: Yahoo Finance (free, unlimited) > Alpha Vantage (rate limited)
        """
        cache_key = self._get_cache_key('estimates', symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        estimates = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'earnings_estimates': [],
            'revenue_estimates': [],
            'source': 'unknown'
        }
        
        # Try Yahoo Finance FIRST (best free source for estimates, no rate limits)
        yf_data = self._fetch_yfinance_data(symbol)
        if yf_data and 'earningsTrend' in yf_data:
            estimates.update(self._parse_yfinance_estimates(yf_data))
            estimates['source'] = 'yahoo_finance'
        
        # Fallback to Alpha Vantage earnings (rate limited - 5 calls/minute)
        if estimates['source'] == 'unknown':
            av_earnings = self._fetch_alpha_vantage_earnings(symbol)
            if av_earnings:
                estimates.update(self._parse_alpha_vantage_estimates(av_earnings))
                estimates['source'] = 'alpha_vantage'
        
        self._set_cache(cache_key, estimates)
        return estimates
    
    def _fetch_alpha_vantage_earnings(self, symbol: str) -> Optional[Dict]:
        """Fetch earnings data from Alpha Vantage"""
        try:
            params = {
                'function': 'EARNINGS',
                'symbol': symbol,
                'apikey': self.alpha_vantage_key
            }
            
            response = requests.get(self.alpha_vantage_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data
            return None
        except Exception as e:
            print(f"Alpha Vantage earnings error for {symbol}: {str(e)}")
            return None
    
    def _parse_yfinance_estimates(self, data: Dict) -> Dict:
        """Parse Yahoo Finance analyst estimates"""
        estimates = {}
        try:
            earnings_trend = data.get('earningsTrend', {}).get('trend', [])
            
            earnings_list = []
            revenue_list = []
            
            for trend in earnings_trend:
                period = trend.get('period', '')
                
                # Earnings estimates
                earnings_est = trend.get('earningsEstimate', {})
                if earnings_est:
                    earnings_list.append({
                        'period': period,
                        'avg': earnings_est.get('avg', {}).get('raw', 0),
                        'low': earnings_est.get('low', {}).get('raw', 0),
                        'high': earnings_est.get('high', {}).get('raw', 0),
                        'num_analysts': earnings_est.get('numberOfAnalysts', {}).get('raw', 0)
                    })
                
                # Revenue estimates
                revenue_est = trend.get('revenueEstimate', {})
                if revenue_est:
                    revenue_list.append({
                        'period': period,
                        'avg': revenue_est.get('avg', {}).get('raw', 0),
                        'low': revenue_est.get('low', {}).get('raw', 0),
                        'high': revenue_est.get('high', {}).get('raw', 0),
                        'num_analysts': revenue_est.get('numberOfAnalysts', {}).get('raw', 0)
                    })
            
            estimates['earnings_estimates'] = earnings_list
            estimates['revenue_estimates'] = revenue_list
            
        except Exception as e:
            print(f"Error parsing Yahoo Finance estimates: {str(e)}")
        
        return estimates
    
    def _parse_alpha_vantage_estimates(self, data: Dict) -> Dict:
        """Parse Alpha Vantage earnings data"""
        estimates = {}
        try:
            quarterly_earnings = data.get('quarterlyEarnings', [])
            
            earnings_list = []
            for quarter in quarterly_earnings[:4]:  # Last 4 quarters
                earnings_list.append({
                    'period': quarter.get('fiscalDateEnding', ''),
                    'reported_eps': float(quarter.get('reportedEPS', 0)),
                    'estimated_eps': float(quarter.get('estimatedEPS', 0)),
                    'surprise': float(quarter.get('surprise', 0)),
                    'surprise_percent': float(quarter.get('surprisePercentage', 0))
                })
            
            estimates['earnings_estimates'] = earnings_list
            
        except Exception as e:
            print(f"Error parsing Alpha Vantage estimates: {str(e)}")
        
        return estimates
    
    def get_financial_statements(self, symbol: str) -> Dict:
        """Get financial statements for a stock"""
        # Placeholder implementation
        return {
            'symbol': symbol,
            'financials': {
                'revenue': 'N/A',
                'net_income': 'N/A',
                'total_assets': 'N/A',
                'total_liabilities': 'N/A'
            },
            'last_updated': datetime.now().isoformat()
        }

    def get_stock_factors(self, symbol: str) -> Dict:
        """Get factor scores for a stock"""
        # Placeholder implementation
        return {
            'symbol': symbol,
            'factors': {
                'value': 0.5,
                'growth': 0.6,
                'quality': 0.7,
                'momentum': 0.4,
                'volatility': 0.3
            },
            'last_updated': datetime.now().isoformat()
        }

    def get_stock_news(self, symbol: str) -> Dict:
        """Get news for a stock"""
        # Placeholder implementation
        return {
            'symbol': symbol,
            'news': [
                {
                    'title': f'Latest news about {symbol}',
                    'url': '#',
                    'published_date': datetime.now().isoformat(),
                    'source': 'News API'
                }
            ],
            'last_updated': datetime.now().isoformat()
        }

    def get_financial_statements(self, symbol: str) -> Dict:
        """
        Get financial statements (income statement, balance sheet, cash flow)
        Priority: Yahoo Finance (free, unlimited) > Alpha Vantage (rate limited)
        """
        cache_key = self._get_cache_key('financials', symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        financials = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'income_statement': [],
            'balance_sheet': [],
            'cash_flow': [],
            'source': 'unknown'
        }
        
        # Try Yahoo Finance FIRST (free, no rate limits)
        # Note: _fetch_yfinance_data() now fetches ALL modules including financials in one call
        yf_data = self._fetch_yfinance_data(symbol)
        if yf_data:
            financials.update(self._parse_yfinance_financials(yf_data))
            financials['source'] = 'yahoo_finance'
        
        # Fallback to Alpha Vantage ONLY if Yahoo fails (rate limited - 5 calls/minute)
        # Note: This makes 3 API calls sequentially, consuming 3/5 of the per-minute quota
        if financials['source'] == 'unknown':
            av_income = self._fetch_alpha_vantage_income_statement(symbol)
            av_balance = self._fetch_alpha_vantage_balance_sheet(symbol)
            av_cashflow = self._fetch_alpha_vantage_cash_flow(symbol)
            
            if av_income or av_balance or av_cashflow:
                if av_income:
                    financials['income_statement'] = self._parse_alpha_vantage_income(av_income)
                if av_balance:
                    financials['balance_sheet'] = self._parse_alpha_vantage_balance(av_balance)
                if av_cashflow:
                    financials['cash_flow'] = self._parse_alpha_vantage_cashflow(av_cashflow)
                financials['source'] = 'alpha_vantage'
        
        self._set_cache(cache_key, financials)
        return financials
    
    def _fetch_alpha_vantage_income_statement(self, symbol: str) -> Optional[Dict]:
        """Fetch income statement from Alpha Vantage"""
        try:
            params = {
                'function': 'INCOME_STATEMENT',
                'symbol': symbol,
                'apikey': self.alpha_vantage_key
            }
            response = requests.get(self.alpha_vantage_url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Alpha Vantage income statement error: {str(e)}")
            return None
    
    def _fetch_alpha_vantage_balance_sheet(self, symbol: str) -> Optional[Dict]:
        """Fetch balance sheet from Alpha Vantage"""
        try:
            params = {
                'function': 'BALANCE_SHEET',
                'symbol': symbol,
                'apikey': self.alpha_vantage_key
            }
            response = requests.get(self.alpha_vantage_url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Alpha Vantage balance sheet error: {str(e)}")
            return None
    
    def _fetch_alpha_vantage_cash_flow(self, symbol: str) -> Optional[Dict]:
        """Fetch cash flow from Alpha Vantage"""
        try:
            params = {
                'function': 'CASH_FLOW',
                'symbol': symbol,
                'apikey': self.alpha_vantage_key
            }
            response = requests.get(self.alpha_vantage_url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Alpha Vantage cash flow error: {str(e)}")
            return None
    
    def _parse_alpha_vantage_income(self, data: Dict) -> List[Dict]:
        """Parse Alpha Vantage income statement"""
        statements = []
        try:
            annual_reports = data.get('annualReports', [])
            for report in annual_reports[:5]:  # Last 5 years
                statements.append({
                    'fiscal_date': report.get('fiscalDateEnding', ''),
                    'revenue': int(report.get('totalRevenue', 0)),
                    'cost_of_revenue': int(report.get('costOfRevenue', 0)),
                    'gross_profit': int(report.get('grossProfit', 0)),
                    'operating_expenses': int(report.get('operatingExpenses', 0)),
                    'operating_income': int(report.get('operatingIncome', 0)),
                    'net_income': int(report.get('netIncome', 0)),
                    'ebitda': int(report.get('ebitda', 0)),
                    'eps': float(report.get('eps', 0))
                })
        except Exception as e:
            print(f"Error parsing income statement: {str(e)}")
        return statements
    
    def _parse_alpha_vantage_balance(self, data: Dict) -> List[Dict]:
        """Parse Alpha Vantage balance sheet"""
        statements = []
        try:
            annual_reports = data.get('annualReports', [])
            for report in annual_reports[:5]:
                statements.append({
                    'fiscal_date': report.get('fiscalDateEnding', ''),
                    'total_assets': int(report.get('totalAssets', 0)),
                    'current_assets': int(report.get('totalCurrentAssets', 0)),
                    'total_liabilities': int(report.get('totalLiabilities', 0)),
                    'current_liabilities': int(report.get('totalCurrentLiabilities', 0)),
                    'shareholders_equity': int(report.get('totalShareholderEquity', 0)),
                    'cash': int(report.get('cashAndCashEquivalentsAtCarryingValue', 0)),
                    'debt': int(report.get('shortLongTermDebtTotal', 0))
                })
        except Exception as e:
            print(f"Error parsing balance sheet: {str(e)}")
        return statements
    
    def _parse_alpha_vantage_cashflow(self, data: Dict) -> List[Dict]:
        """Parse Alpha Vantage cash flow statement"""
        statements = []
        try:
            annual_reports = data.get('annualReports', [])
            for report in annual_reports[:5]:
                statements.append({
                    'fiscal_date': report.get('fiscalDateEnding', ''),
                    'operating_cashflow': int(report.get('operatingCashflow', 0)),
                    'capex': int(report.get('capitalExpenditures', 0)),
                    'free_cash_flow': int(report.get('operatingCashflow', 0)) - abs(int(report.get('capitalExpenditures', 0))),
                    'dividends_paid': int(report.get('dividendPayout', 0))
                })
        except Exception as e:
            print(f"Error parsing cash flow: {str(e)}")
        return statements
    
    def _fetch_yfinance_financials(self, symbol: str) -> Optional[Dict]:
        """
        Fetch financial statements from Yahoo Finance
        DEPRECATED: Now uses unified _fetch_yfinance_data() method
        """
        # Use unified fetch method with all modules
        return self._fetch_yfinance_data(symbol)
    
    def _parse_yfinance_financials(self, data: Dict) -> Dict:
        """Parse Yahoo Finance financial statements"""
        parsed = {}
        
        try:
            # Income Statement
            income_history = data.get('incomeStatementHistory', {}).get('incomeStatementHistory', [])
            income_statements = []
            for statement in income_history:
                stmt = statement.get('incomeStatement', {})
                income_statements.append({
                    'fiscal_date': statement.get('endDate', {}).get('fmt', ''),
                    'revenue': stmt.get('totalRevenue', {}).get('raw', 0),
                    'cost_of_revenue': stmt.get('costOfRevenue', {}).get('raw', 0),
                    'gross_profit': stmt.get('grossProfit', {}).get('raw', 0),
                    'operating_income': stmt.get('operatingIncome', {}).get('raw', 0),
                    'net_income': stmt.get('netIncome', {}).get('raw', 0),
                    'ebitda': stmt.get('ebitda', {}).get('raw', 0)
                })
            parsed['income_statement'] = income_statements
            
            # Balance Sheet
            balance_history = data.get('balanceSheetHistory', {}).get('balanceSheetStatements', [])
            balance_statements = []
            for statement in balance_history:
                stmt = statement.get('balanceSheet', {})
                balance_statements.append({
                    'fiscal_date': statement.get('endDate', {}).get('fmt', ''),
                    'total_assets': stmt.get('totalAssets', {}).get('raw', 0),
                    'current_assets': stmt.get('totalCurrentAssets', {}).get('raw', 0),
                    'total_liabilities': stmt.get('totalLiab', {}).get('raw', 0),
                    'current_liabilities': stmt.get('totalCurrentLiabilities', {}).get('raw', 0),
                    'shareholders_equity': stmt.get('totalStockholderEquity', {}).get('raw', 0),
                    'cash': stmt.get('cash', {}).get('raw', 0)
                })
            parsed['balance_sheet'] = balance_statements
            
            # Cash Flow
            cashflow_history = data.get('cashflowStatementHistory', {}).get('cashflowStatements', [])
            cashflow_statements = []
            for statement in cashflow_history:
                stmt = statement.get('cashflowStatement', {})
                operating_cf = stmt.get('totalCashFromOperatingActivities', {}).get('raw', 0)
                capex = stmt.get('capitalExpenditures', {}).get('raw', 0)
                cashflow_statements.append({
                    'fiscal_date': statement.get('endDate', {}).get('fmt', ''),
                    'operating_cashflow': operating_cf,
                    'capex': capex,
                    'free_cash_flow': operating_cf - abs(capex),
                    'dividends_paid': stmt.get('dividendsPaid', {}).get('raw', 0)
                })
            parsed['cash_flow'] = cashflow_statements
            
        except Exception as e:
            print(f"Error parsing Yahoo Finance financials: {str(e)}")
        
        return parsed
    
    # ========================================================================
    # ASYNC BATCH METHODS FOR CONCURRENT MULTI-STOCK OPERATIONS
    # ========================================================================
    
    async def _fetch_yfinance_data_async(self, session: aiohttp.ClientSession, symbol: str, modules: str = None) -> tuple:
        """
        Async version of _fetch_yfinance_data for concurrent requests
        Returns: (symbol, data) tuple
        """
        try:
            url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
            
            if modules is None:
                modules = 'price,summaryDetail,defaultKeyStatistics,financialData,earningsTrend,incomeStatementHistory,balanceSheetHistory,cashflowStatementHistory'
            
            params = {'modules': modules}
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get('quoteSummary', {}).get('result', [])
                    if result:
                        return (symbol, result[0])
            return (symbol, None)
        except Exception as e:
            print(f"YFinance async error for {symbol}: {str(e)}")
            return (symbol, None)
    
    async def get_multiple_stock_prices_async(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Fetch stock prices for multiple symbols concurrently using Yahoo Finance
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to price data
            
        Example:
            api = StockDataAPI()
            prices = await api.get_multiple_stock_prices_async(['AAPL', 'MSFT', 'GOOGL'])
        """
        results = {}
        
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_yfinance_data_async(session, symbol) for symbol in symbols]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for item in responses:
                if isinstance(item, Exception):
                    print(f"Error in batch request: {str(item)}")
                    continue
                    
                symbol, data = item
                if data:
                    price_data = {
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'yahoo_finance'
                    }
                    price_data.update(self._parse_yfinance_price(data))
                    results[symbol] = price_data
                    
                    # Cache the result
                    cache_key = self._get_cache_key('price', symbol)
                    self._set_cache(cache_key, price_data)
                else:
                    results[symbol] = {
                        'symbol': symbol,
                        'error': 'Failed to fetch data',
                        'timestamp': datetime.now().isoformat()
                    }
        
        return results
    
    async def get_multiple_stock_metrics_async(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Fetch stock metrics for multiple symbols concurrently using Yahoo Finance
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to metrics data
        """
        results = {}
        
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_yfinance_data_async(session, symbol) for symbol in symbols]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for item in responses:
                if isinstance(item, Exception):
                    print(f"Error in batch request: {str(item)}")
                    continue
                    
                symbol, data = item
                if data:
                    metrics = {
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'yahoo_finance'
                    }
                    metrics.update(self._parse_yfinance_metrics(data))
                    results[symbol] = metrics
                    
                    # Cache the result
                    cache_key = self._get_cache_key('metrics', symbol)
                    self._set_cache(cache_key, metrics)
                else:
                    results[symbol] = {
                        'symbol': symbol,
                        'error': 'Failed to fetch data',
                        'timestamp': datetime.now().isoformat()
                    }
        
        return results
    
    def get_multiple_stock_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Synchronous wrapper for async batch price fetching
        Use this in Lambda or synchronous contexts
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to price data
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_multiple_stock_prices_async(symbols))
    
    def get_multiple_stock_metrics(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Synchronous wrapper for async batch metrics fetching
        Use this in Lambda or synchronous contexts
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to metrics data
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_multiple_stock_metrics_async(symbols))
    
    async def get_multiple_analyst_estimates_async(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Fetch analyst estimates for multiple symbols concurrently using Yahoo Finance
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to estimates data
        """
        results = {}
        
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_yfinance_data_async(session, symbol) for symbol in symbols]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for item in responses:
                if isinstance(item, Exception):
                    print(f"Error in batch request: {str(item)}")
                    continue
                    
                symbol, data = item
                if data and 'earningsTrend' in data:
                    estimates = {
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'earnings_estimates': [],
                        'revenue_estimates': [],
                        'source': 'yahoo_finance'
                    }
                    estimates.update(self._parse_yfinance_estimates(data))
                    results[symbol] = estimates
                    
                    # Cache the result
                    cache_key = self._get_cache_key('estimates', symbol)
                    self._set_cache(cache_key, estimates)
                else:
                    results[symbol] = {
                        'symbol': symbol,
                        'error': 'Failed to fetch data',
                        'timestamp': datetime.now().isoformat()
                    }
        
        return results
    
    async def get_multiple_financial_statements_async(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Fetch financial statements for multiple symbols concurrently using Yahoo Finance
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to financial statements data
        """
        results = {}
        
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_yfinance_data_async(session, symbol) for symbol in symbols]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for item in responses:
                if isinstance(item, Exception):
                    print(f"Error in batch request: {str(item)}")
                    continue
                    
                symbol, data = item
                if data:
                    financials = {
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'income_statement': [],
                        'balance_sheet': [],
                        'cash_flow': [],
                        'source': 'yahoo_finance'
                    }
                    financials.update(self._parse_yfinance_financials(data))
                    results[symbol] = financials
                    
                    # Cache the result
                    cache_key = self._get_cache_key('financials', symbol)
                    self._set_cache(cache_key, financials)
                else:
                    results[symbol] = {
                        'symbol': symbol,
                        'error': 'Failed to fetch data',
                        'timestamp': datetime.now().isoformat()
                    }
        
        return results
    
    def get_multiple_analyst_estimates(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Synchronous wrapper for async batch estimates fetching
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to estimates data
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_multiple_analyst_estimates_async(symbols))
    
    def get_multiple_financial_statements(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Synchronous wrapper for async batch financial statements fetching
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to financial statements data
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_multiple_financial_statements_async(symbols))


def lambda_handler(event, context):
    """
    AWS Lambda handler for stock data API
    
    Single stock endpoints:
        /api/stock/metrics?symbol=AAPL
        /api/stock/price?symbol=AAPL
        /api/stock/estimates?symbol=AAPL
        /api/stock/financials?symbol=AAPL
        /api/stock/factors?symbol=AAPL
        /api/stock/news?symbol=AAPL
    
    Batch endpoints (NEW):
        /api/stock/batch/prices?symbols=AAPL,MSFT,GOOGL
        /api/stock/batch/metrics?symbols=AAPL,MSFT,GOOGL
        /api/stock/batch/estimates?symbols=AAPL,MSFT,GOOGL
        /api/stock/batch/financials?symbols=AAPL,MSFT,GOOGL
    """
    
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': ''
        }
    
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    query_params = event.get('queryStringParameters') or {}
    
    # Initialize API
    api = StockDataAPI()
    
    try:
        # Check if this is a batch request
        if '/batch/' in path:
            # Batch endpoints - require 'symbols' parameter (comma-separated)
            symbols_param = query_params.get('symbols', '')
            if not symbols_param:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'error': 'Symbols parameter is required (comma-separated list)'})
                }
            
            # Parse comma-separated symbols
            symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
            
            if not symbols:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'error': 'At least one symbol is required'})
                }
            
            # Limit batch size to prevent abuse
            if len(symbols) > 50:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'error': 'Maximum 50 symbols per batch request'})
                }
            
            # Route to appropriate batch handler
            if '/batch/prices' in path or '/batch/price' in path:
                result = api.get_multiple_stock_prices(symbols)
            elif '/batch/metrics' in path:
                result = api.get_multiple_stock_metrics(symbols)
            elif '/batch/estimates' in path:
                result = api.get_multiple_analyst_estimates(symbols)
            elif '/batch/financials' in path:
                result = api.get_multiple_financial_statements(symbols)
            else:
                result = {'error': 'Invalid batch endpoint'}
        
        else:
            # Single stock endpoints - require 'symbol' parameter
            symbol = query_params.get('symbol', '').upper()
            
            if not symbol:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'error': 'Symbol parameter is required'})
                }
            
            # Route to appropriate single stock handler
            if '/metrics' in path:
                result = api.get_stock_metrics(symbol)
            elif '/price' in path:
                result = api.get_stock_price(symbol)
            elif '/estimates' in path:
                result = api.get_analyst_estimates(symbol)
            elif '/financials' in path:
                result = api.get_financial_statements(symbol)
            elif '/factors' in path:
                result = api.get_stock_factors(symbol)
            elif '/news' in path:
                result = api.get_stock_news(symbol)
            else:
                result = {'error': 'Invalid endpoint'}
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(result, default=decimal_default)
        }
    
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


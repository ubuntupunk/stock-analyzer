"""
Stock Data API - Main Orchestrator
Coordinates multiple API clients with fallback mechanisms
"""

import json
import os
import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal

from api_clients import YahooFinanceClient, AlphaVantageClient, PolygonClient, AlpacaClient


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
        # Initialize API clients
        self.yahoo = YahooFinanceClient()
        self.alpha_vantage = AlphaVantageClient()
        self.polygon = PolygonClient()
        self.alpaca = AlpacaClient()
        
        # Cache for reducing API calls
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
    
    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================
    
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
    
    # ========================================================================
    # SINGLE STOCK METHODS
    # ========================================================================
    
    def get_stock_price(self, symbol: str, period: str = '1mo', startDate: str = None, endDate: str = None) -> Dict:
        """
        Get current stock price and basic quote information
        Priority: Yahoo Finance (free) > Alpaca > Polygon > Alpha Vantage (rate limited)
        Also includes historical data for charting
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            period: Historical data period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
            startDate: Custom start date (YYYY-MM-DD) - takes precedence over period
            endDate: Custom end date (YYYY-MM-DD)
        """
        # Cache key includes period since different periods return different data
        # Use startDate for cache key when using custom range
        cache_key = self._get_cache_key(f'price:{period}:{startDate or "default"}', symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        price_data = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'source': 'unknown'
        }
        
        # 1. Try Yahoo Finance first
        yf_data = self.yahoo.fetch_data(symbol)
        if yf_data:
            price_data.update(self.yahoo.parse_price(yf_data))
            price_data['source'] = 'yahoo_finance'
        
        # 2. Fetch historical data for charting (support custom date range)
        if startDate and endDate:
            history = self.yahoo.fetch_history_range(symbol, startDate, endDate)
        else:
            history = self.yahoo.fetch_history(symbol, period)
        if history:
            price_data['historicalData'] = history
        
        # 3. Try Alpaca
        if price_data['source'] == 'unknown' and self.alpaca.api_key:
            alpaca_data = self.alpaca.fetch_snapshot(symbol)
            if alpaca_data:
                price_data.update(self.alpaca.parse_price(alpaca_data))
                price_data['source'] = 'alpaca'
        
        # 4. Try Polygon
        if price_data['source'] == 'unknown' and self.polygon.api_key:
            poly_snap = self.polygon.fetch_snapshot(symbol)
            if poly_snap:
                price_data.update(self.polygon.parse_price(poly_snap))
                price_data['source'] = 'polygon'
        
        # 5. Try Alpha Vantage as LAST RESORT
        if price_data['source'] == 'unknown':
            av_quote = self.alpha_vantage.fetch_quote(symbol)
            if av_quote:
                price_data.update(self.alpha_vantage.parse_price(av_quote))
                price_data['source'] = 'alpha_vantage'
        
        self._set_cache(cache_key, price_data)
        return price_data
    
    def get_stock_metrics(self, symbol: str) -> Dict:
        """
        Get comprehensive stock metrics
        Priority: Yahoo Finance > Alpha Vantage > Polygon
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
        
        # Try Yahoo Finance FIRST
        yf_data = self.yahoo.fetch_data(symbol)
        if yf_data:
            metrics.update(self.yahoo.parse_metrics(yf_data))
            metrics['source'] = 'yahoo_finance'
        
        # Fallback to Alpha Vantage
        if metrics['source'] == 'unknown':
            av_data = self.alpha_vantage.fetch_overview(symbol)
            if av_data:
                metrics.update(self.alpha_vantage.parse_metrics(av_data))
                metrics['source'] = 'alpha_vantage'
        
        # Enhance with Polygon data if available
        if self.polygon.api_key:
            poly_data = self.polygon.fetch_ticker(symbol)
            if poly_data:
                metrics.update(self.polygon.parse_metrics(poly_data))
                if metrics['source'] == 'unknown':
                    metrics['source'] = 'polygon'
        
        self._set_cache(cache_key, metrics)
        return metrics
    
    def get_analyst_estimates(self, symbol: str) -> Dict:
        """
        Get analyst estimates for earnings and revenue
        Priority: Yahoo Finance > Alpha Vantage
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
        
        # Try Yahoo Finance FIRST
        yf_data = self.yahoo.fetch_data(symbol)
        if yf_data and 'earningsTrend' in yf_data:
            estimates.update(self.yahoo.parse_estimates(yf_data))
            estimates['source'] = 'yahoo_finance'
        
        # Fallback to Alpha Vantage
        if estimates['source'] == 'unknown':
            av_earnings = self.alpha_vantage.fetch_earnings(symbol)
            if av_earnings:
                estimates.update(self.alpha_vantage.parse_estimates(av_earnings))
                estimates['source'] = 'alpha_vantage'
        
        self._set_cache(cache_key, estimates)
        return estimates
    
    def get_financial_statements(self, symbol: str) -> Dict:
        """
        Get financial statements (income statement, balance sheet, cash flow)
        Priority: Yahoo Finance > Alpha Vantage
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
        
        # Try Yahoo Finance FIRST
        yf_data = self.yahoo.fetch_data(symbol)
        if yf_data:
            financials.update(self.yahoo.parse_financials(yf_data))
            financials['source'] = 'yahoo_finance'
        
        # Fallback to Alpha Vantage (makes 3 API calls)
        if financials['source'] == 'unknown':
            av_income = self.alpha_vantage.fetch_income_statement(symbol)
            av_balance = self.alpha_vantage.fetch_balance_sheet(symbol)
            av_cashflow = self.alpha_vantage.fetch_cash_flow(symbol)
            
            if av_income or av_balance or av_cashflow:
                if av_income:
                    financials['income_statement'] = self.alpha_vantage.parse_income(av_income)
                if av_balance:
                    financials['balance_sheet'] = self.alpha_vantage.parse_balance(av_balance)
                if av_cashflow:
                    financials['cash_flow'] = self.alpha_vantage.parse_cashflow(av_cashflow)
                financials['source'] = 'alpha_vantage'
        
        self._set_cache(cache_key, financials)
        return financials
    
    def get_stock_factors(self, symbol: str) -> Dict:
        """Get factor scores for a stock"""
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
    
    # ========================================================================
    # ASYNC BATCH METHODS
    # ========================================================================
    
    async def get_multiple_stock_prices_async(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch stock prices for multiple symbols concurrently"""
        results = {}
        print(f"get_multiple_stock_prices_async: Fetching prices for {symbols}")

        async with aiohttp.ClientSession() as session:
            tasks = [self.yahoo.fetch_data_async(session, symbol) for symbol in symbols]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            print(f"get_multiple_stock_prices_async: Got {len(responses)} responses")

            for item in responses:
                if isinstance(item, Exception):
                    print(f"get_multiple_stock_prices_async: Exception in response: {item}")
                    continue

                symbol, data = item
                print(f"get_multiple_stock_prices_async: Processing {symbol}, data is {'truthy' if data else 'falsy'}")

                if data:
                    price_data = {
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'yahoo_finance'
                    }

                    # Parse the price data
                    parsed = self.yahoo.parse_price(data)
                    print(f"get_multiple_stock_prices_async: Parsed price for {symbol}: {parsed}")

                    if parsed:
                        price_data.update(parsed)
                        results[symbol] = price_data

                        cache_key = self._get_cache_key('price', symbol)
                        self._set_cache(cache_key, price_data)
                    else:
                        # If parsing failed, store error
                        results[symbol] = {
                            'symbol': symbol,
                            'error': 'Failed to parse price data',
                            'timestamp': datetime.now().isoformat()
                        }
                        print(f"get_multiple_stock_prices_async: WARNING - no parsed data for {symbol}")
                else:
                    results[symbol] = {
                        'symbol': symbol,
                        'error': 'Failed to fetch data',
                        'timestamp': datetime.now().isoformat()
                    }
                    print(f"get_multiple_stock_prices_async: WARNING - no data for {symbol}")

        print(f"get_multiple_stock_prices_async: Final results: {results}")
        return results
    
    async def get_multiple_stock_metrics_async(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch stock metrics for multiple symbols concurrently"""
        results = {}
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.yahoo.fetch_data_async(session, symbol) for symbol in symbols]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for item in responses:
                if isinstance(item, Exception):
                    continue
                    
                symbol, data = item
                if data:
                    metrics = {
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'yahoo_finance'
                    }
                    metrics.update(self.yahoo.parse_metrics(data))
                    results[symbol] = metrics
                    
                    cache_key = self._get_cache_key('metrics', symbol)
                    self._set_cache(cache_key, metrics)
                else:
                    results[symbol] = {
                        'symbol': symbol,
                        'error': 'Failed to fetch data',
                        'timestamp': datetime.now().isoformat()
                    }
        
        return results
    
    async def get_multiple_analyst_estimates_async(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch analyst estimates for multiple symbols concurrently"""
        results = {}
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.yahoo.fetch_data_async(session, symbol) for symbol in symbols]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for item in responses:
                if isinstance(item, Exception):
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
                    estimates.update(self.yahoo.parse_estimates(data))
                    results[symbol] = estimates
                    
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
        """Fetch financial statements for multiple symbols concurrently"""
        results = {}
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.yahoo.fetch_data_async(session, symbol) for symbol in symbols]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for item in responses:
                if isinstance(item, Exception):
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
                    financials.update(self.yahoo.parse_financials(data))
                    results[symbol] = financials
                    
                    cache_key = self._get_cache_key('financials', symbol)
                    self._set_cache(cache_key, financials)
                else:
                    results[symbol] = {
                        'symbol': symbol,
                        'error': 'Failed to fetch data',
                        'timestamp': datetime.now().isoformat()
                    }
        
        return results
    
    # ========================================================================
    # SYNCHRONOUS WRAPPERS FOR BATCH METHODS
    # ========================================================================
    
    def get_multiple_stock_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """Synchronous wrapper for batch price fetching"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_multiple_stock_prices_async(symbols))
    
    def get_multiple_stock_metrics(self, symbols: List[str]) -> Dict[str, Dict]:
        """Synchronous wrapper for batch metrics fetching"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_multiple_stock_metrics_async(symbols))
    
    def get_multiple_analyst_estimates(self, symbols: List[str]) -> Dict[str, Dict]:
        """Synchronous wrapper for batch estimates fetching"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_multiple_analyst_estimates_async(symbols))
    
    def get_multiple_financial_statements(self, symbols: List[str]) -> Dict[str, Dict]:
        """Synchronous wrapper for batch financial statements fetching"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_multiple_financial_statements_async(symbols))

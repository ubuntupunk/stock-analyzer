"""
Stock Data API - Main Orchestrator
Coordinates multiple API clients with fallback mechanisms, circuit breaker, and metrics
"""

import json
import os
import asyncio
import aiohttp
import time
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

from api_clients import YahooFinanceClient, AlphaVantageClient, PolygonClient, AlpacaClient
from circuit_breaker import CircuitBreakerManager, get_circuit_breaker


def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


class APIMetrics:
    """Track API performance metrics"""
    
    def __init__(self):
        self.metrics = {
            'requests': {'total': 0, 'success': 0, 'failed': 0},
            'sources': {},
            'latency': {'total_ms': 0, 'count': 0, 'avg_ms': 0},
            'rate_limits': 0,
            'timeouts': 0,
            'errors': {}
        }
        self._lock = asyncio.Lock()
    
    async def record_request(self, source: str, success: bool, latency_ms: float):
        """Record an API request"""
        async with self._lock:
            self.metrics['requests']['total'] += 1
            if success:
                self.metrics['requests']['success'] += 1
            else:
                self.metrics['requests']['failed'] += 1
            
            # Source-specific tracking
            if source not in self.metrics['sources']:
                self.metrics['sources'][source] = {'calls': 0, 'success': 0, 'failed': 0}
            self.metrics['sources'][source]['calls'] += 1
            if success:
                self.metrics['sources'][source]['success'] += 1
            else:
                self.metrics['sources'][source]['failed'] += 1
            
            # Latency tracking
            self.metrics['latency']['total_ms'] += latency_ms
            self.metrics['latency']['count'] += 1
            self.metrics['latency']['avg_ms'] = (
                self.metrics['latency']['total_ms'] / self.metrics['latency']['count']
            )
    
    def record_rate_limit(self, source: str):
        """Record a rate limit hit"""
        self.metrics['rate_limits'] += 1
        if source not in self.metrics['errors']:
            self.metrics['errors'][source] = {'rate_limits': 0, 'timeouts': 0, 'other': 0}
        self.metrics['errors'][source]['rate_limits'] += 1
    
    def record_timeout(self, source: str):
        """Record a timeout"""
        self.metrics['timeouts'] += 1
        if source not in self.metrics['errors']:
            self.metrics['errors'][source] = {'rate_limits': 0, 'timeouts': 0, 'other': 0}
        self.metrics['errors'][source]['timeouts'] += 1
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        return {
            **self.metrics,
            'success_rate': (
                f"{(self.metrics['requests']['success'] / self.metrics['requests']['total'] * 100):.1f}%"
                if self.metrics['requests']['total'] > 0 else "N/A"
            )
        }
    
    def get_source_stats(self, source: str) -> Dict:
        """Get stats for a specific source"""
        if source not in self.metrics['sources']:
            return {'calls': 0, 'success': 0, 'failed': 0}
        
        source_data = self.metrics['sources'][source]
        total = source_data['calls']
        return {
            **source_data,
            'success_rate': f"{(source_data['success'] / total * 100):.1f}%" if total > 0 else "N/A"
        }


class StockDataAPI:
    """
    Multi-source stock data API with fallback mechanisms
    
    Features:
    - Circuit breaker pattern for API resilience
    - Parallel fallback for faster responses
    - API metrics tracking
    - Configurable priorities
    
    API Priority Order (configurable):
    1. Yahoo Finance - FREE, no API key required, no rate limits
    2. Alpaca - Real-time data with free tier, requires API key
    3. Polygon.io - Requires API key, some rate limits
    4. Alpha Vantage - FREE but RATE LIMITED (5 calls/minute on free tier)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        # Configuration
        cfg = config or {}
        self.timeout = cfg.get('timeout', 10)
        
        # Initialize API clients
        self.yahoo = YahooFinanceClient(timeout_seconds=self.timeout)
        self.alpha_vantage = AlphaVantageClient()
        self.polygon = PolygonClient(timeout_seconds=self.timeout)
        self.alpaca = AlpacaClient(timeout_seconds=self.timeout)
        
        # Circuit breaker manager
        self.cb = get_circuit_breaker()
        
        # Metrics tracker
        self.metrics = APIMetrics()
        
        # Cache for reducing API calls
        self.cache = {}
        self.cache_timeout = cfg.get('cache_timeout', 300)  # 5 minutes
        
        # Configurable priorities
        self.priorities = cfg.get('priorities', [
            ('yahoo_finance', 1),
            ('alpaca', 2),
            ('polygon', 3),
            ('alpha_vantage', 4)
        ])
        
        # Thread pool for sync fallback
        self.executor = ThreadPoolExecutor(max_workers=4)
    
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
    # PARALLEL FALLBACK STRATEGY
    # ========================================================================
    
    async def _fetch_parallel(self, symbol: str, data_type: str) -> Optional[Dict]:
        """
        Fetch data from multiple APIs in parallel
        Returns first successful result
        """
        start_time = time.time()

        # Build tasks for enabled sources
        tasks = []
        sources_to_try = []

        for source_name, priority in self.priorities:
            if not self.cb.can_call(source_name):
                print(f"Circuit OPEN for {source_name}, skipping")
                continue

            if source_name == 'yahoo_finance':
                tasks.append(self._fetch_yahoo_price(symbol))
                sources_to_try.append('yahoo_finance')
            elif source_name == 'alpaca' and self.alpaca.api_key:
                tasks.append(self._fetch_alpaca_price(symbol))
                sources_to_try.append('alpaca')
            elif source_name == 'polygon' and self.polygon.api_key:
                tasks.append(self._fetch_polygon_price(symbol))
                sources_to_try.append('polygon')
            elif source_name == 'alpha_vantage':
                tasks.append(self._fetch_alpha_price(symbol))
                sources_to_try.append('alpha_vantage')

        if not tasks:
            print(f"All circuits OPEN for {symbol}")
            return None

        # Wait for first successful result using asyncio.as_completed
        try:
            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    if result:
                        latency_ms = (time.time() - start_time) * 1000
                        print(f"Parallel fetch succeeded in {latency_ms:.0f}ms")
                        return result
                except Exception as e:
                    print(f"Task failed: {e}")
                    continue
        except Exception as e:
            print(f"Parallel fetch error: {e}")

        # All failed
        return None
    
    async def _fetch_yahoo_price(self, symbol: str) -> Optional[Dict]:
        """Fetch price from Yahoo Finance"""
        try:
            start = time.time()
            data = await asyncio.get_event_loop().run_in_executor(
                self.executor, self.yahoo.fetch_data, symbol
            )
            latency_ms = (time.time() - start) * 1000
            
            if data:
                await self.metrics.record_request('yahoo_finance', True, latency_ms)
                return self.yahoo.parse_price(data)
            else:
                await self.metrics.record_request('yahoo_finance', False, latency_ms)
                return None
        except Exception as e:
            await self.metrics.record_request('yahoo_finance', False, 0)
            self.cb.record_failure('yahoo_finance', type(e).__name__)
            return None
    
    async def _fetch_alpaca_price(self, symbol: str) -> Optional[Dict]:
        """Fetch price from Alpaca"""
        try:
            start = time.time()
            data = await asyncio.get_event_loop().run_in_executor(
                self.executor, self.alpaca.fetch_snapshot, symbol
            )
            latency_ms = (time.time() - start) * 1000
            
            if data:
                await self.metrics.record_request('alpaca', True, latency_ms)
                return self.alpaca.parse_price(data)
            else:
                await self.metrics.record_request('alpaca', False, latency_ms)
                return None
        except Exception as e:
            await self.metrics.record_request('alpaca', False, 0)
            self.cb.record_failure('alpaca', type(e).__name__)
            return None
    
    async def _fetch_polygon_price(self, symbol: str) -> Optional[Dict]:
        """Fetch price from Polygon"""
        try:
            start = time.time()
            data = await asyncio.get_event_loop().run_in_executor(
                self.executor, self.polygon.fetch_snapshot, symbol
            )
            latency_ms = (time.time() - start) * 1000
            
            if data:
                await self.metrics.record_request('polygon', True, latency_ms)
                return self.polygon.parse_price(data)
            else:
                await self.metrics.record_request('polygon', False, latency_ms)
                return None
        except Exception as e:
            await self.metrics.record_request('polygon', False, 0)
            self.cb.record_failure('polygon', type(e).__name__)
            return None
    
    async def _fetch_alpha_price(self, symbol: str) -> Optional[Dict]:
        """Fetch price from Alpha Vantage"""
        try:
            start = time.time()
            data = await asyncio.get_event_loop().run_in_executor(
                self.executor, self.alpha_vantage.fetch_quote, symbol
            )
            latency_ms = (time.time() - start) * 1000
            
            if data and '05. price' in data:
                await self.metrics.record_request('alpha_vantage', True, latency_ms)
                return self.alpha_vantage.parse_price(data)
            else:
                await self.metrics.record_request('alpha_vantage', False, latency_ms)
                return None
        except Exception as e:
            await self.metrics.record_request('alpha_vantage', False, 0)
            self.cb.record_failure('alpha_vantage', type(e).__name__)
            return None
    
    # ========================================================================
    # SINGLE STOCK METHODS
    # ========================================================================
    
    def get_stock_price(self, symbol: str, period: str = '1mo', startDate: str = None, endDate: str = None) -> Dict:
        """
        Get current stock price and basic quote information
        Includes both price data and metrics for comprehensive view
        """
        # Check cache first
        cache_key = self._get_cache_key(f'price:{period}:{startDate or "default"}', symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        price_data = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'source': 'unknown'
        }

        # Get price data from Yahoo Finance FIRST (fastest, most complete)
        try:
            start = time.time()
            yf_data = self.yahoo.fetch_data(symbol)
            latency_ms = (time.time() - start) * 1000

            if yf_data:
                # Parse both price and metrics data from Yahoo Finance
                price_data.update(self.yahoo.parse_price(yf_data))
                price_data.update(self.yahoo.parse_metrics(yf_data))  # Add metrics data
                price_data['source'] = 'yahoo_finance'
                self.metrics.record_request('yahoo_finance', True, latency_ms)
            else:
                self.metrics.record_request('yahoo_finance', False, latency_ms)

        except Exception as e:
            self.metrics.record_request('yahoo_finance', False, 0)
            print(f"Yahoo price/metrics error for {symbol}: {str(e)}")

        # Fallback to other sources if needed
        if price_data['source'] == 'unknown':
            # Try Alpha Vantage
            try:
                start = time.time()
                av_data = self.alpha_vantage.fetch_quote(symbol)
                latency_ms = (time.time() - start) * 1000

                if av_data and '05. price' in av_data:
                    price_data.update(self.alpha_vantage.parse_price(av_data))
                    price_data['source'] = 'alpha_vantage'
                    self.metrics.record_request('alpha_vantage', True, latency_ms)
                else:
                    self.metrics.record_request('alpha_vantage', False, latency_ms)
            except Exception as e:
                self.metrics.record_request('alpha_vantage', False, 0)

        # Also fetch historical data for charting (support custom date range)
        if startDate and endDate:
            history = self.yahoo.fetch_history_range(symbol, startDate, endDate)
        else:
            history = self.yahoo.fetch_history(symbol, period)
        if history:
            price_data['historicalData'] = history

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
        
        # Try Yahoo Finance FIRST (fastest, most complete)
        try:
            start = time.time()
            yf_data = self.yahoo.fetch_data(symbol)
            latency_ms = (time.time() - start) * 1000
            
            if yf_data:
                metrics.update(self.yahoo.parse_metrics(yf_data))
                metrics['source'] = 'yahoo_finance'
                self.metrics.record_request('yahoo_finance', True, latency_ms)
            else:
                self.metrics.record_request('yahoo_finance', False, latency_ms)
                
        except Exception as e:
            self.metrics.record_request('yahoo_finance', False, 0)
            print(f"Yahoo metrics error for {symbol}: {str(e)}")
        
        # Fallback to Alpha Vantage if needed
        if metrics['source'] == 'unknown':
            try:
                start = time.time()
                av_data = self.alpha_vantage.fetch_overview(symbol)
                latency_ms = (time.time() - start) * 1000
                
                if av_data:
                    metrics.update(self.alpha_vantage.parse_metrics(av_data))
                    metrics['source'] = 'alpha_vantage'
                    self.metrics.record_request('alpha_vantage', True, latency_ms)
                else:
                    self.metrics.record_request('alpha_vantage', False, latency_ms)
            except Exception as e:
                self.metrics.record_request('alpha_vantage', False, 0)
        
        # Enhance with Polygon data if available
        if self.polygon.api_key and metrics['source'] == 'unknown':
            try:
                start = time.time()
                poly_data = self.polygon.fetch_ticker(symbol)
                latency_ms = (time.time() - start) * 1000
                
                if poly_data:
                    metrics.update(self.polygon.parse_metrics(poly_data))
                    if metrics['source'] == 'unknown':
                        metrics['source'] = 'polygon'
                    self.metrics.record_request('polygon', True, latency_ms)
                else:
                    self.metrics.record_request('polygon', False, latency_ms)
            except Exception as e:
                self.metrics.record_request('polygon', False, 0)
        
        self._set_cache(cache_key, metrics)
        return metrics
    
    def get_analyst_estimates(self, symbol: str) -> Dict:
        """Get analyst estimates for earnings and revenue"""
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
        try:
            yf_data = self.yahoo.fetch_data(symbol)
            if yf_data and ('earningsTrend' in yf_data or 'targetMeanPrice' in yf_data):
                estimates.update(self.yahoo.parse_estimates(yf_data))
                estimates['source'] = 'yahoo_finance'
        except Exception as e:
            print(f"Yahoo estimates error for {symbol}: {str(e)}")
        
        # Fallback to Alpha Vantage
        if estimates['source'] == 'unknown':
            try:
                av_earnings = self.alpha_vantage.fetch_earnings(symbol)
                if av_earnings:
                    estimates.update(self.alpha_vantage.parse_estimates(av_earnings))
                    estimates['source'] = 'alpha_vantage'
            except Exception as e:
                print(f"Alpha Vantage estimates error for {symbol}: {str(e)}")
        
        self._set_cache(cache_key, estimates)
        return estimates
    
    def get_financial_statements(self, symbol: str) -> Dict:
        """Get financial statements (income statement, balance sheet, cash flow)"""
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
        
        # Try Yahoo Finance with full financial statements
        try:
            yf_financials = self.yahoo.fetch_financials(symbol)
            if yf_financials and (yf_financials.get('income_statement') or 
                                   yf_financials.get('balance_sheet') or 
                                   yf_financials.get('cash_flow')):
                financials.update(self.yahoo.parse_financials(yf_financials))
                financials['source'] = 'yahoo_finance'
        except Exception as e:
            print(f"Yahoo financials error for {symbol}: {str(e)}")
        
        self._set_cache(cache_key, financials)
        return financials

    def get_stock_news(self, symbol: str) -> Dict:
        """
        Get stock news articles

        Uses Yahoo Finance news API

        Returns:
            Dict with news articles list
        """
        cache_key = self._get_cache_key('news', symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        news_data = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'articles': [],
            'source': 'unknown'
        }

        # Try Yahoo Finance
        try:
            start = time.time()
            articles = self.yahoo.fetch_news(symbol)
            latency_ms = (time.time() - start) * 1000

            if articles:
                news_data['articles'] = articles
                news_data['source'] = 'yahoo_finance'
                self.metrics.record_request('yahoo_finance', True, latency_ms)
            else:
                self.metrics.record_request('yahoo_finance', False, latency_ms)
        except Exception as e:
            self.metrics.record_request('yahoo_finance', False, 0)
            print(f"Yahoo news error for {symbol}: {str(e)}")

        self._set_cache(cache_key, news_data)
        return news_data

    def get_stock_factors(self, symbol: str) -> Dict:
        """
        Get stock factors for screening (value, growth, momentum, quality metrics)

        Returns:
            Dict with computed factor values
        """
        cache_key = self._get_cache_key('factors', symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        factors = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'source': 'computed',
            'value_factors': {},
            'growth_factors': {},
            'momentum_factors': {},
            'quality_factors': {}
        }

        # Get metrics first
        try:
            metrics = self.get_stock_metrics(symbol)
            if metrics:
                # Value factors
                factors['value_factors'] = {
                    'pe_ratio': metrics.get('pe_ratio', 0),
                    'forward_pe': metrics.get('forward_pe', 0),
                    'peg_ratio': metrics.get('peg_ratio', 0),
                    'price_to_book': metrics.get('price_to_book', 0),
                    'dividend_yield': metrics.get('dividend_yield', 0)
                }

                # Growth factors
                factors['growth_factors'] = {
                    'revenue_growth': metrics.get('revenue_growth', 0),
                    'earnings_growth': metrics.get('earnings_growth', 0),
                    'eps_growth_5y': 0,  # Would need historical data
                    'revenue_growth_5y': 0  # Would need historical data
                }

                # Quality factors
                factors['quality_factors'] = {
                    'roe': metrics.get('roe', 0),
                    'roa': metrics.get('roa', 0),
                    'profit_margin': metrics.get('profit_margin', 0),
                    'operating_margin': metrics.get('operating_margin', 0),
                    'debt_to_equity': metrics.get('debt_to_equity', 0),
                    'current_ratio': metrics.get('current_ratio', 0)
                }

        except Exception as e:
            print(f"Error computing factors for {symbol}: {str(e)}")

        # Momentum factors require historical price data
        try:
            price_data = self.get_stock_price(symbol, period='1y')
            if price_data and 'historicalData' in price_data:
                hist_data = price_data['historicalData']
                if hist_data:
                    dates = sorted(hist_data.keys())
                    if len(dates) >= 2:
                        # Get first and last prices for momentum calculation
                        first_price = hist_data[dates[0]].get('4. close', 0) if isinstance(hist_data[dates[0]], dict) else 0
                        last_price = hist_data[dates[-1]].get('4. close', 0) if isinstance(hist_data[dates[-1]], dict) else 0

                        if first_price and first_price > 0:
                            # 52-week return (or available period)
                            period_return = ((last_price - first_price) / first_price) * 100
                            factors['momentum_factors'] = {
                                '52_week_return': period_return,
                                'near_52_week_high': 0,  # Would need more data
                                'near_52_week_low': 0  # Would need more data
                            }
        except Exception as e:
            print(f"Error computing momentum factors for {symbol}: {str(e)}")

        self._set_cache(cache_key, factors)
        return factors

    def get_all_data(self, symbol: str) -> Dict:
        """
        Get all available stock data from multiple sources
        
        This is the main entry point for fetching comprehensive stock data.
        It tries multiple sources and combines the results.
        """
        data = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'source': 'unknown'
        }
        
        # Get price data
        try:
            price = self.get_stock_price(symbol)
            if price:
                data['price'] = price
        except Exception as e:
            print(f"Error fetching price for {symbol}: {str(e)}")
        
        # Get metrics
        try:
            metrics = self.get_stock_metrics(symbol)
            if metrics:
                data['metrics'] = metrics
        except Exception as e:
            print(f"Error fetching metrics for {symbol}: {str(e)}")
        
        # Get analyst estimates
        try:
            estimates = self.get_analyst_estimates(symbol)
            if estimates and estimates.get('earnings_estimates'):
                data['estimates'] = estimates
        except Exception as e:
            print(f"Error fetching estimates for {symbol}: {str(e)}")
        
        # Get financials
        try:
            financials = self.get_financial_statements(symbol)
            if financials and (financials.get('income_statement') or 
                              financials.get('balance_sheet')):
                data['financials'] = financials
        except Exception as e:
            print(f"Error fetching financials for {symbol}: {str(e)}")
        
        # Add cache metadata
        data['cached'] = False
        
        return data

    def get_batch_prices(self, symbols: List[str]) -> Dict:
        """Get prices for multiple symbols concurrently"""
        results = {}
        for symbol in symbols:
            try:
                price = self.get_stock_price(symbol)
                if price:
                    results[symbol] = price
                else:
                    results[symbol] = {'symbol': symbol, 'error': 'No data'}
            except Exception as e:
                results[symbol] = {'symbol': symbol, 'error': str(e)}
        return results

    def get_batch_metrics(self, symbols: List[str]) -> Dict:
        """Get metrics for multiple symbols concurrently"""
        results = {}
        for symbol in symbols:
            try:
                metrics = self.get_stock_metrics(symbol)
                if metrics:
                    results[symbol] = metrics
                else:
                    results[symbol] = {'symbol': symbol, 'error': 'No data'}
            except Exception as e:
                results[symbol] = {'symbol': symbol, 'error': str(e)}
        return results

    def get_batch_estimates(self, symbols: List[str]) -> Dict:
        """Get analyst estimates for multiple symbols concurrently"""
        results = {}
        for symbol in symbols:
            try:
                estimates = self.get_analyst_estimates(symbol)
                if estimates:
                    results[symbol] = estimates
                else:
                    results[symbol] = {'symbol': symbol, 'error': 'No data'}
            except Exception as e:
                results[symbol] = {'symbol': symbol, 'error': str(e)}
        return results

    def get_batch_financials(self, symbols: List[str]) -> Dict:
        """Get financials for multiple symbols concurrently"""
        results = {}
        for symbol in symbols:
            try:
                financials = self.get_financial_statements(symbol)
                if financials:
                    results[symbol] = financials
                else:
                    results[symbol] = {'symbol': symbol, 'error': 'No data'}
            except Exception as e:
                results[symbol] = {'symbol': symbol, 'error': str(e)}
        return results


def lambda_handler(event, context):
    """
    AWS Lambda handler for stock API requests
    """
    try:
        # Parse request
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        params = event.get('queryStringParameters') or {}
        body = event.get('body')
        
        # Create API instance
        api = StockDataAPI()
        
        # Route request
        if http_method == 'GET':
            if '/metrics' in path:
                symbol = params.get('symbol')
                if not symbol:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'symbol required'})}
                result = api.get_stock_metrics(symbol)
                return {'statusCode': 200, 'body': json.dumps(result, default=decimal_default)}
            
            elif '/price' in path:
                symbol = params.get('symbol')
                if not symbol:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'symbol required'})}
                period = params.get('period', '1mo')
                result = api.get_stock_price(symbol, period)
                return {'statusCode': 200, 'body': json.dumps(result, default=decimal_default)}
            
            elif '/estimates' in path:
                symbol = params.get('symbol')
                if not symbol:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'symbol required'})}
                result = api.get_analyst_estimates(symbol)
                return {'statusCode': 200, 'body': json.dumps(result, default=decimal_default)}
            
            elif '/financials' in path:
                symbol = params.get('symbol')
                if not symbol:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'symbol required'})}
                result = api.get_financial_statements(symbol)
                return {'statusCode': 200, 'body': json.dumps(result, default=decimal_default)}
            
            elif '/health' in path:
                result = {
                    'status': 'healthy',
                    'circuit_breaker': api.cb.get_health_report(),
                    'metrics': api.metrics.get_metrics()
                }
                return {'statusCode': 200, 'body': json.dumps(result)}

            elif '/batch/prices' in path:
                symbols = params.get('symbols')
                if not symbols:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'symbols required'})}
                symbol_list = symbols.split(',')
                result = api.get_batch_prices(symbol_list)
                return {'statusCode': 200, 'body': json.dumps(result, default=decimal_default)}

            elif '/batch/metrics' in path:
                symbols = params.get('symbols')
                if not symbols:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'symbols required'})}
                symbol_list = symbols.split(',')
                result = api.get_batch_metrics(symbol_list)
                return {'statusCode': 200, 'body': json.dumps(result, default=decimal_default)}

            elif '/batch/estimates' in path:
                symbols = params.get('symbols')
                if not symbols:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'symbols required'})}
                symbol_list = symbols.split(',')
                result = api.get_batch_estimates(symbol_list)
                return {'statusCode': 200, 'body': json.dumps(result, default=decimal_default)}

            elif '/batch/financials' in path:
                symbols = params.get('symbols')
                if not symbols:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'symbols required'})}
                symbol_list = symbols.split(',')
                result = api.get_batch_financials(symbol_list)
                return {'statusCode': 200, 'body': json.dumps(result, default=decimal_default)}

            else:
                return {'statusCode': 404, 'body': json.dumps({'error': 'not found'})}
        
        elif http_method == 'POST':
            if '/all' in path:
                data = json.loads(body) if body else {}
                symbol = data.get('symbol')
                if not symbol:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'symbol required'})}
                result = api.get_all_data(symbol)
                return {'statusCode': 200, 'body': json.dumps(result, default=decimal_default)}
            
            else:
                return {'statusCode': 404, 'body': json.dumps({'error': 'not found'})}
        
        else:
            return {'statusCode': 405, 'body': json.dumps({'error': 'method not allowed'})}
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
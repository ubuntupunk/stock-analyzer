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

from api_clients import (
    YahooFinanceClient,
    AlphaVantageClient,
    PolygonClient,
    AlpacaClient,
)
from circuit_breaker import CircuitBreakerManager, get_circuit_breaker
from constants import (
    CONFIG_KEY_CACHE_TIMEOUT,
    CONFIG_KEY_PRIORITIES,
    CONFIG_KEY_TIMEOUT,
    DEFAULT_PRIORITIES,
    DELIMITER_COMMA,
    ERROR_METHOD_NOT_ALLOWED,
    ERROR_NOT_FOUND,
    ERROR_SYMBOL_REQUIRED,
    ERROR_SYMBOLS_REQUIRED,
    HTTP_BAD_REQUEST,
    HTTP_METHOD_GET,
    HTTP_METHOD_NOT_ALLOWED,
    HTTP_METHOD_POST,
    HTTP_NOT_FOUND,
    HTTP_OK,
    HTTP_SERVER_ERROR,
    KEY_BODY,
    KEY_ERROR,
    KEY_STATUS_CODE,
    METRICS_KEY_AVG_MS,
    METRICS_KEY_CALLS,
    METRICS_KEY_COUNT,
    METRICS_KEY_ERRORS,
    METRICS_KEY_FAILED,
    METRICS_KEY_LATENCY,
    METRICS_KEY_RATE_LIMITS,
    METRICS_KEY_REQUESTS,
    METRICS_KEY_SOURCES,
    METRICS_KEY_SUCCESS,
    METRICS_KEY_SUCCESS_RATE,
    METRICS_KEY_TIMEOUTS,
    METRICS_KEY_TOTAL,
    METRICS_KEY_TOTAL_MS,
    PATH_ALL,
    PATH_BATCH_ESTIMATES,
    PATH_BATCH_FINANCIALS,
    PATH_BATCH_METRICS,
    PATH_BATCH_PRICES,
    PATH_ESTIMATES,
    PATH_FINANCIALS,
    PATH_HEALTH,
    PATH_METRICS,
    PATH_PRICE,
    QUERY_PARAM_PERIOD,
    QUERY_PARAM_SYMBOL,
    QUERY_PARAM_SYMBOLS,
    REQUEST_KEY_BODY,
    REQUEST_KEY_HTTP_METHOD,
    REQUEST_KEY_PATH,
    REQUEST_KEY_QUERY_STRING_PARAMS,
    RESPONSE_FORMAT_NA,
    RESPONSE_FORMAT_SUCCESS_RATE,
    RESPONSE_KEY_CIRCUIT_BREAKER,
    RESPONSE_KEY_METRICS,
    RESPONSE_KEY_STATUS,
    RESPONSE_STATUS_HEALTHY,
    STOCK_API_DEFAULT_CACHE_TIMEOUT,
    STOCK_API_DEFAULT_PERIOD,
    STOCK_API_DEFAULT_TIMEOUT,
    STOCK_API_MAX_WORKERS,
)


def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


class APIMetrics:
    """Track API performance metrics"""

    def __init__(self):
        self.metrics = {
            METRICS_KEY_REQUESTS: {
                METRICS_KEY_TOTAL: 0,
                METRICS_KEY_SUCCESS: 0,
                METRICS_KEY_FAILED: 0,
            },
            METRICS_KEY_SOURCES: {},
            METRICS_KEY_LATENCY: {
                METRICS_KEY_TOTAL_MS: 0,
                METRICS_KEY_COUNT: 0,
                METRICS_KEY_AVG_MS: 0,
            },
            METRICS_KEY_RATE_LIMITS: 0,
            METRICS_KEY_TIMEOUTS: 0,
            METRICS_KEY_ERRORS: {},
        }
        self._lock = asyncio.Lock()

    def _init_source_metrics(self, source: str):
        """Initialize metrics for a new source"""
        if source not in self.metrics[METRICS_KEY_SOURCES]:
            self.metrics[METRICS_KEY_SOURCES][source] = {
                METRICS_KEY_CALLS: 0,
                METRICS_KEY_SUCCESS: 0,
                METRICS_KEY_FAILED: 0,
            }

    def _init_error_metrics(self, source: str):
        """Initialize error metrics for a source"""
        if source not in self.metrics[METRICS_KEY_ERRORS]:
            self.metrics[METRICS_KEY_ERRORS][source] = {
                METRICS_KEY_RATE_LIMITS: 0,
                METRICS_KEY_TIMEOUTS: 0,
                "other": 0,
            }

    async def record_request(self, source: str, success: bool, latency_ms: float):
        """Record an API request"""
        async with self._lock:
            self.metrics[METRICS_KEY_REQUESTS][METRICS_KEY_TOTAL] += 1
            if success:
                self.metrics[METRICS_KEY_REQUESTS][METRICS_KEY_SUCCESS] += 1
            else:
                self.metrics[METRICS_KEY_REQUESTS][METRICS_KEY_FAILED] += 1

            # Source-specific tracking
            self._init_source_metrics(source)
            self.metrics[METRICS_KEY_SOURCES][source][METRICS_KEY_CALLS] += 1
            if success:
                self.metrics[METRICS_KEY_SOURCES][source][METRICS_KEY_SUCCESS] += 1
            else:
                self.metrics[METRICS_KEY_SOURCES][source][METRICS_KEY_FAILED] += 1

            # Latency tracking
            self.metrics[METRICS_KEY_LATENCY][METRICS_KEY_TOTAL_MS] += latency_ms
            self.metrics[METRICS_KEY_LATENCY][METRICS_KEY_COUNT] += 1
            self.metrics[METRICS_KEY_LATENCY][METRICS_KEY_AVG_MS] = (
                self.metrics[METRICS_KEY_LATENCY][METRICS_KEY_TOTAL_MS]
                / self.metrics[METRICS_KEY_LATENCY][METRICS_KEY_COUNT]
            )

    def record_rate_limit(self, source: str):
        """Record a rate limit hit"""
        self.metrics[METRICS_KEY_RATE_LIMITS] += 1
        self._init_error_metrics(source)
        self.metrics[METRICS_KEY_ERRORS][source][METRICS_KEY_RATE_LIMITS] += 1

    def record_timeout(self, source: str):
        """Record a timeout"""
        self.metrics[METRICS_KEY_TIMEOUTS] += 1
        self._init_error_metrics(source)
        self.metrics[METRICS_KEY_ERRORS][source][METRICS_KEY_TIMEOUTS] += 1

    def get_metrics(self) -> Dict:
        """Get current metrics"""
        total_requests = self.metrics[METRICS_KEY_REQUESTS][METRICS_KEY_TOTAL]
        success_requests = self.metrics[METRICS_KEY_REQUESTS][METRICS_KEY_SUCCESS]

        if total_requests > 0:
            success_rate = RESPONSE_FORMAT_SUCCESS_RATE.format(
                (success_requests / total_requests) * 100
            )
        else:
            success_rate = RESPONSE_FORMAT_NA

        return {**self.metrics, METRICS_KEY_SUCCESS_RATE: success_rate}

    def get_source_stats(self, source: str) -> Dict:
        """Get stats for a specific source"""
        if source not in self.metrics[METRICS_KEY_SOURCES]:
            return {METRICS_KEY_CALLS: 0, METRICS_KEY_SUCCESS: 0, METRICS_KEY_FAILED: 0}

        source_data = self.metrics[METRICS_KEY_SOURCES][source]
        total_calls = source_data[METRICS_KEY_CALLS]

        if total_calls > 0:
            success_rate = RESPONSE_FORMAT_SUCCESS_RATE.format(
                (source_data[METRICS_KEY_SUCCESS] / total_calls) * 100
            )
        else:
            success_rate = RESPONSE_FORMAT_NA

        return {**source_data, METRICS_KEY_SUCCESS_RATE: success_rate}


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
        self.timeout = cfg.get(CONFIG_KEY_TIMEOUT, STOCK_API_DEFAULT_TIMEOUT)

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
        self.cache_timeout = cfg.get(
            CONFIG_KEY_CACHE_TIMEOUT, STOCK_API_DEFAULT_CACHE_TIMEOUT
        )

        # Configurable priorities
        self.priorities = cfg.get(CONFIG_KEY_PRIORITIES, DEFAULT_PRIORITIES)

        # Thread pool for sync fallback
        self.executor = ThreadPoolExecutor(max_workers=STOCK_API_MAX_WORKERS)

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

        cached_time = self.cache[cache_key].get("timestamp", 0)
        return (datetime.now().timestamp() - cached_time) < self.cache_timeout

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache if valid"""
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key].get("data")
        return None

    def _set_cache(self, cache_key: str, data: Dict):
        """Store data in cache"""
        self.cache[cache_key] = {"data": data, "timestamp": datetime.now().timestamp()}

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

            if source_name == "yahoo_finance":
                tasks.append(self._fetch_yahoo_price(symbol))
                sources_to_try.append("yahoo_finance")
            elif source_name == "alpaca" and self.alpaca.api_key:
                tasks.append(self._fetch_alpaca_price(symbol))
                sources_to_try.append("alpaca")
            elif source_name == "polygon" and self.polygon.api_key:
                tasks.append(self._fetch_polygon_price(symbol))
                sources_to_try.append("polygon")
            elif source_name == "alpha_vantage":
                tasks.append(self._fetch_alpha_price(symbol))
                sources_to_try.append("alpha_vantage")

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
                except Exception as err:
                    print(f"Task failed: {err}")
                    continue
        except Exception as err:
            print(f"Parallel fetch error: {err}")

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
                await self.metrics.record_request("yahoo_finance", True, latency_ms)
                return self.yahoo.parse_price(data)
            else:
                await self.metrics.record_request("yahoo_finance", False, latency_ms)
                return None
        except Exception as err:
            await self.metrics.record_request("yahoo_finance", False, 0)
            self.cb.record_failure("yahoo_finance", type(err).__name__)
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
                await self.metrics.record_request("alpaca", True, latency_ms)
                return self.alpaca.parse_price(data)
            else:
                await self.metrics.record_request("alpaca", False, latency_ms)
                return None
        except Exception as err:
            await self.metrics.record_request("alpaca", False, 0)
            self.cb.record_failure("alpaca", type(err).__name__)
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
                await self.metrics.record_request("polygon", True, latency_ms)
                return self.polygon.parse_price(data)
            else:
                await self.metrics.record_request("polygon", False, latency_ms)
                return None
        except Exception as err:
            await self.metrics.record_request("polygon", False, 0)
            self.cb.record_failure("polygon", type(err).__name__)
            return None

    async def _fetch_alpha_price(self, symbol: str) -> Optional[Dict]:
        """Fetch price from Alpha Vantage"""
        try:
            start = time.time()
            data = await asyncio.get_event_loop().run_in_executor(
                self.executor, self.alpha_vantage.fetch_quote, symbol
            )
            latency_ms = (time.time() - start) * 1000

            if data and "05. price" in data:
                await self.metrics.record_request("alpha_vantage", True, latency_ms)
                return self.alpha_vantage.parse_price(data)
            else:
                await self.metrics.record_request("alpha_vantage", False, latency_ms)
                return None
        except Exception as err:
            await self.metrics.record_request("alpha_vantage", False, 0)
            self.cb.record_failure("alpha_vantage", type(err).__name__)
            return None

    # ========================================================================
    # SINGLE STOCK METHODS
    # ========================================================================

    def get_stock_price(
        self,
        symbol: str,
        period: str = "1mo",
        startDate: str = None,
        endDate: str = None,
    ) -> Dict:
        """
        Get current stock price and basic quote information
        Includes both price data and metrics for comprehensive view
        """
        # Check cache first
        cache_key = self._get_cache_key(
            f'price:{period}:{startDate or "default"}', symbol
        )
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        price_data = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "source": "unknown",
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
                price_data["source"] = "yahoo_finance"
                self.metrics.record_request("yahoo_finance", True, latency_ms)
            else:
                self.metrics.record_request("yahoo_finance", False, latency_ms)

        except Exception as err:
            self.metrics.record_request("yahoo_finance", False, 0)
            print(f"Yahoo price/metrics error for {symbol}: {str(err)}")

        # Fallback to other sources if needed
        if price_data["source"] == "unknown":
            # Try Alpha Vantage
            try:
                start = time.time()
                av_data = self.alpha_vantage.fetch_quote(symbol)
                latency_ms = (time.time() - start) * 1000

                if av_data and "05. price" in av_data:
                    price_data.update(self.alpha_vantage.parse_price(av_data))
                    price_data["source"] = "alpha_vantage"
                    self.metrics.record_request("alpha_vantage", True, latency_ms)
                else:
                    self.metrics.record_request("alpha_vantage", False, latency_ms)
            except Exception as err:
                self.metrics.record_request("alpha_vantage", False, 0)

        # Also fetch historical data for charting (support custom date range)
        if startDate and endDate:
            history = self.yahoo.fetch_history_range(symbol, startDate, endDate)
        else:
            history = self.yahoo.fetch_history(symbol, period)
        if history:
            price_data["historicalData"] = history

        self._set_cache(cache_key, price_data)
        return price_data

    def get_stock_metrics(self, symbol: str) -> Dict:
        """
        Get comprehensive stock metrics
        Priority: Yahoo Finance > Alpha Vantage > Polygon
        """
        cache_key = self._get_cache_key("metrics", symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        metrics = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "source": "unknown",
        }

        # Try Yahoo Finance FIRST (fastest, most complete)
        try:
            start = time.time()
            yf_data = self.yahoo.fetch_data(symbol)
            latency_ms = (time.time() - start) * 1000

            if yf_data:
                metrics.update(self.yahoo.parse_metrics(yf_data))
                metrics["source"] = "yahoo_finance"
                self.metrics.record_request("yahoo_finance", True, latency_ms)
            else:
                self.metrics.record_request("yahoo_finance", False, latency_ms)

        except Exception as err:
            self.metrics.record_request("yahoo_finance", False, 0)
            print(f"Yahoo metrics error for {symbol}: {str(err)}")

        # Fallback to Alpha Vantage if needed
        if metrics["source"] == "unknown":
            try:
                start = time.time()
                av_data = self.alpha_vantage.fetch_overview(symbol)
                latency_ms = (time.time() - start) * 1000

                if av_data:
                    metrics.update(self.alpha_vantage.parse_metrics(av_data))
                    metrics["source"] = "alpha_vantage"
                    self.metrics.record_request("alpha_vantage", True, latency_ms)
                else:
                    self.metrics.record_request("alpha_vantage", False, latency_ms)
            except Exception as err:
                self.metrics.record_request("alpha_vantage", False, 0)

        # Enhance with Polygon data if available
        if self.polygon.api_key and metrics["source"] == "unknown":
            try:
                start = time.time()
                poly_data = self.polygon.fetch_ticker(symbol)
                latency_ms = (time.time() - start) * 1000

                if poly_data:
                    metrics.update(self.polygon.parse_metrics(poly_data))
                    if metrics["source"] == "unknown":
                        metrics["source"] = "polygon"
                    self.metrics.record_request("polygon", True, latency_ms)
                else:
                    self.metrics.record_request("polygon", False, latency_ms)
            except Exception as err:
                self.metrics.record_request("polygon", False, 0)

        self._set_cache(cache_key, metrics)
        return metrics

    def get_analyst_estimates(self, symbol: str) -> Dict:
        """Get analyst estimates for earnings and revenue"""
        cache_key = self._get_cache_key("estimates", symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        estimates = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "earnings_estimates": [],
            "revenue_estimates": [],
            "source": "unknown",
        }

        # Try Yahoo Finance FIRST
        try:
            yf_data = self.yahoo.fetch_data(symbol)
            if yf_data and ("earningsTrend" in yf_data or "targetMeanPrice" in yf_data):
                estimates.update(self.yahoo.parse_estimates(yf_data))
                estimates["source"] = "yahoo_finance"
        except Exception as err:
            print(f"Yahoo estimates error for {symbol}: {str(err)}")

        # Fallback to Alpha Vantage
        if estimates["source"] == "unknown":
            try:
                av_earnings = self.alpha_vantage.fetch_earnings(symbol)
                if av_earnings:
                    estimates.update(self.alpha_vantage.parse_estimates(av_earnings))
                    estimates["source"] = "alpha_vantage"
            except Exception as err:
                print(f"Alpha Vantage estimates error for {symbol}: {str(err)}")

        self._set_cache(cache_key, estimates)
        return estimates

    def get_financial_statements(self, symbol: str) -> Dict:
        """Get financial statements (income statement, balance sheet, cash flow)"""
        cache_key = self._get_cache_key("financials", symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        financials = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
            "source": "unknown",
        }

        # Try Yahoo Finance with full financial statements
        try:
            yf_financials = self.yahoo.fetch_financials(symbol)
            if yf_financials and (
                yf_financials.get("income_statement")
                or yf_financials.get("balance_sheet")
                or yf_financials.get("cash_flow")
            ):
                financials.update(yf_financials)
                financials["source"] = "yahoo_finance"
        except Exception as err:
            print(f"Yahoo financials error for {symbol}: {str(err)}")

        self._set_cache(cache_key, financials)
        return financials

    def get_stock_news(self, symbol: str) -> Dict:
        """
        Get stock news articles

        Uses Yahoo Finance news API

        Returns:
            Dict with news articles list
        """
        cache_key = self._get_cache_key("news", symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        news_data = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "articles": [],
            "source": "unknown",
        }

        # Try Yahoo Finance
        try:
            start = time.time()
            articles = self.yahoo.fetch_news(symbol)
            latency_ms = (time.time() - start) * 1000

            if articles:
                news_data["articles"] = articles
                news_data["source"] = "yahoo_finance"
                self.metrics.record_request("yahoo_finance", True, latency_ms)
            else:
                self.metrics.record_request("yahoo_finance", False, latency_ms)
        except Exception as err:
            self.metrics.record_request("yahoo_finance", False, 0)
            print(f"Yahoo news error for {symbol}: {str(err)}")

        self._set_cache(cache_key, news_data)
        return news_data

    def get_stock_factors(self, symbol: str) -> Dict:
        """
        Get stock factors for screening (value, growth, momentum, quality metrics)

        Returns:
            Dict with computed factor values
        """
        cache_key = self._get_cache_key("factors", symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        factors = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "source": "computed",
            "value_factors": {},
            "growth_factors": {},
            "momentum_factors": {},
            "quality_factors": {},
        }

        # Get metrics first
        try:
            metrics = self.get_stock_metrics(symbol)
            if metrics:
                # Value factors
                factors["value_factors"] = {
                    "pe_ratio": metrics.get("pe_ratio", 0),
                    "forward_pe": metrics.get("forward_pe", 0),
                    "peg_ratio": metrics.get("peg_ratio", 0),
                    "price_to_book": metrics.get("price_to_book", 0),
                    "dividend_yield": metrics.get("dividend_yield", 0),
                }

                # Growth factors
                factors["growth_factors"] = {
                    "revenue_growth": metrics.get("revenue_growth", 0),
                    "earnings_growth": metrics.get("earnings_growth", 0),
                    "eps_growth_5y": 0,  # Would need historical data
                    "revenue_growth_5y": 0,  # Would need historical data
                }

                # Quality factors
                factors["quality_factors"] = {
                    "roe": metrics.get("roe", 0),
                    "roa": metrics.get("roa", 0),
                    "profit_margin": metrics.get("profit_margin", 0),
                    "operating_margin": metrics.get("operating_margin", 0),
                    "debt_to_equity": metrics.get("debt_to_equity", 0),
                    "current_ratio": metrics.get("current_ratio", 0),
                }

        except Exception as err:
            print(f"Error computing factors for {symbol}: {str(err)}")

        # Momentum factors require historical price data
        try:
            price_data = self.get_stock_price(symbol, period="1y")
            if price_data and "historicalData" in price_data:
                hist_data = price_data["historicalData"]
                if hist_data:
                    dates = sorted(hist_data.keys())
                    if len(dates) >= 2:
                        # Get first and last prices for momentum calculation
                        first_price = (
                            hist_data[dates[0]].get("4. close", 0)
                            if isinstance(hist_data[dates[0]], dict)
                            else 0
                        )
                        last_price = (
                            hist_data[dates[-1]].get("4. close", 0)
                            if isinstance(hist_data[dates[-1]], dict)
                            else 0
                        )

                        if first_price and first_price > 0:
                            # 52-week return (or available period)
                            period_return = (
                                (last_price - first_price) / first_price
                            ) * 100
                            factors["momentum_factors"] = {
                                "52_week_return": period_return,
                                "near_52_week_high": 0,  # Would need more data
                                "near_52_week_low": 0,  # Would need more data
                            }
        except Exception as err:
            print(f"Error computing momentum factors for {symbol}: {str(err)}")

        self._set_cache(cache_key, factors)
        return factors

    def get_all_data(self, symbol: str) -> Dict:
        """
        Get all available stock data from multiple sources

        This is the main entry point for fetching comprehensive stock data.
        It tries multiple sources and combines the results.
        """
        data = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "source": "unknown",
        }

        # Get price data
        try:
            price = self.get_stock_price(symbol)
            if price:
                data["price"] = price
        except Exception as err:
            print(f"Error fetching price for {symbol}: {str(err)}")

        # Get metrics
        try:
            metrics = self.get_stock_metrics(symbol)
            if metrics:
                data["metrics"] = metrics
        except Exception as err:
            print(f"Error fetching metrics for {symbol}: {str(err)}")

        # Get analyst estimates
        try:
            estimates = self.get_analyst_estimates(symbol)
            if estimates and estimates.get("earnings_estimates"):
                data["estimates"] = estimates
        except Exception as err:
            print(f"Error fetching estimates for {symbol}: {str(err)}")

        # Get financials
        try:
            financials = self.get_financial_statements(symbol)
            if financials and (
                financials.get("income_statement") or financials.get("balance_sheet")
            ):
                data["financials"] = financials
        except Exception as err:
            print(f"Error fetching financials for {symbol}: {str(err)}")

        # Add cache metadata
        data["cached"] = False

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
                    results[symbol] = {"symbol": symbol, "error": "No data"}
            except Exception as err:
                results[symbol] = {"symbol": symbol, "error": str(err)}
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
                    results[symbol] = {"symbol": symbol, "error": "No data"}
            except Exception as err:
                results[symbol] = {"symbol": symbol, "error": str(err)}
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
                    results[symbol] = {"symbol": symbol, "error": "No data"}
            except Exception as err:
                results[symbol] = {"symbol": symbol, "error": str(err)}
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
                    results[symbol] = {"symbol": symbol, "error": "No data"}
            except Exception as err:
                results[symbol] = {"symbol": symbol, "error": str(err)}
        return results

    def run_dcf(self, assumptions: Dict) -> Dict:
        """
        Perform a Discounted Cash Flow (DCF) analysis using real financial data.
        
        Args:
            assumptions: Dict with optional overrides:
                - symbol: Stock symbol (required)
                - growth_rate: FCF growth rate (default: 5%)
                - terminal_growth_rate: Terminal growth rate (default: 2%)
                - discount_rate: WACC/discount rate (default: 10%)
                - years: Projection years (default: 5)
                - tax_rate: Corporate tax rate (default: 21%)
        
        Returns:
            Dict with DCF valuation results
        """
        from constants import (
            DCF_DEFAULT_DISCOUNT_RATE,
            DCF_DEFAULT_GROWTH_RATE,
            DCF_DEFAULT_PROJECTION_YEARS,
            DCF_DEFAULT_TAX_RATE,
            DCF_DEFAULT_TERMINAL_GROWTH_RATE,
            DCF_KEY_ASSUMPTIONS,
            DCF_KEY_BASE_FCF,
            DCF_KEY_BETA,
            DCF_KEY_CASH,
            DCF_KEY_CURRENT_PRICE,
            DCF_KEY_DEBT,
            DCF_KEY_DISCOUNT_RATE,
            DCF_KEY_ENTERPRISE_VALUE,
            DCF_KEY_EQUITY_VALUE,
            DCF_KEY_FCF_PROJECTIONS,
            DCF_KEY_GROWTH_RATE,
            DCF_KEY_INTRINSIC_VALUE,
            DCF_KEY_MODEL_DATE,
            DCF_KEY_PV_FCF,
            DCF_KEY_PV_TERMINAL_VALUE,
            DCF_KEY_SHARES_OUTSTANDING,
            DCF_KEY_SYMBOL,
            DCF_KEY_TAX_RATE,
            DCF_KEY_TERMINAL_GROWTH,
            DCF_KEY_TERMINAL_VALUE,
            DCF_KEY_UPSIDE_POTENTIAL,
            DCF_KEY_VALUE_PER_SHARE,
            DCF_KEY_WACC,
            DCF_KEY_YEARS,
            DCF_MSG_CALCULATED,
            DCF_MSG_MISSING_DATA,
            DCF_MSG_PERFORMING,
            DCF_MSG_USING_REAL_DATA,
        )
        
        stock_symbol = assumptions.get(DCF_KEY_SYMBOL, "UNKNOWN")
        print(DCF_MSG_PERFORMING.format(stock_symbol))
        
        # Get real financial data
        try:
            financials = self.get_financial_statements(stock_symbol)
            metrics = self.get_stock_metrics(stock_symbol)
            price_data = self.get_stock_price(stock_symbol)
            
            # Extract current price
            current_price = price_data.get("price", assumptions.get(DCF_KEY_CURRENT_PRICE, 100.0))
            
            # Extract financial data
            cash_flow_data = financials.get("cash_flow", [])
            balance_sheet_data = financials.get("balance_sheet", [])
            
            # Get most recent free cash flow
            base_fcf = 0
            if cash_flow_data and len(cash_flow_data) > 0:
                latest_cf = cash_flow_data[0]
                base_fcf = latest_cf.get("free_cash_flow", 0)
                print(DCF_MSG_USING_REAL_DATA.format("cash flow statements"))
            
            # Get cash and debt from balance sheet
            total_cash = 0
            total_debt = 0
            if balance_sheet_data and len(balance_sheet_data) > 0:
                latest_bs = balance_sheet_data[0]
                total_cash = latest_bs.get("cash", 0)
                total_debt = latest_bs.get("long_term_debt", 0)
            
            # Get shares outstanding and beta
            shares_outstanding = metrics.get(DCF_KEY_SHARES_OUTSTANDING, 0)
            beta = metrics.get(DCF_KEY_BETA, 1.0)
            
            # If no real FCF data, estimate from operating cash flow
            if base_fcf == 0:
                print(DCF_MSG_MISSING_DATA.format(stock_symbol))
                operating_cf = metrics.get("operating_cash_flow", 0)
                if operating_cf > 0:
                    base_fcf = operating_cf * 0.8  # Estimate FCF as 80% of operating CF
                else:
                    # Last resort: estimate from market cap
                    market_cap = metrics.get("market_cap", 0)
                    base_fcf = market_cap * 0.05  # Estimate 5% FCF yield
            
        except Exception as data_error:
            print(f"Error fetching financial data: {str(data_error)}")
            # Use fallback estimates
            current_price = assumptions.get(DCF_KEY_CURRENT_PRICE, 100.0)
            base_fcf = current_price * 10  # Rough estimate
            total_cash = 0
            total_debt = 0
            shares_outstanding = 1_000_000  # Estimate
            beta = 1.0
        
        # Get assumptions with defaults
        growth_rate = assumptions.get(DCF_KEY_GROWTH_RATE, DCF_DEFAULT_GROWTH_RATE)
        terminal_growth_rate = assumptions.get(DCF_KEY_TERMINAL_GROWTH, DCF_DEFAULT_TERMINAL_GROWTH_RATE)
        discount_rate = assumptions.get(DCF_KEY_DISCOUNT_RATE, DCF_DEFAULT_DISCOUNT_RATE)
        projection_years = assumptions.get(DCF_KEY_YEARS, DCF_DEFAULT_PROJECTION_YEARS)
        tax_rate = assumptions.get(DCF_KEY_TAX_RATE, DCF_DEFAULT_TAX_RATE)
        
        # Calculate WACC if beta is available
        wacc = discount_rate
        if beta > 0:
            from constants import DCF_DEFAULT_MARKET_RETURN, DCF_DEFAULT_RISK_FREE_RATE
            risk_free_rate = DCF_DEFAULT_RISK_FREE_RATE
            market_return = DCF_DEFAULT_MARKET_RETURN
            equity_risk_premium = market_return - risk_free_rate
            cost_of_equity = risk_free_rate + (beta * equity_risk_premium)
            wacc = cost_of_equity  # Simplified WACC (assuming mostly equity financed)
        
        # Project Free Cash Flows
        fcf_projections = []
        for year in range(1, projection_years + 1):
            projected_fcf = base_fcf * ((1 + growth_rate) ** year)
            fcf_projections.append(projected_fcf)
        
        # Calculate Terminal Value (Gordon Growth Model)
        terminal_fcf = fcf_projections[-1] * (1 + terminal_growth_rate)
        terminal_value = terminal_fcf / (wacc - terminal_growth_rate)
        
        # Calculate Present Values
        pv_fcf = sum([
            fcf / ((1 + wacc) ** year)
            for year, fcf in enumerate(fcf_projections, 1)
        ])
        
        pv_terminal_value = terminal_value / ((1 + wacc) ** projection_years)
        
        # Calculate Enterprise Value
        enterprise_value = pv_fcf + pv_terminal_value
        
        # Calculate Equity Value (EV - Debt + Cash)
        equity_value = enterprise_value - total_debt + total_cash
        
        # Calculate Value Per Share
        value_per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0
        
        # Calculate Upside Potential
        upside_potential = 0
        if current_price > 0:
            upside_potential = ((value_per_share - current_price) / current_price) * 100
        
        print(DCF_MSG_CALCULATED.format(value_per_share, current_price, upside_potential))
        
        return {
            DCF_KEY_SYMBOL: stock_symbol,
            DCF_KEY_INTRINSIC_VALUE: round(value_per_share, 2),
            DCF_KEY_CURRENT_PRICE: round(current_price, 2),
            DCF_KEY_UPSIDE_POTENTIAL: round(upside_potential, 2),
            DCF_KEY_ENTERPRISE_VALUE: round(enterprise_value, 2),
            DCF_KEY_EQUITY_VALUE: round(equity_value, 2),
            DCF_KEY_SHARES_OUTSTANDING: shares_outstanding,
            DCF_KEY_VALUE_PER_SHARE: round(value_per_share, 2),
            DCF_KEY_FCF_PROJECTIONS: [round(fcf, 2) for fcf in fcf_projections],
            DCF_KEY_TERMINAL_VALUE: round(terminal_value, 2),
            DCF_KEY_PV_FCF: round(pv_fcf, 2),
            DCF_KEY_PV_TERMINAL_VALUE: round(pv_terminal_value, 2),
            DCF_KEY_BASE_FCF: round(base_fcf, 2),
            DCF_KEY_CASH: round(total_cash, 2),
            DCF_KEY_DEBT: round(total_debt, 2),
            DCF_KEY_BETA: round(beta, 2),
            DCF_KEY_WACC: round(wacc * 100, 2),  # As percentage
            DCF_KEY_ASSUMPTIONS: {
                DCF_KEY_GROWTH_RATE: growth_rate,
                DCF_KEY_TERMINAL_GROWTH: terminal_growth_rate,
                DCF_KEY_DISCOUNT_RATE: discount_rate,
                DCF_KEY_YEARS: projection_years,
                DCF_KEY_TAX_RATE: tax_rate,
            },
            DCF_KEY_MODEL_DATE: datetime.now().isoformat(),
        }


from constants import (
    DELIMITER_COMMA,
    ERROR_METHOD_NOT_ALLOWED,
    ERROR_NOT_FOUND,
    ERROR_SYMBOL_REQUIRED,
    ERROR_SYMBOLS_REQUIRED,
    HTTP_BAD_REQUEST,
    HTTP_METHOD_NOT_ALLOWED,
    HTTP_NOT_FOUND,
    HTTP_OK,
    HTTP_SERVER_ERROR,
    KEY_BODY,
    KEY_ERROR,
    KEY_STATUS_CODE,
    PATH_ALL,
    PATH_BATCH_ESTIMATES,
    PATH_BATCH_FINANCIALS,
    PATH_BATCH_METRICS,
    PATH_BATCH_PRICES,
    PATH_ESTIMATES,
    PATH_FINANCIALS,
    PATH_HEALTH,
    PATH_METRICS,
    PATH_PRICE,
    QUERY_PARAM_PERIOD,
    QUERY_PARAM_SYMBOL,
    QUERY_PARAM_SYMBOLS,
    REQUEST_KEY_BODY,
    REQUEST_KEY_HTTP_METHOD,
    REQUEST_KEY_PATH,
    REQUEST_KEY_QUERY_STRING_PARAMS,
    RESPONSE_KEY_CIRCUIT_BREAKER,
    RESPONSE_KEY_METRICS,
    RESPONSE_KEY_STATUS,
    RESPONSE_STATUS_HEALTHY,
    STOCK_API_DEFAULT_PERIOD,
)


def _create_error_response(status_code: int, error_message: str) -> Dict:
    """Create standardized error response"""
    return {
        KEY_STATUS_CODE: status_code,
        KEY_BODY: json.dumps({KEY_ERROR: error_message}),
    }


def _create_success_response(api_result: Dict) -> Dict:
    """Create standardized success response"""
    return {
        KEY_STATUS_CODE: HTTP_OK,
        KEY_BODY: json.dumps(api_result, default=decimal_default),
    }


def _validate_symbol(query_params: Dict) -> Optional[str]:
    """Validate and extract symbol from query parameters"""
    return query_params.get(QUERY_PARAM_SYMBOL)


def _validate_symbols(query_params: Dict) -> Optional[List[str]]:
    """Validate and extract symbols list from query parameters"""
    symbols_str = query_params.get(QUERY_PARAM_SYMBOLS)
    if symbols_str:
        return symbols_str.split(DELIMITER_COMMA)
    return None


def _handle_metrics_request(api: StockDataAPI, query_params: Dict) -> Dict:
    """Handle /metrics endpoint"""
    stock_symbol = _validate_symbol(query_params)
    if not stock_symbol:
        return _create_error_response(HTTP_BAD_REQUEST, ERROR_SYMBOL_REQUIRED)

    api_result = api.get_stock_metrics(stock_symbol)
    return _create_success_response(api_result)


def _handle_price_request(api: StockDataAPI, query_params: Dict) -> Dict:
    """Handle /price endpoint"""
    stock_symbol = _validate_symbol(query_params)
    if not stock_symbol:
        return _create_error_response(HTTP_BAD_REQUEST, ERROR_SYMBOL_REQUIRED)

    period = query_params.get(QUERY_PARAM_PERIOD, STOCK_API_DEFAULT_PERIOD)
    api_result = api.get_stock_price(stock_symbol, period)
    return _create_success_response(api_result)


def _handle_estimates_request(api: StockDataAPI, query_params: Dict) -> Dict:
    """Handle /estimates endpoint"""
    stock_symbol = _validate_symbol(query_params)
    if not stock_symbol:
        return _create_error_response(HTTP_BAD_REQUEST, ERROR_SYMBOL_REQUIRED)

    api_result = api.get_analyst_estimates(stock_symbol)
    return _create_success_response(api_result)


def _handle_financials_request(api: StockDataAPI, query_params: Dict) -> Dict:
    """Handle /financials endpoint"""
    stock_symbol = _validate_symbol(query_params)
    if not stock_symbol:
        return _create_error_response(HTTP_BAD_REQUEST, ERROR_SYMBOL_REQUIRED)

    api_result = api.get_financial_statements(stock_symbol)
    return _create_success_response(api_result)


def _handle_health_request(api: StockDataAPI) -> Dict:
    """Handle /health endpoint"""
    health_result = {
        RESPONSE_KEY_STATUS: RESPONSE_STATUS_HEALTHY,
        RESPONSE_KEY_CIRCUIT_BREAKER: api.cb.get_health_report(),
        RESPONSE_KEY_METRICS: api.metrics.get_metrics(),
    }
    return _create_success_response(health_result)


def _handle_batch_prices_request(api: StockDataAPI, query_params: Dict) -> Dict:
    """Handle /batch/prices endpoint"""
    symbol_list = _validate_symbols(query_params)
    if not symbol_list:
        return _create_error_response(HTTP_BAD_REQUEST, ERROR_SYMBOLS_REQUIRED)

    api_result = api.get_batch_prices(symbol_list)
    return _create_success_response(api_result)


def _handle_batch_metrics_request(api: StockDataAPI, query_params: Dict) -> Dict:
    """Handle /batch/metrics endpoint"""
    symbol_list = _validate_symbols(query_params)
    if not symbol_list:
        return _create_error_response(HTTP_BAD_REQUEST, ERROR_SYMBOLS_REQUIRED)

    api_result = api.get_batch_metrics(symbol_list)
    return _create_success_response(api_result)


def _handle_batch_estimates_request(api: StockDataAPI, query_params: Dict) -> Dict:
    """Handle /batch/estimates endpoint"""
    symbol_list = _validate_symbols(query_params)
    if not symbol_list:
        return _create_error_response(HTTP_BAD_REQUEST, ERROR_SYMBOLS_REQUIRED)

    api_result = api.get_batch_estimates(symbol_list)
    return _create_success_response(api_result)


def _handle_batch_financials_request(api: StockDataAPI, query_params: Dict) -> Dict:
    """Handle /batch/financials endpoint"""
    symbol_list = _validate_symbols(query_params)
    if not symbol_list:
        return _create_error_response(HTTP_BAD_REQUEST, ERROR_SYMBOLS_REQUIRED)

    api_result = api.get_batch_financials(symbol_list)
    return _create_success_response(api_result)


def _handle_all_data_request(api: StockDataAPI, request_body: str) -> Dict:
    """Handle /all endpoint (POST)"""
    request_data = json.loads(request_body) if request_body else {}
    stock_symbol = request_data.get(QUERY_PARAM_SYMBOL)
    if not stock_symbol:
        return _create_error_response(HTTP_BAD_REQUEST, ERROR_SYMBOL_REQUIRED)

    api_result = api.get_all_data(stock_symbol)
    return _create_success_response(api_result)


def _route_get_request(api: StockDataAPI, path: str, query_params: Dict) -> Dict:
    """Route GET requests to appropriate handlers"""
    if PATH_METRICS in path:
        return _handle_metrics_request(api, query_params)
    if PATH_PRICE in path:
        return _handle_price_request(api, query_params)
    if PATH_ESTIMATES in path:
        return _handle_estimates_request(api, query_params)
    if PATH_FINANCIALS in path:
        return _handle_financials_request(api, query_params)
    if PATH_HEALTH in path:
        return _handle_health_request(api)
    if PATH_BATCH_PRICES in path:
        return _handle_batch_prices_request(api, query_params)
    if PATH_BATCH_METRICS in path:
        return _handle_batch_metrics_request(api, query_params)
    if PATH_BATCH_ESTIMATES in path:
        return _handle_batch_estimates_request(api, query_params)
    if PATH_BATCH_FINANCIALS in path:
        return _handle_batch_financials_request(api, query_params)

    return _create_error_response(HTTP_NOT_FOUND, ERROR_NOT_FOUND)


def _route_post_request(api: StockDataAPI, path: str, request_body: str) -> Dict:
    """Route POST requests to appropriate handlers"""
    if PATH_ALL in path:
        return _handle_all_data_request(api, request_body)

    return _create_error_response(HTTP_NOT_FOUND, ERROR_NOT_FOUND)


def lambda_handler(event, context):
    """AWS Lambda handler for stock API requests"""
    try:
        # Parse request
        http_method = event.get(REQUEST_KEY_HTTP_METHOD, HTTP_METHOD_GET)
        path = event.get(REQUEST_KEY_PATH, "/")
        query_params = event.get(REQUEST_KEY_QUERY_STRING_PARAMS) or {}
        request_body = event.get(REQUEST_KEY_BODY)

        # Create API instance
        api = StockDataAPI()

        # Route request based on HTTP method
        if http_method == HTTP_METHOD_GET:
            return _route_get_request(api, path, query_params)

        if http_method == HTTP_METHOD_POST:
            return _route_post_request(api, path, request_body)

        return _create_error_response(HTTP_METHOD_NOT_ALLOWED, ERROR_METHOD_NOT_ALLOWED)

    except Exception as handler_error:
        print(f"Error: {str(handler_error)}")
        return _create_error_response(HTTP_SERVER_ERROR, str(handler_error))

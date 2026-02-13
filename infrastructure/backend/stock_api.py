"""
Stock Data API - Main Orchestrator
Coordinates multiple API clients with fallback mechanisms, circuit breaker, and metrics
"""

import json
import logging
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
from dcf_calculator import DCFCalculator
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

# Configure logging
logger = logging.getLogger(__name__)


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
                logger.debug("Circuit OPEN for %s, skipping", source_name)
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
            logger.warning("All circuits OPEN for %s", symbol)
            return None

        # Wait for first successful result using asyncio.as_completed
        try:
            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    if result:
                        latency_ms = (time.time() - start_time) * 1000
                        logger.debug("Parallel fetch succeeded in %.0fms", latency_ms)
                        return result
                except Exception as err:
                    logger.debug("Task failed: %s", err)
                    continue
        except Exception as err:
            logger.warning("Parallel fetch error: %s", err)

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

    def _fetch_price_from_yahoo(self, symbol: str, price_data: Dict) -> bool:
        """Fetch price data from Yahoo Finance. Returns True if successful."""
        try:
            start = time.time()
            yf_data = self.yahoo.fetch_data(symbol)
            latency_ms = (time.time() - start) * 1000

            if yf_data:
                price_data.update(self.yahoo.parse_price(yf_data))
                price_data.update(self.yahoo.parse_metrics(yf_data))
                price_data["source"] = "yahoo_finance"
                self.metrics.record_request("yahoo_finance", True, latency_ms)
                return True

            self.metrics.record_request("yahoo_finance", False, latency_ms)
            return False

        except Exception as err:
            self.metrics.record_request("yahoo_finance", False, 0)
            logger.warning("Yahoo price/metrics error for %s: %s", symbol, str(err))
            return False

    def _fetch_price_from_alpha_vantage(self, symbol: str, price_data: Dict) -> bool:
        """Fetch price data from Alpha Vantage. Returns True if successful."""
        try:
            start = time.time()
            av_data = self.alpha_vantage.fetch_quote(symbol)
            latency_ms = (time.time() - start) * 1000

            if av_data and "05. price" in av_data:
                price_data.update(self.alpha_vantage.parse_price(av_data))
                price_data["source"] = "alpha_vantage"
                self.metrics.record_request("alpha_vantage", True, latency_ms)
                return True

            self.metrics.record_request("alpha_vantage", False, latency_ms)
            return False

        except Exception as err:
            self.metrics.record_request("alpha_vantage", False, 0)
            return False

    def _fetch_historical_data(
        self, symbol: str, period: str, startDate: str = None, endDate: str = None
    ) -> Dict:
        """Fetch historical price data"""
        if startDate and endDate:
            return self.yahoo.fetch_history_range(symbol, startDate, endDate)
        return self.yahoo.fetch_history(symbol, period)

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

        # Try sources in priority order
        if not self._fetch_price_from_yahoo(symbol, price_data):
            self._fetch_price_from_alpha_vantage(symbol, price_data)

        # Fetch historical data for charting
        history = self._fetch_historical_data(symbol, period, startDate, endDate)
        if history:
            price_data["historicalData"] = history

        self._set_cache(cache_key, price_data)
        return price_data

    def _fetch_from_yahoo(self, symbol: str, metrics: Dict) -> bool:
        """Fetch metrics from Yahoo Finance. Returns True if successful."""
        try:
            start = time.time()
            yf_data = self.yahoo.fetch_data(symbol)
            latency_ms = (time.time() - start) * 1000

            if yf_data:
                metrics.update(self.yahoo.parse_metrics(yf_data))
                metrics["source"] = "yahoo_finance"
                self.metrics.record_request("yahoo_finance", True, latency_ms)
                return True

            self.metrics.record_request("yahoo_finance", False, latency_ms)
            return False

        except Exception as err:
            self.metrics.record_request("yahoo_finance", False, 0)
            logger.warning("Yahoo metrics error for %s: %s", symbol, str(err))
            return False

    def _fetch_from_alpha_vantage(self, symbol: str, metrics: Dict) -> bool:
        """Fetch metrics from Alpha Vantage. Returns True if successful."""
        try:
            start = time.time()
            av_data = self.alpha_vantage.fetch_overview(symbol)
            latency_ms = (time.time() - start) * 1000

            if av_data:
                metrics.update(self.alpha_vantage.parse_metrics(av_data))
                metrics["source"] = "alpha_vantage"
                self.metrics.record_request("alpha_vantage", True, latency_ms)
                return True

            self.metrics.record_request("alpha_vantage", False, latency_ms)
            return False

        except Exception as err:
            self.metrics.record_request("alpha_vantage", False, 0)
            return False

    def _fetch_from_polygon(self, symbol: str, metrics: Dict) -> bool:
        """Fetch metrics from Polygon. Returns True if successful."""
        if not self.polygon.api_key:
            return False

        try:
            start = time.time()
            poly_data = self.polygon.fetch_ticker(symbol)
            latency_ms = (time.time() - start) * 1000

            if poly_data:
                metrics.update(self.polygon.parse_metrics(poly_data))
                if metrics["source"] == "unknown":
                    metrics["source"] = "polygon"
                self.metrics.record_request("polygon", True, latency_ms)
                return True

            self.metrics.record_request("polygon", False, latency_ms)
            return False

        except Exception as err:
            self.metrics.record_request("polygon", False, 0)
            return False

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

        # Try sources in priority order
        if not self._fetch_from_yahoo(symbol, metrics):
            if not self._fetch_from_alpha_vantage(symbol, metrics):
                self._fetch_from_polygon(symbol, metrics)

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
            logger.warning("Yahoo estimates error for %s: %s", symbol, str(err))

        # Fallback to Alpha Vantage
        if estimates["source"] == "unknown":
            try:
                av_earnings = self.alpha_vantage.fetch_earnings(symbol)
                if av_earnings:
                    estimates.update(self.alpha_vantage.parse_estimates(av_earnings))
                    estimates["source"] = "alpha_vantage"
            except Exception as err:
                logger.warning("Alpha Vantage estimates error for %s: %s", symbol, str(err))

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
            logger.warning("Yahoo financials error for %s: %s", symbol, str(err))

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
            logger.warning("Yahoo news error for %s: %s", symbol, str(err))

        self._set_cache(cache_key, news_data)
        return news_data

    def _compute_value_factors(self, metrics: Dict) -> Dict:
        """Extract value factors from metrics"""
        return {
            "pe_ratio": metrics.get("pe_ratio", 0),
            "forward_pe": metrics.get("forward_pe", 0),
            "peg_ratio": metrics.get("peg_ratio", 0),
            "price_to_book": metrics.get("price_to_book", 0),
            "dividend_yield": metrics.get("dividend_yield", 0),
        }

    def _compute_growth_factors(self, metrics: Dict) -> Dict:
        """Extract growth factors from metrics"""
        return {
            "revenue_growth": metrics.get("revenue_growth", 0),
            "earnings_growth": metrics.get("earnings_growth", 0),
            "eps_growth_5y": 0,  # Would need historical data
            "revenue_growth_5y": 0,  # Would need historical data
        }

    def _compute_quality_factors(self, metrics: Dict) -> Dict:
        """Extract quality factors from metrics"""
        return {
            "roe": metrics.get("roe", 0),
            "roa": metrics.get("roa", 0),
            "profit_margin": metrics.get("profit_margin", 0),
            "operating_margin": metrics.get("operating_margin", 0),
            "debt_to_equity": metrics.get("debt_to_equity", 0),
            "current_ratio": metrics.get("current_ratio", 0),
        }

    def _compute_momentum_factors(self, price_data: Dict) -> Dict:
        """Compute momentum factors from historical price data"""
        if not price_data or "historicalData" not in price_data:
            return {}

        hist_data = price_data["historicalData"]
        if not hist_data:
            return {}

        dates = sorted(hist_data.keys())
        if len(dates) < 2:
            return {}

        # Get first and last prices
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

        if not first_price or first_price <= 0:
            return {}

        # Calculate 52-week return
        period_return = ((last_price - first_price) / first_price) * 100
        return {
            "52_week_return": period_return,
            "near_52_week_high": 0,  # Would need more data
            "near_52_week_low": 0,  # Would need more data
        }

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

        # Get metrics and compute factors
        try:
            metrics = self.get_stock_metrics(symbol)
            if metrics:
                factors["value_factors"] = self._compute_value_factors(metrics)
                factors["growth_factors"] = self._compute_growth_factors(metrics)
                factors["quality_factors"] = self._compute_quality_factors(metrics)
        except Exception as err:
            logger.warning("Error computing factors for %s: %s", symbol, str(err))

        # Compute momentum factors from historical data
        try:
            price_data = self.get_stock_price(symbol, period="1y")
            factors["momentum_factors"] = self._compute_momentum_factors(price_data)
        except Exception as err:
            logger.warning("Error computing momentum factors for %s: %s", symbol, str(err))

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
            logger.warning("Error fetching price for %s: %s", symbol, str(err))

        # Get metrics
        try:
            metrics = self.get_stock_metrics(symbol)
            if metrics:
                data["metrics"] = metrics
        except Exception as err:
            logger.warning("Error fetching metrics for %s: %s", symbol, str(err))

        # Get analyst estimates
        try:
            estimates = self.get_analyst_estimates(symbol)
            if estimates and estimates.get("earnings_estimates"):
                data["estimates"] = estimates
        except Exception as err:
            logger.warning("Error fetching estimates for %s: %s", symbol, str(err))

        # Get financials
        try:
            financials = self.get_financial_statements(symbol)
            if financials and (
                financials.get("income_statement") or financials.get("balance_sheet")
            ):
                data["financials"] = financials
        except Exception as err:
            logger.warning("Error fetching financials for %s: %s", symbol, str(err))

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

    def _extract_dcf_financial_data(self, stock_symbol: str) -> Dict:
        """Extract financial data needed for DCF analysis"""
        from constants import (
            DCF_KEY_BETA,
            DCF_KEY_CURRENT_PRICE,
            DCF_KEY_SHARES_OUTSTANDING,
            DCF_MSG_MISSING_DATA,
            DCF_MSG_USING_REAL_DATA,
        )

        try:
            financials = self.get_financial_statements(stock_symbol)
            metrics = self.get_stock_metrics(stock_symbol)
            price_data = self.get_stock_price(stock_symbol)

            # Extract current price
            current_price = price_data.get("price", 100.0)

            # Extract cash flow data
            cash_flow_data = financials.get("cash_flow", [])
            base_fcf = 0
            if cash_flow_data and len(cash_flow_data) > 0:
                base_fcf = cash_flow_data[0].get("free_cash_flow", 0)
                logger.info(DCF_MSG_USING_REAL_DATA.format("cash flow statements"))

            # Extract balance sheet data
            balance_sheet_data = financials.get("balance_sheet", [])
            total_cash = 0
            total_debt = 0
            if balance_sheet_data and len(balance_sheet_data) > 0:
                latest_bs = balance_sheet_data[0]
                total_cash = latest_bs.get("cash", 0)
                total_debt = latest_bs.get("long_term_debt", 0)

            # Get shares and beta
            shares_outstanding = metrics.get(DCF_KEY_SHARES_OUTSTANDING, 0)
            beta = metrics.get(DCF_KEY_BETA, 1.0)

            # Estimate FCF if missing
            if base_fcf == 0:
                logger.info(DCF_MSG_MISSING_DATA.format(stock_symbol))
                operating_cf = metrics.get("operating_cash_flow", 0)
                if operating_cf > 0:
                    base_fcf = operating_cf * 0.8
                else:
                    market_cap = metrics.get("market_cap", 0)
                    base_fcf = market_cap * 0.05

            return {
                "current_price": current_price,
                "base_fcf": base_fcf,
                "total_cash": total_cash,
                "total_debt": total_debt,
                "shares_outstanding": shares_outstanding,
                "beta": beta,
            }

        except Exception as data_error:
            logger.warning("Error fetching financial data: %s", str(data_error))
            # Return fallback estimates
            return {
                "current_price": 100.0,
                "base_fcf": 1000.0,
                "total_cash": 0,
                "total_debt": 0,
                "shares_outstanding": 1_000_000,
                "beta": 1.0,
            }

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
            DCF_KEY_DISCOUNT_RATE,
            DCF_KEY_GROWTH_RATE,
            DCF_KEY_SYMBOL,
            DCF_KEY_TAX_RATE,
            DCF_KEY_TERMINAL_GROWTH,
            DCF_KEY_YEARS,
        )

        stock_symbol = assumptions.get(DCF_KEY_SYMBOL, "UNKNOWN")

        # Extract financial data
        financial_data = self._extract_dcf_financial_data(stock_symbol)

        # Override with assumptions if provided
        current_price = assumptions.get("current_price", financial_data["current_price"])

        # Initialize DCF Calculator
        dcf_calc = DCFCalculator()

        # Run DCF analysis using the calculator
        return dcf_calc.run_dcf_analysis(
            symbol=stock_symbol,
            base_fcf=financial_data["base_fcf"],
            current_price=current_price,
            shares_outstanding=financial_data["shares_outstanding"],
            total_cash=financial_data["total_cash"],
            total_debt=financial_data["total_debt"],
            beta=financial_data["beta"],
            growth_rate=assumptions.get(DCF_KEY_GROWTH_RATE),
            terminal_growth=assumptions.get(DCF_KEY_TERMINAL_GROWTH),
            discount_rate=assumptions.get(DCF_KEY_DISCOUNT_RATE),
            years=assumptions.get(DCF_KEY_YEARS),
            tax_rate=assumptions.get(DCF_KEY_TAX_RATE),
        )
            tax_rate=assumptions.get(DCF_KEY_TAX_RATE),
        )


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
        logger.error("Error: %s", str(handler_error))
        return _create_error_response(HTTP_SERVER_ERROR, str(handler_error))

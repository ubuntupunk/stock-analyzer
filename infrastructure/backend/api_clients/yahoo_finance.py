"""
Yahoo Finance API Client
Primary data source - Uses yfinance library (handles authentication internally)
"""

import time
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

from constants import (
    DATE_FORMAT_YYYY_MM,
    DATE_FORMAT_YYYY_MM_DD,
    DEFAULT_EMPTY_STRING,
    DEFAULT_SOURCE_YAHOO,
    DEFAULT_TITLE_NO_TITLE,
    DEFAULT_URL_HASH,
    DEFAULT_VALUE_NA,
    DEFAULT_VALUE_ZERO,
    HIST_KEY_CLOSE,
    HIST_KEY_HIGH,
    HIST_KEY_LOW,
    HIST_KEY_OPEN,
    HIST_KEY_VOLUME,
    UNIX_TIMESTAMP_MAX,
    YF_BALANCE_CASH,
    YF_BALANCE_LONG_TERM_DEBT,
    YF_BALANCE_STOCKHOLDERS_EQUITY,
    YF_BALANCE_TOTAL_ASSETS,
    YF_BALANCE_TOTAL_LIABILITIES,
    YF_CASHFLOW_CAPEX,
    YF_CASHFLOW_DIVIDENDS,
    YF_CASHFLOW_FREE,
    YF_CASHFLOW_OPERATING,
    YF_CASHFLOW_STOCK_REPURCHASED,
    YF_DEFAULT_TIMEOUT_SECONDS,
    YF_INCOME_EBITDA,
    YF_INCOME_GROSS_PROFIT,
    YF_INCOME_NET_INCOME,
    YF_INCOME_OPERATING_INCOME,
    YF_INCOME_TOTAL_REVENUE,
    YF_KEY_AVERAGE_VOLUME,
    YF_KEY_BETA,
    YF_KEY_CURRENT_PRICE,
    YF_KEY_CURRENT_RATIO,
    YF_KEY_DEBT_TO_EQUITY,
    YF_KEY_DIVIDEND_YIELD,
    YF_KEY_EARNINGS_GROWTH,
    YF_KEY_EPS_CURRENT_YEAR,
    YF_KEY_EPS_FORWARD,
    YF_KEY_EPS_TRAILING_TWELVE_MONTHS,
    YF_KEY_FIFTY_DAY_AVERAGE,
    YF_KEY_FIFTY_TWO_WEEK_HIGH,
    YF_KEY_FIFTY_TWO_WEEK_LOW,
    YF_KEY_FORWARD_PE,
    YF_KEY_FREE_CASHFLOW,
    YF_KEY_LONG_NAME,
    YF_KEY_MARKET_CAP,
    YF_KEY_NUMBER_OF_ANALYST_OPINIONS,
    YF_KEY_OPERATING_CASHFLOW,
    YF_KEY_OPERATING_MARGINS,
    YF_KEY_PEG_RATIO,
    YF_KEY_PRICE_TO_BOOK,
    YF_KEY_PROFIT_MARGINS,
    YF_KEY_RECOMMENDATION_KEY,
    YF_KEY_RECOMMENDATION_MEAN,
    YF_KEY_REGULAR_MARKET_CHANGE,
    YF_KEY_REGULAR_MARKET_CHANGE_PERCENT,
    YF_KEY_REGULAR_MARKET_DAY_HIGH,
    YF_KEY_REGULAR_MARKET_DAY_LOW,
    YF_KEY_REGULAR_MARKET_PREVIOUS_CLOSE,
    YF_KEY_REGULAR_MARKET_PRICE,
    YF_KEY_REGULAR_MARKET_VOLUME,
    YF_KEY_RETURN_ON_ASSETS,
    YF_KEY_RETURN_ON_EQUITY,
    YF_KEY_REVENUE_GROWTH,
    YF_KEY_SHARES_OUTSTANDING,
    YF_KEY_SHORT_NAME,
    YF_KEY_TARGET_HIGH_PRICE,
    YF_KEY_TARGET_LOW_PRICE,
    YF_KEY_TARGET_MEAN_PRICE,
    YF_KEY_TARGET_MEDIAN_PRICE,
    YF_KEY_TOTAL_REVENUE,
    YF_KEY_TRAILING_EPS,
    YF_KEY_TRAILING_PE,
    YF_KEY_TWO_HUNDRED_DAY_AVERAGE,
    YF_LONG_TIMEOUT_SECONDS,
    YF_MAX_FINANCIAL_YEARS,
    YF_MAX_NEWS_ARTICLES,
    YF_MAX_SUMMARY_LENGTH,
    YF_NEWS_CANONICAL_URL,
    YF_NEWS_CAPTION,
    YF_NEWS_DESCRIPTION,
    YF_NEWS_DISPLAY_NAME,
    YF_NEWS_HEADLINE,
    YF_NEWS_LINK,
    YF_NEWS_PROVIDER,
    YF_NEWS_PROVIDER_PUBLISH_TIME,
    YF_NEWS_PUB_DATE,
    YF_NEWS_SNIPPET,
    YF_NEWS_SUMMARY,
    YF_NEWS_TITLE,
    YF_NEWS_URL,
)


class YahooFinanceClient:
    """Client for Yahoo Finance API using yfinance library"""

    def __init__(self, timeout_seconds: float = YF_DEFAULT_TIMEOUT_SECONDS):
        self.base_url = "https://query2.finance.yahoo.com/v10/finance/quoteSummary"
        self.timeout = timeout_seconds

    def _fetch_with_timeout(self, func, timeout: float = None):
        """Execute a function with timeout protection"""
        timeout_value = timeout or self.timeout

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func)
            try:
                return future.result(timeout=timeout_value)
            except FuturesTimeoutError:
                logger.warning(f"YFinance timeout after {timeout_value}s")
                return None

    def fetch_data(self, symbol: str, modules: str = None) -> Optional[Dict]:
        """
        Fetch data from Yahoo Finance using yfinance
        With timeout protection to prevent hanging
        """

        def _fetch():
            try:
                ticker = yf.Ticker(symbol)
                ticker_info = ticker.info
                if ticker_info:
                    return ticker_info
                return None
            except Exception as fetch_error:
                logger.error(f"YFinance error for {symbol}: {str(fetch_error)}")
                return None

        start_time = time.time()
        fetch_result = self._fetch_with_timeout(_fetch)
        latency_ms = (time.time() - start_time) * 1000

        if fetch_result is None:
            logger.warning(
                f"YFinance fetch for {symbol} timed out or failed ({latency_ms:.0f}ms)"
            )

        return fetch_result

    async def fetch_data_async(self, session, symbol: str, modules: str = None):
        """
        Async version of fetch_data using yfinance
        Returns: (symbol, data) tuple
        With timeout protection
        """

        def _fetch():
            ticker = yf.Ticker(symbol)
            return ticker.info

        loop = asyncio.get_event_loop()
        try:
            start_time = time.time()
            ticker_info = await loop.run_in_executor(None, _fetch)
            latency_ms = (time.time() - start_time) * 1000

            if ticker_info:
                has_price = (
                    YF_KEY_CURRENT_PRICE in ticker_info
                    or YF_KEY_REGULAR_MARKET_PRICE in ticker_info
                )
                logger.debug(
                    f"YFinance async: {symbol} - info keys: {len(ticker_info)}, "
                    f"has price key: {has_price} ({latency_ms:.0f}ms)"
                )
                return (symbol, ticker_info)

            logger.debug(
                f"YFinance async: {symbol} - info is empty or None ({latency_ms:.0f}ms)"
            )
            return (symbol, None)
        except asyncio.TimeoutError:
            logger.warning(f"YFinance async: {symbol} - timeout after {self.timeout}s")
            return (symbol, None)
        except Exception as async_error:
            logger.error(f"YFinance async error for {symbol}: {str(async_error)}")
            return (symbol, None)

    def parse_price(self, data: Dict) -> Dict:
        """Parse Yahoo Finance price data"""
        price_info = {}
        try:
            price_info["price"] = data.get(
                YF_KEY_CURRENT_PRICE,
                data.get(YF_KEY_REGULAR_MARKET_PRICE, DEFAULT_VALUE_ZERO),
            )
            price_info["open"] = data.get("open", DEFAULT_VALUE_ZERO)
            price_info["high"] = data.get(
                "dayHigh", data.get(YF_KEY_REGULAR_MARKET_DAY_HIGH, DEFAULT_VALUE_ZERO)
            )
            price_info["low"] = data.get(
                "dayLow", data.get(YF_KEY_REGULAR_MARKET_DAY_LOW, DEFAULT_VALUE_ZERO)
            )
            price_info["volume"] = data.get(
                "volume", data.get(YF_KEY_REGULAR_MARKET_VOLUME, DEFAULT_VALUE_ZERO)
            )
            price_info["previous_close"] = data.get(
                "previousClose",
                data.get(YF_KEY_REGULAR_MARKET_PREVIOUS_CLOSE, DEFAULT_VALUE_ZERO),
            )
            price_info["change"] = data.get(
                "change", data.get(YF_KEY_REGULAR_MARKET_CHANGE, DEFAULT_VALUE_ZERO)
            )
            price_info["change_percent"] = data.get(
                "changePercent",
                data.get(YF_KEY_REGULAR_MARKET_CHANGE_PERCENT, DEFAULT_VALUE_ZERO),
            )
        except Exception as parse_error:
            logger.error(f"Error parsing Yahoo Finance price: {str(parse_error)}")

        return price_info

    def _convert_history_to_dict(self, hist_dataframe: pd.DataFrame) -> Dict:
        """Convert pandas DataFrame history to dict format"""
        historical_data = {}
        for date, row in hist_dataframe.iterrows():
            date_str = date.strftime(DATE_FORMAT_YYYY_MM_DD)
            historical_data[date_str] = {
                HIST_KEY_OPEN: float(row["Open"]),
                HIST_KEY_HIGH: float(row["High"]),
                HIST_KEY_LOW: float(row["Low"]),
                HIST_KEY_CLOSE: float(row["Close"]),
                HIST_KEY_VOLUME: int(row["Volume"]),
            }
        return historical_data

    def fetch_history(self, symbol: str, period: str = "1mo") -> Optional[Dict]:
        """
        Fetch historical price data for charting
        Returns dict with dates as keys and OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            hist_dataframe = ticker.history(period=period)

            if hist_dataframe is None or hist_dataframe.empty:
                return None

            return self._convert_history_to_dict(hist_dataframe)
        except Exception as history_error:
            logger.error(f"YFinance history error for {symbol}: {str(history_error)}")
            return None

    def fetch_history_range(
        self, symbol: str, startDate: str, endDate: str
    ) -> Optional[Dict]:
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
            hist_dataframe = ticker.history(start=startDate, end=endDate)

            if hist_dataframe is None or hist_dataframe.empty:
                return None

            return self._convert_history_to_dict(hist_dataframe)
        except Exception as history_error:
            logger.error(f"YFinance history range error for {symbol}: {str(history_error)}")
            return None

    def parse_history(self, historical_data: Dict) -> Dict:
        """Parse historical data into price format with historicalData key"""
        return {"historicalData": historical_data}

    def parse_metrics(self, data: Dict) -> Dict:
        """Parse Yahoo Finance data into standard metrics format"""
        metrics = {}

        try:
            metrics["company_name"] = data.get(
                YF_KEY_SHORT_NAME, data.get(YF_KEY_LONG_NAME, DEFAULT_VALUE_NA)
            )
            metrics["current_price"] = data.get(
                YF_KEY_CURRENT_PRICE,
                data.get(YF_KEY_REGULAR_MARKET_PRICE, DEFAULT_VALUE_ZERO),
            )
            metrics["change"] = data.get(
                YF_KEY_REGULAR_MARKET_CHANGE, DEFAULT_VALUE_ZERO
            )
            metrics["change_percent"] = data.get(
                YF_KEY_REGULAR_MARKET_CHANGE_PERCENT, DEFAULT_VALUE_ZERO
            )
            metrics["market_cap"] = data.get(YF_KEY_MARKET_CAP, DEFAULT_VALUE_ZERO)
            metrics["shares_outstanding"] = data.get(
                YF_KEY_SHARES_OUTSTANDING, DEFAULT_VALUE_ZERO
            )
            metrics["revenue"] = data.get(YF_KEY_TOTAL_REVENUE, DEFAULT_VALUE_ZERO)
            metrics["pe_ratio"] = data.get(YF_KEY_TRAILING_PE, DEFAULT_VALUE_ZERO)
            metrics["forward_pe"] = data.get(YF_KEY_FORWARD_PE, DEFAULT_VALUE_ZERO)
            metrics["peg_ratio"] = data.get(YF_KEY_PEG_RATIO, DEFAULT_VALUE_ZERO)
            metrics["price_to_book"] = data.get(
                YF_KEY_PRICE_TO_BOOK, DEFAULT_VALUE_ZERO
            )
            metrics["dividend_yield"] = data.get(
                YF_KEY_DIVIDEND_YIELD, DEFAULT_VALUE_ZERO
            )
            metrics["52_week_high"] = data.get(
                YF_KEY_FIFTY_TWO_WEEK_HIGH, DEFAULT_VALUE_ZERO
            )
            metrics["52_week_low"] = data.get(
                YF_KEY_FIFTY_TWO_WEEK_LOW, DEFAULT_VALUE_ZERO
            )
            metrics["50_day_avg"] = data.get(
                YF_KEY_FIFTY_DAY_AVERAGE, DEFAULT_VALUE_ZERO
            )
            metrics["200_day_avg"] = data.get(
                YF_KEY_TWO_HUNDRED_DAY_AVERAGE, DEFAULT_VALUE_ZERO
            )
            metrics["volume"] = data.get("volume", DEFAULT_VALUE_ZERO)
            metrics["avg_volume"] = data.get(YF_KEY_AVERAGE_VOLUME, DEFAULT_VALUE_ZERO)
            metrics["beta"] = data.get(YF_KEY_BETA, DEFAULT_VALUE_ZERO)
            metrics["eps"] = data.get(YF_KEY_TRAILING_EPS, DEFAULT_VALUE_ZERO)
            metrics["revenue_growth"] = data.get(
                YF_KEY_REVENUE_GROWTH, DEFAULT_VALUE_ZERO
            )
            metrics["earnings_growth"] = data.get(
                YF_KEY_EARNINGS_GROWTH, DEFAULT_VALUE_ZERO
            )
            metrics["profit_margin"] = data.get(
                YF_KEY_PROFIT_MARGINS, DEFAULT_VALUE_ZERO
            )
            metrics["operating_margin"] = data.get(
                YF_KEY_OPERATING_MARGINS, DEFAULT_VALUE_ZERO
            )
            metrics["roe"] = data.get(YF_KEY_RETURN_ON_EQUITY, DEFAULT_VALUE_ZERO)
            metrics["roa"] = data.get(YF_KEY_RETURN_ON_ASSETS, DEFAULT_VALUE_ZERO)
            metrics["debt_to_equity"] = data.get(
                YF_KEY_DEBT_TO_EQUITY, DEFAULT_VALUE_ZERO
            )
            metrics["current_ratio"] = data.get(
                YF_KEY_CURRENT_RATIO, DEFAULT_VALUE_ZERO
            )
            metrics["free_cash_flow"] = data.get(
                YF_KEY_FREE_CASHFLOW, DEFAULT_VALUE_ZERO
            )
            metrics["operating_cash_flow"] = data.get(
                YF_KEY_OPERATING_CASHFLOW, DEFAULT_VALUE_ZERO
            )

        except Exception as parse_error:
            logger.error(f"Error parsing Yahoo Finance metrics: {str(parse_error)}")

        return metrics

    def _create_estimate_entry(
        self,
        period: str,
        avg_value: float,
        low_value: float = 0,
        high_value: float = 0,
        num_analysts: int = 0,
    ) -> Dict:
        """Create a standardized estimate entry"""
        return {
            "period": period,
            "avg": avg_value,
            "low": low_value,
            "high": high_value,
            "num_analysts": num_analysts,
        }

    def parse_estimates(self, data: Dict) -> Dict:
        """Parse Yahoo Finance analyst estimates"""
        estimates = {}
        try:
            # Price targets
            estimates[YF_KEY_CURRENT_PRICE] = data.get(
                YF_KEY_CURRENT_PRICE,
                data.get(YF_KEY_REGULAR_MARKET_PRICE, DEFAULT_VALUE_ZERO),
            )
            estimates[YF_KEY_TARGET_MEAN_PRICE] = data.get(
                YF_KEY_TARGET_MEAN_PRICE, DEFAULT_VALUE_ZERO
            )
            estimates[YF_KEY_TARGET_HIGH_PRICE] = data.get(
                YF_KEY_TARGET_HIGH_PRICE, DEFAULT_VALUE_ZERO
            )
            estimates[YF_KEY_TARGET_LOW_PRICE] = data.get(
                YF_KEY_TARGET_LOW_PRICE, DEFAULT_VALUE_ZERO
            )
            estimates[YF_KEY_TARGET_MEDIAN_PRICE] = data.get(
                YF_KEY_TARGET_MEDIAN_PRICE, DEFAULT_VALUE_ZERO
            )

            # Analyst ratings
            estimates[YF_KEY_RECOMMENDATION_MEAN] = data.get(
                YF_KEY_RECOMMENDATION_MEAN, DEFAULT_VALUE_ZERO
            )
            estimates[YF_KEY_RECOMMENDATION_KEY] = data.get(
                YF_KEY_RECOMMENDATION_KEY, DEFAULT_VALUE_NA
            )
            estimates[YF_KEY_NUMBER_OF_ANALYST_OPINIONS] = data.get(
                YF_KEY_NUMBER_OF_ANALYST_OPINIONS, DEFAULT_VALUE_ZERO
            )

            # EPS estimates
            estimates[YF_KEY_EPS_FORWARD] = data.get(
                YF_KEY_EPS_FORWARD, DEFAULT_VALUE_ZERO
            )
            estimates[YF_KEY_EPS_CURRENT_YEAR] = data.get(
                YF_KEY_EPS_CURRENT_YEAR, DEFAULT_VALUE_ZERO
            )
            estimates[YF_KEY_EPS_TRAILING_TWELVE_MONTHS] = data.get(
                YF_KEY_EPS_TRAILING_TWELVE_MONTHS, DEFAULT_VALUE_ZERO
            )

            # Build earnings estimates list
            earnings_list = []
            revenue_list = []

            if YF_KEY_TARGET_MEAN_PRICE in data:
                earnings_list.append(
                    self._create_estimate_entry(
                        "Price Target",
                        data.get(YF_KEY_TARGET_MEAN_PRICE, DEFAULT_VALUE_ZERO),
                        data.get(YF_KEY_TARGET_LOW_PRICE, DEFAULT_VALUE_ZERO),
                        data.get(YF_KEY_TARGET_HIGH_PRICE, DEFAULT_VALUE_ZERO),
                        data.get(YF_KEY_NUMBER_OF_ANALYST_OPINIONS, DEFAULT_VALUE_ZERO),
                    )
                )

            if data.get(YF_KEY_EPS_CURRENT_YEAR):
                earnings_list.append(
                    self._create_estimate_entry(
                        "Current Year EPS",
                        data.get(YF_KEY_EPS_CURRENT_YEAR, DEFAULT_VALUE_ZERO),
                    )
                )

            if data.get(YF_KEY_EPS_FORWARD):
                earnings_list.append(
                    self._create_estimate_entry(
                        "Next Year EPS",
                        data.get(YF_KEY_EPS_FORWARD, DEFAULT_VALUE_ZERO),
                    )
                )

            estimates["earnings_estimates"] = earnings_list
            estimates["revenue_estimates"] = revenue_list

        except Exception as parse_error:
            logger.error(f"Error parsing Yahoo Finance estimates: {str(parse_error)}")

        return estimates

    def _safe_get_financial_value(
        self, dataframe: pd.DataFrame, row_key: str, column_date
    ) -> float:
        """Safely extract financial value from DataFrame"""
        if row_key in dataframe.index and not pd.isna(
            dataframe.loc[row_key, column_date]
        ):
            return float(dataframe.loc[row_key, column_date])
        return DEFAULT_VALUE_ZERO

    def _format_fiscal_date(self, date_value) -> str:
        """Format fiscal date to YYYY-MM format"""
        if hasattr(date_value, "strftime"):
            return date_value.strftime(DATE_FORMAT_YYYY_MM)
        return str(date_value)

    def _parse_income_statement(self, ticker) -> List[Dict]:
        """Parse income statement from ticker object"""
        try:
            financials = ticker.financials
            if financials is None or financials.empty:
                return []

            income_statement = []
            for date in financials.columns[:YF_MAX_FINANCIAL_YEARS]:
                income_statement.append(
                    {
                        "fiscal_date": self._format_fiscal_date(date),
                        "revenue": self._safe_get_financial_value(
                            financials, YF_INCOME_TOTAL_REVENUE, date
                        ),
                        "net_income": self._safe_get_financial_value(
                            financials, YF_INCOME_NET_INCOME, date
                        ),
                        "ebitda": self._safe_get_financial_value(
                            financials, YF_INCOME_EBITDA, date
                        ),
                        "gross_profit": self._safe_get_financial_value(
                            financials, YF_INCOME_GROSS_PROFIT, date
                        ),
                        "operating_income": self._safe_get_financial_value(
                            financials, YF_INCOME_OPERATING_INCOME, date
                        ),
                    }
                )
            return income_statement
        except Exception as parse_error:
            logger.error(f"Error parsing income statement: {str(parse_error)}")
            return []

    def _parse_balance_sheet(self, ticker) -> List[Dict]:
        """Parse balance sheet from ticker object"""
        try:
            balance_sheet = ticker.balance_sheet
            if balance_sheet is None or balance_sheet.empty:
                return []

            balance_data = []
            for date in balance_sheet.columns[:YF_MAX_FINANCIAL_YEARS]:
                balance_data.append(
                    {
                        "fiscal_date": self._format_fiscal_date(date),
                        "total_assets": self._safe_get_financial_value(
                            balance_sheet, YF_BALANCE_TOTAL_ASSETS, date
                        ),
                        "total_liabilities": self._safe_get_financial_value(
                            balance_sheet, YF_BALANCE_TOTAL_LIABILITIES, date
                        ),
                        "shareholders_equity": self._safe_get_financial_value(
                            balance_sheet, YF_BALANCE_STOCKHOLDERS_EQUITY, date
                        ),
                        "cash": self._safe_get_financial_value(
                            balance_sheet, YF_BALANCE_CASH, date
                        ),
                        "long_term_debt": self._safe_get_financial_value(
                            balance_sheet, YF_BALANCE_LONG_TERM_DEBT, date
                        ),
                    }
                )
            return balance_data
        except Exception as parse_error:
            logger.error(f"Error parsing balance sheet: {str(parse_error)}")
            return []

    def _parse_cash_flow(self, ticker) -> List[Dict]:
        """Parse cash flow statement from ticker object"""
        try:
            cashflow = ticker.cashflow
            if cashflow is None or cashflow.empty:
                return []

            cash_flow = []
            for date in cashflow.columns[:YF_MAX_FINANCIAL_YEARS]:
                cash_flow.append(
                    {
                        "fiscal_date": self._format_fiscal_date(date),
                        "operating_cashflow": self._safe_get_financial_value(
                            cashflow, YF_CASHFLOW_OPERATING, date
                        ),
                        "free_cash_flow": self._safe_get_financial_value(
                            cashflow, YF_CASHFLOW_FREE, date
                        ),
                        "capex": self._safe_get_financial_value(
                            cashflow, YF_CASHFLOW_CAPEX, date
                        ),
                        "dividends_paid": self._safe_get_financial_value(
                            cashflow, YF_CASHFLOW_DIVIDENDS, date
                        ),
                        "stock_repurchased": self._safe_get_financial_value(
                            cashflow, YF_CASHFLOW_STOCK_REPURCHASED, date
                        ),
                    }
                )
            return cash_flow
        except Exception as parse_error:
            logger.error(f"Error parsing cash flow: {str(parse_error)}")
            return []

    def _create_fallback_financials(self, data: Dict) -> Dict:
        """Create fallback financial data from info dict"""
        return {
            "income_statement": [
                {
                    "revenue": data.get(YF_KEY_TOTAL_REVENUE, DEFAULT_VALUE_ZERO),
                    "net_income": data.get("netIncomeToCommon", DEFAULT_VALUE_ZERO),
                    "ebitda": data.get("ebitda", DEFAULT_VALUE_ZERO),
                }
            ],
            "balance_sheet": [
                {
                    "total_assets": data.get("totalAssets", DEFAULT_VALUE_ZERO),
                    "total_liabilities": data.get(
                        "totalLiabilities", DEFAULT_VALUE_ZERO
                    ),
                    "shareholders_equity": data.get(
                        "totalStockholderEquity", DEFAULT_VALUE_ZERO
                    ),
                    "cash": data.get("cash", DEFAULT_VALUE_ZERO),
                }
            ],
            "cash_flow": [
                {
                    "operating_cashflow": data.get(
                        YF_KEY_OPERATING_CASHFLOW, DEFAULT_VALUE_ZERO
                    ),
                    "free_cash_flow": data.get(
                        YF_KEY_FREE_CASHFLOW, DEFAULT_VALUE_ZERO
                    ),
                    "capex": data.get("capitalExpenditures", DEFAULT_VALUE_ZERO),
                }
            ],
        }

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

                parsed["income_statement"] = self._parse_income_statement(ticker)
                parsed["balance_sheet"] = self._parse_balance_sheet(ticker)
                parsed["cash_flow"] = self._parse_cash_flow(ticker)

            # Fallback to info dict if no ticker object or empty results
            has_no_income_statement = not parsed or not parsed.get("income_statement")
            if has_no_income_statement and data and isinstance(data, dict):
                parsed = self._create_fallback_financials(data)

        except Exception as parse_error:
            logger.error(f"Error parsing Yahoo Finance financials: {str(parse_error)}")
            parsed = {"income_statement": [], "balance_sheet": [], "cash_flow": []}

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
        except Exception as fetch_error:
            logger.error(f"YFinance fetch_financials error for {symbol}: {str(fetch_error)}")
            return {"income_statement": [], "balance_sheet": [], "cash_flow": []}

    def _extract_news_source(self, provider_data) -> str:
        """Extract source name from provider data"""
        if isinstance(provider_data, dict):
            return (
                provider_data.get(YF_NEWS_DISPLAY_NAME)
                or provider_data.get(KEY_NAME)
                or provider_data.get("id")
                or DEFAULT_SOURCE_YAHOO
            )
        if provider_data:
            return str(provider_data)
        return DEFAULT_SOURCE_YAHOO

    def _extract_news_title(self, news_item: Dict) -> str:
        """Extract title from news item"""
        return (
            news_item.get(YF_NEWS_TITLE)
            or news_item.get(YF_NEWS_HEADLINE)
            or news_item.get(YF_NEWS_CAPTION)
            or DEFAULT_TITLE_NO_TITLE
        )

    def _extract_news_url(self, news_item: Dict) -> str:
        """Extract URL from news item"""
        return (
            news_item.get(YF_NEWS_LINK)
            or news_item.get(YF_NEWS_URL)
            or news_item.get(YF_NEWS_CANONICAL_URL)
            or DEFAULT_URL_HASH
        )

    def _extract_news_summary(self, news_item: Dict) -> str:
        """Extract and truncate summary from news item"""
        summary_text = (
            news_item.get(YF_NEWS_SUMMARY)
            or news_item.get(YF_NEWS_DESCRIPTION)
            or news_item.get(YF_NEWS_SNIPPET)
            or DEFAULT_EMPTY_STRING
        )
        if summary_text:
            return summary_text[:YF_MAX_SUMMARY_LENGTH]
        return DEFAULT_EMPTY_STRING

    def _convert_publish_time(self, pub_time) -> str:
        """Convert publish time to ISO format"""
        if not pub_time:
            return datetime.now().isoformat()

        try:
            # Try as Unix timestamp first (seconds)
            if isinstance(pub_time, (int, float)) and pub_time < UNIX_TIMESTAMP_MAX:
                return datetime.fromtimestamp(pub_time).isoformat()
            return str(pub_time)
        except Exception:
            return str(pub_time)

    def _parse_news_item(self, news_item: Dict) -> Dict:
        """Parse a single news item into standardized format"""
        provider_data = news_item.get(YF_NEWS_PROVIDER)
        source = self._extract_news_source(provider_data)
        title = self._extract_news_title(news_item)
        url = self._extract_news_url(news_item)
        summary = self._extract_news_summary(news_item)

        pub_time = news_item.get(YF_NEWS_PROVIDER_PUBLISH_TIME)
        if not pub_time:
            pub_time = news_item.get(YF_NEWS_PUB_DATE, DEFAULT_EMPTY_STRING)

        pub_date = self._convert_publish_time(pub_time)

        return {
            "title": title,
            "url": url,
            "publishedAt": pub_date,
            "source": source,
            "summary": summary,
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

            news_count = len(news_data) if news_data else 0
            logger.debug(f"YFinance fetch_news for {symbol}: received {news_count} items")

            if news_data and len(news_data) > 0:
                # Log first item structure for debugging
                logger.debug(f"YFinance news sample for {symbol}:")
                logger.debug(f"  First item keys: {list(news_data[0].keys())}")
                logger.debug(f"  First item: {news_data[0]}")

                articles = [
                    self._parse_news_item(news_item)
                    for news_item in news_data[:YF_MAX_NEWS_ARTICLES]
                ]
                return articles
            return []
        except Exception as fetch_error:
            logger.error(f"YFinance fetch_news error for {symbol}: {str(fetch_error)}")
            import traceback

            traceback.print_exc()
            return []

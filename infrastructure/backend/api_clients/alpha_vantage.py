"""
Alpha Vantage API Client
Fallback data source - FREE but RATE LIMITED (5 calls/minute on free tier)
"""

import os
import time
import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

from constants import (
    AV_BALANCE_CASH,
    AV_BALANCE_CURRENT_ASSETS,
    AV_BALANCE_CURRENT_LIABILITIES,
    AV_BALANCE_DEBT,
    AV_BALANCE_SHAREHOLDER_EQUITY,
    AV_BALANCE_TOTAL_ASSETS,
    AV_BALANCE_TOTAL_LIABILITIES,
    AV_CASHFLOW_CAPEX,
    AV_CASHFLOW_DIVIDENDS,
    AV_CASHFLOW_OPERATING,
    AV_DEFAULT_TIMEOUT,
    AV_DEFAULT_WAIT_TIME,
    AV_EARNINGS_ESTIMATED_EPS,
    AV_EARNINGS_FISCAL_DATE,
    AV_EARNINGS_REPORTED_EPS,
    AV_EARNINGS_SURPRISE,
    AV_EARNINGS_SURPRISE_PERCENT,
    AV_FUNCTION_BALANCE_SHEET,
    AV_FUNCTION_CASH_FLOW,
    AV_FUNCTION_EARNINGS,
    AV_FUNCTION_GLOBAL_QUOTE,
    AV_FUNCTION_INCOME_STATEMENT,
    AV_FUNCTION_OVERVIEW,
    AV_INCOME_COST_OF_REVENUE,
    AV_INCOME_EBITDA,
    AV_INCOME_EPS,
    AV_INCOME_GROSS_PROFIT,
    AV_INCOME_NET_INCOME,
    AV_INCOME_OPERATING_EXPENSES,
    AV_INCOME_OPERATING_INCOME,
    AV_INCOME_TOTAL_REVENUE,
    AV_KEY_200_DAY_MA,
    AV_KEY_50_DAY_MA,
    AV_KEY_52_WEEK_HIGH,
    AV_KEY_52_WEEK_LOW,
    AV_KEY_ANNUAL_REPORTS,
    AV_KEY_BETA,
    AV_KEY_DIVIDEND_YIELD,
    AV_KEY_EARNINGS_GROWTH_YOY,
    AV_KEY_EPS,
    AV_KEY_FORWARD_PE,
    AV_KEY_GLOBAL_QUOTE,
    AV_KEY_MARKET_CAP,
    AV_KEY_NAME,
    AV_KEY_NOTE,
    AV_KEY_OPERATING_MARGIN,
    AV_KEY_PE_RATIO,
    AV_KEY_PEG_RATIO,
    AV_KEY_PRICE_TO_BOOK,
    AV_KEY_PROFIT_MARGIN,
    AV_KEY_QUARTERLY_EARNINGS,
    AV_KEY_REVENUE_GROWTH_YOY,
    AV_KEY_REVENUE_PER_SHARE,
    AV_KEY_ROA,
    AV_KEY_ROE,
    AV_KEY_SYMBOL,
    AV_MAX_ANNUAL_REPORTS,
    AV_MAX_QUARTERS,
    AV_MAX_RETRIES,
    AV_MSG_API_LIMIT,
    AV_MSG_ERROR,
    AV_MSG_HTTP_ERROR,
    AV_MSG_RATE_LIMITED_WAIT,
    AV_MSG_RATE_LIMIT_HIT,
    AV_MSG_TIMEOUT,
    AV_QUOTE_CHANGE,
    AV_QUOTE_CHANGE_PERCENT,
    AV_QUOTE_PREVIOUS_CLOSE,
    AV_QUOTE_PRICE,
    AV_QUOTE_TRADING_DAY,
    AV_QUOTE_VOLUME,
    AV_RATE_LIMIT_CALLS,
    AV_RATE_LIMIT_PERIOD,
    DEFAULT_API_KEY_DEMO,
    DEFAULT_VALUE_NA,
    DEFAULT_VALUE_ZERO,
    ENV_FINANCIAL_API_KEY,
    HEADER_RETRY_AFTER,
    HTTP_OK,
    HTTP_RATE_LIMIT,
    KEY_SYMBOL,
    PARAM_APIKEY,
    PARAM_FUNCTION,
    STRING_NONE,
    STRING_PERCENT,
)


class AlphaVantageClient:
    """Client for Alpha Vantage API - rate limited fallback"""

    def __init__(self):
        self.api_key = os.environ.get(ENV_FINANCIAL_API_KEY, DEFAULT_API_KEY_DEMO)
        self.base_url = "https://www.alphavantage.co/query"
        self.timeout = AV_DEFAULT_TIMEOUT

        # Rate limiting tracking
        self._rate_limit_calls = []
        self._rate_limit_hits = 0

    def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits
        Returns True if within limits, False if limit exceeded
        """
        now = time.time()
        # Remove calls older than rate limit period
        self._rate_limit_calls = [
            call_time
            for call_time in self._rate_limit_calls
            if now - call_time < AV_RATE_LIMIT_PERIOD
        ]

        if len(self._rate_limit_calls) >= AV_RATE_LIMIT_CALLS:
            self._rate_limit_hits += 1
            logger.warning(AV_MSG_RATE_LIMIT_HIT.format(self._rate_limit_hits))
            return False

        return True

    def _record_api_call(self):
        """Record an API call for rate limiting"""
        self._rate_limit_calls.append(time.time())

    def _should_retry_after(self, response) -> Optional[int]:
        """
        Check if response indicates rate limiting with Retry-After header
        Returns seconds to wait, or None
        """
        if response.status_code == HTTP_RATE_LIMIT:
            retry_after = response.headers.get(HEADER_RETRY_AFTER)
            if retry_after:
                try:
                    return int(retry_after)
                except ValueError:
                    pass
            return AV_RATE_LIMIT_PERIOD
        return None

    def _calculate_wait_time(self) -> float:
        """Calculate wait time until rate limit resets"""
        if self._rate_limit_calls:
            wait_time = AV_RATE_LIMIT_PERIOD - (time.time() - self._rate_limit_calls[0])
            return max(wait_time, AV_DEFAULT_WAIT_TIME)
        return AV_RATE_LIMIT_PERIOD

    def _is_rate_limit_response(self, response_data: Dict) -> bool:
        """Check if response contains rate limit message"""
        note_text = response_data.get(AV_KEY_NOTE, "")
        return AV_KEY_NOTE in response_data and AV_MSG_API_LIMIT.split()[0] in note_text

    def _fetch_with_retry(
        self, url: str, params: Dict, max_retries: int = AV_MAX_RETRIES
    ) -> Optional[Dict]:
        """Fetch data with rate limit handling and retries"""
        for attempt in range(max_retries):
            # Check rate limit before making call
            if not self._check_rate_limit():
                wait_time = self._calculate_wait_time()
                logger.warning(AV_MSG_RATE_LIMITED_WAIT.format(f"{wait_time:.0f}"))
                time.sleep(wait_time)
                continue

            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                self._record_api_call()

                # Check for rate limiting
                retry_after = self._should_retry_after(response)
                if retry_after is not None:
                    logger.warning(AV_MSG_RATE_LIMITED_WAIT.format(retry_after))
                    time.sleep(retry_after)
                    continue

                if response.status_code == HTTP_OK:
                    response_data = response.json()

                    # Check for API limit message
                    if self._is_rate_limit_response(response_data):
                        logger.warning(AV_MSG_API_LIMIT)
                        self._rate_limit_hits += 1
                        if attempt < max_retries - 1:
                            time.sleep(AV_RATE_LIMIT_PERIOD)
                            continue
                        return None
                    return response_data

                logger.error(AV_MSG_HTTP_ERROR.format(response.status_code))

            except requests.Timeout:
                logger.warning(AV_MSG_TIMEOUT.format(attempt + 1, max_retries))
            except Exception as fetch_error:
                logger.error(AV_MSG_ERROR.format(str(fetch_error)))

        return None

    def fetch_overview(self, symbol: str) -> Optional[Dict]:
        """Fetch company overview from Alpha Vantage"""
        params = {
            PARAM_FUNCTION: AV_FUNCTION_OVERVIEW,
            KEY_SYMBOL: symbol,
            PARAM_APIKEY: self.api_key,
        }

        fetch_result = self._fetch_with_retry(self.base_url, params)
        if fetch_result and AV_KEY_SYMBOL in fetch_result:
            return fetch_result
        return None

    def fetch_quote(self, symbol: str) -> Optional[Dict]:
        """Fetch real-time quote from Alpha Vantage"""
        params = {
            PARAM_FUNCTION: AV_FUNCTION_GLOBAL_QUOTE,
            KEY_SYMBOL: symbol,
            PARAM_APIKEY: self.api_key,
        }

        fetch_result = self._fetch_with_retry(self.base_url, params)
        if fetch_result:
            return fetch_result.get(AV_KEY_GLOBAL_QUOTE, {})
        return None

    def fetch_earnings(self, symbol: str) -> Optional[Dict]:
        """Fetch earnings data from Alpha Vantage"""
        params = {
            PARAM_FUNCTION: AV_FUNCTION_EARNINGS,
            KEY_SYMBOL: symbol,
            PARAM_APIKEY: self.api_key,
        }
        return self._fetch_with_retry(self.base_url, params)

    def fetch_income_statement(self, symbol: str) -> Optional[Dict]:
        """Fetch income statement from Alpha Vantage"""
        params = {
            PARAM_FUNCTION: AV_FUNCTION_INCOME_STATEMENT,
            KEY_SYMBOL: symbol,
            PARAM_APIKEY: self.api_key,
        }
        return self._fetch_with_retry(self.base_url, params)

    def fetch_balance_sheet(self, symbol: str) -> Optional[Dict]:
        """Fetch balance sheet from Alpha Vantage"""
        params = {
            PARAM_FUNCTION: AV_FUNCTION_BALANCE_SHEET,
            KEY_SYMBOL: symbol,
            PARAM_APIKEY: self.api_key,
        }
        return self._fetch_with_retry(self.base_url, params)

    def fetch_cash_flow(self, symbol: str) -> Optional[Dict]:
        """Fetch cash flow from Alpha Vantage"""
        params = {
            PARAM_FUNCTION: AV_FUNCTION_CASH_FLOW,
            KEY_SYMBOL: symbol,
            PARAM_APIKEY: self.api_key,
        }
        return self._fetch_with_retry(self.base_url, params)

    def _safe_float(self, value, default=DEFAULT_VALUE_ZERO):
        """Safely convert value to float"""
        try:
            return float(value) if value and value != STRING_NONE else default
        except (ValueError, TypeError):
            return default

    def parse_metrics(self, data: Dict) -> Dict:
        """Parse Alpha Vantage data into standard metrics format"""
        metrics = {}

        try:
            metrics["company_name"] = data.get(AV_KEY_NAME, DEFAULT_VALUE_NA)
            metrics["market_cap"] = self._safe_float(data.get(AV_KEY_MARKET_CAP))
            metrics["pe_ratio"] = self._safe_float(data.get(AV_KEY_PE_RATIO))
            metrics["forward_pe"] = self._safe_float(data.get(AV_KEY_FORWARD_PE))
            metrics["peg_ratio"] = self._safe_float(data.get(AV_KEY_PEG_RATIO))
            metrics["price_to_book"] = self._safe_float(data.get(AV_KEY_PRICE_TO_BOOK))
            metrics["dividend_yield"] = self._safe_float(
                data.get(AV_KEY_DIVIDEND_YIELD)
            )
            metrics["52_week_high"] = self._safe_float(data.get(AV_KEY_52_WEEK_HIGH))
            metrics["52_week_low"] = self._safe_float(data.get(AV_KEY_52_WEEK_LOW))
            metrics["50_day_avg"] = self._safe_float(data.get(AV_KEY_50_DAY_MA))
            metrics["200_day_avg"] = self._safe_float(data.get(AV_KEY_200_DAY_MA))
            metrics["beta"] = self._safe_float(data.get(AV_KEY_BETA))
            metrics["eps"] = self._safe_float(data.get(AV_KEY_EPS))
            metrics["revenue_per_share"] = self._safe_float(
                data.get(AV_KEY_REVENUE_PER_SHARE)
            )
            metrics["profit_margin"] = self._safe_float(data.get(AV_KEY_PROFIT_MARGIN))
            metrics["operating_margin"] = self._safe_float(
                data.get(AV_KEY_OPERATING_MARGIN)
            )
            metrics["roe"] = self._safe_float(data.get(AV_KEY_ROE))
            metrics["roa"] = self._safe_float(data.get(AV_KEY_ROA))
            metrics["revenue_growth_yoy"] = self._safe_float(
                data.get(AV_KEY_REVENUE_GROWTH_YOY)
            )
            metrics["earnings_growth_yoy"] = self._safe_float(
                data.get(AV_KEY_EARNINGS_GROWTH_YOY)
            )

        except Exception as parse_error:
            logger.error(f"Error parsing Alpha Vantage metrics: {str(parse_error)}")

        return metrics

    def parse_price(self, data: Dict) -> Dict:
        """Parse Alpha Vantage quote data"""
        price_info = {}
        try:
            price_info["price"] = float(data.get(AV_QUOTE_PRICE, DEFAULT_VALUE_ZERO))
            price_info["volume"] = int(data.get(AV_QUOTE_VOLUME, DEFAULT_VALUE_ZERO))
            price_info["previous_close"] = float(
                data.get(AV_QUOTE_PREVIOUS_CLOSE, DEFAULT_VALUE_ZERO)
            )
            price_info["change"] = float(data.get(AV_QUOTE_CHANGE, DEFAULT_VALUE_ZERO))

            change_percent_str = data.get(AV_QUOTE_CHANGE_PERCENT, "0").replace(
                STRING_PERCENT, ""
            )
            price_info["change_percent"] = float(change_percent_str)
            price_info["timestamp"] = data.get(AV_QUOTE_TRADING_DAY, "")
        except Exception as parse_error:
            logger.error(f"Error parsing Alpha Vantage price: {str(parse_error)}")

        return price_info

    def _parse_earnings_quarter(self, quarter: Dict) -> Dict:
        """Parse a single quarter's earnings data"""
        return {
            "period": quarter.get(AV_EARNINGS_FISCAL_DATE, ""),
            "reported_eps": float(
                quarter.get(AV_EARNINGS_REPORTED_EPS, DEFAULT_VALUE_ZERO)
            ),
            "estimated_eps": float(
                quarter.get(AV_EARNINGS_ESTIMATED_EPS, DEFAULT_VALUE_ZERO)
            ),
            "surprise": float(quarter.get(AV_EARNINGS_SURPRISE, DEFAULT_VALUE_ZERO)),
            "surprise_percent": float(
                quarter.get(AV_EARNINGS_SURPRISE_PERCENT, DEFAULT_VALUE_ZERO)
            ),
        }

    def parse_estimates(self, data: Dict) -> Dict:
        """Parse Alpha Vantage earnings data"""
        estimates = {}
        try:
            quarterly_earnings = data.get(AV_KEY_QUARTERLY_EARNINGS, [])

            earnings_list = [
                self._parse_earnings_quarter(quarter)
                for quarter in quarterly_earnings[:AV_MAX_QUARTERS]
            ]

            estimates["earnings_estimates"] = earnings_list

        except Exception as parse_error:
            logger.error(f"Error parsing Alpha Vantage estimates: {str(parse_error)}")

        return estimates

    def _parse_income_report(self, report: Dict) -> Dict:
        """Parse a single income statement report"""
        return {
            "fiscal_date": report.get(AV_EARNINGS_FISCAL_DATE, ""),
            "revenue": int(report.get(AV_INCOME_TOTAL_REVENUE, DEFAULT_VALUE_ZERO)),
            "cost_of_revenue": int(
                report.get(AV_INCOME_COST_OF_REVENUE, DEFAULT_VALUE_ZERO)
            ),
            "gross_profit": int(report.get(AV_INCOME_GROSS_PROFIT, DEFAULT_VALUE_ZERO)),
            "operating_expenses": int(
                report.get(AV_INCOME_OPERATING_EXPENSES, DEFAULT_VALUE_ZERO)
            ),
            "operating_income": int(
                report.get(AV_INCOME_OPERATING_INCOME, DEFAULT_VALUE_ZERO)
            ),
            "net_income": int(report.get(AV_INCOME_NET_INCOME, DEFAULT_VALUE_ZERO)),
            "ebitda": int(report.get(AV_INCOME_EBITDA, DEFAULT_VALUE_ZERO)),
            "eps": float(report.get(AV_INCOME_EPS, DEFAULT_VALUE_ZERO)),
        }

    def parse_income(self, data: Dict) -> List[Dict]:
        """Parse Alpha Vantage income statement"""
        statements = []
        try:
            annual_reports = data.get(AV_KEY_ANNUAL_REPORTS, [])
            statements = [
                self._parse_income_report(report)
                for report in annual_reports[:AV_MAX_ANNUAL_REPORTS]
            ]
        except Exception as parse_error:
            logger.error(f"Error parsing income statement: {str(parse_error)}")
        return statements

    def _parse_balance_report(self, report: Dict) -> Dict:
        """Parse a single balance sheet report"""
        return {
            "fiscal_date": report.get(AV_EARNINGS_FISCAL_DATE, ""),
            "total_assets": int(
                report.get(AV_BALANCE_TOTAL_ASSETS, DEFAULT_VALUE_ZERO)
            ),
            "current_assets": int(
                report.get(AV_BALANCE_CURRENT_ASSETS, DEFAULT_VALUE_ZERO)
            ),
            "total_liabilities": int(
                report.get(AV_BALANCE_TOTAL_LIABILITIES, DEFAULT_VALUE_ZERO)
            ),
            "current_liabilities": int(
                report.get(AV_BALANCE_CURRENT_LIABILITIES, DEFAULT_VALUE_ZERO)
            ),
            "shareholders_equity": int(
                report.get(AV_BALANCE_SHAREHOLDER_EQUITY, DEFAULT_VALUE_ZERO)
            ),
            "cash": int(report.get(AV_BALANCE_CASH, DEFAULT_VALUE_ZERO)),
            "debt": int(report.get(AV_BALANCE_DEBT, DEFAULT_VALUE_ZERO)),
        }

    def parse_balance(self, data: Dict) -> List[Dict]:
        """Parse Alpha Vantage balance sheet"""
        statements = []
        try:
            annual_reports = data.get(AV_KEY_ANNUAL_REPORTS, [])
            statements = [
                self._parse_balance_report(report)
                for report in annual_reports[:AV_MAX_ANNUAL_REPORTS]
            ]
        except Exception as parse_error:
            logger.error(f"Error parsing balance sheet: {str(parse_error)}")
        return statements

    def _parse_cashflow_report(self, report: Dict) -> Dict:
        """Parse a single cash flow report"""
        operating_cf = int(report.get(AV_CASHFLOW_OPERATING, DEFAULT_VALUE_ZERO))
        capex = int(report.get(AV_CASHFLOW_CAPEX, DEFAULT_VALUE_ZERO))

        return {
            "fiscal_date": report.get(AV_EARNINGS_FISCAL_DATE, ""),
            "operating_cashflow": operating_cf,
            "capex": capex,
            "free_cash_flow": operating_cf - abs(capex),
            "dividends_paid": int(
                report.get(AV_CASHFLOW_DIVIDENDS, DEFAULT_VALUE_ZERO)
            ),
        }

    def parse_cashflow(self, data: Dict) -> List[Dict]:
        """Parse Alpha Vantage cash flow statement"""
        statements = []
        try:
            annual_reports = data.get(AV_KEY_ANNUAL_REPORTS, [])
            statements = [
                self._parse_cashflow_report(report)
                for report in annual_reports[:AV_MAX_ANNUAL_REPORTS]
            ]
        except Exception as parse_error:
            logger.error(f"Error parsing cash flow: {str(parse_error)}")
        return statements

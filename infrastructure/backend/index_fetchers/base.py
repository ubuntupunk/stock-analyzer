"""
Base Index Fetcher

Abstract base class for index constituent fetchers.
Implement specific logic for each data source (Wikipedia, ETF holdings, official sites).
"""

from abc import ABC, abstractmethod
import logging
import yfinance as yf
from typing import Optional

logger = logging.getLogger(__name__)


class IndexFetcher(ABC):
    """
    Abstract base class for index constituent fetchers

    Each fetcher implementation must provide:
    - fetch_constituents(): Fetch the list of stocks for the index
    - normalize_symbol(): Add exchange prefix/suffix if needed
    - apply_fx_conversion(): Convert market cap to USD if needed
    """

    def __init__(self, config: dict):
        """
        Initialize fetcher with index configuration

        Args:
            config: Index configuration dict from IndexConfig
        """
        self.config = config
        self.id = config["id"]
        self.name = config["name"]
        self.region = config["region"]
        self.currency = config["currency"]
        self.exchange = config["exchange"]
        self.exchange_suffix = config.get("exchangeSuffix", "")
        self.data_source = config["dataSource"]
        self.url = config["url"]

    @abstractmethod
    def fetch_constituents(self) -> list:
        """
        Fetch list of stocks for this index

        Returns:
            List of dicts with keys:
            - symbol: Stock ticker (with exchange suffix if applicable)
            - name: Company name
            - sector: Industry sector
            - subSector: Industry sub-sector (optional)
            - region: Region code (e.g., 'US', 'ZA')
            - currency: Currency code (e.g., 'USD', 'ZAR')
            - exchange: Exchange name
        """
        pass

    def normalize_symbol(self, symbol: str) -> str:
        """
        Add exchange suffix if needed

        E.g., 'AGL' -> 'AGL.JO' for JSE stocks
        E.g., 'BRK.B' -> 'BRK-B' for US stocks

        Args:
            symbol: Raw stock symbol

        Returns:
            Normalized symbol with exchange suffix
        """
        # Remove any dots from US symbols (yfinance uses hyphens)
        if self.region == "US" and "." in symbol and self.exchange_suffix == "":
            return symbol.replace(".", "-")

        # Add exchange suffix if not already present
        if self.exchange_suffix and not symbol.endswith(self.exchange_suffix):
            return f"{symbol}{self.exchange_suffix}"

        return symbol

    def apply_fx_conversion(
        self, amount: float, fx_rate: Optional[float] = None
    ) -> float:
        """
        Convert amount to USD if needed

        Args:
            amount: Amount in local currency
            fx_rate: Exchange rate (local currency per 1 USD)
                    If None, will fetch live rate from yfinance

        Returns:
            Amount converted to USD
        """
        if self.currency == "USD":
            return amount

        if fx_rate is None:
            fx_rate = self.get_fx_rate()

        if fx_rate and fx_rate > 0:
            return amount / fx_rate

        return amount

    def get_fx_rate(self) -> float:
        """
        Get current FX rate to USD

        Returns:
            Exchange rate (local currency per 1 USD)
            Returns 1.0 if no conversion needed or error occurs
        """
        if self.currency == "USD":
            return 1.0

        fx_config = self.config.get("fxRate", {})
        fx_symbol = fx_config.get("symbol")
        source = fx_config.get("source")

        if not fx_symbol:
            return 1.0

        try:
            if source == "yfinance":
                ticker = yf.Ticker(fx_symbol)
                info = ticker.info
                rate = info.get("regularMarketPrice") or info.get("previousClose")

                if rate and rate > 0:
                    return float(rate)
        except Exception as err:
            logger.warning(f"Error fetching FX rate for {fx_symbol}: {err}")

        return 1.0

    def format_stock(
        self, symbol: str, name: str, sector: str, subSector: str = ""
    ) -> dict:
        """
        Format stock data to standard structure

        Args:
            symbol: Raw stock symbol
            name: Company name
            sector: Industry sector
            subSector: Industry sub-sector (optional)

        Returns:
            Formatted stock dict
        """
        return {
            "symbol": self.normalize_symbol(symbol),
            "name": name,
            "sector": sector,
            "subSector": subSector,
            "region": self.region,
            "currency": self.currency,
            "exchange": self.exchange,
        }

    def get_market_cap_bucket(self, market_cap_usd: float) -> str:
        """
        Categorize stock by market cap bucket

        Uses index-specific thresholds if available, else defaults

        Args:
            market_cap_usd: Market cap in USD

        Returns:
            Bucket name: 'mega', 'large', 'mid', 'small', or 'unknown'
        """
        thresholds = self.config.get("marketCapThresholds", {})

        mega_threshold = thresholds.get("mega", 200_000_000_000)
        large_threshold = thresholds.get("large", 10_000_000_000)
        mid_threshold = thresholds.get("mid", 2_000_000_000)

        if market_cap_usd >= mega_threshold:
            return "mega"
        elif market_cap_usd >= large_threshold:
            return "large"
        elif market_cap_usd >= mid_threshold:
            return "mid"
        elif market_cap_usd > 0:
            return "small"
        else:
            return "unknown"

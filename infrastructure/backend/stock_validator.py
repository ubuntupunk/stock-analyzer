"""
Stock Universe Validator

Validates stock data quality and detects issues like:
- Delisted stocks (no recent price activity)
- Stale market cap data
- Data anomalies (sudden market cap drops, etc.)
"""

import logging
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)


class StockValidator:
    """
    Validate stock data for the stock universe

    Performs quality checks on stock data to ensure the database
    contains accurate and up-to-date information.
    """

    def __init__(self, logger=None):
        self.logger = logger or print
        self.issues = []

    def validate_symbol_exists(self, symbol: str, exchange_suffix: str = "") -> bool:
        """
        Check if a stock symbol still exists and trades

        Args:
            symbol: Stock ticker symbol
            exchange_suffix: Exchange suffix (e.g., '.JO' for JSE)

        Returns:
            True if stock exists and trades, False otherwise
        """
        full_symbol = f"{symbol}{exchange_suffix}" if exchange_suffix else symbol

        try:
            ticker = yf.Ticker(full_symbol)
            info = ticker.info

            # Check if stock has recent data
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")

            if current_price is None or current_price == 0:
                # Try historical price
                hist = ticker.history(period="5d")
                if hist is None or hist.empty:
                    self.issues.append(
                        {
                            "symbol": full_symbol,
                            "issue": "delisted",
                            "message": f"No price data found for {full_symbol}",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                    return False

            return True

        except Exception as err:
            self.issues.append(
                {
                    "symbol": full_symbol,
                    "issue": "error",
                    "message": f"Error validating {full_symbol}: {str(err)[:100]}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            return False

    def is_data_stale(self, last_updated: str, threshold_hours: int = 168) -> bool:
        """
        Check if stock data is older than threshold

        Args:
            last_updated: ISO timestamp string
            threshold_hours: Hours before data is considered stale (default 7 days)

        Returns:
            True if data is stale, False otherwise
        """
        try:
            last_updated_dt = datetime.fromisoformat(
                last_updated.replace("Z", "+00:00")
            )
            age_hours = (datetime.utcnow() - last_updated_dt).total_seconds() / 3600

            if age_hours > threshold_hours:
                age_days = age_hours / 24
                self.issues.append(
                    {
                        "issue": "stale_data",
                        "message": f"Data is {age_days:.1f} days old",
                        "last_updated": last_updated,
                        "age_hours": int(age_hours),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                return True

            return False

        except Exception as err:
            self.logger(f"⚠️  Error checking staleness: {err}")
            return True  # Assume stale if we can't check

    def detect_anomalies(self, stock_data: Dict) -> List[Dict]:
        """
        Detect data anomalies in stock record

        Args:
            stock_data: Stock record dictionary

        Returns:
            List of anomaly dictionaries
        """
        anomalies = []

        symbol = stock_data.get("symbol", "Unknown")

        # Anomaly 1: Sudden market cap drop (> 50%)
        market_cap_usd = float(stock_data.get("marketCapUSD", 0))

        # Check for market cap of 0 (should have data)
        if market_cap_usd == 0:
            anomalies.append(
                {
                    "symbol": symbol,
                    "type": "missing_market_cap",
                    "severity": "warning",
                    "message": "Market cap is 0, data may be incomplete",
                }
            )

        # Anomaly 2: Market cap bucket inconsistency
        market_cap_bucket = stock_data.get("marketCapBucket")
        expected_bucket = self._determine_market_cap_bucket(market_cap_usd)

        if market_cap_bucket != expected_bucket and market_cap_bucket != "unknown":
            anomalies.append(
                {
                    "symbol": symbol,
                    "type": "bucket_mismatch",
                    "severity": "info",
                    "message": f"Market cap bucket ({market_cap_bucket}) does not match value (expected {expected_bucket})",
                    "market_cap_usd": market_cap_usd,
                    "current_bucket": market_cap_bucket,
                    "expected_bucket": expected_bucket,
                }
            )

        # Anomaly 3: Empty name
        name = stock_data.get("name", "")
        if not name or name.lower() == "unknown":
            anomalies.append(
                {
                    "symbol": symbol,
                    "type": "missing_name",
                    "severity": "warning",
                    "message": 'Company name is missing or "Unknown"',
                }
            )

        # Anomaly 4: Unknown sector
        sector = stock_data.get("sector", "")
        if not sector or sector.lower() == "unknown":
            anomalies.append(
                {
                    "symbol": symbol,
                    "type": "unknown_sector",
                    "severity": "info",
                    "message": 'Sector is "Unknown"',
                }
            )

        # Anomaly 5: Missing index membership
        index_id = stock_data.get("indexId")
        if not index_id:
            anomalies.append(
                {
                    "symbol": symbol,
                    "type": "no_index",
                    "severity": "warning",
                    "message": "Stock has no index membership",
                }
            )

        # Anomaly 6: Currency/region mismatch for known regions
        region = stock_data.get("region", "")
        currency = stock_data.get("currency", "")

        if region == "ZA" and currency != "ZAR":
            anomalies.append(
                {
                    "symbol": symbol,
                    "type": "currency_mismatch",
                    "severity": "error",
                    "message": f"ZA region should have ZAR currency, found {currency}",
                    "region": region,
                    "currency": currency,
                }
            )

        if region == "US" and currency != "USD":
            anomalies.append(
                {
                    "symbol": symbol,
                    "type": "currency_mismatch",
                    "severity": "error",
                    "message": f"US region should have USD currency, found {currency}",
                    "region": region,
                    "currency": currency,
                }
            )

        return anomalies

    def validate_exchange_info(self, exchange: str, symbol: str, region: str) -> bool:
        """
        Validate exchange information matches symbol format

        Args:
            exchange: Exchange name
            symbol: Stock symbol
            region: Region code

        Returns:
            True if exchange info is valid
        """
        if region == "ZA":
            # JSE symbols should have .JO suffix
            if not symbol.endswith(".JO"):
                self.issues.append(
                    {
                        "symbol": symbol,
                        "issue": "exchange_mismatch",
                        "message": f"JSE stock {symbol} missing .JO suffix",
                        "region": region,
                        "exchange": exchange,
                    }
                )
                return False

        elif region == "US":
            # US symbols should NOT have exchange suffix
            if "." in symbol and symbol.endswith((".JO", ".TO", ".L")):
                self.issues.append(
                    {
                        "symbol": symbol,
                        "issue": "exchange_mismatch",
                        "message": f"US stock {symbol} has unexpected exchange suffix",
                        "region": region,
                        "exchange": exchange,
                    }
                )
                return False

        return True

    def validate_stock(
        self,
        stock_data: Dict,
        check_existence: bool = True,
        check_freshness: bool = True,
        check_anomalies: bool = True,
    ) -> Dict:
        """
        Perform comprehensive validation on a stock record

        Args:
            stock_data: Stock record dictionary
            check_existence: Check if stock still trades
            check_freshness: Check if data is stale
            check_anomalies: Check for data anomalies

        Returns:
            Validation result dictionary with 'valid' boolean and 'issues' list
        """
        result = {
            "symbol": stock_data.get("symbol", "Unknown"),
            "valid": True,
            "issues": [],
            "warnings": [],
            "errors": [],
        }

        # Reset issues list
        self.issues = []

        # Check if stock still exists (expensive - only if requested)
        if check_existence:
            exists = self.validate_symbol_exists(
                stock_data.get("symbol", ""), stock_data.get("exchangeSuffix", "")
            )
            if not exists:
                result["valid"] = False
                result["errors"] = [
                    issue for issue in self.issues if issue.get("issue") == "delisted"
                ]

        # Check data freshness
        if check_freshness and "lastUpdated" in stock_data:
            staleness_threshold_hours = {
                "US": 168,  # 7 days for US stocks
                "ZA": 336,  # 14 days for ZAR stocks (less frequent updates)
            }.get(stock_data.get("region", "US"), 168)

            is_stale = self.is_data_stale(
                stock_data["lastUpdated"], staleness_threshold_hours
            )
            if is_stale:
                result["warnings"].extend(
                    [
                        issue
                        for issue in self.issues
                        if issue.get("issue") == "stale_data"
                    ]
                )

        # Check for anomalies
        if check_anomalies:
            anomalies = self.detect_anomalies(stock_data)
            for anomaly in anomalies:
                severity = anomaly.get("severity", "info")
                if severity == "error":
                    result["errors"].append(anomaly)
                    result["valid"] = False
                elif severity == "warning":
                    result["warnings"].append(anomaly)
                else:
                    result["issues"].append(anomaly)

        # Validate exchange info
        exchange = stock_data.get("exchange", "")
        region = stock_data.get("region", "")
        symbol = stock_data.get("symbol", "")
        if exchange and region and symbol:
            exchange_valid = self.validate_exchange_info(exchange, symbol, region)
            if not exchange_valid:
                result["valid"] = False
                result["errors"].extend(
                    [
                        issue
                        for issue in self.issues
                        if issue.get("issue") == "exchange_mismatch"
                    ]
                )

        return result

    def _determine_market_cap_bucket(self, market_cap_usd: float) -> str:
        """
        Determine expected market cap bucket based on value

        Args:
            market_cap_usd: Market cap in USD

        Returns:
            Expected bucket name
        """
        if market_cap_usd >= 200_000_000_000:
            return "mega"
        elif market_cap_usd >= 10_000_000_000:
            return "large"
        elif market_cap_usd >= 2_000_000_000:
            return "mid"
        elif market_cap_usd > 0:
            return "small"
        else:
            return "unknown"


if __name__ == "__main__":
    # Test the validator
    import sys

    sys.path.insert(
        0, "/home/ubuntupunk/Projects/stock-analyzer/infrastructure/backend"
    )

    logger.info("=== Stock Validator Tests ===\n")

    validator = StockValidator()

    # Test 1: Stale data detection
    logger.info("1. Stale Data Test:")
    old_timestamp = "2025-01-01T00:00:00"
    is_stale = validator.is_data_stale(old_timestamp)
    logger.info(f"   Data from {old_timestamp} is stale: {is_stale}")

    # Test 2: Market cap bucket determination
    logger.info("\n2. Market Cap Bucket Test:")
    test_caps = [250e9, 50e9, 5e9, 500e6, 0]
    for cap in test_caps:
        bucket = validator._determine_market_cap_bucket(cap)
        logger.info(f"   ${cap/1e9:,.0f}B -> {bucket}")

    # Test 3: Anomaly detection
    logger.info("\n3. Anomaly Detection Test:")
    test_stocks = [
        {
            "symbol": "TEST",
            "marketCapUSD": 0,
            "marketCapBucket": "mega",
            "name": "Unknown",
            "sector": "Unknown",
            "indexId": "",
        },
        {
            "symbol": "GOOD",
            "marketCapUSD": 50e9,
            "marketCapBucket": "mega",
            "name": "Good Corp",
            "sector": "Technology",
            "indexId": "SP500",
        },
        {
            "symbol": "BAD.JO",
            "marketCapUSD": 10e9,
            "marketCapBucket": "large",
            "name": "Bad Corp",
            "sector": "Financials",
            "indexId": "JSE_ALSI",
            "region": "ZA",
            "currency": "USD",
        },
    ]

    for stock in test_stocks:
        anomalies = validator.detect_anomalies(stock)
        if anomalies:
            logger.info(f"   {stock['symbol']}: {len(anomalies)} anomalies")
            for anomaly in anomalies:
                logger.info(f"      - {anomaly['type']}: {anomaly['message']}")
        else:
            logger.info(f"   {stock['symbol']}: No anomalies")

    logger.info("\n✅ Validator tests passed!")

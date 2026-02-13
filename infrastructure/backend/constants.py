"""
Constants used across the backend application.
Centralizes repeated strings, magic numbers, and configuration values.
"""

# HTTP Status Codes
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_METHOD_NOT_ALLOWED = 405
HTTP_RATE_LIMIT = 429
HTTP_SERVER_ERROR = 500

# API Response Keys
KEY_SYMBOL = "symbol"
KEY_NAME = "name"
KEY_ERROR = "error"
KEY_MESSAGE = "message"
KEY_STATUS_CODE = "statusCode"
KEY_BODY = "body"
KEY_SUCCESS = "success"
KEY_ITEMS = "Items"
KEY_COUNT = "Count"
KEY_REGION = "region"
KEY_CURRENCY = "currency"
KEY_SECTOR = "sector"
KEY_INDEX_ID = "indexId"
KEY_INDEX_IDS = "indexIds"
KEY_MARKET_CAP = "marketCap"
KEY_MARKET_CAP_USD = "marketCapUSD"
KEY_MARKET_CAP_BUCKET = "marketCapBucket"
KEY_LAST_UPDATED = "lastUpdated"

# DynamoDB GSI Names
GSI_INDEX_ID = "index-id-index"
GSI_REGION = "region-index"
GSI_CURRENCY = "currency-index"
GSI_SECTOR = "sector-index"

# CORS Headers
CORS_ALLOW_ORIGIN = "*"
CORS_ALLOW_HEADERS = (
    "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
)
CORS_ALLOW_METHODS_GET = "GET,OPTIONS"
CORS_ALLOW_METHODS_ALL = "GET,POST,PUT,DELETE,OPTIONS"

# Cache/Rate Limiting
CACHE_TTL_SECONDS = 3600
RATE_LIMIT_DELAY = 0.05
RETRY_DELAY = 0.10
MAX_RETRIES = 3

# Validation Limits
MAX_SYMBOLS_PER_REQUEST = 100
MIN_SYMBOL_LENGTH = 1
MAX_SYMBOL_LENGTH = 10
DEFAULT_SEARCH_LIMIT = 20
DEFAULT_POPULAR_LIMIT = 10
DEFAULT_INDEX_STOCKS_LIMIT = 100

# Market Cap Buckets (in USD)
MARKET_CAP_MEGA = "mega"  # >200B
MARKET_CAP_LARGE = "large"  # 10-200B
MARKET_CAP_MID = "mid"  # 2-10B
MARKET_CAP_SMALL = "small"  # <2B

MARKET_CAP_MEGA_THRESHOLD = 200_000_000_000
MARKET_CAP_LARGE_THRESHOLD = 10_000_000_000
MARKET_CAP_MID_THRESHOLD = 2_000_000_000

# Default Values
DEFAULT_SECTOR = "Unknown"
DEFAULT_MARKET_CAP = 0
DEFAULT_STATUS = "active"

# Environment Variables
ENV_STOCK_UNIVERSE_TABLE = "STOCK_UNIVERSE_TABLE"
DEFAULT_TABLE_NAME = "stock-universe"

# HTTP Methods
HTTP_METHOD_GET = "GET"
HTTP_METHOD_POST = "POST"
HTTP_METHOD_PUT = "PUT"
HTTP_METHOD_DELETE = "DELETE"
HTTP_METHOD_OPTIONS = "OPTIONS"

# API Paths
PATH_SEARCH = "/search"
PATH_POPULAR = "/popular"
PATH_SECTORS = "/sectors"
PATH_FILTER = "/filter"
PATH_SYMBOL = "/symbol/"
PATH_INDICES = "/indices"
PATH_STOCKS = "/stocks"

# Query Parameters
PARAM_QUERY = "q"
PARAM_LIMIT = "limit"
PARAM_REGION = "region"
PARAM_INDEX_ID = "indexId"
PARAM_CURRENCY = "currency"
PARAM_SECTOR = "sector"
PARAM_MIN_CAP = "minCap"
PARAM_MAX_CAP = "maxCap"
PARAM_MARKET_CAP_BUCKET = "marketCapBucket"

# Error Messages
ERROR_METHOD_NOT_ALLOWED = "Method not allowed"
ERROR_QUERY_REQUIRED = 'Query parameter "q" is required'
ERROR_INVALID_ENDPOINT = "Invalid endpoint"
ERROR_INTERNAL_SERVER = "Internal server error"
ERROR_INDEX_NOT_FOUND = "Index not found: {}"

# Sort Priority (for search relevance)
SORT_PRIORITY_EXACT_MATCH = 0
SORT_PRIORITY_STARTS_WITH = 1
SORT_PRIORITY_CONTAINS = 2


# Yahoo Finance Specific Constants
YF_DEFAULT_TIMEOUT_SECONDS = 10
YF_LONG_TIMEOUT_SECONDS = 30
YF_MAX_NEWS_ARTICLES = 20
YF_MAX_SUMMARY_LENGTH = 500
YF_MAX_FINANCIAL_YEARS = 4

# Yahoo Finance Data Keys
YF_KEY_CURRENT_PRICE = "currentPrice"
YF_KEY_REGULAR_MARKET_PRICE = "regularMarketPrice"
YF_KEY_REGULAR_MARKET_CHANGE = "regularMarketChange"
YF_KEY_REGULAR_MARKET_CHANGE_PERCENT = "regularMarketChangePercent"
YF_KEY_REGULAR_MARKET_DAY_HIGH = "regularMarketDayHigh"
YF_KEY_REGULAR_MARKET_DAY_LOW = "regularMarketDayLow"
YF_KEY_REGULAR_MARKET_VOLUME = "regularMarketVolume"
YF_KEY_REGULAR_MARKET_PREVIOUS_CLOSE = "regularMarketPreviousClose"
YF_KEY_SHORT_NAME = "shortName"
YF_KEY_LONG_NAME = "longName"
YF_KEY_MARKET_CAP = "marketCap"
YF_KEY_SHARES_OUTSTANDING = "sharesOutstanding"
YF_KEY_TOTAL_REVENUE = "totalRevenue"
YF_KEY_TRAILING_PE = "trailingPE"
YF_KEY_FORWARD_PE = "forwardPE"
YF_KEY_PEG_RATIO = "pegRatio"
YF_KEY_PRICE_TO_BOOK = "priceToBook"
YF_KEY_DIVIDEND_YIELD = "dividendYield"
YF_KEY_FIFTY_TWO_WEEK_HIGH = "fiftyTwoWeekHigh"
YF_KEY_FIFTY_TWO_WEEK_LOW = "fiftyTwoWeekLow"
YF_KEY_FIFTY_DAY_AVERAGE = "fiftyDayAverage"
YF_KEY_TWO_HUNDRED_DAY_AVERAGE = "twoHundredDayAverage"
YF_KEY_AVERAGE_VOLUME = "averageVolume"
YF_KEY_BETA = "beta"
YF_KEY_TRAILING_EPS = "trailingEps"
YF_KEY_REVENUE_GROWTH = "revenueGrowth"
YF_KEY_EARNINGS_GROWTH = "earningsGrowth"
YF_KEY_PROFIT_MARGINS = "profitMargins"
YF_KEY_OPERATING_MARGINS = "operatingMargins"
YF_KEY_RETURN_ON_EQUITY = "returnOnEquity"
YF_KEY_RETURN_ON_ASSETS = "returnOnAssets"
YF_KEY_DEBT_TO_EQUITY = "debtToEquity"
YF_KEY_CURRENT_RATIO = "currentRatio"
YF_KEY_FREE_CASHFLOW = "freeCashflow"
YF_KEY_OPERATING_CASHFLOW = "operatingCashflow"

# Yahoo Finance Estimate Keys
YF_KEY_TARGET_MEAN_PRICE = "targetMeanPrice"
YF_KEY_TARGET_HIGH_PRICE = "targetHighPrice"
YF_KEY_TARGET_LOW_PRICE = "targetLowPrice"
YF_KEY_TARGET_MEDIAN_PRICE = "targetMedianPrice"
YF_KEY_RECOMMENDATION_MEAN = "recommendationMean"
YF_KEY_RECOMMENDATION_KEY = "recommendationKey"
YF_KEY_NUMBER_OF_ANALYST_OPINIONS = "numberOfAnalystOpinions"
YF_KEY_EPS_FORWARD = "epsForward"
YF_KEY_EPS_CURRENT_YEAR = "epsCurrentYear"
YF_KEY_EPS_TRAILING_TWELVE_MONTHS = "epsTrailingTwelveMonths"

# Yahoo Finance Financial Statement Keys
YF_INCOME_TOTAL_REVENUE = "Total Revenue"
YF_INCOME_NET_INCOME = "Net Income"
YF_INCOME_EBITDA = "EBITDA"
YF_INCOME_GROSS_PROFIT = "Gross Profit"
YF_INCOME_OPERATING_INCOME = "Operating Income"

YF_BALANCE_TOTAL_ASSETS = "Total Assets"
YF_BALANCE_TOTAL_LIABILITIES = "Total Liabilities Net Minority Interest"
YF_BALANCE_STOCKHOLDERS_EQUITY = "Stockholders Equity"
YF_BALANCE_CASH = "Cash And Cash Equivalents"
YF_BALANCE_LONG_TERM_DEBT = "Long Term Debt"

YF_CASHFLOW_OPERATING = "Operating Cash Flow"
YF_CASHFLOW_FREE = "Free Cash Flow"
YF_CASHFLOW_CAPEX = "Capital Expenditure"
YF_CASHFLOW_DIVIDENDS = "Cash Dividends Paid"
YF_CASHFLOW_STOCK_REPURCHASED = "Repurchase Of Capital Stock"

# Yahoo Finance News Keys
YF_NEWS_PROVIDER = "provider"
YF_NEWS_TITLE = "title"
YF_NEWS_HEADLINE = "headline"
YF_NEWS_CAPTION = "caption"
YF_NEWS_LINK = "link"
YF_NEWS_URL = "url"
YF_NEWS_CANONICAL_URL = "canonicalUrl"
YF_NEWS_SUMMARY = "summary"
YF_NEWS_DESCRIPTION = "description"
YF_NEWS_SNIPPET = "snippet"
YF_NEWS_PROVIDER_PUBLISH_TIME = "providerPublishTime"
YF_NEWS_PUB_DATE = "pubDate"
YF_NEWS_DISPLAY_NAME = "displayName"

# Default Values
DEFAULT_VALUE_ZERO = 0
DEFAULT_VALUE_NA = "N/A"
DEFAULT_SOURCE_YAHOO = "Yahoo Finance"
DEFAULT_TITLE_NO_TITLE = "No Title"
DEFAULT_URL_HASH = "#"
DEFAULT_EMPTY_STRING = ""

# Historical Data Keys
HIST_KEY_OPEN = "1. open"
HIST_KEY_HIGH = "2. high"
HIST_KEY_LOW = "3. low"
HIST_KEY_CLOSE = "4. close"
HIST_KEY_VOLUME = "5. volume"

# Date Format
DATE_FORMAT_YYYY_MM_DD = "%Y-%m-%d"
DATE_FORMAT_YYYY_MM = "%Y-%m"

# Unix Timestamp Threshold (for validation)
UNIX_TIMESTAMP_MAX = 9999999999


# Alpha Vantage Specific Constants
AV_RATE_LIMIT_CALLS = 5
AV_RATE_LIMIT_PERIOD = 60  # seconds
AV_DEFAULT_TIMEOUT = 10  # seconds
AV_MAX_RETRIES = 3
AV_DEFAULT_WAIT_TIME = 1
AV_MAX_QUARTERS = 4
AV_MAX_ANNUAL_REPORTS = 5

# Alpha Vantage API Functions
AV_FUNCTION_OVERVIEW = "OVERVIEW"
AV_FUNCTION_GLOBAL_QUOTE = "GLOBAL_QUOTE"
AV_FUNCTION_EARNINGS = "EARNINGS"
AV_FUNCTION_INCOME_STATEMENT = "INCOME_STATEMENT"
AV_FUNCTION_BALANCE_SHEET = "BALANCE_SHEET"
AV_FUNCTION_CASH_FLOW = "CASH_FLOW"

# Alpha Vantage Response Keys
AV_KEY_SYMBOL = "Symbol"
AV_KEY_NAME = "Name"
AV_KEY_GLOBAL_QUOTE = "Global Quote"
AV_KEY_NOTE = "Note"
AV_KEY_QUARTERLY_EARNINGS = "quarterlyEarnings"
AV_KEY_ANNUAL_REPORTS = "annualReports"

# Alpha Vantage Overview Keys
AV_KEY_MARKET_CAP = "MarketCapitalization"
AV_KEY_PE_RATIO = "PERatio"
AV_KEY_FORWARD_PE = "ForwardPE"
AV_KEY_PEG_RATIO = "PEGRatio"
AV_KEY_PRICE_TO_BOOK = "PriceToBookRatio"
AV_KEY_DIVIDEND_YIELD = "DividendYield"
AV_KEY_52_WEEK_HIGH = "52WeekHigh"
AV_KEY_52_WEEK_LOW = "52WeekLow"
AV_KEY_50_DAY_MA = "50DayMovingAverage"
AV_KEY_200_DAY_MA = "200DayMovingAverage"
AV_KEY_BETA = "Beta"
AV_KEY_EPS = "EPS"
AV_KEY_REVENUE_PER_SHARE = "RevenuePerShareTTM"
AV_KEY_PROFIT_MARGIN = "ProfitMargin"
AV_KEY_OPERATING_MARGIN = "OperatingMarginTTM"
AV_KEY_ROE = "ReturnOnEquityTTM"
AV_KEY_ROA = "ReturnOnAssetsTTM"
AV_KEY_REVENUE_GROWTH_YOY = "QuarterlyRevenueGrowthYOY"
AV_KEY_EARNINGS_GROWTH_YOY = "QuarterlyEarningsGrowthYOY"

# Alpha Vantage Quote Keys
AV_QUOTE_PRICE = "05. price"
AV_QUOTE_VOLUME = "06. volume"
AV_QUOTE_TRADING_DAY = "07. latest trading day"
AV_QUOTE_PREVIOUS_CLOSE = "08. previous close"
AV_QUOTE_CHANGE = "09. change"
AV_QUOTE_CHANGE_PERCENT = "10. change percent"

# Alpha Vantage Earnings Keys
AV_EARNINGS_FISCAL_DATE = "fiscalDateEnding"
AV_EARNINGS_REPORTED_EPS = "reportedEPS"
AV_EARNINGS_ESTIMATED_EPS = "estimatedEPS"
AV_EARNINGS_SURPRISE = "surprise"
AV_EARNINGS_SURPRISE_PERCENT = "surprisePercentage"

# Alpha Vantage Income Statement Keys
AV_INCOME_TOTAL_REVENUE = "totalRevenue"
AV_INCOME_COST_OF_REVENUE = "costOfRevenue"
AV_INCOME_GROSS_PROFIT = "grossProfit"
AV_INCOME_OPERATING_EXPENSES = "operatingExpenses"
AV_INCOME_OPERATING_INCOME = "operatingIncome"
AV_INCOME_NET_INCOME = "netIncome"
AV_INCOME_EBITDA = "ebitda"
AV_INCOME_EPS = "eps"

# Alpha Vantage Balance Sheet Keys
AV_BALANCE_TOTAL_ASSETS = "totalAssets"
AV_BALANCE_CURRENT_ASSETS = "totalCurrentAssets"
AV_BALANCE_TOTAL_LIABILITIES = "totalLiabilities"
AV_BALANCE_CURRENT_LIABILITIES = "totalCurrentLiabilities"
AV_BALANCE_SHAREHOLDER_EQUITY = "totalShareholderEquity"
AV_BALANCE_CASH = "cashAndCashEquivalentsAtCarryingValue"
AV_BALANCE_DEBT = "shortLongTermDebtTotal"

# Alpha Vantage Cash Flow Keys
AV_CASHFLOW_OPERATING = "operatingCashflow"
AV_CASHFLOW_CAPEX = "capitalExpenditures"
AV_CASHFLOW_DIVIDENDS = "dividendPayout"

# Alpha Vantage Error Messages
AV_MSG_RATE_LIMIT = "API rate limit"
AV_MSG_RATE_LIMIT_HIT = "Alpha Vantage rate limit hit! ({} total hits)"
AV_MSG_RATE_LIMITED_WAIT = "Alpha Vantage rate limited, waiting {}s..."
AV_MSG_TIMEOUT = "Alpha Vantage timeout (attempt {}/{})"
AV_MSG_HTTP_ERROR = "Alpha Vantage HTTP {}"
AV_MSG_ERROR = "Alpha Vantage error: {}"
AV_MSG_API_LIMIT = "Alpha Vantage API limit message received"

# Environment Variables
ENV_FINANCIAL_API_KEY = "FINANCIAL_API_KEY"
DEFAULT_API_KEY_DEMO = "demo"

# HTTP Headers
HEADER_RETRY_AFTER = "Retry-After"

# API Parameters
PARAM_FUNCTION = "function"
PARAM_APIKEY = "apikey"

# String Values
STRING_NONE = "None"
STRING_PERCENT = "%"


# Stock API Specific Constants
STOCK_API_DEFAULT_TIMEOUT = 10
STOCK_API_DEFAULT_CACHE_TIMEOUT = 300  # 5 minutes
STOCK_API_DEFAULT_PERIOD = "1mo"
STOCK_API_MAX_WORKERS = 4

# Stock API Paths
PATH_METRICS = "/metrics"
PATH_PRICE = "/price"
PATH_ESTIMATES = "/estimates"
PATH_FINANCIALS = "/financials"
PATH_HEALTH = "/health"
PATH_BATCH_PRICES = "/batch/prices"
PATH_BATCH_METRICS = "/batch/metrics"
PATH_BATCH_ESTIMATES = "/batch/estimates"
PATH_BATCH_FINANCIALS = "/batch/financials"
PATH_ALL = "/all"
PATH_NOT_FOUND = "/not-found"

# Stock API Error Messages
ERROR_SYMBOL_REQUIRED = "symbol required"
ERROR_SYMBOLS_REQUIRED = "symbols required"
ERROR_NOT_FOUND = "not found"
ERROR_METHOD_NOT_ALLOWED = "method not allowed"

# Stock API Response Keys
RESPONSE_KEY_STATUS = "status"
RESPONSE_KEY_CIRCUIT_BREAKER = "circuit_breaker"
RESPONSE_KEY_METRICS = "metrics"
RESPONSE_STATUS_HEALTHY = "healthy"

# Stock API Source Names
SOURCE_YAHOO_FINANCE = "yahoo_finance"
SOURCE_ALPACA = "alpaca"
SOURCE_POLYGON = "polygon"
SOURCE_ALPHA_VANTAGE = "alpha_vantage"

# Stock API Metrics Keys
METRICS_KEY_REQUESTS = "requests"
METRICS_KEY_TOTAL = "total"
METRICS_KEY_SUCCESS = "success"
METRICS_KEY_FAILED = "failed"
METRICS_KEY_SOURCES = "sources"
METRICS_KEY_LATENCY = "latency"
METRICS_KEY_TOTAL_MS = "total_ms"
METRICS_KEY_COUNT = "count"
METRICS_KEY_AVG_MS = "avg_ms"
METRICS_KEY_RATE_LIMITS = "rate_limits"
METRICS_KEY_TIMEOUTS = "timeouts"
METRICS_KEY_ERRORS = "errors"
METRICS_KEY_CALLS = "calls"
METRICS_KEY_SUCCESS_RATE = "success_rate"
METRICS_KEY_OTHER = "other"

# Stock API Cache Keys
CACHE_KEY_TIMESTAMP = "timestamp"
CACHE_KEY_DATA = "data"

# Stock API Config Keys
CONFIG_KEY_TIMEOUT = "timeout"
CONFIG_KEY_CACHE_TIMEOUT = "cache_timeout"
CONFIG_KEY_PRIORITIES = "priorities"

# Stock API Default Priorities
DEFAULT_PRIORITIES = [
    (SOURCE_YAHOO_FINANCE, 1),
    (SOURCE_ALPACA, 2),
    (SOURCE_POLYGON, 3),
    (SOURCE_ALPHA_VANTAGE, 4),
]

# Stock API Messages
MSG_CIRCUIT_OPEN = "Circuit OPEN for {}, skipping"
MSG_ALL_CIRCUITS_OPEN = "All circuits OPEN for {}"
MSG_PARALLEL_FETCH_SUCCESS = "Parallel fetch succeeded in {}ms"
MSG_TASK_FAILED = "Task failed: {}"
MSG_PARALLEL_FETCH_ERROR = "Parallel fetch error: {}"

# HTTP Request Keys
REQUEST_KEY_HTTP_METHOD = "httpMethod"
REQUEST_KEY_PATH = "path"
REQUEST_KEY_QUERY_STRING_PARAMS = "queryStringParameters"
REQUEST_KEY_BODY = "body"

# Query Parameter Keys
QUERY_PARAM_SYMBOL = "symbol"
QUERY_PARAM_SYMBOLS = "symbols"
QUERY_PARAM_PERIOD = "period"

# Response Format
RESPONSE_FORMAT_SUCCESS_RATE = "{:.1f}%"
RESPONSE_FORMAT_NA = "N/A"

# Delimiters
DELIMITER_COMMA = ","
DELIMITER_COLON = ":"

# Alpha Vantage Price Key (for checking data validity)
AV_PRICE_KEY = "05. price"


# Local Server Specific Constants
LOCAL_DEV_TOKEN = "local-dev-token"
LOCAL_DEV_USER_ID = "local-dev-user"
LOCAL_SERVER_PORT = 5000
LOCAL_SERVER_HOST = "0.0.0.0"

# Flask Route Paths
ROUTE_INDEX = "/"
ROUTE_STATIC = "/<path:filename>"
ROUTE_API_STOCK_PRICE = "/api/stock/price"
ROUTE_API_STOCK_PRICE_HISTORY = "/api/stock/price/history"
ROUTE_API_STOCK_METRICS = "/api/stock/metrics"
ROUTE_API_STOCK_ESTIMATES = "/api/stock/estimates"
ROUTE_API_STOCK_FINANCIALS = "/api/stock/financials"
ROUTE_API_STOCK_NEWS = "/api/stock/news"
ROUTE_API_STOCK_FACTORS = "/api/stock/factors"
ROUTE_API_STOCKS_SEARCH = "/api/stocks/search"
ROUTE_API_STOCKS_POPULAR = "/api/stocks/popular"
ROUTE_API_STOCK_BATCH_PRICES = "/api/stock/batch/prices"
ROUTE_API_STOCK_BATCH_METRICS = "/api/stock/batch/metrics"
ROUTE_API_STOCK_BATCH_ESTIMATES = "/api/stock/batch/estimates"
ROUTE_API_STOCK_BATCH_FINANCIALS = "/api/stock/batch/financials"
ROUTE_API_WATCHLIST = "/api/watchlist"
ROUTE_API_WATCHLIST_ITEM = "/api/watchlist/<symbol>"
ROUTE_API_SCREENER_SCREEN = "/api/screener/screen"
ROUTE_API_SCREENER_DCF = "/api/screener/dcf"
ROUTE_API_HEALTH = "/api/health"

# Flask Request Parameters
PARAM_START_DATE = "startDate"
PARAM_END_DATE = "endDate"
PARAM_MIN_PRICE = "minPrice"
PARAM_MAX_PRICE = "maxPrice"
PARAM_MIN_MARKET_CAP = "minMarketCap"
PARAM_MAX_MARKET_CAP = "maxMarketCap"
PARAM_MIN_PE = "minPE"
PARAM_MAX_PE = "maxPE"
PARAM_MIN_DIVIDEND_YIELD = "minDividendYield"

# Flask Response Keys
RESPONSE_KEY_STOCKS = "stocks"
RESPONSE_KEY_TOTAL = "total"
RESPONSE_KEY_FILTERED = "filtered"

# HTTP Headers
HEADER_AUTHORIZATION = "Authorization"
HEADER_BEARER_PREFIX = "Bearer "

# Error Messages
ERROR_AUTH_REQUIRED = "Authentication required for this resource."
ERROR_INVALID_TOKEN = "Warning: Invalid local dev token received: {}"
ERROR_SYMBOL_PARAM_REQUIRED = "symbol parameter is required"
ERROR_SYMBOLS_PARAM_REQUIRED = "symbols parameter is required"

# Flask Template Folder
TEMPLATE_FOLDER_FRONTEND = "../frontend"

# User Context Key
CONTEXT_KEY_USER_ID = "user_id"

# HTTP Status Codes (additional)
HTTP_UNAUTHORIZED = 401


# Circuit Breaker Constants
CB_DEFAULT_FAILURE_THRESHOLD = 5
CB_DEFAULT_SUCCESS_THRESHOLD = 2
CB_DEFAULT_TIMEOUT_SECONDS = 30.0
CB_DEFAULT_MONITORING_WINDOW = 60
CB_DEFAULT_HALF_OPEN_MAX_CALLS = 3
CB_DEFAULT_SUCCESS_RATE = 1.0
CB_DEFAULT_LATENCY = 0.0
CB_MONITORING_WINDOW_SECONDS = 60

# Circuit Breaker States
CB_STATE_CLOSED = "closed"
CB_STATE_OPEN = "open"
CB_STATE_HALF_OPEN = "half_open"

# Circuit Breaker Messages
CB_MSG_CIRCUIT_OPENED = "Circuit OPENED for {} after {} failures"
CB_MSG_CIRCUIT_CLOSED = "Circuit CLOSED for {} after {} successes"
CB_MSG_CIRCUIT_HALF_OPEN = "Circuit HALF_OPEN for {}, testing recovery"
CB_MSG_CALL_BLOCKED = "Circuit OPEN for {}, call blocked"
CB_MSG_SUCCESS_RECORDED = "Success recorded for {}"
CB_MSG_FAILURE_RECORDED = "Failure recorded for {}: {}"

# Circuit Breaker Error Types
CB_ERROR_TYPE_UNKNOWN = "unknown"
CB_ERROR_TYPE_TIMEOUT = "timeout"
CB_ERROR_TYPE_RATE_LIMIT = "rate_limit"
CB_ERROR_TYPE_CONNECTION = "connection"

# Circuit Breaker Metrics Keys
CB_METRIC_FAILURES = "failures"
CB_METRIC_SUCCESSES = "successes"
CB_METRIC_TOTAL_CALLS = "total_calls"
CB_METRIC_TOTAL_ERRORS = "total_errors"
CB_METRIC_SUCCESS_RATE = "success_rate"
CB_METRIC_AVG_LATENCY_MS = "avg_latency_ms"
CB_METRIC_RATE_LIMIT_HITS = "rate_limit_hits"
CB_METRIC_STATE = "state"
CB_METRIC_LAST_FAILURE = "last_failure_time"
CB_METRIC_LAST_SUCCESS = "last_success_time"


# Stock Universe Seeder Constants
SEED_DEFAULT_BATCH_SIZE = 25
SEED_ENRICH_BATCH_SIZE = 50
SEED_MAX_RETRIES = 3
SEED_RETRY_DELAY = 1

# Market Cap Buckets (USD)
MARKET_CAP_MEGA_MIN = 200_000_000_000  # $200B+
MARKET_CAP_LARGE_MIN = 10_000_000_000  # $10B-$200B
MARKET_CAP_MID_MIN = 2_000_000_000     # $2B-$10B
# Below $2B is small cap

# Index IDs
INDEX_ID_SP500 = "SP500"
INDEX_ID_RUSSELL3000 = "RUSSELL3000"
INDEX_ID_JSE_ALSI = "JSE_ALSI"

# Stock Universe Keys
STOCK_KEY_INDEX_ID = "indexId"
STOCK_KEY_INDEX_IDS = "indexIds"
STOCK_KEY_MARKET_CAP_BUCKET = "marketCapBucket"
STOCK_KEY_MARKET_CAP_USD = "marketCapUSD"
STOCK_KEY_LAST_UPDATED = "lastUpdated"

# Seeding Result Keys
SEED_RESULT_SEEDED = "seeded"
SEED_RESULT_FAILED = "failed"
SEED_RESULT_UPDATED = "updated"
SEED_RESULT_SKIPPED = "skipped"
SEED_RESULT_ERROR = "error"

# Seeding Messages
SEED_MSG_SEEDING_INDEX = "Seeding {} ({})"
SEED_MSG_FOUND_STOCKS = "Found {} stocks to seed"
SEED_MSG_ENRICHING = "Enriching {} stocks with market data..."
SEED_MSG_SEEDING_TO_DB = "Seeding {} stocks to DynamoDB..."
SEED_MSG_BATCH_PROGRESS = "Batch {}/{}: Seeded {} stocks"
SEED_MSG_COMPLETE = "Seeding complete: {} seeded, {} failed"
SEED_MSG_UNKNOWN_INDEX = "Unknown index: {}"
SEED_MSG_NO_FETCHER = "No fetcher for index: {}"
SEED_MSG_NO_STOCKS = "No stocks fetched for {}"
SEED_MSG_MERGING = "Merging index memberships for overlapping stocks..."
SEED_MSG_MERGED = "Merged {} stocks with multiple index memberships"

# Separator
SEPARATOR_LINE = "=" * 60

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

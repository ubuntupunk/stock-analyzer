# Multi-Index Stock Universe Architecture

## Overview

Expanding from single S&P 500 index to support multiple stock indices/exchanges:
- **S&P 500** (~500 stocks, USD, US)
- **Russell 3000** (~3,000 stocks, USD, US)
- **JSE All Share / ALSI** (~350 stocks, ZAR, South Africa)

---

## Database Schema Enhancements

### Current Schema
```python
{
    'symbol': 'AAPL',
    'name': 'Apple Inc.',
    'sector': 'Technology',
    'marketCap': 3000000000000,
    'lastUpdated': '2026-02-11T...'
}
```

### New Schema
```python
{
    'symbol': 'AAPL',                    # PK
    'name': 'Apple Inc.',
    'sector': 'Technology',
    'subSector': 'Software',
    'industry': 'Technology - Hardware',
    'region': 'US',                      # NEW: Region identifier
    'exchange': 'NASDAQ',                # NEW: Exchange name
    'currency': 'USD',                   # NEW: Base currency
    'currencyCode': 'USD',
    'exchangeSuffix': '',                # NEW: .JO for JSE, '' for US
    'indexId': 'SP500',                  # NEW: Index membership
    'indexIds': ['SP500', 'RUSSELL3000'], # NEW: Multiple indices
    'marketCap': 3000000000000,          # In local currency
    'marketCapUSD': 3000000000000,       # NEW: USD normalized
    'marketCapBucket': 'mega',           # mega/large/mid/small
    'lastUpdated': '2026-02-11T...',
    'lastValidated': '2026-02-11T...',   # NEW: Validation timestamp
    'isActive': True,                    # NEW: Still trading?
    'dataSource': 'yfinance',            # NEW: Source system
    'country': 'USA',                    # Existing field
    'headquarters': 'Cupertino, CA',     # Existing field
}
```

### New Global Secondary Indexes (GSIs)

| GSI Name | PK | SK | Purpose |
|----------|----|----|---------|
| `region-index` | `region` | `symbol` | Filter by country/region |
| `index-id-index` | `indexId` | `symbol` | Get all stocks in an index |
| `currency-index` | `currency` | `symbol` | Filter by currency |
| `status-index` | `isActive` | `symbol` | Query active/delisted stocks |

---

## Index Configuration Registry

### `infrastructure/backend/index_config.py`

```python
"""
Central registry for all supported stock indices
Each index defines its metadata and fetch strategy
"""

class IndexConfig:
    def __init__(self):
        self.indices = {
            'SP500': {
                'id': 'SP500',
                'name': 'S&P 500',
                'description': 'Large-cap US stocks',
                'region': 'US',
                'currency': 'USD',
                'exchange': 'NYSE/NASDAQ',
                'exchangeSuffix': '',
                'approxCount': 500,
                'dataSource': 'wikipedia',
                'url': 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
                'fetcher': 'S&P500Fetcher',
                'updateFrequency': '7 days',
                'marketCapThresholds': {
                    'mega': 200_000_000_000,
                    'large': 10_000_000_000,
                    'mid': 2_000_000_000
                }
            },
            'RUSSELL3000': {
                'id': 'RUSSELL3000',
                'name': 'Russell 3000',
                'description': 'US total market (small to large cap)',
                'region': 'US',
                'currency': 'USD',
                'exchange': 'NYSE/NASDAQ',
                'exchangeSuffix': '',
                'approxCount': 3000,
                'dataSource': 'ishares_etf',
                'url': 'https://www.ishares.com/us/products/239724/',
                'fetcher': 'Russell3000Fetcher',
                'etfSymbol': 'IWV',  # iShares Russell 3000 ETF
                'updateFrequency': '7 days',
                'marketCapThresholds': {
                    'mega': 200_000_000_000,
                    'large': 10_000_000_000,
                    'mid': 2_000_000_000,
                    'small': 300_000_000
                }
            },
            'JSE_ALSI': {
                'id': 'JSE_ALSI',
                'name': 'JSE All Share Index',
                'description': 'South African total market index',
                'region': 'ZA',
                'currency': 'ZAR',
                'exchange': 'JSE',
                'exchangeSuffix': '.JO',
                'approxCount': 350,
                'dataSource': 'jse_official',
                'url': 'https://www.jse.co.za/',  # Need specific endpoint
                'fetcher': 'JSEFetcher',
                'updateFrequency': '7 days',
                'fxRate': {
                    'from': 'ZAR',
                    'to': 'USD',
                    'symbol': 'ZAR=X',
                    'source': 'yfinance'
                },
                'marketCapThresholds': {
                    'mega': 200_000_000_000,  # ZAR
                    'large': 10_000_000_000,
                    'mid': 2_000_000_000,
                    'small': 500_000_000
                }
            },
            'JSE_TOP40': {
                'id': 'JSE_TOP40',
                'name': 'JSE Top 40',
                'description': 'Top 40 stocks on JSE',
                'region': 'ZA',
                'currency': 'ZAR',
                'exchange': 'JSE',
                'exchangeSuffix': '.JO',
                'approxCount': 40,
                'dataSource': 'wikipedia',
                'url': 'https://en.wikipedia.org/wiki/JSE_Top_40',
                'fetcher': 'JSETop40Fetcher',
                'updateFrequency': '7 days',
                'fxRate': {
                    'from': 'ZAR',
                    'to': 'USD',
                    'symbol': 'ZAR=X',
                    'source': 'yfinance'
                },
                'marketCapThresholds': {
                    'mega': 200_000_000_000,
                    'large': 10_000_000_000,
                    'mid': 2_000_000_000
                }
            }
        }

    def get_index(self, index_id: str) -> dict:
        """Get configuration for a specific index"""
        return self.indices.get(index_id)

    def get_all_indices(self) -> list:
        """Get all configured indices"""
        return list(self.indices.values())

    def get_indices_by_region(self, region: str) -> list:
        """Get all indices for a specific region"""
        return [idx for idx in self.indices.values() if idx['region'] == region]

    def get_indices_by_currency(self, currency: str) -> list:
        """Get all indices using a specific currency"""
        return [idx for idx in self.indices.values() if idx['currency'] == currency]
```

---

## Index Fetcher Strategy Pattern

### `infrastructure/backend/index_fetchers/base.py`

```python
"""
Base class for index constituent fetchers
Implement specific logic for each data source
"""
from abc import ABC, abstractmethod

class IndexFetcher(ABC):
    """Abstract base class for index constituent fetchers"""

    def __init__(self, config: dict):
        self.config = config
        self.region = config['region']
        self.currency = config['currency']
        self.exchange_suffix = config.get('exchangeSuffix', '')

    @abstractmethod
    def fetch_constituents(self) -> list:
        """
        Fetch list of stocks for this index
        Returns: [{'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Tech'}, ...]
        """
        pass

    def normalize_symbol(self, symbol: str) -> str:
        """
        Add exchange suffix if needed
        E.g., 'AGL' -> 'AGL.JO' for JSE
        """
        if self.exchange_suffix and not symbol.endswith(self.exchange_suffix):
            return f"{symbol}{self.exchange_suffix}"
        return symbol

    def apply_fx_conversion(self, market_cap: float, fx_rate: float = None) -> float:
        """
        Convert market cap to USD if needed
        """
        if self.currency == 'USD':
            return market_cap
        if fx_rate:
            return market_cap / fx_rate
        # Future: fetch live FX rate
        return market_cap
```

### `infrastructure/backend/index_fetchers/sp500_fetcher.py`

```python
import pandas as pd
from .base import IndexFetcher

class SP500Fetcher(IndexFetcher):
    """Fetch S&P 500 constituents from Wikipedia"""

    def fetch_constituents(self) -> list:
        url = self.config['url']
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            tables = pd.read_html(url, storage_options=headers)
            sp500_table = tables[0]

            stocks = []
            for _, row in sp500_table.iterrows():
                symbol = str(row['Symbol']).replace('.', '-')
                stocks.append({
                    'symbol': self.normalize_symbol(symbol),
                    'name': str(row['Security']),
                    'sector': str(row['GICS Sector']),
                    'subSector': str(row['GICS Sub-Industry']),
                    'region': self.region,
                    'currency': self.currency,
                    'exchange': 'NYSE/NASDAQ'
                })

            return stocks
        except Exception as e:
            print(f"Error fetching SP500: {e}")
            return self._get_fallback()

    def _get_fallback(self) -> list:
        """Fallback hardcoded list"""
        # Return popular stocks as fallback
        pass
```

### `infrastructure/backend/index_fetchers/russell_fetcher.py`

```python
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from .base import IndexFetcher

class Russell3000Fetcher(IndexFetcher):
    """Fetch Russell 3000 constituents from iShares ETF"""

    def fetch_constituents(self) -> list:
        """
        Strategy 1: Parse iShares ETF holdings page
        """
        etf_symbol = self.config.get('etfSymbol', 'IWV')
        url = self.config['url']

        # Alternative: Use beatthemarketanalyzer.com
        fallback_url = "http://www.beatthemarketanalyzer.com/blog/wp-content/uploads/2016/10/Russell-3000-Stock-Tickers-List.xlsx"

        try:
            # Try iShares holdings first
            holdings = self._fetch_ishares_holdings(etf_symbol)
            if holdings:
                return self._format Holdings(holdings)

            # Fallback to alternative source
            return self._fetch_from_excel(fallback_url)

        except Exception as e:
            print(f"Error fetching Russell 3000: {e}")
            return []

    def _fetch_ishares_holdings(self, etf_symbol: str) -> list:
        """Parse iShares ETF holdings page"""
        # Implementation: scrape or download holdings CSV
        pass

    def _fetch_from_excel(self, url: str) -> list:
        """Download and parse Excel file"""
        # Implementation with pandas
        pass

    def _format_holdings(self, holdings: list) -> list:
        """Format data to standard structure"""
        return [
            {
                'symbol': self.normalize_symbol(h['symbol']),
                'name': h['name'],
                'sector': h.get('sector', ''),
                'region': self.region,
                'currency': self.currency,
                'exchange': 'NYSE/NASDAQ'
            }
            for h in holdings
        ]
```

### `infrastructure/backend/index_fetchers/jse_fetcher.py`

```python
import yfinance as yf
import requests
import pandas as pd
from .base import IndexFetcher

class JSEFetcher(IndexFetcher):
    """Fetch JSE constituents and handle ZAR currency"""

    def fetch_constituents(self) -> list:
        """
        Fetch JSE All Share or Top 40 constituents
        """
        # Try Wikipedia first
        stocks = self._fetch_from_wikipedia()

        if not stocks:
            # Try JSE official site
            stocks = self._fetch_from_jse_official()

        return stocks

    def _fetch_from_wikipedia(self) -> list:
        """Parse JSE Top 40 Wikipedia page"""
        url = self.config['url']
        headers = {'User-Agent': 'Mozilla/5.0 ...'}

        try:
            tables = pd.read_html(url, storage_options=headers)
            # Parse and return stocks
            pass
        except Exception as e:
            print(f"Error fetching from Wikipedia: {e}")
            return []

    def _fetch_from_jse_official(self) -> list:
        """Fetch from JSE official website"""
        # Implementation: may need specific API endpoint
        pass

    def get_fx_rate(self) -> float:
        """Get current ZAR/USD exchange rate"""
        fx_symbol = self.config.get('fxRate', {}).get('symbol', 'ZAR=X')
        ticker = yf.Ticker(fx_symbol)
        info = ticker.info
        return info.get('regularMarketPrice', 18.0)  # Fallback rate

    def enrich_with_fx(self, stocks: list) -> list:
        """Convert ZAR market caps to USD"""
        fx_rate = self.get_fx_rate()

        for stock in stocks:
            if 'marketCap' in stock:
                stock['marketCapUSD'] = stock['marketCap'] / fx_rate

        return stocks
```

---

## Enhanced Seeder Architecture

### `infrastructure/backend/stock_universe_seed.py` (Refactored)

```python
from index_config import IndexConfig
from index_fetchers import SP500Fetcher, Russell3000Fetcher, JSEFetcher

class StockUniverseSeeder:
    """Multi-index stock universe seeder"""

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(os.environ.get('STOCK_UNIVERSE_TABLE', 'stock-universe'))
        self.index_config = IndexConfig()
        self.fetchers = {
            'SP500': SP500Fetcher,
            'RUSSELL3000': Russell3000Fetcher,
            'JSE_ALSI': JSEFetcher,
            'JSE_TOP40': JSEFetcher
        }

    def seed_index(self, index_id: str, enrich: bool = True) -> dict:
        """
        Seed a specific index
        """
        index_config = self.index_config.get_index(index_id)
        if not index_config:
            return {'error': f'Unknown index: {index_id}'}

        fetcher = self.fetchers.get(index_id)
        if not fetcher:
            return {'error': f'No fetcher for index: {index_id}'}

        # Fetch constituents
        print(f"Fetching {index_config['name']} constituents...")
        stocks = fetcher(index_config).fetch_constituents()
        print(f"Found {len(stocks)} stocks")

        # Add index-specific metadata
        for stock in stocks:
            stock['indexId'] = index_id
            stock['indexIds'] = [index_id]

        # Enrich with market data
        if enrich:
            market_data = self._enrich_stocks(stocks, index_config)

        # Seed to DynamoDB
        return self._seed_to_database(stocks, market_data, index_config)

    def seed_all_indices(self, enrich: bool = True) -> dict:
        """
        Seed all configured indices
        """
        results = {}
        for index_id in self.index_config.get_all_indices():
            result = self.seed_index(index_id, enrich)
            results[index_id] = result

        # Merge overlapping stocks (stocks in multiple indices)
        self._merge_index_memberships()

        return results

    def _enrich_stocks(self, stocks: list, index_config: dict) -> dict:
        """
        Fetch market data from yfinance with currency handling
        """
        symbols = [s['symbol'] for s in stocks]

        # Use yfinance
        tickers = yf.Tickers(' '.join(symbols))
        market_data = {}

        fx_rate = None
        if index_config['currency'] != 'USD':
            fx_rate = self._get_fx_rate(index_config['currency'])

        for symbol in symbols:
            try:
                ticker = tickers.tickers.get(symbol)
                if ticker:
                    info = ticker.info
                    market_cap = info.get('marketCap', 0)

                    market_data[symbol] = {
                        'marketCap': market_cap,
                        'marketCapUSD': self._convert_to_usd(market_cap, fx_rate),
                        'exchange': info.get('exchange', index_config['exchange']),
                        'country': info.get('country', index_config['region']),
                        'industry': info.get('industry', ''),
                        'isActive': True  # Will validate separately
                    }
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                market_data[symbol] = {}

        return market_data

    def _get_fx_rate(self, from_currency: str) -> float:
        """Get FX rate to USD"""
        fx_symbol = f"{from_currency}=X"
        ticker = yf.Ticker(fx_symbol)
        return ticker.info.get('regularMarketPrice', 1.0)

    def _convert_to_usd(self, amount: float, fx_rate: float = None) -> float:
        """Convert amount to USD"""
        if fx_rate:
            return amount / fx_rate
        return amount

    def _seed_to_database(self, stocks: list, market_data: dict, index_config: dict) -> dict:
        """Seed stocks to DynamoDB"""
        seeded = 0
        failed = 0

        with self.table.batch_writer() as batch:
            for stock in stocks:
                symbol = stock['symbol']
                md = market_data.get(symbol, {})

                item = {
                    'symbol': symbol,
                    'name': stock['name'],
                    'sector': stock.get('sector', 'Unknown'),
                    'subSector': stock.get('subSector', ''),
                    'industry': md.get('industry', ''),
                    'region': index_config['region'],
                    'currency': index_config['currency'],
                    'exchange': md.get('exchange', index_config['exchange']),
                    'exchangeSuffix': index_config.get('exchangeSuffix', ''),
                    'indexId': stock['indexId'],
                    'indexIds': [stock['indexId']],
                    'marketCap': Decimal(str(md.get('marketCap', 0))) if md.get('marketCap') else Decimal('0'),
                    'marketCapUSD': Decimal(str(md.get('marketCapUSD', 0))) if md.get('marketCapUSD') else Decimal('0'),
                    'marketCapBucket': self._get_market_cap_bucket(md.get('marketCapUSD', 0)),
                    'lastUpdated': datetime.utcnow().isoformat(),
                    'lastValidated': datetime.utcnow().isoformat(),
                    'isActive': md.get('isActive', True),
                    'dataSource': 'yfinance',
                    'country': md.get('country', index_config['region'])
                }

                try:
                    batch.put_item(Item=item)
                    seeded += 1
                except Exception as e:
                    print(f"Failed to seed {symbol}: {e}")
                    failed += 1

        return {'seeded': seeded, 'failed': failed, 'total': len(stocks)}

    def _merge_index_memberships(self):
        """
        Merge stocks that belong to multiple indices
        E.g., AAPL is in both SP500 and RUSSELL3000
        """
        # Scan all stocks and group by symbol
        response = self.table.scan()
        stocks_by_symbol = {}

        for item in response['Items']:
            symbol = item['symbol']
            if symbol not in stocks_by_symbol:
                stocks_by_symbol[symbol] = item
            else:
                # Merge indexIds
                existing = stocks_by_symbol[symbol]
                new_indices = item['indexIds']
                for idx in new_indices:
                    if idx not in existing['indexIds']:
                        existing['indexIds'].append(idx)
                        existing['indexIds'].sort()

        # Update merged items
        with self.table.batch_writer() as batch:
            for symbol, item in stocks_by_symbol.items():
                if len(item['indexIds']) > 1:
                    batch.put_item(Item=item)

    def validate_stocks(self, index_id: str = None) -> dict:
        """
        Validate stocks for specific index or all indices
        Check for delisted/stale stocks
        """
        # Implementation
        pass
```

---

## API Enhancements

### New Query Parameters

```bash
# Filter by region
GET /api/stocks/filter?region=US

# Filter by index
GET /api/stocks/filter?indexId=SP500

# Filter by currency
GET /api/stocks/filter?currency=USD

# Multiple filters
GET /api/stocks/filter?region=ZA&indexId=JSE_ALSI

# Get stocks in multiple indices
GET /api/stocks/filter?indexId=SP500&indexId=RUSSELL3000

# Search with region context
GET /api/stocks/search?q=BHP&region=ZA

# Get index summary
GET /api/indices

# Get specific index details
GET /api/indices/SP500
```

### New Endpoints

#### `GET /api/indices`
```json
{
  "indices": [
    {
      "id": "SP500",
      "name": "S&P 500",
      "region": "US",
      "currency": "USD",
      "stockCount": 498,
      "lastUpdated": "2026-02-10T...",
      "status": "active"
    },
    {
      "id": "JSE_ALSI",
      "name": "JSE All Share",
      "region": "ZA",
      "currency": "ZAR",
      "stockCount": 345,
      "lastUpdated": "2026-02-10T...",
      "status": "active"
    }
  ]
}
```

#### `GET /api/indices/{indexId}/stocks`
```python
def get_index_stocks(index_id: str, limit: int = 100):
    """Get all stocks for a specific index"""
    # Query using index-id-index GSI
```

---

## EventBridge Schedule Updates

### `template.yaml`

```yaml
StockUniverseSeedFunction:
  Events:
    SP500Weekly:
      Type: Schedule
      Properties:
        Schedule: rate(7 days)
        Description: Weekly update of S&P 500
        Enabled: true
        Input: { "indexId": "SP500", "operation": "seed" }

    RussellWeekly:
      Type: Schedule
      Properties:
        Schedule: rate(7 days)
        Description: Weekly update of Russell 3000
        Enabled: true
        Input: { "indexId": "RUSSELL3000", "operation": "seed" }

    JSEWeekly:
      Type: Schedule
      Properties:
        Schedule: rate(7 days)
        Description: Weekly update of JSE indices
        Enabled: true
        Input: { "indexId": "JSE_ALSI", "operation": "seed" }

    DailyValidation:
      Type: Schedule
      Properties:
        Schedule: rate(1 day)
        Description: Daily validation of all stocks
        Enabled: true
        Input: { "operation": "validate" }
```

---

## Frontend Changes

### Search with Region/Index Filter
```javascript
// Search with multiple options
async searchStocks(query, options = {}) {
    const { region, indexId, currency } = options;
    let url = `/api/stocks/search?q=${query}`;
    if (region) url += `&region=${region}`;
    if (indexId) url += `&indexId=${indexId}`;
    if (currency) url += `&currency=${currency}`;
    return this.api.get(url);
}
```

### Index Selector Component
```javascript
// Filter by index
<IndexSelector indices={indices} onChange={handleIndexChange} />

// Show currency indicator
<CurrencyIndicator code="ZAR" symbol="R" />
```

---

## Migration Strategy

### Phase 1: Schema Update
1. Add new fields to DynamoDB (backward compatible)
2. Create new GSIs
3. Run script to backfill existing records

### Phase 2: Implement Fetchers
1. Create base fetcher class
2. Implement SP500 fetcher (migrate existing code)
3. Implement Russell 3000 fetcher
4. Implement JSE fetcher

### Phase 3: API Extensions
1. Add new endpoint handlers
2. Update OpenAPI spec
3. Update frontend search

### Phase 4: Scheduling
1. Add multiple EventBridge schedules
2. Configure staggered updates (avoid rate limits)

### Phase 5: Testing & Validation
1. Run test seeds for each index
2. Validate data quality
3. Monitor FX conversion accuracy

---

## Data Validation Considerations

### Per-Region Rules

| Region | Validation Rules |
|--------|------------------|
| US | Standard: check recent price activity |
| ZA | Check `.JO` suffix, ZAR currency validity |

### FX Conversion
- Fetch live USD/ZAR rate on validation
- Cache rates for 15 minutes
- Alert if rate deviates > 10% from previous

### Delisting Detection
- US: No price data for 5 consecutive days
- SA: JSE publishes delisting announcements daily

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| yfinance JSE rate limits | Medium | Cache data, use alternative sources |
| FX rate volatility | Low | Use daily average rates |
| Index constituent changes | Medium | Weekly updates catch rebalances |
| Data quality differences | High | Validations and manual review |

---

## File Structure

```
infrastructure/backend/
├── index_config.py                  # NEW: Index registry
├── index_fetchers/
│   ├── __init__.py
│   ├── base.py                      # NEW: Base fetcher class
│   ├── sp500_fetcher.py             # NEW: S&P 500 specific
│   ├── russell_fetcher.py           # NEW: Russell 3000 specific
│   └── jse_fetcher.py               # NEW: JSE specific
├── stock_validator.py               # NEW: Validation logic
├── stock_metrics.py                 # NEW: Metrics module
└── stock_universe_seed.py           # MODIFIED: Multi-index support
```

---

## Implementation Order

1. **Index Configuration** - `index_config.py` (foundation)
2. **Base Fetcher** - `index_fetchers/base.py` (abstraction)
3. **SP500 Fetcher** - `index_fetchers/sp500_fetcher.py` (migrate existing)
4. **Russell Fetcher** - `index_fetchers/russell_fetcher.py` (new index)
5. **JSE Fetcher** - `index_fetchers/jse_fetcher.py` (new region)
6. **Enhanced Seeder** - Refactor `stock_universe_seed.py`
7. **Schema Migration** - Add fields and GSIs
8. **API Extensions** - New endpoints and filters
9. **Scheduling** - Multiple EventBridge events
10. **Validation** - Per-region rules

---

## Next Steps

Do you want to:
1. **Start implementation** with Phase 1 (Index Configuration)?
2. **Adjust the design** (e.g., different indices, other considerations)?
3. **Discuss specific aspects** (FX handling, data validation strategies)?

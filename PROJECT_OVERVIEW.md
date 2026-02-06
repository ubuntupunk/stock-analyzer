# Stock Analyzer - Project Overview

## What is This?

A full-stack stock analysis application that runs on AWS serverless infrastructure (Lambda + S3). It provides comprehensive tools for analyzing stocks, performing DCF valuations, screening stocks based on custom factors, and managing watchlists.

## Key Features

### 1. Stock Metrics Dashboard
- Real-time stock prices
- Comprehensive financial metrics (P/E, ROI, ROE, Revenue Growth, etc.)
- 52-week highs/lows
- Interactive price charts
- Market capitalization and enterprise value

### 2. DCF Valuation Tool
- Discounted Cash Flow analysis
- Customizable assumptions (revenue growth, profit margins, etc.)
- Multiple scenarios (Low, Mid, High)
- Expected returns calculation
- Terminal value calculations

### 3. Factor Screener
- Create custom stock screening criteria
- Save and reuse screening factors
- Examples:
  - P/E ratio < 22.5
  - ROIC > 9%
  - Revenue growth > 5% over 5 years
  - Cash flow growth positive

### 4. Analyst Estimates
- Consensus earnings per share (EPS) estimates
- Revenue forecasts
- Number of analysts covering
- Historical vs. projected visualization

### 5. Watchlist Management
- Track favorite stocks
- Real-time price updates
- Custom notes and tags
- Alert price settings

### 6. Financial Statements
- Income statements
- Balance sheets
- Cash flow statements
- Multi-year comparison

### 7. API Resilience & Circuit Breaker
- **Multi-source Fallback Strategy**: Automatically switches between data sources when one fails
- **Circuit Breaker Pattern**: Prevents cascading failures when external APIs are unavailable
- **Real-time Metrics**: Tracks API performance, latency, success rates, and error types
- **Configurable Priorities**: Customize the order of API sources based on your needs
- **Automatic Recovery**: Circuits automatically transition to half-open state to test recovery

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User's Browser                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP/HTTPS
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Amazon S3 (Frontend)                      │
│                  HTML + CSS + JavaScript                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ REST API Calls
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Amazon API Gateway                         │
│                    (REST API Endpoints)                      │
└─────────┬──────────────┬──────────────┬─────────────────────┘
          │              │              │
          │              │              │
          ▼              ▼              ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│   Lambda    │  │   Lambda     │  │   Lambda     │
│ Stock API   │  │ Screener API │  │ Watchlist    │
└──────┬──────┘  └──────┬───────┘  └──────┬───────┘
       │                │                 │
       │    ┌────────────┴────────────┐
       │    │                         │
       │    ▼                         ▼
       │ ┌──────────────────────┐ ┌──────────────────────┐
       │ │  Circuit Breaker    │ │   API Metrics       │
       │ │  - State Tracking   │ │   - Performance      │
       │ │  - Fallback Logic   │ │   - Error Logging   │
       │ └──────────────────────┘ └──────────────────────┘
       │    │                         │
       └────┼─────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│              Multi-Source Data Provider Layer               │
├─────────────┬─────────────┬──────────────┬─────────────────┤
│   Yahoo     │   Alpaca    │   Polygon    │  Alpha Vantage  │
│   Finance   │             │    .io       │                 │
│  (Default)  │ (Realtime)  │  (Historical)│  (Fundamental)  │
└─────────────┴─────────────┴──────────────┴─────────────────┘
       │                │                │                  │
       └────────────────┴────────────────┴──────────────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │  Amazon DynamoDB     │
                 │  - Factors Table     │
                 │  - Watchlist Table  │
                 └──────────────────────┘
```

---

## Circuit Breaker & API Resilience

### Overview

The Stock Analyzer implements a **Circuit Breaker pattern** to ensure reliable data retrieval even when external APIs experience issues. This prevents cascading failures and provides graceful degradation.

### How It Works

```
                    ┌─────────────────────────────────────────────┐
                    │           Normal Operation                 │
                    │  (Circuit CLOSED - Requests flow normally)  │
                    └────────────────────┬────────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────────┐
                    │         API Failure Detected               │
                    │  (Failure count reaches threshold)          │
                    └────────────────────┬────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────┐
                    │         Circuit OPENS                      │
                    │  - Fail-fast for failing API               │
                    │  - Requests skip to next source            │
                    │  - Timeout timer starts                     │
                    └────────────────────┬────────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────────┐
                    │         Timeout Expires                    │
                    │  (Default: 30 seconds)                     │
                    └────────────────────┬────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────┐
                    │       Circuit HALF-OPEN                   │
                    │  - Allows limited test requests           │
                    │  - Tests if API recovered                 │
                    └────────────────────┬────────────────────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         │                               │
                         ▼                               ▼
                ┌─────────────────┐              ┌─────────────────┐
                │   Success!     │              │    Failure!     │
                │  Circuit CLOSES│              │  Circuit REOPENS│
                └─────────────────┘              └─────────────────┘
```

### API Sources & Priority

The system supports multiple data sources with configurable priorities:

| Priority | Source | Type | Rate Limits | Best For |
|----------|--------|------|-------------|----------|
| 1 | Yahoo Finance | Free | None | Primary - Fast, comprehensive |
| 2 | Alpaca | Freemium | 200 req/min | Real-time quotes |
| 3 | Polygon.io | Freemium | 5 req/min | Historical data |
| 4 | Alpha Vantage | Free | 5 req/min | Fundamentals |

### Default Priority Configuration

```python
DEFAULT_PRIORITIES = [
    ('yahoo_finance', 1),      # First choice - free, no rate limits
    ('alpaca', 2),              # Second - good for real-time
    ('polygon', 3),             # Third - excellent historical data
    ('alpha_vantage', 4)        # Fourth - slow, use as last resort
]
```

### Configuration Options

#### Environment Variables

```bash
# API Key Configuration
ALPACA_API_KEY=your_alpaca_key
POLYGON_API_KEY=your_polygon_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key

# Circuit Breaker Configuration (Optional)
CIRCUIT_FAILURE_THRESHOLD=5       # Failures before opening (default: 5)
CIRCUIT_TIMEOUT_SECONDS=30.0      # Time in open state (default: 30)
CIRCUIT_SUCCESS_THRESHOLD=2       # Successes to close from half_open (default: 2)
```

#### Programmatic Configuration

```python
from stock_api import StockDataAPI
from circuit_breaker import CircuitBreakerConfig

# Custom circuit breaker configuration
cb_config = CircuitBreakerConfig(
    failure_threshold=10,     # More failures before opening
    success_threshold=3,      # More successes needed to close
    timeout_seconds=60.0      # Longer timeout
)

# Custom priorities
api = StockDataAPI(config={
    'timeout': 15,
    'cache_timeout': 300,
    'priorities': [
        ('yahoo_finance', 1),
        ('alpaca', 2),
        ('polygon', 3),
        ('alpha_vantage', 4)
    ]
})
```

### API Metrics & Monitoring

The system tracks comprehensive metrics for each data source:

#### Metrics Tracked

| Metric | Description |
|--------|-------------|
| Total Requests | Number of API calls made |
| Success/Failed | Call outcomes |
| Average Latency | Response time in milliseconds |
| Rate Limits | 429 errors encountered |
| Timeouts | Request timeout count |
| Error Types | Breakdown of error categories |

#### Accessing Metrics

```python
from stock_api import StockDataAPI

api = StockDataAPI()

# Get all metrics
metrics = api.metrics.get_metrics()
print(f"Success Rate: {metrics['success_rate']}")
print(f"Total Requests: {metrics['requests']['total']}")
print(f"Average Latency: {metrics['latency']['avg_ms']}ms")

# Get source-specific stats
source_stats = api.metrics.get_source_stats('yahoo_finance')
print(f"Yahoo Finance Calls: {source_stats['calls']}")
print(f"Success Rate: {source_stats['success_rate']}")

# Get circuit breaker states
cb_states = api.cb.get_all_states()
print(f"Open Circuits: {[k for k,v in cb_states.items() if v['state'] == 'open']}")
```

#### Health Report

```python
health = api.cb.get_health_report()

print(f"Health Score: {health['health_score']:.1%}")
print(f"Healthy APIs: {len(health['healthy'])}")
print(f"Degraded APIs: {len(health['degraded'])}")
print(f"Unhealthy APIs: {len(health['unhealthy'])}")
```

### Fallback Behavior

#### Parallel Fallback Strategy

When fetching stock data, the system attempts multiple sources in parallel:

```
Request: get_stock_price("AAPL")
    │
    ▼
┌───────────────────────────────────────────────┐
│  Check circuit state for each source         │
│  Skip sources with OPEN circuits             │
└────────────────────┬────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │  Yahoo  │  │  Alpaca │  │ Polygon │
   │ (并行)   │  │ (并行)   │  │ (并行)   │
   └────┬────┘  └────┬────┘  └────┬────┘
        │            │            │
        └────────────┬────────────┘
                     │
              First successful response
                     │
                     ▼
              Return result (cache if configured)
```

#### Caching Strategy

- **Cache TTL**: 5 minutes (300 seconds) by default
- **Cache Keys**: Prefix-based (`price:{period}:{symbol}`, `metrics:{symbol}`, etc.)
- **Cache Bypass**: Cache can be bypassed by setting `cache_timeout=0`

```python
api = StockDataAPI(config={
    'cache_timeout': 300  # 5 minutes
})

# Clear cache manually
api.cache.clear()
```

### Manual Circuit Control

For maintenance or testing, circuits can be controlled manually:

```python
# Force a circuit open (skip this source)
api.cb.force_open('alpha_vantage')

# Force a circuit closed (use normally)
api.cb.force_close('alpha_vantage')

# Reset a specific circuit
api.cb.reset('alpha_vantage')

# Reset all circuits
api.cb.reset()
```

---

## Tech Stack

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Responsive design with flexbox/grid
- **JavaScript (ES6+)**: Vanilla JS, no frameworks
- **Chart.js**: Data visualization library

### Backend
- **Python 3.11**: Lambda functions
- **boto3**: AWS SDK for Python
- **requests**: HTTP library for API calls

### Infrastructure
- **AWS Lambda**: Serverless compute
- **API Gateway**: REST API management
- **DynamoDB**: NoSQL database
- **S3**: Static website hosting
- **CloudFormation/SAM**: Infrastructure as Code

### External Services
- **Alpha Vantage**: Financial data API (free tier available)
- Alternative: Yahoo Finance, IEX Cloud, Finnhub

## File Structure

```
stock-analyzer/
│
├── README.md              # Comprehensive documentation
├── QUICKSTART.md          # Quick deployment guide
├── package.json           # NPM scripts (optional)
├── PROJECT_OVERVIEW.md    # This file
├── .gitignore            # Git ignore rules
│
├── deploy.sh             # Automated deployment script
├── test.sh               # API testing script
│
├── tests/                # Test suite
│   ├── unit/             # Unit tests
│   │   ├── __init__.py
│   │   ├── test_circuit_breaker.py   # Circuit breaker tests
│   │   └── test_stock_api.py          # Stock API tests
│   └── integration/      # Integration tests
│       ├── package.json
│       ├── jest.config.js
│       └── *.test.js
│
├── backend/              # Lambda functions
│   ├── stock_api.py      # Stock data retrieval with circuit breaker
│   ├── screener_api.py   # Screening & DCF analysis
│   ├── watchlist_api.py  # Watchlist management
│   ├── circuit_breaker.py # Circuit breaker implementation
│   ├── requirements.txt  # Python dependencies
│   └── api_clients/      # Individual API client modules
│       ├── __init__.py
│       ├── yahoo_finance.py
│       ├── alpha_vantage.py
│       ├── polygon.py
│       └── alpaca.py
│
├── frontend/             # Static website files
│   ├── index.html        # Main HTML
│   ├── styles.css        # Stylesheet
│   ├── config.js         # Configuration
│   ├── api.js           # API client
│   └── app.js           # Application logic
│
└── infrastructure/       # AWS infrastructure
    └── template.yaml     # SAM template
```

## Testing

### Unit Tests

Run unit tests with pytest:

```bash
# Install test dependencies
cd infrastructure/backend
pip install pytest pytest-asyncio pytest-cov

# Run all unit tests
cd ../../tests/unit
python -m pytest -v

# Run specific test file
python -m pytest test_circuit_breaker.py -v
python -m pytest test_stock_api.py -v

# Run with coverage
python -m pytest --cov=backend --cov-report=html
```

### Test Coverage

| Module | Tests | Description |
|--------|-------|-------------|
| circuit_breaker.py | 30+ | Circuit states, transitions, metrics |
| stock_api.py | 20+ | Cache, metrics, priorities, API methods |

### Integration Tests

Run integration tests with Jest:

```bash
cd tests/integration
npm install
npm test
```

---

## API Resilience Features

| Feature | Status | Description |
|---------|--------|-------------|
| Circuit Breaker | ✅ Implemented | Prevents cascading failures |
| Multi-source Fallback | ✅ Implemented | Parallel fallback strategy |
| API Metrics | ✅ Implemented | Performance tracking |
| Configurable Priorities | ✅ Implemented | Customizable source order |
| Automatic Recovery | ✅ Implemented | Half-open state testing |
| Rate Limit Handling | ✅ Implemented | Per-client timeout & retry |
| Request Caching | ✅ Implemented | 5-minute cache TTL |

---

## API Endpoints Reference

### Stock Data Endpoints
```
GET /api/stock/metrics?symbol={SYMBOL}
GET /api/stock/price?symbol={SYMBOL}
GET /api/stock/estimates?symbol={SYMBOL}
GET /api/stock/financials?symbol={SYMBOL}
```

### Analysis Endpoints
```
POST /api/screen
POST /api/dcf
GET /api/factors
POST /api/factors
```

### Watchlist Endpoints
```
GET /api/watchlist
POST /api/watchlist
PUT /api/watchlist
DELETE /api/watchlist?symbol={SYMBOL}
```

## Deployment Process

1. **Prerequisites Check**: AWS CLI, SAM CLI, Python 3.11+
2. **AWS Configuration**: Set up credentials
3. **Backend Deployment**: SAM build and deploy
4. **Frontend Configuration**: Update API endpoint
5. **Frontend Deployment**: Sync to S3
6. **Testing**: Run test script to verify

## Cost Structure

### Free Tier (First 12 Months)
- Lambda: 1M requests/month
- API Gateway: 1M calls/month
- DynamoDB: 25GB storage + 25 RCU/WCU
- S3: 5GB storage + 20k GET + 2k PUT

### Beyond Free Tier
- Lambda: ~$0.20 per 1M requests
- API Gateway: ~$3.50 per 1M requests
- DynamoDB: ~$0.25 per GB/month
- S3: ~$0.023 per GB/month

**Typical Monthly Cost**: $5-20 for moderate usage

## Security Features

1. **HTTPS Only**: Enforced by S3 and API Gateway
2. **CORS Configuration**: Restricted origins
3. **Input Validation**: All user inputs validated
4. **API Key Management**: Environment variables
5. **IAM Roles**: Least privilege access
6. **No Hardcoded Secrets**: All sensitive data in environment

## Performance Optimizations

1. **Lambda Cold Start**: Minimal dependencies
2. **Caching**: DynamoDB queries cached
3. **Compression**: Gzip enabled on S3
4. **CDN Ready**: Can add CloudFront
5. **Async Loading**: Frontend loads progressively

## Scalability

- **Auto-scaling**: Lambda scales automatically
- **DynamoDB**: On-demand billing, auto-scales
- **API Gateway**: Handles millions of requests
- **S3**: Unlimited storage and requests

## Monitoring & Logging

- **CloudWatch Logs**: All Lambda executions logged
- **CloudWatch Metrics**: API Gateway metrics
- **X-Ray**: Distributed tracing (optional)
- **Cost Explorer**: Usage and cost tracking

## Gotchas & Technical Debt

### Frontend Issues Fixed ✅

1. **Circuit Breaker Module Not Loaded**
   - **Problem**: `CircuitBreaker.js` existed but wasn't imported in `index.html`, causing "CircuitBreaker is not defined" error
   - **Solution**: Added `<script src="modules/CircuitBreaker.js"></script>` to index.html
   - **Files Modified**: `infrastructure/frontend/index.html`

2. **Memory Leak in DataManager**
   - **Problem**: `setInterval()` for cache pruning never cleared on page unload
   - **Solution**: Added `cleanup()` method that clears the interval and all caches
   - **Files Modified**: `infrastructure/frontend/modules/DataManager.js`

3. **Missing Error Boundaries**
   - **Problem**: No global error handler - single module failures could crash entire app
   - **Solution**: Created `ErrorBoundary.js` with global error catching and fallback UIs
   - **Files Created**: `infrastructure/frontend/modules/ErrorBoundary.js`

### Architecture Gotchas ⚠️

4. **Backend-Frontend Circuit Breaker Desync**
   - **Issue**: Frontend and backend circuit breakers operate independently
   - **Impact**: Frontend may open circuit while backend is healthy
   - **Mitigation**: Added `HealthManager.js` with periodic backend health checks
   - **Files Created**: `infrastructure/frontend/modules/HealthManager.js`

5. **Missing Frontend Tests**
   - **Issue**: Only backend had unit test coverage
   - **Solution**: Added Jest tests for CircuitBreaker.js
   - **Files Created**: `tests/integration/circuitbreaker.test.js` (20 tests)

### Known Limitations

6. **API Key Exposure**
   - API URLs visible in browser network tab (acceptable for client-side apps)
   - API keys stored in Lambda environment variables (secure)

7. **No WebSocket Support**
   - Real-time updates require polling (future enhancement)

8. **Lambda Cold Starts**
   - First request after idle period may be slow (30+ seconds)
   - Mitigated by circuit breaker timeout configuration

### Recommended Actions

- Add Jest tests for DataManager, ErrorBoundary, and HealthManager
- Implement WebSocket for real-time updates
- Add end-to-end tests with Playwright
- Consider Cognito for user authentication

## Future Enhancements

### Phase 1 (Foundation)
- ✅ Stock data retrieval
- ✅ DCF analysis
- ✅ Factor screening
- ✅ Watchlist management

### Phase 2 (User Features)
- [ ] User authentication (Cognito)
- [ ] Save analysis reports
- [ ] Email alerts for watchlist
- [ ] Export to PDF/Excel

### Phase 3 (Advanced Features)
- [ ] Real-time WebSocket updates
- [ ] Options pricing calculator
- [ ] Portfolio tracking
- [ ] Technical analysis indicators
- [ ] Social features (share analysis)

### Phase 4 (Mobile & Integration)
- [ ] Mobile app (React Native)
- [ ] Chrome extension
- [ ] Slack/Discord integration
- [ ] API marketplace integration

## Customization Guide

### Change Color Scheme
Edit `frontend/styles.css`:
```css
:root {
    --primary-color: #5ba3d0;    /* Main theme color */
    --secondary-color: #a8d5ba;  /* Accent color */
    --accent-color: #ffb3ba;     /* Button color */
}
```

### Add New Metrics
1. Backend: Fetch data in `stock_api.py`
2. Frontend: Add HTML in `index.html`
3. Logic: Update `app.js` to display

### Change Financial Data Provider
Edit `backend/stock_api.py`:
```python
self.base_url = "https://your-provider.com"
self.api_key = os.environ.get('YOUR_API_KEY')
```

## Troubleshooting Guide

### Common Issues

1. **CORS Errors**: Check API Gateway CORS settings
2. **No Data Loading**: Verify API key and rate limits
3. **Deployment Fails**: Check AWS permissions
4. **High Costs**: Review CloudWatch usage metrics

### Debug Commands
```bash
# View Lambda logs
sam logs -n StockAPIFunction --tail

# Test API endpoint
curl https://your-api.com/api/stock/metrics?symbol=AAPL

# Check CloudFormation stack
aws cloudformation describe-stacks --stack-name stock-analyzer-stack
```

## Support & Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **Alpha Vantage API**: https://www.alphavantage.co/documentation/
- **Chart.js Docs**: https://www.chartjs.org/docs/
- **SAM Documentation**: https://docs.aws.amazon.com/serverless-application-model/

## Contributing

Contributions welcome! Areas for improvement:
- Additional financial calculators
- More data providers
- UI/UX enhancements
- Performance optimizations
- Documentation improvements

## License

MIT License - Free to use and modify for personal and commercial projects.

---

**Built with ❤️ for stock market enthusiasts and value investors**

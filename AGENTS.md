# Stock Analyzer - Agent Documentation

## Project Overview

Stock Analyzer is a comprehensive stock analysis platform built on AWS serverless infrastructure. It provides tools for DCF valuation, factor-based stock screening, watchlist management, and financial metrics visualization.

**Key Features:**
- Stock Metrics Dashboard (P/E, ROI, ROE, Revenue Growth, etc.)
- DCF (Discounted Cash Flow) Valuation Tool with customizable assumptions
- Factor Screener for custom stock screening criteria
- Analyst Estimates tracking
- Watchlist Management with real-time updates
- Financial Statements (Income, Balance Sheet, Cash Flow)
- Multi-source API resilience with Circuit Breaker pattern

---

## Technology Stack

### Backend
- **Runtime**: Python 3.12
- **Platform**: AWS Lambda (Serverless)
- **API**: Amazon API Gateway (REST)
- **Database**: Amazon DynamoDB
- **Authentication**: AWS Cognito User Pools
- **Infrastructure**: AWS SAM (Serverless Application Model)

### Frontend
- **Type**: Static Website (HTML5, CSS3, Vanilla JavaScript)
- **Hosting**: Amazon S3 + CloudFront CDN
- **Styling**: SCSS/Sass (compiled to CSS)
- **Charts**: Chart.js for data visualization
- **Build Tool**: npm scripts with Sass compiler

### External APIs (Data Sources)
- Yahoo Finance (primary)
- Alpha Vantage
- Polygon.io
- Alpaca (real-time data)

---

## Project Structure

```
stock-analyzer/
├── infrastructure/           # All infrastructure and application code
│   ├── template.yaml         # SAM/CloudFormation template
│   ├── samconfig.toml        # SAM deployment configuration
│   ├── backend/              # Python Lambda functions
│   │   ├── lambda_handler.py   # Main API router & entry point
│   │   ├── stock_api.py        # Stock data retrieval with multi-source fallback
│   │   ├── screener_api.py     # DCF analysis & stock screening
│   │   ├── watchlist_api.py    # Watchlist CRUD operations
│   │   ├── stock_universe_api.py   # Stock search & filtering
│   │   ├── stock_universe_seed.py  # Weekly data seeding job
│   │   ├── circuit_breaker.py    # Circuit breaker implementation
│   │   ├── requirements.txt      # Python dependencies
│   │   └── api_clients/          # Individual API client modules
│   │       ├── __init__.py
│   │       ├── yahoo_finance.py
│   │       ├── alpha_vantage.py
│   │       ├── polygon.py
│   │       └── alpaca.py
│   └── frontend/             # Static web assets
│       ├── index.html          # Main entry point
│       ├── app.js              # Main application orchestrator
│       ├── config.js           # Environment configuration
│       ├── api.js              # API service layer
│       ├── auth.js             # Authentication handling
│       ├── styles.css          # Compiled CSS (from SCSS)
│       ├── scss/               # Sass source files
│       │   ├── main.scss
│       │   ├── base/
│       │   ├── components/
│       │   ├── layout/
│       │   └── sections/
│       ├── modules/            # JavaScript modules
│       │   ├── DataManager.js
│       │   ├── StockManager.js
│       │   ├── WatchlistManager.js
│       │   ├── ChartManager.js
│       │   ├── MetricsManager.js
│       │   ├── CircuitBreaker.js
│       │   └── ... (16+ modules)
│       ├── components/         # HTML components
│       ├── sections/           # Tab content HTML files
│       └── utils/              # Utility classes (EventBus, Formatters, Validators)
├── tests/
│   ├── unit/                   # Python unit tests (pytest)
│   │   ├── test_stock_api.py
│   │   └── test_circuit_breaker.py
│   └── integration/            # JavaScript integration tests (Jest + Playwright)
│       ├── package.json
│       ├── jest.config.js
│       ├── watchlist.test.js
│       ├── datamanager.test.js
│       └── circuitbreaker.test.js
├── docs/                       # Additional documentation
├── deploy.sh                   # Main deployment script
├── package.json                # Node.js dependencies & scripts
└── README.md                   # User-facing documentation
```

---

## Build & Deployment Commands

### Prerequisites
- AWS CLI (v2+)
- AWS SAM CLI
- Python 3.11+
- Node.js 14+ (for Sass compilation)

### Full Deployment
```bash
# Deploy entire application (backend + frontend)
./deploy.sh
```

### Backend Only
```bash
cd infrastructure
sam build
sam deploy --guided
```

### Frontend Only
```bash
# Compile SCSS to CSS
npm run build:css

# Watch SCSS for changes during development
npm run watch:css

# Deploy to S3 (requires backend to be deployed first)
cd infrastructure/frontend
aws s3 sync . s3://<bucket-name>/ --delete
```

### Available npm Scripts
```bash
npm run deploy              # Run deploy.sh
npm run deploy-backend      # Deploy SAM backend only
npm run deploy-frontend     # Deploy frontend to S3
npm run validate            # Validate SAM template
npm run clean               # Remove build artifacts
npm run logs                # Tail Lambda logs
npm run test-api            # Test API endpoint
npm run build:css           # Compile SCSS
npm run watch:css           # Watch SCSS changes
```

---

## Testing

### Unit Tests (Python)
```bash
# Run from project root
pytest tests/unit/

# With coverage
pytest tests/unit/ --cov=infrastructure/backend
```

**Test Files:**
- `tests/unit/test_stock_api.py` - Tests for StockDataAPI, APIMetrics
- `tests/unit/test_circuit_breaker.py` - Tests for CircuitBreaker pattern

### Integration Tests (JavaScript)
```bash
cd tests/integration
npm install
npm test                    # Run all tests
npm run test:watch          # Watch mode
npm run test:watchlist      # Test specific file
```

**Test Files:**
- `watchlist.test.js` - Watchlist functionality
- `datamanager.test.js` - Data management
- `circuitbreaker.test.js` - Circuit breaker behavior

---

## API Endpoints

### Stock Data (GET)
- `/api/stock/metrics?symbol=AAPL` - Financial metrics
- `/api/stock/price?symbol=AAPL&period=1mo` - Price & historical data
- `/api/stock/estimates?symbol=AAPL` - Analyst estimates
- `/api/stock/financials?symbol=AAPL` - Financial statements
- `/api/stock/factors?symbol=AAPL` - Factor ratings
- `/api/stock/news?symbol=AAPL` - Stock news

### Batch Operations (GET)
- `/api/stock/batch/prices?symbols=AAPL,MSFT,GOOGL`
- `/api/stock/batch/metrics?symbols=AAPL,MSFT,GOOGL`
- `/api/stock/batch/estimates?symbols=AAPL,MSFT,GOOGL`
- `/api/stock/batch/financials?symbols=AAPL,MSFT,GOOGL`

### Screening & Analysis (POST)
- `/api/screen` - Screen stocks by criteria
- `/api/dcf` - DCF valuation calculation

### Factors (Auth Required for POST)
- `GET /api/factors` - Get saved factors
- `POST /api/factors` - Save new factor (requires Cognito auth)

### Watchlist (CRUD)
- `GET /api/watchlist` - Get user's watchlist
- `POST /api/watchlist` - Add stock
- `PUT /api/watchlist` - Update stock
- `DELETE /api/watchlist?symbol=AAPL` - Remove stock

### Stock Universe
- `GET /api/stocks/search?q=apple` - Search stocks
- `GET /api/stocks/popular` - Popular stocks
- `GET /api/stocks/sectors` - List sectors
- `GET /api/stocks/filter?sector=Technology` - Filter by sector
- `GET /api/stocks/symbol/{symbol}` - Get by symbol

---

## Code Style Guidelines

### Python (Backend)
- Follow PEP 8 style guide
- Use type hints where appropriate
- Document classes and methods with docstrings
- Use async/await for I/O operations
- Handle exceptions gracefully with try/except blocks

**Example:**
```python
async def get_stock_metrics(self, symbol: str) -> Dict:
    """
    Retrieve stock metrics with fallback to multiple sources.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL')
        
    Returns:
        Dictionary containing financial metrics
    """
    try:
        # Implementation
        pass
    except Exception as e:
        logger.error(f"Failed to fetch metrics for {symbol}: {e}")
        return {'error': str(e)}
```

### JavaScript (Frontend)
- Use ES6+ class syntax for modules
- Use async/await for asynchronous operations
- Document public methods with JSDoc comments
- Use camelCase for variables and methods
- Use PascalCase for class names

**Example:**
```javascript
/**
 * Load stock metrics for the given symbol
 * @param {string} symbol - Stock ticker symbol
 * @returns {Promise<Object>} Stock metrics data
 */
async loadMetrics(symbol) {
    try {
        const data = await this.api.get(`/stock/metrics?symbol=${symbol}`);
        return data;
    } catch (error) {
        console.error('Failed to load metrics:', error);
        throw error;
    }
}
```

### SCSS/CSS
- Use Sass modules (`@use` instead of `@import`)
- Organize styles by component/section
- Use CSS custom properties for theming
- Follow BEM-like naming for classes

---

## Configuration

### Environment Variables (Backend)
Set in Lambda environment or SAM template:
- `FINANCIAL_API_KEY` - Alpha Vantage API key (or other provider)
- `FACTORS_TABLE` - DynamoDB table name for factors
- `WATCHLIST_TABLE` - DynamoDB table name for watchlist
- `STOCK_UNIVERSE_TABLE` - DynamoDB table name for stock universe
- `USERS_TABLE` - DynamoDB table name for users

### Frontend Configuration (`infrastructure/frontend/config.js`)
```javascript
const config = {
    apiEndpoint: 'https://xxx.execute-api.region.amazonaws.com/prod',
    frontendUrl: 'https://xxx.cloudfront.net',
    cognito: {
        region: 'us-east-1',
        userPoolId: 'us-east-1_xxx',
        userPoolClientId: 'xxx'
    },
    isDevelopment: false,
    debug: false
};
```

---

## DynamoDB Schema

### stock-factors Table
- **PK**: userId (String)
- **SK**: factorId (String)
- Stores user-defined screening criteria

### stock-watchlist Table
- **PK**: userId (String)
- **SK**: symbol (String)
- Stores user's watchlist with notes/tags

### stock-universe Table
- **PK**: symbol (String)
- **GSI1**: sector-index (sector + symbol)
- **GSI2**: marketcap-index (marketCapBucket + symbol)
- Stores comprehensive stock information

### stock-users Table
- **PK**: PK (String)
- **SK**: SK (String)
- Generic user data storage

---

## Security Considerations

1. **API Keys**: Never commit API keys to version control. Use:
   - Environment variables
   - AWS SSM Parameter Store (referenced in SAM template)
   - Lambda environment variables

2. **Authentication**: 
   - AWS Cognito for user authentication
   - JWT tokens for API authorization
   - Some endpoints (factors POST) require authentication

3. **CORS**: API Gateway configured with CORS headers

4. **Input Validation**: Validate all user inputs on backend

5. **HTTPS**: Enforced via CloudFront and API Gateway

---

## Development Workflow

### Local Development
1. Backend can be tested locally using SAM local:
   ```bash
   cd infrastructure
   sam local start-api
   ```

2. Frontend can be served locally:
   ```bash
   cd infrastructure/frontend
   python -m http.server 8000
   ```

3. Update `config.js` to point to local endpoints when developing locally

### Adding a New API Endpoint
1. Add route handler in `lambda_handler.py`
2. Implement business logic in appropriate module (e.g., `stock_api.py`)
3. Add API Gateway event in `template.yaml`
4. Update frontend API service if needed
5. Add tests

### Adding a New Frontend Module
1. Create module in `infrastructure/frontend/modules/`
2. Register in `app.js` `initializeModules()` method
3. Add corresponding section HTML in `infrastructure/frontend/sections/`
4. Update SCSS styles if needed
5. Add tests

---

## Troubleshooting

### Common Issues

**"AWS CLI not configured"**
- Run `aws configure` and enter credentials

**"CORS errors"**
- Verify API Gateway CORS configuration in template.yaml
- Check that `Access-Control-Allow-Origin` header is set

**"Stock data not loading"**
- Check Financial API key is set correctly
- Verify API rate limits haven't been exceeded
- Check Lambda logs in CloudWatch

**"DynamoDB access denied"**
- Verify Lambda execution role has appropriate DynamoDB permissions

### Viewing Logs
```bash
# Lambda logs via SAM
sam logs -n StockAPIFunction --stack-name stock-analyzer --tail

# Lambda logs via AWS CLI
aws logs tail /aws/lambda/stock-analyzer-StockAPIFunction --follow
```

---

## License

This project is licensed under the Non-Commercial Software License Agreement. See LICENSE file for details. Commercial use requires a separate license from Netbones Solutions Pty Ltd.

---

## Additional Resources

- `README.md` - User-facing setup and usage guide
- `PROJECT_OVERVIEW.md` - Detailed architecture and circuit breaker documentation
- `infrastructure/frontend/WORKFLOW.md` - Frontend workflow documentation
- `docs/` - Additional technical documentation

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

## Issue Tracking

This project uses **bd (beads)** for issue tracking.
Run `bd prime` for workflow context, or install hooks (`bd hooks install`) for auto-injection.

**Quick reference:**
- `bd ready` - Find unblocked work
- `bd create "Title" --type task --priority 2` - Create issue
- `bd close <id>` - Complete work
- `bd sync` - Sync with git (run at session end)

For full workflow details: `bd prime`



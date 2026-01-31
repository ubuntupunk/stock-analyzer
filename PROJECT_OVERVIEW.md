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
       │                └────────┬────────┘
       │                         │
       │                         ▼
       │              ┌──────────────────────┐
       │              │  Amazon DynamoDB     │
       │              │  - Factors Table     │
       │              │  - Watchlist Table   │
       │              └──────────────────────┘
       │
       ▼
┌──────────────────────┐
│  External Financial  │
│     Data API         │
│  (Alpha Vantage)     │
└──────────────────────┘
```

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
├── .gitignore            # Git ignore rules
│
├── deploy.sh             # Automated deployment script
├── test.sh               # API testing script
│
├── backend/              # Lambda functions
│   ├── stock_api.py      # Stock data retrieval
│   ├── screener_api.py   # Screening & DCF analysis
│   ├── watchlist_api.py  # Watchlist management
│   └── requirements.txt  # Python dependencies
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

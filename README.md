# Stock Analyzer Application

A comprehensive stock analysis platform with tools for DCF valuation, factor screening, watchlists, and financial metrics visualization.

## Features

### 📊 Core Functionality
- **Stock Metrics Dashboard**: View comprehensive financial metrics including P/E ratios, revenue growth, ROI, and more
- **Analyst Estimates**: Track consensus earnings and revenue estimates
- **DCF Analyzer**: Perform discounted cash flow analysis with customizable assumptions
- **Factor Screener**: Create custom stock screening criteria based on financial factors
- **Watchlist Management**: Track your favorite stocks with real-time updates
- **Interactive Charts**: Visualize stock prices and analyst estimates

### 🛠 Tools Menu
1. **Retirement Calculator**: Calculate investment requirements for retirement goals
2. **Stock Analyser**: Deep dive DCF valuation tool
3. **Analyst Estimates**: View consensus estimates
4. **Factor Search**: Pre-screened stock searches
5. **Model Portfolio**: Portfolio modeling tools
6. **Real Estate Calculator**: Bond and ROI calculations
7. **Factor Screener**: Custom stock screening
8. **Watchlist**: Starred items tracking

## Architecture

### Backend (AWS Lambda)
- **Language**: Python 3.11
- **Functions**:
  - `stock_api.py`: Stock data retrieval (metrics, prices, financials, estimates)
  - `screener_api.py`: Stock screening and DCF analysis
  - `watchlist_api.py`: Watchlist management

### Frontend (S3 Static Hosting)
- **Technologies**: HTML5, CSS3, Vanilla JavaScript
- **Libraries**: Chart.js for data visualization
- **Design**: Responsive, mobile-friendly interface

### Infrastructure
- **API Gateway**: RESTful API with CORS support
- **DynamoDB**: Two tables (stock-factors, stock-watchlist)
- **S3**: Static website hosting
- **CloudFormation/SAM**: Infrastructure as Code

## Prerequisites

### Required Tools
1. **AWS CLI** (v2+)
   ```bash
   # Install on macOS
   brew install awscli
   
   # Install on Linux
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   ```

2. **AWS SAM CLI**
   ```bash
   # Install on macOS
   brew install aws-sam-cli
   
   # Install on Linux
   pip install aws-sam-cli
   ```

3. **Python 3.11+**
   ```bash
   python --version  # Should be 3.11 or higher
   ```

4. **Financial Data API Key** (Optional but recommended)
   - Alpha Vantage: https://www.alphavantage.co/support/#api-key
   - Or use another financial data provider

### AWS Configuration
Configure your AWS credentials:
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter your default region (e.g., us-east-1)
# Enter your default output format (json)
```

## Installation & Deployment

### 1. Clone or Download the Project
```bash
cd stock-analyzer
```

### 2. Set Up Development Environment
First, install the project dependencies and set up code quality tools:

```bash
# Install project dependencies
pip install -r infrastructure/backend/requirements.txt

# Install and set up pre-commit hooks (formats code automatically before commits)
pip install pre-commit
pre-commit install
```

For JavaScript development, install additional code quality tools:

```bash
# Install ESLint, Prettier, and related packages
npm install --save-dev eslint prettier eslint-config-prettier eslint-plugin-prettier
```

### 3. Set Environment Variables
```bash
# Optional: Set your financial API key
export FINANCIAL_API_KEY="your_api_key_here"

# Or use the demo key (limited functionality)
export FINANCIAL_API_KEY="demo"
```

### 3. Deploy Using the Deployment Script
```bash
./deploy.sh
```

The deployment script will:
1. Build the SAM application
2. Deploy Lambda functions, API Gateway, and DynamoDB tables
3. Retrieve the API Gateway endpoint
4. Update the frontend configuration
5. Deploy the frontend to S3
6. Display the website and API URLs

### 4. Manual Deployment (Alternative)

#### Deploy Backend
```bash
cd infrastructure
sam build
sam deploy --guided
```

During the guided deployment, you'll be prompted for:
- Stack name (default: stock-analyzer-stack)
- AWS Region (e.g., us-east-1)
- Financial API Key
- S3 Bucket Name for frontend

#### Deploy Frontend
```bash
cd frontend

# Update config.js with your API Gateway endpoint
# Then sync to S3
aws s3 sync . s3://your-bucket-name/ --delete
```

## Configuration

### Frontend Configuration (`frontend/config.js`)
```javascript
const config = {
    // Your API Gateway endpoint (auto-populated by deploy script)
    apiEndpoint: 'https://xxx.execute-api.region.amazonaws.com/prod',
    
    // Feature toggles
    features: {
        enableRealTimeData: true,
        enableWatchlist: true,
        enableDCF: true,
        enableScreener: true
    },
    
    // Chart settings
    charts: {
        defaultPeriod: '1Y',
        refreshInterval: 60000  // 60 seconds
    }
};
```

### Backend Environment Variables
Set these in the Lambda console or SAM template:
- `FINANCIAL_API_KEY`: Your financial data API key
- `FACTORS_TABLE`: DynamoDB table name for factors
- `WATCHLIST_TABLE`: DynamoDB table name for watchlist

## API Endpoints

### Stock Data
- `GET /api/stock/metrics?symbol={SYMBOL}` - Get stock metrics
- `GET /api/stock/price?symbol={SYMBOL}` - Get current price and historical data
- `GET /api/stock/estimates?symbol={SYMBOL}` - Get analyst estimates
- `GET /api/stock/financials?symbol={SYMBOL}` - Get financial statements

### Screening & Analysis
- `POST /api/screen` - Screen stocks based on criteria
  ```json
  {
    "criteria": {
      "pe_ratio": {"max": 22.5},
      "roic": {"min": 0.09}
    }
  }
  ```
- `POST /api/dcf` - Calculate DCF valuation
  ```json
  {
    "currentPrice": 368,
    "assumptions": {
      "revenueGrowth": {"low": 0.03, "mid": 0.05, "high": 0.07},
      "profitMargin": {"low": 0.09, "mid": 0.10, "high": 0.11}
    },
    "yearsToProject": 10
  }
  ```

### Factors
- `GET /api/factors` - Get user's saved factors
- `POST /api/factors` - Save a new factor

### Watchlist
- `GET /api/watchlist` - Get user's watchlist
- `POST /api/watchlist` - Add stock to watchlist
- `PUT /api/watchlist` - Update watchlist item
- `DELETE /api/watchlist?symbol={SYMBOL}` - Remove from watchlist

## Usage Examples

### Viewing Stock Metrics
1. Enter a stock symbol in the search bar (e.g., "AAPL", "MSFT", "GOOGL")
2. Navigate to the "METRICS" tab
3. View comprehensive financial metrics and charts

### Performing DCF Analysis
1. Search for a stock
2. Click "Stock Analyser" in the tools menu or "STOCK ANALYSER" tab
3. Adjust assumptions in the "My Assumptions" table
4. Click "Analyse (Button)" to run the analysis
5. View results in the "Output from Analysis" section

### Creating a Custom Factor Screen
1. Navigate to "FACTORS" tab
2. Click the + button to add a new factor
3. Define your screening criteria (e.g., P/E < 22.5, ROIC > 9%)
4. Save and use for stock screening

### Managing Watchlist
1. Search for a stock
2. Click "ON WATCHLIST" button to add/remove
3. Navigate to "WATCHLIST" tab to view all tracked stocks
4. Click "Add Stock" to add more stocks

## Project Structure

```
stock-analyzer/
├── backend/
│   ├── stock_api.py          # Stock data retrieval Lambda
│   ├── screener_api.py        # Screening & DCF Lambda
│   ├── watchlist_api.py       # Watchlist management Lambda
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── index.html             # Main HTML file
│   ├── styles.css             # Application styles
│   ├── config.js              # Configuration
│   ├── api.js                 # API service layer
│   └── app.js                 # Application logic
├── infrastructure/
│   └── template.yaml          # SAM/CloudFormation template
├── deploy.sh                  # Deployment script
└── README.md                  # This file
```

## Cost Estimation

### AWS Free Tier Eligible
- Lambda: 1M requests/month free
- API Gateway: 1M calls/month free (first 12 months)
- DynamoDB: 25GB storage, 25 read/write capacity units free
- S3: 5GB storage, 20k GET requests, 2k PUT requests free (first 12 months)

### Beyond Free Tier (Estimated)
- Lambda: $0.20 per 1M requests
- API Gateway: $3.50 per 1M requests
- DynamoDB: $0.25 per GB/month (on-demand)
- S3: $0.023 per GB/month

**Estimated monthly cost for moderate usage**: $5-20/month

## Customization

### Adding New Financial Data Sources
Edit `backend/stock_api.py`:
```python
class StockDataAPI:
    def __init__(self):
        self.api_key = os.environ.get('YOUR_API_KEY')
        self.base_url = "https://your-api-provider.com"
```

### Adding New Metrics
1. Update the backend to fetch new metrics
2. Add display fields in `frontend/index.html`
3. Update `updateMetricsDisplay()` in `frontend/app.js`

### Customizing Styles
Edit `frontend/styles.css` to change:
- Color scheme (CSS variables in `:root`)
- Layout (grid/flexbox properties)
- Typography (font families, sizes)

## Troubleshooting

### Issue: "AWS CLI not configured"
**Solution**: Run `aws configure` and enter your credentials

### Issue: "API returns CORS errors"
**Solution**: Ensure API Gateway CORS is properly configured in `template.yaml`

### Issue: "Stock data not loading"
**Solution**: 
1. Check if your Financial API key is set correctly
2. Verify API rate limits haven't been exceeded
3. Check Lambda logs in CloudWatch

### Issue: "DynamoDB access denied"
**Solution**: Verify Lambda execution role has DynamoDB permissions

### Viewing Logs
```bash
# View Lambda logs
sam logs -n StockAPIFunction --stack-name stock-analyzer-stack --tail

# View all logs
aws logs tail /aws/lambda/stock-analyzer-stack-StockAPIFunction --follow
```

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Authentication**: Consider adding AWS Cognito for user authentication
3. **Rate Limiting**: Implement API Gateway throttling
4. **Input Validation**: Validate all user inputs on the backend
5. **HTTPS**: Use HTTPS for all API calls (enforced by API Gateway)

## Future Enhancements

- [ ] Add user authentication with AWS Cognito
- [ ] Implement real-time stock price updates with WebSockets
- [ ] Add more financial calculators (options pricing, bond valuation)
- [ ] Export analysis to PDF/Excel
- [ ] Social features (share analysis, community factors)
- [ ] Mobile app (React Native/Flutter)
- [ ] Advanced charting with technical indicators
- [ ] Portfolio tracking and performance analysis

## Contributing

This is a template project. To contribute:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review AWS CloudWatch logs
3. Verify your configuration

## License

This project is licensed under the **Non-Commercial Software License Agreement**.

### Non-Commercial Use
This software is free to use for:
- Personal use
- Educational purposes
- Academic research
- Non-profit organizations
- Evaluation and testing

### Commercial Use
**Commercial use requires a separate license agreement.**

If you intend to use this software for commercial purposes (including but not limited to use by for-profit businesses, in commercial products/services, or in production environments), you must contact:

**Netbones Solutions Pty Ltd**
South Africa
Email: [Please specify contact email]
Website: [Please specify website]

Please provide details about your intended commercial use, including organization name, use case, and expected scale of deployment.

### License Terms
By using this software, you agree to the terms and conditions outlined in the [LICENSE](LICENSE) file. For the full license agreement, please see the LICENSE file in this repository.

**Important**: Any commercial use without obtaining a proper license agreement is a violation of the license terms.

## Acknowledgments

- Built with AWS Lambda, API Gateway, DynamoDB, and S3
- Uses Chart.js for data visualization
- Financial data powered by Alpha Vantage (or your chosen provider)

---

**Note**: Remember to replace placeholder values (API keys, bucket names, etc.) with your actual values before deployment.

# Stock Analyzer - Deployment Guide (Without Auth)

## 🚀 Quick Start Deployment

This guide walks you through deploying the Stock Analyzer application **without authentication** to test core functionality first.

---

## ✅ Pre-Deployment Checklist

### **1. Prerequisites Installed**

Check you have the required tools:

```bash
# Check AWS CLI
aws --version
# Expected: aws-cli/2.x.x or higher

# Check SAM CLI
sam --version
# Expected: SAM CLI, version 1.x.x or higher

# Check Python
python3 --version
# Expected: Python 3.11 or higher

# Check Node.js (optional, for local testing)
node --version
# Expected: v18.x or higher
```

**Install if missing:**
```bash
# AWS CLI: https://aws.amazon.com/cli/
# SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
```

---

### **2. AWS Credentials Configured**

```bash
# Check current AWS configuration
aws sts get-caller-identity

# Should return:
{
    "UserId": "AIDAI...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/yourname"
}

# If not configured, run:
aws configure
# Enter:
#   AWS Access Key ID: YOUR_KEY
#   AWS Secret Access Key: YOUR_SECRET
#   Default region name: us-east-1
#   Default output format: json
```

**Region Selection:**
- Recommended: `us-east-1` (cheapest, most services)
- Alternative: `us-west-2`, `eu-west-1`

---

### **3. Set Environment Variables**

```bash
# Required: Financial API Key (or use demo)
export FINANCIAL_API_KEY="demo"
# Get free key: https://www.alphavantage.co/support/#api-key

# Optional: Other API keys (for enhanced features)
export POLYGON_API_KEY=""
export ALPACA_API_KEY=""
export ALPACA_SECRET_KEY=""

# Verify
echo $FINANCIAL_API_KEY
```

---

### **4. Project Structure Verification**

Ensure all files are in place:

```bash
# From project root, check structure
tree -L 2

# Should see:
.
├── backend/
│   ├── requirements.txt
│   ├── screener_api.py
│   ├── stock_api.py          ✅ (newly created)
│   └── watchlist_api.py
├── frontend/
│   ├── api.js
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── infrastructure/
│   └── template.yaml
├── deploy.sh                  ✅ (deployment script)
├── README.md
└── PROJECT_OVERVIEW.md
```

---

## 🎯 Deployment Steps

### **Step 1: Review Deployment Script**

```bash
# Make script executable
chmod +x deploy.sh

# Review what it will do
cat deploy.sh

# The script will:
# 1. Build SAM application
# 2. Package Lambda functions
# 3. Deploy to AWS (CloudFormation)
# 4. Upload frontend to S3
# 5. Generate config.js with API endpoint
```

---

### **Step 2: Run Deployment**

```bash
# Deploy everything
./deploy.sh

# Expected output:
# ✓ Checking prerequisites...
# ✓ Building SAM application...
# ✓ Deploying to AWS...
# ✓ Uploading frontend to S3...
# ✓ Deployment complete!
#
# 🎉 Your Stock Analyzer is live!
```

**Deployment Time:** ~3-5 minutes

**What's Being Created:**
- 3 Lambda functions (StockAPI, ScreenerAPI, WatchlistAPI)
- API Gateway REST API
- 2 DynamoDB tables (stock-watchlist, stock-factors)
- S3 bucket for frontend
- CloudFormation stack

---

### **Step 3: Verify Deployment**

After deployment, you'll see:

```bash
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 Deployment Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Frontend URL:
http://stock-analyzer-frontend-TIMESTAMP.s3-website-us-east-1.amazonaws.com

API Endpoint:
https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod
```

**Save these URLs!** You'll need them for testing.

---

## 🧪 Testing Your Deployment

### **Test 1: Frontend Access**

```bash
# Open in browser
open http://stock-analyzer-frontend-TIMESTAMP.s3-website-us-east-1.amazonaws.com

# Or use curl
curl -I http://stock-analyzer-frontend-TIMESTAMP.s3-website-us-east-1.amazonaws.com
# Should return: HTTP/1.1 200 OK
```

**Expected:** Stock Analyzer UI loads

---

### **Test 2: API Endpoints**

Replace `API_ENDPOINT` with your actual endpoint from deployment output.

```bash
export API_ENDPOINT="https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod"

# Test 1: Stock Metrics
curl "${API_ENDPOINT}/api/stock/metrics?symbol=AAPL" | jq .

# Expected response:
{
  "symbol": "AAPL",
  "timestamp": "2026-01-28T...",
  "source": "yahoo_finance",
  "company_name": "Apple Inc.",
  "current_price": 178.50,
  "pe_ratio": 28.5,
  "market_cap": 2850000000000,
  ...
}

# Test 2: Stock Price
curl "${API_ENDPOINT}/api/stock/price?symbol=MSFT" | jq .

# Test 3: Analyst Estimates
curl "${API_ENDPOINT}/api/stock/estimates?symbol=GOOGL" | jq .

# Test 4: Financial Statements
curl "${API_ENDPOINT}/api/stock/financials?symbol=TSLA" | jq .

# Test 5: Stock Screener
curl -X POST "${API_ENDPOINT}/api/screener" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "minMarketCap": 1000000000,
      "maxPE": 30
    }
  }' | jq .

# Test 6: Watchlist - Add Stock
curl -X POST "${API_ENDPOINT}/api/watchlist" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "notes": "Testing watchlist"
  }' | jq .

# Test 7: Watchlist - Get All
curl "${API_ENDPOINT}/api/watchlist" | jq .
```

---

### **Test 3: Frontend Functionality**

**Manual Testing in Browser:**

1. **Stock Search**
   - Enter symbol: `AAPL`
   - Click "Get Metrics"
   - Verify data displays

2. **Stock Screener**
   - Set filters (P/E < 30, Market Cap > $1B)
   - Click "Run Screener"
   - Verify results appear

3. **Watchlist**
   - Add stock to watchlist
   - Verify it appears in list
   - Remove stock
   - Verify it's removed

4. **Price Charts**
   - Select stock with historical data
   - Verify price chart renders

---

## 📊 Monitoring Your Deployment

### **1. CloudWatch Logs**

```bash
# View Lambda logs
sam logs -n StockAPIFunction --tail

# View all logs
sam logs --tail

# View specific time range
sam logs -n StockAPIFunction --start-time '5min ago' --tail
```

---

### **2. AWS Console Monitoring**

**CloudWatch Dashboard:**
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:
```

**Key Metrics to Watch:**
- Lambda Invocations
- Lambda Errors
- Lambda Duration
- API Gateway 4XX/5XX errors
- DynamoDB Read/Write capacity

---

### **3. Cost Monitoring**

```bash
# Check current costs (after 24 hours)
aws ce get-cost-and-usage \
  --time-period Start=2026-01-28,End=2026-01-29 \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

**Set up Budget Alert:**
```
https://console.aws.amazon.com/billing/home#/budgets
```

Recommended: $10/month alert

---

## 🔧 Troubleshooting

### **Issue 1: Deployment Fails**

**Symptom:** SAM deploy returns error

**Solutions:**

```bash
# Check AWS credentials
aws sts get-caller-identity

# Check SAM CLI version
sam --version

# Check CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name stock-analyzer \
  --max-items 10

# View detailed error
sam logs -n StockAPIFunction --tail
```

**Common Issues:**
- ❌ Insufficient IAM permissions → Add AdministratorAccess
- ❌ Stack already exists → Run `sam delete` first
- ❌ S3 bucket name conflict → Change bucket name in deploy.sh

---

### **Issue 2: API Returns 500 Errors**

**Symptom:** API calls return Internal Server Error

**Solutions:**

```bash
# Check Lambda logs
sam logs -n StockAPIFunction --tail

# Test Lambda locally
sam local invoke StockAPIFunction -e test_event.json

# Check environment variables
aws lambda get-function-configuration \
  --function-name stock-analyzer-StockAPIFunction-XXXXX \
  --query 'Environment'
```

**Common Issues:**
- ❌ Missing API key → Set FINANCIAL_API_KEY
- ❌ Python import error → Check requirements.txt
- ❌ Timeout → Increase Lambda timeout in template.yaml

---

### **Issue 3: Frontend Not Loading**

**Symptom:** S3 URL returns 403 Forbidden

**Solutions:**

```bash
# Check S3 bucket policy
aws s3api get-bucket-policy --bucket stock-analyzer-frontend-TIMESTAMP

# Check bucket website configuration
aws s3api get-bucket-website --bucket stock-analyzer-frontend-TIMESTAMP

# Manually set public read
aws s3api put-bucket-policy \
  --bucket stock-analyzer-frontend-TIMESTAMP \
  --policy file://bucket-policy.json

# Re-upload frontend
cd frontend
aws s3 sync . s3://stock-analyzer-frontend-TIMESTAMP/ --acl public-read
```

---

### **Issue 4: CORS Errors**

**Symptom:** Browser console shows CORS error

**Solutions:**

Check Lambda response headers in `backend/*.py`:

```python
# Ensure all responses have CORS headers
'headers': {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    'Content-Type': 'application/json'
}
```

---

### **Issue 5: API Key Limits Exceeded**

**Symptom:** API returns "API call frequency limit exceeded"

**Solutions:**

```bash
# Check Alpha Vantage usage
# Free tier: 25 calls/day

# Upgrade API key
# https://www.alphavantage.co/premium/

# Or use caching to reduce calls
# Cache is already implemented (5-minute TTL)
```

---

## 🎯 Post-Deployment Actions

### **1. Document Your URLs**

Create `deployed-urls.txt`:

```bash
cat > deployed-urls.txt << EOF
Frontend URL: http://stock-analyzer-frontend-TIMESTAMP.s3-website-us-east-1.amazonaws.com
API Endpoint: https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod
CloudFormation Stack: stock-analyzer
Region: us-east-1
Deployed: $(date)
EOF
```

---

### **2. Test All Features**

Use the included test script:

```bash
# Create test script
cat > test_deployment.sh << 'EOF'
#!/bin/bash
API_ENDPOINT=$1

if [ -z "$API_ENDPOINT" ]; then
    echo "Usage: ./test_deployment.sh <API_ENDPOINT>"
    exit 1
fi

echo "Testing Stock Analyzer API..."

# Test 1: Stock Metrics
echo "Test 1: Stock Metrics (AAPL)"
curl -s "${API_ENDPOINT}/api/stock/metrics?symbol=AAPL" | jq -r '.symbol, .current_price, .pe_ratio'

# Test 2: Stock Price
echo "Test 2: Stock Price (MSFT)"
curl -s "${API_ENDPOINT}/api/stock/price?symbol=MSFT" | jq -r '.symbol, .price, .change_percent'

# Test 3: Estimates
echo "Test 3: Analyst Estimates (GOOGL)"
curl -s "${API_ENDPOINT}/api/stock/estimates?symbol=GOOGL" | jq -r '.symbol, .earnings_estimates[0]'

# Test 4: Financials
echo "Test 4: Financial Statements (TSLA)"
curl -s "${API_ENDPOINT}/api/stock/financials?symbol=TSLA" | jq -r '.symbol, .income_statement[0].fiscal_date'

echo "✅ All tests complete!"
EOF

chmod +x test_deployment.sh

# Run tests
./test_deployment.sh "https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod"
```

---

### **3. Set Up Monitoring**

**CloudWatch Alarms:**

```bash
# Create alarm for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name stock-analyzer-lambda-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

---

### **4. Share with Team**

Create a quick reference card:

```markdown
# Stock Analyzer - Quick Reference

## URLs
- Frontend: http://stock-analyzer-frontend-TIMESTAMP.s3-website-us-east-1.amazonaws.com
- API: https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod

## API Endpoints
- GET  /api/stock/metrics?symbol=AAPL
- GET  /api/stock/price?symbol=MSFT
- GET  /api/stock/estimates?symbol=GOOGL
- GET  /api/stock/financials?symbol=TSLA
- POST /api/screener
- GET  /api/watchlist
- POST /api/watchlist
- DELETE /api/watchlist/{symbol}

## Test Command
curl "https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod/api/stock/metrics?symbol=AAPL"
```

---

## 🧹 Cleanup (When Done Testing)

To remove all resources:

```bash
# Delete CloudFormation stack
sam delete --stack-name stock-analyzer

# Delete S3 bucket (if not auto-deleted)
aws s3 rb s3://stock-analyzer-frontend-TIMESTAMP --force

# Delete DynamoDB tables (if not auto-deleted)
aws dynamodb delete-table --table-name stock-watchlist
aws dynamodb delete-table --table-name stock-factors
```

**Cost after cleanup:** $0

---

## 📈 Next Steps After Testing

Once you've validated core functionality:

1. **Add Authentication**
   - Implement AWS Cognito
   - See: `COGNITO_COST_ANALYSIS.md`

2. **Add Monitoring**
   - CloudWatch dashboards
   - Custom metrics
   - Error alerting

3. **Add CI/CD**
   - GitHub Actions
   - Automated testing
   - Auto-deploy on push

4. **Optimize Performance**
   - Reduce Lambda cold starts
   - Implement CloudFront CDN
   - Add Redis caching

5. **Add Features**
   - Portfolio tracking
   - Price alerts
   - Email notifications
   - Premium features

---

## 📊 Expected Costs (Without Auth)

**First 12 Months (Free Tier):**
```
Lambda:              $0.00
API Gateway:         $0.00
DynamoDB:            $0.00
S3:                  $0.00
Data Transfer:       $0.00
───────────────────────────
TOTAL:               $0.00/month ✅
```

**After Free Tier (1,000 requests/day):**
```
Lambda:              $0.13
API Gateway:         $0.11
DynamoDB:            $0.00 (always free tier)
S3:                  $0.01
───────────────────────────
TOTAL:               $0.25/month ✅
```

---

## 🎉 Summary

You're ready to deploy! Here's the quick command:

```bash
# Set API key (or use demo)
export FINANCIAL_API_KEY="demo"

# Deploy
./deploy.sh

# Test
curl "$(cat deployed-urls.txt | grep API | cut -d' ' -f3)/api/stock/metrics?symbol=AAPL"
```

**Deployment time:** 3-5 minutes  
**Cost:** $0/month (Free Tier)  
**Next:** Test functionality, then add auth

---

Good luck! 🚀

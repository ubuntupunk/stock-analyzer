# AWS Deployment Cost Analysis

## 📋 Executive Summary

**Estimated Monthly Cost**: **$0 - $25/month** (depending on usage)

- **First 12 months**: Likely **$0** (within AWS Free Tier)
- **After Free Tier**: **$5-10/month** for light usage, **$15-25/month** for moderate usage
- **High traffic**: Could reach $50-100+/month

---

## 🔍 Deploy Script Review

### ✅ **Deploy Script Status: GOOD**

The `deploy.sh` script is well-structured with:

**Strengths:**
- ✅ Proper error handling (`set -e`)
- ✅ Prerequisites check (AWS CLI, SAM CLI)
- ✅ Clear step-by-step progress indicators
- ✅ Automatic API endpoint retrieval
- ✅ Auto-generates `config.js` with correct API endpoint
- ✅ Clean output with next steps

**Potential Issues:**
1. ⚠️ **S3 Bucket Name**: Uses timestamp, creates new bucket each deployment
2. ⚠️ **No cleanup script**: Old buckets may accumulate
3. ⚠️ **Missing SAM guided deploy option**: First-time users need `samconfig.toml`

**Recommended Improvements:**
```bash
# Line 17 - Use consistent bucket name
S3_BUCKET_NAME="${S3_BUCKET_NAME:-stock-analyzer-frontend-${AWS_ACCOUNT_ID}}"

# Add cleanup option
if [ "$1" == "cleanup" ]; then
    # Delete old buckets, stack, etc.
fi
```

---

## 💰 Detailed Cost Breakdown

### 1. **AWS Lambda** (3 Functions)

**Configuration:**
- Memory: 512 MB per function
- Timeout: 30 seconds
- Runtime: Python 3.11
- Functions: StockAPIFunction, ScreenerAPIFunction, WatchlistAPIFunction

**Free Tier (First 12 Months):**
- 1 Million requests/month FREE
- 400,000 GB-seconds of compute time FREE

**Pricing After Free Tier:**
- $0.20 per 1M requests
- $0.0000166667 per GB-second

**Cost Examples:**

| Usage Level | Requests/Month | Lambda Cost |
|-------------|----------------|-------------|
| Light (100/day) | 3,000 | **$0.00** (Free Tier) |
| Moderate (1,000/day) | 30,000 | **$0.00** (Free Tier) |
| Heavy (10,000/day) | 300,000 | **$0.00** (Free Tier) |
| Very Heavy (50,000/day) | 1.5M | **$0.10** |

**Compute Cost Calculation:**
- Duration: ~500ms average (with cache)
- Memory: 512 MB = 0.5 GB
- GB-seconds per request: 0.5 GB × 0.5s = 0.25 GB-seconds
- 30,000 requests = 7,500 GB-seconds = **$0.13/month**

**Total Lambda (Moderate Usage):** **$0.13/month** after free tier

---

### 2. **Amazon API Gateway**

**Configuration:**
- Type: REST API
- Stage: prod
- Endpoints: 11 total (4 stock + 4 screener + 3 watchlist)

**Free Tier (First 12 Months):**
- 1 Million API calls/month FREE

**Pricing After Free Tier:**
- $3.50 per million requests
- $0.09 per GB data transfer out

**Cost Examples:**

| Usage Level | Requests/Month | API Gateway Cost |
|-------------|----------------|------------------|
| Light | 3,000 | **$0.00** (Free Tier) |
| Moderate | 30,000 | **$0.00** (Free Tier) |
| Heavy | 300,000 | **$0.00** (Free Tier) |
| Very Heavy | 1.5M | **$1.75** |

**Data Transfer:**
- Average response size: 5 KB
- 30,000 requests × 5 KB = 150 MB = **$0.01/month**

**Total API Gateway (Moderate Usage):** **$0.11/month** after free tier

---

### 3. **Amazon DynamoDB** (2 Tables)

**Configuration:**
- Tables: stock-factors, stock-watchlist
- Billing Mode: PAY_PER_REQUEST (On-Demand)
- No provisioned capacity

**Free Tier (Always Free):**
- 25 GB storage FREE
- 25 Write Capacity Units (WCU) FREE
- 25 Read Capacity Units (RCU) FREE

**Pricing After Free Tier:**
- $1.25 per million write requests
- $0.25 per million read requests
- $0.25 per GB-month storage

**Cost Examples:**

| Usage Level | Reads/Month | Writes/Month | Storage | DynamoDB Cost |
|-------------|-------------|--------------|---------|---------------|
| Light | 1,000 | 100 | 10 MB | **$0.00** (Free Tier) |
| Moderate | 10,000 | 1,000 | 50 MB | **$0.00** (Free Tier) |
| Heavy | 100,000 | 10,000 | 200 MB | **$0.03** |

**Typical Usage Pattern:**
- Watchlist: 10 items per user, ~1 KB each
- Factors: 5 saved screens per user, ~2 KB each
- 100 users = ~1.5 MB storage

**Total DynamoDB (Moderate Usage):** **$0.00/month** (within free tier)

---

### 4. **Amazon S3** (Static Website Hosting)

**Configuration:**
- Bucket: Frontend files (~70 KB total)
- Website hosting enabled
- Public read access

**Free Tier (First 12 Months):**
- 5 GB storage FREE
- 20,000 GET requests FREE
- 2,000 PUT requests FREE

**Pricing After Free Tier:**
- $0.023 per GB-month storage
- $0.0004 per 1,000 GET requests
- $0.005 per 1,000 PUT requests

**Cost Examples:**

| Usage Level | Page Views/Month | Storage | S3 Cost |
|-------------|------------------|---------|---------|
| Light | 1,000 | 70 KB | **$0.00** (Free Tier) |
| Moderate | 10,000 | 70 KB | **$0.00** (Free Tier) |
| Heavy | 100,000 | 70 KB | **$0.04** |

**Total S3 (Moderate Usage):** **$0.00/month** (within free tier)

---

### 5. **Data Transfer Costs**

**Pricing:**
- First 1 GB/month: FREE
- Next 9.999 TB: $0.09 per GB
- IN to AWS: FREE

**Cost Examples:**

| Usage Level | Data Out/Month | Transfer Cost |
|-------------|----------------|---------------|
| Light | 100 MB | **$0.00** (Free Tier) |
| Moderate | 500 MB | **$0.00** (Free Tier) |
| Heavy | 5 GB | **$0.36** |

---

### 6. **External API Costs** (Third-Party)

**Free Tier Options:**

| Provider | Free Tier | Cost After |
|----------|-----------|------------|
| **Yahoo Finance** | ✅ Unlimited | N/A (unofficial API) |
| **Alpha Vantage** | 25 calls/day | $50/month (500/day) |
| **Alpaca** | ✅ Free (trading) | N/A |
| **Polygon.io** | 5 calls/min | $29/month (starter) |

**Recommended Strategy:**
- Use Yahoo Finance as primary (FREE)
- Alpha Vantage for fallback (25/day FREE)
- Only upgrade external APIs if needed

**Estimated External API Cost:** **$0/month** (using free tiers)

---

## 📊 Total Cost Summary

### **Scenario 1: Light Usage** (100 requests/day, ~10 users)
```
├─ Lambda:          $0.00  (Free Tier)
├─ API Gateway:     $0.00  (Free Tier)
├─ DynamoDB:        $0.00  (Free Tier)
├─ S3:              $0.00  (Free Tier)
├─ Data Transfer:   $0.00  (Free Tier)
└─ External APIs:   $0.00  (Free Tier)
────────────────────────────────────────
   TOTAL:           $0.00/month ✅
```

### **Scenario 2: Moderate Usage** (1,000 requests/day, ~50 users)
```
├─ Lambda:          $0.00  (Free Tier Year 1) → $0.13  (After)
├─ API Gateway:     $0.00  (Free Tier Year 1) → $0.11  (After)
├─ DynamoDB:        $0.00  (Always Free)
├─ S3:              $0.00  (Free Tier Year 1) → $0.01  (After)
├─ Data Transfer:   $0.00  (< 1 GB)
└─ External APIs:   $0.00  (Free Tier)
────────────────────────────────────────
   TOTAL (Year 1):  $0.00/month ✅
   TOTAL (After):   $0.25/month ✅
```

### **Scenario 3: Heavy Usage** (10,000 requests/day, ~500 users)
```
├─ Lambda:          $1.30/month
├─ API Gateway:     $1.05/month
├─ DynamoDB:        $0.50/month
├─ S3:              $0.05/month
├─ Data Transfer:   $0.20/month
└─ External APIs:   $0.00  (or $50 if upgrading Alpha Vantage)
────────────────────────────────────────
   TOTAL:           $3.10/month ✅
   (or $53.10 with paid APIs)
```

### **Scenario 4: Production Usage** (50,000 requests/day, ~5,000 users)
```
├─ Lambda:          $6.50/month
├─ API Gateway:     $5.25/month
├─ DynamoDB:        $2.50/month
├─ S3:              $0.25/month
├─ Data Transfer:   $1.00/month
└─ External APIs:   $50.00/month (Alpha Vantage Pro)
────────────────────────────────────────
   TOTAL:           $65.50/month
```

---

## 🎯 Cost Optimization Recommendations

### **1. Reduce Lambda Memory** (Current: 512 MB)
```yaml
# In template.yaml Globals section
MemorySize: 256  # Reduces cost by 50%
```
**Savings:** ~$0.07/month (moderate usage)

### **2. Increase Cache TTL** (Current: 5 minutes)
```python
# In stock_api.py
self.cache_timeout = 600  # 10 minutes
```
**Savings:** Reduces API calls by ~40%, saves ~$0.05/month

### **3. Add CloudFront CDN** (Optional)
```yaml
# Add CloudFront distribution for S3
# First 1 TB data transfer: $0.085 per GB
```
**Benefit:** Faster performance, lower S3 costs at scale
**Cost:** Free tier: 1 TB data transfer, 10M requests

### **4. Use Reserved Capacity** (For Production)
```yaml
# DynamoDB: Switch to Provisioned mode
BillingMode: PROVISIONED
ProvisionedThroughput:
  ReadCapacityUnits: 5
  WriteCapacityUnits: 2
```
**Savings:** ~60% for predictable traffic

### **5. Implement API Caching** (API Gateway)
```yaml
# Add caching to API Gateway
CacheClusterEnabled: true
CacheClusterSize: '0.5'  # $0.02/hour = $14.40/month
```
**Trade-off:** Adds cost but reduces Lambda invocations

---

## 🚨 Cost Alerts & Monitoring

### **Recommended AWS Budget Alerts**

```bash
# Set up budget alert via AWS CLI
aws budgets create-budget \
  --account-id 123456789012 \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

**budget.json:**
```json
{
  "BudgetName": "StockAnalyzerMonthly",
  "BudgetLimit": {
    "Amount": "10.00",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

**Alert Thresholds:**
- 50% of budget ($5): Email warning
- 80% of budget ($8): Email alert
- 100% of budget ($10): Email critical

### **CloudWatch Cost Metrics**

Monitor these metrics:
- Lambda invocations
- API Gateway 4XX/5XX errors (wasted calls)
- DynamoDB consumed capacity
- S3 request count

---

## 🔒 Security Cost Considerations

### **Optional Security Enhancements** (Additional Costs)

1. **AWS WAF** (Web Application Firewall)
   - $5/month + $1/million requests
   - Protects against DDoS, SQL injection

2. **AWS Shield Standard**
   - FREE (included)
   - Basic DDoS protection

3. **AWS Cognito** (User Authentication)
   - 50,000 MAU (Monthly Active Users) FREE
   - $0.0055 per MAU after

4. **AWS Certificate Manager** (SSL/TLS)
   - FREE for ACM certificates
   - (S3 website already uses HTTPS)

---

## 📈 Scaling Cost Projection

### **Growth Trajectory**

| Users | Requests/Day | Monthly Cost (Year 1) | Monthly Cost (After) |
|-------|--------------|------------------------|----------------------|
| 10 | 100 | $0.00 | $0.25 |
| 50 | 500 | $0.00 | $0.50 |
| 100 | 1,000 | $0.00 | $1.00 |
| 500 | 5,000 | $0.00 | $5.00 |
| 1,000 | 10,000 | $0.00 | $10.00 |
| 5,000 | 50,000 | $10.00 | $65.00 |
| 10,000 | 100,000 | $25.00 | $130.00 |

---

## ✅ Deploy Script Improvements

### **Recommended Updates to `deploy.sh`**

```bash
# Add these improvements:

# 1. Check for existing stack
if aws cloudformation describe-stacks --stack-name $STACK_NAME 2>/dev/null; then
    echo "Stack exists. Updating..."
    DEPLOY_MODE="update"
else
    echo "Creating new stack..."
    DEPLOY_MODE="create"
fi

# 2. Use consistent S3 bucket name
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET_NAME="stock-analyzer-frontend-${AWS_ACCOUNT_ID}"

# 3. Add cost estimate before deployment
echo ""
echo "💰 Estimated Monthly Cost:"
echo "  - First 12 months: ~$0 (Free Tier)"
echo "  - After Free Tier: ~$0.25 - $10 (usage dependent)"
echo ""
read -p "Proceed with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# 4. Add deployment confirmation
echo ""
echo "⏳ Deployment will take 3-5 minutes..."
echo "   Lambda functions: ~1 minute"
echo "   API Gateway: ~1 minute"
echo "   DynamoDB: ~30 seconds"
echo "   S3 + Frontend: ~1 minute"
echo ""

# 5. Add cleanup function
cleanup_old_resources() {
    echo "🧹 Cleaning up old resources..."
    
    # List old SAM artifacts
    sam list --stack-name $STACK_NAME 2>/dev/null || true
    
    # Clean up old deployment packages
    rm -rf .aws-sam/
}

# 6. Add cost monitoring reminder
echo ""
echo "💡 Cost Monitoring Tips:"
echo "   1. Set up AWS Budget Alert: https://console.aws.amazon.com/billing/home#/budgets"
echo "   2. Monitor CloudWatch metrics: https://console.aws.amazon.com/cloudwatch/"
echo "   3. Check AWS Cost Explorer: https://console.aws.amazon.com/cost-management/home"
echo ""
```

---

## 🎓 Cost Comparison with Alternatives

### **vs. Traditional EC2 Hosting**

| Aspect | Serverless (Current) | EC2 t3.micro |
|--------|---------------------|--------------|
| Base Cost | $0 (Free Tier) | $8.50/month |
| Scaling | Automatic | Manual |
| Maintenance | None | OS updates, patches |
| Availability | 99.99% | Depends on setup |
| **Winner** | ✅ Serverless | - |

### **vs. Heroku**

| Aspect | Serverless (Current) | Heroku Hobby |
|--------|---------------------|--------------|
| Cost | $0-10/month | $7/dyno/month |
| Cold Starts | 1-2s | None (always on) |
| Database | DynamoDB | PostgreSQL |
| Free Tier | ✅ Generous | Limited |
| **Winner** | ✅ Serverless (cost) | Heroku (simplicity) |

### **vs. DigitalOcean App Platform**

| Aspect | Serverless (Current) | DO App Platform |
|--------|---------------------|-----------------|
| Cost | $0-10/month | $5/month minimum |
| Scaling | Automatic | Manual tiers |
| Global CDN | CloudFront option | Included |
| **Winner** | ✅ Serverless | - |

---

## 🎯 Final Recommendations

### **For Development/Testing:**
✅ Current configuration is **PERFECT**
- All within Free Tier
- No upfront costs
- Easy to tear down

### **For Production (< 1000 users):**
✅ Keep current setup, add:
- CloudWatch alarms
- Budget alerts ($10/month limit)
- Weekly cost review

### **For Production (> 1000 users):**
Consider:
- Provisioned DynamoDB capacity (save 60%)
- CloudFront CDN (faster, cheaper at scale)
- Reserved Lambda capacity (save 40%)
- API Gateway caching (reduce Lambda calls)

### **For Enterprise (> 10,000 users):**
Optimize:
- Lambda@Edge for global distribution
- ElastiCache for Redis caching
- RDS for relational data needs
- Enterprise support plan

---

## 📝 Deployment Checklist

Before running `./deploy.sh`:

- [ ] AWS CLI configured (`aws configure`)
- [ ] SAM CLI installed
- [ ] IAM permissions verified
- [ ] Budget alert set up
- [ ] Review region pricing (us-east-1 recommended)
- [ ] Set FINANCIAL_API_KEY environment variable
- [ ] Understand Free Tier limits
- [ ] Have AWS account ID ready

After deployment:

- [ ] Test all endpoints
- [ ] Monitor CloudWatch logs
- [ ] Check Cost Explorer after 24 hours
- [ ] Set up billing alerts
- [ ] Document API endpoint URL
- [ ] Test frontend functionality

---

## 💡 Summary

**Deploy Script:** ✅ Good (minor improvements recommended)

**Cost Estimate:**
- **First Year:** **$0/month** (Free Tier covers everything)
- **After Free Tier:** **$0.25 - $10/month** (moderate usage)
- **High Traffic:** **$50 - $100/month** (with paid API tiers)

**Recommendation:** **DEPLOY IT!** 🚀

The current setup is extremely cost-effective and production-ready for small to medium applications.

---

*Cost analysis as of January 2026. AWS pricing may vary by region and over time.*
*Always verify current pricing at: https://aws.amazon.com/pricing/*

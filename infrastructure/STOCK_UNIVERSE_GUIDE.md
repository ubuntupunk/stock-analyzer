# Stock Universe Seeding Guide

## Overview

The stock-analyzer application includes an automated S&P 500 stock universe population system that:
1. Fetches S&P 500 stocks from Wikipedia (with fallback list)
2. Enriches data with Alpha Vantage API
3. Stores in DynamoDB with proper indexing
4. Updates weekly via scheduled Lambda

## Current Implementation Status

✅ **Database Schema**: `stock-universe` table with GSI indexes for sector and market cap
✅ **Seeding Script**: `stock_universe_seed.py` with Wikipedia + Alpha Vantage integration  
✅ **Weekly Updates**: Lambda function scheduled every 7 days via EventBridge
✅ **API Endpoints**: Search, popular stocks, sectors, filtering available

## Database Schema

**Table**: `stock-universe`
- **Primary Key**: `symbol` (string)
- **Attributes**: name, sector, subSector, marketCap, exchange, currency, country
- **GSIs**: 
  - `sector-index` (sector → symbol)
  - `marketcap-index` (marketCapBucket → symbol)

**Market Cap Buckets**:
- `mega`: >$200B
- `large`: $10-200B  
- `mid`: $2-10B
- `small`: <$2B

## Manual Seeding Commands

### Initial Population (Fast - No API Enrichment)
```bash
# Deploy first
sam build && sam deploy

# Run initial seed (fast, uses Wikipedia data only)
aws lambda invoke \
  --function-name StockUniverseSeedFunction \
  --payload '{ "enrich": false }' \
  response.json
```

### Full Population with API Enrichment (Slow - Rate Limited)
```bash
# Seed with live market data (takes ~20 minutes due to API limits)
aws lambda invoke \
  --function-name StockUniverseSeedFunction \
  --payload '{ "enrich": true }' \
  response.json
```

### Check Seeding Status
```bash
# View DynamoDB items
aws dynamodb scan --table-name stock-universe --max-items 5

# Count total stocks
aws dynamodb describe-table --table-name stock-universe | grep "ItemCount"
```

## API Usage

### Search Stocks
```bash
curl "https://your-api.execute-api.region.amazonaws.com/prod/api/stocks/search?q=AAPL"
```

### Get Popular Stocks  
```bash
curl "https://your-api.execute-api.region.amazonaws.com/prod/api/stocks/popular?limit=20"
```

### Filter by Sector
```bash
curl "https://your-api.execute-api.region.amazonaws.com/prod/api/stocks/filter?sector=Technology"
```

## Configuration

### Environment Variables
- `STOCK_UNIVERSE_TABLE`: DynamoDB table name
- `FINANCIAL_API_KEY`: Alpha Vantage API key (stored in SSM)

### Alpha Vantage API Limits
- Free tier: 5 calls/minute, 500 calls/day
- Enrichment mode respects limits with 12-second delays
- For production, consider upgrading API tier

### Weekly Schedule
- **Trigger**: EventBridge Schedule (rate 7 days)
- **Timeout**: 15 minutes
- **Memory**: 1024MB
- **Enrichment**: Enabled for scheduled runs

## Monitoring & Troubleshooting

### CloudWatch Logs
```bash
aws logs tail /aws/lambda/StockUniverseSeedFunction --follow
```

### Common Issues

**Wikipedia Parse Failures**
- Script falls back to curated 100-stock list
- Check logs for pandas HTML parse errors

**API Rate Limits**  
- Free tier: 5 calls/minute
- Enrichment skips 4/5 stocks to stay within limits
- Consider Alpha Vantage Premium for full enrichment

**DynamoDB Throttling**
- Uses PAY_PER_REQUEST billing (no provisioning needed)
- Batch writes handle throttling automatically

### Monitoring Metrics
- Lambda success/failure rates
- DynamoDB consumed capacity
- API remaining quota
- Stock count in database

## Production Recommendations

1. **API Key**: Use Alpha Vantage Premium for full enrichment
2. **Error Handling**: Add dead-letter queue for failed enrichments  
3. **Data Validation**: Add checksum validation for Wikipedia data
4. **Backup**: Enable point-in-time recovery for DynamoDB
5. **Alerting**: CloudWatch alarms for seeding failures

## Frontend Integration

The frontend already uses these endpoints:
- `app.js:201-209`: `api.getPopularStocks()`
- `app.js:233-248`: `api.searchStocks()`
- `app.js:50-64`: Search autocomplete functionality

The weekly updates ensure the frontend always has fresh stock universe data for searching and filtering.
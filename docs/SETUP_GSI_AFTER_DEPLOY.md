# Quick Guide: Add Multi-Index GSIs via AWS CLI

## After SAM Deployment

Your SAM template is deployed with:
- ✅ Multi-index fetcher code in Lambda
- ✅ EventBridge schedules configured
- ✅ New API endpoints live
- ❌ StockUniverseTable removed from CloudFormation (managed via CLI)

---

## Step 1: Create the Table

The `stock-universe` table doesn't exist yet. Create it first:

```bash
./infrastructure/scripts/create-stock-universe-table.sh
```

This will create the table with:
- Primary key: `symbol`
- 2 existing GSIs: `sector-index`, `marketcap-index`
- PAY_PER_REQUEST billing mode

---

## Step 2: Add New GSIs

After the table is ACTIVE, add the 4 remaining GSIs:

```bash
# Make script executable
chmod +x infrastructure/scripts/add-multi-index-gsis.sh

# Run it (will take ~1-2 minutes total, ~15-30 seconds per GSI)
./infrastructure/scripts/add-multi-index-gsis.sh
```

Each GSI will be added sequentially with automatic waiting between steps.

---

## Step 2: Verify GSIs Created

```bash
# List all GSIs
aws dynamodb describe-table \
  --table-name stock-universe \
  --query 'Table.GlobalSecondaryIndexes[].IndexName' \
  --output text
```

Expected output:
```
sector-index
marketcap-index
region-index
index-id-index
currency-index
status-index
```

```bash
# Check all GSI statuses
aws dynamodb describe-table \
  --table-name stock-universe \
  --query 'Table.GlobalSecondaryIndexes[].{Name:IndexName,Status:IndexStatus}' \
  --output table
```

Expected output:
```
--------------------------------------------------------------
|             DescribeTable                |
+----------------+-----------------+--------+
|    IndexName   |   IndexStatus   | Key    |
+----------------+-----------------+--------+
|  sector-index  |      ACTIVE     | sector |
| marketcap-index|      ACTIVE     |  cap   |
|    region-index |      ACTIVE     | region |
|  index-id-index|      ACTIVE     | indexId|
|  currency-index|      ACTIVE     |currency|
| status-index   |      ACTIVE     | status |
+----------------+-----------------+--------+
```

---

## Step 3: Test New API Endpoints

```bash
# Get all indices
curl https://YOUR-API.execute-api.REGION.amazonaws.com/prod/api/stocks/indices

# Get index details (SP500)
curl https://YOUR-API.execute-api.REGION.amazonaws.com/prod/api/stocks/indices/SP500

# Filter by region
curl "https://YOUR-API.execute-api.REGION.amazonaws.com/prod/api/stocks/filter?region=ZA"

# Filter by currency
curl "https://YOUR-API.execute-api.REGION.amazonaws.com/prod/api/stocks/filter?currency=ZAR"
```

---

## Manual GSI Addition (If Script Fails)

If you prefer to add each GSI manually:

### GSI #1: region-index
```bash
aws dynamodb update-table \
  --table-name stock-universe \
  --attribute-definitions AttributeName=region,AttributeType=S AttributeName=symbol,AttributeType=S \
  --global-secondary-indexes '[{"IndexName":"region-index","KeySchema":[{"AttributeName":"region","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]'
```

Wait ~30 seconds for ACTIVE status, then:

### GSI #2: index-id-index
```bash
aws dynamodb update-table \
  --table-name stock-universe \
  --attribute-definitions AttributeName=indexId,AttributeType=S AttributeName=symbol,AttributeType=S \
  --global-secondary-indexes '[{"IndexName":"index-id-index","KeySchema":[{"AttributeName":"indexId","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]'
```

### GSI #3: currency-index
```bash
aws dynamodb update-table \
  --table-name stock-universe \
  --attribute-definitions AttributeName=currency,AttributeType=S AttributeName=symbol,AttributeType=S \
  --global-secondary-indexes '[{"IndexName":"currency-index","KeySchema":[{"AttributeName":"currency","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]'
```

### GSI #4: status-index
```bash
aws dynamodb update-table \
  --table-name stock-universe \
  --attribute-definitions AttributeName=isActive,AttributeType=B AttributeName=symbol,AttributeType=S \
  --global-secondary-indexes '[{"IndexName":"status-index","KeySchema":[{"AttributeName":"isActive","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]'
```

---

## Troubleshooting

### Error: "Cannot perform more than one GSI creation..."
Wait for the current GSI to become ACTIVE before adding the next one. The script handles this automatically.

### Check GSI Status
```bash
aws dynamodb describe-table \
  --table-name stock-universe \
  --query 'Table.GlobalSecondaryIndexes[?IndexName==`region-index`].{Name:IndexName,Status:IndexStatus,CreationDate:CreationDate}' \
  --output table
```

### Delete GSI (if needed to retry)
```bash
aws dynamodb update-table \
  --table-name stock-universe \
  --global-secondary-index-updates '[
    {
      "Delete": {"IndexName": "region-index"}
    }
  ]'
```

---

## Next Steps After GSIs Are Active

1. **Test EventBridge schedules:**
   - SP500Weekly, RussellWeekly, JSEWeekly will auto-trigger in 7 days
   - DailyValidation will run daily

2. **Seed initial data:**
   ```bash
   # Seed SP500
   aws lambda invoke \
     --function-name StockUniverseSeedFunction \
     --payload '{"indexId":"SP500","operation":"seed","enrich":true}' \
     response.json

   # Seed JSE
   aws lambda invoke \
     --function-name StockUniverseSeedFunction \
     --payload '{"indexId":"JSE_ALSI","operation":"seed","enrich":true}' \
     response.json
   ```

3. **Monitor CloudWatch metrics:**
   - Navigate to CloudWatch console
   - Namespace: `StockAnalyzer/StockUniverse`
   - Metrics: `StocksSeeded`, `FreshnessScore`, `DataQualityScore`

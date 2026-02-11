# GSI Staged Deployment Guide

## Issue
DynamoDB CloudFormation does not allow creating more than one Global Secondary Index (GSI) in a single update attempt.

## Current Status
- The rollback was successful
- The new GSIs have been commented out in `template.yaml`
- Deployment can proceed now

## Staged Deployment Process

### Step 1: Deploy without new GSIs (IMMEDIATE)
```bash
cd infrastructure
sam build
sam deploy
```
This will deploy the updated Lambda functions and EventBridge schedules without the new GSIs.

---

### Step 2: Add GSIs one at a time (4 deployments)

After Step 1 completes, add each GSI separately:

#### GSI #1: region-index
1. Edit `template.yaml`
2. Uncomment the `region-index` GSI block
3. Run:
   ```bash
   sam build
   sam deploy
   ```

#### GSI #2: index-id-index
1. Edit `template.yaml`
2. Uncomment the `index-id-index` GSI block
3. Run:
   ```bash
   sam build
   sam deploy
   ```

#### GSI #3: currency-index
1. Edit `template.yaml`
2. Uncomment the `currency-index` GSI block
3. Run:
   ```bash
   sam build
   sam deploy
   ```

#### GSI #4: status-index
1. Edit `template.yaml`
2. Uncomment the `status-index` GSI block
3. Run:
   ```bash
   sam build
   sam deploy
   ```

---

## Alternative: CLI Command for GSI Creation

Alternatively, create GSIs directly via AWS CLI after the initial deployment:

```bash
# Set table name (update with your actual table name)
TABLE_NAME="stock-universe"

# Create region-index
aws dynamodb update-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=region,AttributeType=S AttributeName=symbol,AttributeType=S \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "region-index",
        "KeySchema": [{"AttributeName":"region","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],
        "Projection": {"ProjectionType":"ALL"}
      }
    ]'

# Wait for region-index to become ACTIVE (check with: aws dynamodb describe-table --table-name $TABLE_NAME)

# Create index-id-index
aws dynamodb update-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=indexId,AttributeType=S AttributeName=symbol,AttributeType=S \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "index-id-index",
        "KeySchema": [{"AttributeName":"indexId","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],
        "Projection": {"ProjectionType":"ALL"}
      }
    ]'

# Wait for ACTIVE...

# Create currency-index
aws dynamodb update-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=currency,AttributeType=S AttributeName=symbol,AttributeType=S \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "currency-index",
        "KeySchema": [{"AttributeName":"currency","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],
        "Projection": {"ProjectionType":"ALL"}
      }
    ]'

# Wait for ACTIVE...

# Create status-index
aws dynamodb update-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=isActive,AttributeType=B AttributeName=symbol,AttributeType=S \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "status-index",
        "KeySchema": [{"AttributeName":"isActive","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],
        "Projection": {"ProjectionType":"ALL"}
      }
    ]'
```

---

## Verification

After all GSIs are created, verify:

```bash
aws dynamodb describe-table --table-name stock-universe --query 'Table.GlobalSecondaryIndexes[].IndexName'
```

Expected output:
```
[
  "sector-index",
  "marketcap-index",
  "region-index",
  "index-id-index",
  "currency-index",
  "status-index"
]
```

---

## API Behavior During Migration

The API (`stock_universe_api.py`) already includes fallback logic to use `scan()` when a GSI doesn't exist. This means:

- **Before GSIs are created:** API will use scans (slower but works)
- **After each GSI is created:** API will automatically use the new GSI for queries that support it

No code changes needed during this migration.

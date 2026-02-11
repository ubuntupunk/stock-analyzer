# DynamoDB Schema Update for Multi-Index Support

## Overview

Update the `stock-universe` DynamoDB table to support multiple stock indices, regions, and currencies.

## Schema Changes

### Current Schema
```python
{
    'symbol': 'AAPL',                    # PK
    'name': 'Apple Inc.',
    'sector': 'Technology',
    'subSector': '',
    'marketCap': 3000000000000,
    'marketCapBucket': 'mega',
    'exchange': 'NASDAQ',
    'currency': 'USD',
    'country': 'USA',
    'headquarters': 'Cupertino, CA',
    'lastUpdated': '2026-02-11T...'
}
```

### New Schema (Backward Compatible)
```python
{
    # Existing Fields
    'symbol': 'AAPL',                    # PK (unchanged)
    'name': 'Apple Inc.',
    'sector': 'Technology',
    'subSector': '',
    'industry': 'Technology - Hardware', # NEW: More granular industry
    'marketCap': 3000000000000,          # Local currency
    'marketCapBucket': 'mega',
    'exchange': 'NASDAQ',
    'currency': 'USD',                   # Existing, now explicitly used
    'country': 'USA',
    'headquarters': 'Cupertino, CA',
    'lastUpdated': '2026-02-11T...',

    # NEW Fields
    'region': 'US',                      # NEW: Region code (US, ZA, etc.)
    'exchangeSuffix': '',                # NEW: Empty for US, '.JO' for JSE
    'indexId': 'SP500',                  # NEW: Primary index membership
    'indexIds': ['SP500', 'RUSSELL3000'], # NEW: All index memberships
    'marketCapUSD': 3000000000000,       # NEW: Normalized USD value
    'lastValidated': '2026-02-11T...',   # NEW: Last validation timestamp
    'isActive': True,                    # NEW: Stock still trading?
    'dataSource': 'yfinance',            # NEW: System that provided data
}
```

## Global Secondary Indexes (GSIs)

### 1. region-index
```
Partition Key: region (String)
Sort Key: symbol (String)
```
Purpose: Filter stocks by region (US, ZA, etc.)
```bash
# Query: Get all US stocks
AWS DynamoDB > Query > region-index
  Partition Key: "US"
```

### 2. index-id-index
```
Partition Key: indexId (String)
Sort Key: symbol (String)
```
Purpose: Get all stocks in a specific index
```bash
# Query: Get all S&P 500 stocks
AWS DynamoDB > Query > index-id-index
  Partition Key: "SP500"
```

### 3. currency-index
```
Partition Key: currency (String)
Sort Key: symbol (String)
```
Purpose: Filter stocks by currency (USD, ZAR, etc.)
```bash
# Query: Get all ZAR stocks
AWS DynamoDB > Query > currency-index
  Partition Key: "ZAR"
```

### 4. status-index
```
Partition Key: isActive (Boolean)
Sort Key: symbol (String)
```
Purpose: Query active/delisted stocks
```bash
# Query: Get all delisted stocks
AWS DynamoDB > Query > status-index
  Partition Key: false
```

## Migration Strategy

### Option 1: CloudFormation Update (Recommended)
Edit `infrastructure/template.yaml` and add the new GSI definitions, then redeploy.

### Option 2: Manual DynamoDB Update
Use AWS CLI to add GSIs to the existing table.

### Option 3: Table Recreate
Export existing data, create new table with schema, re-import.

### Recommended: Option 1 (CloudFormation Update)

```yaml
# infrastructure/template.yaml
StockUniverseTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: stock-universe
    AttributeDefinitions:
      - AttributeName: symbol
        AttributeType: S
      # NEW FOR GSIs
      - AttributeName: region
        AttributeType: S
      - AttributeName: indexId
        AttributeType: S
      - AttributeName: currency
        AttributeType: S
      - AttributeName: isActive
        AttributeType: S
    KeySchema:
      - AttributeName: symbol
        KeyType: HASH
    # NEW GSIs
    GlobalSecondaryIndexes:
      - IndexName: region-index
        KeySchema:
          - AttributeName: region
            KeyType: HASH
          - AttributeName: symbol
            KeyType: RANGE
        Projection:
          ProjectionType: ALL
        BillingMode: PAY_PER_REQUEST
      - IndexName: index-id-index
        KeySchema:
          - AttributeName: indexId
            KeyType: HASH
          - AttributeName: symbol
            KeyType: RANGE
        Projection:
          ProjectionType: ALL
        BillingMode: PAY_PER_REQUEST
      - IndexName: currency-index
        KeySchema:
          - AttributeName: currency
            KeyType: HASH
          - AttributeName: symbol
            KeyType: RANGE
        Projection:
          ProjectionType: ALL
        BillingMode: PAY_PER_REQUEST
      - IndexName: status-index
        KeySchema:
          - AttributeName: isActive
            KeyType: HASH
          - AttributeName: symbol
            KeyType: RANGE
        Projection:
          ProjectionType: ALL
        BillingMode: PAY_PER_REQUEST
    BillingMode: PAY_PER_REQUEST
```

## Data Backfill Script

After updating the schema, run a script to backfill existing records with default values for new fields.

```python
import boto3
from datetime import datetime

def backfill_old_records():
    """
    Add new fields to existing records with default values
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('stock-universe')

    # Scan all existing items
    print("Scanning existing records...")
    response = table.scan()
    items = response.get('Items', [])

    print(f"Found {len(items)} records to backfill")

    updated = 0
    with table.batch_writer() as batch:
        for item in items:
            try:
                # Add default values for new fields if not present
                if 'region' not in item:
                    # Guess region from country
                    country = item.get('country', 'USA')
                    if country == 'USA':
                        item['region'] = 'US'
                    elif country in ['South Africa', 'SouthAfrica']:
                        item['region'] = 'ZA'
                    else:
                        item['region'] = 'US'  # Default

                if 'exchangeSuffix' not in item:
                    item['exchangeSuffix'] = ''

                if 'indexId' not in item:
                    item['indexId'] = 'SP500'  # Assume S&P 500

                if 'indexIds' not in item:
                    item['indexIds'] = ['SP500']

                if 'marketCapUSD' not in item:
                    # Use existing marketCap if currency is USD
                    if item.get('currency') == 'USD':
                        item['marketCapUSD'] = item.get('marketCap', 0)
                    else:
                        item['marketCapUSD'] = 0

                if 'lastValidated' not in item:
                    item['lastValidated'] = datetime.utcnow().isoformat()

                if 'isActive' not in item:
                    item['isActive'] = True

                if 'dataSource' not in item:
                    item['dataSource'] = 'legacy'

                batch.put_item(Item=item)
                updated += 1

                if updated % 100 == 0:
                    print(f"  {updated} records updated...")

            except Exception as e:
                print(f"  Error updating {item.get('symbol')}: {e}")

    print(f"✅ Backfill complete: {updated} records updated")


if __name__ == '__main__':
    backfill_old_records()
```

## Validation

After schema update and backfill, validate with queries:

```bash
# Test region-index
aws dynamodb query \
  --table-name stock-universe \
  --index-name region-index \
  --key-condition-expression "region = :region" \
  --expression-attribute-values '{":region":{"S":"US"}}'

# Test index-id-index
aws dynamodb query \
  --table-name stock-universe \
  --index-name index-id-index \
  --key-condition-expression "indexId = :indexId" \
  --expression-attribute-values '{":indexId":{"S":"SP500"}}'

# Test currency-index
aws dynamodb query \
  --table-name stock-universe \
  --index-name currency-index \
  --key-condition-expression "currency = :currency" \
  --expression-attribute-values '{":currency":{"S":"ZAR"}}'
```

## Rolling Back

If issues occur, roll back by:
1. Disabling the new GSIs in CloudFormation
2. Removing the GSI definitions
3. Redeploying

## Cost Impact

- Additional GSIs use `PAY_PER_REQUEST` billing
- Storage increased slightly (~20 bytes per item)
- Read/write capacity: Minimal impact (GSIs share RCUs/WCUs with table)

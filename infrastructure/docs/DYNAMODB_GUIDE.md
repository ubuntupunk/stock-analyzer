# DynamoDB Table Design for Stock Analyzer

## Single Table Design Pattern

This project uses DynamoDB's **Single Table Design** pattern where multiple entity types share the same table using a composite key structure.

## Table Schema

### Primary Key
```
PK (Partition Key) | SK (Sort Key)
-------------------|-------------
USER#userId        | METADATA#profile
USER#userId        | WATCHLIST#AAPL
STOCK#symbol       | METADATA#info
```

### Entity Types

#### User Entity
```json
{
  "PK": "USER#user123",
  "SK": "METADATA#profile",
  "entityType": "USER",
  "userId": "user123",
  "email": "user@example.com",
  "name": "John Doe",
  "preferences": {
    "theme": "dark",
    "notifications": true
  },
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T10:30:00Z"
}
```

#### Watchlist Item Entity
```json
{
  "PK": "USER#user123",
  "SK": "WATCHLIST#AAPL",
  "entityType": "WATCHLIST_ITEM",
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "notes": "Strong tech stock",
  "alertPrice": 180.00,
  "tags": ["tech", "dividend"],
  "addedAt": "2024-01-15T10:30:00Z",
  "userId": "user123"
}
```

#### Stock Metadata Entity
```json
{
  "PK": "STOCK#AAPL",
  "SK": "METADATA#info",
  "entityType": "STOCK_METADATA",
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "cachedAt": "2024-01-15T10:30:00Z"
}
```

## Global Secondary Indexes (GSIs)

### email-index
For looking up users by email address:
```
email (Partition Key)
```

### GSI1
For querying related data across entity types:
```
GSI1PK (Partition Key) | GSI1SK (Sort Key)
```

## Access Patterns

| Operation | Key Expression | Use Case |
|-----------|----------------|----------|
| Get User | PK = USER#id, SK = METADATA#profile | User profile |
| Get Watchlist | PK = USER#id, SK begins_with(WATCHLIST#) | All watchlist items |
| Get Watchlist Item | PK = USER#id, SK = WATCHLIST#SYMBOL | Single item |
| Get Stock Metadata | PK = STOCK#symbol, SK = METADATA#info | Stock info |
| Find User by Email | email-index | Login |

## Deployment

### CloudFormation
```bash
aws cloudformation deploy \
  --template-file dynamodb-template.yaml \
  --stack-name stock-analyzer-dynamodb \
  --parameter-overrides Environment=dev
```

### Terraform
```hcl
resource "aws_dynamodb_table" "stock_analyzer" {
  name         = "StockAnalyzer"
  billing_mode = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  
  hash_key  = "PK"
  range_key = "SK"
  
  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }
  attribute {
    name = "email"
    type = "S"
  }
}
```

## Sample Data

Run the seed script to populate sample data:
```bash
node scripts/seed-dynamodb.js
```

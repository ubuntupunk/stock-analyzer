# Custom Factors - DynamoDB Table Setup

## Overview

The custom factors feature uses DynamoDB to store user-defined screening factors. This allows users to save their custom factor criteria and access them across devices and sessions.

---

## Table Structure Options

You have **two options** for storing custom factors:

### Option 1: Separate Table (Simple - Recommended for Development)

Create a dedicated `stock-factors` table:

```json
{
  "TableName": "stock-factors",
  "KeySchema": [
    {
      "AttributeName": "userId",
      "KeyType": "HASH"
    },
    {
      "AttributeName": "factorId",
      "KeyType": "RANGE"
    }
  ],
  "AttributeDefinitions": [
    {
      "AttributeName": "userId",
      "AttributeType": "S"
    },
    {
      "AttributeName": "factorId",
      "AttributeType": "S"
    }
  ],
  "BillingMode": "PAY_PER_REQUEST",
  "Tags": [
    {
      "Key": "Application",
      "Value": "StockAnalyzer"
    },
    {
      "Key": "Purpose",
      "Value": "CustomFactors"
    }
  ]
}
```

### Option 2: Single Table Design (Recommended for Production)

Use your existing `StockAnalyzer` table with composite keys:

**Key Structure:**
- `PK`: `USER#{userId}`
- `SK`: `FACTOR#{factorId}`

**Example Item:**
```json
{
  "PK": "USER#12345",
  "SK": "FACTOR#custom_1707123456789",
  "userId": "12345",
  "factorId": "custom_1707123456789",
  "name": "High Growth Low Debt",
  "description": "Companies with high revenue growth and low debt",
  "criteria": "Revenue Growth > 20% AND Debt/Equity < 0.5",
  "createdAt": "2024-02-05T10:30:45.123Z",
  "entityType": "CUSTOM_FACTOR"
}
```

---

## AWS Setup Requirements

### Do You Need to Create Tables on AWS?

**For Local Testing: NO! ✅**
- The app uses localStorage fallback automatically
- No AWS setup needed
- No DynamoDB tables required
- Custom factors saved in browser only

**For Production Deployment: YES ⚠️**
- Need to create DynamoDB tables in AWS
- Two tables required (current implementation):
  1. `stock-factors` - Stores custom factors
  2. `stock-universe` - Stores stock metrics for screening

### What About the StockAnalyzer Table?

You mentioned seeing `TABLE_NAME=StockAnalyzer` - that's confusing! Let me clarify:

- **`StockAnalyzer` table** = Used for user profiles, watchlists (already exists in your setup)
- **`stock-factors` table** = NEW table needed for custom factors (separate table)
- **`stock-universe` table** = NEW table needed for stock screening data

**Current code expects 2 NEW tables for the factors feature.**

If you want to use the existing `StockAnalyzer` table for custom factors (single-table design), you need to modify the code (instructions provided in the doc).

---

## Setup Instructions

### For Local Development (Using Separate Table)

1. **Create the table locally using AWS CLI:**

```bash
aws dynamodb create-table \
  --table-name stock-factors \
  --attribute-definitions \
    AttributeName=userId,AttributeType=S \
    AttributeName=factorId,AttributeType=S \
  --key-schema \
    AttributeName=userId,KeyType=HASH \
    AttributeName=factorId,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1 \
  --endpoint-url http://localhost:8000  # If using DynamoDB Local
```

2. **Or skip DynamoDB for local dev:**
   - The frontend already has localStorage fallback
   - Custom factors will be saved locally in the browser
   - No backend setup needed!

### For Production (Using Single Table)

The existing `StockAnalyzer` table already supports this! No changes needed.

Just update your `screener_api.py` to use the single-table pattern:

```python
class StockScreener:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        # Use the main table instead of a separate factors table
        self.table = self.dynamodb.Table(os.environ.get('TABLE_NAME', 'StockAnalyzer'))
        self.stock_universe_table = self.dynamodb.Table(os.environ.get('STOCK_UNIVERSE_TABLE', 'stock-universe'))
    
    def save_factor(self, user_id: str, factor_data: Dict) -> Dict:
        """Save a custom factor using single-table design"""
        try:
            item = {
                'PK': f'USER#{user_id}',
                'SK': f'FACTOR#{factor_data.get("factorId")}',
                'userId': user_id,
                'factorId': factor_data.get('factorId'),
                'name': factor_data.get('name'),
                'description': factor_data.get('description'),
                'criteria': factor_data.get('criteria'),
                'createdAt': factor_data.get('createdAt'),
                'entityType': 'CUSTOM_FACTOR'
            }
            
            self.table.put_item(Item=item)
            return {'success': True, 'factor': item}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_user_factors(self, user_id: str) -> List[Dict]:
        """Get all factors for a user using single-table design"""
        try:
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'USER#{user_id}',
                    ':sk': 'FACTOR#'
                }
            )
            return response.get('Items', [])
        except Exception as e:
            return {'error': str(e)}
    
    def delete_factor(self, user_id: str, factor_id: str) -> Dict:
        """Delete a factor using single-table design"""
        try:
            self.table.delete_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'FACTOR#{factor_id}'
                }
            )
            return {'success': True, 'message': 'Factor deleted successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
```

---

## Environment Variables

### ⚠️ IMPORTANT: Current Implementation Uses Separate Tables

**The current `screener_api.py` code expects TWO separate tables:**

```python
# In screener_api.py __init__:
self.factors_table = self.dynamodb.Table(os.environ.get('FACTORS_TABLE', 'stock-factors'))
self.stock_universe_table = self.dynamodb.Table(os.environ.get('STOCK_UNIVERSE_TABLE', 'stock-universe'))
```

**So you need to set:**
```bash
export FACTORS_TABLE=stock-factors
export STOCK_UNIVERSE_TABLE=stock-universe
```

### To Use Single-Table Design Instead

If you want to use the single `StockAnalyzer` table (recommended for production), you need to:

1. **Modify `screener_api.py` to use single-table pattern** (see code in doc above)
2. **Then set:**
   ```bash
   export TABLE_NAME=StockAnalyzer
   export STOCK_UNIVERSE_TABLE=stock-universe
   ```

**Current Status:** Code uses separate tables by default. Single-table is an optimization you can implement later.

---

## Data Access Patterns

### 1. Save Custom Factor
- **Operation:** `PUT`
- **Endpoint:** `POST /api/factors`
- **Requires:** Authentication
- **Body:**
```json
{
  "factorId": "custom_1707123456789",
  "name": "High Growth Low Debt",
  "description": "Companies with high revenue growth and low debt",
  "criteria": "Revenue Growth > 20% AND Debt/Equity < 0.5",
  "createdAt": "2024-02-05T10:30:45.123Z"
}
```

### 2. Get User's Custom Factors
- **Operation:** `QUERY`
- **Endpoint:** `GET /api/factors`
- **Requires:** Authentication
- **Returns:** Array of custom factors

### 3. Delete Custom Factor
- **Operation:** `DELETE`
- **Endpoint:** `DELETE /api/factors/{factorId}`
- **Requires:** Authentication

### 4. Screen Stocks
- **Operation:** `SCAN` (on stock-universe table)
- **Endpoint:** `POST /api/screener/screen`
- **Body:**
```json
{
  "criteria": {
    "pe_ratio": { "max": 22.5 },
    "roic": { "min": 0.09 },
    "revenue_growth": { "min": 0.05 }
  }
}
```

---

## Stock Universe Table

You also need a `stock-universe` table with stock metrics:

```json
{
  "TableName": "stock-universe",
  "KeySchema": [
    {
      "AttributeName": "symbol",
      "KeyType": "HASH"
    }
  ],
  "AttributeDefinitions": [
    {
      "AttributeName": "symbol",
      "AttributeType": "S"
    }
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

**Example Item:**
```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "sector": "Technology",
  "pe_ratio": 28.5,
  "roic": 0.42,
  "revenue_growth": 0.15,
  "debt_to_equity": 1.8,
  "current_ratio": 1.1,
  "price_to_fcf": 25.3,
  "market_cap": 2890000000000,
  "lastUpdated": "2024-02-05T10:00:00Z"
}
```

---

## Quick Start Guide

### For Local Testing (No DynamoDB Required)

1. **Just run the local server:**
   ```bash
   cd infrastructure/backend
   python3 local_server.py
   ```

2. **Custom factors will automatically use localStorage fallback**
   - Works without any DynamoDB setup
   - Factors saved in browser localStorage
   - Perfect for testing and development

### For Production Deployment

1. **Option A: Use existing StockAnalyzer table**
   - Update `screener_api.py` to use single-table pattern (code above)
   - Set `TABLE_NAME` environment variable
   - Deploy to Lambda

2. **Option B: Create separate tables**
   - Create `stock-factors` table using AWS Console or CLI
   - Create `stock-universe` table
   - Seed `stock-universe` with stock data
   - Set environment variables
   - Deploy to Lambda

---

## Cost Considerations

**Separate Tables (Option 1):**
- Simple to understand and manage
- Slightly higher cost (2 tables = 2x free tier)
- Easier to backup/restore factors separately

**Single Table (Option 2):**
- More cost-effective (1 table = 1x free tier)
- Better scalability
- Industry best practice
- Requires composite key pattern

**Recommendation:** Use Option 1 (separate table) for development, migrate to Option 2 (single table) for production.

---

## Testing the Implementation

### 1. Test Custom Factor Creation

```bash
# With authentication (production)
curl -X POST http://localhost:8000/api/factors \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "factorId": "custom_123",
    "name": "Test Factor",
    "description": "Test description",
    "criteria": "P/E < 20",
    "createdAt": "2024-02-05T10:00:00Z"
  }'

# Without authentication (local dev)
curl -X POST http://localhost:8000/api/factors \
  -H "Content-Type: application/json" \
  -d '{
    "factorId": "custom_123",
    "name": "Test Factor",
    "description": "Test description",
    "criteria": "P/E < 20",
    "createdAt": "2024-02-05T10:00:00Z"
  }'
```

### 2. Test Get Factors

```bash
curl http://localhost:8000/api/factors
```

### 3. Test Delete Factor

```bash
curl -X DELETE http://localhost:8000/api/factors/custom_123
```

### 4. Test Stock Screening

```bash
curl -X POST http://localhost:8000/api/screener/screen \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": {
      "pe_ratio": {"max": 25},
      "roic": {"min": 0.10}
    }
  }'
```

---

## Current Status

✅ **Frontend:** Fully implemented with localStorage fallback  
✅ **Backend API:** Endpoints implemented in `screener_api.py` and `local_server.py`  
⚠️ **DynamoDB Tables:** Need to be created (or use localStorage fallback)  
⚠️ **Stock Universe Data:** Needs to be seeded with actual stock metrics  

---

## Next Steps

1. **For Local Testing:**
   - No action needed! Use localStorage fallback
   - Test the UI and custom factors feature
   - Export/import works without backend

2. **For Production:**
   - Decide: Separate tables or single-table design?
   - Create DynamoDB tables
   - Seed `stock-universe` with stock data
   - Deploy Lambda functions
   - Update environment variables
   - Test end-to-end with authentication

---

## Questions?

- **Q: Do I need DynamoDB for local development?**
  - A: No! The app falls back to localStorage automatically.

- **Q: Which table design should I use?**
  - A: Separate table for simplicity, single-table for production scale.

- **Q: How do I populate the stock-universe table?**
  - A: Use `stock_universe_seed.py` (see STOCK_UNIVERSE_GUIDE.md)

- **Q: Will my custom factors sync across devices?**
  - A: Yes, when using DynamoDB backend with authentication.
  - A: No, when using localStorage (browser-specific storage).

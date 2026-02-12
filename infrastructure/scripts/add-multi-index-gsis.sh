#!/bin/bash

# Add Multi-Index Global Secondary Indexes to stock-universe table
# Run this script after sam deploy completes successfully
# Each GSI must be added separately (DynamoDB limitation)

set -e

TABLE_NAME="stock-universe"

echo "=================================="
echo "Adding GSIs to $TABLE_NAME"
echo "=================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to wait for GSI to become ACTIVE
wait_for_gsi() {
    local index_name=$1
    echo -n "Waiting for $index_name to become ACTIVE..."
    while true; do
        status=$(aws dynamodb describe-table --table-name $TABLE_NAME --query "Table.GlobalSecondaryIndexes[?IndexName=='$index_name'].IndexStatus" --output text 2>/dev/null || echo "CREATING")
        if [ "$status" = "ACTIVE" ]; then
            echo -e " ${GREEN}✓ ACTIVE${NC}"
            break
        fi
        echo -n "."
        sleep 5
    done
}

# GSI #1: region-index
echo "Step 1/4: Adding region-index"
aws dynamodb update-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=region,AttributeType=S AttributeName=symbol,AttributeType=S \
  --global-secondary-index-updates '{"Create":{"IndexName":"region-index","KeySchema":[{"AttributeName":"region","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}}'

wait_for_gsi "region-index"
echo ""

# GSI #2: index-id-index
echo "Step 2/4: Adding index-id-index"
aws dynamodb update-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=indexId,AttributeType=S AttributeName=symbol,AttributeType=S \
  --global-secondary-index-updates '{"Create":{"IndexName":"index-id-index","KeySchema":[{"AttributeName":"indexId","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}}'

wait_for_gsi "index-id-index"
echo ""

# GSI #3: currency-index
echo "Step 3/4: Adding currency-index"
aws dynamodb update-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=currency,AttributeType=S AttributeName=symbol,AttributeType=S \
  --global-secondary-index-updates '{"Create":{"IndexName":"currency-index","KeySchema":[{"AttributeName":"currency","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}}'

wait_for_gsi "currency-index"
echo ""

# GSI #4: status-index
echo "Step 4/4: Adding status-index"
aws dynamodb update-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=isActive,AttributeType=S AttributeName=symbol,AttributeType=S \
  --global-secondary-index-updates '{"Create":{"IndexName":"status-index","KeySchema":[{"AttributeName":"isActive","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}}'

wait_for_gsi "status-index"
echo ""

# Summary
echo "=================================="
echo "✓ All GSIs added successfully!"
echo "=================================="
echo ""
echo "Verifying GSIs..."
aws dynamodb describe-table --table-name $TABLE_NAME \
  --query 'Table.GlobalSecondaryIndexes[].{Name:IndexName,Status:IndexStatus}' \
  --output table

echo ""
echo "${GREEN}Done!${NC} The stock-universe table now has 6 GSIs ready for multi-index support."

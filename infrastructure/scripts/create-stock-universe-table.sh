#!/bin/bash

# Create stock-universe DynamoDB table with basic structure
# Run this BEFORE add-multi-index-gsis.sh

set -e

TABLE_NAME="stock-universe"

echo "=================================="
echo "Creating $TABLE_NAME table"
echo "=================================="
echo ""

# Check if table already exists
echo "Checking if table exists..."
if aws dynamodb describe-table --table-name $TABLE_NAME >/dev/null 2>&1; then
    echo "Table $TABLE_NAME already exists!"
    echo ""
    echo "Current GSIs:"
    aws dynamodb describe-table --table-name $TABLE_NAME \
      --query 'Table.GlobalSecondaryIndexes[].{Name:IndexName,Status:IndexStatus}' \
      --output table
    echo ""
    echo "If you need to recreate it, delete it first:"
    echo "  aws dynamodb delete-table --table-name $TABLE_NAME"
    echo ""
    read -p "Delete and recreate? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Deleting table..."
        aws dynamodb delete-table --table-name $TABLE_NAME
        echo "Waiting for table to be deleted..."
        while aws dynamodb describe-table --table-name $TABLE_NAME >/dev/null 2>&1; do
            echo -n "."
            sleep 5
        done
        echo ""
        echo "Table deleted. Proceeding with creation..."
    else
        echo "Aborting. Keep existing table and run: ./add-multi-index-gsis.sh"
        exit 0
    fi
else
    echo "Table does not exist. Creating..."
fi

# Create table with basic structure
echo ""
echo "Creating table with basic structure..."
aws dynamodb create-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=symbol,AttributeType=S AttributeName=sector,AttributeType=S AttributeName=marketCapBucket,AttributeType=S \
  --key-schema AttributeName=symbol,KeyType=HASH \
  --global-secondary-indexes '[
    {
      "IndexName": "sector-index",
      "KeySchema": [{"AttributeName":"sector","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],
      "Projection": {"ProjectionType": "ALL"}
    },
    {
      "IndexName": "marketcap-index",
      "KeySchema": [{"AttributeName":"marketCapBucket","KeyType":"HASH"},{"AttributeName":"symbol","KeyType":"RANGE"}],
      "Projection": {"ProjectionType": "ALL"}
    }
  ]' \
  --billing-mode PAY_PER_REQUEST \
  --tags Key=Application,Value=stock-analyzer

echo "Waiting for table to become ACTIVE..."
while true; do
    status=$(aws dynamodb describe-table --table-name $TABLE_NAME --query 'Table.TableStatus' --output text)
    if [ "$status" = "ACTIVE" ]; then
        break
    fi
    echo -n "."
    sleep 5
done

echo ""
echo "Waiting for GSIs to become ACTIVE..."
echo -n "sector-index..."
while true; do
    gsi_status=$(aws dynamodb describe-table --table-name $TABLE_NAME --query "Table.GlobalSecondaryIndexes[?IndexName=='sector-index'].IndexStatus" --output text)
    if [ "$gsi_status" = "ACTIVE" ]; then
        echo " ✓ ACTIVE"
        break
    fi
    sleep 5
done

echo -n "marketcap-index..."
while true; do
    gsi_status=$(aws dynamodb describe-table --table-name $TABLE_NAME --query "Table.GlobalSecondaryIndexes[?IndexName=='marketcap-index'].IndexStatus" --output text)
    if [ "$gsi_status" = "ACTIVE" ]; then
        echo " ✓ ACTIVE"
        break
    fi
    sleep 5
done

echo ""
echo "=================================="
echo "✓ Table created successfully!"
echo "=================================="
echo ""
echo "Table status:"
aws dynamodb describe-table --table-name $TABLE_NAME \
  --query 'Table.{Name:TableName,Status:TableStatus,GSICount:length(GlobalSecondaryIndexes)}' \
  --output table

echo ""
echo "Next step: Run ./add-multi-index-gsis.sh to add the 4 remaining GSIs"

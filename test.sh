#!/bin/bash

# Test Script for Stock Analyzer
# Tests all API endpoints after deployment

set -e

echo "======================================"
echo "Stock Analyzer - API Testing Script"
echo "======================================"

STACK_NAME="stock-analyzer-stack"
REGION="${AWS_REGION:-us-east-1}"

# Get API endpoint
echo ""
echo "Retrieving API endpoint..."
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
    --output text 2>/dev/null)

if [ -z "$API_ENDPOINT" ]; then
    echo "❌ Error: Could not retrieve API endpoint. Is the stack deployed?"
    exit 1
fi

echo "✓ API Endpoint: $API_ENDPOINT"

# Test function
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo ""
    echo "Testing: $description"
    echo "  Method: $method"
    echo "  Endpoint: $endpoint"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" -X GET "$API_ENDPOINT$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X POST \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_ENDPOINT$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        echo "  ✓ Status: $http_code"
        echo "  Response: ${body:0:100}..."
    else
        echo "  ❌ Status: $http_code"
        echo "  Error: $body"
        return 1
    fi
}

echo ""
echo "======================================"
echo "Running Tests..."
echo "======================================"

# Test 1: Stock Metrics
test_endpoint "GET" "/api/stock/metrics?symbol=AAPL" "" "Get Stock Metrics (AAPL)"

# Test 2: Stock Price
test_endpoint "GET" "/api/stock/price?symbol=MSFT" "" "Get Stock Price (MSFT)"

# Test 3: Analyst Estimates
test_endpoint "GET" "/api/stock/estimates?symbol=GOOGL" "" "Get Analyst Estimates (GOOGL)"

# Test 4: Financial Statements
test_endpoint "GET" "/api/stock/financials?symbol=TSLA" "" "Get Financial Statements (TSLA)"

# Test 5: Stock Screening
test_endpoint "POST" "/api/screen" \
    '{"criteria":{"pe_ratio":{"max":25},"roic":{"min":0.1}}}' \
    "Screen Stocks"

# Test 6: DCF Analysis
test_endpoint "POST" "/api/dcf" \
    '{"currentPrice":150,"assumptions":{"revenueGrowth":{"low":0.05,"mid":0.07,"high":0.10},"profitMargin":{"low":0.08,"mid":0.10,"high":0.12},"fcfMargin":{"low":0.08,"mid":0.10,"high":0.12},"discountRate":0.10,"terminalGrowthRate":0.03},"yearsToProject":10}' \
    "DCF Analysis"

# Test 7: Get Watchlist
test_endpoint "GET" "/api/watchlist" "" "Get Watchlist"

# Test 8: Add to Watchlist
test_endpoint "POST" "/api/watchlist" \
    '{"symbol":"AAPL","notes":"Test stock","tags":["tech"]}' \
    "Add to Watchlist"

# Test 9: Get User Factors
test_endpoint "GET" "/api/factors" "" "Get User Factors"

echo ""
echo "======================================"
echo "Test Summary"
echo "======================================"
echo ""
echo "✓ All basic tests passed!"
echo ""
echo "Next Steps:"
echo "1. Open the frontend URL in your browser"
echo "2. Test the UI functionality"
echo "3. Try searching for different stocks"
echo "4. Create custom factors"
echo "5. Add stocks to your watchlist"
echo ""

# Get frontend URL
FRONTEND_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' \
    --output text 2>/dev/null)

if [ ! -z "$FRONTEND_URL" ]; then
    echo "Frontend URL: $FRONTEND_URL"
    echo ""
fi

echo "To view logs:"
echo "  sam logs -n StockAPIFunction --stack-name $STACK_NAME --tail"
echo ""
echo "To delete the stack:"
echo "  aws cloudformation delete-stack --stack-name $STACK_NAME"
echo ""

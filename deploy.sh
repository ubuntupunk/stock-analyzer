#!/bin/bash

# Stock Analyzer Deployment Script
# This script deploys the application to AWS Lambda and S3

set -e

echo "======================================"
echo "Stock Analyzer Deployment Script"
echo "======================================"

# Check for required tools
command -v aws >/dev/null 2>&1 || { echo "AWS CLI is required but not installed. Aborting." >&2; exit 1; }
command -v sam >/dev/null 2>&1 || { echo "AWS SAM CLI is required but not installed. Aborting." >&2; exit 1; }

# Configuration
STACK_NAME="stock-analyzer-stack"
S3_BUCKET_NAME="stock-analyzer-frontend-$(date +%s)"
REGION="af-south-1"
FINANCIAL_API_KEY="${FINANCIAL_API_KEY:-demo}"

echo ""
echo "Configuration:"
echo "  Stack Name: $STACK_NAME"
echo "  S3 Bucket: $S3_BUCKET_NAME"
echo "  Region: $REGION"
echo ""

# Step 1: Build the SAM application
echo "[1/5] Building SAM application..."
cd infrastructure
sam build
echo "✓ Build complete"

# Step 2: Deploy the SAM application
echo ""
echo "[2/5] Deploying backend (Lambda + API Gateway + DynamoDB)..."
sam deploy \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_IAM \
    --region $REGION \
    --parameter-overrides \
        S3BucketName=$S3_BUCKET_NAME \
    --no-fail-on-empty-changeset

echo "✓ Backend deployed"

# Step 3: Get API Gateway endpoint
echo ""
echo "[3/5] Retrieving API Gateway endpoint..."
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
    --output text)

echo "✓ API Endpoint: $API_ENDPOINT"

# Step 4: Update frontend configuration
echo ""
echo "[4/5] Updating frontend configuration..."
cd ../frontend
cat > config.js << EOF
// Auto-generated configuration file
// Generated on: $(date)

const config = {
    apiEndpoint: '$API_ENDPOINT',
    
    features: {
        enableRealTimeData: true,
        enableWatchlist: true,
        enableDCF: true,
        enableScreener: true
    },
    
    charts: {
        defaultPeriod: '1Y',
        refreshInterval: 60000
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = config;
}
EOF
echo "✓ Configuration updated"

# Step 5: Deploy frontend to S3
echo ""
echo "[5/5] Deploying frontend to S3..."

# Sync files to S3
aws s3 sync . s3://$S3_BUCKET_NAME/ \
    --region $REGION \
    --exclude "*.md" \
    --exclude ".git/*" \
    --delete

echo "✓ Frontend deployed"

# Get website URL
WEBSITE_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' \
    --output text)

echo ""
echo "======================================"
echo "✓ Deployment Complete!"
echo "======================================"
echo ""
echo "Application URLs:"
echo "  Frontend: $WEBSITE_URL"
echo "  API: $API_ENDPOINT"
echo ""
echo "DynamoDB Tables:"
echo "  - stock-factors"
echo "  - stock-watchlist"
echo ""
echo "Next Steps:"
echo "1. Open the frontend URL in your browser"
echo "2. Configure your Financial API key in the Lambda environment variables if needed"
echo "3. Test the application functionality"
echo ""
echo "To update the application:"
echo "  - Backend: Run 'sam build && sam deploy' in the infrastructure directory"
echo "  - Frontend: Run 'aws s3 sync . s3://$S3_BUCKET_NAME/' in the frontend directory"
echo ""

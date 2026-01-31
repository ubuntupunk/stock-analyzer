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
STACK_NAME="stock-analyzer" # Corrected stack name
REGION="us-east-1"
FINANCIAL_API_KEY="${FINANCIAL_API_KEY:}"

echo ""
echo "Configuration:"
echo "  Stack Name: $STACK_NAME"
echo "  Region: $REGION"
echo ""

# Step 1: Build the SAM application
echo "[1/4] Building SAM application..." # Step count changed
cd infrastructure
sam build
echo "✓ Build complete"

# Step 2: Deploy the SAM application
echo ""
echo "[2/4] Deploying backend (Lambda + API Gateway + DynamoDB)..." # Step count changed
sam deploy \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_IAM \
    --region $REGION \
    --no-fail-on-empty-changeset # Removed parameter override for S3BucketName

echo "✓ Backend deployed"

# Step 3: Get API Gateway endpoint AND S3 Frontend Bucket Name
echo ""
echo "[3/4] Retrieving API Gateway endpoint and Frontend S3 Bucket Name..."
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
    --output text)

FRONTEND_BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
    --output text)

echo "✓ API Endpoint: $API_ENDPOINT"
echo "✓ Frontend S3 Bucket: $FRONTEND_BUCKET_NAME"

# Step 4: Update frontend configuration and Deploy to S3
echo ""
echo "[4/4] Updating frontend configuration and Deploying to S3..."
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

# Sync files to S3
aws s3 sync . s3://$FRONTEND_BUCKET_NAME/ \
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
echo "  - Frontend: Run 'aws s3 sync . s3://$FRONTEND_BUCKET_NAME/' in the frontend directory"
echo ""

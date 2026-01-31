// Configuration file for Stock Analyzer
// Update these values after CloudFormation deployment

const config = {
    // API Gateway endpoint - update after deployment
    apiEndpoint: 'https://j5lafw9554.execute-api.us-east-1.amazonaws.com/prod',
    
    // CloudFront URL for frontend (HTTPS)
    frontendUrl: 'https://d1gl9b1d3yuv4y.cloudfront.net',
    
    // Cognito configuration - update after deployment
    cognito: {
        region: 'us-east-1',
        userPoolId: 'us-east-1_pSr2hBy9j',
        userPoolClientId: 'g3h1dsvker3kp9gqansbcht77'
    }
};

// Make config available globally
if (typeof window !== 'undefined') {
    window.config = config;
}

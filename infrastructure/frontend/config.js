// Configuration file for Stock Analyzer
// Update these values after CloudFormation deployment

// Determine environment
const isLocal = window.location.hostname === 'localhost' || 
                window.location.hostname === '127.0.0.1' ||
                window.location.port === '5000' ||
                window.location.port === '8000';

const config = {
    // API Gateway endpoint - auto-selects based on environment
    apiEndpoint: isLocal 
        ? 'http://localhost:5000' 
        : 'https://j5lafw9554.execute-api.us-east-1.amazonaws.com/prod',
    
    // CloudFront URL for frontend (HTTPS) - auto-selects based on environment
    frontendUrl: isLocal
        ? 'http://localhost:5000'
        : 'https://d1gl9b1d3yuv4y.cloudfront.net',
    
    // Cognito configuration - update after deployment
    cognito: {
        region: 'us-east-1',
        userPoolId: 'us-east-1_pSr2hBy9j',
        userPoolClientId: 'g3h1dsvker3kp9gqansbcht77'
    },
    
    // Environment flag for debugging
    isDevelopment: isLocal,
    
    // Debug logging
    debug: isLocal
};

// Log config on initialization (only in development)
if (config.isDevelopment) {
    console.log('=== Config Initialized ===');
    console.log('Environment: Development (Local)');
    console.log('API Endpoint:', config.apiEndpoint);
    console.log('Frontend URL:', config.frontendUrl);
}

// Make config available globally
if (typeof window !== 'undefined') {
    window.config = config;
}

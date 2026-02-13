# Authentication Status - Stock Analyzer

## Current State

### Local Development (local_server.py)
**Status:** ✅ Mock Authentication Implemented

The local development server uses **mock authentication** for testing:

```python
# Mock credentials
Email: test@example.com
Password: password
```

**How it works:**
1. Frontend sends login request with email/password
2. Local server validates against hardcoded credentials
3. Returns a dummy JWT token
4. Token is stored in localStorage
5. Subsequent requests include token in Authorization header

**Mock Token:**
```
Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Auth Decorator:**
```python
@auth_required
def protected_route():
    user_id = g.user_id  # Set by before_request
```

### AWS Production
**Status:** ⚠️ NOT IMPLEMENTED

**What's Missing:**
1. ❌ AWS Cognito User Pool not configured
2. ❌ No Lambda Authorizer
3. ❌ No real JWT validation
4. ❌ No user registration flow
5. ❌ No password reset functionality

## Will Login Work on AWS?

**Short Answer:** ❌ NO - Authentication will NOT work on AWS without additional setup.

**Why:**
- Local server uses mock authentication with hardcoded credentials
- AWS Lambda functions don't have authentication middleware
- No Cognito integration exists
- Frontend expects JWT tokens that won't be validated on AWS

## What Needs to Be Done for AWS

### 1. Set Up AWS Cognito

```hcl
# infrastructure/terraform/cognito.tf
resource "aws_cognito_user_pool" "stock_analyzer" {
  name = "stock-analyzer-users"
  
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }
  
  auto_verified_attributes = ["email"]
  
  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = false
  }
}

resource "aws_cognito_user_pool_client" "stock_analyzer" {
  name         = "stock-analyzer-client"
  user_pool_id = aws_cognito_user_pool.stock_analyzer.id
  
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]
}
```

### 2. Create Lambda Authorizer

```python
# infrastructure/backend/authorizer.py
import json
import jwt
from jwt import PyJWKClient

def lambda_handler(event, context):
    """
    Lambda authorizer to validate Cognito JWT tokens
    """
    token = event['authorizationToken'].replace('Bearer ', '')
    
    try:
        # Get Cognito public keys
        region = os.environ['AWS_REGION']
        user_pool_id = os.environ['USER_POOL_ID']
        jwks_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
        
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Verify token
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=['RS256'],
            audience=os.environ['CLIENT_ID']
        )
        
        # Return policy allowing access
        return {
            'principalId': decoded['sub'],
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [{
                    'Action': 'execute-api:Invoke',
                    'Effect': 'Allow',
                    'Resource': event['methodArn']
                }]
            },
            'context': {
                'userId': decoded['sub'],
                'email': decoded['email']
            }
        }
    except Exception as e:
        print(f'Authorization failed: {e}')
        raise Exception('Unauthorized')
```

### 3. Update API Gateway

```hcl
# Add authorizer to API Gateway
resource "aws_api_gateway_authorizer" "cognito" {
  name          = "cognito-authorizer"
  rest_api_id   = aws_api_gateway_rest_api.stock_api.id
  type          = "COGNITO_USER_POOLS"
  provider_arns = [aws_cognito_user_pool.stock_analyzer.arn]
}

# Apply to protected routes
resource "aws_api_gateway_method" "watchlist_get" {
  # ...
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}
```

### 4. Update Frontend

```javascript
// Use AWS Amplify for Cognito integration
import { Auth } from 'aws-amplify';

// Configure Amplify
Auth.configure({
  region: 'us-east-1',
  userPoolId: 'us-east-1_XXXXXXXXX',
  userPoolWebClientId: 'XXXXXXXXXXXXXXXXXXXXXXXXXX'
});

// Sign in
async login(email, password) {
  const user = await Auth.signIn(email, password);
  const session = await Auth.currentSession();
  const idToken = session.getIdToken().getJwtToken();
  
  // Use idToken in API requests
  return { user, idToken };
}
```

### 5. Update Lambda Functions

```python
# Extract user from authorizer context
def lambda_handler(event, context):
    # User ID from authorizer
    user_id = event['requestContext']['authorizer']['userId']
    
    # Use for user-specific operations
    watchlist = get_user_watchlist(user_id)
```

## Recommended Implementation Order

1. **Phase 1: Cognito Setup** (2-3 hours)
   - Create Cognito User Pool
   - Configure user pool client
   - Set up password policies

2. **Phase 2: Lambda Authorizer** (2-3 hours)
   - Create authorizer function
   - Add JWT validation
   - Test with sample tokens

3. **Phase 3: API Gateway Integration** (1-2 hours)
   - Add authorizer to API Gateway
   - Apply to protected routes
   - Test authorization flow

4. **Phase 4: Frontend Integration** (3-4 hours)
   - Install AWS Amplify
   - Update UserManager to use Cognito
   - Update API calls to include tokens
   - Test full auth flow

5. **Phase 5: User Management** (2-3 hours)
   - Implement registration
   - Implement password reset
   - Add email verification

**Total Estimated Time:** 10-15 hours

## Current Workaround

For now, the local development mock authentication allows you to:
- Test the UI and UX
- Develop features that require authentication
- Test user-specific functionality (watchlists, custom factors)

But remember: **This will not work on AWS without the above implementation.**

## Testing on AWS Without Auth

If you want to deploy to AWS without authentication:
1. Remove `@auth_required` decorators from Lambda functions
2. Use a default user ID for all requests
3. Add authentication later as a separate feature

**Note:** This is NOT recommended for production but can work for initial testing.

## References

- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [Lambda Authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html)
- [AWS Amplify Auth](https://docs.amplify.aws/lib/auth/getting-started/q/platform/js/)

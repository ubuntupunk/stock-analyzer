# Authentication System Setup - Stock Analyzer

## ✅ What's Already Configured

### AWS Infrastructure (Deployed)
- **Cognito User Pool**: `us-east-1_pSr2hBy9j`
- **User Pool Client**: `g3h1dsvker3kp9gqansbcht77`
- **Region**: `us-east-1`
- **Password Policy**: Min 8 chars, requires uppercase, lowercase, and numbers
- **Email Verification**: Enabled (auto-verified)

### Frontend Code (Implemented)
- ✅ `auth.js` - Complete AuthManager class with all methods
- ✅ `config.js` - Cognito configuration values
- ✅ `app.js` - AuthManager initialization on startup
- ✅ `components/auth-modal.html` - Sign in/up/verify UI
- ✅ Auth handlers in app.js (handleSignIn, handleSignUp, etc.)
- ✅ AWS Amplify library loaded in index.html

### Features Available
- User sign up with email
- Email verification with code
- User sign in
- User sign out
- Password reset (forgot password)
- Change password
- Session management
- JWT token retrieval for API calls

## 🧪 Testing

### Test Page
Access the test page at:
- **CloudFront**: https://d1gl9b1d3yuv4y.cloudfront.net/auth-test.html
- **S3**: http://stock-analyzer-frontendbucket-s1vv1souwynv.s3-website-us-east-1.amazonaws.com/auth-test.html

### Test Flow
1. **Sign Up**
   - Enter email and password (min 8 chars, uppercase, lowercase, numbers)
   - Click "Sign Up"
   - Check email for verification code

2. **Verify Email**
   - Enter email and verification code from email
   - Click "Verify"

3. **Sign In**
   - Enter email and password
   - Click "Sign In"
   - Should see user info displayed

4. **Check User**
   - Click "Check Current User" to see authenticated user details

5. **Sign Out**
   - Click "Sign Out"

### Main App Testing
1. Open https://d1gl9b1d3yuv4y.cloudfront.net/
2. Look for auth button in header
3. Click to open auth modal
4. Test sign up/sign in flow

## 📋 Current Status

### ✅ Completed
- [x] Cognito User Pool created and deployed
- [x] User Pool Client configured
- [x] AuthManager class implemented
- [x] Amplify configured on app startup
- [x] Auth UI components created
- [x] Auth handlers in app.js
- [x] Test page created and deployed
- [x] Frontend deployed to S3/CloudFront

### 🔄 Next Steps (Optional Enhancements)

1. **Protected Routes**
   - Add authentication checks for certain features
   - Redirect to sign in when needed

2. **User Profile**
   - Display user info in header
   - User settings page

3. **Watchlist Sync**
   - Currently uses localStorage
   - Could sync to DynamoDB with user ID

4. **API Authorization**
   - Add Cognito authorizer to API Gateway
   - Protect certain endpoints (factors POST, watchlist)
   - Pass JWT token in API requests

5. **Social Sign In** (Future)
   - Google/Facebook/Apple sign in
   - Requires additional Cognito configuration

## 🔧 Configuration Files

### config.js
```javascript
cognito: {
    region: 'us-east-1',
    userPoolId: 'us-east-1_pSr2hBy9j',
    userPoolClientId: 'g3h1dsvker3kp9gqansbcht77'
}
```

### SAM Template (template.yaml)
```yaml
UserPool:
  Type: AWS::Cognito::UserPool
  Properties:
    UserPoolName: stock-analyzer-users
    AutoVerifiedAttributes:
      - email
    UsernameAttributes:
      - email
```

## 🐛 Troubleshooting

### Common Issues

**"Amplify not available"**
- Check that Amplify scripts are loaded in index.html
- Check browser console for script loading errors

**"Missing required Cognito configuration"**
- Verify config.js has correct values
- Check that config is loaded before auth.js

**"User not confirmed"**
- User needs to verify email with code
- Check spam folder for verification email
- Use "Resend Code" if needed

**"Invalid password"**
- Must be at least 8 characters
- Must contain uppercase letter
- Must contain lowercase letter
- Must contain number

### AWS CLI Commands

**List users:**
```bash
aws cognito-idp list-users --user-pool-id us-east-1_pSr2hBy9j --region us-east-1
```

**Delete user (for testing):**
```bash
aws cognito-idp admin-delete-user --user-pool-id us-east-1_pSr2hBy9j --username <email> --region us-east-1
```

**Confirm user manually (skip email verification):**
```bash
aws cognito-idp admin-confirm-sign-up --user-pool-id us-east-1_pSr2hBy9j --username <email> --region us-east-1
```

## 📚 Resources

- [AWS Amplify Auth Docs](https://docs.amplify.aws/lib/auth/getting-started/q/platform/js/)
- [Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html)
- [Amplify Auth API](https://aws-amplify.github.io/amplify-js/api/classes/authclass.html)

## 🔐 Security Notes

- Passwords are never stored in plain text
- JWT tokens expire after 60 minutes
- Refresh tokens valid for 30 days
- Email verification required before sign in
- User existence errors are prevented (security feature)

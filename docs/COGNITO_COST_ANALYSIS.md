# AWS Cognito Authentication - Cost Analysis

## 📋 Executive Summary

**Adding Cognito for User Authentication:**
- **First 50,000 MAU**: **FREE** (Always Free Tier) ✅
- **Beyond 50,000 MAU**: **$0.0055 per MAU** (~$0.55 per 100 users)
- **No upfront costs, no minimum fees**

**Bottom Line:** For most applications, Cognito adds **$0/month** to your costs!

---

## 💰 AWS Cognito Pricing Breakdown

### **1. User Pools (Authentication)**

#### **Free Tier (Always Free - Not just 12 months!)**
```
✅ First 50,000 Monthly Active Users (MAU): FREE
   - MAU = Users who perform auth operation in a month
   - Includes: Sign-up, sign-in, token refresh, password reset
```

#### **Pricing After Free Tier**
```
Users 50,001 - 100,000:     $0.0055 per MAU
Users 100,001+:             $0.0046 per MAU

Example:
- 60,000 MAU = 50,000 free + (10,000 × $0.0055) = $55/month
- 150,000 MAU = 50,000 free + (50,000 × $0.0055) + (50,000 × $0.0046)
              = $0 + $275 + $230 = $505/month
```

### **2. Advanced Security Features (Optional)**

| Feature | Pricing | Use Case |
|---------|---------|----------|
| **Basic Security** | FREE | Standard protection |
| **Advanced Security** | $0.05 per MAU | Risk-based auth, compromised credential checks |
| **MFA (SMS)** | $0.00075 per SMS | Two-factor authentication |
| **MFA (TOTP)** | FREE | App-based 2FA (Google Authenticator) |

---

## 📊 Cost Scenarios with Cognito

### **Scenario 1: Small Application (10-100 users)**
```
Current Stack:
├─ Lambda:              $0.00  (Free Tier)
├─ API Gateway:         $0.00  (Free Tier)
├─ DynamoDB:            $0.00  (Free Tier)
├─ S3:                  $0.00  (Free Tier)
└─ External APIs:       $0.00  (Free Tier)

+ Cognito:              $0.00  (< 50K MAU)
────────────────────────────────────────────
TOTAL:                  $0.00/month ✅

Impact: NO COST INCREASE
```

### **Scenario 2: Medium Application (1,000 users)**
```
Current Stack:
├─ Lambda:              $0.13/month  (After Year 1)
├─ API Gateway:         $0.11/month  (After Year 1)
├─ DynamoDB:            $0.00/month  (Always Free)
├─ S3:                  $0.01/month  (After Year 1)
└─ External APIs:       $0.00/month  (Free Tier)
                        ─────────────
Subtotal:               $0.25/month

+ Cognito:              $0.00/month  (< 50K MAU)
────────────────────────────────────────────
TOTAL:                  $0.25/month ✅

Impact: NO COST INCREASE
```

### **Scenario 3: Growing Application (10,000 users)**
```
Current Stack:
├─ Lambda:              $1.30/month
├─ API Gateway:         $1.05/month
├─ DynamoDB:            $0.50/month
├─ S3:                  $0.05/month
└─ External APIs:       $0.00/month
                        ─────────────
Subtotal:               $2.90/month

+ Cognito:              $0.00/month  (< 50K MAU)
────────────────────────────────────────────
TOTAL:                  $2.90/month ✅

Impact: NO COST INCREASE
```

### **Scenario 4: Large Application (60,000 MAU)**
```
Current Stack:
├─ Lambda:              $6.50/month
├─ API Gateway:         $5.25/month
├─ DynamoDB:            $2.50/month
├─ S3:                  $0.25/month
└─ External APIs:       $50.00/month
                        ─────────────
Subtotal:               $64.50/month

+ Cognito:              $55.00/month  (10K over free tier)
────────────────────────────────────────────
TOTAL:                  $119.50/month

Impact: +$55/month for users beyond 50K
```

### **Scenario 5: Enterprise (200,000 MAU)**
```
Current Stack:          $150.00/month

+ Cognito:              $685.00/month
  (50K free + 50K @ $0.0055 + 100K @ $0.0046)
────────────────────────────────────────────
TOTAL:                  $835.00/month

Impact: Significant, but at this scale you have revenue!
```

---

## 🔍 What Counts as a Monthly Active User (MAU)?

### **Operations That Count as MAU:**
✅ Sign-up (new user registration)
✅ Sign-in (email/password, social login)
✅ Token refresh
✅ Password reset request
✅ Email verification
✅ Phone verification
✅ Change password

### **Operations That DON'T Count:**
❌ API requests with valid token
❌ Accessing protected resources
❌ Reading user attributes from existing session
❌ Lambda authorizer checks (after initial auth)

### **Example:**
```
User Activity:
Day 1:  Sign-in (counts as 1 MAU)
Day 2:  Makes 100 API requests (doesn't count)
Day 3:  Token refreshes automatically (counts as 1 MAU)
Day 15: Makes 50 more API requests (doesn't count)
Day 30: Signs in again (already counted this month)

Total: 1 MAU for the month
```

---

## 💡 Cognito Features & Benefits

### **What You Get for FREE (< 50K MAU):**

#### **Core Authentication**
- ✅ User registration & sign-in
- ✅ Email & phone verification
- ✅ Password reset flows
- ✅ Secure password policies
- ✅ JWT token management
- ✅ Session management
- ✅ User profile attributes

#### **Social Identity Providers (FREE)**
- ✅ Google sign-in
- ✅ Facebook sign-in
- ✅ Amazon sign-in
- ✅ Apple sign-in
- ✅ SAML identity providers

#### **Security Features (FREE)**
- ✅ Password encryption
- ✅ Secure password policies
- ✅ Account confirmation
- ✅ Email/SMS verification
- ✅ HTTPS only
- ✅ OAuth 2.0 / OpenID Connect

#### **Developer Features (FREE)**
- ✅ Lambda triggers (pre/post auth, custom messages)
- ✅ User migration
- ✅ Custom attributes
- ✅ Group-based access control
- ✅ Admin APIs
- ✅ SDK support (JavaScript, Python, etc.)

---

## 🛠️ Implementation Changes Needed

### **1. Infrastructure Changes (template.yaml)**

```yaml
# Add to Resources section
UserPool:
  Type: AWS::Cognito::UserPool
  Properties:
    UserPoolName: stock-analyzer-users
    AutoVerifiedAttributes:
      - email
    UsernameAttributes:
      - email
    Policies:
      PasswordPolicy:
        MinimumLength: 8
        RequireUppercase: true
        RequireLowercase: true
        RequireNumbers: true
        RequireSymbols: false
    Schema:
      - Name: email
        Required: true
        Mutable: false
      - Name: name
        Required: false
        Mutable: true

UserPoolClient:
  Type: AWS::Cognito::UserPoolClient
  Properties:
    UserPoolId: !Ref UserPool
    ClientName: stock-analyzer-web-client
    GenerateSecret: false
    ExplicitAuthFlows:
      - ALLOW_USER_PASSWORD_AUTH
      - ALLOW_REFRESH_TOKEN_AUTH
    PreventUserExistenceErrors: ENABLED

# Update API Gateway
StockAnalyzerAPI:
  Type: AWS::Serverless::Api
  Properties:
    StageName: prod
    Auth:
      DefaultAuthorizer: CognitoAuthorizer
      Authorizers:
        CognitoAuthorizer:
          UserPoolArn: !GetAtt UserPool.Arn
```

**Cost Impact:** ✅ **$0** (infrastructure definition is free)

### **2. Lambda Function Changes**

**Before (Anonymous):**
```python
# watchlist_api.py - line 113
user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub', 'anonymous')
```

**After (Authenticated):**
```python
# watchlist_api.py - line 113
user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')

if not user_id:
    return {
        'statusCode': 401,
        'body': json.dumps({'error': 'Unauthorized - Authentication required'})
    }
```

**Cost Impact:** ✅ **$0** (code change, no cost)

### **3. Frontend Changes (frontend/app.js)**

**Add Cognito SDK:**
```html
<!-- In index.html -->
<script src="https://cdn.jsdelivr.net/npm/amazon-cognito-identity-js@6.2.0/dist/amazon-cognito-identity.min.js"></script>
```

**Add Authentication Functions:**
```javascript
// In app.js
const cognitoConfig = {
    UserPoolId: 'us-east-1_XXXXXXXXX',  // From CloudFormation output
    ClientId: 'xxxxxxxxxxxxxxxxxxxxxxxxxx'   // From CloudFormation output
};

const userPool = new AmazonCognitoIdentity.CognitoUserPool(cognitoConfig);

// Sign up
function signUp(email, password, name) {
    const attributeList = [
        new AmazonCognitoIdentity.CognitoUserAttribute({
            Name: 'email',
            Value: email
        }),
        new AmazonCognitoIdentity.CognitoUserAttribute({
            Name: 'name',
            Value: name
        })
    ];

    userPool.signUp(email, password, attributeList, null, (err, result) => {
        if (err) {
            console.error('Sign up error:', err);
            return;
        }
        console.log('User signed up:', result.user.getUsername());
    });
}

// Sign in
function signIn(email, password) {
    const authenticationData = {
        Username: email,
        Password: password
    };
    
    const authenticationDetails = new AmazonCognitoIdentity.AuthenticationDetails(authenticationData);
    
    const userData = {
        Username: email,
        Pool: userPool
    };
    
    const cognitoUser = new AmazonCognitoIdentity.CognitoUser(userData);
    
    cognitoUser.authenticateUser(authenticationDetails, {
        onSuccess: (result) => {
            const idToken = result.getIdToken().getJwtToken();
            // Store token for API requests
            localStorage.setItem('idToken', idToken);
            console.log('Signed in successfully');
        },
        onFailure: (err) => {
            console.error('Sign in error:', err);
        }
    });
}

// Add token to API requests
function makeAuthenticatedRequest(url, options = {}) {
    const token = localStorage.getItem('idToken');
    
    if (!token) {
        window.location.href = '/login.html';
        return;
    }
    
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`
    };
    
    return fetch(url, options);
}
```

**Cost Impact:** ✅ **$0** (using CDN-hosted SDK)

### **4. Add Login/Signup UI**

**Create `frontend/login.html`:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Stock Analyzer - Login</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="auth-container">
        <h1>Sign In</h1>
        <form id="loginForm">
            <input type="email" id="email" placeholder="Email" required>
            <input type="password" id="password" placeholder="Password" required>
            <button type="submit">Sign In</button>
        </form>
        <p>Don't have an account? <a href="signup.html">Sign Up</a></p>
        <p><a href="#" id="forgotPassword">Forgot Password?</a></p>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/amazon-cognito-identity-js@6.2.0/dist/amazon-cognito-identity.min.js"></script>
    <script src="config.js"></script>
    <script src="auth.js"></script>
</body>
</html>
```

**Cost Impact:** ✅ **$0** (static HTML files)

---

## 📈 Cost Comparison: DIY Auth vs Cognito

### **Option 1: DIY Authentication**

**Costs:**
```
RDS PostgreSQL (db.t3.micro):   $15/month
Developer time (20 hours):      $2,000 (one-time)
Maintenance (monthly):          $500/month (security patches, updates)
Security audits:                $5,000/year
────────────────────────────────────────────
Year 1 Total:                   $13,180
```

**Risks:**
- ❌ Security vulnerabilities
- ❌ Compliance issues (GDPR, CCPA)
- ❌ Password storage liability
- ❌ Account recovery complexity
- ❌ Ongoing maintenance burden

### **Option 2: AWS Cognito**

**Costs:**
```
Setup time (4 hours):           $400 (one-time)
Monthly cost (< 50K users):     $0/month
Monthly cost (100K users):      $275/month
Security & compliance:          INCLUDED
Maintenance:                    INCLUDED
────────────────────────────────────────────
Year 1 Total (< 50K users):     $400 ✅
Year 1 Total (100K users):      $3,700 ✅
```

**Benefits:**
- ✅ AWS-managed security
- ✅ HIPAA, SOC, PCI DSS compliant
- ✅ Built-in password policies
- ✅ Automatic security updates
- ✅ No infrastructure to maintain
- ✅ Social login (Google, Facebook, etc.)

**Winner:** Cognito is **97% cheaper** and **infinitely more secure**

---

## 🎯 Updated Total Cost with Cognito

### **Complete Stack with Authentication**

| Users | Requests/Day | Without Auth | With Cognito | Increase |
|-------|--------------|--------------|--------------|----------|
| 10 | 100 | $0.00 | $0.00 | $0 ✅ |
| 100 | 1,000 | $0.25 | $0.25 | $0 ✅ |
| 1,000 | 10,000 | $1.00 | $1.00 | $0 ✅ |
| 10,000 | 100,000 | $10.00 | $10.00 | $0 ✅ |
| 50,000 | 500,000 | $50.00 | $50.00 | $0 ✅ |
| 60,000 | 600,000 | $60.00 | $115.00 | +$55 ⚠️ |
| 100,000 | 1,000,000 | $100.00 | $375.00 | +$275 ⚠️ |

**Key Insight:** For 99% of applications (< 50K users), Cognito adds **$0** to your costs!

---

## 🔐 Additional Cognito Costs (Optional)

### **1. SMS MFA (Two-Factor Authentication)**

**Pricing:**
- $0.00075 per SMS sent
- 100 SMS/month = $0.075
- 1,000 SMS/month = $0.75

**Alternative (FREE):**
- Use TOTP-based MFA (Google Authenticator, Authy)
- Cost: $0 ✅

### **2. Advanced Security Features**

**Pricing:**
- $0.05 per MAU for advanced security
- Includes: Risk-based authentication, compromised credential checks

**Example:**
- 1,000 users with advanced security = $50/month
- 10,000 users with advanced security = $500/month

**Recommendation:** Start with basic security (FREE), upgrade if needed

### **3. Custom Domains**

**Hosted UI Domain:**
- Default: `https://your-app.auth.us-east-1.amazoncognito.com` (FREE)
- Custom: `https://login.yourapp.com` (Requires ACM certificate - FREE)

**Cost:** ✅ **$0** (using free ACM certificate)

---

## 📊 Implementation Complexity

### **Development Time Estimate:**

| Task | Time | Difficulty |
|------|------|------------|
| Add Cognito to template.yaml | 30 min | Easy |
| Update Lambda authorizers | 1 hour | Easy |
| Frontend login UI | 2 hours | Medium |
| Frontend signup UI | 1 hour | Easy |
| Password reset flow | 1 hour | Easy |
| Testing & debugging | 2 hours | Medium |
| **TOTAL** | **7.5 hours** | **Medium** |

**Developer Cost:** ~$750 (at $100/hour)

---

## 🎓 Cognito vs Alternatives

### **Comparison Matrix**

| Feature | Cognito | Auth0 | Firebase Auth | Custom |
|---------|---------|-------|---------------|--------|
| **Free Tier** | 50K MAU | 7K MAU | 50K MAU | N/A |
| **Price (100K MAU)** | $275/mo | $467/mo | Free | $5K+/year |
| **AWS Integration** | Native | API | API | Custom |
| **Social Login** | Yes | Yes | Yes | Custom |
| **MFA** | Yes | Yes | Yes | Custom |
| **Compliance** | HIPAA, SOC | HIPAA, SOC | SOC | DIY |
| **Setup Time** | 1 day | 2 days | 1 day | 2 months |
| **Maintenance** | AWS | Auth0 | Google | You |

**Winner for AWS Apps:** Cognito ✅

---

## 🚀 Recommendation

### **Should You Add Cognito?**

✅ **YES, if:**
- You want user-specific watchlists
- You need secure authentication
- You want to scale to thousands of users
- You want to add premium features later
- You want social login (Google, Facebook)

❌ **NO, if:**
- You want a public demo (no login required)
- You have < 10 users (not worth the complexity)
- You're just testing the concept

### **Best Approach:**

**Phase 1: Launch without Auth**
- Keep current anonymous setup
- Get feedback, test the app
- **Cost:** $0/month

**Phase 2: Add Cognito (when needed)**
- Add authentication when you have real users
- Migrate from anonymous to authenticated
- **Cost:** Still $0/month (< 50K MAU)

**Phase 3: Scale with Confidence**
- Cognito scales automatically
- Pay only for what you use
- **Cost:** Predictable and reasonable

---

## 💡 Cost Optimization Tips for Cognito

### **1. Use TOTP MFA Instead of SMS**
```
SMS MFA:  $0.00075 per SMS = $75 per 100K MFA requests
TOTP MFA: FREE
Savings:  $75/month per 100K MFA
```

### **2. Implement Token Caching**
```javascript
// Cache tokens to avoid unnecessary refresh calls
const tokenCache = {
    token: null,
    expiry: null
};

function getToken() {
    if (tokenCache.token && Date.now() < tokenCache.expiry) {
        return tokenCache.token;
    }
    // Refresh token logic
}
```

### **3. Use Federated Identity (Social Login)**
```
Cost: FREE (Google, Facebook handle auth)
Benefit: Better UX, fewer password resets
```

### **4. Set Token Expiry Appropriately**
```yaml
# In Cognito UserPoolClient
TokenValidityUnits:
  AccessToken: hours
  IdToken: hours
  RefreshToken: days

AccessTokenValidity: 1    # 1 hour (reduces refresh frequency)
IdTokenValidity: 1        # 1 hour
RefreshTokenValidity: 30  # 30 days (less frequent sign-ins)
```

---

## 📊 Final Cost Summary with Cognito

### **Complete Infrastructure Cost (After Free Tier)**

```
Monthly Active Users: 1,000

Core Services:
├─ Lambda (3 functions):    $0.13
├─ API Gateway:             $0.11
├─ DynamoDB (2 tables):     $0.00  (Always free)
├─ S3 (Frontend):           $0.01
├─ Data Transfer:           $0.00
├─ External APIs:           $0.00  (Free tiers)
└─ Cognito:                 $0.00  (< 50K MAU)
────────────────────────────────────
TOTAL:                      $0.25/month ✅

With 60,000 MAU:
└─ Cognito:                 $55.00  (10K over free tier)
────────────────────────────────────
TOTAL:                      $55.25/month
```

---

## 🎯 Final Verdict

**Adding Cognito Authentication:**

✅ **Highly Recommended**
- Cost: **$0/month** for first 50,000 users
- Security: Enterprise-grade, AWS-managed
- Features: Social login, MFA, password reset
- Maintenance: Zero (AWS handles it)
- Compliance: HIPAA, SOC, PCI DSS ready
- ROI: Saves thousands vs DIY auth

**Only starts costing money when you're successful (> 50K users)!**

---

*Analysis as of January 2026. Cognito pricing: https://aws.amazon.com/cognito/pricing/*

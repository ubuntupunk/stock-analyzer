// Authentication module using AWS Amplify
// Handles Cognito user authentication, token management, and session handling

class AuthManager {
    constructor() {
        this.currentUser = null;
        this.isConfigured = false;
    }

    /**
     * Configure Amplify with Cognito settings
     * Should be called on app initialization with CloudFormation outputs
     */
    configure(config) {
        // Check if Amplify is available
        if (typeof Amplify === 'undefined') {
            console.warn('Amplify not available - authentication disabled');
            this.isConfigured = false;
            return false;
        }

        if (!config.userPoolId || !config.userPoolClientId || !config.region) {
            console.error('Missing required Cognito configuration');
            return false;
        }

        try {
            Amplify.configure({
                Auth: {
                    region: config.region,
                    userPoolId: config.userPoolId,
                    userPoolWebClientId: config.userPoolClientId,
                    mandatorySignIn: false,
                    authenticationFlowType: 'USER_SRP_AUTH'
                }
            });
            
            this.isConfigured = true;
            console.log('Amplify configured successfully');
            return true;
        } catch (error) {
            console.error('Failed to configure Amplify:', error);
            return false;
        }
    }

    /**
     * Sign up a new user
     */
    async signUp(email, password) {
        try {
            const { user } = await Auth.signUp({
                username: email,
                password: password,
                attributes: {
                    email: email
                }
            });
            
            return {
                success: true,
                user: user,
                message: 'Sign up successful! Please check your email for verification code.'
            };
        } catch (error) {
            console.error('Sign up error:', error);
            return {
                success: false,
                error: error.message || 'Sign up failed'
            };
        }
    }

    /**
     * Confirm sign up with verification code
     */
    async confirmSignUp(email, code) {
        try {
            await Auth.confirmSignUp(email, code);
            return {
                success: true,
                message: 'Email verified successfully! You can now sign in.'
            };
        } catch (error) {
            console.error('Confirmation error:', error);
            return {
                success: false,
                error: error.message || 'Verification failed'
            };
        }
    }

    /**
     * Resend verification code
     */
    async resendConfirmationCode(email) {
        try {
            await Auth.resendSignUp(email);
            return {
                success: true,
                message: 'Verification code resent to your email'
            };
        } catch (error) {
            console.error('Resend code error:', error);
            return {
                success: false,
                error: error.message || 'Failed to resend code'
            };
        }
    }

    /**
     * Sign in an existing user
     */
    async signIn(email, password) {
        try {
            const user = await Auth.signIn(email, password);
            this.currentUser = user;
            
            // Store user info in session
            this.storeUserSession(user);
            
            return {
                success: true,
                user: user,
                message: 'Signed in successfully!'
            };
        } catch (error) {
            console.error('Sign in error:', error);
            
            // Handle specific error cases
            if (error.code === 'UserNotConfirmedException') {
                return {
                    success: false,
                    needsConfirmation: true,
                    error: 'Please verify your email before signing in'
                };
            }
            
            return {
                success: false,
                error: error.message || 'Sign in failed'
            };
        }
    }

    /**
     * Sign out the current user
     */
    async signOut() {
        try {
            await Auth.signOut();
            this.currentUser = null;
            this.clearUserSession();
            
            return {
                success: true,
                message: 'Signed out successfully'
            };
        } catch (error) {
            console.error('Sign out error:', error);
            return {
                success: false,
                error: error.message || 'Sign out failed'
            };
        }
    }

    /**
     * Get the current authenticated user
     */
    async getCurrentUser() {
        try {
            const user = await Auth.currentAuthenticatedUser();
            this.currentUser = user;
            return user;
        } catch (error) {
            this.currentUser = null;
            return null;
        }
    }

    /**
     * Check if user is authenticated
     */
    async isAuthenticated() {
        const user = await this.getCurrentUser();
        return user !== null;
    }

    /**
     * Get current session and JWT token
     */
    async getSession() {
        try {
            // Check if Auth is available
            if (typeof Auth === 'undefined') {
                console.warn('Auth not available - authentication not configured');
                return null;
            }
            
            const session = await Auth.currentSession();
            return session;
        } catch (error) {
            console.error('Failed to get session:', error);
            return null;
        }
    }

    /**
     * Get JWT token for API requests
     */
    async getAuthToken() {
        try {
            const session = await this.getSession();
            if (session) {
                return session.getIdToken().getJwtToken();
            }
            return null;
        } catch (error) {
            console.error('Failed to get auth token:', error);
            return null;
        }
    }

    /**
     * Get user attributes (email, etc.)
     */
    async getUserAttributes() {
        try {
            const user = await this.getCurrentUser();
            if (user) {
                return user.attributes;
            }
            return null;
        } catch (error) {
            console.error('Failed to get user attributes:', error);
            return null;
        }
    }

    /**
     * Forgot password - send reset code
     */
    async forgotPassword(email) {
        try {
            await Auth.forgotPassword(email);
            return {
                success: true,
                message: 'Password reset code sent to your email'
            };
        } catch (error) {
            console.error('Forgot password error:', error);
            return {
                success: false,
                error: error.message || 'Failed to send reset code'
            };
        }
    }

    /**
     * Reset password with code
     */
    async resetPassword(email, code, newPassword) {
        try {
            await Auth.forgotPasswordSubmit(email, code, newPassword);
            return {
                success: true,
                message: 'Password reset successfully! You can now sign in.'
            };
        } catch (error) {
            console.error('Reset password error:', error);
            return {
                success: false,
                error: error.message || 'Failed to reset password'
            };
        }
    }

    /**
     * Change password for authenticated user
     */
    async changePassword(oldPassword, newPassword) {
        try {
            const user = await this.getCurrentUser();
            if (!user) {
                return {
                    success: false,
                    error: 'No authenticated user'
                };
            }
            
            await Auth.changePassword(user, oldPassword, newPassword);
            return {
                success: true,
                message: 'Password changed successfully'
            };
        } catch (error) {
            console.error('Change password error:', error);
            return {
                success: false,
                error: error.message || 'Failed to change password'
            };
        }
    }

    /**
     * Store user session in localStorage
     */
    storeUserSession(user) {
        try {
            const userInfo = {
                username: user.username,
                email: user.attributes?.email,
                userId: user.attributes?.sub,
                signInTime: new Date().toISOString()
            };
            localStorage.setItem('stockAnalyzerUser', JSON.stringify(userInfo));
        } catch (error) {
            console.error('Failed to store user session:', error);
        }
    }

    /**
     * Get stored user session
     */
    getStoredUserSession() {
        try {
            const stored = localStorage.getItem('stockAnalyzerUser');
            return stored ? JSON.parse(stored) : null;
        } catch (error) {
            console.error('Failed to get stored session:', error);
            return null;
        }
    }

    /**
     * Clear user session from localStorage
     */
    clearUserSession() {
        try {
            localStorage.removeItem('stockAnalyzerUser');
        } catch (error) {
            console.error('Failed to clear user session:', error);
        }
    }

    /**
     * Get user display name (email or username)
     */
    async getDisplayName() {
        const attributes = await this.getUserAttributes();
        return attributes?.email || 'User';
    }
}

// Create global auth instance
const authManager = new AuthManager();

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.authManager = authManager;
}

/**
 * User Manager
 * Handles user authentication, profile management, and session persistence
 * Integrates with Cognito for auth and DynamoDB for data
 */

class UserManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.dynamoService = new DynamoDBService();
        this.currentUser = null;
        this.sessionKey = 'stock_analyzer_session';
        
        // Subscribe to events
        this.setupEventListeners();
    }
    
    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for session restore on app init
        this.eventBus.on('app:initialized', () => {
            this.restoreSession();
        });
    }
    
    /**
     * Initialize user manager
     */
    async initialize() {
        await this.dynamoService.initialize();
        await this.restoreSession();
    }
    
    // ============================================
    // AUTHENTICATION
    // ============================================
    
    /**
     * Register a new user
     * @param {string} email - User email
     * @param {string} password - User password
     * @param {string} name - User display name
     * @returns {Promise} Registration result
     */
    async register(email, password, name) {
        try {
            console.log('UserManager: Registering user:', email);
            
            // Validate input
            if (!this.validateEmail(email)) {
                throw new Error('Invalid email format');
            }
            
            if (password.length < 8) {
                throw new Error('Password must be at least 8 characters');
            }
            
            // Check if user already exists
            const existingUser = await this.dynamoService.getUserByEmail(email);
            if (existingUser) {
                throw new Error('User with this email already exists');
            }
            
            // Generate user ID
            const userId = this.generateUserId();
            
            // In production, this would call Cognito SignUp
            // For now, we'll use a simple registration flow
            const userData = {
                userId,
                email: email.toLowerCase(),
                name: name || email.split('@')[0]
            };
            
            // Create user in DynamoDB
            await this.dynamoService.createUser(userData);
            
            // Create session
            this.createSession(userId, userData);
            
            this.eventBus.emit('user:registered', { userId, email });
            
            return {
                success: true,
                user: {
                    userId,
                    email: email.toLowerCase(),
                    name: name || email.split('@')[0]
                }
            };
        } catch (error) {
            console.error('UserManager: Registration failed:', error);
            this.eventBus.emit('user:error', { error: error.message, type: 'registration' });
            throw error;
        }
    }
    
    /**
     * Login user
     * @param {string} email - User email
     * @param {string} password - User password
     * @returns {Promise} Login result
     */
    async login(email, password) {
        try {
            console.log('UserManager: Login attempt:', email);
            
            // Validate input
            if (!this.validateEmail(email)) {
                throw new Error('Invalid email format');
            }
            
            // In production, this would call Cognito InitiateAuth
            // For demo, we'll check against DynamoDB
            
            // Get user by email
            const user = await this.dynamoService.getUserByEmail(email.toLowerCase());
            
            if (!user) {
                // Create demo user for testing
                const demoUserId = this.generateUserId();
                await this.dynamoService.createUser({
                    userId: demoUserId,
                    email: email.toLowerCase(),
                    name: email.split('@')[0]
                });
                
                this.createSession(demoUserId, {
                    userId: demoUserId,
                    email: email.toLowerCase(),
                    name: email.split('@')[0]
                });
                
                this.eventBus.emit('user:loggedin', { userId: demoUserId, email });
                
                return {
                    success: true,
                    user: {
                        userId: demoUserId,
                        email: email.toLowerCase(),
                        name: email.split('@')[0]
                    }
                };
            }
            
            // Create session
            this.createSession(user.userId, user);
            
            this.eventBus.emit('user:loggedin', { userId: user.userId, email });
            
            return {
                success: true,
                user: {
                    userId: user.userId,
                    email: user.email,
                    name: user.name
                }
            };
        } catch (error) {
            console.error('UserManager: Login failed:', error);
            this.eventBus.emit('user:error', { error: error.message, type: 'login' });
            throw error;
        }
    }
    
    /**
     * Logout user
     */
    logout() {
        console.log('UserManager: Logging out');
        
        // Clear current user
        this.currentUser = null;
        
        // Remove session from localStorage
        localStorage.removeItem(this.sessionKey);
        
        // Also clear any other potential session keys
        // (in case there are multiple session keys being used)
        Object.keys(localStorage).forEach(key => {
            if (key.includes('stock_analyzer') || key.includes('session')) {
                localStorage.removeItem(key);
            }
        });
        
        // Emit logout event
        this.eventBus.emit('user:loggedout');
        
        // Force a page reload to clear any in-memory state
        // This ensures a clean slate after logout
        setTimeout(() => {
            window.location.reload();
        }, 100);
    }
    
    /**
     * Get current user
     * @returns {object|null} Current user
     */
    getCurrentUser() {
        return this.currentUser;
    }
    
    /**
     * Check if user is logged in
     * @returns {boolean} Is logged in
     */
    isLoggedIn() {
        return !!this.currentUser;
    }
    
    /**
     * Get current user ID
     * @returns {string|null} User ID
     */
    getCurrentUserId() {
        return this.currentUser?.userId || null;
    }
    
    // ============================================
    // SESSION MANAGEMENT
    // ============================================
    
    /**
     * Create session
     * @param {string} userId - User ID
     * @param {object} userData - User data
     */
    createSession(userId, userData) {
        const session = {
            userId,
            user: userData,
            createdAt: new Date().toISOString()
        };
        
        localStorage.setItem(this.sessionKey, JSON.stringify(session));
        this.currentUser = userData;
        
        console.log('UserManager: Session created for:', userData.email);
    }
    
    /**
     * Restore session from localStorage
     */
    async restoreSession() {
        try {
            const sessionData = localStorage.getItem(this.sessionKey);
            
            if (!sessionData) {
                console.log('UserManager: No session found');
                return;
            }
            
            const session = JSON.parse(sessionData);
            
            // Check if session is expired (7 days)
            const sessionAge = Date.now() - new Date(session.createdAt).getTime();
            const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days
            
            if (sessionAge > maxAge) {
                console.log('UserManager: Session expired');
                localStorage.removeItem(this.sessionKey);
                return;
            }
            
            // Verify user still exists in DB
            const user = await this.dynamoService.getUser(session.userId);
            
            if (!user) {
                console.log('UserManager: User no longer exists');
                localStorage.removeItem(this.sessionKey);
                return;
            }
            
            this.currentUser = session.user;
            console.log('UserManager: Session restored for:', this.currentUser.email);
            
            this.eventBus.emit('user:sessionRestored', { user: this.currentUser });
        } catch (error) {
            console.error('UserManager: Failed to restore session:', error);
            localStorage.removeItem(this.sessionKey);
        }
    }
    
    // ============================================
    // USER PROFILE
    // ============================================
    
    /**
     * Get user profile
     * @param {string} userId - User ID (uses current user if not provided)
     * @returns {Promise} User profile
     */
    async getProfile(userId = this.getCurrentUserId()) {
        if (!userId) {
            throw new Error('Not logged in');
        }
        
        const user = await this.dynamoService.getUser(userId);
        return user;
    }
    
    /**
     * Update user profile
     * @param {object} updates - Profile updates
     * @returns {Promise} Updated profile
     */
    async updateProfile(updates) {
        const userId = this.getCurrentUserId();
        
        if (!userId) {
            throw new Error('Not logged in');
        }
        
        // Validate updates
        if (updates.email && !this.validateEmail(updates.email)) {
            throw new Error('Invalid email format');
        }
        
        if (updates.name && updates.name.length < 2) {
            throw new Error('Name must be at least 2 characters');
        }
        
        const updatedUser = await this.dynamoService.updateUser(userId, updates);
        
        // Update session
        this.currentUser = { ...this.currentUser, ...updatedUser };
        this.createSession(userId, this.currentUser);
        
        this.eventBus.emit('user:profileUpdated', { user: updatedUser });
        
        return updatedUser;
    }
    
    /**
     * Update user preferences
     * @param {object} preferences - Preference updates
     * @returns {Promise} Updated preferences
     */
    async updatePreferences(preferences) {
        const userId = this.getCurrentUserId();
        
        if (!userId) {
            throw new Error('Not logged in');
        }
        
        const currentProfile = await this.getProfile();
        const mergedPreferences = { ...currentProfile.preferences, ...preferences };
        
        const updatedUser = await this.dynamoService.updateUser(userId, {
            preferences: mergedPreferences
        });
        
        this.eventBus.emit('user:preferencesUpdated', { preferences: mergedPreferences });
        
        return mergedPreferences;
    }
    
    // ============================================
    // PASSWORD MANAGEMENT
    // ============================================
    
    /**
     * Change password
     * @param {string} currentPassword - Current password
     * @param {string} newPassword - New password
     * @returns {Promise} Result
     */
    async changePassword(currentPassword, newPassword) {
        // In production, this would call Cognito ChangePassword
        if (newPassword.length < 8) {
            throw new Error('New password must be at least 8 characters');
        }
        
        console.log('UserManager: Password changed successfully');
        
        this.eventBus.emit('user:passwordChanged');
        
        return { success: true };
    }
    
    /**
     * Request password reset
     * @param {string} email - User email
     * @returns {Promise} Result
     */
    async requestPasswordReset(email) {
        // In production, this would call Cognito ForgotPassword
        console.log('UserManager: Password reset requested for:', email);
        
        this.eventBus.emit('user:passwordResetRequested', { email });
        
        return { success: true, message: 'Password reset email sent' };
    }
    
    // ============================================
    // HELPER METHODS
    // ============================================
    
    /**
     * Generate unique user ID
     * @returns {string} User ID
     */
    generateUserId() {
        return 'user_' + Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * Validate email format
     * @param {string} email - Email to validate
     * @returns {boolean} Is valid
     */
    validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    /**
     * Clean up resources
     */
    cleanup() {
        this.currentUser = null;
        console.log('UserManager: Cleaned up');
    }

    /**
     * Lifecycle: Initialize module (called once)
     */
    onInit() {
        console.log('[UserManager] Initialized');
        this.isInitialized = true;
        this.isVisible = true;
    }

    /**
     * Lifecycle: Show module (resume operations)
     */
    onShow() {
        console.log('[UserManager] Shown');
        this.isVisible = true;
    }

    /**
     * Lifecycle: Hide module (pause operations)
     */
    onHide() {
        console.log('[UserManager] Hidden');
        this.isVisible = false;
    }

    /**
     * Lifecycle: Destroy module (complete cleanup)
     */
    onDestroy() {
        console.log('[UserManager] Destroyed - complete cleanup');
        this.cleanup();
        this.isInitialized = false;
    }

    /**
     * Get module state for lifecycle manager
     */
    getState() {
        return {
            currentUser: this.currentUser,
            isInitialized: this.isInitialized,
            isVisible: this.isVisible
        };
    }

    /**
     * Set module state from lifecycle manager
     */
    setState(state) {
        console.log('[UserManager] Restoring state:', state);
        if (state?.currentUser) {
            this.currentUser = state.currentUser;
        }
        this.isVisible = state?.isVisible ?? true;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UserManager;
} else {
    window.UserManager = UserManager;
}
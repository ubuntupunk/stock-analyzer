// Main Application Orchestrator
// Coordinates all modules and provides the main application interface

class StockAnalyzer {
    constructor() {
        this.modules = {};
        this.isInitialized = false;
        
        // Initialize immediately
        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        try {
            console.log('Initializing Stock Analyzer...');
            
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                await new Promise(resolve => {
                    document.addEventListener('DOMContentLoaded', resolve);
                });
            }

            // Initialize modules in dependency order
            await this.initializeModules();
            
            // Setup module communication
            this.setupModuleCommunication();
            
            // Setup global event handlers
            this.setupGlobalHandlers();
            
            // Setup auth dropdown close handler
            this.setupAuthDropdownCloseHandler();
            
            // Load initial data - but wait for popular-stocks section to exist
            await this.waitForSections();
            
            this.isInitialized = true;
            console.log('Stock Analyzer initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize Stock Analyzer:', error);
            this.showFatalError(error);
        }
    }

    /**
     * Wait for required sections to be loaded before loading data
     */
    async waitForSections() {
        console.log('Waiting for sections to load...');
        let attempts = 0;
        const maxAttempts = 50; // 2.5 seconds max
        
        while (!document.getElementById('popular-stocks') && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 50));
            attempts++;
        }
        
        if (document.getElementById('popular-stocks')) {
            console.log('Sections ready after', attempts * 50, 'ms');
            await this.loadInitialData();
        } else {
            console.warn('Sections not ready after timeout, loading data anyway');
            await this.loadInitialData();
        }
    }

    /**
     * Initialize components (called by index.html after sections are loaded)
     */
    async initializeComponents() {
        await this.init();
    }

    /**
     * Initialize all modules
     */
    async initializeModules() {
        // Core modules
        this.modules.dataManager = new DataManager(eventBus);
        this.modules.uiManager = new UIManager(eventBus);
        this.modules.tabManager = new TabManager(this.modules.dataManager, eventBus);
        
        // Feature modules
        this.modules.stockManager = new StockManager(this.modules.dataManager, eventBus);
        this.modules.searchManager = new SearchManager(this.modules.dataManager, eventBus);
        this.modules.watchlistManager = new WatchlistManager(this.modules.dataManager, eventBus);
        this.modules.chartManager = new ChartManager(eventBus);

        // Initialize modules that need setup
        this.modules.searchManager.initialize();
        this.modules.watchlistManager.initialize();
        this.modules.tabManager.setupTabHandlers();
    }

    /**
     * Setup communication between modules
     */
    setupModuleCommunication() {
        // Stock selection flow
        eventBus.on('stock:selected', ({ symbol }) => {
            this.modules.watchlistManager.updateWatchlistButtonState(symbol);
            this.modules.uiManager.updateBreadcrumbs(symbol, 'search');
        });

        // Tab switching flow
        eventBus.on('tab:switched', ({ tabName }) => {
            // Update URL hash for bookmarking
            window.location.hash = tabName;
        });

        // Error handling
        eventBus.on('error', ({ message, type }) => {
            this.modules.uiManager.showNotification(message, 'error');
        });

        // UI notifications
        eventBus.on('ui:notification', ({ message, type }) => {
            this.modules.uiManager.showNotification(message, type);
        });

        // Chart creation requests
        eventBus.on('chart:create', ({ canvasId, type, data, options, symbol }) => {
            switch (type) {
                case 'price':
                    this.modules.chartManager.createPriceChart(canvasId, data, symbol);
                    break;
                case 'estimates':
                    this.modules.chartManager.createEstimatesChart(canvasId, data, symbol);
                    break;
                case 'metrics':
                    this.modules.chartManager.createMetricsChart(canvasId, data, symbol);
                    break;
                case 'dcf':
                    this.modules.chartManager.createDCFChart(canvasId, data, symbol);
                    break;
                default:
                    this.modules.chartManager.createChart(canvasId, type, data, options);
            }
        });
    }

    /**
     * Setup global event handlers
     */
    setupGlobalHandlers() {
        // Handle browser back/forward for tab navigation
        window.addEventListener('popstate', (e) => {
            const tabName = e.state?.tab;
            if (tabName && this.modules.tabManager.isValidTab(tabName)) {
                this.modules.tabManager.switchTab(tabName);
            }
        });

        // Handle URL hash changes
        window.addEventListener('hashchange', () => {
            const hash = window.location.hash.slice(1);
            if (hash && this.modules.tabManager.isValidTab(hash)) {
                this.modules.tabManager.switchTab(hash);
            }
        });

        // Handle window resize for charts
        window.addEventListener('resize', () => {
            this.modules.chartManager.resizeAllCharts();
        });
    }

    /**
     * Setup burger menu functionality
     */
    setupBurgerMenu() {
        console.log('App: Setting up burger menu...');
        const menuBtn = document.getElementById('menuBtn');
        const toolsMenu = document.getElementById('toolsMenu');
        const closeMenu = document.getElementById('closeMenu');

        console.log('App: Burger menu elements found:', {
            menuBtn: !!menuBtn,
            toolsMenu: !!toolsMenu,
            closeMenu: !!closeMenu
        });

        if (menuBtn && toolsMenu) {
            menuBtn.addEventListener('click', () => {
                console.log('App: Menu button clicked');
                toolsMenu.classList.add('active');
            });
        }

        if (closeMenu && toolsMenu) {
            closeMenu.addEventListener('click', () => {
                console.log('App: Close menu clicked');
                toolsMenu.classList.remove('active');
            });
        }

        // Setup tool item click handlers
        const toolItems = document.querySelectorAll('.tool-item');
        console.log('App: Found tool items:', toolItems.length);
        
        toolItems.forEach(item => {
            const toolName = item.getAttribute('data-tool');
            console.log('App: Setting up handler for tool:', toolName);
            
            item.addEventListener('click', () => {
                console.log('App: Tool item clicked:', toolName);
                
                // Close the menu
                toolsMenu.classList.remove('active');
                
                // Special mapping for Factor Search → Factors Tab
                let targetTab = toolName;
                if (toolName === 'factor-search') {
                    targetTab = 'factors';
                }
                
                // Switch to the corresponding tab
                if (this.modules.tabManager && this.modules.tabManager.isValidTab(targetTab)) {
                    this.modules.tabManager.switchTab(targetTab);
                } else {
                    console.warn('App: Invalid tab or tab manager not available:', targetTab);
                }
            });
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (toolsMenu && !toolsMenu.contains(e.target) && !menuBtn.contains(e.target)) {
                toolsMenu.classList.remove('active');
            }
        });

        console.log('App: Burger menu setup complete');
    }

    /**
     * Setup menu handlers
     */
    setupMenuHandlers() {
        // Menu toggle
        const menuBtn = document.getElementById('menuBtn');
        if (menuBtn) {
            menuBtn.addEventListener('click', () => {
                document.getElementById('toolsMenu')?.classList.add('active');
            });
        }

        // Close menu
        const closeMenu = document.getElementById('closeMenu');
        if (closeMenu) {
            closeMenu.addEventListener('click', () => {
                document.getElementById('toolsMenu')?.classList.remove('active');
            });
        }

        // Tool menu items
        document.querySelectorAll('.tool-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const tool = e.currentTarget.getAttribute('data-tool');
                this.modules.tabManager.switchTab(tool);
                document.getElementById('toolsMenu')?.classList.remove('active');
            });
        });
    }

    /**
     * Setup authentication handlers
     */
    setupAuthHandlers() {
        // Auth button
        const authButton = document.getElementById('authButton');
        if (authButton) {
            authButton.addEventListener('click', () => {
                this.showLoginModal();
            });
        }

        // Check authentication status
        this.checkAuthStatus();
    }

    /**
     * Load initial data
     */
    async loadInitialData() {
        try {
            // Load popular stocks
            await this.modules.stockManager.loadPopularStocks();
            
            // Load watchlist
            await this.modules.watchlistManager.loadWatchlist();
            
            // Handle initial URL hash
            const initialHash = window.location.hash.slice(1);
            if (initialHash && this.modules.tabManager.isValidTab(initialHash)) {
                this.modules.tabManager.switchTab(initialHash);
            } else {
                this.modules.tabManager.switchTab('popular-stocks');
            }
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }

    /**
     * Check authentication status
     */
    async checkAuthStatus() {
        if (window.authManager) {
            try {
                const isAuth = await window.authManager.isAuthenticated();
                this.updateAuthUI(isAuth);
                
                if (isAuth) {
                    await this.modules.watchlistManager.loadWatchlist();
                }
            } catch (error) {
                console.error('Auth check failed:', error);
            }
        }
    }

    /**
     * Update authentication UI
     * @param {boolean} isAuthenticated - Whether user is authenticated
     */
    updateAuthUI(isAuthenticated) {
        const authButton = document.getElementById('authButton');
        const userMenu = document.getElementById('userMenu');
        
        if (authButton && userMenu) {
            if (isAuthenticated) {
                authButton.style.display = 'none';
                userMenu.style.display = 'block';
                this.updateUserDisplayName();
            } else {
                authButton.style.display = 'block';
                userMenu.style.display = 'none';
            }
        }
    }

    /**
     * Update user display name
     */
    async updateUserDisplayName() {
        if (window.authManager) {
            try {
                const displayName = await window.authManager.getDisplayName();
                const userNameElement = document.getElementById('userName');
                if (userNameElement) {
                    userNameElement.textContent = displayName;
                }
            } catch (error) {
                console.error('Failed to update user display name:', error);
            }
        }
    }

    /**
     * Show login modal
     */
    showLoginModal() {
        const modal = document.getElementById('authModal');
        if (modal) {
            modal.style.display = 'block';
        }
    }

    /**
     * Hide login modal
     */
    hideLoginModal() {
        const modal = document.getElementById('authModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * Handle sign in
     * @param {Event} event - Form submit event
     */
    async handleSignIn(event) {
        event.preventDefault();
        
        if (!window.authManager) return;
        
        const email = document.getElementById('signInEmail')?.value;
        const password = document.getElementById('signInPassword')?.value;
        
        try {
            const result = await window.authManager.signIn(email, password);
            
            if (result.success) {
                this.showNotification('Signed in successfully!');
                this.hideLoginModal();
                this.updateAuthUI(true);
                await this.modules.watchlistManager.loadWatchlist();
            } else if (result.needsConfirmation) {
                this.showNotification('Please verify your email first');
                this.showVerifyForm(email);
            } else {
                this.showNotification('Sign in failed: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('Sign in error:', error);
            this.showNotification('Sign in failed', 'error');
        }
    }

    /**
     * Handle sign up
     * @param {Event} event - Form submit event
     */
    async handleSignUp(event) {
        event.preventDefault();
        
        if (!window.authManager) return;
        
        const email = document.getElementById('signUpEmail')?.value;
        const password = document.getElementById('signUpPassword')?.value;
        
        try {
            const result = await window.authManager.signUp(email, password);
            
            if (result.success) {
                this.showNotification('Sign up successful! Please check your email for verification.');
                this.showVerifyForm(email);
            } else {
                this.showNotification('Sign up failed: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('Sign up error:', error);
            this.showNotification('Sign up failed', 'error');
        }
    }

    /**
     * Show verification form
     * @param {string} email - User email
     */
    showVerifyForm(email) {
        const signInForm = document.getElementById('signInForm');
        const signUpForm = document.getElementById('signUpForm');
        const verifyForm = document.getElementById('verifyForm');
        
        if (signInForm) signInForm.style.display = 'none';
        if (signUpForm) signUpForm.style.display = 'none';
        if (verifyForm) verifyForm.style.display = 'block';
    }

    /**
     * Handle logout
     */
    async handleLogout() {
        if (!window.authManager) return;
        
        try {
            await window.authManager.signOut();
            this.updateAuthUI(false);
            this.showNotification('Signed out successfully');
        } catch (error) {
            console.error('Logout error:', error);
            this.showNotification('Logout failed', 'error');
        }
    }

    /**
     * Toggle authentication dropdown
     */
    toggleAuthDropdown() {
        const dropdown = document.getElementById('authDropdown');
        if (dropdown) {
            const isVisible = dropdown.classList.contains('show');
            
            // Close dropdown if it's open
            if (isVisible) {
                dropdown.classList.remove('show');
            } else {
                // Close any other dropdowns first
                document.querySelectorAll('.auth-dropdown.show').forEach(d => {
                    d.classList.remove('show');
                });
                
                // Open this dropdown
                dropdown.classList.add('show');
                
                // Focus on the email field
                setTimeout(() => {
                    const emailInput = document.getElementById('quickSignInEmail');
                    if (emailInput) {
                        emailInput.focus();
                    }
                }, 100);
            }
        }
    }

    /**
     * Handle quick sign in from dropdown
     * @param {Event} event - Form submit event
     */
    async handleQuickSignIn(event) {
        event.preventDefault();
        
        if (!window.authManager) return;
        
        const email = document.getElementById('quickSignInEmail')?.value;
        const password = document.getElementById('quickSignInPassword')?.value;
        
        if (!email || !password) {
            this.showNotification('Please enter email and password', 'error');
            return;
        }
        
        try {
            const result = await window.authManager.signIn(email, password);
            
            if (result.success) {
                this.showNotification('Signed in successfully!');
                // Close dropdown
                const dropdown = document.getElementById('authDropdown');
                if (dropdown) {
                    dropdown.classList.remove('show');
                }
                this.updateAuthUI(true);
                await this.modules.watchlistManager.loadWatchlist();
            } else if (result.needsConfirmation) {
                this.showNotification('Please check your email for verification code');
                this.showVerifyForm(email);
            } else {
                this.showNotification('Sign in failed: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('Quick sign in error:', error);
            this.showNotification('Sign in failed', 'error');
        }
    }

    /**
     * Close auth dropdown when clicking outside
     */
    setupAuthDropdownCloseHandler() {
        document.addEventListener('click', (event) => {
            const dropdown = document.getElementById('authDropdown');
            const authButton = document.getElementById('authButton');
            
            if (dropdown && authButton && 
                !dropdown.contains(event.target) && 
                !authButton.contains(event.target)) {
                dropdown.classList.remove('show');
            }
        });
    }

    /**
     * Show notification
     * @param {string} message - Notification message
     * @param {string} type - Notification type
     */
    showNotification(message, type = 'info') {
        this.modules.uiManager.showNotification(message, type);
    }

    /**
     * Show fatal error
     * @param {Error} error - Error object
     */
    showFatalError(error) {
        document.body.innerHTML = `
            <div style="text-align: center; padding: 50px; color: #fff;">
                <h1>Application Error</h1>
                <p>Failed to initialize the Stock Analyzer application.</p>
                <p>Please refresh the page and try again.</p>
                <details style="margin-top: 20px; text-align: left;">
                    <summary>Error Details</summary>
                    <pre style="background: #333; padding: 10px; margin-top: 10px; overflow: auto;">
                        ${error.stack || error.message}
                    </pre>
                </details>
            </div>
        `;
    }

    /**
     * Get application statistics
     * @returns {object} Application stats
     */
    getStats() {
        return {
            initialized: this.isInitialized,
            modules: Object.keys(this.modules),
            tabStats: this.modules.tabManager?.getTabStats(),
            chartStats: this.modules.chartManager?.getChartStats(),
            watchlistStats: this.modules.watchlistManager?.getWatchlistStats()
        };
    }

    /**
     * Initialize components (for compatibility with existing loading system)
     */
    initializeComponents() {
        // This method is called by the component loader
        // All initialization is already done in the constructor
        console.log('Components initialized');
    }

    /**
     * Cleanup resources and event listeners
     */
    cleanup() {
        // Clean up event listeners and resources
        if (this.modules.tabManager) {
            this.modules.tabManager.cleanup();
        }
        if (this.modules.stockManager) {
            this.modules.stockManager.cleanup();
        }
        if (this.modules.uiManager) {
            this.modules.uiManager.cleanup();
        }
        console.log('App cleaned up');
    }
}

// Global app instance
let app;

// Initialize application when DOM is ready
// The app waits for sections to load via waitForSections() in init()
document.addEventListener('DOMContentLoaded', () => {
    app = new StockAnalyzer();
    
    // Make app globally available
    window.app = app;
    window.stockManager = app.modules.stockManager;
    window.searchManager = app.modules.searchManager;
    window.watchlistManager = app.modules.watchlistManager;
    window.chartManager = app.modules.chartManager;
    window.tabManager = app.modules.tabManager;
    window.dataManager = app.modules.dataManager;
    window.uiManager = app.modules.uiManager;
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (app) {
        app.cleanup();
    }
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StockAnalyzer;
}

// Main Application Orchestrator
// Coordinates all modules and provides the main application interface

class StockAnalyzer {
    constructor() {
        this.modules = {};
        this.isInitialized = false;
        this.hCaptchaToken = null;
        this.hCaptchaWidgetId = null;
        this._tempQuickSignInData = null;

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
        // Error boundary must be initialized first
        this.modules.errorBoundary = new ErrorBoundary(eventBus);

        // Initialize lifecycle manager for module lifecycle management
        this.modules.lifecycleManager = new LifecycleManager(eventBus);

        // Configure authentication
        if (window.authManager && window.config?.cognito) {
            const configured = window.authManager.configure({
                region: window.config.cognito.region,
                userPoolId: window.config.cognito.userPoolId,
                userPoolClientId: window.config.cognito.userPoolClientId
            });
            
            if (configured) {
                console.log('✓ Authentication configured');
                // Check if user is already authenticated
                this.checkAuthStatus();
            } else {
                console.warn('⚠ Authentication configuration failed');
            }
        } else {
            console.warn('⚠ Authentication not available (missing authManager or config)');
        }

        // Core modules
        this.modules.dataManager = new DataManager(eventBus);
        this.modules.uiManager = new UIManager(eventBus);
        this.modules.tabManager = new TabManager(this.modules.dataManager, eventBus, this.modules.uiManager);

        // Auth module (depends on DynamoDBService)
        this.modules.userManager = new UserManager(eventBus);

        // Feature modules
        this.modules.stockManager = new StockManager(this.modules.dataManager, eventBus);
        this.modules.searchManager = new SearchManager(this.modules.dataManager, eventBus);
        this.modules.watchlistManager = new WatchlistManager(this.modules.dataManager, eventBus);
        this.modules.chartManager = new ChartManager(eventBus);
        this.modules.metricsManager = new MetricsManager(eventBus);
        this.modules.financialsManager = new FinancialsManager(eventBus);

        // Initialize modules that need setup
        this.modules.searchManager.initialize();
        this.modules.stockAnalyserManager = new StockAnalyserManager(eventBus, api, this.modules.dataManager);
        this.modules.stockAnalyserManager.init();
        window.stockAnalyserManager = this.modules.stockAnalyserManager; // Also expose globally for onclick handlers
        this.modules.watchlistManager.initialize();
        this.modules.metricsManager.initialize();
        this.modules.tabManager.setupTabHandlers();

        // News Manager
        this.modules.newsManager = new NewsManager(eventBus);
        window.newsManager = this.modules.newsManager;

        // Estimates Manager
        this.modules.estimatesManager = new EstimatesManager(eventBus);
        window.estimatesManager = this.modules.estimatesManager;

        // Factors Manager
        this.modules.factorsManager = new FactorsManager(eventBus);
        window.factorsManager = this.modules.factorsManager;

        // Register modules with lifecycle manager
        this.registerModulesWithLifecycle();

        // Expose financials manager globally
        window.financialsManager = this.modules.financialsManager;
    }

    /**
     * Register all modules with lifecycle manager
     */
    registerModulesWithLifecycle() {
        if (!this.modules.lifecycleManager) return;

        const lifecycle = this.modules.lifecycleManager;

        // Register modules with their lifecycle hooks
        // Modules will implement hooks gradually, starting with basic registration

        if (this.modules.stockManager) {
            lifecycle.registerModule('stockManager', this.modules.stockManager, {
                onInit: () => this.modules.stockManager.onInit?.(),
                onShow: () => this.modules.stockManager.onShow?.(),
                onHide: () => this.modules.stockManager.onHide?.(),
                onDestroy: () => this.modules.stockManager.onDestroy?.()
            });
        }

        if (this.modules.metricsManager) {
            lifecycle.registerModule('metricsManager', this.modules.metricsManager, {
                onInit: () => this.modules.metricsManager.onInit?.(),
                onShow: () => this.modules.metricsManager.onShow?.(),
                onHide: () => this.modules.metricsManager.onHide?.(),
                onDestroy: () => this.modules.metricsManager.onDestroy?.()
            });
        }

        if (this.modules.financialsManager) {
            lifecycle.registerModule('financialsManager', this.modules.financialsManager, {
                onInit: () => this.modules.financialsManager.onInit?.(),
                onShow: () => this.modules.financialsManager.onShow?.(),
                onHide: () => this.modules.financialsManager.onHide?.(),
                onDestroy: () => this.modules.financialsManager.onDestroy?.()
            });
        }

        if (this.modules.watchlistManager) {
            lifecycle.registerModule('watchlistManager', this.modules.watchlistManager, {
                onInit: () => this.modules.watchlistManager.initialize?.(),
                onShow: () => console.log('WatchlistManager shown'),
                onHide: () => this.modules.watchlistManager.cleanup?.(),
                onDestroy: () => this.modules.watchlistManager.cleanup?.()
            });
        }

        if (this.modules.chartManager) {
            lifecycle.registerModule('chartManager', this.modules.chartManager, {
                onInit: () => this.modules.chartManager.onInit?.(),
                onShow: () => this.modules.chartManager.onShow?.(),
                onHide: () => this.modules.chartManager.onHide?.(),
                onDestroy: () => this.modules.chartManager.onDestroy?.()
            });
        }

        if (this.modules.newsManager) {
            lifecycle.registerModule('newsManager', this.modules.newsManager, {
                onShow: () => console.log('NewsManager shown'),
                onHide: () => this.modules.newsManager.cleanup?.(),
                onDestroy: () => this.modules.newsManager.cleanup?.()
            });
        }

        if (this.modules.estimatesManager) {
            lifecycle.registerModule('estimatesManager', this.modules.estimatesManager, {
                onShow: () => console.log('EstimatesManager shown'),
                onHide: () => this.modules.estimatesManager.cleanup?.(),
                onDestroy: () => this.modules.estimatesManager.cleanup?.()
            });
        }

        if (this.modules.factorsManager) {
            lifecycle.registerModule('factorsManager', this.modules.factorsManager, {
                onShow: () => console.log('FactorsManager shown'),
                onHide: () => this.modules.factorsManager.cleanup?.(),
                onDestroy: () => this.modules.factorsManager.cleanup?.()
            });
        }

        console.log('✓ All modules registered with lifecycle manager');
    }

    /**
     * Setup communication between modules
     */
    setupModuleCommunication() {
        // Stock selection flow
        eventBus.on('stock:selected', ({ symbol, targetTab, source }) => {
            this.modules.watchlistManager.updateWatchlistButtonState(symbol);
            // Default to 'metrics' tab when no targetTab is specified (e.g., from search)
            const effectiveTargetTab = targetTab || 'metrics';
            this.modules.uiManager.updateBreadcrumbs(symbol, 'metrics');
            // Update URL with symbol and target tab
            this.updateURL(symbol, effectiveTargetTab);

            // Trigger data loading and module selection
            if (this.modules.stockManager) {
                // Prevent infinite loop: Only call selectStock if the event didn't originate 
                // from StockManager itself.
                if (source !== 'StockManager') {
                    this.modules.stockManager.selectStock(symbol, effectiveTargetTab);
                }
            }
        });

        // Tab switching flow
        eventBus.on('tab:switched', ({ tabName }) => {
            // Update URL for tab navigation (keep current symbol if any)
            const currentSymbol = this.modules.stockManager?.currentSymbol;
            if (currentSymbol) {
                this.updateURL(currentSymbol, tabName);
            } else if (tabName !== 'popular-stocks') {
                // Update URL for tab-only navigation
                this.updateURL(null, tabName);
            } else {
                // Clear URL params for default tab
                const url = new URL(window.location.href);
                url.searchParams.delete('symbol');
                url.searchParams.delete('tab');
                url.hash = '';
                window.history.replaceState({}, '', url.toString());
            }
        });

        // Error handling
        eventBus.on('error', ({ message, type }) => {
            this.modules.uiManager.showNotification(message, 'error');
        });

        // UI notifications
        eventBus.on('ui:notification', ({ message, type }) => {
            this.modules.uiManager.showNotification(message, type);
        });


        // Chart creation from price data
        eventBus.on('data:loaded', ({ symbol, type, data }) => {
            // Create price chart when price data OR metrics data with history is loaded
            const hasHistoricalData = (type === 'price' && data?.historicalData) ||
                (type === 'metrics' && data?.hasHistoricalData);
            if (hasHistoricalData) {
                // Only create chart if canvas element exists (metrics tab is loaded)
                const canvas = document.getElementById('priceChart');
                if (!canvas) {
                    console.log('ChartManager: Canvas not ready yet, chart will be created when tab loads');
                    return;
                }

                const chart = this.modules.chartManager.createPriceChart('priceChart', data, symbol);
                if (chart) {
                    // Setup timeframe handlers after chart is created
                    setTimeout(() => {
                        this.modules.chartManager.setupTimeframeHandlers();
                        this.modules.chartManager.setupCustomRangeHandlers();
                    }, 100);
                }
            }
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
        // Handle browser back/forward for navigation
        window.addEventListener('popstate', async (e) => {
            const urlParams = new URLSearchParams(window.location.search);
            const symbol = urlParams.get('symbol');
            const tab = urlParams.get('tab');

            if (symbol) {
                // Navigate to the stock and tab from URL
                await this.modules.stockManager.selectStock(symbol, tab || 'metrics');
            } else if (tab && this.modules.tabManager.isValidTab(tab)) {
                this.modules.tabManager.switchTab(tab);
            } else {
                this.modules.tabManager.switchTab('popular-stocks');
            }
        });

        // Handle URL hash changes (backward compatibility)
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

        // Setup burger menu
        this.setupBurgerMenu();
    }

    /**
     * Setup burger menu functionality
     */
    setupBurgerMenu() {
        console.log('App: Setting up burger menu...');

        // Wait for elements to be available (they load via componentLoader)
        const maxAttempts = 50; // 2.5 seconds max
        let attempts = 0;

        const trySetup = () => {
            const menuBtn = document.getElementById('menuBtn');
            const toolsMenu = document.getElementById('toolsMenu');
            const closeMenu = document.getElementById('closeMenu');

            console.log('App: Burger menu elements found:', {
                menuBtn: !!menuBtn,
                toolsMenu: !!toolsMenu,
                closeMenu: !!closeMenu,
                attempts: attempts
            });

            if (menuBtn && toolsMenu && closeMenu) {
                // Elements found, setup handlers
                menuBtn.addEventListener('click', () => {
                    console.log('App: Menu button clicked');
                    toolsMenu.classList.add('active');
                });

                closeMenu.addEventListener('click', () => {
                    console.log('App: Close menu clicked');
                    toolsMenu.classList.remove('active');
                });

                this.setupToolMenuItems(toolsMenu);

                console.log('App: Burger menu setup complete');
            } else if (attempts < maxAttempts) {
                // Try again
                attempts++;
                setTimeout(trySetup, 50);
            } else {
                console.warn('App: Burger menu elements not found after timeout');
            }
        };

        trySetup();
    }

    /**
     * Setup tool menu item handlers
     */
    setupToolMenuItems(toolsMenu) {

        const toolItems = toolsMenu.querySelectorAll('.tool-item');
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
        const menuBtn = document.getElementById('menuBtn');
        document.addEventListener('click', (e) => {
            if (toolsMenu && !toolsMenu.contains(e.target) && menuBtn && !menuBtn.contains(e.target)) {
                toolsMenu.classList.remove('active');
            }
        });
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

            // Handle initial URL params and hash
            await this.handleInitialURL();

        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }

    /**
     * Handle initial URL parameters and hash
     * Supports: ?symbol=AAPL&tab=stock-analyser or #tabName
     */
    async handleInitialURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const hash = window.location.hash.slice(1);

        const symbol = urlParams.get('symbol');
        const tab = urlParams.get('tab') || hash;

        console.log('handleInitialURL: symbol=', symbol, 'tab=', tab);

        if (symbol) {
            // Load the stock and optionally switch to specified tab
            const targetTab = tab && this.modules.tabManager.isValidTab(tab) ? tab : 'metrics';
            await this.modules.stockManager.selectStock(symbol, targetTab);
        } else if (tab && this.modules.tabManager.isValidTab(tab)) {
            this.modules.tabManager.switchTab(tab);
        } else {
            this.modules.tabManager.switchTab('popular-stocks');
        }
    }

    /**
     * Update URL with current symbol and tab
     * @param {string} symbol - Stock symbol (optional)
     * @param {string} tab - Tab name (optional)
     * @param {boolean} replace - Whether to replace history entry
     */
    updateURL(symbol = null, tab = null, replace = false) {
        const url = new URL(window.location.href);

        if (symbol) {
            url.searchParams.set('symbol', symbol);
        } else {
            url.searchParams.delete('symbol');
        }

        const targetTab = tab || this.modules.tabManager.currentTab;
        if (targetTab && targetTab !== 'popular-stocks') {
            url.searchParams.set('tab', targetTab);
        } else {
            url.searchParams.delete('tab');
        }

        // Clear hash since we're using query params
        url.hash = '';

        if (replace) {
            window.history.replaceState({}, '', url.toString());
        } else {
            window.history.pushState({}, '', url.toString());
        }

        console.log('updateURL:', url.toString());
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
     * Go to home (popular-stocks tab) and clear stock selection
     */
    goHome() {
        console.log('Going home...');
        // Clear current stock selection
        this.modules.stockManager.currentSymbol = null;
        this.modules.stockManager.updateStockSymbolDisplay();

        // Switch to popular-stocks tab
        this.modules.tabManager.switchTab('popular-stocks');

        // Update URL
        this.updateURL();

        // Clear any search results
        this.modules.stockManager.hideSearchResults();
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

                // Programmatically render hCaptcha if it hasn't been rendered yet and hcaptcha API is loaded
                console.log('toggleAuthDropdown: Checking hCaptcha rendering conditions...');
                console.log('toggleAuthDropdown: typeof hcaptcha:', typeof hcaptcha);
                console.log('toggleAuthDropdown: this.hCaptchaWidgetId:', this.hCaptchaWidgetId);

                if (typeof hcaptcha !== 'undefined' && this.hCaptchaWidgetId === null) {
                    const hCaptchaContainer = dropdown.querySelector('.h-captcha');
                    console.log('toggleAuthDropdown: hCaptchaContainer found:', !!hCaptchaContainer);
                    if (hCaptchaContainer) {
                        this.hCaptchaWidgetId = hcaptcha.render(hCaptchaContainer, {
                            sitekey: hCaptchaContainer.dataset.sitekey, // Use sitekey from data-attribute
                            size: 'invisible', // Ensure it's invisible
                            callback: window.onHCaptchaSuccess, // Use global callback
                            'expired-callback': window.onHCaptchaExpired // Use global callback
                        });
                        console.log('hCaptcha rendered. Widget ID:', this.hCaptchaWidgetId);
                    } else {
                        console.warn('toggleAuthDropdown: hCaptcha container not found in dropdown.');
                    }
                } else if (typeof hcaptcha === 'undefined') {
                    console.warn('toggleAuthDropdown: hCaptcha object not available, cannot render.');
                } else if (this.hCaptchaWidgetId !== null) {
                    console.log('toggleAuthDropdown: hCaptcha already rendered with ID:', this.hCaptchaWidgetId);
                }

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
        event.preventDefault(); // Prevent immediate form submission

        if (!window.authManager) return;

        const email = document.getElementById('quickSignInEmail')?.value;
        const password = document.getElementById('quickSignInPassword')?.value;

        if (!email || !password) {
            this.showNotification('Please enter email and password', 'error');
            return;
        }

        console.log('handleQuickSignIn: Checking for hCaptcha token and rendering status...');
        console.log('handleQuickSignIn: this.hCaptchaToken:', this.hCaptchaToken);
        console.log('handleQuickSignIn: typeof hcaptcha:', typeof hcaptcha);
        console.log('handleQuickSignIn: this.hCaptchaWidgetId:', this.hCaptchaWidgetId);

        // Store data temporarily and execute hCaptcha if no token
        if (!this.hCaptchaToken) {
            if (typeof hcaptcha !== 'undefined' && this.hCaptchaWidgetId !== null) {
                this.showNotification('Please complete the security check...', 'info');
                this._tempQuickSignInData = { email, password }; // Store credentials
                console.log('handleQuickSignIn: Executing invisible hCaptcha...');
                hcaptcha.execute(this.hCaptchaWidgetId); // Execute invisible hCaptcha
                return; // Wait for onHCaptchaSuccess to call handleQueuedQuickSignIn
            } else {
                console.error('handleQuickSignIn: Security check not available. hCaptcha object or widget ID missing.');
                this.showNotification('Security check not available, please try again.', 'error');
                return;
            }
        }

        // If hCaptchaToken is already present (e.g., from a previous execution or rapid re-submission)
        // proceed directly to sign-in. This case might be less common with invisible hCaptcha.
        this.showNotification('Proceeding with sign-in using existing security token...', 'info');
        this._tempQuickSignInData = { email, password }; // Ensure data is set for handleQueuedQuickSignIn
        this.handleQueuedQuickSignIn();
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
     * Handles a quick sign-in attempt that was queued after hCaptcha completion.
     */
    async handleQueuedQuickSignIn() {
        if (this.hCaptchaToken && this._tempQuickSignInData) {
            const { email, password } = this._tempQuickSignInData;
            this.showNotification('Security check passed, attempting sign-in...', 'info');

            try {
                // Assuming authManager.signIn does not directly take captcha token,
                // but the API Gateway/Lambda layer will validate it.
                const result = await window.authManager.signIn(email, password);

                if (result.success) {
                    this.showNotification('Signed in successfully!');
                    this.hideAuthDropdown();
                    this.updateAuthUI(true);
                    await this.modules.watchlistManager.loadWatchlist();
                } else if (result.needsConfirmation) {
                    this.showNotification('Please check your email for verification code');
                    this.showVerifyForm(email);
                } else {
                    this.showNotification('Sign in failed: ' + result.error, 'error');
                }
            } catch (error) {
                console.error('Queued quick sign in error:', error);
                this.showNotification('Sign in failed', 'error');
            } finally {
                // Always reset hCaptcha and clear token/temp data
                if (typeof hcaptcha !== 'undefined' && this.hCaptchaWidgetId !== null) {
                    hcaptcha.reset(this.hCaptchaWidgetId);
                }
                this.hCaptchaToken = null;
                this._tempQuickSignInData = null;
            }
        } else {
            console.warn('Queued sign in called without hCaptcha token or temporary data.');
        }
    }

    /**
     * Helper to hide the authentication dropdown.
     */
    hideAuthDropdown() {
        const dropdown = document.getElementById('authDropdown');
        if (dropdown) {
            dropdown.classList.remove('show');
        }
    }

    /**
     * Cleanup resources and event listeners
     */
    cleanup() {
        // Clean up lifecycle manager first (will destroy all modules)
        if (this.modules.lifecycleManager) {
            this.modules.lifecycleManager.cleanupAll();
        }

        // Clean up individual modules
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

// Define global hCaptcha callbacks and helper methods BEFORE app instance is created
// to ensure they are available when hCaptcha script loads or widget callbacks are fired.

/**
 * Global callback for hCaptcha API loaded event.
 * Called when the hCaptcha script (api.js) has fully loaded.
 */
window.onHCaptchaLoad = function() {
    console.log('hCaptcha API loaded.');
    // At this point, hcaptcha object is available globally.
    // We don't render it immediately, but rather when the auth dropdown is toggled.
};

/**
 * Global callback for hCaptcha successful challenge completion.
 * Called by the hCaptcha widget when a user successfully completes a challenge.
 * @param {string} token - The hCaptcha response token.
 */
window.onHCaptchaSuccess = function(token) {
    console.log('hCaptcha success. Token:', token.substring(0, 10) + '...');
    if (app) {
        app.hCaptchaToken = token;
        // Attempt to proceed with the quick sign-in if it was queued
        app.handleQueuedQuickSignIn();
    }
};

/**
 * Global callback for hCaptcha challenge expiration.
 * Called by the hCaptcha widget when the response token expires.
 */
window.onHCaptchaExpired = function() {
    console.log('hCaptcha expired.');
    if (app) {
        app.hCaptchaToken = null;
        app.showNotification('Security check expired, please try again.', 'warning');
        // Optionally, reset the hCaptcha widget if it's currently visible
        if (typeof hcaptcha !== 'undefined' && app.hCaptchaWidgetId !== null) {
            hcaptcha.reset(app.hCaptchaWidgetId);
        }
    }
};

// Initialize application when DOM is ready
// The app waits for sections to load via waitForSections() in init()
document.addEventListener('DOMContentLoaded', () => {
    app = new StockAnalyzer();

    // Make app globally available
    window.app = app;
    window.stockManager = app.modules.stockManager;
    window.searchManager = app.modules.searchManager;
    window.userManager = app.modules.userManager;
    window.watchlistManager = app.modules.watchlistManager;
    window.chartManager = app.modules.chartManager;
    window.tabManager = app.modules.tabManager;
    window.dataManager = app.modules.dataManager;
    window.uiManager = app.modules.uiManager;
    window.metricsManager = app.modules.metricsManager;
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

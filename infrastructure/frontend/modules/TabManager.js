// Tab Management Module
// Handles tab switching, content loading, and tab state management

class TabManager {
    constructor(dataManager, eventBus) {
        this.dataManager = dataManager;
        this.eventBus = eventBus;
        this.currentTab = 'popular-stocks';
        this.tabHistory = [];
        this.sectionsLoaded = new Set(); // Track which sections are loaded
        
        // Subscribe to tab events
        this.setupEventListeners();
    }

    /**
     * Setup event listeners for tab-related events
     */
    setupEventListeners() {
        console.log('TabManager: setupEventListeners called');
        
        // Subscribe to tab events
        this.eventBus.on('tab:switch', ({ tabName }) => {
            console.log('TabManager: Received tab:switch event for:', tabName);
            this.switchTab(tabName);
        });

        // Subscribe to stock selection events
        this.eventBus.on('stock:selected', ({ symbol }) => {
            console.log('TabManager: Received stock:selected event for:', symbol);
            // Auto-switch to metrics tab when stock is selected
            this.switchTab('metrics');
        });
    }

    /**
     * Switch to a specific tab
     * @param {string} tabName - Tab name to switch to
     */
    switchTab(tabName) {
        console.log('TabManager: switchTab called with:', tabName);
        
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(tab => {
            tab.classList.remove('active');
        });
        const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
            console.log('TabManager: Active tab set to:', tabName);
        } else {
            console.warn('TabManager: Tab element not found for:', tabName);
        }

        // Hide all content sections (but DON'T destroy them)
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });

        // Show the target section if it exists
        const targetSection = document.getElementById(tabName);
        if (targetSection) {
            targetSection.classList.add('active');
            console.log('TabManager: Section activated:', tabName);
        }

        // Track tab history (don't add duplicates)
        if (this.tabHistory[this.tabHistory.length - 1] !== tabName) {
            this.tabHistory.push(tabName);
            if (this.tabHistory.length > 10) this.tabHistory.shift();
        }

        this.currentTab = tabName;
        console.log('TabManager: Current tab set to:', tabName);

        // Load content for the specific tab (only if needed)
        console.log('TabManager: Loading content for tab:', tabName);
        this.loadTabContent(tabName);

        // Emit tab switched event
        this.eventBus.emit('tab:switched', { tabName, previousTab: this.tabHistory[this.tabHistory.length - 2] });
    }

    /**
     * Load a section dynamically
     * @param {string} sectionName - Section name
     */
    async loadSection(sectionName) {
        try {
            console.log('TabManager: Loading section:', sectionName);
            
            // Check if already loaded in DOM
            const existingSection = document.getElementById(sectionName);
            if (existingSection) {
                console.log('TabManager: Section already in DOM:', sectionName);
                return;
            }
            
            const response = await fetch(`sections/${sectionName}.html`);
            const html = await response.text();
            
            // Create a temporary div to parse the HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            
            // Get the section element
            const section = tempDiv.firstElementChild;
            if (section) {
                // Append to container without clearing
                const dynamicContainer = document.getElementById('dynamic-content-container');
                if (dynamicContainer) {
                    dynamicContainer.appendChild(section);
                    this.sectionsLoaded.add(sectionName);
                    console.log('TabManager: Section loaded:', sectionName);
                }
            }
        } catch (error) {
            console.error('TabManager: Failed to load section:', sectionName, error);
        }
    }

    /**
     * Load content for a specific tab
     * @param {string} tabName - Tab name
     */
    async loadTabContent(tabName) {
        console.log('TabManager: loadTabContent called for:', tabName);
        try {
            switch (tabName) {
                case 'analyst-estimates':
                    console.log('TabManager: Loading analyst-estimates data');
                    await this.loadSection('analyst-estimates');
                    await this.loadAnalystEstimatesData();
                    break;
                case 'metrics':
                    console.log('TabManager: Loading metrics data');
                    await this.loadSection('metrics');
                    await this.loadMetricsData();
                    break;
                case 'financials':
                    console.log('TabManager: Loading financials data');
                    await this.loadSection('financials');
                    await this.loadFinancialsData();
                    break;
                case 'factors':
                    console.log('TabManager: Loading factors data');
                    await this.loadSection('factors');
                    await this.loadFactorsData();
                    break;
                case 'stock-analyser':
                    console.log('TabManager: Loading stock-analyser data');
                    await this.loadSection('stock-analyser');
                    await this.loadStockAnalyserData();
                    break;
                case 'watchlist':
                    console.log('TabManager: Loading watchlist data');
                    await this.loadSection('watchlist');
                    await this.loadWatchlistData();
                    break;
                case 'popular-stocks':
                    console.log('TabManager: Loading popular-stocks data');
                    await this.loadSection('popular-stocks');
                    await this.loadPopularStocksData();
                    break;
                case 'news':
                    console.log('TabManager: Loading news data');
                    await this.loadSection('news');
                    await this.loadNewsData();
                    break;
                case 'retirement-calculator':
                    console.log('TabManager: Loading retirement-calculator');
                    await this.loadSection('retirement-calculator');
                    break;
                case 'real-estate-calculator':
                    console.log('TabManager: Loading real-estate-calculator');
                    await this.loadSection('real-estate-calculator');
                    break;
                case 'model-portfolio':
                    console.log('TabManager: Loading model-portfolio');
                    await this.loadSection('model-portfolio');
                    break;
                default:
                    console.warn('Unknown tab:', tabName);
            }
        } catch (error) {
            console.error(`Failed to load tab ${tabName}:`, error);
            this.eventBus.emit('tab:error', { tabName, error: error.message });
        }
    }

    /**
     * Load analyst estimates tab
     */
    async loadAnalystEstimatesTab() {
        console.log('TabManager: loadAnalystEstimatesTab called');
        try {
            const dynamicContentContainer = document.getElementById('dynamic-content-container');
            if (dynamicContentContainer) {
                dynamicContentContainer.classList.add('active');
            }

            await componentLoader.loadSection('analyst-estimates');
            
            // Load data if stock is selected
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'analyst-estimates');
            }
        } catch (error) {
            console.error('TabManager: Failed to load analyst-estimates tab:', error);
            // Don't switch back to popular-stocks on error
        }
    }

    /**
     * Load metrics tab
     */
    async loadMetricsTab() {
        console.log('TabManager: loadMetricsTab called');
        try {
            await componentLoader.loadSection('metrics');
            
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'metrics');
            }
        } catch (error) {
            console.error('TabManager: Failed to load metrics tab:', error);
        }
    }

    /**
     * Load financials tab
     */
    async loadFinancialsTab() {
        console.log('TabManager: loadFinancialsTab called');
        try {
            await componentLoader.loadSection('financials');
            
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'financials');
            }
        } catch (error) {
            console.error('TabManager: Failed to load financials tab:', error);
        }
    }

    /**
     * Load factors tab
     */
    async loadFactorsTab() {
        console.log('TabManager: loadFactorsTab called');
        try {
            await componentLoader.loadSection('factors');
            
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'factors');
            } else {
                // Load user factors when no stock selected
                await this.dataManager.loadStockData(null, 'user-factors');
            }
        } catch (error) {
            console.error('TabManager: Failed to load factors tab:', error);
        }
    }

    /**
     * Load stock analyser tab
     */
    async loadStockAnalyserTab() {
        await componentLoader.loadSection('stock-analyser');
        
        const currentSymbol = window.stockManager?.getCurrentSymbol();
        if (currentSymbol) {
            await this.dataManager.loadStockData(currentSymbol, 'stock-analyser');
        }
    }

    /**
     * Load watchlist tab
     */
    async loadWatchlistTab() {
        await componentLoader.loadSection('watchlist');
        await this.dataManager.loadWatchlist();
    }

    /**
     * Load popular stocks tab
     */
    async loadPopularStocksTab() {
        console.log('TabManager: loadPopularStocksTab called');
        try {
            console.log('TabManager: Loading popular-stocks section');
            await componentLoader.loadSection('popular-stocks');
            console.log('TabManager: Section loaded, now getting popular stocks data');
            
            // Load popular stocks through the stock manager
            if (window.stockManager) {
                await window.stockManager.loadPopularStocks();
            } else {
                await this.dataManager.getPopularStocks();
            }
            
            console.log('TabManager: Popular stocks tab loaded successfully');
        } catch (error) {
            console.error('TabManager: Failed to load popular stocks tab:', error);
            // Don't throw error to prevent tab switching loop
        }
    }

    /**
     * Load news tab
     */
    async loadNewsTab() {
        const dynamicContentContainer = document.getElementById('dynamic-content-container');
        if (dynamicContentContainer) {
            dynamicContentContainer.classList.add('active');
        }

        await componentLoader.loadSection('news');
        
        const currentSymbol = window.stockManager?.getCurrentSymbol();
        if (currentSymbol) {
            await this.dataManager.loadStockData(currentSymbol, 'news');
        } else {
            const newsContainer = document.getElementById('newsContainer');
            if (newsContainer) {
                newsContainer.innerHTML = '<p class="empty-message">Select a stock to view news</p>';
            }
        }
    }

    /**
     * Update tab buttons to show active state
     * @param {string} activeTabName - Name of active tab
     */
    updateTabButtons(activeTabName) {
        // Remove active class from all tabs
        document.querySelectorAll('.tab-btn').forEach(tab => {
            tab.classList.remove('active');
        });

        // Add active class to selected tab
        const activeTab = document.querySelector(`[data-tab="${activeTabName}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
        }
    }

    /**
     * Hide all content sections
     */
    hideAllSections() {
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
    }

    /**
     * Validate tab name
     * @param {string} tabName - Tab name to validate
     * @returns {boolean} Whether tab is valid
     */
    isValidTab(tabName) {
        const validTabs = [
            'metrics',
            'financials',
            'factors',
            'analyst-estimates',
            'news',
            'stock-analyser',
            'watchlist',
            'popular-stocks',
            'factor-search',
            'retirement-calculator',
            'model-portfolio',
            'real-estate-calculator'
        ];
        
        return validTabs.includes(tabName);
    }

    /**
     * Add tab to history
     * @param {string} tabName - Tab name to add
     */
    addToHistory(tabName) {
        // Don't add duplicate consecutive entries
        if (this.tabHistory[this.tabHistory.length - 1] !== tabName) {
            this.tabHistory.push(tabName);
            
            // Limit history to 20 entries
            if (this.tabHistory.length > 20) {
                this.tabHistory.shift();
            }
        }
    }

    /**
     * Go back to previous tab
     * @returns {boolean} Whether navigation was successful
     */
    goBack() {
        if (this.tabHistory.length > 1) {
            this.tabHistory.pop(); // Remove current tab
            const previousTab = this.tabHistory.pop(); // Get previous tab
            this.switchTab(previousTab);
            return true;
        }
        return false;
    }

    /**
     * Get current tab
     * @returns {string} Current tab name
     */
    getCurrentTab() {
        return this.currentTab;
    }

    /**
     * Get tab history
     * @returns {Array} Tab history array
     */
    getTabHistory() {
        return [...this.tabHistory];
    }

    /**
     * Clear tab history
     */
    clearHistory() {
        this.tabHistory = [this.currentTab];
    }

    /**
     * Get tab navigation info
     * @returns {object} Navigation info
     */
    getNavigationInfo() {
        return {
            current: this.currentTab,
            canGoBack: this.tabHistory.length > 1,
            history: this.getTabHistory(),
            validTabs: [
                'metrics',
                'financials',
                'factors',
                'analyst-estimates',
                'news',
                'stock-analyser',
                'watchlist',
                'popular-stocks'
            ]
        };
    }

    /**
     * Setup tab click handlers
     */
    setupTabHandlers() {
        console.log('TabManager: setupTabHandlers called');
        // Wait a moment for DOM to be ready
        setTimeout(() => {
            const tabs = document.querySelectorAll('.tab-btn');
            console.log('TabManager: Found', tabs.length, 'tab elements');
            
            if (tabs.length === 0) {
                console.warn('TabManager: No tab elements found - DOM may not be ready yet');
                // Try again after a short delay
                setTimeout(() => this.setupTabHandlers(), 100);
                return;
            }
            
            tabs.forEach((tab, index) => {
                const tabName = tab.getAttribute('data-tab');
                console.log(`TabManager: Setting up handler for tab ${index}: ${tabName}`);
                
                tab.addEventListener('click', (e) => {
                    console.log('TabManager: Tab clicked:', tabName);
                    if (tabName) {
                        this.switchTab(tabName);
                    }
                });
            });
        }, 100);
    }

    /**
     * Enable/disable tab based on conditions
     * @param {string} tabName - Tab name
     * @param {boolean} enabled - Whether tab should be enabled
     */
    setTabEnabled(tabName, enabled) {
        const tab = document.querySelector(`[data-tab="${tabName}"]`);
        if (tab) {
            if (enabled) {
                tab.classList.remove('disabled');
                tab.disabled = false;
            } else {
                tab.classList.add('disabled');
                tab.disabled = true;
            }
        }
    }

    /**
     * Show tab loading state
     * @param {string} tabName - Tab name
     */
    showTabLoading(tabName) {
        const tab = document.querySelector(`[data-tab="${tabName}"]`);
        if (tab) {
            tab.classList.add('loading');
        }
    }

    /**
     * Hide tab loading state
     * @param {string} tabName - Tab name
     */
    hideTabLoading(tabName) {
        const tab = document.querySelector(`[data-tab="${tabName}"]`);
        if (tab) {
            tab.classList.remove('loading');
        }
    }

    /**
     * Set tab badge
     * @param {string} tabName - Tab name
     * @param {string|number} badge - Badge content
     */
    setTabBadge(tabName, badge) {
        const tab = document.querySelector(`[data-tab="${tabName}"]`);
        if (tab) {
            // Remove existing badge
            const existingBadge = tab.querySelector('.tab-badge');
            if (existingBadge) {
                existingBadge.remove();
            }

            // Add new badge if provided
            if (badge) {
                const badgeElement = document.createElement('span');
                badgeElement.className = 'tab-badge';
                badgeElement.textContent = badge;
                tab.appendChild(badgeElement);
            }
        }
    }

    /**
     * Get tab statistics
     * @returns {object} Tab statistics
     */
    getTabStats() {
        const tabs = document.querySelectorAll('.tab-btn');
        const stats = {
            total: tabs.length,
            active: 0,
            disabled: 0,
            loading: 0
        };

        tabs.forEach(tab => {
            if (tab.classList.contains('active')) stats.active++;
            if (tab.classList.contains('disabled')) stats.disabled++;
            if (tab.classList.contains('loading')) stats.loading++;
        });

        return stats;
    }

    /**
     * Load popular stocks data
     */
    async loadPopularStocksData() {
        console.log('TabManager: loadPopularStocksData called');
        try {
            if (window.stockManager) {
                await window.stockManager.loadPopularStocks();
            }
        } catch (error) {
            console.error('TabManager: Failed to load popular stocks data:', error);
        }
    }

    /**
     * Load metrics data
     */
    async loadMetricsData() {
        console.log('TabManager: loadMetricsData called');
        try {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'metrics');
            }
            // Setup custom range handlers after metrics section is loaded
            if (window.chartManager && window.chartManager.setupCustomRangeHandlers) {
                setTimeout(() => {
                    window.chartManager.setupCustomRangeHandlers();
                    console.log('TabManager: Custom range handlers re-initialized');
                }, 100);
            }
            // Load saved metrics view preference
            if (window.metricsManager && window.metricsManager.loadViewPreference) {
                window.metricsManager.loadViewPreference();
            }
        } catch (error) {
            console.error('TabManager: Failed to load metrics data:', error);
        }
    }

    /**
     * Load financials data
     */
    async loadFinancialsData() {
        console.log('TabManager: loadFinancialsData called');
        try {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'financials');
            }
        } catch (error) {
            console.error('TabManager: Failed to load financials data:', error);
        }
    }

    /**
     * Load factors data
     */
    async loadFactorsData() {
        console.log('TabManager: loadFactorsData called');
        try {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'factors');
            } else {
                // No stock selected - just show empty factors or user factors if available
                console.log('TabManager: No stock selected for factors tab');
                // Emit event to show empty state
                this.eventBus.emit('data:loaded', { 
                    symbol: null, 
                    type: 'factors', 
                    data: { message: 'Select a stock to view factors' } 
                });
            }
        } catch (error) {
            console.error('TabManager: Failed to load factors data:', error);
        }
    }

    /**
     * Load stock analyser data
     */
    async loadStockAnalyserData() {
        console.log('TabManager: loadStockAnalyserData called');
        try {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'stock-analyser');
            }
        } catch (error) {
            console.error('TabManager: Failed to load stock analyser data:', error);
        }
    }

    /**
     * Load watchlist data
     */
    async loadWatchlistData() {
        console.log('TabManager: loadWatchlistData called');
        try {
            await this.dataManager.loadWatchlist();
        } catch (error) {
            console.error('TabManager: Failed to load watchlist data:', error);
        }
    }

    /**
     * Load news data
     */
    async loadNewsData() {
        console.log('TabManager: loadNewsData called');
        try {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'news');
            }
        } catch (error) {
            console.error('TabManager: Failed to load news data:', error);
        }
    }

    /**
     * Load analyst estimates data
     */
    async loadAnalystEstimatesData() {
        console.log('TabManager: loadAnalystEstimatesData called');
        try {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'analyst-estimates');
            }
        } catch (error) {
            console.error('TabManager: Failed to load analyst estimates data:', error);
        }
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        // Remove event listeners
        this.eventBus.off('tab:switch', this.switchTab);
        console.log('TabManager: Cleaned up');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TabManager;
} else {
    window.TabManager = TabManager;
}

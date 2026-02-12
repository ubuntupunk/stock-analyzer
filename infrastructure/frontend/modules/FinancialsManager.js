// Financials Management Module
// Handles financial statements tab switching and period selection

class FinancialsManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.currentStatement = 'income';
        this.currentPeriod = 'annual';
        this.setupEventListeners();
        this.setupSymbolInputHandlers();
    }

    /**
     * Setup event listeners for financials interactions
     */
    setupEventListeners() {
        // Listen for data loaded events
        this.eventBus.on('data:loaded', ({ type, data, symbol }) => {
            if (type === 'financials') {
                console.log('FinancialsManager: Financials data loaded, setting up UI');
                // Update company info in header
                this.updateCompanyInfo(symbol, data);
                // Use a small delay to ensure DOM is fully updated
                setTimeout(() => this.setupFinancialsUI(), 50);
            }
        });

        // Listen for tab switched events to reinitialize UI
        this.eventBus.on('tab:switched', ({ tabName }) => {
            if (tabName === 'financials') {
                console.log('FinancialsManager: Financials tab switched, setting up UI');
                // Wait a bit longer for section to load and render
                setTimeout(() => this.setupFinancialsUI(), 200);
            }
        });

        // Also listen for section loaded events
        this.eventBus.on('section:loaded', ({ sectionName }) => {
            if (sectionName === 'financials') {
                console.log('FinancialsManager: Financials section loaded, setting up UI');
                setTimeout(() => this.setupFinancialsUI(), 100);
            }
        });

        // Listen for period changes and reload data
        this.eventBus.on('financials:periodChanged', async ({ period }) => {
            console.log('FinancialsManager: Period changed to:', period);
            this.currentPeriod = period;
            
            // Reload financials data with new period
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol && window.dataManager) {
                console.log('FinancialsManager: Reloading financials with period:', period);
                await window.dataManager.loadStockData(currentSymbol, 'financials', period);
            }
        });

        // Listen for stock selected events to update company info
        this.eventBus.on('stock:selected', ({ symbol }) => {
            console.log('FinancialsManager: Stock selected:', symbol);
            this.updateCompanyInfo(symbol, null);
        });
    }

    /**
     * Update company info in the financials header
     * @param {string} symbol - Stock symbol
     * @param - Financial data (optional, contains company {object} data name)
     */
    updateCompanyInfo(symbol, data = null) {
        const symbolElement = document.getElementById('financialsSymbol');
        const nameElement = document.getElementById('financialsCompanyName');
        
        if (symbolElement) {
            symbolElement.textContent = symbol ? `(${symbol})` : '-';
        }
        
        if (nameElement) {
            // Try to get company name from various sources
            let companyName = '-';
            
            // 1. First try from the financial data directly (if provided)
            if (data) {
                if (data.company_name) {
                    companyName = data.company_name;
                } else if (data.meta && data.meta.company_name) {
                    companyName = data.meta.company_name;
                } else if (data.meta && data.meta.companyName) {
                    companyName = data.meta.companyName;
                }
            }
            
            // 2. Try to find in popular stocks
            if (companyName === '-' && window.stockManager && window.stockManager.popularStocks) {
                const stock = window.stockManager.popularStocks.find(s => s.symbol === symbol);
                if (stock && stock.name) {
                    companyName = stock.name;
                }
            }
            
            // 3. Try to get from metrics cache (this is where company_name is typically stored)
            if (companyName === '-' && window.dataManager && window.dataManager.getCachedData) {
                try {
                    const metricsCacheKey = `${symbol}:metrics`;
                    const metricsData = window.dataManager.getCachedData(metricsCacheKey);
                    if (metricsData) {
                        // Check various possible locations for company name
                        if (metricsData.companyName) {
                            companyName = metricsData.companyName;
                        } else if (metricsData.company_name) {
                            companyName = metricsData.company_name;
                        } else if (metricsData.meta && metricsData.meta.companyName) {
                            companyName = metricsData.meta.companyName;
                        } else if (metricsData.meta && metricsData.meta.company_name) {
                            companyName = metricsData.meta.company_name;
                        }
                    }
                } catch (e) {
                    console.warn('FinancialsManager: Error getting metrics cache:', e);
                }
            }
            
            // 4. Try to get from metrics manager or other tabs
            if (companyName === '-') {
                try {
                    // Try from StockAnalyserManager (has companyName element)
                    const analyserNameElement = document.querySelector('#stockAnalyserSection #companyName');
                    if (analyserNameElement && analyserNameElement.textContent && 
                        analyserNameElement.textContent !== 'Market Data' && 
                        analyserNameElement.textContent !== '-') {
                        companyName = analyserNameElement.textContent;
                    }
                } catch (e) {
                    // Ignore errors
                }
            }
            
            // 5. Try from MetricsManager if available
            if (companyName === '-' && window.metricsManager) {
                try {
                    const metricsCompanyNameElement = document.getElementById('companyName');
                    if (metricsCompanyNameElement && metricsCompanyNameElement.textContent && 
                        metricsCompanyNameElement.textContent !== 'Market Data' && 
                        metricsCompanyNameElement.textContent !== '-') {
                        companyName = metricsCompanyNameElement.textContent;
                    }
                } catch (e) {
                    // Ignore errors
                }
            }
            
            nameElement.textContent = companyName;
        }
    }

    /**
     * Setup symbol input handlers for the financials section
     */
    setupSymbolInputHandlers() {
        console.log('FinancialsManager: Setting up symbol input handlers');
        
        // Make the loadFinancialsSymbol function globally available
        window.loadFinancialsSymbol = () => {
            const input = document.getElementById('financialsSymbolInput');
            if (input && input.value.trim()) {
                const symbol = input.value.trim().toUpperCase();
                console.log('FinancialsManager: Loading financials for symbol:', symbol);
                if (window.stockManager) {
                    window.stockManager.selectStock(symbol, 'financials');
                } else if (window.app && window.app.modules && window.app.modules.stockManager) {
                    window.app.modules.stockManager.selectStock(symbol, 'financials');
                } else {
                    console.error('FinancialsManager: stockManager not available');
                }
            }
        };
        
        // Make the keydown handler globally available
        window.handleFinancialsSymbolKeydown = (event) => {
            if (event.key === 'Enter') {
                loadFinancialsSymbol();
            }
        };
        
        console.log('FinancialsManager: Symbol input handlers set up');
    }

    /**
     * Setup financials UI interactions (statement tabs and period selectors)
     */
    setupFinancialsUI() {
        console.log('=== FinancialsManager: setupFinancialsUI START ===');
        console.log('FinancialsManager: Current DOM state:', {
            financialsSection: !!document.getElementById('financials'),
            financialsTabs: !!document.querySelector('.financials-tabs'),
            incomeStatement: !!document.getElementById('incomeStatement'),
            balanceSheet: !!document.getElementById('balanceSheet'),
            cashFlowStatement: !!document.getElementById('cashFlowStatement')
        });
        
        // Setup statement tab buttons (Income, Balance, Cash Flow)
        // Using .financials-tabs .tab-btn to match the SCSS styling
        const statementTabs = document.querySelectorAll('.financials-tabs .tab-btn');
        console.log('FinancialsManager: Found', statementTabs.length, 'statement tabs');
        
        if (statementTabs.length === 0) {
            console.warn('FinancialsManager: No statement tabs found! Available classes:', 
                Array.from(document.querySelectorAll('[class*="tab"]')).map(el => el.className)
            );
        }
        
        statementTabs.forEach((tab, index) => {
            console.log(`FinancialsManager: Setting up tab ${index}:`, {
                dataStatement: tab.getAttribute('data-statement'),
                classList: Array.from(tab.classList),
                textContent: tab.textContent
            });
            
            // Remove existing listeners to prevent duplicates
            const newTab = tab.cloneNode(true);
            tab.parentNode.replaceChild(newTab, tab);
            
            newTab.addEventListener('click', (e) => {
                const statement = newTab.getAttribute('data-statement');
                console.log('FinancialsManager: Statement tab clicked:', statement);
                this.switchStatement(statement);
            });
        });

        // Setup period selectors
        console.log('FinancialsManager: Setting up period selectors');
        this.setupPeriodSelector('incomePeriod');
        this.setupPeriodSelector('balancePeriod');
        this.setupPeriodSelector('cashflowPeriod');
        
        console.log('=== FinancialsManager: setupFinancialsUI END ===');
    }

    /**
     * Setup period selector event listener
     * @param {string} selectorId - Period selector element ID
     */
    setupPeriodSelector(selectorId) {
        console.log(`FinancialsManager: Setting up period selector: ${selectorId}`);
        const selector = document.getElementById(selectorId);
        if (selector) {
            console.log(`FinancialsManager: Period selector ${selectorId} FOUND`);
            // Remove existing listeners
            const newSelector = selector.cloneNode(true);
            selector.parentNode.replaceChild(newSelector, selector);
            
            newSelector.addEventListener('change', (e) => {
                const period = e.target.value;
                console.log(`FinancialsManager: Period changed for ${selectorId}:`, period);
                this.currentPeriod = period;
                // In future, this could trigger a reload with quarterly data
                this.eventBus.emit('financials:periodChanged', { period });
            });
        } else {
            console.warn(`FinancialsManager: Period selector ${selectorId} NOT FOUND`);
        }
    }

    /**
     * Switch between financial statement views
     * @param {string} statement - Statement type (income, balance, cashflow)
     */
    switchStatement(statement) {
        console.log('=== FinancialsManager: switchStatement START ===');
        console.log('FinancialsManager: Switching to statement:', statement);
        
        // Update active tab button
        const allTabs = document.querySelectorAll('.financials-tabs .tab-btn');
        console.log('FinancialsManager: Found tabs to update:', allTabs.length);
        allTabs.forEach((tab, index) => {
            console.log(`FinancialsManager: Tab ${index} before:`, {
                dataStatement: tab.getAttribute('data-statement'),
                hasActive: tab.classList.contains('active')
            });
            tab.classList.remove('active');
        });
        
        const activeTab = document.querySelector(`.financials-tabs .tab-btn[data-statement="${statement}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
            console.log('FinancialsManager: Active tab set:', statement);
        } else {
            console.error('FinancialsManager: Active tab NOT FOUND for statement:', statement);
        }

        // Hide all statement content divs
        const allContent = document.querySelectorAll('.statement-content');
        console.log('FinancialsManager: Found content divs to hide:', allContent.length);
        allContent.forEach((content, index) => {
            console.log(`FinancialsManager: Content ${index} before:`, {
                id: content.id,
                hasActive: content.classList.contains('active'),
                display: window.getComputedStyle(content).display
            });
            content.classList.remove('active');
        });

        // Show selected statement content
        let contentId;
        switch (statement) {
            case 'income':
                contentId = 'incomeStatement';
                break;
            case 'balance':
                contentId = 'balanceSheet';
                break;
            case 'cashflow':
                contentId = 'cashFlowStatement';
                break;
        }

        console.log('FinancialsManager: Looking for content element:', contentId);
        const content = document.getElementById(contentId);
        if (content) {
            content.classList.add('active');
            console.log('FinancialsManager: Activated content:', contentId);
            console.log('FinancialsManager: Content after activation:', {
                hasActive: content.classList.contains('active'),
                display: window.getComputedStyle(content).display,
                classList: Array.from(content.classList)
            });
        } else {
            console.error('FinancialsManager: Content element NOT FOUND:', contentId);
            console.log('FinancialsManager: Available content elements:', 
                Array.from(document.querySelectorAll('.statement-content')).map(el => el.id)
            );
        }

        this.currentStatement = statement;
        console.log('FinancialsManager: Emitting financials:statementChanged event');
        this.eventBus.emit('financials:statementChanged', { statement });
        console.log('=== FinancialsManager: switchStatement END ===');
    }

    /**
     * Get current statement type
     * @returns {string} Current statement type
     */
    getCurrentStatement() {
        return this.currentStatement;
    }

    /**
     * Get current period
     * @returns {string} Current period
     */
    getCurrentPeriod() {
        return this.currentPeriod;
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        // Clear financial data caches
        this.financialData = null;
        this.statementCache?.clear();
        this.calculationCache?.clear();
        console.log('FinancialsManager: Cleaned up');
    }

    /**
     * Lifecycle: Initialize module (called once)
     */
    onInit() {
        console.log('[FinancialsManager] Initialized');
        this.isInitialized = true;
        // Initialize caches
        this.statementCache = new Map();
        this.calculationCache = new Map();
    }

    /**
     * Lifecycle: Show module (resume operations)
     */
    onShow() {
        console.log('[FinancialsManager] Shown - resuming operations');
        this.isVisible = true;
        this.calculationsActive = true;
        // Refresh financials if data is stale
        if (this.financialData && this.isDataStale()) {
            this.refreshFinancials();
        }
    }

    /**
     * Lifecycle: Hide module (pause operations)
     */
    onHide() {
        console.log('[FinancialsManager] Hidden - clearing caches to free memory');
        this.isVisible = false;
        this.calculationsActive = false;
        // Clear expensive caches to free memory
        this.clearExpensiveCaches();
    }

    /**
     * Lifecycle: Destroy module (complete cleanup)
     */
    onDestroy() {
        console.log('[FinancialsManager] Destroyed - complete cleanup');
        this.cleanup();
        this.statementCache?.clear();
        this.calculationCache?.clear();
        this.isInitialized = false;
    }

    /**
     * Clear expensive memory caches
     */
    clearExpensiveCaches() {
        // Clear calculation cache (can be recalculated)
        if (this.calculationCache) {
            this.calculationCache.clear();
        }
        // Keep statement cache for faster reload, but limit size
        if (this.statementCache && this.statementCache.size > 10) {
            // Keep only recent entries
            const entries = Array.from(this.statementCache.entries());
            this.statementCache.clear();
            entries.slice(-5).forEach(([key, value]) => {
                this.statementCache.set(key, value);
            });
        }
        console.log('[FinancialsManager] Expensive caches cleared');
    }

    /**
     * Check if financial data is stale
     */
    isDataStale() {
        if (!this.lastUpdate) return true;
        const staleThreshold = 5 * 60 * 1000; // 5 minutes
        return (Date.now() - this.lastUpdate) > staleThreshold;
    }

    /**
     * Refresh financials display
     */
    refreshFinancials() {
        if (this.currentSymbol) {
            this.loadFinancials(this.currentSymbol);
        }
    }

    /**
     * Get module state for lifecycle manager
     */
    getState() {
        return {
            currentSymbol: this.currentSymbol,
            isInitialized: this.isInitialized,
            isVisible: this.isVisible,
            calculationsActive: this.calculationsActive,
            cacheSizes: {
                statements: this.statementCache?.size || 0,
                calculations: this.calculationCache?.size || 0
            }
        };
    }

    /**
     * Set module state from lifecycle manager
     */
    setState(state) {
        console.log('[FinancialsManager] Restoring state:', state);
        if (state?.currentSymbol) {
            this.currentSymbol = state.currentSymbol;
        }
        this.isVisible = state?.isVisible ?? true;
        this.calculationsActive = state?.calculationsActive ?? true;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FinancialsManager;
} else {
    window.FinancialsManager = FinancialsManager;
}

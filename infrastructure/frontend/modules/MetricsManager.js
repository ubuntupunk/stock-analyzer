// Metrics Management Module
// Handles metrics display, grid/list view toggle, and data rendering

class MetricsManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.currentView = 'grid'; // 'grid' or 'list'
        this.setupSymbolInputHandlers();
    }

    /**
     * Initialize metrics manager
     */
    initialize() {
        this.setupViewToggleHandlers();
        this.setupEventListeners();
    }

    /**
     * Setup event listeners for metrics interactions
     */
    setupEventListeners() {
        // Listen for data loaded events
        this.eventBus.on('data:loaded', ({ type, data, symbol }) => {
            if (type === 'metrics') {
                console.log('MetricsManager: Metrics data loaded, updating display');
                this.updateCompanyInfo(symbol, data);
                this.updateMetricsDisplay(data);
                this.updatePriceIndicators(data);
            }
        });

        // Listen for stock selected events to update company info
        this.eventBus.on('stock:selected', ({ symbol }) => {
            console.log('MetricsManager: Stock selected:', symbol);
            this.updateCompanyInfo(symbol, null);
        });
    }

    /**
     * Update company info in the metrics header
     * @param {string} symbol - Stock symbol
     * @param {object} data - Metrics data (optional, contains company name)
     */
    updateCompanyInfo(symbol, data = null) {
        const symbolElement = document.getElementById('metricsSymbol');
        const nameElement = document.getElementById('metricsCompanyName');
        
        if (symbolElement) {
            symbolElement.textContent = symbol ? `(${symbol})` : '-';
        }
        
        if (nameElement) {
            // Try to get company name from various sources
            let companyName = '-';
            
            // 1. First try from the metrics data directly (if provided)
            if (data) {
                if (data.company_name) {
                    companyName = data.company_name;
                } else if (data.companyName) {
                    companyName = data.companyName;
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
            
            // 3. Try to get from cache
            if (companyName === '-' && window.dataManager && window.dataManager.getCachedData) {
                try {
                    const metricsCacheKey = `${symbol}:metrics`;
                    const metricsData = window.dataManager.getCachedData(metricsCacheKey);
                    if (metricsData) {
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
                    console.warn('MetricsManager: Error getting metrics cache:', e);
                }
            }
            
            nameElement.textContent = companyName;
        }
    }

    /**
     * Setup symbol input handlers for the metrics section
     */
    setupSymbolInputHandlers() {
        console.log('MetricsManager: Setting up symbol input handlers');
        
        // Make the loadMetricsSymbol function globally available
        window.loadMetricsSymbol = () => {
            const input = document.getElementById('metricsSymbolInput');
            if (input && input.value.trim()) {
                const symbol = input.value.trim().toUpperCase();
                console.log('MetricsManager: Loading metrics for symbol:', symbol);
                if (window.stockManager) {
                    window.stockManager.selectStock(symbol, 'metrics');
                } else if (window.app && window.app.modules && window.app.modules.stockManager) {
                    window.app.modules.stockManager.selectStock(symbol, 'metrics');
                } else {
                    console.error('MetricsManager: stockManager not available');
                }
            }
        };
        
        // Make the keydown handler globally available
        window.handleMetricsSymbolKeydown = (event) => {
            if (event.key === 'Enter') {
                loadMetricsSymbol();
            }
        };
        
        console.log('MetricsManager: Symbol input handlers set up');
    }

    /**
     * Setup view toggle button handlers
     */
    setupViewToggleHandlers() {
        const viewButtons = document.querySelectorAll('.metrics-view-toggle .view-btn');
        
        viewButtons.forEach(btn => {
            const viewMode = btn.getAttribute('data-view');
            
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.setMetricsView(viewMode);
            });
        });
    }

    /**
     * Set metrics view mode (grid or list)
     * @param {string} viewMode - View mode ('grid' or 'list')
     */
    setMetricsView(viewMode) {
        const gridContainer = document.getElementById('metricsGrid');
        const viewButtons = document.querySelectorAll('.metrics-view-toggle .view-btn');
        
        if (!gridContainer) {
            console.warn('MetricsManager: metricsGrid container not found');
            return;
        }

        // Update view toggle buttons
        viewButtons.forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-view') === viewMode) {
                btn.classList.add('active');
            }
        });

        // Update container class
        if (viewMode === 'list') {
            gridContainer.classList.remove('metrics-grid');
            gridContainer.classList.add('metrics-list');
        } else {
            gridContainer.classList.remove('metrics-list');
            gridContainer.classList.add('metrics-grid');
        }

        // Save view preference
        this.currentView = viewMode;
        
        // Store in localStorage for persistence
        try {
            localStorage.setItem('metricsView', viewMode);
        } catch (e) {
            // localStorage may be disabled
        }

        console.log('MetricsManager: View set to', viewMode);
        
        // Emit event
        this.eventBus.emit('metrics:viewChanged', { viewMode });
    }

    /**
     * Get current view mode
     * @returns {string} Current view mode
     */
    getCurrentView() {
        return this.currentView;
    }

    /**
     * Load saved view preference from localStorage
     */
    loadViewPreference() {
        try {
            const savedView = localStorage.getItem('metricsView');
            if (savedView && (savedView === 'grid' || savedView === 'list')) {
                this.setMetricsView(savedView);
            }
        } catch (e) {
            // localStorage may be disabled
        }
    }

    /**
     * Update a single metric value in the UI
     * @param {string} metricId - Element ID for the metric
     * @param {string|number} value - Value to display
     */
    updateMetric(metricId, value) {
        const element = document.getElementById(metricId);
        if (element) {
            element.textContent = value;
        }
    }

    /**
     * Update all metrics from data object
     * @param {object} data - Metrics data object (may contain nested metrics)
     */
    updateMetricsDisplay(data) {
        const metrics = data.metrics || data;
        
        const metricMappings = {
            'peRatio': this.formatValue(metrics.peRatio, 'ratio'),
            'marketCap': this.formatValue(metrics.marketCap, 'currency'),
            'priceToBook': this.formatValue(metrics.priceToBook, 'ratio'),
            'roe': this.formatValue(metrics.roe, 'percentage'),
            'debtToEquity': this.formatValue(metrics.debtToEquity, 'ratio'),
            'currentRatio': this.formatValue(metrics.currentRatio, 'ratio'),
            'revenueGrowth': this.formatValue(metrics.revenueGrowth, 'percentage'),
            'earningsGrowth': this.formatValue(metrics.earningsGrowth, 'percentage'),
            'epsGrowth': this.formatValue(metrics.epsGrowth, 'percentage'),
            'profitMargin': this.formatValue(metrics.profitMargin, 'percentage'),
            'operatingMargin': this.formatValue(metrics.operatingMargin, 'percentage'),
            'netMargin': this.formatValue(metrics.netMargin, 'percentage')
        };

        Object.entries(metricMappings).forEach(([metricId, formattedValue]) => {
            this.updateMetric(metricId, formattedValue);
        });
    }

    /**
     * Update price indicators
     * @param {object} data - Data containing price information
     */
    updatePriceIndicators(data) {
        if (data.currentPrice !== undefined) {
            const element = document.getElementById('atClosePrice');
            if (element) {
                element.textContent = this.formatValue(data.currentPrice, 'currency');
            }
        }
        if (data.afterHoursPrice) {
            const element = document.getElementById('afterHoursPrice');
            if (element) {
                element.textContent = this.formatValue(data.afterHoursPrice, 'currency');
            }
        }
    }

    /**
     * Format a value based on type
     * @param {*} value - Raw value
     * @param {string} type - Value type (currency, percentage, ratio)
     * @returns {string} Formatted value
     */
    formatValue(value, type = 'text') {
        if (value === null || value === undefined || value === 'N/A') {
            return '-';
        }

        switch (type) {
            case 'currency':
                return this.formatCurrency(value);
            case 'percentage':
                return this.formatPercentage(value);
            case 'ratio':
                return this.formatRatio(value);
            default:
                return String(value);
        }
    }

    /**
     * Format currency value
     * @param {number} value - Value to format
     * @returns {string} Formatted currency
     */
    formatCurrency(value) {
        if (value >= 1e12) {
            return '$' + (value / 1e12).toFixed(2) + 'T';
        } else if (value >= 1e9) {
            return '$' + (value / 1e9).toFixed(2) + 'B';
        } else if (value >= 1e6) {
            return '$' + (value / 1e6).toFixed(2) + 'M';
        } else if (value >= 1e3) {
            return '$' + (value / 1e3).toFixed(2) + 'K';
        }
        return '$' + value.toFixed(2);
    }

    /**
     * Format percentage value
     * @param {number} value - Value to format
     * @returns {string} Formatted percentage
     */
    formatPercentage(value) {
        const percentage = (value * 100).toFixed(2);
        return percentage + '%';
    }

    /**
     * Format ratio value
     * @param {number} value - Value to format
     * @returns {string} Formatted ratio
     */
    formatRatio(value) {
        return value.toFixed(2);
    }

    /**
     * Get metrics statistics
     * @returns {object} Metrics statistics
     */
    getMetricsStats() {
        return {
            currentView: this.currentView,
            container: !!document.getElementById('metricsGrid')
        };
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.currentView = 'grid';
        console.log('MetricsManager: Cleaned up');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MetricsManager;
} else {
    window.MetricsManager = MetricsManager;
}

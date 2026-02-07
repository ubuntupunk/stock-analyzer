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
                console.log('MetricsManager: Metrics data loaded for', symbol, data);
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
        // Use metrics if available, otherwise use data directly
        const rawMetrics = data.metrics || data;

        // Normalize keys (handle both snake_case from API and camelCase from transformations)
        const metrics = (window.dataManager && window.dataManager.snakeToCamel)
            ? window.dataManager.snakeToCamel(rawMetrics)
            : rawMetrics;

        console.log('MetricsManager: Updating display with normalized metrics:', metrics);

        const metricMappings = {
            'peRatio': this.formatValue(metrics.peRatio || metrics.pe_ratio, 'ratio'),
            'marketCap': this.formatValue(metrics.marketCap || metrics.market_cap, 'currency'),
            'priceToBook': this.formatValue(metrics.priceToBook || metrics.price_to_book, 'ratio'),
            'roe': this.formatValue(metrics.roe, 'percentage'),
            'debtToEquity': this.formatValue(metrics.debtToEquity || metrics.debt_to_equity, 'ratio'),
            'currentRatio': this.formatValue(metrics.currentRatio || metrics.current_ratio, 'ratio'),
            'revenueGrowth': this.formatValue(metrics.revenueGrowth || metrics.revenue_growth, 'percentage'),
            'earningsGrowth': this.formatValue(metrics.earningsGrowth || metrics.earnings_growth, 'percentage'),
            'epsGrowth': this.formatValue(metrics.epsGrowth || metrics.eps_growth, 'percentage'),
            'profitMargin': this.formatValue(metrics.profitMargin || metrics.profit_margin, 'percentage'),
            'operatingMargin': this.formatValue(metrics.operatingMargin || metrics.operating_margin, 'percentage'),
            'netMargin': this.formatValue(metrics.netMargin || metrics.net_margin, 'percentage')
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
        // Handle various key names for price and changes (handle both snake_case and camelCase)
        // Check for price in multiple locations (top level or inside metrics object)
        const metrics = data.metrics || data;

        const price = data.currentPrice !== undefined ? data.currentPrice :
            (data.current_price !== undefined ? data.current_price :
                (metrics.currentPrice !== undefined ? metrics.currentPrice :
                    (metrics.current_price !== undefined ? metrics.current_price : data.price)));

        const change = data.change !== undefined ? data.change :
            (data.change_amount !== undefined ? data.change_amount :
                (metrics.change !== undefined ? metrics.change : metrics.change_amount));

        const changePercent = data.changePercent !== undefined ? data.changePercent :
            (data.change_percent !== undefined ? data.change_percent :
                (metrics.changePercent !== undefined ? metrics.changePercent : metrics.change_percent));

        console.log('MetricsManager: Updating price indicators with:', { price, change, changePercent });

        if (price !== undefined && price !== null) {
            const element = document.getElementById('atClosePrice');
            if (element) {
                element.textContent = this.formatValue(price, 'currency');
            }
        }

        if (change !== undefined && changePercent !== undefined) {
            const changeElement = document.getElementById('metricsChange');
            if (changeElement) {
                const sign = change >= 0 ? '+' : '';
                changeElement.textContent = `${sign}${change.toFixed(2)} (${sign}${changePercent.toFixed(2)}%)`;

                // Set color class
                changeElement.classList.remove('positive', 'negative');
                if (change > 0) {
                    changeElement.classList.add('positive');
                } else if (change < 0) {
                    changeElement.classList.add('negative');
                }
            }
        }

        if (data.afterHoursPrice) {
            const element = document.getElementById('afterHoursPrice');
            if (element) {
                element.textContent = this.formatValue(data.afterHoursPrice, 'currency');
            }
            const afterHoursRow = document.querySelector('.metrics-after-hours');
            if (afterHoursRow) afterHoursRow.style.display = 'flex';
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

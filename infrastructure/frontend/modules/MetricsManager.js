// Metrics Management Module
// Handles metrics display, grid/list view toggle, and data rendering

class MetricsManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.currentView = 'grid'; // 'grid' or 'list'
    }

    /**
     * Initialize metrics manager
     */
    initialize() {
        this.setupViewToggleHandlers();
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
     * @param {object} metricsData - Metrics data object
     */
    updateAllMetrics(metricsData) {
        const metricMappings = {
            'peRatio': this.formatValue(metricsData.peRatio, 'ratio'),
            'marketCap': this.formatValue(metricsData.marketCap, 'currency'),
            'priceToBook': this.formatValue(metricsData.priceToBook, 'ratio'),
            'roe': this.formatValue(metricsData.roe, 'percentage'),
            'debtToEquity': this.formatValue(metricsData.debtToEquity, 'ratio'),
            'currentRatio': this.formatValue(metricsData.currentRatio, 'ratio'),
            'revenueGrowth': this.formatValue(metricsData.revenueGrowth, 'percentage'),
            'earningsGrowth': this.formatValue(metricsData.earningsGrowth, 'percentage'),
            'epsGrowth': this.formatValue(metricsData.epsGrowth, 'percentage'),
            'profitMargin': this.formatValue(metricsData.profitMargin, 'percentage'),
            'operatingMargin': this.formatValue(metricsData.operatingMargin, 'percentage'),
            'netMargin': this.formatValue(metricsData.netMargin, 'percentage')
        };

        Object.entries(metricMappings).forEach(([metricId, formattedValue]) => {
            this.updateMetric(metricId, formattedValue);
        });
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

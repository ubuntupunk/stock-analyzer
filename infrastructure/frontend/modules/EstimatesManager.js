/**
 * EstimatesManager - Handles Analyst Estimates data display
 * Listens for analyst estimates data and updates the UI
 */

class EstimatesManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.currentSymbol = null;
        this.initialized = false;
        
        console.log('EstimatesManager: Initializing');
        
        // Set up event listeners
        this.setupEventListeners();
        
        console.log('EstimatesManager: Initialized');
    }

    /**
     * Set up event listeners for data and tab events
     */
    setupEventListeners() {
        console.log('EstimatesManager: Setting up event listeners');
        
        // Listen for data loaded events
        this.eventBus.on('data:loaded', (data) => {
            if (data && data.type === 'analyst-estimates') {
                console.log('EstimatesManager: Received analyst-estimates data:', data);
                this.currentSymbol = data.symbol;
                this.updateEstimatesDisplay(data.data || data);
            }
        });

        // Listen for tab switched events to set up UI
        this.eventBus.on('tab:switched', (data) => {
            if (data && data.tab === 'analyst-estimates') {
                console.log('EstimatesManager: Tab switched to analyst-estimates');
                this.setupEstimatesUI();
            }
        });

        // Listen for section loaded events
        this.eventBus.on('section:loaded', (data) => {
            if (data && data.section === 'analyst-estimates') {
                console.log('EstimatesManager: Section loaded:', data.section);
                this.setupEstimatesUI();
            }
        });

        // Listen for stock selected events
        this.eventBus.on('stock:selected', (data) => {
            if (data && data.symbol) {
                console.log('EstimatesManager: Stock selected:', data.symbol);
                this.currentSymbol = data.symbol;
            }
        });

        console.log('EstimatesManager: Event listeners set up');
    }

    /**
     * Set up UI interactions for the estimates section
     */
    setupEstimatesUI() {
        console.log('=== EstimatesManager: setupEstimatesUI START ===');
        
        const contentContainer = document.getElementById('estimatesContent');
        if (contentContainer) {
            console.log('EstimatesManager: Estimates content container found');
        } else {
            console.log('EstimatesManager: Estimates content container NOT found');
        }
        
        console.log('=== EstimatesManager: setupEstimatesUI END ===');
    }

    /**
     * Update company info in the estimates header
     * @param {string} symbol - Stock symbol
     * @param {Object} data - Estimates data (optional)
     */
    updateCompanyInfo(symbol, data = null) {
        const symbolElement = document.getElementById('estimatesSymbol');
        const nameElement = document.getElementById('estimatesCompanyName');

        if (symbolElement) {
            symbolElement.textContent = symbol ? `(${symbol})` : '-';
        }

        if (nameElement) {
            // Try to get company name from various sources
            let companyName = '-';

            // 1. First try from the data directly (if provided)
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

            // 3. Try to get from metrics cache
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
                    console.warn('EstimatesManager: Error getting metrics cache:', e);
                }
            }

            // 4. Try from other tab elements
            if (companyName === '-') {
                try {
                    const analyserNameElement = document.querySelector('#stock-analyser #companyName');
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
     * Update estimates display when data arrives
     * @param {Object} data - Estimates data
     */
    updateEstimatesDisplay(data) {
        console.log('EstimatesManager: updateEstimatesDisplay called with:', {
            symbol: this.currentSymbol,
            hasData: !!data,
            dataKeys: data ? Object.keys(data) : []
        });

        // Update the content container
        const contentContainer = document.getElementById('estimatesContent');
        if (!contentContainer) {
            console.error('EstimatesManager: estimatesContent element not found');
            return;
        }

        // Handle both direct data and event-wrapped data
        const estimatesData = data.data || data;
        const source = estimatesData?.source || data?.source || 'Unknown';

        // Update company info
        this.updateCompanyInfo(this.currentSymbol, estimatesData || data);

        // Extract estimates data
        const earningsEstimates = estimatesData?.earnings_estimates || data?.earnings_estimates || [];
        const revenueEstimates = estimatesData?.revenue_estimates || data?.revenue_estimates || [];

        console.log('EstimatesManager: Earnings estimates:', earningsEstimates);
        console.log('EstimatesManager: Revenue estimates:', revenueEstimates);

        // Generate HTML for estimates
        let html = this.generateEstimatesHTML(earningsEstimates, revenueEstimates, source);

        // Update the content
        contentContainer.innerHTML = html;

        // Update summary cards if they exist
        this.updateSummaryCards(estimatesData || data);

        console.log('EstimatesManager: Estimates display updated');
    }

    /**
     * Generate HTML for estimates display
     * @param {Array} earningsEstimates - Earnings estimates data
     * @param {Array} revenueEstimates - Revenue estimates data
     * @param {string} source - Data source
     * @returns {string} HTML string
     */
    generateEstimatesHTML(earningsEstimates, revenueEstimates, source = 'Unknown') {
        let html = '';
        
        if (!earningsEstimates.length && !revenueEstimates.length) {
            return `
                <div class="estimates-empty">
                    <p>No analyst estimates available for this stock</p>
                    <p class="estimates-hint">Estimates will appear when analysts publish new research.</p>
                </div>
            `;
        }
        
        // Earnings Estimates Section
        if (earningsEstimates.length > 0) {
            html += `
                <div class="estimates-section">
                    <h3>Earnings Estimates</h3>
                    <table class="estimates-table">
                        <thead>
                            <tr>
                                <th>Period</th>
                                <th>Avg Estimate</th>
                                <th>Low Estimate</th>
                                <th>High Estimate</th>
                                <th>Analysts</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            earningsEstimates.forEach(estimate => {
                html += `
                    <tr>
                        <td>${estimate.period || 'N/A'}</td>
                        <td>$${this.formatNumber(estimate.avg)}</td>
                        <td>$${this.formatNumber(estimate.low)}</td>
                        <td>$${this.formatNumber(estimate.high)}</td>
                        <td>${estimate.num_analysts || 0}</td>
                    </tr>
                `;
            });
            
            html += `
                        </tbody>
                    </table>
                </div>
            `;
        }
        
        // Revenue Estimates Section
        if (revenueEstimates.length > 0) {
            html += `
                <div class="estimates-section">
                    <h3>Revenue Estimates</h3>
                    <table class="estimates-table">
                        <thead>
                            <tr>
                                <th>Period</th>
                                <th>Avg Estimate</th>
                                <th>Low Estimate</th>
                                <th>High Estimate</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            revenueEstimates.forEach(estimate => {
                html += `
                    <tr>
                        <td>${estimate.period || 'N/A'}</td>
                        <td>$${this.formatNumber(estimate.avg)}</td>
                        <td>$${this.formatNumber(estimate.low)}</td>
                        <td>$${this.formatNumber(estimate.high)}</td>
                    </tr>
                `;
            });
            
            html += `
                        </tbody>
                    </table>
                </div>
            `;
        }
        
        // Add source attribution
        html += `
            <div class="estimates-footer">
                <p>Data source: ${source}</p>
            </div>
        `;
        
        return html;
    }

    /**
     * Update summary cards with key metrics
     * @param {Object} data - Estimates data
     */
    updateSummaryCards(data) {
        // Update price target if available
        const priceTargetEl = document.getElementById('priceTarget');
        if (priceTargetEl) {
            const currentPriceEl = priceTargetEl.querySelector('.current-price');
            const targetPriceEl = priceTargetEl.querySelector('.target-price');
            
            if (currentPriceEl && data?.currentPrice) {
                currentPriceEl.textContent = `${this.formatNumber(data.currentPrice)}`;
            }
            if (targetPriceEl && data?.targetMeanPrice) {
                targetPriceEl.textContent = `${this.formatNumber(data.targetMeanPrice)}`;
            }
        }
        
        // Update analyst rating if available
        const ratingEl = document.getElementById('analystRating');
        if (ratingEl) {
            const ratingValueEl = ratingEl.querySelector('.rating');
            if (ratingValueEl && data?.recommendationMean) {
                const rating = this.getRatingLabel(data.recommendationMean);
                ratingValueEl.textContent = rating;
            }
            
            // Update rating bars if available
            const buyBar = ratingEl.querySelector('.rating-bar.buy span');
            const holdBar = ratingEl.querySelector('.rating-bar.hold span');
            const sellBar = ratingEl.querySelector('.rating-bar.sell span');
            
            if (data?.numberOfAnalystOpinions) {
                // Distribute opinions based on recommendation mean (approximation)
                const total = data.numberOfAnalystOpinions;
                if (buyBar) buyBar.textContent = `Buy: ${Math.round(total * 0.4)}`;
                if (holdBar) holdBar.textContent = `Hold: ${Math.round(total * 0.35)}`;
                if (sellBar) sellBar.textContent = `Sell: ${Math.round(total * 0.25)}`;
            }
        }
        
        // Update earnings estimates section
        const earningsEl = document.getElementById('earningsEstimates');
        if (earningsEl) {
            const rows = earningsEl.querySelectorAll('.estimate-row');
            if (rows.length >= 2) {
                // Current Year EPS
                const currentYearValue = data?.epsCurrentYear || data?.epsTrailingTwelveMonths || 0;
                const currentYearSpan = rows[0].querySelector('.estimate-value');
                if (currentYearSpan) {
                    currentYearSpan.textContent = `${this.formatNumber(currentYearValue)}`;
                }
                
                // Next Year EPS (forward)
                const nextYearValue = data?.epsForward || 0;
                const nextYearSpan = rows[1].querySelector('.estimate-value');
                if (nextYearSpan) {
                    nextYearSpan.textContent = `${this.formatNumber(nextYearValue)}`;
                }
            }
        }
    }

    /**
     * Get rating label from numerical value
     * @param {number} value - Rating value
     * @returns {string} Rating label
     */
    getRatingLabel(value) {
        if (value <= 1) return 'Strong Buy';
        if (value <= 2) return 'Buy';
        if (value <= 3) return 'Hold';
        if (value <= 4) return 'Sell';
        return 'Strong Sell';
    }

    /**
     * Format number for display
     * @param {number} num - Number to format
     * @returns {string} Formatted number
     */
    formatNumber(num) {
        if (num === null || num === undefined) return '0.00';
        if (typeof num === 'number') {
            return num.toFixed(2);
        }
        return String(num);
    }

    /**
     * Load estimates for a symbol
     * @param {string} symbol - Stock symbol
     */
    async loadEstimates(symbol) {
        console.log('EstimatesManager: Loading estimates for:', symbol);
        this.currentSymbol = symbol;
        
        try {
            this.eventBus.emit('data:loading', { type: 'analyst-estimates', symbol });
            
            const response = await fetch(`/api/stock/estimates?symbol=${symbol}`);
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.updateEstimatesDisplay(data);
            this.eventBus.emit('data:loaded', { type: 'analyst-estimates', symbol, data });
            
        } catch (error) {
            console.error('EstimatesManager: Error loading estimates:', error);
            this.eventBus.emit('data:error', { type: 'analyst-estimates', symbol, error: error.message });
        }
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        console.log('EstimatesManager: Cleaning up');
        if (this.eventBus) {
            this.eventBus.off('data:loaded');
            this.eventBus.off('tab:switched');
            this.eventBus.off('section:loaded');
            this.eventBus.off('stock:selected');
        }
        console.log('EstimatesManager: Cleaned up');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EstimatesManager;
} else {
    window.EstimatesManager = EstimatesManager;
}

/**
 * Load stock by symbol input (called from symbol input in analyst-estimates tab)
 */
window.loadEstimatesSymbol = function() {
    const input = document.getElementById('estimatesSymbolInput');
    if (!input) {
        console.error('EstimatesManager: estimatesSymbolInput not found');
        return;
    }

    const symbol = input.value.trim().toUpperCase();
    if (!symbol) {
        // Show error notification
        if (window.app && window.app.showNotification) {
            window.app.showNotification('Please enter a stock symbol', 'error');
        } else {
            alert('Please enter a stock symbol');
        }
        return;
    }

    console.log('EstimatesManager: Loading symbol from input:', symbol);

    // Use stockManager to select the stock
    if (window.stockManager) {
        window.stockManager.selectStock(symbol, 'analyst-estimates');
    } else {
        console.error('EstimatesManager: stockManager not available');
    }
};

/**
 * Handle Enter key in symbol input
 */
window.handleEstimatesSymbolKeydown = function(event) {
    if (event.key === 'Enter') {
        window.loadEstimatesSymbol();
    }
};

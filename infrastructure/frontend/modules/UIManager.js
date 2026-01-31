// UI Management Module
// Handles DOM updates, loading states, error displays, and UI state management

class UIManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.loadingStates = new Map();
        this.errorStates = new Map();
        this.charts = new Map();
        
        // Subscribe to data events
        this.setupEventListeners();
    }

    /**
     * Setup event listeners for data and error events
     */
    setupEventListeners() {
        // Data loading events
        this.eventBus.on('data:loading', ({ symbol, type }) => {
            this.showLoading(type, `Loading ${type} for ${symbol}...`);
        });

        this.eventBus.on('data:loaded', ({ symbol, type, data }) => {
            this.hideLoading(type);
            this.updateDataDisplay(type, data, symbol);
        });

        this.eventBus.on('data:error', ({ symbol, type, error }) => {
            this.hideLoading(type);
            this.showError(type, `Failed to load ${type}: ${error}`);
        });

        // Search events
        this.eventBus.on('search:loading', ({ query }) => {
            this.showSearchLoading();
        });

        this.eventBus.on('search:loaded', ({ query, results }) => {
            this.hideSearchLoading();
        });

        this.eventBus.on('search:error', ({ query, error }) => {
            this.hideSearchLoading();
            this.showNotification(`Search failed: ${error}`, 'error');
        });

        // Watchlist events
        this.eventBus.on('watchlist:loading', () => {
            this.showLoading('watchlist', 'Loading watchlist...');
        });

        this.eventBus.on('watchlist:loaded', ({ watchlist }) => {
            this.hideLoading('watchlist');
        });

        // DCF events
        this.eventBus.on('dcf:analyzing', () => {
            this.showDCFAnalyzing();
        });

        this.eventBus.on('dcf:analyzed', ({ results }) => {
            this.hideDCFAnalyzing();
        });
    }

    /**
     * Update element content safely
     * @param {string} id - Element ID
     * @param {string} content - Content to set
     */
    updateElement(id, content) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = content;
        }
    }

    /**
     * Update element HTML safely
     * @param {string} id - Element ID
     * @param {string} html - HTML content to set
     */
    updateElementHTML(id, html) {
        const element = document.getElementById(id);
        if (element) {
            element.innerHTML = html;
        }
    }

    /**
     * Show loading state for a section
     * @param {string} section - Section identifier
     * @param {string} message - Loading message
     */
    showLoading(section, message = 'Loading...') {
        this.loadingStates.set(section, true);
        
        const loadingElement = document.getElementById(`${section}-loading`);
        if (loadingElement) {
            loadingElement.style.display = 'block';
            loadingElement.textContent = message;
        }

        // Show loading in section container
        const sectionElement = document.getElementById(section);
        if (sectionElement) {
            sectionElement.classList.add('loading');
        }
    }

    /**
     * Hide loading state for a section
     * @param {string} section - Section identifier
     */
    hideLoading(section) {
        this.loadingStates.delete(section);
        
        const loadingElement = document.getElementById(`${section}-loading`);
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }

        const sectionElement = document.getElementById(section);
        if (sectionElement) {
            sectionElement.classList.remove('loading');
        }
    }

    /**
     * Show error message for a section
     * @param {string} section - Section identifier
     * @param {string} message - Error message
     */
    showError(section, message) {
        this.errorStates.set(section, message);
        
        const errorElement = document.getElementById(`${section}-error`);
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        }

        // Also show as notification
        this.showNotification(message, 'error');
    }

    /**
     * Hide error message for a section
     * @param {string} section - Section identifier
     */
    hideError(section) {
        this.errorStates.delete(section);
        
        const errorElement = document.getElementById(`${section}-error`);
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }

    /**
     * Show notification message
     * @param {string} message - Notification message
     * @param {string} type - Notification type (info, success, error, warning)
     */
    showNotification(message, type = 'info') {
        // Create notification element if it doesn't exist
        let notificationContainer = document.getElementById('notification-container');
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.id = 'notification-container';
            notificationContainer.className = 'notification-container';
            document.body.appendChild(notificationContainer);
        }

        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        notificationContainer.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

    /**
     * Update data display based on type
     * @param {string} type - Data type
     * @param {*} data - Data to display
     * @param {string} symbol - Stock symbol
     */
    updateDataDisplay(type, data, symbol) {
        switch (type) {
            case 'metrics':
                this.updateMetricsDisplay(data);
                break;
            case 'financials':
                this.updateFinancialsDisplay(data, symbol);
                break;
            case 'analyst-estimates':
                this.updateEstimatesDisplay(data, symbol);
                break;
            case 'stock-analyser':
                this.updateStockAnalyserDisplay(data, symbol);
                break;
            case 'factors':
                this.updateFactorsDisplay(data, symbol);
                break;
            case 'news':
                this.updateNewsDisplay(data, symbol);
                break;
        }
    }

    /**
     * Update metrics display
     * @param {object} metrics - Metrics data
     */
    updateMetricsDisplay(metrics) {
        const fields = {
            'marketCap': Formatters.formatCurrency(metrics.marketCap),
            'revenue': Formatters.formatCurrency(metrics.revenue),
            'peRatio': Formatters.formatRatio(metrics.peRatio),
            'roe': Formatters.formatPercentage(metrics.roe),
            'debtToEquity': Formatters.formatRatio(metrics.debtToEquity),
            'currentRatio': Formatters.formatNumber(metrics.currentRatio),
            'revenueGrowth': Formatters.formatPercentage(metrics.revenueGrowth),
            'earningsGrowth': Formatters.formatPercentage(metrics.earningsGrowth),
            'profitMargin': Formatters.formatPercentage(metrics.profitMargin),
            'operatingMargin': Formatters.formatPercentage(metrics.operatingMargin),
            'netMargin': Formatters.formatPercentage(metrics.netMargin)
        };

        Object.entries(fields).forEach(([id, value]) => {
            this.updateElement(id, value || 'N/A');
        });
    }

    /**
     * Update financials display
     * @param {object} financials - Financials data
     * @param {string} symbol - Stock symbol
     */
    updateFinancialsDisplay(financials, symbol) {
        // Update stock symbol
        this.updateElement('stockSymbol', symbol);

        // Update financial statements tables
        this.updateFinancialsTable('incomeData', financials.income_statement || []);
        this.updateFinancialsTable('balanceData', financials.balance_sheet || []);
        this.updateFinancialsTable('cashflowData', financials.cash_flow || []);

        // Update source and timestamp
        this.updateElement('financialsSource', financials.source || 'Unknown');
        this.updateElement('financialsUpdated', financials.timestamp || new Date().toLocaleString());
    }

    /**
     * Update financials table
     * @param {string} tableId - Table ID
     * @param {Array} data - Table data
     */
    updateFinancialsTable(tableId, data) {
        const tbody = document.getElementById(tableId);
        if (!tbody || !data || data.length === 0) {
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="5" class="loading">No financial data available</td></tr>';
            }
            return;
        }

        let html = '';
        data.slice(0, 5).forEach(statement => {
            const fiscalDate = statement.fiscal_date || statement.fiscalDateEnding || 'N/A';
            const revenue = Formatters.formatCurrency(statement.revenue || statement.totalRevenue || 0);
            const netIncome = Formatters.formatCurrency(statement.net_income || statement.netIncome || 0);
            const totalAssets = Formatters.formatCurrency(statement.total_assets || statement.totalAssets || 0);
            const operatingCashflow = Formatters.formatCurrency(statement.operating_cashflow || statement.operatingCashflow || 0);

            html += `
                <tr>
                    <td>${fiscalDate}</td>
                    <td>${revenue}</td>
                    <td>${netIncome}</td>
                    <td>${totalAssets}</td>
                    <td>${operatingCashflow}</td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    /**
     * Update estimates display
     * @param {object} estimates - Estimates data
     * @param {string} symbol - Stock symbol
     */
    updateEstimatesDisplay(estimates, symbol) {
        this.updateElement('stockSymbol', symbol);
        // Additional estimates UI updates would go here
    }

    /**
     * Update stock analyser display
     * @param {object} data - Stock analyser data
     * @param {string} symbol - Stock symbol
     */
    updateStockAnalyserDisplay(data, symbol) {
        if (data.price) {
            this.updateElement('currentPrice', Formatters.formatStockPrice(data.price.currentPrice));
            
            // Calculate price change if historical data available
            if (data.price.historicalData && Object.keys(data.price.historicalData).length > 1) {
                const dates = Object.keys(data.price.historicalData).sort();
                const latestPrice = data.price.currentPrice;
                const previousPrice = parseFloat(data.price.historicalData[dates[dates.length - 2]]['4. close']);
                const priceChange = ((latestPrice - previousPrice) / previousPrice * 100).toFixed(2);
                
                const priceChangeElement = document.getElementById('priceChange');
                if (priceChangeElement) {
                    priceChangeElement.textContent = `${priceChange > 0 ? '+' : ''}${priceChange}%`;
                    priceChangeElement.style.color = priceChange > 0 ? '#4ade80' : '#f87171';
                }
            }
        }

        // Update analyser header
        const analyserHeader = document.querySelector('#stock-analyser .analyser-header h2');
        if (analyserHeader) {
            analyserHeader.textContent = `Stock Analyser - ${symbol}`;
        }
    }

    /**
     * Update factors display
     * @param {object} factors - Factors data
     * @param {string} symbol - Stock symbol
     */
    updateFactorsDisplay(factors, symbol) {
        const factorsList = document.getElementById('factorsList');
        if (!factorsList) return;

        const basicFactors = [
            { name: 'P/E Ratio', value: factors.pe_ratio || 'N/A', status: this.evaluateFactor(factors.pe_ratio, 'pe') },
            { name: 'ROIC', value: factors.roic ? Formatters.formatPercentage(factors.roic) : 'N/A', status: this.evaluateFactor(factors.roic, 'roic') },
            { name: 'Revenue Growth', value: factors.revenue_growth ? Formatters.formatPercentage(factors.revenue_growth) : 'N/A', status: this.evaluateFactor(factors.revenue_growth, 'growth') },
            { name: 'Debt to Equity', value: factors.debt_to_equity || 'N/A', status: this.evaluateFactor(factors.debt_to_equity, 'debt') },
            { name: 'Current Ratio', value: factors.current_ratio || 'N/A', status: this.evaluateFactor(factors.current_ratio, 'current') },
            { name: 'Price to FCF', value: factors.price_to_fcf || 'N/A', status: this.evaluateFactor(factors.price_to_fcf, 'fcf') }
        ];

        let html = `
            <div class="stock-factors-header">
                <h3>Factors for ${symbol}</h3>
                <button class="add-factor-btn" onclick="app.showAddFactorDialog()">
                    <i class="fas fa-plus"></i> Add Custom Factor
                </button>
            </div>
            <div class="factors-grid">
        `;

        basicFactors.forEach(factor => {
            const statusClass = factor.status === 'good' ? 'factor-good' : factor.status === 'warning' ? 'factor-warning' : 'factor-poor';
            html += `
                <div class="factor-item ${statusClass}">
                    <div class="factor-name">${factor.name}</div>
                    <div class="factor-value">${factor.value}</div>
                    <div class="factor-status">${factor.status}</div>
                </div>
            `;
        });

        html += '</div>';
        factorsList.innerHTML = html;
    }

    /**
     * Update news display
     * @param {object} news - News data
     * @param {string} symbol - Stock symbol
     */
    updateNewsDisplay(news, symbol) {
        const container = document.getElementById('newsContainer');
        if (!container) return;

        if (!news || news.length === 0) {
            container.innerHTML = '<p class="empty-message">No news available for this stock</p>';
            return;
        }

        let html = news.map(article => `
            <div class="news-item">
                <div class="news-title">${article.title}</div>
                <div class="news-source">${article.source}</div>
                <div class="news-time">${Formatters.formatDate(article.publishedAt, 'time')}</div>
                <div class="news-summary">${article.summary}</div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    /**
     * Evaluate factor status
     * @param {*} value - Factor value
     * @param {string} type - Factor type
     * @returns {string} Factor status
     */
    evaluateFactor(value, type) {
        if (!value || value === 'N/A') return 'unknown';
        
        switch(type) {
            case 'pe':
                return value < 15 ? 'good' : value < 25 ? 'warning' : 'poor';
            case 'roic':
                return value > 0.15 ? 'good' : value > 0.10 ? 'warning' : 'poor';
            case 'growth':
                return value > 0.10 ? 'good' : value > 0.05 ? 'warning' : 'poor';
            case 'debt':
                return value < 0.5 ? 'good' : value < 1.0 ? 'warning' : 'poor';
            case 'current':
                return value > 2.0 ? 'good' : value > 1.5 ? 'warning' : 'poor';
            case 'fcf':
                return value < 15 ? 'good' : value < 25 ? 'warning' : 'poor';
            default:
                return 'unknown';
        }
    }

    /**
     * Show search loading state
     */
    showSearchLoading() {
        const searchInput = document.getElementById('stockSearch');
        if (searchInput) {
            searchInput.classList.add('loading');
        }
    }

    /**
     * Hide search loading state
     */
    hideSearchLoading() {
        const searchInput = document.getElementById('stockSearch');
        if (searchInput) {
            searchInput.classList.remove('loading');
        }
    }

    /**
     * Show DCF analyzing state
     */
    showDCFAnalyzing() {
        const analyseBtn = document.getElementById('analyseBtn');
        if (analyseBtn) {
            analyseBtn.textContent = 'Analyzing...';
            analyseBtn.disabled = true;
        }
    }

    /**
     * Hide DCF analyzing state
     */
    hideDCFAnalyzing() {
        const analyseBtn = document.getElementById('analyseBtn');
        if (analyseBtn) {
            analyseBtn.textContent = 'Analyse (Button)';
            analyseBtn.disabled = false;
        }
    }

    /**
     * Update breadcrumb navigation
     * @param {string} symbol - Stock symbol
     * @param {string} searchType - Search type
     */
    updateBreadcrumbs(symbol, searchType) {
        console.log('UIManager: updateBreadcrumbs called with:', { symbol, searchType });
        const breadcrumbElement = document.getElementById('breadcrumbPath');
        if (breadcrumbElement) {
            if (symbol) {
                breadcrumbElement.textContent = `Home > ${searchType} > ${symbol}`;
                console.log('UIManager: Breadcrumb updated to:', breadcrumbElement.textContent);
            } else {
                breadcrumbElement.textContent = 'Home > Popular Stocks';
                console.log('UIManager: Breadcrumb set to default');
            }
        }
    }

    /**
     * Update price indicators
     * @param {object} priceData - Price data
     */
    updatePriceIndicators(priceData) {
        this.updateElement('atClosePrice', Formatters.formatStockPrice(priceData.currentPrice));
        
        if (priceData.afterHoursPrice) {
            this.updateElement('afterHoursPrice', Formatters.formatStockPrice(priceData.afterHoursPrice));
        }
    }

    /**
     * Get loading state for a section
     * @param {string} section - Section identifier
     * @returns {boolean} Loading state
     */
    isLoading(section) {
        return this.loadingStates.get(section) || false;
    }

    /**
     * Get error message for a section
     * @param {string} section - Section name
     * @returns {string|null} Error message
     */
    getError(section) {
        return this.errorStates.get(section) || null;
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        // Clear error states
        this.errorStates.clear();
        console.log('UIManager: Cleaned up');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UIManager;
} else {
    window.UIManager = UIManager;
}

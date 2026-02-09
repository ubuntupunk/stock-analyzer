/**
 * StockAnalyserManager.js
 * Handles DCF analysis functionality for the Stock Analyser tab
 * Populates historical data, collects user assumptions, and displays analysis results
 */

class StockAnalyserManager {
    constructor(eventBus, api, dataManager) {
        this.eventBus = eventBus;
        this.api = api;
        this.dataManager = dataManager;
        this.currentSymbol = null;
        this.currentData = null;
        this.marketData = { marketCap: 0, revenue: 0, sharesOutstanding: 0 };
        this.initialized = false;
    }

    /**
     * Initialize the Stock Analyser manager
     */
    init() {
        console.log('StockAnalyserManager: Initializing');
        this.setupEventListeners();
        this.initialized = true;
        console.log('StockAnalyserManager: Initialized, currentSymbol:', this.currentSymbol);
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for stock selection to populate data
        this.eventBus.on('stock:selected', async ({ symbol }) => {
            console.log('StockAnalyserManager: Stock selected:', symbol);
            this.currentSymbol = symbol;
            await this.populateStockData(symbol);
        });

        // Listen for stock data loaded - populate if we're on stock-analyser tab
        this.eventBus.on('data:loaded', async ({ symbol, type, data }) => {
            if (type === 'stock-analyser') {
                console.log('StockAnalyserManager: data:loaded for stock-analyser:', symbol);
                this.currentSymbol = symbol;
                this.currentData = data;
                await this.populateHistoricalData(data);
            }
        });

        // Listen for tab switched to stock-analyser to load current stock data
        this.eventBus.on('tab:switched', async ({ tabName }) => {
            if (tabName === 'stock-analyser') {
                console.log('StockAnalyserManager: Tab switched to stock-analyser');
                // Get current symbol from stockManager
                const currentSymbol = window.stockManager?.getCurrentSymbol();
                console.log('StockAnalyserManager: Current symbol from stockManager:', currentSymbol);
                if (currentSymbol) {
                    this.currentSymbol = currentSymbol;
                    await this.populateStockData(currentSymbol);
                } else {
                    console.log('StockAnalyserManager: No current symbol, checking if data already loaded...');
                    // Data might already be loaded via dataManager.loadStockData
                    // Check if we have cached data
                    const cachedData = this.dataManager?.getCachedData?.(`${currentSymbol}:stock-analyser`);
                    if (cachedData) {
                        this.currentData = cachedData;
                        await this.populateHistoricalData(cachedData);
                    }
                }
            }
        });
    }

    /**
     * Populate stock data for analysis
     * @param {string} symbol - Stock symbol
     */
    async populateStockData(symbol) {
        try {
            console.log('StockAnalyserManager: Loading data for', symbol);

            // Use DataManager to load data (handles caching, throttling, error handling)
            // Expecting 'stock-analyser' type which returns { price, metrics, historicalData, combined: true }
            if (this.dataManager && this.dataManager.loadStockData) {
                const data = await this.dataManager.loadStockData(symbol, 'stock-analyser');
                this.currentData = data;
                await this.populateHistoricalData(data);
            } else {
                console.error('StockAnalyserManager: DataManager not available or loadStockData missing');
                throw new Error('DataManager not available');
            }
        } catch (error) {
            console.error('StockAnalyserManager: Failed to load stock data:', error);
            // Show error in UI
            const container = document.querySelector('#stock-analyser .analyser-content');
            if (container) {
                if (window.app && window.app.showNotification) {
                    window.app.showNotification(`Failed to load data for ${symbol}: ${error.message}`, 'error');
                }
            }
        }
    }

    /**
     * Populate historical data table from stock metrics
     * @param {Object} data - Stock data object
     * @param {number} retryCount - Number of retries attempted (internal use)
     */
    async populateHistoricalData(data, retryCount = 0) {
        const MAX_RETRIES = 10; // Max 10 retries = 1 second total

        // Only log on first attempt or every 5th retry to reduce console spam
        if (retryCount === 0 || retryCount % 5 === 0) {
            console.log(`StockAnalyserManager: Populating historical data (attempt ${retryCount + 1})`);
        }

        // Check if section is loaded
        const section = document.getElementById('stock-analyser');
        if (!section) {
            if (retryCount < MAX_RETRIES) {
                // Only log occasionally to reduce spam
                if (retryCount === 0 || retryCount === MAX_RETRIES - 1) {
                    console.log(`StockAnalyserManager: Section not yet loaded, will retry (${retryCount + 1}/${MAX_RETRIES})`);
                }
                // Retry after a short delay
                setTimeout(() => this.populateHistoricalData(data, retryCount + 1), 100);
            } else {
                console.warn('StockAnalyserManager: Section not loaded after max retries, giving up');
            }
            return;
        }

        // Extract metrics from data
        const metrics = data?.metrics || data || {};
        const priceData = data?.price || data || {};

        console.log('StockAnalyserManager: priceData:', priceData);
        console.log('StockAnalyserManager: metrics:', metrics);
        const currentPrice = priceData?.currentPrice || priceData?.price || metrics?.current_price || metrics?.price || 0;
        const priceChange = priceData?.changePercent || priceData?.change || 0;

        // Update header with company name
        const analyserHeader = document.querySelector('#stock-analyser .analyser-header h2');
        const companyName = metrics?.company_name || data?.symbol || this.currentSymbol;
        if (analyserHeader) {
            analyserHeader.textContent = `Stock Analyser - ${companyName}`;
        }

        // Update current price display
        const priceDisplay = document.getElementById('currentPrice');
        const priceChangeEl = document.getElementById('priceChange');

        if (priceDisplay) {
            priceDisplay.textContent = this.formatCurrency(currentPrice);
        }
        if (priceChangeEl) {
            const prefix = priceChange >= 0 ? '+' : '';
            priceChangeEl.textContent = `${prefix}${priceChange.toFixed(2)}%`;
            priceChangeEl.className = `price-change ${priceChange >= 0 ? 'positive' : 'negative'}`;
        }

        // Extract market data from metrics (backend uses snake_case)
        // Note: Yahoo Finance returns market_cap, shares_outstanding, revenue
        const marketCap = metrics?.market_cap || 0;
        const sharesOutstanding = metrics?.shares_outstanding ||
            metrics?.impliedSharesOutstanding ||
            (currentPrice > 0 ? Math.round(marketCap / currentPrice) : 0);
        const revenue = metrics?.revenue || metrics?.totalRevenue || 0;

        this.marketData = {
            marketCap: marketCap,
            revenue: revenue,
            sharesOutstanding: sharesOutstanding
        };

        console.log('StockAnalyserManager: marketData:', this.marketData);

        // Update market data display
        this.updateMarketInfoDisplay();

        // Historical metrics (1yr, 5yr, 10yr)
        // Yahoo Finance returns current values only, not historical
        const historicalData = {
            roic: {
                '1y': metrics?.roic || metrics?.roe || null,  // Use ROE as proxy for ROIC
                '5y': null,
                '10y': null
            },
            revenueGrowth: {
                '1y': metrics?.revenue_growth || null,
                '5y': null,
                '10y': null
            },
            profitMargin: {
                '1y': metrics?.profit_margin || null,
                '5y': null,
                '10y': null
            },
            fcfMargin: {
                '1y': metrics?.fcf_margin || null,
                '5y': null,
                '10y': null
            },
            peRatio: {
                '1y': metrics?.pe_ratio || null,
                '5y': null,
                '10y': null
            },
            pfcfRatio: {
                '1y': metrics?.pfcf_ratio || null,
                '5y': null,
                '10y': null
            }
        };

        // Populate Historical Data table (order matches HTML)
        this.populateTableCell('rev-growth-1y', historicalData.revenueGrowth['1y'], true);
        this.populateTableCell('rev-growth-5y', historicalData.revenueGrowth['5y'], true);
        this.populateTableCell('rev-growth-10y', historicalData.revenueGrowth['10y'], true);

        this.populateTableCell('profit-margin-1y', historicalData.profitMargin['1y'], true);
        this.populateTableCell('profit-margin-5y', historicalData.profitMargin['5y'], true);
        this.populateTableCell('profit-margin-10y', historicalData.profitMargin['10y'], true);

        this.populateTableCell('fcf-margin-1y', historicalData.fcfMargin['1y'], true);
        this.populateTableCell('fcf-margin-5y', historicalData.fcfMargin['5y'], true);
        this.populateTableCell('fcf-margin-10y', historicalData.fcfMargin['10y'], true);

        this.populateTableCell('roic-1y', historicalData.roic['1y'], true);
        this.populateTableCell('roic-5y', historicalData.roic['5y'], true);
        this.populateTableCell('roic-10y', historicalData.roic['10y'], true);

        this.populateTableCell('pe-1y', historicalData.peRatio['1y'], false);
        this.populateTableCell('pe-5y', historicalData.peRatio['5y'], false);
        this.populateTableCell('pe-10y', historicalData.peRatio['10y'], false);

        this.populateTableCell('pfcf-1y', historicalData.pfcfRatio['1y'], false);
        this.populateTableCell('pfcf-5y', historicalData.pfcfRatio['5y'], false);
        this.populateTableCell('pfcf-10y', historicalData.pfcfRatio['10y'], false);

        // Store current price for analysis
        this.currentPrice = currentPrice;

        // Update market info display
        this.updateMarketInfoDisplay();

        console.log('StockAnalyserManager: Historical data populated');
    }

    /**
     * Update market info display with current market data
     */
    updateMarketInfoDisplay() {
        const companyNameEl = document.getElementById('companyName');
        const marketCapEl = document.getElementById('marketCap');
        const sharesOutstandingEl = document.getElementById('sharesOutstanding');
        const baseRevenueEl = document.getElementById('baseRevenue');

        // Update company name in market data section
        const metrics = this.currentData?.metrics || this.currentData || {};
        const companyName = metrics?.company_name || this.currentSymbol;
        if (companyNameEl) {
            companyNameEl.textContent = companyName || 'Market Data';
        }

        if (marketCapEl && this.marketData?.marketCap) {
            marketCapEl.textContent = this.formatLargeNumber(this.marketData.marketCap);
        }

        if (sharesOutstandingEl && this.marketData?.sharesOutstanding) {
            sharesOutstandingEl.textContent = this.formatLargeNumber(this.marketData.sharesOutstanding) + ' shares';
        }

        if (baseRevenueEl && this.marketData?.revenue) {
            baseRevenueEl.textContent = this.formatLargeNumber(this.marketData.revenue);
        }
    }

    /**
     * Format large numbers (market cap, shares, revenue)
     * @param {number} value - Number to format
     * @returns {string} Formatted string
     */
    formatLargeNumber(value) {
        if (!value || isNaN(value)) return '—';

        if (value >= 1.0e+12) {
            return '$' + (value / 1.0e+12).toFixed(2) + 'T';
        } else if (value >= 1.0e+9) {
            return '$' + (value / 1.0e+9).toFixed(2) + 'B';
        } else if (value >= 1.0e+6) {
            return '$' + (value / 1.0e+6).toFixed(2) + 'M';
        } else {
            return '$' + value.toFixed(2);
        }
    }

    /**
     * Populate a table cell with value
     * @param {string} id - Element ID
     * @param {number|null} value - Value to display
     * @param {boolean} isPercentage - Whether to format as percentage
     */
    populateTableCell(id, value, isPercentage) {
        const cell = document.getElementById(id);
        if (cell) {
            // Check for null, undefined, or NaN (0 is a valid value)
            if (value !== null && value !== undefined && !isNaN(value)) {
                cell.textContent = isPercentage ? `${(value * 100).toFixed(0)}%` : value.toFixed(2);
            } else {
                cell.textContent = '—';
            }
        }
    }

    /**
     * Get user assumptions from input fields
     * @returns {Object} User assumptions
     */
    getUserAssumptions() {
        const getInputValue = (id, defaultValue) => {
            const el = document.getElementById(id);
            return el ? parseFloat(el.value) || defaultValue : defaultValue;
        };

        return {
            revenueGrowth: {
                low: getInputValue('assumption-rev-growth-low', 3) / 100,
                mid: getInputValue('assumption-rev-growth-mid', 6) / 100,
                high: getInputValue('assumption-rev-growth-high', 9) / 100
            },
            profitMargin: {
                low: getInputValue('assumption-profit-margin-low', 8) / 100,
                mid: getInputValue('assumption-profit-margin-mid', 10) / 100,
                high: getInputValue('assumption-profit-margin-high', 12) / 100
            },
            fcfMargin: {
                low: getInputValue('assumption-fcf-margin-low', 6) / 100,
                mid: getInputValue('assumption-fcf-margin-mid', 9) / 100,
                high: getInputValue('assumption-fcf-margin-high', 12) / 100
            },
            discountRate: {
                low: getInputValue('assumption-discount-rate-low', 8) / 100,
                mid: getInputValue('assumption-discount-rate-mid', 10) / 100,
                high: getInputValue('assumption-discount-rate-high', 12) / 100
            },
            terminalGrowthRate: {
                low: getInputValue('assumption-terminal-growth-low', 2) / 100,
                mid: getInputValue('assumption-terminal-growth-mid', 3) / 100,
                high: getInputValue('assumption-terminal-growth-high', 4) / 100
            },
            desiredReturn: {
                low: getInputValue('assumption-desired-return-low', 8) / 100,
                mid: getInputValue('assumption-desired-return-mid', 10) / 100,
                high: getInputValue('assumption-desired-return-high', 12) / 100
            }
        };
    }

    /**
     * Run DCF analysis
     */
    async runAnalysis() {
        console.log('StockAnalyserManager: runAnalysis called', {
            currentSymbol: this.currentSymbol,
            currentPrice: this.currentPrice
        });

        if (!this.currentSymbol || !this.currentPrice) {
            console.error('StockAnalyserManager: No stock selected or price available');
            // Try to get price from display
            const priceDisplay = document.getElementById('currentPrice');
            if (priceDisplay && priceDisplay.textContent && priceDisplay.textContent !== '$0.00') {
                console.log('StockAnalyserManager: Found price in display, retrying...');
                // Price might be displayed but not stored, refresh data
                if (this.currentSymbol) {
                    await this.populateStockData(this.currentSymbol);
                }
            }
            return;
        }

        const yearsSelect = document.getElementById('yearsSelect');
        const yearsToProject = yearsSelect ? parseInt(yearsSelect.value) : 10;

        const assumptions = this.getUserAssumptions();
        console.log('StockAnalyserManager: User assumptions:', assumptions);

        const requestData = {
            currentPrice: this.currentPrice,
            assumptions: {
                revenueGrowth: assumptions.revenueGrowth,
                profitMargin: assumptions.profitMargin,
                fcfMargin: assumptions.fcfMargin,
                discountRate: assumptions.discountRate,
                terminalGrowthRate: assumptions.terminalGrowthRate,
                desiredReturn: assumptions.desiredReturn
            },
            yearsToProject: yearsToProject
        };

        console.log('StockAnalyserManager: Running DCF analysis', requestData);

        try {
            this.eventBus.emit('dcf:calculating');

            const results = await this.api.calculateDCF(requestData);

            console.log('StockAnalyserManager: DCF results:', results);
            this.displayResults(results);

            this.eventBus.emit('dcf:calculated', { results });
        } catch (error) {
            console.error('StockAnalyserManager: DCF calculation failed:', error);
            this.eventBus.emit('dcf:error', { error: error.message });

            // Fallback to local calculation
            console.log('StockAnalyserManager: Falling back to local calculation');
            const localResults = this.calculateDCFLocal(requestData);
            this.displayResults(localResults);
        }
    }

    /**
     * Local DCF calculation fallback
     * @param {Object} params - DCF parameters
     * @returns {Object} DCF results
     */
    calculateDCFLocal(params) {
        const { currentPrice, assumptions, yearsToProject } = params;

        // Estimate shares outstanding from current market cap (approximation)
        // This is a simplification - in production you'd have actual shares data
        const sharesOutstanding = 1000; // Mock value in millions

        const results = {};

        for (const scenario of ['low', 'mid', 'high']) {
            const revGrowthRate = assumptions.revenueGrowth[scenario];
            const profitMargin = assumptions.profitMargin[scenario];
            const fcfMargin = assumptions.fcfMargin[scenario];
            const discountRate = assumptions.discountRate[scenario];
            const terminalGrowth = assumptions.terminalGrowthRate[scenario];

            // Project cash flows
            const projectedFCF = [];
            const baseRevenue = 100; // Mock base revenue in millions

            for (let year = 1; year <= yearsToProject; year++) {
                const revenue = baseRevenue * Math.pow(1 + revGrowthRate, year);
                const netIncome = revenue * profitMargin;
                const fcf = revenue * fcfMargin;
                projectedFCF.push(fcf);
            }

            // Calculate present value of projected FCF
            let pvFCF = 0;
            for (let i = 0; i < projectedFCF.length; i++) {
                pvFCF += projectedFCF[i] / Math.pow(1 + discountRate, i + 1);
            }

            // Calculate terminal value
            const terminalFCF = projectedFCF[projectedFCF.length - 1] * (1 + terminalGrowth);
            const terminalValue = terminalFCF / (discountRate - terminalGrowth);
            const pvTerminal = terminalValue / Math.pow(1 + discountRate, yearsToProject);

            // Total enterprise value
            const enterpriseValue = pvFCF + pvTerminal;

            // Intrinsic value per share (simplified)
            const intrinsicValue = enterpriseValue / sharesOutstanding;

            // Expected return
            const expectedReturn = (intrinsicValue - currentPrice) / currentPrice;

            results[scenario] = {
                intrinsicValue: round(intrinsicValue, 2),
                expectedReturn: round(expectedReturn * 100, 2),
                discountedCashFlowValue: round(pvFCF, 2),
                terminalValue: round(pvTerminal, 2)
            };
        }

        results.currentPrice = currentPrice;
        return results;
    }

    /**
     * Display DCF analysis results
     * @param {Object} results - DCF results
     */
    displayResults(results) {
        console.log('StockAnalyserManager: displayResults called with:', results);

        if (!results) {
            console.error('StockAnalyserManager: No results to display');
            return;
        }

        // Multiple of Earnings Value (simplified - uses intrinsic value)
        const moeLow = document.getElementById('moeValueLow');
        const moeMid = document.getElementById('moeValueMid');
        const moeHigh = document.getElementById('moeValueHigh');

        console.log('StockAnalyserManager: moeLow element:', moeLow, 'results.low:', results.low);

        if (moeLow) moeLow.textContent = this.formatCurrency(results.low?.intrinsicValue || 0);
        if (moeMid) moeMid.textContent = this.formatCurrency(results.mid?.intrinsicValue || 0);
        if (moeHigh) moeHigh.textContent = this.formatCurrency(results.high?.intrinsicValue || 0);

        // Discounted Cash Flow Value
        const dcfLow = document.getElementById('dcfValueLow');
        const dcfMid = document.getElementById('dcfValueMid');
        const dcfHigh = document.getElementById('dcfValueHigh');

        if (dcfLow) dcfLow.textContent = this.formatCurrency(results.low?.discountedCashFlowValue || 0);
        if (dcfMid) dcfMid.textContent = this.formatCurrency(results.mid?.discountedCashFlowValue || 0);
        if (dcfHigh) dcfHigh.textContent = this.formatCurrency(results.high?.discountedCashFlowValue || 0);

        // Current Price Return
        const returnLow = document.getElementById('returnLow');
        const returnMid = document.getElementById('returnMid');
        const returnHigh = document.getElementById('returnHigh');

        const formatReturn = (value) => {
            const prefix = value >= 0 ? '+' : '';
            return `${prefix}${value.toFixed(1)}%`;
        };

        if (returnLow) {
            returnLow.textContent = formatReturn(results.low?.expectedReturn || 0);
            returnLow.className = (results.low?.expectedReturn || 0) >= 0 ? 'positive' : 'negative';
        }
        if (returnMid) {
            returnMid.textContent = formatReturn(results.mid?.expectedReturn || 0);
            returnMid.className = (results.mid?.expectedReturn || 0) >= 0 ? 'positive' : 'negative';
        }
        if (returnHigh) {
            returnHigh.textContent = formatReturn(results.high?.expectedReturn || 0);
            returnHigh.className = (results.high?.expectedReturn || 0) >= 0 ? 'positive' : 'negative';
        }
    }

    /**
     * Format number as currency
     * @param {number} value - Number to format
     * @returns {string} Formatted currency string
     */
    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    }

    /**
     * Reset analysis results
     */
    resetResults() {
        const resultCells = [
            'moeValueLow', 'moeValueMid', 'moeValueHigh',
            'dcfValueLow', 'dcfValueMid', 'dcfValueHigh',
            'returnLow', 'returnMid', 'returnHigh'
        ];

        resultCells.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = '—';
                el.className = '';
            }
        });
    }
}

// Helper function for rounding
function round(value, decimals) {
    return Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals);
}

// Global instance
window.stockAnalyserManager = null;

/**
 * Run DCF analysis (called from Analyze button)
 */
window.runDCFAnalysis = function () {
    if (window.stockAnalyserManager) {
        window.stockAnalyserManager.runAnalysis();
    } else {
        console.error('StockAnalyserManager: Not initialized');
    }
};

/**
 * Load stock by symbol input (called from symbol input in stock-analyser tab)
 */
window.loadAnalyserSymbol = function () {
    const input = document.getElementById('analyserSymbolInput');
    if (!input) {
        console.error('StockAnalyserManager: analyserSymbolInput not found');
        return;
    }

    const symbol = input.value.trim().toUpperCase();
            if (!symbol) {
                // Show error notification
                if (window.app && window.app.showNotification) {
                    window.app.showNotification('Please enter a stock symbol', 'error');
                }
                return;
            }
    console.log('StockAnalyserManager: Loading symbol from input:', symbol);

    // Use stockManager to select the stock and switch to stock-analyser tab
    if (window.stockManager) {
        window.stockManager.selectStock(symbol, 'stock-analyser');
    } else {
        console.error('StockAnalyserManager: stockManager not available');
    }
};

/**
 * Handle Enter key in symbol input
 */
window.handleAnalyserSymbolKeydown = function (event) {
    if (event.key === 'Enter') {
        window.loadAnalyserSymbol();
    }
};

/**
 * Extrapolate assumptions from historical data
 * Reads historical values and auto-fills Low/Mid/High assumptions
 */
window.extrapolateFromHistorical = function () {
    console.log('StockAnalyserManager: Extrapolating from historical data');

    // Helper to get cell value
    const getCellValue = (id) => {
        const cell = document.getElementById(id);
        if (!cell) return null;
        let text = cell.textContent.trim();
        if (text === '—' || text === '') return null;
        // Remove % sign and parse
        text = text.replace('%', '');
        const val = parseFloat(text);
        return isNaN(val) ? null : val / 100; // Convert percentage to decimal
    };

    // Helper to set input value
    const setInputValue = (id, value) => {
        const input = document.getElementById(id);
        if (input) {
            input.value = (value * 100).toFixed(1);
        }
    };

    // Get historical values (use 1y as base)
    const histRevGrowth = getCellValue('rev-growth-1y');
    const histProfitMargin = getCellValue('profit-margin-1y');
    const histFCFMargin = getCellValue('fcf-margin-1y');
    const histROIC = getCellValue('roic-1y');
    const histPE = getCellValue('pe-1y');
    const histPFCF = getCellValue('pfcf-1y');

    console.log('StockAnalyserManager: Historical values:', {
        revGrowth: histRevGrowth,
        profitMargin: histProfitMargin,
        fcfMargin: histFCFMargin,
        roic: histROIC,
        pe: histPE,
        pfcf: histPFCF
    });

    // Helper to calculate low/mid/high from a base value
    const calcRange = (base, type) => {
        if (base === null) {
            // Return defaults if no historical data
            if (type === 'growth') return { low: 0.03, mid: 0.06, high: 0.09 };
            if (type === 'margin') return { low: 0.08, mid: 0.10, high: 0.12 };
            return { low: 0.08, mid: 0.10, high: 0.12 };
        }

        if (type === 'growth') {
            // For growth rates: low = 70%, mid = 100%, high = 130% of historical
            return {
                low: Math.max(0, base * 0.70),
                mid: base,
                high: base * 1.30
            };
        } else {
            // For margins: low = 80%, mid = 100%, high = 120% of historical
            return {
                low: Math.max(0, base * 0.80),
                mid: base,
                high: Math.min(1, base * 1.20)
            };
        }
    };

    // Set Revenue Growth assumptions
    const revGrowthRange = calcRange(histRevGrowth, 'growth');
    setInputValue('assumption-rev-growth-low', revGrowthRange.low);
    setInputValue('assumption-rev-growth-mid', revGrowthRange.mid);
    setInputValue('assumption-rev-growth-high', revGrowthRange.high);

    // Set Profit Margin assumptions
    const profitMarginRange = calcRange(histProfitMargin, 'margin');
    setInputValue('assumption-profit-margin-low', profitMarginRange.low);
    setInputValue('assumption-profit-margin-mid', profitMarginRange.mid);
    setInputValue('assumption-profit-margin-high', profitMarginRange.high);

    // Set FCF Margin assumptions
    const fcfMarginRange = calcRange(histFCFMargin, 'margin');
    setInputValue('assumption-fcf-margin-low', fcfMarginRange.low);
    setInputValue('assumption-fcf-margin-mid', fcfMarginRange.mid);
    setInputValue('assumption-fcf-margin-high', fcfMarginRange.high);

    // Set Discount Rate (default: low=8%, mid=10%, high=12%)
    setInputValue('assumption-discount-rate-low', 0.08);
    setInputValue('assumption-discount-rate-mid', 0.10);
    setInputValue('assumption-discount-rate-high', 0.12);

    // Set Terminal Growth (default: low=2%, mid=3%, high=4%)
    setInputValue('assumption-terminal-growth-low', 0.02);
    setInputValue('assumption-terminal-growth-mid', 0.03);
    setInputValue('assumption-terminal-growth-high', 0.04);

    // Set Desired Return (default: low=8%, mid=10%, high=12%)
    setInputValue('assumption-desired-return-low', 0.08);
    setInputValue('assumption-desired-return-mid', 0.10);
    setInputValue('assumption-desired-return-high', 0.12);

    // Show notification
    if (window.app && window.app.showNotification) {
        window.app.showNotification('Assumptions auto-filled from historical data', 'success');
    }

    console.log('StockAnalyserManager: Extrapolation complete');
};

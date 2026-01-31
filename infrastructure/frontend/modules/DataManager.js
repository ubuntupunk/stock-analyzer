// Data Management Module
// Handles API calls, caching, error handling, and data transformation

class DataManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
        this.retryAttempts = 3;
        this.retryDelay = 1000; // 1 second
    }

    /**
     * Load stock data for a specific tab/type
     * @param {string} symbol - Stock symbol
     * @param {string} type - Data type (metrics, financials, etc.)
     * @returns {Promise} Data promise
     */
    async loadStockData(symbol, type) {
        const cacheKey = `${symbol}:${type}`;
        
        // Check cache first
        const cachedData = this.getCachedData(cacheKey);
        if (cachedData) {
            this.eventBus.emit('data:cached', { symbol, type, data: cachedData });
            return cachedData;
        }

        try {
            this.eventBus.emit('data:loading', { symbol, type });
            
            let data;
            switch (type) {
                case 'price':
                    data = await this.loadWithRetry(() => api.getStockPrice(symbol));
                    break;
                case 'metrics':
                    data = await this.loadWithRetry(() => api.getStockMetrics(symbol));
                    break;
                case 'financials':
                    data = await this.loadWithRetry(() => api.getFinancialStatements(symbol));
                    break;
                case 'analyst-estimates':
                    data = await this.loadWithRetry(() => api.getAnalystEstimates(symbol));
                    break;
                case 'stock-analyser':
                    data = await this.loadStockAnalyserData(symbol);
                    break;
                case 'factors':
                    data = await this.loadWithRetry(() => api.getStockFactors(symbol));
                    break;
                case 'news':
                    data = await this.loadWithRetry(() => api.getStockNews(symbol));
                    break;
                default:
                    throw new Error(`Unknown data type: ${type}`);
            }

            if (data.error) {
                throw new Error(data.error);
            }

            // Cache the successful response
            this.setCachedData(cacheKey, data);
            
            this.eventBus.emit('data:loaded', { symbol, type, data });
            return data;

        } catch (error) {
            console.error(`Failed to load ${type} for ${symbol}:`, error);
            this.eventBus.emit('data:error', { symbol, type, error: error.message });
            throw error;
        }
    }

    /**
     * Load stock analyser data (combines multiple API calls)
     * @param {string} symbol - Stock symbol
     * @returns {Promise} Combined stock analyser data
     */
    async loadStockAnalyserData(symbol) {
        try {
            const [priceData, metricsData] = await Promise.all([
                this.loadWithRetry(() => api.getStockPrice(symbol)),
                this.loadWithRetry(() => api.getStockMetrics(symbol))
            ]);

            return {
                price: priceData,
                metrics: metricsData,
                combined: true
            };
        } catch (error) {
            throw new Error(`Failed to load stock analyser data: ${error.message}`);
        }
    }

    /**
     * Search for stocks
     * @param {string} query - Search query
     * @param {number} limit - Result limit
     * @returns {Promise} Search results
     */
    async searchStocks(query, limit = 10) {
        try {
            this.eventBus.emit('search:loading', { query });
            
            const results = await this.loadWithRetry(() => api.searchStocks(query, limit));
            
            this.eventBus.emit('search:loaded', { query, results });
            return results;

        } catch (error) {
            console.error('Stock search failed:', error);
            this.eventBus.emit('search:error', { query, error: error.message });
            throw error;
        }
    }

    /**
     * Get popular stocks
     * @param {number} limit - Number of stocks to get
     * @returns {Promise} Popular stocks
     */
    async getPopularStocks(limit = 12) {
        try {
            this.eventBus.emit('popularStocks:loading');
            
            const stocks = await this.loadWithRetry(() => api.getPopularStocks(limit));
            
            this.eventBus.emit('popularStocks:loaded', { stocks });
            return stocks;

        } catch (error) {
            console.error('Failed to load popular stocks:', error);
            this.eventBus.emit('popularStocks:error', { error: error.message });
            throw error;
        }
    }

    /**
     * Load watchlist data
     * @returns {Promise} Watchlist data
     */
    async loadWatchlist() {
        try {
            this.eventBus.emit('watchlist:loading');
            
            const watchlist = await this.loadWithRetry(() => api.getWatchlist());
            
            this.eventBus.emit('watchlist:loaded', { watchlist });
            return watchlist;

        } catch (error) {
            console.error('Failed to load watchlist:', error);
            this.eventBus.emit('watchlist:error', { error: error.message });
            throw error;
        }
    }

    /**
     * Add stock to watchlist
     * @param {object} stockData - Stock data to add
     * @returns {Promise} Add result
     */
    async addToWatchlist(stockData) {
        try {
            const validation = Validators.validateWatchlistItem(stockData);
            if (!validation.isValid) {
                throw new Error(validation.error);
            }

            this.eventBus.emit('watchlist:adding', { stockData });
            
            const result = await this.loadWithRetry(() => api.addToWatchlist(stockData));
            
            // Clear watchlist cache
            this.clearCachePattern('watchlist');
            
            this.eventBus.emit('watchlist:added', { stockData, result });
            return result;

        } catch (error) {
            console.error('Failed to add to watchlist:', error);
            this.eventBus.emit('watchlist:error', { error: error.message });
            throw error;
        }
    }

    /**
     * Remove stock from watchlist
     * @param {string} symbol - Stock symbol to remove
     * @returns {Promise} Remove result
     */
    async removeFromWatchlist(symbol) {
        try {
            this.eventBus.emit('watchlist:removing', { symbol });
            
            const result = await this.loadWithRetry(() => api.removeFromWatchlist(symbol));
            
            // Clear watchlist cache
            this.clearCachePattern('watchlist');
            
            this.eventBus.emit('watchlist:removed', { symbol, result });
            return result;

        } catch (error) {
            console.error('Failed to remove from watchlist:', error);
            this.eventBus.emit('watchlist:error', { error: error.message });
            throw error;
        }
    }

    /**
     * Run DCF analysis
     * @param {object} assumptions - DCF assumptions
     * @returns {Promise} DCF results
     */
    async runDCFAnalysis(assumptions) {
        try {
            const validation = Validators.validateDCFAssumptions(assumptions);
            if (!validation.isValid) {
                throw new Error(validation.error);
            }

            this.eventBus.emit('dcf:analyzing', { assumptions });
            
            const results = await this.loadWithRetry(() => api.runDCF(assumptions));
            
            this.eventBus.emit('dcf:analyzed', { assumptions, results });
            return results;

        } catch (error) {
            console.error('DCF analysis failed:', error);
            this.eventBus.emit('dcf:error', { error: error.message });
            throw error;
        }
    }

    /**
     * Load data with retry logic
     * @param {function} dataLoader - Function that loads data
     * @param {number} attempts - Current attempt number
     * @returns {Promise} Data promise
     */
    async loadWithRetry(dataLoader, attempts = 0) {
        try {
            return await dataLoader();
        } catch (error) {
            if (attempts < this.retryAttempts) {
                console.warn(`Retry attempt ${attempts + 1} for ${dataLoader.name || 'data loading'}`);
                await this.delay(this.retryDelay * Math.pow(2, attempts));
                return this.loadWithRetry(dataLoader, attempts + 1);
            }
            throw error;
        }
    }

    /**
     * Get cached data
     * @param {string} key - Cache key
     * @returns {*} Cached data or null
     */
    getCachedData(key) {
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            return cached.data;
        }
        return null;
    }

    /**
     * Set cached data
     * @param {string} key - Cache key
     * @param {*} data - Data to cache
     */
    setCachedData(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    /**
     * Clear cache for a specific key
     * @param {string} key - Cache key to clear
     */
    clearCache(key) {
        this.cache.delete(key);
    }

    /**
     * Clear cache matching a pattern
     * @param {string} pattern - Pattern to match
     */
    clearCachePattern(pattern) {
        for (const key of this.cache.keys()) {
            if (key.includes(pattern)) {
                this.cache.delete(key);
            }
        }
    }

    /**
     * Clear all cache
     */
    clearAllCache() {
        this.cache.clear();
    }

    /**
     * Get cache statistics
     * @returns {object} Cache stats
     */
    getCacheStats() {
        return {
            size: this.cache.size,
            keys: Array.from(this.cache.keys()),
            timeout: this.cacheTimeout
        };
    }

    /**
     * Delay execution
     * @param {number} ms - Milliseconds to delay
     * @returns {Promise} Delay promise
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Transform API response data
     * @param {*} data - Raw API data
     * @param {string} type - Data type
     * @returns {*} Transformed data
     */
    transformData(data, type) {
        switch (type) {
            case 'metrics':
                return this.transformMetricsData(data);
            case 'financials':
                return this.transformFinancialsData(data);
            case 'analyst-estimates':
                return this.transformEstimatesData(data);
            default:
                return data;
        }
    }

    /**
     * Transform metrics data
     * @param {object} data - Raw metrics data
     * @returns {object} Transformed metrics data
     */
    transformMetricsData(data) {
        return {
            ...data,
            formattedMarketCap: Formatters.formatCurrency(data.marketCap),
            formattedRevenue: Formatters.formatCurrency(data.revenue),
            formattedPERatio: Formatters.formatRatio(data.peRatio),
            formattedROE: Formatters.formatPercentage(data.roe),
            formattedDebtToEquity: Formatters.formatRatio(data.debtToEquity)
        };
    }

    /**
     * Transform financials data
     * @param {object} data - Raw financials data
     * @returns {object} Transformed financials data
     */
    transformFinancialsData(data) {
        if (data.income_statement) {
            data.income_statement = data.income_statement.map(statement => ({
                ...statement,
                formattedRevenue: Formatters.formatCurrency(statement.revenue),
                formattedNetIncome: Formatters.formatCurrency(statement.net_income)
            }));
        }
        return data;
    }

    /**
     * Transform estimates data
     * @param {object} data - Raw estimates data
     * @returns {object} Transformed estimates data
     */
    transformEstimatesData(data) {
        if (data.earnings_estimates) {
            data.earnings_estimates = data.earnings_estimates.map(estimate => ({
                ...estimate,
                formattedEPS: Formatters.formatStockPrice(estimate.avg)
            }));
        }
        return data;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DataManager;
} else {
    window.DataManager = DataManager;
}

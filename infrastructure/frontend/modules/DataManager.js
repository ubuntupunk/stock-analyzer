// Data Management Module
// Handles API calls, caching, error handling, and data transformation

class DataManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
        this.retryAttempts = 3;
        this.retryDelay = 1000; // 1 second
        this.pendingRequests = new Map(); // Deduplicate in-flight requests
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

        // Check for pending request - deduplicate in-flight requests
        if (this.pendingRequests.has(cacheKey)) {
            console.log(`DataManager: Reusing pending request for ${cacheKey}`);
            return this.pendingRequests.get(cacheKey);
        }

        try {
            this.eventBus.emit('data:loading', { symbol, type });
            
            let data;
            switch (type) {
                case 'price':
                    data = await this.loadWithRetry(() => api.getStockPrice(symbol));
                    break;
                case 'metrics':
                    // Fetch both price (for charts) and metrics data
                    const [priceData, metricsData] = await Promise.all([
                        this.loadWithRetry(() => api.getStockPrice(symbol)),
                        this.loadWithRetry(() => api.getStockMetrics(symbol))
                    ]);
                    // Transform metrics data
                    const transformedMetrics = this.transformMetricsData(metricsData);
                    // Combine price (with historicalData) and metrics
                    // Spread metrics fields at root level for UI compatibility
                    data = {
                        ...priceData,
                        ...transformedMetrics,  // Spread metrics at root level for UI
                        metrics: transformedMetrics,  // Also keep nested version
                        hasHistoricalData: !!priceData?.historicalData
                    };
                    break;
                case 'financials':
                    console.log('=== DataManager: Loading financials START ===');
                    console.log('DataManager: Calling API for financials, symbol:', symbol);
                    data = await this.loadWithRetry(() => api.getFinancialStatements(symbol));
                    console.log('DataManager: Financials data received from API:', {
                        hasData: !!data,
                        dataType: typeof data,
                        dataKeys: data ? Object.keys(data) : [],
                        rawData: data
                    });
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

            // Clear pending request on success
            this.pendingRequests.delete(cacheKey);

            if (data.error) {
                throw new Error(data.error);
            }

            // Transform data if needed
            if (type === 'metrics' && data) {
                data = this.transformMetricsData(data);
            } else if (type === 'financials' && data) {
                console.log('DataManager: Transforming financials data BEFORE:', data);
                data = this.transformFinancialsData(data);
                console.log('DataManager: Transforming financials data AFTER:', data);
            } else if (type === 'analyst-estimates' && data) {
                data = this.transformEstimatesData(data);
            }

            // Cache the successful response
            this.setCachedData(cacheKey, data);
            
            if (type === 'financials') {
                console.log('DataManager: Emitting data:loaded event for financials:', {
                    symbol,
                    type,
                    hasData: !!data,
                    dataStructure: {
                        hasIncomeStatement: !!data?.income_statement,
                        hasBalanceSheet: !!data?.balance_sheet,
                        hasCashFlow: !!data?.cash_flow
                    }
                });
            }
            
            this.eventBus.emit('data:loaded', { symbol, type, data });
            
            if (type === 'financials') {
                console.log('=== DataManager: Loading financials END ===');
            }
            
            return data;

        } catch (error) {
            // Clear pending request on error too
            this.pendingRequests.delete(cacheKey);
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
        console.log('DataManager: loadStockAnalyserData called for:', symbol);
        try {
            const [priceData, metricsData] = await Promise.all([
                this.loadWithRetry(() => api.getStockPrice(symbol)),
                this.loadWithRetry(() => api.getStockMetrics(symbol))
            ]);

            console.log('DataManager: priceData:', priceData);
            console.log('DataManager: metricsData:', metricsData);

            const result = {
                price: priceData,
                metrics: metricsData,
                combined: true
            };
            
            console.log('DataManager: Returning combined result:', result);
            return result;
        } catch (error) {
            console.error('DataManager: Failed to load stock analyser data:', error);
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
            console.warn('Failed to load watchlist from API, falling back to localStorage:', error);
            
            // Fallback to localStorage
            const localWatchlist = this.loadWatchlistFromLocalStorage();
            this.eventBus.emit('watchlist:loaded', { watchlist: localWatchlist });
            return localWatchlist;
        }
    }

    /**
     * Load watchlist from localStorage
     * @returns {Array} Watchlist data
     */
    loadWatchlistFromLocalStorage() {
        try {
            const data = localStorage.getItem('stock_analyzer_watchlist');
            if (data) {
                return JSON.parse(data);
            }
            
            // If no data exists, seed with sample watchlist
            const sampleWatchlist = this.getSampleWatchlistData();
            this.saveWatchlistToLocalStorage(sampleWatchlist);
            return sampleWatchlist;
        } catch (error) {
            console.error('Failed to load watchlist from localStorage:', error);
            return [];
        }
    }

    /**
     * Get sample watchlist data for demo purposes
     * @returns {Array} Sample watchlist data
     */
    getSampleWatchlistData() {
        return [
            {
                symbol: 'AAPL',
                name: 'Apple Inc.',
                addedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
                notes: 'Strong tech stock, good dividends',
                alertPrice: null,
                tags: ['tech', 'dividend']
            },
            {
                symbol: 'MSFT',
                name: 'Microsoft Corporation',
                addedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
                notes: 'Cloud computing leader',
                alertPrice: 400,
                tags: ['tech', 'cloud']
            },
            {
                symbol: 'GOOGL',
                name: 'Alphabet Inc.',
                addedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
                notes: 'Google parent company',
                alertPrice: null,
                tags: ['tech', 'ai']
            },
            {
                symbol: 'AMZN',
                name: 'Amazon.com Inc.',
                addedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
                notes: 'E-commerce and cloud giant',
                alertPrice: 180,
                tags: ['tech', 'ecommerce']
            },
            {
                symbol: 'NVDA',
                name: 'NVIDIA Corporation',
                addedAt: new Date().toISOString(),
                notes: 'AI and GPU leader',
                alertPrice: null,
                tags: ['tech', 'ai', 'gpu']
            }
        ];
    }

    /**
     * Save watchlist to localStorage
     * @param {Array} watchlist - Watchlist data to save
     */
    saveWatchlistToLocalStorage(watchlist) {
        try {
            localStorage.setItem('stock_analyzer_watchlist', JSON.stringify(watchlist));
        } catch (error) {
            console.error('Failed to save watchlist to localStorage:', error);
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
            console.warn('Failed to add to watchlist via API, saving to localStorage:', error);
            
            // Fallback to localStorage
            const watchlist = this.loadWatchlistFromLocalStorage();
            
            // Check if already exists
            const exists = watchlist.some(item => item.symbol === stockData.symbol);
            if (!exists) {
                const watchlistItem = {
                    symbol: stockData.symbol,
                    name: stockData.name || stockData.symbol,
                    addedAt: new Date().toISOString(),
                    notes: stockData.notes || '',
                    alertPrice: stockData.alertPrice || null,
                    tags: stockData.tags || []
                };
                watchlist.push(watchlistItem);
                this.saveWatchlistToLocalStorage(watchlist);
            }
            
            this.eventBus.emit('watchlist:added', { stockData, result: { success: true, local: true } });
            return { success: true, local: true };
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
            console.warn('Failed to remove from watchlist via API, removing from localStorage:', error);
            
            // Fallback to localStorage
            let watchlist = this.loadWatchlistFromLocalStorage();
            watchlist = watchlist.filter(item => item.symbol !== symbol);
            this.saveWatchlistToLocalStorage(watchlist);
            
            this.eventBus.emit('watchlist:removed', { symbol, result: { success: true, local: true } });
            return { success: true, local: true };
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
        // Convert snake_case to camelCase
        const camelData = this.snakeToCamel(data);
        
        return {
            ...camelData,
            formattedMarketCap: Formatters.formatCurrency(camelData.marketCap),
            formattedRevenue: Formatters.formatCurrency(camelData.revenue),
            formattedPERatio: Formatters.formatRatio(camelData.peRatio),
            formattedROE: Formatters.formatPercentage(camelData.roe),
            formattedDebtToEquity: Formatters.formatRatio(camelData.debtToEquity)
        };
    }

    /**
     * Convert snake_case object keys to camelCase
     * @param {object} obj - Object with snake_case keys
     * @returns {object} Object with camelCase keys
     */
    snakeToCamel(obj) {
        if (!obj || typeof obj !== 'object') return obj;
        
        const result = {};
        
        for (const key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                // Convert snake_case to camelCase
                const camelKey = key.replace(/_([a-z])/g, (g) => g[1].toUpperCase());
                result[camelKey] = obj[key];
            }
        }
        
        return result;
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

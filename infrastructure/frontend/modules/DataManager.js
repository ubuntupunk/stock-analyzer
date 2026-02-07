/**
 * Data Management Module
 * Handles API calls, caching, error handling, and data transformation
 * Features: LRU Cache, Circuit Breaker, Priority Queue, Batching, Metrics, Offline Support
 */

// Priority levels for request queue
const PRIORITY = {
    CRITICAL: 1,  // Price data, critical metrics
    HIGH: 2,       // Metrics, financials
    NORMAL: 3,     // Watchlist, screening
    LOW: 4         // News, factors, non-critical
};

// Data types mapped to priorities
const PRIORITY_MAP = {
    'price': PRIORITY.CRITICAL,
    'metrics': PRIORITY.HIGH,
    'financials': PRIORITY.HIGH,
    'analyst-estimates': PRIORITY.HIGH,
    'stock-analyser': PRIORITY.CRITICAL,
    'factors': PRIORITY.LOW,
    'news': PRIORITY.LOW,
    'watchlist': PRIORITY.NORMAL,
    'search': PRIORITY.NORMAL,
    'dcf': PRIORITY.NORMAL
};

class LRUCache {
    constructor(maxSize = 100) {
        this.maxSize = maxSize;
        this.cache = new Map();
    }

    get(key) {
        if (!this.cache.has(key)) return null;

        const value = this.cache.get(key);
        // Move to end (most recently used)
        this.cache.delete(key);
        this.cache.set(key, value);
        return value?.data;
    }

    set(key, data, ttlMs = 300000) {
        // Evict oldest entry if at capacity
        if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
            console.log(`LRUCache: Evicted ${firstKey} (capacity reached)`);
        }

        this.cache.set(key, {
            data,
            timestamp: Date.now(),
            ttl: ttlMs
        });
    }

    delete(key) {
        this.cache.delete(key);
    }

    has(key) {
        if (!this.cache.has(key)) return false;

        const entry = this.cache.get(key);
        // Check TTL
        if (Date.now() - entry.timestamp > entry.ttl) {
            this.cache.delete(key);
            return false;
        }
        return true;
    }

    clear() {
        this.cache.clear();
    }

    // Clean expired entries
    prune() {
        const now = Date.now();
        for (const [key, entry] of this.cache.entries()) {
            if (now - entry.timestamp > entry.ttl) {
                this.cache.delete(key);
            }
        }
        console.log(`LRUCache: Pruned expired entries, new size: ${this.cache.size}`);
    }

    getStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxSize,
            keys: Array.from(this.cache.keys())
        };
    }
}

class RequestQueue {
    constructor(concurrency = 3) {
        this.queue = [];
        this.processing = new Set();
        this.concurrency = concurrency;
    }

    /**
     * Add request to queue
     * @param {Function} fn - Function to execute
     * @param {number} priority - Priority level (1=High, 4=Low)
     * @param {string} key - Unique key for deduplication
     * @returns {Promise} - Resolves when request completes
     */
    enqueue(fn, priority = PRIORITY.NORMAL, key = null) {
        return new Promise((resolve, reject) => {
            const item = {
                fn,
                priority,
                key,
                timestamp: Date.now(),
                attempts: 0,
                resolve,
                reject
            };

            // Insert based on priority (lower number = higher priority)
            const index = this.queue.findIndex(i => i.priority > priority);
            if (index === -1) {
                this.queue.push(item);
            } else {
                this.queue.splice(index, 0, item);
            }

            console.log(`RequestQueue: Enqueued ${key || 'anonymous'} (priority: ${priority}, queue size: ${this.queue.length})`);
            this.process();
        });
    }

    /**
     * Process queue
     */
    async process() {
        // Check concurrency limit
        if (this.processing.size >= this.concurrency) {
            return;
        }

        // Get next item
        const item = this.queue.shift();
        if (!item) return;

        const itemKey = item.key || `req-${Date.now()}-${Math.random()}`;
        this.processing.add(itemKey);

        console.log(`RequestQueue: Processing ${item.key || 'anonymous'} (active: ${this.processing.size})`);

        try {
            const result = await item.fn();
            item.resolve(result);
        } catch (error) {
            item.reject(error);
        } finally {
            this.processing.delete(itemKey);
            // Process next
            this.process();
        }
    }

    /**
     * Get queue stats
     */
    getStats() {
        return {
            pending: this.queue.length,
            processing: this.processing.size,
            concurrency: this.concurrency
        };
    }
}

class APIMetrics {
    constructor() {
        this.metrics = {
            requests: {
                total: 0,
                success: 0,
                failed: 0
            },
            cache: {
                hits: 0,
                misses: 0
            },
            circuitBreaker: {
                open: 0,
                halfOpen: 0,
                closed: 0
            },
            latency: {
                total: 0,
                count: 0,
                avg: 0,
                p50: 0,
                p95: 0
            },
            errors: {}
        };
        this.latencyHistory = [];
    }

    /**
     * Record API request
     */
    recordRequest(endpoint, success, latencyMs) {
        this.metrics.requests.total++;
        if (success) {
            this.metrics.requests.success++;
        } else {
            this.metrics.requests.failed++;
        }

        // Update latency
        this.metrics.latency.total += latencyMs;
        this.metrics.latency.count++;
        this.metrics.latency.avg = Math.round(this.metrics.latency.total / this.metrics.latency.count);
        this.latencyHistory.push(latencyMs);

        // Keep only last 1000 latency samples
        if (this.latencyHistory.length > 1000) {
            this.latencyHistory.shift();
        }

        // Calculate percentiles
        const sorted = [...this.latencyHistory].sort((a, b) => a - b);
        this.metrics.latency.p50 = sorted[Math.floor(sorted.length * 0.5)] || 0;
        this.metrics.latency.p95 = sorted[Math.floor(sorted.length * 0.95)] || 0;
    }

    /**
     * Record cache hit/miss
     */
    recordCache(hit) {
        if (hit) {
            this.metrics.cache.hits++;
        } else {
            this.metrics.cache.misses++;
        }
    }

    /**
     * Get cache hit rate
     */
    getCacheHitRate() {
        const total = this.metrics.cache.hits + this.metrics.cache.misses;
        if (total === 0) return 'N/A';
        return ((this.metrics.cache.hits / total) * 100).toFixed(1) + '%';
    }

    /**
     * Record circuit breaker state
     */
    recordCircuitBreakerState(state) {
        this.metrics.circuitBreaker[state]++;
    }

    /**
     * Record error type
     */
    recordError(errorType) {
        this.metrics.errors[errorType] = (this.metrics.errors[errorType] || 0) + 1;
    }

    /**
     * Get all metrics
     */
    getMetrics() {
        return {
            ...this.metrics,
            cacheHitRate: this.getCacheHitRate(),
            errorRate: this.metrics.requests.total > 0
                ? ((this.metrics.requests.failed / this.metrics.requests.total) * 100).toFixed(1) + '%'
                : 'N/A'
        };
    }

    /**
     * Reset metrics
     */
    reset() {
        this.metrics = {
            requests: { total: 0, success: 0, failed: 0 },
            cache: { hits: 0, misses: 0 },
            circuitBreaker: { open: 0, halfOpen: 0, closed: 0 },
            latency: { total: 0, count: 0, avg: 0, p50: 0, p95: 0 },
            errors: {}
        };
        this.latencyHistory = [];
    }
}

class OfflineQueue {
    constructor(storageKey = 'stock_analyzer_offline_queue') {
        this.storageKey = storageKey;
        this.queue = this.loadFromStorage();
        this.isOnline = navigator.onLine;

        // Listen for online/offline events
        window.addEventListener('online', () => {
            this.isOnline = true;
            console.log('OfflineQueue: Back online, processing queue');
            this.processQueue();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            console.log('OfflineQueue: Gone offline');
        });
    }

    /**
     * Load queue from localStorage
     */
    loadFromStorage() {
        try {
            const data = localStorage.getItem(this.storageKey);
            return data ? JSON.parse(data) : [];
        } catch {
            return [];
        }
    }

    /**
     * Save queue to localStorage
     */
    saveToStorage() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.queue));
        } catch (e) {
            console.warn('OfflineQueue: Failed to save to storage:', e);
        }
    }

    /**
     * Add request to offline queue
     */
    enqueue(request) {
        const item = {
            id: Date.now().toString(36) + Math.random().toString(36).substr(2),
            request,
            timestamp: Date.now(),
            attempts: 0
        };
        this.queue.push(item);
        this.saveToStorage();
        console.log(`OfflineQueue: Enqueued ${request.key || request.type}`);
    }

    /**
     * Process pending requests when online
     */
    async processQueue() {
        if (!this.isOnline || this.queue.length === 0) return;

        console.log(`OfflineQueue: Processing ${this.queue.length} pending requests`);

        // Process in order
        const toRemove = [];

        for (const item of this.queue) {
            try {
                await item.request.fn();
                toRemove.push(item.id);
                console.log(`OfflineQueue: Completed ${item.request.key || item.request.type}`);
            } catch (e) {
                item.attempts++;
                if (item.attempts >= 3) {
                    toRemove.push(item.id);
                    console.warn(`OfflineQueue: Max attempts reached for ${item.request.key || item.request.type}`);
                }
            }
        }

        // Remove completed/failed items
        this.queue = this.queue.filter(item => !toRemove.includes(item.id));
        this.saveToStorage();
    }

    /**
     * Get queue stats
     */
    getStats() {
        return {
            pending: this.queue.length,
            isOnline: this.isOnline
        };
    }

    /**
     * Clear queue
     */
    clear() {
        this.queue = [];
        this.saveToStorage();
    }
}

class DataManager {
    constructor(eventBus) {
        this.eventBus = eventBus;

        // Core components
        this.cache = new LRUCache(100); // 100 items max
        this.circuitBreaker = new CircuitBreaker({
            failureThreshold: 5,
            successThreshold: 2,
            timeout: 30000
        });
        // Initialize RequestQueue with concurrency limit of 3
        this.requestQueue = new RequestQueue(3);

        this.metrics = new APIMetrics();
        this.offlineQueue = new OfflineQueue();

        // Configuration
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
        this.pendingRequests = new Map();

        // Periodic cleanup
        this.pruneInterval = setInterval(() => this.cache.prune(), 60000);
    }

    /**
     * Load stock data for a specific tab/type
     * SIMPLIFIED: Direct async/await execution (no queue)
     * @param {string} symbol - Stock symbol
     * @param {string} type - Data type (metrics, financials, etc.)
     * @returns {Promise} Data promise
     */
    /**
     * Load stock data for a specific tab/type
     * Uses RequestQueue to throttle concurrent requests
     * @param {string} symbol - Stock symbol
     * @param {string} type - Data type (metrics, financials, etc.)
     * @returns {Promise} Data promise
     */
    async loadStockData(symbol, type) {
        const cacheKey = `${symbol}:${type}`;

        // Check cache first
        const cachedData = this.cache.get(cacheKey);
        if (cachedData) {
            this.metrics.recordCache(true);
            this.eventBus.emit('data:cached', { symbol, type, data: cachedData });
            this.eventBus.emit('data:loaded', { symbol, type, data: cachedData });
            return cachedData;
        }
        this.metrics.recordCache(false);

        // Check for pending request - deduplicate in-flight requests
        if (this.pendingRequests.has(cacheKey)) {
            console.log(`DataManager: Reusing pending request for ${cacheKey}`);
            return this.pendingRequests.get(cacheKey);
        }

        // Determine priority
        const priority = PRIORITY_MAP[type] || PRIORITY.NORMAL;

        // Create the task to be queued
        const task = async () => {
            const startTime = Date.now();
            try {
                this.eventBus.emit('data:loading', { symbol, type });

                // Check circuit breaker before making request
                const cbState = this.circuitBreaker.getState(`/api/stock/${type}`);
                if (cbState.state === 'OPEN') {
                    throw new Error(`Service unavailable for ${type} (Circuit Breaker)`);
                }

                let data;
                switch (type) {
                    case 'price':
                        data = await this.executeWithCircuitBreaker(() => api.getStockPrice(symbol), type);
                        // If we got historical data, update the metrics cache so chart can be created
                        if (data?.historicalData) {
                            const metricsCacheKey = `${symbol}:metrics`;
                            const cachedMetrics = this.cache.get(metricsCacheKey);

                            if (cachedMetrics && !cachedMetrics.hasHistoricalData) {
                                cachedMetrics.hasHistoricalData = true;
                                cachedMetrics.historicalData = data.historicalData;
                                this.cache.set(metricsCacheKey, cachedMetrics, this.cacheTimeout);
                            } else if (!cachedMetrics) {
                                const metricsData = {
                                    ...data,
                                    hasHistoricalData: true,
                                    historicalData: data.historicalData,
                                    metrics: {},
                                    symbol: symbol
                                };
                                this.cache.set(metricsCacheKey, metricsData, this.cacheTimeout);
                            }
                        }
                        break;
                    case 'metrics':
                        // Prioritize price data for immediate UI feedback
                        const priceData = await this.executeWithCircuitBreaker(() => api.getStockPrice(symbol), type);

                        // Then get metrics
                        const metricsData = await this.executeWithCircuitBreaker(() => api.getStockMetrics(symbol), type);

                        const transformedMetrics = this.transformMetricsData(metricsData);
                        data = {
                            ...priceData,
                            ...transformedMetrics,
                            metrics: transformedMetrics,
                            hasHistoricalData: !!priceData?.historicalData
                        };
                        break;
                    case 'financials':
                        data = await this.executeWithCircuitBreaker(() => api.getFinancialStatements(symbol), type);
                        data = this.transformFinancialsData(data);
                        break;
                    case 'analyst-estimates':
                        data = await this.executeWithCircuitBreaker(() => api.getAnalystEstimates(symbol), type);
                        data = this.transformEstimatesData(data);
                        break;
                    case 'stock-analyser':
                        data = await this.loadStockAnalyserData(symbol);
                        break;
                    case 'factors':
                        data = await this.executeWithCircuitBreaker(() => api.getStockFactors(symbol), type);
                        break;
                    case 'news':
                        data = await this.executeWithCircuitBreaker(() => api.getStockNews(symbol), type);
                        break;
                    default:
                        throw new Error(`Unknown data type: ${type}`);
                }

                if (data.error) {
                    throw new Error(data.error);
                }

                // Record success metrics
                this.metrics.recordRequest(type, true, Date.now() - startTime);

                // Cache the successful response
                this.cache.set(cacheKey, data, this.cacheTimeout);

                // Emit data:loaded event
                this.eventBus.emit('data:loaded', { symbol, type, data });

                return data;
            } catch (error) {
                this.metrics.recordRequest(type, false, Date.now() - startTime);
                this.metrics.recordError(error.message);
                console.error(`DataManager: Failed to load ${type} for ${symbol}:`, error);
                this.eventBus.emit('data:error', { symbol, type, error: error.message });
                throw error;
            }
        };

        // Queue the request
        const promise = this.requestQueue.enqueue(task, priority, cacheKey);

        // Store promise to deduplicate
        this.pendingRequests.set(cacheKey, promise);

        // Cleanup pending map when done
        promise.finally(() => {
            this.pendingRequests.delete(cacheKey);
        });

        return promise;
    }

    /**
     * Execute with circuit breaker
     */
    async executeWithCircuitBreaker(fn, endpoint) {
        return this.circuitBreaker.execute(`/api/stock/${endpoint}`, async () => {
            try {
                return await fn();
            } catch (error) {
                // Check if error indicates circuit should open
                if (error.message.includes('503') || error.message.includes('timeout') || error.message.includes('network')) {
                    this.circuitBreaker.recordFailure(`/api/stock/${endpoint}`);
                }
                throw error;
            }
        });
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
                this.executeWithCircuitBreaker(() => api.getStockPrice(symbol), 'price'),
                this.executeWithCircuitBreaker(() => api.getStockMetrics(symbol), 'metrics')
            ]);

            console.log('DataManager: priceData:', priceData);
            console.log('DataManager: metricsData:', metricsData);

            const result = {
                price: priceData,
                metrics: metricsData,
                hasHistoricalData: !!priceData?.historicalData,
                historicalData: priceData?.historicalData,
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

            const cacheKey = `search:${query}:${limit}`;
            const cachedData = this.cache.get(cacheKey);
            if (cachedData) {
                this.metrics.recordCache(true);
                this.eventBus.emit('search:loaded', { query, results: cachedData });
                return cachedData;
            }
            this.metrics.recordCache(false);

            const results = await this.executeWithCircuitBreaker(() => api.searchStocks(query, limit), 'search');

            this.cache.set(cacheKey, results, this.cacheTimeout);
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

            const cacheKey = `popular:${limit}`;
            const cachedData = this.cache.get(cacheKey);
            if (cachedData) {
                this.metrics.recordCache(true);
                this.eventBus.emit('popularStocks:loaded', { stocks: cachedData });
                return cachedData;
            }
            this.metrics.recordCache(false);

            const stocks = await this.executeWithCircuitBreaker(() => api.getPopularStocks(limit), 'popular-stocks');

            this.cache.set(cacheKey, stocks, this.cacheTimeout);
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

            const cacheKey = 'watchlist';
            const cachedData = this.cache.get(cacheKey);
            if (cachedData) {
                this.metrics.recordCache(true);
                this.eventBus.emit('watchlist:loaded', { watchlist: cachedData });
                return cachedData;
            }
            this.metrics.recordCache(false);

            const watchlist = await this.executeWithCircuitBreaker(() => api.getWatchlist(), 'watchlist');

            this.cache.set(cacheKey, watchlist, this.cacheTimeout);
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

            const result = await this.executeWithCircuitBreaker(() => api.addToWatchlist(stockData), 'watchlist-add');

            // Clear watchlist cache
            this.cache.delete('watchlist');

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

            const result = await this.executeWithCircuitBreaker(() => api.removeFromWatchlist(symbol), 'watchlist-remove');

            // Clear watchlist cache
            this.cache.delete('watchlist');

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

            const results = await this.executeWithCircuitBreaker(() => api.runDCF(assumptions), 'dcf');

            this.eventBus.emit('dcf:analyzed', { assumptions, results });
            return results;

        } catch (error) {
            console.error('DCF analysis failed:', error);
            this.eventBus.emit('dcf:error', { error: error.message });
            throw error;
        }
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
        return this.cache.getStats();
    }

    /**
     * Get circuit breaker stats
     * @returns {object} Circuit breaker stats
     */
    getCircuitBreakerStats() {
        return this.circuitBreaker.getStats();
    }

    /**
     * Get metrics
     * @returns {object} Metrics data
     */
    getMetrics() {
        return this.metrics.getMetrics();
    }

    /**
     * Get all stats
     * @returns {object} All stats
     */
    getAllStats() {
        return {
            cache: this.getCacheStats(),
            circuitBreaker: this.getCircuitBreakerStats(),
            queue: this.requestQueue.getStats(),
            offline: this.offlineQueue.getStats(),
            metrics: this.getMetrics()
        };
    }

    /**
     * Clean up resources (call on page unload)
     */
    cleanup() {
        // Clear cache pruning interval to prevent memory leaks
        if (this.pruneInterval) {
            clearInterval(this.pruneInterval);
            this.pruneInterval = null;
        }

        // Clear pending requests
        this.pendingRequests.clear();

        // Clear queues
        this.requestQueue.clear();
        this.offlineQueue.clear();

        // Clear cache
        this.cache.clear();

        console.log('DataManager: Cleanup complete');
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
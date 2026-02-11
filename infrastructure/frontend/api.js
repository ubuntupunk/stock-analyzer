// API Service Layer
// Handles all communication with the backend Lambda functions

class APIService {
    constructor() {
        this.baseURL = config.apiEndpoint;
        this.timeout = 30000; // 30 second timeout (increased for cold starts)
        this.maxRetries = 3;
        this.retryDelays = [1000, 2000, 4000]; // Exponential backoff
        this.rateLimitDelay = 60000; // 60 second delay on 429
        this.tokenRefreshThreshold = 300000; // Refresh token 5 min before expiry

        // Endpoints that do not strictly require authentication for GET requests
        // (but will still send a token if available, for personalization)
        this.publicEndpoints = [
            /^\/stock\/metrics/,
            /^\/stock\/price/,
            /^\/stock\/estimates/,
            /^\/stock\/financials/,
            /^\/stock\/factors/,
            /^\/stock\/news/,
            /^\/stock\/batch\/prices/,
            /^\/stock\/batch\/metrics/,
            /^\/stock\/batch\/estimates/,
            /^\/stock\/batch\/financials/,
            /^\/stocks\/search/,
            /^\/stocks\/popular/,
            /^\/stocks\/sectors/,
            /^\/stocks\/filter/,
            /^\/stocks\/symbol/
        ];
    }

    /**
     * Check if token needs refresh
     */
    async shouldRefreshToken() {
        if (!window.authManager || !window.authManager.getTokenExpiry) return false;
        const expiry = await window.authManager.getTokenExpiry();
        if (!expiry) return false;
        return (expiry - Date.now()) < this.tokenRefreshThreshold;
    }

    /**
     * Proactively refresh auth token if needed
     */
    async refreshTokenIfNeeded() {
        if (await this.shouldRefreshToken()) {
            console.log('APIService: Proactively refreshing auth token');
            if (window.authManager && window.authManager.refreshAuthToken) {
                await window.authManager.refreshAuthToken();
            }
        }
    }

    /**
     * Sleep utility for delays
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const method = options.method ? options.method.toUpperCase() : 'GET';

        // Determine if this endpoint requires authentication
        let requiresAuth = true;
        if (method === 'GET') {
            for (const pattern of this.publicEndpoints) {
                if (pattern.test(endpoint)) {
                    requiresAuth = false;
                    break;
                }
            }
        }
        // If it's a POST/PUT/DELETE (or other) to factors, watchlist, screen, dcf, etc., it generally requires auth.
        // We'll rely on the default `requiresAuth = true` for these,
        // unless explicitly marked as public (which they typically won't be).


        // Get auth token if available (only if auth is required or user is already logged in)
        let authToken = null;
        if (window.authManager && (requiresAuth || await window.authManager.isAuthenticated())) {
            try {
                authToken = await window.authManager.getAuthToken();
            } catch (e) {
                console.warn('APIService: Failed to get auth token for endpoint:', endpoint, e.message);
                // If auth is strictly required and token cannot be obtained, rethrow
                if (requiresAuth) {
                    throw new Error('Authentication required and token could not be obtained.');
                }
            }
        }

        // --- Local Development Fallback for Auth Token ---
        // If in local development and authentication is required, but no Cognito token is present,
        // use a predefined local dev token. This is for local testing of protected routes.
        if (!authToken && config.isLocal && requiresAuth) {
            authToken = config.localDevToken;
            console.log('APIService: Using local development token for authenticated request.');
        }
        // --- End Local Development Fallback ---


        // Proactively refresh token if needed (only if a token was obtained)
        if (authToken) {
            await this.refreshTokenIfNeeded();
        }


        // Build headers
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        // Add Authorization header if token exists
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        }

        // Make request with retry logic
        let lastError;
        for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
            try {
                const response = await this.fetchWithTimeout(url, {
                    ...options,
                    headers: headers
                }, this.timeout);

                // Handle 429 Rate Limiting - wait and retry
                if (response.status === 429) {
                    console.warn(`APIService: Rate limited (429), attempt ${attempt + 1}/${this.maxRetries + 1}`);
                    if (attempt < this.maxRetries) {
                        // Exponential backoff for rate limiting
                        const waitTime = this.rateLimitDelay * Math.pow(2, attempt);
                        await this.sleep(waitTime);
                        continue;
                    } else {
                        throw new Error('Rate limited - too many requests');
                    }
                }

                // Handle 401 Unauthorized - try token refresh once
                if (response.status === 401 && attempt === 0) {
                    console.warn('APIService: Unauthorized (401), attempting token refresh');
                    if (window.authManager && window.authManager.refreshAuthToken) {
                        await window.authManager.refreshAuthToken();
                        // Retry with new token
                        continue;
                    }
                    throw new Error('Authentication required');
                }

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                lastError = error;

                // Handle timeout specifically
                if (error.message === 'Timeout') {
                    console.warn(`APIService: Request timeout (${this.timeout}ms), attempt ${attempt + 1}/${this.maxRetries + 1}`);
                    if (attempt < this.maxRetries) {
                        // Exponential backoff for timeouts
                        await this.sleep(this.retryDelays[attempt]);
                        continue;
                    }
                }

                // Don't retry client errors (except 429 and 401 which are handled above)
                // Only check response if it was defined (network errors won't have response)
                if (typeof response !== 'undefined' && response.status >= 400 && response.status < 500 && response.status !== 429 && response.status !== 401) {
                    throw error;
                }

                if (attempt < this.maxRetries) {
                    await this.sleep(this.retryDelays[attempt]);
                }
            }
        }

        console.error(`APIService: All retry attempts exhausted for ${url}:`, lastError);
        throw lastError;
    }

    /**
     * Fetch with timeout wrapper
     */
    async fetchWithTimeout(url, options, timeoutMs) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Timeout');
            }
            throw error;
        }
    }

    // Stock Data APIs
    async getStockMetrics(symbol) {
        return this.request(`/stock/metrics?symbol=${symbol}`);
    }

    async getStockPrice(symbol) {
        return this.request(`/stock/price?symbol=${symbol}`);
    }

    async getStockPriceHistory(symbol, period = "3mo") {
        return this.request(`/stock/price?symbol=${symbol}&period=${period}`);
    }

    async getStockPriceHistoryRange(symbol, startDate, endDate) {
        return this.request(`/stock/price?symbol=${symbol}&startDate=${startDate}&endDate=${endDate}`);
    }

    async getAnalystEstimates(symbol) {
        return this.request(`/stock/estimates?symbol=${symbol}`);
    }

    async getFinancialStatements(symbol, period = 'annual') {
        console.log('=== API: getFinancialStatements START ===');
        console.log('API: Requesting financials for symbol:', symbol, 'period:', period);
        console.log('API: Request URL:', `${this.baseURL}/stock/financials?symbol=${symbol}&period=${period}`);

        try {
            const data = await this.request(`/stock/financials?symbol=${symbol}&period=${period}`);
            console.log('API: Financials response received:', {
                hasData: !!data,
                dataKeys: data ? Object.keys(data) : [],
                hasIncomeStatement: !!data?.income_statement,
                incomeStatementLength: data?.income_statement?.length,
                hasBalanceSheet: !!data?.balance_sheet,
                balanceSheetLength: data?.balance_sheet?.length,
                hasCashFlow: !!data?.cash_flow,
                cashFlowLength: data?.cash_flow?.length,
                fullData: data
            });
            console.log('=== API: getFinancialStatements END ===');
            return data;
        } catch (error) {
            console.error('API: getFinancialStatements ERROR:', error);
            console.error('API: Error details:', {
                message: error.message,
                stack: error.stack
            });
            console.log('=== API: getFinancialStatements END (ERROR) ===');
            throw error;
        }
    }

    async getStockFactors(symbol) {
        return this.request(`/stock/factors?symbol=${symbol}`);
    }

    async getStockNews(symbol) {
        return this.request(`/stock/news?symbol=${symbol}`);
    }

    // Batch Stock Data APIs (NEW - for concurrent fetching)
    async getBatchStockPrices(symbols) {
        const symbolsParam = Array.isArray(symbols) ? symbols.join(',') : symbols;
        return this.request(`/stock/batch/prices?symbols=${symbolsParam}`);
    }

    async getBatchStockMetrics(symbols) {
        const symbolsParam = Array.isArray(symbols) ? symbols.join(',') : symbols;
        return this.request(`/stock/batch/metrics?symbols=${symbolsParam}`);
    }

    async getBatchAnalystEstimates(symbols) {
        const symbolsParam = Array.isArray(symbols) ? symbols.join(',') : symbols;
        return this.request(`/stock/batch/estimates?symbols=${symbolsParam}`);
    }

    async getBatchFinancialStatements(symbols) {
        const symbolsParam = Array.isArray(symbols) ? symbols.join(',') : symbols;
        return this.request(`/stock/batch/financials?symbols=${symbolsParam}`);
    }

    // Screening APIs
    async screenStocks(criteria) {
        return this.request(`/screen`, {
            method: 'POST',
            body: JSON.stringify({ criteria })
        });
    }

    async saveFactor(factorData) {
        return this.request(`/factors`, {
            method: 'POST',
            body: JSON.stringify(factorData)
        });
    }

    async getUserFactors() {
        return this.request(`/factors`);
    }

    async deleteFactor(factorId) {
        return this.request(`/factors/${factorId}`, {
            method: 'DELETE'
        });
    }

    // DCF Analysis
    async calculateDCF(params) {
        return this.request(`/dcf`, {
            method: 'POST',
            body: JSON.stringify(params)
        });
    }

    // Stock Analyser Data (combined metrics and price)
    async getStockAnalyserData(symbol) {
        const [priceData, metricsData] = await Promise.all([
            this.getStockPrice(symbol),
            this.getStockMetrics(symbol)
        ]);
        return {
            price: priceData,
            metrics: metricsData,
            combined: true
        };
    }

    // Watchlist APIs
    async getWatchlist() {
        return this.request(`/watchlist`);
    }

    async addToWatchlist(stockData) {
        return this.request(`/watchlist`, {
            method: 'POST',
            body: JSON.stringify(stockData)
        });
    }

    async updateWatchlistItem(symbol, updates) {
        return this.request(`/watchlist`, {
            method: 'PUT',
            body: JSON.stringify({ symbol, updates })
        });
    }

    async removeFromWatchlist(symbol) {
        return this.request(`/watchlist?symbol=${symbol}`, {
            method: 'DELETE'
        });
    }

    // Stock Universe APIs
    async searchStocks(query, limit = 20) {
        return this.request(`/stocks/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    }

    async getPopularStocks(limit = 10) {
        return this.request(`/stocks/popular?limit=${limit}`);
    }

    async getSectors() {
        return this.request(`/stocks/sectors`);
    }

    async filterStocks(filters = {}) {
        const params = new URLSearchParams();
        if (filters.sector) params.append('sector', filters.sector);
        if (filters.minCap) params.append('minCap', filters.minCap);
        if (filters.maxCap) params.append('maxCap', filters.maxCap);
        if (filters.marketCapBucket) params.append('marketCapBucket', filters.marketCapBucket);

        const queryString = params.toString();
        return this.request(`/stocks/filter${queryString ? '?' + queryString : ''}`);
    }

    async getStockBySymbol(symbol) {
        return this.request(`/stocks/symbol/${symbol}`);
    }
}

// Create a singleton instance
const api = new APIService();

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.api = api;
}

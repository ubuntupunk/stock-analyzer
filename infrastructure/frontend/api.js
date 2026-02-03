// API Service Layer
// Handles all communication with the backend Lambda functions

class APIService {
    constructor() {
        this.baseURL = config.apiEndpoint;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        // Get auth token if available
        let authToken = null;
        if (window.authManager) {
            authToken = await window.authManager.getAuthToken();
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
        
        try {
            const response = await fetch(url, {
                ...options,
                headers: headers
            });

            // Handle 401 Unauthorized - redirect to login
            if (response.status === 401) {
                console.warn('Unauthorized request - authentication required');
                if (window.app && window.app.showLoginModal) {
                    window.app.showLoginModal();
                }
                throw new Error('Authentication required');
            }

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // Stock Data APIs
    async getStockMetrics(symbol) {
        return this.request(`/api/stock/metrics?symbol=${symbol}`);
    }

    async getStockPrice(symbol) {
        return this.request(`/api/stock/price?symbol=${symbol}`);
    }

    async getStockPriceHistory(symbol, period = "3mo") {
        return this.request(`/api/stock/price?symbol=${symbol}&period=${period}`);
    }

    async getStockPriceHistoryRange(symbol, startDate, endDate) {
        return this.request(`/api/stock/price?symbol=${symbol}&startDate=${startDate}&endDate=${endDate}`);
    }

    async getAnalystEstimates(symbol) {
        return this.request(`/api/stock/estimates?symbol=${symbol}`);
    }

    async getFinancialStatements(symbol) {
        console.log('=== API: getFinancialStatements START ===');
        console.log('API: Requesting financials for symbol:', symbol);
        console.log('API: Request URL:', `${this.baseURL}/api/stock/financials?symbol=${symbol}`);
        
        try {
            const data = await this.request(`/api/stock/financials?symbol=${symbol}`);
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
        return this.request(`/api/stock/factors?symbol=${symbol}`);
    }

    async getStockNews(symbol) {
        return this.request(`/api/stock/news?symbol=${symbol}`);
    }

    // Batch Stock Data APIs (NEW - for concurrent fetching)
    async getBatchStockPrices(symbols) {
        const symbolsParam = Array.isArray(symbols) ? symbols.join(',') : symbols;
        return this.request(`/api/stock/batch/prices?symbols=${symbolsParam}`);
    }

    async getBatchStockMetrics(symbols) {
        const symbolsParam = Array.isArray(symbols) ? symbols.join(',') : symbols;
        return this.request(`/api/stock/batch/metrics?symbols=${symbolsParam}`);
    }

    async getBatchAnalystEstimates(symbols) {
        const symbolsParam = Array.isArray(symbols) ? symbols.join(',') : symbols;
        return this.request(`/api/stock/batch/estimates?symbols=${symbolsParam}`);
    }

    async getBatchFinancialStatements(symbols) {
        const symbolsParam = Array.isArray(symbols) ? symbols.join(',') : symbols;
        return this.request(`/api/stock/batch/financials?symbols=${symbolsParam}`);
    }

    // Screening APIs
    async screenStocks(criteria) {
        return this.request('/api/screen', {
            method: 'POST',
            body: JSON.stringify({ criteria })
        });
    }

    async saveFactor(factorData) {
        return this.request('/api/factors', {
            method: 'POST',
            body: JSON.stringify(factorData)
        });
    }

    async getUserFactors() {
        return this.request('/api/factors');
    }

    // DCF Analysis
    async calculateDCF(params) {
        return this.request('/api/dcf', {
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
        return this.request('/api/watchlist');
    }

    async addToWatchlist(stockData) {
        return this.request('/api/watchlist', {
            method: 'POST',
            body: JSON.stringify(stockData)
        });
    }

    async updateWatchlistItem(symbol, updates) {
        return this.request('/api/watchlist', {
            method: 'PUT',
            body: JSON.stringify({ symbol, updates })
        });
    }

    async removeFromWatchlist(symbol) {
        return this.request(`/api/watchlist?symbol=${symbol}`, {
            method: 'DELETE'
        });
    }

    // Stock Universe APIs
    async searchStocks(query, limit = 20) {
        return this.request(`/api/stocks/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    }

    async getPopularStocks(limit = 10) {
        return this.request(`/api/stocks/popular?limit=${limit}`);
    }

    async getSectors() {
        return this.request('/api/stocks/sectors');
    }

    async filterStocks(filters = {}) {
        const params = new URLSearchParams();
        if (filters.sector) params.append('sector', filters.sector);
        if (filters.minCap) params.append('minCap', filters.minCap);
        if (filters.maxCap) params.append('maxCap', filters.maxCap);
        if (filters.marketCapBucket) params.append('marketCapBucket', filters.marketCapBucket);
        
        const queryString = params.toString();
        return this.request(`/api/stocks/filter${queryString ? '?' + queryString : ''}`);
    }

    async getStockBySymbol(symbol) {
        return this.request(`/api/stocks/symbol/${symbol}`);
    }
}

// Create a singleton instance
const api = new APIService();

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.api = api;
}

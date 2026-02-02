// Stock Management Module
// Handles stock selection, validation, and preloading

class StockManager {
    constructor(dataManager, eventBus) {
        this.dataManager = dataManager;
        this.eventBus = eventBus;
        this.currentSymbol = null;
        this.searchResults = [];
        this.popularStocks = [];
        this.loadingPopularStocks = false;
        this.pricesLoaded = false;
    }

    /**
     * Search for and select a stock
     * @param {string} symbol - Stock symbol to search for
     * @param {string} targetTab - Optional target tab to switch to (default: 'metrics')
     */
    async searchStock(symbol, targetTab = 'metrics') {
        const validation = Validators.validateStockSymbol(symbol);
        if (!validation.isValid) {
            this.eventBus.emit('error', { message: validation.error, type: 'validation' });
            return;
        }

        const cleanSymbol = validation.symbol;
        console.log('Stock selected:', cleanSymbol, 'targetTab:', targetTab);
        
        this.currentSymbol = cleanSymbol;
        
        // Update stock symbol display
        this.updateStockSymbolDisplay();
        
        // Emit stock selection event with target tab
        this.eventBus.emit('stock:selected', { symbol: cleanSymbol, targetTab });
        
        // Preload data for all tabs (non-blocking, fires and forgets)
        // This ensures instant navigation when switching tabs later
        this.preloadStockData(cleanSymbol).catch(err => {
            console.warn('Preload failed (non-blocking):', err.message);
        });
        
        // Switch to target tab (default: metrics) - now returns immediately
        this.eventBus.emit('tab:switch', { tabName: targetTab });
        
        // Hide search results
        this.hideSearchResults();
    }

    /**
     * Select a stock (alias for searchStock)
     * @param {string} symbol - Stock symbol to select
     * @param {string} targetTab - Optional target tab to switch to
     */
    selectStock(symbol, targetTab = 'metrics') {
        this.searchStock(symbol, targetTab);
    }

    /**
     * Preload data for all tabs to ensure instant navigation
     * @param {string} symbol - Stock symbol to preload data for
     */
    async preloadStockData(symbol) {
        console.log('Preloading data for stock:', symbol);
        
        // Preload all stock data in parallel for better UX
        const dataPromises = [
            this.dataManager.loadStockData(symbol, 'metrics'),
            this.dataManager.loadStockData(symbol, 'financials'),
            this.dataManager.loadStockData(symbol, 'analyst-estimates'),
            this.dataManager.loadStockData(symbol, 'stock-analyser'),
            this.dataManager.loadStockData(symbol, 'factors'),
            this.dataManager.loadStockData(symbol, 'news')
        ];

        try {
            await Promise.allSettled(dataPromises);
            console.log('All stock data preloaded for:', symbol);
            this.eventBus.emit('stock:dataPreloaded', { symbol });
        } catch (error) {
            console.error('Error preloading stock data:', error);
            this.eventBus.emit('error', { message: 'Failed to preload stock data', type: 'data' });
        }
    }

    /**
     * Update stock symbol display in all relevant places
     */
    updateStockSymbolDisplay() {
        const stockSymbolElements = document.querySelectorAll('#stockSymbol, .current-stock-symbol');
        stockSymbolElements.forEach(element => {
            if (element) {
                element.textContent = this.currentSymbol;
            }
        });
    }

    /**
     * Perform stock search with autocomplete
     * @param {string} query - Search query
     */
    async performStockSearch(query) {
        const validation = Validators.validateSearchQuery(query);
        if (!validation.isValid) {
            this.searchResults = [];
            this.hideSearchResults();
            return;
        }
        
        try {
            const results = await this.dataManager.searchStocks(validation.query, 10);
            this.searchResults = results;
            this.showSearchResults();
        } catch (error) {
            console.error('Stock search failed:', error);
            this.eventBus.emit('error', { message: 'Failed to search stocks', type: 'search' });
        }
    }

    /**
     * Display search results
     */
    showSearchResults() {
        const resultsContainer = document.getElementById('searchResults');
        if (!resultsContainer || this.searchResults.length === 0) return;
        
        const resultsHtml = this.searchResults.map(stock => `
            <div class="search-result-item" onclick="window.stockManager.selectStock('${stock.symbol}')">
                <div class="search-result-symbol">${stock.symbol}</div>
                <div class="search-result-name">${stock.name}</div>
                <div class="search-result-sector">${stock.sector || 'N/A'}</div>
            </div>
        `).join('');
        
        resultsContainer.innerHTML = resultsHtml;
        resultsContainer.style.display = 'block';
    }

    /**
     * Hide search results
     */
    hideSearchResults() {
        const resultsContainer = document.getElementById('searchResults');
        if (resultsContainer) {
            resultsContainer.style.display = 'none';
        }
    }

    /**
     * Load popular stocks
     */
    async loadPopularStocks() {
        console.log('StockManager: loadPopularStocks called');
        
        // Prevent duplicate loading
        if (this.loadingPopularStocks) {
            console.log('StockManager: Already loading popular stocks, skipping duplicate call');
            return;
        }
        
        // If already loaded, just re-render
        if (this.popularStocks && this.popularStocks.length > 0) {
            console.log('StockManager: Popular stocks already loaded, re-rendering');
            // Wait a tiny bit for DOM to be ready
            setTimeout(async () => {
                this.populateSectorFilter();
                this.renderPopularStocks();
                this.setupPopularStocksHandlers();
                // Restore prices after re-rendering (fixes tab switch showing "Loading...")
                // Must await to ensure prices are restored before pricesLoaded flag is set
                await this.loadPopularStockPrices();
            }, 100);
            return;
        }
        
        this.loadingPopularStocks = true;
        
        try {
            console.log('StockManager: Calling dataManager.getPopularStocks(12)');
            const stocks = await this.dataManager.getPopularStocks(12);
            console.log('StockManager: Received stocks:', stocks);
            this.popularStocks = stocks;
            this.populateSectorFilter();
            this.renderPopularStocks();
            // Setup sector filter handler after DOM is loaded
            this.setupPopularStocksHandlers();
            this.eventBus.emit('popularStocks:loaded', { stocks });
            
            // Load prices asynchronously for each stock
            this.loadPopularStockPrices();
        } catch (error) {
            console.error('Failed to load popular stocks:', error);
            this.eventBus.emit('popularStocks:error', { error: error.message });
        } finally {
            this.loadingPopularStocks = false;
        }
    }

    /**
     * Populate sector filter with available sectors
     */
    populateSectorFilter() {
        const sectorFilter = document.getElementById('sectorFilter');
        if (!sectorFilter) return;

        // Get unique sectors from the data
        const uniqueSectors = [...new Set(this.popularStocks.map(stock => stock.sector).filter(Boolean))];
        console.log('StockManager: Populating sector filter with:', uniqueSectors);

        // Clear existing options except the first one
        sectorFilter.innerHTML = '<option value="">All Sectors</option>';

        // Add sector options
        uniqueSectors.sort().forEach(sector => {
            const option = document.createElement('option');
            option.value = sector;
            option.textContent = sector;
            sectorFilter.appendChild(option);
        });
    }

    /**
     * Render popular stocks in the UI
     */
    renderPopularStocks() {
        console.log('StockManager: renderPopularStocks called');
        let container = document.getElementById('popularStocksGrid');
        
        // Retry mechanism for finding container (sections load dynamically)
        let retries = 0;
        const maxRetries = 10;
        const retryDelay = 100;
        
        const tryRender = () => {
            container = document.getElementById('popularStocksGrid');
            console.log('StockManager: container found:', !!container);
            
            if (!container && retries < maxRetries) {
                retries++;
                console.log(`StockManager: Retrying to find container (${retries}/${maxRetries})`);
                setTimeout(tryRender, retryDelay);
                return;
            }
            
            if (!container) {
                console.warn('StockManager: popularStocksGrid container not found after retries');
                return;
            }

            console.log('StockManager: Rendering popular stocks:', this.popularStocks);
            const currentView = this.currentPopularStocksView || 'grid';
            
            if (this.popularStocks.length === 0) {
                container.innerHTML = '<p class="empty-message">No popular stocks available.</p>';
                return;
            }

            const stocksHtml = this.popularStocks.map(stock => {
                const isOnWatchlist = window.watchlistManager?.isOnWatchlist(stock.symbol);
                return currentView === 'grid' ? `
                    <div class="stock-card" data-symbol="${stock.symbol}">
                        <div class="stock-header">
                            <div class="stock-symbol">${stock.symbol}</div>
                            <div class="stock-price" id="price-${stock.symbol}">
                                <span class="price-loading">Loading...</span>
                            </div>
                        </div>
                        <div class="stock-info">
                            <div class="stock-name">${stock.name}</div>
                            <div class="stock-sector">${stock.sector || 'N/A'}</div>
                        </div>
                        <div class="stock-change" id="change-${stock.symbol}">
                            <span class="change-loading">--</span>
                        </div>
                        <div class="stock-actions">
                            <button class="btn-primary view-details-btn" onclick="window.stockManager.selectStock('${stock.symbol}')">
                                <i class="fas fa-chart-line"></i> View
                            </button>
                            <button class="add-to-watchlist-btn ${isOnWatchlist ? 'added' : ''}" 
                                    onclick="window.watchlistManager.toggleWatchlist('${stock.symbol}')" 
                                    title="${isOnWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}">
                                <i class="${isOnWatchlist ? 'fas fa-star' : 'far fa-star'}"></i>
                            </button>
                        </div>
                    </div>
                ` : `
                    <div class="stock-list-item" data-symbol="${stock.symbol}">
                        <div class="stock-list-info">
                            <div class="stock-list-symbol">${stock.symbol}</div>
                            <div class="stock-list-name">${stock.name}</div>
                            <div class="stock-list-sector">${stock.sector || 'N/A'}</div>
                        </div>
                        <div class="stock-list-price" id="price-${stock.symbol}">
                            <span class="price-loading">Loading...</span>
                        </div>
                        <div class="stock-list-change" id="change-${stock.symbol}">
                            <span class="change-loading">--</span>
                        </div>
                        <div class="stock-list-actions">
                            <button class="btn-primary view-details-btn" onclick="window.stockManager.selectStock('${stock.symbol}')">
                                <i class="fas fa-chart-line"></i> View
                            </button>
                            <button class="add-to-watchlist-btn ${isOnWatchlist ? 'added' : ''}" 
                                    onclick="window.watchlistManager.toggleWatchlist('${stock.symbol}')" 
                                    title="${isOnWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}">
                                <i class="${isOnWatchlist ? 'fas fa-star' : 'far fa-star'}"></i>
                            </button>
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = stocksHtml;
            console.log('StockManager: Popular stocks rendered successfully');

            // Restore prices if already loaded (fixes view switch losing prices)
            if (this.pricesLoaded) {
                this.restorePricesToUI();
            }
        };
        
        tryRender();
    }

    /**
     * Restore prices to UI after re-rendering (e.g., view switch)
     */
    restorePricesToUI() {
        console.log('StockManager: Restoring prices to UI');
        
        this.popularStocks.forEach(stock => {
            if (stock.price) {
                this.updateStockPriceInUI(stock.symbol, stock.price, stock.change, stock.changePercent);
            }
        });
    }

    /**
     * Get current stock symbol
     * @returns {string|null} Current stock symbol
     */
    getCurrentSymbol() {
        return this.currentSymbol;
    }

    /**
     * Check if a stock is currently selected
     * @returns {boolean} Whether a stock is selected
     */
    hasCurrentStock() {
        return this.currentSymbol !== null;
    }

    /**
     * Clear current stock selection
     */
    clearCurrentStock() {
        this.currentSymbol = null;
        this.updateStockSymbolDisplay();
        this.eventBus.emit('stock:cleared');
    }

    /**
     * Get search results
     * @returns {Array} Current search results
     */
    getSearchResults() {
        return this.searchResults;
    }

    /**
     * Set popular stocks view mode (grid/list)
     * @param {string} viewMode - View mode ('grid' or 'list')
     */
    setPopularStocksView(viewMode) {
        const container = document.getElementById('popularStocksGrid');
        if (!container) return;

        // Update view toggle buttons
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-view') === viewMode) {
                btn.classList.add('active');
            }
        });

        // Update container class
        container.className = viewMode === 'list' ? 'popular-stocks-list' : 'popular-stocks-grid';

        // Re-render stocks with new view
        this.renderPopularStocks();
    }

    /**
     * Filter popular stocks by sector
     */
    filterPopularStocksBySector() {
        const sectorFilter = document.getElementById('sectorFilter');
        if (!sectorFilter) return;

        const selectedSector = sectorFilter.value;
        console.log('StockManager: Filtering by sector:', selectedSector);
        console.log('StockManager: Available stocks:', this.popularStocks);
        
        // Log unique sectors in the data
        const uniqueSectors = [...new Set(this.popularStocks.map(stock => stock.sector).filter(Boolean))];
        console.log('StockManager: Unique sectors in data:', uniqueSectors);
        
        let filteredStocks = this.popularStocks;

        if (selectedSector) {
            filteredStocks = this.popularStocks.filter(stock => {
                // Case-insensitive comparison and handle null/undefined
                const stockSector = (stock.sector || '').toLowerCase().trim();
                const filterSector = selectedSector.toLowerCase().trim();
                
                // Exact match
                if (stockSector === filterSector) {
                    return true;
                }
                
                // Partial match (e.g., "tech" matches "technology")
                if (stockSector.includes(filterSector) || filterSector.includes(stockSector)) {
                    return true;
                }
                
                return false;
            });
        }

        console.log('StockManager: Filtered stocks:', filteredStocks);
        this.renderFilteredStocks(filteredStocks);
    }

    /**
     * Render filtered popular stocks
     * @param {Array} stocks - Filtered stocks to render
     */
    renderFilteredStocks(stocks) {
        console.log('StockManager: Rendering filtered stocks:', stocks.length);
        
        const container = document.getElementById('popularStocksGrid');
        if (!container) {
            console.warn('StockManager: popularStocksGrid container not found');
            return;
        }

        if (stocks.length === 0) {
            container.innerHTML = '<p class="empty-message">No stocks found for this sector</p>';
            return;
        }

        const viewMode = container.className.includes('list') ? 'list' : 'grid';
        const stockHtml = stocks.map(stock => {
            const isOnWatchlist = window.watchlistManager?.isOnWatchlist(stock.symbol) || false;
            return viewMode === 'list' ? `
                <div class="stock-list-item ${isOnWatchlist ? 'in-watchlist' : ''}" data-symbol="${stock.symbol}">
                    <div class="stock-list-info">
                        <div class="stock-list-symbol">${stock.symbol}</div>
                        <div class="stock-list-name">${stock.name}</div>
                        <div class="stock-list-sector">${stock.sector || 'N/A'}</div>
                    </div>
                    <div class="stock-list-actions">
                        <span class="stock-list-price">${stock.price ? Formatters.formatStockPrice(stock.price) : 'N/A'}</span>
                        <button class="add-to-watchlist-btn ${isOnWatchlist ? 'added' : ''}" 
                                onclick="window.watchlistManager.toggleWatchlist('${stock.symbol}')"
                                ${isOnWatchlist ? 'title="Remove from watchlist"' : 'title="Add to watchlist"'}>
                            <i class="${isOnWatchlist ? 'fas fa-star' : 'far fa-star'}"></i>
                        </button>
                    </div>
                </div>
            ` : `
                <div class="stock-card ${isOnWatchlist ? 'in-watchlist' : ''}" data-symbol="${stock.symbol}" onclick="window.stockManager.selectStock('${stock.symbol}')">
                    <div class="watchlist-indicator">
                        <i class="fas fa-star"></i>
                    </div>
                    <div class="stock-symbol">${stock.symbol}</div>
                    <div class="stock-name">${stock.name}</div>
                    <div class="stock-sector">${stock.sector || 'N/A'}</div>
                    <div class="stock-price">${stock.price ? Formatters.formatStockPrice(stock.price) : 'N/A'}</div>
                    <button class="add-to-watchlist-btn ${isOnWatchlist ? 'added' : ''}" 
                            onclick="event.stopPropagation(); window.watchlistManager.toggleWatchlist('${stock.symbol}')"
                            ${isOnWatchlist ? 'title="Remove from watchlist"' : 'title="Add to watchlist"'}>
                        <i class="${isOnWatchlist ? 'fas fa-star' : 'far fa-star'}"></i>
                    </button>
                </div>
            `;
        }).join('');

        container.innerHTML = stockHtml;
        console.log('StockManager: Filtered stocks rendered successfully');
    }

    /**
     * Load prices for popular stocks
     * Uses BATCH API for concurrent fetching (optimized)
     */
    async loadPopularStockPrices() {
        // Check if we have prices already loaded - restore them to UI without API calls
        const hasCachedPrices = this.popularStocks.some(stock => stock.price);
        
        if (hasCachedPrices && this.pricesLoaded) {
            console.log('StockManager: Prices already loaded, restoring to UI');
            this.restorePricesToUI();
            return;
        }
        
        // Prevent duplicate API calls
        if (this.apiPricesLoading) {
            console.log('StockManager: API prices already loading, skipping');
            return;
        }
        
        console.log('StockManager: Loading prices for popular stocks using BATCH API');
        this.apiPricesLoading = true;
        this.pricesLoaded = true;
        
        // Extract all symbols
        const symbols = this.popularStocks.map(stock => stock.symbol);
        
        if (symbols.length === 0) {
            console.log('StockManager: No symbols to load prices for');
            this.apiPricesLoading = false;
            return;
        }
        
        try {
            // Use batch API to fetch all prices concurrently
            console.log(`StockManager: Fetching batch prices for ${symbols.length} stocks:`, symbols);
            const batchPrices = await api.getBatchStockPrices(symbols);
            console.log('StockManager: Batch price data received:', batchPrices);
            
            // Update each stock with its price data
            Object.entries(batchPrices).forEach(([symbol, priceData]) => {
                // Find the stock in our list
                const stock = this.popularStocks.find(s => s.symbol === symbol);
                
                if (stock && priceData && !priceData.error) {
                    const price = priceData.price || priceData.currentPrice;
                    const change = priceData.change;
                    const changePercent = priceData.change_percent;
                    
                    if (price) {
                        // Update the stock object
                        stock.price = price;
                        stock.change = change;
                        stock.changePercent = changePercent;
                        
                        // Update the UI
                        this.updateStockPriceInUI(symbol, price, change, changePercent);
                    }
                } else if (priceData && priceData.error) {
                    console.warn(`Failed to load price for ${symbol}:`, priceData.error);
                }
            });
            
            console.log('StockManager: Finished loading batch prices');
        } catch (error) {
            console.error('StockManager: Failed to load batch prices:', error);
            // Fallback to sequential loading if batch fails
            console.log('StockManager: Falling back to sequential price loading');
            await this.loadPopularStockPricesSequential();
        } finally {
            this.apiPricesLoading = false;
        }
    }
    
    /**
     * Fallback: Load prices sequentially (legacy method)
     */
    async loadPopularStockPricesSequential() {
        console.log('StockManager: Loading prices sequentially');
        const delay = 500; // 500ms delay between requests
        
        for (let i = 0; i < this.popularStocks.length; i++) {
            const stock = this.popularStocks[i];
            
            try {
                const priceData = await api.getStockPrice(stock.symbol);
                const price = priceData.price || priceData.currentPrice;
                
                if (priceData && price) {
                    stock.price = price;
                    stock.change = priceData.change;
                    stock.changePercent = priceData.change_percent;
                    this.updateStockPriceInUI(stock.symbol, price, priceData.change, priceData.change_percent);
                }
            } catch (error) {
                console.warn(`Failed to load price for ${stock.symbol}:`, error);
            }
            
            if (i < this.popularStocks.length - 1) {
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    
    /**
     * Update stock price in the UI
     * @param {string} symbol - Stock symbol
     * @param {number} price - Stock price
     * @param {number} change - Price change
     * @param {number} changePercent - Price change percentage
     */
    updateStockPriceInUI(symbol, price, change = null, changePercent = null) {
        // Find all price elements for this symbol
        const stockCards = document.querySelectorAll(`[data-symbol="${symbol}"]`);
        console.log(`Updating UI for ${symbol}: found ${stockCards.length} cards, price: ${price}`);
        
        if (stockCards.length === 0) {
            console.warn(`No card found for ${symbol} - it may not be rendered yet`);
        }
        
        stockCards.forEach(card => {
            // Determine if price change is positive or negative
            const isPositive = change >= 0;
            const changeClass = isPositive ? 'positive' : 'negative';
            
            // Update price
            const priceElement = card.querySelector('.stock-price, .stock-list-price');
            if (priceElement) {
                priceElement.textContent = Formatters.formatStockPrice(price);
                priceElement.classList.add('loaded');
                priceElement.classList.add(changeClass);
            }
            
            // Update change if available
            if (change !== null && changePercent !== null) {
                const changeElement = card.querySelector('.stock-change, .stock-list-change');
                if (changeElement) {
                    changeElement.innerHTML = `
                        <span class="${changeClass}">
                            ${isPositive ? '+' : ''}${Formatters.formatStockPrice(change)} 
                            (${isPositive ? '+' : ''}${changePercent.toFixed(2)}%)
                        </span>
                    `;
                    changeElement.classList.add('loaded');
                }
            }
        });
    }

    /**
     * Get popular stocks
     * @returns {Array} Popular stocks list
     */
    getPopularStocks() {
        return this.popularStocks;
    }

    /**
     * Initialize stock manager
     */
    initialize() {
        this.setupEventListeners();
        this.setupSearchHandlers();
        // Don't setup popular stocks handlers here - they will be setup when popular stocks are loaded
    }

    /**
     * Setup popular stocks handlers
     */
    setupPopularStocksHandlers() {
        // Sector filter change handler
        const sectorFilter = document.getElementById('sectorFilter');
        if (sectorFilter) {
            // Remove existing listener to prevent duplicates
            const newSectorFilter = sectorFilter.cloneNode(true);
            sectorFilter.parentNode.replaceChild(newSectorFilter, sectorFilter);
            
            newSectorFilter.addEventListener('change', () => {
                console.log('StockManager: Sector filter changed to:', newSectorFilter.value);
                this.filterPopularStocksBySector();
            });
            console.log('StockManager: Sector filter event listener attached');
        } else {
            console.warn('StockManager: Sector filter element not found');
        }
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        // Clear search timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        // Clear popular stocks
        this.popularStocks = [];
        this.searchResults = [];
        this.currentSymbol = null;
        console.log('StockManager: Cleaned up');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StockManager;
} else {
    window.StockManager = StockManager;
}

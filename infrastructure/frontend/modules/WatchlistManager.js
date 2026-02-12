// Watchlist Management Module
// Handles watchlist CRUD operations, UI updates, and price tracking

class WatchlistManager {
    constructor(dataManager, eventBus) {
        this.dataManager = dataManager;
        this.eventBus = eventBus;
        this.watchlist = [];
        this.priceUpdateInterval = null;
        this.priceUpdateFrequency = 60000; // 1 minute
        this._pricesLoading = false; // Guard against duplicate price loading
        this._pricesLoadingPromise = null; // Promise for in-progress price load
        this._watchlistLoading = false; // Guard against concurrent loadWatchlist calls
        this._watchlistRendered = false; // Track if watchlist has been rendered with prices
        this._watchlistLoadPromise = null; // Promise for in-progress watchlist load
        this._renderCount = 0; // Track number of renders

        // Subscribe to watchlist events
        this.setupEventListeners();
    }

    /**
     * Setup event listeners for watchlist functionality
     */
    setupEventListeners() {
        this.eventBus.on('watchlist:load', () => {
            this.loadWatchlist();
        });

        this.eventBus.on('watchlist:add', ({ stockData }) => {
            this.addToWatchlist(stockData);
        });

        this.eventBus.on('watchlist:remove', ({ symbol }) => {
            this.removeFromWatchlist(symbol);
        });

        this.eventBus.on('watchlist:toggle', ({ symbol }) => {
            this.toggleWatchlist(symbol);
        });

        this.eventBus.on('stock:selected', ({ symbol }) => {
            this.updateWatchlistButtonState(symbol);
        });
    }

    /**
     * Initialize watchlist functionality
     */
    initialize() {
        this.setupWatchlistHandlers();
        this.startPriceUpdates();
    }

    /**
     * Setup watchlist UI handlers
     */
    setupWatchlistHandlers() {
        // Watchlist toggle button (exists in tabs, so safe to attach here)
        const watchlistToggle = document.getElementById('watchlistToggle');
        if (watchlistToggle) {
            watchlistToggle.addEventListener('click', () => {
                const currentSymbol = window.stockManager?.getCurrentSymbol();
                if (currentSymbol) {
                    this.toggleWatchlist(currentSymbol);
                }
            });
        }

        // Note: Add to watchlist button handler is set up in setupAddStockButtonHandler()
        // which is called after the watchlist section is loaded in DOM
    }

    /**
     * Setup the Add Stock button handler after section is loaded
     * This is called from renderWatchlist() after the section exists
     */
    setupAddStockButtonHandler() {
        const addToWatchlistBtn = document.getElementById('addToWatchlistBtn');
        if (addToWatchlistBtn) {
            // Remove any existing listeners to avoid duplicates
            const newBtn = addToWatchlistBtn.cloneNode(true);
            addToWatchlistBtn.parentNode.replaceChild(newBtn, addToWatchlistBtn);

            newBtn.addEventListener('click', () => {
                this.showAddToWatchlistDialog();
            });
            console.log('WatchlistManager: Add Stock button handler attached');
        } else {
            console.warn('WatchlistManager: addToWatchlistBtn not found');
        }
    }

    /**
     * Load watchlist from API
     */
    async loadWatchlist() {
        console.log('>>> loadWatchlist()');

        if (!window.authManager) {
            console.warn('AuthManager not available, cannot check authentication status for watchlist.');
            return;
        }

        const isAuthenticated = await window.authManager.isAuthenticated();
        if (!isAuthenticated) {
            console.log('User not authenticated, skipping watchlist load.');
            // Optionally, clear existing watchlist data or show a message to the user
            this.watchlist = [];
            this.renderWatchlist(); // Render an empty watchlist or a login prompt
            return;
        }

        // If already loading, wait for it
        if (this._watchlistLoading && this._watchlistLoadPromise) {
            console.log('>>> loadWatchlist: Waiting for in-progress load');
            return this._watchlistLoadPromise;
        }

        this._watchlistLoading = true;
        const loadPromise = this._doLoadWatchlist();
        this._watchlistLoadPromise = loadPromise;

        try {
            await loadPromise;
        } finally {
            this._watchlistLoading = false;
            this._watchlistLoadPromise = null;
        }
    }

    /**
     * Internal load watchlist implementation
     */
    async _doLoadWatchlist() {
        try {
            this.eventBus.emit('watchlist:loading');

            console.log('>>> _doLoadWatchlist: Loading from dataManager');

            const watchlistData = await this.dataManager.loadWatchlist();
            this.watchlist = watchlistData || [];

            console.log('>>> _doLoadWatchlist: Loaded', this.watchlist.length, 'items');

            // Ensure all items have proper names
            this.watchlist = this.watchlist.map(item => ({
                ...item,
                name: item.name || this.getStockName(item.symbol)
            }));

            // Wait for watchlist section to be loaded in DOM if not present yet
            await this.waitForWatchlistSection();

            // Check if watchlist section is in DOM
            const container = document.getElementById('watchlistGrid');
            const hasContent = container && container.children.length > 0;

            console.log('>>> _doLoadWatchlist: container=' + !!container + ', hasContent=' + hasContent);

            if (container && !hasContent) {
                // Section exists but empty - render for first time
                console.log('>>> _doLoadWatchlist: Rendering watchlist');
                await this.renderWatchlist();
            } else if (hasContent) {
                // Already has content - just update buttons and reload prices
                console.log('>>> _doLoadWatchlist: Already rendered, updating buttons and reloading prices');
                this.updateAllWatchlistButtons();
                // Ensure Add Stock button handler is set up
                this.setupAddStockButtonHandler();
                await this.loadWatchlistPrices();
            } else {
                // Section not loaded yet (shouldn't happen after waitForWatchlistSection)
                console.log('>>> _doLoadWatchlist: Section not loaded after wait, rendering anyway');
                // Ensure Add Stock button handler is set up
                this.setupAddStockButtonHandler();
                await this.renderWatchlist();
            }

            this.eventBus.emit('watchlist:loaded', { watchlist: this.watchlist });
            
            // Update the watchlist button state for the currently selected stock
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                this.updateWatchlistButtonState(currentSymbol);
            }
        } catch (error) {
            console.error('>>> _doLoadWatchlist: Failed:', error);
            this.eventBus.emit('watchlist:error', { error: error.message });
        }
    }

    /**
     * Wait for watchlist section to be loaded in DOM
     */
    async waitForWatchlistSection() {
        console.log('>>> waitForWatchlistSection: Checking if section exists');
        const maxAttempts = 50; // 2.5 seconds max
        let attempts = 0;

        while (!document.getElementById('watchlistContainer') && attempts < maxAttempts) {
            console.log('>>> waitForWatchlistSection: Waiting... attempt', attempts + 1);
            await new Promise(resolve => setTimeout(resolve, 50));
            attempts++;
        }

        const exists = !!document.getElementById('watchlistContainer');
        console.log('>>> waitForWatchlistSection: Section exists:', exists, 'after', attempts * 50, 'ms');
        return exists;
    }

    /**
     * Add stock to watchlist
     * @param {object} stockData - Stock data to add
     */
    async addToWatchlist(stockData) {
        try {
            const validation = Validators.validateWatchlistItem(stockData);
            if (!validation.isValid) {
                this.showNotification(validation.error, 'error');
                return;
            }

            this.eventBus.emit('watchlist:adding', { stockData });

            const result = await this.dataManager.addToWatchlist(stockData);

            if (result.success || result.status === 'success') {
                // Ensure name is properly set
                const stockName = stockData.name || this.getStockName(stockData.symbol);

                // Add to local watchlist
                const watchlistItem = {
                    symbol: stockData.symbol,
                    name: stockName,
                    addedAt: new Date().toISOString(),
                    notes: stockData.notes || '',
                    alertPrice: stockData.alertPrice || null,
                    tags: stockData.tags || []
                };

                this.watchlist.push(watchlistItem);
                this.renderWatchlist();
                this.updateStockCardWatchlistButtons(stockData.symbol);
                this.updateWatchlistButtonState(stockData.symbol);

                this.showNotification(`${stockData.symbol} added to watchlist`, 'success');
                this.eventBus.emit('watchlist:added', { stockData, item: watchlistItem });
            } else {
                throw new Error(result.error || 'Failed to add to watchlist');
            }
        } catch (error) {
            console.error('Failed to add to watchlist:', error);
            this.showNotification(`Failed to add to watchlist: ${error.message}`, 'error');
            this.eventBus.emit('watchlist:error', { error: error.message });
        }
    }

    /**
     * Remove stock from watchlist
     * @param {string} symbol - Stock symbol to remove
     */
    async removeFromWatchlist(symbol) {
        try {
            this.eventBus.emit('watchlist:removing', { symbol });

            const result = await this.dataManager.removeFromWatchlist(symbol);

            if (result.success || result.status === 'success') {
                // Remove from local watchlist
                this.watchlist = this.watchlist.filter(item => item.symbol !== symbol);
                this.renderWatchlist();
                this.updateStockCardWatchlistButtons(symbol);
                this.updateWatchlistButtonState(symbol);

                this.showNotification(`${symbol} removed from watchlist`, 'success');
                this.eventBus.emit('watchlist:removed', { symbol });
            } else {
                throw new Error(result.error || 'Failed to remove from watchlist');
            }
        } catch (error) {
            console.error('Failed to remove from watchlist:', error);
            this.showNotification(`Failed to remove from watchlist: ${error.message}`, 'error');
            this.eventBus.emit('watchlist:error', { error: error.message });
        }
    }

    /**
     * Toggle watchlist status for a stock
     * @param {string} symbol - Stock symbol to toggle
     */
    async toggleWatchlist(symbol) {
        console.log('WatchlistManager: toggleWatchlist called for:', symbol);
        console.log('WatchlistManager: Current watchlist before toggle:', this.watchlist.map(i => i.symbol));

        const isOnWatchlist = this.watchlist.some(item => item.symbol === symbol);
        console.log('WatchlistManager: Is on watchlist?', isOnWatchlist);

        if (isOnWatchlist) {
            await this.removeFromWatchlist(symbol);
        } else {
            // Get stock info from popular stocks list
            let stockName = this.getStockName(symbol);

            const stockData = {
                symbol: symbol,
                name: stockName,
                notes: '',
                alertPrice: null,
                tags: []
            };
            await this.addToWatchlist(stockData);
        }

        console.log('WatchlistManager: Watchlist after toggle:', this.watchlist.map(i => i.symbol));
    }

    /**
     * Get stock name from various sources
     * @param {string} symbol - Stock symbol
     * @returns {string} Stock name
     */
    getStockName(symbol) {
        // Try to get name from popular stocks
        const popularStocks = window.stockManager?.getPopularStocks() || [];
        const stock = popularStocks.find(s => s.symbol === symbol);
        if (stock?.name) {
            return stock.name;
        }

        // Try to get name from search results
        const searchResults = window.stockManager?.getSearchResults() || [];
        const searchResult = searchResults.find(s => s.symbol === symbol);
        if (searchResult?.name) {
            return searchResult.name;
        }

        // Try to get name from current watchlist (if editing)
        const watchlistItem = this.watchlist.find(item => item.symbol === symbol);
        if (watchlistItem?.name && watchlistItem.name !== symbol) {
            return watchlistItem.name;
        }

        // Fallback to symbol - use a more readable format
        return this.formatSymbolAsName(symbol);
    }

    /**
     * Format symbol as a readable name
     * @param {string} symbol - Stock symbol
     * @returns {string} Formatted name
     */
    formatSymbolAsName(symbol) {
        // Common stock name mappings
        const stockNames = {
            'AAPL': 'Apple Inc.',
            'MSFT': 'Microsoft Corporation',
            'GOOGL': 'Alphabet Inc.',
            'AMZN': 'Amazon.com Inc.',
            'NVDA': 'NVIDIA Corporation',
            'META': 'Meta Platforms Inc.',
            'TSLA': 'Tesla Inc.',
            'JPM': 'JPMorgan Chase & Co.',
            'V': 'Visa Inc.',
            'JNJ': 'Johnson & Johnson',
            'WMT': 'Walmart Inc.',
            'PG': 'Procter & Gamble Co.',
            'MA': 'Mastercard Inc.',
            'HD': 'The Home Depot Inc.',
            'DIS': 'The Walt Disney Company',
            'NFLX': 'Netflix Inc.',
            'ADBE': 'Adobe Inc.',
            'CRM': 'Salesforce Inc.',
            'PYPL': 'PayPal Holdings Inc.',
            'INTC': 'Intel Corporation',
            'AMD': 'Advanced Micro Devices Inc.',
            'QCOM': 'Qualcomm Inc.',
            'TXN': 'Texas Instruments Inc.',
            'NKE': 'Nike Inc.',
            'MCD': "McDonald's Corporation",
            'KO': 'The Coca-Cola Company',
            'PEP': 'PepsiCo Inc.',
            'COST': 'Costco Wholesale Corporation',
            'MRK': 'Merck & Co. Inc.',
            'ABBV': 'AbbVie Inc.',
            'LLY': 'Eli Lilly and Company',
            'UNH': 'UnitedHealth Group Inc.',
            'GS': 'Goldman Sachs Group Inc.',
            'BAC': 'Bank of America Corp.',
            'C': 'Citigroup Inc.',
            'WFC': 'Wells Fargo & Company',
            'MS': 'Morgan Stanley',
            'BLK': 'BlackRock Inc.',
            'SCHW': 'Charles Schwab Corporation',
            'AXP': 'American Express Company',
            'USB': 'U.S. Bancorp',
            'PNC': 'PNC Financial Services Group',
            'TFC': 'Truist Financial Corporation',
            'COF': 'Capital One Financial Corp.',
            'SPGI': 'S&P Global Inc.',
            'MCO': "Moody's Corporation",
            'CME': 'CME Group Inc.',
            'ICE': 'Intercontinental Exchange Inc.',
            'MSCI': 'MSCI Inc.',
            'NDAQ': 'Nasdaq Inc.',
            'CBRE': 'CBRE Group Inc.',
            'DHI': 'D.R. Horton Inc.',
            'LEN': 'Lennar Corporation',
            'PLD': 'Prologis Inc.',
            'AMT': 'American Tower Corporation',
            'EQIX': 'Equinix Inc.',
            'CCI': 'Crown Castle Inc.',
            'PSA': 'Public Storage',
            'SPG': 'Simon Property Group Inc.',
            'O': 'Realty Income Corporation',
            'WELL': 'Welltower Inc.',
            'HCP': 'Healthpeak Properties Inc.',
            'VTR': 'Ventas Inc.',
            'SNY': 'Sanofi',
            'NVS': 'Novartis AG',
            'AZN': 'AstraZeneca PLC',
            'BMY': 'Bristol-Myers Squibb Company',
            'MRK_EU': 'Merck KGaA',
            'GSK': 'GSK PLC',
            'CVS': 'CVS Health Corporation',
            'CI': 'Cigna Group',
            'ELV': 'Elevance Health Inc.',
            'HUM': 'Humana Inc.',
            'CNC': 'Centene Corporation',
            'UNH': 'UnitedHealth Group Inc.',
            'BC': 'Brunswick Corporation',
            'MAR': 'Marriott International Inc.',
            'HLT': 'Hilton Worldwide Holdings Inc.',
            'H': 'Hyatt Hotels Corporation',
            'CCL': 'Carnival Corporation',
            'RCL': 'Royal Caribbean Cruises Ltd.',
            'NCLH': 'Norwegian Cruise Line Holdings Ltd.',
            'DAL': 'Delta Air Lines Inc.',
            'UAL': 'United Airlines Holdings Inc.',
            'AAL': 'American Airlines Group Inc.',
            'LUV': 'Southwest Airlines Co.',
            'ALK': 'Alaska Air Group Inc.',
            'GE': 'General Electric Company',
            'BA': 'The Boeing Company',
            'RTX': 'RTX Corporation',
            'LMT': 'Lockheed Martin Corporation',
            'NOC': 'Northrop Grumman Corporation',
            'GD': 'General Dynamics Corporation',
            'CAT': 'Caterpillar Inc.',
            'DE': 'Deere & Company',
            'MMM': '3M Company',
            'HON': 'Honeywell International Inc.',
            'UPS': 'United Parcel Service Inc.',
            'FDX': 'FedEx Corporation',
            'FDX': 'FedEx Corporation',
        };

        return stockNames[symbol] || symbol;
    }

    /**
     * Format currency
     * @param {number} value - Value to format
     * @returns {string} Formatted currency
     */
    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(value);
    }

    /**
     * Format date
     * @param {string} dateString - Date string
     * @returns {string} Formatted date
     */
    formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
        } catch (error) {
            return dateString;
        }
    }

    /**
     * Update watchlist count
     * @param {number} count - Count to display
     */
    updateWatchlistCount(count) {
        const countEl = document.getElementById('watchlistCount');
        if (countEl) {
            countEl.textContent = count;
        }
    }

    /**
     * Update watchlist timestamp
     */
    updateWatchlistTimestamp() {
        const timestampEl = document.getElementById('watchlistUpdated');
        if (timestampEl) {
            const now = new Date();
            timestampEl.textContent = now.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }

    /**
     * Render watchlist in the UI
     */
    async renderWatchlist() {
        this._renderCount++;
        console.log(`>>> renderWatchlist: Call #${this._renderCount}`);

        const container = document.getElementById('watchlistContainer');
        const grid = document.getElementById('watchlistGrid');
        const empty = document.getElementById('watchlistEmpty');

        if (!container) {
            console.log('>>> renderWatchlist: No container, skipping');
            return;
        }

        if (this.watchlist.length === 0) {
            if (empty) empty.style.display = 'block';
            if (grid) grid.style.display = 'none';
            this.updateWatchlistCount(0);
            // Still setup the Add Stock button handler even when empty
            this.setupAddStockButtonHandler();
            return;
        }

        if (empty) empty.style.display = 'none';
        if (grid) grid.style.display = 'grid';

        // Build watchlist HTML
        const watchlistHtml = this.watchlist.map(item => {
            // Ensure name is set
            const displayName = item.name || this.getStockName(item.symbol);
            // Normalize symbol to lowercase for consistent element IDs
            const symbolId = item.symbol.toUpperCase();

            return `
            <div class="watchlist-item" data-symbol="${symbolId}" data-context="watchlist">
                <div class="watchlist-header">
                    <div class="watchlist-symbol">
                        <span class="symbol">${symbolId}</span>
                        <span class="name">${displayName}</span>
                    </div>
                    <button class="watchlist-remove" onclick="window.watchlistManager.removeFromWatchlist('${symbolId}')" title="Remove from watchlist">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="watchlist-content">
                    <div class="watchlist-price" id="watchlist-price-${symbolId}">
                        <span class="price-loading">Loading...</span>
                    </div>
                    <div class="watchlist-change" id="watchlist-change-${symbolId}">
                        <span class="change-loading">--</span>
                    </div>
                    ${item.alertPrice ? `
                        <div class="watchlist-alert">
                            <i class="fas fa-bell"></i> Alert: ${this.formatCurrency(item.alertPrice)}
                        </div>
                    ` : ''}
                    ${item.notes ? `
                        <div class="watchlist-notes">
                            <i class="fas fa-sticky-note"></i> ${item.notes}
                        </div>
                    ` : ''}
                    <div class="watchlist-meta">
                        <span class="added-date">
                            <i class="fas fa-calendar-plus"></i> Added: ${this.formatDate(item.addedAt)}
                        </span>
                    </div>
                </div>
                <div class="watchlist-actions">
                    <button class="btn-small" onclick="window.stockManager.selectStock('${symbolId}', 'stock-analyser')">
                        <i class="fas fa-chart-line"></i> Analyze
                    </button>
                    <button class="btn-small btn-secondary" onclick="window.watchlistManager.editWatchlistItem('${symbolId}')">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                </div>
            </div>
        `}).join('');

        grid.innerHTML = watchlistHtml;

        // Update count
        this.updateWatchlistCount(this.watchlist.length);

        // Update timestamp
        this.updateWatchlistTimestamp();

        // Setup Add Stock button handler after section is rendered
        this.setupAddStockButtonHandler();

        // Load prices for all watchlist items
        console.log('>>> renderWatchlist: Calling loadWatchlistPrices()');
        this.loadWatchlistPrices();
    }


    /**
     * Update all watchlist buttons on the page
     */
    updateAllWatchlistButtons() {
        console.log('WatchlistManager: Updating all watchlist buttons');
        const allButtons = document.querySelectorAll('.add-to-watchlist-btn');

        allButtons.forEach(button => {
            const card = button.closest('[data-symbol]');
            if (card) {
                const symbol = card.dataset.symbol;
                const isOnWatchlist = this.isOnWatchlist(symbol);
                const icon = button.querySelector('i');

                if (icon) {
                    if (isOnWatchlist) {
                        button.classList.add('added');
                        button.title = 'Remove from watchlist';
                        icon.classList.remove('far');
                        icon.classList.add('fas');
                        card.classList.add('in-watchlist');
                    } else {
                        button.classList.remove('added');
                        button.title = 'Add to watchlist';
                        icon.classList.remove('fas');
                        icon.classList.add('far');
                        card.classList.remove('in-watchlist');
                    }
                }
            }
        });

        console.log(`WatchlistManager: Updated ${allButtons.length} watchlist buttons`);
    }

    /**
     * Update watchlist button states on stock cards
     * @param {string} symbol - Stock symbol to update
     */
    updateStockCardWatchlistButtons(symbol) {
        console.log(`WatchlistManager: Updating watchlist buttons for ${symbol}`);
        const stockCards = document.querySelectorAll(`[data-symbol="${symbol}"]`);
        const isOnWatchlist = this.isOnWatchlist(symbol);

        console.log(`WatchlistManager: ${symbol} is on watchlist: ${isOnWatchlist}`);
        console.log(`WatchlistManager: Found ${stockCards.length} stock cards for ${symbol}`);

        stockCards.forEach(card => {
            const button = card.querySelector('.add-to-watchlist-btn');
            const icon = button?.querySelector('i');

            if (button && icon) {
                if (isOnWatchlist) {
                    button.classList.add('added');
                    button.title = 'Remove from watchlist';
                    icon.classList.remove('far');
                    icon.classList.add('fas');
                    card.classList.add('in-watchlist');
                    console.log(`WatchlistManager: Updated ${symbol} button to ADDED state`);
                } else {
                    button.classList.remove('added');
                    button.title = 'Add to watchlist';
                    icon.classList.remove('fas');
                    icon.classList.add('far');
                    card.classList.remove('in-watchlist');
                    console.log(`WatchlistManager: Updated ${symbol} button to NOT ADDED state`);
                }
            }
        });
    }

    /**
     * Load prices for all watchlist items using BATCH API
     * Uses promise-based guard to handle concurrent calls consistently
     */
    async loadWatchlistPrices() {
        console.log('>>> loadWatchlistPrices() CALLED, _pricesLoading=' + this._pricesLoading);

        if (!window.authManager) {
            console.warn('AuthManager not available, cannot check authentication status for watchlist prices.');
            return;
        }

        const isAuthenticated = await window.authManager.isAuthenticated();
        if (!isAuthenticated) {
            console.log('User not authenticated, skipping watchlist price load.');
            // Optionally, clear existing price data or show a message
            return;
        }

        // If prices are already loading, wait for that to complete
        if (this._pricesLoading && this._pricesLoadingPromise) {
            console.log('>>> loadWatchlistPrices: WAIT - Prices already loading');
            return this._pricesLoadingPromise;
        }

        if (this.watchlist.length === 0) {
            console.log('>>> loadWatchlistPrices: No items to load prices for');
            return;
        }

        this._pricesLoading = true;

        // Create promise that others can await
        const loadPromise = this._doLoadWatchlistPrices();
        this._pricesLoadingPromise = loadPromise;

        try {
            await loadPromise;
        } finally {
            this._pricesLoading = false;
            this._pricesLoadingPromise = null;
            console.log('>>> loadWatchlistPrices: COMPLETE');
        }
    }

    /**
     * Internal implementation of loading watchlist prices
     */
    async _doLoadWatchlistPrices() {
        const symbols = this.watchlist.map(item => item.symbol.toUpperCase());
        console.log('>>> _doLoadWatchlistPrices: Loading batch prices for:', symbols);

        try {
            const batchPrices = await api.getBatchStockPrices(symbols);
            console.log('>>> _doLoadWatchlistPrices: Batch prices received:', Object.keys(batchPrices));

            // Update each watchlist item with price data
            let updated = 0;
            for (const symbol of symbols) {
                const priceData = batchPrices[symbol] || batchPrices[symbol.toUpperCase()];
                if (priceData && !priceData.error) {
                    this.updateWatchlistPriceDisplay(symbol, priceData);
                    this.checkPriceAlert(symbol, priceData);
                    updated++;
                }
            }
            console.log(`>>> _doLoadWatchlistPrices: Updated ${updated} prices`);

            // If no prices were updated, try showing demo data or retry
            if (updated === 0) {
                console.log('>>> _doLoadWatchlistPrices: No prices loaded from API, showing demo');
                this.showDemoPrices();
            }
        } catch (error) {
            console.error('>>> _doLoadWatchlistPrices: Failed:', error);
            // Show demo prices on error
            this.showDemoPrices();
        }
    }

    /**
     * Show demo prices when API fails
     */
    showDemoPrices() {
        const demoPrices = {
            'AAPL': { price: 178.50, change: 2.35, change_percent: 1.33 },
            'MSFT': { price: 378.25, change: -1.50, change_percent: -0.40 },
            'GOOGL': { price: 141.80, change: 3.20, change_percent: 2.31 },
            'AMZN': { price: 178.75, change: 1.85, change_percent: 1.05 },
            'NVDA': { price: 495.22, change: 12.50, change_percent: 2.59 },
            'ABB': { price: 52.40, change: 0.35, change_percent: 0.67 },
        };

        this.watchlist.forEach(item => {
            const demoPrice = demoPrices[item.symbol];
            if (demoPrice) {
                this.updateWatchlistPriceDisplay(item.symbol, demoPrice);
            } else {
                // Generate random price for unknown symbols
                const randomPrice = (Math.random() * 100 + 50).toFixed(2);
                const randomChange = (Math.random() * 10 - 5).toFixed(2);
                const randomPercent = (parseFloat(randomChange) / parseFloat(randomPrice) * 100).toFixed(2);
                this.updateWatchlistPriceDisplay(item.symbol, {
                    price: parseFloat(randomPrice),
                    change: parseFloat(randomChange),
                    change_percent: parseFloat(randomPercent)
                });
            }
        });
    }

    /**
     * Fallback: Load prices sequentially
     */
    async loadWatchlistPricesSequential() {
        const pricePromises = this.watchlist.map(item =>
            this.loadWatchlistPrice(item.symbol)
        );

        try {
            await Promise.allSettled(pricePromises);
        } catch (error) {
            console.error('Error loading watchlist prices:', error);
        }
    }

    /**
     * Load price for a specific watchlist item
     * @param {string} symbol - Stock symbol
     */
    async loadWatchlistPrice(symbol) {
        try {
            const priceData = await this.dataManager.loadStockData(symbol, 'price');

            if (priceData && !priceData.error) {
                this.updateWatchlistPriceDisplay(symbol, priceData);

                // Check for price alerts
                this.checkPriceAlert(symbol, priceData);
            }
        } catch (error) {
            console.error(`Failed to load price for ${symbol}:`, error);
        }
    }

    /**
     * Update price display for watchlist item
     * @param {string} symbol - Stock symbol
     * @param {object} priceData - Price data
     */
    updateWatchlistPriceDisplay(symbol, priceData) {
        try {
            const priceContainer = document.getElementById(`watchlist-price-${symbol}`);
            const changeElement = document.getElementById(`watchlist-change-${symbol}`);

            // Handle both API response formats
            const price = priceData.price || priceData.currentPrice;
            const change = priceData.change;
            const changePercent = priceData.change_percent;
            const changeClass = change >= 0 ? 'positive' : 'negative';

            if (!priceContainer || !price) {
                console.log(`>>> updateWatchlistPriceDisplay: No container or price for ${symbol}`);
                return;
            }

            const formattedPrice = Formatters.formatStockPrice(price);

            // Check if there's a span with price-loading class or any span
            let priceSpan = priceContainer.querySelector('.price-loading') || priceContainer.querySelector('span');

            if (priceSpan) {
                // Update the existing span
                priceSpan.textContent = formattedPrice;
                priceSpan.classList.remove('price-loading', 'change-loading');
                priceSpan.classList.add('loaded', changeClass);
            } else {
                // Span doesn't exist, create a new one with proper styling
                priceContainer.innerHTML = `<span class="loaded ${changeClass}">${formattedPrice}</span>`;
            }

            if (changeElement && change !== undefined && changePercent !== undefined) {
                const changeSymbol = change >= 0 ? '+' : '';
                const changeSpan = changeElement.querySelector('span');
                const changeHtml = `<span class="${changeClass}">${changeSymbol}${Formatters.formatStockPrice(change)} (${changeSymbol}${changePercent.toFixed(2)}%)</span>`;

                if (changeSpan) {
                    changeSpan.className = changeClass;
                    changeSpan.textContent = `${changeSymbol}${Formatters.formatStockPrice(change)} (${changeSymbol}${changePercent.toFixed(2)}%)`;
                } else {
                    changeElement.innerHTML = changeHtml;
                }
                changeElement.classList.add('loaded');
            }
        } catch (error) {
            console.error(`>>> updateWatchlistPriceDisplay: ERROR for ${symbol}:`, error);
        }
    }

    /**
     * Check if price alert should be triggered
     * @param {string} symbol - Stock symbol
     * @param {object} priceData - Current price data
     */
    checkPriceAlert(symbol, priceData) {
        const watchlistItem = this.watchlist.find(item => item.symbol === symbol);
        if (!watchlistItem || !watchlistItem.alertPrice) return;

        const currentPrice = priceData.price || priceData.currentPrice;
        const alertPrice = parseFloat(watchlistItem.alertPrice);

        if (currentPrice >= alertPrice) {
            this.showNotification(`Price alert: ${symbol} reached $${alertPrice}`, 'info');
            this.eventBus.emit('watchlist:alert', { symbol, currentPrice, alertPrice });
        }
    }

    /**
     * Update watchlist button state
     * @param {string} symbol - Stock symbol (optional)
     */
    updateWatchlistButtonState(symbol = null) {
        const watchlistToggle = document.getElementById('watchlistToggle');
        if (!watchlistToggle) return;

        const currentSymbol = symbol || window.stockManager?.getCurrentSymbol();
        if (!currentSymbol) return;

        const isOnWatchlist = this.watchlist.some(item => item.symbol === currentSymbol);

        if (isOnWatchlist) {
            watchlistToggle.innerHTML = '<i class="fas fa-star"></i> ON WATCHLIST';
            watchlistToggle.classList.add('on-watchlist');
        } else {
            watchlistToggle.innerHTML = '<i class="far fa-star"></i> ADD TO WATCHLIST';
            watchlistToggle.classList.remove('on-watchlist');
        }
    }

    /**
     * Show add to watchlist dialog - now opens stock picker
     */
    showAddToWatchlistDialog() {
        this.showStockPicker();
    }

    /**
     * Show stock picker modal for searching and adding stocks
     */
    async showStockPicker() {
        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.className = 'stock-picker-overlay';
        overlay.innerHTML = `
            <div class="stock-picker-modal">
                <div class="stock-picker-header">
                    <h3>Add Stock to Watchlist</h3>
                    <button class="stock-picker-close" onclick="this.closest('.stock-picker-overlay').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="stock-picker-search">
                    <div class="search-input-wrapper">
                        <i class="fas fa-search"></i>
                        <input type="text" id="stockPickerSearch" placeholder="Search stocks by symbol or name..." autocomplete="off">
                    </div>
                </div>
                <div class="stock-picker-results" id="stockPickerResults">
                    <div class="stock-picker-empty">
                        <i class="fas fa-search"></i>
                        <p>Search for stocks to add to your watchlist</p>
                    </div>
                </div>
                <div class="stock-picker-popular">
                    <h4>Popular Stocks</h4>
                    <div class="popular-tags" id="popularStockTags">
                        <!-- Popular stock tags will be loaded here -->
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Add styles if not already present
        this.addStockPickerStyles();

        // Setup search functionality
        const searchInput = document.getElementById('stockPickerSearch');
        const resultsContainer = document.getElementById('stockPickerResults');
        let searchTimeout;

        // Load popular stocks for quick add
        this.loadPopularStockTags();

        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim().toUpperCase();

            if (query.length < 1) {
                resultsContainer.innerHTML = `
                    <div class="stock-picker-empty">
                        <i class="fas fa-search"></i>
                        <p>Search for stocks to add to your watchlist</p>
                    </div>
                `;
                return;
            }

            // Debounce search
            searchTimeout = setTimeout(async () => {
                await this.searchAndDisplayStocks(query, resultsContainer);
            }, 300);
        });

        // Focus search input
        setTimeout(() => searchInput.focus(), 100);

        // Close on overlay click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
            }
        });
    }

    /**
     * Load popular stock tags for quick add
     */
    async loadPopularStockTags() {
        const container = document.getElementById('popularStockTags');
        if (!container) return;

        try {
            const popularStocks = await api.getPopularStocks(20);

            container.innerHTML = popularStocks.slice(0, 12).map(stock => `
                <button class="stock-tag" data-symbol="${stock.symbol}" data-name="${stock.name}">
                    ${stock.symbol}
                </button>
            `).join('');

            // Add click handlers
            container.querySelectorAll('.stock-tag').forEach(tag => {
                tag.addEventListener('click', () => {
                    const symbol = tag.dataset.symbol;
                    const name = tag.dataset.name;
                    this.addStockFromPicker(symbol, name);
                });
            });
        } catch (error) {
            console.error('Failed to load popular stocks:', error);
        }
    }

    /**
     * Search and display stocks in picker
     */
    async searchAndDisplayStocks(query, resultsContainer) {
        const upperQuery = query.toUpperCase().trim();
        
        resultsContainer.innerHTML = `
            <div class="stock-picker-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Searching...</p>
            </div>
        `;

        try {
            // First search the API
            const searchResults = await api.searchStocks(query, 10);

            // If no results, search stock universe directly
            let stocks = searchResults;
            if (!stocks || stocks.length === 0) {
                stocks = await this.searchStockUniverse(query);
            }

            if (stocks && stocks.length > 0) {
                resultsContainer.innerHTML = stocks.map(stock => `
                    <div class="stock-picker-item" data-symbol="${stock.symbol}" data-name="${stock.name || stock.company_name || stock.symbol}">
                        <div class="stock-info">
                            <span class="stock-symbol">${stock.symbol}</span>
                            <span class="stock-name">${stock.name || stock.company_name || stock.symbol}</span>
                        </div>
                        <button class="btn-add-stock" onclick="window.watchlistManager.addStockFromPicker('${stock.symbol}', '${stock.name || stock.company_name || stock.symbol}')">
                            <i class="fas fa-plus"></i> Add
                        </button>
                    </div>
                `).join('');
            } else {
                // No results found - show manual entry option for valid-looking symbols
                const isValidSymbol = upperQuery.length >= 1 && upperQuery.length <= 5 && /^[A-Z]/.test(upperQuery);
                
                if (isValidSymbol) {
                    resultsContainer.innerHTML = `
                        <div class="stock-picker-item manual-entry" data-symbol="${upperQuery}">
                            <div class="stock-info">
                                <span class="stock-symbol">${upperQuery}</span>
                                <span class="stock-name">Add symbol directly</span>
                            </div>
                            <button class="btn-add-stock" onclick="window.watchlistManager.addStockDirectly('${upperQuery}')">
                                <i class="fas fa-plus"></i> Add
                            </button>
                        </div>
                        <div class="stock-picker-manual-hint">
                            <i class="fas fa-info-circle"></i>
                            <span>Symbol not found in database. Click Add to add it anyway.</span>
                        </div>
                    `;
                } else {
                    resultsContainer.innerHTML = `
                        <div class="stock-picker-empty">
                            <i class="fas fa-search"></i>
                            <p>No stocks found for "${query}"</p>
                            <span class="hint">Try searching with a different term</span>
                        </div>
                    `;
                }
            }
        } catch (error) {
            console.error('Search failed:', error);
            resultsContainer.innerHTML = `
                <div class="stock-picker-empty">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Search failed. Please try again.</p>
                </div>
            `;
        }
    }

    /**
     * Add a stock directly by symbol (when not found in search)
     * @param {string} symbol - Stock symbol
     */
    async addStockDirectly(symbol) {
        const upperSymbol = symbol.toUpperCase().trim();
        
        // Validate symbol format
        if (!/^[A-Z]{1,5}$/.test(upperSymbol)) {
            this.showNotification('Invalid symbol format', 'error');
            return;
        }

        // Try to get company info from the metrics API
        let companyName = upperSymbol;
        try {
            const metricsData = await api.getStockMetrics(upperSymbol);
            if (metricsData && metricsData.companyName) {
                companyName = metricsData.companyName;
            }
        } catch (e) {
            console.log('Could not fetch company name for', upperSymbol, '- using symbol as name');
        }

        // Check if already on watchlist
        if (this.isOnWatchlist(upperSymbol)) {
            this.showNotification(`${upperSymbol} is already in your watchlist`, 'warning');
            return;
        }

        const stockData = {
            symbol: upperSymbol,
            name: companyName,
            notes: '',
            alertPrice: null,
            tags: []
        };

        await this.addToWatchlist(stockData);

        // Close picker
        const overlay = document.querySelector('.stock-picker-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * Search stock universe directly
     */
    async searchStockUniverse(query) {
        try {
            // Try to get stocks by sector or filter
            const stocks = await api.filterStocks({});
            if (stocks && stocks.length > 0) {
                // Filter locally by query
                return stocks.filter(stock =>
                    stock.symbol.toUpperCase().includes(query) ||
                    (stock.name && stock.name.toUpperCase().includes(query))
                ).slice(0, 10);
            }
            return [];
        } catch (error) {
            console.error('Failed to search stock universe:', error);
            return [];
        }
    }

    /**
     * Add stock from picker to watchlist
     */
    async addStockFromPicker(symbol, name) {
        // Check if already on watchlist
        if (this.isOnWatchlist(symbol)) {
            this.showNotification(`${symbol} is already in your watchlist`, 'warning');
            return;
        }

        const stockData = {
            symbol: symbol.toUpperCase(),
            name: name || symbol,
            notes: '',
            alertPrice: null,
            tags: []
        };

        await this.addToWatchlist(stockData);

        // Close picker
        const overlay = document.querySelector('.stock-picker-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * Add styles for stock picker
     */
    addStockPickerStyles() {
        if (document.getElementById('stock-picker-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'stock-picker-styles';
        styles.textContent = `
            .stock-picker-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: rgba(0,0,0,0.6);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                animation: fadeIn .2s ease-out;
            }
            .stock-picker-modal {
                background-color: var(--bg-white);
                border-radius: var(--border-radius-lg);
                box-shadow: var(--shadow-lg);
                max-width: 500px;
                width: 90%;
                max-height: 80vh;
                display: flex;
                flex-direction: column;
                animation: slideUp .3s ease-out;
            }
            .stock-picker-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: var(--spacing-lg);
                border-bottom: 1px solid var(--border-color);
            }
            .stock-picker-header h3 {
                margin: 0;
                color: var(--primary-color);
            }
            .stock-picker-close {
                background: none;
                border: none;
                color: var(--text-muted);
                font-size: var(--font-size-xl);
                cursor: pointer;
                padding: var(--spacing-xs);
                border-radius: var(--border-radius-sm);
                transition: all var(--transition-fast);
            }
            .stock-picker-close:hover {
                color: var(--danger-color);
                background-color: rgba(231,76,60,.1);
            }
            .stock-picker-search {
                padding: var(--spacing-md) var(--spacing-lg);
                border-bottom: 1px solid var(--border-color);
            }
            .search-input-wrapper {
                position: relative;
            }
            .search-input-wrapper i {
                position: absolute;
                left: var(--spacing-md);
                top: 50%;
                transform: translateY(-50%);
                color: var(--text-muted);
            }
            .stock-picker-search input {
                width: 100%;
                padding: var(--spacing-md) var(--spacing-lg) var(--spacing-md) 40px;
                border: 2px solid var(--border-color);
                border-radius: var(--border-radius-md);
                font-size: var(--font-size-base);
                transition: border-color var(--transition-fast);
            }
            .stock-picker-search input:focus {
                outline: none;
                border-color: var(--primary-color);
            }
            .stock-picker-results {
                flex: 1;
                overflow-y: auto;
                max-height: 300px;
            }
            .stock-picker-empty {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: var(--spacing-2xl);
                text-align: center;
                color: var(--text-secondary);
            }
            .stock-picker-empty i {
                font-size: 48px;
                color: var(--text-muted);
                margin-bottom: var(--spacing-md);
            }
            .stock-picker-empty .hint {
                font-size: var(--font-size-sm);
                color: var(--text-muted);
                margin-top: var(--spacing-sm);
            }
            .stock-picker-loading {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: var(--spacing-2xl);
            }
            .stock-picker-loading i {
                font-size: 32px;
                color: var(--primary-color);
                margin-bottom: var(--spacing-md);
            }
            .stock-picker-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: var(--spacing-md) var(--spacing-lg);
                border-bottom: 1px solid var(--border-color);
                cursor: pointer;
                transition: background-color var(--transition-fast);
            }
            .stock-picker-item:hover {
                background-color: var(--bg-hover);
            }
            .stock-picker-item:last-child {
                border-bottom: none;
            }
            .stock-picker-item.manual-entry {
                background-color: rgba(91, 163, 208, 0.1);
                border: 1px dashed var(--primary-color);
                margin: var(--spacing-sm) var(--spacing-md);
                border-radius: var(--border-radius-md);
            }
            .stock-picker-item.manual-entry:hover {
                background-color: rgba(91, 163, 208, 0.2);
            }
            .stock-picker-manual-hint {
                display: flex;
                align-items: center;
                gap: var(--spacing-sm);
                padding: var(--spacing-sm) var(--spacing-lg);
                color: var(--text-muted);
                font-size: var(--font-size-xs);
                font-style: italic;
            }
            .stock-picker-manual-hint i {
                color: var(--primary-color);
            }
            .stock-info {
                display: flex;
                flex-direction: column;
            }
            .stock-info .stock-symbol {
                font-weight: var(--font-weight-bold);
                color: var(--primary-color);
            }
            .stock-info .stock-name {
                font-size: var(--font-size-sm);
                color: var(--text-secondary);
            }
            .btn-add-stock {
                display: flex;
                align-items: center;
                gap: var(--spacing-xs);
                padding: var(--spacing-xs) var(--spacing-md);
                background-color: var(--primary-color);
                color: #fff;
                border: none;
                border-radius: var(--border-radius-md);
                font-size: var(--font-size-sm);
                font-weight: var(--font-weight-medium);
                cursor: pointer;
                transition: all var(--transition-fast);
            }
            .btn-add-stock:hover {
                background-color: color-mix(in srgb, var(--primary-color), black 10%);
                transform: translateY(-1px);
            }
            .stock-picker-popular {
                padding: var(--spacing-md) var(--spacing-lg);
                border-top: 1px solid var(--border-color);
                background-color: var(--bg-light);
            }
            .stock-picker-popular h4 {
                font-size: var(--font-size-sm);
                color: var(--text-secondary);
                margin: 0 0 var(--spacing-sm) 0;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .popular-tags {
                display: flex;
                flex-wrap: wrap;
                gap: var(--spacing-sm);
            }
            .stock-tag {
                padding: var(--spacing-xs) var(--spacing-md);
                background-color: var(--bg-white);
                border: 1px solid var(--border-color);
                border-radius: 20px;
                font-size: var(--font-size-sm);
                font-weight: var(--font-weight-medium);
                color: var(--text-primary);
                cursor: pointer;
                transition: all var(--transition-fast);
            }
            .stock-tag:hover {
                border-color: var(--primary-color);
                color: var(--primary-color);
                background-color: rgba(91,163,208,.1);
            }
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            @keyframes slideUp {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
        `;
        document.head.appendChild(styles);
    }

    /**
     * Handle add to watchlist form submission
     */
    async handleAddToWatchlist() {
        const symbol = document.getElementById('watchlistSymbol').value;
        const notes = document.getElementById('watchlistNotes').value;
        const alertPrice = document.getElementById('watchlistAlertPrice').value;

        const stockData = {
            symbol: symbol,
            name: symbol, // Will be updated with real name
            notes: notes,
            alertPrice: alertPrice ? parseFloat(alertPrice) : null
        };

        await this.addToWatchlist(stockData);

        // Close modal
        const modal = document.querySelector('.modal');
        if (modal) {
            modal.remove();
        }
    }

    /**
     * Edit watchlist item
     * @param {string} symbol - Stock symbol to edit
     */
    editWatchlistItem(symbol) {
        const item = this.watchlist.find(item => item.symbol === symbol);
        if (!item) return;

        // Create edit modal with overlay
        const overlay = document.createElement('div');
        overlay.className = 'watchlist-modal-overlay';

        // Create the modal card (vertical rectangle)
        const modal = document.createElement('div');
        modal.className = 'watchlist-modal';
        modal.innerHTML = `
            <div class="watchlist-modal-header">
                <h3>Edit ${item.symbol}</h3>
                <button class="watchlist-modal-close" onclick="this.closest('.watchlist-modal-overlay').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="watchlist-modal-body">
                <div class="form-group">
                    <label>Stock Symbol</label>
                    <input type="text" class="form-control" value="${item.symbol}" readonly>
                </div>
                <div class="form-group">
                    <label>Notes</label>
                    <textarea id="editNotes" class="form-control" rows="3" placeholder="Add notes about this stock...">${item.notes || ''}</textarea>
                </div>
                <div class="form-group">
                    <label>Price Alert ($)</label>
                    <input type="number" id="editAlertPrice" class="form-control" value="${item.alertPrice || ''}" step="0.01" placeholder="Alert when price reaches...">
                </div>
            </div>
            <div class="watchlist-modal-footer">
                <button class="btn-secondary" onclick="this.closest('.watchlist-modal-overlay').remove()">Cancel</button>
                <button class="btn-primary" onclick="window.watchlistManager.handleEditWatchlistItem('${symbol}')">Save Changes</button>
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        // Add click handler to close on overlay click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
            }
        });

        // Focus on notes field
        setTimeout(() => {
            const notesField = document.getElementById('editNotes');
            if (notesField) notesField.focus();
        }, 100);
    }

    /**
     * Handle edit watchlist item form submission
     */
    async handleEditWatchlistItem(symbol) {
        const notes = document.getElementById('editNotes').value;
        const alertPrice = document.getElementById('editAlertPrice').value;

        // Get the original item to preserve all data
        const originalItem = this.watchlist.find(item => item.symbol === symbol);
        if (!originalItem) return;

        // Update the item directly instead of remove/add (preserves addedAt)
        originalItem.notes = notes;
        originalItem.alertPrice = alertPrice ? parseFloat(alertPrice) : null;

        // Save to localStorage
        await this.dataManager.saveWatchlistToLocalStorage(this.watchlist);

        // Re-render
        this.renderWatchlist();
        this.updateStockCardWatchlistButtons(symbol);

        // Close modal
        const modal = document.querySelector('.watchlist-modal-overlay');
        if (modal) {
            modal.remove();
        }

        this.showNotification(`${symbol} updated successfully`, 'success');
    }

    /**
     * Start automatic price updates
     */
    startPriceUpdates() {
        if (this.priceUpdateInterval) {
            clearInterval(this.priceUpdateInterval);
        }

        this.priceUpdateInterval = setInterval(() => {
            if (this.watchlist.length > 0) {
                this.loadWatchlistPrices();
            }
        }, this.priceUpdateFrequency);
    }

    /**
     * Stop automatic price updates
     */
    stopPriceUpdates() {
        if (this.priceUpdateInterval) {
            clearInterval(this.priceUpdateInterval);
            this.priceUpdateInterval = null;
        }
    }

    /**
     * Show notification message
     * @param {string} message - Message to show
     * @param {string} type - Notification type
     */
    showNotification(message, type = 'info') {
        this.eventBus.emit('ui:notification', { message, type });
    }

    /**
     * Get current watchlist
     * @returns {Array} Current watchlist
     */
    getWatchlist() {
        return [...this.watchlist];
    }

    /**
     * Check if stock is on watchlist
     * @param {string} symbol - Stock symbol
     * @returns {boolean} Whether stock is on watchlist
     */
    isOnWatchlist(symbol) {
        return this.watchlist.some(item => item.symbol === symbol);
    }

    /**
     * Get watchlist statistics
     * @returns {object} Watchlist stats
     */
    getWatchlistStats() {
        return {
            totalItems: this.watchlist.length,
            withAlerts: this.watchlist.filter(item => item.alertPrice).length,
            withNotes: this.watchlist.filter(item => item.notes).length,
            lastUpdated: new Date().toISOString()
        };
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.stopPriceUpdates();
        this.watchlist = [];
        this._watchlistRendered = false;
        console.log('WatchlistManager: Cleaned up');
    }

    /**
     * Lifecycle: Initialize module (called once)
     */
    onInit() {
        console.log('[WatchlistManager] Initialized');
        this.isInitialized = true;
        this.isVisible = false;
        this.savedScrollPosition = 0;
    }

    /**
     * Lifecycle: Show module (resume operations)
     */
    onShow() {
        console.log('[WatchlistManager] Shown - resuming price updates and restoring scroll');
        this.isVisible = true;
        this.startPriceUpdates();
        this.restoreScrollPosition();
        // Refresh watchlist if needed
        if (!this._watchlistRendered && this.watchlist.length > 0) {
            this.renderWatchlist();
        }
    }

    /**
     * Lifecycle: Hide module (pause operations)
     */
    onHide() {
        console.log('[WatchlistManager] Hidden - pausing price updates and saving scroll');
        this.isVisible = false;
        this.saveScrollPosition();
        this.stopPriceUpdates();
    }

    /**
     * Lifecycle: Destroy module (complete cleanup)
     */
    onDestroy() {
        console.log('[WatchlistManager] Destroyed - complete cleanup');
        this.stopPriceUpdates();
        this.cleanup();
        this.isInitialized = false;
    }

    /**
     * Save scroll position of watchlist grid
     */
    saveScrollPosition() {
        const grid = document.getElementById('watchlistGrid');
        if (grid) {
            this.savedScrollPosition = grid.scrollTop;
            console.log('[WatchlistManager] Scroll position saved:', this.savedScrollPosition);
        }
    }

    /**
     * Restore scroll position of watchlist grid
     */
    restoreScrollPosition() {
        const grid = document.getElementById('watchlistGrid');
        if (grid && this.savedScrollPosition > 0) {
            grid.scrollTop = this.savedScrollPosition;
            console.log('[WatchlistManager] Scroll position restored:', this.savedScrollPosition);
        }
    }

    /**
     * Get module state for lifecycle manager
     */
    getState() {
        return {
            watchlist: this.watchlist,
            isInitialized: this.isInitialized,
            isVisible: this.isVisible,
            savedScrollPosition: this.savedScrollPosition,
            _watchlistRendered: this._watchlistRendered
        };
    }

    /**
     * Set module state from lifecycle manager
     */
    setState(state) {
        console.log('[WatchlistManager] Restoring state:', state);
        if (state?.watchlist) {
            this.watchlist = state.watchlist;
        }
        this.isVisible = state?.isVisible ?? true;
        this.savedScrollPosition = state?.savedScrollPosition ?? 0;
        this._watchlistRendered = state?._watchlistRendered ?? false;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WatchlistManager;
} else {
    window.WatchlistManager = WatchlistManager;
}

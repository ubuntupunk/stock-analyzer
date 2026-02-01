// Watchlist Management Module
// Handles watchlist CRUD operations, UI updates, and price tracking

class WatchlistManager {
    constructor(dataManager, eventBus) {
        this.dataManager = dataManager;
        this.eventBus = eventBus;
        this.watchlist = [];
        this.priceUpdateInterval = null;
        this.priceUpdateFrequency = 60000; // 1 minute
        
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
        // Watchlist toggle button
        const watchlistToggle = document.getElementById('watchlistToggle');
        if (watchlistToggle) {
            watchlistToggle.addEventListener('click', () => {
                const currentSymbol = window.stockManager?.getCurrentSymbol();
                if (currentSymbol) {
                    this.toggleWatchlist(currentSymbol);
                }
            });
        }

        // Add to watchlist button
        const addToWatchlistBtn = document.getElementById('addToWatchlistBtn');
        if (addToWatchlistBtn) {
            addToWatchlistBtn.addEventListener('click', () => {
                this.showAddToWatchlistDialog();
            });
        }
    }

    /**
     * Load watchlist from API
     */
    async loadWatchlist() {
        try {
            this.eventBus.emit('watchlist:loading');
            
            const watchlistData = await this.dataManager.loadWatchlist();
            this.watchlist = watchlistData || [];
            
            this.renderWatchlist();
            this.updateAllWatchlistButtons();
            
            this.eventBus.emit('watchlist:loaded', { watchlist: this.watchlist });
        } catch (error) {
            console.error('Failed to load watchlist:', error);
            this.eventBus.emit('watchlist:error', { error: error.message });
        }
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
            
            if (result.success) {
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
            
            if (result.success) {
                // Remove from local watchlist
                this.watchlist = this.watchlist.filter(item => item.symbol !== symbol);
                this.renderWatchlist();
                this.updateStockCardWatchlistButtons(symbol);
                
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
    renderWatchlist() {
        const container = document.getElementById('watchlistContainer');
        const grid = document.getElementById('watchlistGrid');
        const empty = document.getElementById('watchlistEmpty');
        
        if (!container) return;

        if (this.watchlist.length === 0) {
            if (empty) empty.style.display = 'block';
            if (grid) grid.style.display = 'none';
            this.updateWatchlistCount(0);
            return;
        }

        if (empty) empty.style.display = 'none';
        if (grid) grid.style.display = 'grid';

        const watchlistHtml = this.watchlist.map(item => `
            <div class="watchlist-item" data-symbol="${item.symbol}">
                <div class="watchlist-header">
                    <div class="watchlist-symbol">
                        <span class="symbol">${item.symbol}</span>
                        <span class="name">${item.name}</span>
                    </div>
                    <button class="watchlist-remove" onclick="window.watchlistManager.removeFromWatchlist('${item.symbol}')" title="Remove from watchlist">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="watchlist-content">
                    <div class="watchlist-price" id="price-${item.symbol}">
                        <span class="price-loading">Loading...</span>
                    </div>
                    <div class="watchlist-change" id="change-${item.symbol}">
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
                    <button class="btn-small" onclick="window.stockManager.selectStock('${item.symbol}')">
                        <i class="fas fa-chart-line"></i> Analyze
                    </button>
                    <button class="btn-small btn-secondary" onclick="window.watchlistManager.editWatchlistItem('${item.symbol}')">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                </div>
            </div>
        `).join('');

        grid.innerHTML = watchlistHtml;
        
        // Update count
        this.updateWatchlistCount(this.watchlist.length);
        
        // Update timestamp
        this.updateWatchlistTimestamp();

        // Load prices for all watchlist items
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
     */
    async loadWatchlistPrices() {
        if (this.watchlist.length === 0) {
            return;
        }
        
        const symbols = this.watchlist.map(item => item.symbol);
        
        try {
            console.log('WatchlistManager: Loading batch prices for watchlist:', symbols);
            const batchPrices = await api.getBatchStockPrices(symbols);
            console.log('WatchlistManager: Batch prices received:', batchPrices);
            
            // Update each watchlist item with price data
            Object.entries(batchPrices).forEach(([symbol, priceData]) => {
                if (priceData && !priceData.error) {
                    this.updateWatchlistPriceDisplay(symbol, priceData);
                    this.checkPriceAlert(symbol, priceData);
                }
            });
        } catch (error) {
            console.error('WatchlistManager: Failed to load batch prices:', error);
            // Fallback to sequential loading
            console.log('WatchlistManager: Falling back to sequential loading');
            await this.loadWatchlistPricesSequential();
        }
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
        const priceElement = document.getElementById(`price-${symbol}`);
        const changeElement = document.getElementById(`change-${symbol}`);
        
        // Handle both API response formats
        const price = priceData.price || priceData.currentPrice;
        const change = priceData.change;
        const changePercent = priceData.change_percent;
        
        if (priceElement && price) {
            priceElement.innerHTML = Formatters.formatStockPrice(price);
        }
        
        if (changeElement && change !== undefined && changePercent !== undefined) {
            const changeClass = change >= 0 ? 'positive' : 'negative';
            const changeSymbol = change >= 0 ? '+' : '';
            changeElement.innerHTML = `<span class="${changeClass}">${changeSymbol}${Formatters.formatStockPrice(change)} (${changeSymbol}${changePercent.toFixed(2)}%)</span>`;
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
     * Show add to watchlist dialog
     */
    showAddToWatchlistDialog() {
        const currentSymbol = window.stockManager?.getCurrentSymbol();
        if (!currentSymbol) {
            this.showNotification('Please select a stock first', 'warning');
            return;
        }

        // Create modal dialog
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Add to Watchlist</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Stock Symbol</label>
                        <input type="text" id="watchlistSymbol" value="${currentSymbol}" readonly>
                    </div>
                    <div class="form-group">
                        <label>Notes (optional)</label>
                        <textarea id="watchlistNotes" placeholder="Add notes about this stock..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Price Alert (optional)</label>
                        <input type="number" id="watchlistAlertPrice" placeholder="Alert when price reaches this level" step="0.01">
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button class="btn-primary" onclick="window.watchlistManager.handleAddToWatchlist()">Add to Watchlist</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.style.display = 'block';
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
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WatchlistManager;
} else {
    window.WatchlistManager = WatchlistManager;
}

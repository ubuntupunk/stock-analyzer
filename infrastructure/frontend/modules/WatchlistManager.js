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
                // Add to local watchlist
                const watchlistItem = {
                    symbol: stockData.symbol,
                    name: stockData.name || stockData.symbol,
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
        const isOnWatchlist = this.watchlist.some(item => item.symbol === symbol);
        
        if (isOnWatchlist) {
            await this.removeFromWatchlist(symbol);
        } else {
            const stockData = {
                symbol: symbol,
                name: symbol, // Will be updated with real name
                notes: '',
                alertPrice: null,
                tags: []
            };
            await this.addToWatchlist(stockData);
        }
    }

    /**
     * Render watchlist in the UI
     */
    renderWatchlist() {
        const grid = document.getElementById('watchlistGrid');
        if (!grid) return;

        if (this.watchlist.length === 0) {
            grid.innerHTML = `
                <div class="empty-watchlist">
                    <i class="fas fa-star"></i>
                    <h3>Your watchlist is empty</h3>
                    <p>Add stocks to track their performance</p>
                    <button class="btn-primary" onclick="window.watchlistManager.showAddToWatchlistDialog()">
                        <i class="fas fa-plus"></i> Add Stock
                    </button>
                </div>
            `;
            return;
        }

        const watchlistHtml = this.watchlist.map(item => `
            <div class="watchlist-item" data-symbol="${item.symbol}">
                <div class="watchlist-header">
                    <div class="watchlist-symbol">${item.symbol}</div>
                    <div class="watchlist-name">${item.name}</div>
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
                            Alert: ${Formatters.formatStockPrice(item.alertPrice)}
                        </div>
                    ` : ''}
                    ${item.notes ? `
                        <div class="watchlist-notes">${item.notes}</div>
                    ` : ''}
                    <div class="watchlist-meta">
                        Added: ${Formatters.formatDate(item.addedAt, 'short')}
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

        // Create edit modal
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Edit Watchlist Item</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Stock Symbol</label>
                        <input type="text" value="${item.symbol}" readonly>
                    </div>
                    <div class="form-group">
                        <label>Notes</label>
                        <textarea id="editNotes">${item.notes || ''}</textarea>
                    </div>
                    <div class="form-group">
                        <label>Price Alert</label>
                        <input type="number" id="editAlertPrice" value="${item.alertPrice || ''}" step="0.01">
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button class="btn-primary" onclick="window.watchlistManager.handleEditWatchlistItem('${symbol}')">Save Changes</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.style.display = 'block';
    }

    /**
     * Handle edit watchlist item form submission
     */
    async handleEditWatchlistItem(symbol) {
        const notes = document.getElementById('editNotes').value;
        const alertPrice = document.getElementById('editAlertPrice').value;

        // Remove old item
        await this.removeFromWatchlist(symbol);
        
        // Add updated item
        const stockData = {
            symbol: symbol,
            name: symbol,
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

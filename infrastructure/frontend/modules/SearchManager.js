// Search Management Module
// Handles stock search, autocomplete, and search UI interactions

class SearchManager {
    constructor(dataManager, eventBus) {
        this.dataManager = dataManager;
        this.eventBus = eventBus;
        this.searchResults = [];
        this.searchTimeout = null;
        this.isSearching = false;
        
        // Subscribe to search events
        this.setupEventListeners();
    }

    /**
     * Setup event listeners for search functionality
     */
    setupEventListeners() {
        this.eventBus.on('search:perform', ({ query }) => {
            this.performSearch(query);
        });

        this.eventBus.on('search:clear', () => {
            this.clearSearch();
        });

        this.eventBus.on('search:hide', () => {
            this.hideSearchResults();
        });
    }

    /**
     * Initialize search functionality
     */
    initialize() {
        this.setupSearchInput();
        this.setupSearchKeyboardHandlers();
    }

    /**
     * Setup search input event handlers
     */
    setupSearchInput() {
        const searchInput = document.getElementById('stockSearch');
        if (!searchInput) return;

        searchInput.addEventListener('input', (e) => {
            this.handleSearchInput(e.target.value.trim());
        });

        searchInput.addEventListener('keydown', (e) => {
            this.handleSearchKeydown(e);
        });

        searchInput.addEventListener('focus', () => {
            if (this.searchResults.length > 0) {
                this.showSearchResults();
            }
        });
    }

    /**
     * Setup keyboard navigation for search
     */
    setupSearchKeyboardHandlers() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideSearchResults();
                this.clearSearchInput();
            }
        });

        // Close search results when clicking outside
        document.addEventListener('click', (e) => {
            const searchContainer = document.getElementById('stockSearch');
            const resultsContainer = document.getElementById('searchResults');
            
            if (searchContainer && !searchContainer.contains(e.target) && 
                resultsContainer && !resultsContainer.contains(e.target)) {
                this.hideSearchResults();
            }
        });
    }

    /**
     * Handle search input with debouncing
     * @param {string} query - Search query
     */
    handleSearchInput(query) {
        // Clear existing timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        if (query.length === 0) {
            this.clearSearch();
            return;
        }

        if (query.length < 1) {
            this.hideSearchResults();
            return;
        }

        // Debounce search to avoid too many requests
        this.searchTimeout = setTimeout(() => {
            this.performSearch(query);
        }, 300);
    }

    /**
     * Handle keyboard navigation in search
     * @param {KeyboardEvent} e - Keyboard event
     */
    handleSearchKeydown(e) {
        const resultsContainer = document.getElementById('searchResults');
        if (!resultsContainer || !resultsContainer.classList.contains('show')) {
            return;
        }

        const resultItems = resultsContainer.querySelectorAll('.search-result-item');
        let currentIndex = -1;

        // Find currently selected item
        resultItems.forEach((item, index) => {
            if (item.classList.contains('selected')) {
                currentIndex = index;
            }
        });

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                currentIndex = Math.min(currentIndex + 1, resultItems.length - 1);
                this.highlightSearchResult(resultItems, currentIndex);
                break;

            case 'ArrowUp':
                e.preventDefault();
                currentIndex = Math.max(currentIndex - 1, 0);
                this.highlightSearchResult(resultItems, currentIndex);
                break;

            case 'Enter':
                e.preventDefault();
                if (currentIndex >= 0 && resultItems[currentIndex]) {
                    const symbol = resultItems[currentIndex].getAttribute('data-symbol');
                    if (symbol) {
                        this.selectSearchResult(symbol);
                    }
                }
                break;

            case 'Tab':
                this.hideSearchResults();
                break;
        }
    }

    /**
     * Highlight a search result item during keyboard navigation
     * @param {NodeList} resultItems - Search result items
     * @param {number} index - Index to select
     */
    highlightSearchResult(resultItems, index) {
        // Remove previous selection
        resultItems.forEach(item => item.classList.remove('selected'));
        
        // Add selection to current item
        if (resultItems[index]) {
            resultItems[index].classList.add('selected');
            resultItems[index].scrollIntoView({ block: 'nearest' });
        }
    }

    /**
     * Perform stock search
     * @param {string} query - Search query
     */
    async performSearch(query) {
        if (this.isSearching) return;

        const validation = Validators.validateSearchQuery(query);
        if (!validation.isValid) {
            this.eventBus.emit('search:error', { query, error: validation.error });
            return;
        }

        this.isSearching = true;
        this.showSearchLoading();

        try {
            const results = await this.dataManager.searchStocks(validation.query, 10);
            this.searchResults = results;
            this.showSearchResults();
            
            this.eventBus.emit('search:completed', { query, results });
        } catch (error) {
            console.error('Search failed:', error);
            this.eventBus.emit('search:error', { query, error: error.message });
            this.hideSearchResults();
        } finally {
            this.isSearching = false;
            this.hideSearchLoading();
        }
    }

    /**
     * Select a search result
     * @param {string} symbol - Stock symbol to select
     */
    selectSearchResult(symbol) {
        this.hideSearchResults();
        this.clearSearchInput();
        
        // Emit stock selection event
        this.eventBus.emit('stock:selected', { symbol });
        
        // Also emit search selection event for analytics
        this.eventBus.emit('search:selected', { symbol, query: this.getLastQuery() });
    }

    /**
     * Show search results
     */
    showSearchResults() {
        const resultsContainer = document.getElementById('searchResults');
        if (!resultsContainer || this.searchResults.length === 0) return;

        const resultsHtml = this.searchResults.map(stock => `
            <div class="search-result-item" data-symbol="${stock.symbol}" onclick="window.searchManager.selectSearchResult('${stock.symbol}')">
                <div class="search-result-symbol">${stock.symbol}</div>
                <div class="search-result-name">${stock.name}</div>
                <div class="search-result-sector">${stock.sector || 'N/A'}</div>
                <div class="search-result-price">${stock.price ? Formatters.formatStockPrice(stock.price) : 'N/A'}</div>
            </div>
        `).join('');

        resultsContainer.innerHTML = resultsHtml;
        resultsContainer.classList.add('show');
        
        this.eventBus.emit('search:resultsShown', { results: this.searchResults });
    }

    /**
     * Hide search results
     */
    hideSearchResults() {
        const resultsContainer = document.getElementById('searchResults');
        if (resultsContainer) {
            resultsContainer.classList.remove('show');
        }
        
        this.eventBus.emit('search:resultsHidden');
    }

    /**
     * Show search loading state
     */
    showSearchLoading() {
        const searchInput = document.getElementById('stockSearch');
        if (searchInput) {
            searchInput.classList.add('loading');
        }

        const resultsContainer = document.getElementById('searchResults');
        if (resultsContainer) {
            resultsContainer.innerHTML = '<div class="search-loading">Searching...</div>';
            resultsContainer.classList.add('show');
        }
    }

    /**
     * Hide search loading state
     */
    hideSearchLoading() {
        const searchInput = document.getElementById('stockSearch');
        if (searchInput) {
            searchInput.classList.remove('loading');
        }
    }

    /**
     * Clear search results and input
     */
    clearSearch() {
        this.searchResults = [];
        this.hideSearchResults();
        this.clearSearchInput();
        
        this.eventBus.emit('search:cleared');
    }

    /**
     * Clear search input
     */
    clearSearchInput() {
        const searchInput = document.getElementById('stockSearch');
        if (searchInput) {
            searchInput.value = '';
        }
    }

    /**
     * Get current search results
     * @returns {Array} Search results
     */
    getSearchResults() {
        return [...this.searchResults];
    }

    /**
     * Get last search query
     * @returns {string} Last query
     */
    getLastQuery() {
        const searchInput = document.getElementById('stockSearch');
        return searchInput ? searchInput.value.trim() : '';
    }

    /**
     * Check if currently searching
     * @returns {boolean} Whether search is in progress
     */
    isCurrentlySearching() {
        return this.isSearching;
    }

    /**
     * Get search statistics
     * @returns {object} Search statistics
     */
    getSearchStats() {
        return {
            resultCount: this.searchResults.length,
            isSearching: this.isSearching,
            lastQuery: this.getLastQuery(),
            hasResults: this.searchResults.length > 0
        };
    }

    /**
     * Focus search input
     */
    focusSearch() {
        const searchInput = document.getElementById('stockSearch');
        if (searchInput) {
            searchInput.focus();
        }
    }

    /**
     * Set search input value
     * @param {string} value - Value to set
     */
    setSearchValue(value) {
        const searchInput = document.getElementById('stockSearch');
        if (searchInput) {
            searchInput.value = value;
        }
    }

    /**
     * Add recent search to history
     * @param {string} symbol - Stock symbol
     */
    addToRecentSearches(symbol) {
        let recentSearches = this.getRecentSearches();
        
        // Remove if already exists
        recentSearches = recentSearches.filter(s => s !== symbol);
        
        // Add to beginning
        recentSearches.unshift(symbol);
        
        // Limit to 10 items
        recentSearches = recentSearches.slice(0, 10);
        
        // Save to localStorage
        try {
            localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
        } catch (error) {
            console.warn('Failed to save recent searches:', error);
        }
    }

    /**
     * Get recent searches
     * @returns {Array} Recent search symbols
     */
    getRecentSearches() {
        try {
            const saved = localStorage.getItem('recentSearches');
            return saved ? JSON.parse(saved) : [];
        } catch (error) {
            console.warn('Failed to load recent searches:', error);
            return [];
        }
    }

    /**
     * Clear recent searches
     */
    clearRecentSearches() {
        try {
            localStorage.removeItem('recentSearches');
        } catch (error) {
            console.warn('Failed to clear recent searches:', error);
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SearchManager;
} else {
    window.SearchManager = SearchManager;
}

// News Management Module
// Handles news data loading and display for the News tab

class NewsManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.currentPeriod = '24h';
        this.currentSymbol = null;
        this.setupEventListeners();
        this.setupSymbolInputHandlers();
    }

    /**
     * Setup event listeners for news interactions
     */
    setupEventListeners() {
        // Listen for data loaded events
        this.eventBus.on('data:loaded', ({ type, data, symbol }) => {
            if (type === 'news') {
                console.log('NewsManager: News data loaded, updating display');
                this.updateNewsDisplay(symbol, data);
            }
        });

        // Listen for tab switched events to reinitialize UI
        this.eventBus.on('tab:switched', ({ tabName }) => {
            if (tabName === 'news') {
                console.log('NewsManager: News tab switched, setting up UI');
                setTimeout(() => this.setupNewsUI(), 200);
            }
        });

        // Listen for section loaded events
        this.eventBus.on('section:loaded', ({ sectionName }) => {
            if (sectionName === 'news') {
                console.log('NewsManager: News section loaded, setting up UI');
                setTimeout(() => this.setupNewsUI(), 100);
            }
        });

        // Listen for stock selected events to load news
        this.eventBus.on('stock:selected', ({ symbol }) => {
            console.log('NewsManager: Stock selected:', symbol);
            this.currentSymbol = symbol;
            this.updateCompanyInfo(symbol);
            if (symbol) {
                this.loadNews(symbol);
            }
        });
    }

    /**
     * Setup symbol input handlers for the news section
     */
    setupSymbolInputHandlers() {
        console.log('NewsManager: Setting up symbol input handlers');
        
        // Make the loadNewsSymbol function globally available
        window.loadNewsSymbol = () => {
            const input = document.getElementById('newsSymbolInput');
            if (input && input.value.trim()) {
                const symbol = input.value.trim().toUpperCase();
                console.log('NewsManager: Loading news for symbol:', symbol);
                if (window.stockManager) {
                    window.stockManager.selectStock(symbol, 'news');
                } else if (window.app && window.app.modules && window.app.modules.stockManager) {
                    window.app.modules.stockManager.selectStock(symbol, 'news');
                } else {
                    console.error('NewsManager: stockManager not available');
                }
            }
        };
        
        // Make the keydown handler globally available
        window.handleNewsSymbolKeydown = (event) => {
            if (event.key === 'Enter') {
                loadNewsSymbol();
            }
        };
        
        console.log('NewsManager: Symbol input handlers set up');
    }

    /**
     * Update company info in the news header
     * @param {string} symbol - Stock symbol
     */
    updateCompanyInfo(symbol) {
        const symbolElement = document.getElementById('newsSymbol');
        const nameElement = document.getElementById('newsCompanyName');
        
        if (symbolElement) {
            symbolElement.textContent = symbol ? `(${symbol})` : '-';
        }
        
        if (nameElement) {
            // Try to get company name from various sources
            let companyName = '-';
            
            // 1. Try to find in popular stocks
            if (window.stockManager && window.stockManager.popularStocks) {
                const stock = window.stockManager.popularStocks.find(s => s.symbol === symbol);
                if (stock && stock.name) {
                    companyName = stock.name;
                }
            }
            
            // 2. Try to get from metrics cache
            if (companyName === '-' && window.dataManager && window.dataManager.getCachedData) {
                try {
                    const metricsCacheKey = `${symbol}:metrics`;
                    const metricsData = window.dataManager.getCachedData(metricsCacheKey);
                    if (metricsData) {
                        if (metricsData.companyName) {
                            companyName = metricsData.companyName;
                        } else if (metricsData.company_name) {
                            companyName = metricsData.company_name;
                        } else if (metricsData.meta && metricsData.meta.companyName) {
                            companyName = metricsData.meta.companyName;
                        } else if (metricsData.meta && metricsData.meta.company_name) {
                            companyName = metricsData.meta.company_name;
                        }
                    }
                } catch (e) {
                    console.warn('NewsManager: Error getting metrics cache:', e);
                }
            }
            
            // 3. Try from other UI elements
            if (companyName === '-') {
                try {
                    const analyserNameElement = document.querySelector('#stockAnalyserSection #companyName');
                    if (analyserNameElement && analyserNameElement.textContent && 
                        analyserNameElement.textContent !== 'Market Data' && 
                        analyserNameElement.textContent !== '-') {
                        companyName = analyserNameElement.textContent;
                    }
                } catch (e) {
                    // Ignore errors
                }
            }
            
            // 4. Try from MetricsManager if available
            if (companyName === '-' && window.metricsManager) {
                try {
                    const metricsCompanyNameElement = document.getElementById('companyName');
                    if (metricsCompanyNameElement && metricsCompanyNameElement.textContent && 
                        metricsCompanyNameElement.textContent !== 'Market Data' && 
                        metricsCompanyNameElement.textContent !== '-') {
                        companyName = metricsCompanyNameElement.textContent;
                    }
                } catch (e) {
                    // Ignore errors
                }
            }
            
            nameElement.textContent = companyName;
        }
    }

    /**
     * Load news for a given symbol
     * @param {string} symbol - Stock symbol
     */
    loadNews(symbol) {
        if (!symbol) {
            console.warn('NewsManager: No symbol provided for loading news');
            return;
        }
        
        console.log('NewsManager: Loading news for:', symbol, 'Period:', this.currentPeriod);
        
        // Emit loading event
        this.eventBus.emit('data:loading', { symbol, type: 'news' });
        
        // Show loading state in container
        const container = document.getElementById('newsContainer');
        if (container) {
            container.innerHTML = `
                <div class="news-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Loading news for ${symbol}...</p>
                </div>
            `;
        }
        
        // Use api to get news if available
        if (window.api && typeof window.api.getStockNews === 'function') {
            window.api.getStockNews(symbol, this.currentPeriod)
                .then(newsData => {
                    console.log('NewsManager: Received news data:', newsData);
                    this.eventBus.emit('data:loaded', { 
                        type: 'news', 
                        data: newsData, 
                        symbol 
                    });
                })
                .catch(error => {
                    console.error('NewsManager: Error loading news:', error);
                    this.eventBus.emit('data:error', { 
                        type: 'news', 
                        error: error.message, 
                        symbol 
                    });
                });
        } else {
            // Fallback: emit empty data after a delay
            console.warn('NewsManager: API not available, using fallback');
            setTimeout(() => {
                this.eventBus.emit('data:loaded', { 
                    type: 'news', 
                    data: [], 
                    symbol 
                });
            }, 500);
        }
    }

    /**
     * Update news display when data arrives
     * @param {string} symbol - Stock symbol
     * @param {Array} data - News data
     */
    updateNewsDisplay(symbol, data) {
        console.log('NewsManager: updateNewsDisplay called with:', { symbol, hasData: !!data, dataLength: data?.length });
        
        const container = document.getElementById('newsContainer');
        if (!container) {
            console.error('NewsManager: newsContainer element not found');
            return;
        }
        
        // Update source and timestamp
        const sourceElement = document.getElementById('newsSource');
        const updatedElement = document.getElementById('newsUpdated');
        
        if (sourceElement) {
            sourceElement.innerHTML = '<a href="https://finance.yahoo.com" target="_blank" rel="noopener">Yahoo Finance</a>';
        }
        
        if (updatedElement) {
            updatedElement.textContent = new Date().toLocaleString();
        }
        
        if (!data || data.length === 0) {
            console.log('NewsManager: No news data available');
            container.innerHTML = `
                <div class="news-empty">
                    <p>No news available for ${symbol}</p>
                    <p class="news-hint">Try selecting a different stock or check back later.</p>
                </div>
            `;
            return;
        }
        
        console.log('NewsManager: Rendering', data.length, 'news articles');
        
        let html = '';
        data.forEach(article => {
            const publishedAt = article.publishedAt || article.pubDate || article.datetime;
            const timeAgo = this.getTimeAgo(publishedAt);
            const source = article.source || 'Unknown Source';
            const title = article.title || 'No Title';
            const summary = article.summary || article.description || '';
            const url = article.url || '#';
            const imageUrl = article.imageUrl || article.thumbnail || article.bannerImage || '';
            
            html += `
                <div class="news-item">
                    ${imageUrl ? `<div class="news-image"><img src="${imageUrl}" alt="${title}" onerror="this.parentElement.style.display='none'"></div>` : ''}
                    <div class="news-content">
                        <a href="${url}" target="_blank" rel="noopener" class="news-title">${title}</a>
                        <div class="news-meta">
                            <span class="news-source">${source}</span>
                            <span class="news-time">${timeAgo}</span>
                        </div>
                        ${summary ? `<div class="news-summary">${summary}</div>` : ''}
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
        console.log('NewsManager: News display updated successfully');
    }

    /**
     * Get relative time string from date
     * @param {string|number} date - Date string or timestamp
     * @returns {string} Relative time string
     */
    getTimeAgo(date) {
        if (!date) return 'Unknown';
        
        const timestamp = typeof date === 'string' ? new Date(date).getTime() : date;
        if (isNaN(timestamp)) return 'Unknown';
        
        const now = Date.now();
        const diff = now - timestamp;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;
        
        return new Date(timestamp).toLocaleDateString();
    }

    /**
     * Setup news UI interactions (period selector and refresh button)
     */
    setupNewsUI() {
        console.log('=== NewsManager: setupNewsUI START ===');
        
        // Setup period selector
        const periodSelector = document.getElementById('newsPeriod');
        if (periodSelector) {
            console.log('NewsManager: Period selector found, setting up event listener');
            // Remove existing listeners
            const newSelector = periodSelector.cloneNode(true);
            periodSelector.parentNode.replaceChild(newSelector, periodSelector);
            
            newSelector.addEventListener('change', (e) => {
                const period = e.target.value;
                console.log('NewsManager: Period changed to:', period);
                this.currentPeriod = period;
                
                // Update period display
                const periodLabels = { '1': '24h', '7': 'Week', '30': 'Month' };
                this.currentPeriod = periodLabels[period] || '24h';
                
                // Reload news if symbol is selected
                if (this.currentSymbol) {
                    this.loadNews(this.currentSymbol);
                }
            });
        } else {
            console.warn('NewsManager: Period selector not found');
        }
        
        // Setup refresh button
        const refreshButton = document.getElementById('refreshNews');
        if (refreshButton) {
            console.log('NewsManager: Refresh button found, setting up event listener');
            const newButton = refreshButton.cloneNode(true);
            refreshButton.parentNode.replaceChild(newButton, refreshButton);
            
            newButton.addEventListener('click', () => {
                console.log('NewsManager: Refresh button clicked');
                if (this.currentSymbol) {
                    this.loadNews(this.currentSymbol);
                } else {
                    // Show hint if no stock selected
                    const container = document.getElementById('newsContainer');
                    if (container) {
                        container.innerHTML = `
                            <div class="news-empty">
                                <p>Select a stock to view news</p>
                                <p class="news-hint">Enter a symbol above or select from Popular Stocks</p>
                            </div>
                        `;
                    }
                }
            });
        } else {
            console.warn('NewsManager: Refresh button not found');
        }
        
        console.log('=== NewsManager: setupNewsUI END ===');
    }

    /**
     * Get current period
     * @returns {string} Current period
     */
    getCurrentPeriod() {
        return this.currentPeriod;
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        console.log('NewsManager: Cleaned up');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NewsManager;
} else {
    window.NewsManager = NewsManager;
}

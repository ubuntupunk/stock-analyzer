// Tab Management Module
// Handles tab switching, content loading, and tab state management

class TabManager {
    constructor(dataManager, eventBus, uiManager = null) {
        this.dataManager = dataManager;
        this.eventBus = eventBus;
        this.uiManager = uiManager; // Store reference to UIManager for breadcrumb updates
        this.currentTab = 'popular-stocks';
        this.tabHistory = [];
        this.sectionsLoaded = new Set(); // Track which sections are loaded
        
        // Tab display names for breadcrumbs
        this.tabDisplayNames = {
            'popular-stocks': 'Popular Stocks',
            'metrics': 'Metrics',
            'financials': 'Financials',
            'factors': 'Factors',
            'analyst-estimates': 'Analyst Estimates',
            'news': 'News',
            'stock-analyser': 'Stock Analyser',
            'watchlist': 'Watchlist'
        };
        
        // Subscribe to tab events
        this.setupEventListeners();
    }

    /**
     * Get the display name for a tab
     * @param {string} tabName - Tab identifier
     * @returns {string} Display name
     */
    getTabDisplayName(tabName) {
        return this.tabDisplayNames[tabName] || tabName;
    }

    /**
     * Setup event listeners for tab-related events
     */
    setupEventListeners() {
        console.log('TabManager: setupEventListeners called');
        
        // Subscribe to tab events
        this.eventBus.on('tab:switch', ({ tabName }) => {
            console.log('TabManager: Received tab:switch event for:', tabName);
            this.switchTab(tabName);
        });

        // Subscribe to stock selection events
        // Note: StockManager now handles tab switching via targetTab
        // This is kept for backward compatibility if no targetTab is provided
        this.eventBus.on('stock:selected', ({ symbol, targetTab }) => {
            console.log('TabManager: Received stock:selected event for:', symbol, 'targetTab:', targetTab);
            // Only auto-switch to metrics if no targetTab is specified
            // StockManager emits the correct tab via tab:switch event
        });

        // Subscribe to watchlist loaded event to trigger rendering if section exists
        this.eventBus.on('watchlist:loaded', ({ watchlist }) => {
            console.log('TabManager: Watchlist loaded event received, count:', watchlist?.length);
            // If we're on the watchlist tab and section is loaded, ensure rendering
            if (this.currentTab === 'watchlist' && document.getElementById('watchlistContainer')) {
                console.log('TabManager: On watchlist tab, triggering render if needed');
                // The WatchlistManager should have already rendered, but this is a safety net
                if (window.watchlistManager && watchlist?.length > 0) {
                    const grid = document.getElementById('watchlistGrid');
                    if (grid && grid.children.length === 0) {
                        console.log('TabManager: Grid is empty, triggering render');
                        window.watchlistManager.renderWatchlist();
                    }
                }
            }
        });
    }

    /**
     * Switch to a specific tab
     * @param {string} tabName - Tab name to switch to
     */
    switchTab(tabName) {
        console.log('TabManager: switchTab called with:', tabName);
        
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(tab => {
            tab.classList.remove('active');
        });
        const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
            console.log('TabManager: Active tab set to:', tabName);
        } else {
            console.warn('TabManager: Tab element not found for:', tabName);
        }

        // Hide all content sections (but DON'T destroy them)
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });

        // Show the target section if it exists
        const targetSection = document.getElementById(tabName);
        if (targetSection) {
            targetSection.classList.add('active');
            console.log('TabManager: Section activated:', tabName);
        }

        // Track tab history (don't add duplicates)
        if (this.tabHistory[this.tabHistory.length - 1] !== tabName) {
            this.tabHistory.push(tabName);
            if (this.tabHistory.length > 10) this.tabHistory.shift();
        }

        this.currentTab = tabName;
        console.log('TabManager: Current tab set to:', tabName);

        // Update breadcrumbs with current tab
        if (this.uiManager) {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            this.uiManager.updateBreadcrumbs(currentSymbol, this.getTabDisplayName(tabName));
        }

        // Load content for the specific tab (only if needed)
        console.log('TabManager: Loading content for tab:', tabName);
        this.loadTabContent(tabName);

        // Emit tab switched event
        this.eventBus.emit('tab:switched', { tabName, previousTab: this.tabHistory[this.tabHistory.length - 2] });
    }

    /**
     * Load a section dynamically
     * @param {string} sectionName - Section name
     */
    async loadSection(sectionName) {
        try {
            console.log('TabManager: loadSection called for:', sectionName);

            // Check if already loaded in DOM
            const existingSection = document.getElementById(sectionName);
            if (existingSection) {
                console.log('TabManager: Section already in DOM:', sectionName);
                return;
            }

            console.log('TabManager: Fetching sections/' + sectionName + '.html');
            const response = await fetch(`sections/${sectionName}.html`);
            console.log('TabManager: Fetch response status:', response.status);

            if (!response.ok) {
                console.error('TabManager: Failed to fetch section, status:', response.status);
                return;
            }

            const html = await response.text();
            console.log('TabManager: Fetched HTML length:', html.length);

            // Create a temporary div to parse the HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;

            // Get the section element
            const section = tempDiv.firstElementChild;
            console.log('TabManager: Parsed section element:', section?.id, section?.tagName);

            if (section) {
                // Append to container without clearing
                const dynamicContainer = document.getElementById('dynamic-content-container');
                console.log('TabManager: dynamic-content-container found:', !!dynamicContainer);

                if (dynamicContainer) {
                    dynamicContainer.appendChild(section);
                    this.sectionsLoaded.add(sectionName);
                    console.log('TabManager: Section loaded successfully:', sectionName);

                    // Verify it's in the DOM
                    const verifySection = document.getElementById(sectionName);
                    console.log('TabManager: Verification - section in DOM:', !!verifySection);
                    
                    // Emit section loaded event
                    this.eventBus.emit('section:loaded', { sectionName });
                }
            }
        } catch (error) {
            console.error('TabManager: Failed to load section:', sectionName, error);
        }
    }

    /**
     * Load content for a specific tab
     * @param {string} tabName - Tab name
     */
    async loadTabContent(tabName) {
        console.log('TabManager: loadTabContent called for:', tabName);
        try {
            switch (tabName) {
                case 'analyst-estimates':
                    console.log('TabManager: Loading analyst-estimates data');
                    await this.loadSection('analyst-estimates');
                    await this.loadAnalystEstimatesData();
                    break;
                case 'metrics':
                    console.log('TabManager: Loading metrics data');
                    await this.loadSection('metrics');
                    await this.loadMetricsData();
                    break;
                case 'financials':
                    console.log('TabManager: Loading financials data');
                    await this.loadSection('financials');
                    await this.loadFinancialsData();
                    break;
                case 'factors':
                    console.log('TabManager: Loading factors data');
                    await this.loadSection('factors');
                    // Trigger FactorsManager to render after section loads
                    if (window.factorsManager) {
                        window.factorsManager.onTabActivated();
                    }
                    await this.loadFactorsData();
                    break;
                case 'stock-analyser':
                    console.log('TabManager: Loading stock-analyser data');
                    await this.loadSection('stock-analyser');
                    await this.loadStockAnalyserData();
                    break;
                case 'watchlist':
                    console.log('TabManager: Loading watchlist data');
                    await this.loadSection('watchlist');
                    await this.loadWatchlistData();
                    break;
                case 'popular-stocks':
                    console.log('TabManager: Loading popular-stocks data');
                    await this.loadSection('popular-stocks');
                    await this.loadPopularStocksData();
                    break;
                case 'news':
                    console.log('TabManager: Loading news data');
                    await this.loadSection('news');
                    // Delegate to NewsManager - it will handle loading if needed
                    if (window.newsManager) {
                        const currentSymbol = window.stockManager?.getCurrentSymbol();
                        if (currentSymbol) {
                            window.newsManager.loadNews(currentSymbol);
                        }
                    }
                    break;
                case 'retirement-calculator':
                    console.log('TabManager: Loading retirement-calculator');
                    await this.loadSection('retirement-calculator');
                    break;
                case 'real-estate-calculator':
                    console.log('TabManager: Loading real-estate-calculator');
                    await this.loadSection('real-estate-calculator');
                    break;
                case 'model-portfolio':
                    console.log('TabManager: Loading model-portfolio');
                    await this.loadSection('model-portfolio');
                    break;
                default:
                    console.warn('Unknown tab:', tabName);
            }
        } catch (error) {
            console.error(`Failed to load tab ${tabName}:`, error);
            this.eventBus.emit('tab:error', { tabName, error: error.message });
        }
    }

    /**
     * Load analyst estimates tab
     */
    async loadAnalystEstimatesTab() {
        console.log('TabManager: loadAnalystEstimatesTab called');
        try {
            const dynamicContentContainer = document.getElementById('dynamic-content-container');
            if (dynamicContentContainer) {
                dynamicContentContainer.classList.add('active');
            }

            await componentLoader.loadSection('analyst-estimates');
            
            // Load data if stock is selected
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'analyst-estimates');
            }
        } catch (error) {
            console.error('TabManager: Failed to load analyst-estimates tab:', error);
            // Don't switch back to popular-stocks on error
        }
    }

    /**
     * Load metrics tab
     */
    async loadMetricsTab() {
        console.log('TabManager: loadMetricsTab called');
        try {
            await componentLoader.loadSection('metrics');
            
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'metrics');
            }
        } catch (error) {
            console.error('TabManager: Failed to load metrics tab:', error);
        }
    }

    /**
     * Load financials tab
     */
    async loadFinancialsTab() {
        console.log('TabManager: loadFinancialsTab called');
        try {
            await componentLoader.loadSection('financials');
            
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'financials');
            }
        } catch (error) {
            console.error('TabManager: Failed to load financials tab:', error);
        }
    }

    /**
     * Load factors tab
     */
    async loadFactorsTab() {
        console.log('TabManager: loadFactorsTab called');
        try {
            await componentLoader.loadSection('factors');
            
            // Trigger FactorsManager to render after section loads
            if (window.factorsManager) {
                window.factorsManager.onTabActivated();
            }
            
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'factors');
            } else {
                // Load user factors when no stock selected
                await this.dataManager.loadStockData(null, 'user-factors');
            }
        } catch (error) {
            console.error('TabManager: Failed to load factors tab:', error);
        }
    }

    /**
     * Load stock analyser tab
     */
    async loadStockAnalyserTab() {
        console.log('TabManager: loadStockAnalyserTab called');
        await componentLoader.loadSection('stock-analyser');
        
        const currentSymbol = window.stockManager?.getCurrentSymbol();
        console.log('TabManager: currentSymbol for stock-analyser:', currentSymbol);
        if (currentSymbol) {
            console.log('TabManager: Loading stock analyser data for:', currentSymbol);
            const data = await this.dataManager.loadStockData(currentSymbol, 'stock-analyser');
            console.log('TabManager: Loaded stock analyser data:', data);
        }
    }

    /**
     * Load watchlist tab
     */
    async loadWatchlistTab() {
        await componentLoader.loadSection('watchlist');
        await this.dataManager.loadWatchlist();
    }

    /**
     * Load popular stocks tab
     */
    async loadPopularStocksTab() {
        console.log('TabManager: loadPopularStocksTab called');
        try {
            console.log('TabManager: Loading popular-stocks section');
            await componentLoader.loadSection('popular-stocks');
            console.log('TabManager: Section loaded, now getting popular stocks data');
            
            // Load popular stocks through the stock manager
            if (window.stockManager) {
                await window.stockManager.loadPopularStocks();
            } else {
                await this.dataManager.getPopularStocks();
            }
            
            console.log('TabManager: Popular stocks tab loaded successfully');
        } catch (error) {
            console.error('TabManager: Failed to load popular stocks tab:', error);
            // Don't throw error to prevent tab switching loop
        }
    }

    /**
     * Load news tab
     */
    async loadNewsTab() {
        const dynamicContentContainer = document.getElementById('dynamic-content-container');
        if (dynamicContentContainer) {
            dynamicContentContainer.classList.add('active');
        }

        await componentLoader.loadSection('news');
        
        const currentSymbol = window.stockManager?.getCurrentSymbol();
        if (currentSymbol) {
            await this.dataManager.loadStockData(currentSymbol, 'news');
        } else {
            const newsContainer = document.getElementById('newsContainer');
            if (newsContainer) {
                newsContainer.innerHTML = '<p class="empty-message">Select a stock to view news</p>';
            }
        }
    }

    /**
     * Update tab buttons to show active state
     * @param {string} activeTabName - Name of active tab
     */
    updateTabButtons(activeTabName) {
        // Remove active class from all tabs
        document.querySelectorAll('.tab-btn').forEach(tab => {
            tab.classList.remove('active');
        });

        // Add active class to selected tab
        const activeTab = document.querySelector(`[data-tab="${activeTabName}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
        }
    }

    /**
     * Hide all content sections
     */
    hideAllSections() {
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
    }

    /**
     * Validate tab name
     * @param {string} tabName - Tab name to validate
     * @returns {boolean} Whether tab is valid
     */
    isValidTab(tabName) {
        const validTabs = [
            'metrics',
            'financials',
            'factors',
            'analyst-estimates',
            'news',
            'stock-analyser',
            'watchlist',
            'popular-stocks',
            'factor-search',
            'retirement-calculator',
            'model-portfolio',
            'real-estate-calculator'
        ];
        
        return validTabs.includes(tabName);
    }

    /**
     * Add tab to history
     * @param {string} tabName - Tab name to add
     */
    addToHistory(tabName) {
        // Don't add duplicate consecutive entries
        if (this.tabHistory[this.tabHistory.length - 1] !== tabName) {
            this.tabHistory.push(tabName);
            
            // Limit history to 20 entries
            if (this.tabHistory.length > 20) {
                this.tabHistory.shift();
            }
        }
    }

    /**
     * Go back to previous tab
     * @returns {boolean} Whether navigation was successful
     */
    goBack() {
        if (this.tabHistory.length > 1) {
            this.tabHistory.pop(); // Remove current tab
            const previousTab = this.tabHistory.pop(); // Get previous tab
            this.switchTab(previousTab);
            return true;
        }
        return false;
    }

    /**
     * Get current tab
     * @returns {string} Current tab name
     */
    getCurrentTab() {
        return this.currentTab;
    }

    /**
     * Get tab history
     * @returns {Array} Tab history array
     */
    getTabHistory() {
        return [...this.tabHistory];
    }

    /**
     * Clear tab history
     */
    clearHistory() {
        this.tabHistory = [this.currentTab];
    }

    /**
     * Get tab navigation info
     * @returns {object} Navigation info
     */
    getNavigationInfo() {
        return {
            current: this.currentTab,
            canGoBack: this.tabHistory.length > 1,
            history: this.getTabHistory(),
            validTabs: [
                'metrics',
                'financials',
                'factors',
                'analyst-estimates',
                'news',
                'stock-analyser',
                'watchlist',
                'popular-stocks'
            ]
        };
    }

    /**
     * Setup tab click handlers
     */
    setupTabHandlers() {
        console.log('TabManager: setupTabHandlers called');
        
        // Use a more robust polling approach for DOM readiness
        const checkAndSetup = () => {
            const tabs = document.querySelectorAll('.tab-btn');
            const scrollContainer = document.querySelector('.tabs-scroll-container');
            
            if (tabs.length > 0) {
                console.log('TabManager: Found', tabs.length, 'tab elements');
                
                tabs.forEach((tab, index) => {
                    const tabName = tab.getAttribute('data-tab');
                    console.log(`TabManager: Setting up handler for tab ${index}: ${tabName}`);
                    
                    tab.addEventListener('click', (e) => {
                        console.log('TabManager: Tab clicked:', tabName);
                        if (tabName) {
                            this.switchTab(tabName);
                        }
                    });
                });
                
                // Setup carousel navigation handlers
                this.setupCarouselHandlers();
            } else {
                // Try again after a short delay
                setTimeout(checkAndSetup, 50);
            }
        };
        
        // Start checking
        checkAndSetup();
    }
    
    /**
     * Setup carousel navigation buttons (mobile)
     */
    setupCarouselHandlers() {
        const prevBtn = document.querySelector('.tab-carousel-prev');
        const nextBtn = document.querySelector('.tab-carousel-next');
        const scrollContainer = document.querySelector('.tabs-scroll-container');
        const tabsContainer = document.querySelector('.tabs-container');
        
        if (!prevBtn || !nextBtn || !scrollContainer) {
            console.log('TabManager: Carousel elements not found yet, retrying...');
            setTimeout(() => this.setupCarouselHandlers(), 100);
            return;
        }
        
        // Left arrow - scroll left
        prevBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.scrollTabsLeft();
        });
        
        // Right arrow - scroll right
        nextBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.scrollTabsRight();
        });
        
        // Update button visibility based on scroll position
        scrollContainer.addEventListener('scroll', () => {
            this.updateCarouselButtons();
        });
        
        // Update on window resize
        window.addEventListener('resize', () => {
            this.updateCarouselButtons();
        });
        
        // Initial button state
        this.updateCarouselButtons();
        
        // Add touch swipe support for mobile
        this.setupTouchSwipe(scrollContainer);
        
        console.log('TabManager: Carousel handlers setup complete');
    }
    
    /**
     * Scroll tabs container left
     */
    scrollTabsLeft() {
        const scrollContainer = document.querySelector('.tabs-scroll-container');
        if (scrollContainer) {
            const tabWidth = scrollContainer.querySelector('.tab-btn')?.offsetWidth || 100;
            scrollContainer.scrollBy({
                left: -tabWidth * 2,
                behavior: 'smooth'
            });
        }
    }
    
    /**
     * Scroll tabs container right
     */
    scrollTabsRight() {
        const scrollContainer = document.querySelector('.tabs-scroll-container');
        if (scrollContainer) {
            const tabWidth = scrollContainer.querySelector('.tab-btn')?.offsetWidth || 100;
            scrollContainer.scrollBy({
                left: tabWidth * 2,
                behavior: 'smooth'
            });
        }
    }
    
    /**
     * Update carousel arrow button visibility based on scroll position
     */
    updateCarouselButtons() {
        const scrollContainer = document.querySelector('.tabs-scroll-container');
        const prevBtn = document.querySelector('.tab-carousel-prev');
        const nextBtn = document.querySelector('.tab-carousel-next');
        
        if (scrollContainer && prevBtn && nextBtn) {
            const maxScroll = scrollContainer.scrollWidth - scrollContainer.clientWidth;
            const currentScroll = scrollContainer.scrollLeft;
            
            // Show/hide prev button based on scroll position
            if (currentScroll > 10) {
                prevBtn.classList.remove('disabled');
                prevBtn.style.opacity = '1';
                prevBtn.style.pointerEvents = 'auto';
            } else {
                prevBtn.classList.add('disabled');
                prevBtn.style.opacity = '0.3';
                prevBtn.style.pointerEvents = 'none';
            }
            
            // Show/hide next button based on scroll position
            if (currentScroll < maxScroll - 10) {
                nextBtn.classList.remove('disabled');
                nextBtn.style.opacity = '1';
                nextBtn.style.pointerEvents = 'auto';
            } else {
                nextBtn.classList.add('disabled');
                nextBtn.style.opacity = '0.3';
                nextBtn.style.pointerEvents = 'none';
            }
        }
    }
    
    /**
     * Setup touch swipe support for carousel
     * @param {HTMLElement} element - Scroll container element
     */
    setupTouchSwipe(element) {
        if (!element) return;
        
        let touchStartX = 0;
        let touchStartY = 0;
        let touchEndX = 0;
        let touchEndY = 0;
        const minSwipeDistance = 30;
        
        // Get the container for bounds calculation
        const container = element;
        
        const handleTouchStart = (e) => {
            // Store both X and Y to distinguish horizontal from vertical swipes
            touchStartX = e.changedTouches[0].screenX;
            touchStartY = e.changedTouches[0].screenY;
        };
        
        const handleTouchEnd = (e) => {
            touchEndX = e.changedTouches[0].screenX;
            touchEndY = e.changedTouches[0].screenY;
            this.handleSwipe();
        };
        
        const handleSwipe = () => {
            const diffX = touchEndX - touchStartX;
            const diffY = touchEndY - touchStartY;
            
            // Only handle horizontal swipes (ignore vertical scrolling)
            if (Math.abs(diffX) > Math.abs(diffY)) {
                const swipeDistance = diffX;
                
                if (Math.abs(swipeDistance) > minSwipeDistance) {
                    if (swipeDistance > 0) {
                        // Swipe right - scroll left (show previous tabs)
                        this.scrollTabsLeft();
                    } else {
                        // Swipe left - scroll right (show next tabs)
                        this.scrollTabsRight();
                    }
                }
            }
        };
        
        // Use passive: false to allow preventDefault() if needed
        element.addEventListener('touchstart', handleTouchStart, { passive: true });
        element.addEventListener('touchend', handleTouchEnd, { passive: true });
        
        console.log('TabManager: Touch swipe support enabled');
    }

    /**
     * Enable/disable tab based on conditions
     * @param {string} tabName - Tab name
     * @param {boolean} enabled - Whether tab should be enabled
     */
    setTabEnabled(tabName, enabled) {
        const tab = document.querySelector(`[data-tab="${tabName}"]`);
        if (tab) {
            if (enabled) {
                tab.classList.remove('disabled');
                tab.disabled = false;
            } else {
                tab.classList.add('disabled');
                tab.disabled = true;
            }
        }
    }

    /**
     * Show tab loading state
     * @param {string} tabName - Tab name
     */
    showTabLoading(tabName) {
        const tab = document.querySelector(`[data-tab="${tabName}"]`);
        if (tab) {
            tab.classList.add('loading');
        }
    }

    /**
     * Hide tab loading state
     * @param {string} tabName - Tab name
     */
    hideTabLoading(tabName) {
        const tab = document.querySelector(`[data-tab="${tabName}"]`);
        if (tab) {
            tab.classList.remove('loading');
        }
    }

    /**
     * Set tab badge
     * @param {string} tabName - Tab name
     * @param {string|number} badge - Badge content
     */
    setTabBadge(tabName, badge) {
        const tab = document.querySelector(`[data-tab="${tabName}"]`);
        if (tab) {
            // Remove existing badge
            const existingBadge = tab.querySelector('.tab-badge');
            if (existingBadge) {
                existingBadge.remove();
            }

            // Add new badge if provided
            if (badge) {
                const badgeElement = document.createElement('span');
                badgeElement.className = 'tab-badge';
                badgeElement.textContent = badge;
                tab.appendChild(badgeElement);
            }
        }
    }

    /**
     * Get tab statistics
     * @returns {object} Tab statistics
     */
    getTabStats() {
        const tabs = document.querySelectorAll('.tab-btn');
        const stats = {
            total: tabs.length,
            active: 0,
            disabled: 0,
            loading: 0
        };

        tabs.forEach(tab => {
            if (tab.classList.contains('active')) stats.active++;
            if (tab.classList.contains('disabled')) stats.disabled++;
            if (tab.classList.contains('loading')) stats.loading++;
        });

        return stats;
    }

    /**
     * Load popular stocks data
     */
    async loadPopularStocksData() {
        console.log('TabManager: loadPopularStocksData called');
        try {
            if (window.stockManager) {
                await window.stockManager.loadPopularStocks();
            }
        } catch (error) {
            console.error('TabManager: Failed to load popular stocks data:', error);
        }
    }

    /**
     * Load metrics data
     */
    async loadMetricsData() {
        console.log('TabManager: loadMetricsData called');
        try {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'metrics');
            }
            // Setup custom range handlers after metrics section is loaded
            if (window.chartManager && window.chartManager.setupCustomRangeHandlers) {
                setTimeout(() => {
                    window.chartManager.setupCustomRangeHandlers();
                    console.log('TabManager: Custom range handlers re-initialized');
                }, 100);
            }
            // Load saved metrics view preference
            if (window.metricsManager && window.metricsManager.loadViewPreference) {
                window.metricsManager.loadViewPreference();
            }
        } catch (error) {
            console.error('TabManager: Failed to load metrics data:', error);
        }
    }

    /**
     * Load financials data
     */
    async loadFinancialsData() {
        console.log('TabManager: loadFinancialsData called');
        try {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'financials');
            }
        } catch (error) {
            console.error('TabManager: Failed to load financials data:', error);
        }
    }

    /**
     * Load factors data
     */
    async loadFactorsData() {
        console.log('TabManager: loadFactorsData called');
        try {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'factors');
            } else {
                // No stock selected - just show empty factors or user factors if available
                console.log('TabManager: No stock selected for factors tab');
                // Emit event to show empty state
                this.eventBus.emit('data:loaded', { 
                    symbol: null, 
                    type: 'factors', 
                    data: { message: 'Select a stock to view factors' } 
                });
            }
        } catch (error) {
            console.error('TabManager: Failed to load factors data:', error);
        }
    }

    /**
     * Load stock analyser data
     */
    async loadStockAnalyserData() {
        console.log('TabManager: loadStockAnalyserData called');
        try {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'stock-analyser');
            }
        } catch (error) {
            console.error('TabManager: Failed to load stock analyser data:', error);
        }
    }

    /**
     * Load watchlist data
     */
    async loadWatchlistData() {
        console.log('TabManager: loadWatchlistData called');

        // Prevent duplicate loading - check if recently loaded
        const now = Date.now();
        if (this._lastWatchlistLoad && (now - this._lastWatchlistLoad < 500)) {
            console.log('TabManager: Watchlist recently loaded, skipping duplicate call');
            return;
        }
        this._lastWatchlistLoad = now;

        // Prevent duplicate loading - check if already loading
        if (this._watchlistLoading) {
            console.log('TabManager: Watchlist already loading, skipping');
            return;
        }

        this._watchlistLoading = true;

        try {
            // Ensure section is loaded first
            console.log('TabManager: Ensuring watchlist section is loaded');
            const sectionExists = document.getElementById('watchlistContainer');
            if (!sectionExists) {
                console.log('TabManager: Watchlist section not in DOM, waiting for it');
                await this.waitForSection('watchlistContainer', 2500);
            }

            // Call watchlistManager.loadWatchlist() which properly renders the UI
            console.log('TabManager: Calling watchlistManager.loadWatchlist()');
            await window.watchlistManager?.loadWatchlist();
            console.log('TabManager: watchlistManager.loadWatchlist() completed');
        } catch (error) {
            console.error('TabManager: Failed to load watchlist data:', error);
        } finally {
            this._watchlistLoading = false;
        }
    }

    /**
     * Wait for a specific section to appear in DOM
     */
    async waitForSection(sectionId, maxWaitMs = 2500) {
        const maxAttempts = maxWaitMs / 50;
        let attempts = 0;
        
        while (!document.getElementById(sectionId) && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 50));
            attempts++;
        }
        
        const exists = !!document.getElementById(sectionId);
        console.log(`TabManager: waitForSection(${sectionId}): exists=${exists} after ${attempts * 50}ms`);
        return exists;
    }

    /**
     * Load news data
     */
    async loadNewsData() {
        console.log('TabManager: loadNewsData called');
        try {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'news');
            }
        } catch (error) {
            console.error('TabManager: Failed to load news data:', error);
        }
    }

    /**
     * Load analyst estimates data
     */
    async loadAnalystEstimatesData() {
        console.log('TabManager: loadAnalystEstimatesData called');
        try {
            const currentSymbol = window.stockManager?.getCurrentSymbol();
            if (currentSymbol) {
                await this.dataManager.loadStockData(currentSymbol, 'analyst-estimates');
            }
        } catch (error) {
            console.error('TabManager: Failed to load analyst estimates data:', error);
        }
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        // Remove event listeners
        this.eventBus.off('tab:switch', this.switchTab);
        console.log('TabManager: Cleaned up');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TabManager;
} else {
    window.TabManager = TabManager;
}

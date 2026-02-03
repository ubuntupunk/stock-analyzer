// Financials Management Module
// Handles financial statements tab switching and period selection

class FinancialsManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.currentStatement = 'income';
        this.currentPeriod = 'annual';
        this.setupEventListeners();
    }

    /**
     * Setup event listeners for financials interactions
     */
    setupEventListeners() {
        // Listen for data loaded events
        this.eventBus.on('data:loaded', ({ type, data, symbol }) => {
            if (type === 'financials') {
                console.log('FinancialsManager: Financials data loaded, setting up UI');
                // Use a small delay to ensure DOM is fully updated
                setTimeout(() => this.setupFinancialsUI(), 50);
            }
        });

        // Listen for tab switched events to reinitialize UI
        this.eventBus.on('tab:switched', ({ tabName }) => {
            if (tabName === 'financials') {
                console.log('FinancialsManager: Financials tab switched, setting up UI');
                // Wait a bit longer for section to load and render
                setTimeout(() => this.setupFinancialsUI(), 200);
            }
        });

        // Also listen for section loaded events
        this.eventBus.on('section:loaded', ({ sectionName }) => {
            if (sectionName === 'financials') {
                console.log('FinancialsManager: Financials section loaded, setting up UI');
                setTimeout(() => this.setupFinancialsUI(), 100);
            }
        });
    }

    /**
     * Setup financials UI interactions (statement tabs and period selectors)
     */
    setupFinancialsUI() {
        console.log('=== FinancialsManager: setupFinancialsUI START ===');
        console.log('FinancialsManager: Current DOM state:', {
            financialsSection: !!document.getElementById('financials'),
            financialsTabs: !!document.querySelector('.financials-tabs'),
            incomeStatement: !!document.getElementById('incomeStatement'),
            balanceSheet: !!document.getElementById('balanceSheet'),
            cashFlowStatement: !!document.getElementById('cashFlowStatement')
        });
        
        // Setup statement tab buttons (Income, Balance, Cash Flow)
        // Using .financials-tabs .tab-btn to match the SCSS styling
        const statementTabs = document.querySelectorAll('.financials-tabs .tab-btn');
        console.log('FinancialsManager: Found', statementTabs.length, 'statement tabs');
        
        if (statementTabs.length === 0) {
            console.warn('FinancialsManager: No statement tabs found! Available classes:', 
                Array.from(document.querySelectorAll('[class*="tab"]')).map(el => el.className)
            );
        }
        
        statementTabs.forEach((tab, index) => {
            console.log(`FinancialsManager: Setting up tab ${index}:`, {
                dataStatement: tab.getAttribute('data-statement'),
                classList: Array.from(tab.classList),
                textContent: tab.textContent
            });
            
            // Remove existing listeners to prevent duplicates
            const newTab = tab.cloneNode(true);
            tab.parentNode.replaceChild(newTab, tab);
            
            newTab.addEventListener('click', (e) => {
                const statement = newTab.getAttribute('data-statement');
                console.log('FinancialsManager: Statement tab clicked:', statement);
                this.switchStatement(statement);
            });
        });

        // Setup period selectors
        console.log('FinancialsManager: Setting up period selectors');
        this.setupPeriodSelector('incomePeriod');
        this.setupPeriodSelector('balancePeriod');
        this.setupPeriodSelector('cashflowPeriod');
        
        console.log('=== FinancialsManager: setupFinancialsUI END ===');
    }

    /**
     * Setup period selector event listener
     * @param {string} selectorId - Period selector element ID
     */
    setupPeriodSelector(selectorId) {
        console.log(`FinancialsManager: Setting up period selector: ${selectorId}`);
        const selector = document.getElementById(selectorId);
        if (selector) {
            console.log(`FinancialsManager: Period selector ${selectorId} FOUND`);
            // Remove existing listeners
            const newSelector = selector.cloneNode(true);
            selector.parentNode.replaceChild(newSelector, selector);
            
            newSelector.addEventListener('change', (e) => {
                const period = e.target.value;
                console.log(`FinancialsManager: Period changed for ${selectorId}:`, period);
                this.currentPeriod = period;
                // In future, this could trigger a reload with quarterly data
                this.eventBus.emit('financials:periodChanged', { period });
            });
        } else {
            console.warn(`FinancialsManager: Period selector ${selectorId} NOT FOUND`);
        }
    }

    /**
     * Switch between financial statement views
     * @param {string} statement - Statement type (income, balance, cashflow)
     */
    switchStatement(statement) {
        console.log('=== FinancialsManager: switchStatement START ===');
        console.log('FinancialsManager: Switching to statement:', statement);
        
        // Update active tab button
        const allTabs = document.querySelectorAll('.financials-tabs .tab-btn');
        console.log('FinancialsManager: Found tabs to update:', allTabs.length);
        allTabs.forEach((tab, index) => {
            console.log(`FinancialsManager: Tab ${index} before:`, {
                dataStatement: tab.getAttribute('data-statement'),
                hasActive: tab.classList.contains('active')
            });
            tab.classList.remove('active');
        });
        
        const activeTab = document.querySelector(`.financials-tabs .tab-btn[data-statement="${statement}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
            console.log('FinancialsManager: Active tab set:', statement);
        } else {
            console.error('FinancialsManager: Active tab NOT FOUND for statement:', statement);
        }

        // Hide all statement content divs
        const allContent = document.querySelectorAll('.statement-content');
        console.log('FinancialsManager: Found content divs to hide:', allContent.length);
        allContent.forEach((content, index) => {
            console.log(`FinancialsManager: Content ${index} before:`, {
                id: content.id,
                hasActive: content.classList.contains('active'),
                display: window.getComputedStyle(content).display
            });
            content.classList.remove('active');
        });

        // Show selected statement content
        let contentId;
        switch (statement) {
            case 'income':
                contentId = 'incomeStatement';
                break;
            case 'balance':
                contentId = 'balanceSheet';
                break;
            case 'cashflow':
                contentId = 'cashFlowStatement';
                break;
        }

        console.log('FinancialsManager: Looking for content element:', contentId);
        const content = document.getElementById(contentId);
        if (content) {
            content.classList.add('active');
            console.log('FinancialsManager: Activated content:', contentId);
            console.log('FinancialsManager: Content after activation:', {
                hasActive: content.classList.contains('active'),
                display: window.getComputedStyle(content).display,
                classList: Array.from(content.classList)
            });
        } else {
            console.error('FinancialsManager: Content element NOT FOUND:', contentId);
            console.log('FinancialsManager: Available content elements:', 
                Array.from(document.querySelectorAll('.statement-content')).map(el => el.id)
            );
        }

        this.currentStatement = statement;
        console.log('FinancialsManager: Emitting financials:statementChanged event');
        this.eventBus.emit('financials:statementChanged', { statement });
        console.log('=== FinancialsManager: switchStatement END ===');
    }

    /**
     * Get current statement type
     * @returns {string} Current statement type
     */
    getCurrentStatement() {
        return this.currentStatement;
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
        console.log('FinancialsManager: Cleaned up');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FinancialsManager;
} else {
    window.FinancialsManager = FinancialsManager;
}

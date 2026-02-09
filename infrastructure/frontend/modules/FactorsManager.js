/**
 * FactorsManager - Manages factor-based stock screening
 * Handles factor building blocks, custom factors, and screening results
 */
class FactorsManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.factors = [];
        this.customFactors = [];
        this.currentStock = null;
        this.dropZoneSetup = false; // Guard to prevent duplicate event listeners
        this.availableFactors = [
            { id: 'pe_ratio', name: 'P/E Ratio', category: 'valuation', description: '5yr P/E Ratio' },
            { id: 'roic', name: 'ROIC', category: 'profitability', description: '5yr Return on Invested Capital' },
            { id: 'revenue_growth', name: 'Revenue Growth', category: 'growth', description: '5yr Revenue Growth' },
            { id: 'debt_to_equity', name: 'Debt to Equity', category: 'financial_health', description: 'Debt to Equity Ratio' },
            { id: 'current_ratio', name: 'Current Ratio', category: 'financial_health', description: 'Current Ratio' },
            { id: 'price_to_fcf', name: 'Price to FCF', category: 'valuation', description: '5yr Price to Free Cash Flow' }
        ];
        this.operators = ['>', '<', '>=', '<=', '=', '!='];
        this.screenResults = [];

        // Default values for quick add - sensible defaults for each factor type
        this.factorDefaults = {
            'pe_ratio': { operator: '>', value: 15 },
            'roic': { operator: '>', value: 15 },
            'revenue_growth': { operator: '>', value: 10 },
            'debt_to_equity': { operator: '<', value: 1 },
            'current_ratio': { operator: '>', value: 1.5 },
            'price_to_fcf': { operator: '>', value: 15 }
        };

        this.init();
    }

    init() {
        console.log('FactorsManager initialized');
        // Delay initialization to ensure DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initAfterDOMReady();
            });
        } else {
            // DOM is already ready, but wait a tick for dynamic content
            setTimeout(() => this.initAfterDOMReady(), 100);
        }
    }

    initAfterDOMReady() {
        console.log('FactorsManager: DOM ready, initializing...');
        this.loadCustomFactorsFromBackend();

        this.setupActiveListDropZone();
        this.renderFactorBlocks();
        this.renderActiveFactors();
    }

    setupEventListeners() {
        // Stock input
        const stockInput = document.getElementById('factorStockInput');
        if (stockInput) {
            stockInput.addEventListener('change', (e) => this.handleStockChange(e.target.value));
        }

        // Add custom factor button
        const addFactorBtn = document.getElementById('addFactorBtn');
        if (addFactorBtn) {
            addFactorBtn.addEventListener('click', () => this.showCustomFactorModal());
        }

        // Screen stocks button
        const screenBtn = document.getElementById('screenStocksBtn');
        if (screenBtn) {
            screenBtn.addEventListener('click', () => this.screenStocks());
        }

        // Clear factors button
        const clearBtn = document.getElementById('clearFactorsBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearFactors());
        }

        // Export CSV button
        const exportBtn = document.getElementById('exportResultsBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportToCSV());
        }

        // Custom factor modal buttons
        const saveCustomBtn = document.getElementById('saveCustomFactorBtn');
        if (saveCustomBtn) {
            saveCustomBtn.addEventListener('click', () => this.saveCustomFactor());
        }

        const cancelCustomBtn = document.getElementById('cancelCustomFactorBtn');
        if (cancelCustomBtn) {
            cancelCustomBtn.addEventListener('click', () => this.hideCustomFactorModal());
        }

        // Modal close button
        const modalClose = document.querySelector('#customFactorModal .modal-close');
        if (modalClose) {
            modalClose.addEventListener('click', () => this.hideCustomFactorModal());
        }

        // Close modal on outside click
        const modal = document.getElementById('customFactorModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideCustomFactorModal();
                }
            });
        }

        // Listen for stock changes from other modules
        this.eventBus.on('stock:selected', (data) => {
            this.handleStockChange(data.symbol);
        });
    }

    handleStockChange(symbol) {
        this.currentStock = symbol ? symbol.toUpperCase() : null;
        const stockDisplay = document.getElementById('currentStockDisplay');
        if (stockDisplay) {
            stockDisplay.textContent = this.currentStock || 'No stock selected';
        }
        console.log('Current stock for factors:', this.currentStock);
    }

    renderFactorBlocks() {
        const container = document.getElementById('factorBlocksContainer');
        if (!container) return;

        container.innerHTML = '';

        // Render available factor building blocks
        this.availableFactors.forEach(factor => {
            const block = this.createFactorBlock(factor);
            container.appendChild(block);
        });

        // Render custom factors
        this.customFactors.forEach(factor => {
            const block = this.createCustomFactorBlock(factor);
            container.appendChild(block);
        });
    }

    createFactorBlock(factor) {
        const block = document.createElement('div');
        block.className = `factor-block factor-block-${factor.category}`;
        block.draggable = true;
        block.dataset.factorId = factor.id;
        block.dataset.factorName = factor.name;
        block.dataset.factorCategory = factor.category;

        const categoryColors = {
            valuation: '#3b82f6',
            profitability: '#10b981',
            growth: '#8b5cf6',
            financial_health: '#f59e0b'
        };

        const defaults = this.factorDefaults[factor.id] || { operator: '>', value: 10 };

        // Generate operator options with the default pre-selected
        const operatorOptions = this.operators.map(op =>
            `<option value="${op}" ${op === defaults.operator ? 'selected' : ''}>${op}</option>`
        ).join('');

        block.innerHTML = `
            <div class="factor-block-header" style="background: ${categoryColors[factor.category] || '#6b7280'}">
                <span class="factor-block-icon">📊</span>
                <span class="factor-block-name">${factor.name}</span>
                <button class="factor-quick-add" title="Add with defaults">
                    <i class="fas fa-plus"></i>
                </button>
            </div>
            <div class="factor-block-body">
                <p class="factor-description">${factor.description}</p>
                <div class="factor-controls">
                    <select class="factor-operator" data-factor="${factor.id}">
                        ${operatorOptions}
                    </select>
                    <input type="number" class="factor-value" data-factor="${factor.id}"
                           placeholder="Value" value="${defaults.value}" step="0.1">
                    <button class="factor-add-btn" data-factor="${factor.id}">
                        <i class="fas fa-plus"></i> Add
                    </button>
                </div>
            </div>
        `;

        // Quick add button - uses defaults, no popup
        const quickAddBtn = block.querySelector('.factor-quick-add');
        quickAddBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.quickAddFactor(factor);
        });

        // Inline Add button - uses current values in dropdown and input
        const addBtn = block.querySelector('.factor-add-btn');
        addBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.addFactorFromBlock(factor);
        });

        // Drag and drop handlers for blocks
        block.addEventListener('dragstart', (e) => this.handleBlockDragStart(e, factor));
        block.addEventListener('dragend', (e) => this.handleBlockDragEnd(e));

        return block;
    }

    /**
     * Add factor using values from the inline controls in the block
     */
    addFactorFromBlock(factor) {
        // We need to find the block that was clicked - use event target
        const addBtn = event.target.closest('.factor-add-btn');
        if (!addBtn) return;

        const blockEl = addBtn.closest('.factor-block');
        if (!blockEl) return;

        const operator = blockEl.querySelector('.factor-operator').value;
        const value = parseFloat(blockEl.querySelector('.factor-value').value);

        if (isNaN(value)) {
            alert('Please enter a valid number');
            return;
        }

        this.addFactorToScreenDirect(factor, operator, value);
    }

    quickAddFactor(factor) {
        // Use preloaded defaults - no popup dialogs
        const defaults = this.factorDefaults[factor.id] || { operator: '>', value: 10 };
        this.addFactorToScreenDirect(factor, defaults.operator, defaults.value);
    }

    addFactorToScreenDirect(factor, operator, value) {
        const screenFactor = {
            id: factor.id,
            name: factor.name,
            operator: operator,
            value: value,
            category: factor.category
        };

        this.factors.push(screenFactor);
        this.renderActiveFactors();

        console.log('Factor added to screen:', screenFactor);
    }

    createCustomFactorBlock(factor) {
        const block = document.createElement('div');
        block.className = 'factor-block factor-block-custom';
        block.dataset.factorId = factor.id;

        block.innerHTML = `
            <div class="factor-block-header" style="background: #ec4899">
                <span class="factor-block-icon">⭐</span>
                <span class="factor-block-name">${factor.name}</span>
                <button class="factor-delete-btn" data-factor="${factor.id}">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="factor-block-body">
                <p class="factor-description">${factor.description}</p>
                <div class="factor-custom-criteria">
                    ${factor.criteria}
                </div>
            </div>
        `;

        // Add delete listener
        const deleteBtn = block.querySelector('.factor-delete-btn');
        deleteBtn.addEventListener('click', () => this.deleteCustomFactor(factor.id));

        return block;
    }

    addFactorToScreen(factor) {
        const operatorSelect = document.querySelector(`.factor-operator[data-factor="${factor.id}"]`);
        const valueInput = document.querySelector(`.factor-value[data-factor="${factor.id}"]`);

        if (!operatorSelect || !valueInput || !valueInput.value) {
            alert('Please set operator and value for the factor');
            return;
        }

        const screenFactor = {
            id: factor.id,
            name: factor.name,
            operator: operatorSelect.value,
            value: parseFloat(valueInput.value),
            category: factor.category
        };

        this.factors.push(screenFactor);
        this.renderActiveFactors();

        // Clear the inputs
        valueInput.value = '';

        console.log('Factor added to screen:', screenFactor);
    }

    renderActiveFactors() {
        const container = document.getElementById('activeFactorsList');
        if (!container) return;

        if (this.factors.length === 0) {
            container.innerHTML = '<p class="no-factors">No active factors. Add factors from the building blocks above.</p>';
            return;
        }

        container.innerHTML = '<h3>Active Screening Factors:</h3>';
        const list = document.createElement('div');
        list.className = 'active-factors-grid';
        list.id = 'activeFactorsGrid';

        this.factors.forEach((factor, index) => {
            const item = document.createElement('div');
            item.className = 'active-factor-item';
            item.draggable = true;
            item.dataset.index = index;

            // Get category color for this factor
            const categoryColors = {
                valuation: '#3b82f6',
                profitability: '#10b981',
                growth: '#8b5cf6',
                financial_health: '#f59e0b'
            };
            const borderColor = categoryColors[factor.category] || '#6b7280';

            item.style.borderLeftColor = borderColor;
            item.style.background = `linear-gradient(135deg, ${borderColor}15, ${borderColor}05)`;

            item.innerHTML = `
                <span class="drag-handle" title="Drag to reorder">
                    <i class="fas fa-grip-vertical"></i>
                </span>
                <span class="active-factor-text">
                    ${index + 1}. ${factor.name} ${factor.operator} ${factor.value}
                </span>
                <button class="active-factor-remove" data-index="${index}">
                    <i class="fas fa-times"></i>
                </button>
            `;

            const removeBtn = item.querySelector('.active-factor-remove');
            removeBtn.addEventListener('click', () => this.removeFactor(index));

            // Drag and drop handlers
            item.addEventListener('dragstart', (e) => this.handleDragStart(e, index));
            item.addEventListener('dragover', (e) => this.handleDragOver(e));
            item.addEventListener('drop', (e) => this.handleDrop(e, index));
            item.addEventListener('dragend', (e) => this.handleDragEnd(e));

            list.appendChild(item);
        });

        container.appendChild(list);
    }

    // Drag and Drop handlers for factor blocks
    handleBlockDragStart(e, factor) {
        e.dataTransfer.effectAllowed = 'copy';
        e.dataTransfer.setData('application/json', JSON.stringify({
            type: 'factor-block',
            factor: factor
        }));
        e.target.classList.add('dragging');
    }

    handleBlockDragEnd(e) {
        e.target.classList.remove('dragging');
    }

    // Drag and Drop handlers for active factors (reordering)
    handleDragStart(e, index) {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('application/json', JSON.stringify({
            type: 'active-factor',
            index: index
        }));
        e.target.classList.add('dragging');
    }

    handleDragOver(e) {
        if (e.preventDefault) {
            e.preventDefault();
        }
        e.dataTransfer.dropEffect = 'move';
        return false;
    }

    handleDrop(e, dropIndex) {
        // Stop propagation to prevent container handler from also handling this drop
        if (e.stopPropagation) {
            e.stopPropagation();
        }
        e.preventDefault();
        e.stopImmediatePropagation();

        try {
            const data = JSON.parse(e.dataTransfer.getData('application/json'));

            if (data.type === 'active-factor') {
                // Reordering active factors - only handle on individual items
                const dragIndex = data.index;
                if (dragIndex !== dropIndex) {
                    const draggedItem = this.factors[dragIndex];
                    this.factors.splice(dragIndex, 1);
                    this.factors.splice(dropIndex, 0, draggedItem);
                    this.renderActiveFactors();
                }
            }
            // Factor blocks are handled by the container drop zone only
        } catch (error) {
            console.error('Error handling drop:', error);
        }

        return false;
    }

    handleDragEnd(e) {
        e.target.classList.remove('dragging');
    }

    // Drop zone for active factors list
    setupActiveListDropZone() {
        const activeList = document.getElementById('activeFactorsList');
        if (!activeList || this.dropZoneSetup) return;

        this.dropZoneSetup = true;

        activeList.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
            activeList.classList.add('drop-zone-active');
        });

        activeList.addEventListener('dragleave', (e) => {
            if (e.target === activeList) {
                activeList.classList.remove('drop-zone-active');
            }
        });

        activeList.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            activeList.classList.remove('drop-zone-active');

            try {
                const data = JSON.parse(e.dataTransfer.getData('application/json'));
                if (data.type === 'factor-block') {
                    this.quickAddFactor(data.factor);
                }
            } catch (error) {
                console.error('Error handling drop on active list:', error);
            }
        });
    }

    removeFactor(index) {
        this.factors.splice(index, 1);
        this.renderActiveFactors();
    }

    clearFactors() {
        this.factors = [];
        this.renderActiveFactors();
        this.clearResults();
    }

    async screenStocks() {
        if (this.factors.length === 0) {
            alert('Please add at least one factor to screen stocks');
            return;
        }

        const resultsContainer = document.getElementById('screenResults');
        if (resultsContainer) {
            resultsContainer.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Screening stocks...</div>';
        }

        try {
            // Convert factors to API format (backend expects min/max format)
            const criteria = {};
            this.factors.forEach(factor => {
                const key = factor.id;
                const operator = factor.operator;
                const value = factor.value;

                // Convert operator to min/max format expected by backend
                if (operator === '>' || operator === '>=') {
                    criteria[key] = { min: value };
                } else if (operator === '<' || operator === '<=') {
                    criteria[key] = { max: value };
                } else if (operator === '=') {
                    criteria[key] = { min: value, max: value };
                } else if (operator === '!=') {
                    // Not equal is harder to handle with min/max, skip for now
                    console.warn(`Operator ${operator} not fully supported yet`);
                }
            });

            const response = await fetch(`${API_BASE_URL}/screener/screen`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ criteria })
            });

            if (!response.ok) {
                throw new Error('Failed to screen stocks');
            }

            const data = await response.json();
            this.screenResults = data || [];
            this.renderResults();

        } catch (error) {
            console.error('Error screening stocks:', error);
            if (resultsContainer) {
                resultsContainer.innerHTML = `<p class="error">Error screening stocks: ${error.message}</p>`;
            }
        }
    }

    renderResults() {
        const container = document.getElementById('screenResults');
        const exportBtn = document.getElementById('exportResultsBtn');

        if (!container) return;

        if (this.screenResults.length === 0) {
            container.innerHTML = '<p class="no-results">No stocks match your criteria</p>';
            if (exportBtn) exportBtn.style.display = 'none';
            return;
        }

        // Show export button when we have results
        if (exportBtn) exportBtn.style.display = 'inline-flex';

        let html = `
            <h3>Screening Results (${this.screenResults.length} stocks)</h3>
            <div class="results-table-container">
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Name</th>
                            <th>P/E Ratio</th>
                            <th>ROIC</th>
                            <th>Revenue Growth</th>
                            <th>D/E</th>
                            <th>Current Ratio</th>
                            <th>Price/FCF</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        this.screenResults.forEach(stock => {
            html += `
                <tr>
                    <td><strong>${stock.symbol}</strong></td>
                    <td>${stock.name || 'N/A'}</td>
                    <td>${this.formatValue(stock.pe_ratio)}</td>
                    <td>${this.formatValue(stock.roic, '%')}</td>
                    <td>${this.formatValue(stock.revenue_growth, '%')}</td>
                    <td>${this.formatValue(stock.debt_to_equity)}</td>
                    <td>${this.formatValue(stock.current_ratio)}</td>
                    <td>${this.formatValue(stock.price_to_fcf)}</td>
                    <td>
                        <button class="btn-view-stock" data-symbol="${stock.symbol}">
                            View
                        </button>
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = html;

        // Add click handlers for view buttons
        container.querySelectorAll('.btn-view-stock').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const symbol = e.target.dataset.symbol;
                this.eventBus.emit('stock:selected', { symbol });
            });
        });
    }

    clearResults() {
        const container = document.getElementById('screenResults');
        const exportBtn = document.getElementById('exportResultsBtn');

        if (container) {
            container.innerHTML = '';
        }
        if (exportBtn) {
            exportBtn.style.display = 'none';
        }
    }

    formatValue(value, suffix = '') {
        if (value === null || value === undefined) return 'N/A';
        if (typeof value === 'number') {
            return value.toFixed(2) + suffix;
        }
        return value + suffix;
    }

    showCustomFactorModal() {
        const modal = document.getElementById('customFactorModal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    hideCustomFactorModal() {
        const modal = document.getElementById('customFactorModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    async saveCustomFactor() {
        const nameInput = document.getElementById('customFactorName');
        const descInput = document.getElementById('customFactorDesc');
        const criteriaInput = document.getElementById('customFactorCriteria');

        if (!nameInput.value || !descInput.value || !criteriaInput.value) {
            alert('Please fill in all fields');
            return;
        }

        const customFactor = {
            id: `custom_${Date.now()}`,
            name: nameInput.value,
            description: descInput.value,
            criteria: criteriaInput.value,
            type: 'custom',
            createdAt: new Date().toISOString()
        };

        this.customFactors.push(customFactor);

        // Save to backend
        await this.saveCustomFactorToBackend(customFactor);

        this.renderFactorBlocks();
        this.hideCustomFactorModal();

        // Clear inputs
        nameInput.value = '';
        descInput.value = '';
        criteriaInput.value = '';
    }

    async saveCustomFactorToBackend(factor) {
        try {
            // Check if user is authenticated
            if (!window.userManager || !window.userManager.currentUser) {
                console.warn('User not authenticated, saving to localStorage only');
                this.saveCustomFactorsToLocalStorage();
                return;
            }

            const userId = window.userManager.currentUser.userId;

            const response = await fetch(`${API_BASE_URL}/factors`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${window.userManager.currentUser.token || ''}`
                },
                body: JSON.stringify({
                    factorId: factor.id,
                    name: factor.name,
                    criteria: factor.criteria,
                    description: factor.description,
                    createdAt: factor.createdAt
                })
            });

            if (!response.ok) {
                throw new Error('Failed to save custom factor to backend');
            }

            console.log('Custom factor saved to backend successfully');
        } catch (error) {
            console.error('Error saving to backend, falling back to localStorage:', error);
            this.saveCustomFactorsToLocalStorage();
        }
    }

    async loadCustomFactorsFromBackend() {
        try {
            // Check if user is authenticated
            if (!window.userManager || !window.userManager.currentUser) {
                console.log('User not authenticated, loading from localStorage');
                this.loadCustomFactorsFromLocalStorage();
                return;
            }

            const userId = window.userManager.currentUser.userId;

            const response = await fetch(`${API_BASE_URL}/factors`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${window.userManager.currentUser.token || ''}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load custom factors from backend');
            }

            const data = await response.json();
            if (Array.isArray(data)) {
                this.customFactors = data.map(f => ({
                    id: f.factorId,
                    name: f.name,
                    description: f.description || '',
                    criteria: f.criteria,
                    type: 'custom',
                    createdAt: f.createdAt
                }));
                console.log('Loaded custom factors from backend:', this.customFactors.length);
            }
        } catch (error) {
            console.error('Error loading from backend, falling back to localStorage:', error);
            this.loadCustomFactorsFromLocalStorage();
        }
    }

    async deleteCustomFactor(id) {
        if (!confirm('Are you sure you want to delete this custom factor?')) {
            return;
        }

        this.customFactors = this.customFactors.filter(f => f.id !== id);

        // Delete from backend
        try {
            if (window.userManager && window.userManager.currentUser) {
                await fetch(`${API_BASE_URL}/factors/${id}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${window.userManager.currentUser.token || ''}`
                    }
                });
            }
        } catch (error) {
            console.error('Error deleting from backend:', error);
        }

        this.saveCustomFactorsToLocalStorage();
        this.renderFactorBlocks();
    }

    loadCustomFactorsFromLocalStorage() {
        try {
            const stored = localStorage.getItem('customFactors');
            if (stored) {
                this.customFactors = JSON.parse(stored);
                console.log('Loaded custom factors from localStorage:', this.customFactors.length);
            }
        } catch (error) {
            console.error('Error loading custom factors from localStorage:', error);
        }
    }

    saveCustomFactorsToLocalStorage() {
        try {
            localStorage.setItem('customFactors', JSON.stringify(this.customFactors));
        } catch (error) {
            console.error('Error saving custom factors to localStorage:', error);
        }
    }

    // Export results to CSV
    exportToCSV() {
        if (this.screenResults.length === 0) {
            alert('No results to export. Please run a screen first.');
            return;
        }

        // Define CSV headers
        const headers = ['Symbol', 'Name', 'P/E Ratio', 'ROIC (%)', 'Revenue Growth (%)',
            'Debt/Equity', 'Current Ratio', 'Price/FCF'];

        // Build CSV content
        let csvContent = headers.join(',') + '\n';

        this.screenResults.forEach(stock => {
            const row = [
                stock.symbol || '',
                `"${(stock.name || '').replace(/"/g, '""')}"`, // Escape quotes
                stock.pe_ratio || '',
                stock.roic || '',
                stock.revenue_growth || '',
                stock.debt_to_equity || '',
                stock.current_ratio || '',
                stock.price_to_fcf || ''
            ];
            csvContent += row.join(',') + '\n';
        });

        // Create download link
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);

        link.setAttribute('href', url);
        link.setAttribute('download', `stock_screen_results_${new Date().toISOString().slice(0, 10)}.csv`);
        link.style.visibility = 'hidden';

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        console.log('Exported', this.screenResults.length, 'results to CSV');
    }

    // Public API
    getActiveFactors() {
        return this.factors;
    }

    getResults() {
        return this.screenResults;
    }

    // Called when the factors tab is activated
    onTabActivated() {
        console.log('FactorsManager: Tab activated, setting up event listeners and rendering blocks...');
        this.setupEventListeners(); // Setup listeners when tab is activated and content is in DOM
        // Wait a bit for DOM to be ready
        setTimeout(() => {
            this.setupActiveListDropZone();
            this.renderFactorBlocks();
            this.renderActiveFactors();
        }, 50);
    }
}

// Make available globally
if (typeof window !== 'undefined') {
    window.FactorsManager = FactorsManager;
}

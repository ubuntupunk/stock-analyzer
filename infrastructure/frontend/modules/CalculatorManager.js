/**
 * CalculatorManager.js
 * Handles all calculator functionality for the application
 */

class CalculatorManager {
    constructor() {
        this.initialized = false;
    }

    /**
     * Initialize the calculator
     */
    init() {
        console.log('CalculatorManager: Initializing');
        this.initialized = true;
    }

    /**
     * Format number as currency
     * @param {number} value - Number to format
     * @returns {string} Formatted currency string
     */
    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(value);
    }

    /**
     * Calculate retirement savings and display results
     */
    calculateRetirement() {
        console.log('CalculatorManager: calculateRetirement called');

        // Get input values
        const currentAge = parseFloat(document.getElementById('currentAge')?.value) || 0;
        const retirementAge = parseFloat(document.getElementById('retirementAge')?.value) || 65;
        const currentSavings = parseFloat(document.getElementById('currentSavings')?.value) || 0;
        const monthlyContribution = parseFloat(document.getElementById('monthlyContribution')?.value) || 0;
        const annualReturn = parseFloat(document.getElementById('annualReturn')?.value) || 7;
        const retirementGoal = parseFloat(document.getElementById('retirementGoal')?.value) || 1000000;

        // Validate inputs
        if (currentAge <= 0 || retirementAge <= 0 || currentAge >= retirementAge) {
            this.showError('Please enter valid ages (current age must be less than retirement age)');
            return;
        }

        // Calculate years to retirement
        const yearsToRetirement = retirementAge - currentAge;

        // Calculate projected savings using compound interest formula
        // FV = PV * (1 + r)^n + PMT * [(1 + r)^n - 1] / r
        const monthlyRate = annualReturn / 100 / 12;
        const totalMonths = yearsToRetirement * 12;

        let projectedSavings;
        if (monthlyRate === 0) {
            projectedSavings = currentSavings + (monthlyContribution * totalMonths);
        } else {
            projectedSavings = currentSavings * Math.pow(1 + monthlyRate, totalMonths) +
                              (monthlyContribution * (Math.pow(1 + monthlyRate, totalMonths) - 1)) / monthlyRate;
        }

        // Calculate monthly contribution needed to reach goal
        // PMT = (FV - PV * (1 + r)^n) * r / [(1 + r)^n - 1]
        const futureValueOfCurrentSavings = currentSavings * Math.pow(1 + monthlyRate, totalMonths);
        let monthlyNeeded;
        if (monthlyRate === 0) {
            monthlyNeeded = (retirementGoal - currentSavings) / totalMonths;
        } else {
            monthlyNeeded = (retirementGoal - futureValueOfCurrentSavings) * monthlyRate /
                           (Math.pow(1 + monthlyRate, totalMonths) - 1);
        }

        // Display results
        this.displayResults({
            projectedSavings: projectedSavings || 0,
            monthlyNeeded: monthlyNeeded > 0 ? monthlyNeeded : 0,
            yearsToRetirement: yearsToRetirement
        });
    }

    /**
     * Display calculation results
     * @param {Object} results - Calculation results
     */
    displayResults(results) {
        console.log('CalculatorManager: Displaying results', results);

        const projectedSavingsEl = document.getElementById('projectedSavings');
        const monthlyNeededEl = document.getElementById('monthlyNeeded');
        const yearsToRetirementEl = document.getElementById('yearsToRetirement');

        if (projectedSavingsEl) {
            projectedSavingsEl.textContent = this.formatCurrency(results.projectedSavings);
        }
        if (monthlyNeededEl) {
            monthlyNeededEl.textContent = this.formatCurrency(results.monthlyNeeded);
        }
        if (yearsToRetirementEl) {
            yearsToRetirementEl.textContent = results.yearsToRetirement;
        }
    }

    /**
     * Show error message
     * @param {string} message - Error message to display
     */
    showError(message) {
        console.error('CalculatorManager Error:', message);
        window.uiManager.showNotification(message, 'error');
    }
}

// Global calculator instance
const calculatorManager = new CalculatorManager();

// Make calculateRetirement globally accessible
window.calculateRetirement = function() {
    calculatorManager.calculateRetirement();
};

/**
 * Calculate Real Estate ROI and display results
 */
window.calculateRealEstate = function() {
    console.log('CalculatorManager: calculateRealEstate called');

    // Get input values
    const propertyValue = parseFloat(document.getElementById('propertyValue')?.value) || 0;
    const downPayment = parseFloat(document.getElementById('downPayment')?.value) || 0;
    const interestRate = parseFloat(document.getElementById('interestRate')?.value) || 6.5;
    const loanTerm = parseFloat(document.getElementById('loanTerm')?.value) || 30;
    const monthlyRent = parseFloat(document.getElementById('monthlyRent')?.value) || 0;
    const monthlyExpenses = parseFloat(document.getElementById('monthlyExpenses')?.value) || 0;

    // Validate inputs
    if (propertyValue <= 0 || downPayment < 0) {
        calculatorManager.showError('Please enter valid property values');
        return;
    }

    // Calculate loan amount
    const loanAmount = propertyValue - downPayment;

    // Calculate monthly mortgage payment (P&I)
    const monthlyRate = interestRate / 100 / 12;
    const totalPayments = loanTerm * 12;

    let monthlyPayment;
    if (monthlyRate === 0) {
        monthlyPayment = loanAmount / totalPayments;
    } else {
        monthlyPayment = loanAmount * (monthlyRate * Math.pow(1 + monthlyRate, totalPayments)) /
                         (Math.pow(1 + monthlyRate, totalPayments) - 1);
    }

    // Calculate cash flow
    const totalMonthlyExpenses = monthlyExpenses + monthlyPayment;
    const cashFlow = monthlyRent - totalMonthlyExpenses;

    // Calculate Annual ROI (Cash-on-Cash Return)
    const annualCashFlow = cashFlow * 12;
    const annualROI = downPayment > 0 ? (annualCashFlow / downPayment) * 100 : 0;

    // Calculate Cap Rate (Net Operating Income / Property Value)
    const annualRent = monthlyRent * 12;
    const annualExpenses = monthlyExpenses * 12;
    const netOperatingIncome = annualRent - annualExpenses;
    const capRate = propertyValue > 0 ? (netOperatingIncome / propertyValue) * 100 : 0;

    // Display results
    calculatorManager.displayRealEstateResults({
        monthlyPayment: monthlyPayment || 0,
        cashFlow: cashFlow || 0,
        annualROI: annualROI || 0,
        capRate: capRate || 0
    });
};

/**
 * Display real estate calculation results
 */
calculatorManager.displayRealEstateResults = function(results) {
    console.log('CalculatorManager: Displaying real estate results', results);

    const monthlyPaymentEl = document.getElementById('monthlyPayment');
    const cashFlowEl = document.getElementById('cashFlow');
    const annualROIEl = document.getElementById('annualROI');
    const capRateEl = document.getElementById('capRate');

    if (monthlyPaymentEl) {
        monthlyPaymentEl.textContent = this.formatCurrency(results.monthlyPayment);
    }
    if (cashFlowEl) {
        const prefix = results.cashFlow >= 0 ? '+' : '';
        cashFlowEl.textContent = prefix + this.formatCurrency(results.cashFlow);
        cashFlowEl.className = 'result-value ' + (results.cashFlow >= 0 ? 'positive' : 'negative');
    }
    if (annualROIEl) {
        annualROIEl.textContent = results.annualROI.toFixed(2) + '%';
        annualROIEl.className = 'result-value ' + (results.annualROI >= 0 ? 'positive' : 'negative');
    }
    if (capRateEl) {
        capRateEl.textContent = results.capRate.toFixed(2) + '%';
    }
};

/**
 * Select a model portfolio and display details
 */
window.selectModel = function(modelType) {
    console.log('CalculatorManager: selectModel called with:', modelType);

    const portfolioDetails = document.getElementById('portfolioDetails');
    if (!portfolioDetails) {
        console.error('CalculatorManager: portfolioDetails element not found');
        return;
    }

    // Remove selected class from all cards
    document.querySelectorAll('.model-card').forEach(card => {
        card.classList.remove('selected');
    });

    // Add selected class to clicked card
    const selectedCard = document.querySelector(`.model-card[data-risk="${modelType === 'conservative' ? 'low' : modelType === 'balanced' ? 'medium' : 'high'}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }

    const portfolios = {
        'conservative': {
            title: 'Conservative Portfolio',
            description: 'Low risk, stable returns',
            expectedReturn: '4-6%',
            bestFor: 'Near-term goals, risk-averse investors',
            allocation: [
                { asset: 'Bonds', percent: 60, color: '#27ae60' },
                { asset: 'Large Cap Stocks', percent: 30, color: '#3498db' },
                { asset: 'Cash', percent: 10, color: '#95a5a6' }
            ]
        },
        'balanced': {
            title: 'Balanced Portfolio',
            description: 'Moderate risk, balanced growth',
            expectedReturn: '6-8%',
            bestFor: 'Medium-term goals, moderate risk tolerance',
            allocation: [
                { asset: 'Large Cap Stocks', percent: 40, color: '#3498db' },
                { asset: 'Mid Cap Stocks', percent: 20, color: '#1abc9c' },
                { asset: 'Bonds', percent: 30, color: '#27ae60' },
                { asset: 'International', percent: 10, color: '#9b59b6' }
            ]
        },
        'aggressive': {
            title: 'Aggressive Portfolio',
            description: 'High risk, high growth potential',
            expectedReturn: '8-12%',
            bestFor: 'Long-term goals, high risk tolerance',
            allocation: [
                { asset: 'Large Cap Stocks', percent: 30, color: '#3498db' },
                { asset: 'Mid Cap Stocks', percent: 30, color: '#1abc9c' },
                { asset: 'Small Cap Stocks', percent: 20, color: '#e74c3c' },
                { asset: 'International', percent: 15, color: '#9b59b6' },
                { asset: 'Bonds', percent: 5, color: '#27ae60' }
            ]
        }
    };

    const portfolio = portfolios[modelType];
    if (!portfolio) {
        console.error('CalculatorManager: Unknown portfolio type:', modelType);
        return;
    }

    // Generate allocation bars HTML
    const allocationBars = portfolio.allocation.map(item => `
        <div class="allocation-bar-item">
            <div class="allocation-label">
                <span class="allocation-color" style="background-color: ${item.color}"></span>
                <span>${item.asset}</span>
                <span class="allocation-percent">${item.percent}%</span>
            </div>
            <div class="allocation-bar">
                <div class="allocation-fill" style="width: ${item.percent}%; background-color: ${item.color}"></div>
            </div>
        </div>
    `).join('');

    portfolioDetails.innerHTML = `
        <div class="portfolio-detail-card">
            <h3>${portfolio.title}</h3>
            <p class="portfolio-description">${portfolio.description}</p>
            
            <div class="portfolio-stats">
                <div class="stat-item">
                    <span class="stat-label">Expected Annual Return</span>
                    <span class="stat-value">${portfolio.expectedReturn}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Best For</span>
                    <span class="stat-value">${portfolio.bestFor}</span>
                </div>
            </div>
            
            <div class="allocation-breakdown">
                <h4>Asset Allocation</h4>
                ${allocationBars}
            </div>
        </div>
    `;
};

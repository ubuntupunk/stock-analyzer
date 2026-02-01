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
        alert(message);
    }
}

// Global calculator instance
const calculatorManager = new CalculatorManager();

// Make calculateRetirement globally accessible
window.calculateRetirement = function() {
    calculatorManager.calculateRetirement();
};

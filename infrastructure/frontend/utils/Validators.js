// Input validation utilities
// Handles symbol validation, input sanitization, and form validation

class Validators {
    /**
     * Validate stock symbol
     * @param {string} symbol - The stock symbol to validate
     * @returns {object} Validation result with isValid and error message
     */
    static validateStockSymbol(symbol) {
        if (!symbol || typeof symbol !== 'string') {
            return { isValid: false, error: 'Stock symbol is required' };
        }
        
        const cleanSymbol = symbol.trim().toUpperCase();
        
        // Check length
        if (cleanSymbol.length < 1 || cleanSymbol.length > 5) {
            return { isValid: false, error: 'Stock symbol must be 1-5 characters' };
        }
        
        // Check for valid characters (letters and numbers only)
        if (!/^[A-Z0-9]+$/.test(cleanSymbol)) {
            return { isValid: false, error: 'Stock symbol can only contain letters and numbers' };
        }
        
        // Check for common invalid symbols
        const invalidSymbols = ['NULL', 'UNDEFINED', 'NaN', 'NONE'];
        if (invalidSymbols.includes(cleanSymbol)) {
            return { isValid: false, error: 'Invalid stock symbol' };
        }
        
        return { isValid: true, symbol: cleanSymbol };
    }

    /**
     * Validate email address
     * @param {string} email - The email to validate
     * @returns {object} Validation result with isValid and error message
     */
    static validateEmail(email) {
        if (!email || typeof email !== 'string') {
            return { isValid: false, error: 'Email is required' };
        }
        
        const cleanEmail = email.trim();
        
        // Basic email regex
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(cleanEmail)) {
            return { isValid: false, error: 'Please enter a valid email address' };
        }
        
        return { isValid: true, email: cleanEmail };
    }

    /**
     * Validate password
     * @param {string} password - The password to validate
     * @returns {object} Validation result with isValid and error message
     */
    static validatePassword(password) {
        if (!password || typeof password !== 'string') {
            return { isValid: false, error: 'Password is required' };
        }
        
        if (password.length < 8) {
            return { isValid: false, error: 'Password must be at least 8 characters' };
        }
        
        if (!/[A-Z]/.test(password)) {
            return { isValid: false, error: 'Password must contain at least one uppercase letter' };
        }
        
        if (!/[a-z]/.test(password)) {
            return { isValid: false, error: 'Password must contain at least one lowercase letter' };
        }
        
        if (!/[0-9]/.test(password)) {
            return { isValid: false, error: 'Password must contain at least one number' };
        }
        
        return { isValid: true };
    }

    /**
     * Validate number within range
     * @param {number} value - The value to validate
     * @param {number} min - Minimum value
     * @param {number} max - Maximum value
     * @returns {object} Validation result with isValid and error message
     */
    static validateNumber(value, min = null, max = null) {
        if (value === null || value === undefined || value === '') {
            return { isValid: false, error: 'Value is required' };
        }
        
        const numValue = parseFloat(value);
        
        if (isNaN(numValue)) {
            return { isValid: false, error: 'Please enter a valid number' };
        }
        
        if (min !== null && numValue < min) {
            return { isValid: false, error: `Value must be at least ${min}` };
        }
        
        if (max !== null && numValue > max) {
            return { isValid: false, error: `Value must be no more than ${max}` };
        }
        
        return { isValid: true, value: numValue };
    }

    /**
     * Validate percentage value
     * @param {number} value - The percentage to validate
     * @returns {object} Validation result with isValid and error message
     */
    static validatePercentage(value) {
        return this.validateNumber(value, 0, 100);
    }

    /**
     * Validate DCF assumptions
     * @param {object} assumptions - DCF assumptions object
     * @returns {object} Validation result with isValid and error message
     */
    static validateDCFAssumptions(assumptions) {
        if (!assumptions || typeof assumptions !== 'object') {
            return { isValid: false, error: 'Assumptions are required' };
        }
        
        const errors = [];
        
        // Validate revenue growth
        if (assumptions.revenueGrowth) {
            const revenueGrowth = this.validatePercentage(assumptions.revenueGrowth.low);
            if (!revenueGrowth.isValid) errors.push('Revenue growth (low): ' + revenueGrowth.error);
        }
        
        // Validate profit margin
        if (assumptions.profitMargin) {
            const profitMargin = this.validatePercentage(assumptions.profitMargin.low);
            if (!profitMargin.isValid) errors.push('Profit margin (low): ' + profitMargin.error);
        }
        
        // Validate discount rate
        if (assumptions.discountRate) {
            const discountRate = this.validateNumber(assumptions.discountRate, 0, 50);
            if (!discountRate.isValid) errors.push('Discount rate: ' + discountRate.error);
        }
        
        if (errors.length > 0) {
            return { isValid: false, error: errors.join('; ') };
        }
        
        return { isValid: true };
    }

    /**
     * Sanitize user input
     * @param {string} input - The input to sanitize
     * @returns {string} Sanitized input
     */
    static sanitizeInput(input) {
        if (!input || typeof input !== 'string') {
            return '';
        }
        
        return input
            .trim()
            .replace(/[<>]/g, '') // Remove potential HTML tags
            .replace(/javascript:/gi, '') // Remove javascript protocol
            .replace(/on\w+=/gi, ''); // Remove event handlers
    }

    /**
     * Validate search query
     * @param {string} query - The search query to validate
     * @returns {object} Validation result with isValid and error message
     */
    static validateSearchQuery(query) {
        if (!query || typeof query !== 'string') {
            return { isValid: false, error: 'Search query is required' };
        }
        
        const cleanQuery = this.sanitizeInput(query);
        
        if (cleanQuery.length < 1) {
            return { isValid: false, error: 'Search query must be at least 1 character' };
        }
        
        if (cleanQuery.length > 100) {
            return { isValid: false, error: 'Search query is too long' };
        }
        
        return { isValid: true, query: cleanQuery };
    }

    /**
     * Validate watchlist item
     * @param {object} item - Watchlist item to validate
     * @returns {object} Validation result with isValid and error message
     */
    static validateWatchlistItem(item) {
        if (!item || typeof item !== 'object') {
            return { isValid: false, error: 'Watchlist item is required' };
        }
        
        const symbolValidation = this.validateStockSymbol(item.symbol);
        if (!symbolValidation.isValid) {
            return { isValid: false, error: 'Invalid stock symbol: ' + symbolValidation.error };
        }
        
        if (item.alertPrice !== undefined && item.alertPrice !== null) {
            const priceValidation = this.validateNumber(item.alertPrice, 0);
            if (!priceValidation.isValid) {
                return { isValid: false, error: 'Invalid alert price: ' + priceValidation.error };
            }
        }
        
        return { isValid: true };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Validators;
} else {
    window.Validators = Validators;
}

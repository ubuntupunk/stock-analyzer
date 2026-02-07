// Data formatting utilities
// Handles currency, percentage, date, and number formatting

class Formatters {
    /**
     * Format currency values with appropriate suffixes
     * @param {number} value - The value to format
     * @returns {string} Formatted currency string
     */
    static formatCurrency(value) {
        if (value === undefined || value === null) return 'N/A';
        if (typeof value !== 'number') return value;

        const isNegative = value < 0;
        const absValue = Math.abs(value);
        let formatted = '';

        if (absValue >= 1e9) {
            formatted = `$${(absValue / 1e9).toFixed(1)}B`;
        } else if (absValue >= 1e6) {
            formatted = `$${(absValue / 1e6).toFixed(1)}M`;
        } else if (absValue >= 1e3) {
            formatted = `$${(absValue / 1e3).toFixed(1)}K`;
        } else {
            formatted = `$${absValue.toFixed(0)}`;
        }

        return isNegative ? `-${formatted}` : formatted;
    }

    /**
     * Format percentage values
     * @param {number} value - The value to format (0-1 or 0-100)
     * @param {boolean} isDecimal - Whether the value is already decimal (0-1)
     * @returns {string} Formatted percentage string
     */
    static formatPercentage(value, isDecimal = true) {
        if (!value || value === 'N/A') return 'N/A';
        if (typeof value !== 'number') return value;

        const percentage = isDecimal ? value * 100 : value;
        return `${percentage.toFixed(1)}%`;
    }

    /**
     * Format date strings
     * @param {string|Date} date - The date to format
     * @param {string} format - The format to use ('short', 'long', 'time')
     * @returns {string} Formatted date string
     */
    static formatDate(date, format = 'short') {
        if (!date) return 'N/A';

        const dateObj = new Date(date);
        if (isNaN(dateObj.getTime())) return 'N/A';

        switch (format) {
            case 'short':
                return dateObj.toLocaleDateString();
            case 'long':
                return dateObj.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
            case 'time':
                return dateObj.toLocaleString();
            default:
                return dateObj.toLocaleDateString();
        }
    }

    /**
     * Format numbers with decimal places
     * @param {number} value - The number to format
     * @param {number} decimals - Number of decimal places
     * @returns {string} Formatted number string
     */
    static formatNumber(value, decimals = 2) {
        if (!value || value === 'N/A') return 'N/A';
        if (typeof value !== 'number') return value;

        return value.toFixed(decimals);
    }

    /**
     * Format large numbers with suffixes (K, M, B)
     * @param {number} value - The number to format
     * @returns {string} Formatted number string
     */
    static formatLargeNumber(value) {
        if (!value || value === 0) return 'N/A';
        if (typeof value !== 'number') return value;

        if (value >= 1e9) {
            return `${(value / 1e9).toFixed(1)}B`;
        } else if (value >= 1e6) {
            return `${(value / 1e6).toFixed(1)}M`;
        } else if (value >= 1e3) {
            return `${(value / 1e3).toFixed(1)}K`;
        } else {
            return value.toFixed(0);
        }
    }

    /**
     * Format stock price with appropriate precision
     * @param {number} price - The stock price
     * @returns {string} Formatted price string
     */
    static formatStockPrice(price) {
        if (!price || price === 'N/A') return 'N/A';
        if (typeof price !== 'number') return price;

        if (price >= 1000) {
            return `$${price.toFixed(0)}`;
        } else if (price >= 100) {
            return `$${price.toFixed(2)}`;
        } else {
            return `$${price.toFixed(3)}`;
        }
    }

    /**
     * Format ratio values (P/E, P/B, etc.)
     * @param {number} ratio - The ratio to format
     * @returns {string} Formatted ratio string
     */
    static formatRatio(ratio) {
        if (!ratio || ratio === 'N/A') return 'N/A';
        if (typeof ratio !== 'number') return ratio;

        return ratio.toFixed(2);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Formatters;
} else {
    window.Formatters = Formatters;
}

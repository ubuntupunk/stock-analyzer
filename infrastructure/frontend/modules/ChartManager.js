// Chart Management Module
// Handles Chart.js integration, chart creation, updates, and destruction

class ChartManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.charts = new Map();
        this.defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#ffffff',
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#ffffff',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)',
                        borderColor: 'rgba(255, 255, 255, 0.2)'
                    },
                    ticks: {
                        color: '#ffffff'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)',
                        borderColor: 'rgba(255, 255, 255, 0.2)'
                    },
                    ticks: {
                        color: '#ffffff'
                    }
                }
            }
        };
    }

    /**
     * Create a new chart
     * @param {string} canvasId - Canvas element ID
     * @param {string} type - Chart type (line, bar, etc.)
     * @param {object} data - Chart data
     * @param {object} options - Chart options
     * @returns {Chart} Chart instance
     */
    createChart(canvasId, type, data, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`Canvas element with id '${canvasId}' not found`);
            return null;
        }

        // Destroy existing chart if it exists
        this.destroyChart(canvasId);

        const mergedOptions = this.mergeOptions(options);
        
        try {
            const chart = new Chart(canvas, {
                type: type,
                data: data,
                options: mergedOptions
            });

            this.charts.set(canvasId, chart);
            
            this.eventBus.emit('chart:created', { canvasId, type, chart });
            
            return chart;
        } catch (error) {
            console.error(`Failed to create chart '${canvasId}':`, error);
            this.eventBus.emit('chart:error', { canvasId, error: error.message });
            return null;
        }
    }

    /**
     * Update existing chart data
     * @param {string} canvasId - Canvas element ID
     * @param {object} data - New chart data
     * @param {object} options - New chart options (optional)
     */
    updateChart(canvasId, data, options = null) {
        const chart = this.charts.get(canvasId);
        if (!chart) {
            console.warn(`Chart '${canvasId}' not found`);
            return;
        }

        try {
            chart.data = data;
            
            if (options) {
                chart.options = this.mergeOptions(options);
            }
            
            chart.update();
            
            this.eventBus.emit('chart:updated', { canvasId, chart });
        } catch (error) {
            console.error(`Failed to update chart '${canvasId}':`, error);
            this.eventBus.emit('chart:error', { canvasId, error: error.message });
        }
    }

    /**
     * Destroy a chart
     * @param {string} canvasId - Canvas element ID
     */
    destroyChart(canvasId) {
        const chart = this.charts.get(canvasId);
        if (chart) {
            chart.destroy();
            this.charts.delete(canvasId);
            this.eventBus.emit('chart:destroyed', { canvasId });
        }
    }

    /**
     * Destroy all charts
     */
    destroyAllCharts() {
        for (const [canvasId, chart] of this.charts) {
            chart.destroy();
        }
        this.charts.clear();
        this.eventBus.emit('chart:allDestroyed');
    }

    /**
     * Create price chart for stock
     * @param {string} canvasId - Canvas element ID
     * @param {object} priceData - Price data with historical prices
     * @param {string} symbol - Stock symbol
     * @returns {Chart} Chart instance
     */
    createPriceChart(canvasId, priceData, symbol) {
        if (!priceData || !priceData.historicalData) {
            console.error('No historical data available for price chart');
            return null;
        }

        const dates = Object.keys(priceData.historicalData).sort();
        const prices = dates.map(date => parseFloat(priceData.historicalData[date]['4. close']));
        
        // Take last 30 days for better visualization
        const recentDates = dates.slice(-30);
        const recentPrices = prices.slice(-30);

        const chartData = {
            labels: recentDates.map(date => this.formatChartDate(date)),
            datasets: [{
                label: `${symbol} Price`,
                data: recentPrices,
                borderColor: '#4ade80',
                backgroundColor: 'rgba(74, 222, 128, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.1,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: '#4ade80'
            }]
        };

        const options = {
            plugins: {
                title: {
                    display: true,
                    text: `${symbol} Stock Price (30 Days)`,
                    color: '#ffffff',
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    callbacks: {
                        title: (context) => {
                            const dateIndex = context[0].dataIndex;
                            const dateStr = recentDates[dateIndex];
                            // Show year in tooltip for multi-year ranges
                            return this.formatChartDateWithYear(dateStr);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(2);
                        }
                    }
                }
            }
        };

        const chart = this.createChart(canvasId, 'line', chartData, options);
        // Store symbol and dates on the chart object for tooltip access
        if (chart) {
            chart.symbol = symbol;
            chart.dates = recentDates;
        }
        return chart;
    }

    /**
     * Create analyst estimates chart
     * @param {string} canvasId - Canvas element ID
     * @param {object} estimatesData - Analyst estimates data
     * @param {string} symbol - Stock symbol
     * @returns {Chart} Chart instance
     */
    createEstimatesChart(canvasId, estimatesData, symbol) {
        if (!estimatesData) {
            console.error('No estimates data available');
            return null;
        }

        // Process earnings estimates
        const earningsEstimates = estimatesData.earnings_estimates || [];
        const revenueEstimates = estimatesData.revenue_estimates || [];

        // Combine data by period
        const periodMap = {};

        earningsEstimates.forEach(estimate => {
            const period = estimate.period || estimate.fiscalDateEnding || 'N/A';
            if (!periodMap[period]) {
                periodMap[period] = { period, eps: null, revenue: null };
            }
            periodMap[period].eps = estimate.avg;
        });

        revenueEstimates.forEach(estimate => {
            const period = estimate.period || estimate.fiscalDateEnding || 'N/A';
            if (!periodMap[period]) {
                periodMap[period] = { period, eps: null, revenue: null };
            }
            periodMap[period].revenue = estimate.avg;
        });

        const periods = Object.keys(periodMap).sort();
        const epsData = periods.map(period => periodMap[period].eps);
        const revenueData = periods.map(period => periodMap[period].revenue);

        const chartData = {
            labels: periods,
            datasets: [
                {
                    label: 'EPS Estimates',
                    data: epsData,
                    borderColor: '#60a5fa',
                    backgroundColor: 'rgba(96, 165, 250, 0.1)',
                    borderWidth: 2,
                    yAxisID: 'y',
                    tension: 0.1
                },
                {
                    label: 'Revenue Estimates (B)',
                    data: revenueData,
                    borderColor: '#f87171',
                    backgroundColor: 'rgba(248, 113, 113, 0.1)',
                    borderWidth: 2,
                    yAxisID: 'y1',
                    tension: 0.1
                }
            ]
        };

        const options = {
            plugins: {
                title: {
                    display: true,
                    text: `${symbol} Analyst Estimates`,
                    color: '#ffffff',
                    font: {
                        size: 16
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'EPS ($)',
                        color: '#60a5fa'
                    },
                    ticks: {
                        color: '#60a5fa'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Revenue (B)',
                        color: '#f87171'
                    },
                    ticks: {
                        color: '#f87171'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        };

        return this.createChart(canvasId, 'line', chartData, options);
    }

    /**
     * Create financial metrics chart
     * @param {string} canvasId - Canvas element ID
     * @param {object} metricsData - Financial metrics data
     * @param {string} symbol - Stock symbol
     * @returns {Chart} Chart instance
     */
    createMetricsChart(canvasId, metricsData, symbol) {
        if (!metricsData) {
            console.error('No metrics data available');
            return null;
        }

        const metrics = [
            { name: 'P/E Ratio', value: metricsData.peRatio || 0, color: '#4ade80' },
            { name: 'ROE', value: (metricsData.roe || 0) * 100, color: '#60a5fa' },
            { name: 'Revenue Growth', value: (metricsData.revenueGrowth || 0) * 100, color: '#f87171' },
            { name: 'Profit Margin', value: (metricsData.profitMargin || 0) * 100, color: '#fbbf24' }
        ];

        const chartData = {
            labels: metrics.map(m => m.name),
            datasets: [{
                label: 'Financial Metrics',
                data: metrics.map(m => m.value),
                backgroundColor: metrics.map(m => m.color),
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        };

        const options = {
            plugins: {
                title: {
                    display: true,
                    text: `${symbol} Key Metrics`,
                    color: '#ffffff',
                    font: {
                        size: 16
                    }
                },
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        };

        return this.createChart(canvasId, 'bar', chartData, options);
    }

    /**
     * Create DCF analysis chart
     * @param {string} canvasId - Canvas element ID
     * @param {object} dcfResults - DCF analysis results
     * @param {string} symbol - Stock symbol
     * @returns {Chart} Chart instance
     */
    createDCFChart(canvasId, dcfResults, symbol) {
        if (!dcfResults) {
            console.error('No DCF results available');
            return null;
        }

        const scenarios = ['Low', 'Mid', 'High'];
        const values = [
            dcfResults.low?.discountedCashFlowValue || 0,
            dcfResults.mid?.discountedCashFlowValue || 0,
            dcfResults.high?.discountedCashFlowValue || 0
        ];

        const currentPrice = dcfResults.currentPrice || 0;

        const chartData = {
            labels: scenarios,
            datasets: [
                {
                    label: 'DCF Valuation',
                    data: values,
                    backgroundColor: ['#f87171', '#fbbf24', '#4ade80'],
                    borderColor: '#ffffff',
                    borderWidth: 2
                },
                {
                    label: 'Current Price',
                    data: [currentPrice, currentPrice, currentPrice],
                    type: 'line',
                    borderColor: '#ffffff',
                    borderWidth: 2,
                    pointRadius: 0,
                    borderDash: [5, 5]
                }
            ]
        };

        const options = {
            plugins: {
                title: {
                    display: true,
                    text: `${symbol} DCF Analysis`,
                    color: '#ffffff',
                    font: {
                        size: 16
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(2);
                        }
                    }
                }
            }
        };

        return this.createChart(canvasId, 'bar', chartData, options);
    }

    /**
     * Merge default options with custom options
     * @param {object} customOptions - Custom chart options
     * @returns {object} Merged options
     */
    mergeOptions(customOptions) {
        return this.deepMerge(this.defaultOptions, customOptions);
    }

    /**
     * Deep merge two objects
     * @param {object} target - Target object
     * @param {object} source - Source object
     * @returns {object} Merged object
     */
    deepMerge(target, source) {
        const result = { ...target };
        
        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                result[key] = this.deepMerge(result[key] || {}, source[key]);
            } else {
                result[key] = source[key];
            }
        }
        
        return result;
    }

    /**
     * Format date for chart display
     * @param {string} dateString - Date string
     * @returns {string} Formatted date
     */
    formatChartDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric' 
        });
    }

    /**
     * Get chart instance
     * @param {string} canvasId - Canvas element ID
     * @returns {Chart|null} Chart instance
     */
    getChart(canvasId) {
        return this.charts.get(canvasId) || null;
    }

    /**
     * Get all charts
     * @returns {Map} All charts
     */
    getAllCharts() {
        return new Map(this.charts);
    }

    /**
     * Get chart statistics
     * @returns {object} Chart statistics
     */
    getChartStats() {
        return {
            totalCharts: this.charts.size,
            chartIds: Array.from(this.charts.keys()),
            charts: Array.from(this.charts.entries()).map(([id, chart]) => ({
                id,
                type: chart.config.type,
                datasets: chart.data.datasets.length
            }))
        };
    }

    /**
     * Export chart as image
     * @param {string} canvasId - Canvas element ID
     * @param {string} format - Image format ('png', 'jpeg')
     * @returns {string} Base64 image data
     */
    exportChart(canvasId, format = 'png') {
        const chart = this.charts.get(canvasId);
        if (!chart) {
            throw new Error(`Chart '${canvasId}' not found`);
        }

        return chart.toBase64Image(format);
    }

    /**
     * Resize all charts
     */
    resizeAllCharts() {
        for (const chart of this.charts.values()) {
            chart.resize();
        }
    }

    /**
     * Set chart theme
     * @param {string} theme - Theme name ('light', 'dark')
     */
    setTheme(theme) {
        const isDark = theme === 'dark';
        
        this.defaultOptions.plugins.legend.labels.color = isDark ? '#ffffff' : '#000000';
        this.defaultOptions.plugins.tooltip.backgroundColor = isDark ? 'rgba(0, 0, 0, 0.8)' : 'rgba(255, 255, 255, 0.8)';
        this.defaultOptions.plugins.tooltip.titleColor = isDark ? '#ffffff' : '#000000';
        this.defaultOptions.plugins.tooltip.bodyColor = isDark ? '#ffffff' : '#000000';
        this.defaultOptions.scales.x.grid.color = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
        this.defaultOptions.scales.x.ticks.color = isDark ? '#ffffff' : '#000000';
        this.defaultOptions.scales.y.grid.color = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
        this.defaultOptions.scales.y.ticks.color = isDark ? '#ffffff' : '#000000';

        // Update all existing charts
        for (const chart of this.charts.values()) {
            chart.options = this.deepMerge(chart.options, this.defaultOptions);
            chart.update();
        }
    }

    /**
     * Setup time frame button handlers
     */
    setupTimeframeHandlers() {
        const buttons = document.querySelectorAll(".timeframe-btn");
        buttons.forEach(btn => {
            btn.addEventListener("click", (e) => {
                const period = e.target.dataset.period;
                this.changeTimeframe(period);

                // Update active state
                buttons.forEach(b => b.classList.remove("active"));
                e.target.classList.add("active");
            });
        });

        // Setup custom range handlers
        this.setupCustomRangeHandlers();
    }

    /**
     * Setup custom date range handlers
     */
    setupCustomRangeHandlers() {
        const toggle = document.getElementById("customRangeToggle");
        const dateRangeDiv = document.getElementById("customDateRange");
        const startDateInput = document.getElementById("startDate");
        const endDateInput = document.getElementById("endDate");
        const applyBtn = document.getElementById("applyCustomRange");
        const cancelBtn = document.getElementById("cancelCustomRange");

        if (!toggle || !dateRangeDiv) return;

        // Toggle custom range visibility
        toggle.addEventListener("click", () => {
            const isHidden = dateRangeDiv.style.display === "none";
            dateRangeDiv.style.display = isHidden ? "flex" : "none";
            toggle.classList.toggle("active", isHidden);

            // Hide timeframe buttons when custom range is active
            document.querySelectorAll(".timeframe-btn").forEach(btn => {
                btn.style.display = isHidden ? "none" : "inline-block";
            });
        });

        // Apply custom range
        applyBtn.addEventListener("click", () => {
            const startDate = startDateInput.value;
            const endDate = endDateInput.value;

            if (startDate && endDate) {
                this.changeTimeframeCustom(startDate, endDate);

                // Hide custom range UI
                dateRangeDiv.style.display = "none";
            } else {
                alert("Please select both start and end dates");
            }
        });

        // Cancel custom range
        cancelBtn.addEventListener("click", () => {
            dateRangeDiv.style.display = "none";
            toggle.classList.remove("active");

            // Show timeframe buttons
            document.querySelectorAll(".timeframe-btn").forEach(btn => {
                btn.style.display = "inline-block";
            });
        });
    }

    /**
     * Change chart time frame with custom date range
     */
    async changeTimeframeCustom(startDate, endDate) {
        const chart = this.charts.get("priceChart");
        if (!chart) return;

        const symbol = chart.symbol || "Unknown";

        try {
            // Use window.api (global) to fetch historical data for custom range
            const priceData = await window.api.getStockPriceHistoryRange(symbol, startDate, endDate);
            if (priceData && priceData.historicalData) {
                const periodLabel = `${startDate} - ${endDate}`;
                this.updatePriceChartWithData("priceChart", priceData, symbol, periodLabel);
            }
        } catch (error) {
            console.error("Failed to change timeframe with custom range:", error);
        }
    }

    /**
     * Change chart time frame
     */
    async changeTimeframe(period) {
        const chart = this.charts.get("priceChart");
        if (!chart) return;
        
        const symbol = chart.symbol || "Unknown";
        const periodMap = {
            "1W": "5d", "1M": "1mo", "3M": "3mo", "6M": "6mo",
            "YTD": "ytd", "1Y": "1y", "3Y": "3y", "5Y": "5y", "MAX": "max"
        };
        
        try {
            const yfPeriod = periodMap[period] || "3mo";
            // Use window.api (global) to fetch historical data
            const priceData = await window.api.getStockPriceHistory(symbol, yfPeriod);
            if (priceData && priceData.historicalData) {
                this.updatePriceChartWithData("priceChart", priceData, symbol, period);
            }
        } catch (error) {
            console.error("Failed to change timeframe:", error);
        }
    }

    /**
     * Update price chart with new data and period
     */
    updatePriceChartWithData(canvasId, priceData, symbol, period) {
        if (!priceData || !priceData.historicalData) return null;
        
        const dates = Object.keys(priceData.historicalData).sort();
        const prices = dates.map(d => parseFloat(priceData.historicalData[d]["4. close"]));
        
        const chartData = {
            labels: dates.map(d => this.formatChartDate(d)),
            datasets: [{
                label: symbol + " Price",
                data: prices,
                borderColor: "#4ade80",
                backgroundColor: "rgba(74, 222, 128, 0.1)",
                borderWidth: 2,
                fill: true,
                tension: 0.1,
                pointRadius: dates.length > 60 ? 0 : 2
            }]
        };

        const options = {
            plugins: {
                title: {
                    display: true,
                    text: symbol + " Stock Price (" + period + ")",
                    color: "#ffffff",
                    font: { size: 16 }
                },
                tooltip: {
                    callbacks: {
                        title: (context) => {
                            const dateIndex = context[0].dataIndex;
                            const dateStr = dates[dateIndex];
                            // Show year in tooltip for multi-year ranges
                            return this.formatChartDateWithYear(dateStr);
                        }
                    }
                }
            },
            scales: {
                y: {
                    ticks: { callback: function(v) { return "$" + v.toFixed(2); } }
                }
            }
        };

        const existingChart = this.charts.get(canvasId);
        if (existingChart) {
            existingChart.data = chartData;
            existingChart.options = options;
            existingChart.dates = dates;
            existingChart.update();
            return existingChart;
        }
        return this.createChart(canvasId, "line", chartData, options);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChartManager;
} else {
    window.ChartManager = ChartManager;
}

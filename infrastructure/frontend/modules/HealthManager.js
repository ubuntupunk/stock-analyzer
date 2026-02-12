/**
 * Health Manager Module
 * Coordinates frontend circuit breaker with backend health status
 * Implements the Health Check Sync pattern to prevent desync
 */

class HealthManager {
    constructor(eventBus, circuitBreaker) {
        this.eventBus = eventBus;
        this.circuitBreaker = circuitBreaker;
        this.backendHealthy = true;
        this.healthCheckInterval = null;
        this.healthCheckUrl = null;
        this.healthCheckIntervalMs = 30000; // 30 seconds
        this.consecutiveFailures = 0;
        this.maxConsecutiveFailures = 3;

        // Get API URL from config
        if (window.CONFIG && window.CONFIG.apiUrl) {
            this.healthCheckUrl = `${window.CONFIG.apiUrl}/health`;
        }

        // Listen for circuit breaker state changes
        if (this.eventBus) {
            this.eventBus.on('circuit:opened', this.handleCircuitOpened.bind(this));
            this.eventBus.on('circuit:closed', this.handleCircuitClosed.bind(this));
        }
    }

    /**
     * Start periodic health checks
     */
    startHealthChecks() {
        if (this.healthCheckInterval) {
            console.log('HealthManager: Health checks already running');
            return;
        }

        // Run initial health check immediately
        this.checkBackendHealth();

        // Then run periodically
        this.healthCheckInterval = setInterval(() => {
            this.checkBackendHealth();
        }, this.healthCheckIntervalMs);

        console.log('HealthManager: Started periodic health checks');
    }

    /**
     * Stop periodic health checks
     */
    stopHealthChecks() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
            console.log('HealthManager: Stopped periodic health checks');
        }
    }

    /**
     * Check backend health status
     */
    async checkBackendHealth() {
        if (!this.healthCheckUrl) {
            console.warn('HealthManager: No health check URL configured');
            return;
        }

        try {
            const startTime = Date.now();
            const response = await fetch(this.healthCheckUrl, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                cache: 'no-store'
            });

            const latency = Date.now() - startTime;

            if (response.ok) {
                const healthData = await response.json();
                this.handleHealthyResponse(healthData, latency);
            } else {
                this.handleUnhealthyResponse(`HTTP ${response.status}`);
            }
        } catch (error) {
            this.handleUnhealthyResponse(error.message);
        }
    }

    /**
     * Handle a healthy response from the backend
     * @param {object} healthData - Health check response data
     * @param {number} latency - Request latency in ms
     */
    handleHealthyResponse(healthData, latency) {
        this.consecutiveFailures = 0;
        this.backendHealthy = true;

        // Emit health status event
        if (this.eventBus) {
            this.eventBus.emit('health:status', {
                status: 'healthy',
                latency,
                data: healthData
            });
        }

        // Sync circuit breaker with backend state
        this.syncCircuitBreakerWithBackend(healthData);

        console.log(`HealthManager: Backend healthy (${latency}ms)`);
    }

    /**
     * Handle an unhealthy response from the backend
     * @param {string} reason - Reason for unhealthy status
     */
    handleUnhealthyResponse(reason) {
        this.consecutiveFailures++;
        this.backendHealthy = false;

        // Emit unhealthy event
        if (this.eventBus) {
            this.eventBus.emit('health:status', {
                status: 'unhealthy',
                reason,
                consecutiveFailures: this.consecutiveFailures
            });
        }

        // Open circuit if too many consecutive failures
        if (this.consecutiveFailures >= this.maxConsecutiveFailures) {
            console.warn(`HealthManager: ${this.consecutiveFailures} consecutive failures, opening circuit`);
            this.circuitBreaker.state = 'OPEN';

            if (this.eventBus) {
                this.eventBus.emit('circuit:force-open', { reason });
            }
        }

        console.warn(`HealthManager: Backend unhealthy: ${reason}`);
    }

    /**
     * Sync frontend circuit breaker with backend health status
     * @param {object} backendHealth - Backend health report
     */
    syncCircuitBreakerWithBackend(backendHealth) {
        if (!backendHealth || !backendHealth.circuit_breaker) {
            return;
        }

        const backendState = backendHealth.circuit_breaker;

        // If backend is healthy but frontend circuit is OPEN, try HALF_OPEN
        if (this.circuitBreaker.state === 'OPEN' && backendState.status === 'healthy') {
            console.log('HealthManager: Backend recovered, transitioning to HALF_OPEN');
            this.circuitBreaker.state = 'HALF_OPEN';

            if (this.eventBus) {
                this.eventBus.emit('circuit:half-open', { source: 'health-sync' });
            }
        }
    }

    /**
     * Handle circuit breaker opened event
     * @param {object} data - Event data
     */
    handleCircuitOpened(data) {
        console.log('HealthManager: Circuit opened:', data);

        // Reduce health check frequency when circuit is open
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = setInterval(() => {
                this.checkBackendHealth();
            }, 15000); // Check every 15 seconds when circuit is open
        }
    }

    /**
     * Handle circuit breaker closed event
     * @param {object} data - Event data
     */
    handleCircuitClosed(data) {
        console.log('HealthManager: Circuit closed:', data);

        // Restore normal health check frequency
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = setInterval(() => {
                this.checkBackendHealth();
            }, this.healthCheckIntervalMs);
        }

        // Reset consecutive failures
        this.consecutiveFailures = 0;
        this.backendHealthy = true;
    }

    /**
     * Force open the circuit breaker (for manual intervention)
     */
    forceOpenCircuit() {
        this.circuitBreaker.state = 'OPEN';
        this.consecutiveFailures = this.maxConsecutiveFailures;

        if (this.eventBus) {
            this.eventBus.emit('circuit:force-open', { source: 'manual' });
        }

        console.log('HealthManager: Circuit force-opened');
    }

    /**
     * Force close the circuit breaker (for manual intervention)
     */
    forceCloseCircuit() {
        this.circuitBreaker.state = 'CLOSED';
        this.circuitBreaker.failures.clear();
        this.circuitBreaker.successes.clear();
        this.consecutiveFailures = 0;
        this.backendHealthy = true;

        if (this.eventBus) {
            this.eventBus.emit('circuit:force-closed', { source: 'manual' });
        }

        console.log('HealthManager: Circuit force-closed');
    }

    /**
     * Get current health status
     * @returns {object} Health status object
     */
    getHealthStatus() {
        return {
            backendHealthy: this.backendHealthy,
            frontendCircuitState: this.circuitBreaker?.state || 'UNKNOWN',
            consecutiveFailures: this.consecutiveFailures,
            lastCheck: new Date().toISOString()
        };
    }

    /**
     * Configure health check settings
     * @param {object} config - Configuration options
     */
    configure(config = {}) {
        if (config.intervalMs) {
            this.healthCheckIntervalMs = config.intervalMs;
        }
        if (config.maxFailures) {
            this.maxConsecutiveFailures = config.maxFailures;
        }
        if (config.healthCheckUrl) {
            this.healthCheckUrl = config.healthCheckUrl;
        }
    }

    /**
     * Clean up resources
     */
    cleanup() {
        this.stopHealthChecks();

        if (this.eventBus) {
            this.eventBus.off('circuit:opened');
            this.eventBus.off('circuit:closed');
        }

        console.log('HealthManager: Cleanup complete');
    }

    /**
     * Lifecycle: Initialize module (called once)
     */
    onInit() {
        console.log('[HealthManager] Initialized');
        this.isInitialized = true;
        this.isVisible = true;
    }

    /**
     * Lifecycle: Show module (resume operations)
     */
    onShow() {
        console.log('[HealthManager] Shown - resuming health checks');
        this.isVisible = true;
        this.startHealthChecks();
    }

    /**
     * Lifecycle: Hide module (pause operations)
     */
    onHide() {
        console.log('[HealthManager] Hidden - pausing health checks');
        this.isVisible = false;
        this.stopHealthChecks();
    }

    /**
     * Lifecycle: Destroy module (complete cleanup)
     */
    onDestroy() {
        console.log('[HealthManager] Destroyed - complete cleanup');
        this.cleanup();
        this.isInitialized = false;
    }

    /**
     * Get module state for lifecycle manager
     */
    getState() {
        return {
            isHealthy: this.isHealthy,
            degradedSources: Array.from(this.degradedSources),
            isInitialized: this.isInitialized,
            isVisible: this.isVisible
        };
    }

    /**
     * Set module state from lifecycle manager
     */
    setState(state) {
        console.log('[HealthManager] Restoring state:', state);
        this.isVisible = state?.isVisible ?? true;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HealthManager;
} else {
    window.HealthManager = HealthManager;
}

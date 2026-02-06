/**
 * Circuit Breaker Pattern Implementation
 * Prevents cascading failures during API outages
 */

class CircuitBreaker {
    constructor(options = {}) {
        this.failureThreshold = options.failureThreshold || 5; // Failures before opening
        this.successThreshold = options.successThreshold || 2; // Successes to close
        this.timeout = options.timeout || 30000; // 30s timeout before half-open
        this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
        this.failures = new Map();
        this.lastFailure = new Map();
        this.successes = new Map();
    }

    /**
     * Get state for a specific endpoint
     */
    getState(endpoint) {
        const failures = this.failures.get(endpoint) || 0;
        const lastFailure = this.lastFailure.get(endpoint) || 0;
        const successes = this.successes.get(endpoint) || 0;

        // Check if circuit should transition from OPEN to HALF_OPEN
        if (this.state === 'OPEN' && Date.now() - lastFailure > this.timeout) {
            this.state = 'HALF_OPEN';
        }

        return {
            state: this.state,
            failures,
            successes,
            lastFailure
        };
    }

    /**
     * Execute a function through the circuit breaker
     */
    async execute(endpoint, fn) {
        const state = this.getState(endpoint);

        if (state.state === 'OPEN') {
            throw new Error(`Circuit breaker is OPEN for ${endpoint}`);
        }

        try {
            const result = await fn();
            this.recordSuccess(endpoint);
            return result;
        } catch (error) {
            this.recordFailure(endpoint);
            throw error;
        }
    }

    /**
     * Record a successful request
     */
    recordSuccess(endpoint) {
        const current = this.successes.get(endpoint) || 0;
        this.successes.set(endpoint, current + 1);
        this.lastFailure.delete(endpoint);

        const state = this.getState(endpoint);

        // If HALF_OPEN, close after successThreshold successes
        if (state.state === 'HALF_OPEN' && state.successes >= this.successThreshold) {
            console.log(`CircuitBreaker: Closing circuit for ${endpoint}`);
            this.state = 'CLOSED';
            this.failures.delete(endpoint);
            this.successes.delete(endpoint);
        }
    }

    /**
     * Record a failed request
     */
    recordFailure(endpoint) {
        const current = this.failures.get(endpoint) || 0;
        this.failures.set(endpoint, current + 1);
        this.lastFailure.set(endpoint, Date.now());

        const state = this.getState(endpoint);

        // If CLOSED and reached failure threshold, open circuit
        if (state.state === 'CLOSED' && state.failures >= this.failureThreshold) {
            console.warn(`CircuitBreaker: Opening circuit for ${endpoint} after ${state.failures} failures`);
            this.state = 'OPEN';
        }

        // If HALF_OPEN, open circuit again on failure
        if (state.state === 'HALF_OPEN') {
            console.warn(`CircuitBreaker: Opening circuit for ${endpoint} (HALF_OPEN failure)`);
            this.state = 'OPEN';
        }
    }

    /**
     * Reset circuit breaker for an endpoint
     */
    reset(endpoint) {
        this.failures.delete(endpoint);
        this.successes.delete(endpoint);
        this.lastFailure.delete(endpoint);
        this.state = 'CLOSED';
    }

    /**
     * Force open the circuit
     */
    forceOpen(endpoint) {
        console.warn(`CircuitBreaker: Forcing OPEN for ${endpoint}`);
        this.state = 'OPEN';
        this.lastFailure.set(endpoint, Date.now());
    }

    /**
     * Force close the circuit
     */
    forceClose(endpoint) {
        console.log(`CircuitBreaker: Forcing CLOSE for ${endpoint}`);
        this.state = 'CLOSED';
        this.failures.delete(endpoint);
        this.successes.delete(endpoint);
    }

    /**
     * Get all circuit states
     */
    getAllStates() {
        const allEndpoints = new Set([
            ...this.failures.keys(),
            ...this.successes.keys()
        ]);

        const states = {};
        for (const endpoint of allEndpoints) {
            states[endpoint] = this.getState(endpoint);
        }
        return states;
    }

    /**
     * Get circuit breaker stats
     */
    getStats() {
        const allEndpoints = new Set([
            ...this.failures.keys(),
            ...this.successes.keys()
        ]);

        let totalFailures = 0;
        let totalSuccesses = 0;
        const endpointStates = {};

        for (const endpoint of allEndpoints) {
            const state = this.getState(endpoint);
            totalFailures += state.failures;
            totalSuccesses += state.successes;
            endpointStates[endpoint] = state;
        }

        return {
            globalState: this.state,
            totalEndpoints: allEndpoints.size,
            totalFailures,
            totalSuccesses,
            successRate: totalSuccesses + totalFailures > 0
                ? (totalSuccesses / (totalSuccesses + totalFailures) * 100).toFixed(1) + '%'
                : 'N/A',
            endpointStates
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CircuitBreaker;
} else {
    window.CircuitBreaker = CircuitBreaker;
}

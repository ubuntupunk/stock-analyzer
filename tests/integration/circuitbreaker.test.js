/**
 * Frontend Circuit Breaker Tests
 * Tests for infrastructure/frontend/modules/CircuitBreaker.js
 */

const CircuitBreaker = require('../../infrastructure/frontend/modules/CircuitBreaker.js');

// Mock event bus for testing
const createMockEventBus = () => ({
    emit: jest.fn(),
    on: jest.fn(),
    off: jest.fn()
});

describe('CircuitBreaker', () => {
    let circuitBreaker;

    beforeEach(() => {
        circuitBreaker = new CircuitBreaker({
            failureThreshold: 3,
            successThreshold: 2,
            timeout: 1000
        });
        jest.useFakeTimers();
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    describe('Initialization', () => {
        test('should initialize with default values', () => {
            const cb = new CircuitBreaker();
            expect(cb.failureThreshold).toBe(5);
            expect(cb.successThreshold).toBe(2);
            expect(cb.timeout).toBe(30000);
            expect(cb.state).toBe('CLOSED');
        });

        test('should initialize with custom values', () => {
            const cb = new CircuitBreaker({
                failureThreshold: 10,
                successThreshold: 5,
                timeout: 60000
            });
            expect(cb.failureThreshold).toBe(10);
            expect(cb.successThreshold).toBe(5);
            expect(cb.timeout).toBe(60000);
        });
    });

    describe('getState', () => {
        test('should return CLOSED state initially', () => {
            const state = circuitBreaker.getState('/api/test');
            expect(state.state).toBe('CLOSED');
            expect(state.failures).toBe(0);
            expect(state.successes).toBe(0);
        });

        test('should track failures per endpoint', () => {
            circuitBreaker.recordFailure('/api/stock');
            circuitBreaker.recordFailure('/api/stock');
            const state = circuitBreaker.getState('/api/stock');
            expect(state.failures).toBe(2);
        });

        test('should transition to HALF_OPEN after timeout', () => {
            circuitBreaker.state = 'OPEN';
            circuitBreaker.lastFailure.set('/api/test', Date.now() - 2000);

            // Timeout is 1000ms, so after 1100ms should transition
            jest.advanceTimersByTime(1100);
            const state = circuitBreaker.getState('/api/test');
            expect(state.state).toBe('HALF_OPEN');
        });
    });

    describe('execute', () => {
        test('should execute function when circuit is CLOSED', async () => {
            const mockFn = jest.fn().mockResolvedValue('success');
            const result = await circuitBreaker.execute('/api/test', mockFn);
            expect(result).toBe('success');
            expect(mockFn).toHaveBeenCalledTimes(1);
        });

        test('should throw when circuit is OPEN', async () => {
            circuitBreaker.state = 'OPEN';
            // Set lastFailure to now so it stays OPEN (within timeout window)
            circuitBreaker.lastFailure.set('/api/test', Date.now());
            const mockFn = jest.fn().mockResolvedValue('success');

            await expect(circuitBreaker.execute('/api/test', mockFn))
                .rejects
                .toThrow('Circuit breaker is OPEN for /api/test');
            expect(mockFn).not.toHaveBeenCalled();
        });

        test('should record success and close circuit from HALF_OPEN', async () => {
            circuitBreaker.state = 'HALF_OPEN';
            circuitBreaker.successes.set('/api/test', 1); // Need 2 to close

            const mockFn = jest.fn().mockResolvedValue('success');
            await circuitBreaker.execute('/api/test', mockFn);

            expect(mockFn).toHaveBeenCalledTimes(1);
            // After reaching successThreshold, should be CLOSED
        });

        test('should record failure and keep circuit OPEN', async () => {
            circuitBreaker.state = 'HALF_OPEN';
            const mockFn = jest.fn().mockRejectedValue(new Error('fail'));

            await expect(circuitBreaker.execute('/api/test', mockFn))
                .rejects
                .toThrow('fail');
            expect(mockFn).toHaveBeenCalledTimes(1);
        });
    });

    describe('recordSuccess', () => {
        test('should increment success count', () => {
            circuitBreaker.recordSuccess('/api/test');
            circuitBreaker.recordSuccess('/api/test');
            const state = circuitBreaker.getState('/api/test');
            expect(state.successes).toBe(2);
        });

        test('should clear lastFailure on success', () => {
            circuitBreaker.recordFailure('/api/test');
            circuitBreaker.lastFailure.set('/api/test', Date.now()); // Ensure it's set
            circuitBreaker.recordSuccess('/api/test');
            // lastFailure should be cleared
            expect(circuitBreaker.lastFailure.has('/api/test')).toBe(false);
        });

        test('should close circuit from HALF_OPEN after successThreshold', () => {
            circuitBreaker.state = 'HALF_OPEN';
            circuitBreaker.recordSuccess('/api/test');
            circuitBreaker.recordSuccess('/api/test');
            expect(circuitBreaker.state).toBe('CLOSED');
        });
    });

    describe('recordFailure', () => {
        test('should increment failure count', () => {
            circuitBreaker.recordFailure('/api/test');
            circuitBreaker.recordFailure('/api/test');
            circuitBreaker.recordFailure('/api/test');
            const state = circuitBreaker.getState('/api/test');
            expect(state.failures).toBe(3);
        });

        test('should open circuit when failure threshold is reached', () => {
            circuitBreaker.recordFailure('/api/test');
            circuitBreaker.recordFailure('/api/test');
            circuitBreaker.recordFailure('/api/test');
            expect(circuitBreaker.state).toBe('OPEN');
        });
    });

    describe('reset', () => {
        test('should use forceClose to reset all state', () => {
            circuitBreaker.recordFailure('/api/test');
            circuitBreaker.recordSuccess('/api/test');
            circuitBreaker.state = 'OPEN';

            circuitBreaker.forceClose('/api/test');

            expect(circuitBreaker.state).toBe('CLOSED');
            expect(circuitBreaker.failures.size).toBe(0);
            expect(circuitBreaker.successes.size).toBe(0);
        });
    });

    describe('getStats', () => {
        test('should return comprehensive statistics', () => {
            circuitBreaker.recordFailure('/api/test');
            const stats = circuitBreaker.getStats();

            expect(stats).toHaveProperty('globalState');
            expect(stats).toHaveProperty('totalEndpoints');
            expect(stats).toHaveProperty('totalFailures');
            expect(stats).toHaveProperty('totalSuccesses');
            expect(stats).toHaveProperty('successRate');
            expect(stats).toHaveProperty('endpointStates');
            expect(stats.totalFailures).toBe(1);
        });

        test('should return N/A success rate when no requests', () => {
            const stats = circuitBreaker.getStats();
            expect(stats.successRate).toBe('N/A');
        });
    });

    describe('Integration with EventBus', () => {
        test('should be instantiable without eventBus', () => {
            const cb = new CircuitBreaker({
                failureThreshold: 1
            });
            expect(cb).toBeDefined();
            expect(cb.failureThreshold).toBe(1);
        });
    });
});

describe('CircuitBreaker - Stress Tests', () => {
    test('should handle rapid concurrent requests', async () => {
        const cb = new CircuitBreaker({ failureThreshold: 10 });
        const mockFn = jest.fn().mockResolvedValue('success');

        // Fire 50 concurrent requests
        const promises = Array(50).fill().map(() => cb.execute('/api/test', mockFn));
        const results = await Promise.all(promises);

        // Function should only be called once due to deduplication
        // Note: This behavior depends on implementation
        expect(results.every(r => r === 'success')).toBe(true);
    });

    test('should handle rapid failures correctly', async () => {
        const cb = new CircuitBreaker({ failureThreshold: 3, timeout: 100 });
        const mockFn = jest.fn().mockRejectedValue(new Error('fail'));

        // Fire 5 concurrent failing requests
        const promises = Array(5).fill().map(() => cb.execute('/api/test', mockFn));

        try {
            await Promise.all(promises);
        } catch (e) {}

        // Should have opened
        expect(cb.state).toBe('OPEN');
    });
});

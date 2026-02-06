/**
 * Unit Tests for DataManager New Features
 * Tests: CircuitBreaker, LRUCache, RequestQueue, APIMetrics, OfflineQueue
 */

const { chromium } = require('playwright');
const { expect } = require('@playwright/test');

describe('DataManager Unit Tests', () => {
    let browser;
    let page;
    const BASE_URL = process.env.TEST_URL || 'http://localhost:8080';

    beforeAll(async () => {
        browser = await chromium.launch({
            headless: process.env.CI === 'true'
        });
    });

    afterAll(async () => {
        await browser.close();
    });

    beforeEach(async () => {
        page = await browser.newPage();
        await page.goto(BASE_URL);
        await page.waitForLoadState('networkidle');
        
        // Clear localStorage before each test
        await page.evaluate(() => {
            localStorage.clear();
        });
    });

    afterEach(async () => {
        await page.close();
    });

    describe('LRUCache', () => {
        test('should store and retrieve data', async () => {
            const result = await page.evaluate(() => {
                const cache = new LRUCache(10);
                cache.set('key1', { value: 'test' });
                return cache.get('key1');
            });

            expect(result.value).toBe('test');
        });

        test('should return null for missing keys', async () => {
            const result = await page.evaluate(() => {
                const cache = new LRUCache(10);
                return cache.get('nonexistent');
            });

            expect(result).toBeNull();
        });

        test('should evict oldest entry when at capacity', async () => {
            const result = await page.evaluate(() => {
                const cache = new LRUCache(3);
                cache.set('key1', { value: '1' });
                cache.set('key2', { value: '2' });
                cache.set('key3', { value: '3' });
                cache.set('key4', { value: '4' }); // Should evict key1
                return {
                    key1: cache.get('key1'),
                    key4: cache.get('key4')
                };
            });

            expect(result.key1).toBeNull();
            expect(result.key4.value).toBe('4');
        });

        test('should check TTL expiration', async () => {
            const result = await page.evaluate(() => {
                const cache = new LRUCache(10);
                cache.set('key1', { value: 'test' }, 100); // 100ms TTL
                
                // Wait for expiration
                return new Promise(resolve => {
                    setTimeout(() => {
                        resolve(cache.has('key1'));
                    }, 150);
                });
            });

            expect(result).toBe(false);
        });

        test('should return stats', async () => {
            const result = await page.evaluate(() => {
                const cache = new LRUCache(5);
                cache.set('key1', { value: '1' });
                cache.set('key2', { value: '2' });
                return cache.getStats();
            });

            expect(result.size).toBe(2);
            expect(result.maxSize).toBe(5);
            expect(result.keys.length).toBe(2);
        });
    });

    describe('CircuitBreaker', () => {
        test('should start in CLOSED state', async () => {
            const result = await page.evaluate(() => {
                const cb = new CircuitBreaker();
                return cb.getState('test-endpoint');
            });

            expect(result.state).toBe('CLOSED');
        });

        test('should record failures correctly', async () => {
            const result = await page.evaluate(() => {
                const cb = new CircuitBreaker({ failureThreshold: 3 });
                
                // Simulate failures
                cb.recordFailure('test-endpoint');
                cb.recordFailure('test-endpoint');
                
                return cb.getState('test-endpoint');
            });

            expect(result.failures).toBe(2);
            expect(result.state).toBe('CLOSED');
        });

        test('should open circuit after threshold', async () => {
            const result = await page.evaluate(() => {
                const cb = new CircuitBreaker({ 
                    failureThreshold: 3,
                    timeout: 1000 
                });
                
                // Record 3 failures to open circuit
                cb.recordFailure('test-endpoint');
                cb.recordFailure('test-endpoint');
                cb.recordFailure('test-endpoint');
                
                return cb.getState('test-endpoint');
            });

            expect(result.failures).toBe(3);
            expect(result.state).toBe('OPEN');
        });

        test('should record successes correctly', async () => {
            const result = await page.evaluate(() => {
                const cb = new CircuitBreaker({ successThreshold: 2 });
                
                cb.recordSuccess('test-endpoint');
                cb.recordSuccess('test-endpoint');
                
                return cb.getState('test-endpoint');
            });

            expect(result.successes).toBe(2);
        });

        test('should get all states', async () => {
            const result = await page.evaluate(() => {
                const cb = new CircuitBreaker();
                cb.recordFailure('endpoint1');
                cb.recordSuccess('endpoint2');
                return cb.getAllStates();
            });

            expect(result.endpoint1).toBeDefined();
            expect(result.endpoint2).toBeDefined();
        });

        test('should get stats', async () => {
            const result = await page.evaluate(() => {
                const cb = new CircuitBreaker();
                cb.recordFailure('endpoint1');
                cb.recordSuccess('endpoint2');
                return cb.getStats();
            });

            expect(result.totalFailures).toBe(1);
            expect(result.totalSuccesses).toBe(1);
        });
    });

    describe('RequestQueue', () => {
        test('should enqueue and dequeue items', async () => {
            const result = await page.evaluate(() => {
                const queue = new RequestQueue();
                
                queue.enqueue(() => Promise.resolve('result1'), 1, 'key1');
                queue.enqueue(() => Promise.resolve('result2'), 2, 'key2');
                
                const dequeued = queue.dequeue();
                return {
                    pending: queue.getStats().pending,
                    processing: queue.getStats().processing
                };
            });

            expect(result.pending).toBe(1);
            expect(result.processing).toBe(1);
        });

        test('should respect priority ordering', async () => {
            const result = await page.evaluate(() => {
                const queue = new RequestQueue();
                
                // Enqueue in reverse priority order
                queue.enqueue(() => {}, 4, 'low');
                queue.enqueue(() => {}, 1, 'critical');
                queue.enqueue(() => {}, 3, 'normal');
                
                const dequeued = queue.dequeue();
                return dequeued.key;
            });

            expect(result).toBe('critical');
        });

        test('should retry failed items', async () => {
            const result = await page.evaluate(() => {
                const queue = new RequestQueue();
                
                const failingFn = () => Promise.reject(new Error('fail'));
                queue.enqueue(failingFn, 1, 'test');
                
                // Simulate retry
                queue.retry({
                    fn: failingFn,
                    priority: 1,
                    key: 'test',
                    attempts: 1
                });
                
                return queue.getStats().pending;
            });

            expect(result).toBe(1);
        });

        test('should complete processing', async () => {
            const result = await page.evaluate(() => {
                const queue = new RequestQueue();
                queue.enqueue(() => {}, 1, 'test');
                queue.complete('test');
                
                return queue.getStats().processing;
            });

            expect(result).toBe(0);
        });
    });

    describe('APIMetrics', () => {
        test('should record request metrics', async () => {
            const result = await page.evaluate(() => {
                const metrics = new APIMetrics();
                metrics.recordRequest('/api/test', true, 100);
                metrics.recordRequest('/api/test', false, 200);
                
                return metrics.getMetrics();
            });

            expect(result.requests.total).toBe(2);
            expect(result.requests.success).toBe(1);
            expect(result.requests.failed).toBe(1);
        });

        test('should calculate cache hit rate', async () => {
            const result = await page.evaluate(() => {
                const metrics = new APIMetrics();
                metrics.recordCache(true);
                metrics.recordCache(true);
                metrics.recordCache(false);
                
                return metrics.getCacheHitRate();
            });

            expect(result).toBe('66.7%');
        });

        test('should record latency percentiles', async () => {
            const result = await page.evaluate(() => {
                const metrics = new APIMetrics();
                
                // Record various latencies
                metrics.recordRequest('/api/test', true, 50);
                metrics.recordRequest('/api/test', true, 100);
                metrics.recordRequest('/api/test', true, 200);
                metrics.recordRequest('/api/test', true, 500);
                metrics.recordRequest('/api/test', true, 1000);
                
                const data = metrics.getMetrics();
                return {
                    avg: data.latency.avg,
                    p50: data.latency.p50,
                    p95: data.latency.p95
                };
            });

            expect(result.avg).toBe(370); // (50+100+200+500+1000)/5
            expect(result.p50).toBe(200);
        });

        test('should record error types', async () => {
            const result = await page.evaluate(() => {
                const metrics = new APIMetrics();
                metrics.recordError('Timeout');
                metrics.recordError('Network Error');
                metrics.recordError('Timeout');
                
                return metrics.getMetrics().errors;
            });

            expect(result['Timeout']).toBe(2);
            expect(result['Network Error']).toBe(1);
        });

        test('should reset metrics', async () => {
            const result = await page.evaluate(() => {
                const metrics = new APIMetrics();
                metrics.recordRequest('/api/test', true, 100);
                metrics.recordRequest('/api/test', false, 200);
                
                metrics.reset();
                
                return metrics.getMetrics().requests.total;
            });

            expect(result).toBe(0);
        });
    });

    describe('OfflineQueue', () => {
        test('should detect online status', async () => {
            const result = await page.evaluate(() => {
                const queue = new OfflineQueue();
                return queue.isOnline;
            });

            // Should match navigator.onLine
            expect(typeof result).toBe('boolean');
        });

        test('should save and load from storage', async () => {
            const result = await page.evaluate(() => {
                const queue = new OfflineQueue();
                queue.enqueue({ type: 'test', fn: () => {} });
                queue.saveToStorage();
                
                // Load new instance to verify persistence
                const queue2 = new OfflineQueue();
                return queue2.queue.length;
            });

            expect(result).toBe(1);
        });

        test('should clear queue', async () => {
            const result = await page.evaluate(() => {
                const queue = new OfflineQueue();
                queue.enqueue({ type: 'test', fn: () => {} });
                queue.clear();
                
                return queue.getStats().pending;
            });

            expect(result).toBe(0);
        });

        test('should get stats', async () => {
            const result = await page.evaluate(() => {
                const queue = new OfflineQueue();
                queue.enqueue({ type: 'test1', fn: () => {} });
                queue.enqueue({ type: 'test2', fn: () => {} });
                
                return queue.getStats();
            });

            expect(result.pending).toBe(2);
            expect(typeof result.isOnline).toBe('boolean');
        });
    });

    describe('PRIORITY Constants', () => {
        test('should have correct priority values', async () => {
            const result = await page.evaluate(() => {
                return {
                    CRITICAL: PRIORITY.CRITICAL,
                    HIGH: PRIORITY.HIGH,
                    NORMAL: PRIORITY.NORMAL,
                    LOW: PRIORITY.LOW
                };
            });

            expect(result.CRITICAL).toBe(1);
            expect(result.HIGH).toBe(2);
            expect(result.NORMAL).toBe(3);
            expect(result.LOW).toBe(4);
        });

        test('PRIORITY_MAP should map data types', async () => {
            const result = await page.evaluate(() => {
                return {
                    price: PRIORITY_MAP['price'],
                    metrics: PRIORITY_MAP['metrics'],
                    financials: PRIORITY_MAP['financials'],
                    news: PRIORITY_MAP['news']
                };
            });

            expect(result.price).toBe(PRIORITY.CRITICAL);
            expect(result.metrics).toBe(PRIORITY.HIGH);
            expect(result.financials).toBe(PRIORITY.HIGH);
            expect(result.news).toBe(PRIORITY.LOW);
        });
    });

    describe('DataManager Integration', () => {
        test('should initialize all components', async () => {
            const result = await page.evaluate(() => {
                const eventBus = {
                    emit: () => {},
                    on: () => {}
                };
                const dm = new DataManager(eventBus);
                
                return {
                    hasCache: !!dm.cache,
                    hasCircuitBreaker: !!dm.circuitBreaker,
                    hasRequestQueue: !!dm.requestQueue,
                    hasMetrics: !!dm.metrics,
                    hasOfflineQueue: !!dm.offlineQueue,
                    cacheType: dm.cache.constructor.name,
                    cbType: dm.circuitBreaker.constructor.name
                };
            });

            expect(result.hasCache).toBe(true);
            expect(result.hasCircuitBreaker).toBe(true);
            expect(result.hasRequestQueue).toBe(true);
            expect(result.hasMetrics).toBe(true);
            expect(result.hasOfflineQueue).toBe(true);
            expect(result.cacheType).toBe('LRUCache');
            expect(result.cbType).toBe('CircuitBreaker');
        });

        test('should get all stats', async () => {
            const result = await page.evaluate(() => {
                const eventBus = {
                    emit: () => {},
                    on: () => {}
                };
                const dm = new DataManager(eventBus);
                
                // Generate some metrics
                dm.cache.set('test1', { value: 'test' });
                dm.metrics.recordRequest('/api/test', true, 100);
                
                return dm.getAllStats();
            });

            expect(result.cache).toBeDefined();
            expect(result.circuitBreaker).toBeDefined();
            expect(result.queue).toBeDefined();
            expect(result.offline).toBeDefined();
            expect(result.metrics).toBeDefined();
        });

        test('should clear cache pattern', async () => {
            const result = await page.evaluate(() => {
                const eventBus = {
                    emit: () => {},
                    on: () => {}
                };
                const dm = new DataManager(eventBus);
                
                dm.cache.set('watchlist:1', { value: '1' });
                dm.cache.set('watchlist:2', { value: '2' });
                dm.cache.set('price:AAPL', { value: '3' });
                
                dm.clearCachePattern('watchlist');
                
                return {
                    watchlist1: dm.cache.has('watchlist:1'),
                    watchlist2: dm.cache.has('watchlist:2'),
                    aapl: dm.cache.has('price:AAPL')
                };
            });

            expect(result.watchlist1).toBe(false);
            expect(result.watchlist2).toBe(false);
            expect(result.aapl).toBe(true);
        });
    });
});

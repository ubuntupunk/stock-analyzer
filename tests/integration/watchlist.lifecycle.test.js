/**
 * Updated Integration Tests for Watchlist Tab with LifecycleManager Support
 * Tests the complete watchlist functionality including lifecycle hooks, state preservation, and tab switching
 */

const { chromium } = require('playwright');
const { expect } = require('@playwright/test');

describe('Watchlist Tab Integration Tests (with LifecycleManager)', () => {
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
    });

    afterEach(async () => {
        await page.close();
    });

    describe('Tab Loading with Lifecycle', () => {
        test('should load watchlist tab when clicked and trigger lifecycle hooks', async () => {
            // Listen for lifecycle events
            const lifecycleLogs = [];
            page.on('console', msg => {
                if (msg.text().includes('[WatchlistManager]')) {
                    lifecycleLogs.push(msg.text());
                }
            });

            // Click watchlist tab (8th tab)
            await page.click('.tab-btn:nth-child(8)');
            
            // Wait for section to be visible
            await page.waitForSelector('#watchlist.content-section.active', { timeout: 5000 });
            
            // Verify section is visible
            const isVisible = await page.isVisible('#watchlist');
            expect(isVisible).toBe(true);

            // Verify lifecycle hook was called (may need to wait a moment)
            await page.waitForTimeout(500);
            const showLogs = lifecycleLogs.filter(log => log.includes('Shown'));
            expect(showLogs.length).toBeGreaterThan(0);
        });

        test('should display watchlist container elements after lifecycle init', async () => {
            await page.click('.tab-btn:nth-child(8)');
            
            // Wait for lifecycle initialization
            await page.waitForFunction(() => {
                return window.app?.modules?.watchlistManager?.isVisible === true;
            }, { timeout: 5000 });
            
            // Check for required elements
            const hasContainer = await page.isVisible('#watchlistContainer');
            const hasGrid = await page.isVisible('#watchlistGrid');
            const hasCount = await page.isVisible('#watchlistCount');
            
            expect(hasContainer).toBe(true);
            expect(hasGrid).toBe(true);
            expect(hasCount).toBe(true);
        });

        test('should not have duplicate renders with lifecycle', async () => {
            const consoleLogs = [];
            page.on('console', msg => {
                if (msg.text().includes('renderWatchlist') || msg.text().includes('[WatchlistManager]')) {
                    consoleLogs.push(msg.text());
                }
            });

            await page.click('.tab-btn:nth-child(8)');
            await page.waitForTimeout(3000);

            // Should only have one render call
            const renderCalls = consoleLogs.filter(log => log.includes('renderWatchlist: Call #'));
            expect(renderCalls.length).toBeLessThanOrEqual(1);
            
            // Should have lifecycle show event
            const showEvents = consoleLogs.filter(log => log.includes('[WatchlistManager] Shown'));
            expect(showEvents.length).toBe(1);
        });
    });

    describe('Watchlist Rendering', () => {
        test('should render watchlist items with correct structure', async () => {
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });

            const items = await page.$$('.watchlist-item');
            expect(items.length).toBeGreaterThan(0);

            // Check first item structure
            const firstItem = items[0];
            const hasSymbol = await firstItem.$('.watchlist-symbol');
            const hasPriceContainer = await firstItem.$('.watchlist-price');
            const hasChangeContainer = await firstItem.$('.watchlist-change');
            const hasActions = await firstItem.$('.watchlist-actions');

            expect(hasSymbol).toBeTruthy();
            expect(hasPriceContainer).toBeTruthy();
            expect(hasChangeContainer).toBeTruthy();
            expect(hasActions).toBeTruthy();
        });

        test('should use unique watchlist-price-* IDs (no collision with StockManager)', async () => {
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });

            const priceIds = await page.$$eval('.watchlist-price', elements => 
                elements.map(el => el.id)
            );

            // All IDs should start with 'watchlist-price-'
            priceIds.forEach(id => {
                expect(id).toMatch(/^watchlist-price-[A-Z]+$/);
            });

            // Check for no duplicate IDs in the entire page
            for (const id of priceIds) {
                const elements = await page.$$(`#${id}`);
                expect(elements.length).toBe(1);
            }
        });
    });

    describe('Lifecycle State Preservation', () => {
        test('should preserve watchlist state when switching tabs', async () => {
            // Go to watchlist
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });
            
            // Get initial items count
            const initialItems = await page.$$eval('.watchlist-item', items => items.length);
            expect(initialItems).toBeGreaterThan(0);
            
            // Switch to different tab (e.g., metrics - 2nd tab)
            await page.click('.tab-btn:nth-child(2)');
            await page.waitForTimeout(500);
            
            // Switch back to watchlist
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });
            
            // Verify items are still there (state preserved)
            const restoredItems = await page.$$eval('.watchlist-item', items => items.length);
            expect(restoredItems).toBe(initialItems);
        });

        test('should trigger hide lifecycle hook when switching away', async () => {
            const lifecycleLogs = [];
            page.on('console', msg => {
                if (msg.text().includes('[WatchlistManager]')) {
                    lifecycleLogs.push(msg.text());
                }
            });

            // Go to watchlist
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForTimeout(1000);
            
            // Switch away
            await page.click('.tab-btn:nth-child(2)');
            await page.waitForTimeout(500);
            
            // Verify hide event was logged
            const hideEvents = lifecycleLogs.filter(log => log.includes('[WatchlistManager] Hidden'));
            expect(hideEvents.length).toBeGreaterThan(0);
        });
    });

    describe('Price Updates with Lifecycle', () => {
        test('should start price updates when watchlist shown', async () => {
            const consoleLogs = [];
            page.on('console', msg => {
                if (msg.text().includes('price updates') || msg.text().includes('[WatchlistManager]')) {
                    consoleLogs.push(msg.text());
                }
            });

            await page.click('.tab-btn:nth-child(8)');
            await page.waitForTimeout(2000);

            // Should indicate price updates started
            const priceUpdateLogs = consoleLogs.filter(log => 
                log.includes('price updates') || log.includes('resuming')
            );
            expect(priceUpdateLogs.length).toBeGreaterThan(0);
        });

        test('should stop price updates when watchlist hidden', async () => {
            const consoleLogs = [];
            page.on('console', msg => {
                if (msg.text().includes('price updates') || msg.text().includes('[WatchlistManager]')) {
                    consoleLogs.push(msg.text());
                }
            });

            // Go to watchlist
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForTimeout(1000);
            
            // Switch away
            await page.click('.tab-btn:nth-child(2)');
            await page.waitForTimeout(500);
            
            // Verify price updates stopped
            const stopLogs = consoleLogs.filter(log => 
                log.includes('pausing') || log.includes('Hidden')
            );
            expect(stopLogs.length).toBeGreaterThan(0);
        });
    });
});

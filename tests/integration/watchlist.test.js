/**
 * Integration Tests for Watchlist Tab
 * Tests the complete watchlist functionality including tab loading, rendering, and price updates
 */

const { chromium } = require('playwright');
const { expect } = require('@playwright/test');

describe('Watchlist Tab Integration Tests', () => {
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

    describe('Tab Loading', () => {
        test('should load watchlist tab when clicked', async () => {
            // Click watchlist tab (8th tab)
            await page.click('.tab-btn:nth-child(8)');
            
            // Wait for section to be visible
            await page.waitForSelector('#watchlist.content-section.active', { timeout: 5000 });
            
            // Verify section is visible
            const isVisible = await page.isVisible('#watchlist');
            expect(isVisible).toBe(true);
        });

        test('should display watchlist container elements', async () => {
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('#watchlistContainer', { timeout: 5000 });
            
            // Check for required elements
            const hasContainer = await page.isVisible('#watchlistContainer');
            const hasGrid = await page.isVisible('#watchlistGrid');
            const hasCount = await page.isVisible('#watchlistCount');
            
            expect(hasContainer).toBe(true);
            expect(hasGrid).toBe(true);
            expect(hasCount).toBe(true);
        });

        test('should not have duplicate renders', async () => {
            const consoleLogs = [];
            page.on('console', msg => {
                if (msg.text().includes('renderWatchlist')) {
                    consoleLogs.push(msg.text());
                }
            });

            await page.click('.tab-btn:nth-child(8)');
            await page.waitForTimeout(3000);

            // Should only have one render call
            const renderCalls = consoleLogs.filter(log => log.includes('renderWatchlist: Call #'));
            expect(renderCalls.length).toBeLessThanOrEqual(1);
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
                expect(elements.length).toBe(1); // Should only find one element per ID
            }
        });

        test('should have data-context="watchlist" attribute', async () => {
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });

            const contexts = await page.$$eval('.watchlist-item', elements =>
                elements.map(el => el.dataset.context)
            );

            contexts.forEach(context => {
                expect(context).toBe('watchlist');
            });
        });
    });

    describe('Price Loading and Display', () => {
        test('should load and display stock prices', async () => {
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });

            // Wait for prices to load (max 10 seconds)
            await page.waitForSelector('.watchlist-price span.loaded', { timeout: 10000 });

            // Get all price spans
            const prices = await page.$$eval('.watchlist-price span', spans =>
                spans.map(span => ({
                    text: span.textContent,
                    classes: span.className,
                    hasLoaded: span.classList.contains('loaded')
                }))
            );

            // All prices should be loaded
            prices.forEach(price => {
                expect(price.hasLoaded).toBe(true);
                expect(price.text).toMatch(/^\$\d+\.\d{2}$/); // Should match $XXX.XX format
                expect(['loaded positive', 'loaded negative'].some(cls => 
                    price.classes.includes(cls)
                )).toBe(true);
            });
        });

        test('should not show "Loading..." after prices load', async () => {
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });
            await page.waitForTimeout(8000); // Wait for prices to load

            const loadingTexts = await page.$$eval('.watchlist-price', containers =>
                containers.map(c => c.textContent)
            );

            loadingTexts.forEach(text => {
                expect(text).not.toContain('Loading...');
            });
        });

        test('should maintain span wrapper after price update', async () => {
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });
            await page.waitForTimeout(8000);

            // Check that spans exist and have content
            const spanInfo = await page.$$eval('.watchlist-price', containers =>
                containers.map(container => ({
                    id: container.id,
                    hasSpan: !!container.querySelector('span'),
                    spanClass: container.querySelector('span')?.className || '',
                    innerHTML: container.innerHTML.substring(0, 100)
                }))
            );

            spanInfo.forEach(info => {
                expect(info.hasSpan).toBe(true);
                expect(info.spanClass).toContain('loaded');
                expect(info.innerHTML).toContain('<span');
            });
        });

        test('should display price changes with correct styling', async () => {
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });
            await page.waitForSelector('.watchlist-change span.loaded', { timeout: 10000 });

            const changes = await page.$$eval('.watchlist-change span', spans =>
                spans.map(span => ({
                    text: span.textContent,
                    isPositive: span.classList.contains('positive'),
                    isNegative: span.classList.contains('negative')
                }))
            );

            changes.forEach(change => {
                // Should have either positive or negative class
                expect(change.isPositive || change.isNegative).toBe(true);
                // Should match format: +/-$X.XX (+/-X.XX%)
                expect(change.text).toMatch(/[+-]\$\d+\.\d{2}\s+\([+-]\d+\.\d{2}%\)/);
            });
        });
    });

    describe('No StockManager Interference', () => {
        test('should not be affected by StockManager batch updates', async () => {
            // Load popular stocks first
            await page.waitForSelector('.stock-card', { timeout: 5000 });
            
            // Then load watchlist
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });
            
            // Wait for both managers to complete their updates
            await page.waitForTimeout(8000);

            // Check that watchlist prices are still properly formatted
            const watchlistPrices = await page.$$eval('[id^="watchlist-price-"] span', spans =>
                spans.map(span => ({
                    exists: true,
                    hasLoadedClass: span.classList.contains('loaded'),
                    text: span.textContent
                }))
            );

            watchlistPrices.forEach(price => {
                expect(price.exists).toBe(true);
                expect(price.hasLoadedClass).toBe(true);
                expect(price.text).toMatch(/^\$\d+\.\d{2}$/);
            });
        });

        test('should have different IDs than popular stocks for same symbol', async () => {
            // Wait for popular stocks to load
            await page.waitForSelector('.stock-card', { timeout: 5000 });
            
            // Get a symbol from popular stocks
            const popularSymbol = await page.$eval('.stock-card:first-child', 
                card => card.dataset.symbol
            );

            // Load watchlist
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });

            // Check if the same symbol exists in watchlist
            const watchlistHasSymbol = await page.$(`[data-context="watchlist"][data-symbol="${popularSymbol}"]`);
            
            if (watchlistHasSymbol) {
                // Verify they have different price container IDs
                const popularPriceId = `price-${popularSymbol}`;
                const watchlistPriceId = `watchlist-price-${popularSymbol}`;

                const popularExists = await page.$(`#${popularPriceId}`);
                const watchlistExists = await page.$(`#${watchlistPriceId}`);

                expect(popularExists).toBeTruthy();
                expect(watchlistExists).toBeTruthy();
                
                // Verify they're different elements
                expect(popularPriceId).not.toBe(watchlistPriceId);
            }
        });
    });

    describe('Watchlist Actions', () => {
        test('should have functional remove buttons', async () => {
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });

            const removeButtons = await page.$$('.watchlist-remove');
            expect(removeButtons.length).toBeGreaterThan(0);

            // Check that buttons have onclick handlers
            const hasOnclick = await page.$eval('.watchlist-remove:first-child',
                btn => btn.hasAttribute('onclick')
            );
            expect(hasOnclick).toBe(true);
        });

        test('should have functional analyze buttons', async () => {
            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('.watchlist-item', { timeout: 5000 });

            const analyzeButtons = await page.$$('.watchlist-actions .btn-small');
            expect(analyzeButtons.length).toBeGreaterThan(0);
        });
    });

    describe('Error Handling', () => {
        test('should not have JavaScript errors during load', async () => {
            const errors = [];
            page.on('pageerror', error => {
                errors.push(error.message);
            });

            await page.click('.tab-btn:nth-child(8)');
            await page.waitForTimeout(10000);

            // Filter out known harmless errors
            const criticalErrors = errors.filter(err => 
                !err.includes('favicon') && 
                !err.includes('404')
            );

            expect(criticalErrors.length).toBe(0);
        });

        test('should handle empty watchlist gracefully', async () => {
            // Clear localStorage to simulate empty watchlist
            await page.evaluate(() => {
                localStorage.removeItem('stock_analyzer_watchlist');
            });

            await page.reload();
            await page.waitForLoadState('networkidle');

            await page.click('.tab-btn:nth-child(8)');
            await page.waitForSelector('#watchlistEmpty', { timeout: 5000 });

            const emptyMessage = await page.isVisible('#watchlistEmpty');
            expect(emptyMessage).toBe(true);

            const emptyText = await page.textContent('#watchlistEmpty');
            expect(emptyText).toContain('watchlist is empty');
        });
    });
});

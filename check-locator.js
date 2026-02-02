const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Capture console
    page.on('console', msg => {
        const text = msg.text();
        if (text.includes('>>> updateWatchlistPriceDisplay: VERIFY') || text.includes('>>> loadWatchlistPrices: COMPLETE')) {
            console.log(`[${msg.type()}] ${text}`);
        }
    });

    console.log('Navigating...');
    await page.goto('http://localhost:8091', { timeout: 30000 });
    await page.waitForTimeout(5000);

    // Click watchlist tab
    console.log('Clicking watchlist tab...');
    await page.click('.tab-btn:nth-child(8)');

    // Wait for price update
    await page.waitForTimeout(15000);

    // Use locator API which reads from live DOM
    console.log('\n=== Using Locator API ===');
    const watchlistItems = page.locator('.watchlist-item');
    const count = await watchlistItems.count();
    console.log(`Found ${count} watchlist items`);

    for (let i = 0; i < count; i++) {
        const item = watchlistItems.nth(i);
        const symbol = await item.getAttribute('data-symbol');
        const priceSpan = item.locator('.watchlist-price span');
        const priceText = await priceSpan.innerText();
        console.log(`${symbol}: "${priceText}"`);
    }

    // Also try getting HTML directly
    console.log('\n=== Getting innerHTML directly ===');
    const html = await page.evaluate(() => {
        const items = document.querySelectorAll('.watchlist-item');
        return Array.from(items).map(item => {
            const symbol = item.dataset.symbol;
            const priceContainer = item.querySelector('.watchlist-price');
            return `${symbol}: ${priceContainer?.innerHTML}`;
        }).join('\n');
    });
    console.log(html);

    await browser.close();
})();

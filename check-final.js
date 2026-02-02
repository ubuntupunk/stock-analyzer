const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Track all requests
    const failedRequests = [];
    page.on('response', response => {
        if (response.status() >= 400) {
            failedRequests.push({
                url: response.url(),
                status: response.status()
            });
        }
    });

    // Capture console
    page.on('console', msg => {
        const text = msg.text();
        if (text.includes('updateWatchlistPriceDisplay') || text.includes('>>>')) {
            console.log(`[${msg.type()}] ${text}`);
        }
    });

    console.log('Navigating to http://localhost:8091...');
    await page.goto('http://localhost:8091', { timeout: 30000 });
    await page.waitForTimeout(5000);

    // Click watchlist tab (8th tab)
    console.log('\nClicking watchlist tab...');
    await page.click('.tab-btn:nth-child(8)');
    await page.waitForTimeout(15000);

    // Wait a bit more for prices to fully update
    console.log('Waiting additional 2 seconds for DOM to settle...');
    await page.waitForTimeout(2000);

    // Check DOM
    const result = await page.evaluate(() => {
        const items = document.querySelectorAll('.watchlist-item');
        return Array.from(items).map(item => {
            const symbol = item.dataset.symbol;
            const priceSpan = item.querySelector('.watchlist-price span');
            const changeSpan = item.querySelector('.watchlist-change span');
            return {
                symbol,
                priceClass: priceSpan?.className,
                priceText: priceSpan?.textContent,
                changeText: changeSpan?.textContent
            };
        });
    });

    console.log('\n=== WATCHLIST PRICES ===');
    result.forEach(r => {
        console.log(`${r.symbol}: price="${r.priceText}" (${r.priceClass}), change="${r.changeText}"`);
    });

    // Show failed requests
    if (failedRequests.length > 0) {
        console.log('\n=== FAILED REQUESTS ===');
        failedRequests.forEach(r => {
            console.log(`${r.status}: ${r.url}`);
        });
    }

    await browser.close();
})();

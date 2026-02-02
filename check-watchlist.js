const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Capture all console messages
    page.on('console', msg => {
        const text = msg.text();
        // Only show relevant watchlist messages
        if (text.includes('WatchlistManager') || text.includes('price') || text.includes('loadWatchlist')) {
            console.log(`[${msg.type()}] ${text}`);
        }
    });

    // Capture page errors
    page.on('pageerror', error => {
        console.log(`[PAGE ERROR] ${error.message}`);
    });

    console.log('Navigating to http://localhost:8080...');
    await page.goto('http://localhost:8080');
    await page.waitForTimeout(3000);

    // Click watchlist tab (8th tab)
    console.log('\n=== Clicking watchlist tab ===');
    await page.click('.tab-btn:nth-child(8)');

    // Wait for prices to load
    console.log('=== Waiting 15 seconds for prices... ===\n');
    await page.waitForTimeout(15000);

    // Get the actual DOM state
    const watchlistContent = await page.evaluate(() => {
        const items = document.querySelectorAll('.watchlist-item');
        return Array.from(items).map(item => {
            const symbol = item.dataset.symbol;
            const priceContainer = item.querySelector('.watchlist-price');
            const priceSpan = priceContainer?.querySelector('span');
            return {
                symbol,
                hasId: !!document.getElementById(`price-${symbol}`),
                spanHTML: priceSpan?.outerHTML,
                spanClass: priceSpan?.className,
                spanText: priceSpan?.textContent
            };
        });
    });

    console.log('\n=== Watchlist Items State ===');
    watchlistContent.forEach(item => {
        console.log(`Symbol: ${item.symbol}`);
        console.log(`  Span HTML: ${item.spanHTML}`);
        console.log('');
    });

    // Wait 2 more seconds and check again
    console.log('\n=== Waiting 2 more seconds and checking again ===');
    await page.waitForTimeout(2000);

    const watchlistContentAfter = await page.evaluate(() => {
        const items = document.querySelectorAll('.watchlist-item');
        return Array.from(items).map(item => {
            const symbol = item.dataset.symbol;
            const priceContainer = item.querySelector('.watchlist-price');
            const priceSpan = priceContainer?.querySelector('span');
            return {
                symbol,
                spanHTML: priceSpan?.outerHTML,
                spanClass: priceSpan?.className,
                spanText: priceSpan?.textContent
            };
        });
    });

    console.log('\n=== Watchlist Items State AFTER WAIT ===');
    watchlistContentAfter.forEach(item => {
        console.log(`Symbol: ${item.symbol}`);
        console.log(`  Span HTML: ${item.spanHTML}`);
        console.log('');
    });

    await browser.close();
})();

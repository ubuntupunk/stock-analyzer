const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Capture ALL console messages - NO FILTERING
    page.on('console', msg => {
        const text = msg.text();
        // Show ALL messages
        process.stdout.write(`[${msg.type()}] ${text}\n`);
    });

    // Capture page errors
    page.on('pageerror', error => {
        process.stdout.write(`[PAGE ERROR] ${error.message}\n`);
        process.stdout.write(`[PAGE ERROR STACK] ${error.stack}\n`);
    });

    console.log('Navigating to http://localhost:8080...');
    await page.goto('http://localhost:8080');
    await page.waitForTimeout(3000);

    // Click watchlist tab
    console.log('Clicking watchlist tab...');
    await page.click('.tab-btn:nth-child(8)');

    // Wait for prices to load
    console.log('Waiting 15 seconds for prices...\n');
    await page.waitForTimeout(15000);

    // Get the actual DOM state
    console.log('\n=== WATCHLIST DOM STATE ===');
    const watchlistContent = await page.evaluate(() => {
        const items = document.querySelectorAll('.watchlist-item');
        return Array.from(items).map(item => {
            const symbol = item.dataset.symbol;
            const priceContainer = item.querySelector('.watchlist-price');
            const priceSpan = priceContainer?.querySelector('span');
            return {
                symbol,
                spanHTML: priceSpan?.outerHTML || 'NO SPAN'
            };
        });
    });

    watchlistContent.forEach(item => {
        console.log(`${item.symbol}: ${item.spanHTML}`);
    });

    await browser.close();
})();

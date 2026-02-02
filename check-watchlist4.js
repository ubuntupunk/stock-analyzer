const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Capture ALL console messages
    page.on('console', msg => {
        console.log(`[${msg.type()}] ${msg.text()}`);
    });

    // Capture page errors
    page.on('pageerror', error => {
        console.log(`[PAGEERROR] ${error.message}`);
    });

    // Capture failed requests
    page.on('response', response => {
        if (response.status() >= 400) {
            console.log(`[${response.status()}] ${response.url()}`);
        }
    });

    console.log('Navigating to http://localhost:8090...');
    await page.goto('http://localhost:8090');
    await page.waitForTimeout(5000);

    // Check if tabs loaded
    const tabCount = await page.locator('.tab-btn').count();
    console.log(`Found ${tabCount} tab buttons`);

    if (tabCount > 0) {
        // Click watchlist tab
        console.log('Clicking watchlist tab...');
        await page.click('.tab-btn:nth-child(8)');
        await page.waitForTimeout(5000);

        // Check DOM
        const result = await page.evaluate(() => {
            const items = document.querySelectorAll('.watchlist-item');
            return Array.from(items).map(item => {
                const symbol = item.dataset.symbol;
                const span = item.querySelector('.watchlist-price span');
                return {
                    symbol,
                    class: span?.className,
                    text: span?.textContent
                };
            });
        });

        console.log('\n=== RESULT ===');
        result.forEach(r => {
            console.log(`${r.symbol}: class="${r.class}", text="${r.text}"`);
        });
    } else {
        console.log('Tabs not loaded - page may have errors');
    }

    await browser.close();
})();

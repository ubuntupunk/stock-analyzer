const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Capture ALL console messages with full text
    page.on('console', msg => {
        console.log(`[${msg.type()}] ${msg.text()}`);
    });

    // Capture page errors
    page.on('pageerror', error => {
        console.log(`[PAGEERROR] ${error.message}`);
        console.log(`[STACK] ${error.stack}`);
    });

    // Capture request failures
    page.on('requestfailed', request => {
        console.log(`[REQUESTFAILED] ${request.url()} - ${request.failure().errorText}`);
    });

    console.log('Navigating...');
    try {
        await page.goto('http://localhost:8080', { timeout: 30000 });
        console.log('Page loaded');
    } catch (e) {
        console.log('Page load error:', e.message);
    }

    await page.waitForTimeout(3000);

    // Click watchlist tab
    console.log('\nClicking watchlist tab...');
    await page.click('.tab-btn:nth-child(8)');

    // Wait
    console.log('Waiting 20 seconds...\n');
    await page.waitForTimeout(20000);

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

    await browser.close();
})();

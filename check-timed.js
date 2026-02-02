const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    console.log('Navigating to http://localhost:8091...');
    await page.goto('http://localhost:8091', { timeout: 30000 });
    await page.waitForTimeout(5000);

    // Click watchlist tab
    console.log('Clicking watchlist tab...');
    await page.click('.tab-btn:nth-child(8)');
    await page.waitForTimeout(15000);

    // First check - immediately
    console.log('\n=== CHECK 1: Immediate ===');
    let result = await page.evaluate(() => {
        const items = document.querySelectorAll('.watchlist-item');
        return Array.from(items).map(item => {
            const symbol = item.dataset.symbol;
            const priceSpan = item.querySelector('.watchlist-price span');
            return { symbol, priceText: priceSpan?.textContent };
        });
    });
    result.forEach(r => console.log(`${r.symbol}: "${r.priceText}"`));

    // Second check - after 2 seconds
    console.log('\n=== CHECK 2: After 2 seconds ===');
    await page.waitForTimeout(2000);
    result = await page.evaluate(() => {
        const items = document.querySelectorAll('.watchlist-item');
        return Array.from(items).map(item => {
            const symbol = item.dataset.symbol;
            const priceSpan = item.querySelector('.watchlist-price span');
            return { symbol, priceText: priceSpan?.textContent };
        });
    });
    result.forEach(r => console.log(`${r.symbol}: "${r.priceText}"`));

    await browser.close();
})();

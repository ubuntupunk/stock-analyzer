const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Track all network requests
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
        if (msg.type() === 'error') {
            console.log(`[CONSOLE ERROR] ${msg.text()}`);
        }
    });

    console.log('Navigating...');
    await page.goto('http://localhost:8080', { timeout: 30000 });
    await page.waitForTimeout(5000);

    console.log('\n=== FAILED REQUESTS ===');
    failedRequests.forEach(r => {
        console.log(`${r.status}: ${r.url}`);
    });

    // Check what's loaded
    const hasHeader = await page.$('#header-container');
    const hasTabs = await page.$('#tabs-container');
    const headerContent = await page.$eval('#header-container', el => el.innerHTML.substring(0, 100));
    const tabsContent = await page.$eval('#tabs-container', el => el.innerHTML.substring(0, 100));

    console.log('\n=== DOM STATE ===');
    console.log('Header container has content:', !!hasHeader);
    console.log('Header HTML:', headerContent.substring(0, 200));
    console.log('Tabs container has content:', !!hasTabs);
    console.log('Tabs HTML:', tabsContent.substring(0, 200));

    await browser.close();
})();

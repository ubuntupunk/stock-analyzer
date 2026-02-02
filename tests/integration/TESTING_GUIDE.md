# Watchlist Integration Testing Guide

## Quick Start

1. **Install dependencies:**
   ```bash
   cd tests/integration
   npm install
   npx playwright install chromium
   ```

2. **Start the application:**
   ```bash
   cd ../../infrastructure/frontend
   python3 -m http.server 8080 &
   ```

3. **Run the tests:**
   ```bash
   cd ../../tests/integration
   npm test
   ```

## What The Tests Verify

### ✅ Fixed Issues

1. **Tab Loading Race Condition**
   - Test: `should load watchlist tab when clicked`
   - Verifies: Section loads within 5 seconds without errors
   - Expected: Tab becomes visible and active

2. **No Duplicate Renders**
   - Test: `should not have duplicate renders`
   - Verifies: Only one render call occurs
   - Expected: `renderWatchlist: Call #1` appears once

3. **Unique IDs (No Collision)**
   - Test: `should use unique watchlist-price-* IDs`
   - Verifies: All price containers use `watchlist-price-` prefix
   - Expected: No duplicate IDs in the entire DOM

4. **Price Display Works**
   - Test: `should load and display stock prices`
   - Verifies: Prices display within 10 seconds with proper format
   - Expected: All prices show as `$XXX.XX` with `loaded` class

5. **Span Wrapper Maintained**
   - Test: `should maintain span wrapper after price update`
   - Verifies: StockManager doesn't strip watchlist spans
   - Expected: `<span class="loaded positive/negative">` remains intact

6. **No StockManager Interference**
   - Test: `should not be affected by StockManager batch updates`
   - Verifies: Watchlist and popular stocks update independently
   - Expected: Different IDs, no cross-contamination

## Test Output Examples

### Successful Run
```
 PASS  watchlist.test.js
  Watchlist Tab Integration Tests
    Tab Loading
      ✓ should load watchlist tab when clicked (2045ms)
      ✓ should display watchlist container elements (1823ms)
      ✓ should not have duplicate renders (3012ms)
    Watchlist Rendering
      ✓ should render watchlist items with correct structure (1654ms)
      ✓ should use unique watchlist-price-* IDs (1876ms)
      ✓ should have data-context="watchlist" attribute (1432ms)
    Price Loading and Display
      ✓ should load and display stock prices (8234ms)
      ✓ should not show "Loading..." after prices load (8123ms)
      ✓ should maintain span wrapper after price update (8456ms)
    No StockManager Interference
      ✓ should not be affected by StockManager batch updates (9876ms)
      ✓ should have different IDs than popular stocks for same symbol (5432ms)

Test Suites: 1 passed, 1 total
Tests:       11 passed, 11 total
Time:        56.234s
```

### Failed Test Example (Before Fix)
```
 FAIL  watchlist.test.js
  Watchlist Tab Integration Tests
    Price Loading and Display
      ✗ should maintain span wrapper after price update (8456ms)

    Expected: true
    Received: false

      103 |     spanInfo.forEach(info => {
      104 |         expect(info.hasSpan).toBe(true);
    > 105 |         expect(info.spanClass).toContain('loaded');
          |                                ^
      106 |     });

    HTML found: "$223.01" (plain text, no span)
    Expected: "<span class=\"loaded positive\">$223.01</span>"
```

## Debugging Failed Tests

### Enable Visual Browser
```bash
CI=false npm test
```

### Run Single Test
```bash
npm test -- -t "should load and display stock prices"
```

### Enable Playwright Inspector
```bash
PWDEBUG=1 npm test
```

### Increase Timeout
Edit `jest.config.js`:
```javascript
testTimeout: 120000  // 2 minutes
```

## Common Issues

### Issue: Tests timeout
**Cause**: Application not running or slow API responses
**Solution**: 
```bash
# Check if app is running
curl http://localhost:8080

# Increase timeout in jest.config.js
testTimeout: 90000
```

### Issue: "Element not found"
**Cause**: Selectors changed or timing issue
**Solution**: Add explicit waits
```javascript
await page.waitForSelector('.watchlist-item', { 
    timeout: 10000,
    state: 'visible' 
});
```

### Issue: Flaky tests
**Cause**: Network delays or async timing
**Solution**: Use `waitForLoadState` and `waitForSelector`
```javascript
await page.waitForLoadState('networkidle');
await page.waitForSelector('.loaded', { timeout: 15000 });
```

## Adding New Tests

### Template
```javascript
test('should do something specific', async () => {
    // 1. Navigate and wait for stability
    await page.click('.tab-btn:nth-child(8)');
    await page.waitForSelector('#watchlist', { timeout: 5000 });
    
    // 2. Perform action
    await page.click('.some-button');
    
    // 3. Wait for result
    await page.waitForSelector('.expected-result', { timeout: 5000 });
    
    // 4. Assert
    const result = await page.textContent('.expected-result');
    expect(result).toBe('Expected Value');
});
```

### Best Practices

1. **Always wait for elements**: Use `waitForSelector` instead of `$` when elements appear async
2. **Use descriptive test names**: "should X when Y" format
3. **Test one thing per test**: Keep tests focused and atomic
4. **Clean up state**: Each test should be independent
5. **Use timeouts wisely**: Long enough for slow environments, not too long for fast feedback

## Coverage

Generate coverage report:
```bash
npm run test:ci
open coverage/lcov-report/index.html
```

Target coverage:
- **Line Coverage**: > 80%
- **Branch Coverage**: > 75%
- **Function Coverage**: > 80%

## CI/CD Integration

### GitHub Actions
```yaml
- name: Run Integration Tests
  run: |
    cd tests/integration
    npm ci
    npx playwright install --with-deps chromium
    npm run test:ci
```

### GitLab CI
```yaml
integration-tests:
  script:
    - cd tests/integration
    - npm ci
    - npx playwright install --with-deps chromium
    - npm run test:ci
  artifacts:
    reports:
      junit: tests/integration/junit.xml
    paths:
      - tests/integration/coverage/
```

## Performance Benchmarks

Expected test execution times:
- **Tab Loading tests**: ~2-3 seconds each
- **Rendering tests**: ~2-4 seconds each
- **Price loading tests**: ~8-10 seconds each (includes API wait)
- **Full suite**: ~50-60 seconds

## Next Steps

After tests pass:
1. ✅ Run full test suite: `npm test`
2. ✅ Check coverage: `npm run test:ci`
3. ✅ Review test output for warnings
4. ✅ Commit test results
5. ✅ Set up CI/CD pipeline
6. ✅ Monitor test stability over time

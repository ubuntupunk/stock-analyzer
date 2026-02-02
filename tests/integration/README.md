# Integration Tests

This directory contains integration tests for the Stock Analyzer application using Playwright and Jest.

## Setup

```bash
cd tests/integration
npm install
```

## Running Tests

### Run all tests
```bash
npm test
```

### Run watchlist tests only
```bash
npm run test:watchlist
```

### Run tests in watch mode (for development)
```bash
npm run test:watch
```

### Run tests in CI mode with coverage
```bash
npm run test:ci
```

## Test Structure

### `watchlist.test.js`
Comprehensive integration tests for the watchlist tab including:

- **Tab Loading**: Verifies the tab loads correctly without race conditions
- **Watchlist Rendering**: Checks DOM structure and unique IDs
- **Price Loading and Display**: Validates price formatting and updates
- **No StockManager Interference**: Ensures no ID collision issues
- **Watchlist Actions**: Tests interactive elements
- **Error Handling**: Validates graceful error handling

## Prerequisites

Before running tests, ensure:

1. The application is running on `http://localhost:8080` (or set `TEST_URL` env var)
2. Playwright browsers are installed: `npx playwright install`

## Environment Variables

- `TEST_URL`: Base URL for the application (default: `http://localhost:8080`)
- `CI`: Set to `true` for headless mode in CI environments

## Writing New Tests

Follow this structure:

```javascript
describe('Feature Name', () => {
    test('should do something specific', async () => {
        // Arrange
        await page.goto(BASE_URL);
        
        // Act
        await page.click('.some-button');
        
        // Assert
        expect(await page.isVisible('.result')).toBe(true);
    });
});
```

## Custom Matchers

The test suite includes custom matchers:

- `toBeValidPrice(received)`: Checks if string matches `$XXX.XX` format
- `toBeValidPercentage(received)`: Checks if string matches `+/-XX.XX%` format

Usage:
```javascript
expect('$123.45').toBeValidPrice();
expect('+2.35%').toBeValidPercentage();
```

## Debugging Tests

### Run with headed browser
```bash
CI=false npm test
```

### Run specific test
```bash
npm test -- -t "should load watchlist tab"
```

### Debug mode
```bash
PWDEBUG=1 npm test
```

## CI/CD Integration

The tests are designed to run in CI environments. Example GitHub Actions workflow:

```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - name: Install dependencies
        run: |
          cd tests/integration
          npm install
      - name: Install Playwright browsers
        run: npx playwright install --with-deps
      - name: Start application
        run: |
          cd infrastructure/frontend
          python3 -m http.server 8080 &
          sleep 5
      - name: Run tests
        run: cd tests/integration && npm run test:ci
```

## Coverage

Coverage reports are generated in `coverage/` directory when running:
```bash
npm run test:ci
```

## Known Issues

- Tests may be flaky if the backend API is slow
- Some tests require localStorage to be accessible
- Network-dependent tests may fail in offline mode

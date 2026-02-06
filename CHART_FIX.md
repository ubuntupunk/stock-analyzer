# Chart Not Loading Fix - Timing Issue

## Problem

The price chart on the metrics page was not loading due to a **timing/race condition**:

1. User selects a stock → data is preloaded for all tabs (including metrics)
2. `data:loaded` event fires → tries to create chart
3. **BUT** the metrics tab HTML isn't loaded yet (user is on popular-stocks tab)
4. Canvas element `#priceChart` doesn't exist
5. Chart creation fails silently

## Root Cause

The chart creation logic in `app.js` assumed the canvas element would always exist when metrics data loaded. However, with the preloading optimization (from commit 820f1a1), data loads **before** the user navigates to the metrics tab.

**Timeline:**
```
1. User clicks stock → StockManager.selectStock()
2. Preload all data (non-blocking) → metrics data loads
3. data:loaded event fires → tries to create chart
4. Canvas doesn't exist yet (still on popular-stocks tab)
5. User clicks Metrics tab → section loads, but chart was never created
```

## Solution

### 1. Guard Chart Creation (app.js)
Check if canvas exists before attempting to create chart:

```javascript
eventBus.on('data:loaded', ({ symbol, type, data }) => {
    const hasHistoricalData = (type === 'price' && data?.historicalData) ||
                              (type === 'metrics' && data?.hasHistoricalData);
    if (hasHistoricalData) {
        // Only create chart if canvas element exists
        const canvas = document.getElementById('priceChart');
        if (!canvas) {
            console.log('Canvas not ready yet, chart will be created when tab loads');
            return;  // Exit early, don't try to create chart
        }
        // ... create chart
    }
});
```

### 2. Create Chart on Tab Load (TabManager.js)
When metrics tab loads, check if data is cached and chart needs to be created:

```javascript
async loadMetricsData() {
    const currentSymbol = window.stockManager?.getCurrentSymbol();
    if (currentSymbol) {
        const data = await this.dataManager.loadStockData(currentSymbol, 'metrics');
        
        // If data was cached and chart wasn't created, create it now
        if (data && data.hasHistoricalData) {
            const canvas = document.getElementById('priceChart');
            if (canvas && window.chartManager) {
                const existingChart = window.chartManager.charts?.get('priceChart');
                if (!existingChart) {
                    console.log('Creating chart from cached data');
                    window.chartManager.createPriceChart('priceChart', data, currentSymbol);
                }
            }
        }
    }
}
```

## How It Works Now

### Scenario 1: Data loads before tab switch
1. User selects stock → data preloads
2. `data:loaded` fires → canvas doesn't exist → skip chart creation
3. User switches to metrics tab → `loadMetricsData()` runs
4. Data is in cache → returns immediately
5. Check if chart exists → it doesn't
6. Create chart from cached data ✅

### Scenario 2: Tab switch before data loads
1. User switches to metrics tab → section loads
2. `loadMetricsData()` fetches data
3. `data:loaded` fires → canvas exists → create chart ✅

### Scenario 3: Already on metrics tab
1. Data loads while on metrics tab
2. `data:loaded` fires → canvas exists → create chart ✅

## Files Modified

1. **infrastructure/frontend/app.js**
   - Added canvas existence check before chart creation
   - Prevents errors when canvas doesn't exist

2. **infrastructure/frontend/modules/TabManager.js**
   - Added chart creation from cached data
   - Ensures chart is created when tab loads

## Testing

To verify the fix:

1. **Test preload scenario:**
   - Select a stock from popular stocks
   - Wait 1 second (let data preload)
   - Click Metrics tab
   - ✅ Chart should appear

2. **Test direct navigation:**
   - Select a stock
   - Immediately click Metrics tab
   - ✅ Chart should appear after data loads

3. **Test tab switching:**
   - Load metrics for one stock
   - Switch to another tab
   - Switch back to metrics
   - ✅ Chart should still be there

## Related Commits

- **820f1a1**: Introduced preloading optimization (caused the timing issue)
- **f7fe40b**: Enhanced tab management
- **Current**: Fixed chart loading timing issue

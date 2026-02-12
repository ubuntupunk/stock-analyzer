# Frontend Module Migration to LifecycleManager Hooks

## Overview

This document tracks the migration of all frontend modules to use the new LifecycleManager hooks system.

## Lifecycle Hooks

Each module should implement:
- `onInit()` - One-time initialization
- `onShow()` - Resume operations when tab visible
- `onHide()` - Pause operations when tab hidden
- `onDestroy()` - Complete cleanup
- Optional: `getState()` / `setState()` for state preservation

## Migration Status

### Priority 1 - High Resource Usage
- [x] **ChartManager** - ✅ Migrated - Destroys charts on hide, saves states, lifecycle hooks implemented
- [x] **StockManager** - ✅ Migrated - Pauses data preloading on hide, aborts ongoing requests, lifecycle hooks implemented
- [x] **MetricsManager** - ✅ Migrated - Pauses calculations on hide, marks for refresh on show, lifecycle hooks implemented
- [x] **FinancialsManager** - ✅ Migrated - Clears expensive caches on hide, manages statement cache, lifecycle hooks implemented

### Priority 2 - Data Heavy
- [x] **WatchlistManager** - ✅ Migrated - Stops price updates on hide, saves/restores scroll position, lifecycle hooks implemented
- [x] **NewsManager** - ✅ Migrated - Stops news refresh on hide, auto-refreshes every 5 min when visible, lifecycle hooks implemented
- [x] **EstimatesManager** - ✅ Migrated - Pauses calculations on hide, refreshes if data stale on show, lifecycle hooks implemented
- [x] **FactorsManager** - ✅ Migrated - Clears screen results on hide to free memory, re-renders on show, lifecycle hooks implemented

### Priority 3 - Supporting
- [x] **SearchManager** - ✅ Migrated - Clears search timeout on hide, hides results, lifecycle hooks implemented
- [x] **StockAnalyserManager** - ✅ Migrated - Saves analysis state, refreshes data on show, lifecycle hooks implemented
- [x] **UserManager** - ✅ Migrated - Basic lifecycle hooks implemented, user state preserved
- [x] **UIManager** - ✅ Migrated - Basic lifecycle hooks implemented, error states managed

### Priority 4 - Infrastructure
- [x] **DataManager** - ✅ Migrated - Stops cache pruning on hide, manages cache lifecycle, lifecycle hooks implemented
- [x] **TabManager** - ✅ Already integrated
- [x] **HealthManager** - ✅ Migrated - Pauses health checks on hide, lifecycle hooks implemented

## Implementation Template

```javascript
// Add to module class

onInit() {
    console.log(`${this.constructor.name}: Initialized`);
    this.isInitialized = true;
}

onShow() {
    console.log(`${this.constructor.name}: Shown`);
    // Resume operations
    this.resumeOperations();
}

onHide() {
    console.log(`${this.constructor.name}: Hidden`);
    // Pause operations
    this.pauseOperations();
    // Clear expensive resources
    this.clearCache?.();
}

onDestroy() {
    console.log(`${this.constructor.name}: Destroyed`);
    this.cleanup();
}

// Optional state management
getState() {
    return {
        // Module-specific state
    };
}

setState(state) {
    // Restore module-specific state
}
```

## Testing Checklist

For each module migrated:
- [ ] Tab switch to module works
- [ ] Tab switch away pauses operations
- [ ] Tab switch back restores state
- [ ] Rapid tab switching doesn't crash
- [ ] Memory usage reduced when hidden
- [ ] No console errors

## Benefits

- Reduced CPU/memory usage when tab not visible
- Prevented memory leaks
- Faster tab switches
- Better debugging via lifecycle events

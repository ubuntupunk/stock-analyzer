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
- [ ] **StockManager** - Pause data fetching
- [ ] **MetricsManager** - Stop calculations
- [ ] **FinancialsManager** - Clear caches

### Priority 2 - Data Heavy
- [ ] **WatchlistManager** - Save scroll position
- [ ] **NewsManager** - Stop polling
- [ ] **EstimatesManager** - Pause calculations
- [ ] **FactorsManager** - Cleanup analysis

### Priority 3 - Supporting
- [ ] **SearchManager** - Clear timeouts
- [ ] **StockAnalyserManager** - Save state
- [ ] **UserManager** - Cleanup listeners
- [ ] **UIManager** - Manage UI state

### Priority 4 - Infrastructure
- [ ] **DataManager** - Cache lifecycle
- [ ] **TabManager** - ✅ Already integrated
- [ ] **HealthManager** - Pause checks

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

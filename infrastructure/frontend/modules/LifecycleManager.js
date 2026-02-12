/**
 * Lifecycle Manager
 * 
 * Manages module lifecycle across the application:
 * - onInit: Initialize module (once on first load)
 * - onShow: Resume operations when tab becomes visible
 * - onHide: Pause operations when tab hidden
 * - onDestroy: Cleanup resources when module destroyed
 * 
 * Integrates with TabManager to orchestrate lifecycle events
 * and provides memory leak detection and state management.
 */

class LifecycleManager {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.modules = new Map(); // moduleName -> { instance, state, hooks }
        this.activeModule = null;
        this.visibilityState = 'visible';
        this.memorySnapshots = new Map();
        this.lifecycleTimeouts = new Map();
        
        this.setupVisibilityTracking();
        this.setupEventListeners();
    }

    /**
     * Register a module with lifecycle hooks
     * @param {string} moduleName - Unique module identifier
     * @param {Object} moduleInstance - Module instance
     * @param {Object} hooks - Lifecycle hooks { onInit, onShow, onHide, onDestroy }
     */
    registerModule(moduleName, moduleInstance, hooks = {}) {
        if (this.modules.has(moduleName)) {
            console.warn(`[LifecycleManager] Module ${moduleName} already registered`);
            return;
        }

        const moduleInfo = {
            name: moduleName,
            instance: moduleInstance,
            hooks: {
                onInit: hooks.onInit || this.defaultHook('onInit', moduleName),
                onShow: hooks.onShow || this.defaultHook('onShow', moduleName),
                onHide: hooks.onHide || this.defaultHook('onHide', moduleName),
                onDestroy: hooks.onDestroy || this.defaultHook('onDestroy', moduleName),
            },
            state: 'uninitialized', // uninitialized | initialized | visible | hidden | destroyed
            initCalled: false,
            showCount: 0,
            hideCount: 0,
            memoryUsage: 0,
            subscriptions: [],
            intervals: [],
            timeouts: [],
            charts: [],
            stateData: {}
        };

        this.modules.set(moduleName, moduleInfo);
        
        // Track subscriptions if eventBus has tracking
        if (moduleInstance._eventSubscriptions) {
            moduleInfo.subscriptions = moduleInstance._eventSubscriptions;
        }

        console.log(`[LifecycleManager] Registered module: ${moduleName}`);
        
        this.eventBus.emit('lifecycle:moduleRegistered', {
            moduleName,
            timestamp: Date.now()
        });
    }

    /**
     * Unregister a module
     * @param {string} moduleName - Module to unregister
     */
    unregisterModule(moduleName) {
        const moduleInfo = this.modules.get(moduleName);
        if (!moduleInfo) {
            console.warn(`[LifecycleManager] Module ${moduleName} not found`);
            return;
        }

        // Ensure proper cleanup
        if (moduleInfo.state !== 'destroyed') {
            this.destroyModule(moduleName);
        }

        this.modules.delete(moduleName);
        
        console.log(`[LifecycleManager] Unregistered module: ${moduleName}`);
        
        this.eventBus.emit('lifecycle:moduleUnregistered', {
            moduleName,
            timestamp: Date.now()
        });
    }

    /**
     * Initialize a module (called once on first use)
     * @param {string} moduleName - Module to initialize
     */
    async initModule(moduleName) {
        const moduleInfo = this.modules.get(moduleName);
        if (!moduleInfo) {
            console.error(`[LifecycleManager] Cannot init unknown module: ${moduleName}`);
            return;
        }

        if (moduleInfo.initCalled) {
            console.log(`[LifecycleManager] Module ${moduleName} already initialized`);
            return;
        }

        console.log(`[LifecycleManager] Initializing module: ${moduleName}`);
        
        try {
            await this.executeHook(moduleName, 'onInit');
            moduleInfo.initCalled = true;
            moduleInfo.state = 'initialized';
            
            this.eventBus.emit('lifecycle:moduleInitialized', {
                moduleName,
                timestamp: Date.now()
            });
        } catch (error) {
            console.error(`[LifecycleManager] Error initializing ${moduleName}:`, error);
            this.eventBus.emit('lifecycle:moduleInitError', {
                moduleName,
                error,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Show a module (resume operations)
     * @param {string} moduleName - Module to show
     */
    async showModule(moduleName) {
        const moduleInfo = this.modules.get(moduleName);
        if (!moduleInfo) {
            console.error(`[LifecycleManager] Cannot show unknown module: ${moduleName}`);
            return;
        }

        // Initialize if needed
        if (!moduleInfo.initCalled) {
            await this.initModule(moduleName);
        }

        console.log(`[LifecycleManager] Showing module: ${moduleName}`);
        
        // Update active module tracking
        if (this.activeModule && this.activeModule !== moduleName) {
            await this.hideModule(this.activeModule);
        }
        this.activeModule = moduleName;

        try {
            // Take memory snapshot before showing
            this.takeMemorySnapshot(moduleName, 'beforeShow');
            
            await this.executeHook(moduleName, 'onShow');
            moduleInfo.state = 'visible';
            moduleInfo.showCount++;
            
            // Resume any paused operations
            this.resumeModuleOperations(moduleName);
            
            this.eventBus.emit('lifecycle:moduleShown', {
                moduleName,
                showCount: moduleInfo.showCount,
                timestamp: Date.now()
            });
            
            // Take memory snapshot after showing
            setTimeout(() => {
                this.takeMemorySnapshot(moduleName, 'afterShow');
            }, 100);
            
        } catch (error) {
            console.error(`[LifecycleManager] Error showing ${moduleName}:`, error);
            this.eventBus.emit('lifecycle:moduleShowError', {
                moduleName,
                error,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Hide a module (pause operations)
     * @param {string} moduleName - Module to hide
     */
    async hideModule(moduleName) {
        const moduleInfo = this.modules.get(moduleName);
        if (!moduleInfo) {
            console.error(`[LifecycleManager] Cannot hide unknown module: ${moduleName}`);
            return;
        }

        if (moduleInfo.state === 'hidden' || moduleInfo.state === 'destroyed') {
            return;
        }

        console.log(`[LifecycleManager] Hiding module: ${moduleName}`);
        
        try {
            // Take memory snapshot before hiding
            this.takeMemorySnapshot(moduleName, 'beforeHide');
            
            // Pause operations before calling onHide
            this.pauseModuleOperations(moduleName);
            
            await this.executeHook(moduleName, 'onHide');
            moduleInfo.state = 'hidden';
            moduleInfo.hideCount++;
            
            // Save module state
            this.saveModuleState(moduleName);
            
            this.eventBus.emit('lifecycle:moduleHidden', {
                moduleName,
                hideCount: moduleInfo.hideCount,
                timestamp: Date.now()
            });
            
            // Check for memory leaks
            setTimeout(() => {
                this.takeMemorySnapshot(moduleName, 'afterHide');
                this.detectMemoryLeak(moduleName);
            }, 100);
            
        } catch (error) {
            console.error(`[LifecycleManager] Error hiding ${moduleName}:`, error);
            this.eventBus.emit('lifecycle:moduleHideError', {
                moduleName,
                error,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Destroy a module (cleanup all resources)
     * @param {string} moduleName - Module to destroy
     */
    async destroyModule(moduleName) {
        const moduleInfo = this.modules.get(moduleName);
        if (!moduleInfo) {
            return;
        }

        if (moduleInfo.state === 'destroyed') {
            return;
        }

        console.log(`[LifecycleManager] Destroying module: ${moduleName}`);
        
        try {
            // Ensure module is hidden first
            if (moduleInfo.state === 'visible') {
                await this.hideModule(moduleName);
            }
            
            // Clear all tracked resources
            this.clearModuleResources(moduleName);
            
            await this.executeHook(moduleName, 'onDestroy');
            moduleInfo.state = 'destroyed';
            
            this.eventBus.emit('lifecycle:moduleDestroyed', {
                moduleName,
                timestamp: Date.now()
            });
            
        } catch (error) {
            console.error(`[LifecycleManager] Error destroying ${moduleName}:`, error);
            this.eventBus.emit('lifecycle:moduleDestroyError', {
                moduleName,
                error,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Execute a lifecycle hook
     * @param {string} moduleName - Module name
     * @param {string} hookName - Hook to execute
     */
    async executeHook(moduleName, hookName) {
        const moduleInfo = this.modules.get(moduleName);
        if (!moduleInfo) return;

        const hook = moduleInfo.hooks[hookName];
        if (typeof hook === 'function') {
            await hook.call(moduleInfo.instance);
        }
    }

    /**
     * Default no-op hook
     */
    defaultHook(hookName, moduleName) {
        return () => {
            console.log(`[LifecycleManager] ${moduleName}.${hookName}() called (default)`);
        };
    }

    /**
     * Pause module operations (intervals, animations, etc.)
     */
    pauseModuleOperations(moduleName) {
        const moduleInfo = this.modules.get(moduleName);
        if (!moduleInfo) return;

        // Pause intervals
        moduleInfo.intervals.forEach(interval => {
            clearInterval(interval);
        });

        // Pause timeouts
        moduleInfo.timeouts.forEach(timeout => {
            clearTimeout(timeout);
        });

        // Pause charts
        moduleInfo.charts.forEach(chart => {
            if (chart && typeof chart.pause === 'function') {
                chart.pause();
            }
        });

        console.log(`[LifecycleManager] Paused operations for ${moduleName}`);
    }

    /**
     * Resume module operations
     */
    resumeModuleOperations(moduleName) {
        const moduleInfo = this.modules.get(moduleName);
        if (!moduleInfo) return;

        // Charts are typically recreated on show, so no need to resume
        console.log(`[LifecycleManager] Resumed operations for ${moduleName}`);
    }

    /**
     * Clear all tracked resources for a module
     */
    clearModuleResources(moduleName) {
        const moduleInfo = this.modules.get(moduleName);
        if (!moduleInfo) return;

        // Clear intervals
        moduleInfo.intervals.forEach(interval => {
            clearInterval(interval);
        });
        moduleInfo.intervals = [];

        // Clear timeouts
        moduleInfo.timeouts.forEach(timeout => {
            clearTimeout(timeout);
        });
        moduleInfo.timeouts = [];

        // Destroy charts
        moduleInfo.charts.forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        moduleInfo.charts = [];

        // Unsubscribe from events
        moduleInfo.subscriptions.forEach(unsubscribe => {
            if (typeof unsubscribe === 'function') {
                unsubscribe();
            }
        });
        moduleInfo.subscriptions = [];

        console.log(`[LifecycleManager] Cleared resources for ${moduleName}`);
    }

    /**
     * Save module state
     */
    saveModuleState(moduleName) {
        const moduleInfo = this.modules.get(moduleName);
        if (!moduleInfo || !moduleInfo.instance) return;

        // Try to get state from module
        if (typeof moduleInfo.instance.getState === 'function') {
            moduleInfo.stateData = moduleInfo.instance.getState();
            console.log(`[LifecycleManager] Saved state for ${moduleName}`);
        }
    }

    /**
     * Restore module state
     */
    restoreModuleState(moduleName) {
        const moduleInfo = this.modules.get(moduleName);
        if (!moduleInfo || !moduleInfo.instance) return;

        if (moduleInfo.stateData && typeof moduleInfo.instance.setState === 'function') {
            moduleInfo.instance.setState(moduleInfo.stateData);
            console.log(`[LifecycleManager] Restored state for ${moduleName}`);
        }
    }

    /**
     * Take memory snapshot
     */
    takeMemorySnapshot(moduleName, phase) {
        if (!performance.memory) return;

        const key = `${moduleName}_${phase}`;
        this.memorySnapshots.set(key, {
            usedJSHeapSize: performance.memory.usedJSHeapSize,
            totalJSHeapSize: performance.memory.totalJSHeapSize,
            jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
            timestamp: Date.now()
        });
    }

    /**
     * Detect memory leaks
     */
    detectMemoryLeak(moduleName) {
        const beforeKey = `${moduleName}_beforeHide`;
        const afterKey = `${moduleName}_afterHide`;
        
        const before = this.memorySnapshots.get(beforeKey);
        const after = this.memorySnapshots.get(afterKey);
        
        if (!before || !after) return;

        const increase = after.usedJSHeapSize - before.usedJSHeapSize;
        const increaseMB = increase / (1024 * 1024);
        
        // Flag if memory increased by more than 10MB
        if (increaseMB > 10) {
            console.warn(`[LifecycleManager] Potential memory leak detected in ${moduleName}: +${increaseMB.toFixed(2)}MB`);
            
            this.eventBus.emit('lifecycle:memoryLeakDetected', {
                moduleName,
                increaseBytes: increase,
                increaseMB: increaseMB,
                timestamp: Date.now()
            });
        }

        // Store memory usage in module info
        const moduleInfo = this.modules.get(moduleName);
        if (moduleInfo) {
            moduleInfo.memoryUsage = after.usedJSHeapSize;
        }
    }

    /**
     * Setup page visibility tracking
     */
    setupVisibilityTracking() {
        document.addEventListener('visibilitychange', () => {
            const isVisible = document.visibilityState === 'visible';
            this.visibilityState = document.visibilityState;
            
            console.log(`[LifecycleManager] Page visibility changed: ${this.visibilityState}`);
            
            if (isVisible) {
                this.eventBus.emit('lifecycle:pageVisible', { timestamp: Date.now() });
            } else {
                this.eventBus.emit('lifecycle:pageHidden', { timestamp: Date.now() });
            }
        });
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for tab switches
        this.eventBus.on('tab:switch', ({ tabName }) => {
            this.handleTabSwitch(tabName);
        });

        // Listen for page unload
        window.addEventListener('beforeunload', () => {
            this.cleanupAll();
        });
    }

    /**
     * Handle tab switch
     */
    async handleTabSwitch(tabName) {
        // Map tab names to module names
        const tabToModule = {
            'popular-stocks': 'stockManager',
            'metrics': 'metricsManager',
            'financials': 'financialsManager',
            'factors': 'factorsManager',
            'analyst-estimates': 'estimatesManager',
            'news': 'newsManager',
            'stock-analyser': 'stockAnalyserManager',
            'watchlist': 'watchlistManager',
            'model-portfolio': 'portfolioManager'
        };

        const moduleName = tabToModule[tabName];
        if (!moduleName) return;

        // Show new module
        if (this.modules.has(moduleName)) {
            await this.showModule(moduleName);
        }
    }

    /**
     * Get module status
     */
    getModuleStatus(moduleName) {
        const moduleInfo = this.modules.get(moduleName);
        if (!moduleInfo) return null;

        return {
            name: moduleInfo.name,
            state: moduleInfo.state,
            initCalled: moduleInfo.initCalled,
            showCount: moduleInfo.showCount,
            hideCount: moduleInfo.hideCount,
            memoryUsage: moduleInfo.memoryUsage,
            resourceCounts: {
                subscriptions: moduleInfo.subscriptions.length,
                intervals: moduleInfo.intervals.length,
                timeouts: moduleInfo.timeouts.length,
                charts: moduleInfo.charts.length
            }
        };
    }

    /**
     * Get all module statuses
     */
    getAllModuleStatuses() {
        const statuses = {};
        for (const [name] of this.modules) {
            statuses[name] = this.getModuleStatus(name);
        }
        return statuses;
    }

    /**
     * Cleanup all modules
     */
    async cleanupAll() {
        console.log('[LifecycleManager] Cleaning up all modules...');
        
        for (const [moduleName, moduleInfo] of this.modules) {
            if (moduleInfo.state !== 'destroyed') {
                await this.destroyModule(moduleName);
            }
        }
        
        this.modules.clear();
        this.memorySnapshots.clear();
        
        console.log('[LifecycleManager] Cleanup complete');
    }

    /**
     * Cleanup this manager
     */
    cleanup() {
        this.cleanupAll();
        this.eventBus = null;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LifecycleManager;
} else {
    window.LifecycleManager = LifecycleManager;
}

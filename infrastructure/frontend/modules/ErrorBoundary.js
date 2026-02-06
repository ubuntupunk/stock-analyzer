/**
 * Error Boundary Component
 * Catches and gracefully handles errors in child components
 */

class ErrorBoundary {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.errorHandlers = new Map();
        this.fallbackUIs = new Map();
        this.isRecovering = false;

        // Set up global error handlers
        this.setupGlobalErrorHandlers();
    }

    /**
     * Set up global error handlers for uncaught exceptions
     */
    setupGlobalErrorHandlers() {
        // Catch unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError('Unhandled Promise Rejection', event.reason);
            event.preventDefault(); // Prevent default browser handling
        });

        // Catch JavaScript errors
        window.addEventListener('error', (event) => {
            // Ignore script loading errors from external sources
            if (event.target.tagName === 'SCRIPT' && event.target.src) {
                return;
            }
            this.handleError('JavaScript Error', event.error);
        });
    }

    /**
     * Wrap an async function with error handling
     * @param {Function} fn - Function to wrap
     * @param {string} context - Context name for error reporting
     * @param {Function} fallback - Optional fallback function
     * @returns {Promise} Wrapped function result
     */
    async wrap(fn, context, fallback = null) {
        try {
            return await fn();
        } catch (error) {
            this.handleError(context, error);
            if (fallback) {
                return fallback(error);
            }
            throw error;
        }
    }

    /**
     * Wrap a component's render method
     * @param {string} componentName - Name of the component
     * @param {Function} renderFn - Component's render function
     * @param {HTMLElement} container - Container element
     * @param {object} props - Component props
     * @returns {*} Render result or error UI
     */
    wrapComponent(componentName, renderFn, container, props = {}) {
        try {
            return renderFn(container, props);
        } catch (error) {
            this.handleError(`Component: ${componentName}`, error);
            this.showErrorUI(container, componentName, error);
            return null;
        }
    }

    /**
     * Handle an error
     * @param {string} context - Error context
     * @param {Error|object} error - Error object or reason
     */
    handleError(context, error) {
        const errorInfo = {
            message: error?.message || String(error),
            stack: error?.stack || null,
            context,
            timestamp: Date.now(),
            userAgent: navigator.userAgent,
            url: window.location.href
        };

        console.error(`[ErrorBoundary] ${context}:`, error);
        console.error('[ErrorBoundary] Error details:', errorInfo);

        // Emit error event for monitoring
        if (this.eventBus) {
            this.eventBus.emit('error:caught', errorInfo);
        }

        // Notify registered error handlers
        this.notifyHandlers(errorInfo);

        // Attempt recovery if not already recovering
        if (!this.isRecovering) {
            this.attemptRecovery();
        }
    }

    /**
     * Register an error handler
     * @param {string} name - Handler name
     * @param {Function} handler - Handler function
     */
    registerHandler(name, handler) {
        this.errorHandlers.set(name, handler);
    }

    /**
     * Unregister an error handler
     * @param {string} name - Handler name
     */
    unregisterHandler(name) {
        this.errorHandlers.delete(name);
    }

    /**
     * Notify all registered error handlers
     * @param {object} errorInfo - Error information
     */
    notifyHandlers(errorInfo) {
        for (const [name, handler] of this.errorHandlers) {
            try {
                handler(errorInfo);
            } catch (e) {
                console.error(`[ErrorBoundary] Error in handler '${name}':`, e);
            }
        }
    }

    /**
     * Attempt to recover from error
     */
    attemptRecovery() {
        this.isRecovering = true;

        // Emit recovery event
        if (this.eventBus) {
            this.eventBus.emit('app:recovering', { timestamp: Date.now() });
        }

        // Attempt to recover after a short delay
        setTimeout(() => {
            this.isRecovering = false;
            if (this.eventBus) {
                this.eventBus.emit('app:recovered', { timestamp: Date.now() });
            }
            console.log('[ErrorBoundary] Recovery period ended');
        }, 5000); // 5 second recovery cooldown
    }

    /**
     * Show error UI in a container
     * @param {HTMLElement} container - Container element
     * @param {string} componentName - Component name
     * @param {Error} error - Error object
     */
    showErrorUI(container, componentName, error) {
        if (!container) return;

        container.innerHTML = `
            <div class="error-boundary" style="
                padding: 20px;
                background: #fff5f5;
                border: 1px solid #ffcccc;
                border-radius: 8px;
                color: #cc0000;
            ">
                <h3 style="margin: 0 0 10px 0; font-size: 16px;">
                    <i class="fas fa-exclamation-triangle" style="margin-right: 8px;"></i>
                    Error in ${componentName}
                </h3>
                <p style="margin: 0 0 10px 0; font-size: 14px; color: #666;">
                    ${error?.message || 'An unknown error occurred'}
                </p>
                <button onclick="
                    this.parentElement.parentElement.innerHTML = '<p style=\\'color: #666;\\'>Reloading...</p>';
                    window.location.reload();
                " style="
                    padding: 8px 16px;
                    background: #cc0000;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                ">
                    Reload Page
                </button>
            </div>
        `;
    }

    /**
     * Set fallback UI for a specific context
     * @param {string} context - Context name
     * @param {Function|HTMLElement} fallback - Fallback UI
     */
    setFallback(context, fallback) {
        this.fallbackUIs.set(context, fallback);
    }

    /**
     * Get fallback UI for a context
     * @param {string} context - Context name
     * @returns {Function|HTMLElement|null}
     */
    getFallback(context) {
        return this.fallbackUIs.get(context) || null;
    }

    /**
     * Check if we're in recovery mode
     * @returns {boolean}
     */
    isInRecoveryMode() {
        return this.isRecovering;
    }

    /**
     * Clear all error handlers
     */
    clearHandlers() {
        this.errorHandlers.clear();
    }

    /**
     * Clean up resources
     */
    cleanup() {
        this.clearHandlers();
        this.fallbackUIs.clear();
        this.isRecovering = false;
        console.log('ErrorBoundary: Cleanup complete');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ErrorBoundary;
} else {
    window.ErrorBoundary = ErrorBoundary;
}

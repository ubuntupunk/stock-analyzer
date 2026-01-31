// Simple Event Bus for module communication
// Provides publish-subscribe pattern for decoupled communication

class EventBus {
    constructor() {
        this.events = new Map();
    }

    /**
     * Subscribe to an event
     * @param {string} event - Event name
     * @param {function} callback - Callback function
     * @param {object} context - Optional context to bind callback
     */
    on(event, callback, context = null) {
        if (!this.events.has(event)) {
            this.events.set(event, []);
        }
        
        const listener = { callback, context };
        this.events.get(event).push(listener);
        
        // Return unsubscribe function
        return () => this.off(event, callback);
    }

    /**
     * Subscribe to an event (once)
     * @param {string} event - Event name
     * @param {function} callback - Callback function
     * @param {object} context - Optional context to bind callback
     */
    once(event, callback, context = null) {
        const onceCallback = (data) => {
            callback.call(context, data);
            this.off(event, onceCallback);
        };
        
        return this.on(event, onceCallback, context);
    }

    /**
     * Unsubscribe from an event
     * @param {string} event - Event name
     * @param {function} callback - Callback function to remove
     */
    off(event, callback) {
        if (!this.events.has(event)) {
            return;
        }
        
        const listeners = this.events.get(event);
        const index = listeners.findIndex(listener => listener.callback === callback);
        
        if (index > -1) {
            listeners.splice(index, 1);
        }
        
        if (listeners.length === 0) {
            this.events.delete(event);
        }
    }

    /**
     * Emit/publish an event
     * @param {string} event - Event name
     * @param {*} data - Data to pass to subscribers
     */
    emit(event, data) {
        if (!this.events.has(event)) {
            return;
        }
        
        const listeners = this.events.get(event);
        
        // Create a copy to avoid issues if listeners are modified during iteration
        const listenersCopy = [...listeners];
        
        listenersCopy.forEach(listener => {
            try {
                if (listener.context) {
                    listener.callback.call(listener.context, data);
                } else {
                    listener.callback(data);
                }
            } catch (error) {
                console.error(`Error in event listener for '${event}':`, error);
            }
        });
    }

    /**
     * Remove all listeners for an event or all events
     * @param {string} event - Optional event name (if not provided, clears all)
     */
    clear(event = null) {
        if (event) {
            this.events.delete(event);
        } else {
            this.events.clear();
        }
    }

    /**
     * Get the number of listeners for an event
     * @param {string} event - Event name
     * @returns {number} Number of listeners
     */
    listenerCount(event) {
        return this.events.has(event) ? this.events.get(event).length : 0;
    }

    /**
     * Get all event names
     * @returns {Array} Array of event names
     */
    eventNames() {
        return Array.from(this.events.keys());
    }

    /**
     * Check if there are listeners for an event
     * @param {string} event - Event name
     * @returns {boolean} Whether there are listeners
     */
    hasListeners(event) {
        return this.events.has(event) && this.events.get(event).length > 0;
    }
}

// Create global instance
const eventBus = new EventBus();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EventBus, eventBus };
} else {
    window.EventBus = EventBus;
    window.eventBus = eventBus;
}

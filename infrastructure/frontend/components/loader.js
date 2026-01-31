// Component Loader Utility
// Handles dynamic loading of HTML components

class ComponentLoader {
    constructor() {
        this.cache = new Map();
        this.basePath = 'components/';
    }

    async loadComponent(componentName, containerId) {
        // Check cache first
        if (this.cache.has(componentName)) {
            this.renderComponent(this.cache.get(componentName), containerId);
            return;
        }

        try {
            const response = await fetch(`${this.basePath}${componentName}.html`);
            if (!response.ok) {
                throw new Error(`Failed to load ${componentName}: ${response.status}`);
            }
            
            const html = await response.text();
            this.cache.set(componentName, html);
            this.renderComponent(html, containerId);
        } catch (error) {
            console.error(`Error loading component ${componentName}:`, error);
            // Fallback: show error in container
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = `<div class="component-error">Failed to load ${componentName}</div>`;
            }
        }
    }

    renderComponent(html, containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = html;
        }
    }

    async loadSection(sectionName, containerId = 'dynamic-content-container') {
        try {
            const response = await fetch(`sections/${sectionName}.html`);
            if (!response.ok) {
                throw new Error(`Failed to load section ${sectionName}: ${response.status}`);
            }
            
            const html = await response.text();
            this.renderComponent(html, containerId);
        } catch (error) {
            console.error(`Error loading section ${sectionName}:`, error);
            this.renderComponent(`<div class="component-error">Failed to load ${sectionName}</div>`, containerId);
        }
    }

    async loadAll(components) {
        const promises = components.map(({ name, container }) => 
            this.loadComponent(name, container)
        );
        await Promise.all(promises);
    }

    // Clear cache (useful for development)
    clearCache() {
        this.cache.clear();
    }
}

// Create singleton instance
const componentLoader = new ComponentLoader();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ComponentLoader;
} else {
    window.ComponentLoader = ComponentLoader;
    window.componentLoader = componentLoader;
}

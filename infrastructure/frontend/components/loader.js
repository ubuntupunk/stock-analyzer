// Component Loader Utility
// Handles dynamic loading of HTML components

class ComponentLoader {
    constructor() {
        this.cache = new Map();
        this.basePath = 'components/';
        this.loadedSections = new Set(); // Track which sections are loaded
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
        // Check if section is already loaded - if so, don't reload
        if (this.loadedSections.has(sectionName)) {
            console.log('ComponentLoader: Section already loaded, skipping:', sectionName);
            return;
        }

        try {
            const response = await fetch(`sections/${sectionName}.html`);
            if (!response.ok) {
                throw new Error(`Failed to load section ${sectionName}: ${response.status}`);
            }
            
            const html = await response.text();
            
            // Parse and append without destroying existing content
            const container = document.getElementById(containerId);
            if (container) {
                // Create a temporary container to parse the HTML
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;
                
                // Get the section element
                const section = tempDiv.firstElementChild;
                if (section) {
                    // Append to container without clearing
                    container.appendChild(section);
                    this.loadedSections.add(sectionName);
                    console.log('ComponentLoader: Section loaded:', sectionName);
                }
            }
        } catch (error) {
            console.error(`Error loading section ${sectionName}:`, error);
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML += `<div class="component-error">Failed to load ${sectionName}</div>`;
            }
        }
    }

    async loadAll(components) {
        const promises = components.map(({ name, container }) => 
            this.loadComponent(name, container)
        );
        await Promise.all(promises);
    }

    // Check if a section is loaded
    isSectionLoaded(sectionName) {
        return this.loadedSections.has(sectionName);
    }

    // Clear cache (useful for development)
    clearCache() {
        this.cache.clear();
        this.loadedSections.clear();
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

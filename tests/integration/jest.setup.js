// Jest setup for integration tests

// Extend timeout for integration tests
jest.setTimeout(60000);

// Global test utilities
global.sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Custom matchers
expect.extend({
  toBeValidPrice(received) {
    const priceRegex = /^\$\d+\.\d{2}$/;
    const pass = priceRegex.test(received);
    
    return {
      pass,
      message: () => 
        pass
          ? `expected ${received} not to be a valid price format`
          : `expected ${received} to match price format $XXX.XX`
    };
  },
  
  toBeValidPercentage(received) {
    const percentRegex = /^[+-]?\d+\.\d{2}%$/;
    const pass = percentRegex.test(received);
    
    return {
      pass,
      message: () =>
        pass
          ? `expected ${received} not to be a valid percentage format`
          : `expected ${received} to match percentage format +/-XX.XX%`
    };
  }
});

// Console filtering
const originalConsoleError = console.error;
console.error = (...args) => {
  // Filter out known non-critical errors
  const message = args[0]?.toString() || '';
  if (
    message.includes('favicon') ||
    message.includes('404') ||
    message.includes('Failed to load resource')
  ) {
    return;
  }
  originalConsoleError(...args);
};

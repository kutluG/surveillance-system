/**
 * Jest setup for frontend XSS tests
 */

// Mock DOMPurify for testing
global.DOMPurify = {
    sanitize: jest.fn((input, config) => {
        // Simple mock implementation that removes script tags
        if (typeof input !== 'string') return '';
        
        // Remove script tags
        let sanitized = input.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
        
        // If ALLOWED_TAGS is empty array, remove all HTML tags
        if (config && config.ALLOWED_TAGS && config.ALLOWED_TAGS.length === 0) {
            sanitized = sanitized.replace(/<[^>]*>/g, '');
        }
        
        return sanitized;
    })
};

// Mock window object
Object.defineProperty(window, 'DOMPurify', {
    value: global.DOMPurify,
    writable: true
});

console.log('✅ Jest setup complete with DOMPurify mock');

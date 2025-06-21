/**
 * Jest setup configuration
 * Sets up global mocks and test utilities
 */

// Mock console methods to reduce noise in tests (preserve original for Jest)
const originalConsole = global.console;
global.console = {
    ...originalConsole,
    log: jest.fn(),
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
};

// Mock window.confirm and window.alert
global.confirm = jest.fn(() => true);
global.alert = jest.fn();

// Mock canvas context for jsdom
HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
    fillStyle: '',
    fillRect: jest.fn(),
    fillText: jest.fn(),
    font: '',
    textAlign: '',
}));

// Mock DOM methods that might not be available in jsdom
global.ResizeObserver = jest.fn().mockImplementation(() => ({
    observe: jest.fn(),
    unobserve: jest.fn(),
    disconnect: jest.fn(),
}));

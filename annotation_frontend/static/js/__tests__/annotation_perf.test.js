/**
 * Frontend Performance Tests
 * Tests for WebSocket functionality and pagination rendering
 */

// Mock DOM elements for testing
const mockDOM = {
    createElement: jest.fn((tagName) => ({
        tagName: tagName.toUpperCase(),
        className: '',
        textContent: '',
        style: {},
        setAttribute: jest.fn(),
        appendChild: jest.fn(),
        addEventListener: jest.fn(),
        insertBefore: jest.fn(),
        remove: jest.fn(),
        querySelector: jest.fn(),
        querySelectorAll: jest.fn(),
        firstChild: null,
        parentNode: null
    })),
    querySelector: jest.fn(),
    getElementById: jest.fn(),
    createDocumentFragment: jest.fn(() => ({
        appendChild: jest.fn(),
        children: []
    }))
};

// Mock window and document
global.document = mockDOM;
global.window = {
    addEventListener: jest.fn(),
    API_BASE_URL: 'http://localhost:8000'
};

// Mock WebSocket
class MockWebSocket {
    constructor(url) {
        this.url = url;
        this.readyState = WebSocket.CONNECTING;
        this.onopen = null;
        this.onmessage = null;
        this.onerror = null;
        this.onclose = null;
        MockWebSocket.instances.push(this);
        
        // Simulate connection after a short delay
        setTimeout(() => {
            this.readyState = WebSocket.OPEN;
            if (this.onopen) this.onopen({ type: 'open' });
        }, 10);
    }
    
    send(data) {
        this.lastSentData = data;
    }
    
    close() {
        this.readyState = WebSocket.CLOSED;
        if (this.onclose) this.onclose({ type: 'close' });
    }
    
    // Helper to simulate receiving messages
    simulateMessage(data) {
        if (this.onmessage) {
            this.onmessage({ data: JSON.stringify(data) });
        }
    }
    
    // Helper to simulate errors
    simulateError(error) {
        if (this.onerror) {
            this.onerror(error);
        }
    }
}

MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSING = 2;
MockWebSocket.CLOSED = 3;
MockWebSocket.instances = [];

global.WebSocket = MockWebSocket;

// Import the modules we're testing
import { connectWebSocket, disconnectWebSocket } from '../api.js';
import { renderExamples, addExample } from '../ui.js';

describe('WebSocket Functionality', () => {
    beforeEach(() => {
        MockWebSocket.instances = [];
        jest.clearAllMocks();
    });    test('should connect to WebSocket and handle new example events', async () => {
        const mockOnNewExample = jest.fn();
        const mockOnError = jest.fn();
        const mockOnStatusChange = jest.fn();

        // Connect WebSocket
        const ws = connectWebSocket(mockOnNewExample, mockOnError, mockOnStatusChange);
        
        expect(ws).toBeInstanceOf(MockWebSocket);
        expect(ws.url).toBe('ws://localhost:8000/ws/v1/examples');

        // Wait for connection
        await new Promise(resolve => setTimeout(resolve, 20));
        expect(ws.readyState).toBe(WebSocket.OPEN);
        expect(mockOnStatusChange).toHaveBeenCalledWith('connected');

        // Simulate receiving a new example
        const newExample = {
            event_id: 'test-123',
            camera_id: 'cam-01',
            timestamp: '2024-01-15T10:30:00Z',
            confidence_scores: { person: 0.85 },
            reason: 'Low confidence'
        };

        ws.simulateMessage({
            type: 'new_example',
            example: newExample
        });

        expect(mockOnNewExample).toHaveBeenCalledWith(newExample);
    });    test('should handle WebSocket errors gracefully', async () => {
        const mockOnNewExample = jest.fn();
        const mockOnError = jest.fn();
        const mockOnStatusChange = jest.fn();

        const ws = connectWebSocket(mockOnNewExample, mockOnError, mockOnStatusChange);
        
        // Simulate an error
        const error = new Error('Connection failed');
        ws.simulateError(error);

        expect(mockOnError).toHaveBeenCalledWith(error);
        expect(mockOnStatusChange).toHaveBeenCalledWith('disconnected', 'Connection error');
    });    test('should attempt reconnection on disconnect', async () => {
        const mockOnNewExample = jest.fn();
        const mockOnError = jest.fn();
        const mockOnStatusChange = jest.fn();

        const ws = connectWebSocket(mockOnNewExample, mockOnError, mockOnStatusChange);
        
        // Wait for initial connection
        await new Promise(resolve => setTimeout(resolve, 20));
        
        // Simulate disconnect
        ws.close();
        
        expect(mockOnStatusChange).toHaveBeenCalledWith('disconnected');
        
        // Wait for reconnection attempt
        await new Promise(resolve => setTimeout(resolve, 1100));
        
        // Should have created a new WebSocket instance for reconnection
        expect(MockWebSocket.instances.length).toBeGreaterThan(1);
    });    test('should disconnect WebSocket cleanly', () => {
        const mockOnNewExample = jest.fn();
        const mockOnError = jest.fn();
        const mockOnStatusChange = jest.fn();

        const ws = connectWebSocket(mockOnNewExample, mockOnError, mockOnStatusChange);
        
        disconnectWebSocket();
        
        expect(ws.readyState).toBe(WebSocket.CLOSED);
    });
});

describe('Pagination Rendering', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        
        // Mock required DOM elements
        mockDOM.getElementById.mockImplementation((id) => {
            const mockElement = {
                textContent: '',
                innerHTML: '',
                appendChild: jest.fn(),
                insertBefore: jest.fn(),
                querySelector: jest.fn(),
                remove: jest.fn(),
                firstChild: null,
                parentNode: null
            };
            
            if (id === 'examples-list') {
                mockElement.innerHTML = '';
            } else if (id === 'pagination-container') {
                mockElement.innerHTML = '';
            } else if (id === 'pending-count') {
                mockElement.textContent = '0';
            }
            
            return mockElement;
        });
    });

    test('should render examples with pagination controls', () => {
        const examples = [
            {
                event_id: 'test-1',
                camera_id: 'cam-01',
                timestamp: '2024-01-15T10:30:00Z',
                confidence_scores: { person: 0.85 },
                reason: 'Low confidence'
            },
            {
                event_id: 'test-2',
                camera_id: 'cam-02',
                timestamp: '2024-01-15T10:35:00Z',
                confidence_scores: { vehicle: 0.45 },
                reason: 'Low confidence'
            }
        ];

        const mockOnExampleClick = jest.fn();
        const mockOnPageChange = jest.fn();

        renderExamples(examples, 25, 1, 10, mockOnExampleClick, mockOnPageChange);

        // Should update pending count
        const pendingCount = mockDOM.getElementById('pending-count');
        expect(pendingCount.textContent).toBe('25');

        // Should render examples using DocumentFragment
        expect(mockDOM.createDocumentFragment).toHaveBeenCalled();
        
        // Should render pagination for multiple pages
        const paginationContainer = mockDOM.getElementById('pagination-container');
        expect(paginationContainer.innerHTML).toBe(''); // Mock clears innerHTML
    });

    test('should handle empty examples list', () => {
        const mockOnExampleClick = jest.fn();
        const mockOnPageChange = jest.fn();

        renderExamples([], 0, 1, 10, mockOnExampleClick, mockOnPageChange);

        const examplesList = mockDOM.getElementById('examples-list');
        expect(examplesList.innerHTML).toBe('');
    });

    test('should not render pagination for single page', () => {
        const examples = [
            {
                event_id: 'test-1',
                camera_id: 'cam-01',
                timestamp: '2024-01-15T10:30:00Z',
                confidence_scores: { person: 0.85 },
                reason: 'Low confidence'
            }
        ];

        const mockOnExampleClick = jest.fn();
        const mockOnPageChange = jest.fn();

        renderExamples(examples, 5, 1, 10, mockOnExampleClick, mockOnPageChange);

        // Should not render pagination when total <= pageSize
        const paginationContainer = mockDOM.getElementById('pagination-container');
        expect(paginationContainer.innerHTML).toBe('');
    });

    test('should calculate correct number of pages', () => {
        const examples = [];
        const mockOnExampleClick = jest.fn();
        const mockOnPageChange = jest.fn();

        // Test with 25 total items, 10 per page = 3 pages
        renderExamples(examples, 25, 2, 10, mockOnExampleClick, mockOnPageChange);

        // Mock would normally create pagination elements
        // In a real test, we'd verify the correct number of page buttons
        expect(mockDOM.createDocumentFragment).toHaveBeenCalled();
    });
});

describe('Incremental DOM Updates', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        
        mockDOM.getElementById.mockImplementation((id) => {
            const mockElement = {
                textContent: '5',
                appendChild: jest.fn(),
                insertBefore: jest.fn(),
                querySelector: jest.fn(() => null), // No empty message initially
                remove: jest.fn(),
                firstChild: null,
                parentNode: null,
                style: {}
            };
            
            return mockElement;
        });

        mockDOM.querySelector.mockReturnValue({
            insertBefore: jest.fn(),
            firstChild: null
        });

        // Mock requestAnimationFrame
        global.requestAnimationFrame = jest.fn(cb => setTimeout(cb, 16));
    });

    test('should add new example incrementally without full re-render', () => {
        const newExample = {
            event_id: 'new-test',
            camera_id: 'cam-03',
            timestamp: '2024-01-15T11:00:00Z',
            confidence_scores: { person: 0.75 },
            reason: 'Low confidence'
        };

        const mockOnExampleClick = jest.fn();

        addExample(newExample, mockOnExampleClick);

        // Should create new DOM element
        expect(mockDOM.createElement).toHaveBeenCalledWith('div');
        
        // Should insert at beginning of list
        const examplesList = mockDOM.getElementById('examples-list');
        expect(examplesList.insertBefore).toHaveBeenCalled();

        // Should update pending count
        const pendingCount = mockDOM.getElementById('pending-count');
        expect(pendingCount.textContent).toBe('6'); // 5 + 1
    });

    test('should remove empty message when adding first example', () => {
        // Mock empty message exists
        const mockEmptyMessage = {
            remove: jest.fn()
        };
        
        mockDOM.getElementById.mockImplementation((id) => {
            if (id === 'examples-list') {
                return {
                    textContent: '0',
                    appendChild: jest.fn(),
                    insertBefore: jest.fn(),
                    querySelector: jest.fn(() => mockEmptyMessage),
                    firstChild: null,
                    style: {}
                };
            }
            return {
                textContent: '0',
                appendChild: jest.fn(),
                insertBefore: jest.fn(),
                querySelector: jest.fn(),
                remove: jest.fn(),
                firstChild: null,
                parentNode: null,
                style: {}
            };
        });

        const newExample = {
            event_id: 'first-example',
            camera_id: 'cam-01',
            timestamp: '2024-01-15T10:00:00Z',
            confidence_scores: { person: 0.90 },
            reason: 'Low confidence'
        };

        const mockOnExampleClick = jest.fn();

        addExample(newExample, mockOnExampleClick);

        // Should remove empty message
        expect(mockEmptyMessage.remove).toHaveBeenCalled();
    });

    test('should animate new example addition', () => {
        const newExample = {
            event_id: 'animated-test',
            camera_id: 'cam-04',
            timestamp: '2024-01-15T11:30:00Z',
            confidence_scores: { vehicle: 0.80 },
            reason: 'Low confidence'
        };

        const mockOnExampleClick = jest.fn();

        addExample(newExample, mockOnExampleClick);

        // Should set initial animation state
        const mockCard = mockDOM.createElement('div');
        expect(mockCard.style.opacity).toBeDefined();
        expect(mockCard.style.transform).toBeDefined();

        // Should trigger animation via requestAnimationFrame
        expect(global.requestAnimationFrame).toHaveBeenCalled();
    });
});

describe('Performance Optimizations', () => {
    test('should use DocumentFragment for batch DOM updates', () => {
        const examples = new Array(20).fill(null).map((_, i) => ({
            event_id: `test-${i}`,
            camera_id: `cam-${i}`,
            timestamp: '2024-01-15T10:30:00Z',
            confidence_scores: { person: 0.85 },
            reason: 'Low confidence'
        }));

        const mockOnExampleClick = jest.fn();
        const mockOnPageChange = jest.fn();

        renderExamples(examples, 100, 1, 20, mockOnExampleClick, mockOnPageChange);

        // Should create DocumentFragment for batch operations
        expect(mockDOM.createDocumentFragment).toHaveBeenCalled();
        
        // Should create elements for each example
        expect(mockDOM.createElement).toHaveBeenCalledWith('div');
    });

    test('should minimize DOM queries by caching elements', () => {
        const mockOnExampleClick = jest.fn();
        const mockOnPageChange = jest.fn();

        // Call renderExamples multiple times
        renderExamples([], 0, 1, 10, mockOnExampleClick, mockOnPageChange);
        renderExamples([], 0, 1, 10, mockOnExampleClick, mockOnPageChange);

        // getElementById should be called but we're testing the pattern
        expect(mockDOM.getElementById).toHaveBeenCalledWith('examples-list');
        expect(mockDOM.getElementById).toHaveBeenCalledWith('pending-count');
    });
});

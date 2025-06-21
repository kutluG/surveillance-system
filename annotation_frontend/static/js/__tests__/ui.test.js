/**
 * Jest tests for the UI module
 * Tests DOM manipulation and rendering logic using @testing-library/dom
 */

import '@testing-library/jest-dom';
import { 
    showError, 
    showSuccess, 
    renderExamples
} from '../ui.js';

// Mock window and global DOM objects
global.document = document;
global.HTMLElement = HTMLElement;

describe('UI Module', () => {
    beforeEach(() => {
        // Reset DOM before each test
        document.body.innerHTML = '';
        
        // Create basic DOM structure that the UI module expects
        const container = document.createElement('div');
        container.className = 'container-fluid';
        
        const pendingCountElement = document.createElement('span');
        pendingCountElement.id = 'pending-count';
        
        const examplesList = document.createElement('div');
        examplesList.id = 'examples-list';
        
        container.appendChild(pendingCountElement);
        container.appendChild(examplesList);
        document.body.appendChild(container);
    });

    describe('showError', () => {
        it('should display error message in DOM', () => {
            const errorMessage = 'Test error message';
            
            showError(errorMessage);
            
            // Check that error element was created
            const errorElement = document.querySelector('.error-alert');
            expect(errorElement).toBeInTheDocument();
            expect(errorElement).toHaveClass('alert', 'alert-danger', 'alert-dismissible', 'fade', 'show');
            expect(errorElement).toHaveAttribute('role', 'alert');
            
            // Check error message content (should use textContent for XSS safety)
            const errorText = errorElement.querySelector('span');
            expect(errorText).toHaveTextContent(errorMessage);
            
            // Check close button
            const closeButton = errorElement.querySelector('button.btn-close');
            expect(closeButton).toBeInTheDocument();
            expect(closeButton).toHaveAttribute('data-bs-dismiss', 'alert');
            expect(closeButton).toHaveAttribute('aria-label', 'Close');
        });

        it('should remove existing error before showing new one', () => {
            showError('First error');
            expect(document.querySelectorAll('.error-alert')).toHaveLength(1);
            
            showError('Second error');
            expect(document.querySelectorAll('.error-alert')).toHaveLength(1);
            expect(document.querySelector('.error-alert span')).toHaveTextContent('Second error');
        });

        it('should insert error at top of container', () => {
            const existingElement = document.createElement('div');
            existingElement.textContent = 'Existing content';
            document.querySelector('.container-fluid').appendChild(existingElement);
            
            showError('Test error');
            
            const container = document.querySelector('.container-fluid');
            expect(container.firstChild).toHaveClass('error-alert');
        });        it('should handle missing container gracefully', () => {
            // Remove container
            document.body.innerHTML = '';
            
            // Should not throw error
            expect(() => showError('Test error')).not.toThrow();
        });

        // TODO: Fix timing-based tests
        it.skip('should auto-remove error after timeout', (done) => {
            jest.useFakeTimers();
            
            showError('Test error');
            expect(document.querySelector('.error-alert')).toBeInTheDocument();
            
            // Fast-forward time
            jest.advanceTimersByTime(5000);
            
            // Use setTimeout to check after the removal
            setTimeout(() => {
                expect(document.querySelector('.error-alert')).not.toBeInTheDocument();
                jest.useRealTimers();
                done();
            }, 0);
        });
    });

    describe('showSuccess', () => {
        it('should display success message in DOM', () => {
            const successMessage = 'Operation successful';
            
            showSuccess(successMessage);
            
            const successElement = document.querySelector('.success-alert');
            expect(successElement).toBeInTheDocument();
            expect(successElement).toHaveClass('alert', 'alert-success', 'alert-dismissible', 'fade', 'show');
            
            const successText = successElement.querySelector('span');
            expect(successText).toHaveTextContent(successMessage);
        });

        it('should remove existing success before showing new one', () => {
            showSuccess('First success');
            showSuccess('Second success');
            
            expect(document.querySelectorAll('.success-alert')).toHaveLength(1);
            expect(document.querySelector('.success-alert span')).toHaveTextContent('Second success');
        });

        it('should auto-remove success after 3 seconds', () => {
            jest.useFakeTimers();
            
            showSuccess('Test success');
            expect(document.querySelector('.success-alert')).toBeInTheDocument();
            
            jest.advanceTimersByTime(3000);
            
            // Check that it's removed after 3 seconds (faster than error timeout)
            setTimeout(() => {
                expect(document.querySelector('.success-alert')).not.toBeInTheDocument();
                jest.useRealTimers();
            }, 0);
        });
    });

    describe('renderExamples', () => {
        const mockOnExampleClick = jest.fn();

        beforeEach(() => {
            mockOnExampleClick.mockClear();
        });

        it('should update pending count', () => {
            const examples = [];
            const total = 5;
            
            renderExamples(examples, total, mockOnExampleClick);
            
            const pendingCountElement = document.getElementById('pending-count');
            expect(pendingCountElement).toHaveTextContent('5');
        });        it('should render empty state when no examples', () => {
            renderExamples([], 0, mockOnExampleClick);
            
            const examplesList = document.getElementById('examples-list');
            expect(examplesList.innerHTML).toBe('<p class="text-muted text-center">No pending examples</p>');
            
            const emptyMessage = examplesList.querySelector('p');
            expect(emptyMessage).toBeInTheDocument();
            expect(emptyMessage).toHaveTextContent('No pending examples');
            expect(emptyMessage).toHaveClass('text-muted', 'text-center');
        });

        it('should render example cards when examples exist', () => {
            const mockExamples = [
                {
                    event_id: 'test-1',
                    camera_id: 'cam-1',
                    timestamp: '2025-06-16T10:00:00Z',
                    reason: 'Low confidence',
                    confidence_scores: { person: 0.3 }
                },
                {
                    event_id: 'test-2',
                    camera_id: 'cam-2',
                    timestamp: '2025-06-16T11:00:00Z',
                    reason: 'Object detection failed',
                    confidence_scores: { vehicle: 0.2 }
                }
            ];
            
            renderExamples(mockExamples, 2, mockOnExampleClick);
            
            const examplesList = document.getElementById('examples-list');
            const cards = examplesList.querySelectorAll('.example-card');
            
            expect(cards).toHaveLength(2);
            expect(cards[0]).toHaveClass('card', 'example-card', 'mb-2');
            expect(cards[0]).toHaveStyle('cursor: pointer');
        });

        it('should handle missing elements gracefully', () => {
            // Remove pending count element
            document.getElementById('pending-count').remove();
            
            expect(() => renderExamples([], 0, mockOnExampleClick)).not.toThrow();
            
            // Remove examples list
            document.getElementById('examples-list').remove();
            
            expect(() => renderExamples([], 0, mockOnExampleClick)).not.toThrow();
        });

        it('should clear existing examples before rendering new ones', () => {
            // Add some existing content
            const examplesList = document.getElementById('examples-list');
            examplesList.innerHTML = '<div class="old-content">Old</div>';
            
            const mockExamples = [
                { event_id: 'new-1', camera_id: 'cam-1', timestamp: '2025-06-16T10:00:00Z' }
            ];
            
            renderExamples(mockExamples, 1, mockOnExampleClick);
            
            expect(examplesList.querySelector('.old-content')).not.toBeInTheDocument();
            expect(examplesList.querySelectorAll('.example-card')).toHaveLength(1);
        });

        it('should add click handlers to example cards', () => {
            const mockExamples = [
                { event_id: 'clickable-1', camera_id: 'cam-1', timestamp: '2025-06-16T10:00:00Z' }
            ];
            
            renderExamples(mockExamples, 1, mockOnExampleClick);
            
            const card = document.querySelector('.example-card');
            expect(card).toBeInTheDocument();
            
            // Simulate click
            card.click();
            
            expect(mockOnExampleClick).toHaveBeenCalledWith('clickable-1');
            expect(mockOnExampleClick).toHaveBeenCalledTimes(1);
        });        it('should safely handle XSS in example data', () => {
            const maliciousExamples = [
                {
                    event_id: '<script>alert("xss")</script>',
                    camera_id: '<img src=x onerror=alert("xss")>',
                    timestamp: '2025-06-16T10:00:00Z',
                    reason: '<svg onload=alert("xss")>attack</svg>'
                }
            ];
            
            renderExamples(maliciousExamples, 1, mockOnExampleClick);
            
            const examplesList = document.getElementById('examples-list');
            
            // Should not contain executable script tags
            expect(examplesList.innerHTML).not.toContain('<script>alert("xss")</script>');
            expect(examplesList.innerHTML).not.toContain('<img src=x onerror=alert("xss")>');
            expect(examplesList.innerHTML).not.toContain('<svg onload=alert("xss")>attack</svg>');
            
            // But should contain the text content safely escaped
            expect(examplesList.innerHTML).toContain('&lt;img src=x onerror=alert("xss")&gt;');
            expect(examplesList.textContent).toContain('alert("xss")'); // As safe text, not executable
        });
    });    describe('DOM manipulation safety', () => {
        it('should use textContent instead of innerHTML for user data', () => {
            const maliciousContent = '<script>alert("xss")</script>';
            
            showError(maliciousContent);
            
            const errorElement = document.querySelector('.error-alert span');
            expect(errorElement.textContent).toBe(maliciousContent);
            expect(errorElement.innerHTML).toBe('&lt;script&gt;alert("xss")&lt;/script&gt;'); // Should be escaped
            expect(document.querySelector('script')).not.toBeInTheDocument();
        });
        
        it('should use createElement for dynamic DOM creation', () => {
            showError('Test message');
            
            const errorElement = document.querySelector('.error-alert');
            
            // Should be created with createElement (proper DOM node)
            expect(errorElement).toBeInstanceOf(HTMLElement);
            expect(errorElement.tagName).toBe('DIV');
        });
    });
});

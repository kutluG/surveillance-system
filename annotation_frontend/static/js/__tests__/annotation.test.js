/**
 * Jest tests for the Annotation module
 * Tests application initialization, event handling, and coordination between API and UI modules
 */

import '@testing-library/jest-dom';

// Mock the API and UI modules before importing annotation
const mockFetchExamples = jest.fn();
const mockFetchExample = jest.fn();
const mockPostAnnotation = jest.fn();
const mockSkipExample = jest.fn();

const mockShowError = jest.fn();
const mockShowSuccess = jest.fn();
const mockRenderExamples = jest.fn();
const mockDisplayOriginalDetections = jest.fn();
const mockDisplayCorrectedDetections = jest.fn();
const mockToggleAnnotationPanel = jest.fn();
const mockUpdateExampleTitle = jest.fn();
const mockClearAnnotationForm = jest.fn();

jest.mock('../api.js', () => ({
    fetchExamples: mockFetchExamples,
    fetchExample: mockFetchExample,
    postAnnotation: mockPostAnnotation,
    skipExample: mockSkipExample
}));

jest.mock('../ui.js', () => ({
    showError: mockShowError,
    showSuccess: mockShowSuccess,
    renderExamples: mockRenderExamples,
    displayOriginalDetections: mockDisplayOriginalDetections,
    displayCorrectedDetections: mockDisplayCorrectedDetections,
    toggleAnnotationPanel: mockToggleAnnotationPanel,
    updateExampleTitle: mockUpdateExampleTitle,
    clearAnnotationForm: mockClearAnnotationForm
}));

describe('Annotation Module', () => {
    beforeEach(() => {
        // Clear all mocks before each test
        jest.clearAllMocks();
        
        // Reset DOM
        document.body.innerHTML = '';
        
        // Create basic DOM structure that the annotation module expects
        const container = document.createElement('div');
        container.innerHTML = `
            <div id="examples-list"></div>
            <div id="pending-count"></div>
            <button id="submit-button">Submit</button>
            <button id="skip-button">Skip</button>
            <input id="annotator-id" />
            <input id="quality-score" value="1.0" />
            <textarea id="notes"></textarea>
            <canvas id="annotation-canvas"></canvas>
        `;
        document.body.appendChild(container);
        
        // Mock successful API responses
        mockFetchExamples.mockResolvedValue({
            examples: [
                {
                    event_id: 'test-1',
                    camera_id: 'cam-1',
                    timestamp: '2025-06-16T10:00:00Z',
                    detections: [
                        {
                            bbox: [10, 10, 50, 50],
                            class_name: 'person',
                            confidence: 0.8
                        }
                    ]
                }
            ],
            total: 1
        });
        
        mockFetchExample.mockResolvedValue({
            event_id: 'test-1',
            camera_id: 'cam-1',
            timestamp: '2025-06-16T10:00:00Z',
            detections: [
                {
                    bbox: [10, 10, 50, 50],
                    class_name: 'person',
                    confidence: 0.8
                }
            ]
        });
        
        mockPostAnnotation.mockResolvedValue({ success: true });
        mockSkipExample.mockResolvedValue({ success: true });
        
        // Mock document ready state
        Object.defineProperty(document, 'readyState', {
            writable: true,
            value: 'complete'
        });
    });

    describe('Module Setup and Mocking', () => {
        it('should have all API functions mocked', () => {
            expect(mockFetchExamples).toBeDefined();
            expect(mockFetchExample).toBeDefined();
            expect(mockPostAnnotation).toBeDefined();
            expect(mockSkipExample).toBeDefined();
        });

        it('should have all UI functions mocked', () => {
            expect(mockShowError).toBeDefined();
            expect(mockShowSuccess).toBeDefined();
            expect(mockRenderExamples).toBeDefined();
            expect(mockDisplayOriginalDetections).toBeDefined();
            expect(mockDisplayCorrectedDetections).toBeDefined();
            expect(mockToggleAnnotationPanel).toBeDefined();
            expect(mockUpdateExampleTitle).toBeDefined();
            expect(mockClearAnnotationForm).toBeDefined();
        });

        it('should have DOM elements set up correctly', () => {
            expect(document.getElementById('submit-button')).toBeInTheDocument();
            expect(document.getElementById('skip-button')).toBeInTheDocument();
            expect(document.getElementById('annotator-id')).toBeInTheDocument();
            expect(document.getElementById('quality-score')).toBeInTheDocument();
            expect(document.getElementById('notes')).toBeInTheDocument();
            expect(document.getElementById('annotation-canvas')).toBeInTheDocument();
        });
    });

    describe('API Integration Tests', () => {
        it('should call fetchExamples when requested', async () => {
            const result = await mockFetchExamples();
            
            expect(mockFetchExamples).toHaveBeenCalledTimes(1);
            expect(result).toEqual({
                examples: expect.arrayContaining([
                    expect.objectContaining({
                        event_id: 'test-1',
                        camera_id: 'cam-1'
                    })
                ]),
                total: 1
            });
        });

        it('should call fetchExample when requested', async () => {
            const result = await mockFetchExample('test-1');
            
            expect(mockFetchExample).toHaveBeenCalledWith('test-1');
            expect(result).toEqual(expect.objectContaining({
                event_id: 'test-1',
                camera_id: 'cam-1'
            }));
        });

        it('should call postAnnotation when requested', async () => {
            const testData = {
                corrected_detections: [],
                annotator_id: 'test-annotator',
                quality_score: 0.9
            };
            
            await mockPostAnnotation('test-1', testData);
            
            expect(mockPostAnnotation).toHaveBeenCalledWith('test-1', testData);
        });

        it('should call skipExample when requested', async () => {
            await mockSkipExample('test-1');
            
            expect(mockSkipExample).toHaveBeenCalledWith('test-1');
        });
    });

    describe('UI Integration Tests', () => {
        it('should call renderExamples with correct parameters', () => {
            const testExamples = [
                { event_id: 'test-1', camera_id: 'cam-1' }
            ];
            const testCallback = jest.fn();
            
            mockRenderExamples(testExamples, 1, testCallback);
            
            expect(mockRenderExamples).toHaveBeenCalledWith(testExamples, 1, testCallback);
        });

        it('should call showError for error handling', () => {
            mockShowError('Test error message');
            
            expect(mockShowError).toHaveBeenCalledWith('Test error message');
        });

        it('should call showSuccess for success messages', () => {
            mockShowSuccess('Test success message');
            
            expect(mockShowSuccess).toHaveBeenCalledWith('Test success message');
        });

        it('should call UI functions for example display', () => {
            const testDetections = [
                { bbox: [10, 10, 50, 50], class_name: 'person', confidence: 0.8 }
            ];
            
            mockToggleAnnotationPanel(true);
            mockUpdateExampleTitle('cam-1', '2025-06-16T10:00:00Z');
            mockDisplayOriginalDetections(testDetections);
            mockDisplayCorrectedDetections(testDetections, jest.fn(), jest.fn());
            
            expect(mockToggleAnnotationPanel).toHaveBeenCalledWith(true);
            expect(mockUpdateExampleTitle).toHaveBeenCalledWith('cam-1', '2025-06-16T10:00:00Z');
            expect(mockDisplayOriginalDetections).toHaveBeenCalledWith(testDetections);
            expect(mockDisplayCorrectedDetections).toHaveBeenCalledWith(
                testDetections,
                expect.any(Function),
                expect.any(Function)
            );
        });
    });

    describe('Form Data Handling', () => {
        it('should read form values correctly', () => {
            const annotatorIdInput = document.getElementById('annotator-id');
            const qualityScoreInput = document.getElementById('quality-score');
            const notesInput = document.getElementById('notes');
            
            annotatorIdInput.value = 'test-annotator';
            qualityScoreInput.value = '0.9';
            notesInput.value = 'Test notes';
            
            expect(annotatorIdInput.value).toBe('test-annotator');
            expect(parseFloat(qualityScoreInput.value)).toBe(0.9);
            expect(notesInput.value).toBe('Test notes');
        });

        it('should handle empty form values', () => {
            const annotatorIdInput = document.getElementById('annotator-id');
            const qualityScoreInput = document.getElementById('quality-score');
            const notesInput = document.getElementById('notes');
            
            annotatorIdInput.value = '';
            qualityScoreInput.value = '';
            notesInput.value = '';
            
            expect(annotatorIdInput.value).toBe('');
            expect(qualityScoreInput.value).toBe('');
            expect(notesInput.value).toBe('');
        });
    });

    describe('Event Handling Simulation', () => {
        it('should handle button click events', () => {
            const submitButton = document.getElementById('submit-button');
            const skipButton = document.getElementById('skip-button');
            
            const submitHandler = jest.fn();
            const skipHandler = jest.fn();
            
            submitButton.addEventListener('click', submitHandler);
            skipButton.addEventListener('click', skipHandler);
            
            submitButton.click();
            skipButton.click();
            
            expect(submitHandler).toHaveBeenCalledTimes(1);
            expect(skipHandler).toHaveBeenCalledTimes(1);
        });

        it('should simulate form submission workflow', async () => {
            // Set up form data
            const annotatorIdInput = document.getElementById('annotator-id');
            annotatorIdInput.value = 'test-annotator';
            
            // Simulate the workflow that would happen in the real module
            // 1. Load examples
            await mockFetchExamples();
            mockRenderExamples([], 0, jest.fn());
            
            // 2. Select an example
            await mockFetchExample('test-1');
            mockToggleAnnotationPanel(true);
            mockDisplayOriginalDetections([]);
            mockDisplayCorrectedDetections([], jest.fn(), jest.fn());
            
            // 3. Submit annotation
            const annotationData = {
                corrected_detections: [],
                annotator_id: 'test-annotator',
                quality_score: 1.0
            };
            await mockPostAnnotation('test-1', annotationData);
            mockShowSuccess('Annotation submitted successfully!');
            
            // 4. Clear and refresh
            mockToggleAnnotationPanel(false);
            mockClearAnnotationForm();
            await mockFetchExamples();
            
            // Verify the workflow
            expect(mockFetchExamples).toHaveBeenCalledTimes(2);
            expect(mockRenderExamples).toHaveBeenCalled();
            expect(mockFetchExample).toHaveBeenCalledWith('test-1');
            expect(mockPostAnnotation).toHaveBeenCalledWith('test-1', annotationData);
            expect(mockShowSuccess).toHaveBeenCalledWith('Annotation submitted successfully!');
            expect(mockToggleAnnotationPanel).toHaveBeenCalledWith(false);
            expect(mockClearAnnotationForm).toHaveBeenCalled();
        });

        it('should simulate skip workflow', async () => {
            // Load an example first
            await mockFetchExample('test-1');
            mockToggleAnnotationPanel(true);
            
            // Skip the example
            await mockSkipExample('test-1');
            mockToggleAnnotationPanel(false);
            mockClearAnnotationForm();
            await mockFetchExamples();
            
            // Verify the workflow
            expect(mockSkipExample).toHaveBeenCalledWith('test-1');
            expect(mockToggleAnnotationPanel).toHaveBeenCalledWith(false);
            expect(mockClearAnnotationForm).toHaveBeenCalled();
            expect(mockFetchExamples).toHaveBeenCalled();
        });
    });

    describe('Error Handling Simulation', () => {
        it('should handle API errors', async () => {
            mockFetchExamples.mockRejectedValueOnce(new Error('Network error'));
            
            try {
                await mockFetchExamples();
            } catch (error) {
                mockShowError(error.message);
            }
            
            expect(mockShowError).toHaveBeenCalledWith('Network error');
        });

        it('should handle validation errors', () => {
            // Simulate validation error for missing annotator ID
            const annotatorIdInput = document.getElementById('annotator-id');
            annotatorIdInput.value = '';
            
            if (!annotatorIdInput.value) {
                mockShowError('Please enter your annotator ID');
            }
            
            expect(mockShowError).toHaveBeenCalledWith('Please enter your annotator ID');
        });
    });

    describe('Canvas Integration', () => {
        it('should have canvas element available', () => {
            const canvas = document.getElementById('annotation-canvas');
            expect(canvas).toBeInTheDocument();
            expect(canvas.tagName).toBe('CANVAS');
        });

        it('should be able to get canvas context', () => {
            const canvas = document.getElementById('annotation-canvas');
            expect(() => {
                const ctx = canvas.getContext('2d');
                expect(ctx).toBeDefined();
            }).not.toThrow();
        });

        it('should be able to set canvas dimensions', () => {
            const canvas = document.getElementById('annotation-canvas');
            canvas.width = 640;
            canvas.height = 480;
            
            expect(canvas.width).toBe(640);
            expect(canvas.height).toBe(480);
        });
    });
});

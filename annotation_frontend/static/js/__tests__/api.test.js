/**
 * Jest tests for the API module
 * Tests network calls and error handling with comprehensive coverage
 */

// Mock window object before importing the module
global.window = {
    API_BASE_URL: 'http://localhost:8000'
};

// Mock global fetch
global.fetch = jest.fn();

import { fetchExamples, fetchExample, postAnnotation, skipExample } from '../api.js';

describe('API Module', () => {
    beforeEach(() => {
        // Clear all mocks before each test
        fetch.mockClear();
        // Reset console.error mock
        jest.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        // Restore console.error
        console.error.mockRestore();
    });

    describe('fetchExamples', () => {
        it('should fetch examples successfully', async () => {
            const mockResponse = {
                examples: [
                    {
                        event_id: 'test-1',
                        camera_id: 'cam-1',
                        timestamp: '2025-06-16T10:00:00Z',
                        reason: 'Low confidence',
                        confidence_scores: { person: 0.3 }
                    }
                ],
                total: 1
            };

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            const result = await fetchExamples();

            expect(fetch).toHaveBeenCalledWith('/api/v1/examples');
            expect(result).toEqual(mockResponse);
        });

        it('should handle fetch errors', async () => {
            fetch.mockRejectedValueOnce(new Error('Network error'));

            await expect(fetchExamples()).rejects.toThrow('Failed to load examples. Please check your network connection.');
            expect(console.error).toHaveBeenCalledWith('Failed to fetch examples:', expect.any(Error));
        });

        it('should handle non-2xx HTTP responses', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 500,
                statusText: 'Internal Server Error'
            });

            await expect(fetchExamples()).rejects.toThrow('Failed to load examples. Please check your network connection.');
            expect(console.error).toHaveBeenCalledWith('Failed to fetch examples:', expect.any(Error));
        });

        it('should handle empty response', async () => {
            const mockResponse = {
                examples: [],
                total: 0
            };

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            const result = await fetchExamples();

            expect(result).toEqual(mockResponse);
            expect(result.examples).toHaveLength(0);
        });
    });

    describe('fetchExample', () => {
        it('should fetch a specific example successfully', async () => {
            const mockExample = {
                event_id: 'test-123',
                camera_id: 'cam-1',
                timestamp: '2025-06-16T10:00:00Z',
                detections: [{ class: 'person', confidence: 0.75 }]
            };

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockExample
            });

            const result = await fetchExample('test-123');

            expect(fetch).toHaveBeenCalledWith('/api/v1/examples/test-123');
            expect(result).toEqual(mockExample);
        });

        it('should handle 404 response for non-existent example', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 404,
                statusText: 'Not Found'
            });

            await expect(fetchExample('nonexistent')).rejects.toThrow('Failed to load example. Please try again.');
        });
    });

    describe('postAnnotation', () => {
        const mockAnnotationData = {
            corrected_detections: [
                {
                    bbox: { x1: 100, y1: 200, x2: 300, y2: 400 },
                    class_name: 'person',
                    confidence: 0.85,
                    is_correct: true
                }
            ],
            annotator_id: 'test-annotator',
            quality_score: 0.9,
            notes: 'Good detection'
        };

        it('should submit annotation successfully', async () => {
            const mockResponse = { status: 'success', event_id: 'test-123' };

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            const result = await postAnnotation('test-123', mockAnnotationData);

            expect(fetch).toHaveBeenCalledWith('/api/v1/examples/test-123/label', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(mockAnnotationData)
            });
            expect(result).toEqual(mockResponse);
        });

        it('should handle validation errors (422)', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 422,
                statusText: 'Unprocessable Entity'
            });

            await expect(postAnnotation('test-123', mockAnnotationData))
                .rejects.toThrow('Failed to submit annotation. Please try again.');
        });

        it('should handle server errors (500)', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 500,
                statusText: 'Internal Server Error'
            });

            await expect(postAnnotation('test-123', mockAnnotationData))
                .rejects.toThrow('Failed to submit annotation. Please try again.');
        });

        it('should handle network failures', async () => {
            fetch.mockRejectedValueOnce(new Error('Connection timeout'));

            await expect(postAnnotation('test-123', mockAnnotationData))
                .rejects.toThrow('Failed to submit annotation. Please try again.');
            expect(console.error).toHaveBeenCalledWith('Failed to submit annotation:', expect.any(Error));
        });
    });

    describe('skipExample', () => {
        it('should skip example successfully', async () => {
            const mockResponse = { status: 'skipped', event_id: 'test-123' };

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            const result = await skipExample('test-123');

            expect(fetch).toHaveBeenCalledWith('/api/v1/examples/test-123', {
                method: 'DELETE'
            });
            expect(result).toEqual(mockResponse);
        });

        it('should handle skip failures', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 404,
                statusText: 'Not Found'
            });

            await expect(skipExample('test-123'))
                .rejects.toThrow('Failed to skip example. Please try again.');
        });
    });

    describe('API configuration', () => {
        it('should use correct base URL when window.API_BASE_URL is set', async () => {
            global.window.API_BASE_URL = 'https://example.com';

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ examples: [], total: 0 })
            });

            await fetchExamples();

            expect(fetch).toHaveBeenCalledWith('https://example.com/api/v1/examples');

            // Reset for other tests
            global.window.API_BASE_URL = 'http://localhost:8000';
        });

        it('should handle missing window object gracefully', async () => {
            // Temporarily remove window
            const originalWindow = global.window;
            delete global.window;

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ examples: [], total: 0 })
            });

            await fetchExamples();

            expect(fetch).toHaveBeenCalledWith('/api/v1/examples');

            // Restore window
            global.window = originalWindow;
        });
    });
});

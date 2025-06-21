/**
 * Annotation Module - Main application logic and coordination
 * Coordinates between API and UI modules, handles canvas and events
 */

import { fetchExamples, fetchExample, postAnnotation, skipExample, connectWebSocket, disconnectWebSocket, initializeApi } from './api.js';
import { 
    showError, 
    showSuccess, 
    renderExamples, 
    displayOriginalDetections, 
    displayCorrectedDetections,
    toggleAnnotationPanel,
    updateExampleTitle,
    clearAnnotationForm,
    addExample
} from './ui.js';
import { 
    sanitizeFormData, 
    validateAnnotationLabel, 
    validateAnnotatorId,
    initializeSanitization 
} from './sanitize.js';

// Application state
let currentExample = null;
let correctedDetections = [];
let currentPage = 1;
let pageSize = 10;
let totalExamples = 0;

/**
 * Initialize the annotation application
 */
async function initializeApp() {
    // Initialize sanitization first
    await initializeSanitization();
    
    // Initialize API with CSRF token
    await initializeApi();
    
    // Load initial examples
    loadExamples();

    // Update WebSocket status to connecting
    updateWebSocketStatus('connecting');

    // Connect to WebSocket for real-time updates
    connectWebSocket(handleNewExample, handleWebSocketError, handleWebSocketStatusChange);

    // Set up event listeners
    setupEventListeners();

    // Initialize canvas
    initializeCanvas();

    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        disconnectWebSocket();
    });
}

/**
 * Set up event listeners for the application
 */
function setupEventListeners() {
    // Submit button
    const submitButton = document.getElementById('submit-button');
    if (submitButton) {
        submitButton.addEventListener('click', handleSubmitAnnotation);
    }

    // Skip button
    const skipButton = document.getElementById('skip-button');
    if (skipButton) {
        skipButton.addEventListener('click', handleSkipExample);
    }
}

/**
 * Load and display the list of pending examples with pagination
 * @param {number} [page] - Page number to load (defaults to currentPage)
 */
async function loadExamples(page = currentPage) {
    try {
        const data = await fetchExamples(page, pageSize);
        currentPage = page;
        totalExamples = data.total || 0;
        
        renderExamples(
            data.examples || [], 
            totalExamples, 
            currentPage, 
            pageSize, 
            handleExampleClick, 
            handlePageChange
        );
    } catch (error) {
        showError(error.message);
    }
}

/**
 * Handle clicking on an example card
 * @param {string} eventId - The event ID to load
 */
async function handleExampleClick(eventId) {
    try {
        const example = await fetchExample(eventId);
        loadExampleData(example);
    } catch (error) {
        showError(error.message);
    }
}

/**
 * Load example data into the annotation interface
 * @param {Object} example - The example data
 */
function loadExampleData(example) {
    currentExample = example;
    correctedDetections = [];

    // Show annotation panel
    toggleAnnotationPanel(true);

    // Update title
    updateExampleTitle(example.camera_id || 'Unknown Camera', example.timestamp);

    // Load original detections
    displayOriginalDetections(example.detections || []);

    // Initialize corrected detections
    initializeCorrectedDetections(example.detections || []);

    // Display placeholder image for now
    displayPlaceholderImage();
}

/**
 * Initialize corrected detections based on original detections
 * @param {Array} detections - Original detections
 */
function initializeCorrectedDetections(detections) {
    correctedDetections = detections.map(det => ({
        bbox: det.bbox,
        class_name: det.class_name,
        confidence: det.confidence,
        corrected_class: det.class_name,
        is_correct: true
    }));

    displayCorrectedDetections(
        correctedDetections,
        handleDetectionCorrectnessChange,
        handleDetectionClassChange
    );
}

/**
 * Handle changes to detection correctness
 * @param {number} idx - Index of the detection
 * @param {boolean} isCorrect - Whether the detection is correct
 */
function handleDetectionCorrectnessChange(idx, isCorrect) {
    if (idx >= 0 && idx < correctedDetections.length) {
        correctedDetections[idx].is_correct = isCorrect;
        if (isCorrect) {
            correctedDetections[idx].corrected_class = correctedDetections[idx].class_name;
        }
        displayCorrectedDetections(
            correctedDetections,
            handleDetectionCorrectnessChange,
            handleDetectionClassChange
        );
    }
}

/**
 * Handle changes to detection class
 * @param {number} idx - Index of the detection
 * @param {string} newClass - New class name
 */
function handleDetectionClassChange(idx, newClass) {
    if (idx >= 0 && idx < correctedDetections.length) {
        correctedDetections[idx].corrected_class = newClass;
    }
}

/**
 * Handle annotation submission with input sanitization and validation
 */
async function handleSubmitAnnotation() {
    if (!currentExample) return;

    const annotatorId = document.getElementById('annotator-id')?.value;
    const qualityScore = parseFloat(document.getElementById('quality-score')?.value || '1.0');
    const notes = document.getElementById('notes')?.value;

    if (!annotatorId) {
        showError('Please enter your annotator ID');
        return;
    }

    try {
        // Validate inputs before sanitization
        if (!validateAnnotatorId(annotatorId)) {
            showError('Invalid annotator ID. Only alphanumeric characters, underscores, and hyphens allowed (1-100 chars).');
            return;
        }

        // Validate corrected detections labels
        for (const detection of correctedDetections) {
            if (detection.class_name && !validateAnnotationLabel(detection.class_name)) {
                showError(`Invalid label "${detection.class_name}". Only alphanumeric characters, spaces, underscores, and hyphens allowed (1-50 chars).`);
                return;
            }
        }

        // Prepare form data for sanitization
        const formData = {
            corrected_detections: correctedDetections,
            annotator_id: annotatorId,
            quality_score: qualityScore,
            notes: notes || undefined
        };

        // Sanitize form data
        const sanitizedData = await sanitizeFormData(formData);

        await postAnnotation(currentExample.event_id, sanitizedData);
        showSuccess('Annotation submitted successfully!');
        clearCurrentExample();
        loadExamples();
    } catch (error) {
        console.error('Annotation submission error:', error);
        showError(error.message || 'Failed to submit annotation');
    }
}

/**
 * Handle skipping an example
 */
async function handleSkipExample() {
    if (!currentExample) return;

    if (confirm('Are you sure you want to skip this example?')) {
        try {
            await skipExample(currentExample.event_id);
            clearCurrentExample();
            loadExamples();
        } catch (error) {
            showError(error.message);
        }
    }
}

/**
 * Clear the current example and return to welcome state
 */
function clearCurrentExample() {
    currentExample = null;
    correctedDetections = [];
    toggleAnnotationPanel(false);
    clearAnnotationForm();
}

/**
 * Initialize the annotation canvas
 */
function initializeCanvas() {
    const canvas = document.getElementById('annotation-canvas');
    if (canvas) {
        // Set up canvas for future image annotation features
        const ctx = canvas.getContext('2d');
        if (ctx) {
            // Canvas is ready for future enhancements
            console.log('Annotation canvas initialized');
        }
    }
}

/**
 * Display a placeholder image on the canvas
 */
function displayPlaceholderImage() {
    const canvas = document.getElementById('annotation-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = 640;
    canvas.height = 480;

    // Draw placeholder
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = '#6c757d';
    ctx.font = '24px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Frame Preview Placeholder', canvas.width / 2, canvas.height / 2);
    ctx.font = '16px Arial';
    ctx.fillText('(Frame data integration pending)', canvas.width / 2, canvas.height / 2 + 30);
}

/**
 * Update WebSocket status indicator
 * @param {string} status - Status: 'connecting', 'connected', 'disconnected'
 * @param {string} [message] - Optional status message
 */
function updateWebSocketStatus(status, message = '') {
    const statusElement = document.getElementById('websocket-status');
    const textElement = document.getElementById('websocket-text');
    
    if (!statusElement || !textElement) return;
    
    // Remove existing status classes
    statusElement.classList.remove('connecting', 'connected', 'disconnected');
    
    // Add new status class
    statusElement.classList.add(status);
    
    // Update text
    const statusText = {
        connecting: message || 'Connecting...',
        connected: message || 'Live Updates Active',
        disconnected: message || 'Offline - No Live Updates'
    };
    
    textElement.textContent = statusText[status] || status;
}

/**
 * Handle new example received via WebSocket
 * @param {Object} example - The new example data
 */
function handleNewExample(example) {
    // Only add to current view if we're on the first page
    // (new examples appear at the top)
    if (currentPage === 1) {
        addExample(example, handleExampleClick);
        totalExamples++;
    } else {
        // Just update the total count and show notification
        totalExamples++;
        const pendingCountElement = document.getElementById('pending-count');
        if (pendingCountElement) {
            pendingCountElement.textContent = totalExamples.toString();
        }
        showSuccess(`New example received from ${example.camera_id || 'Unknown Camera'}`);
    }
}

/**
 * Handle WebSocket errors
 * @param {Error} error - The error that occurred
 */
function handleWebSocketError(error) {
    console.error('WebSocket connection error:', error);
    showError('Real-time updates temporarily unavailable. Please refresh the page.');
}

/**
 * Handle WebSocket status changes
 * @param {string} status - The new status
 * @param {string} [message] - Optional status message
 */
function handleWebSocketStatusChange(status, message) {
    updateWebSocketStatus(status, message);
}

/**
 * Handle page change in pagination
 * @param {number} page - The new page number
 */
function handlePageChange(page) {
    if (page !== currentPage && page > 0) {
        loadExamples(page);
    }
}

// Initialize the application when the DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}

/**
 * UI Module - Handles all DOM manipulation with XSS prevention
 * Uses createElement and textContent instead of innerHTML for user data
 */

import { 
    sanitizeText, 
    setSafeTextContent, 
    validateAnnotationLabel,
    validateAnnotatorId,
    validateNotes,
    initializeSanitization 
} from './sanitize.js';

// Initialize sanitization on module load
let sanitizationReady = false;
initializeSanitization().then(ready => {
    sanitizationReady = ready;
});

/**
 * Display an error message to the user (XSS-safe)
 * @param {string} message - The error message to display
 */
export async function showError(message) {
    // Remove any existing error messages
    const existingError = document.querySelector('.error-alert');
    if (existingError) {
        existingError.remove();
    }

    // Sanitize the error message
    const sanitizedMessage = await sanitizeText(message);

    // Create error alert element
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show error-alert';
    errorDiv.setAttribute('role', 'alert');

    // Create error message text (safe from XSS)
    const errorText = document.createElement('span');
    setSafeTextContent(errorText, sanitizedMessage);

    // Create close button
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    closeButton.setAttribute('aria-label', 'Close');

    errorDiv.appendChild(errorText);
    errorDiv.appendChild(closeButton);

    // Insert at the top of the container
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(errorDiv, container.firstChild);
    }

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 5000);
}

/**
 * Display a success message to the user (XSS-safe)
 * @param {string} message - The success message to display
 */
export async function showSuccess(message) {
    // Remove any existing success messages
    const existingSuccess = document.querySelector('.success-alert');
    if (existingSuccess) {
        existingSuccess.remove();
    }

    // Sanitize the success message
    const sanitizedMessage = await sanitizeText(message);

    // Create success alert element
    const successDiv = document.createElement('div');
    successDiv.className = 'alert alert-success alert-dismissible fade show success-alert';
    successDiv.setAttribute('role', 'alert');    // Create success message text (safe from XSS)
    const successText = document.createElement('span');
    setSafeTextContent(successText, sanitizedMessage);

    // Create close button
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    closeButton.setAttribute('aria-label', 'Close');

    successDiv.appendChild(successText);
    successDiv.appendChild(closeButton);

    // Insert at the top of the container
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(successDiv, container.firstChild);
    }

    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (successDiv.parentNode) {
            successDiv.remove();
        }
    }, 3000);
}

/**
 * Render the list of pending examples with pagination support (XSS-safe)
 * @param {Array} examples - Array of example objects
 * @param {number} total - Total count of examples
 * @param {number} currentPage - Current page number
 * @param {number} pageSize - Number of items per page
 * @param {Function} onExampleClick - Callback when example is clicked
 * @param {Function} onPageChange - Callback when page changes
 */
export async function renderExamples(examples, total, currentPage, pageSize, onExampleClick, onPageChange) {
    // Update pending count safely
    const pendingCountElement = document.getElementById('pending-count');
    if (pendingCountElement) {
        pendingCountElement.textContent = total.toString();
    }

    const examplesList = document.getElementById('examples-list');
    if (!examplesList) return;    // Clear existing examples (safe - no user content)
    examplesList.innerHTML = '';

    if (examples.length === 0) {
        const emptyMessage = document.createElement('p');
        emptyMessage.className = 'text-muted text-center';
        emptyMessage.textContent = 'No pending examples';
        examplesList.appendChild(emptyMessage);
        renderPagination(0, currentPage, pageSize, onPageChange);
        return;
    }

    // Use DocumentFragment for efficient DOM updates
    const fragment = document.createDocumentFragment();
    
    // Process examples asynchronously with sanitization
    for (const example of examples) {
        try {
            const card = await createExampleCard(example, onExampleClick);
            fragment.appendChild(card);        } catch (error) {
            console.error('Error creating example card:', error);
            // Create a safe fallback card
            const errorCard = document.createElement('div');
            errorCard.className = 'card example-card mb-2 bg-light';
            
            const cardBody = document.createElement('div');
            cardBody.className = 'card-body';
            
            const errorText = document.createElement('p');
            errorText.className = 'text-muted';
            setSafeTextContent(errorText, 'Error loading example');
            
            cardBody.appendChild(errorText);
            errorCard.appendChild(cardBody);
            fragment.appendChild(errorCard);
        }
    }
    
    // Single DOM append for better performance
    examplesList.appendChild(fragment);
    
    // Render pagination controls
    renderPagination(total, currentPage, pageSize, onPageChange);
}

/**
 * Create an example card element (XSS-safe)
 * @param {Object} example - The example data
 * @param {Function} onExampleClick - Callback when card is clicked
 * @returns {Promise<HTMLElement>} The card element
 */
async function createExampleCard(example, onExampleClick) {
    const card = document.createElement('div');
    card.className = 'card example-card mb-2';
    card.style.cursor = 'pointer';
    
    // Add click handler
    card.addEventListener('click', () => onExampleClick(example.event_id));

    const cardBody = document.createElement('div');
    cardBody.className = 'card-body p-3';

    // Create header row
    const headerRow = document.createElement('div');
    headerRow.className = 'd-flex justify-content-between align-items-start';

    const leftSection = document.createElement('div');
    
    const title = document.createElement('h6');
    title.className = 'card-title mb-1';
    // Sanitize camera_id before display
    const sanitizedCameraId = await sanitizeText(example.camera_id || 'Unknown Camera');
    setSafeTextContent(title, sanitizedCameraId);

    const timestamp = document.createElement('small');
    timestamp.className = 'text-muted';
    timestamp.textContent = new Date(example.timestamp).toLocaleString();

    leftSection.appendChild(title);
    leftSection.appendChild(timestamp);

    const badge = document.createElement('span');
    badge.className = 'badge bg-warning text-dark';
    badge.textContent = getReason(example.reason || '');

    headerRow.appendChild(leftSection);
    headerRow.appendChild(badge);

    // Create confidence scores section
    const confidenceSection = document.createElement('div');
    confidenceSection.className = 'mt-2';

    if (example.confidence_scores) {
        Object.entries(example.confidence_scores).forEach(([cls, conf]) => {
            const confidenceBadge = document.createElement('span');
            confidenceBadge.className = `badge ${conf < 0.5 ? 'bg-danger' : 'bg-warning'} confidence-badge me-1`;
            confidenceBadge.textContent = `${cls}: ${conf.toFixed(2)}`;
            confidenceSection.appendChild(confidenceBadge);
        });
    }

    cardBody.appendChild(headerRow);
    cardBody.appendChild(confidenceSection);
    card.appendChild(cardBody);

    return card;
}

/**
 * Get a shortened reason text
 * @param {string} reason - The full reason text
 * @returns {string} Shortened reason
 */
function getReason(reason) {
    if (reason.includes('Low confidence')) {
        return 'Low Conf';
    }
    return reason.length > 10 ? reason.substring(0, 10) + '...' : reason;
}

/**
 * Display original detections in the UI
 * @param {Array} detections - Array of detection objects
 */
export function displayOriginalDetections(detections) {
    const container = document.getElementById('original-detections');
    if (!container) return;

    // Clear container (safe - no user content)
    container.innerHTML = '';

    detections.forEach((det) => {
        const detDiv = document.createElement('div');
        detDiv.className = 'card mb-2';

        const cardBody = document.createElement('div');
        cardBody.className = 'card-body p-2';

        const headerRow = document.createElement('div');
        headerRow.className = 'd-flex justify-content-between';

        const className = document.createElement('strong');
        className.textContent = det.class_name || 'Unknown';

        const confidenceBadge = document.createElement('span');
        confidenceBadge.className = `badge ${det.confidence < 0.5 ? 'bg-danger' : 'bg-warning'}`;
        confidenceBadge.textContent = det.confidence ? det.confidence.toFixed(3) : 'N/A';

        headerRow.appendChild(className);
        headerRow.appendChild(confidenceBadge);

        const bboxInfo = document.createElement('small');
        bboxInfo.className = 'text-muted';
        if (det.bbox) {
            bboxInfo.textContent = `BBox: [${det.bbox.x1.toFixed(1)}, ${det.bbox.y1.toFixed(1)}, ${det.bbox.x2.toFixed(1)}, ${det.bbox.y2.toFixed(1)}]`;
        } else {
            bboxInfo.textContent = 'BBox: N/A';
        }

        cardBody.appendChild(headerRow);
        cardBody.appendChild(bboxInfo);
        detDiv.appendChild(cardBody);
        container.appendChild(detDiv);
    });
}

/**
 * Display corrected detections in the UI
 * @param {Array} correctedDetections - Array of corrected detection objects
 * @param {Function} onCorrectnessChange - Callback when correctness changes
 * @param {Function} onClassChange - Callback when class changes
 */
export function displayCorrectedDetections(correctedDetections, onCorrectnessChange, onClassChange) {
    const container = document.getElementById('corrected-detections');
    if (!container) return;

    // Clear container (safe - no user content)
    container.innerHTML = '';

    correctedDetections.forEach((det, idx) => {
        const detDiv = document.createElement('div');
        detDiv.className = 'card mb-2';

        const cardBody = document.createElement('div');
        cardBody.className = 'card-body p-2';

        // Create checkbox section
        const checkSection = document.createElement('div');
        checkSection.className = 'form-check';

        const checkbox = document.createElement('input');
        checkbox.className = 'form-check-input';
        checkbox.type = 'checkbox';
        checkbox.checked = det.is_correct;
        checkbox.addEventListener('change', (e) => onCorrectnessChange(idx, e.target.checked));

        const label = document.createElement('label');
        label.className = 'form-check-label';
        
        const labelStrong = document.createElement('strong');
        labelStrong.textContent = det.class_name || 'Unknown';
        label.appendChild(labelStrong);

        checkSection.appendChild(checkbox);
        checkSection.appendChild(label);

        // Create select section
        const selectSection = document.createElement('div');
        selectSection.className = 'mt-2';

        const select = document.createElement('select');
        select.className = 'form-control form-control-sm';
        select.disabled = det.is_correct;
        select.addEventListener('change', (e) => onClassChange(idx, e.target.value));

        const options = ['person', 'vehicle', 'face', 'object'];
        options.forEach(optionValue => {
            const option = document.createElement('option');
            option.value = optionValue;
            option.textContent = optionValue.charAt(0).toUpperCase() + optionValue.slice(1);
            option.selected = det.corrected_class === optionValue;
            select.appendChild(option);
        });

        selectSection.appendChild(select);

        cardBody.appendChild(checkSection);
        cardBody.appendChild(selectSection);
        detDiv.appendChild(cardBody);
        container.appendChild(detDiv);
    });
}

/**
 * Show/hide annotation panels
 * @param {boolean} showAnnotation - Whether to show annotation panel
 */
export function toggleAnnotationPanel(showAnnotation) {
    const welcomePanel = document.getElementById('welcome-panel');
    const annotationPanel = document.getElementById('annotation-panel');

    if (welcomePanel) {
        welcomePanel.style.display = showAnnotation ? 'none' : 'block';
    }
    if (annotationPanel) {
        annotationPanel.style.display = showAnnotation ? 'block' : 'none';
    }
}

/**
 * Update the current example title
 * @param {string} cameraId - Camera ID
 * @param {string} timestamp - Timestamp
 */
export function updateExampleTitle(cameraId, timestamp) {
    const titleElement = document.getElementById('current-example-title');
    if (titleElement) {
        const formattedTimestamp = new Date(timestamp).toLocaleString();
        titleElement.textContent = `${cameraId} - ${formattedTimestamp}`;
    }
}

/**
 * Clear the annotation form
 */
export function clearAnnotationForm() {
    const form = document.getElementById('annotation-form');
    if (form) {
        form.reset();
    }
}

/**
 * Render pagination controls
 * @param {number} total - Total number of items
 * @param {number} currentPage - Current page number
 * @param {number} pageSize - Number of items per page
 * @param {Function} onPageChange - Callback when page changes
 */
function renderPagination(total, currentPage, pageSize, onPageChange) {
    const paginationContainer = document.getElementById('pagination-container');
    if (!paginationContainer) return;    // Clear existing pagination (safe - no user content)
    paginationContainer.innerHTML = '';

    if (total <= pageSize) {
        return; // No pagination needed
    }

    const totalPages = Math.ceil(total / pageSize);
    
    // Create pagination wrapper
    const nav = document.createElement('nav');
    nav.setAttribute('aria-label', 'Examples pagination');
    
    const ul = document.createElement('ul');
    ul.className = 'pagination pagination-sm justify-content-center';

    // Previous button
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage <= 1 ? 'disabled' : ''}`;
    
    const prevLink = document.createElement('button');
    prevLink.className = 'page-link';
    prevLink.textContent = 'Previous';
    prevLink.disabled = currentPage <= 1;
    prevLink.addEventListener('click', () => {
        if (currentPage > 1) {
            onPageChange(currentPage - 1);
        }
    });
    
    prevLi.appendChild(prevLink);
    ul.appendChild(prevLi);

    // Page info
    const pageInfoLi = document.createElement('li');
    pageInfoLi.className = 'page-item active';
    
    const pageInfoSpan = document.createElement('span');
    pageInfoSpan.className = 'page-link';
    pageInfoSpan.textContent = `Page ${currentPage} of ${totalPages}`;
    
    pageInfoLi.appendChild(pageInfoSpan);
    ul.appendChild(pageInfoLi);

    // Next button
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage >= totalPages ? 'disabled' : ''}`;
    
    const nextLink = document.createElement('button');
    nextLink.className = 'page-link';
    nextLink.textContent = 'Next';
    nextLink.disabled = currentPage >= totalPages;
    nextLink.addEventListener('click', () => {
        if (currentPage < totalPages) {
            onPageChange(currentPage + 1);
        }
    });
    
    nextLi.appendChild(nextLink);
    ul.appendChild(nextLi);

    nav.appendChild(ul);
    paginationContainer.appendChild(nav);
}

/**
 * Add a new example to the list incrementally (for real-time updates)
 * @param {Object} example - The new example to add
 * @param {Function} onExampleClick - Callback when example is clicked
 */
export function addExample(example, onExampleClick) {
    const examplesList = document.getElementById('examples-list');
    if (!examplesList) return;

    // Remove "no examples" message if it exists
    const emptyMessage = examplesList.querySelector('.text-muted');
    if (emptyMessage) {
        emptyMessage.remove();
    }

    // Create new example card
    const card = createExampleCard(example, onExampleClick);
    
    // Add to the top of the list with smooth animation
    card.style.opacity = '0';
    card.style.transform = 'translateY(-20px)';
    
    examplesList.insertBefore(card, examplesList.firstChild);
    
    // Animate in
    requestAnimationFrame(() => {
        card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        card.style.opacity = '1';
        card.style.transform = 'translateY(0)';
    });

    // Update pending count
    const pendingCountElement = document.getElementById('pending-count');
    if (pendingCountElement) {
        const currentCount = parseInt(pendingCountElement.textContent || '0');
        pendingCountElement.textContent = (currentCount + 1).toString();
    }

    // Show notification
    showInfo(`New example received from ${example.camera_id || 'Unknown Camera'}`);
}

/**
 * Display an info message to the user
 * @param {string} message - The info message to display
 */
export function showInfo(message) {
    // Remove any existing info messages
    const existingInfo = document.querySelector('.info-alert');
    if (existingInfo) {
        existingInfo.remove();
    }

    // Create info alert element
    const infoDiv = document.createElement('div');
    infoDiv.className = 'alert alert-info alert-dismissible fade show info-alert';
    infoDiv.setAttribute('role', 'alert');

    // Create info message text
    const infoText = document.createElement('span');
    infoText.textContent = message;

    // Create close button
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    closeButton.setAttribute('aria-label', 'Close');    infoDiv.appendChild(infoText);
    infoDiv.appendChild(closeButton);

    // Insert at the top of the container
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(infoDiv, container.firstChild);
    }

    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (infoDiv.parentNode) {
            infoDiv.remove();
        }
    }, 3000);
}

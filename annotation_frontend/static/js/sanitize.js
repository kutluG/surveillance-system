/**
 * XSS Sanitization Utility
 * Provides safe HTML sanitization and text validation for user inputs
 */

// DOMPurify configuration for strict sanitization
const DOMPURIFY_CONFIG = {
    ALLOWED_TAGS: [], // No HTML tags allowed for strict text-only sanitization
    ALLOWED_ATTR: [],
    ALLOW_DATA_ATTR: false,
    FORBID_TAGS: ['script', 'object', 'embed', 'link', 'style', 'iframe'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
    KEEP_CONTENT: true, // Keep text content but strip tags
    RETURN_DOM: false,
    RETURN_DOM_FRAGMENT: false,
    RETURN_DOM_IMPORT: false
};

/**
 * Load DOMPurify from CDN if not already loaded
 * @returns {Promise<Object>} DOMPurify instance
 */
async function loadDOMPurify() {
    if (window.DOMPurify) {
        return window.DOMPurify;
    }

    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/dompurify@3.0.5/dist/purify.min.js';
        script.integrity = 'sha384-FkTM/30xX+uctsiR/mTpNKRze83/t/HW8F/0z9QpQ7v7Q8sY4Cf8F/+8A8T8f8M8X';
        script.crossOrigin = 'anonymous';
        script.onload = () => {
            if (window.DOMPurify) {
                resolve(window.DOMPurify);
            } else {
                reject(new Error('Failed to load DOMPurify'));
            }
        };
        script.onerror = () => reject(new Error('Failed to load DOMPurify script'));
        document.head.appendChild(script);
    });
}

/**
 * Sanitize text input by removing all HTML tags and dangerous content
 * @param {string} input - User input to sanitize
 * @param {Object} options - Sanitization options
 * @returns {string} Sanitized text
 */
export async function sanitizeText(input, options = {}) {
    if (typeof input !== 'string') {
        return '';
    }

    // Basic string validation
    if (input.length === 0) {
        return '';
    }

    try {
        const DOMPurify = await loadDOMPurify();
        
        // Use DOMPurify for HTML sanitization with strict config
        const sanitized = DOMPurify.sanitize(input, {
            ...DOMPURIFY_CONFIG,
            ...options
        });

        // Additional manual checks for common XSS patterns
        return sanitized
            .replace(/javascript:/gi, '') // Remove javascript: protocols
            .replace(/vbscript:/gi, '')   // Remove vbscript: protocols
            .replace(/data:/gi, '')       // Remove data: protocols
            .replace(/on\w+=/gi, '')      // Remove event handlers
            .trim();

    } catch (error) {
        console.error('Sanitization error:', error);
        // Fallback to basic text cleaning if DOMPurify fails
        return input
            .replace(/<[^>]*>/g, '')      // Remove all HTML tags
            .replace(/[<>'"&]/g, '')      // Remove dangerous characters
            .trim();
    }
}

/**
 * Validate annotation label against allowed pattern
 * @param {string} label - Label to validate
 * @returns {boolean} True if valid
 */
export function validateAnnotationLabel(label) {
    if (typeof label !== 'string') {
        return false;
    }

    // Must match backend validation: only alphanumeric, spaces, underscores, hyphens
    const LABEL_PATTERN = /^[A-Za-z0-9 _-]{1,50}$/;
    return LABEL_PATTERN.test(label);
}

/**
 * Validate annotator ID
 * @param {string} annotatorId - Annotator ID to validate
 * @returns {boolean} True if valid
 */
export function validateAnnotatorId(annotatorId) {
    if (typeof annotatorId !== 'string') {
        return false;
    }

    // Must be alphanumeric with underscores and hyphens, 1-100 chars
    const ID_PATTERN = /^[A-Za-z0-9_-]{1,100}$/;
    return ID_PATTERN.test(annotatorId);
}

/**
 * Validate notes field
 * @param {string} notes - Notes to validate
 * @returns {boolean} True if valid
 */
export function validateNotes(notes) {
    if (!notes) {
        return true; // Notes are optional
    }

    if (typeof notes !== 'string') {
        return false;
    }

    // Max 1000 characters, no script tags
    return notes.length <= 1000 && 
           !/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi.test(notes);
}

/**
 * Sanitize and validate form input
 * @param {Object} formData - Form data object
 * @returns {Promise<Object>} Sanitized and validated form data
 */
export async function sanitizeFormData(formData) {
    const sanitized = {};

    for (const [key, value] of Object.entries(formData)) {
        if (typeof value === 'string') {
            sanitized[key] = await sanitizeText(value);
        } else {
            sanitized[key] = value;
        }
    }

    // Validate specific fields
    if (sanitized.label && !validateAnnotationLabel(sanitized.label)) {
        throw new Error('Invalid label format. Only alphanumeric characters, spaces, underscores, and hyphens allowed (1-50 chars).');
    }

    if (sanitized.annotator_id && !validateAnnotatorId(sanitized.annotator_id)) {
        throw new Error('Invalid annotator ID format. Only alphanumeric characters, underscores, and hyphens allowed (1-100 chars).');
    }

    if (sanitized.notes && !validateNotes(sanitized.notes)) {
        throw new Error('Invalid notes. Maximum 1000 characters, no script tags allowed.');
    }

    return sanitized;
}

/**
 * Safe innerHTML alternative - creates text nodes instead of parsing HTML
 * @param {HTMLElement} element - Target element
 * @param {string} content - Content to set (will be treated as text)
 */
export function setSafeTextContent(element, content) {
    if (!element || typeof content !== 'string') {
        return;
    }

    // Clear existing content
    element.textContent = '';
    
    // Create text node to prevent HTML parsing
    const textNode = document.createTextNode(content);
    element.appendChild(textNode);
}

/**
 * Safe HTML rendering with DOMPurify (for controlled HTML content)
 * @param {HTMLElement} element - Target element
 * @param {string} htmlContent - HTML content to sanitize and render
 * @param {Object} options - DOMPurify options
 */
export async function setSafeHTML(element, htmlContent, options = {}) {
    if (!element || typeof htmlContent !== 'string') {
        return;
    }

    try {
        const DOMPurify = await loadDOMPurify();
        
        const sanitizedHTML = DOMPurify.sanitize(htmlContent, {
            ALLOWED_TAGS: ['b', 'i', 'strong', 'em', 'span', 'div', 'p'],
            ALLOWED_ATTR: ['class'],
            ...options
        });

        element.innerHTML = sanitizedHTML;
    } catch (error) {
        console.error('Safe HTML rendering error:', error);
        // Fallback to text content
        element.textContent = htmlContent.replace(/<[^>]*>/g, '');
    }
}

/**
 * Initialize sanitization module
 */
export async function initializeSanitization() {
    try {
        await loadDOMPurify();
        console.log('✅ DOMPurify loaded successfully');
        return true;
    } catch (error) {
        console.warn('⚠️ Failed to load DOMPurify, using fallback sanitization:', error);
        return false;
    }
}

// Export validation patterns for use in other modules
export const VALIDATION_PATTERNS = {
    LABEL: /^[A-Za-z0-9 _-]{1,50}$/,
    ANNOTATOR_ID: /^[A-Za-z0-9_-]{1,100}$/,
    CAMERA_ID: /^[A-Za-z0-9_-]{1,100}$/
};

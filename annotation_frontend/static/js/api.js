/**
 * API Module - Handles all API communication
 * Uses configurable base URL, JWT authentication, and CSRF protection
 */

// Global variables for authentication and CSRF
let authToken = null;
let csrfToken = null;

/**
 * Get the API base URL from global config
 * @returns {string} The base URL for API calls
 */
function getApiBaseUrl() {
    // Handle both browser and test environments
    const baseUrl = (typeof window !== 'undefined' && window.API_BASE_URL) ? window.API_BASE_URL : '';
    return baseUrl;
}

/**
 * Get the API base path from global config
 * @returns {string} The base path for API versioning
 */
function getApiBasePath() {
    // Handle both browser and test environments
    const basePath = (typeof window !== 'undefined' && window.API_BASE_PATH) ? window.API_BASE_PATH : '/api/v1';
    return basePath;
}

/**
 * Get the WebSocket base path from global config
 * @returns {string} The base path for WebSocket versioning
 */
function getWsBasePath() {
    // Handle both browser and test environments
    const wsBasePath = (typeof window !== 'undefined' && window.WS_BASE_PATH) ? window.WS_BASE_PATH : '/ws/v1';
    return wsBasePath;
}

/**
 * Get CSRF token from cookie
 * @returns {string|null} CSRF token from cookie
 */
function getCsrfTokenFromCookie() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken' || name === 'csrf_token') {
            return decodeURIComponent(value);
        }
    }
    return null;
}

/**
 * Initialize CSRF token by fetching it from the server
 * @returns {Promise<void>}
 */
async function initializeCsrfToken() {
    try {
        const response = await fetch(`${getApiBaseUrl()}${getApiBasePath()}/csrf-token`, {
            method: 'GET',
            credentials: 'include'  // Include cookies
        });
        
        if (response.ok) {
            const data = await response.json();
            csrfToken = data.csrf_token;
            console.log('CSRF token initialized successfully');
        } else {
            console.error('Failed to fetch CSRF token:', response.status);
        }
    } catch (error) {
        console.error('Error initializing CSRF token:', error);
    }
}

/**
 * Get authentication headers
 * @returns {Object} Headers object with authentication and CSRF tokens
 */
function getAuthHeaders() {
    const headers = {
        'Content-Type': 'application/json',
    };
    
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    
    if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
    }
    
    return headers;
}

/**
 * Set authentication token
 * @param {string} token - JWT token
 */
export function setAuthToken(token) {
    authToken = token;
    if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', token);
    }
}

/**
 * Get authentication token
 * @returns {string|null} JWT token
 */
export function getAuthToken() {
    if (authToken) return authToken;
    
    if (typeof window !== 'undefined') {
        authToken = localStorage.getItem('auth_token');
    }
    
    return authToken;
}

/**
 * Clear authentication token
 */
export function clearAuthToken() {
    authToken = null;
    if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
    }
}

/**
 * Initialize API module
 * @returns {Promise<void>}
 */
export async function initializeApi() {
    // Load auth token from storage
    getAuthToken();
    
    // Initialize CSRF token
    await initializeCsrfToken();
}

/**
 * Handle fetch errors consistently
 * @param {Response} response - The fetch response
 * @returns {Promise<any>} The parsed JSON response
 * @throws {Error} If response is not ok
 */
async function handleFetchResponse(response) {
    if (response.status === 401) {
        clearAuthToken();
        // Redirect to login if unauthorized
        if (typeof window !== 'undefined') {
            window.location.href = '/login';
        }
        throw new Error('Authentication required. Please log in.');
    }
    
    if (response.status === 403) {
        throw new Error('Access forbidden. You do not have permission for this action.');
    }
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Login with username and password
 * @param {string} username - Username
 * @param {string} password - Password
 * @returns {Promise<Object>} Login response with token
 */
export async function login(username, password) {
    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        
        const response = await fetch(`${getApiBaseUrl()}${getApiBasePath()}/login`, {
            method: 'POST',
            body: formData
        });
        
        const data = await handleFetchResponse(response);
        setAuthToken(data.access_token);
        return data;
    } catch (error) {
        console.error('Login failed:', error);
        throw new Error('Login failed. Please check your credentials.');
    }
}

/**
 * Fetch the list of pending annotation examples with pagination support
 * @param {number} [page=1] - Page number (1-based)
 * @param {number} [size=10] - Number of items per page
 * @returns {Promise<Object>} Object containing examples array, total count, and pagination info
 * @throws {Error} If fetch fails or response is invalid
 */
export async function fetchExamples(page = 1, size = 10) {
    try {
        const url = new URL(`${getApiBaseUrl()}${getApiBasePath()}/examples`);
        url.searchParams.append('page', page.toString());
        url.searchParams.append('size', size.toString());
        
        const response = await fetch(url.toString(), {
            method: 'GET',
            headers: getAuthHeaders(),
            credentials: 'same-origin'
        });
        return await handleFetchResponse(response);
    } catch (error) {
        console.error('Failed to fetch examples:', error);
        throw new Error('Failed to load examples. Please check your network connection.');
    }
}

/**
 * Fetch a specific annotation example by ID
 * @param {string} eventId - The event ID to fetch
 * @returns {Promise<Object>} The example data
 * @throws {Error} If fetch fails or response is invalid
 */
export async function fetchExample(eventId) {
    try {
        const response = await fetch(`${getApiBaseUrl()}${getApiBasePath()}/examples/${eventId}`, {
            method: 'GET',
            headers: getAuthHeaders(),
            credentials: 'same-origin'
        });
        return await handleFetchResponse(response);
    } catch (error) {
        console.error('Failed to fetch example:', error);
        throw new Error('Failed to load example. Please try again.');
    }
}

/**
 * Submit an annotation for a specific example
 * @param {string} eventId - The event ID to annotate
 * @param {Object} annotationData - The annotation data
 * @param {Array} annotationData.corrected_detections - Corrected detections
 * @param {string} annotationData.annotator_id - Annotator ID
 * @param {number} annotationData.quality_score - Quality score
 * @param {string} [annotationData.notes] - Optional notes
 * @returns {Promise<Object>} The response data
 * @throws {Error} If submission fails
 */
export async function postAnnotation(eventId, annotationData) {
    try {
        const response = await fetch(`${getApiBaseUrl()}${getApiBasePath()}/examples/${eventId}/label`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(annotationData),
            credentials: 'include'  // Include cookies for CSRF
        });
        return await handleFetchResponse(response);
    } catch (error) {
        console.error('Failed to submit annotation:', error);
        throw new Error('Failed to submit annotation. Please try again.');
    }
}

/**
 * Skip an annotation example
 * @param {string} eventId - The event ID to skip
 * @returns {Promise<Object>} The response data
 * @throws {Error} If skip fails
 */
export async function skipExample(eventId) {
    try {
        const response = await fetch(`${getApiBaseUrl()}${getApiBasePath()}/examples/${eventId}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
            credentials: 'same-origin'
        });
        return await handleFetchResponse(response);
    } catch (error) {
        console.error('Failed to skip example:', error);
        throw new Error('Failed to skip example. Please try again.');
    }
}

/**
 * WebSocket connection for real-time updates
 */
let websocket = null;
let websocketReconnectAttempts = 0;
const maxReconnectAttempts = 5;
const reconnectDelay = 1000; // Start with 1 second

/**
 * Connect to WebSocket for real-time updates
 * @param {Function} onNewExample - Callback when new example is received
 * @param {Function} onError - Callback when error occurs
 * @param {Function} onStatusChange - Callback when connection status changes
 * @returns {WebSocket} The WebSocket connection
 */
export function connectWebSocket(onNewExample, onError, onStatusChange) {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        return websocket;
    }    try {
        const baseUrl = getApiBaseUrl();
        const wsBasePath = getWsBasePath();
        const wsUrl = baseUrl.replace(/^http/, 'ws') + wsBasePath + '/examples';
        
        websocket = new WebSocket(wsUrl);

        websocket.onopen = function(event) {
            console.log('WebSocket connected');
            websocketReconnectAttempts = 0;
            if (onStatusChange) {
                onStatusChange('connected');
            }
        };

        websocket.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'new_example' && data.example) {
                    onNewExample(data.example);
                }
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        websocket.onerror = function(error) {
            console.error('WebSocket error:', error);
            if (onStatusChange) {
                onStatusChange('disconnected', 'Connection error');
            }
            if (onError) {
                onError(error);
            }
        };

        websocket.onclose = function(event) {
            console.log('WebSocket disconnected');
            websocket = null;
            if (onStatusChange) {
                onStatusChange('disconnected');
            }
            
            // Attempt to reconnect with exponential backoff
            if (websocketReconnectAttempts < maxReconnectAttempts) {
                const delay = reconnectDelay * Math.pow(2, websocketReconnectAttempts);
                websocketReconnectAttempts++;
                
                if (onStatusChange) {
                    onStatusChange('connecting', `Reconnecting in ${Math.ceil(delay/1000)}s...`);
                }
                
                setTimeout(() => {
                    console.log(`Attempting WebSocket reconnection (${websocketReconnectAttempts}/${maxReconnectAttempts})`);
                    connectWebSocket(onNewExample, onError, onStatusChange);
                }, delay);
            }
        };

        return websocket;
    } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        if (onStatusChange) {
            onStatusChange('disconnected', 'Failed to connect');
        }
        if (onError) {
            onError(error);
        }
        return null;
    }
}

/**
 * Disconnect WebSocket connection
 */
export function disconnectWebSocket() {
    if (websocket) {
        websocket.close();
        websocket = null;
    }
}

/**
 * Check if WebSocket is connected
 * @returns {boolean} True if WebSocket is connected
 */
export function isWebSocketConnected() {
    return websocket && websocket.readyState === WebSocket.OPEN;
}

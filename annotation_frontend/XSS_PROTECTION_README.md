# XSS Protection Implementation

## Overview
This implementation provides comprehensive XSS (Cross-Site Scripting) protection for the annotation frontend service, covering both frontend JavaScript and backend Python validation.

## Frontend Protection (`static/js/`)

### `sanitize.js`
- **DOMPurify Integration**: Loads DOMPurify from CDN for robust HTML sanitization
- **Strict Configuration**: Removes all HTML tags and dangerous content by default
- **Validation Functions**: Provides frontend validation for labels, annotator IDs, and notes
- **Safe DOM Manipulation**: `setSafeTextContent()` uses `textContent` instead of `innerHTML`

### `ui.js` 
- **Safe innerHTML Usage**: All `innerHTML` usage is now limited to clearing containers (safe)
- **XSS-Safe Error Handling**: Uses `setSafeTextContent()` for displaying user data
- **Sanitization Integration**: Imports and uses sanitization functions throughout

## Backend Protection (`schemas.py`)

### Input Validation
- **Label Pattern**: `^[A-Za-z0-9 _-]{1,50}$` - Only alphanumeric, spaces, underscores, hyphens
- **Annotator ID Pattern**: `^[A-Za-z0-9_-]{1,100}$` - Alphanumeric, underscores, hyphens only
- **Notes Validation**: Max 1000 chars, blocks script tags and event handlers
- **HTML Entity Escaping**: All text fields are HTML-escaped using `html.escape()`

### Dangerous Pattern Detection
The validators detect and block:
- `<script>` tags (case-insensitive)
- Event handlers (`onclick`, `onload`, etc.)
- JavaScript protocols (`javascript:`, `vbscript:`)
- HTML tags (`<.*>`)
- Iframe, object, embed tags
- Data URLs with scripts
- HTML entities that might bypass validation

## Security Features

### Defense in Depth
1. **Frontend Sanitization**: DOMPurify removes malicious content
2. **Input Validation**: Strict regex patterns limit allowed characters
3. **Backend Validation**: Pydantic validators with HTML escaping
4. **Pattern Detection**: Multiple layers of dangerous content detection

### Length Limits
- Labels: 1-50 characters
- Annotator IDs: 1-100 characters  
- Notes: 0-1000 characters
- Example IDs: 1-255 characters

### Safe DOM Practices
- Uses `textContent` instead of `innerHTML` for user data
- Creates elements programmatically instead of parsing HTML strings
- Validates data before rendering

## Testing (`tests/`)

### Backend Tests (`test_xss_sanitize.py`)
- **XSS Payload Testing**: 10+ different XSS attack vectors
- **Valid Input Testing**: Ensures legitimate data is accepted
- **Pattern Enforcement**: Tests regex validation thoroughly
- **Edge Case Testing**: Empty inputs, length limits, special characters
- **Performance Testing**: Ensures sanitization doesn't create bottlenecks

### Frontend Tests (`sanitization.test.js`)
- **DOMPurify Integration**: Tests script tag removal
- **Safe DOM Manipulation**: Validates `setSafeTextContent` behavior
- **Form Validation**: Tests client-side validation functions
- **Integration Testing**: End-to-end XSS protection flow

## Usage Examples

### Valid Inputs ✅
```python
# These inputs are accepted
AnnotationRequest(
    example_id="example_123",
    bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
    label="person-walking",      # Valid: alphanumeric + underscore + hyphen
    annotator_id="user_123",     # Valid: alphanumeric + underscore
    notes="Clear detection"      # Valid: normal text
)
```

### Blocked Attacks 🛡️
```python
# These inputs are rejected with ValidationError
AnnotationRequest(
    label="<script>alert('xss')</script>",  # ❌ Script tag
    annotator_id="user@domain.com",         # ❌ Invalid characters
    notes="<iframe src='evil.com'></iframe>" # ❌ Dangerous HTML
)
```

## Running Tests

### Backend Tests
```bash
cd annotation_frontend
python -m pytest tests/test_xss_sanitize.py -v
```

### Frontend Tests
```bash
cd annotation_frontend/tests
npm install
npm test
```

### Demonstration
```bash
cd annotation_frontend
python demo_xss_protection.py
```

## Configuration

### DOMPurify Settings
```javascript
const DOMPURIFY_CONFIG = {
    ALLOWED_TAGS: [],        // No HTML tags allowed
    ALLOWED_ATTR: [],        // No attributes allowed
    FORBID_TAGS: ['script', 'object', 'embed', 'link', 'style', 'iframe'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover'],
    KEEP_CONTENT: true       // Keep text content, strip tags
};
```

### Validation Patterns
```python
LABEL_PATTERN = r'^[A-Za-z0-9 _-]{1,50}$'
ANNOTATOR_ID_PATTERN = r'^[A-Za-z0-9_-]{1,100}$'
EXAMPLE_ID_PATTERN = r'^[A-Za-z0-9._-]{1,255}$'
```

## Security Checklist

- [x] All user input is validated with strict patterns
- [x] HTML entities are escaped in all text fields
- [x] Script tags are detected and blocked
- [x] Event handlers are detected and blocked
- [x] Dangerous protocols (javascript:, data:) are blocked
- [x] Frontend uses textContent instead of innerHTML for user data
- [x] DOMPurify provides additional sanitization layer
- [x] Length limits prevent DoS attacks
- [x] Comprehensive test coverage for all attack vectors
- [x] Regular expression patterns prevent ReDoS attacks

## Performance Considerations

- **Efficient Validation**: Regex patterns are optimized for performance
- **Cached DOMPurify**: Library is loaded once and reused
- **Minimal DOM Manipulation**: Uses efficient DOM creation methods
- **Lazy Loading**: DOMPurify is loaded asynchronously when needed

## Future Enhancements

- **Content Security Policy (CSP)**: Add CSP headers for additional protection
- **Rate Limiting**: Implement rate limiting on validation endpoints
- **Logging**: Add security event logging for blocked attempts
- **Monitoring**: Set up alerts for repeated XSS attempts

## References

- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [DOMPurify Documentation](https://github.com/cure53/DOMPurify)
- [Pydantic Validation](https://docs.pydantic.dev/latest/concepts/validators/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

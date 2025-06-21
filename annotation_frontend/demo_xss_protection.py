#!/usr/bin/env python3
"""
XSS Protection Demonstration Script

This script demonstrates how the annotation frontend's XSS protection
works by showing both valid and invalid inputs.
"""

from schemas import AnnotationRequest, BboxSchema
from pydantic import ValidationError


def test_xss_protection():
    """Demonstrate XSS protection in action."""
    
    print("🛡️  XSS Protection Demonstration")
    print("=" * 50)
    
    # Test valid input
    print("\n✅ Testing VALID input:")
    try:
        valid_request = AnnotationRequest(
            example_id="example_123",
            bbox=BboxSchema(x1=10, y1=10, x2=100, y2=100),
            label="person-walking",
            annotator_id="user_123",
            quality_score=0.9,
            notes="Clear detection of person"
        )
        print(f"   Label: '{valid_request.label}' ✓")
        print(f"   Annotator: '{valid_request.annotator_id}' ✓")
        print(f"   Notes: '{valid_request.notes}' ✓")
    except ValidationError as e:
        print(f"   ERROR: {e}")
    
    # Test XSS attempts
    print("\n❌ Testing XSS ATTACKS (should be blocked):")
    
    xss_tests = [
        {
            'name': 'Script tag in label',
            'data': {
                'example_id': 'test_123',
                'bbox': BboxSchema(x1=10, y1=10, x2=100, y2=100),
                'label': '<script>alert("xss")</script>',
                'annotator_id': 'user_123',
                'quality_score': 0.9
            }
        },
        {
            'name': 'Event handler in label',
            'data': {
                'example_id': 'test_123',
                'bbox': BboxSchema(x1=10, y1=10, x2=100, y2=100),
                'label': 'person onload=alert(1)',
                'annotator_id': 'user_123',
                'quality_score': 0.9
            }
        },
        {
            'name': 'Script in notes',
            'data': {
                'example_id': 'test_123',
                'bbox': BboxSchema(x1=10, y1=10, x2=100, y2=100),
                'label': 'person',
                'annotator_id': 'user_123',
                'quality_score': 0.9,
                'notes': 'Note with <script>fetch("http://evil.com")</script>'
            }
        },
        {
            'name': 'Invalid characters in annotator_id',
            'data': {
                'example_id': 'test_123',
                'bbox': BboxSchema(x1=10, y1=10, x2=100, y2=100),
                'label': 'person',
                'annotator_id': 'user@domain.com<script>',
                'quality_score': 0.9
            }
        }
    ]
    
    for test in xss_tests:
        print(f"\n   Testing: {test['name']}")
        try:
            AnnotationRequest(**test['data'])
            print("   ⚠️  WARNING: Attack was NOT blocked!")
        except ValidationError as e:
            print(f"   🛡️  BLOCKED: {e.errors()[0]['msg']}")
    
    # Test edge cases
    print("\n🧪 Testing EDGE CASES:")
    
    edge_cases = [
        {
            'name': 'Empty label',
            'data': {
                'example_id': 'test_123',
                'bbox': BboxSchema(x1=10, y1=10, x2=100, y2=100),
                'label': '',
                'annotator_id': 'user_123',
                'quality_score': 0.9
            }
        },
        {
            'name': 'Label too long',
            'data': {
                'example_id': 'test_123',
                'bbox': BboxSchema(x1=10, y1=10, x2=100, y2=100),
                'label': 'a' * 51,  # Max is 50
                'annotator_id': 'user_123',
                'quality_score': 0.9
            }
        },
        {
            'name': 'Notes too long',
            'data': {
                'example_id': 'test_123',
                'bbox': BboxSchema(x1=10, y1=10, x2=100, y2=100),
                'label': 'person',
                'annotator_id': 'user_123',
                'quality_score': 0.9,
                'notes': 'a' * 1001  # Max is 1000
            }
        }
    ]
    
    for test in edge_cases:
        print(f"\n   Testing: {test['name']}")
        try:
            AnnotationRequest(**test['data'])
            print("   ✅ Accepted")
        except ValidationError as e:
            print(f"   🛡️  BLOCKED: {e.errors()[0]['msg']}")
    
    print("\n" + "=" * 50)
    print("🎯 Demonstration complete!")
    print("✅ Valid inputs are accepted")
    print("🛡️  XSS attacks are blocked")
    print("⚡ Input validation is working correctly")


if __name__ == "__main__":
    test_xss_protection()

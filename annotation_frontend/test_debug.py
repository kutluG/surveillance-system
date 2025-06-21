import sys
import os
sys.path.append('..')

# Test direct endpoint call
from fastapi import Request
from fastapi_csrf_protect import CsrfProtect
from unittest.mock import Mock

def test_csrf_endpoint():
    print("Testing CSRF endpoint logic...")
    
    # Create mock request
    request = Mock()
    request.headers = {}
    
    # Create CSRF protect instance
    csrf_protect = CsrfProtect()
    
    try:
        # Test token generation
        csrf_token = csrf_protect.generate_csrf()
        print(f"CSRF token generated: {csrf_token[:50]}...")
        
        # Test the actual endpoint logic
        from main import get_csrf_token
        
        # This should work without the full request context
        print("CSRF endpoint imported successfully")
        
    except Exception as e:
        import traceback
        print(f"Error testing CSRF endpoint: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_csrf_endpoint()

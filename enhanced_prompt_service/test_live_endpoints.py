#!/usr/bin/env python3
"""
Test the enhanced prompt service endpoints if it's running.
"""
import requests
import sys

def test_enhanced_prompt_service():
    """Test the enhanced prompt service endpoints."""
    try:
        # Test health endpoints
        response = requests.get('http://localhost:8009/healthz', timeout=5)
        print(f'/healthz: {response.status_code} - {response.json()}')
        
        response = requests.get('http://localhost:8009/readyz', timeout=5)
        print(f'/readyz: {response.status_code} - {response.json()}')
        
        # Test legacy redirect
        response = requests.get('http://localhost:8009/api/prompt', allow_redirects=False, timeout=5)
        print(f'/api/prompt redirect: {response.status_code}')
        if 'location' in response.headers:
            print(f'Location: {response.headers["location"]}')
        
        # Test another redirect
        response = requests.get('http://localhost:8009/api/history/test', allow_redirects=False, timeout=5)
        print(f'/api/history/test redirect: {response.status_code}')
        if 'location' in response.headers:
            print(f'Location: {response.headers["location"]}')
        
        print("\nAll endpoint tests completed successfully!")
        return True
        
    except requests.exceptions.ConnectionError:
        print('Enhanced prompt service is not running on port 8009')
        return False
    except Exception as e:
        print(f'Error testing service: {e}')
        return False

if __name__ == "__main__":
    success = test_enhanced_prompt_service()
    sys.exit(0 if success else 1)

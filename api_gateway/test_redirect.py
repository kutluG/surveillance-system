#!/usr/bin/env python3
"""
Test script to verify backwards compatibility redirect functionality
"""

import asyncio
import httpx
from fastapi.testclient import TestClient
from main import app

def test_redirect_functionality():
    """Test that unversioned API calls redirect to v1"""
    
    client = TestClient(app)
    
    # Test cases for different HTTP methods and paths
    test_cases = [
        ("GET", "/api/edge/health"),
        ("POST", "/api/rag/analysis"),
        ("PUT", "/api/prompt/query"),
        ("DELETE", "/api/notifier/send"),
        ("GET", "/api/vms/clips/recent"),
        ("POST", "/api/voice/transcribe"),
        ("GET", "/api/training/jobs?status=running"),
    ]
    
    print("Testing backwards compatibility redirects...")
    print("=" * 60)
    
    for method, path in test_cases:
        print(f"\nTesting: {method} {path}")
        
        # Make request without following redirects
        response = client.request(
            method=method,
            url=path,
            follow_redirects=False
        )
        
        # Check for 301 redirect
        if response.status_code == 301:
            redirect_location = response.headers.get("location", "")
            redirect_header = response.headers.get("X-API-Version-Redirect", "")
            
            print(f"✅ Status: 301 Moved Permanently")
            print(f"   Location: {redirect_location}")
            print(f"   Version Header: {redirect_header}")
            
            # Verify the redirect URL is correct
            expected_redirect = path.replace("/api/", "/api/v1/")
            if redirect_location == expected_redirect:
                print(f"   ✅ Redirect URL is correct")
            else:
                print(f"   ❌ Expected: {expected_redirect}")
                print(f"   ❌ Got: {redirect_location}")
        else:
            print(f"❌ Expected 301, got: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("Redirect testing completed!")

if __name__ == "__main__":
    test_redirect_functionality()

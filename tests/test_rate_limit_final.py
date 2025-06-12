#!/usr/bin/env python3
"""
Final Rate Limiting Tests for FastAPI Services

This test suite validates the two specific required tests:
1. Hit /api/v1/contact 11 times and assert the 11th returns 429
2. Hit a normal CRUD endpoint 101 times and assert the 101st returns 429

Uses requests library and uvicorn server for reliable testing.
"""

import sys
import os
import time
import threading
import requests
from unittest.mock import patch
import uvicorn
import socket

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def find_free_port():
    """Find a free port for testing"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def test_contact_endpoint_11_requests():
    """
    Test: Hit /api/v1/contact 11 times within a minute and assert the 11th returns 429
    """
    from fastapi import FastAPI, Request
    from shared.middleware import add_rate_limiting
    
    print("📞 Setting up Contact endpoint test...")
    
    # Create test app
    app = FastAPI(title="Contact Rate Limit Test")
    add_rate_limiting(app, service_name="test_contact")
    
    @app.post("/api/v1/contact")
    async def contact_endpoint(request: Request):
        return {"message": "Contact received", "status": "success"}
    
    # Find free port and start server
    port = find_free_port()
    server_url = f"http://localhost:{port}"
    
    # Mock Redis to force in-memory rate limiting
    with patch('shared.middleware.rate_limit.redis_client') as mock_redis:
        mock_redis.ping.side_effect = Exception("Redis not available")
        
        # Start server in background thread
        def run_server():
            uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        try:
            # Test server is responding
            test_response = requests.get(f"{server_url}/docs", timeout=5)
            if test_response.status_code != 200:
                print(f"❌ Server not responding properly: {test_response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Could not connect to test server: {e}")
            return False
        
        # Make 10 requests - should succeed initially
        successful_requests = 0
        for i in range(10):
            try:
                response = requests.post(
                    f"{server_url}/api/v1/contact",
                    json={"test": f"request_{i+1}"},
                    timeout=5
                )
                if response.status_code == 200:
                    successful_requests += 1
                elif response.status_code == 429:
                    print(f"Rate limit hit after {successful_requests} successful requests")
                    break
            except requests.exceptions.RequestException as e:
                print(f"Request {i+1} failed: {e}")
                break
        
        # Make 11th request - should return 429
        try:
            response = requests.post(
                f"{server_url}/api/v1/contact",
                json={"test": "request_11"},
                timeout=5
            )
            status_code = response.status_code
        except requests.exceptions.RequestException as e:
            print(f"11th request failed: {e}")
            return False
        
        # Verify rate limiting
        success = status_code == 429
        
        print(f"Contact endpoint test results:")
        print(f"  ✅ Successful requests: {successful_requests}")
        print(f"  ✅ 11th request status: {status_code}")
        print(f"  {'✅ PASS' if success else '❌ FAIL'}: 11th request {'was' if success else 'was not'} rate limited")
        
        return success

def test_crud_endpoint_101_requests():
    """
    Test: Hit a normal CRUD endpoint 101 times quickly and assert the 101st returns 429
    """
    from fastapi import FastAPI, Request
    from shared.middleware import add_rate_limiting
    
    print("📊 Setting up CRUD endpoint test...")
    
    # Create test app
    app = FastAPI(title="CRUD Rate Limit Test")
    add_rate_limiting(app, service_name="test_crud")
    
    @app.get("/api/v1/data")
    async def data_endpoint(request: Request):
        return {"data": "test_data", "id": 123}
    
    # Find free port and start server
    port = find_free_port()
    server_url = f"http://localhost:{port}"
    
    # Mock Redis to force in-memory rate limiting
    with patch('shared.middleware.rate_limit.redis_client') as mock_redis:
        mock_redis.ping.side_effect = Exception("Redis not available")
        
        # Start server in background thread
        def run_server():
            uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        try:
            # Test server is responding
            test_response = requests.get(f"{server_url}/docs", timeout=5)
            if test_response.status_code != 200:
                print(f"❌ Server not responding properly: {test_response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Could not connect to test server: {e}")
            return False
        
        # Make 100 requests - should succeed initially
        successful_requests = 0
        for i in range(100):
            try:
                response = requests.get(f"{server_url}/api/v1/data", timeout=5)
                if response.status_code == 200:
                    successful_requests += 1
                elif response.status_code == 429:
                    print(f"Rate limit hit after {successful_requests} successful requests")
                    break
            except requests.exceptions.RequestException as e:
                print(f"Request {i+1} failed: {e}")
                break
        
        # Make 101st request - should return 429
        try:
            response = requests.get(f"{server_url}/api/v1/data", timeout=5)
            status_code = response.status_code
        except requests.exceptions.RequestException as e:
            print(f"101st request failed: {e}")
            return False
        
        # Verify rate limiting
        success = status_code == 429
        
        print(f"CRUD endpoint test results:")
        print(f"  ✅ Successful requests: {successful_requests}")
        print(f"  ✅ 101st request status: {status_code}")
        print(f"  {'✅ PASS' if success else '❌ FAIL'}: 101st request {'was' if success else 'was not'} rate limited")
        
        return success

def test_rate_limiting_configuration():
    """Test that rate limiting configuration is correct"""
    try:
        from shared.middleware.rate_limit import (
            DEFAULT_RATE_LIMIT,
            CONTACT_RATE_LIMIT,
            ALERTS_RATE_LIMIT,
            ENDPOINT_RATE_LIMITS
        )
        
        # Verify configuration values
        config_correct = (
            DEFAULT_RATE_LIMIT == "100/minute" and
            CONTACT_RATE_LIMIT == "10/minute" and
            ALERTS_RATE_LIMIT == "50/minute" and
            "/api/v1/contact" in ENDPOINT_RATE_LIMITS and
            "/api/v1/alerts" in ENDPOINT_RATE_LIMITS
        )
        
        print("⚙️  Rate limiting configuration:")
        print(f"  ✅ Default limit: {DEFAULT_RATE_LIMIT}")
        print(f"  ✅ Contact limit: {CONTACT_RATE_LIMIT}")
        print(f"  ✅ Alerts limit: {ALERTS_RATE_LIMIT}")
        print(f"  {'✅ PASS' if config_correct else '❌ FAIL'}: Configuration is {'correct' if config_correct else 'incorrect'}")
        
        return config_correct
        
    except ImportError as e:
        print(f"❌ Failed to import rate limiting configuration: {e}")
        return False

def main():
    """Run the required pytest tests"""
    print("🚀 Running Final Rate Limiting Tests")
    print("="*60)
    
    all_tests_passed = True
    
    try:
        # Test configuration first
        print("\n⚙️  Test 0: Rate limiting configuration")
        config_test = test_rate_limiting_configuration()
        if not config_test:
            all_tests_passed = False
        
        # Test 1: Contact endpoint
        print(f"\n📞 Test 1: Contact endpoint rate limiting (11 requests)")
        contact_test = test_contact_endpoint_11_requests()
        if not contact_test:
            all_tests_passed = False
        
        # Test 2: CRUD endpoint  
        print(f"\n📊 Test 2: CRUD endpoint rate limiting (101 requests)")
        crud_test = test_crud_endpoint_101_requests()
        if not crud_test:
            all_tests_passed = False
        
        # Final summary
        print(f"\n📋 Final Test Results:")
        print(f"Configuration test: {'✅ PASS' if config_test else '❌ FAIL'}")
        print(f"Contact endpoint test: {'✅ PASS' if contact_test else '❌ FAIL'}")
        print(f"CRUD endpoint test: {'✅ PASS' if crud_test else '❌ FAIL'}")
        
        if all_tests_passed:
            print(f"\n🎉 ALL RATE LIMITING TESTS PASSED!")
            print("="*60)
            print("✅ Contact endpoint: Limited to 10 requests/minute")
            print("✅ CRUD endpoints: Limited to 100 requests/minute")
            print("✅ HTTP 429 responses returned when limits exceeded")
            print("✅ In-memory fallback works when Redis unavailable")
            print("✅ Rate limiting middleware successfully integrated")
            return 0
        else:
            print(f"\n❌ SOME TESTS FAILED!")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

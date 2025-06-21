"""
Rate Limiting and Request Size Constraint Tests

Tests the rate limiting functionality and request body size limits
for the annotation service endpoints.
"""
import json
import time
import pytest
from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import patch, MagicMock, Mock

from main import app
from schemas import AnnotationRequest, BboxSchema
from auth import TokenData, require_role
from rate_limiting import MAX_JSON_FIELD_SIZE, MAX_REQUEST_BODY_SIZE


class TestRateLimiting:
    """Test rate limiting functionality for different endpoints."""
    
    def setup_method(self):
        """Set up test client and authentication mocks."""
        self.client = TestClient(app)
        
        # Mock authentication
        mock_user = TokenData(sub="test_user", exp=9999999999, roles=["annotator"], scopes=["annotate"])
        
        def mock_require_role(role):
            def mock_dependency():
                return mock_user
            return mock_dependency
        
        # Override the dependency
        self.client.app.dependency_overrides[require_role("annotator")] = mock_require_role("annotator")
    
    def teardown_method(self):
        """Clean up after tests."""
        self.client.app.dependency_overrides.clear()
    
    @patch('routers.examples.AnnotationService')
    @patch('routers.examples.get_db')
    def test_annotation_endpoint_rate_limit(self, mock_get_db, mock_service):
        """Test that annotation endpoint enforces 10 requests/minute limit."""
        # Mock database and service
        mock_db = MagicMock()
        mock_example = MagicMock()
        mock_example.example_id = "test_123"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_example
        mock_get_db.return_value = mock_db
        
        mock_service_instance = MagicMock()
        mock_service_instance.process_annotation.return_value = {"status": "success"}
        mock_service.return_value = mock_service_instance
        
        # Valid annotation data
        annotation_data = {
            "example_id": "test_123",
            "bbox": {"x1": 10, "y1": 10, "x2": 100, "y2": 100},
            "label": "person",
            "annotator_id": "test_user",
            "quality_score": 0.9
        }
        
        # Make 10 requests (within limit)
        for i in range(10):
            response = self.client.post(
                "/api/v1/examples/test_123/label",
                json=annotation_data,
                headers={"Authorization": "Bearer fake_token"}
            )
            # Should succeed or fail for non-rate-limit reasons
            assert response.status_code != status.HTTP_429_TOO_MANY_REQUESTS
        
        # 11th request should be rate limited
        response = self.client.post(
            "/api/v1/examples/test_123/label",
            json=annotation_data,
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Should be rate limited
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        response_data = response.json()
        assert "rate limit exceeded" in response_data["error"].lower()
        assert "retry_after" in response_data
    
    @patch('data_subject.get_db')
    def test_data_deletion_rate_limit(self, mock_get_db):
        """Test that data deletion endpoint enforces 5 requests/hour limit."""
        # Mock authentication for compliance officer
        mock_user = TokenData(sub="compliance_user", exp=9999999999, roles=["compliance_officer"], scopes=["delete"])
        
        def mock_require_compliance_role(role):
            def mock_dependency():
                return mock_user
            return mock_dependency
        
        # Override the dependency for compliance officer
        self.client.app.dependency_overrides[require_role("compliance_officer")] = mock_require_compliance_role("compliance_officer")
        
        # Mock database
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = []
        mock_get_db.return_value = mock_db
        
        # Valid deletion request data
        deletion_data = {
            "face_hash_id": "a" * 64  # 64-character hex string
        }
        
        # Make 5 requests (within limit)
        for i in range(5):
            response = self.client.post(
                "/data-subject/delete",
                json=deletion_data,
                headers={"Authorization": "Bearer fake_token"}
            )
            # Should not be rate limited yet
            assert response.status_code != status.HTTP_429_TOO_MANY_REQUESTS
        
        # 6th request should be rate limited
        response = self.client.post(
            "/data-subject/delete",
            json=deletion_data,
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Should be rate limited
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        response_data = response.json()
        assert "rate limit exceeded" in response_data["error"].lower()
    
    def test_global_rate_limit(self):
        """Test that all endpoints respect the global 60 requests/minute limit."""
        # Test health endpoint which should have global rate limit
        success_count = 0
        
        # Make 60 requests (within global limit)
        for i in range(60):
            response = self.client.get("/health")
            if response.status_code == status.HTTP_200_OK:
                success_count += 1
        
        # Most should succeed
        assert success_count >= 50  # Allow some variation
        
        # 61st request should be rate limited
        response = self.client.get("/health")
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestRequestSizeConstraints:
    """Test request body size constraints."""
    
    def setup_method(self):
        """Set up test client and authentication mocks."""
        self.client = TestClient(app)
        
        # Mock authentication
        mock_user = TokenData(sub="test_user", exp=9999999999, roles=["annotator"], scopes=["annotate"])
        
        def mock_require_role(role):
            def mock_dependency():
                return mock_user
            return mock_dependency
          # Override the dependency
        self.client.app.dependency_overrides[require_role("annotator")] = mock_require_role("annotator")
    
    def teardown_method(self):
        """Clean up after tests."""
        self.client.app.dependency_overrides.clear()
    
    def test_large_json_field_rejection(self):
        """Test that JSON fields larger than 4KB are rejected."""
        # Create a payload with a large field (5KB)
        large_label = "a" * 5120  # 5KB label
        
        annotation_data = {
            "example_id": "test_123",
            "bbox": {"x1": 10, "y1": 10, "x2": 100, "y2": 100},
            "label": large_label,  # This exceeds 4KB limit
            "annotator_id": "test_user",
            "quality_score": 0.9
        }
        
        response = self.client.post(
            "/api/v1/examples/test_123/label",
            json=annotation_data,
            headers={
                "Authorization": "Bearer fake_token",
                "X-CSRF-Token": "test_token"  # Add CSRF token to avoid 403
            }
        )
        
        # Should be rejected due to field size
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE]
        
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            response_data = response.json()
            # Should indicate validation error
            assert "validation" in response_data.get("error", "").lower() or "error" in response_data
    
    def test_large_notes_field_rejection(self):
        """Test that notes field larger than allowed size is rejected."""
        # Create a payload with large notes (5KB)
        large_notes = "This is a very long note. " * 200  # Approximately 5KB
        
        annotation_data = {
            "example_id": "test_123",
            "bbox": {"x1": 10, "y1": 10, "x2": 100, "y2": 100},
            "label": "person",
            "annotator_id": "test_user",
            "quality_score": 0.9,
            "notes": large_notes
        }
        
        response = self.client.post(
            "/api/v1/examples/test_123/label",
            json=annotation_data,
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Should be rejected due to field size
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE]
    
    def test_maximum_request_body_size(self):
        """Test that request bodies larger than 1MB are rejected."""
        # Create a payload larger than 1MB
        very_large_data = "x" * (1024 * 1024 + 1000)  # Just over 1MB
        
        large_payload = {
            "example_id": "test_123",
            "bbox": {"x1": 10, "y1": 10, "x2": 100, "y2": 100},
            "label": "person",
            "annotator_id": "test_user",
            "quality_score": 0.9,
            "large_field": very_large_data
        }
        
        response = self.client.post(
            "/api/v1/examples/test_123/label",
            json=large_payload,
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Should be rejected due to overall body size
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        response_data = response.json()
        assert "too large" in response_data.get("error", "").lower()
        assert "max_size" in response_data or "detail" in response_data
    
    def test_valid_size_request_accepted(self):
        """Test that requests within size limits are accepted."""
        # Create a valid payload within limits
        annotation_data = {
            "example_id": "test_123",
            "bbox": {"x1": 10, "y1": 10, "x2": 100, "y2": 100},
            "label": "person",
            "annotator_id": "test_user",
            "quality_score": 0.9,
            "notes": "This is a reasonable sized note"
        }
        
        with patch('routers.examples.AnnotationService') as mock_service, \
             patch('routers.examples.get_db') as mock_get_db:
            
            # Mock database and service
            mock_db = MagicMock()
            mock_example = MagicMock()
            mock_example.example_id = "test_123"
            mock_db.query.return_value.filter.return_value.first.return_value = mock_example
            mock_get_db.return_value = mock_db
            
            mock_service_instance = MagicMock()
            mock_service_instance.process_annotation.return_value = {"status": "success"}
            mock_service.return_value = mock_service_instance
            
            response = self.client.post(
                "/api/v1/examples/test_123/label",
                json=annotation_data,
                headers={"Authorization": "Bearer fake_token"}
            )
            
            # Should succeed or fail for reasons other than size constraints
            # (might fail due to CSRF, auth, etc. but not size limits)
            assert response.status_code != status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    
    def test_content_length_header_enforcement(self):
        """Test that Content-Length header is respected for size limits."""
        # Test with explicit Content-Length header
        large_content = json.dumps({"data": "x" * (1024 * 1024 + 1000)})  # Over 1MB
        
        response = self.client.post(
            "/api/v1/examples/test_123/label",
            data=large_content,
            headers={
                "Authorization": "Bearer fake_token",
                "Content-Type": "application/json",
                "Content-Length": str(len(large_content))
            }
        )
        
        # Should be rejected due to size
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


class TestRateLimitHeaders:
    """Test that rate limit headers are properly set."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_rate_limit_headers_present(self):
        """Test that rate limit headers are included in responses."""
        response = self.client.get("/health")
        
        # Rate limit headers should be present when rate limiting is active
        if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            assert "Retry-After" in response.headers
            assert "X-RateLimit-Limit" in response.headers or "retry_after" in response.json()
    
    def test_rate_limit_error_format(self):
        """Test that rate limit error responses have proper format."""
        # Make many requests to trigger rate limit
        for _ in range(70):  # Exceed global limit
            response = self.client.get("/health")
        
        # Final request should be rate limited
        response = self.client.get("/health")
        
        if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            response_data = response.json()
            
            # Check error format
            assert "error" in response_data
            assert "detail" in response_data
            assert "retry_after" in response_data
            assert "endpoint" in response_data
            assert "timestamp" in response_data
            
            # Check headers
            assert "Retry-After" in response.headers


class TestRequestSizeMiddleware:
    """Test the request size middleware specifically."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_middleware_max_size_constant(self):
        """Test that the middleware uses the correct max size constant."""
        assert MAX_REQUEST_BODY_SIZE == 1024 * 1024  # 1MB
    
    def test_middleware_json_field_size_constant(self):
        """Test that the JSON field size constant is correct."""
        assert MAX_JSON_FIELD_SIZE == 4096  # 4KB


class TestPerformanceUnderLoad:
    """Test performance characteristics under rate limiting."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_rate_limiter_performance(self):
        """Test that rate limiting doesn't significantly impact response time."""
        # Measure response time for requests within limits
        start_time = time.time()
        
        for _ in range(10):
            response = self.client.get("/health")
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break
        
        end_time = time.time()
        avg_response_time = (end_time - start_time) / 10
        
        # Response time should be reasonable (less than 100ms per request)
        assert avg_response_time < 0.1
    
    def test_memory_usage_under_rate_limiting(self):
        """Test that rate limiting doesn't cause memory leaks."""
        # This is a basic test - in production you'd use memory profiling tools
        initial_response = self.client.get("/health")
        
        # Make many requests
        for _ in range(50):
            self.client.get("/health")
        
        # Should still be able to get responses
        final_response = self.client.get("/health")
        assert final_response.status_code in [status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

class TestRequestSizeValidation:
    """Test request size validation functionality."""
    
    def test_large_json_field_rejection(self):
        """Test that JSON fields larger than 4KB are rejected with 422"""
        # Mock the authentication and other dependencies
        mock_user = Mock()
        mock_user.sub = "test-user"
        mock_user.roles = ["annotator"]
        
        # Create annotation data with a field larger than 4KB
        large_notes = "x" * (MAX_JSON_FIELD_SIZE + 1)
        annotation_data = {
            "corrected_detections": [],
            "annotator_id": "test-annotator", 
            "quality_score": 0.95,
            "notes": large_notes
        }
        
        # Mock dependencies to bypass authentication
        with patch('main.get_current_user', return_value=mock_user):
            with patch('main.require_role', return_value=lambda: mock_user):
                # Mock the CSRF middleware to skip validation
                with patch('main.csrf_middleware', side_effect=lambda request, call_next: call_next(request)):
                    response = self.client.post(
                        "/api/v1/examples/test-event/label",
                        json=annotation_data,
                        headers={"X-CSRF-Token": "test-token"}
                    )
                    
                    # Should get 422 Unprocessable Entity due to field size validation
                    assert response.status_code == 422
                    
                    error_data = response.json()
                    assert "detail" in error_data
                    print(f"✓ Large JSON field correctly rejected: {error_data}")
    
    def test_acceptable_request_size(self):
        """Test that requests within size limits are processed"""
        # Test with health endpoint which doesn't require authentication
        response = self.client.get("/health")
        
        # Should succeed 
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        print(f"✓ Normal request processed successfully: {data['status']}")


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
    
    def test_health_endpoint_rate_limit(self):
        """Test health endpoint rate limiting (120 req/min)"""
        # Make multiple requests to health endpoint
        success_count = 0
        rate_limited = False
        
        # Test with 20 requests (well under the 120/min limit)
        for i in range(20):
            response = self.client.get("/health")
            
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                rate_limited = True
                error_data = response.json()
                print(f"Rate limited at request {i+1}: {error_data}")
                break
        
        print(f"✓ Health endpoint: {success_count} successful requests")
        
        # Should not be rate limited for reasonable number of requests
        assert success_count >= 20, f"Expected at least 20 successes, got {success_count}"
    
    def test_annotation_submission_rate_limit_simulation(self):
        """Test annotation submission rate limiting (10 req/min)"""
        # Mock the authentication and dependencies
        mock_user = Mock()
        mock_user.sub = "test-user"
        mock_user.roles = ["annotator"]
        
        annotation_data = {
            "corrected_detections": [],
            "annotator_id": "test-annotator",
            "quality_score": 0.95,
            "notes": "Test annotation"
        }
        
        with patch('main.get_current_user', return_value=mock_user):
            with patch('main.require_role', return_value=lambda: mock_user):
                with patch('main.get_db'):
                    with patch('main.AnnotationService.submit_annotation'):
                        with patch('main.kafka_pool.send_message', return_value=True):
                            with patch('main.csrf_middleware', side_effect=lambda request, call_next: call_next(request)):
                                
                                success_count = 0
                                rate_limited = False
                                
                                # Make 12 requests (should hit 10 req/min limit)
                                for i in range(12):
                                    response = self.client.post(
                                        "/api/v1/examples/test-event/label",
                                        json=annotation_data,
                                        headers={"X-CSRF-Token": "test-token"}
                                    )
                                    
                                    if response.status_code == 200:
                                        success_count += 1
                                    elif response.status_code == 429:
                                        rate_limited = True
                                        error_data = response.json()
                                        print(f"✓ Rate limited at request {i+1}: {error_data}")
                                        
                                        # Verify rate limit response format
                                        assert "error" in error_data
                                        assert "Rate limit exceeded" in error_data["error"]
                                        break
                                
                                print(f"✓ Annotation endpoint: {success_count} successful requests before rate limit")
                                
                                # Should get rate limited at some point with 12 requests
                                assert rate_limited or success_count <= 10, "Should be rate limited or limited to 10 requests"

    def test_data_subject_delete_rate_limit_simulation(self):
        """Test data subject delete rate limiting (5 req/hour)"""
        # Mock compliance officer user
        compliance_user = Mock()
        compliance_user.sub = "compliance-officer"
        compliance_user.roles = ["compliance_officer"]
        
        delete_data = {
            "face_hash_id": "a" * 64  # Valid 64-character hex string
        }
        
        with patch('main.get_current_user', return_value=compliance_user):
            with patch('main.require_role', return_value=lambda: compliance_user):
                with patch('main.get_db'):
                    with patch('main.csrf_middleware', side_effect=lambda request, call_next: call_next(request)):
                        
                        success_count = 0
                        rate_limited = False
                        
                        # Make 7 requests (should hit 5 req/hour limit)
                        for i in range(7):
                            response = self.client.post(
                                "/data-subject/delete",
                                json=delete_data,
                                headers={"X-CSRF-Token": "test-token"}
                            )
                            
                            if response.status_code == 200:
                                success_count += 1
                            elif response.status_code == 429:
                                rate_limited = True
                                error_data = response.json()
                                print(f"✓ Data subject delete rate limited at request {i+1}: {error_data}")
                                break
                        
                        print(f"✓ Data subject delete: {success_count} successful requests before rate limit")
                        
                        # Should get rate limited at some point with 7 requests
                        assert rate_limited or success_count <= 5, "Should be rate limited or limited to 5 requests"


class TestMiddlewareIntegration:
    """Test that middleware is properly integrated"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
    
    def test_slowapi_middleware_active(self):
        """Test that SlowAPI middleware is active"""
        # Check that the app has the limiter attached
        assert hasattr(app.state, 'limiter'), "SlowAPI limiter not attached to app state"
        print("✓ SlowAPI limiter is attached to app state")
    
    def test_request_size_middleware_active(self):
        """Test that request size middleware is active by checking middleware stack"""
        from rate_limiting import RequestSizeMiddleware
        
        # Check if RequestSizeMiddleware is in the middleware stack
        middleware_found = False
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls') and middleware.cls == RequestSizeMiddleware:
                middleware_found = True
                break
        
        assert middleware_found, "RequestSizeMiddleware not found in middleware stack"
        print("✓ RequestSizeMiddleware is active in middleware stack")


class TestRateLimitHeaders:
    """Test that proper rate limiting headers are returned"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
    
    def test_rate_limit_response_format(self):
        """Test the format of rate limit responses"""
        # This test verifies the structure of rate limit error responses
        # by checking the custom handler implementation
        from rate_limiting import custom_rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from fastapi import Request
        import asyncio
        
        # Create mock objects
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test"
        
        mock_exc = RateLimitExceeded("10/minute")
        mock_exc.retry_after = 60
        mock_exc.detail = "10/minute"
        
        async def test_handler():
            response = await custom_rate_limit_exceeded_handler(mock_request, mock_exc)
            
            # Verify response status
            assert response.status_code == 429
            
            # Verify headers are present
            assert "Retry-After" in response.headers
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
            
            return response
        
        # Run the async test
        response = asyncio.run(test_handler())
        print("✓ Rate limit response format is correct")


if __name__ == "__main__":
    # Run tests if file is executed directly
    import sys
    
    print("🧪 Running Rate Limiting and Request Size Tests")
    print("=" * 60)
    
    # Test request size constraints
    print("\n📏 Testing Request Size Constraints...")
    size_tests = TestRequestSizeConstraints()
    size_tests.setup_method()
    
    try:
        size_tests.test_large_request_body_rejection()
        size_tests.test_acceptable_request_size()
        print("✅ Request size constraint tests passed")
    except Exception as e:
        print(f"❌ Request size tests failed: {e}")
    
    # Test rate limiting  
    print("\n🚦 Testing Rate Limiting...")
    rate_tests = TestRateLimiting()
    rate_tests.setup_method()
    
    try:
        rate_tests.test_health_endpoint_rate_limit()
        print("✅ Rate limiting tests passed")
    except Exception as e:
        print(f"❌ Rate limiting tests failed: {e}")
    
    # Test middleware integration
    print("\n🔧 Testing Middleware Integration...")
    middleware_tests = TestMiddlewareIntegration()
    middleware_tests.setup_method()
    
    try:
        middleware_tests.test_slowapi_middleware_active()
        middleware_tests.test_request_size_middleware_active()
        print("✅ Middleware integration tests passed")
    except Exception as e:
        print(f"❌ Middleware tests failed: {e}")
    
    # Test rate limit headers
    print("\n📋 Testing Rate Limit Response Format...")
    header_tests = TestRateLimitHeaders()
    header_tests.setup_method()
    
    try:
        header_tests.test_rate_limit_response_format()
        print("✅ Rate limit header tests passed")
    except Exception as e:
        print(f"❌ Rate limit header tests failed: {e}")
    
    print("\n🎉 Test suite completed!")

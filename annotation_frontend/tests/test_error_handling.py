"""
Test cases for error handling in the annotation frontend service.
Tests global exception handler and consistent error response formats.
"""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from main import app
from schemas import ErrorResponse, ValidationErrorResponse


class TestGlobalExceptionHandler:
    """Test global exception handler for consistent error responses."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_undefined_route_returns_404_json_error(self, client):
        """Test that calling an undefined route returns JSON error with 404 status."""
        # Call a non-existent endpoint
        response = client.get("/api/v1/undefined-route")
        
        # Verify status code
        assert response.status_code == 404
        
        # Verify response is JSON
        assert response.headers["content-type"] == "application/json"
        
        # Verify response format matches ErrorResponse schema
        error_data = response.json()
        assert "error" in error_data
        assert error_data["error"] == "Not Found"
        
        # Additional checks for consistent error format
        assert "detail" in error_data
        assert "timestamp" in error_data
        assert "request_id" in error_data
        
        # Verify it's a valid UUID for request_id
        import uuid
        uuid.UUID(error_data["request_id"])  # Should not raise exception

    def test_custom_exception_endpoint_returns_500_internal_server_error(self, client):
        """Test that a custom endpoint raising ValueError returns 500 with consistent error format."""
        # Add a test-only endpoint that raises ValueError
        @app.get("/test/raise-error", include_in_schema=False)
        async def test_raise_error():
            raise ValueError("This is a test ValueError for testing error handling")
        
        # Call the test endpoint
        response = client.get("/test/raise-error")
        
        # Verify status code is 500
        assert response.status_code == 500
        
        # Verify response is JSON
        assert response.headers["content-type"] == "application/json"
        
        # Verify response format matches ErrorResponse schema  
        error_data = response.json()
        assert "error" in error_data
        assert error_data["error"] == "Internal Server Error"
        
        # Additional checks
        assert "detail" in error_data
        assert error_data["detail"] == "An unexpected error occurred while processing your request"
        assert "timestamp" in error_data
        assert "request_id" in error_data

    def test_validation_error_returns_422_with_detailed_errors(self, client):
        """Test that validation errors return 422 with detailed error information."""
        # Mock authentication to bypass auth for this test
        with patch('routers.examples.get_current_user') as mock_auth:
            mock_auth.return_value = MagicMock(sub="test_user", scopes=["annotator"])
            
            # Send invalid data to trigger Pydantic validation error
            invalid_data = {
                "example_id": "",  # Invalid: empty string (min_length=1)
                "bbox": {
                    "x1": -10,  # Invalid: negative coordinate
                    "y1": 0,
                    "x2": 100,
                    "y2": 100
                },
                "label": "",  # Invalid: empty string (min_length=1)
                "annotator_id": "test_user",
                "quality_score": 2.0  # Invalid: greater than 1.0
            }
            
            # Mock CSRF validation to focus on validation errors
            with patch('main.csrf_protect.validate_csrf'):
                response = client.post(
                    "/api/v1/examples/test_example/label",
                    json=invalid_data,
                    headers={"X-CSRF-Token": "test-token"}
                )
            
            # Verify status code is 422 (Unprocessable Entity)
            assert response.status_code == 422
            
            # Verify response format
            error_data = response.json()
            assert "error" in error_data
            assert error_data["error"] == "Validation Error"
            assert "detail" in error_data
            assert "errors" in error_data
            assert isinstance(error_data["errors"], list)
            assert len(error_data["errors"]) > 0
            
            # Verify error structure matches ValidationErrorResponse
            for error in error_data["errors"]:
                assert "field" in error
                assert "message" in error
                # code field is optional but should be present

    def test_http_exception_preserves_status_code_and_detail(self, client):
        """Test that HTTPException raised in code preserves status and detail."""
        # Add a test endpoint that raises HTTPException with custom status
        @app.get("/test/raise-http-exception", include_in_schema=False)
        async def test_raise_http_exception():
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Custom forbidden message")
        
        response = client.get("/test/raise-http-exception")
        
        # Verify status code is preserved
        assert response.status_code == 403
        
        # Verify response format
        error_data = response.json()
        assert "error" in error_data
        assert error_data["error"] == "Custom forbidden message"
        assert error_data["detail"] == "Custom forbidden message"
        assert "timestamp" in error_data
        assert "request_id" in error_data

    def test_database_error_handling(self, client):
        """Test that database errors are properly handled."""
        # Add a test endpoint that simulates database error
        @app.get("/test/database-error", include_in_schema=False)
        async def test_database_error():
            from sqlalchemy.exc import SQLAlchemyError
            raise SQLAlchemyError("Database connection failed")
        
        response = client.get("/test/database-error")
        
        # Should return 500 with standard error format
        assert response.status_code == 500
        error_data = response.json()
        assert error_data["error"] == "Internal Server Error"
        assert "detail" in error_data
        assert "timestamp" in error_data
        assert "request_id" in error_data

    def test_error_response_has_consistent_structure(self, client):
        """Test that all error responses have consistent structure."""
        # Test different error scenarios
        test_cases = [
            ("/api/v1/nonexistent", 404),
            ("/test/raise-error", 500),  # From our test endpoint above
        ]
        
        for endpoint, expected_status in test_cases:
            response = client.get(endpoint)
            assert response.status_code == expected_status
            
            error_data = response.json()
            
            # All error responses should have these fields
            required_fields = ["error", "detail", "timestamp", "request_id"]
            for field in required_fields:
                assert field in error_data, f"Missing {field} in error response for {endpoint}"
            
            # Timestamp should be valid ISO format
            from datetime import datetime
            try:
                datetime.fromisoformat(error_data["timestamp"].replace("Z", "+00:00"))
            except ValueError:
                pytest.fail(f"Invalid timestamp format in error response for {endpoint}")
            
            # Request ID should be valid UUID
            import uuid
            try:
                uuid.UUID(error_data["request_id"])
            except ValueError:
                pytest.fail(f"Invalid request_id format in error response for {endpoint}")

    def test_cors_error_handling(self, client):
        """Test that CORS-related errors are handled properly."""
        # Test with invalid Origin header
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://malicious-site.com"}
        )
        
        # Should still return proper response (CORS is handled at middleware level)
        # But error format should be consistent if any CORS error occurs
        assert response.status_code in [200, 400, 403]  # Various valid responses
        
        if response.status_code != 200:
            error_data = response.json()
            assert "error" in error_data
            assert "detail" in error_data

    def test_rate_limiting_error_format(self, client):
        """Test that rate limiting errors return consistent format."""
        # This test might need adjustment based on actual rate limiting implementation
        # For now, we'll test the structure if rate limiting triggers
        
        # Make many requests quickly to potentially trigger rate limiting
        # Note: This might not trigger in test environment, but structure should be consistent
        responses = []
        for i in range(50):  # Try to exceed rate limit
            response = client.get("/healthz")
            responses.append(response)
            if response.status_code == 429:  # Rate limited
                break
        
        # Check if any response was rate limited
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        if rate_limited_responses:
            error_data = rate_limited_responses[0].json()
            assert "error" in error_data
            assert "detail" in error_data
            assert "timestamp" in error_data

    def test_content_type_consistency(self, client):
        """Test that error responses always return JSON content type."""
        error_endpoints = [
            "/api/v1/nonexistent",
            "/test/raise-error",
        ]
        
        for endpoint in error_endpoints:
            response = client.get(endpoint)
            assert "application/json" in response.headers["content-type"]
            
            # Should be valid JSON
            try:
                response.json()
            except json.JSONDecodeError:
                pytest.fail(f"Response from {endpoint} is not valid JSON")


class TestRouterErrorHandling:
    """Test error handling in specific routers."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_examples_router_error_responses(self, client):
        """Test that examples router returns consistent error formats."""
        # Test unauthorized access (no auth header)
        response = client.get("/api/v1/examples")
        
        # Should return 401 or redirect to login
        assert response.status_code in [401, 403, 422]  # Depending on auth implementation
        
        if response.status_code in [401, 403]:
            # If it's an error response, should have consistent format
            if response.headers.get("content-type", "").startswith("application/json"):
                error_data = response.json()
                assert "error" in error_data or "detail" in error_data

    def test_health_router_error_responses(self, client):
        """Test that health router handles errors consistently."""
        # Health endpoints should generally not error, but if they do, format should be consistent
        response = client.get("/healthz")
        
        # Health should return 200, but if it errors, format should be consistent
        if response.status_code != 200:
            error_data = response.json()
            assert "error" in error_data
            assert "detail" in error_data


class TestExceptionHandlerTraceability:
    """Test that exception handling provides proper traceability."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_request_id_uniqueness(self, client):
        """Test that each error response gets a unique request ID."""
        request_ids = set()
        
        # Make multiple requests to generate multiple errors
        for i in range(5):
            response = client.get(f"/api/v1/nonexistent-{i}")
            assert response.status_code == 404
            
            error_data = response.json()
            request_id = error_data["request_id"]
            
            # Should not have seen this request_id before
            assert request_id not in request_ids
            request_ids.add(request_id)
        
        # All request IDs should be unique
        assert len(request_ids) == 5

    def test_error_logging_context(self, client):
        """Test that errors are logged with proper context."""
        with patch('main.logger.error') as mock_logger:
            # Trigger an error
            response = client.get("/api/v1/nonexistent")
            assert response.status_code == 404
            
            # Verify logging was called with context
            mock_logger.assert_called()
            
            # Check that the log call included proper context
            call_args = mock_logger.call_args
            assert len(call_args) >= 1  # Should have message
            
            # Should include extra context
            if len(call_args) > 1 and 'extra' in call_args[1]:
                extra = call_args[1]['extra']
                assert 'request_id' in extra
                assert 'method' in extra
                assert 'path' in extra


class TestGlobalExceptionHandler:
    """Test global exception handler for consistent error responses."""
    
    def test_404_not_found_error_format(self, client, mock_dependencies):
        """Test that 404 errors return consistent JSON format."""
        # Call a non-existent endpoint
        response = client.get("/api/v1/nonexistent-endpoint")
        
        assert response.status_code == 404
        
        # Verify response format
        error_data = response.json()
        assert "error" in error_data
        assert "detail" in error_data
        assert "timestamp" in error_data
        assert "request_id" in error_data
        
        # Verify error content
        assert error_data["error"] == "Not Found"
        assert "not found" in error_data["detail"].lower()
        
        # Verify timestamp format (ISO format)
        from datetime import datetime
        datetime.fromisoformat(error_data["timestamp"].replace("Z", "+00:00"))
        
        # Verify request_id is a UUID-like string
        import uuid
        uuid.UUID(error_data["request_id"])  # Should not raise exception
    
    def test_validation_error_format(self, client, mock_dependencies):
        """Test that validation errors return consistent JSON format."""
        # Mock authentication to bypass auth requirements
        with patch('main.get_current_user') as mock_auth:
            mock_auth.return_value = MagicMock(sub="test_user", scopes=["annotator"])
            
            # Send invalid data to trigger validation error
            invalid_data = {
                "example_id": "",  # Invalid: empty string
                "bbox": {
                    "x1": -1,  # Invalid: negative coordinate
                    "y1": 0,
                    "x2": 100,
                    "y2": 100
                },
                "label": "",  # Invalid: empty string
                "annotator_id": "test_user",
                "quality_score": 1.5  # Invalid: > 1.0
            }
            
            response = client.post(
                "/api/v1/examples/test_id/label",
                json=invalid_data,
                headers={"X-CSRF-Token": "test-token"}
            )
            
            assert response.status_code == 422
            
            # Verify response format
            error_data = response.json()
            assert "error" in error_data
            assert "detail" in error_data
            assert "errors" in error_data
            assert "timestamp" in error_data
            assert "request_id" in error_data
            
            # Verify error content
            assert error_data["error"] == "Validation Error"
            assert isinstance(error_data["errors"], list)
            assert len(error_data["errors"]) > 0
            
            # Verify error structure
            for error in error_data["errors"]:
                assert "field" in error
                assert "message" in error
                assert "code" in error
    
    def test_internal_server_error_format(self, client, mock_dependencies):
        """Test that unhandled exceptions return consistent 500 error format."""
        # Create a test endpoint that raises an unhandled exception
        @app.get("/test/error")
        async def test_error_endpoint():
            raise ValueError("This is a test error")
        
        response = client.get("/test/error")
        
        assert response.status_code == 500
        
        # Verify response format
        error_data = response.json()
        assert "error" in error_data
        assert "detail" in error_data
        assert "timestamp" in error_data
        assert "request_id" in error_data
        
        # Verify error content
        assert error_data["error"] == "Internal Server Error"
        assert error_data["detail"] == "An unexpected error occurred while processing your request"
        
        # Verify timestamp format
        from datetime import datetime
        datetime.fromisoformat(error_data["timestamp"].replace("Z", "+00:00"))
        
        # Verify request_id is present
        import uuid
        uuid.UUID(error_data["request_id"])
    
    def test_http_exception_format(self, client, mock_dependencies):
        """Test that HTTPException returns consistent error format."""
        # Mock authentication to bypass auth requirements
        with patch('main.get_current_user') as mock_auth:
            mock_auth.return_value = MagicMock(sub="test_user", scopes=["annotator"])
            
            # Mock database to return None (example not found)
            mock_dependencies['db'].query.return_value.filter.return_value.first.return_value = None
            
            response = client.get("/api/v1/examples/nonexistent_id")
            
            assert response.status_code == 404
            
            # Verify response format
            error_data = response.json()
            assert "error" in error_data
            assert "detail" in error_data
            assert "timestamp" in error_data
            assert "request_id" in error_data
            
            # Verify error content matches HTTPException detail
            assert "not found" in error_data["error"].lower()
    
    def test_csrf_error_format(self, client, mock_dependencies):
        """Test that CSRF errors return consistent format."""
        # Mock authentication
        with patch('main.get_current_user') as mock_auth:
            mock_auth.return_value = MagicMock(sub="test_user", scopes=["annotator"])
            
            # Try to make a POST request without CSRF token
            response = client.post(
                "/api/v1/examples/test_id/label",
                json={"test": "data"}
            )
            
            assert response.status_code == 403
            
            # Verify response format
            error_data = response.json()
            assert "detail" in error_data
            assert "csrf" in error_data["detail"].lower()


class TestErrorResponseModels:
    """Test that error response models match actual responses."""
    
    def test_error_response_model_validation(self):
        """Test that ErrorResponse model can validate actual error responses."""
        # Sample error response data
        error_data = {
            "error": "Not Found",
            "detail": "The requested resource was not found",
            "timestamp": "2025-06-16T10:30:00.000Z",
            "request_id": "123e4567-e89b-12d3-a456-426614174000"
        }
        
        # Should not raise validation error
        error_response = ErrorResponse(**error_data)
        assert error_response.error == "Not Found"
        assert error_response.detail == "The requested resource was not found"
    
    def test_validation_error_response_model(self):
        """Test that ValidationErrorResponse model can validate actual responses."""
        validation_error_data = {
            "error": "Validation Error",
            "detail": "Request validation failed",
            "errors": [
                {
                    "field": "body.label",
                    "message": "String should have at least 1 character",
                    "code": "string_too_short"
                }
            ],
            "timestamp": "2025-06-16T10:30:00.000Z",
            "request_id": "123e4567-e89b-12d3-a456-426614174000"
        }
        
        # Should not raise validation error
        validation_response = ValidationErrorResponse(**validation_error_data)
        assert validation_response.error == "Validation Error"
        assert len(validation_response.errors) == 1
    
    def test_error_response_serialization(self):
        """Test that error response models serialize correctly."""
        from datetime import datetime
        
        error_response = ErrorResponse(
            error="Test Error",
            detail="This is a test error",
            timestamp=datetime.utcnow(),
            request_id="test-request-id"
        )
        
        serialized = error_response.model_dump()
        assert "error" in serialized
        assert "detail" in serialized
        assert "timestamp" in serialized
        assert "request_id" in serialized


class TestRouterErrorHandling:
    """Test error handling in modular routers."""
    
    def test_health_router_error_handling(self, client, mock_dependencies):
        """Test that health router errors are handled consistently."""
        # Mock database to raise an exception
        mock_dependencies['db'].execute.side_effect = Exception("Database connection failed")
        
        response = client.get("/health")
        
        # Should still return a response (health checks are resilient)
        assert response.status_code in [200, 503]
        
        # If it's an error response, it should have consistent format
        if response.status_code != 200:
            error_data = response.json()
            assert "status" in error_data
    
    def test_examples_router_error_handling(self, client, mock_dependencies):
        """Test that examples router errors are handled consistently."""
        # Mock authentication
        with patch('main.get_current_user') as mock_auth:
            mock_auth.return_value = MagicMock(sub="test_user", scopes=["annotator"])
            
            # Mock database to raise an exception
            mock_dependencies['db'].query.side_effect = Exception("Database error")
            
            response = client.get("/api/v1/examples")
            
            assert response.status_code == 500
            
            # Verify error format
            error_data = response.json()
            assert "error" in error_data
            assert "detail" in error_data
            assert "timestamp" in error_data
            assert "request_id" in error_data


# Integration tests with actual error scenarios
class TestRealWorldErrorScenarios:
    """Test real-world error scenarios."""
    
    def test_authentication_failure(self, client, mock_dependencies):
        """Test authentication failure error format."""
        # Try to access protected endpoint without authentication
        response = client.get("/api/v1/examples")
        
        assert response.status_code == 401
        
        # Should have consistent error format
        error_data = response.json()
        assert "detail" in error_data
    
    def test_rate_limit_error(self, client, mock_dependencies):
        """Test rate limiting error format."""
        # This would require actually hitting rate limits,
        # which is impractical in unit tests
        # Could be tested in integration tests
        pass
    
    def test_request_size_limit_error(self, client, mock_dependencies):
        """Test request size limit error format."""
        # Mock authentication
        with patch('main.get_current_user') as mock_auth:
            mock_auth.return_value = MagicMock(sub="test_user", scopes=["annotator"])
            
            # Create oversized request data
            oversized_data = {
                "example_id": "test_id",
                "bbox": {"x1": 0, "y1": 0, "x2": 100, "y2": 100},
                "label": "test_label",
                "annotator_id": "test_user",
                "notes": "x" * 10000  # Very long notes field
            }
            
            response = client.post(
                "/api/v1/examples/test_id/label",
                json=oversized_data,
                headers={"X-CSRF-Token": "test-token"}
            )
            
            # Should return validation error or request too large
            assert response.status_code in [413, 422]
            
            if response.status_code == 422:
                error_data = response.json()
                assert "error" in error_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

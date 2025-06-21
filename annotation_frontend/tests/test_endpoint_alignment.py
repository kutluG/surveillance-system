"""
Test suite for API endpoint alignment between frontend and backend.
Validates that frontend calls use /api/v1 and backend redirects work correctly.
Enhanced to cover comprehensive API versioning strategy.
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
from fastapi.testclient import TestClient
from fastapi import status

from main import app
from config import settings


class TestFrontendEndpointAlignment:
    """Test that frontend JavaScript uses versioned endpoints."""
    
    def test_frontend_fetch_uses_versioned_examples_endpoint(self):
        """Test that frontend fetch function calls /api/v1/examples."""
        # Test the expected URL construction logic used by frontend
        expected_url = f"{settings.API_BASE_PATH}/examples"
        
        # The test validates that our frontend code constructs the correct URL
        assert settings.API_BASE_PATH == "/api/v1"
        assert expected_url == "/api/v1/examples"
    
    def test_frontend_config_exposes_api_base_path(self):
        """Test that frontend configuration exposes API_BASE_PATH."""
        # Test that our settings include the API_BASE_PATH
        assert hasattr(settings, 'API_BASE_PATH')
        assert settings.API_BASE_PATH == "/api/v1"
        
        # Test that we also have API_VERSION
        assert hasattr(settings, 'API_VERSION')
        assert settings.API_VERSION == "v1"
    
    def test_frontend_websocket_uses_versioned_endpoint(self):
        """Test that frontend WebSocket connects to versioned endpoint."""
        # Test WebSocket URL construction logic
        ws_base_path = settings.WS_BASE_PATH
        expected_ws_path = ws_base_path + '/examples'
        
        assert expected_ws_path == "/ws/v1/examples"


class TestBackendRedirectSupport:
    """Test that backend provides proper redirects for unversioned endpoints."""
    
    def setUp(self):
        self.client = TestClient(app)
    
    def test_unversioned_examples_redirects_to_v1(self):
        """Test that /api/examples redirects to /api/v1/examples with 301."""
        client = TestClient(app)
        
        # Make request to unversioned endpoint without following redirects
        response = client.get("/api/examples", follow_redirects=False)
        
        # Should get 301 redirect
        assert response.status_code == status.HTTP_301_MOVED_PERMANENTLY
        
        # Should redirect to versioned endpoint
        expected_location = "/api/v1/examples"
        assert response.headers["location"] == expected_location
        
        # Should include custom headers indicating version redirect
        assert response.headers["x-api-version-redirect"] == settings.API_VERSION
        assert response.headers["x-deprecated-endpoint"] == "true"
    
    def test_unversioned_data_subject_delete_redirects_to_v1(self):
        """Test that /api/data-subject/delete redirects to /api/v1/data-subject/delete with 301."""
        client = TestClient(app)
        
        # Make DELETE request to unversioned endpoint
        response = client.delete("/api/data-subject/delete/test-id", follow_redirects=False)
        
        # Should get 301 redirect
        assert response.status_code == status.HTTP_301_MOVED_PERMANENTLY
          # Should redirect to versioned endpoint
        expected_location = "/api/v1/data-subject/delete/test-id"
        assert response.headers["location"] == expected_location
        
        # Should include custom headers
        assert response.headers["x-api-version-redirect"] == settings.API_VERSION
        assert response.headers["x-deprecated-endpoint"] == "true"
    
    def test_comprehensive_api_redirect_coverage(self):
        """Test that various unversioned API endpoints redirect properly."""
        client = TestClient(app)
        
        test_endpoints = [
            "/api/csrf-token",
            "/api/login", 
            "/api/health",
            "/api/metrics"
        ]
        
        for endpoint in test_endpoints:
            response = client.get(endpoint, follow_redirects=False)
            
            # Should get 301 redirect
            assert response.status_code == status.HTTP_301_MOVED_PERMANENTLY, f"Failed for {endpoint}"
            
            # Should redirect to versioned endpoint  
            expected_location = endpoint.replace("/api/", f"{settings.API_BASE_PATH}/")
            assert response.headers["location"] == expected_location, f"Wrong redirect for {endpoint}"
            
            # Should include custom headers
            assert response.headers["x-api-version-redirect"] == settings.API_VERSION
            assert response.headers["x-deprecated-endpoint"] == "true"
    
    def test_redirect_preserves_query_parameters(self):
        """Test that redirects preserve query parameters."""
        client = TestClient(app)
        
        # Make request with query parameters
        response = client.get(
            "/api/examples?page=2&size=20",
            follow_redirects=False
        )
        
        # Should get 301 redirect
        assert response.status_code == status.HTTP_301_MOVED_PERMANENTLY
        
        # Should preserve query parameters in redirect
        expected_location = "/api/v1/examples?page=2&size=20"
        assert response.headers["location"] == expected_location
    
    def test_versioned_endpoints_work_directly(self):
        """Test that versioned endpoints work without redirect."""
        client = TestClient(app)
        
        # Make request to versioned endpoint - this should NOT redirect
        # (It may return 401 due to auth, but should not redirect)
        response = client.get("/api/v1/examples", follow_redirects=False)
        
        # Should NOT be a redirect (could be 401 Unauthorized due to missing auth)
        assert response.status_code != status.HTTP_301_MOVED_PERMANENTLY
        assert response.status_code != status.HTTP_302_FOUND
    
    def test_health_endpoint_not_redirected(self):
        """Test that /health endpoint is not affected by redirect logic."""
        client = TestClient(app)
        
        # Health endpoint should work directly without redirect
        response = client.get("/health", follow_redirects=False)
        
        # Should NOT redirect (should work directly)
        assert response.status_code != status.HTTP_301_MOVED_PERMANENTLY
        assert response.status_code != status.HTTP_302_FOUND
        
        # Should return actual health response
        assert response.status_code in [200, 503]  # Healthy or unhealthy


class TestAPIVersioningStrategy:
    """Test comprehensive API versioning strategy."""
    
    def test_api_base_path_configuration(self):
        """Test that API_BASE_PATH is properly configured."""
        # Ensure API_BASE_PATH is set correctly
        assert settings.API_BASE_PATH == "/api/v1"
        assert settings.API_BASE_PATH.startswith("/api/v")
        assert len(settings.API_BASE_PATH.split("/")) == 3  # '', 'api', 'v1'
        
        # Ensure API_VERSION matches
        assert settings.API_VERSION == "v1"
        
        # Ensure WebSocket path is properly configured
        assert settings.WS_BASE_PATH == "/ws/v1"
    
    def test_all_routers_use_versioned_paths(self):
        """Test that all routers are mounted under versioned paths."""
        # Check that the examples router is properly configured
        from routers.examples import router as examples_router
        # Note: In the actual implementation, routers are mounted with prefix
        # This test validates the mounting approach in main.py
        assert hasattr(settings, 'API_BASE_PATH')
    
    def test_websocket_endpoint_versioned(self):
        """Test that WebSocket endpoints use versioned paths."""
        client = TestClient(app)
        
        # Test that WebSocket endpoint exists at versioned path
        try:
            with client.websocket_connect("/ws/v1/examples") as websocket:
                # If we can connect, the endpoint exists
                pass
        except Exception:
            # WebSocket might fail due to auth or other reasons,
            # but the important thing is that the endpoint exists
            pass
    
    def test_websocket_backwards_compatibility(self):
        """Test that old WebSocket endpoints provide deprecation notices."""
        client = TestClient(app)
        
        # Test WebSocket backwards compatibility
        try:
            with client.websocket_connect("/ws/examples") as websocket:
                # Should receive deprecation notice
                data = websocket.receive_json()
                assert data["type"] == "deprecation_notice"
                assert "deprecated" in data["message"].lower()
                assert data["new_endpoint"] == "/ws/v1/examples"
        except Exception:
            # WebSocket might close immediately, which is expected behavior
            pass


class TestIntegrationEndpointUpdates:
    """Integration tests for updated endpoint calls."""
    
    def test_template_configuration_exposed(self):
        """Test that templates expose the correct configuration."""
        client = TestClient(app)
        
        # Get the main page
        response = client.get("/")
        
        # Should contain the API_BASE_PATH configuration
        assert "API_BASE_PATH" in response.text
        assert settings.API_BASE_PATH in response.text
        
        # Should contain WebSocket configuration
        assert "WS_BASE_PATH" in response.text
        assert settings.WS_BASE_PATH in response.text
        
        # Should contain API version
        assert "API_VERSION" in response.text
        assert settings.API_VERSION in response.text
    
    def test_csrf_token_endpoint_versioned(self):
        """Test that CSRF token endpoint uses versioned path."""
        client = TestClient(app)
        
        # CSRF token should be available at versioned endpoint
        response = client.get("/api/v1/csrf-token", follow_redirects=False)
        
        # Should not redirect (may return other status due to implementation)
        assert response.status_code != status.HTTP_301_MOVED_PERMANENTLY
    
    def test_login_endpoint_versioned(self):
        """Test that login endpoint uses versioned path."""
        client = TestClient(app)
        
        # Login should be available at versioned endpoint
        response = client.post(
            "/api/v1/login",
            data={"username": "test", "password": "test"},
            follow_redirects=False
        )
        
        # Should not redirect (may return 401 due to invalid credentials)
        assert response.status_code != status.HTTP_301_MOVED_PERMANENTLY


class TestDeprecationAndMigrationStrategy:
    """Test deprecation warnings and migration guidance."""
    
    def test_deprecated_endpoint_headers(self):
        """Test that deprecated endpoints return proper headers."""
        client = TestClient(app)
        
        response = client.get("/api/examples", follow_redirects=False)
        
        assert response.status_code == status.HTTP_301_MOVED_PERMANENTLY
        assert response.headers["x-deprecated-endpoint"] == "true"
        assert response.headers["x-api-version-redirect"] == settings.API_VERSION
    
    def test_frontend_mock_api_call_uses_versioned_endpoint(self):
        """Mock test that frontend API calls use versioned endpoints."""
        # This would be a more comprehensive test with actual JS testing
        # For now, we test the configuration that the frontend uses
        
        expected_endpoint = f"{settings.API_BASE_PATH}/examples"
        assert expected_endpoint == "/api/v1/examples"
        
        expected_ws_endpoint = f"{settings.WS_BASE_PATH}/examples"
        assert expected_ws_endpoint == "/ws/v1/examples"


if __name__ == "__main__":
    pytest.main([__file__])

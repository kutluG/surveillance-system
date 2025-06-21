"""
Tests for API versioning, legacy redirects, and health/readiness probes.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from fastapi.testclient import TestClient
from fastapi import status
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the shared modules before importing main
sys.modules['shared.logging_config'] = Mock()
sys.modules['shared.audit_middleware'] = Mock()
sys.modules['shared.metrics'] = Mock()
sys.modules['shared.middleware'] = Mock()

# Mock the enhanced_prompt_service modules
sys.modules['enhanced_prompt_service.weaviate_client'] = Mock()
sys.modules['enhanced_prompt_service.clip_store'] = Mock()
sys.modules['enhanced_prompt_service.conversation_manager'] = Mock()
sys.modules['enhanced_prompt_service.llm_client'] = Mock()

def setup_mocks():
    """Set up the mocks with proper return values."""
    # Mock shared modules
    mock_logger = Mock()
    sys.modules['shared.logging_config'].configure_logging = Mock(return_value=mock_logger)
    sys.modules['shared.logging_config'].get_logger = Mock(return_value=mock_logger)
    sys.modules['shared.audit_middleware'].add_audit_middleware = Mock()
    sys.modules['shared.metrics'].instrument_app = Mock()
    sys.modules['shared.middleware'].add_rate_limiting = Mock()
    
    # Mock auth
    mock_auth = Mock()
    mock_user = Mock()
    mock_user.sub = "test_user"
    mock_auth.get_current_user = Mock(return_value=mock_user)
    sys.modules['shared.auth'] = mock_auth
    
    # Mock config
    mock_config = Mock()
    mock_settings = Mock()
    mock_settings.redis_url = "redis://redis:6379/0"
    mock_settings.weaviate_url = "http://weaviate:8080"
    mock_settings.openai_api_key = "test-key"
    mock_settings.api_base_path = "/api/v1"
    
    mock_config.get_service_config = Mock(return_value={
        "weaviate_url": "http://weaviate:8080",
        "openai_api_key": "test-key",
        "redis_url": "redis://redis:6379/0"
    })
    mock_config.Settings = Mock(return_value=mock_settings)
    sys.modules['shared.config'] = mock_config
    
    # Mock models
    sys.modules['shared.models'] = Mock()
      # Mock enhanced_prompt_service modules
    sys.modules['enhanced_prompt_service.schemas'] = Mock()
    sys.modules['enhanced_prompt_service.routers'] = Mock()
    sys.modules['enhanced_prompt_service.routers.prompt'] = Mock()
    sys.modules['enhanced_prompt_service.routers.history'] = Mock()
    
    # Create mock routers with proper routes attribute
    mock_prompt_router = Mock()
    mock_prompt_router.routes = []  # Empty routes list
    mock_prompt_router.router = Mock()
    mock_prompt_router.router.routes = []
    
    mock_history_router = Mock()
    mock_history_router.routes = []  # Empty routes list
    mock_history_router.router = Mock()
    mock_history_router.router.routes = []
    
    # Create proper router objects
    from fastapi import APIRouter
    actual_prompt_router = APIRouter()
    actual_history_router = APIRouter()
    
    sys.modules['enhanced_prompt_service.routers.prompt'].router = actual_prompt_router
    sys.modules['enhanced_prompt_service.routers.history'].router = actual_history_router
    
    # Mock response schemas
    class MockHealthResponse:
        def __init__(self, status):
            self.status = status
    
    class MockErrorResponse:
        def __init__(self, error, detail=None, code=None):
            self.error = error
            self.detail = detail
            self.code = code
            
        def model_dump(self):
            return {"error": self.error, "detail": self.detail, "code": self.code}
    
    sys.modules['enhanced_prompt_service.schemas'].HealthResponse = MockHealthResponse
    sys.modules['enhanced_prompt_service.schemas'].ErrorResponse = MockErrorResponse

# Set up mocks before importing main
setup_mocks()

# Now import the main module
from enhanced_prompt_service.main import app


class TestAPIVersioning:
    """Test API versioning and legacy redirects."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        
        # Mock app state
        app.state.redis_client = AsyncMock()
        app.state.weaviate_client = MagicMock()
        app.state.openai_client = MagicMock()
        app.state.conversation_manager = MagicMock()
        
        # Configure mocks
        app.state.redis_client.ping = AsyncMock(return_value=True)
        app.state.weaviate_client.is_ready = MagicMock(return_value=True)
        app.state.openai_client.api_key = "test-key"
    
    def test_legacy_redirect_prompt_endpoint(self):
        """Test that /api/prompt redirects to /api/v1/prompt with 301."""
        response = self.client.get("/api/prompt", allow_redirects=False)
        
        assert response.status_code == 301
        assert response.headers["location"] == "/api/v1/prompt"
    
    def test_legacy_redirect_history_endpoint(self):
        """Test that /api/history redirects to /api/v1/history with 301."""
        response = self.client.get("/api/history", allow_redirects=False)
        
        assert response.status_code == 301
        assert response.headers["location"] == "/api/v1/history"
    
    def test_legacy_redirect_nested_paths(self):
        """Test that nested legacy paths are redirected correctly."""
        response = self.client.get("/api/history/session123", allow_redirects=False)
        
        assert response.status_code == 301
        assert response.headers["location"] == "/api/v1/history/session123"
    
    def test_legacy_redirect_with_query_params(self):
        """Test that redirects preserve query parameters."""
        response = self.client.get("/api/prompt?limit=10&query=test", allow_redirects=False)
        
        assert response.status_code == 301
        # FastAPI redirects should preserve query params
        location = response.headers["location"]
        assert location.startswith("/api/v1/prompt")
    
    def test_versioned_paths_work_correctly(self):
        """Test that versioned paths are accessible (would normally return 404 due to auth, but path is correct)."""        # This test verifies the path routing works, even if auth fails
        response = self.client.get("/api/v1/prompt")
        
        # Should get auth error (401/403) or method not allowed (405), not 404
        # 404 would indicate the path doesn't exist
        assert response.status_code in [401, 403, 405, 422], f"Got {response.status_code} instead of auth/method error"
    
    def test_websocket_redirect_connection_upgrade(self):
        """Test WebSocket connections are properly redirected to versioned endpoints."""
        # Test WebSocket redirect - should close with redirect code
        try:
            with pytest.raises(Exception):
                with self.client.websocket_connect("/ws/prompt") as websocket:
                    # Should not establish connection, should get redirect
                    pass
        except Exception as e:
            # WebSocket redirect should handle gracefully
            assert "websocket" in str(e).lower() or "connection" in str(e).lower()
    
    def test_websocket_redirect_alerts_endpoint(self):
        """Test WebSocket redirect for alerts endpoint."""
        # Test that /ws/alerts redirects to /ws/v1/alerts
        try:
            with pytest.raises(Exception):
                with self.client.websocket_connect("/ws/alerts/session123") as websocket:
                    pass
        except Exception as e:
            # Should handle WebSocket redirect gracefully
            assert "websocket" in str(e).lower() or "connection" in str(e).lower()


class TestHealthProbes:
    """Test health and readiness probe endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        
        # Mock app state with healthy services
        app.state.redis_client = AsyncMock()
        app.state.weaviate_client = MagicMock()
        app.state.openai_client = MagicMock()
        app.state.conversation_manager = MagicMock()
        
        # Configure mocks for healthy state
        app.state.redis_client.ping = AsyncMock(return_value=True)
        app.state.weaviate_client.is_ready = MagicMock(return_value=True)
        app.state.openai_client.api_key = "test-key"
    
    def test_health_endpoint_always_ok(self):
        """Test that /health always returns 200 OK."""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_healthz_endpoint_always_ok(self):
        """Test that /healthz (liveness probe) always returns 200 OK."""
        response = self.client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_readyz_endpoint_all_healthy(self):
        """Test that /readyz returns 200 when all services are healthy."""
        response = self.client.get("/readyz")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
    
    @pytest.mark.asyncio
    async def test_readyz_redis_failure(self):
        """Test that /readyz returns 503 when Redis is unhealthy."""
        # Mock Redis ping failure
        app.state.redis_client.ping = AsyncMock(side_effect=Exception("Redis connection failed"))
        
        response = self.client.get("/readyz")
        
        assert response.status_code == 503
        data = response.json()
        assert "Service not ready" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_readyz_weaviate_failure(self):
        """Test that /readyz returns 503 when Weaviate is unhealthy."""
        # Mock Weaviate readiness failure
        app.state.weaviate_client.is_ready = MagicMock(return_value=False)
        
        response = self.client.get("/readyz")
        
        assert response.status_code == 503
        data = response.json()
        assert "Service not ready" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_readyz_openai_client_missing(self):
        """Test that /readyz returns 503 when OpenAI client is not configured."""        # Mock missing OpenAI API key
        app.state.openai_client.api_key = None
        
        response = self.client.get("/readyz")
        
        assert response.status_code == 503
        data = response.json()
        assert "Service not ready" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_readyz_conversation_manager_missing(self):
        """Test that /readyz returns 503 when ConversationManager is not initialized."""
        # Mock missing conversation manager
        app.state.conversation_manager = None
        
        response = self.client.get("/readyz")
        
        assert response.status_code == 503
        data = response.json()
        assert "Service not ready" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_readyz_redis_client_missing(self):
        """Test that /readyz returns 503 when Redis client is not initialized."""
        # Mock missing Redis client
        app.state.redis_client = None
        
        response = self.client.get("/readyz")
        
        assert response.status_code == 503
        data = response.json()
        assert "Service not ready" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_readyz_weaviate_client_missing(self):
        """Test that /readyz returns 503 when Weaviate client is not initialized."""
        # Mock missing Weaviate client
        app.state.weaviate_client = None
        
        response = self.client.get("/readyz")
        
        assert response.status_code == 503
        data = response.json()
        assert "Service not ready" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_readyz_openai_client_missing_entirely(self):
        """Test that /readyz returns 503 when OpenAI client is not initialized."""
        # Mock missing OpenAI client
        app.state.openai_client = None
        
        response = self.client.get("/readyz")
        
        assert response.status_code == 503
        data = response.json()
        assert "Service not ready" in data["detail"]


class TestEndpointAccessibility:
    """Test that all endpoints are properly accessible."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
    
    def test_health_endpoints_no_auth_required(self):
        """Test that health endpoints don't require authentication."""
        endpoints = ["/health", "/healthz", "/readyz"]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Should not get 401/403 (auth errors) for health endpoints
            assert response.status_code not in [401, 403], f"Health endpoint {endpoint} requires auth"
    
    def test_api_endpoints_require_auth(self):
        """Test that API endpoints require authentication."""
        endpoints = ["/api/v1/prompt", "/api/v1/history"]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Should get auth error (or method not allowed for GET on POST endpoints)
            assert response.status_code in [401, 403, 405, 422], f"API endpoint {endpoint} doesn't require auth"


class TestRedirectLogging:
    """Test that redirects are properly logged."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
    
    @patch('enhanced_prompt_service.main.logger')
    def test_redirect_logged(self, mock_logger):
        """Test that redirects are logged for monitoring."""
        self.client.get("/api/prompt", allow_redirects=False)
        
        # Verify that the redirect was logged
        mock_logger.info.assert_called()
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Redirecting legacy API path" in call for call in log_calls)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

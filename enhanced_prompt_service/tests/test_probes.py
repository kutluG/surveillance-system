"""
Tests for health and readiness probe endpoints.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import redis.asyncio as redis

from enhanced_prompt_service.main import app


class TestHealthProbes:
    """Test health and readiness probe endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
    
    def test_healthz_endpoint_success(self):
        """Test that healthz endpoint returns 200 OK."""
        response = self.client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    def test_health_endpoint_success(self):
        """Test that basic health endpoint returns 200 OK."""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    @pytest.mark.asyncio
    async def test_readyz_endpoint_success(self):
        """Test that readyz endpoint returns 200 when all services are healthy."""
        # Mock Redis client
        mock_redis = AsyncMock(spec=redis.Redis)
        mock_redis.ping = AsyncMock(return_value=True)
        
        # Mock Weaviate client
        mock_weaviate = MagicMock()
        mock_weaviate.is_ready = MagicMock(return_value=True)
        
        # Mock OpenAI client
        mock_openai = MagicMock()
        
        # Set up app state with mocked clients
        app.state.redis_client = mock_redis
        app.state.weaviate_client = mock_weaviate
        app.state.openai_client = mock_openai
        
        try:
            response = self.client.get("/readyz")
            assert response.status_code == 200
            assert response.json() == {"status": "ready"}
            
            # Verify that health checks were called
            mock_redis.ping.assert_called_once()
            mock_weaviate.is_ready.assert_called_once()
            
        finally:
            # Clean up app state
            delattr(app.state, 'redis_client')
            delattr(app.state, 'weaviate_client')
            delattr(app.state, 'openai_client')
    
    @pytest.mark.asyncio
    async def test_readyz_endpoint_redis_failure(self):
        """Test that readyz endpoint returns 503 when Redis ping fails."""
        # Mock Redis client that fails ping
        mock_redis = AsyncMock(spec=redis.Redis)
        mock_redis.ping = AsyncMock(side_effect=redis.ConnectionError("Redis connection failed"))
        
        # Mock Weaviate client (healthy)
        mock_weaviate = MagicMock()
        mock_weaviate.is_ready = MagicMock(return_value=True)
        
        # Mock OpenAI client
        mock_openai = MagicMock()
        
        # Set up app state with mocked clients
        app.state.redis_client = mock_redis
        app.state.weaviate_client = mock_weaviate
        app.state.openai_client = mock_openai
        
        try:
            response = self.client.get("/readyz")
            assert response.status_code == 503
            assert "Service not ready" in response.json()["detail"]
            
            # Verify that Redis ping was called
            mock_redis.ping.assert_called_once()
            
        finally:
            # Clean up app state
            delattr(app.state, 'redis_client')
            delattr(app.state, 'weaviate_client')
            delattr(app.state, 'openai_client')
    
    @pytest.mark.asyncio
    async def test_readyz_endpoint_weaviate_failure(self):
        """Test that readyz endpoint returns 503 when Weaviate health check fails."""
        # Mock Redis client (healthy)
        mock_redis = AsyncMock(spec=redis.Redis)
        mock_redis.ping = AsyncMock(return_value=True)
        
        # Mock Weaviate client that fails health check
        mock_weaviate = MagicMock()
        mock_weaviate.is_ready = MagicMock(return_value=False)
        
        # Mock OpenAI client
        mock_openai = MagicMock()
        
        # Set up app state with mocked clients
        app.state.redis_client = mock_redis
        app.state.weaviate_client = mock_weaviate
        app.state.openai_client = mock_openai
        
        try:
            response = self.client.get("/readyz")
            assert response.status_code == 503
            assert "Service not ready" in response.json()["detail"]
            
            # Verify that health checks were called
            mock_redis.ping.assert_called_once()
            mock_weaviate.is_ready.assert_called_once()
            
        finally:
            # Clean up app state
            delattr(app.state, 'redis_client')
            delattr(app.state, 'weaviate_client')
            delattr(app.state, 'openai_client')
    
    @pytest.mark.asyncio
    async def test_readyz_endpoint_multiple_failures(self):
        """Test that readyz endpoint returns 503 when multiple services fail."""
        # Mock Redis client that fails
        mock_redis = AsyncMock(spec=redis.Redis)
        mock_redis.ping = AsyncMock(side_effect=Exception("Redis error"))
        
        # Mock Weaviate client that fails
        mock_weaviate = MagicMock()
        mock_weaviate.is_ready = MagicMock(side_effect=Exception("Weaviate error"))
        
        # Mock OpenAI client
        mock_openai = MagicMock()
        
        # Set up app state with mocked clients
        app.state.redis_client = mock_redis
        app.state.weaviate_client = mock_weaviate
        app.state.openai_client = mock_openai
        
        try:
            response = self.client.get("/readyz")
            assert response.status_code == 503
            assert "Service not ready" in response.json()["detail"]
            
            # Verify that Redis ping was called (first failure stops execution)
            mock_redis.ping.assert_called_once()
            
        finally:
            # Clean up app state
            delattr(app.state, 'redis_client')
            delattr(app.state, 'weaviate_client')
            delattr(app.state, 'openai_client')
    
    def test_readyz_endpoint_missing_app_state(self):
        """Test that readyz endpoint returns 503 when app state is not initialized."""
        # Ensure app state doesn't have the required attributes
        if hasattr(app.state, 'redis_client'):
            delattr(app.state, 'redis_client')
        if hasattr(app.state, 'weaviate_client'):
            delattr(app.state, 'weaviate_client')
        if hasattr(app.state, 'openai_client'):
            delattr(app.state, 'openai_client')
        
        response = self.client.get("/readyz")
        assert response.status_code == 503
        assert "Service not ready" in response.json()["detail"]

"""
Test JWT Authentication for Annotation Frontend Service.
"""
import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import create_test_token, verify_jwt_token, TokenData
from config import settings

# Mock FastAPI components for testing
try:
    from fastapi.testclient import TestClient
    from main import app
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    TestClient = None
    app = None


@pytest.fixture
def client():
    """Create test client if available."""
    if HAS_FASTAPI and app:
        return TestClient(app)
    else:
        pytest.skip("FastAPI components not available")


@pytest.fixture
def valid_token():
    """Create a valid JWT token for testing."""
    return create_test_token(
        subject="test-user-123",
        scopes=["annotation:read", "annotation:write"],
        roles=["annotator"],
        expires_delta=timedelta(hours=1)
    )


@pytest.fixture
def expired_token():
    """Create an expired JWT token for testing."""
    return create_test_token(
        subject="test-user-123",
        scopes=["annotation:read", "annotation:write"],
        roles=["annotator"],
        expires_delta=timedelta(seconds=-1)  # Already expired
    )


@pytest.fixture
def limited_scope_token():
    """Create a token with limited scopes (read only)."""
    return create_test_token(
        subject="read-only-user",
        scopes=["annotation:read"],  # Missing annotation:write
        roles=["viewer"],
        expires_delta=timedelta(hours=1)
    )


class TestTokenVerification:
    """Test JWT token verification functionality."""
    
    def test_verify_valid_token(self, valid_token):
        """Test that a valid token is properly decoded."""
        token_data = verify_jwt_token(valid_token)
        
        assert isinstance(token_data, TokenData)
        assert token_data.sub == "test-user-123"
        assert "annotation:read" in token_data.scopes
        assert "annotation:write" in token_data.scopes
        assert "annotator" in token_data.roles
        assert token_data.exp > datetime.utcnow().timestamp()
    
    def test_verify_expired_token(self, expired_token):
        """Test that an expired token raises HTTPException."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token(expired_token)
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
    
    def test_verify_invalid_token(self):
        """Test that an invalid token raises HTTPException."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token("invalid.token.here")
        
        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()
    
    def test_verify_malformed_token(self):
        """Test that a malformed token raises HTTPException."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token("not-a-jwt-at-all")
        
        assert exc_info.value.status_code == 401
    
    def test_verify_token_missing_subject(self):
        """Test token without subject claim."""
        from jose import jwt
        from fastapi import HTTPException
        from calendar import timegm
        
        payload = {
            "exp": timegm((datetime.utcnow() + timedelta(hours=1)).utctimetuple()),
            "scopes": ["annotation:read"]
            # Missing "sub" claim
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
        
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token(token)
        
        assert exc_info.value.status_code == 401
        assert "subject" in exc_info.value.detail.lower()


class TestAuthenticatedEndpoints:
    """Test that API endpoints properly enforce authentication."""
    
    def test_get_examples_requires_auth(self, client):
        """Test that /api/v1/examples requires authentication."""
        response = client.get("/api/v1/examples")
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()
    
    def test_get_examples_with_valid_token(self, client, valid_token):
        """Test that /api/v1/examples works with valid token."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        with patch('main.pending_examples', []):
            response = client.get("/api/v1/examples", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "examples" in data
            assert "total" in data
    
    def test_get_specific_example_requires_auth(self, client):
        """Test that /api/v1/examples/{event_id} requires authentication."""
        response = client.get("/api/v1/examples/test-event-123")
        assert response.status_code == 401
    
    def test_get_specific_example_with_valid_token(self, client, valid_token):
        """Test that /api/v1/examples/{event_id} works with valid token."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        mock_example = {
            "event_id": "test-event-123",
            "camera_id": "cam-01",
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        with patch('main.pending_examples', [mock_example]):
            response = client.get("/api/v1/examples/test-event-123", headers=headers)
            assert response.status_code == 200
            assert response.json()["event_id"] == "test-event-123"
    
    def test_label_example_requires_write_scope(self, client, limited_scope_token):
        """Test that labeling requires annotation:write scope."""
        headers = {"Authorization": f"Bearer {limited_scope_token}"}
        
        mock_example = {
            "event_id": "test-event-123",
            "camera_id": "cam-01",
            "timestamp": "2023-01-01T12:00:00Z",
            "detections": []
        }
        
        with patch('main.pending_examples', [mock_example]):
            response = client.post(
                "/api/v1/examples/test-event-123/label",
                headers=headers,
                data={
                    "annotator_id": "test-annotator",
                    "quality_score": 1.0
                },
                json={"corrected_detections": []}
            )
            assert response.status_code == 403
            assert "insufficient privileges" in response.json()["detail"].lower()
    
    def test_label_example_with_valid_scope(self, client, valid_token):
        """Test that labeling works with proper scope."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        mock_example = {
            "event_id": "test-event-123",
            "camera_id": "cam-01",
            "timestamp": "2023-01-01T12:00:00Z",
            "detections": []
        }
        
        mock_producer = MagicMock()
        
        with patch('main.pending_examples', [mock_example]), \
             patch('main.producer', mock_producer):
            
            response = client.post(
                "/api/v1/examples/test-event-123/label",
                headers=headers,
                data={
                    "annotator_id": "test-annotator",
                    "quality_score": 1.0,
                    "corrected_detections": "[]"  # Form data as string
                }
            )
            assert response.status_code == 200
            assert response.json()["status"] == "success"
            mock_producer.produce.assert_called_once()
    
    def test_skip_example_requires_write_scope(self, client, limited_scope_token):
        """Test that skipping examples requires annotation:write scope."""
        headers = {"Authorization": f"Bearer {limited_scope_token}"}
        
        response = client.delete("/api/v1/examples/test-event-123", headers=headers)
        assert response.status_code == 403
    
    def test_skip_example_with_valid_scope(self, client, valid_token):
        """Test that skipping works with proper scope."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        mock_example = {
            "event_id": "test-event-123",
            "camera_id": "cam-01"
        }
        
        with patch('main.pending_examples', [mock_example]):
            response = client.delete("/api/v1/examples/test-event-123", headers=headers)
            assert response.status_code == 200
            assert response.json()["status"] == "skipped"
    
    def test_stats_requires_auth(self, client):
        """Test that /api/v1/stats requires authentication."""
        response = client.get("/api/v1/stats")
        assert response.status_code == 401
    
    def test_stats_with_valid_token(self, client, valid_token):
        """Test that /api/v1/stats works with valid token."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        response = client.get("/api/v1/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "pending_examples" in data
        assert "topics" in data


class TestAuthorizationHeaders:
    """Test various authorization header formats."""
    
    def test_missing_authorization_header(self, client):
        """Test request without Authorization header."""
        response = client.get("/api/v1/examples")
        assert response.status_code == 401
    
    def test_invalid_authorization_scheme(self, client, valid_token):
        """Test with invalid authorization scheme (not Bearer)."""
        headers = {"Authorization": f"Basic {valid_token}"}
        response = client.get("/api/v1/examples", headers=headers)
        assert response.status_code == 401
    
    def test_malformed_authorization_header(self, client):
        """Test with malformed Authorization header."""
        headers = {"Authorization": "Bearer"}  # Missing token
        response = client.get("/api/v1/examples", headers=headers)
        assert response.status_code == 401
    
    def test_empty_bearer_token(self, client):
        """Test with empty bearer token."""
        headers = {"Authorization": "Bearer "}
        response = client.get("/api/v1/examples", headers=headers)
        assert response.status_code == 401


class TestTokenCreation:
    """Test token creation helper functions."""
    
    def test_create_test_token_basic(self):
        """Test basic token creation."""
        token = create_test_token("test-user")
        token_data = verify_jwt_token(token)
        
        assert token_data.sub == "test-user"
        assert token_data.scopes == []
        assert token_data.roles == []
    
    def test_create_test_token_with_scopes_and_roles(self):
        """Test token creation with scopes and roles."""
        token = create_test_token(
            "test-user",
            scopes=["read", "write"],
            roles=["admin", "user"]
        )
        token_data = verify_jwt_token(token)
        
        assert token_data.sub == "test-user"
        assert token_data.scopes == ["read", "write"]
        assert token_data.roles == ["admin", "user"]
    
    def test_create_test_token_custom_expiration(self):
        """Test token creation with custom expiration."""
        short_expiry = timedelta(minutes=5)
        token = create_test_token("test-user", expires_delta=short_expiry)
        token_data = verify_jwt_token(token)
        
        # Should expire within the next 5 minutes
        expected_exp = datetime.utcnow() + short_expiry
        actual_exp = datetime.fromtimestamp(token_data.exp)
        
        # Allow some tolerance for processing time
        assert abs((actual_exp - expected_exp).total_seconds()) < 5


class TestPublicEndpoints:
    """Test that public endpoints don't require authentication."""
    
    def test_health_endpoint_public(self, client):
        """Test that health endpoint is publicly accessible."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data


# Integration test
class TestEndToEndAuthentication:
    """End-to-end authentication tests."""
    
    def test_full_annotation_workflow_with_auth(self, client, valid_token):
        """Test complete annotation workflow with authentication."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Mock data
        mock_example = {
            "event_id": "e2e-test-123",
            "camera_id": "cam-01",
            "timestamp": "2023-01-01T12:00:00Z",
            "detections": [{"class": "person", "confidence": 0.8}]
        }
        
        mock_producer = MagicMock()
        
        with patch('main.pending_examples', [mock_example]), \
             patch('main.producer', mock_producer):
            
            # 1. Get list of examples
            response = client.get("/api/v1/examples", headers=headers)
            assert response.status_code == 200
            
            # 2. Get specific example
            response = client.get("/api/v1/examples/e2e-test-123", headers=headers)
            assert response.status_code == 200
            
            # 3. Label the example
            response = client.post(
                "/api/v1/examples/e2e-test-123/label",
                headers=headers,
                data={
                    "annotator_id": "e2e-tester",
                    "quality_score": 0.95,
                    "corrected_detections": "[]"
                }
            )
            assert response.status_code == 200
            
            # 4. Check stats
            response = client.get("/api/v1/stats", headers=headers)
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__])

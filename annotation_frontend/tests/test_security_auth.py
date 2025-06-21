"""
Security Authentication Tests for Annotation Frontend

Tests JWT authentication and role-based access control for all secured endpoints.
Updated to test:
1. POST annotation without token → 401
2. POST annotation with wrong role → 403
3. Data subject deletion access control
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from main import app
from auth import create_test_token
from database import get_db
from models import AnnotationExample, AnnotationStatus

# Override database dependency for testing
@pytest.fixture
def client():
    """Test client with database override"""
    return TestClient(app)

@pytest.fixture
def mock_db():
    """Mock database session"""
    from unittest.mock import Mock
    db = Mock()
    # Mock query result
    mock_query = Mock()
    mock_query.filter.return_value.count.return_value = 5
    db.query.return_value = mock_query
    return db

@pytest.fixture
def annotator_token():
    """Valid JWT token for annotator role"""
    return create_test_token(
        subject="test_annotator",
        roles=["annotator"],
        scopes=["annotation:read", "annotation:write"],
        expires_delta=timedelta(hours=1)
    )

@pytest.fixture
def compliance_officer_token():
    """Valid JWT token for compliance officer role"""
    return create_test_token(
        subject="test_compliance",
        roles=["compliance_officer"],
        scopes=["data:read", "data:delete", "annotation:read"],
        expires_delta=timedelta(hours=1)
    )

@pytest.fixture
def regular_user_token():
    """JWT token for user without required roles"""
    return create_test_token(
        subject="test_user",
        roles=["user"],
        scopes=["read:basic"],
        expires_delta=timedelta(hours=1)
    )

@pytest.fixture
def expired_token():
    """Expired JWT token"""
    return create_test_token(
        subject="test_user",
        roles=["annotator"],
        scopes=["annotation:read", "annotation:write"],
        expires_delta=timedelta(seconds=-1)  # Already expired
    )

class TestAuthenticationEndpoints:
    """Test authentication requirements for all endpoints"""
    
    def test_login_endpoint_public(self, client):
        """Test that login endpoint is accessible without authentication"""
        response = client.post("/api/v1/login", data={
            "username": "annotator",
            "password": "annotator_pass"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post("/api/v1/login", data={
            "username": "invalid",
            "password": "invalid"
        })
        assert response.status_code == 401
        
    def test_csrf_token_endpoint_public(self, client):
        """Test that CSRF token endpoint is accessible without authentication"""
        response = client.get("/api/v1/csrf-token")
        assert response.status_code == 200
        data = response.json()
        assert "csrf_token" in data
    
    def test_health_endpoint_public(self, client):
        """Test that health endpoint is accessible without authentication"""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_get_examples_requires_auth(self, client):
        """Test that getting examples requires authentication"""
        response = client.get("/api/v1/examples")
        assert response.status_code == 401
        
    def test_get_examples_with_valid_token(self, client, annotator_token, mock_db):
        """Test that getting examples works with valid annotator token"""
        # Override the get_db dependency
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get(
                "/api/v1/examples",
                headers={"Authorization": f"Bearer {annotator_token}"}
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()
    
    def test_get_examples_wrong_role(self, client, regular_user_token, mock_db):
        """Test that getting examples fails with wrong role"""
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get(
                "/api/v1/examples",
                headers={"Authorization": f"Bearer {regular_user_token}"}
            )
            assert response.status_code == 403
            data = response.json()
            assert "Insufficient privileges" in data["detail"]
        finally:
            app.dependency_overrides.clear()
    
    def test_get_specific_example_requires_auth(self, client):
        """Test that getting specific example requires authentication"""
        response = client.get("/api/v1/examples/test-event-id")
        assert response.status_code == 401
    
    def test_post_annotation_requires_auth(self, client):
        """Test that posting annotation requires authentication"""
        response = client.post("/api/v1/examples/test-event-id/label", json={
            "corrected_detections": [],
            "annotator_id": "test",
            "quality_score": 1.0
        })
        assert response.status_code == 401
    
    def test_post_annotation_wrong_role(self, client, compliance_officer_token):
        """Test that posting annotation fails without annotator role"""
        # Get CSRF token first
        csrf_response = client.get("/api/v1/csrf-token")
        csrf_token = csrf_response.json()["csrf_token"]
        
        response = client.post(
            "/api/v1/examples/test-event-id/label",
            headers={
                "Authorization": f"Bearer {compliance_officer_token}",
                "X-CSRF-Token": csrf_token
            },
            data={
                "csrf_token": csrf_token,
                "corrected_detections": "[]",
                "annotator_id": "test",
                "quality_score": "1.0"
            }
        )
        assert response.status_code == 403
        data = response.json()
        assert "Insufficient privileges" in data["detail"]
    
    def test_skip_example_requires_auth(self, client):
        """Test that skipping example requires authentication"""
        response = client.delete("/api/v1/examples/test-event-id")
        assert response.status_code == 401
    
    def test_skip_example_wrong_role(self, client, compliance_officer_token):
        """Test that skipping example fails without annotator role"""
        response = client.delete(
            "/api/v1/examples/test-event-id",
            headers={
                "Authorization": f"Bearer {compliance_officer_token}",
                "X-CSRF-Token": "dummy"
            }
        )
        assert response.status_code == 403
    
    def test_data_subject_delete_requires_auth(self, client):
        """Test that data subject deletion requires authentication"""
        response = client.post("/data-subject/delete", json={
            "face_hash_id": "a" * 64
        })
        assert response.status_code == 401
    
    def test_data_subject_delete_wrong_role(self, client, annotator_token):
        """Test that data subject deletion fails without compliance officer role"""
        # Get CSRF token first
        csrf_response = client.get("/api/v1/csrf-token")
        csrf_token = csrf_response.json()["csrf_token"]
        
        response = client.post(
            "/data-subject/delete",
            headers={
                "Authorization": f"Bearer {annotator_token}",
                "X-CSRF-Token": csrf_token
            },
            json={"face_hash_id": "a" * 64}
        )
        assert response.status_code == 403
        data = response.json()
        assert "Insufficient privileges" in data["detail"]
    
    def test_stats_endpoint_requires_auth(self, client):
        """Test that stats endpoint requires authentication"""
        response = client.get("/api/v1/stats")
        assert response.status_code == 401
    
    def test_expired_token_rejected(self, client, expired_token):
        """Test that expired tokens are rejected"""
        response = client.get(
            "/api/v1/examples",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "expired" in data["detail"].lower()
    
    def test_invalid_token_rejected(self, client):
        """Test that invalid tokens are rejected"""
        response = client.get(
            "/api/v1/examples",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
    
    def test_malformed_authorization_header(self, client):
        """Test that malformed authorization headers are rejected"""
        response = client.get(
            "/api/v1/examples",
            headers={"Authorization": "InvalidFormat token"}
        )
        assert response.status_code == 401

class TestRoleBasedAccess:
    """Test role-based access control"""
    
    def test_annotator_can_access_annotation_endpoints(self, client, annotator_token, mock_db):
        """Test that annotator can access annotation endpoints"""
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            # Test GET examples
            response = client.get(
                "/api/v1/examples",
                headers={"Authorization": f"Bearer {annotator_token}"}
            )
            assert response.status_code == 200
            
            # Test GET specific example (would fail on missing example, not auth)
            response = client.get(
                "/api/v1/examples/test-event-id",
                headers={"Authorization": f"Bearer {annotator_token}"}
            )
            # Expecting 404 or 500, not 401/403 (auth passed)
            assert response.status_code not in [401, 403]
            
        finally:
            app.dependency_overrides.clear()
    
    def test_compliance_officer_can_access_data_subject_endpoints(self, client, compliance_officer_token, mock_db):
        """Test that compliance officer can access data subject endpoints"""
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            # Get CSRF token first
            csrf_response = client.get("/api/v1/csrf-token")
            csrf_token = csrf_response.json()["csrf_token"]
            
            response = client.post(
                "/data-subject/delete",
                headers={
                    "Authorization": f"Bearer {compliance_officer_token}",
                    "X-CSRF-Token": csrf_token
                },
                json={"face_hash_id": "a" * 64}
            )
            # Should not fail on authorization (might fail on business logic)
            assert response.status_code not in [401, 403]
            
        finally:
            app.dependency_overrides.clear()
    
    def test_admin_has_all_access(self, client, mock_db):
        """Test that admin role has access to all endpoints"""
        admin_token = create_test_token(
            subject="test_admin",
            roles=["admin", "annotator", "compliance_officer"],
            scopes=["annotation:read", "annotation:write", "data:read", "data:delete", "admin:all"],
            expires_delta=timedelta(hours=1)
        )
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            # Test annotation endpoints
            response = client.get(
                "/api/v1/examples",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200
            
            # Test data subject endpoints
            csrf_response = client.get("/api/v1/csrf-token")
            csrf_token = csrf_response.json()["csrf_token"]
            
            response = client.post(
                "/data-subject/delete",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "X-CSRF-Token": csrf_token
                },
                json={"face_hash_id": "a" * 64}
            )
            assert response.status_code not in [401, 403]
            
        finally:
            app.dependency_overrides.clear()

class TestRequiredSecurityTests:
    """Required security tests as per specifications"""
    
    def test_post_annotation_without_token_returns_401(self, client):
        """1. Attempt to POST annotation without token → assert 401."""
        annotation_data = {
            "example_id": "test_example_123",
            "label": "person",
            "bbox": {
                "x1": 0.1,
                "y1": 0.1,
                "x2": 0.9,
                "y2": 0.9
            },
            "confidence": 0.95,
            "notes": "Test annotation"
        }
        
        response = client.post(
            "/api/v1/examples/test_example_123/label",
            json=annotation_data,
            headers={"X-CSRF-Token": "test-csrf-token"}  # Add CSRF but no auth
        )
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    def test_post_annotation_without_annotator_role_returns_403(self, client):
        """2. Use a token without "annotator" role → assert 403."""
        # Create token with compliance_officer role but not annotator
        token = create_test_token(
            subject="compliance_user",
            roles=["compliance_officer"],
            scopes=["data:read", "data:delete"],
            expires_delta=timedelta(hours=1)
        )
        
        annotation_data = {
            "example_id": "test_example_123",
            "label": "person",
            "bbox": {
                "x1": 0.1,
                "y1": 0.1,
                "x2": 0.9,
                "y2": 0.9
            },
            "confidence": 0.95,
            "notes": "Test annotation"
        }
        
        response = client.post(
            "/api/v1/examples/test_example_123/label",
            json=annotation_data,
            headers={
                "Authorization": f"Bearer {token}",
                "X-CSRF-Token": "test-csrf-token"
            }
        )
        
        assert response.status_code == 403
        response_data = response.json()
        assert "detail" in response_data
        assert "annotator" in response_data["detail"].lower()
    
    def test_data_subject_delete_without_compliance_role_returns_403(self, client):
        """Test data-subject delete requires compliance_officer role"""
        # Create token with annotator role but not compliance_officer
        token = create_test_token(
            subject="annotator_user",
            roles=["annotator"],
            scopes=["annotation:read", "annotation:write"],
            expires_delta=timedelta(hours=1)
        )
        
        delete_data = {
            "face_hash_id": "abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"
        }
        
        response = client.post(
            "/data-subject/delete",
            json=delete_data,
            headers={
                "Authorization": f"Bearer {token}",
                "X-CSRF-Token": "test-csrf-token"
            }
        )
        
        assert response.status_code == 403
        response_data = response.json()
        assert "detail" in response_data
        assert "compliance_officer" in response_data["detail"].lower()

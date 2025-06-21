"""
CSRF Protection Tests for Annotation Frontend

Tests CSRF token validation for all state-changing endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import timedelta

from main import app
from auth import create_test_token
from database import get_db

@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)

@pytest.fixture
def mock_db():
    """Mock database session"""
    from unittest.mock import Mock
    db = Mock()
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

class TestCSRFProtection:
    """Test CSRF protection for state-changing requests"""
    
    def test_get_csrf_token(self, client):
        """Test that CSRF token can be obtained"""
        response = client.get("/api/v1/csrf-token")
        assert response.status_code == 200
        data = response.json()
        assert "csrf_token" in data
        assert len(data["csrf_token"]) > 0
        
        # Check that CSRF token is set in cookie
        assert "csrftoken" in response.cookies or "csrf_token" in response.cookies
    
    def test_get_requests_dont_need_csrf(self, client, annotator_token, mock_db):
        """Test that GET requests don't require CSRF tokens"""
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get(
                "/api/v1/examples",
                headers={"Authorization": f"Bearer {annotator_token}"}
            )
            assert response.status_code == 200
            
            response = client.get(
                "/api/v1/examples/test-event-id",
                headers={"Authorization": f"Bearer {annotator_token}"}
            )
            # Should not fail on CSRF (might fail on missing example)
            assert response.status_code != 403 or "CSRF" not in response.json().get("detail", "")
            
        finally:
            app.dependency_overrides.clear()
    
    def test_post_annotation_without_csrf_fails(self, client, annotator_token, mock_db):
        """Test that POST annotation without CSRF token fails"""
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post(
                "/api/v1/examples/test-event-id/label",
                headers={"Authorization": f"Bearer {annotator_token}"},
                json={
                    "corrected_detections": [],
                    "annotator_id": "test",
                    "quality_score": 1.0
                }
            )
            assert response.status_code == 403
            data = response.json()
            assert "CSRF" in data["detail"]
            
        finally:
            app.dependency_overrides.clear()
    
    def test_post_annotation_with_invalid_csrf_fails(self, client, annotator_token, mock_db):
        """Test that POST annotation with invalid CSRF token fails"""
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post(
                "/api/v1/examples/test-event-id/label",
                headers={
                    "Authorization": f"Bearer {annotator_token}",
                    "X-CSRF-Token": "invalid_csrf_token"
                },
                data={
                    "csrf_token": "invalid_csrf_token",
                    "corrected_detections": "[]",
                    "annotator_id": "test",
                    "quality_score": "1.0"
                }
            )
            assert response.status_code == 403
            data = response.json()
            assert "CSRF" in data["detail"]
            
        finally:
            app.dependency_overrides.clear()
    
    def test_post_annotation_with_valid_csrf_succeeds(self, client, annotator_token, mock_db):
        """Test that POST annotation with valid CSRF token succeeds (auth-wise)"""
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            # First get a valid CSRF token
            csrf_response = client.get("/api/v1/csrf-token")
            assert csrf_response.status_code == 200
            csrf_token = csrf_response.json()["csrf_token"]
            
            # Mock the annotation service to avoid business logic errors
            from unittest.mock import Mock, patch
            with patch('main.AnnotationService') as mock_service:
                mock_example = Mock()
                mock_example.camera_id = "test-camera"
                mock_example.timestamp = "2024-01-01T00:00:00"
                mock_example.frame_data = ""
                mock_example.original_detections = []
                mock_service.submit_annotation.return_value = mock_example
                
                with patch('main.kafka_pool') as mock_kafka:
                    mock_kafka.send_message.return_value = True
                    
                    response = client.post(
                        "/api/v1/examples/test-event-id/label",
                        headers={
                            "Authorization": f"Bearer {annotator_token}",
                            "X-CSRF-Token": csrf_token
                        },
                        data={
                            "csrf_token": csrf_token,
                            "corrected_detections": "[]",
                            "annotator_id": "test",
                            "quality_score": "1.0"
                        },
                        cookies=csrf_response.cookies
                    )
                    # Should not fail on CSRF/auth (might fail on business logic)
                    assert response.status_code not in [401, 403] or "CSRF" not in response.json().get("detail", "")
            
        finally:
            app.dependency_overrides.clear()
    
    def test_delete_without_csrf_fails(self, client, annotator_token, mock_db):
        """Test that DELETE request without CSRF token fails"""
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.delete(
                "/api/v1/examples/test-event-id",
                headers={"Authorization": f"Bearer {annotator_token}"}
            )
            assert response.status_code == 403
            data = response.json()
            assert "CSRF" in data["detail"]
            
        finally:
            app.dependency_overrides.clear()
    
    def test_delete_with_valid_csrf_succeeds(self, client, annotator_token, mock_db):
        """Test that DELETE request with valid CSRF token succeeds (auth-wise)"""
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            # First get a valid CSRF token
            csrf_response = client.get("/api/v1/csrf-token")
            csrf_token = csrf_response.json()["csrf_token"]
            
            # Mock the annotation service
            from unittest.mock import Mock, patch
            with patch('main.AnnotationService') as mock_service:
                mock_service.skip_example.return_value = Mock()
                
                response = client.delete(
                    "/api/v1/examples/test-event-id",
                    headers={
                        "Authorization": f"Bearer {annotator_token}",
                        "X-CSRF-Token": csrf_token
                    },
                    cookies=csrf_response.cookies
                )
                # Should not fail on CSRF/auth
                assert response.status_code not in [401, 403] or "CSRF" not in response.json().get("detail", "")
            
        finally:
            app.dependency_overrides.clear()
    
    def test_data_subject_delete_without_csrf_fails(self, client, compliance_officer_token, mock_db):
        """Test that data subject deletion without CSRF token fails"""
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post(
                "/data-subject/delete",
                headers={"Authorization": f"Bearer {compliance_officer_token}"},
                json={"face_hash_id": "a" * 64}
            )
            assert response.status_code == 403
            data = response.json()
            assert "CSRF" in data["detail"]
            
        finally:
            app.dependency_overrides.clear()
    
    def test_data_subject_delete_with_valid_csrf_succeeds(self, client, compliance_officer_token, mock_db):
        """Test that data subject deletion with valid CSRF token succeeds (auth-wise)"""
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            # First get a valid CSRF token
            csrf_response = client.get("/api/v1/csrf-token")
            csrf_token = csrf_response.json()["csrf_token"]
            
            # Mock database operations to avoid actual deletion
            from unittest.mock import Mock, patch
            with patch('data_subject.is_s3_path', return_value=False):
                mock_db.execute = Mock()
                mock_db.commit = Mock()
                
                # Mock the query results
                mock_result = Mock()
                mock_result.fetchall.return_value = []  # No matching events
                mock_db.execute.return_value = mock_result
                
                response = client.post(
                    "/data-subject/delete",
                    headers={
                        "Authorization": f"Bearer {compliance_officer_token}",
                        "X-CSRF-Token": csrf_token
                    },
                    json={"face_hash_id": "a" * 64},
                    cookies=csrf_response.cookies
                )
                # Should not fail on CSRF/auth
                assert response.status_code not in [401, 403] or "CSRF" not in response.json().get("detail", "")
            
        finally:
            app.dependency_overrides.clear()
    
    def test_login_endpoint_exempt_from_csrf(self, client):
        """Test that login endpoint is exempt from CSRF protection"""
        response = client.post("/api/v1/login", data={
            "username": "annotator",
            "password": "annotator_pass"
        })
        # Should succeed without CSRF token
        assert response.status_code == 200
    
    def test_health_endpoint_exempt_from_csrf(self, client):
        """Test that health endpoint is exempt from CSRF protection"""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_csrf_token_endpoint_exempt_from_csrf(self, client):
        """Test that CSRF token endpoint is exempt from CSRF protection"""
        response = client.get("/api/v1/csrf-token")
        assert response.status_code == 200

class TestCSRFTokenManagement:
    """Test CSRF token lifecycle and management"""
    
    def test_csrf_token_format(self, client):
        """Test that CSRF token has expected format"""
        response = client.get("/api/v1/csrf-token")
        data = response.json()
        csrf_token = data["csrf_token"]
        
        # Token should be a non-empty string
        assert isinstance(csrf_token, str)
        assert len(csrf_token) > 10  # Should be reasonably long
    
    def test_csrf_token_uniqueness(self, client):
        """Test that each CSRF token request returns a unique token"""
        response1 = client.get("/api/v1/csrf-token")
        response2 = client.get("/api/v1/csrf-token")
        
        token1 = response1.json()["csrf_token"]
        token2 = response2.json()["csrf_token"]
        
        # Tokens should be different (very high probability)
        assert token1 != token2
    
    def test_csrf_cookie_set(self, client):
        """Test that CSRF token is properly set in cookie"""
        response = client.get("/api/v1/csrf-token")
        
        # Check that a CSRF-related cookie is set
        cookie_names = [name.lower() for name in response.cookies.keys()]
        assert any('csrf' in name for name in cookie_names)
    
    def test_missing_csrf_header_error_message(self, client, annotator_token):
        """Test that missing CSRF header gives clear error message"""
        response = client.post(
            "/api/v1/examples/test-event-id/label",
            headers={"Authorization": f"Bearer {annotator_token}"},
            json={"test": "data"}
        )
        assert response.status_code == 403
        data = response.json()
        assert "CSRF" in data["detail"]
        assert "Missing X-CSRF-Token header" in data["detail"]

class TestRequiredCSRFTests:
    """Required CSRF tests as per specifications"""
    
    def test_get_csrf_token_endpoint(self, client):
        """1. GET `/` to fetch `csrf_token` cookie."""
        response = client.get("/api/v1/csrf-token")
        assert response.status_code == 200
        
        data = response.json()
        assert "csrf_token" in data
        assert len(data["csrf_token"]) > 0
        
        # Check if CSRF cookie is set
        assert "csrf_token" in response.cookies or "Set-Cookie" in response.headers
    
    def test_post_without_csrf_token_returns_403(self, client, annotator_token):
        """2. POST without `X-CSRF-Token` → assert 403."""
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
                "Authorization": f"Bearer {annotator_token}"
                # Missing X-CSRF-Token header
            }
        )
        
        assert response.status_code == 403
        response_data = response.json()
        assert "detail" in response_data
        assert "csrf" in response_data["detail"].lower()
    
    def test_post_with_valid_token_and_csrf_succeeds_auth(self, client, annotator_token):
        """3. POST with valid token & header → should pass authentication/CSRF checks."""
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
        
        # First get CSRF token
        csrf_response = client.get("/api/v1/csrf-token")
        csrf_token = csrf_response.json()["csrf_token"]
        
        response = client.post(
            "/api/v1/examples/test_example_123/label",
            json=annotation_data,
            headers={
                "Authorization": f"Bearer {annotator_token}",
                "X-CSRF-Token": csrf_token
            },
            cookies=csrf_response.cookies  # Include CSRF cookie from first request
        )
        
        # Should not be 401 (auth) or 403 (CSRF/role) - may be 404 (example not found) or 200
        assert response.status_code not in [401, 403]
    
    def test_csrf_protection_applies_to_all_state_changing_methods(self, client, annotator_token):
        """Test CSRF protection applies to POST, PUT, PATCH, DELETE"""
        headers_without_csrf = {
            "Authorization": f"Bearer {annotator_token}"
        }
        
        # Test POST
        response = client.post(
            "/api/v1/examples/test123/label",
            json={"example_id": "test123", "label": "test"},
            headers=headers_without_csrf
        )
        assert response.status_code == 403
        
        # Test PUT (if exists)
        response = client.put(
            "/api/v1/examples/test123",
            json={"example_id": "test123", "label": "test"},
            headers=headers_without_csrf
        )
        # Should be 403 for CSRF or 405/404 if endpoint doesn't exist
        assert response.status_code in [403, 404, 405]
        
        # Test PATCH (if exists)
        response = client.patch(
            "/api/v1/examples/test123",
            json={"label": "test"},
            headers=headers_without_csrf
        )
        assert response.status_code in [403, 404, 405]
        
        # Test DELETE for data subject (with compliance officer token)
        compliance_token = create_test_token(
            subject="compliance_user",
            roles=["compliance_officer"],
            scopes=["data:read", "data:delete"],
            expires_delta=timedelta(hours=1)
        )
        
        response = client.post(
            "/data-subject/delete",
            json={"face_hash_id": "abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"},
            headers={"Authorization": f"Bearer {compliance_token}"}  # No CSRF
        )
        assert response.status_code == 403
    
    def test_csrf_protection_skips_safe_methods(self, client, annotator_token):
        """Test CSRF protection doesn't apply to GET, HEAD, OPTIONS"""
        headers = {
            "Authorization": f"Bearer {annotator_token}"
            # No X-CSRF-Token header
        }
        
        # GET should work without CSRF token
        response = client.get("/api/v1/examples", headers=headers)
        # Should not be 403 due to CSRF (may be other errors)
        assert response.status_code != 403 or "csrf" not in response.json().get("detail", "").lower()
        
        # HEAD should work without CSRF token
        response = client.head("/api/v1/examples", headers=headers)
        # Should not be 403 due to CSRF
        assert response.status_code != 403
        
        # OPTIONS should work without CSRF token
        response = client.options("/api/v1/examples", headers=headers)
        # Should not be 403 due to CSRF
        assert response.status_code != 403
    
    def test_login_and_csrf_token_endpoints_exempt_from_csrf(self, client):
        """Test that login and csrf-token endpoints are exempt from CSRF protection"""
        # Login endpoint should work without CSRF token
        response = client.post("/api/v1/login", data={
            "username": "annotator",
            "password": "annotator_pass"
        })
        assert response.status_code in [200, 401]  # Not 403 for CSRF
        
        # CSRF token endpoint should work without CSRF token
        response = client.get("/api/v1/csrf-token")
        assert response.status_code == 200

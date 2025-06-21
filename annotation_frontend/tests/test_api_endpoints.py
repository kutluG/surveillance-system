"""
Unit tests for API endpoints in the annotation frontend service.

Tests FastAPI endpoints with TestClient to validate:
- Request/response handling
- Authentication and authorization
- Input validation
- Database interactions
- Error handling
"""
import pytest
import json
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import status

from main import app, pending_examples
from models import AnnotationExample, AnnotationStatus
from database import get_db


class TestGetPendingExamples:
    """Test the GET /api/v1/examples endpoint."""
    
    def test_get_examples_empty_db(self, client):
        """Test GET /api/v1/examples returns empty list when no examples."""
        # Ensure pending_examples is empty
        pending_examples.clear()
        
        response = client.get("/api/v1/examples")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["examples"] == []
        assert data["total"] == 0
    
    def test_get_examples_with_data(self, client, sample_hard_example):
        """Test GET /api/v1/examples returns examples when available."""
        # Add sample data to pending_examples
        pending_examples.clear()
        pending_examples.append(sample_hard_example)
        
        response = client.get("/api/v1/examples")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["examples"]) == 1
        assert data["total"] == 1
        assert data["examples"][0]["event_id"] == "test-event-123"
    
    def test_get_examples_pagination(self, client, sample_hard_example):
        """Test GET /api/v1/examples respects pagination settings."""
        # Add multiple examples (more than page size)
        pending_examples.clear()
        for i in range(15):
            example = sample_hard_example.copy()
            example["event_id"] = f"test-event-{i}"
            pending_examples.append(example)
        
        response = client.get("/api/v1/examples")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should return last 10 (ANNOTATION_PAGE_SIZE from test_settings)
        assert len(data["examples"]) == 10
        assert data["total"] == 15
        # Should return the last 10 examples
        assert data["examples"][0]["event_id"] == "test-event-5"
        assert data["examples"][-1]["event_id"] == "test-event-14"
    
    def test_get_examples_requires_auth(self, test_db):
        """Test GET /api/v1/examples requires authentication."""
        # Create client without auth override
        with TestClient(app) as unauthenticated_client:
            app.dependency_overrides.clear()  # Remove auth override
            
            def override_get_db():
                session = test_db()
                try:
                    yield session
                finally:
                    session.close()
            
            app.dependency_overrides[get_db] = override_get_db
            
            response = unauthenticated_client.get("/api/v1/examples")
            
            # Should return 401 or 403 (depending on auth implementation)
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


class TestGetSpecificExample:
    """Test the GET /api/v1/examples/{event_id} endpoint."""
    
    def test_get_existing_example(self, client, sample_hard_example):
        """Test GET /api/v1/examples/{event_id} returns specific example."""
        pending_examples.clear()
        pending_examples.append(sample_hard_example)
        
        response = client.get("/api/v1/examples/test-event-123")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["event_id"] == "test-event-123"
        assert data["camera_id"] == "camera-001"
    
    def test_get_nonexistent_example(self, client):
        """Test GET /api/v1/examples/{event_id} returns 404 for non-existent example."""
        pending_examples.clear()
        
        response = client.get("/api/v1/examples/nonexistent-id")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()


class TestLabelExample:
    """Test the POST /api/v1/examples/{event_id}/label endpoint."""
    
    @patch('main.producer')
    def test_label_example_success(self, mock_producer, client, sample_hard_example, sample_labeled_detection):
        """Test successful labeling of an example."""
        # Setup mock producer
        mock_producer.produce = Mock()
        mock_producer.poll = Mock()
        
        # Add example to pending list
        pending_examples.clear()
        pending_examples.append(sample_hard_example)
        
        # Prepare form data
        form_data = {
            "annotator_id": "test-annotator",
            "quality_score": "0.9",
            "notes": "Good annotation"
        }
        
        # Prepare JSON data for corrected_detections
        json_data = [sample_labeled_detection]
        
        response = client.post(
            "/api/v1/examples/test-event-123/label",
            data=form_data,
            json=json_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["event_id"] == "test-event-123"
        
        # Verify example was removed from pending list
        assert len(pending_examples) == 0
        
        # Verify Kafka producer was called
        mock_producer.produce.assert_called_once()
        mock_producer.poll.assert_called_once_with(0)
    
    def test_label_nonexistent_example(self, client, sample_labeled_detection):
        """Test labeling non-existent example returns 404."""
        pending_examples.clear()
        
        form_data = {
            "annotator_id": "test-annotator",
            "quality_score": "0.9"
        }
        
        response = client.post(
            "/api/v1/examples/nonexistent-id/label",
            data=form_data,
            json=[sample_labeled_detection]
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_label_example_invalid_bbox(self, client, sample_hard_example, invalid_bbox_data):
        """Test labeling with invalid bounding box data returns 422."""
        pending_examples.clear()
        pending_examples.append(sample_hard_example)
        
        form_data = {
            "annotator_id": "test-annotator",
            "quality_score": "0.9"
        }
        
        # Test each invalid bbox case
        for invalid_bbox in invalid_bbox_data:
            invalid_detection = {
                "bbox": invalid_bbox,
                "class_name": "person",
                "confidence": 0.75,
                "is_correct": True
            }
            
            response = client.post(
                "/api/v1/examples/test-event-123/label",
                data=form_data,
                json=[invalid_detection]
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_label_example_missing_required_fields(self, client, sample_hard_example):
        """Test labeling without required fields returns 422."""
        pending_examples.clear()
        pending_examples.append(sample_hard_example)
        
        # Missing annotator_id
        response = client.post(
            "/api/v1/examples/test-event-123/label",
            data={"quality_score": "0.9"},
            json=[]
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('main.producer')
    def test_label_example_kafka_failure(self, mock_producer, client, sample_hard_example, sample_labeled_detection):
        """Test handling of Kafka producer failure."""
        # Setup mock producer to fail
        mock_producer.produce.side_effect = Exception("Kafka connection failed")
        
        pending_examples.clear()
        pending_examples.append(sample_hard_example)
        
        form_data = {
            "annotator_id": "test-annotator",
            "quality_score": "0.9"
        }
        
        response = client.post(
            "/api/v1/examples/test-event-123/label",
            data=form_data,
            json=[sample_labeled_detection]
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to save annotation" in response.json()["detail"]


class TestSkipExample:
    """Test the DELETE /api/v1/examples/{event_id} endpoint."""
    
    def test_skip_existing_example(self, client, sample_hard_example):
        """Test skipping an existing example."""
        pending_examples.clear()
        pending_examples.append(sample_hard_example)
        
        response = client.delete("/api/v1/examples/test-event-123")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "skipped"
        assert data["event_id"] == "test-event-123"
        
        # Verify example was removed from pending list
        assert len(pending_examples) == 0
    
    def test_skip_nonexistent_example(self, client):
        """Test skipping non-existent example returns 404."""
        pending_examples.clear()
        
        response = client.delete("/api/v1/examples/nonexistent-id")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestHealthEndpoint:
    """Test the GET /health endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint returns success."""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "annotation_frontend"
        assert "pending_examples" in data
        assert isinstance(data["pending_examples"], int)


class TestStatsEndpoint:
    """Test the GET /api/v1/stats endpoint."""
    
    def test_get_stats(self, client, sample_hard_example):
        """Test stats endpoint returns correct information."""
        pending_examples.clear()
        pending_examples.append(sample_hard_example)
        
        response = client.get("/api/v1/stats")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pending_examples"] == 1
        assert "topics" in data
        assert "input" in data["topics"]
        assert "output" in data["topics"]
    
    def test_stats_requires_auth(self, test_db):
        """Test stats endpoint requires authentication."""
        with TestClient(app) as unauthenticated_client:
            app.dependency_overrides.clear()
            
            def override_get_db():
                session = test_db()
                try:
                    yield session
                finally:
                    session.close()
            
            app.dependency_overrides[get_db] = override_get_db
            
            response = unauthenticated_client.get("/api/v1/stats")
            
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


class TestMainPageEndpoint:
    """Test the GET / endpoint (main annotation interface)."""
    
    def test_main_page_loads(self, client):
        """Test main annotation page loads successfully."""
        response = client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]
    
    def test_main_page_context(self, client, sample_hard_example):
        """Test main annotation page includes correct context."""
        pending_examples.clear()
        pending_examples.append(sample_hard_example)
        
        response = client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        # Should include pending_count and config in template context
        assert "text/html" in response.headers["content-type"]


class TestAuthorizationScopes:
    """Test endpoint authorization with different scopes."""
    
    def test_label_endpoint_requires_write_scope(self, test_db):
        """Test that labeling endpoint requires annotation:write scope."""
        from auth import get_current_user, TokenData
        
        # Create user with only read scope
        read_only_user = TokenData(
            sub="read-only-user",
            scopes=["annotation:read"]
        )
        
        def override_get_db():
            session = test_db()
            try:
                yield session
            finally:
                session.close()
        
        def override_get_current_user():
            return read_only_user
        
        with TestClient(app) as test_client:
            app.dependency_overrides[get_db] = override_get_db
            app.dependency_overrides[get_current_user] = override_get_current_user
            
            form_data = {"annotator_id": "test-annotator"}
            response = test_client.post(
                "/api/v1/examples/test-event-123/label",
                data=form_data,
                json=[]
            )
            
            # Should fail due to insufficient scope
            assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_skip_endpoint_requires_write_scope(self, test_db):
        """Test that skip endpoint requires annotation:write scope."""
        from auth import get_current_user, TokenData
        
        read_only_user = TokenData(
            sub="read-only-user", 
            scopes=["annotation:read"]
        )
        
        def override_get_db():
            session = test_db()
            try:
                yield session
            finally:
                session.close()
        
        def override_get_current_user():
            return read_only_user
        
        with TestClient(app) as test_client:
            app.dependency_overrides[get_db] = override_get_db
            app.dependency_overrides[get_current_user] = override_get_current_user
            
            response = test_client.delete("/api/v1/examples/test-event-123")
            
            assert response.status_code == status.HTTP_403_FORBIDDEN

"""
Integration tests for the temporal RAG endpoint

Tests the complete /rag/query endpoint functionality including:
- Request validation
- Response structure
- Error handling
- Integration with temporal processing
"""

import pytest
from fastapi.testclient import TestClient
import json
from unittest.mock import Mock, patch, AsyncMock

# Mock dependencies
import sys
import types

# Mock sentence_transformers
mock_sentence_transformers = types.ModuleType("sentence_transformers")
mock_sentence_transformers.SentenceTransformer = Mock
sys.modules["sentence_transformers"] = mock_sentence_transformers

# Mock weaviate
mock_weaviate = types.ModuleType("weaviate")
mock_weaviate.connect_to_custom = Mock()
mock_weaviate.AuthApiKey = Mock()
mock_weaviate.classes = types.ModuleType("weaviate.classes")
mock_weaviate.classes.config = types.ModuleType("weaviate.classes.config")
mock_weaviate.classes.config.Configure = Mock()
mock_weaviate.classes.config.Property = Mock()
mock_weaviate.classes.config.DataType = Mock()
mock_weaviate.classes.query = types.ModuleType("weaviate.classes.query")
mock_weaviate.classes.query.MetadataQuery = Mock()
sys.modules["weaviate"] = mock_weaviate
sys.modules["weaviate.classes"] = mock_weaviate.classes

# Mock advanced_rag before importing main
mock_advanced_rag = types.ModuleType("advanced_rag")

# Create a proper mock for QueryEvent that behaves like a dataclass
class MockQueryEvent:
    def __init__(self, camera_id, timestamp, label, bbox=None):
        self.camera_id = camera_id
        self.timestamp = timestamp
        self.label = label
        self.bbox = bbox

# Create a proper mock for TemporalRAGResponse that behaves like a dataclass
class MockTemporalRAGResponse:
    def __init__(self, linked_explanation, retrieved_context):
        self.linked_explanation = linked_explanation
        self.retrieved_context = retrieved_context

# Create async mock for rag_service with default return value
mock_rag_service = Mock()
default_response = MockTemporalRAGResponse(
    linked_explanation="Default test response",
    retrieved_context=[]
)
mock_rag_service.process_temporal_query = AsyncMock(return_value=default_response)

mock_advanced_rag.rag_service = mock_rag_service
mock_advanced_rag.QueryEvent = MockQueryEvent
mock_advanced_rag.TemporalRAGResponse = MockTemporalRAGResponse
sys.modules["advanced_rag"] = mock_advanced_rag

# Now import main after mocking  
from main import app

client = TestClient(app)


class TestTemporalRAGEndpoint:
    """Integration tests for /rag/query endpoint"""

    @pytest.fixture
    def valid_request_payload(self):
        """Valid request payload for testing"""
        return {
            "query_event": {
                "camera_id": "cam_001",
                "timestamp": "2025-06-06T10:30:00Z",
                "label": "person_detected",
                "bbox": {
                    "x": 100.0,
                    "y": 150.0,
                    "width": 50.0,
                    "height": 100.0
                }
            },
            "k": 5
        }

    @pytest.fixture
    def mock_temporal_response(self):
        """Mock temporal RAG response"""
        return {
            "linked_explanation": "Analysis shows a temporal sequence where a person was detected entering the monitored area. This event appears to be part of a normal access pattern based on the chronological context of similar detection events in the same camera zone.",
            "retrieved_context": [
                {
                    "id": "event_1",
                    "properties": {
                        "camera_id": "cam_001",
                        "timestamp": "2025-06-06T10:25:00Z",
                        "label": "motion_detected",
                        "confidence": 0.88
                    },
                    "distance": 0.15
                },
                {
                    "id": "event_2", 
                    "properties": {
                        "camera_id": "cam_001",
                        "timestamp": "2025-06-06T10:30:00Z",
                        "label": "person_walking",
                        "confidence": 0.92
                    },
                    "distance": 0.12
                }
            ]
        }

    def test_temporal_rag_query_success(self, valid_request_payload, mock_temporal_response):
        """Test successful temporal RAG query"""
        # Mock the service response
        from advanced_rag import TemporalRAGResponse
        mock_response = TemporalRAGResponse(
            linked_explanation=mock_temporal_response["linked_explanation"],
            retrieved_context=mock_temporal_response["retrieved_context"]
        )
        
        with patch('main.advanced_rag.rag_service') as mock_service:
            # Make the method async
            async def mock_process_temporal_query(*args, **kwargs):
                return mock_response
            mock_service.process_temporal_query = mock_process_temporal_query
            
            response = client.post("/rag/query", json=valid_request_payload)
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "linked_explanation" in data
            assert "retrieved_context" in data
            assert isinstance(data["retrieved_context"], list)
            
            # Verify content
            assert "temporal sequence" in data["linked_explanation"]
            assert len(data["retrieved_context"]) == 2

    def test_missing_required_fields(self):
        """Test validation for missing required fields"""
        invalid_payloads = [
            # Missing camera_id
            {
                "query_event": {
                    "timestamp": "2025-06-06T10:30:00Z",
                    "label": "person_detected"
                },
                "k": 5
            },
            # Missing timestamp
            {
                "query_event": {
                    "camera_id": "cam_001",
                    "label": "person_detected"
                },
                "k": 5            },
            # Missing label
            {
                "query_event": {
                    "camera_id": "cam_001", 
                    "timestamp": "2025-06-06T10:30:00Z"
                },
                "k": 5
            }        ]
        
        for payload in invalid_payloads:
            response = client.post("/rag/query", json=payload)
            assert response.status_code == 400
            assert "Missing required field" in response.json()["detail"]

    def test_invalid_timestamp_format(self):
        """Test validation for invalid timestamp format"""
        invalid_timestamps = [
            "2025-06-06 10:30:00",  # No timezone
            "2025/06/06T10:30:00Z",  # Wrong date format
            "invalid_timestamp",     # Completely invalid
            "2025-13-32T25:70:00Z"   # Invalid date/time values
        ]
        
        # No mocking needed - validation happens before service is called
        for timestamp in invalid_timestamps:
            payload = {
                "query_event": {
                    "camera_id": "cam_001",
                    "timestamp": timestamp,
                    "label": "person_detected"
                },                "k": 5
            }
            
            response = client.post("/rag/query", json=payload)
            assert response.status_code == 400, f"Expected 400 but got {response.status_code} for timestamp: {timestamp}"
            response_data = response.json()
            assert "ISO 8601 format" in response_data["detail"]

    @patch('main.advanced_rag.rag_service')
    def test_k_parameter_validation(self, mock_service):
        """Test validation for k parameter bounds"""
        base_payload = {
            "query_event": {
                "camera_id": "cam_001",
                "timestamp": "2025-06-06T10:30:00Z",
                "label": "person_detected"
            }
        }

        # Test k too small
        payload_small = {**base_payload, "k": 0}
        response = client.post("/rag/query", json=payload_small)
        assert response.status_code == 422  # Validation error

        # Test k too large
        payload_large = {**base_payload, "k": 101}
        response = client.post("/rag/query", json=payload_large)
        assert response.status_code == 422  # Validation error

        # Test valid k values
        from advanced_rag import TemporalRAGResponse
        mock_response = TemporalRAGResponse(
            linked_explanation="test", 
            retrieved_context=[]
        )
        mock_service.process_temporal_query = AsyncMock(return_value=mock_response)
        
        for k in [1, 10, 50, 100]:
            payload_valid = {**base_payload, "k": k}
            response = client.post("/rag/query", json=payload_valid)
            assert response.status_code == 200

    @patch('main.advanced_rag.rag_service')
    def test_optional_bbox_parameter(self, mock_service):
        """Test that bbox parameter is optional"""
        from advanced_rag import TemporalRAGResponse
        mock_response = TemporalRAGResponse(
            linked_explanation="test", 
            retrieved_context=[]
        )
        mock_service.process_temporal_query = AsyncMock(return_value=mock_response)
        
        # Without bbox
        payload_no_bbox = {
            "query_event": {
                "camera_id": "cam_001",
                "timestamp": "2025-06-06T10:30:00Z",
                "label": "person_detected"
            },
            "k": 5
        }
        response = client.post("/rag/query", json=payload_no_bbox)
        assert response.status_code == 200

    def test_service_error_handling(self, valid_request_payload):
        """Test error handling when service fails"""
        with patch('main.advanced_rag.rag_service') as mock_service:
            mock_service.process_temporal_query.side_effect = Exception("Service unavailable")
            
            response = client.post("/rag/query", json=valid_request_payload)
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]

    def test_malformed_json(self):
        """Test handling of malformed JSON requests"""
        response = client.post("/rag/query", data="invalid json")
        assert response.status_code == 422

    def test_empty_request_body(self):
        """Test handling of empty request body"""
        response = client.post("/rag/query", json={})
        assert response.status_code == 422  # Validation error for missing required fields

    @patch('main.advanced_rag.rag_service')
    def test_bbox_format_validation(self, mock_service):
        """Test various bbox formats are accepted"""
        from advanced_rag import TemporalRAGResponse
        mock_response = TemporalRAGResponse(
            linked_explanation="test", 
            retrieved_context=[]
        )
        mock_service.process_temporal_query = AsyncMock(return_value=mock_response)
        
        valid_bbox_formats = [
            {"x": 100.0, "y": 150.0, "width": 50.0, "height": 100.0},
            {"x": 0, "y": 0, "width": 10, "height": 20},  # Integer values
            {"x": 100.5, "y": 150.7, "width": 50.2, "height": 100.9}  # Decimal values
        ]
        
        for bbox in valid_bbox_formats:
            payload = {
                "query_event": {
                    "camera_id": "cam_001",
                    "timestamp": "2025-06-06T10:30:00Z",
                    "label": "person_detected",
                    "bbox": bbox
                },
                "k": 5
            }
            response = client.post("/rag/query", json=payload)
            assert response.status_code == 200

    @patch('main.advanced_rag.rag_service')
    def test_default_k_parameter(self, mock_service):
        """Test that k parameter defaults to 10 when not specified"""
        from advanced_rag import TemporalRAGResponse
        mock_response = TemporalRAGResponse(
            linked_explanation="test", 
            retrieved_context=[]
        )
        mock_service.process_temporal_query = AsyncMock(return_value=mock_response)
        
        payload_no_k = {
            "query_event": {
                "camera_id": "cam_001",
                "timestamp": "2025-06-06T10:30:00Z",
                "label": "person_detected"
            }
        }
        response = client.post("/rag/query", json=payload_no_k)
        assert response.status_code == 200
        
        # Verify k=10 was used (default value)
        call_args = mock_service.process_temporal_query.call_args
        assert call_args[0][1] == 10  # Second argument is k

    @patch('main.advanced_rag.rag_service')
    def test_response_format_consistency(self, mock_service, valid_request_payload, mock_temporal_response):
        """Test that response format is consistent and complete"""
        from advanced_rag import TemporalRAGResponse
        mock_response = TemporalRAGResponse(
            linked_explanation=mock_temporal_response["linked_explanation"],
            retrieved_context=mock_temporal_response["retrieved_context"]
        )
        mock_service.process_temporal_query = AsyncMock(return_value=mock_response)
        
        response = client.post("/rag/query", json=valid_request_payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify response has exactly the expected fields  
        expected_fields = {"linked_explanation", "retrieved_context"}
        assert set(data.keys()) == expected_fields
        
        # Verify field types
        assert isinstance(data["linked_explanation"], str)
        assert isinstance(data["retrieved_context"], list)
        
        # Verify retrieved_context structure
        for event in data["retrieved_context"]:
            assert isinstance(event, dict)
            if "properties" in event:
                assert isinstance(event["properties"], dict)


if __name__ == "__main__":
    pytest.main([__file__])

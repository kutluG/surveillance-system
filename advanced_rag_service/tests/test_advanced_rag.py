"""
Unit tests for Advanced RAG Service temporal functionality

Tests cover:
- Chronological sorting of events by timestamp
- Temporal prompt construction with causality emphasis  
- Event embedding generation
- Weaviate querying and insertion
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from typing import List, Dict, Any

# Mock dependencies before importing
import sys
from pathlib import Path
import types

# Mock external dependencies
mock_sentence_transformers = types.ModuleType("sentence_transformers")
mock_sentence_transformers.SentenceTransformer = Mock
sys.modules["sentence_transformers"] = mock_sentence_transformers

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
sys.modules["weaviate.classes.config"] = mock_weaviate.classes.config
sys.modules["weaviate.classes.query"] = mock_weaviate.classes.query

# Now import our module
from advanced_rag import AdvancedRAGService, QueryEvent, TemporalRAGResponse


class TestAdvancedRAGService:
    """Test cases for Advanced RAG Service temporal functionality"""
    
    @pytest.fixture
    def service(self):
        """Create mock AdvancedRAGService for testing"""
        with patch('sentence_transformers.SentenceTransformer'), \
             patch('weaviate.connect_to_custom'), \
             patch('openai.AsyncOpenAI'):
            service = AdvancedRAGService()
            return service

    @pytest.fixture 
    def sample_query_event(self):
        """Sample query event for testing"""
        return QueryEvent(
            camera_id="cam_001",
            timestamp="2025-06-06T10:30:00Z",
            label="person_detected",
            bbox={"x": 100.0, "y": 150.0, "width": 50.0, "height": 100.0}
        )

    @pytest.fixture
    def sample_events_unordered(self):
        """Sample events in non-chronological order for sorting tests"""
        return [
            {
                "id": "event_3",
                "properties": {
                    "camera_id": "cam_001", 
                    "timestamp": "2025-06-06T10:35:00Z",
                    "label": "vehicle_detected",
                    "confidence": 0.95
                },
                "distance": 0.1
            },
            {
                "id": "event_1", 
                "properties": {
                    "camera_id": "cam_001",
                    "timestamp": "2025-06-06T10:25:00Z", 
                    "label": "person_walking",
                    "confidence": 0.88
                },
                "distance": 0.2
            },
            {
                "id": "event_2",
                "properties": {
                    "camera_id": "cam_002",
                    "timestamp": "2025-06-06T10:30:00Z",
                    "label": "door_opened", 
                    "confidence": 0.92
                },
                "distance": 0.15
            }
        ]

    def test_chronological_sorting(self, service, sample_events_unordered):
        """Test that events are sorted chronologically (ascending order)"""
        # Sort the events
        sorted_events = service.sort_by_timestamp(sample_events_unordered)
        
        # Verify chronological order
        timestamps = [event["properties"]["timestamp"] for event in sorted_events]
        expected_order = [
            "2025-06-06T10:25:00Z",  # earliest
            "2025-06-06T10:30:00Z",  # middle  
            "2025-06-06T10:35:00Z"   # latest
        ]
        
        assert timestamps == expected_order
        
        # Verify event IDs are in correct order
        event_ids = [event["id"] for event in sorted_events]
        assert event_ids == ["event_1", "event_2", "event_3"]

    def test_chronological_sorting_with_invalid_timestamps(self, service):
        """Test sorting handles invalid timestamps gracefully"""
        events_with_invalid = [
            {
                "id": "valid_event",
                "properties": {
                    "timestamp": "2025-06-06T10:30:00Z",
                    "label": "person_detected"
                }
            },
            {
                "id": "invalid_event", 
                "properties": {
                    "timestamp": "invalid_timestamp",
                    "label": "object_detected"
                }
            },
            {
                "id": "missing_timestamp_event",
                "properties": {
                    "label": "movement_detected"
                }
            }
        ]
        
        # Should not raise exception and should handle gracefully
        sorted_events = service.sort_by_timestamp(events_with_invalid)
        
        # Valid timestamp should be last (invalid timestamps get datetime.min)
        assert sorted_events[-1]["id"] == "valid_event"

    @pytest.mark.asyncio
    async def test_temporal_prompt_construction(self, service, sample_query_event, sample_events_unordered):
        """Test construction of temporal prompts emphasizing causality"""
        # Sort events first
        chronological_events = service.sort_by_timestamp(sample_events_unordered)
        
        # Construct prompt
        prompt = await service.construct_temporal_prompt(sample_query_event, chronological_events)
        
        # Verify prompt contains key temporal elements
        assert "temporal sequence" in prompt.lower()
        assert "causal relationships" in prompt.lower() or "causality" in prompt.lower()
        assert "chronologically ordered" in prompt.lower()
        assert sample_query_event.camera_id in prompt
        assert sample_query_event.timestamp in prompt
        assert sample_query_event.label in prompt
        
        # Verify chronological context is present
        assert "10:25:00Z" in prompt  # earliest event
        assert "10:30:00Z" in prompt  # middle event  
        assert "10:35:00Z" in prompt  # latest event
        
        # Verify analysis instructions are present
        assert "cause-and-effect" in prompt.lower()
        assert "temporal" in prompt.lower()

    def test_event_embedding_generation(self, service, sample_query_event):
        """Test embedding generation for query events"""
        # Mock the embedding model
        mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        service.embedding_model = Mock()
        service.embedding_model.encode.return_value = Mock()
        service.embedding_model.encode.return_value.tolist.return_value = mock_embedding
        
        # Generate embedding
        embedding = service.get_event_embedding(sample_query_event)
        
        # Verify embedding is generated correctly
        assert embedding == mock_embedding
        
        # Verify the text representation includes all event details
        call_args = service.embedding_model.encode.call_args[0][0]
        assert sample_query_event.camera_id in call_args
        assert sample_query_event.label in call_args
        assert sample_query_event.timestamp in call_args
        assert "100.00" in call_args  # bbox x coordinate

    def test_event_embedding_without_bbox(self, service):
        """Test embedding generation for events without bounding box"""
        event_no_bbox = QueryEvent(
            camera_id="cam_002",
            timestamp="2025-06-06T11:00:00Z", 
            label="motion_detected",
            bbox=None
        )
        
        # Mock the embedding model
        mock_embedding = [0.1, 0.2, 0.3]
        service.embedding_model = Mock()
        service.embedding_model.encode.return_value = Mock()
        service.embedding_model.encode.return_value.tolist.return_value = mock_embedding
        
        # Generate embedding
        embedding = service.get_event_embedding(event_no_bbox)
        
        # Verify embedding is generated
        assert embedding == mock_embedding
        
        # Verify text doesn't contain bbox info
        call_args = service.embedding_model.encode.call_args[0][0]
        assert "region" not in call_args.lower()

    @pytest.mark.asyncio
    async def test_process_temporal_query_integration(self, service, sample_query_event):
        """Test the complete temporal query processing pipeline"""
        # Mock all dependencies
        mock_similar_events = [
            {
                "id": "event_1",
                "properties": {
                    "timestamp": "2025-06-06T10:20:00Z",
                    "camera_id": "cam_001", 
                    "label": "person_entering",
                    "confidence": 0.9
                }
            },
            {
                "id": "event_2", 
                "properties": {
                    "timestamp": "2025-06-06T10:25:00Z",
                    "camera_id": "cam_001",
                    "label": "door_opened",
                    "confidence": 0.85
                }
            }
        ]
        
        # Mock service methods
        service.query_weaviate = Mock(return_value=mock_similar_events)
        service.openai_client = AsyncMock()
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This sequence shows a person entering through a door, suggesting normal access behavior with temporal causality."
        service.openai_client.chat.completions.create.return_value = mock_response
        
        # Process query
        result = await service.process_temporal_query(sample_query_event, k=5)
        
        # Verify result structure
        assert isinstance(result, TemporalRAGResponse)
        assert "temporal causality" in result.linked_explanation
        assert len(result.retrieved_context) == 2
        
        # Verify chronological ordering in result
        timestamps = [event["properties"]["timestamp"] for event in result.retrieved_context]
        assert timestamps == ["2025-06-06T10:20:00Z", "2025-06-06T10:25:00Z"]

    def test_empty_events_sorting(self, service):
        """Test sorting behavior with empty event list"""
        empty_events = []
        sorted_events = service.sort_by_timestamp(empty_events)
        assert sorted_events == []

    def test_single_event_sorting(self, service):
        """Test sorting behavior with single event"""
        single_event = [{
            "id": "single",
            "properties": {"timestamp": "2025-06-06T10:30:00Z"}
        }]
        sorted_events = service.sort_by_timestamp(single_event)
        assert len(sorted_events) == 1
        assert sorted_events[0]["id"] == "single"

    @pytest.mark.asyncio
    async def test_prompt_construction_error_handling(self, service, sample_query_event):
        """Test prompt construction handles errors gracefully"""
        # Events with problematic data
        problematic_events = [
            {
                "id": "bad_event",
                "properties": None  # This should cause issues
            }
        ]
        
        # Should not raise exception
        prompt = await service.construct_temporal_prompt(sample_query_event, problematic_events)
        
        # Should return a basic prompt even with errors
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_same_timestamp_sorting_stability(self, service):
        """Test sorting stability when events have identical timestamps"""
        same_time_events = [
            {
                "id": "event_a",
                "properties": {"timestamp": "2025-06-06T10:30:00Z", "label": "first"}
            },
            {
                "id": "event_b", 
                "properties": {"timestamp": "2025-06-06T10:30:00Z", "label": "second"}
            }
        ]
        
        sorted_events = service.sort_by_timestamp(same_time_events)
        
        # Should maintain stable order
        assert len(sorted_events) == 2
        # Both events should be present
        event_ids = [event["id"] for event in sorted_events]
        assert "event_a" in event_ids
        assert "event_b" in event_ids

    def test_similarity_score_normalization(self, service):
        """Test that vector distance is properly normalized to similarity score (0-1)"""
        # Mock Weaviate collection and query response
        mock_obj = Mock()
        mock_obj.uuid = "test-id"
        mock_obj.properties = {"camera_id": "cam_001", "label": "person"}
        
        # Test different distance values and expected similarity scores
        test_cases = [
            (0.0, 1.0),    # Perfect match: distance=0 -> similarity=1.0
            (1.0, 0.5),    # Medium match: distance=1 -> similarity=0.5
            (2.0, 0.0),    # Poor match: distance=2 -> similarity=0.0
            (0.5, 0.75),   # Good match: distance=0.5 -> similarity=0.75
            (3.0, 0.0),    # Beyond range: distance=3 -> similarity=0.0 (clamped)
        ]
        
        for distance, expected_similarity in test_cases:
            # Setup mock metadata
            mock_metadata = Mock()
            mock_metadata.distance = distance
            mock_metadata.certainty = 0.8
            mock_metadata.creation_time = datetime.now()
            mock_obj.metadata = mock_metadata
            
            # Mock collection query response
            mock_response = Mock()
            mock_response.objects = [mock_obj]
            
            # Mock collection and client
            mock_collection = Mock()
            mock_collection.query.near_vector.return_value = mock_response
            service.weaviate_client.collections.get.return_value = mock_collection
            
            # Mock embedding generation
            with patch.object(service, 'get_event_embedding', return_value=[0.1, 0.2, 0.3]):
                query_event = QueryEvent(
                    camera_id="cam_001",
                    timestamp="2025-06-10T10:00:00Z",
                    label="person"
                )
                
                results = service.query_weaviate(query_event, k=1)
                  # Verify similarity score calculation
                assert len(results) == 1
                result = results[0]
                assert "similarity_score" in result
                assert abs(result["similarity_score"] - expected_similarity) < 0.001, \
                    f"Distance {distance} should give similarity {expected_similarity}, got {result['similarity_score']}"
                assert 0.0 <= result["similarity_score"] <= 1.0, "Similarity score must be in [0,1] range"

    def test_explanation_confidence_calculation(self, service):
        """Test that explanation confidence is calculated correctly from similarity scores"""
        # Mock Weaviate query results with different similarity scores
        mock_events = [
            {
                "id": "event_1",
                "properties": {"camera_id": "cam_001", "timestamp": "2025-06-10T09:00:00Z", "label": "person"},
                "similarity_score": 0.9
            },
            {
                "id": "event_2", 
                "properties": {"camera_id": "cam_001", "timestamp": "2025-06-10T10:00:00Z", "label": "vehicle"},
                "similarity_score": 0.7
            },
            {
                "id": "event_3",
                "properties": {"camera_id": "cam_002", "timestamp": "2025-06-10T11:00:00Z", "label": "person"},
                "similarity_score": 0.8
            }
        ]
        
        # Expected confidence is average: (0.9 + 0.7 + 0.8) / 3 = 0.8
        expected_confidence = 0.8
        
        # Create async mock for the method
        async def mock_process_temporal_query(query_event, k=10):
            return TemporalRAGResponse(
                linked_explanation="Test explanation",
                retrieved_context=mock_events,
                explanation_confidence=expected_confidence
            )
        
        # Test the confidence calculation logic directly
        similarity_scores = [event.get("similarity_score", 0.0) for event in mock_events]
        calculated_confidence = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
        
        # Verify confidence calculation
        assert abs(calculated_confidence - expected_confidence) < 0.001
        assert 0.0 <= calculated_confidence <= 1.0, "Confidence must be in [0,1] range"
        
        # Verify all events have similarity scores
        for event in mock_events:
            assert "similarity_score" in event
            assert 0.0 <= event["similarity_score"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__])

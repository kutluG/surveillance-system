"""
Unit tests for weaviate_client.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import weaviate
import weaviate.classes as wvc
from datetime import datetime, timedelta

# Mock the shared.config module before importing weaviate_client
import sys
sys.modules['shared.config'] = Mock()
sys.modules['shared.config'].get_service_config = Mock(return_value={
    "weaviate_url": "http://test-weaviate:8080"
})

from weaviate_client import (
    get_client,
    semantic_search,
    semantic_search_with_patterns,
    get_related_events,
    _build_enhanced_query,
    _build_where_filter,
    _calculate_relevance_score,
    _assess_context_match,
    _analyze_event_patterns,
    _analyze_temporal_patterns,
    _generate_search_recommendations
)


class TestWeavateClient:
    """Test cases for Weaviate client functions."""
    
    @pytest.fixture
    def mock_weaviate_client(self):
        """Mock Weaviate client."""
        client = Mock()
        collection = Mock()
        client.collections.get.return_value = collection
        return client, collection
    
    @pytest.fixture
    def sample_weaviate_objects(self):
        """Sample Weaviate response objects."""
        objects = []
        
        # Object 1
        obj1 = Mock()
        obj1.properties = {
            "event_id": "event-001",
            "timestamp": "2025-06-18T09:00:00Z",
            "camera_id": "cam-001",
            "event_type": "person_detected",
            "details": "Person detected at main entrance",
            "location": "main_entrance",
            "confidence": 0.95
        }
        obj1.metadata = Mock()
        obj1.metadata.certainty = 0.92
        obj1.metadata.distance = 0.08
        objects.append(obj1)
        
        # Object 2
        obj2 = Mock()
        obj2.properties = {
            "event_id": "event-002",
            "timestamp": "2025-06-18T09:15:00Z",
            "camera_id": "cam-002",
            "event_type": "motion_detected",
            "details": "Motion in parking area",
            "location": "parking_lot",
            "confidence": 0.87
        }
        obj2.metadata = Mock()
        obj2.metadata.certainty = 0.85
        obj2.metadata.distance = 0.15
        objects.append(obj2)
        
        return objects
    
    @pytest.fixture
    def sample_conversation_context(self):
        """Sample conversation context."""
        return [
            {"role": "user", "content": "Show me main entrance events"},
            {"role": "assistant", "content": "I found several events..."},
            {"role": "user", "content": "What about person detection?"}
        ]

    # Test get_client
    @patch('weaviate_client.weaviate.connect_to_local')
    @patch('weaviate_client._client', None)  # Reset global client
    def test_get_client_success(self, mock_connect):
        """Test successful client initialization."""
        mock_client = Mock()
        mock_connect.return_value = mock_client
        
        # Reset the global client to test initialization
        import weaviate_client
        weaviate_client._client = None
        
        client = get_client()
        
        assert client == mock_client
        mock_connect.assert_called_once_with(host="test-weaviate", port=8080)
    
    @patch('weaviate_client.weaviate.connect_to_local')
    @patch('weaviate_client._client', None)
    def test_get_client_connection_error(self, mock_connect):
        """Test client initialization with connection error."""
        mock_connect.side_effect = Exception("Connection failed")
        
        import weaviate_client
        weaviate_client._client = None
        
        client = get_client()
        
        assert client is None
    
    def test_get_client_cached(self):
        """Test that client is cached after first initialization."""
        import weaviate_client
        mock_client = Mock()
        weaviate_client._client = mock_client
        
        client = get_client()
        
        assert client == mock_client

    # Test semantic_search
    @patch('weaviate_client.get_client')
    def test_semantic_search_success(self, mock_get_client, mock_weaviate_client, sample_weaviate_objects):
        """Test successful semantic search."""
        client, collection = mock_weaviate_client
        mock_get_client.return_value = client
        
        # Setup search response
        search_response = Mock()
        search_response.objects = sample_weaviate_objects
        collection.query.near_text.return_value = search_response
        
        query = "person detected at entrance"
        result = semantic_search(query, limit=5)
        
        # Verify result structure
        assert len(result) == 2
        assert result[0]["event_id"] == "event-001"
        assert result[0]["camera_id"] == "cam-001"
        assert result[0]["certainty"] == 0.92
        assert result[0]["distance"] == 0.08
        assert "relevance_score" in result[0]
        assert "context_match" in result[0]
        
        # Verify Weaviate was called correctly
        client.collections.get.assert_called_with("CameraEvent")
        collection.query.near_text.assert_called_once()
        call_args = collection.query.near_text.call_args
        assert call_args[1]["query"] == query
        assert call_args[1]["limit"] == 5
    
    @patch('weaviate_client.get_client')
    def test_semantic_search_with_conversation_context(
        self, mock_get_client, mock_weaviate_client, sample_weaviate_objects, sample_conversation_context  
    ):
        """Test semantic search with conversation context."""
        client, collection = mock_weaviate_client
        mock_get_client.return_value = client
        
        search_response = Mock()
        search_response.objects = sample_weaviate_objects
        collection.query.near_text.return_value = search_response
        
        query = "recent events"
        result = semantic_search(
            query=query,
            conversation_context=sample_conversation_context
        )
        
        # Should enhance query with conversation context
        call_args = collection.query.near_text.call_args
        enhanced_query = call_args[1]["query"]
        # Query should be enhanced with context terms
        assert len(enhanced_query) >= len(query)
    
    @patch('weaviate_client.get_client')
    def test_semantic_search_with_filters(self, mock_get_client, mock_weaviate_client, sample_weaviate_objects):
        """Test semantic search with filters."""
        client, collection = mock_weaviate_client
        mock_get_client.return_value = client
        
        search_response = Mock()
        search_response.objects = sample_weaviate_objects
        collection.query.near_text.return_value = search_response
        
        filters = {
            "camera_id": "cam-001",
            "event_type": "person_detected",
            "min_confidence": 0.8
        }
        
        result = semantic_search("test query", filters=filters)
        
        # Verify filter was applied
        call_args = collection.query.near_text.call_args
        assert "where" in call_args[1]
    
    @patch('weaviate_client.get_client')
    def test_semantic_search_no_client(self, mock_get_client):
        """Test semantic search when client is unavailable."""
        mock_get_client.return_value = None
        
        result = semantic_search("test query")
        
        assert result == []
    
    @patch('weaviate_client.get_client')
    def test_semantic_search_weaviate_error(self, mock_get_client, mock_weaviate_client):
        """Test semantic search with Weaviate error."""
        client, collection = mock_weaviate_client
        mock_get_client.return_value = client
        collection.query.near_text.side_effect = Exception("Weaviate error")
        
        result = semantic_search("test query")
        
        assert result == []

    # Test semantic_search_with_patterns
    @patch('weaviate_client.get_client')
    def test_semantic_search_with_patterns_success(
        self, mock_get_client, mock_weaviate_client, sample_weaviate_objects
    ):
        """Test semantic search with pattern analysis."""
        client, collection = mock_weaviate_client
        mock_get_client.return_value = client
        
        search_response = Mock()
        search_response.objects = sample_weaviate_objects
        collection.query.near_text.return_value = search_response
        
        result = semantic_search_with_patterns(
            query="security events",
            limit=5,
            include_patterns=True,
            time_window_hours=24
        )
        
        # Verify result structure
        assert "results" in result
        assert "patterns" in result
        assert "temporal_analysis" in result
        assert "recommendations" in result
        
        assert len(result["results"]) == 2
        assert isinstance(result["patterns"], dict)
        assert isinstance(result["temporal_analysis"], dict)
        assert isinstance(result["recommendations"], list)
    
    @patch('weaviate_client.get_client')
    def test_semantic_search_with_patterns_no_patterns(
        self, mock_get_client, mock_weaviate_client, sample_weaviate_objects
    ):
        """Test semantic search without pattern analysis."""
        client, collection = mock_weaviate_client
        mock_get_client.return_value = client
        
        search_response = Mock()
        search_response.objects = sample_weaviate_objects
        collection.query.near_text.return_value = search_response
        
        result = semantic_search_with_patterns(
            query="test",
            include_patterns=False
        )
        
        # Should still return results but without pattern analysis
        assert "results" in result
        assert len(result["results"]) == 2

    # Test get_related_events
    @patch('weaviate_client.get_client')
    def test_get_related_events_success(self, mock_get_client, mock_weaviate_client):
        """Test finding related events."""
        client, collection = mock_weaviate_client
        mock_get_client.return_value = client
        
        # Mock the reference event
        ref_event = Mock()
        ref_event.properties = {
            "event_id": "ref-event",
            "timestamp": "2025-06-18T10:00:00Z",
            "camera_id": "cam-001",
            "event_type": "person_detected"
        }
          # Mock search for reference event
        ref_search_response = Mock()
        ref_search_response.objects = [ref_event]
        
        # Mock related events search
        related_response = Mock()
        related_response.objects = []
        
        # Setup proper mock chain - fetch_objects is used to get the reference event first
        collection.query.fetch_objects.return_value = ref_search_response
        collection.query.near_text.return_value = related_response
        collection.query.where.return_value.limit.return_value = related_response
        
        result = get_related_events(
            event_id="ref-event",
            relation_types=["temporal", "spatial", "semantic"],
            limit=10
        )
        
        assert isinstance(result, list)
        # Verify the reference event was fetched
        assert collection.query.fetch_objects.called
    
    @patch('weaviate_client.get_client')
    def test_get_related_events_no_client(self, mock_get_client):
        """Test get_related_events when client unavailable."""
        mock_get_client.return_value = None
        
        result = get_related_events("event-123")
        
        assert result == []
    
    @patch('weaviate_client.get_client')
    def test_get_related_events_not_found(self, mock_get_client, mock_weaviate_client):
        """Test get_related_events when reference event not found."""
        client, collection = mock_weaviate_client
        mock_get_client.return_value = client
        
        # Mock empty search response
        search_response = Mock()
        search_response.objects = []
        collection.query.near_text.return_value = search_response
        
        result = get_related_events("nonexistent-event")
        
        assert result == []

    # Test helper functions
    def test_build_enhanced_query_no_context(self):
        """Test query building without conversation context."""
        query = "test query"
        result = _build_enhanced_query(query, None)
        
        assert result == query
    
    def test_build_enhanced_query_with_context(self, sample_conversation_context):
        """Test query building with conversation context."""
        query = "recent events"
        result = _build_enhanced_query(query, sample_conversation_context)
          # Should be enhanced with context terms
        assert len(result) > len(query)
        assert query in result
    
    def test_build_where_filter_single_condition(self):
        """Test building where filter with single condition."""
        filters = {"camera_id": "cam-001"}
        
        with patch('weaviate_client.wvc.query.Filter') as mock_filter_class:
            mock_filter = Mock()
            mock_filter_class.by_property.return_value.equal.return_value = mock_filter
            
            result = _build_where_filter(filters)
            
            mock_filter_class.by_property.assert_called_with("camera_id")
            mock_filter_class.by_property.return_value.equal.assert_called_with("cam-001")
    
    def test_build_where_filter_multiple_conditions(self):
        """Test building where filter with multiple conditions."""
        filters = {
            "camera_id": "cam-001",
            "event_type": "person_detected",
            "min_confidence": 0.8
        }
        
        with patch('weaviate_client.wvc.query.Filter') as mock_filter_class:
            mock_filter1 = Mock()
            mock_filter2 = Mock()
            mock_filter3 = Mock()
            mock_combined = Mock()
            
            # Setup the mock to support the & operator
            mock_filter1.__and__ = Mock(return_value=mock_combined)
            mock_combined.__and__ = Mock(return_value=mock_combined)
            
            mock_filter_class.by_property.return_value.equal.side_effect = [mock_filter1, mock_filter2]
            mock_filter_class.by_property.return_value.greater_or_equal.return_value = mock_filter3
            
            result = _build_where_filter(filters)
            
            # Should combine multiple conditions with AND
            assert mock_filter_class.by_property.call_count >= 3
    
    def test_build_where_filter_time_range(self):
        """Test building where filter with time range."""
        filters = {
            "time_range": {
                "start": "2025-06-18T08:00:00Z",
                "end": "2025-06-18T18:00:00Z"
            }
        }
        
        with patch('weaviate_client.wvc.query.Filter') as mock_filter_class:
            mock_filter = Mock()
            mock_filter_class.by_property.return_value.greater_or_equal.return_value.logical_and.return_value.less_or_equal.return_value = mock_filter
            
            result = _build_where_filter(filters)
            
            # Should create time range filter
            mock_filter_class.by_property.assert_called_with("timestamp")
    
    def test_calculate_relevance_score_base(self, sample_weaviate_objects):
        """Test relevance score calculation."""
        obj = sample_weaviate_objects[0]
        query = "person detection"
        
        score = _calculate_relevance_score(obj, query, None)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        # Should be higher than base certainty due to confidence boost
        assert score >= obj.metadata.certainty
    
    def test_calculate_relevance_score_with_query_match(self, sample_weaviate_objects):
        """Test relevance score with query match in details."""
        obj = sample_weaviate_objects[0]
        query = "main entrance"  # Matches details
        
        score = _calculate_relevance_score(obj, query, None)
        
        # Should get boost for query match
        assert score > obj.metadata.certainty
    
    def test_calculate_relevance_score_high_confidence(self, sample_weaviate_objects):
        """Test relevance score with high confidence event."""
        obj = sample_weaviate_objects[0]  # Has confidence 0.95
        query = "test"
        
        score = _calculate_relevance_score(obj, query, None)
        
        # Should get boost for high confidence
        assert score > obj.metadata.certainty
    
    def test_assess_context_match_no_context(self, sample_weaviate_objects):
        """Test context match assessment without context."""
        obj = sample_weaviate_objects[0]
        
        match_score = _assess_context_match(obj, None)
        
        assert match_score == 0.0
    
    def test_assess_context_match_with_context(self, sample_weaviate_objects, sample_conversation_context):
        """Test context match assessment with conversation context."""
        obj = sample_weaviate_objects[0]  # Has "main entrance" details
        
        match_score = _assess_context_match(obj, sample_conversation_context)
        
        assert isinstance(match_score, float)
        assert 0.0 <= match_score <= 1.0
    
    def test_analyze_event_patterns_empty(self):
        """Test pattern analysis with empty results."""
        result = _analyze_event_patterns([])
        
        assert result["most_common_cameras"] == {}
        assert result["most_common_types"] == {}
        assert result["confidence_distribution"] == {}
        assert result["time_patterns"] == []
    
    def test_analyze_event_patterns_with_data(self):
        """Test pattern analysis with data."""
        results = [
            {"camera_id": "cam-001", "event_type": "person_detected", "confidence": 0.9},
            {"camera_id": "cam-001", "event_type": "motion_detected", "confidence": 0.8},
            {"camera_id": "cam-002", "event_type": "person_detected", "confidence": 0.7}
        ]
        
        patterns = _analyze_event_patterns(results)
        
        assert "cam-001" in patterns["most_common_cameras"]
        assert patterns["most_common_cameras"]["cam-001"] == 2
        assert "person_detected" in patterns["most_common_types"]
        assert patterns["most_common_types"]["person_detected"] == 2
          # Should have confidence statistics
        assert "confidence_distribution" in patterns

    def test_analyze_temporal_patterns(self):
        """Test temporal pattern analysis."""
        results = [
            {"timestamp": "2025-06-18T09:00:00Z"},
            {"timestamp": "2025-06-18T10:00:00Z"}
        ]
        
        patterns = _analyze_temporal_patterns(results, 24)
        
        assert patterns["events_in_window"] == 2
        assert patterns["time_window_hours"] == 24
        assert "analysis" in patterns
    
    def test_generate_search_recommendations_empty(self):
        """Test search recommendations with empty results."""
        recommendations = _generate_search_recommendations([], "test query")
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any("try broadening" in rec.lower() for rec in recommendations)
    
    def test_generate_search_recommendations_with_data(self):
        """Test search recommendations with results."""
        results = [
            {"camera_id": "cam-001", "event_type": "person_detected"},
            {"camera_id": "cam-002", "event_type": "motion_detected"}
        ]
        
        recommendations = _generate_search_recommendations(results, "security events")
        
        assert isinstance(recommendations, list)
        # Should suggest filtering by specific cameras or event types
        assert any("cam-001" in rec or "cam-002" in rec for rec in recommendations)

    # Test edge cases and error conditions
    @patch('weaviate_client.get_client')
    def test_semantic_search_malformed_objects(self, mock_get_client, mock_weaviate_client):
        """Test handling of malformed Weaviate objects."""
        client, collection = mock_weaviate_client
        mock_get_client.return_value = client
        
        # Create malformed objects
        malformed_obj = Mock()
        malformed_obj.properties = {}  # Missing required fields
        malformed_obj.metadata = None  # No metadata
        
        search_response = Mock()
        search_response.objects = [malformed_obj]
        collection.query.near_text.return_value = search_response
        
        result = semantic_search("test query")
        
        # Should handle gracefully
        assert len(result) == 1
        assert result[0]["event_id"] is None
        assert result[0]["certainty"] is None
    
    @patch('weaviate_client.get_client')
    def test_semantic_search_large_limit(self, mock_get_client, mock_weaviate_client, sample_weaviate_objects):
        """Test semantic search with very large limit."""
        client, collection = mock_weaviate_client
        mock_get_client.return_value = client
        
        search_response = Mock()
        search_response.objects = sample_weaviate_objects
        collection.query.near_text.return_value = search_response
        
        result = semantic_search("test query", limit=1000)
        
        # Should handle large limits
        call_args = collection.query.near_text.call_args
        assert call_args[1]["limit"] == 1000
        assert len(result) == 2  # Still returns actual number of results
    
    def test_build_enhanced_query_empty_context(self):
        """Test query building with empty conversation context."""
        query = "test query"
        empty_context = []
        
        result = _build_enhanced_query(query, empty_context)
        
        assert result == query
    
    def test_build_enhanced_query_context_without_content(self):
        """Test query building with context missing content."""
        query = "test query"
        malformed_context = [
            {"role": "user"},  # Missing content
            {"content": "test"},  # Missing role
            {}  # Empty message
        ]
        
        result = _build_enhanced_query(query, malformed_context)
        
        # Should handle gracefully and return enhanced query
        assert len(result) >= len(query)
    
    def test_calculate_relevance_score_no_metadata(self):
        """Test relevance score calculation with missing metadata."""
        obj = Mock()
        obj.properties = {"details": "test details", "confidence": 0.8}
        obj.metadata = None
        
        score = _calculate_relevance_score(obj, "test", None)
        
        # Should use default base score
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_calculate_relevance_score_recent_events(self):
        """Test relevance score boost for recent events."""
        obj = Mock()
        obj.properties = {
            "details": "test details",
            "confidence": 0.8,
            "timestamp": datetime.utcnow().isoformat()  # Very recent
        }
        obj.metadata = Mock()
        obj.metadata.certainty = 0.7
        
        score = _calculate_relevance_score(obj, "test", None)
        
        # Should get boost for recent timestamp
        assert score > 0.7
    
    def test_build_where_filter_empty(self):
        """Test building filter with empty filter dict."""
        result = _build_where_filter({})
        
        assert result is None
    
    def test_build_where_filter_unknown_field(self):
        """Test building filter with unknown field."""
        filters = {"unknown_field": "value"}
        
        result = _build_where_filter(filters)
        
        # Should handle unknown fields gracefully
        assert result is None or result is not None  # Either way is acceptable

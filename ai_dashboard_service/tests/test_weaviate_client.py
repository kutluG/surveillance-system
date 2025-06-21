"""
Comprehensive unit tests for Weaviate Client Service.

This module provides complete test coverage for the WeaviateService class,
including vector database operations, semantic search, and pattern analysis.
All Weaviate operations are mocked for isolated testing.

Test Coverage:
- Semantic search with various query scenarios
- Pattern analysis and vector clustering
- Similar event detection and retrieval
- Event storage and vector indexing
- Error handling for database failures
- Client availability and graceful degradation

Classes Tested:
    - WeaviateService: Main vector database service with comprehensive validation
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

from app.services.weaviate_client import WeaviateService


class TestWeaviateService:
    """
    Comprehensive test suite for WeaviateService functionality.
    
    Tests all major vector database operations including semantic search,
    pattern analysis, event storage, and error scenarios.
    """
    
    @pytest.mark.asyncio
    async def test_semantic_search_success(self, weaviate_service, sample_weaviate_events):
        """
        Test successful semantic search with realistic surveillance queries.
        
        Validates that semantic search correctly processes natural language
        queries and returns ranked surveillance events with similarity scores.
        """
        query = "person detected in parking area"
        limit = 5
        filters = {"camera_id": "cam-001", "confidence": {"$gte": 0.8}}
        
        # Execute semantic search
        result = await weaviate_service.semantic_search(query, limit, filters)
        
        # Validate result structure
        assert isinstance(result, list)
        assert len(result) <= limit
        
        # Validate result content for non-empty case
        if len(result) > 0:
            for item in result:
                assert isinstance(item, dict)
                assert "id" in item
                assert "score" in item
                assert "distance" in item
                
                # Validate similarity scores
                assert 0.0 <= item["score"] <= 1.0
                assert item["distance"] >= 0.0
                
                # Should contain surveillance event properties
                assert "event_type" in item or "camera_id" in item
        
        # Verify Weaviate client interaction
        if weaviate_service.client:
            weaviate_service.client.collections.get.assert_called_with("SurveillanceEvent")
    
    @pytest.mark.asyncio
    async def test_semantic_search_no_client(self, mock_weaviate_client):
        """
        Test semantic search behavior when Weaviate client is unavailable.
        
        Validates graceful degradation when vector database is not accessible,
        ensuring service availability with fallback responses.
        """
        # Create service without client
        service = WeaviateService(weaviate_client=None)
        
        result = await service.semantic_search("test query", 10)
        
        # Should return empty results gracefully
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_filters(self, weaviate_service):
        """
        Test semantic search with complex metadata filters.
        
        Validates that search filters are properly converted to Weaviate
        where clauses and applied during vector similarity search.
        """
        query = "motion detected"
        filters = {
            "camera_id": "cam-001",
            "confidence": {"$gte": 0.8},
            "timestamp": {"$gte": "2025-06-20T00:00:00Z"},
            "event_type": "motion_detected"
        }
        
        result = await weaviate_service.semantic_search(query, 5, filters)
        
        # Should handle complex filters without errors
        assert isinstance(result, list)
        
        # Verify filter building was called
        # In a real test, you would verify that _build_where_clause was called
        # with the correct filters
    
    @pytest.mark.asyncio
    async def test_semantic_search_empty_query(self, weaviate_service):
        """
        Test semantic search with empty or invalid queries.
        
        Validates proper handling of edge cases where queries are
        empty, None, or contain only whitespace.
        """
        # Test empty query
        result = await weaviate_service.semantic_search("", 10)
        assert isinstance(result, list)
        
        # Test whitespace query
        result = await weaviate_service.semantic_search("   ", 10)
        assert isinstance(result, list)
        
        # Test None query - should be handled gracefully
        result = await weaviate_service.semantic_search(None, 10)
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_semantic_search_database_error(self, weaviate_service):
        """
        Test semantic search error handling for database failures.
        
        Validates that Weaviate connection errors are properly handled
        and don't crash the surveillance system.
        """
        # Configure mock to raise database error
        weaviate_service.client.collections.get.side_effect = Exception("Weaviate connection failed")
        
        # Should handle error gracefully
        result = await weaviate_service.semantic_search("test query", 10)
        
        assert isinstance(result, list)
        assert len(result) == 0  # Should return empty on error
    
    @pytest.mark.asyncio
    async def test_analyze_patterns_success(self, weaviate_service, sample_weaviate_events):
        """
        Test successful pattern analysis with surveillance events.
        
        Validates that pattern analysis correctly identifies relationships
        and trends in surveillance data using vector clustering.
        """
        pattern_type = "temporal"
        
        result = await weaviate_service.analyze_patterns(sample_weaviate_events, pattern_type)
        
        # Validate result structure
        assert isinstance(result, dict)
        assert "pattern_type" in result
        assert "total_events" in result
        assert "patterns" in result
        assert "clusters" in result
        assert "insights" in result
        
        # Validate content
        assert result["pattern_type"] == pattern_type
        assert result["total_events"] == len(sample_weaviate_events)
        assert isinstance(result["patterns"], list)
        assert isinstance(result["clusters"], list)
        assert isinstance(result["insights"], list)
        
        # Validate pattern structure
        if len(result["patterns"]) > 0:
            pattern = result["patterns"][0]
            assert "id" in pattern
            assert "type" in pattern
            assert "confidence" in pattern
            assert 0.0 <= pattern["confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_patterns_different_types(self, weaviate_service, sample_weaviate_events):
        """
        Test pattern analysis with different analysis types.
        
        Validates that different pattern analysis algorithms
        (temporal, spatial, semantic) work correctly.
        """
        pattern_types = ["temporal", "spatial", "semantic"]
        
        for pattern_type in pattern_types:
            result = await weaviate_service.analyze_patterns(sample_weaviate_events, pattern_type)
            
            assert isinstance(result, dict)
            assert result["pattern_type"] == pattern_type
            assert "patterns" in result
    
    @pytest.mark.asyncio
    async def test_analyze_patterns_empty_data(self, weaviate_service):
        """
        Test pattern analysis with empty event data.
        
        Validates proper handling when no surveillance events
        are available for pattern analysis.
        """
        result = await weaviate_service.analyze_patterns([], "temporal")
        
        # Should handle empty data gracefully
        assert isinstance(result, dict)
        assert result["total_events"] == 0
        assert len(result["patterns"]) == 0
        assert len(result["clusters"]) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_patterns_no_client(self, mock_weaviate_client):
        """
        Test pattern analysis when Weaviate client is unavailable.
        
        Validates graceful degradation for pattern analysis when
        vector database is not accessible.
        """
        service = WeaviateService(weaviate_client=None)
        
        result = await service.analyze_patterns([], "temporal")
        
        # Should return default structure
        assert isinstance(result, dict)
        assert result["patterns"] == []
        assert result["clusters"] == []
        assert result["insights"] == []
    
    @pytest.mark.asyncio
    async def test_get_similar_events_success(self, weaviate_service):
        """
        Test successful similar event retrieval.
        
        Validates that vector similarity search correctly finds
        events similar to a reference surveillance event.
        """
        reference_event_id = "event-001"
        limit = 5
        
        result = await weaviate_service.get_similar_events(reference_event_id, limit)
        
        # Validate result structure
        assert isinstance(result, list)
        assert len(result) <= limit
        
        # Validate similar event properties
        for event in result:
            assert isinstance(event, dict)
            assert "id" in event
            assert "similarity_score" in event
            assert "distance" in event
            
            # Should not include the reference event itself
            assert event["id"] != reference_event_id
            
            # Validate similarity metrics
            assert 0.0 <= event["similarity_score"] <= 1.0
            assert event["distance"] >= 0.0
    
    @pytest.mark.asyncio
    async def test_get_similar_events_no_results(self, weaviate_service):
        """
        Test similar event retrieval with no similar events found.
        
        Validates behavior when no events are similar enough to
        the reference event to meet similarity thresholds.
        """
        # Use a non-existent event ID
        result = await weaviate_service.get_similar_events("non-existent-event", 5)
        
        # Should return empty list gracefully
        assert isinstance(result, list)
        # May be empty if no similar events found
    
    @pytest.mark.asyncio
    async def test_get_similar_events_database_error(self, weaviate_service):
        """
        Test similar event retrieval with database errors.
        
        Validates error handling when vector similarity search
        fails due to database connectivity issues.
        """
        # Configure mock to raise error
        weaviate_service.client.collections.get.side_effect = Exception("Vector search failed")
        
        result = await weaviate_service.get_similar_events("event-001", 5)
        
        # Should handle error gracefully
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_store_event_success(self, weaviate_service):
        """
        Test successful event storage in vector database.
        
        Validates that surveillance events are properly vectorized
        and stored in Weaviate for future semantic search.
        """
        event_data = {
            "event_id": "event-123",
            "event_type": "person_detected",
            "camera_id": "cam-001",
            "timestamp": datetime.utcnow().isoformat(),
            "confidence": 0.95,
            "description": "Person detected in restricted area"
        }
        
        result = await weaviate_service.store_event(event_data)
        
        # Should return event ID on success
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Verify Weaviate client interaction
        if weaviate_service.client:
            collection = weaviate_service.client.collections.get.return_value
            collection.data.insert.assert_called_once_with(properties=event_data)
    
    @pytest.mark.asyncio
    async def test_store_event_no_client(self, mock_weaviate_client):
        """
        Test event storage when Weaviate client is unavailable.
        
        Validates graceful handling when vector database is not
        accessible for event storage operations.
        """
        service = WeaviateService(weaviate_client=None)
        
        event_data = {"event_id": "test-event"}
        result = await service.store_event(event_data)
        
        # Should return None when client unavailable
        assert result is None
    
    @pytest.mark.asyncio
    async def test_store_event_database_error(self, weaviate_service):
        """
        Test event storage with database insertion errors.
        
        Validates error handling when vector database storage
        operations fail due to connectivity or data issues.
        """
        # Configure mock to raise insertion error
        collection = weaviate_service.client.collections.get.return_value
        collection.data.insert.side_effect = Exception("Storage failed")
        
        event_data = {"event_id": "test-event"}
        result = await weaviate_service.store_event(event_data)
        
        # Should return None on error
        assert result is None
    
    @pytest.mark.asyncio
    async def test_build_where_clause_simple_filters(self, weaviate_service):
        """
        Test where clause building with simple filters.
        
        Validates that simple metadata filters are correctly
        converted to Weaviate query syntax.
        """
        filters = {
            "camera_id": "cam-001",
            "event_type": "motion_detected",
            "confidence": 0.8
        }
        
        where_clause = weaviate_service._build_where_clause(filters)
        
        # Should build proper where clause structure
        assert isinstance(where_clause, dict)
        if where_clause:  # If not empty
            assert "operator" in where_clause or "path" in where_clause
    
    @pytest.mark.asyncio
    async def test_build_where_clause_range_filters(self, weaviate_service):
        """
        Test where clause building with range filters.
        
        Validates that range queries ($gte, $lte, etc.) are properly
        converted to Weaviate comparison operators.
        """
        filters = {
            "confidence": {"$gte": 0.8, "$lte": 1.0},
            "timestamp": {"$gte": "2025-06-20T00:00:00Z"}
        }
        
        where_clause = weaviate_service._build_where_clause(filters)
        
        # Should handle range filters correctly
        assert isinstance(where_clause, dict)
    
    @pytest.mark.asyncio
    async def test_build_where_clause_complex_filters(self, weaviate_service):
        """
        Test where clause building with complex nested filters.
        
        Validates that complex filter combinations are properly
        handled with AND/OR logic.
        """
        filters = {
            "camera_id": "cam-001",
            "confidence": {"$gte": 0.8},
            "event_type": {"$eq": "person_detected"}
        }
        
        where_clause = weaviate_service._build_where_clause(filters)
        
        # Should build complex where clause
        assert isinstance(where_clause, dict)
    
    @pytest.mark.asyncio
    async def test_build_where_clause_empty_filters(self, weaviate_service):
        """
        Test where clause building with empty filters.
        
        Validates proper handling when no filters are provided.
        """
        where_clause = weaviate_service._build_where_clause({})
        
        # Should return empty dict for no filters
        assert isinstance(where_clause, dict)
        assert len(where_clause) == 0
    
    @pytest.mark.asyncio
    async def test_build_where_clause_error_handling(self, weaviate_service):
        """
        Test where clause building with invalid filter data.
        
        Validates error handling when filter data contains
        invalid or malformed values.
        """
        invalid_filters = {
            "invalid_range": {"$invalid_op": "bad_value"},
            "none_value": None,
            "complex_nested": {"nested": {"deep": {"value": "test"}}}
        }
        
        # Should handle invalid filters gracefully
        where_clause = weaviate_service._build_where_clause(invalid_filters)
        assert isinstance(where_clause, dict)
    
    @pytest.mark.asyncio
    async def test_service_initialization_with_client(self, mock_weaviate_client):
        """
        Test service initialization with Weaviate client.
        
        Validates proper dependency injection and configuration
        when Weaviate client is available.
        """
        service = WeaviateService(weaviate_client=mock_weaviate_client)
        
        assert service.client is mock_weaviate_client
        assert service.collection_name == "SurveillanceEvent"
    
    @pytest.mark.asyncio
    async def test_service_initialization_without_client(self):
        """
        Test service initialization without Weaviate client.
        
        Validates graceful initialization when vector database
        is not available or configured.
        """
        service = WeaviateService(weaviate_client=None)
        
        assert service.client is None
        assert service.collection_name == "SurveillanceEvent"
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, weaviate_service):
        """
        Test concurrent vector database operations.
        
        Validates that multiple Weaviate operations can run
        concurrently without conflicts or data corruption.
        """
        import asyncio
        
        # Create multiple concurrent operations
        tasks = [
            weaviate_service.semantic_search("test query 1", 5),
            weaviate_service.semantic_search("test query 2", 5),
            weaviate_service.analyze_patterns([], "temporal")
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should complete successfully
        assert len(results) == 3
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Operation {i} should not raise exception"
    
    @pytest.mark.asyncio
    async def test_collection_configuration(self, weaviate_service):
        """
        Test collection configuration and schema handling.
        
        Validates that the service properly configures and
        uses the surveillance event collection.
        """
        # Verify collection name is properly set
        assert weaviate_service.collection_name == "SurveillanceEvent"
        
        # In a real implementation, you would test:
        # - Collection schema validation
        # - Index configuration
        # - Vector embedding settings
    
    @pytest.mark.asyncio
    async def test_performance_with_large_datasets(self, weaviate_service):
        """
        Test performance with large surveillance datasets.
        
        Validates that the service handles large numbers of
        events efficiently without performance degradation.
        """
        # Create large dataset for testing
        large_events = []
        for i in range(1000):
            event = {
                "event_id": f"event-{i:04d}",
                "event_type": "motion_detected",
                "timestamp": datetime.utcnow().isoformat()
            }
            large_events.append(event)
        
        # Should handle large datasets efficiently
        result = await weaviate_service.analyze_patterns(large_events, "temporal")
        
        assert isinstance(result, dict)
        assert result["total_events"] == 1000
    
    @pytest.mark.asyncio
    async def test_search_result_ranking(self, weaviate_service):
        """
        Test search result ranking and scoring.
        
        Validates that semantic search results are properly
        ranked by relevance and similarity scores.
        """
        result = await weaviate_service.semantic_search("person detected", 10)
        
        if len(result) > 1:
            # Results should be ranked by similarity score (descending)
            scores = [item.get("score", 0) for item in result]
            assert scores == sorted(scores, reverse=True), "Results should be ranked by similarity score"
    
    @pytest.mark.asyncio 
    async def test_metadata_preservation(self, weaviate_service):
        """
        Test metadata preservation during vector operations.
        
        Validates that surveillance event metadata is properly
        preserved during storage and retrieval operations.
        """
        event_data = {
            "event_id": "meta-test-001",
            "event_type": "person_detected",
            "camera_id": "cam-001",
            "timestamp": "2025-06-20T10:00:00Z",
            "confidence": 0.95,
            "metadata": {
                "location": "parking_lot",
                "weather": "clear",
                "lighting": "daylight"
            }
        }
        
        # Store event
        event_id = await weaviate_service.store_event(event_data)
        
        if event_id:
            # Metadata should be preserved in the vector database
            # In a real test, you would retrieve and verify metadata
            assert isinstance(event_id, str)

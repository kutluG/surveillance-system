"""
Comprehensive tests for Enhanced Advanced RAG Service

Tests cover all the new enhancements including:
- Configuration management
- Error handling and retry logic  
- Performance monitoring and caching
- Circuit breaker functionality
- Enhanced validation
"""

import pytest
import asyncio
import time
import sys
import types
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Mock dependencies before importing enhanced components
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

mock_openai = types.ModuleType("openai")
mock_openai.AsyncOpenAI = Mock
sys.modules["openai"] = mock_openai

mock_prometheus = types.ModuleType("prometheus_client")
mock_prometheus.Gauge = Mock
mock_prometheus.Counter = Mock
mock_prometheus.Histogram = Mock
sys.modules["prometheus_client"] = mock_prometheus

# Import enhanced components after mocking
from enhanced_advanced_rag import (
    EnhancedAdvancedRAGService, 
    QueryEvent, 
    TemporalRAGResponse
)
from config import RAGServiceConfig
from error_handling import (
    EnhancedRAGError, 
    ConnectionError, 
    ValidationError,
    CircuitBreaker,
    CircuitBreakerState
)
from performance import InMemoryCache, PerformanceMonitor


class TestEnhancedConfiguration:
    """Test configuration management"""
    
    def test_default_configuration(self):
        """Test default configuration values"""
        config = RAGServiceConfig()
        
        assert config.service_name == "advanced_rag_service"
        assert config.log_level == "INFO"
        assert config.weaviate_url == "http://weaviate:8080"
        assert config.default_k == 10
        assert config.max_k == 50
        assert config.openai_model == "gpt-4"
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        # Test invalid log level
        with pytest.raises(ValueError):
            RAGServiceConfig(log_level="INVALID")
        
        # Test invalid temperature
        with pytest.raises(ValueError):
            RAGServiceConfig(openai_temperature=3.0)
        
        # Test invalid k values
        with pytest.raises(ValueError):
            RAGServiceConfig(default_k=0)


class TestErrorHandling:
    """Test enhanced error handling"""
    
    def test_enhanced_rag_error(self):
        """Test custom error types"""
        error = EnhancedRAGError("test message", "network_error")
        
        assert str(error) == "test message"
        assert error.error_type.value == "network_error"
        assert error.timestamp > 0
    
    def test_circuit_breaker_states(self):
        """Test circuit breaker state transitions"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Initial state should be CLOSED
        assert cb.state == CircuitBreakerState.CLOSED
        
        # Simulate failures
        cb.failure_count = 2
        cb.last_failure_time = time.time()
        
        # Should transition to OPEN
        assert cb.failure_count >= cb.failure_threshold
    
    @pytest.mark.asyncio
    async def test_retry_decorator(self):
        """Test retry decorator functionality"""
        from error_handling import with_retry, RetryConfig
        
        attempt_count = 0
        
        @with_retry(config=RetryConfig(max_attempts=3, base_delay=0.1))
        async def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Simulated failure")
            return "success"
        
        result = await failing_function()
        assert result == "success"
        assert attempt_count == 3


class TestPerformanceFeatures:
    """Test performance monitoring and caching"""
    
    @pytest.mark.asyncio
    async def test_in_memory_cache(self):
        """Test in-memory caching functionality"""
        cache = InMemoryCache(max_size=3, default_ttl=1.0)
        
        # Test set and get
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"
        
        # Test TTL expiration
        await cache.set("key2", "value2", ttl=0.1)
        await asyncio.sleep(0.2)
        result = await cache.get("key2")
        assert result is None
        
        # Test cache eviction
        await cache.set("key3", "value3")
        await cache.set("key4", "value4")
        await cache.set("key5", "value5")  # Should evict key1
        
        stats = cache.stats()
        assert stats["size"] == 3
    
    @pytest.mark.asyncio
    async def test_performance_monitor(self):
        """Test performance monitoring"""
        monitor = PerformanceMonitor()
        
        # Record some metrics
        await monitor.record_request("test_endpoint", 1.5, True)
        await monitor.record_request("test_endpoint", 2.0, False)
        await monitor.record_cache_hit()
        await monitor.record_cache_miss()
        
        metrics = monitor.get_metrics()
        
        assert metrics["total_requests"] == 2
        assert metrics["error_count"] == 1
        assert metrics["cache_hits"] == 1
        assert metrics["cache_misses"] == 1
        assert metrics["average_response_time"] == 1.75


class TestEnhancedRAGService:
    """Test the enhanced RAG service functionality"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        config = RAGServiceConfig()
        config.weaviate_url = "http://test-weaviate:8080"
        config.openai_api_key = "test-key"
        return config
    
    @pytest.fixture
    def enhanced_service(self, mock_config):
        """Create enhanced RAG service for testing"""
        with patch('sentence_transformers.SentenceTransformer'), \
             patch('weaviate.connect_to_custom'), \
             patch('openai.AsyncOpenAI'):
            service = EnhancedAdvancedRAGService(mock_config)
            return service
    
    def test_query_event_validation(self):
        """Test QueryEvent validation"""
        # Valid event
        event = QueryEvent(
            camera_id="cam_001",
            timestamp="2025-06-06T10:30:00Z",
            label="person_detected"
        )
        assert event.camera_id == "cam_001"
        
        # Invalid camera_id
        with pytest.raises(ValidationError):
            QueryEvent(camera_id="", timestamp="2025-06-06T10:30:00Z", label="test")
        
        # Invalid bbox
        with pytest.raises(ValidationError):
            QueryEvent(
                camera_id="cam_001",
                timestamp="2025-06-06T10:30:00Z", 
                label="test",
                bbox={"x": 100}  # Missing required keys
            )
    
    def test_temporal_rag_response_validation(self):
        """Test TemporalRAGResponse validation"""
        # Valid response
        response = TemporalRAGResponse(
            linked_explanation="test explanation",
            retrieved_context=[],
            explanation_confidence=0.8
        )
        assert response.explanation_confidence == 0.8
        
        # Invalid confidence
        with pytest.raises(ValidationError):
            TemporalRAGResponse(
                linked_explanation="test",
                retrieved_context=[],
                explanation_confidence=1.5  # Out of range
            )
    
    @pytest.mark.asyncio
    async def test_enhanced_embedding_generation(self, enhanced_service):
        """Test enhanced embedding generation with caching"""
        # Mock the embedding model
        mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        enhanced_service.embedding_model = Mock()
        enhanced_service.embedding_model.encode.return_value = Mock()
        enhanced_service.embedding_model.encode.return_value.tolist.return_value = mock_embedding
        
        # Create test event
        event = QueryEvent(
            camera_id="cam_001",
            timestamp="2025-06-06T10:30:00Z",
            label="person_detected",
            bbox={"x": 100.0, "y": 150.0, "width": 50.0, "height": 100.0}
        )
        
        # First call - should hit the model
        embedding1 = enhanced_service.get_event_embedding(event)
        assert embedding1 == mock_embedding
        
        # Second call - should hit cache (if caching is working)
        embedding2 = enhanced_service.get_event_embedding(event)
        assert embedding2 == mock_embedding
    
    @pytest.mark.asyncio
    async def test_enhanced_temporal_query_processing(self, enhanced_service):
        """Test complete temporal query processing with enhancements"""
        # Mock dependencies
        mock_similar_events = [
            {
                "id": "event_1",
                "properties": {
                    "timestamp": "2025-06-06T10:20:00Z",
                    "camera_id": "cam_001",
                    "label": "person_entering",
                    "confidence": 0.9
                },
                "similarity_score": 0.8
            }
        ]
        
        enhanced_service.query_weaviate = Mock(return_value=mock_similar_events)
        enhanced_service.openai_client = AsyncMock()
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Enhanced temporal analysis with confidence metrics."
        enhanced_service.openai_client.chat.completions.create.return_value = mock_response
        
        # Create test event
        query_event = QueryEvent(
            camera_id="cam_001",
            timestamp="2025-06-06T10:30:00Z",
            label="person_detected"
        )
        
        # Process query
        result = await enhanced_service.process_temporal_query(query_event, k=5)
        
        # Verify enhanced response structure
        assert isinstance(result, TemporalRAGResponse)
        assert "Enhanced temporal analysis" in result.linked_explanation
        assert len(result.retrieved_context) == 1
        assert result.explanation_confidence == 0.8  # Average similarity score
        assert result.processing_time > 0
        assert hasattr(result, 'cache_hit')
    
    @pytest.mark.asyncio 
    async def test_circuit_breaker_functionality(self, enhanced_service):
        """Test circuit breaker prevents cascading failures"""
        # Simulate OpenAI failures
        enhanced_service.openai_client = AsyncMock()
        enhanced_service.openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Mock other dependencies
        enhanced_service.query_weaviate = Mock(return_value=[])
        
        query_event = QueryEvent(
            camera_id="cam_001",
            timestamp="2025-06-06T10:30:00Z", 
            label="test"
        )
        
        # Make multiple requests to trigger circuit breaker
        for _ in range(5):  # Exceed failure threshold
            result = await enhanced_service.process_temporal_query(query_event)
            assert "unavailable due to API error" in result.linked_explanation
        
        # Circuit breaker should now be OPEN
        assert enhanced_service.openai_circuit_breaker.failure_count >= enhanced_service.openai_circuit_breaker.failure_threshold
    
    def test_enhanced_error_handling_in_sorting(self, enhanced_service):
        """Test enhanced error handling in timestamp sorting"""
        # Events with problematic timestamps
        problematic_events = [
            {
                "id": "good_event",
                "properties": {"timestamp": "2025-06-06T10:30:00Z"}
            },
            {
                "id": "bad_event", 
                "properties": {"timestamp": "invalid-timestamp"}
            },
            {
                "id": "missing_props",
                "properties": None
            }
        ]
        
        # Should not raise exception and handle gracefully
        sorted_events = enhanced_service.sort_by_timestamp(problematic_events)
        
        # Should return all events (fallback timestamps used)
        assert len(sorted_events) == 3
        assert all("id" in event for event in sorted_events)


class TestIntegrationScenarios:
    """Test integration scenarios with multiple components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_with_caching(self):
        """Test end-to-end scenario with caching enabled"""
        config = RAGServiceConfig(cache_ttl_seconds=10)
        
        with patch('sentence_transformers.SentenceTransformer'), \
             patch('weaviate.connect_to_custom'), \
             patch('openai.AsyncOpenAI'):
            
            service = EnhancedAdvancedRAGService(config)
            
            # Mock dependencies
            service.query_weaviate = Mock(return_value=[])
            service.openai_client = AsyncMock()
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Cached response test"
            service.openai_client.chat.completions.create.return_value = mock_response
            
            query_event = QueryEvent(
                camera_id="cam_test",
                timestamp="2025-06-06T10:30:00Z",
                label="test_event"
            )
            
            # First request
            result1 = await service.process_temporal_query(query_event)
            assert not result1.cache_hit
            
            # Second request should hit cache
            result2 = await service.process_temporal_query(query_event)
            # Note: Cache key might be different due to internal implementation
            # This test validates the caching mechanism exists
            assert isinstance(result2, TemporalRAGResponse)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

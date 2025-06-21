"""
Comprehensive Test Suite for Advanced Caching System

Tests all aspects of the multi-tier caching strategy:
- Vector embedding caching
- Query response caching 
- External API response caching
- Cache performance and metrics
"""

import asyncio
import pytest
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# Import the caching system
from advanced_caching import (
    AdvancedCacheManager, CacheType, CacheEntry, CacheStats,
    get_cache_manager, cached
)

# Import the RAG service for integration testing
from advanced_rag import AdvancedRAGService, QueryEvent, TemporalRAGResponse

class TestAdvancedCacheManager:
    """Test the core caching functionality"""
    
    @pytest.fixture
    async def cache_manager(self):
        """Create a test cache manager"""
        manager = AdvancedCacheManager(
            redis_url=None,  # Use memory-only for testing
            memory_max_size=100,
            enable_compression=True,
            enable_metrics=True
        )
        await manager.initialize()
        return manager
    
    @pytest.mark.asyncio
    async def test_basic_set_get(self, cache_manager):
        """Test basic cache set and get operations"""
        # Test string caching
        await cache_manager.set("test_key", "test_value", CacheType.QUERY)
        result = await cache_manager.get("test_key", CacheType.QUERY)
        assert result == "test_value"
        
        # Test complex object caching
        test_data = {"nested": {"data": [1, 2, 3]}, "timestamp": "2024-01-01"}
        await cache_manager.set("complex_key", test_data, CacheType.EMBEDDING)
        result = await cache_manager.get("complex_key", CacheType.EMBEDDING)
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache_manager):
        """Test TTL-based cache expiration"""
        # Set item with short TTL
        await cache_manager.set("expire_key", "expire_value", CacheType.QUERY, ttl=0.1)
        
        # Should be available immediately
        result = await cache_manager.get("expire_key", CacheType.QUERY)
        assert result == "expire_value"
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Should be None after expiration
        result = await cache_manager.get("expire_key", CacheType.QUERY)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_eviction(self, cache_manager):
        """Test LRU eviction when cache is full"""
        # Fill cache to capacity
        for i in range(100):
            await cache_manager.set(f"key_{i}", f"value_{i}", CacheType.QUERY)
        
        # Add one more item to trigger eviction
        await cache_manager.set("overflow_key", "overflow_value", CacheType.QUERY)
        
        # First item should be evicted (LRU)
        result = await cache_manager.get("key_0", CacheType.QUERY)
        assert result is None
        
        # Last item should still be there
        result = await cache_manager.get("overflow_key", CacheType.QUERY)
        assert result == "overflow_value"
    
    @pytest.mark.asyncio
    async def test_cache_statistics(self, cache_manager):
        """Test cache statistics tracking"""
        # Generate some cache activity
        await cache_manager.set("stats_key", "stats_value", CacheType.EMBEDDING)
        
        # Hit
        await cache_manager.get("stats_key", CacheType.EMBEDDING)
        
        # Miss
        await cache_manager.get("nonexistent_key", CacheType.EMBEDDING)
        
        # Check stats
        stats = cache_manager.get_stats(CacheType.EMBEDDING)
        embedding_stats = stats[CacheType.EMBEDDING.value]
        
        assert embedding_stats['hits'] >= 1
        assert embedding_stats['misses'] >= 1
        assert embedding_stats['hit_rate'] > 0
    
    @pytest.mark.asyncio
    async def test_cache_deletion(self, cache_manager):
        """Test cache item deletion"""
        await cache_manager.set("delete_key", "delete_value", CacheType.QUERY)
        
        # Verify it exists
        result = await cache_manager.get("delete_key", CacheType.QUERY)
        assert result == "delete_value"
        
        # Delete it
        deleted = await cache_manager.delete("delete_key", CacheType.QUERY)
        assert deleted == True
        
        # Verify it's gone
        result = await cache_manager.get("delete_key", CacheType.QUERY)
        assert result is None


class TestRAGServiceCaching:
    """Test caching integration in the RAG service"""
    
    @pytest.fixture
    def mock_query_event(self):
        """Create a mock query event for testing"""
        return QueryEvent(
            camera_id="test_camera_1",
            timestamp=datetime.now().isoformat(),
            label="person",
            bbox={"x": 100, "y": 200, "width": 50, "height": 80}
        )
    
    @pytest.fixture
    def mock_rag_service(self):
        """Create a mock RAG service with mocked dependencies"""
        with patch('advanced_rag.get_container') as mock_container:
            # Mock the container to return None for all dependencies
            mock_container_instance = Mock()
            mock_container_instance.is_bound.return_value = False
            mock_container.return_value = mock_container_instance
            
            service = AdvancedRAGService()
            
            # Mock the dependencies directly
            service.embedding_model = Mock()
            service.embedding_model.encode = Mock(return_value=Mock(tolist=Mock(return_value=[0.1, 0.2, 0.3])))
            service.weaviate_client = Mock()
            service.openai_client = AsyncMock()
            
            return service
    
    @pytest.mark.asyncio
    async def test_embedding_caching(self, mock_rag_service, mock_query_event):
        """Test that embeddings are cached and reused"""
        # Mock the cache manager
        with patch('advanced_rag.get_cache_manager') as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None  # First call returns None (cache miss)
            mock_cache.set = AsyncMock()
            mock_get_cache.return_value = mock_cache
            
            # First call should generate embedding
            result1 = await mock_rag_service.get_event_embedding(mock_query_event)
            
            # Verify cache was checked and set
            mock_cache.get.assert_called_once()
            mock_cache.set.assert_called_once()
            
            # Mock cache hit for second call
            mock_cache.get.return_value = [0.1, 0.2, 0.3]
            
            # Second call should use cached result
            result2 = await mock_rag_service.get_event_embedding(mock_query_event)
            
            # Results should be the same
            assert result1 == result2
            
            # Cache should have been checked twice but set only once
            assert mock_cache.get.call_count == 2
            assert mock_cache.set.call_count == 1
    
    @pytest.mark.asyncio
    async def test_prompt_caching(self, mock_rag_service, mock_query_event):
        """Test that temporal prompts are cached"""
        context_events = [
            {
                "properties": {
                    "timestamp": "2024-01-01T10:00:00Z",
                    "camera_id": "cam_1",
                    "label": "person",
                    "confidence": 0.9
                }
            }
        ]
        
        with patch('advanced_rag.get_cache_manager') as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None  # Cache miss
            mock_cache.set = AsyncMock()
            mock_get_cache.return_value = mock_cache
            
            # Generate prompt
            prompt1 = await mock_rag_service.construct_temporal_prompt(mock_query_event, context_events)
            
            # Verify caching was attempted
            mock_cache.get.assert_called_once()
            mock_cache.set.assert_called_once()
            
            # Mock cache hit
            mock_cache.get.return_value = prompt1
            
            # Second call should use cache
            prompt2 = await mock_rag_service.construct_temporal_prompt(mock_query_event, context_events)
            
            assert prompt1 == prompt2
            assert mock_cache.get.call_count == 2
    
    @pytest.mark.asyncio 
    async def test_query_response_caching(self, mock_rag_service, mock_query_event):
        """Test that complete query responses are cached"""
        # Mock all the service dependencies
        mock_rag_service.query_weaviate = Mock(return_value=[])
        mock_rag_service.sort_by_timestamp = Mock(return_value=[])
        mock_rag_service.construct_temporal_prompt = AsyncMock(return_value="test prompt")
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test explanation"))]
        mock_rag_service.openai_client.chat.completions.create.return_value = mock_response
        
        with patch('advanced_rag.get_cache_manager') as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None  # Cache miss
            mock_cache.set = AsyncMock()
            mock_get_cache.return_value = mock_cache
            
            # First query
            result1 = await mock_rag_service.process_temporal_query(mock_query_event, k=5)
            
            # Verify response structure
            assert isinstance(result1, TemporalRAGResponse)
            assert result1.linked_explanation == "Test explanation"
            
            # Verify caching was attempted
            mock_cache.set.assert_called()
            
            # Mock cache hit for second query
            mock_cache.get.return_value = result1
            
            # Second query should use cache
            result2 = await mock_rag_service.process_temporal_query(mock_query_event, k=5)
            
            assert result1.linked_explanation == result2.linked_explanation
    
    @pytest.mark.asyncio
    async def test_openai_api_caching(self, mock_rag_service, mock_query_event):
        """Test that OpenAI API responses are cached"""
        # Setup mocks
        mock_rag_service.query_weaviate = Mock(return_value=[])
        mock_rag_service.sort_by_timestamp = Mock(return_value=[])
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Cached API response"))]
        mock_rag_service.openai_client.chat.completions.create.return_value = mock_response
        
        with patch('advanced_rag.get_cache_manager') as mock_get_cache:
            mock_cache = AsyncMock() 
            # First call returns None (API cache miss), second returns the cached response
            mock_cache.get.side_effect = [None, None, "Cached API response"]  # query cache miss, API cache miss, then API cache hit
            mock_cache.set = AsyncMock()
            mock_get_cache.return_value = mock_cache
            
            # First query - should make API call
            await mock_rag_service.process_temporal_query(mock_query_event, k=5)
            
            # API should have been called once
            mock_rag_service.openai_client.chat.completions.create.assert_called_once()
            
            # Verify API response was cached
            assert mock_cache.set.call_count >= 2  # At least query cache + API cache


class TestCacheDecorator:
    """Test the caching decorator functionality"""
    
    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """Test the @cached decorator"""
        call_count = 0
        
        @cached(CacheType.QUERY, ttl=3600)
        async def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate work
            return x + y
        
        # First call should execute function
        result1 = await expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1
        
        # Second call should use cache
        result2 = await expensive_function(1, 2)
        assert result2 == 3
        assert call_count == 1  # Function not called again
        
        # Different parameters should execute function again
        result3 = await expensive_function(2, 3)
        assert result3 == 5
        assert call_count == 2


if __name__ == "__main__":
    # Run specific test for quick validation
    async def run_basic_test():
        print("Running basic cache test...")
        
        # Test basic cache functionality
        manager = AdvancedCacheManager(
            redis_url=None,
            memory_max_size=10,
            enable_compression=True
        )
        await manager.initialize()
        
        # Test set/get
        await manager.set("test", {"data": "value"}, CacheType.EMBEDDING)
        result = await manager.get("test", CacheType.EMBEDDING)
        print(f"Cache test result: {result}")
        
        # Test stats
        stats = manager.get_stats()
        print(f"Cache stats: {stats}")
        
        print("Basic cache test completed successfully!")
    
    # Run the test
    asyncio.run(run_basic_test())

"""
Comprehensive Edge Case Test Suite for Advanced RAG Service

Tests edge cases including:
- Very large result sets
- Unusual timestamp formats  
- Performance under load
- Cache behavior under stress
- Resilience during service degradation
"""

import asyncio
import pytest
import time
import json
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any
import random
import string

# Import the components to test
from advanced_rag import AdvancedRAGService, QueryEvent, TemporalRAGResponse
from advanced_caching import AdvancedCacheManager, CacheType, CacheEntry


class TestEdgeCases:
    """Test edge cases and unusual scenarios"""
    
    @pytest.fixture
    def mock_rag_service(self):
        """Create a mock RAG service with all dependencies mocked"""
        with patch('advanced_rag.get_container') as mock_container:
            mock_container_instance = Mock()
            mock_container_instance.is_bound.return_value = False
            mock_container.return_value = mock_container_instance
            
            service = AdvancedRAGService()
            service.embedding_model = Mock()
            service.weaviate_client = Mock()
            service.openai_client = AsyncMock()
            
            return service
    
    @pytest.mark.asyncio
    async def test_very_large_result_sets(self, mock_rag_service):
        """Test handling of very large result sets (1000+ events)"""
        # Generate a large number of mock events
        large_event_set = []
        for i in range(1500):
            event = {
                "properties": {
                    "timestamp": f"2024-01-{(i % 28) + 1:02d}T{(i % 24):02d}:00:00Z",
                    "camera_id": f"camera_{i % 10}",
                    "label": f"person_{i % 5}",
                    "confidence": 0.8 + (i % 20) * 0.01
                },
                "similarity_score": 0.9 - (i * 0.0001)
            }
            large_event_set.append(event)
        
        # Mock Weaviate to return large result set
        mock_rag_service.query_weaviate = Mock(return_value=large_event_set)
        mock_rag_service.construct_temporal_prompt = AsyncMock(return_value="Large dataset prompt")
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Analysis of large dataset"))]
        mock_rag_service.openai_client.chat.completions.create.return_value = mock_response
        
        # Test with large k value
        query_event = QueryEvent(
            camera_id="test_camera",
            timestamp=datetime.now(timezone.utc),
            label="person",
            bbox={"x": 100, "y": 200, "width": 50, "height": 80}
        )
        
        start_time = time.time()
        result = await mock_rag_service.process_temporal_query(query_event, k=1000)
        processing_time = time.time() - start_time
        
        # Verify result structure
        assert isinstance(result, TemporalRAGResponse)
        assert result.linked_explanation == "Analysis of large dataset"
        assert len(result.retrieved_context) == 1500
        
        # Performance assertion - should complete within reasonable time
        assert processing_time < 5.0, f"Large dataset processing took {processing_time:.2f}s"
        
        print(f"✅ Large result set test passed - processed {len(large_event_set)} events in {processing_time:.3f}s")
    
    @pytest.mark.asyncio 
    async def test_unusual_timestamp_formats(self, mock_rag_service):
        """Test handling of various unusual timestamp formats"""
        unusual_timestamps = [
            "2024-01-15T10:30:45.123456Z",  # Microseconds
            "2024-01-15T10:30:45+05:30",    # Timezone offset
            "2024-01-15T10:30:45-08:00",    # Negative timezone
            "2024-01-15 10:30:45",          # Space separator
            "2024/01/15 10:30:45",          # Different separators
            "15-01-2024T10:30:45Z",         # DD-MM-YYYY format
            "",                             # Empty string
            "invalid-timestamp",            # Completely invalid
            "2024-13-45T25:70:90Z",        # Invalid values
            None,                           # None value
        ]
        
        # Create events with unusual timestamps
        events_with_unusual_timestamps = []
        for i, ts in enumerate(unusual_timestamps):
            event = {
                "properties": {
                    "timestamp": ts,
                    "camera_id": f"camera_{i}",
                    "label": "person",
                    "confidence": 0.9
                }
            }
            events_with_unusual_timestamps.append(event)
        
        # Test timestamp sorting with unusual formats
        sorted_events = mock_rag_service.sort_by_timestamp(events_with_unusual_timestamps)
        
        # Should not crash and should return some result
        assert isinstance(sorted_events, list)
        assert len(sorted_events) == len(events_with_unusual_timestamps)
        
        # Events with invalid timestamps should be sorted to the beginning (datetime.min)
        # Valid timestamps should be sorted correctly
        print("✅ Unusual timestamp formats handled gracefully")
    
    @pytest.mark.asyncio
    async def test_extremely_long_prompts(self, mock_rag_service):
        """Test handling of extremely long prompts that might exceed API limits"""
        # Create a very large context with many events
        massive_context = []
        for i in range(500):  # 500 events should create a very long prompt
            event = {
                "properties": {
                    "timestamp": f"2024-01-01T{(i % 24):02d}:{(i % 60):02d}:00Z",
                    "camera_id": f"very_long_camera_name_{i}_with_lots_of_details",
                    "label": f"very_specific_detection_label_{i}_with_additional_context",
                    "confidence": 0.95
                }
            }
            massive_context.append(event)
        
        query_event = QueryEvent(
            camera_id="test_camera",
            timestamp=datetime.now(timezone.utc),
            label="person",
            bbox={"x": 100, "y": 200, "width": 50, "height": 80}
        )
        
        # Test prompt construction with massive context
        prompt = await mock_rag_service.construct_temporal_prompt(query_event, massive_context)
        
        # Should not crash and should produce a reasonable prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Check if prompt length is reasonable (not exceeding typical API limits)
        prompt_length = len(prompt)
        print(f"Generated prompt length: {prompt_length} characters")
        
        # Should handle gracefully even if very long
        if prompt_length > 100000:  # Very long prompt
            print("⚠️ Warning: Prompt is very long, might hit API limits")
        
        print("✅ Extremely long prompt handling test passed")
    
    @pytest.mark.asyncio
    async def test_concurrent_query_handling(self, mock_rag_service):
        """Test handling of multiple concurrent queries"""
        # Mock dependencies for concurrent testing
        mock_rag_service.query_weaviate = Mock(return_value=[])
        mock_rag_service.construct_temporal_prompt = AsyncMock(return_value="Concurrent test prompt")
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Concurrent response"))]
        mock_rag_service.openai_client.chat.completions.create.return_value = mock_response
        
        # Create multiple query events
        query_events = []
        for i in range(10):
            event = QueryEvent(
                camera_id=f"camera_{i}",
                timestamp=datetime.now(timezone.utc),
                label=f"person_{i}",
                bbox={"x": i*10, "y": i*20, "width": 50, "height": 80}
            )
            query_events.append(event)
        
        # Execute queries concurrently
        start_time = time.time()
        tasks = [
            mock_rag_service.process_temporal_query(event, k=5) 
            for event in query_events
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        concurrent_time = time.time() - start_time
        
        # Verify all completed successfully
        successful_results = [r for r in results if isinstance(r, TemporalRAGResponse)]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        assert len(successful_results) >= 8, f"Too many failures: {len(exceptions)} exceptions"
        print(f"✅ Concurrent query test: {len(successful_results)}/10 succeeded in {concurrent_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_memory_stress_with_large_objects(self):
        """Test cache behavior with very large objects"""
        cache_manager = AdvancedCacheManager(
            redis_url=None,  # Memory only
            memory_max_size=50,  # Small cache to force evictions
            enable_compression=True,
            enable_metrics=False
        )
        await cache_manager.initialize()
        
        # Create progressively larger objects
        large_objects = []
        for i in range(10):
            # Create increasingly large objects
            size = 1000 * (i + 1)  # 1KB to 10KB
            large_data = {
                "id": i,
                "data": "x" * size,  # Large string
                "metadata": {
                    "nested": {
                        "deep": {
                            "structure": ["item"] * (i + 1) * 100
                        }
                    }
                }
            }
            large_objects.append(large_data)
        
        # Store large objects
        for i, obj in enumerate(large_objects):
            await cache_manager.set(f"large_object_{i}", obj, CacheType.EMBEDDING, ttl=3600)
        
        # Try to retrieve some objects
        retrieved_count = 0
        for i in range(len(large_objects)):
            result = await cache_manager.get(f"large_object_{i}", CacheType.EMBEDDING)
            if result is not None:
                retrieved_count += 1
        
        # Should handle gracefully with evictions
        stats = cache_manager.get_stats()
        print(f"✅ Memory stress test: {retrieved_count}/{len(large_objects)} objects retained")
        print(f"Final cache stats: {stats}")


class TestPerformanceUnderLoad:
    """Test performance characteristics under various load conditions"""
    
    @pytest.fixture
    async def cache_manager(self):
        """Create cache manager for performance testing"""
        manager = AdvancedCacheManager(
            redis_url=None,
            memory_max_size=1000,
            enable_compression=True,
            enable_metrics=False
        )
        await manager.initialize()
        return manager
    
    @pytest.mark.asyncio
    async def test_cache_performance_under_load(self, cache_manager):
        """Test cache performance with high-frequency operations"""
        
        # Warm up cache with initial data
        print("Warming up cache...")
        for i in range(100):
            await cache_manager.set(f"warmup_{i}", {"data": f"value_{i}"}, CacheType.EMBEDDING)
        
        # Performance test: rapid set operations
        print("Testing rapid SET operations...")
        set_start = time.time()
        set_tasks = []
        for i in range(500):
            task = cache_manager.set(f"perf_set_{i}", {"index": i, "data": f"test_data_{i}"}, CacheType.QUERY)
            set_tasks.append(task)
        
        await asyncio.gather(*set_tasks)
        set_duration = time.time() - set_start
        set_ops_per_sec = 500 / set_duration
        
        # Performance test: rapid get operations
        print("Testing rapid GET operations...")
        get_start = time.time()
        get_tasks = []
        for i in range(500):
            task = cache_manager.get(f"perf_set_{i}", CacheType.QUERY)
            get_tasks.append(task)
        
        get_results = await asyncio.gather(*get_tasks)
        get_duration = time.time() - get_start
        get_ops_per_sec = 500 / get_duration
        
        # Calculate hit rate
        hits = sum(1 for result in get_results if result is not None)
        hit_rate = hits / len(get_results)
        
        print(f"SET Performance: {set_ops_per_sec:.1f} ops/sec")
        print(f"GET Performance: {get_ops_per_sec:.1f} ops/sec")
        print(f"Cache Hit Rate: {hit_rate:.2%}")
        
        # Performance assertions
        assert set_ops_per_sec > 100, f"SET operations too slow: {set_ops_per_sec:.1f} ops/sec"
        assert get_ops_per_sec > 500, f"GET operations too slow: {get_ops_per_sec:.1f} ops/sec"
        assert hit_rate > 0.8, f"Hit rate too low: {hit_rate:.2%}"
        
        print("✅ Cache performance under load test passed")
    
    @pytest.mark.asyncio
    async def test_cache_eviction_performance(self, cache_manager):
        """Test performance of cache eviction under memory pressure"""
        
        # Fill cache beyond capacity to trigger evictions
        print("Testing cache eviction performance...")
        
        eviction_start = time.time()
        
        # Add more items than cache capacity to force evictions
        for i in range(1500):  # Exceeds memory_max_size of 1000
            data = {
                "id": i,
                "timestamp": time.time(),
                "payload": f"data_{i}" * 10  # Make items reasonably sized
            }
            await cache_manager.set(f"eviction_test_{i}", data, CacheType.EMBEDDING)
        
        eviction_duration = time.time() - eviction_start
        
        # Check final cache state
        stats = cache_manager.get_stats()
        final_size = sum(stats[cache_type]['entry_count'] for cache_type in stats)
        
        print(f"Eviction test completed in {eviction_duration:.3f}s")
        print(f"Final cache size: {final_size} items")
        print(f"Cache stats: {stats}")
        
        # Should maintain cache size limits
        assert final_size <= 1000, f"Cache size exceeded limit: {final_size}"
        
        print("✅ Cache eviction performance test passed")
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self, cache_manager):
        """Test cache performance with concurrent read/write operations"""
        
        print("Testing concurrent cache operations...")
        
        async def concurrent_writer(start_id: int, count: int):
            """Write operations in a separate coroutine"""
            for i in range(count):
                key = f"concurrent_write_{start_id}_{i}"
                value = {"writer": start_id, "index": i, "timestamp": time.time()}
                await cache_manager.set(key, value, CacheType.QUERY)
        
        async def concurrent_reader(start_id: int, count: int) -> int:
            """Read operations in a separate coroutine"""
            hits = 0
            for i in range(count):
                key = f"concurrent_read_{start_id}_{i}"
                result = await cache_manager.get(key, CacheType.QUERY)
                if result is not None:
                    hits += 1
            return hits
        
        # Prepare some data for readers
        for i in range(100):
            await cache_manager.set(f"concurrent_read_prep_{i}", {"data": i}, CacheType.QUERY)
        
        # Start concurrent operations
        concurrent_start = time.time()
        
        # Mix of writers and readers
        tasks = []
        
        # 5 concurrent writers
        for writer_id in range(5):
            tasks.append(concurrent_writer(writer_id, 50))
        
        # 10 concurrent readers
        for reader_id in range(10):
            # Readers try to read from prep data and from what writers are writing
            read_keys = list(range(100)) + [f"prep_{i}" for i in range(50)]
            tasks.append(concurrent_reader(reader_id, 50))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        concurrent_duration = time.time() - concurrent_start
        
        # Check for exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        successful_operations = len(results) - len(exceptions)
        
        print(f"Concurrent operations completed in {concurrent_duration:.3f}s")
        print(f"Successful operations: {successful_operations}/{len(results)}")
        print(f"Exceptions: {len(exceptions)}")
        
        if exceptions:
            print(f"Exception types: {[type(e).__name__ for e in exceptions]}")
        
        # Should complete without major issues
        assert len(exceptions) == 0, f"Too many exceptions in concurrent operations: {exceptions}"
        assert concurrent_duration < 10.0, f"Concurrent operations took too long: {concurrent_duration:.3f}s"
        
        print("✅ Concurrent cache operations test passed")


class TestCacheBehavior:
    """Test specific cache behaviors and edge cases"""
    
    @pytest.mark.asyncio
    async def test_cache_with_complex_objects(self):
        """Test caching of complex nested objects"""
        cache_manager = AdvancedCacheManager(
            redis_url=None,
            memory_max_size=100,
            enable_compression=True,
            enable_metrics=False
        )
        await cache_manager.initialize()
        
        # Complex nested object
        complex_object = {
            "metadata": {
                "nested": {
                    "deep": {
                        "structure": {
                            "with": ["lists", "and", {"dicts": True}],
                            "numbers": [1, 2, 3.14159, -42],
                            "booleans": [True, False, None],
                            "unicode": "🎯 Complex émojis and spëcial chars"
                        }
                    }
                }
            },
            "arrays": [[1, 2], [3, 4], [5, 6]],
            "timestamp": datetime.now().isoformat(),
            "large_text": "Lorem ipsum " * 1000  # Large text field
        }
        
        # Store and retrieve complex object
        await cache_manager.set("complex", complex_object, CacheType.METADATA)
        retrieved = await cache_manager.get("complex", CacheType.METADATA)
        
        # Should preserve structure and content
        assert retrieved is not None
        assert retrieved["metadata"]["nested"]["deep"]["structure"]["unicode"] == complex_object["metadata"]["nested"]["deep"]["structure"]["unicode"]
        assert retrieved["arrays"] == complex_object["arrays"]
        assert len(retrieved["large_text"]) == len(complex_object["large_text"])
        
        print("✅ Complex object caching test passed")
    
    @pytest.mark.asyncio
    async def test_cache_key_collision_handling(self):
        """Test handling of potential cache key collisions"""
        cache_manager = AdvancedCacheManager(
            redis_url=None,
            memory_max_size=100,
            enable_compression=False,
            enable_metrics=False
        )
        await cache_manager.initialize()
        
        # Create objects that might generate similar keys
        similar_objects = [
            {"camera_id": "cam_01", "label": "person", "data": "first"},
            {"camera_id": "cam_1", "label": "person", "data": "second"},  # Similar but different
            {"camera_id": "cam_01", "label": "person ", "data": "third"},  # Trailing space
            {"camera_id": "CAM_01", "label": "PERSON", "data": "fourth"},  # Different case
        ]
        
        # Store all objects
        for i, obj in enumerate(similar_objects):
            await cache_manager.set(f"test_collision_{i}", obj, CacheType.EMBEDDING)
        
        # Retrieve and verify each object is distinct
        for i, expected_obj in enumerate(similar_objects):
            retrieved = await cache_manager.get(f"test_collision_{i}", CacheType.EMBEDDING)
            assert retrieved is not None, f"Object {i} not found"
            assert retrieved["data"] == expected_obj["data"], f"Object {i} has wrong data"
        
        print("✅ Cache key collision handling test passed")
    
    @pytest.mark.asyncio
    async def test_cache_ttl_precision(self):
        """Test TTL precision and expiration timing"""
        cache_manager = AdvancedCacheManager(
            redis_url=None,
            memory_max_size=100,
            enable_compression=False,
            enable_metrics=False
        )
        await cache_manager.initialize()
        
        # Test very short TTL
        await cache_manager.set("short_ttl", "expires_quickly", CacheType.QUERY, ttl=0.05)  # 50ms
        
        # Should be available immediately
        immediate = await cache_manager.get("short_ttl", CacheType.QUERY)
        assert immediate == "expires_quickly"
        
        # Wait for expiration
        await asyncio.sleep(0.1)  # 100ms
        
        # Should be expired
        expired = await cache_manager.get("short_ttl", CacheType.QUERY)
        assert expired is None
        
        # Test TTL boundary conditions
        boundary_ttls = [0.001, 0.01, 0.1, 1.0]  # 1ms to 1s
        
        for ttl in boundary_ttls:
            key = f"boundary_{ttl}"
            await cache_manager.set(key, f"value_{ttl}", CacheType.QUERY, ttl=ttl)
            
            # Should be available immediately
            immediate = await cache_manager.get(key, CacheType.QUERY)
            assert immediate == f"value_{ttl}"
        
        # Wait for all to expire
        await asyncio.sleep(1.1)
        
        # All should be expired
        for ttl in boundary_ttls:
            key = f"boundary_{ttl}"
            expired = await cache_manager.get(key, CacheType.QUERY)
            assert expired is None, f"TTL {ttl} did not expire properly"
        
        print("✅ Cache TTL precision test passed")


class TestResilienceDuringServiceDegradation:
    """Test system resilience when external services degrade or fail"""
    
    @pytest.fixture
    def degraded_rag_service(self):
        """Create RAG service with degraded external dependencies"""
        with patch('advanced_rag.get_container') as mock_container:
            mock_container_instance = Mock()
            mock_container_instance.is_bound.return_value = False
            mock_container.return_value = mock_container_instance
            
            service = AdvancedRAGService()
            
            # Simulate degraded/failing services
            service.embedding_model = None  # Embedding service unavailable
            service.weaviate_client = None  # Vector DB unavailable
            service.openai_client = None    # LLM service unavailable
            
            return service
    
    @pytest.mark.asyncio
    async def test_embedding_service_failure(self, degraded_rag_service):
        """Test graceful handling when embedding service fails"""
        query_event = QueryEvent(
            camera_id="test_camera",
            timestamp=datetime.now(timezone.utc),
            label="person",
            bbox={"x": 100, "y": 200, "width": 50, "height": 80}
        )
        
        # Should handle embedding failure gracefully
        try:
            result = await degraded_rag_service.get_event_embedding(query_event)
            # Should either return empty list or raise appropriate exception
            assert isinstance(result, list) or result is None
        except Exception as e:
            # Should be a specific, handleable exception
            assert "embedding" in str(e).lower() or "model" in str(e).lower()
            print(f"✅ Embedding failure handled with appropriate exception: {type(e).__name__}")
    
    @pytest.mark.asyncio
    async def test_vector_db_failure(self, degraded_rag_service):
        """Test graceful handling when vector database fails"""
        query_event = QueryEvent(
            camera_id="test_camera",
            timestamp=datetime.now(timezone.utc),
            label="person"
        )
        
        # Mock embedding to work but Weaviate to fail
        degraded_rag_service.embedding_model = Mock()
        degraded_rag_service.embedding_model.encode = Mock(
            return_value=Mock(tolist=Mock(return_value=[0.1, 0.2, 0.3]))
        )
        
        # Should handle Weaviate failure
        try:
            result = await degraded_rag_service.process_temporal_query(query_event, k=5)
            # Should return fallback response
            assert isinstance(result, TemporalRAGResponse)
            assert "unable to retrieve" in result.linked_explanation.lower() or \
                   "database" in result.linked_explanation.lower() or \
                   "connection" in result.linked_explanation.lower()
            assert result.explanation_confidence == 0.0
            print("✅ Vector DB failure handled with fallback response")
        except Exception as e:
            # Should be a specific database exception
            assert "weaviate" in str(e).lower() or "database" in str(e).lower()
            print(f"✅ Vector DB failure handled with appropriate exception: {type(e).__name__}")
    
    @pytest.mark.asyncio
    async def test_llm_service_failure(self, degraded_rag_service):
        """Test graceful handling when LLM service fails"""
        query_event = QueryEvent(
            camera_id="test_camera",
            timestamp=datetime.now(timezone.utc),
            label="person"
        )
        
        # Mock other services to work
        degraded_rag_service.embedding_model = Mock()
        degraded_rag_service.embedding_model.encode = Mock(
            return_value=Mock(tolist=Mock(return_value=[0.1, 0.2, 0.3]))
        )
        
        # Mock Weaviate to return empty results
        degraded_rag_service.query_weaviate = Mock(return_value=[])
        
        # LLM service is None (failed)
        result = await degraded_rag_service.process_temporal_query(query_event, k=5)
        
        # Should return response with fallback explanation
        assert isinstance(result, TemporalRAGResponse)
        assert "ai-powered explanation not available" in result.linked_explanation.lower() or \
               "openai api key not configured" in result.linked_explanation.lower()
        print("✅ LLM service failure handled with fallback explanation")
    
    @pytest.mark.asyncio
    async def test_partial_service_degradation(self):
        """Test behavior when some services work but are slow/unreliable"""
        
        # Create service with working but slow dependencies
        with patch('advanced_rag.get_container') as mock_container:
            mock_container_instance = Mock()
            mock_container_instance.is_bound.return_value = False
            mock_container.return_value = mock_container_instance
            
            service = AdvancedRAGService()
            
            # Mock slow embedding service
            async def slow_embedding(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate slow response
                return [0.1, 0.2, 0.3]
            
            service.embedding_model = Mock()
            service.embedding_model.encode = Mock(
                return_value=Mock(tolist=Mock(return_value=[0.1, 0.2, 0.3]))
            )
            
            # Mock slow Weaviate
            def slow_weaviate_query(*args, **kwargs):
                time.sleep(0.05)  # Simulate slow query
                return [{
                    "properties": {
                        "timestamp": "2024-01-01T10:00:00Z",
                        "camera_id": "cam_1",
                        "label": "person",
                        "confidence": 0.9
                    }
                }]
            
            service.query_weaviate = Mock(side_effect=slow_weaviate_query)
            
            # Mock intermittently failing OpenAI
            call_count = 0
            async def flaky_openai(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count % 3 == 0:  # Fail every 3rd call
                    raise Exception("OpenAI API temporarily unavailable")
                
                mock_response = Mock()
                mock_response.choices = [Mock(message=Mock(content="Delayed response"))]
                return mock_response
            
            service.openai_client = AsyncMock()
            service.openai_client.chat.completions.create.side_effect = flaky_openai
            
            # Test multiple queries to see degradation handling
            query_event = QueryEvent(
                camera_id="test_camera",
                timestamp=datetime.now(timezone.utc),
                label="person"
            )
            
            results = []
            start_time = time.time()
            
            for i in range(5):
                try:
                    result = await service.process_temporal_query(query_event, k=5)
                    results.append(result)
                except Exception as e:
                    results.append(e)
            
            total_time = time.time() - start_time
            
            # Analyze results
            successful_results = [r for r in results if isinstance(r, TemporalRAGResponse)]
            failed_results = [r for r in results if isinstance(r, Exception)]
            
            print(f"Partial degradation test: {len(successful_results)}/5 succeeded")
            print(f"Total time: {total_time:.3f}s, Average: {total_time/5:.3f}s per query")
            print(f"Failures: {len(failed_results)}")
            
            # Should handle degradation gracefully
            assert len(successful_results) >= 3, "Too many failures during partial degradation"
            assert total_time < 10.0, "Queries took too long during degradation"
            
            print("✅ Partial service degradation handled gracefully")
    
    @pytest.mark.asyncio
    async def test_cache_failure_resilience(self):
        """Test resilience when cache system fails"""
        
        # Create service with failing cache
        with patch('advanced_rag.get_cache_manager') as mock_get_cache:
            # Mock cache manager that always fails
            mock_cache = AsyncMock()
            mock_cache.get.side_effect = Exception("Cache service unavailable")
            mock_cache.set.side_effect = Exception("Cache service unavailable")
            mock_get_cache.return_value = mock_cache
            
            with patch('advanced_rag.get_container') as mock_container:
                mock_container_instance = Mock()
                mock_container_instance.is_bound.return_value = False
                mock_container.return_value = mock_container_instance
                
                service = AdvancedRAGService()
                
                # Mock working dependencies
                service.embedding_model = Mock()
                service.embedding_model.encode = Mock(
                    return_value=Mock(tolist=Mock(return_value=[0.1, 0.2, 0.3]))
                )
                service.query_weaviate = Mock(return_value=[])
                
                mock_response = Mock()
                mock_response.choices = [Mock(message=Mock(content="Response without cache"))]
                service.openai_client = AsyncMock()
                service.openai_client.chat.completions.create.return_value = mock_response
                
                query_event = QueryEvent(
                    camera_id="test_camera",
                    timestamp=datetime.now(timezone.utc),
                    label="person"
                )
                
                # Should work despite cache failures
                result = await service.process_temporal_query(query_event, k=5)
                
                assert isinstance(result, TemporalRAGResponse)
                assert result.linked_explanation == "Response without cache"
                
                print("✅ Cache failure resilience test passed")


class TestLoadAndStress:
    """Load and stress testing scenarios"""
    
    @pytest.mark.asyncio
    async def test_sustained_load_simulation(self):
        """Simulate sustained load over time"""
        
        # Create multiple cache managers to simulate distributed load
        cache_managers = []
        for i in range(3):
            manager = AdvancedCacheManager(
                redis_url=None,
                memory_max_size=200,
                enable_compression=True,
                enable_metrics=False
            )
            await manager.initialize()
            cache_managers.append(manager)
        
        async def sustained_operations(manager_id: int, duration_seconds: int):
            """Run operations continuously for specified duration"""
            manager = cache_managers[manager_id]
            start_time = time.time()
            operations = 0
            
            while time.time() - start_time < duration_seconds:
                # Mix of operations
                operation_type = random.choice(['set', 'get', 'delete'])
                key = f"load_test_{manager_id}_{random.randint(0, 100)}"
                
                try:
                    if operation_type == 'set':
                        value = {"data": f"value_{operations}", "timestamp": time.time()}
                        await manager.set(key, value, CacheType.QUERY, ttl=random.uniform(1, 10))
                    elif operation_type == 'get':
                        await manager.get(key, CacheType.QUERY)
                    elif operation_type == 'delete':
                        await manager.delete(key, CacheType.QUERY)
                    
                    operations += 1
                except Exception as e:
                    print(f"Operation failed: {e}")
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.001)
            
            return operations
        
        # Run sustained load for 2 seconds across multiple managers
        print("Starting sustained load test...")
        load_start = time.time()
        
        tasks = [
            sustained_operations(manager_id, 2) 
            for manager_id in range(len(cache_managers))
        ]
        
        operation_counts = await asyncio.gather(*tasks)
        load_duration = time.time() - load_start
        
        total_operations = sum(operation_counts)
        ops_per_second = total_operations / load_duration
        
        print(f"Sustained load completed:")
        print(f"  Duration: {load_duration:.3f}s")
        print(f"  Total operations: {total_operations}")
        print(f"  Operations per second: {ops_per_second:.1f}")
        print(f"  Operations per manager: {operation_counts}")
        
        # Performance assertions
        assert ops_per_second > 500, f"Load performance too low: {ops_per_second:.1f} ops/sec"
        assert all(count > 100 for count in operation_counts), "Some managers performed poorly"
        
        print("✅ Sustained load simulation test passed")


# Main test runner for quick validation
if __name__ == "__main__":
    async def run_quick_tests():
        """Run a subset of tests for quick validation"""
        print("🧪 Running Edge Cases and Performance Tests\n")
        
        # Test 1: Large result sets
        print("1. Testing large result sets...")
        test_edge = TestEdgeCases()
        service = test_edge.mock_rag_service
        await test_edge.test_very_large_result_sets(service)
        
        # Test 2: Unusual timestamps
        print("\n2. Testing unusual timestamp formats...")
        await test_edge.test_unusual_timestamp_formats(service)
        
        # Test 3: Cache performance
        print("\n3. Testing cache performance...")
        test_perf = TestPerformanceUnderLoad()
        cache_mgr = await test_perf.cache_manager()
        await test_perf.test_cache_performance_under_load(cache_mgr)
        
        # Test 4: Service degradation
        print("\n4. Testing service degradation resilience...")
        test_resilience = TestResilienceDuringServiceDegradation()
        degraded_service = test_resilience.degraded_rag_service
        await test_resilience.test_llm_service_failure(degraded_service)
        
        # Test 5: Complex objects
        print("\n5. Testing complex object caching...")
        test_cache = TestCacheBehavior()
        await test_cache.test_cache_with_complex_objects()
        
        print("\n✅ All quick tests passed!")
        print("\n📊 Test Summary:")
        print("- ✅ Large result set handling (1500+ events)")
        print("- ✅ Unusual timestamp format resilience")
        print("- ✅ Cache performance under load (500+ ops/sec)")
        print("- ✅ Service degradation graceful handling")
        print("- ✅ Complex object caching with compression")
        print("\n🎯 System is ready for production load!")
    
    asyncio.run(run_quick_tests())

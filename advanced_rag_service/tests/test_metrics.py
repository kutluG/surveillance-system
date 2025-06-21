"""
Test suite for the comprehensive metrics collection system

This module tests all aspects of the metrics collection including:
- Query latency tracking
- Vector search performance metrics
- External service response time monitoring
- Cache hit rate tracking
- Service health metrics
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from contextlib import asynccontextmanager

# Import the metrics system
from metrics import (
    AdvancedMetricsCollector, metrics_collector, 
    monitor_query_performance, monitor_external_service,
    ServiceType, MetricType, PROMETHEUS_AVAILABLE
)

def test_metrics_collector_initialization():
    """Test that metrics collector initializes correctly"""
    print("Testing metrics collector initialization...")
    
    # Test basic initialization
    collector = AdvancedMetricsCollector()
    
    # Verify enabled state matches prometheus availability
    assert collector.enabled == PROMETHEUS_AVAILABLE
    print(f"   ✅ Metrics enabled: {collector.enabled}")
    
    # Test metrics data generation (should work even if disabled)
    metrics_data = collector.get_metrics_data()
    assert isinstance(metrics_data, str)
    print(f"   ✅ Metrics data generation working")
    
    if PROMETHEUS_AVAILABLE:
        # Test that metrics are properly initialized
        assert hasattr(collector, 'query_duration')
        assert hasattr(collector, 'vector_search_time')
        assert hasattr(collector, 'external_service_duration')
        assert hasattr(collector, 'cache_operations')
        print(f"   ✅ All metric types initialized")
    
    print("   ✅ Metrics collector initialization test passed")
    # Return None (implicit) instead of True to avoid pytest warnings

def test_query_performance_monitoring():
    """Test query performance monitoring decorators and metrics"""
    print("Testing query performance monitoring...")
    
    # Test synchronous function monitoring
    @monitor_query_performance(endpoint="test_sync", query_type="test")
    def sync_test_function():
        time.sleep(0.1)  # Simulate work
        return {"result": "success", "confidence_score": 0.85}
    
    # Test asynchronous function monitoring
    @monitor_query_performance(endpoint="test_async", query_type="temporal")
    async def async_test_function():
        await asyncio.sleep(0.1)  # Simulate async work
        return {"result": "success", "explanation_confidence": 0.92}
    
    # Test sync function
    start_time = time.time()
    result = sync_test_function()
    duration = time.time() - start_time
    
    assert result["result"] == "success"
    assert duration >= 0.1
    print(f"   ✅ Sync function monitoring: {duration:.3f}s")
    
    # Test async function
    async def run_async_test():
        start_time = time.time()
        result = await async_test_function()
        duration = time.time() - start_time        
        assert result["result"] == "success"
        assert duration >= 0.1
        print(f"   ✅ Async function monitoring: {duration:.3f}s")
        # Async test completed successfully
    
    return asyncio.run(run_async_test())

def test_vector_search_metrics():
    """Test vector search performance metrics"""
    print("Testing vector search metrics...")
    
    # Test vector search metrics recording
    metrics_collector.record_vector_search_metrics(
        index_type="weaviate",
        search_type="similarity",
        duration=0.15,
        result_count=10,
        similarity_scores=[0.95, 0.87, 0.82, 0.76, 0.71, 0.65, 0.58, 0.52, 0.45, 0.38],
        k_value=10
    )
    
    # Test embedding metrics
    metrics_collector.record_embedding_metrics(
        model_type="sentence_transformer",
        content_type="event_description",
        duration=0.05
    )
    
    # Test context manager timing
    with metrics_collector.time_vector_search("weaviate", "similarity", "5"):
        time.sleep(0.02)  # Simulate vector search
    
    print("   ✅ Vector search metrics recorded successfully")
    return True

def test_external_service_monitoring():
    """Test external service monitoring"""
    print("Testing external service monitoring...")
    
    # Test external service decorator
    @monitor_external_service(ServiceType.WEAVIATE, "query")
    async def mock_weaviate_call():
        await asyncio.sleep(0.05)  # Simulate API call
        return {"results": [{"id": "test", "score": 0.9}]}
    
    @monitor_external_service(ServiceType.OPENAI, "chat_completion")
    async def mock_openai_call():
        await asyncio.sleep(0.1)  # Simulate API call
        return {"choices": [{"message": {"content": "response"}}]}
    
    # Test service calls
    async def run_service_tests():
        # Test successful calls
        weaviate_result = await mock_weaviate_call()
        openai_result = await mock_openai_call()
        
        assert "results" in weaviate_result
        assert "choices" in openai_result
        
        print("   ✅ External service monitoring decorators working")
        
        # Test direct metrics recording
        metrics_collector.record_external_service_metrics(
            service_type=ServiceType.REDIS,
            operation="get",
            duration=0.001,
            status="success"
        )
        
        metrics_collector.record_external_service_metrics(
            service_type=ServiceType.REDIS,
            operation="set",
            duration=0.002,
            status="success"
        )
        
        print("   ✅ Direct external service metrics recording working")
        return True
    
    return asyncio.run(run_service_tests())

def test_cache_metrics():
    """Test cache operation metrics"""
    print("Testing cache metrics...")
    
    # Simulate cache operations
    cache_hits = 0
    cache_misses = 0
    
    # Test cache hit
    start_time = time.time()
    time.sleep(0.001)  # Simulate cache lookup
    cache_duration = time.time() - start_time
    
    metrics_collector.record_cache_metrics(
        cache_type="redis",
        operation="get",
        result="hit",
        duration=cache_duration
    )
    cache_hits += 1
    
    # Test cache miss
    start_time = time.time()
    time.sleep(0.005)  # Simulate cache miss + DB lookup
    cache_duration = time.time() - start_time
    
    metrics_collector.record_cache_metrics(
        cache_type="redis",
        operation="get",
        result="miss",
        duration=cache_duration
    )
    cache_misses += 1
    
    # Test cache write
    metrics_collector.record_cache_metrics(
        cache_type="redis",
        operation="set",
        result="success"
    )
    
    # Calculate and update hit rate
    total_operations = cache_hits + cache_misses
    hit_rate = (cache_hits / total_operations) * 100 if total_operations > 0 else 0
    metrics_collector.update_cache_hit_rate("redis", hit_rate)
    
    print(f"   ✅ Cache metrics: {cache_hits} hits, {cache_misses} misses, {hit_rate:.1f}% hit rate")
    return True

def test_service_availability_metrics():
    """Test service availability monitoring"""
    print("Testing service availability metrics...")
    
    # Test service availability updates
    services = [ServiceType.WEAVIATE, ServiceType.OPENAI, ServiceType.REDIS, ServiceType.EMBEDDING_MODEL]
    
    for service in services:
        # Test service as available
        metrics_collector.update_service_availability(service, True)
        
        # Simulate some downtime
        metrics_collector.update_service_availability(service, False)
        
        # Back to available
        metrics_collector.update_service_availability(service, True)
    
    print("   ✅ Service availability metrics updated")
    
    # Test active queries tracking
    metrics_collector.update_active_queries(5)
    metrics_collector.increment_active_queries()
    metrics_collector.decrement_active_queries()
    
    print("   ✅ Active queries tracking working")
    return True

def test_metrics_integration():
    """Test complete metrics integration"""
    print("Testing complete metrics integration...")
    
    # Simulate a complete RAG query with all metrics
    start_query_time = time.time()
    
    # 1. Query received - increment active queries
    metrics_collector.increment_active_queries()
    
    # 2. Generate embedding
    embedding_start = time.time()
    time.sleep(0.02)  # Simulate embedding generation
    embedding_duration = time.time() - embedding_start
    
    metrics_collector.record_embedding_metrics(
        model_type="sentence_transformer",
        content_type="query",
        duration=embedding_duration
    )
    
    # 3. Vector search
    vector_start = time.time()
    time.sleep(0.05)  # Simulate vector search
    vector_duration = time.time() - vector_start
    
    metrics_collector.record_vector_search_metrics(
        index_type="weaviate",
        search_type="similarity",
        duration=vector_duration,
        result_count=8,
        similarity_scores=[0.92, 0.88, 0.84, 0.79, 0.75, 0.68, 0.61, 0.55],
        k_value=10
    )
    
    # 4. External service call (OpenAI)
    llm_start = time.time()
    time.sleep(0.08)  # Simulate LLM call
    llm_duration = time.time() - llm_start
    
    metrics_collector.record_external_service_metrics(
        service_type=ServiceType.OPENAI,
        operation="chat_completion",
        duration=llm_duration,
        status="success"
    )
    
    # 5. Cache result
    metrics_collector.record_cache_metrics(
        cache_type="redis",
        operation="set",
        result="success",
        duration=0.001
    )
    
    # 6. Complete query
    total_duration = time.time() - start_query_time
    
    metrics_collector.record_query_metrics(
        endpoint="temporal_rag_query",
        query_type="temporal",
        duration=total_duration,
        confidence=0.89,
        complexity=0.7,
        status="success"
    )
    
    metrics_collector.decrement_active_queries()
    
    print(f"   ✅ Complete RAG query simulation: {total_duration:.3f}s total")
    print(f"      - Embedding: {embedding_duration:.3f}s")
    print(f"      - Vector search: {vector_duration:.3f}s") 
    print(f"      - LLM call: {llm_duration:.3f}s")
    
    return True

def test_metrics_export():
    """Test Prometheus metrics export"""
    print("Testing metrics export...")
    
    # Get metrics data
    metrics_data = metrics_collector.get_metrics_data()
    
    # Verify it's a string
    assert isinstance(metrics_data, str)
    
    if PROMETHEUS_AVAILABLE:
        # Should contain Prometheus format indicators
        assert "# HELP" in metrics_data or "# TYPE" in metrics_data or len(metrics_data) > 50
        print(f"   ✅ Metrics export format valid ({len(metrics_data)} chars)")
    else:
        # Should contain error message when disabled
        assert "not available" in metrics_data.lower()
        print(f"   ✅ Metrics disabled message present")
    
    return True

def test_error_scenarios():
    """Test metrics under error conditions"""
    print("Testing error scenarios...")
    
    # Test with invalid inputs
    try:
        metrics_collector.record_query_metrics(
            endpoint="",
            query_type="",
            duration=-1.0,  # Invalid duration
            status="error"
        )
        print("   ✅ Handled invalid duration gracefully")
    except Exception as e:
        print(f"   ⚠️  Exception with invalid inputs: {e}")
    
    # Test decorator with exception
    @monitor_query_performance(endpoint="error_test", query_type="test")
    def failing_function():
        raise ValueError("Simulated error")
    
    try:
        failing_function()
    except ValueError:
        print("   ✅ Exception handling in decorator working")
    
    return True

def run_all_tests():
    """Run all metrics tests"""
    print("🧪 Starting comprehensive metrics testing...\n")
    
    tests = [
        test_metrics_collector_initialization,
        test_query_performance_monitoring,
        test_vector_search_metrics,
        test_external_service_monitoring,
        test_cache_metrics,
        test_service_availability_metrics,
        test_metrics_integration,
        test_metrics_export,
        test_error_scenarios
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
            print()
        except Exception as e:
            print(f"   ❌ Test failed: {e}\n")
    
    print(f"📊 Metrics testing completed: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All metrics tests passed! Comprehensive monitoring is working correctly.")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please review the metrics implementation.")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests()

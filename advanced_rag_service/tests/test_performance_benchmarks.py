"""
Performance Benchmark Suite for Advanced RAG Service

Comprehensive performance testing including:
- Load testing with concurrent users
- Memory usage monitoring
- Response time analysis
- Throughput measurement
- Cache effectiveness analysis
"""

import asyncio
import time
import psutil
import statistics
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import random
import tracemalloc

# Import components to benchmark
from advanced_rag import AdvancedRAGService, QueryEvent, TemporalRAGResponse
from advanced_caching import AdvancedCacheManager, CacheType


@dataclass
class PerformanceMetrics:
    """Container for performance measurement results"""
    operation_name: str
    total_operations: int
    duration_seconds: float
    success_count: int
    failure_count: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    operations_per_second: float
    memory_usage_mb: float
    cache_hit_rate: Optional[float] = None


class PerformanceBenchmark:
    """Performance benchmark runner"""
    
    def __init__(self):
        self.results: List[PerformanceMetrics] = []
    
    async def benchmark_cache_operations(self, operations: int = 1000) -> PerformanceMetrics:
        """Benchmark pure cache operations"""
        print(f"🔥 Benchmarking {operations} cache operations...")
        
        cache_manager = AdvancedCacheManager(
            redis_url=None,  # Memory only for consistent testing
            memory_max_size=500,
            enable_compression=True,
            enable_metrics=False
        )
        await cache_manager.initialize()
        
        # Warm up
        for i in range(100):
            await cache_manager.set(f"warmup_{i}", {"data": f"value_{i}"}, CacheType.EMBEDDING)
        
        # Benchmark data
        response_times = []
        successes = 0
        failures = 0
        
        # Start memory tracking
        tracemalloc.start()
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        start_time = time.time()
        
        # Mixed operations benchmark
        for i in range(operations):
            operation_start = time.time()
            
            try:
                if i % 3 == 0:  # SET operation
                    data = {
                        "id": i,
                        "timestamp": time.time(),
                        "payload": f"benchmark_data_{i}" * random.randint(1, 10)
                    }
                    await cache_manager.set(f"bench_{i}", data, CacheType.QUERY, ttl=3600)
                elif i % 3 == 1:  # GET operation
                    result = await cache_manager.get(f"bench_{i//2}", CacheType.QUERY)
                else:  # DELETE operation
                    await cache_manager.delete(f"bench_{i//3}", CacheType.QUERY)
                
                successes += 1
            except Exception as e:
                failures += 1
                print(f"Operation {i} failed: {e}")
            
            operation_time = time.time() - operation_start
            response_times.append(operation_time)
        
        total_duration = time.time() - start_time
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Calculate statistics
        response_times.sort()
        
        metrics = PerformanceMetrics(
            operation_name="cache_operations",
            total_operations=operations,
            duration_seconds=total_duration,
            success_count=successes,
            failure_count=failures,
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p95_response_time=response_times[int(0.95 * len(response_times))],
            p99_response_time=response_times[int(0.99 * len(response_times))],
            operations_per_second=operations / total_duration,
            memory_usage_mb=end_memory - start_memory
        )
        
        self.results.append(metrics)
        tracemalloc.stop()
        
        print(f"✅ Cache benchmark complete: {metrics.operations_per_second:.1f} ops/sec")
        return metrics
    
    async def benchmark_embedding_generation(self, operations: int = 100) -> PerformanceMetrics:
        """Benchmark embedding generation with caching"""
        print(f"🧠 Benchmarking {operations} embedding operations...")
        
        # Create mock RAG service
        from unittest.mock import Mock, patch
        
        with patch('advanced_rag.get_container') as mock_container:
            mock_container_instance = Mock()
            mock_container_instance.is_bound.return_value = False
            mock_container.return_value = mock_container_instance
            
            service = AdvancedRAGService()
            
            # Mock embedding model with realistic timing
            async def mock_encode(text):
                await asyncio.sleep(0.01)  # Simulate 10ms embedding generation
                return Mock(tolist=Mock(return_value=[random.random() for _ in range(384)]))
            
            service.embedding_model = Mock()
            service.embedding_model.encode = mock_encode
        
        # Generate diverse query events
        query_events = []
        for i in range(operations):
            event = QueryEvent(
                camera_id=f"camera_{i % 10}",  # 10 different cameras
                timestamp=datetime.now(timezone.utc),
                label=random.choice(["person", "vehicle", "animal", "object"]),
                bbox={
                    "x": random.randint(0, 1000),
                    "y": random.randint(0, 1000),
                    "width": random.randint(50, 200),
                    "height": random.randint(50, 200)
                } if random.random() > 0.3 else None
            )
            query_events.append(event)
        
        # Benchmark
        response_times = []
        successes = 0
        failures = 0
        cache_hits = 0
        
        start_time = time.time()
        
        for i, event in enumerate(query_events):
            operation_start = time.time()
            
            try:
                # Some events are duplicates to test caching
                if i > 50 and random.random() < 0.3:
                    event = query_events[random.randint(0, 49)]  # Reuse earlier event
                
                result = await service.get_event_embedding(event)
                
                if result and len(result) > 0:
                    successes += 1
                    # Simple heuristic: very fast responses are likely cache hits
                    if time.time() - operation_start < 0.005:
                        cache_hits += 1
                else:
                    failures += 1
                
            except Exception as e:
                failures += 1
                print(f"Embedding operation {i} failed: {e}")
            
            operation_time = time.time() - operation_start
            response_times.append(operation_time)
        
        total_duration = time.time() - start_time
        
        # Calculate metrics
        response_times.sort()
        cache_hit_rate = cache_hits / successes if successes > 0 else 0
        
        metrics = PerformanceMetrics(
            operation_name="embedding_generation",
            total_operations=operations,
            duration_seconds=total_duration,
            success_count=successes,
            failure_count=failures,
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p95_response_time=response_times[int(0.95 * len(response_times))],
            p99_response_time=response_times[int(0.99 * len(response_times))],
            operations_per_second=operations / total_duration,
            memory_usage_mb=0,  # Not tracked for this test
            cache_hit_rate=cache_hit_rate
        )
        
        self.results.append(metrics)
        
        print(f"✅ Embedding benchmark complete: {metrics.operations_per_second:.1f} ops/sec, {cache_hit_rate:.1%} cache hits")
        return metrics
    
    async def benchmark_concurrent_queries(self, concurrent_users: int = 20, queries_per_user: int = 10) -> PerformanceMetrics:
        """Benchmark concurrent query processing"""
        print(f"👥 Benchmarking {concurrent_users} concurrent users, {queries_per_user} queries each...")
        
        # Create mock RAG service
        from unittest.mock import Mock, AsyncMock, patch
        
        with patch('advanced_rag.get_container') as mock_container:
            mock_container_instance = Mock()
            mock_container_instance.is_bound.return_value = False
            mock_container.return_value = mock_container_instance
            
            service = AdvancedRAGService()
            
            # Mock all dependencies with realistic timing
            service.embedding_model = Mock()
            service.embedding_model.encode = Mock(
                return_value=Mock(tolist=Mock(return_value=[0.1, 0.2, 0.3]))
            )
            
            async def mock_weaviate_query(*args, **kwargs):
                await asyncio.sleep(0.05)  # Simulate 50ms database query
                return [{
                    "properties": {
                        "timestamp": "2024-01-01T10:00:00Z",
                        "camera_id": "test_cam",
                        "label": "person",
                        "confidence": 0.9
                    }
                }]
            
            service.query_weaviate = mock_weaviate_query
            
            async def mock_openai_call(*args, **kwargs):
                await asyncio.sleep(0.2)  # Simulate 200ms API call
                mock_response = Mock()
                mock_response.choices = [Mock(message=Mock(content="Concurrent test response"))]
                return mock_response
            
            service.openai_client = AsyncMock()
            service.openai_client.chat.completions.create = mock_openai_call
        
        async def user_simulation(user_id: int) -> List[float]:
            """Simulate a single user making multiple queries"""
            response_times = []
            
            for query_id in range(queries_per_user):
                query_event = QueryEvent(
                    camera_id=f"user_{user_id}_cam_{query_id % 3}",
                    timestamp=datetime.now(timezone.utc),
                    label=random.choice(["person", "vehicle", "animal"]),
                    bbox={
                        "x": random.randint(0, 1000),
                        "y": random.randint(0, 1000),
                        "width": 100,
                        "height": 100
                    }
                )
                
                query_start = time.time()
                
                try:
                    result = await service.process_temporal_query(query_event, k=5)
                    query_time = time.time() - query_start
                    response_times.append(query_time)
                except Exception as e:
                    print(f"User {user_id} query {query_id} failed: {e}")
                    response_times.append(float('inf'))  # Mark as failure
            
            return response_times
        
        # Run concurrent simulations
        start_time = time.time()
        
        tasks = [user_simulation(user_id) for user_id in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # Aggregate results
        all_response_times = []
        successes = 0
        failures = 0
        
        for user_times in user_results:
            if isinstance(user_times, Exception):
                failures += queries_per_user
                continue
            
            for response_time in user_times:
                if response_time != float('inf'):
                    all_response_times.append(response_time)
                    successes += 1
                else:
                    failures += 1
        
        total_operations = concurrent_users * queries_per_user
        
        if all_response_times:
            all_response_times.sort()
            
            metrics = PerformanceMetrics(
                operation_name="concurrent_queries",
                total_operations=total_operations,
                duration_seconds=total_duration,
                success_count=successes,
                failure_count=failures,
                avg_response_time=statistics.mean(all_response_times),
                min_response_time=min(all_response_times),
                max_response_time=max(all_response_times),
                p95_response_time=all_response_times[int(0.95 * len(all_response_times))],
                p99_response_time=all_response_times[int(0.99 * len(all_response_times))],
                operations_per_second=total_operations / total_duration,
                memory_usage_mb=0
            )
        else:
            # All operations failed
            metrics = PerformanceMetrics(
                operation_name="concurrent_queries",
                total_operations=total_operations,
                duration_seconds=total_duration,
                success_count=0,
                failure_count=total_operations,
                avg_response_time=0,
                min_response_time=0,
                max_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                operations_per_second=0,
                memory_usage_mb=0
            )
        
        self.results.append(metrics)
        
        print(f"✅ Concurrent benchmark complete: {metrics.operations_per_second:.1f} ops/sec, {successes}/{total_operations} successful")
        return metrics
    
    async def benchmark_memory_usage_under_load(self, duration_seconds: int = 30) -> PerformanceMetrics:
        """Benchmark memory usage during sustained load"""
        print(f"💾 Benchmarking memory usage for {duration_seconds} seconds...")
        
        # Create cache manager for memory testing
        cache_manager = AdvancedCacheManager(
            redis_url=None,
            memory_max_size=1000,
            enable_compression=True,
            enable_metrics=False
        )
        await cache_manager.initialize()
        
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_samples = [start_memory]
        
        operations = 0
        successes = 0
        failures = 0
        response_times = []
        
        start_time = time.time()
        
        # Run operations for specified duration
        while time.time() - start_time < duration_seconds:
            operation_start = time.time()
            
            try:
                # Create increasingly complex objects
                size_factor = operations % 100 + 1
                complex_data = {
                    "id": operations,
                    "timestamp": time.time(),
                    "data": "x" * (size_factor * 10),  # Growing data size
                    "nested": {
                        "level1": {
                            "level2": {
                                "arrays": [[i] * size_factor for i in range(size_factor)],
                                "metadata": f"complex_object_{operations}"
                            }
                        }
                    }
                }
                
                # Mix of operations
                if operations % 3 == 0:
                    await cache_manager.set(f"memory_test_{operations}", complex_data, CacheType.EMBEDDING)
                elif operations % 3 == 1:
                    await cache_manager.get(f"memory_test_{operations//2}", CacheType.EMBEDDING)
                else:
                    await cache_manager.delete(f"memory_test_{operations//3}", CacheType.EMBEDDING)
                
                successes += 1
            except Exception as e:
                failures += 1
            
            operations += 1
            response_times.append(time.time() - operation_start)
            
            # Sample memory usage every 100 operations
            if operations % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.001)
        
        total_duration = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024
        max_memory = max(memory_samples)
        avg_memory = statistics.mean(memory_samples)
        
        response_times.sort()
        
        metrics = PerformanceMetrics(
            operation_name="memory_load_test",
            total_operations=operations,
            duration_seconds=total_duration,
            success_count=successes,
            failure_count=failures,
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p95_response_time=response_times[int(0.95 * len(response_times))],
            p99_response_time=response_times[int(0.99 * len(response_times))],
            operations_per_second=operations / total_duration,
            memory_usage_mb=max_memory - start_memory
        )
        
        self.results.append(metrics)
        
        print(f"✅ Memory benchmark complete:")
        print(f"   Operations: {operations} ({metrics.operations_per_second:.1f} ops/sec)")
        print(f"   Memory usage: {start_memory:.1f} → {final_memory:.1f} MB (peak: {max_memory:.1f} MB)")
        
        return metrics
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report"""
        if not self.results:
            return "No benchmark results available."
        
        report = ["🏆 Performance Benchmark Report", "=" * 50, ""]
        
        for metric in self.results:
            report.extend([
                f"📊 {metric.operation_name.upper()}",
                f"   Total Operations: {metric.total_operations:,}",
                f"   Duration: {metric.duration_seconds:.3f}s",
                f"   Success Rate: {metric.success_count}/{metric.total_operations} ({metric.success_count/metric.total_operations:.1%})",
                f"   Throughput: {metric.operations_per_second:.1f} ops/sec",
                "",
                "   Response Times:",
                f"     Average: {metric.avg_response_time*1000:.1f}ms",
                f"     Min: {metric.min_response_time*1000:.1f}ms",
                f"     Max: {metric.max_response_time*1000:.1f}ms",
                f"     95th percentile: {metric.p95_response_time*1000:.1f}ms",
                f"     99th percentile: {metric.p99_response_time*1000:.1f}ms",
                ""
            ])
            
            if metric.memory_usage_mb > 0:
                report.append(f"   Memory Usage: {metric.memory_usage_mb:.1f} MB")
            
            if metric.cache_hit_rate is not None:
                report.append(f"   Cache Hit Rate: {metric.cache_hit_rate:.1%}")
            
            report.extend(["", "-" * 40, ""])
        
        # Performance summary
        avg_throughput = statistics.mean([m.operations_per_second for m in self.results])
        avg_response_time = statistics.mean([m.avg_response_time for m in self.results])
        overall_success_rate = sum(m.success_count for m in self.results) / sum(m.total_operations for m in self.results)
        
        report.extend([
            "📈 OVERALL PERFORMANCE SUMMARY",
            f"   Average Throughput: {avg_throughput:.1f} operations/second",
            f"   Average Response Time: {avg_response_time*1000:.1f}ms",
            f"   Overall Success Rate: {overall_success_rate:.1%}",
            "",
            "🎯 PERFORMANCE TARGETS:",
            f"   ✅ Throughput > 100 ops/sec: {'PASS' if avg_throughput > 100 else 'FAIL'}",
            f"   ✅ Response time < 500ms: {'PASS' if avg_response_time < 0.5 else 'FAIL'}",
            f"   ✅ Success rate > 95%: {'PASS' if overall_success_rate > 0.95 else 'FAIL'}",
        ])
        
        return "\n".join(report)


# Main benchmark runner
async def run_comprehensive_benchmarks():
    """Run all performance benchmarks"""
    print("🚀 Starting Comprehensive Performance Benchmarks\n")
    
    benchmark = PerformanceBenchmark()
    
    try:
        # 1. Cache operations benchmark
        await benchmark.benchmark_cache_operations(1000)
        
        # 2. Embedding generation benchmark
        await benchmark.benchmark_embedding_generation(100)
        
        # 3. Concurrent queries benchmark
        await benchmark.benchmark_concurrent_queries(10, 5)  # Reduced for testing
        
        # 4. Memory usage benchmark
        await benchmark.benchmark_memory_usage_under_load(10)  # Reduced for testing
        
        # Generate and display report
        print("\n" + benchmark.generate_performance_report())
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_comprehensive_benchmarks())

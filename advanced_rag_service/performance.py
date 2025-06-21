"""
Performance monitoring and caching for Advanced RAG Service

Provides caching, performance metrics, and monitoring capabilities
to improve response times and system reliability.
"""

import asyncio
import json
import time
import hashlib
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: Any
    timestamp: float
    ttl: float
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.timestamp + self.ttl
    
    def touch(self):
        """Update hit count"""
        self.hits += 1


class InMemoryCache:
    """High-performance in-memory cache with TTL support"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._lock = asyncio.Lock()
    
    def _generate_key(self, key_data: Any) -> str:
        """Generate cache key from data"""
        if isinstance(key_data, str):
            return key_data
        
        # Create deterministic hash for complex objects
        serialized = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()
    
    async def get(self, key: Any) -> Optional[Any]:
        """Get value from cache"""
        cache_key = self._generate_key(key)
        
        async with self._lock:
            entry = self.cache.get(cache_key)
            if not entry:
                return None
            
            if entry.is_expired:
                del self.cache[cache_key]
                return None
            
            entry.touch()
            return entry.data
    
    async def set(self, key: Any, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache"""
        cache_key = self._generate_key(key)
        ttl = ttl or self.default_ttl
        
        async with self._lock:
            # Evict if cache is full
            if len(self.cache) >= self.max_size and cache_key not in self.cache:
                await self._evict_lru()
            
            self.cache[cache_key] = CacheEntry(
                data=value,
                timestamp=time.time(),
                ttl=ttl
            )
    
    async def delete(self, key: Any) -> bool:
        """Delete value from cache"""
        cache_key = self._generate_key(key)
        
        async with self._lock:
            if cache_key in self.cache:
                del self.cache[cache_key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self.cache.clear()
    
    async def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if not self.cache:
            return
        
        # Find entry with lowest hit count (simple LRU approximation)
        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k].hits)
        del self.cache[lru_key]
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries and return count"""
        expired_keys = []
        
        async with self._lock:
            for key, entry in self.cache.items():
                if entry.is_expired:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
        
        return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = sum(entry.hits for entry in self.cache.values())
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
            "average_hits": total_hits / len(self.cache) if self.cache else 0,
            "expired_count": sum(1 for entry in self.cache.values() if entry.is_expired)
        }


@dataclass 
class PerformanceMetrics:
    """Performance metrics tracking"""
    total_requests: int = 0
    total_response_time: float = 0.0
    error_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    slow_requests: int = 0  # Requests > 5 seconds
    
    @property
    def average_response_time(self) -> float:
        return self.total_response_time / self.total_requests if self.total_requests > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        return self.error_count / self.total_requests if self.total_requests > 0 else 0.0
    
    @property
    def cache_hit_rate(self) -> float:
        total_cache_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / total_cache_requests if total_cache_requests > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.request_times = defaultdict(list)  # Track response times by endpoint
        self._lock = asyncio.Lock()
    
    async def record_request(self, endpoint: str, response_time: float, success: bool = True):
        """Record request metrics"""
        async with self._lock:
            self.metrics.total_requests += 1
            self.metrics.total_response_time += response_time
            
            if not success:
                self.metrics.error_count += 1
            
            if response_time > 5.0:  # Slow request threshold
                self.metrics.slow_requests += 1
            
            # Track per-endpoint metrics
            self.request_times[endpoint].append(response_time)
            
            # Keep only last 100 requests per endpoint
            if len(self.request_times[endpoint]) > 100:
                self.request_times[endpoint] = self.request_times[endpoint][-100:]
    
    async def record_cache_hit(self):
        """Record cache hit"""
        async with self._lock:
            self.metrics.cache_hits += 1
    
    async def record_cache_miss(self):
        """Record cache miss"""
        async with self._lock:
            self.metrics.cache_misses += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        base_metrics = self.metrics.to_dict()
        
        # Add per-endpoint metrics
        endpoint_metrics = {}
        for endpoint, times in self.request_times.items():
            if times:
                endpoint_metrics[endpoint] = {
                    "count": len(times),
                    "avg_response_time": sum(times) / len(times),
                    "min_response_time": min(times),
                    "max_response_time": max(times)
                }
        
        return {
            **base_metrics,
            "endpoint_metrics": endpoint_metrics
        }
    
    async def reset_metrics(self):
        """Reset all metrics"""
        async with self._lock:
            self.metrics = PerformanceMetrics()
            self.request_times.clear()


def cache_result(ttl: float = 300, key_prefix: str = ""):
    """Decorator for caching function results"""
    
    def decorator(func):
        if not hasattr(func, '_cache'):
            func._cache = InMemoryCache(default_ttl=ttl)
        
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{args}:{sorted(kwargs.items())}"
            
            # Try to get from cache
            cached_result = await func._cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Cache miss - execute function
            logger.debug(f"Cache miss for {func.__name__}")
            result = await func(*args, **kwargs)
            
            # Cache the result
            await func._cache.set(cache_key, result, ttl)
            return result
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, just execute (no caching)
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def monitor_performance(endpoint: str = "unknown"):
    """Decorator for monitoring function performance"""
    
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                response_time = time.time() - start_time
                # Record metrics (would need access to global monitor instance)
                logger.info(f"{func.__name__} took {response_time:.3f}s (success: {success})")
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                response_time = time.time() - start_time
                logger.info(f"{func.__name__} took {response_time:.3f}s (success: {success})")
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global instances
cache = InMemoryCache()
performance_monitor = PerformanceMonitor()

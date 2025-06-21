"""
Advanced Caching Strategy for RAG Service

This module implements a sophisticated multi-tier caching system for:
1. Vector embeddings (persistent and in-memory)
2. Frequently requested queries (LRU with smart eviction)
3. External API responses (with TTL and circuit breaker)
4. Redis-backed persistent cache with fallback to in-memory

Key Features:
- Multi-tier caching (Redis + In-Memory + Local File)
- Smart cache warming and preloading
- Cache invalidation strategies
- Performance metrics and monitoring
- Circuit breaker for external dependencies
- Compression for large payloads
"""

import asyncio
import json
import os
import time
import hashlib
import pickle
import gzip
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict
from pathlib import Path
import logging
import numpy as np
from enum import Enum

# Import metrics for cache monitoring
from metrics import metrics_collector

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheType(Enum):
    """Cache type enumeration"""
    EMBEDDING = "embedding"
    QUERY = "query"
    API_RESPONSE = "api_response"
    METADATA = "metadata"


class CacheTier(Enum):
    """Cache tier enumeration"""
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"


@dataclass
class CacheEntry(Generic[T]):
    """Enhanced cache entry with metadata and analytics"""
    data: T
    timestamp: float
    ttl: float
    cache_type: CacheType
    hits: int = 0
    size_bytes: int = 0
    last_accessed: float = field(default_factory=time.time)
    access_pattern: List[float] = field(default_factory=list)
    compression_ratio: float = 1.0
    source_tier: CacheTier = CacheTier.MEMORY
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() > self.timestamp + self.ttl
    
    @property
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return time.time() - self.timestamp
    
    @property
    def access_frequency(self) -> float:
        """Calculate access frequency (hits per minute)"""
        if self.age_seconds == 0:
            return 0
        return (self.hits / self.age_seconds) * 60
    
    def touch(self):
        """Update access metrics"""
        self.hits += 1
        self.last_accessed = time.time()
        # Keep last 10 access times for pattern analysis
        self.access_pattern.append(time.time())
        if len(self.access_pattern) > 10:
            self.access_pattern.pop(0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp,
            'ttl': self.ttl,
            'cache_type': self.cache_type.value,
            'hits': self.hits,
            'size_bytes': self.size_bytes,
            'last_accessed': self.last_accessed,
            'access_pattern': self.access_pattern,
            'compression_ratio': self.compression_ratio,
            'source_tier': self.source_tier.value
        }


@dataclass
class CacheStats:
    """Cache statistics and metrics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate"""
        return 1.0 - self.hit_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'hit_rate': self.hit_rate,
            'miss_rate': self.miss_rate,
            'total_size_bytes': self.total_size_bytes,
            'entry_count': self.entry_count
        }


class CompressedCache:
    """Cache with compression support for large objects"""
    
    @staticmethod
    def compress_data(data: Any) -> bytes:
        """Compress data using gzip"""
        try:
            pickled = pickle.dumps(data)
            compressed = gzip.compress(pickled)
            return compressed
        except Exception as e:
            logger.warning(f"Failed to compress data: {e}")
            return pickle.dumps(data)
    
    @staticmethod
    def decompress_data(compressed_data: bytes) -> Any:
        """Decompress data"""
        try:
            # Try gzip decompression first
            decompressed = gzip.decompress(compressed_data)
            return pickle.loads(decompressed)
        except:
            # Fallback to direct pickle loading
            return pickle.loads(compressed_data)
    
    @staticmethod
    def get_compression_ratio(original_data: Any, compressed_data: bytes) -> float:
        """Calculate compression ratio"""
        try:
            original_size = len(pickle.dumps(original_data))
            compressed_size = len(compressed_data)
            return original_size / compressed_size if compressed_size > 0 else 1.0
        except:
            return 1.0


class SmartEvictionPolicy:
    """Intelligent cache eviction policies"""
    
    @staticmethod
    def lru_score(entry: CacheEntry) -> float:
        """Calculate LRU score (lower = more likely to evict)"""
        return entry.last_accessed
    
    @staticmethod
    def lfu_score(entry: CacheEntry) -> float:
        """Calculate LFU score (lower = more likely to evict)"""
        return entry.access_frequency
    
    @staticmethod
    def hybrid_score(entry: CacheEntry) -> float:
        """Hybrid scoring combining recency, frequency, and size"""
        recency_factor = 0.4
        frequency_factor = 0.4
        size_factor = 0.2
        
        # Normalize scores (0-1)
        recency_score = min(1.0, entry.age_seconds / 3600)  # Normalize by 1 hour
        frequency_score = min(1.0, entry.access_frequency / 10)  # Normalize by 10 hits/min
        size_score = min(1.0, entry.size_bytes / (1024 * 1024))  # Normalize by 1MB
        
        # Higher score = keep longer
        return (recency_factor * (1 - recency_score) +
                frequency_factor * frequency_score +
                size_factor * (1 - size_score))


class AdvancedCacheManager:
    """Sophisticated multi-tier cache manager"""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        memory_max_size: int = 1000,
        disk_cache_dir: Optional[str] = None,
        default_ttl: float = 3600,
        enable_compression: bool = True,
        enable_metrics: bool = True
    ):
        self.redis_url = redis_url
        self.memory_max_size = memory_max_size
        self.disk_cache_dir = Path(disk_cache_dir) if disk_cache_dir else Path("cache")
        self.default_ttl = default_ttl
        self.enable_compression = enable_compression
        self.enable_metrics = enable_metrics
        
        # Initialize cache tiers
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.redis_client: Optional[redis.Redis] = None
        self.disk_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache statistics by type
        self.stats: Dict[CacheType, CacheStats] = {
            cache_type: CacheStats() for cache_type in CacheType
        }
        
        # Locks for thread safety
        self.memory_lock = asyncio.Lock()
        self.redis_lock = asyncio.Lock()
        
        # Eviction policy
        self.eviction_policy = SmartEvictionPolicy()
        
        # Circuit breaker for Redis
        self.redis_circuit_breaker = {
            'failures': 0,
            'last_failure': 0,
            'failure_threshold': 5,
            'recovery_timeout': 60
        }
    
    async def initialize(self):
        """Initialize cache connections"""
        try:
            if self.redis_url:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}. Using memory cache only.")
            self.redis_client = None
    
    def _generate_key(self, key_data: Any, cache_type: CacheType) -> str:
        """Generate deterministic cache key"""
        if isinstance(key_data, str):
            base_key = key_data
        else:
            # Create deterministic hash for complex objects
            serialized = json.dumps(key_data, sort_keys=True, default=str)
            base_key = hashlib.sha256(serialized.encode()).hexdigest()
        
        return f"{cache_type.value}:{base_key}"
    
    def _is_redis_available(self) -> bool:
        """Check if Redis is available (circuit breaker pattern)"""
        if not self.redis_client:
            return False
        
        now = time.time()
        cb = self.redis_circuit_breaker
        
        # If we have too many failures and haven't waited long enough
        if (cb['failures'] >= cb['failure_threshold'] and
            now - cb['last_failure'] < cb['recovery_timeout']):
            return False
        
        return True
    
    def _record_redis_failure(self):
        """Record Redis failure for circuit breaker"""
        cb = self.redis_circuit_breaker
        cb['failures'] += 1
        cb['last_failure'] = time.time()
    
    def _record_redis_success(self):
        """Record Redis success for circuit breaker"""
        self.redis_circuit_breaker['failures'] = 0
    
    async def _get_from_memory(self, cache_key: str) -> Optional[CacheEntry]:
        """Get from memory cache"""
        async with self.memory_lock:
            entry = self.memory_cache.get(cache_key)
            if entry and not entry.is_expired:
                # Move to end (LRU)
                self.memory_cache.move_to_end(cache_key)
                entry.touch()
                return entry
            elif entry:
                # Remove expired entry
                del self.memory_cache[cache_key]
        return None
    
    async def _set_in_memory(self, cache_key: str, entry: CacheEntry):
        """Set in memory cache with eviction"""
        async with self.memory_lock:
            # Evict if necessary
            while len(self.memory_cache) >= self.memory_max_size:                # Find best candidate for eviction
                candidates = list(self.memory_cache.items())
                if candidates:
                    scores = [(k, self.eviction_policy.hybrid_score(v)) 
                             for k, v in candidates]
                    # Sort by score (lowest first)
                    scores.sort(key=lambda x: x[1])
                    evict_key = scores[0][0]
                    
                    evicted_entry = self.memory_cache.pop(evict_key)
                    self.stats[evicted_entry.cache_type].evictions += 1
                    
                    if self.enable_metrics:
                        metrics_collector.record_cache_metrics(
                            evicted_entry.cache_type.value,
                            "eviction",
                            "success"
                        )
            
            self.memory_cache[cache_key] = entry
    
    async def _get_from_redis(self, cache_key: str) -> Optional[CacheEntry]:
        """Get from Redis cache"""
        if not self._is_redis_available():
            return None
        
        try:
            async with self.redis_lock:
                data = await self.redis_client.get(cache_key)
                if data:
                    metadata_key = f"{cache_key}:meta"
                    metadata = await self.redis_client.get(metadata_key)
                    
                    if metadata:
                        meta_dict = json.loads(metadata)
                        entry_data = CompressedCache.decompress_data(data) if self.enable_compression else pickle.loads(data)
                        
                        entry = CacheEntry(
                            data=entry_data,
                            timestamp=meta_dict['timestamp'],
                            ttl=meta_dict['ttl'],
                            cache_type=CacheType(meta_dict['cache_type']),
                            hits=meta_dict['hits'],
                            size_bytes=meta_dict['size_bytes'],
                            last_accessed=meta_dict['last_accessed'],
                            access_pattern=meta_dict['access_pattern'],
                            compression_ratio=meta_dict['compression_ratio'],
                            source_tier=CacheTier.REDIS
                        )
                        
                        if not entry.is_expired:
                            entry.touch()
                            self._record_redis_success()
                            return entry
                        else:
                            # Clean up expired entry
                            await self.redis_client.delete(cache_key, metadata_key)
            
            self._record_redis_success()
            return None
        
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            self._record_redis_failure()
            return None
    
    async def _set_in_redis(self, cache_key: str, entry: CacheEntry):
        """Set in Redis cache"""
        if not self._is_redis_available():
            return
        
        try:
            async with self.redis_lock:
                # Serialize data
                if self.enable_compression:
                    serialized_data = CompressedCache.compress_data(entry.data)
                    entry.compression_ratio = CompressedCache.get_compression_ratio(entry.data, serialized_data)
                else:
                    serialized_data = pickle.dumps(entry.data)
                
                entry.size_bytes = len(serialized_data)
                  # Store data and metadata separately
                metadata_key = f"{cache_key}:meta"
                
                await self.redis_client.setex(
                    cache_key,
                    int(entry.ttl),
                    serialized_data
                )
                
                await self.redis_client.setex(
                    metadata_key,
                    int(entry.ttl),
                    json.dumps(entry.to_dict())
                )
                
                self._record_redis_success()
        
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
            self._record_redis_failure()
    
    async def get(
        self,
        key: Any,
        cache_type: CacheType,
        default: Optional[T] = None
    ) -> Optional[T]:
        """Get value from cache with tier fallback"""
        cache_key = self._generate_key(key, cache_type)
        
        # Try memory cache first
        entry = await self._get_from_memory(cache_key)
        if entry:
            self.stats[cache_type].hits += 1
            if self.enable_metrics:
                metrics_collector.record_cache_metrics(cache_type.value, "get", "hit")
            return entry.data
        
        # Try Redis cache
        entry = await self._get_from_redis(cache_key)
        if entry:
            # Promote to memory cache
            entry.source_tier = CacheTier.MEMORY
            await self._set_in_memory(cache_key, entry)
            
            self.stats[cache_type].hits += 1
            if self.enable_metrics:
                metrics_collector.record_cache_metrics(cache_type.value, "get", "hit")
            return entry.data
        
        # Cache miss
        self.stats[cache_type].misses += 1
        if self.enable_metrics:
            metrics_collector.record_cache_metrics(cache_type.value, "get", "miss")
        
        return default
    
    async def set(
        self,
        key: Any,
        value: T,
        cache_type: CacheType,
        ttl: Optional[float] = None
    ) -> None:
        """Set value in cache across tiers"""
        cache_key = self._generate_key(key, cache_type)
        ttl = ttl or self.default_ttl
        
        entry = CacheEntry(
            data=value,
            timestamp=time.time(),
            ttl=ttl,
            cache_type=cache_type,
            source_tier=CacheTier.MEMORY
        )
        
        # Set in memory cache
        await self._set_in_memory(cache_key, entry)
        
        # Set in Redis cache
        await self._set_in_redis(cache_key, entry)
          # Update statistics
        self.stats[cache_type].entry_count += 1
        
        if self.enable_metrics:
            metrics_collector.record_cache_metrics(cache_type.value, "set", "success")
    
    async def delete(self, key: Any, cache_type: CacheType) -> bool:
        """Delete from all cache tiers"""
        cache_key = self._generate_key(key, cache_type)
        deleted = False
        
        # Delete from memory
        async with self.memory_lock:
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
                deleted = True
        
        # Delete from Redis
        if self._is_redis_available():
            try:
                async with self.redis_lock:
                    result = await self.redis_client.delete(cache_key, f"{cache_key}:meta")
                    if result > 0:
                        deleted = True
                self._record_redis_success()
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
                self._record_redis_failure()
        
        return deleted
    
    async def clear(self, cache_type: Optional[CacheType] = None):
        """Clear cache entries"""
        if cache_type:
            # Clear specific cache type
            keys_to_remove = []
            async with self.memory_lock:
                for key, entry in self.memory_cache.items():
                    if entry.cache_type == cache_type:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.memory_cache[key]
        else:
            # Clear all
            async with self.memory_lock:
                self.memory_cache.clear()
        
        # Reset statistics
        if cache_type:
            self.stats[cache_type] = CacheStats()
        else:
            self.stats = {ct: CacheStats() for ct in CacheType}
    
    def get_stats(self, cache_type: Optional[CacheType] = None) -> Dict[str, Any]:
        """Get cache statistics"""
        if cache_type:
            return {cache_type.value: self.stats[cache_type].to_dict()}
        
        return {ct.value: stats.to_dict() for ct, stats in self.stats.items()}
    
    async def warm_cache(self, warming_functions: Dict[CacheType, Callable]):
        """Warm cache with precomputed data"""
        logger.info("Starting cache warming...")
        
        for cache_type, warm_func in warming_functions.items():
            try:
                logger.info(f"Warming {cache_type.value} cache...")
                await warm_func(self)
                logger.info(f"Completed warming {cache_type.value} cache")
            except Exception as e:
                logger.error(f"Failed to warm {cache_type.value} cache: {e}")
        
        logger.info("Cache warming completed")


# Global cache manager instance
cache_manager: Optional[AdvancedCacheManager] = None


async def get_cache_manager() -> AdvancedCacheManager:
    """Get or create cache manager instance"""
    global cache_manager
    
    if not cache_manager:
        cache_manager = AdvancedCacheManager(
            redis_url=os.getenv("REDIS_URL", "redis://redis:6379/7"),
            memory_max_size=int(os.getenv("CACHE_MEMORY_SIZE", "1000")),
            disk_cache_dir=os.getenv("CACHE_DISK_DIR", "cache"),
            default_ttl=float(os.getenv("CACHE_DEFAULT_TTL", "3600")),
            enable_compression=os.getenv("CACHE_COMPRESSION", "true").lower() == "true",
            enable_metrics=True
        )
        await cache_manager.initialize()
    
    return cache_manager


# Decorator for automatic caching
def cached(
    cache_type: CacheType,
    ttl: Optional[float] = None,
    key_func: Optional[Callable] = None
):
    """Decorator for automatic function result caching"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache_mgr = await get_cache_manager()
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            
            # Try to get from cache
            cached_result = await cache_mgr.get(cache_key, cache_type)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_mgr.set(cache_key, result, cache_type, ttl)
            
            return result
        
        return wrapper
    return decorator

"""
Simple cache implementation for testing without external dependencies
"""

import asyncio
import time
import hashlib
import json
from collections import OrderedDict
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class CacheType(Enum):
    EMBEDDING = "embedding"
    QUERY = "query"
    API_RESPONSE = "api_response"
    METADATA = "metadata"

@dataclass
class CacheEntry:
    data: Any
    timestamp: float
    ttl: float
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.timestamp + self.ttl
    
    def touch(self):
        self.hits += 1

class SimpleCacheManager:
    """Simple cache manager for testing"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize - no-op for simple cache"""
        pass
    
    def _generate_key(self, key: Any, cache_type: CacheType) -> str:
        """Generate cache key"""
        if isinstance(key, str):
            base_key = key
        else:
            serialized = json.dumps(key, sort_keys=True, default=str)
            base_key = hashlib.sha256(serialized.encode()).hexdigest()
        return f"{cache_type.value}:{base_key}"
    
    async def get(self, key: Any, cache_type: CacheType, default: Any = None) -> Any:
        """Get value from cache"""
        cache_key = self._generate_key(key, cache_type)
        
        async with self.lock:
            entry = self.cache.get(cache_key)
            if entry and not entry.is_expired:
                # Move to end (LRU)
                self.cache.move_to_end(cache_key)
                entry.touch()
                return entry.data
            elif entry:
                # Remove expired entry
                del self.cache[cache_key]
        
        return default
    
    async def set(self, key: Any, value: Any, cache_type: CacheType, ttl: float = 3600):
        """Set value in cache"""
        cache_key = self._generate_key(key, cache_type)
        
        entry = CacheEntry(
            data=value,
            timestamp=time.time(),
            ttl=ttl
        )
        
        async with self.lock:
            # Evict if necessary
            while len(self.cache) >= self.max_size:
                # Remove oldest (LRU)
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
            
            self.cache[cache_key] = entry
    
    async def delete(self, key: Any, cache_type: CacheType) -> bool:
        """Delete from cache"""
        cache_key = self._generate_key(key, cache_type)
        
        async with self.lock:
            if cache_key in self.cache:
                del self.cache[cache_key]
                return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get simple stats"""
        return {
            "total_entries": len(self.cache),
            "max_size": self.max_size
        }

# Test the simple cache
async def test_simple_cache():
    print("Testing simple cache implementation...")
    
    cache = SimpleCacheManager(max_size=5)
    await cache.initialize()
    
    # Test set/get
    await cache.set("test", {"value": 123}, CacheType.EMBEDDING)
    result = await cache.get("test", CacheType.EMBEDDING)
    print(f"Set/Get test: {result}")
    assert result == {"value": 123}
    
    # Test cache miss
    miss = await cache.get("missing", CacheType.EMBEDDING)
    print(f"Cache miss: {miss}")
    assert miss is None
    
    # Test TTL
    await cache.set("expire", "temp", CacheType.QUERY, ttl=0.1)
    immediate = await cache.get("expire", CacheType.QUERY)
    print(f"Before expiry: {immediate}")
    assert immediate == "temp"
    
    await asyncio.sleep(0.2)
    expired = await cache.get("expire", CacheType.QUERY)
    print(f"After expiry: {expired}")
    assert expired is None
    
    # Test eviction
    for i in range(7):  # Exceed max_size of 5
        await cache.set(f"item_{i}", f"value_{i}", CacheType.EMBEDDING)
    
    # Early items should be evicted
    early = await cache.get("item_0", CacheType.EMBEDDING)
    late = await cache.get("item_6", CacheType.EMBEDDING)
    print(f"Early item (evicted): {early}")
    print(f"Late item (kept): {late}")
    
    stats = cache.get_stats()
    print(f"Final stats: {stats}")
    
    print("Simple cache test passed!")

if __name__ == "__main__":
    asyncio.run(test_simple_cache())

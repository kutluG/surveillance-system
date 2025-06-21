"""
Simple test for just the caching system without RAG integration
"""

import asyncio
from advanced_caching import AdvancedCacheManager, CacheType

async def test_basic_caching():
    print("Testing basic caching functionality...")
    
    # Create cache manager (memory only for testing)
    manager = AdvancedCacheManager(
        redis_url=None,  # Memory only
        memory_max_size=10,
        enable_compression=True,
        enable_metrics=False  # Disable metrics to avoid issues
    )
    await manager.initialize()
    
    # Test basic set/get
    print("Testing set/get operations...")
    await manager.set("test_key", {"data": "test_value", "number": 42}, CacheType.EMBEDDING)
    result = await manager.get("test_key", CacheType.EMBEDDING)
    print(f"Set/Get result: {result}")
    assert result == {"data": "test_value", "number": 42}
    
    # Test cache miss
    print("Testing cache miss...")
    miss_result = await manager.get("nonexistent", CacheType.EMBEDDING)
    print(f"Cache miss result: {miss_result}")
    assert miss_result is None
    
    # Test expiration
    print("Testing TTL expiration...")
    await manager.set("expire_test", "temporary", CacheType.QUERY, ttl=0.1)
    immediate_result = await manager.get("expire_test", CacheType.QUERY)
    print(f"Immediate result: {immediate_result}")
    assert immediate_result == "temporary"
    
    await asyncio.sleep(0.2)
    expired_result = await manager.get("expire_test", CacheType.QUERY)
    print(f"Expired result: {expired_result}")
    assert expired_result is None
    
    # Test eviction
    print("Testing cache eviction...")
    for i in range(12):  # Exceed memory_max_size of 10
        await manager.set(f"evict_test_{i}", f"value_{i}", CacheType.EMBEDDING)
    
    # First items should be evicted
    first_result = await manager.get("evict_test_0", CacheType.EMBEDDING)
    last_result = await manager.get("evict_test_11", CacheType.EMBEDDING)
    print(f"First item (should be evicted): {first_result}")
    print(f"Last item (should exist): {last_result}")
    
    # Test statistics
    print("Testing cache statistics...")
    stats = manager.get_stats()
    print(f"Cache statistics: {stats}")
    
    print("All basic caching tests passed!")

if __name__ == "__main__":
    asyncio.run(test_basic_caching())

"""
Redis service for durable retry queue management.
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

# Use redis-py with asyncio support (more stable)
import redis.asyncio as aioredis
from redis.asyncio import Redis

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class RetryItem:
    """Retry item for Redis queue."""
    id: str
    example_id: str
    topic: str
    key: Optional[str]
    payload: str
    attempts: int = 0
    max_attempts: int = 5
    error_message: Optional[str] = None
    created_at: str = None
    last_attempt: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetryItem':
        """Create from dictionary."""
        return cls(**data)


class RedisRetryService:
    """Redis-based retry queue service."""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis_client = redis_client
        self.retry_queue_key = settings.RETRY_QUEUE_KEY
        self.processing_set_key = f"{self.retry_queue_key}:processing"
        self.max_attempts = settings.MAX_RETRY_ATTEMPTS
    
    async def initialize(self):
        """Initialize Redis connection if not provided."""
        if self.redis_client is None:
            try:
                self.redis_client = await aioredis.from_url(
                    settings.REDIS_URL,
                    password=settings.REDIS_PASSWORD or None,
                    db=settings.REDIS_DB,
                    encoding='utf-8',
                    decode_responses=True,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    health_check_interval=30
                )
                logger.info("Redis connection initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Redis connection: {e}")
                raise
    
    async def add_retry_item(
        self,
        example_id: str,
        topic: str,
        payload: str,
        key: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> str:
        """Add item to retry queue."""
        try:
            if not self.redis_client:
                await self.initialize()
            
            # Generate unique ID for retry item
            retry_id = f"{example_id}:{datetime.utcnow().timestamp()}"
            
            retry_item = RetryItem(
                id=retry_id,
                example_id=example_id,
                topic=topic,
                key=key,
                payload=payload,
                error_message=error_message,
                max_attempts=self.max_attempts
            )
            
            # Push to Redis list (FIFO queue)
            await self.redis_client.lpush(
                self.retry_queue_key,
                json.dumps(retry_item.to_dict())
            )
            
            logger.info(f"Added retry item {retry_id} to queue")
            return retry_id
            
        except Exception as e:
            logger.error(f"Failed to add retry item: {e}")
            raise
    
    async def get_retry_items(self, batch_size: int = 10) -> List[RetryItem]:
        """Get items from retry queue for processing."""
        try:
            if not self.redis_client:
                await self.initialize()
            
            retry_items = []
            
            # Use BLPOP to get items from queue (blocking pop)
            for _ in range(batch_size):
                # Non-blocking pop to get available items
                result = await self.redis_client.rpop(self.retry_queue_key)
                if not result:
                    break
                
                try:
                    item_data = json.loads(result)
                    retry_item = RetryItem.from_dict(item_data)
                    
                    # Check if item hasn't exceeded max attempts
                    if retry_item.attempts < retry_item.max_attempts:
                        # Add to processing set to track active processing
                        await self.redis_client.sadd(
                            self.processing_set_key,
                            retry_item.id
                        )
                        retry_items.append(retry_item)
                    else:
                        logger.warning(f"Retry item {retry_item.id} exceeded max attempts")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse retry item: {e}")
                    continue
            
            logger.debug(f"Retrieved {len(retry_items)} retry items")
            return retry_items
            
        except Exception as e:
            logger.error(f"Failed to get retry items: {e}")
            return []
    
    async def update_retry_attempt(
        self,
        retry_id: str,
        success: bool,
        error_message: Optional[str] = None
    ):
        """Update retry attempt status."""
        try:
            if not self.redis_client:
                await self.initialize()
            
            # Remove from processing set
            await self.redis_client.srem(self.processing_set_key, retry_id)
            
            if success:
                logger.info(f"Retry item {retry_id} processed successfully")
            else:
                # If failed, we need to put it back in queue with updated attempt count
                # This is a simplified approach - in production you might want to 
                # implement a more sophisticated retry strategy
                logger.warning(f"Retry item {retry_id} failed: {error_message}")
                
        except Exception as e:
            logger.error(f"Failed to update retry attempt: {e}")
    
    async def get_queue_size(self) -> int:
        """Get current queue size."""
        try:
            if not self.redis_client:
                await self.initialize()
            
            return await self.redis_client.llen(self.retry_queue_key)
            
        except Exception as e:
            logger.error(f"Failed to get queue size: {e}")
            return 0
    
    async def get_processing_count(self) -> int:
        """Get count of items currently being processed."""
        try:
            if not self.redis_client:
                await self.initialize()
            
            return await self.redis_client.scard(self.processing_set_key)
            
        except Exception as e:
            logger.error(f"Failed to get processing count: {e}")
            return 0
    
    async def clear_queue(self):
        """Clear all items from retry queue (for testing)."""
        try:
            if not self.redis_client:
                await self.initialize()
            
            await self.redis_client.delete(self.retry_queue_key)
            await self.redis_client.delete(self.processing_set_key)
            logger.info("Retry queue cleared")
            
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")

    # WebSocket connection tracking methods
    async def increment_websocket_count(self) -> int:
        """Increment WebSocket connection count."""
        try:
            if not self.redis_client:
                await self.initialize()
            
            count = await self.redis_client.incr("websocket:connection_count")
            logger.debug(f"WebSocket connection count incremented to {count}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to increment WebSocket count: {e}")
            return 0

    async def decrement_websocket_count(self) -> int:
        """Decrement WebSocket connection count."""
        try:
            if not self.redis_client:
                await self.initialize()
            
            count = await self.redis_client.decr("websocket:connection_count")
            # Ensure count doesn't go below 0
            if count < 0:
                await self.redis_client.set("websocket:connection_count", 0)
                count = 0
            logger.debug(f"WebSocket connection count decremented to {count}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to decrement WebSocket count: {e}")
            return 0

    async def get_websocket_count(self) -> int:
        """Get current WebSocket connection count."""
        try:
            if not self.redis_client:
                await self.initialize()
            
            count = await self.redis_client.get("websocket:connection_count")
            return int(count) if count else 0
            
        except Exception as e:
            logger.error(f"Failed to get WebSocket count: {e}")
            return 0

    async def publish_new_example_notification(self, example_data: Dict[str, Any]):
        """Publish new example notification for WebSocket broadcasting."""
        try:
            if not self.redis_client:
                await self.initialize()
            
            # Publish to Redis pub/sub channel for all instances to receive
            message = json.dumps({
                'type': 'new_example',
                'example': example_data,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            await self.redis_client.publish("websocket:new_example", message)
            logger.debug(f"Published new example notification for {example_data.get('event_id')}")
            
        except Exception as e:
            logger.error(f"Failed to publish new example notification: {e}")

    async def check_connectivity(self) -> bool:
        """Check Redis connectivity for health checks."""
        try:
            if not self.redis_client:
                await self.initialize()
            
            # Simple ping to check connectivity
            result = await self.redis_client.ping()
            return result == True
            
        except Exception as e:
            logger.error(f"Redis connectivity check failed: {e}")
            return False
        

# Global Redis retry service instance
redis_retry_service = RedisRetryService()

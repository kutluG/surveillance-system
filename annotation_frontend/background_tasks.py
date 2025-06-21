"""
Background tasks for the Annotation Frontend Service with Redis-based retry queue.
"""
import asyncio
import json
import logging
from typing import Optional
from datetime import datetime

from config import settings
from database import get_db_session
from services import RetryService
from redis_service import redis_retry_service, RetryItem
from kafka_pool import kafka_pool

logger = logging.getLogger(__name__)


class BackgroundRetryTask:
    """Background task to retry failed Kafka messages using Redis queue."""
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the retry task."""
        if self.running:
            logger.warning("Retry task is already running")
            return
        
        self.running = True
        logger.info("Starting Redis-based Kafka retry background task")
        
        # Initialize Redis service
        await redis_retry_service.initialize()
        
        # Start the background task
        self.task = asyncio.create_task(self._run_retry_loop())
    
    async def stop(self):
        """Stop the retry task."""
        self.running = False
        
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped Kafka retry background task")
    
    async def _run_retry_loop(self):
        """Main retry loop."""
        while self.running:
            try:
                await self._process_retry_queue()
                await asyncio.sleep(settings.RETRY_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                logger.info("Retry task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in retry task: {e}")
                await asyncio.sleep(10)  # Wait 10 seconds on error
    
    async def _process_retry_queue(self):
        """Process items in the Redis retry queue."""
        try:
            # Get batch of retry items from Redis
            retry_items = await redis_retry_service.get_retry_items(batch_size=10)
            
            if not retry_items:
                logger.debug("No items in retry queue")
                return
            
            logger.info(f"Processing {len(retry_items)} items from Redis retry queue")
            
            for item in retry_items:
                try:
                    # Update attempt count
                    item.attempts += 1
                    item.last_attempt = datetime.utcnow().isoformat()
                    
                    # Attempt to send the message using Kafka pool
                    success = await kafka_pool.send_message(
                        topic=item.topic,
                        message=item.payload,
                        key=item.key
                    )
                    
                    if success:
                        # Mark as successful
                        await redis_retry_service.update_retry_attempt(
                            item.id, success=True
                        )
                        logger.info(f"Successfully retried message for example: {item.example_id}")
                    else:
                        # Mark as failed and potentially re-queue if under max attempts
                        error_msg = "Failed to send message via Kafka pool"
                        await self._handle_retry_failure(item, error_msg)
                        
                except Exception as e:
                    # Handle individual item failure
                    error_msg = f"Exception during retry: {str(e)}"
                    await self._handle_retry_failure(item, error_msg)
                    logger.error(f"Failed to retry message for {item.example_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error processing retry queue: {e}")
    
    async def _handle_retry_failure(self, item: RetryItem, error_message: str):
        """Handle failure of a retry attempt."""
        try:
            if item.attempts < item.max_attempts:
                # Re-add to queue for another attempt
                await redis_retry_service.add_retry_item(
                    example_id=item.example_id,
                    topic=item.topic,
                    payload=item.payload,
                    key=item.key,
                    error_message=error_message
                )
                logger.warning(f"Re-queued retry item {item.id} (attempt {item.attempts}/{item.max_attempts})")
            else:
                # Max attempts reached, log and abandon
                await redis_retry_service.update_retry_attempt(
                    item.id, success=False, error_message=error_message
                )
                logger.error(f"Retry item {item.id} exceeded max attempts ({item.max_attempts})")
                
        except Exception as e:
            logger.error(f"Error handling retry failure: {e}")


# Global retry task instance
background_retry_task = BackgroundRetryTask()

"""
Kafka connection pooling service for high-throughput messaging.
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
    from aiokafka.errors import KafkaError
    AIOKAFKA_AVAILABLE = True
except ImportError:
    AIOKAFKA_AVAILABLE = False

# Always import confluent-kafka as fallback
from confluent_kafka import Producer, Consumer, KafkaError as ConfluentKafkaError

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class KafkaMessage:
    """Kafka message structure."""
    topic: str
    key: Optional[str]
    value: str
    headers: Optional[Dict[str, str]] = None


class KafkaConnectionPool:
    """Kafka connection pool for producers and consumers."""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.fallback_producer: Optional[Producer] = None
        self.fallback_consumer: Optional[Consumer] = None
        self._producer_lock = asyncio.Lock()
        self._consumer_lock = asyncio.Lock()
        self._initialized = False
        self.use_aiokafka = AIOKAFKA_AVAILABLE
    
    async def initialize(self):
        """Initialize Kafka connections."""
        try:
            if self.use_aiokafka:
                await self._initialize_aiokafka()
            else:
                self._initialize_confluent_kafka()
            
            self._initialized = True
            logger.info(f"Kafka connection pool initialized (using {'aiokafka' if self.use_aiokafka else 'confluent-kafka'})")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka connection pool: {e}")
            # Fall back to confluent-kafka if aiokafka fails
            if self.use_aiokafka:
                logger.info("Falling back to confluent-kafka")
                self.use_aiokafka = False
                self._initialize_confluent_kafka()
                self._initialized = True
            else:
                raise
    
    async def _initialize_aiokafka(self):
        """Initialize aiokafka connections."""        # Producer configuration for high throughput
        producer_config = {
            'bootstrap_servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'linger_ms': settings.KAFKA_LINGER_MS,
            'max_batch_size': settings.KAFKA_BATCH_SIZE * 1024,  # aiokafka uses max_batch_size
            'compression_type': settings.KAFKA_COMPRESSION_TYPE,
            'max_request_size': 1048576,  # 1MB
            'client_id': 'annotation-frontend-producer',
            'acks': 'all',  # Wait for all replicas
            'request_timeout_ms': 30000,
        }        # Consumer configuration for proper load balancing
        consumer_config = {
            'bootstrap_servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group_id': settings.KAFKA_GROUP_ID,
            'client_id': f'{settings.SERVICE_NAME}-consumer-{id(self)}',  # Unique client ID per instance
            'auto_offset_reset': 'latest',
            'enable_auto_commit': True,
            'auto_commit_interval_ms': 5000,
            'session_timeout_ms': 30000,
            'heartbeat_interval_ms': 10000,
            'max_poll_records': 100,
            'max_poll_interval_ms': 300000,  # 5 minutes
        }
        
        # Initialize producer
        self.producer = AIOKafkaProducer(**producer_config)
        await self.producer.start()
        
        # Initialize consumer
        self.consumer = AIOKafkaConsumer(
            settings.HARD_EXAMPLES_TOPIC,
            **consumer_config
        )
        await self.consumer.start()
    
    def _initialize_confluent_kafka(self):
        """Initialize confluent-kafka connections."""
        # Producer configuration
        producer_config = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'client.id': 'annotation-frontend-producer',
            'linger.ms': settings.KAFKA_LINGER_MS,
            'batch.size': settings.KAFKA_BATCH_SIZE * 1024,
            'compression.type': settings.KAFKA_COMPRESSION_TYPE,
            'acks': 'all',
            'retries': 3,
            'request.timeout.ms': 30000,
        }        # Consumer configuration for proper load balancing
        consumer_config = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': settings.KAFKA_GROUP_ID,
            'client.id': f'{settings.SERVICE_NAME}-consumer-{id(self)}',  # Unique client ID per instance
            'auto.offset.reset': 'latest',
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000,
            'session.timeout.ms': 30000,
            'heartbeat.interval.ms': 10000,
            'max.poll.interval.ms': 300000,  # 5 minutes
        }
        
        self.fallback_producer = Producer(producer_config)
        self.fallback_consumer = Consumer(consumer_config)
        self.fallback_consumer.subscribe([settings.HARD_EXAMPLES_TOPIC])
    
    async def send_message(
        self,
        topic: str,
        message: str,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Send message using connection pool."""
        if not self._initialized:
            await self.initialize()
        
        try:
            if self.use_aiokafka and self.producer:
                async with self._producer_lock:
                    await self.producer.send_and_wait(
                        topic,
                        value=message.encode('utf-8'),
                        key=key.encode('utf-8') if key else None,
                        headers=[(k, v.encode('utf-8')) for k, v in (headers or {}).items()]
                    )
                    logger.debug(f"Message sent to {topic} via aiokafka")
                    return True
            
            elif self.fallback_producer:
                def delivery_callback(err, msg):
                    if err:
                        logger.error(f"Message delivery failed: {err}")
                    else:
                        logger.debug(f"Message delivered to {msg.topic()}")
                
                self.fallback_producer.produce(
                    topic,
                    value=message.encode('utf-8'),
                    key=key.encode('utf-8') if key else None,
                    headers=headers,
                    callback=delivery_callback
                )
                self.fallback_producer.flush(timeout=10)
                logger.debug(f"Message sent to {topic} via confluent-kafka")
                return True
            
            else:
                raise RuntimeError("No Kafka producer available")
                
        except Exception as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            return False
    
    async def consume_messages(
        self,
        callback: Callable[[str, str, Optional[str]], None],
        timeout_ms: int = 1000
    ):
        """Consume messages using connection pool."""
        if not self._initialized:
            await self.initialize()
        
        try:
            if self.use_aiokafka and self.consumer:
                async with self._consumer_lock:
                    # Get batch of messages
                    msg_pack = await self.consumer.getmany(
                        timeout_ms=timeout_ms,
                        max_records=10
                    )
                    
                    for topic_partition, messages in msg_pack.items():
                        for message in messages:
                            try:
                                value = message.value.decode('utf-8')
                                key = message.key.decode('utf-8') if message.key else None
                                await callback(message.topic, value, key)
                            except Exception as e:
                                logger.error(f"Error processing message: {e}")
            
            elif self.fallback_consumer:
                # Poll for messages
                msg = self.fallback_consumer.poll(timeout=timeout_ms / 1000.0)
                if msg is None:
                    return
                
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    return
                
                try:
                    value = msg.value().decode('utf-8')
                    key = msg.key().decode('utf-8') if msg.key() else None
                    await callback(msg.topic(), value, key)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
            
            else:
                raise RuntimeError("No Kafka consumer available")
                
        except Exception as e:
            logger.error(f"Failed to consume messages: {e}")
    
    async def get_producer_metrics(self) -> Dict[str, Any]:
        """Get producer metrics."""
        metrics = {}
        
        try:
            if self.use_aiokafka and self.producer:
                # aiokafka doesn't expose detailed metrics easily
                metrics['type'] = 'aiokafka'
                metrics['client_id'] = 'annotation-frontend-producer'
            elif self.fallback_producer:
                metrics['type'] = 'confluent-kafka'
                # In production, you might want to add more detailed metrics
                metrics['client_id'] = 'annotation-frontend-producer'
                
        except Exception as e:
            logger.error(f"Failed to get producer metrics: {e}")
        
        return metrics

    async def check_consumer_health(self) -> Dict[str, Any]:
        """Check consumer health and assignment status."""
        health_info = {
            'initialized': self._initialized,
            'using_aiokafka': self.use_aiokafka,
            'consumer_assigned': False,
            'assigned_partitions': [],
            'consumer_ready': False
        }        
        try:
            if self.use_aiokafka and self.consumer:
                # Check if consumer is assigned to partitions
                assignment = self.consumer.assignment()
                health_info['consumer_assigned'] = len(assignment) > 0
                health_info['assigned_partitions'] = [
                    f"{tp.topic}-{tp.partition}" for tp in assignment
                ]
                health_info['consumer_ready'] = True
                health_info['client_id'] = f'{settings.SERVICE_NAME}-consumer-{id(self)}'
                health_info['group_id'] = settings.KAFKA_GROUP_ID
                
            elif self.fallback_consumer:
                # For confluent-kafka, check subscription
                assignment = self.fallback_consumer.assignment()
                health_info['consumer_assigned'] = len(assignment) > 0
                health_info['assigned_partitions'] = [
                    f"{tp.topic}-{tp.partition}" for tp in assignment
                ]
                health_info['consumer_ready'] = True
                
        except Exception as e:
            health_info['error'] = str(e)
            logger.error(f"Error checking consumer health: {e}")
        
        return health_info

    async def get_consumer_metrics(self) -> Dict[str, Any]:
        """Get consumer metrics."""
        metrics = {}
          
        try:
            if self.use_aiokafka and self.consumer:
                # aiokafka metrics
                metrics['type'] = 'aiokafka'
                metrics['client_id'] = f'{settings.SERVICE_NAME}-consumer-{id(self)}'
                metrics['assignment'] = [
                    f"{tp.topic}-{tp.partition}" for tp in self.consumer.assignment()
                ]
                metrics['group_id'] = settings.KAFKA_GROUP_ID
            elif self.fallback_consumer:
                metrics['type'] = 'confluent-kafka'
                metrics['client_id'] = f'{settings.SERVICE_NAME}-consumer-{id(self)}'
                assignment = self.fallback_consumer.assignment()
                metrics['assignment'] = [
                    f"{tp.topic}-{tp.partition}" for tp in assignment
                ]
                metrics['group_id'] = settings.KAFKA_GROUP_ID
                
        except Exception as e:
            logger.error(f"Failed to get consumer metrics: {e}")
            metrics['error'] = str(e)
        
        return metrics

    async def close(self):
        """Close all connections."""
        try:
            if self.producer:
                await self.producer.stop()
                logger.info("AIOKafka producer stopped")
            
            if self.consumer:
                await self.consumer.stop()
                logger.info("AIOKafka consumer stopped")
            
            if self.fallback_producer:
                self.fallback_producer.flush(timeout=10)
                logger.info("Confluent-kafka producer flushed")
            
            if self.fallback_consumer:
                self.fallback_consumer.close()
                logger.info("Confluent-kafka consumer closed")
                
        except Exception as e:
            logger.error(f"Error closing Kafka connections: {e}")


# Global Kafka connection pool instance
kafka_pool = KafkaConnectionPool()

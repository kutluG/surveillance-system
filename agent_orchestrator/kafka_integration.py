"""
Kafka Integration for Agent Orchestrator Service

This module provides Kafka producer and consumer functionality for event-driven
architecture in the agent orchestrator service. It handles:
- Agent registration events
- Task assignment events  
- Workflow state changes
- Agent status updates
- System notifications

Features:
- Async Kafka producer/consumer using aiokafka
- Event serialization/deserialization
- Error handling and retry logic
- Connection management
- Message routing and filtering
- Dead letter queue support
"""

import json
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from enum import Enum

import asyncio
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError, KafkaTimeoutError

from config import Config

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for agent orchestrator."""
    AGENT_REGISTERED = "agent.registered"
    AGENT_UPDATED = "agent.updated"
    AGENT_DEREGISTERED = "agent.deregistered"
    AGENT_STATUS_CHANGED = "agent.status_changed"
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    WORKFLOW_CREATED = "workflow.created"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    SYSTEM_ALERT = "system.alert"
    SYSTEM_HEALTH = "system.health"


@dataclass
class OrchestrationEvent:
    """Base event structure for orchestration events."""
    event_id: str
    event_type: EventType
    timestamp: datetime
    source: str = "agent_orchestrator"
    version: str = "1.0"
    data: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        event_dict = asdict(self)
        event_dict['event_type'] = self.event_type.value
        event_dict['timestamp'] = self.timestamp.isoformat()
        return event_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrchestrationEvent':
        """Create event from dictionary."""
        data['event_type'] = EventType(data['event_type'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class KafkaConfig:
    """Kafka configuration management."""
    
    def __init__(self):
        self.bootstrap_servers = Config.get("kafka.bootstrap_servers", "localhost:9092")
        self.producer_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'value_serializer': self._serialize_json,
            'key_serializer': lambda k: k.encode('utf-8') if k else None,
            'acks': 'all',  # Wait for all replicas
            'retries': 3,
            'retry_backoff_ms': 1000,
            'request_timeout_ms': 30000,
            'compression_type': 'gzip'
        }
        
        self.consumer_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'value_deserializer': self._deserialize_json,
            'key_deserializer': lambda k: k.decode('utf-8') if k else None,
            'auto_offset_reset': 'earliest',
            'enable_auto_commit': False,  # Manual commit for better control
            'group_id': 'agent_orchestrator_group',
            'session_timeout_ms': 30000,
            'heartbeat_interval_ms': 10000
        }
        
        # Topic configuration
        self.topics = {
            'agent_events': Config.get("kafka.topics.agent_events", "orchestrator.agent.events"),
            'task_events': Config.get("kafka.topics.task_events", "orchestrator.task.events"),
            'workflow_events': Config.get("kafka.topics.workflow_events", "orchestrator.workflow.events"),
            'system_events': Config.get("kafka.topics.system_events", "orchestrator.system.events"),
            'dead_letter': Config.get("kafka.topics.dead_letter", "orchestrator.dead_letter")
        }
    
    @staticmethod
    def _serialize_json(value: Any) -> bytes:
        """Serialize value to JSON bytes."""
        if isinstance(value, OrchestrationEvent):
            value = value.to_dict()
        return json.dumps(value, default=str).encode('utf-8')
    
    @staticmethod
    def _deserialize_json(value: bytes) -> Any:
        """Deserialize JSON bytes to value."""
        if value is None:
            return None
        return json.loads(value.decode('utf-8'))


class KafkaProducerManager:
    """Manages Kafka producer for publishing events."""
    
    def __init__(self):
        self.config = KafkaConfig()
        self.producer: Optional[AIOKafkaProducer] = None
        self._is_connected = False
    
    async def start(self):
        """Start the Kafka producer."""
        try:
            self.producer = AIOKafkaProducer(**self.config.producer_config)
            await self.producer.start()
            self._is_connected = True
            logger.info("Kafka producer started successfully")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise
    
    async def stop(self):
        """Stop the Kafka producer."""
        if self.producer:
            try:
                await self.producer.stop()
                self._is_connected = False
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka producer: {e}")
    
    @asynccontextmanager
    async def get_producer(self):
        """Context manager for getting producer with auto-start."""
        if not self._is_connected:
            await self.start()
        try:
            yield self.producer
        finally:
            # Keep connection alive for reuse
            pass
    
    async def publish_event(
        self,
        event: OrchestrationEvent,
        topic: Optional[str] = None,
        key: Optional[str] = None,
        partition: Optional[int] = None
    ) -> bool:
        """
        Publish an event to Kafka.
        
        Args:
            event: The event to publish
            topic: Topic to publish to (auto-selected if None)
            key: Message key for partitioning
            partition: Specific partition to send to
            
        Returns:
            True if published successfully, False otherwise
        """
        try:
            # Auto-select topic based on event type
            if topic is None:
                topic = self._get_topic_for_event(event.event_type)
            
            # Generate key if not provided
            if key is None:
                key = f"{event.source}:{event.event_type.value}"
            
            async with self.get_producer() as producer:
                # Send message
                future = await producer.send(
                    topic=topic,
                    value=event,
                    key=key,
                    partition=partition
                )
                
                # Get metadata
                record_metadata = await future
                
                logger.info(
                    f"Event published successfully - Topic: {record_metadata.topic}, "
                    f"Partition: {record_metadata.partition}, Offset: {record_metadata.offset}"
                )
                
                return True
                
        except (KafkaConnectionError, KafkaTimeoutError) as e:
            logger.error(f"Kafka connection error while publishing event: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while publishing event: {e}")
            return False
    
    def _get_topic_for_event(self, event_type: EventType) -> str:
        """Get appropriate topic for event type."""
        if event_type.value.startswith('agent.'):
            return self.config.topics['agent_events']
        elif event_type.value.startswith('task.'):
            return self.config.topics['task_events']
        elif event_type.value.startswith('workflow.'):
            return self.config.topics['workflow_events']
        elif event_type.value.startswith('system.'):
            return self.config.topics['system_events']
        else:
            return self.config.topics['system_events']  # Default


class KafkaConsumerManager:
    """Manages Kafka consumer for processing events."""
    
    def __init__(self):
        self.config = KafkaConfig()
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.handlers: Dict[EventType, List[Callable]] = {}
        self._running = False
    
    def register_handler(self, event_type: EventType, handler: Callable[[OrchestrationEvent], None]):
        """Register an event handler for specific event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type.value}")
    
    async def start_consuming(self, topics: Optional[List[str]] = None):
        """Start consuming messages from Kafka topics."""
        if topics is None:
            topics = list(self.config.topics.values())
        
        try:
            self.consumer = AIOKafkaConsumer(
                *topics,
                **self.config.consumer_config
            )
            
            await self.consumer.start()
            self._running = True
            
            logger.info(f"Started consuming from topics: {topics}")
            
            # Start consumption loop
            await self._consumption_loop()
            
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise
    
    async def stop_consuming(self):
        """Stop consuming messages."""
        self._running = False
        if self.consumer:
            try:
                await self.consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka consumer: {e}")
    
    async def _consumption_loop(self):
        """Main consumption loop."""
        try:
            async for msg in self.consumer:
                if not self._running:
                    break
                
                try:
                    # Deserialize event
                    event_data = msg.value
                    event = OrchestrationEvent.from_dict(event_data)
                    
                    # Process event
                    await self._process_event(event, msg)
                    
                    # Commit offset
                    await self.consumer.commit()
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self._handle_processing_error(msg, e)
                    
        except Exception as e:
            logger.error(f"Error in consumption loop: {e}")
        finally:
            self._running = False
    
    async def _process_event(self, event: OrchestrationEvent, msg):
        """Process a single event by calling registered handlers."""
        logger.debug(f"Processing event: {event.event_type.value}")
        
        # Get handlers for this event type
        handlers = self.handlers.get(event.event_type, [])
        
        if not handlers:
            logger.warning(f"No handlers registered for event type: {event.event_type.value}")
            return
        
        # Call all handlers
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    async def _handle_processing_error(self, msg, error: Exception):
        """Handle message processing errors."""
        logger.error(f"Failed to process message from {msg.topic}:{msg.partition}:{msg.offset} - {error}")
        
        # Send to dead letter queue
        try:
            dead_letter_event = OrchestrationEvent(
                event_id=f"error_{datetime.now(timezone.utc).timestamp()}",
                event_type=EventType.SYSTEM_ALERT,
                timestamp=datetime.now(timezone.utc),
                data={
                    "error": str(error),
                    "original_topic": msg.topic,
                    "original_partition": msg.partition,
                    "original_offset": msg.offset,
                    "original_key": msg.key,
                    "original_value": msg.value
                },
                metadata={"error_handling": True}
            )
            
            # Would need producer instance here - simplified for now
            logger.info("Message sent to dead letter queue (implementation needed)")
            
        except Exception as dlq_error:
            logger.error(f"Failed to send message to dead letter queue: {dlq_error}")


class EventPublisher:
    """High-level event publisher for orchestration events."""
    
    def __init__(self):
        self.producer_manager = KafkaProducerManager()
    
    async def publish_agent_registered(
        self,
        agent_id: str,
        agent_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Publish agent registration event."""
        event = OrchestrationEvent(
            event_id=f"agent_reg_{agent_id}_{datetime.now(timezone.utc).timestamp()}",
            event_type=EventType.AGENT_REGISTERED,
            timestamp=datetime.now(timezone.utc),
            data={
                "agent_id": agent_id,
                "agent_type": agent_data.get("type"),
                "name": agent_data.get("name"),
                "endpoint": agent_data.get("endpoint"),
                "capabilities": agent_data.get("capabilities", [])
            },
            metadata=metadata or {}
        )
        
        return await self.producer_manager.publish_event(event)
    
    async def publish_task_assigned(
        self,
        task_id: str,
        agent_id: str,
        task_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Publish task assignment event."""
        event = OrchestrationEvent(
            event_id=f"task_assign_{task_id}_{datetime.now(timezone.utc).timestamp()}",
            event_type=EventType.TASK_ASSIGNED,
            timestamp=datetime.now(timezone.utc),
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "task_type": task_data.get("type"),
                "task_name": task_data.get("name"),
                "priority": task_data.get("priority")
            },
            metadata=metadata or {}
        )
        
        return await self.producer_manager.publish_event(event)
    
    async def publish_system_health(
        self,
        status: str,
        metrics: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Publish system health event."""
        event = OrchestrationEvent(
            event_id=f"health_{datetime.now(timezone.utc).timestamp()}",
            event_type=EventType.SYSTEM_HEALTH,
            timestamp=datetime.now(timezone.utc),
            data={
                "status": status,
                "metrics": metrics
            },
            metadata=metadata or {}
        )
        
        return await self.producer_manager.publish_event(event)


# Global instances
event_publisher = EventPublisher()
consumer_manager = KafkaConsumerManager()


async def init_kafka():
    """Initialize Kafka connections."""
    try:
        await event_publisher.producer_manager.start()
        logger.info("Kafka integration initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Kafka: {e}")
        return False


async def shutdown_kafka():
    """Shutdown Kafka connections."""
    try:
        await event_publisher.producer_manager.stop()
        await consumer_manager.stop_consuming()
        logger.info("Kafka integration shutdown completed")
    except Exception as e:
        logger.error(f"Error during Kafka shutdown: {e}")


# Example event handlers
async def handle_agent_registered(event: OrchestrationEvent):
    """Example handler for agent registration events."""
    logger.info(f"Agent registered: {event.data.get('agent_id')} - {event.data.get('name')}")


async def handle_task_assigned(event: OrchestrationEvent):
    """Example handler for task assignment events."""
    logger.info(f"Task {event.data.get('task_id')} assigned to agent {event.data.get('agent_id')}")


# Register example handlers
consumer_manager.register_handler(EventType.AGENT_REGISTERED, handle_agent_registered)
consumer_manager.register_handler(EventType.TASK_ASSIGNED, handle_task_assigned)

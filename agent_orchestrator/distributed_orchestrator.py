"""
Distributed Orchestrator Module for Agent Orchestrator Service

This module implements a horizontally scalable orchestrator with:
- State synchronization using Redis
- Leader election for coordinated actions  
- Shard-based orchestration by capability domain
- Event-driven architecture using Kafka
- Distributed task assignment with locking
- Cross-instance coordination and communication

Features:
- Distributed state management with Redis/etcd
- Leader election for singleton operations
- Shard-based agent partitioning
- Event-driven coordination via Kafka
- Distributed locking for critical sections
- Cross-instance health monitoring
- Automatic failover and recovery
"""

import asyncio
import json
import logging
import time
import uuid
import hashlib
import itertools
import random
import copy
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from abc import ABC, abstractmethod

import httpx
import redis.asyncio as redis
from confluent_kafka import Producer, Consumer, KafkaError
from tenacity import retry, stop_after_attempt, wait_exponential
from fastapi import HTTPException
from pydantic import BaseModel, Field

# Import existing components
from config import get_config
from metrics import metrics_collector, monitor_orchestration_performance
from enhanced_circuit_breaker import (
    EnhancedCircuitBreakerManager,
    ServiceConfig, 
    ServiceType,
    get_enhanced_circuit_breaker_manager
)

# Configure logging
logger = logging.getLogger(__name__)
config = get_config()

class CapabilityDomain(str, Enum):
    """Agent capability domains for sharding"""
    RAG_ANALYSIS = "rag_analysis"
    RULE_GENERATION = "rule_generation"
    NOTIFICATION = "notification"
    VMS_INTEGRATION = "vms_integration"
    SECURITY_MONITORING = "security_monitoring"
    DATA_PROCESSING = "data_processing"

class TaskPriority(str, Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

class OrchestratorRole(str, Enum):
    """Orchestrator instance roles"""
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"

@dataclass
class OrchestratorInstance:
    """Orchestrator instance metadata"""
    instance_id: str
    hostname: str
    port: int
    role: OrchestratorRole
    capabilities: List[CapabilityDomain]
    last_heartbeat: datetime
    load_score: float = 0.0
    active_tasks: int = 0

@dataclass
class DistributedTask:
    """Distributed task definition"""
    task_id: str
    task_type: str
    capability_domain: CapabilityDomain
    priority: TaskPriority
    payload: Dict[str, Any]
    created_at: datetime
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    status: str = "pending"
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300

@dataclass
class AgentInfo:
    """Agent information for distributed assignment"""
    agent_id: str
    capability_domain: CapabilityDomain
    instance_id: str
    endpoint: str
    load_score: float
    last_seen: datetime
    status: str = "active"

class DistributedState:
    """Shared state management via Redis"""
    
    def __init__(self, redis_client: redis.Redis, namespace: str = "orchestrator"):
        self.redis = redis_client
        self.namespace = namespace
        
    def _key(self, suffix: str) -> str:
        """Generate namespaced Redis key"""
        return f"{self.namespace}:{suffix}"
    
    async def set_instance_info(self, instance: OrchestratorInstance):
        """Store orchestrator instance information"""
        key = self._key(f"instances:{instance.instance_id}")
        data = asdict(instance)
        data['last_heartbeat'] = instance.last_heartbeat.isoformat()
        await self.redis.hset(key, mapping=data)
        await self.redis.expire(key, 60)  # 60 second TTL
    
    async def get_all_instances(self) -> List[OrchestratorInstance]:
        """Get all active orchestrator instances"""
        pattern = self._key("instances:*")
        keys = await self.redis.keys(pattern)
        instances = []
        
        for key in keys:
            data = await self.redis.hgetall(key)
            if data:
                data['last_heartbeat'] = datetime.fromisoformat(data['last_heartbeat'])
                data['capabilities'] = json.loads(data['capabilities'])
                data['load_score'] = float(data['load_score'])
                data['active_tasks'] = int(data['active_tasks'])
                instances.append(OrchestratorInstance(**data))
                
        return instances
    
    async def set_task(self, task: DistributedTask):
        """Store distributed task"""
        key = self._key(f"tasks:{task.task_id}")
        data = asdict(task)
        data['created_at'] = task.created_at.isoformat()
        if task.assigned_at:
            data['assigned_at'] = task.assigned_at.isoformat()
        data['payload'] = json.dumps(task.payload)
        await self.redis.hset(key, mapping=data)
    
    async def get_task(self, task_id: str) -> Optional[DistributedTask]:
        """Get distributed task by ID"""
        key = self._key(f"tasks:{task_id}")
        data = await self.redis.hgetall(key)
        if not data:
            return None
            
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('assigned_at'):
            data['assigned_at'] = datetime.fromisoformat(data['assigned_at'])
        data['payload'] = json.loads(data['payload'])
        data['retry_count'] = int(data['retry_count'])
        data['max_retries'] = int(data['max_retries'])
        data['timeout_seconds'] = int(data['timeout_seconds'])
        
        return DistributedTask(**data)
    
    async def set_agent_info(self, agent: AgentInfo):
        """Store agent information"""
        key = self._key(f"agents:{agent.agent_id}")
        data = asdict(agent)
        data['last_seen'] = agent.last_seen.isoformat()
        data['load_score'] = str(agent.load_score)
        await self.redis.hset(key, mapping=data)
        await self.redis.expire(key, 120)  # 2 minute TTL
    
    async def get_agents_by_capability(self, capability: CapabilityDomain) -> List[AgentInfo]:
        """Get agents by capability domain"""
        pattern = self._key("agents:*")
        keys = await self.redis.keys(pattern)
        agents = []
        
        for key in keys:
            data = await self.redis.hgetall(key)
            if data and data.get('capability_domain') == capability.value:
                data['last_seen'] = datetime.fromisoformat(data['last_seen'])
                data['load_score'] = float(data['load_score'])
                agents.append(AgentInfo(**data))
                
        return agents

class LeaderElection:
    """Leader election implementation using Redis"""
    
    def __init__(self, redis_client: redis.Redis, instance_id: str, namespace: str = "orchestrator"):
        self.redis = redis_client
        self.instance_id = instance_id
        self.namespace = namespace
        self.leader_key = f"{namespace}:leader"
        self.leader_ttl = 30  # 30 seconds
        self.is_leader = False
        self._election_task: Optional[asyncio.Task] = None
    
    async def start_election(self):
        """Start leader election process"""
        self._election_task = asyncio.create_task(self._election_loop())
        logger.info(f"Started leader election for instance {self.instance_id}")
    
    async def stop_election(self):
        """Stop leader election process"""
        if self._election_task:
            self._election_task.cancel()
            try:
                await self._election_task
            except asyncio.CancelledError:
                pass
        
        # Release leadership if we're the leader
        if self.is_leader:
            await self._release_leadership()
    
    async def _election_loop(self):
        """Main election loop"""
        while True:
            try:
                await self._attempt_leadership()
                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in leader election: {e}")
                await asyncio.sleep(5)
    
    async def _attempt_leadership(self):
        """Attempt to become or maintain leadership"""
        # Try to set leader key with NX (only if not exists) and EX (expiration)
        result = await self.redis.set(
            self.leader_key, 
            self.instance_id, 
            nx=True, 
            ex=self.leader_ttl
        )
        
        if result:
            # We became the leader
            if not self.is_leader:
                self.is_leader = True
                logger.info(f"Instance {self.instance_id} became leader")
                await self._on_become_leader()
        else:
            # Check if we're still the current leader
            current_leader = await self.redis.get(self.leader_key)
            if current_leader == self.instance_id:
                # We're still the leader, extend TTL
                await self.redis.expire(self.leader_key, self.leader_ttl)
            else:
                # We lost leadership
                if self.is_leader:
                    self.is_leader = False
                    logger.info(f"Instance {self.instance_id} lost leadership to {current_leader}")
                    await self._on_lose_leadership()
    
    async def _release_leadership(self):
        """Release leadership voluntarily"""
        current_leader = await self.redis.get(self.leader_key)
        if current_leader == self.instance_id:
            await self.redis.delete(self.leader_key)
            self.is_leader = False
            logger.info(f"Instance {self.instance_id} released leadership")
    
    async def _on_become_leader(self):
        """Called when instance becomes leader"""
        # Implement leader-specific initialization here
        pass
    
    async def _on_lose_leadership(self):
        """Called when instance loses leadership"""
        # Implement cleanup when losing leadership
        pass
    
    async def get_current_leader(self) -> Optional[str]:
        """Get current leader instance ID"""
        return await self.redis.get(self.leader_key)

class EventDrivenCoordinator:
    """Kafka-based event coordination between orchestrator instances"""
    
    def __init__(self, kafka_config: Dict[str, Any], instance_id: str):
        self.instance_id = instance_id
        self.kafka_config = kafka_config
        self.producer: Optional[Producer] = None
        self.consumer: Optional[Consumer] = None
        self._consumer_task: Optional[asyncio.Task] = None
        
        # Event topics
        self.coordination_topic = "orchestrator.coordination"
        self.task_events_topic = "orchestrator.task_events"
        
    async def initialize(self):
        """Initialize Kafka producer and consumer"""
        # Producer configuration
        producer_config = {
            **self.kafka_config,
            'client.id': f'orchestrator-producer-{self.instance_id}'
        }
        self.producer = Producer(producer_config)
        
        # Consumer configuration
        consumer_config = {
            **self.kafka_config,
            'group.id': 'orchestrator-coordination',
            'client.id': f'orchestrator-consumer-{self.instance_id}',
            'auto.offset.reset': 'latest',
            'enable.auto.commit': True
        }
        self.consumer = Consumer(consumer_config)
        
        # Subscribe to coordination topics
        self.consumer.subscribe([self.coordination_topic, self.task_events_topic])
        
        # Start consumer task
        self._consumer_task = asyncio.create_task(self._consume_events())
        
        logger.info(f"Event coordinator initialized for instance {self.instance_id}")
    
    async def shutdown(self):
        """Shutdown event coordinator"""
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        
        if self.consumer:
            self.consumer.close()
        
        if self.producer:
            self.producer.flush()
    
    async def publish_coordination_event(self, event_type: str, data: Dict[str, Any]):
        """Publish coordination event to other instances"""
        event = {
            'event_type': event_type,
            'instance_id': self.instance_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        self.producer.produce(
            topic=self.coordination_topic,
            key=self.instance_id,
            value=json.dumps(event)
        )
        self.producer.flush()
    
    async def publish_task_event(self, task_id: str, event_type: str, data: Dict[str, Any]):
        """Publish task-related event"""
        event = {
            'task_id': task_id,
            'event_type': event_type,
            'instance_id': self.instance_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        self.producer.produce(
            topic=self.task_events_topic,
            key=task_id,
            value=json.dumps(event)
        )
        self.producer.flush()
    
    async def _consume_events(self):
        """Consume coordination events from Kafka"""
        while True:
            try:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                    
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Kafka consumer error: {msg.error()}")
                    continue
                
                # Parse event
                try:
                    event = json.loads(msg.value().decode('utf-8'))
                    await self._handle_coordination_event(event)
                except Exception as e:
                    logger.error(f"Error processing coordination event: {e}")
                    
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in event consumer: {e}")
                await asyncio.sleep(1)
    
    async def _handle_coordination_event(self, event: Dict[str, Any]):
        """Handle incoming coordination event"""
        event_type = event.get('event_type')
        source_instance = event.get('instance_id')
        
        # Don't process our own events
        if source_instance == self.instance_id:
            return
        
        logger.debug(f"Received coordination event: {event_type} from {source_instance}")
        
        # Handle different event types
        if event_type == 'instance_started':
            await self._handle_instance_started(event)
        elif event_type == 'instance_stopped':
            await self._handle_instance_stopped(event)
        elif event_type == 'task_assigned':
            await self._handle_task_assigned(event)
        elif event_type == 'agent_registered':
            await self._handle_agent_registered(event)
    
    async def _handle_instance_started(self, event: Dict[str, Any]):
        """Handle instance started event"""
        instance_id = event.get('instance_id')
        logger.info(f"New orchestrator instance started: {instance_id}")
    
    async def _handle_instance_stopped(self, event: Dict[str, Any]):
        """Handle instance stopped event"""
        instance_id = event.get('instance_id')
        logger.info(f"Orchestrator instance stopped: {instance_id}")
    
    async def _handle_task_assigned(self, event: Dict[str, Any]):
        """Handle task assignment event"""
        task_id = event.get('data', {}).get('task_id')
        agent_id = event.get('data', {}).get('agent_id')
        logger.debug(f"Task {task_id} assigned to agent {agent_id}")
    
    async def _handle_agent_registered(self, event: Dict[str, Any]):
        """Handle agent registration event"""
        agent_id = event.get('data', {}).get('agent_id')
        capability = event.get('data', {}).get('capability')
        logger.info(f"New agent registered: {agent_id} with capability {capability}")

class DistributedOrchestrator:
    """Main distributed orchestrator with horizontal scalability"""
    
    def __init__(self, instance_id: Optional[str] = None):
        self.instance_id = instance_id or str(uuid.uuid4())
        self.hostname = "localhost"  # Should be set to actual hostname
        self.port = 8000
        
        # Core components
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.distributed_state: Optional[DistributedState] = None
        self.leader_election: Optional[LeaderElection] = None
        self.event_coordinator: Optional[EventDrivenCoordinator] = None
        self.circuit_breaker_manager: Optional[EnhancedCircuitBreakerManager] = None
        self.ml_workflow_manager: Optional["MLWorkflowManager"] = None  # Forward reference
        
        # Instance state
        self.role = OrchestratorRole.FOLLOWER
        self.capabilities = [
            CapabilityDomain.RAG_ANALYSIS,
            CapabilityDomain.RULE_GENERATION,
            CapabilityDomain.NOTIFICATION,
            CapabilityDomain.VMS_INTEGRATION
        ]
        
        # Task management
        self.active_tasks: Dict[str, DistributedTask] = {}
        self.registered_agents: Dict[str, AgentInfo] = {}
        
        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize all distributed orchestrator components"""
        try:
            # Initialize Redis client
            self.redis_client = redis.from_url(config.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
            
            # Initialize HTTP client
            self.http_client = httpx.AsyncClient(timeout=config.http_timeout)
            
            # Initialize distributed state management
            self.distributed_state = DistributedState(self.redis_client)
            
            # Initialize ML workflow manager
            self.ml_workflow_manager = MLWorkflowManager(self)
            
            # Initialize leader election
            self.leader_election = LeaderElection(self.redis_client, self.instance_id)
            await self.leader_election.start_election()
            
            # Initialize event coordinator
            kafka_config = {
                'bootstrap.servers': config.kafka_bootstrap_servers,
            }
            self.event_coordinator = EventDrivenCoordinator(kafka_config, self.instance_id)
            await self.event_coordinator.initialize()
            
            # Initialize circuit breaker manager
            self.circuit_breaker_manager = get_enhanced_circuit_breaker_manager(self.redis_client)
            await self._initialize_circuit_breakers()
            
            # Start background tasks
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            # Announce instance startup
            await self.event_coordinator.publish_coordination_event(
                'instance_started', 
                {'capabilities': [c.value for c in self.capabilities]}
            )
            
            logger.info(f"Distributed orchestrator {self.instance_id} initialized successfully with ML workflow capabilities")
            
        except Exception as e:
            logger.error(f"Failed to initialize distributed orchestrator: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown distributed orchestrator"""
        try:
            # Announce shutdown
            if self.event_coordinator:
                await self.event_coordinator.publish_coordination_event(
                    'instance_stopped', 
                    {}
                )
            
            # Cancel background tasks
            for task in [self._heartbeat_task, self._cleanup_task]:
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Shutdown components
            if self.leader_election:
                await self.leader_election.stop_election()
            
            if self.event_coordinator:
                await self.event_coordinator.shutdown()
            
            if self.http_client:
                await self.http_client.aclose()
            
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info(f"Distributed orchestrator {self.instance_id} shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def _initialize_circuit_breakers(self):
        """Initialize circuit breakers for all services"""
        services = [
            ServiceConfig(
                name="rag_service",
                service_type=ServiceType.RAG_SERVICE,
                fail_max=5,
                recovery_timeout=60,
                timeout=30.0,
                fallback_enabled=True,
                priority=1
            ),
            ServiceConfig(
                name="rulegen_service",
                service_type=ServiceType.RULEGEN_SERVICE,
                fail_max=3,
                recovery_timeout=45,
                timeout=20.0,
                fallback_enabled=True,
                priority=2
            )
        ]
        
        for service_config in services:
            self.circuit_breaker_manager.register_service(service_config)
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to maintain instance presence"""
        while True:
            try:
                instance_info = OrchestratorInstance(
                    instance_id=self.instance_id,
                    hostname=self.hostname,
                    port=self.port,
                    role=OrchestratorRole.LEADER if self.leader_election.is_leader else OrchestratorRole.FOLLOWER,
                    capabilities=self.capabilities,
                    last_heartbeat=datetime.utcnow(),
                    load_score=self._calculate_load_score(),
                    active_tasks=len(self.active_tasks)
                )
                
                await self.distributed_state.set_instance_info(instance_info)
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_loop(self):
        """Periodic cleanup of expired tasks and dead instances"""
        while True:
            try:
                if self.leader_election.is_leader:
                    await self._cleanup_expired_tasks()
                    await self._cleanup_dead_instances()
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(10)
    
    def _calculate_load_score(self) -> float:
        """Calculate current load score for this instance"""
        # Simple load calculation based on active tasks
        # In production, this could include CPU, memory, etc.
        base_score = len(self.active_tasks) * 0.1
        return min(base_score, 1.0)
    
    async def _cleanup_expired_tasks(self):
        """Cleanup expired tasks (leader only)"""
        # Implementation for cleaning up expired/failed tasks
        pattern = f"orchestrator:tasks:*"
        keys = await self.redis_client.keys(pattern)
        
        for key in keys:
            task_data = await self.redis_client.hgetall(key)
            if task_data:
                created_at = datetime.fromisoformat(task_data['created_at'])
                timeout = int(task_data.get('timeout_seconds', 300))
                
                if datetime.utcnow() - created_at > timedelta(seconds=timeout):
                    logger.warning(f"Cleaning up expired task: {task_data['task_id']}")
                    await self.redis_client.delete(key)
    
    async def _cleanup_dead_instances(self):
        """Cleanup dead instance registrations (leader only)"""
        instances = await self.distributed_state.get_all_instances()
        current_time = datetime.utcnow()
        
        for instance in instances:
            if current_time - instance.last_heartbeat > timedelta(minutes=2):
                logger.warning(f"Cleaning up dead instance: {instance.instance_id}")
                await self.redis_client.delete(f"orchestrator:instances:{instance.instance_id}")

class SimpleRedisLock:
    """Simple Redis-based distributed lock implementation"""
    
    def __init__(self, redis_client: redis.Redis, key: str, timeout: int = 30):
        self.redis = redis_client
        self.key = key
        self.timeout = timeout
        self.identifier = str(uuid.uuid4())
        self.acquired = False
    
    async def acquire(self, blocking: bool = True, timeout: Optional[int] = None) -> bool:
        """Acquire the lock"""
        end_time = time.time() + (timeout or self.timeout)
        
        while time.time() < end_time:
            # Try to set the key if it doesn't exist
            result = await self.redis.set(
                self.key, 
                self.identifier, 
                nx=True, 
                ex=self.timeout
            )
            
            if result:
                self.acquired = True
                return True
            
            if not blocking:
                return False
            
            await asyncio.sleep(0.1)  # Small delay before retry
        
        return False
    
    async def release(self):
        """Release the lock"""
        if not self.acquired:
            return
        
        # Only release if we still own the lock
        current_value = await self.redis.get(self.key)
        if current_value == self.identifier:
            await self.redis.delete(self.key)
        
        self.acquired = False
    
    async def __aenter__(self):
        """Async context manager entry"""
        acquired = await self.acquire()
        if not acquired:
            raise HTTPException(status_code=423, detail="Could not acquire distributed lock")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.release()
    
    async def assign_task(self, task_spec: Dict[str, Any]) -> str:
        """Assign task with distributed locking"""
        task_id = str(uuid.uuid4())
        capability_domain = CapabilityDomain(task_spec.get('capability_domain', 'data_processing'))
        
        # Use distributed lock to prevent multiple assignments
        async with self.distributed_lock(f"task-assignment:{task_id}"):
            # Create distributed task
            task = DistributedTask(
                task_id=task_id,
                task_type=task_spec.get('task_type', 'generic'),
                capability_domain=capability_domain,
                priority=TaskPriority(task_spec.get('priority', 'normal')),
                payload=task_spec.get('payload', {}),
                created_at=datetime.utcnow()
            )
            
            # Find best agent for this task
            agent_id = await self._find_best_agent(capability_domain)
            if agent_id:
                task.assigned_to = agent_id
                task.assigned_at = datetime.utcnow()
                task.status = "assigned"
                
                # Record assignment in distributed state
                await self._record_assignment(task_id, agent_id)
                
                # Publish task assignment event
                await self.event_coordinator.publish_task_event(
                    task_id, 
                    'task_assigned', 
                    {'agent_id': agent_id, 'capability_domain': capability_domain.value}
                )
            
            # Store task in distributed state
            await self.distributed_state.set_task(task)
            self.active_tasks[task_id] = task
            
            logger.info(f"Task {task_id} assigned to agent {agent_id}")
            return task_id
    
    async def _find_best_agent(self, capability_domain: CapabilityDomain) -> Optional[str]:
        """Find best available agent for capability domain"""
        agents = await self.distributed_state.get_agents_by_capability(capability_domain)
        
        if not agents:
            logger.warning(f"No agents available for capability domain: {capability_domain}")
            return None
        
        # Sort by load score (ascending) and last seen (descending)
        agents.sort(key=lambda a: (a.load_score, -a.last_seen.timestamp()))
        
        # Return the agent with lowest load
        best_agent = agents[0]
        logger.debug(f"Selected agent {best_agent.agent_id} for {capability_domain}")
        return best_agent.agent_id
    
    async def _record_assignment(self, task_id: str, agent_id: str):
        """Record task assignment in distributed state"""
        assignment_key = f"orchestrator:assignments:{task_id}"
        assignment_data = {
            'task_id': task_id,
            'agent_id': agent_id,
            'assigned_by': self.instance_id,
            'assigned_at': datetime.utcnow().isoformat()
        }
        await self.redis_client.hset(assignment_key, mapping=assignment_data)
        await self.redis_client.expire(assignment_key, 3600)  # 1 hour TTL
    
    async def register_agent(self, agent_spec: Dict[str, Any]) -> bool:
        """Register an agent in the distributed system"""
        agent_id = agent_spec.get('agent_id')
        if not agent_id:
            raise ValueError("Agent ID is required")
        
        capability_domain = CapabilityDomain(agent_spec.get('capability_domain'))
        
        agent_info = AgentInfo(
            agent_id=agent_id,
            capability_domain=capability_domain,
            instance_id=self.instance_id,
            endpoint=agent_spec.get('endpoint', ''),
            load_score=float(agent_spec.get('load_score', 0.0)),
            last_seen=datetime.utcnow(),
            status=agent_spec.get('status', 'active')
        )
        
        # Store in distributed state
        await self.distributed_state.set_agent_info(agent_info)
        self.registered_agents[agent_id] = agent_info
        
        # Publish agent registration event
        await self.event_coordinator.publish_coordination_event(
            'agent_registered',
            {
                'agent_id': agent_id,
                'capability': capability_domain.value,
                'endpoint': agent_info.endpoint
            }
        )
        
        logger.info(f"Registered agent {agent_id} with capability {capability_domain}")
        return True
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get distributed cluster status"""
        instances = await self.distributed_state.get_all_instances()
        current_leader = await self.leader_election.get_current_leader()        
        # Count agents by capability
        capability_counts = {}
        for capability in CapabilityDomain:
            agents = await self.distributed_state.get_agents_by_capability(capability)
            capability_counts[capability.value] = len(agents)
        
        return {
            'cluster_id': 'surveillance-orchestrator',
            'total_instances': len(instances),
            'current_leader': current_leader,
            'this_instance': {
                'instance_id': self.instance_id,
                'role': 'leader' if self.leader_election.is_leader else 'follower',
                'active_tasks': len(self.active_tasks),
                'load_score': self._calculate_load_score()
            },
            'instances': [
                {
                    'instance_id': inst.instance_id,
                    'hostname': inst.hostname,
                    'role': inst.role.value,
                    'active_tasks': inst.active_tasks,
                    'load_score': inst.load_score,
                    'last_heartbeat': inst.last_heartbeat.isoformat()
                }
                for inst in instances
            ],
            'agent_capabilities': capability_counts,
            'total_active_tasks': sum(inst.active_tasks for inst in instances)
        }

    # ML Workflow Management Methods
    async def submit_ml_workflow(self, workflow_spec: Dict[str, Any]) -> str:
        """Submit ML workflow for execution"""
        # Convert dict to WorkflowSpec
        workflow = self._dict_to_workflow_spec(workflow_spec)
        return await self.ml_workflow_manager.submit_workflow(workflow)
    
    async def execute_ml_workflow_sync(self, workflow_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ML workflow synchronously"""
        workflow = self._dict_to_workflow_spec(workflow_spec)
        results = await self.ml_workflow_manager.execute_ml_workflow(workflow)
        
        # Convert results to serializable format
        return {
            task_id: {
                'status': result.status,
                'output_data': result.output_data,
                'metrics': result.metrics,
                'artifacts': result.artifacts,
                'execution_time_seconds': result.execution_time_seconds,
                'completed_at': result.completed_at.isoformat() if result.completed_at else None,
                'error_message': result.error_message
            }
            for task_id, result in results.items()
        }
    
    async def get_workflow_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get ML workflow execution status"""
        execution = await self.ml_workflow_manager.get_workflow_status(execution_id)
        if not execution:
            return None
        
        return {
            'execution_id': execution.execution_id,
            'workflow_id': execution.workflow_id,
            'status': execution.status.value,
            'started_at': execution.started_at.isoformat(),
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'current_stage': execution.current_stage,
            'progress_percentage': execution.progress_percentage,
            'task_results': {
                task_id: {
                    'status': result.status,
                    'metrics': result.metrics,
                    'execution_time_seconds': result.execution_time_seconds
                }
                for task_id, result in (execution.task_results or {}).items()
            }
        }
    
    async def cancel_ml_workflow(self, execution_id: str) -> bool:
        """Cancel running ML workflow"""
        return await self.ml_workflow_manager.cancel_workflow(execution_id)
    
    async def optimize_hyperparameters(self, optimization_request: Dict[str, Any]) -> Dict[str, Any]:
        """Run hyperparameter optimization"""
        workflow_spec = self._dict_to_workflow_spec(optimization_request['workflow_spec'])
        hp_config = self._dict_to_hp_config(optimization_request['hyperparameter_config'])
        
        return await self.ml_workflow_manager.optimize_hyperparameters(workflow_spec, hp_config)
    
    async def register_ml_model(self, model_info: Dict[str, Any]) -> str:
        """Register ML model in lifecycle manager"""
        return await self.ml_workflow_manager.register_model(model_info)
    
    async def deploy_ml_model(self, model_id: str, deployment_config: Dict[str, Any]) -> str:
        """Deploy ML model to production"""
        return await self.ml_workflow_manager.deploy_model(model_id, deployment_config)
    def _dict_to_workflow_spec(self, workflow_dict: Dict[str, Any]) -> Any:
        """Convert dictionary to WorkflowSpec"""
        # Import here to avoid circular dependency
        tasks = []
        for task_dict in workflow_dict.get('tasks', []):
            task = MLTaskSpec(
                task_id=task_dict['task_id'],
                task_type=MLTaskType(task_dict['task_type']),
                dependencies=task_dict.get('dependencies', []),
                parameters=task_dict.get('parameters', {}),
                resource_requirements=task_dict.get('resource_requirements', {}),
                cache_strategy=CacheStrategy(task_dict.get('cache_strategy', 'redis')),
                timeout_seconds=task_dict.get('timeout_seconds', 3600),
                retry_policy=task_dict.get('retry_policy')
            )
            tasks.append(task)
        
        return WorkflowSpec(
            workflow_id=workflow_dict['workflow_id'],
            name=workflow_dict['name'],
            description=workflow_dict.get('description', ''),
            tasks=tasks,
            global_parameters=workflow_dict.get('global_parameters', {}),
            created_at=datetime.utcnow(),
            created_by=workflow_dict.get('created_by', 'api'),
            version=workflow_dict.get('version', '1.0'),
            tags=workflow_dict.get('tags', [])
        )
    
    def _dict_to_hp_config(self, hp_dict: Dict[str, Any]) -> Any:
        """Convert dictionary to HyperparameterConfig"""
        config = HyperparameterConfig(
            search_space=hp_dict['search_space'],
            optimization_strategy=hp_dict.get('optimization_strategy', 'bayesian')
        )
        config.max_trials = hp_dict.get('max_trials', 100)
        config.objective_metric = hp_dict.get('objective_metric', 'accuracy')
        config.direction = hp_dict.get('direction', 'maximize')
        config.early_stopping = hp_dict.get('early_stopping', True)
        config.early_stopping_patience = hp_dict.get('early_stopping_patience', 10)
        return config

# Request/Response Models for distributed orchestrator
class DistributedOrchestrationRequest(BaseModel):
    """Request model for distributed orchestration"""
    task_type: str = Field(..., description="Type of task to orchestrate")
    capability_domain: str = Field(..., description="Required capability domain")
    priority: str = Field(default="normal", description="Task priority")
    payload: Dict[str, Any] = Field(..., description="Task payload data")
    timeout_seconds: int = Field(default=300, description="Task timeout in seconds")

class DistributedOrchestrationResponse(BaseModel):
    """Response model for distributed orchestration"""
    task_id: str = Field(..., description="Assigned task ID")
    assigned_to: Optional[str] = Field(None, description="Agent ID task was assigned to")
    status: str = Field(..., description="Assignment status")
    instance_id: str = Field(..., description="Orchestrator instance that handled the request")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion time")

class AgentRegistrationRequest(BaseModel):
    """Request model for agent registration"""
    agent_id: str = Field(..., description="Unique agent identifier")
    capability_domain: str = Field(..., description="Agent capability domain")
    endpoint: str = Field(..., description="Agent endpoint URL")
    load_score: float = Field(default=0.0, description="Current agent load score")
    status: str = Field(default="active", description="Agent status")

class ClusterStatusResponse(BaseModel):
    """Response model for cluster status"""
    cluster_id: str
    total_instances: int
    current_leader: Optional[str]
    this_instance: Dict[str, Any]
    instances: List[Dict[str, Any]]
    agent_capabilities: Dict[str, int]
    total_active_tasks: int

# ML Pipeline Integration Data Structures

class MLTaskType(str, Enum):
    """ML Task types for workflow specification"""
    DATA_PREPROCESSING = "data_preprocessing"
    FEATURE_EXTRACTION = "feature_extraction"
    MODEL_TRAINING = "model_training"
    MODEL_VALIDATION = "model_validation"
    HYPERPARAMETER_TUNING = "hyperparameter_tuning"
    MODEL_DEPLOYMENT = "model_deployment"
    BATCH_INFERENCE = "batch_inference"
    MODEL_EVALUATION = "model_evaluation"

class WorkflowStatus(str, Enum):
    """ML Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class CacheStrategy(str, Enum):
    """Caching strategies for intermediate results"""
    NONE = "none"
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"
    HYBRID = "hybrid"

@dataclass
class MLTaskSpec:
    """ML Task specification within workflow"""
    task_id: str
    task_type: MLTaskType
    dependencies: List[str]  # Task IDs this task depends on
    parameters: Dict[str, Any]
    resource_requirements: Dict[str, Any]
    cache_strategy: CacheStrategy = CacheStrategy.REDIS
    timeout_seconds: int = 3600
    retry_policy: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.retry_policy is None:
            self.retry_policy = {
                "max_retries": 3,
                "backoff_factor": 2,
                "max_backoff": 300
            }

@dataclass
class WorkflowSpec:
    """Complete ML workflow specification"""
    workflow_id: str
    name: str
    description: str
    tasks: List[MLTaskSpec]
    global_parameters: Dict[str, Any]
    created_at: datetime
    created_by: str
    version: str = "1.0"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class TaskResult:
    """Result of ML task execution"""
    task_id: str
    status: str
    output_data: Dict[str, Any]
    metrics: Dict[str, float]
    artifacts: List[str]  # File paths or URIs
    execution_time_seconds: float
    completed_at: datetime
    error_message: Optional[str] = None

@dataclass
class WorkflowExecution:
    """ML workflow execution tracking"""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    task_results: Dict[str, TaskResult] = None
    current_stage: Optional[str] = None
    progress_percentage: float = 0.0
    
    def __post_init__(self):
        if self.task_results is None:
            self.task_results = {}

class HyperparameterConfig:
    """Hyperparameter optimization configuration"""
    
    def __init__(self, search_space: Dict[str, Any], optimization_strategy: str = "bayesian"):
        self.search_space = search_space
        self.optimization_strategy = optimization_strategy
        self.max_trials = 100
        self.objective_metric = "accuracy"
        self.direction = "maximize"  # or "minimize"
        self.early_stopping = True
        self.early_stopping_patience = 10

class DAGNode:
    """Directed Acyclic Graph node for task dependencies"""
    
    def __init__(self, task_spec: MLTaskSpec):
        self.task_spec = task_spec
        self.dependencies: Set[str] = set(task_spec.dependencies)
        self.dependents: Set[str] = set()
        self.status = "pending"
        self.result: Optional[TaskResult] = None

class DAGExecutor:
    """Execute ML workflows as Directed Acyclic Graphs"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.cache_manager = MLResultCache(orchestrator.redis_client)
    
    async def execute(self, task_dag: Dict[str, DAGNode], execution_id: str) -> Dict[str, TaskResult]:
        """Execute DAG with dependency tracking"""
        results = {}
        ready_tasks = self._get_ready_tasks(task_dag)
        
        while ready_tasks or self._has_running_tasks(task_dag):
            # Execute ready tasks in parallel
            if ready_tasks:
                running_tasks = []
                for task_id in ready_tasks:
                    node = task_dag[task_id]
                    node.status = "running"
                    
                    # Check cache first
                    cached_result = await self.cache_manager.get_cached_result(
                        node.task_spec, execution_id
                    )
                    
                    if cached_result:
                        logger.info(f"Using cached result for task {task_id}")
                        node.result = cached_result
                        node.status = "completed"
                        results[task_id] = cached_result
                    else:
                        # Execute task
                        task_coro = self._execute_task(node.task_spec, execution_id)
                        running_tasks.append((task_id, task_coro))
                
                # Wait for task completions
                if running_tasks:
                    completed_results = await self._wait_for_task_completions(running_tasks)
                    
                    for task_id, result in completed_results:
                        node = task_dag[task_id]
                        node.result = result
                        node.status = "completed" if result.status == "success" else "failed"
                        results[task_id] = result
                        
                        # Cache successful results
                        if result.status == "success":
                            await self.cache_manager.cache_result(
                                node.task_spec, result, execution_id
                            )
            
            # Update ready tasks
            ready_tasks = self._get_ready_tasks(task_dag)
            
            # Small delay to prevent busy waiting
            if not ready_tasks and self._has_running_tasks(task_dag):
                await asyncio.sleep(1)
        
        return results
    
    def _get_ready_tasks(self, task_dag: Dict[str, DAGNode]) -> List[str]:
        """Get tasks that are ready to execute"""
        ready = []
        for task_id, node in task_dag.items():
            if node.status == "pending":
                # Check if all dependencies are completed
                dependencies_completed = all(
                    task_dag[dep_id].status == "completed" 
                    for dep_id in node.dependencies
                    if dep_id in task_dag
                )
                if dependencies_completed:
                    ready.append(task_id)
        return ready
    
    def _has_running_tasks(self, task_dag: Dict[str, DAGNode]) -> bool:
        """Check if any tasks are currently running"""
        return any(node.status == "running" for node in task_dag.values())
    
    async def _execute_task(self, task_spec: MLTaskSpec, execution_id: str) -> TaskResult:
        """Execute individual ML task"""
        start_time = time.time()
        
        try:
            # Prepare task for agent execution
            agent_task = {
                'task_type': 'ml_workflow_task',
                'capability_domain': 'data_processing',  # Map ML tasks to capabilities
                'payload': {
                    'ml_task_type': task_spec.task_type.value,
                    'parameters': task_spec.parameters,
                    'resource_requirements': task_spec.resource_requirements,
                    'execution_id': execution_id,
                    'task_id': task_spec.task_id
                }
            }
            
            # Assign task to agent
            agent_task_id = await self.orchestrator.assign_task(agent_task)
            
            # Wait for task completion (simplified - in practice would be event-driven)
            result = await self._wait_for_task_result(agent_task_id, task_spec.timeout_seconds)
            
            execution_time = time.time() - start_time
            
            return TaskResult(
                task_id=task_spec.task_id,
                status="success",
                output_data=result.get('output_data', {}),
                metrics=result.get('metrics', {}),
                artifacts=result.get('artifacts', []),
                execution_time_seconds=execution_time,
                completed_at=datetime.utcnow()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Task {task_spec.task_id} failed: {e}")
            
            return TaskResult(
                task_id=task_spec.task_id,
                status="failed",
                output_data={},
                metrics={},
                artifacts=[],
                execution_time_seconds=execution_time,
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )
    
    async def _wait_for_task_completions(self, running_tasks: List[Tuple[str, Any]]) -> List[Tuple[str, TaskResult]:
]:
        """Wait for multiple task completions"""
        completed = []
        
        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[task_coro for _, task_coro in running_tasks],
            return_exceptions=True
        )
        
        for i, result in enumerate(results):
            task_id = running_tasks[i][0]
            if isinstance(result, Exception):
                # Convert exception to failed task result
                completed.append((task_id, TaskResult(
                    task_id=task_id,
                    status="failed",
                    output_data={},
                    metrics={},
                    artifacts=[],
                    execution_time_seconds=0,
                    completed_at=datetime.utcnow(),
                    error_message=str(result)
                )))
            else:
                completed.append((task_id, result))
        
        return completed
    
    async def _wait_for_task_result(self, agent_task_id: str, timeout_seconds: int) -> Dict[str, Any]:
        """Wait for agent task completion and return result"""
        # This is a simplified implementation
        # In practice, this would listen for task completion events
        end_time = time.time() + timeout_seconds
        
        while time.time() < end_time:
            # Check task status in distributed state
            task = await self.orchestrator.distributed_state.get_task(agent_task_id)
            if task and task.status in ["completed", "failed"]:
                # Return mock result for now
                return {
                    'output_data': {'processed': True},
                    'metrics': {'accuracy': 0.95},
                    'artifacts': []
                }
            
            await asyncio.sleep(5)  # Poll every 5 seconds
        
        raise TimeoutError(f"Task {agent_task_id} timed out after {timeout_seconds} seconds")

class MLResultCache:
    """Cache for ML workflow intermediate results"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.namespace = "ml_cache"
        self.default_ttl = 86400  # 24 hours
    
    def _cache_key(self, task_spec: MLTaskSpec, execution_id: str) -> str:
        """Generate cache key for task result"""
        # Create a hash of task parameters for cache key
        import hashlib
        param_str = json.dumps(task_spec.parameters, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        return f"{self.namespace}:{task_spec.task_type.value}:{param_hash}:{execution_id}"
    
    async def get_cached_result(self, task_spec: MLTaskSpec, execution_id: str) -> Optional[TaskResult]:
        """Get cached result for task"""
        if task_spec.cache_strategy == CacheStrategy.NONE:
            return None
        
        cache_key = self._cache_key(task_spec, execution_id)
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            try:
                result_data = json.loads(cached_data)
                result_data['completed_at'] = datetime.fromisoformat(result_data['completed_at'])
                return TaskResult(**result_data)
            except Exception as e:
                logger.error(f"Error deserializing cached result: {e}")
                return None
        
        return None
    
    async def cache_result(self, task_spec: MLTaskSpec, result: TaskResult, execution_id: str):
        """Cache task result"""
        if task_spec.cache_strategy == CacheStrategy.NONE:
            return
        
        cache_key = self._cache_key(task_spec, execution_id)
        
        # Serialize result
        result_data = asdict(result)
        result_data['completed_at'] = result.completed_at.isoformat()
        
        # Cache with TTL
        await self.redis.setex(
            cache_key, 
            self.default_ttl, 
            json.dumps(result_data)
        )
        
        logger.debug(f"Cached result for task {task_spec.task_id}")
    
    async def invalidate_cache(self, task_spec: MLTaskSpec, execution_id: str):
        """Invalidate cached result"""
        cache_key = self._cache_key(task_spec, execution_id)
        await self.redis.delete(cache_key)
    
    async def clear_execution_cache(self, execution_id: str):
        """Clear all cached results for an execution"""
        pattern = f"{self.namespace}:*:{execution_id}"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

class HyperparameterOptimizer:
    """Hyperparameter optimization coordinator"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.active_optimizations: Dict[str, Dict] = {}
    
    async def optimize_hyperparameters(
        self, 
        base_workflow: WorkflowSpec, 
        hp_config: HyperparameterConfig,
        optimization_id: str
    ) -> Dict[str, Any]:
        """Coordinate hyperparameter optimization"""
        
        logger.info(f"Starting hyperparameter optimization: {optimization_id}")
        
        # Track optimization
        self.active_optimizations[optimization_id] = {
            'status': 'running',
            'trials_completed': 0,
            'best_score': None,
            'best_params': None,
            'started_at': datetime.utcnow()
        }
        
        try:
            # Generate parameter combinations
            param_combinations = self._generate_parameter_combinations(
                hp_config.search_space, 
                hp_config.max_trials
            )
            
            best_score = None
            best_params = None
            best_execution_id = None
            
            # Execute trials
            for i, params in enumerate(param_combinations):
                trial_id = f"{optimization_id}_trial_{i}"
                
                # Create workflow with trial parameters
                trial_workflow = self._create_trial_workflow(base_workflow, params, trial_id)
                
                # Execute workflow
                try:
                    execution_result = await self._execute_trial_workflow(trial_workflow)
                    
                    # Extract objective metric
                    objective_score = self._extract_objective_score(
                        execution_result, 
                        hp_config.objective_metric
                    )
                    
                    # Update best if better
                    if self._is_better_score(objective_score, best_score, hp_config.direction):
                        best_score = objective_score
                        best_params = params
                        best_execution_id = trial_workflow.workflow_id
                    
                    # Update tracking
                    self.active_optimizations[optimization_id].update({
                        'trials_completed': i + 1,
                        'best_score': best_score,
                        'best_params': best_params
                    })
                    
                    # Early stopping check
                    if hp_config.early_stopping and self._should_stop_early(
                        optimization_id, hp_config.early_stopping_patience
                    ):
                        logger.info(f"Early stopping triggered for optimization {optimization_id}")
                        break
                        
                except Exception as e:
                    logger.error(f"Trial {trial_id} failed: {e}")
                    continue
            
            # Finalize optimization
            self.active_optimizations[optimization_id]['status'] = 'completed'
            
            return {
                'optimization_id': optimization_id,
                'best_score': best_score,
                'best_parameters': best_params,
                'best_execution_id': best_execution_id,
                'trials_completed': self.active_optimizations[optimization_id]['trials_completed'],
                'completed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.active_optimizations[optimization_id]['status'] = 'failed'
            logger.error(f"Hyperparameter optimization {optimization_id} failed: {e}")
            raise
    
    def _generate_parameter_combinations(self, search_space: Dict[str, Any], max_trials: int) -> List[Dict[str, Any]]:
        """Generate parameter combinations for trials"""
        import itertools
        import random
        
        # Simple grid search implementation
        # In practice, would use more sophisticated methods like Bayesian optimization
        param_names = list(search_space.keys())
        param_values = []
        
        for param_name, param_config in search_space.items():
            if param_config['type'] == 'categorical':
                param_values.append(param_config['values'])
            elif param_config['type'] == 'continuous':
                # Generate random values in range
                values = [
                    random.uniform(param_config['min'], param_config['max'])
                    for _ in range(min(10, max_trials // len(search_space)))
                ]
                param_values.append(values)
            elif param_config['type'] == 'integer':
                values = list(range(param_config['min'], param_config['max'] + 1))
                param_values.append(values)
        
        # Generate combinations
        combinations = list(itertools.product(*param_values))
        random.shuffle(combinations)
        
        # Convert to parameter dictionaries
        param_combinations = []
        for combo in combinations[:max_trials]:
            param_dict = dict(zip(param_names, combo))
            param_combinations.append(param_dict)
        
        return param_combinations
    
    def _create_trial_workflow(self, base_workflow: WorkflowSpec, params: Dict[str, Any], trial_id: str) -> WorkflowSpec:
        """Create trial workflow with specific parameters"""
        # Deep copy base workflow
        import copy
        trial_workflow = copy.deepcopy(base_workflow)
        trial_workflow.workflow_id = trial_id
        
        # Update task parameters with trial parameters
        for task in trial_workflow.tasks:
            if task.task_type == MLTaskType.MODEL_TRAINING:
                task.parameters.update(params)
        
        return trial_workflow
    
    async def _execute_trial_workflow(self, workflow: WorkflowSpec) -> Dict[str, TaskResult]:
        """Execute trial workflow"""
        # Create workflow manager and execute
        workflow_manager = MLWorkflowManager(self.orchestrator)
        return await workflow_manager.execute_ml_workflow(workflow)
    
    def _extract_objective_score(self, execution_result: Dict[str, TaskResult], objective_metric: str) -> float:
        """Extract objective score from execution results"""
        # Look for validation/evaluation task results
        for task_result in execution_result.values():
            if objective_metric in task_result.metrics:
                return task_result.metrics[objective_metric]
        
        # Default fallback
        return 0.0
    
    def _is_better_score(self, new_score: float, best_score: Optional[float], direction: str) -> bool:
        """Check if new score is better than current best"""
        if best_score is None:
            return True
        
        if direction == "maximize":
            return new_score > best_score
        else:
            return new_score < best_score
    
    def _should_stop_early(self, optimization_id: str, patience: int) -> bool:
        """Check if early stopping should be triggered"""
        # Simplified early stopping logic
        # In practice, would track improvement history
        opt_info = self.active_optimizations[optimization_id]
        return opt_info['trials_completed'] >= patience * 2

class ModelLifecycleManager:
    """Manage ML model lifecycle operations"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.model_registry: Dict[str, Dict] = {}
    
    async def register_model(self, model_info: Dict[str, Any]) -> str:
        """Register a new model version"""
        model_id = f"{model_info['name']}_v{model_info['version']}"

        self.model_registry[model_id] = {
            **model_info,
            'registered_at': datetime.utcnow().isoformat(),
            'status': 'registered'
        }
        
        logger.info(f"Registered model: {model_id}")
        return model_id
    
    async def deploy_model(self, model_id: str, deployment_config: Dict[str, Any]) -> str:
        """Deploy model to production"""
        if model_id not in self.model_registry:
            raise ValueError(f"Model {model_id} not found in registry")
        
        # Create deployment workflow
        deployment_workflow = self._create_deployment_workflow(model_id, deployment_config)
        
        # Execute deployment
        workflow_manager = MLWorkflowManager(self.orchestrator)
        deployment_result = await workflow_manager.execute_ml_workflow(deployment_workflow)
        
        # Update model status
        self.model_registry[model_id]['status'] = 'deployed'
        self.model_registry[model_id]['deployed_at'] = datetime.utcnow().isoformat()
        
        return deployment_workflow.workflow_id
    
    def _create_deployment_workflow(self, model_id: str, deployment_config: Dict[str, Any]) -> WorkflowSpec:
        """Create deployment workflow specification"""
        workflow_id = f"deploy_{model_id}_{int(time.time())}"
        
        tasks = [
            MLTaskSpec(
                task_id=f"{workflow_id}_validate",
                task_type=MLTaskType.MODEL_VALIDATION,
                dependencies=[],
                parameters={
                    'model_id': model_id,
                    'validation_dataset': deployment_config.get('validation_dataset')
                },
                resource_requirements={'memory': '4GB', 'cpu': '2'}
            ),
            MLTaskSpec(
                task_id=f"{workflow_id}_deploy",
                task_type=MLTaskType.MODEL_DEPLOYMENT,
                dependencies=[f"{workflow_id}_validate"],
                parameters={
                    'model_id': model_id,
                    'deployment_target': deployment_config.get('target', 'production'),
                    'scaling_config': deployment_config.get('scaling', {})
                },
                resource_requirements={'memory': '8GB', 'cpu': '4'}
            )
        ]
        
        return WorkflowSpec(
            workflow_id=workflow_id,
            name=f"Deploy {model_id}",
            description=f"Deployment workflow for model {model_id}",
            tasks=tasks,
            global_parameters=deployment_config,
            created_at=datetime.utcnow(),
            created_by="system",
            tags=["deployment", "model_lifecycle"]
        )

class MLWorkflowManager:
    """Advanced ML workflow manager with DAG execution and lifecycle management"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.dag_executor = DAGExecutor(orchestrator)
        self.hyperparameter_optimizer = HyperparameterOptimizer(orchestrator)
        self.model_lifecycle_manager = ModelLifecycleManager(orchestrator)
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.workflow_specs: Dict[str, WorkflowSpec] = {}
    
    async def submit_workflow(self, workflow_spec: WorkflowSpec) -> str:
        """Submit ML workflow for execution"""
        # Validate workflow specification
        self._validate_workflow_spec(workflow_spec)
        
        # Store workflow spec
        self.workflow_specs[workflow_spec.workflow_id] = workflow_spec
        
        # Create execution tracking
        execution_id = f"{workflow_spec.workflow_id}_exec_{int(time.time())}"
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_spec.workflow_id,
            status=WorkflowStatus.PENDING,
            started_at=datetime.utcnow()
        )
        
        self.active_workflows[execution_id] = execution
        
        # Start workflow execution in background
        asyncio.create_task(self._execute_workflow_async(execution_id))
        
        logger.info(f"Submitted ML workflow: {workflow_spec.workflow_id}")
        return execution_id
    
    async def execute_ml_workflow(self, workflow_spec: WorkflowSpec) -> Dict[str, TaskResult]:
        """Execute ML workflow synchronously"""
        # Convert workflow spec to directed acyclic graph
        task_dag = self._build_task_dag(workflow_spec)
        
        # Create execution tracking
        execution_id = f"{workflow_spec.workflow_id}_sync_{int(time.time())}"
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_spec.workflow_id,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        self.active_workflows[execution_id] = execution
        
        try:
            # Execute DAG with dependency tracking
            results = await self.dag_executor.execute(task_dag, execution_id)
            
            # Update execution status
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.task_results = results
            execution.progress_percentage = 100.0
            
            # Record workflow completion and results
            await self._record_workflow_completion(workflow_spec.workflow_id, results)
            
            logger.info(f"Completed ML workflow: {workflow_spec.workflow_id}")
            return results
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.utcnow()
            logger.error(f"ML workflow {workflow_spec.workflow_id} failed: {e}")
            raise
    
    async def _execute_workflow_async(self, execution_id: str):
        """Execute workflow asynchronously"""
        execution = self.active_workflows[execution_id]
        workflow_spec = self.workflow_specs[execution.workflow_id]
        
        try:
            execution.status = WorkflowStatus.RUNNING
            
            # Build and execute DAG
            task_dag = self._build_task_dag(workflow_spec)
            results = await self.dag_executor.execute(task_dag, execution_id)
            
            # Update execution
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.task_results = results
            execution.progress_percentage = 100.0
            
            await self._record_workflow_completion(workflow_spec.workflow_id, results)
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.utcnow()
            logger.error(f"Async workflow execution failed: {e}")
    
    def _build_task_dag(self, workflow_spec: WorkflowSpec) -> Dict[str, DAGNode]:
        """Convert workflow specification to directed acyclic graph"""
        dag_nodes = {}
        
        # Create nodes for each task
        for task_spec in workflow_spec.tasks:
            node = DAGNode(task_spec)
            dag_nodes[task_spec.task_id] = node
        
        # Build dependency relationships
        for task_spec in workflow_spec.tasks:
            node = dag_nodes[task_spec.task_id]
            for dep_id in task_spec.dependencies:
                if dep_id in dag_nodes:
                    dag_nodes[dep_id].dependents.add(task_spec.task_id)
        
        # Validate DAG (no cycles)
        self._validate_dag(dag_nodes)
        
        return dag_nodes
    
    def _validate_workflow_spec(self, workflow_spec: WorkflowSpec):
        """Validate workflow specification"""
        if not workflow_spec.tasks:
            raise ValueError("Workflow must contain at least one task")
        
        # Check for duplicate task IDs
        task_ids = [task.task_id for task in workflow_spec.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Duplicate task IDs found in workflow")
        
        # Validate dependencies
        for task in workflow_spec.tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    raise ValueError(f"Task {task.task_id} depends on non-existent task {dep_id}")
    
    def _validate_dag(self, dag_nodes: Dict[str, DAGNode]):
        """Validate DAG has no cycles"""
        # Simple cycle detection using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            node = dag_nodes[node_id]
            for dependent_id in node.dependents:
                if dependent_id not in visited:
                    if has_cycle(dependent_id):
                        return True
                elif dependent_id in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in dag_nodes:
            if node_id not in visited:
                if has_cycle(node_id):
                    raise ValueError("Workflow contains circular dependencies")
    
    async def _record_workflow_completion(self, workflow_id: str, results: Dict[str, TaskResult]):
        """Record workflow completion in distributed state"""
        completion_data = {
            'workflow_id': workflow_id,
            'completed_at': datetime.utcnow().isoformat(),
            'task_count': len(results),
            'successful_tasks': len([r for r in results.values() if r.status == 'success']),
            'failed_tasks': len([r for r in results.values() if r.status == 'failed']),
            'total_execution_time': sum(r.execution_time_seconds for r in results.values())
        }
        
        # Store in Redis
        key = f"orchestrator:workflow_completions:{workflow_id}"
        await self.orchestrator.redis_client.hset(key, mapping=completion_data)
        await self.orchestrator.redis_client.expire(key, 86400 * 7)  # 7 days TTL
        
        logger.info(f"Recorded completion for workflow {workflow_id}")
    
    async def get_workflow_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution status"""
        return self.active_workflows.get(execution_id)
    
    async def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel running workflow"""
        if execution_id in self.active_workflows:
            execution = self.active_workflows[execution_id]
            if execution.status == WorkflowStatus.RUNNING:
                execution.status = WorkflowStatus.CANCELLED
                execution.completed_at = datetime.utcnow()
                logger.info(f"Cancelled workflow execution: {execution_id}")
                return True
        return False
    
    async def optimize_hyperparameters(
        self, 
        workflow_spec: WorkflowSpec, 
        hp_config: HyperparameterConfig
    ) -> Dict[str, Any]:
        """Run hyperparameter optimization"""
        optimization_id = f"hp_opt_{workflow_spec.workflow_id}_{int(time.time())}"
        return await self.hyperparameter_optimizer.optimize_hyperparameters(
            workflow_spec, hp_config, optimization_id
        )
    
    async def deploy_model(self, model_id: str, deployment_config: Dict[str, Any]) -> str:
        """Deploy model using lifecycle manager"""
        return await self.model_lifecycle_manager.deploy_model(model_id, deployment_config)
    
    async def register_model(self, model_info: Dict[str, Any]) -> str:
        """Register model in lifecycle manager"""
        return await self.model_lifecycle_manager.register_model(model_info)
    
    def create_preprocessing_workflow(self, dataset_config: Dict[str, Any]) -> WorkflowSpec:
        """Create a standard data preprocessing workflow"""
        workflow_id = f"preprocess_{int(time.time())}"
        
        tasks = [
            MLTaskSpec(
                task_id=f"{workflow_id}_load_data",
                task_type=MLTaskType.DATA_PREPROCESSING,
                dependencies=[],
                parameters={
                    'operation': 'load_data',
                    'dataset_path': dataset_config['path'],
                    'format': dataset_config.get('format', 'csv')
                },
                resource_requirements={'memory': '2GB', 'cpu': '1'}
            ),
            MLTaskSpec(
                task_id=f"{workflow_id}_clean_data",
                task_type=MLTaskType.DATA_PREPROCESSING,
                dependencies=[f"{workflow_id}_load_data"],
                parameters={
                    'operation': 'clean_data',
                    'remove_nulls': dataset_config.get('remove_nulls', True),
                    'normalize': dataset_config.get('normalize', True)
                },
                resource_requirements={'memory': '4GB', 'cpu': '2'}
            ),
            MLTaskSpec(
                task_id=f"{workflow_id}_feature_extraction",
                task_type=MLTaskType.FEATURE_EXTRACTION,
                dependencies=[f"{workflow_id}_clean_data"],
                parameters={
                    'feature_columns': dataset_config.get('feature_columns', []),
                    'target_column': dataset_config.get('target_column'),
                    'scaling_method': dataset_config.get('scaling_method', 'standard')
                },
                resource_requirements={'memory': '4GB', 'cpu': '2'}
            )
        ]
        
        return WorkflowSpec(
            workflow_id=workflow_id,
            name="Data Preprocessing Workflow",
            description="Standard data preprocessing pipeline",
            tasks=tasks,
            global_parameters=dataset_config,
            created_at=datetime.utcnow(),
            created_by="system",
            tags=["preprocessing", "data_pipeline"]
        )
    
    def create_training_workflow(self, model_config: Dict[str, Any]) -> WorkflowSpec:
        """Create a standard model training workflow"""
        workflow_id = f"train_{model_config.get('model_type', 'model')}_{int(time.time())}"
        
        tasks = [
            MLTaskSpec(
                task_id=f"{workflow_id}_train",
                task_type=MLTaskType.MODEL_TRAINING,
                dependencies=[],
                parameters={
                    'model_type': model_config.get('model_type', 'sklearn'),
                    'algorithm': model_config.get('algorithm', 'random_forest'),
                    'hyperparameters': model_config.get('hyperparameters', {}),
                    'training_data': model_config.get('training_data')
                },
                resource_requirements={'memory': '8GB', 'cpu': '4', 'gpu': '1'}
            ),
            MLTaskSpec(
                task_id=f"{workflow_id}_validate",
                task_type=MLTaskType.MODEL_VALIDATION,
                dependencies=[f"{workflow_id}_train"],
                parameters={
                    'validation_data': model_config.get('validation_data'),
                    'metrics': model_config.get('metrics', ['accuracy', 'precision', 'recall'])
                },
                resource_requirements={'memory': '4GB', 'cpu': '2'}
            ),
            MLTaskSpec(
                task_id=f"{workflow_id}_evaluate",
                task_type=MLTaskType.MODEL_EVALUATION,
                dependencies=[f"{workflow_id}_validate"],
                parameters={
                    'test_data': model_config.get('test_data'),
                    'evaluation_metrics': model_config.get('evaluation_metrics', [])
                },
                resource_requirements={'memory': '4GB', 'cpu': '2'}
            )
        ]
        
        return WorkflowSpec(
            workflow_id=workflow_id,
            name=f"Training Workflow - {model_config.get('model_type', 'Model')}",
            description=f"Training pipeline for {model_config.get('algorithm', 'model')}",
            tasks=tasks,
            global_parameters=model_config,
            created_at=datetime.utcnow(),
            created_by="system",
            tags=["training", "ml_pipeline"]
        )

# ML Workflow Request/Response Models
class MLWorkflowRequest(BaseModel):
    """Request model for ML workflow submission"""
    workflow_id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Workflow name")
    description: str = Field(default="", description="Workflow description")
    tasks: List[Dict[str, Any]] = Field(..., description="List of ML tasks")
    global_parameters: Dict[str, Any] = Field(default_factory=dict, description="Global workflow parameters")
    tags: List[str] = Field(default_factory=list, description="Workflow tags")

class MLWorkflowResponse(BaseModel):
    """Response model for ML workflow operations"""
    execution_id: str = Field(..., description="Workflow execution ID")
    workflow_id: str = Field(..., description="Original workflow ID")
    status: str = Field(..., description="Execution status")
    message: str = Field(..., description="Response message")
    started_at: Optional[str] = Field(None, description="Execution start time")

class MLWorkflowStatusResponse(BaseModel):
    """Response model for workflow status queries"""
    execution_id: str
    workflow_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    current_stage: Optional[str] = None
    progress_percentage: float
    task_results: Dict[str, Any]

class HyperparameterOptimizationRequest(BaseModel):
    """Request model for hyperparameter optimization"""
    workflow_spec: Dict[str, Any] = Field(..., description="Base workflow specification")
    hyperparameter_config: Dict[str, Any] = Field(..., description="Hyperparameter search configuration")

class HyperparameterOptimizationResponse(BaseModel):
    """Response model for hyperparameter optimization"""
    optimization_id: str
    best_score: Optional[float]
    best_parameters: Optional[Dict[str, Any]]
    best_execution_id: Optional[str]
    trials_completed: int
    completed_at: str

class ModelRegistrationRequest(BaseModel):
    """Request model for model registration"""
    name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    model_type: str = Field(..., description="Type of model")
    framework: str = Field(..., description="ML framework used")
    artifacts: List[str] = Field(..., description="Model artifact paths")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional model metadata")
    tags: List[str] = Field(default_factory=list, description="Model tags")

class ModelDeploymentRequest(BaseModel):
    """Request model for model deployment"""
    model_id: str = Field(..., description="Model ID to deploy")
    target: str = Field(default="production", description="Deployment target environment")
    scaling_config: Dict[str, Any] = Field(default_factory=dict, description="Scaling configuration")
    validation_dataset: Optional[str] = Field(None, description="Validation dataset for pre-deployment testing")

class WorkflowTemplateRequest(BaseModel):
    """Request model for creating workflow templates"""
    template_type: str = Field(..., description="Type of workflow template (preprocessing, training, etc.)")
    configuration: Dict[str, Any] = Field(..., description="Template configuration parameters")

    @asynccontextmanager
    async def distributed_lock(self, resource_id: str, timeout: int = 30):
        """Distributed lock context manager using SimpleRedisLock"""
        lock_key = f"orchestrator:locks:{resource_id}"
        lock = SimpleRedisLock(self.redis_client, lock_key, timeout=timeout)
        
        try:
            async with lock:
                yield lock
        except Exception as e:
            logger.error(f"Error with distributed lock: {e}")
            raise

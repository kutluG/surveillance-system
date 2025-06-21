"""
Distributed Orchestrator Configuration

Configuration settings for the distributed orchestrator including:
- Redis settings for state synchronization
- Kafka settings for event coordination
- Leader election parameters
- Distributed locking configuration
- Cluster management settings
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

class DistributedMode(str, Enum):
    """Distributed orchestrator mode"""
    STANDALONE = "standalone"  # Single instance mode
    CLUSTER = "cluster"       # Multi-instance cluster mode

@dataclass
class RedisConfig:
    """Redis configuration for distributed state"""
    url: str = "redis://redis:6379/0"
    decode_responses: bool = True
    socket_timeout: int = 30
    socket_connect_timeout: int = 30
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    
    # Connection pool settings
    max_connections: int = 50
    connection_pool_kwargs: Dict[str, Any] = None
    
    # Distributed state settings
    key_prefix: str = "orchestrator"
    state_ttl: int = 300  # 5 minutes
    lock_timeout: int = 30
    lock_sleep: float = 0.1

@dataclass
class KafkaConfig:
    """Kafka configuration for event coordination"""
    bootstrap_servers: str = "kafka:9092"
    client_id_prefix: str = "orchestrator"
    coordination_topic: str = "orchestrator.coordination"
    task_events_topic: str = "orchestrator.task_events"
    
    # Producer settings
    producer_config: Dict[str, Any] = None
    acks: str = "all"
    retries: int = 3
    batch_size: int = 16384
    linger_ms: int = 10
    
    # Consumer settings
    consumer_config: Dict[str, Any] = None
    group_id: str = "orchestrator-coordination"
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 10000

@dataclass
class LeaderElectionConfig:
    """Leader election configuration"""
    enabled: bool = True
    leader_key: str = "leader"
    leader_ttl: int = 30  # seconds
    election_interval: int = 10  # seconds
    candidate_timeout: int = 5  # seconds
    
    # Leader-only operations
    cleanup_interval: int = 60  # seconds
    dead_instance_threshold: int = 120  # seconds
    expired_task_threshold: int = 3600  # seconds

@dataclass
class ShardingConfig:
    """Shard-based orchestration configuration"""
    enabled: bool = True
    shard_by_capability: bool = True
    max_agents_per_shard: int = 100
    rebalance_threshold: float = 0.3  # 30% load difference triggers rebalancing
    rebalance_interval: int = 300  # 5 minutes
    
    # Capability domain weights for load balancing
    capability_weights: Dict[str, float] = None

@dataclass
class TaskAssignmentConfig:
    """Task assignment configuration"""
    assignment_strategy: str = "load_balanced"  # load_balanced, round_robin, random
    max_retry_attempts: int = 3
    default_timeout: int = 300  # seconds
    
    # Load balancing parameters
    load_score_weight: float = 0.7
    last_seen_weight: float = 0.3
    agent_capacity_limit: int = 10
    
    # Task priorities and timeouts
    priority_timeouts: Dict[str, int] = None

@dataclass
class HealthMonitoringConfig:
    """Health monitoring configuration"""
    heartbeat_interval: int = 30  # seconds
    instance_timeout: int = 120  # seconds
    agent_timeout: int = 180  # seconds
    
    # Health check endpoints
    health_check_enabled: bool = True
    health_check_path: str = "/health/distributed"
    metrics_collection: bool = True
    
    # Circuit breaker integration
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout: int = 60

@dataclass
class SecurityConfig:
    """Security configuration for distributed orchestrator"""
    enable_authentication: bool = True
    enable_authorization: bool = True
    enable_encryption: bool = False  # For Redis/Kafka communication
    
    # API security
    require_api_key: bool = True
    api_key_header: str = "X-Orchestrator-API-Key"
    rate_limiting: bool = True
    max_requests_per_minute: int = 1000
    
    # Inter-instance communication
    instance_auth_enabled: bool = False
    shared_secret: Optional[str] = None

@dataclass
class DistributedOrchestratorConfig:
    """Main distributed orchestrator configuration"""
    
    # Basic settings
    mode: DistributedMode = DistributedMode.CLUSTER
    instance_id: Optional[str] = None
    hostname: Optional[str] = None
    port: int = 8000
    
    # Component configurations
    redis: RedisConfig = None
    kafka: KafkaConfig = None
    leader_election: LeaderElectionConfig = None
    sharding: ShardingConfig = None
    task_assignment: TaskAssignmentConfig = None
    health_monitoring: HealthMonitoringConfig = None
    security: SecurityConfig = None
    
    # Feature flags
    enable_distributed_locking: bool = True
    enable_event_coordination: bool = True
    enable_automatic_failover: bool = True
    enable_cluster_rebalancing: bool = True
    
    # Logging and debugging
    log_level: str = "INFO"
    debug_mode: bool = False
    trace_requests: bool = False
    
    def __post_init__(self):
        """Initialize default configurations"""
        if self.redis is None:
            self.redis = RedisConfig()
        
        if self.kafka is None:
            self.kafka = KafkaConfig()
        
        if self.leader_election is None:
            self.leader_election = LeaderElectionConfig()
        
        if self.sharding is None:
            self.sharding = ShardingConfig()
        
        if self.task_assignment is None:
            self.task_assignment = TaskAssignmentConfig()
        
        if self.health_monitoring is None:
            self.health_monitoring = HealthMonitoringConfig()
        
        if self.security is None:
            self.security = SecurityConfig()
        
        # Set default capability weights
        if self.sharding.capability_weights is None:
            self.sharding.capability_weights = {
                "rag_analysis": 1.0,
                "rule_generation": 0.8,
                "notification": 0.6,
                "vms_integration": 1.2,
                "security_monitoring": 1.5,
                "data_processing": 1.0
            }
        
        # Set default priority timeouts
        if self.task_assignment.priority_timeouts is None:
            self.task_assignment.priority_timeouts = {
                "critical": 60,    # 1 minute
                "high": 300,       # 5 minutes
                "normal": 600,     # 10 minutes
                "low": 1800        # 30 minutes
            }
        
        # Set default producer config
        if self.kafka.producer_config is None:
            self.kafka.producer_config = {
                'acks': self.kafka.acks,
                'retries': self.kafka.retries,
                'batch.size': self.kafka.batch_size,
                'linger.ms': self.kafka.linger_ms,
                'compression.type': 'snappy'
            }
        
        # Set default consumer config
        if self.kafka.consumer_config is None:
            self.kafka.consumer_config = {
                'auto.offset.reset': self.kafka.auto_offset_reset,
                'enable.auto.commit': self.kafka.enable_auto_commit,
                'session.timeout.ms': self.kafka.session_timeout_ms,
                'heartbeat.interval.ms': self.kafka.heartbeat_interval_ms
            }

def load_distributed_config() -> DistributedOrchestratorConfig:
    """Load distributed orchestrator configuration from environment variables"""
    
    # Basic settings
    mode = DistributedMode(os.getenv("ORCHESTRATOR_MODE", "cluster"))
    instance_id = os.getenv("ORCHESTRATOR_INSTANCE_ID")
    hostname = os.getenv("ORCHESTRATOR_HOSTNAME", "localhost")
    port = int(os.getenv("ORCHESTRATOR_PORT", "8000"))
    
    # Redis configuration
    redis_config = RedisConfig(
        url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
        decode_responses=bool(os.getenv("REDIS_DECODE_RESPONSES", "true").lower() == "true"),
        socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "30")),
        max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "50")),
        key_prefix=os.getenv("REDIS_KEY_PREFIX", "orchestrator"),
        state_ttl=int(os.getenv("REDIS_STATE_TTL", "300")),
        lock_timeout=int(os.getenv("REDIS_LOCK_TIMEOUT", "30"))
    )
    
    # Kafka configuration
    kafka_config = KafkaConfig(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        client_id_prefix=os.getenv("KAFKA_CLIENT_ID_PREFIX", "orchestrator"),
        coordination_topic=os.getenv("KAFKA_COORDINATION_TOPIC", "orchestrator.coordination"),
        task_events_topic=os.getenv("KAFKA_TASK_EVENTS_TOPIC", "orchestrator.task_events"),
        group_id=os.getenv("KAFKA_GROUP_ID", "orchestrator-coordination")
    )
    
    # Leader election configuration
    leader_election_config = LeaderElectionConfig(
        enabled=bool(os.getenv("LEADER_ELECTION_ENABLED", "true").lower() == "true"),
        leader_ttl=int(os.getenv("LEADER_ELECTION_TTL", "30")),
        election_interval=int(os.getenv("LEADER_ELECTION_INTERVAL", "10")),
        cleanup_interval=int(os.getenv("LEADER_CLEANUP_INTERVAL", "60"))
    )
    
    # Sharding configuration
    sharding_config = ShardingConfig(
        enabled=bool(os.getenv("SHARDING_ENABLED", "true").lower() == "true"),
        shard_by_capability=bool(os.getenv("SHARD_BY_CAPABILITY", "true").lower() == "true"),
        max_agents_per_shard=int(os.getenv("MAX_AGENTS_PER_SHARD", "100")),
        rebalance_threshold=float(os.getenv("REBALANCE_THRESHOLD", "0.3")),
        rebalance_interval=int(os.getenv("REBALANCE_INTERVAL", "300"))
    )
    
    # Task assignment configuration
    task_assignment_config = TaskAssignmentConfig(
        assignment_strategy=os.getenv("TASK_ASSIGNMENT_STRATEGY", "load_balanced"),
        max_retry_attempts=int(os.getenv("TASK_MAX_RETRIES", "3")),
        default_timeout=int(os.getenv("TASK_DEFAULT_TIMEOUT", "300")),
        load_score_weight=float(os.getenv("LOAD_SCORE_WEIGHT", "0.7")),
        agent_capacity_limit=int(os.getenv("AGENT_CAPACITY_LIMIT", "10"))
    )
    
    # Health monitoring configuration
    health_monitoring_config = HealthMonitoringConfig(
        heartbeat_interval=int(os.getenv("HEARTBEAT_INTERVAL", "30")),
        instance_timeout=int(os.getenv("INSTANCE_TIMEOUT", "120")),
        agent_timeout=int(os.getenv("AGENT_TIMEOUT", "180")),
        health_check_enabled=bool(os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true"),
        circuit_breaker_enabled=bool(os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true")
    )
    
    # Security configuration
    security_config = SecurityConfig(
        enable_authentication=bool(os.getenv("ENABLE_AUTHENTICATION", "true").lower() == "true"),
        enable_authorization=bool(os.getenv("ENABLE_AUTHORIZATION", "true").lower() == "true"),
        require_api_key=bool(os.getenv("REQUIRE_API_KEY", "true").lower() == "true"),
        rate_limiting=bool(os.getenv("RATE_LIMITING", "true").lower() == "true"),
        max_requests_per_minute=int(os.getenv("MAX_REQUESTS_PER_MINUTE", "1000"))
    )
    
    # Feature flags
    enable_distributed_locking = bool(os.getenv("ENABLE_DISTRIBUTED_LOCKING", "true").lower() == "true")
    enable_event_coordination = bool(os.getenv("ENABLE_EVENT_COORDINATION", "true").lower() == "true")
    enable_automatic_failover = bool(os.getenv("ENABLE_AUTOMATIC_FAILOVER", "true").lower() == "true")
    enable_cluster_rebalancing = bool(os.getenv("ENABLE_CLUSTER_REBALANCING", "true").lower() == "true")
    
    return DistributedOrchestratorConfig(
        mode=mode,
        instance_id=instance_id,
        hostname=hostname,
        port=port,
        redis=redis_config,
        kafka=kafka_config,
        leader_election=leader_election_config,
        sharding=sharding_config,
        task_assignment=task_assignment_config,
        health_monitoring=health_monitoring_config,
        security=security_config,
        enable_distributed_locking=enable_distributed_locking,
        enable_event_coordination=enable_event_coordination,
        enable_automatic_failover=enable_automatic_failover,
        enable_cluster_rebalancing=enable_cluster_rebalancing,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        debug_mode=bool(os.getenv("DEBUG_MODE", "false").lower() == "true"),
        trace_requests=bool(os.getenv("TRACE_REQUESTS", "false").lower() == "true")
    )

# Global configuration instance
distributed_config = load_distributed_config()

def get_distributed_config() -> DistributedOrchestratorConfig:
    """Get the global distributed orchestrator configuration"""
    return distributed_config

def validate_distributed_config(config: DistributedOrchestratorConfig) -> List[str]:
    """Validate distributed orchestrator configuration and return list of errors"""
    errors = []
    
    # Validate Redis configuration
    if not config.redis.url:
        errors.append("Redis URL is required")
    
    if config.redis.state_ttl <= 0:
        errors.append("Redis state TTL must be positive")
    
    # Validate Kafka configuration if event coordination is enabled
    if config.enable_event_coordination:
        if not config.kafka.bootstrap_servers:
            errors.append("Kafka bootstrap servers required for event coordination")
        
        if not config.kafka.coordination_topic:
            errors.append("Kafka coordination topic is required")
    
    # Validate leader election configuration
    if config.leader_election.enabled:
        if config.leader_election.leader_ttl <= 0:
            errors.append("Leader election TTL must be positive")
        
        if config.leader_election.election_interval <= 0:
            errors.append("Leader election interval must be positive")
    
    # Validate task assignment configuration
    if config.task_assignment.max_retry_attempts < 0:
        errors.append("Max retry attempts cannot be negative")
    
    if config.task_assignment.default_timeout <= 0:
        errors.append("Default task timeout must be positive")
    
    # Validate health monitoring configuration
    if config.health_monitoring.heartbeat_interval <= 0:
        errors.append("Heartbeat interval must be positive")
    
    if config.health_monitoring.instance_timeout <= config.health_monitoring.heartbeat_interval:
        errors.append("Instance timeout must be greater than heartbeat interval")
    
    # Validate port
    if not (1 <= config.port <= 65535):
        errors.append("Port must be between 1 and 65535")
    
    return errors

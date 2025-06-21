"""
Structured Configuration Management for Advanced RAG Service

This module provides centralized configuration management with:
- Environment-specific configuration loading
- Configuration validation and type safety
- Default values and overrides
- Integration with dependency injection
- Configuration hot-reloading capabilities
"""

import os
import logging
from typing import Optional, Dict, Any, Union, List
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json
import yaml
from pydantic import BaseModel, Field, validator, ValidationError

logger = logging.getLogger(__name__)

class Environment(str, Enum):
    """Supported deployment environments"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

class LogLevel(str, Enum):
    """Supported log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# Configuration Models using Pydantic for validation
class DatabaseConfig(BaseModel):
    """Database configuration settings"""
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    name: str = Field(default="surveillance", description="Database name")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="", description="Database password")
    ssl_mode: str = Field(default="prefer", description="SSL mode")
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, le=200, description="Max pool overflow")
    
    @validator('host')
    def validate_host(cls, v):
        if not v or not v.strip():
            raise ValueError('Database host cannot be empty')
        return v.strip()

class WeaviateConfig(BaseModel):
    """Weaviate configuration settings"""
    url: str = Field(default="http://localhost:8080", description="Weaviate URL")
    api_key: Optional[str] = Field(default=None, description="Weaviate API key")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    batch_size: int = Field(default=100, ge=1, le=1000, description="Batch size for operations")
    
    @validator('url')
    def validate_url(cls, v):
        if not v or not v.strip():
            raise ValueError('Weaviate URL cannot be empty')
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Weaviate URL must start with http:// or https://')
        return v.strip()

class OpenAIConfig(BaseModel):
    """OpenAI configuration settings"""
    api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    model: str = Field(default="gpt-3.5-turbo", description="OpenAI model to use")
    max_tokens: int = Field(default=800, ge=1, le=4000, description="Maximum tokens per response")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Response temperature")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if v and v not in ['your_openai_api_key_here', 'sk-dummy', 'sk-test'] and not v.startswith('sk-'):
            raise ValueError('OpenAI API key must start with sk- or be empty for development')
        return v

class EmbeddingConfig(BaseModel):
    """Embedding model configuration settings"""
    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model name"
    )
    cache_folder: Optional[str] = Field(default=None, description="Model cache folder")
    device: str = Field(default="cpu", description="Device to run model on (cpu/cuda)")
    max_seq_length: int = Field(default=512, ge=1, le=2048, description="Maximum sequence length")
    batch_size: int = Field(default=32, ge=1, le=256, description="Batch size for encoding")
    
    @validator('device')
    def validate_device(cls, v):
        if v not in ['cpu', 'cuda', 'auto']:
            raise ValueError('Device must be cpu, cuda, or auto')
        return v

class RedisConfig(BaseModel):
    """Redis configuration settings"""
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")
    timeout: int = Field(default=5, ge=1, le=60, description="Connection timeout")
    max_connections: int = Field(default=10, ge=1, le=100, description="Max connections in pool")
    
    @validator('host')
    def validate_host(cls, v):
        if not v or not v.strip():
            raise ValueError('Redis host cannot be empty')
        return v.strip()

class ServiceConfig(BaseModel):
    """Service-specific configuration settings"""
    host: str = Field(default="0.0.0.0", description="Service host")
    port: int = Field(default=8000, ge=1, le=65535, description="Service port")
    workers: int = Field(default=1, ge=1, le=32, description="Number of worker processes")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    debug: bool = Field(default=False, description="Enable debug mode")
    reload: bool = Field(default=False, description="Enable auto-reload")
    
    # RAG-specific settings
    max_context_length: int = Field(default=10, ge=1, le=50, description="Max context events")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
    temporal_window_hours: int = Field(default=24, ge=1, le=168, description="Temporal window in hours")
    
    @validator('host')
    def validate_host(cls, v):
        if not v or not v.strip():
            raise ValueError('Service host cannot be empty')
        return v.strip()

class SecurityConfig(BaseModel):
    """Security configuration settings"""
    secret_key: str = Field(default="", description="Secret key for signing")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440, description="Token expiry")
    enable_cors: bool = Field(default=True, description="Enable CORS")
    allowed_origins: List[str] = Field(default=["*"], description="Allowed CORS origins")
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000, description="Rate limit per minute")
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if not v or len(v) < 32:
            # Generate a default secret key for development
            import secrets
            return secrets.token_urlsafe(32)
        return v

class MonitoringConfig(BaseModel):
    """Monitoring and observability configuration"""
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=8001, ge=1, le=65535, description="Metrics server port")
    enable_tracing: bool = Field(default=False, description="Enable distributed tracing")
    jaeger_endpoint: Optional[str] = Field(default=None, description="Jaeger endpoint")
    health_check_interval: int = Field(default=30, ge=1, le=300, description="Health check interval")

class AdvancedRAGConfig(BaseModel):
    """Complete Advanced RAG Service configuration"""
    # Environment and basic settings
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Deployment environment")
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    weaviate: WeaviateConfig = Field(default_factory=WeaviateConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    # Global settings
    config_file: Optional[str] = Field(default=None, description="Configuration file path")
    config_reload_interval: int = Field(default=300, ge=0, le=3600, description="Config reload interval")
    
    class Config:
        env_prefix = "RAG_"
        env_nested_delimiter = "__"
        case_sensitive = False

class ConfigurationManager:
    """Centralized configuration management"""
    
    def __init__(self, config_file: Optional[str] = None, environment: Optional[str] = None):
        self.config_file = config_file
        self.environment = Environment(environment) if environment else Environment.DEVELOPMENT
        self._config: Optional[AdvancedRAGConfig] = None
        self._config_sources: List[str] = []
        
    def load_config(self) -> AdvancedRAGConfig:
        """Load configuration from multiple sources with precedence"""
        if self._config is not None:
            return self._config
            
        config_data = {}
        self._config_sources = []
          # 1. Load default configuration
        try:
            self._config = AdvancedRAGConfig()
            config_data = self._config.model_dump()
            self._config_sources.append("defaults")
        except ValidationError as e:
            logger.error(f"Invalid default configuration: {e}")
            raise
        
        # 2. Load from configuration file if specified
        if self.config_file:
            file_config = self._load_config_file(self.config_file)
            if file_config:
                config_data = self._merge_config(config_data, file_config)
                self._config_sources.append(f"file:{self.config_file}")
        
        # 3. Load environment-specific configuration
        env_config_file = f"config/{self.environment.value}.yml"
        if Path(env_config_file).exists():
            env_config = self._load_config_file(env_config_file)
            if env_config:
                config_data = self._merge_config(config_data, env_config)
                self._config_sources.append(f"env_file:{env_config_file}")
        
        # 4. Load from environment variables (highest precedence)
        env_config = self._load_from_environment()
        if env_config:
            config_data = self._merge_config(config_data, env_config)
            self._config_sources.append("environment")
        
        # 5. Apply environment-specific overrides
        config_data = self._apply_environment_overrides(config_data)
        
        # 6. Validate final configuration
        try:
            self._config = AdvancedRAGConfig(**config_data)
            self._config.environment = self.environment
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
        
        logger.info(f"Configuration loaded from sources: {', '.join(self._config_sources)}")
        return self._config
    
    def _load_config_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load configuration from file (JSON or YAML)"""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"Configuration file not found: {file_path}")
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yml', '.yaml']:
                    return yaml.safe_load(f) or {}
                elif path.suffix.lower() == '.json':
                    return json.load(f) or {}
                else:
                    logger.error(f"Unsupported configuration file format: {path.suffix}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error loading configuration file {file_path}: {e}")
            return None
    
    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        prefix = "RAG_"
        
        # Mapping of environment variables to config paths
        env_mappings = {
            # Database
            f"{prefix}DATABASE__HOST": "database.host",
            f"{prefix}DATABASE__PORT": "database.port",
            f"{prefix}DATABASE__NAME": "database.name",
            f"{prefix}DATABASE__USERNAME": "database.username",
            f"{prefix}DATABASE__PASSWORD": "database.password",
            
            # Weaviate
            f"{prefix}WEAVIATE__URL": "weaviate.url",
            f"{prefix}WEAVIATE__API_KEY": "weaviate.api_key",
            f"{prefix}WEAVIATE__TIMEOUT": "weaviate.timeout",
            
            # OpenAI
            f"{prefix}OPENAI__API_KEY": "openai.api_key",
            f"{prefix}OPENAI__MODEL": "openai.model",
            f"{prefix}OPENAI__MAX_TOKENS": "openai.max_tokens",
            
            # Embedding
            f"{prefix}EMBEDDING__MODEL_NAME": "embedding.model_name",
            f"{prefix}EMBEDDING__DEVICE": "embedding.device",
            
            # Redis
            f"{prefix}REDIS__HOST": "redis.host",
            f"{prefix}REDIS__PORT": "redis.port",
            f"{prefix}REDIS__PASSWORD": "redis.password",
            
            # Service
            f"{prefix}SERVICE__HOST": "service.host",
            f"{prefix}SERVICE__PORT": "service.port",
            f"{prefix}SERVICE__DEBUG": "service.debug",
            f"{prefix}SERVICE__LOG_LEVEL": "service.log_level",
            
            # Security
            f"{prefix}SECURITY__SECRET_KEY": "security.secret_key",
            f"{prefix}SECURITY__RATE_LIMIT_PER_MINUTE": "security.rate_limit_per_minute",
            
            # Backward compatibility with existing env vars
            "WEAVIATE_URL": "weaviate.url",
            "WEAVIATE_API_KEY": "weaviate.api_key",
            "OPENAI_API_KEY": "openai.api_key",
            "EMBEDDING_MODEL_NAME": "embedding.model_name",
            "REDIS_HOST": "redis.host",
            "REDIS_PORT": "redis.port",
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(config, config_path, value)
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], path: str, value: str):
        """Set a nested configuration value from dot notation path"""
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Type conversion
        final_key = keys[-1]
        if value.lower() in ['true', 'false']:
            current[final_key] = value.lower() == 'true'
        elif value.isdigit():
            current[final_key] = int(value)
        elif '.' in value and value.replace('.', '').isdigit():
            current[final_key] = float(value)
        else:
            current[final_key] = value
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge configuration dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_environment_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment-specific configuration overrides"""
        if self.environment == Environment.DEVELOPMENT:
            config.setdefault('service', {})
            config['service']['debug'] = True
            config['service']['reload'] = True
            config['service']['log_level'] = LogLevel.DEBUG
            
        elif self.environment == Environment.TESTING:
            config.setdefault('service', {})
            config['service']['debug'] = False
            config['service']['log_level'] = LogLevel.INFO
              # Use in-memory/mock services for testing
            config.setdefault('weaviate', {})
            config['weaviate']['url'] = 'http://localhost:8080'
            
        elif self.environment == Environment.PRODUCTION:
            config.setdefault('service', {})
            config['service']['debug'] = False
            config['service']['reload'] = False
            config['service']['log_level'] = LogLevel.WARNING
            
            config.setdefault('security', {})
            config['security']['enable_cors'] = False
            config['security']['allowed_origins'] = []
        
        return config
    
    def reload_config(self) -> AdvancedRAGConfig:
        """Reload configuration from sources"""
        self._config = None
        return self.load_config()
    
    def get_config(self) -> AdvancedRAGConfig:
        """Get current configuration"""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def validate_config(self) -> bool:
        """Validate current configuration"""
        try:
            self.get_config()
            return True
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration (excluding sensitive data)"""
        config = self.get_config()
        summary = config.model_dump()
        
        # Mask sensitive information
        sensitive_keys = ['password', 'api_key', 'secret_key']
        
        def mask_sensitive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        obj[key] = "***MASKED***" if value else None
                    else:
                        mask_sensitive(value, f"{path}.{key}" if path else key)
        
        mask_sensitive(summary)
        
        return {
            "config": summary,
            "sources": self._config_sources,
            "environment": self.environment.value,
            "valid": self.validate_config()
        }

# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None

def get_config_manager(config_file: Optional[str] = None, environment: Optional[str] = None) -> ConfigurationManager:
    """Get the global configuration manager"""
    global _config_manager
    if _config_manager is None:
        env = environment or os.getenv("RAG_ENVIRONMENT", "development")
        config_file = config_file or os.getenv("RAG_CONFIG_FILE")
        _config_manager = ConfigurationManager(config_file=config_file, environment=env)
    return _config_manager

def get_config() -> AdvancedRAGConfig:
    """Get the current configuration"""
    return get_config_manager().get_config()

def reload_config() -> AdvancedRAGConfig:
    """Reload configuration from sources"""
    return get_config_manager().reload_config()

def set_config_manager(manager: ConfigurationManager):
    """Set the global configuration manager (for testing)"""
    global _config_manager
    _config_manager = manager

def reset_config():
    """Reset the global configuration manager"""
    global _config_manager
    _config_manager = None

# Backward compatibility
@dataclass
class PerformanceMetrics:
    """Performance tracking metrics"""
    query_count: int = 0
    average_response_time: float = 0.0
    error_count: int = 0
    cache_hit_rate: float = 0.0

# Legacy config instance for backward compatibility
config = None

def get_legacy_config():
    """Get legacy config format for backward compatibility"""
    global config
    if config is None:
        modern_config = get_config()
        # Convert to legacy format if needed
        config = modern_config
    return config

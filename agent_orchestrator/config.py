"""
Configuration Management for Agent Orchestrator Service

This module provides centralized configuration management using environment variables
with sensible defaults for all service endpoints and operational parameters.

Features:
- Environment variable support with .env file loading
- Type validation and conversion
- Sensible defaults for all configurations
- Easy deployment across different environments
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class OrchestratorConfig(BaseSettings):
    """Main configuration class for the Agent Orchestrator Service"""
    
    # Service URLs
    redis_url: str = Field(
        default="redis://redis:6379/0",
        env="REDIS_URL",
        description="Redis connection URL for caching and queuing"
    )
    
    rag_service_url: str = Field(
        default="http://advanced_rag_service:8000",
        env="RAG_SERVICE_URL",
        description="Advanced RAG service endpoint URL"
    )
    
    rulegen_service_url: str = Field(
        default="http://rulegen_service:8000", 
        env="RULEGEN_SERVICE_URL",
        description="Rule generation service endpoint URL"
    )
    
    notifier_service_url: str = Field(
        default="http://notifier:8000",
        env="NOTIFIER_SERVICE_URL", 
        description="Notifier service endpoint URL"
    )
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost/surveillance",
        env="DATABASE_URL",
        description="PostgreSQL database connection URL"
    )
    
    # Service Configuration
    service_host: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="Host address to bind the service"
    )
    
    service_port: int = Field(
        default=8006,
        env="PORT", 
        description="Port number to bind the service"
    )
    
    # Retry Configuration
    max_retry_attempts: int = Field(
        default=3,
        env="MAX_RETRY_ATTEMPTS",
        description="Maximum number of retry attempts for service calls"
    )
    
    retry_base_delay: float = Field(
        default=0.5,
        env="RETRY_BASE_DELAY",
        description="Base delay in seconds for exponential backoff"
    )
    
    retry_max_delay: float = Field(
        default=10.0,
        env="RETRY_MAX_DELAY", 
        description="Maximum delay in seconds for exponential backoff"
    )
    
    retry_multiplier: float = Field(
        default=2.0,
        env="RETRY_MULTIPLIER",
        description="Multiplier for exponential backoff"
    )
    
    # HTTP Client Configuration
    http_timeout: float = Field(
        default=30.0,
        env="HTTP_TIMEOUT",
        description="HTTP client timeout in seconds"
    )
    
    # Background Task Configuration
    notification_retry_interval: int = Field(
        default=60,
        env="NOTIFICATION_RETRY_INTERVAL",
        description="Interval in seconds between notification retry attempts"
    )
    
    max_notification_retries: int = Field(
        default=5,
        env="MAX_NOTIFICATION_RETRIES",
        description="Maximum number of notification retry attempts"
    )
    
    # Task Processing Configuration
    task_queue_check_interval: float = Field(
        default=1.0,
        env="TASK_QUEUE_CHECK_INTERVAL",
        description="Interval in seconds for checking task queue"
    )
    
    agent_retry_delay: int = Field(
        default=5,
        env="AGENT_RETRY_DELAY",
        description="Delay in seconds before retrying agent assignment"
    )    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["*"],
        env="CORS_ORIGINS",
        description="Allowed CORS origins (comma-separated)"
    )
    
    cors_allow_credentials: bool = Field(
        default=True,
        env="CORS_ALLOW_CREDENTIALS",
        description="Allow credentials in CORS requests"
    )    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string"""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v if isinstance(v, list) else [str(v)]
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT",
        description="Logging format string"
    )
    
    # Security Configuration
    enable_rate_limiting: bool = Field(
        default=True,
        env="ENABLE_RATE_LIMITING",
        description="Enable rate limiting middleware"
    )
    
    api_key: Optional[str] = Field(
        default=None,
        env="API_KEY",
        description="API key for service authentication (if required)"
    )
    
    # Development/Debug Configuration
    debug_mode: bool = Field(
        default=False,
        env="DEBUG_MODE",
        description="Enable debug mode for development"
    )
    
    enable_docs: bool = Field(
        default=True,
        env="ENABLE_DOCS",
        description="Enable FastAPI auto-generated documentation"
    )
    
    # Health Check Configuration
    health_check_interval: int = Field(
        default=30,
        env="HEALTH_CHECK_INTERVAL",
        description="Health check interval in seconds"
    )
    
    health_check_timeout: int = Field(
        default=10,
        env="HEALTH_CHECK_TIMEOUT",
        description="Health check timeout in seconds"
    )    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    @field_validator('service_port')
    @classmethod
    def validate_port(cls, v):
        """Validate port number"""
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    @field_validator('max_retry_attempts')
    @classmethod
    def validate_retry_attempts(cls, v):
        """Validate retry attempts"""
        if v < 1:
            raise ValueError('Max retry attempts must be at least 1')
        return v
    
    @field_validator('http_timeout', 'retry_base_delay', 'retry_max_delay')
    @classmethod
    def validate_positive_float(cls, v):
        """Validate positive float values"""
        if v <= 0:
            raise ValueError('Value must be positive')
        return v
    
    model_config = {
        'env_file': '.env',
        'env_file_encoding': 'utf-8',
        'case_sensitive': False,
        'validate_assignment': True,
        'extra': 'forbid'
    }


# Global configuration instance
config = OrchestratorConfig()


def get_config() -> OrchestratorConfig:
    """Get the global configuration instance"""
    return config


def reload_config() -> OrchestratorConfig:
    """Reload configuration (useful for testing or dynamic config updates)"""
    global config
    config = OrchestratorConfig()
    return config


# Configuration validation function
def validate_config():
    """Validate the current configuration and log important settings"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Agent Orchestrator Configuration:")
    logger.info(f"  Service: {config.service_host}:{config.service_port}")
    logger.info(f"  Redis: {config.redis_url}")
    logger.info(f"  RAG Service: {config.rag_service_url}")
    logger.info(f"  Rule Gen Service: {config.rulegen_service_url}")
    logger.info(f"  Notifier Service: {config.notifier_service_url}")
    logger.info(f"  Database: {config.database_url}")
    logger.info(f"  Log Level: {config.log_level}")
    logger.info(f"  Debug Mode: {config.debug_mode}")
    logger.info(f"  Rate Limiting: {config.enable_rate_limiting}")
    
    # Validate critical URLs
    critical_urls = [
        config.redis_url,
        config.rag_service_url, 
        config.rulegen_service_url,
        config.notifier_service_url
    ]
    
    for url in critical_urls:
        if not url or not url.startswith(('http://', 'https://', 'redis://')):
            logger.warning(f"Invalid or missing URL: {url}")
    
    return True


# Environment-specific configuration helpers
def is_development() -> bool:
    """Check if running in development environment"""
    return config.debug_mode or os.getenv('ENVIRONMENT', '').lower() in ['dev', 'development', 'local']


def is_production() -> bool:
    """Check if running in production environment"""
    return os.getenv('ENVIRONMENT', '').lower() in ['prod', 'production']


def is_testing() -> bool:
    """Check if running in testing environment"""
    return os.getenv('ENVIRONMENT', '').lower() in ['test', 'testing']

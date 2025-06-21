from pydantic_settings import BaseSettings
from pydantic import Field
import os

class Settings(BaseSettings):
    # API Configuration - Enhanced for consistent versioning strategy
    API_BASE_URL: str = Field(default="http://localhost:8000", description="Base URL for API calls")
    API_BASE_PATH: str = Field(default="/api/v1", description="Base path for API versioning strategy")
    API_VERSION: str = Field(default="v1", description="Current API version")
    
    # WebSocket Configuration - Aligned with API versioning
    WS_BASE_PATH: str = Field(default="/ws/v1", description="Base path for WebSocket versioning strategy")
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="kafka:9092", description="Kafka bootstrap servers")
    JWT_SECRET_KEY: str = Field(default=os.getenv("JWT_SECRET_KEY", "change-me-in-production"), description="JWT secret key for authentication")
    
    # Encryption configuration
    ENCRYPTION_KEY: str = Field(
        default=os.getenv("ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"), 
        description="32-byte hex string for AES-256 encryption"
    )
    
    ANNOTATION_PAGE_SIZE: int = Field(default=50, description="Number of examples to show per page")
    HOST: str = Field(default="0.0.0.0", description="Host to bind the server to")
    PORT: int = Field(default=8000, description="Port to bind the server to")    # Additional Kafka configuration
    KAFKA_GROUP_ID: str = Field(default="annotation-frontend-group", description="Kafka consumer group ID for load balancing")
    SERVICE_NAME: str = Field(default="annotation-frontend", description="Service name for client identification")
    HARD_EXAMPLES_TOPIC: str = Field(default="hard-examples", description="Topic for hard examples")
    LABELED_EXAMPLES_TOPIC: str = Field(default="labeled-examples", description="Topic for labeled examples")
    
    # Kafka performance settings
    KAFKA_LINGER_MS: int = Field(default=100, description="Kafka producer linger time in ms")
    KAFKA_BATCH_SIZE: int = Field(default=32, description="Kafka producer batch size")
    KAFKA_COMPRESSION_TYPE: str = Field(default="snappy", description="Kafka compression type")
    
    # Redis configuration
    REDIS_URL: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    REDIS_PASSWORD: str = Field(default="", description="Redis password")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    RETRY_QUEUE_KEY: str = Field(default="annotation:retry_queue", description="Redis key for retry queue")
    
    # Retry configuration
    MAX_RETRY_ATTEMPTS: int = Field(default=5, description="Maximum retry attempts")
    RETRY_INTERVAL_SECONDS: int = Field(default=30, description="Retry interval in seconds")
      # Static asset caching
    STATIC_CACHE_MAX_AGE: int = Field(default=86400, description="Static file cache max age in seconds")
      # CSRF Protection
    CSRF_SECRET_KEY: str = Field(default=os.getenv("CSRF_SECRET_KEY", "csrf-secret-change-me"), description="CSRF secret key")
    CSRF_TOKEN_EXPIRES: int = Field(default=3600, description="CSRF token expiration time in seconds")

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra environment variables

settings = Settings()
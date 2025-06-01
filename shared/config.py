"""
Configuration management for all services.
"""
import os
from typing import Dict, Any
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    database_url: str = "postgresql://user:password@postgres:5432/events_db"
    
    # Redis
    redis_url: str = "redis://redis:6379/0"
    
    # Kafka
    kafka_broker: str = "kafka:9092"
    kafka_topic: str = "camera.events"
    
    # MQTT
    mqtt_broker: str = "mqtt.example.com"
    mqtt_port: int = 8883
    mqtt_tls_ca: str = "/certs/ca.crt"
    mqtt_tls_cert: str = "/certs/client.crt"
    mqtt_tls_key: str = "/certs/client.key"
    
    # Weaviate
    weaviate_url: str = "http://weaviate:8080"
    weaviate_api_key: str = ""
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    
    # Authentication
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Video Storage
    video_storage_type: str = "local"  # "local" or "s3"
    s3_bucket_name: str = "surveillance-clips"
    aws_region: str = "us-east-1"
    local_storage_path: str = "/data/clips"
    clip_base_url: str = "http://localhost:8000/clips"
    
    # Notification Channels
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = ""
    slack_webhook_url: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    webhook_url: str = ""
    webhook_secret: str = ""
    
    # Monitoring
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    grafana_enabled: bool = True
    grafana_port: int = 3000
    
    # Service URLs
    edge_service_url: str = "http://edge_service:8000"
    ingest_service_url: str = "http://ingest_service:8000"
    rag_service_url: str = "http://rag_service:8000"
    prompt_service_url: str = "http://prompt_service:8000"
    rulegen_service_url: str = "http://rulegen_service:8000"
    notifier_service_url: str = "http://notifier:8000"
    vms_service_url: str = "http://vms_service:8000"
    mqtt_kafka_bridge_url: str = "http://mqtt_kafka_bridge:8000"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

def get_service_config(service_name: str) -> Dict[str, Any]:
    """Get configuration specific to a service."""
    configs = {
        "edge_service": {
            "camera_id": os.getenv("CAMERA_ID", "camera-01"),
            "capture_device": int(os.getenv("CAPTURE_DEVICE", "0")),
            "model_dir": os.getenv("MODEL_DIR", "/models"),
            "target_resolution": tuple(map(int, os.getenv("TARGET_RESOLUTION", "224,224").split(","))),
            "mqtt_broker": settings.mqtt_broker,
            "mqtt_port": settings.mqtt_port,
        },
        "ingest_service": {
            "database_url": settings.database_url,
            "kafka_broker": settings.kafka_broker,
            "kafka_topic": settings.kafka_topic,
            "group_id": os.getenv("GROUP_ID", "ingest-service-group"),
            "weaviate_url": settings.weaviate_url,
            "weaviate_api_key": settings.weaviate_api_key,
        },
        "rag_service": {
            "weaviate_url": settings.weaviate_url,
            "weaviate_api_key": settings.weaviate_api_key,
            "openai_api_key": settings.openai_api_key,
            "openai_model": settings.openai_model,
        },
        "prompt_service": {
            "weaviate_url": settings.weaviate_url,
            "weaviate_api_key": settings.weaviate_api_key,
            "clip_base_url": settings.clip_base_url,
        },
        "rulegen_service": {
            "database_url": settings.database_url,
            "openai_api_key": settings.openai_api_key,
            "openai_model": settings.openai_model,
            "jwt_secret_key": settings.jwt_secret_key,
        },
        "notifier": {
            "database_url": settings.database_url,
            "smtp_server": settings.smtp_server,
            "smtp_port": settings.smtp_port,
            "smtp_username": settings.smtp_username,
            "smtp_password": settings.smtp_password,
            "from_email": settings.from_email,
            "slack_webhook_url": settings.slack_webhook_url,
            "twilio_account_sid": settings.twilio_account_sid,
            "twilio_auth_token": settings.twilio_auth_token,
            "twilio_from_number": settings.twilio_from_number,
            "webhook_url": settings.webhook_url,
            "webhook_secret": settings.webhook_secret,
        },
        "vms_service": {
            "video_storage_type": settings.video_storage_type,
            "s3_bucket_name": settings.s3_bucket_name,
            "aws_region": settings.aws_region,
            "local_storage_path": settings.local_storage_path,
            "clip_base_url": settings.clip_base_url,
            "clip_duration_seconds": int(os.getenv("CLIP_DURATION_SECONDS", "30")),
            "pre_event_buffer_seconds": int(os.getenv("PRE_EVENT_BUFFER_SECONDS", "10")),
            "post_event_buffer_seconds": int(os.getenv("POST_EVENT_BUFFER_SECONDS", "20")),
            "clip_fps": int(os.getenv("CLIP_FPS", "15")),
            "clip_resolution": os.getenv("CLIP_RESOLUTION", "640,480"),
        },
        "mqtt_kafka_bridge": {
            "mqtt_broker": settings.mqtt_broker,
            "mqtt_port": settings.mqtt_port,
            "mqtt_tls_ca": settings.mqtt_tls_ca,
            "mqtt_tls_cert": settings.mqtt_tls_cert,
            "mqtt_tls_key": settings.mqtt_tls_key,
            "mqtt_topic_sub": os.getenv("MQTT_TOPIC_SUB", "camera/events/#"),
            "kafka_broker": settings.kafka_broker,
            "kafka_topic": settings.kafka_topic,
        },
    }
    
    return configs.get(service_name, {})
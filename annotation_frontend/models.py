"""
Database models for the Annotation Frontend Service.
"""
import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Enum, Text, TypeDecorator, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Dict, Any
import base64
import json
import logging

# Use shared encrypted field types instead of local ones
from shared.encrypted_fields import EncryptedType, EncryptedJSONType, EncryptedBase64Type

logger = logging.getLogger(__name__)

Base = declarative_base()


class AnnotationStatus(str, enum.Enum):
    """Status of an annotation example."""
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    RETRY = "retry"


class AnnotationExample(Base):
    """Model for annotation examples with encrypted sensitive fields."""
    __tablename__ = "annotation_examples"
    
    id = Column(Integer, primary_key=True, index=True)
    example_id = Column(String(255), unique=True, index=True, nullable=False)
    camera_id = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    # Encrypted fields for sensitive data
    frame_data = Column(EncryptedBase64Type, nullable=True)  # Encrypted base64 frame data
    original_detections = Column(EncryptedJSONType, nullable=True)  # Encrypted detection data
    confidence_scores = Column(EncryptedJSONType, nullable=True)  # Encrypted confidence data
    bbox = Column(EncryptedJSONType, nullable=True)  # Encrypted bounding box coordinates
    label = Column(EncryptedType, nullable=True)  # Encrypted labels (potentially sensitive)
    notes = Column(EncryptedType, nullable=True)  # Encrypted notes (may contain PII)
    
    # Non-encrypted metadata fields
    reason = Column(String(500), nullable=True)
    status = Column(Enum(AnnotationStatus), default=AnnotationStatus.PENDING, nullable=False)
    annotator_id = Column(String(255), nullable=True)
    quality_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class RetryQueue(Base):
    """Model for failed Kafka messages that need retry."""
    __tablename__ = "retry_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    example_id = Column(String(255), nullable=False)
    topic = Column(String(255), nullable=False)
    key = Column(String(255), nullable=True)
    
    # Encrypt sensitive payload data
    payload = Column(EncryptedType, nullable=False)  # Encrypted JSON string
    
    attempts = Column(Integer, default=0, nullable=False)
    last_attempt = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    error_message = Column(Text, nullable=True)  # Error messages are not sensitive

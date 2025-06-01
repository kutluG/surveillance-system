"""
SQLAlchemy ORM model for tracking notification history.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, JSON, Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum

Base = declarative_base()

class NotificationStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"

class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,    )
    channel = Column(String(50), nullable=False)
    recipients = Column(JSON, nullable=False)  # List of recipient addresses
    subject = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    notification_metadata = Column(JSON, nullable=True)
    status = Column(PgEnum(NotificationStatus, name="notification_status"), nullable=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    retry_count = Column(String, default=0)
    rule_id = Column(String, nullable=True)  # ID of the rule that triggered this
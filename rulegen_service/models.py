"""
SQLAlchemy ORM model for storing policy rules.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class PolicyRule(Base):
    __tablename__ = "policy_rules"

    id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    rule_text = Column(Text, nullable=False)  # Natural language rule
    conditions = Column(Text, nullable=False)  # JSON string of conditions
    actions = Column(Text, nullable=False)     # JSON string of actions
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
"""
SQLAlchemy models for Agent Orchestrator Service

This module defines the database models for persistent storage of agents, tasks,
workflows, and orchestration data. These models work with the dependency injection
system in database.py to provide robust data persistence.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, JSON, ForeignKey, Enum, Float
from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class AgentTypeEnum(enum.Enum):
    """Agent type enumeration for database storage"""
    PROMPT_AGENT = "prompt_agent"
    RAG_AGENT = "rag_agent"
    RULE_AGENT = "rule_agent"
    ANALYSIS_AGENT = "analysis_agent"
    NOTIFICATION_AGENT = "notification_agent"


class TaskStatusEnum(enum.Enum):
    """Task status enumeration for database storage"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStatusEnum(enum.Enum):
    """Workflow status enumeration for database storage"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class Agent(Base):
    """
    Database model for AI agents in the orchestration system
    """
    __tablename__ = "agents"
    
    id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    type = Column(Enum(AgentTypeEnum), nullable=False)
    name = Column(String(255), nullable=False)
    endpoint = Column(String(500), nullable=False)
    capabilities = Column(JSONB, nullable=False, default=list)
    status = Column(String(50), nullable=False, default="idle")
    last_seen = Column(DateTime, nullable=True)
    current_task_id = Column(PgUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    performance_metrics = Column(JSONB, nullable=True, default=dict)
    metadata = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    tasks = relationship("Task", back_populates="assigned_agent", foreign_keys="Task.assigned_agent_id")
    current_task = relationship("Task", foreign_keys=[current_task_id])
    
    def __repr__(self):
        return f"<Agent(id={self.id}, name='{self.name}', type='{self.type}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "type": self.type.value if self.type else None,
            "name": self.name,
            "endpoint": self.endpoint,
            "capabilities": self.capabilities,
            "status": self.status,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "current_task_id": str(self.current_task_id) if self.current_task_id else None,
            "performance_metrics": self.performance_metrics,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active
        }


class Task(Base):
    """
    Database model for tasks in the orchestration system
    """
    __tablename__ = "tasks"
    
    id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    type = Column(String(100), nullable=False)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    input_data = Column(JSONB, nullable=False, default=dict)
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    status = Column(Enum(TaskStatusEnum), nullable=False, default=TaskStatusEnum.PENDING)
    priority = Column(Integer, nullable=False, default=1)
    required_capabilities = Column(JSONB, nullable=False, default=list)
    assigned_agent_id = Column(PgUUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    workflow_id = Column(PgUUID(as_uuid=True), ForeignKey("workflows.id"), nullable=True)
    parent_task_id = Column(PgUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    dependencies = Column(JSONB, nullable=False, default=list)  # List of task IDs
    metadata = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    timeout_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Relationships
    assigned_agent = relationship("Agent", back_populates="tasks", foreign_keys=[assigned_agent_id])
    workflow = relationship("Workflow", back_populates="tasks")
    parent_task = relationship("Task", remote_side=[id])
    child_tasks = relationship("Task", remote_side=[parent_task_id])
    
    def __repr__(self):
        return f"<Task(id={self.id}, type='{self.type}', status='{self.status}', priority={self.priority})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "input_data": self.input_data,
            "result": self.result,
            "error_message": self.error_message,
            "status": self.status.value if self.status else None,
            "priority": self.priority,
            "required_capabilities": self.required_capabilities,
            "assigned_agent_id": str(self.assigned_agent_id) if self.assigned_agent_id else None,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "parent_task_id": str(self.parent_task_id) if self.parent_task_id else None,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "timeout_at": self.timeout_at.isoformat() if self.timeout_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }


class Workflow(Base):
    """
    Database model for workflows in the orchestration system
    """
    __tablename__ = "workflows"
    
    id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    user_id = Column(String(255), nullable=False)
    status = Column(Enum(WorkflowStatusEnum), nullable=False, default=WorkflowStatusEnum.PENDING)
    configuration = Column(JSONB, nullable=False, default=dict)
    metadata = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    timeout_at = Column(DateTime, nullable=True)
    priority = Column(Integer, nullable=False, default=1)
    estimated_duration = Column(Integer, nullable=True)  # in seconds
    actual_duration = Column(Float, nullable=True)  # in seconds
    
    # Relationships
    tasks = relationship("Task", back_populates="workflow", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Workflow(id={self.id}, name='{self.name}', status='{self.status}', user_id='{self.user_id}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "status": self.status.value if self.status else None,
            "configuration": self.configuration,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "timeout_at": self.timeout_at.isoformat() if self.timeout_at else None,
            "priority": self.priority,
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "task_count": len(self.tasks) if self.tasks else 0
        }


class OrchestrationLog(Base):
    """
    Database model for orchestration operation logs
    """
    __tablename__ = "orchestration_logs"
    
    id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    operation_type = Column(String(100), nullable=False)  # e.g., 'agent_registration', 'task_execution', 'workflow_orchestration'
    entity_type = Column(String(50), nullable=False)  # e.g., 'agent', 'task', 'workflow'
    entity_id = Column(PgUUID(as_uuid=True), nullable=True)
    status = Column(String(50), nullable=False)  # e.g., 'success', 'failure', 'partial'
    message = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True, default=dict)
    user_id = Column(String(255), nullable=True)
    duration = Column(Float, nullable=True)  # operation duration in seconds
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<OrchestrationLog(id={self.id}, operation='{self.operation_type}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "operation_type": self.operation_type,
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id) if self.entity_id else None,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "user_id": self.user_id,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class ServiceHealth(Base):
    """
    Database model for tracking service health status
    """
    __tablename__ = "service_health"
    
    id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    service_name = Column(String(100), unique=True, nullable=False)
    status = Column(String(50), nullable=False)  # healthy, degraded, unhealthy
    last_check = Column(DateTime, default=datetime.utcnow, nullable=False)
    response_time = Column(Float, nullable=True)  # in seconds
    error_count = Column(Integer, default=0, nullable=False)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    details = Column(JSONB, nullable=True, default=dict)
    
    def __repr__(self):
        return f"<ServiceHealth(service='{self.service_name}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert service health to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "service_name": self.service_name,
            "status": self.status,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "response_time": self.response_time,
            "error_count": self.error_count,
            "consecutive_failures": self.consecutive_failures,
            "details": self.details
        }

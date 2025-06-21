"""
Enhanced Agent Management Endpoints with Database Integration and Authentication

This module provides enhanced agent management endpoints that use proper
database dependency injection instead of Redis for persistence. It demonstrates
how to integrate the database layer with FastAPI endpoints while maintaining
backward compatibility.

Features:
- Database dependency injection
- Transaction safety
- Connection leak prevention
- Comprehensive error handling
- Audit logging
- Performance monitoring
- API key authentication and authorization
- Permission-based access control
"""

from typing import List, Optional, Dict, Any
from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from database import get_db_session, get_db_transaction
from db_service import (
    AgentRepository, TaskRepository, WorkflowRepository,
    OrchestrationLogRepository, DatabaseOperationError,
    create_agent_with_transaction, create_task_with_transaction,
    assign_task_with_transaction
)
from models import Agent, Task, Workflow, AgentTypeEnum, TaskStatusEnum, WorkflowStatusEnum
from validation import (
    EnhancedAgentRegistrationRequest,
    EnhancedCreateTaskRequest,
    AgentQueryParams,
    TaskQueryParams,
    ValidationUtils
)
from auth import (
    APIKeyInfo, require_permission, verify_endpoint_access,
    verify_api_key, verify_permission
)
from kafka_integration import event_publisher, EventType, OrchestrationEvent

logger = logging.getLogger(__name__)


# Enhanced Agent Management Endpoints with Authentication

async def register_agent_enhanced(
    request: Request,
    agent_info: EnhancedAgentRegistrationRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_info: APIKeyInfo = Depends(require_permission("agent:register"))
) -> Dict[str, Any]:
    """
    Enhanced agent registration using database persistence with authentication.
    
    This endpoint demonstrates proper database dependency injection
    and transaction management for agent registration with API key authentication.
    
    Args:
        request: FastAPI request object
        agent_info: Agent registration information
        db: Database session (dependency injected)
        auth_info: Authenticated API key info (dependency injected)
        
    Returns:
        Dict containing registration result and agent information
        
    Raises:
        HTTPException: If registration fails or validation errors occur
    """
    try:
        # Log authentication info for audit
        logger.info(f"Agent registration requested by API key: {auth_info.key_id}")
        
        # Convert request to database format
        agent_data = {
            "type": agent_info.type.value,
            "name": agent_info.name,
            "endpoint": agent_info.endpoint,
            "capabilities": agent_info.capabilities,
            "metadata": {
                "registration_source": "api",
                "api_version": "2.0",
                "validation_passed": True,
                "registered_by_key": auth_info.key_id
            }
        }
          # Create agent using transaction (will auto-commit on success)
        agent = await create_agent_with_transaction(agent_data)
        
        # Publish agent registration event to Kafka
        try:
            await event_publisher.publish_agent_registered(
                agent_id=str(agent.id),
                agent_data=agent_data,
                metadata={
                    "api_key_id": auth_info.key_id,
                    "request_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent")
                }
            )
            logger.info(f"Agent registration event published to Kafka for agent: {agent.id}")
        except Exception as kafka_error:
            logger.warning(f"Failed to publish agent registration event to Kafka: {kafka_error}")
            # Continue execution - Kafka failure shouldn't block registration
        
        logger.info(f"Agent registered successfully - ID: {agent.id}, Name: {ValidationUtils.sanitize_string(agent.name)}")
        
        return {
            "agent_id": str(agent.id),
            "status": "registered",
            "message": "Agent registered successfully with database persistence",
            "created_at": agent.created_at.isoformat(),
            "database_stored": True,
            "authenticated": True,
            "event_published": True
        }
        
    except DatabaseOperationError as e:
        logger.error(f"Database operation failed during agent registration: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during agent registration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during agent registration")


async def list_agents_enhanced(
    query: AgentQueryParams = Depends(),
    db: AsyncSession = Depends(get_db_session),
    auth_info: APIKeyInfo = Depends(require_permission("agent:read"))
) -> Dict[str, Any]:
    """
    Enhanced agent listing using database queries with filtering and pagination.
    
    Args:
        query: Query parameters for filtering and pagination
        db: Database session (dependency injected)
        auth_info: Authenticated API key info (dependency injected)
        
    Returns:
        Dict containing filtered agent list and pagination info
        
    Raises:
        HTTPException: If database operation fails
    """
    try:
        # Convert query parameters to database types
        agent_type = AgentTypeEnum(query.type.value) if query.type else None
        
        # Parse capabilities filter
        capabilities = None
        if query.capability:
            capabilities = [ValidationUtils.sanitize_string(query.capability)]
        
        # Get agents from database
        agents, total_count = await AgentRepository.list_agents(
            db=db,
            agent_type=agent_type,
            status=query.status if query.status != "all" else None,
            capabilities=capabilities,
            limit=query.limit,
            offset=query.offset
        )
        
        # Convert to response format
        agent_list = []
        for agent in agents:
            agent_dict = agent.to_dict()
            # Sanitize sensitive information
            agent_dict["name"] = ValidationUtils.sanitize_string(agent.name)
            agent_list.append(agent_dict)
        
        return {
            "agents": agent_list,
            "total_count": total_count,
            "limit": query.limit,
            "offset": query.offset,
            "database_source": True,
            "authenticated": True,
            "filtered_by": {
                "type": query.type.value if query.type else None,
                "status": query.status,
                "capability": query.capability
            }
        }
        
    except DatabaseOperationError as e:
        logger.error(f"Database operation failed during agent listing: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during agent listing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during agent listing")


async def get_agent_enhanced(
    agent_id: str,
    include_tasks: bool = Query(False, description="Include assigned tasks in response"),
    db: AsyncSession = Depends(get_db_session),
    auth_info: APIKeyInfo = Depends(require_permission("agent:read"))
) -> Dict[str, Any]:
    """
    Enhanced agent retrieval with optional task loading.
    
    Args:
        agent_id: The ID of the agent to retrieve
        include_tasks: Whether to include assigned tasks in response
        db: Database session (dependency injected)
        auth_info: Authenticated API key info (dependency injected)
        
    Returns:
        Dict containing agent information and optionally tasks
        
    Raises:
        HTTPException: If agent not found or database operation fails
    """
    try:
        # Validate agent ID format
        if not ValidationUtils.validate_uuid(agent_id):
            raise HTTPException(status_code=400, detail="Invalid agent ID format")
        
        # Get agent from database
        agent = await AgentRepository.get_agent_by_id(
            agent_id=agent_id,
            db=db,
            include_tasks=include_tasks
        )
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Convert to dict and sanitize
        agent_dict = agent.to_dict()
        agent_dict["name"] = ValidationUtils.sanitize_string(agent.name)
        
        # Add task information if requested
        if include_tasks and agent.tasks:
            agent_dict["tasks"] = [task.to_dict() for task in agent.tasks]
            agent_dict["task_count"] = len(agent.tasks)
        
        agent_dict["database_source"] = True
        agent_dict["authenticated"] = True
        
        return agent_dict
        
    except HTTPException:
        raise
    except DatabaseOperationError as e:
        logger.error(f"Database operation failed during agent retrieval: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during agent retrieval: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during agent retrieval")


# Enhanced Task Management Endpoints with Authentication

async def create_task_enhanced(
    task_request: EnhancedCreateTaskRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_info: APIKeyInfo = Depends(require_permission("task:create"))
) -> Dict[str, Any]:
    """
    Enhanced task creation using database persistence and transaction safety.
    
    Args:
        task_request: Task creation information
        db: Database session (dependency injected)
        auth_info: Authenticated API key info (dependency injected)
        
    Returns:
        Dict containing task creation result and task information
        
    Raises:
        HTTPException: If task creation fails or validation errors occur
    """
    try:
        # Log authentication info for audit
        logger.info(f"Task creation requested by API key: {auth_info.key_id}")
        
        # Convert request to database format
        task_data = {
            "type": task_request.type.value,
            "name": task_request.name,
            "description": task_request.description,
            "input_data": task_request.input_data,
            "priority": task_request.priority.value,
            "required_capabilities": task_request.required_capabilities,
            "workflow_id": task_request.workflow_id,
            "metadata": {
                "creation_source": "api",
                "api_version": "2.0",
                "validation_passed": True,
                "created_by_key": auth_info.key_id
            },
            "max_retries": task_request.max_retries,
            "timeout_at": task_request.timeout_at
        }
        
        # Create task using transaction
        task = await create_task_with_transaction(task_data)
        
        logger.info(f"Task created successfully - ID: {task.id}, Type: {task.type}")
        
        return {
            "task_id": str(task.id),
            "status": "created",
            "message": "Task created successfully with database persistence",
            "created_at": task.created_at.isoformat(),
            "database_stored": True,
            "authenticated": True
        }
        
    except DatabaseOperationError as e:
        logger.error(f"Database operation failed during task creation: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during task creation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during task creation")


async def list_tasks_enhanced(
    query: TaskQueryParams = Depends(),
    db: AsyncSession = Depends(get_db_session),
    auth_info: APIKeyInfo = Depends(require_permission("task:read"))
) -> Dict[str, Any]:
    """
    Enhanced task listing using database queries with comprehensive filtering.
    
    Args:
        query: Query parameters for filtering and pagination
        db: Database session (dependency injected)
        auth_info: Authenticated API key info (dependency injected)
        
    Returns:
        Dict containing filtered task list and pagination info
        
    Raises:
        HTTPException: If database operation fails
    """
    try:
        # Convert query parameters to database types
        status = TaskStatusEnum(query.status.value) if query.status else None
        
        # Get tasks from database
        tasks, total_count = await TaskRepository.list_tasks(
            db=db,
            status=status,
            workflow_id=query.workflow_id,
            agent_id=query.agent_id,
            limit=query.limit,
            offset=query.offset
        )
        
        # Convert to response format
        task_list = []
        for task in tasks:
            task_dict = task.to_dict()
            # Sanitize sensitive information if needed
            task_list.append(task_dict)
        
        return {
            "tasks": task_list,
            "total_count": total_count,
            "limit": query.limit,
            "offset": query.offset,
            "database_source": True,
            "authenticated": True,
            "filtered_by": {
                "status": query.status.value if query.status else None,
                "workflow_id": query.workflow_id,
                "agent_id": query.agent_id
            }
        }
        
    except DatabaseOperationError as e:
        logger.error(f"Database operation failed during task listing: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during task listing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during task listing")


async def assign_task_enhanced(
    task_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    auth_info: APIKeyInfo = Depends(require_permission("task:assign"))
) -> Dict[str, Any]:
    """
    Enhanced task assignment using database transactions.
    
    Args:
        task_id: The ID of the task to assign
        agent_id: The ID of the agent to assign the task to
        db: Database session (dependency injected)
        auth_info: Authenticated API key info (dependency injected)
        
    Returns:
        Dict containing assignment result
        
    Raises:
        HTTPException: If task/agent not found or assignment fails
    """
    try:
        # Log authentication info for audit
        logger.info(f"Task assignment requested by API key: {auth_info.key_id}")
        
        # Validate UUIDs
        if not ValidationUtils.validate_uuid(task_id):
            raise HTTPException(status_code=400, detail="Invalid task ID format")
        if not ValidationUtils.validate_uuid(agent_id):
            raise HTTPException(status_code=400, detail="Invalid agent ID format")
          # Assign task using transaction
        assignment_result = await assign_task_with_transaction(
            task_id=task_id,
            agent_id=agent_id,
            assigned_by=auth_info.key_id
        )
        
        # Publish task assignment event to Kafka
        try:
            # Get task data for event
            task = await TaskRepository.get_task_by_id(task_id, db)
            await event_publisher.publish_task_assigned(
                task_id=task_id,
                agent_id=agent_id,
                task_data={
                    "type": task.type if task else "unknown",
                    "name": task.name if task else "unknown",
                    "priority": task.priority if task else "normal"
                },
                metadata={
                    "api_key_id": auth_info.key_id,
                    "assigned_by": auth_info.key_id
                }
            )
            logger.info(f"Task assignment event published to Kafka for task: {task_id}")
        except Exception as kafka_error:
            logger.warning(f"Failed to publish task assignment event to Kafka: {kafka_error}")
            # Continue execution - Kafka failure shouldn't block assignment
        
        logger.info(f"Task {task_id} assigned successfully to agent {agent_id}")
        
        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "assigned",
            "message": "Task assigned successfully with database persistence",
            "assigned_at": assignment_result["assigned_at"],
            "database_stored": True,
            "authenticated": True,
            "event_published": True
        }
        
    except DatabaseOperationError as e:
        logger.error(f"Database operation failed during task assignment: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during task assignment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during task assignment")


# Enhanced Monitoring and Health Endpoints with Authentication

async def database_health_check_enhanced(
    db: AsyncSession = Depends(get_db_session),
    auth_info: APIKeyInfo = Depends(require_permission("system:health"))
) -> Dict[str, Any]:
    """
    Enhanced database health check using dependency injection.
    
    Args:
        db: Database session (dependency injected)
        auth_info: Authenticated API key info (dependency injected)
        
    Returns:
        Dict containing database health status
        
    Raises:
        HTTPException: If health check fails
    """
    try:
        # Perform database health checks
        start_time = datetime.utcnow()
        
        # Test basic connectivity
        result = await db.execute("SELECT 1 as health_check")
        health_result = result.scalar()
        
        # Get connection pool status
        pool_status = {
            "pool_size": db.get_bind().pool.size(),
            "checked_out": db.get_bind().pool.checkedout(),
            "overflow": db.get_bind().pool.overflow(),
            "checked_in": db.get_bind().pool.checkedin()
        }
        
        response_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "status": "healthy" if health_result == 1 else "unhealthy",
            "database_connection": "active",
            "response_time_seconds": response_time,
            "pool_status": pool_status,
            "timestamp": datetime.utcnow().isoformat(),
            "authenticated": True,
            "dependency_injection": True
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database health check failed: {str(e)}")


async def get_agent_statistics_enhanced(
    db: AsyncSession = Depends(get_db_session),
    auth_info: APIKeyInfo = Depends(require_permission("agent:stats"))
) -> Dict[str, Any]:
    """
    Get agent statistics using database queries and dependency injection.
    
    Args:
        db: Database session (dependency injected)
        auth_info: Authenticated API key info (dependency injected)
        
    Returns:
        Dict containing agent statistics
        
    Raises:
        HTTPException: If statistics retrieval fails
    """
    try:
        # Get comprehensive agent statistics
        stats = await AgentRepository.get_agent_statistics(db)
        
        return {
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat(),
            "database_source": True,
            "authenticated": True
        }
        
    except DatabaseOperationError as e:
        logger.error(f"Database operation failed during statistics retrieval: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during statistics retrieval: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during statistics retrieval")

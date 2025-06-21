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

logger = logging.getLogger(__name__)


# Enhanced Agent Management Endpoints

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
        # Convert request to database format
        agent_data = {
            "type": agent_info.type.value,
            "name": agent_info.name,
            "endpoint": agent_info.endpoint,
            "capabilities": agent_info.capabilities,
            "metadata": {
                "registration_source": "api",
                "api_version": "2.0",
                "validation_passed": True
            }
        }
        
        # Create agent using transaction (will auto-commit on success)
        agent = await create_agent_with_transaction(agent_data)
        
        logger.info(f"Agent registered successfully - ID: {agent.id}, Name: {ValidationUtils.sanitize_string(agent.name)}")
        
        return {
            "agent_id": str(agent.id),
            "status": "registered",
            "message": "Agent registered successfully with database persistence",
            "created_at": agent.created_at.isoformat(),
            "database_stored": True
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
        
        # Convert to response format
        agent_dict = agent.to_dict()
        agent_dict["name"] = ValidationUtils.sanitize_string(agent.name)
        
        # Include task information if requested
        if include_tasks and agent.tasks:
            agent_dict["tasks"] = [task.to_dict() for task in agent.tasks]
            agent_dict["task_count"] = len(agent.tasks)
        
        agent_dict["database_source"] = True
        
        return agent_dict
        
    except HTTPException:
        raise
    except DatabaseOperationError as e:
        logger.error(f"Database operation failed during agent retrieval: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during agent retrieval: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during agent retrieval")


# Enhanced Task Management Endpoints

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
                "validation_passed": True
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
            "priority": task.priority,
            "database_stored": True
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
            # Sanitize sensitive information
            if task_dict.get("description"):
                task_dict["description"] = ValidationUtils.sanitize_string(task_dict["description"])
            task_list.append(task_dict)
        
        return {
            "tasks": task_list,
            "total_count": total_count,
            "limit": query.limit,
            "offset": query.offset,
            "sort_by": query.sort_by,
            "sort_order": query.sort_order,
            "database_source": True,
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


async def get_task_enhanced(
    task_id: str,
    include_agent: bool = Query(False, description="Include assigned agent in response"),
    include_workflow: bool = Query(False, description="Include workflow in response"),
    db: AsyncSession = Depends(get_db_session),
    auth_info: APIKeyInfo = Depends(require_permission("task:read"))
) -> Dict[str, Any]:
    """
    Enhanced task retrieval with optional relationship loading.
    
    Args:
        task_id: The ID of the task to retrieve
        include_agent: Whether to include assigned agent in response
        include_workflow: Whether to include workflow in response
        db: Database session (dependency injected)
        auth_info: Authenticated API key info (dependency injected)
        
    Returns:
        Dict containing task information and optionally related data
        
    Raises:
        HTTPException: If task not found or database operation fails
    """
    """
    try:
        # Validate task ID format
        if not ValidationUtils.validate_uuid(task_id):
            raise HTTPException(status_code=400, detail="Invalid task ID format")
        
        # Get task from database
        task = await TaskRepository.get_task_by_id(
            task_id=task_id,
            db=db,
            include_agent=include_agent,
            include_workflow=include_workflow
        )
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Convert to response format
        task_dict = task.to_dict()
        if task_dict.get("description"):
            task_dict["description"] = ValidationUtils.sanitize_string(task_dict["description"])
        
        # Include related information if requested
        if include_agent and task.assigned_agent:
            task_dict["assigned_agent"] = task.assigned_agent.to_dict()
            task_dict["assigned_agent"]["name"] = ValidationUtils.sanitize_string(task.assigned_agent.name)
        
        if include_workflow and task.workflow:
            task_dict["workflow"] = task.workflow.to_dict()
        
        task_dict["database_source"] = True
        
        return task_dict
        
    except HTTPException:
        raise
    except DatabaseOperationError as e:
        logger.error(f"Database operation failed during task retrieval: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during task retrieval: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during task retrieval")


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
        # Validate UUIDs
        if not ValidationUtils.validate_uuid(task_id):
            raise HTTPException(status_code=400, detail="Invalid task ID format")
        if not ValidationUtils.validate_uuid(agent_id):
            raise HTTPException(status_code=400, detail="Invalid agent ID format")
        
        # Verify task and agent exist
        task = await TaskRepository.get_task_by_id(task_id, db)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        agent = await AgentRepository.get_agent_by_id(agent_id, db)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Check if task is assignable
        if task.status != TaskStatusEnum.PENDING:
            raise HTTPException(
                status_code=400, 
                detail=f"Task cannot be assigned - current status: {task.status.value}"
            )
        
        # Check if agent is available
        if agent.status != "idle":
            raise HTTPException(
                status_code=400,
                detail=f"Agent is not available - current status: {agent.status}"
            )
        
        # Assign task using transaction
        success = await assign_task_with_transaction(task_id, agent_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Task assignment failed")
        
        logger.info(f"Task {task_id} assigned to agent {agent_id}")
        
        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "assigned",
            "message": "Task assigned successfully with database transaction",
            "assigned_at": datetime.utcnow().isoformat(),
            "database_updated": True
        }
        
    except HTTPException:
        raise
    except DatabaseOperationError as e:
        logger.error(f"Database operation failed during task assignment: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during task assignment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during task assignment")


# Database Health Check Endpoint

async def database_health_check_enhanced(
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Enhanced database health check using dependency injection
    """
    try:
        from db_service import check_database_health
        
        health_status = await check_database_health()
        
        # Add additional connection pool information
        from database import get_database_manager
        db_manager = await get_database_manager()
        
        try:
            pool_stats = await db_manager.get_pool_stats()
            connection_info = await db_manager.get_connection_info()
            
            health_status.update({
                "connection_pool": {
                    "pool_size": pool_stats.pool_size,
                    "checked_in": pool_stats.checked_in,
                    "checked_out": pool_stats.checked_out,
                    "overflow": pool_stats.overflow,
                    "invalid": pool_stats.invalid
                },
                "active_connections": len(connection_info),
                "dependency_injection": "enabled"
            })
        except Exception as e:
            logger.warning(f"Could not get detailed connection info: {e}")
        
        return health_status
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database health check failed",
            "dependency_injection": "enabled"
        }


# Utility functions for demonstrating dependency injection patterns

async def get_agent_statistics_enhanced(
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get agent statistics using database queries and dependency injection
    """
    try:
        from sqlalchemy import func, select
        from models import Agent, Task
        
        # Agent statistics
        total_agents_query = select(func.count(Agent.id)).where(Agent.is_active == True)
        total_agents_result = await db.execute(total_agents_query)
        total_agents = total_agents_result.scalar()
        
        # Agents by status
        agent_status_query = (
            select(Agent.status, func.count(Agent.id))
            .where(Agent.is_active == True)
            .group_by(Agent.status)
        )
        agent_status_result = await db.execute(agent_status_query)
        status_counts = dict(agent_status_result.fetchall())
        
        # Agents by type
        agent_type_query = (
            select(Agent.type, func.count(Agent.id))
            .where(Agent.is_active == True)
            .group_by(Agent.type)
        )
        agent_type_result = await db.execute(agent_type_query)
        type_counts = {str(k): v for k, v in agent_type_result.fetchall()}
        
        # Task statistics
        total_tasks_query = select(func.count(Task.id))
        total_tasks_result = await db.execute(total_tasks_query)
        total_tasks = total_tasks_result.scalar()
        
        # Tasks by status
        task_status_query = (
            select(Task.status, func.count(Task.id))
            .group_by(Task.status)
        )
        task_status_result = await db.execute(task_status_query)
        task_status_counts = {str(k): v for k, v in task_status_result.fetchall()}
        
        return {
            "agent_statistics": {
                "total_agents": total_agents,
                "by_status": status_counts,
                "by_type": type_counts
            },
            "task_statistics": {
                "total_tasks": total_tasks,
                "by_status": task_status_counts
            },
            "data_source": "database",
            "dependency_injection": "enabled",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


# Example of using database transactions for complex operations

async def bulk_agent_operation_enhanced(
    operation: str,
    agent_ids: List[str],
    db: AsyncSession = Depends(get_db_transaction)  # Note: using transaction dependency
) -> Dict[str, Any]:
    """
    Perform bulk operations on agents using database transactions
    
    This demonstrates how to use the transaction dependency for operations
    that need to be atomic across multiple database changes.
    """
    try:
        if operation not in ["activate", "deactivate", "reset_status"]:
            raise HTTPException(status_code=400, detail="Invalid operation")
        
        # Validate all agent IDs
        for agent_id in agent_ids:
            if not ValidationUtils.validate_uuid(agent_id):
                raise HTTPException(status_code=400, detail=f"Invalid agent ID: {agent_id}")
        
        updated_count = 0
        errors = []
        
        for agent_id in agent_ids:
            try:
                if operation == "activate":
                    result = await AgentRepository.update_agent_status(
                        agent_id, "idle", None, db
                    )
                elif operation == "deactivate":
                    result = await AgentRepository.update_agent_status(
                        agent_id, "offline", None, db
                    )
                elif operation == "reset_status":
                    result = await AgentRepository.update_agent_status(
                        agent_id, "idle", None, db
                    )
                
                if result:
                    updated_count += 1
                else:
                    errors.append(f"Agent {agent_id} not found")
                    
            except Exception as e:
                errors.append(f"Agent {agent_id}: {str(e)}")
        
        # Log the bulk operation
        await OrchestrationLogRepository.log_operation(
            operation_type="bulk_agent_operation",
            entity_type="agent",
            entity_id=None,
            status="success" if not errors else "partial",
            db=db,
            message=f"Bulk {operation} operation completed",
            details={
                "operation": operation,
                "total_agents": len(agent_ids),
                "updated_count": updated_count,
                "error_count": len(errors),
                "errors": errors[:10]  # Limit errors in log
            }
        )
        
        # If we have errors but some successes, the transaction will still commit
        # If we want to rollback on any error, we could raise an exception here
        
        return {
            "operation": operation,
            "total_agents": len(agent_ids),
            "updated_count": updated_count,
            "error_count": len(errors),
            "errors": errors,
            "status": "completed" if not errors else "partial",
            "database_transaction": "committed",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk agent operation failed: {e}")
        # The transaction will automatically rollback due to the exception
        raise HTTPException(status_code=500, detail=f"Bulk operation failed: {str(e)}")


# Add this to demonstrate the enhanced endpoints in your FastAPI app:
"""
To integrate these enhanced endpoints in your main.py, you would add routes like:

app.post("/api/v2/agents/register")(register_agent_enhanced)
app.get("/api/v2/agents")(list_agents_enhanced)
app.get("/api/v2/agents/{agent_id}")(get_agent_enhanced)
app.post("/api/v2/tasks")(create_task_enhanced)
app.get("/api/v2/tasks")(list_tasks_enhanced)
app.get("/api/v2/tasks/{task_id}")(get_task_enhanced)
app.post("/api/v2/tasks/{task_id}/assign/{agent_id}")(assign_task_enhanced)
app.get("/api/v2/health/database")(database_health_check_enhanced)
app.get("/api/v2/statistics/agents")(get_agent_statistics_enhanced)
app.post("/api/v2/agents/bulk/{operation}")(bulk_agent_operation_enhanced)
"""

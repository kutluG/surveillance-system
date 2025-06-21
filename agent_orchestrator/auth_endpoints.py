"""
Authenticated endpoints for Agent Orchestrator Service.

This module provides secure endpoints that require API key authentication
for agent registration and management operations. It builds upon the
enhanced_endpoints.py module with added security layers.

Features:
- API key authentication for all endpoints
- Permission-based access control
- Rate limiting per API key
- Endpoint-specific access control
- Comprehensive audit logging

Author: Agent Orchestrator Team
Version: 1.0.0
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.responses import JSONResponse
import logging

from .auth import (
    APIKeyInfo,
    verify_api_key,
    require_permission,
    verify_endpoint_access,
    require_agent_register,
    require_agent_read,
    require_agent_write,
    require_agent_delete,
    require_task_create,
    require_task_read,
    require_admin,
    get_auth_service_dependency,
    AuthenticationService
)
from .db_service import DatabaseService, get_db_service
from .models import Agent, Task, WorkflowTemplate, OrchestrationLog
from .schemas import (
    AgentRegistrationRequest,
    AgentResponse,
    AgentUpdateRequest,
    TaskCreateRequest,
    TaskResponse,
    WorkflowCreateRequest,
    WorkflowResponse,
    PaginatedResponse,
    HealthResponse
)

logger = logging.getLogger(__name__)

# Create router for authenticated endpoints
auth_router = APIRouter(prefix="/api/v1", tags=["Authenticated Operations"])


async def log_api_access(
    request: Request,
    key_info: APIKeyInfo,
    action: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """Log API access for audit purposes."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "api_key_id": key_info.key_id,
        "api_key_name": key_info.name,
        "action": action,
        "endpoint": request.url.path,
        "method": request.method,
        "resource_id": resource_id,
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "details": details or {}
    }
    
    logger.info(f"API Access: {log_entry}")


# Agent Management Endpoints

@auth_router.post(
    "/agents/register",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new agent",
    description="Register a new agent in the orchestrator system with authentication required"
)
async def register_agent_authenticated(
    request: Request,
    agent_data: AgentRegistrationRequest,
    db_service: DatabaseService = Depends(get_db_service),
    key_info: APIKeyInfo = require_agent_register
):
    """Register a new agent with authentication."""
    try:
        # Log the access
        await log_api_access(
            request, key_info, "agent_register",
            details={"agent_name": agent_data.name, "agent_type": agent_data.agent_type}
        )
        
        # Create the agent
        agent = await db_service.create_agent(
            name=agent_data.name,
            agent_type=agent_data.agent_type,
            capabilities=agent_data.capabilities,
            config=agent_data.config,
            metadata=agent_data.metadata
        )
        
        # Convert to response model
        response = AgentResponse(
            id=agent.id,
            name=agent.name,
            agent_type=agent.agent_type,
            capabilities=agent.capabilities,
            status=agent.status,
            config=agent.config,
            metadata=agent.metadata,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            last_heartbeat=agent.last_heartbeat
        )
        
        logger.info(f"Agent registered successfully: {agent.id} by API key: {key_info.name}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to register agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register agent: {str(e)}"
        )


@auth_router.get(
    "/agents",
    response_model=PaginatedResponse[AgentResponse],
    summary="List agents",
    description="Get a paginated list of all registered agents"
)
async def list_agents_authenticated(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    status_filter: Optional[str] = Query(None, description="Filter by agent status"),
    agent_type_filter: Optional[str] = Query(None, description="Filter by agent type"),
    db_service: DatabaseService = Depends(get_db_service),
    key_info: APIKeyInfo = require_agent_read
):
    """List all agents with authentication."""
    try:
        # Log the access
        await log_api_access(
            request, key_info, "agent_list",
            details={"skip": skip, "limit": limit, "filters": {
                "status": status_filter, "agent_type": agent_type_filter
            }}
        )
        
        # Get agents with filters
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        if agent_type_filter:
            filters["agent_type"] = agent_type_filter
        
        agents, total = await db_service.get_agents(
            skip=skip,
            limit=limit,
            filters=filters
        )
        
        # Convert to response models
        agent_responses = [
            AgentResponse(
                id=agent.id,
                name=agent.name,
                agent_type=agent.agent_type,
                capabilities=agent.capabilities,
                status=agent.status,
                config=agent.config,
                metadata=agent.metadata,
                created_at=agent.created_at,
                updated_at=agent.updated_at,
                last_heartbeat=agent.last_heartbeat
            )
            for agent in agents
        ]
        
        return PaginatedResponse(
            items=agent_responses,
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}"
        )


@auth_router.get(
    "/agents/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent details",
    description="Get detailed information about a specific agent"
)
async def get_agent_authenticated(
    agent_id: UUID,
    request: Request,
    db_service: DatabaseService = Depends(get_db_service),
    key_info: APIKeyInfo = require_agent_read
):
    """Get agent details with authentication."""
    try:
        # Log the access
        await log_api_access(
            request, key_info, "agent_get",
            resource_id=str(agent_id)
        )
        
        # Get the agent
        agent = await db_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            agent_type=agent.agent_type,
            capabilities=agent.capabilities,
            status=agent.status,
            config=agent.config,
            metadata=agent.metadata,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            last_heartbeat=agent.last_heartbeat
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent: {str(e)}"
        )


@auth_router.put(
    "/agents/{agent_id}",
    response_model=AgentResponse,
    summary="Update agent",
    description="Update an existing agent's configuration and metadata"
)
async def update_agent_authenticated(
    agent_id: UUID,
    agent_data: AgentUpdateRequest,
    request: Request,
    db_service: DatabaseService = Depends(get_db_service),
    key_info: APIKeyInfo = require_agent_write
):
    """Update agent with authentication."""
    try:
        # Log the access
        await log_api_access(
            request, key_info, "agent_update",
            resource_id=str(agent_id),
            details={"update_fields": list(agent_data.dict(exclude_unset=True).keys())}
        )
        
        # Update the agent
        agent = await db_service.update_agent(agent_id, agent_data.dict(exclude_unset=True))
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            agent_type=agent.agent_type,
            capabilities=agent.capabilities,
            status=agent.status,
            config=agent.config,
            metadata=agent.metadata,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            last_heartbeat=agent.last_heartbeat
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {str(e)}"
        )


@auth_router.delete(
    "/agents/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete agent",
    description="Remove an agent from the orchestrator system"
)
async def delete_agent_authenticated(
    agent_id: UUID,
    request: Request,
    db_service: DatabaseService = Depends(get_db_service),
    key_info: APIKeyInfo = require_agent_delete
):
    """Delete agent with authentication."""
    try:
        # Log the access
        await log_api_access(
            request, key_info, "agent_delete",
            resource_id=str(agent_id)
        )
        
        # Delete the agent
        success = await db_service.delete_agent(agent_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        logger.info(f"Agent {agent_id} deleted by API key: {key_info.name}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {str(e)}"
        )


# Task Management Endpoints

@auth_router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description="Create a new task for agent execution"
)
async def create_task_authenticated(
    request: Request,
    task_data: TaskCreateRequest,
    db_service: DatabaseService = Depends(get_db_service),
    key_info: APIKeyInfo = require_task_create
):
    """Create a new task with authentication."""
    try:
        # Log the access
        await log_api_access(
            request, key_info, "task_create",
            details={
                "task_type": task_data.task_type,
                "priority": task_data.priority,
                "assigned_agent": str(task_data.assigned_agent_id) if task_data.assigned_agent_id else None
            }
        )
        
        # Create the task
        task = await db_service.create_task(
            task_type=task_data.task_type,
            priority=task_data.priority,
            config=task_data.config,
            assigned_agent_id=task_data.assigned_agent_id,
            metadata=task_data.metadata
        )
        
        # Convert to response model
        response = TaskResponse(
            id=task.id,
            task_type=task.task_type,
            status=task.status,
            priority=task.priority,
            config=task.config,
            assigned_agent_id=task.assigned_agent_id,
            result=task.result,
            error_message=task.error_message,
            metadata=task.metadata,
            created_at=task.created_at,
            updated_at=task.updated_at,
            started_at=task.started_at,
            completed_at=task.completed_at
        )
        
        logger.info(f"Task created successfully: {task.id} by API key: {key_info.name}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )


@auth_router.get(
    "/tasks",
    response_model=PaginatedResponse[TaskResponse],
    summary="List tasks",
    description="Get a paginated list of all tasks"
)
async def list_tasks_authenticated(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    status_filter: Optional[str] = Query(None, description="Filter by task status"),
    task_type_filter: Optional[str] = Query(None, description="Filter by task type"),
    agent_id_filter: Optional[UUID] = Query(None, description="Filter by assigned agent ID"),
    db_service: DatabaseService = Depends(get_db_service),
    key_info: APIKeyInfo = require_task_read
):
    """List all tasks with authentication."""
    try:
        # Log the access
        await log_api_access(
            request, key_info, "task_list",
            details={"skip": skip, "limit": limit, "filters": {
                "status": status_filter,
                "task_type": task_type_filter,
                "agent_id": str(agent_id_filter) if agent_id_filter else None
            }}
        )
        
        # Get tasks with filters
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        if task_type_filter:
            filters["task_type"] = task_type_filter
        if agent_id_filter:
            filters["assigned_agent_id"] = agent_id_filter
        
        tasks, total = await db_service.get_tasks(
            skip=skip,
            limit=limit,
            filters=filters
        )
        
        # Convert to response models
        task_responses = [
            TaskResponse(
                id=task.id,
                task_type=task.task_type,
                status=task.status,
                priority=task.priority,
                config=task.config,
                assigned_agent_id=task.assigned_agent_id,
                result=task.result,
                error_message=task.error_message,
                metadata=task.metadata,
                created_at=task.created_at,
                updated_at=task.updated_at,
                started_at=task.started_at,
                completed_at=task.completed_at
            )
            for task in tasks
        ]
        
        return PaginatedResponse(
            items=task_responses,
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}"
        )


# Authentication Management Endpoints (Admin only)

@auth_router.post(
    "/auth/keys",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
    description="Create a new API key (admin only)"
)
async def create_api_key_authenticated(
    request: Request,
    key_data: Dict[str, Any],
    auth_service: AuthenticationService = Depends(get_auth_service_dependency),
    key_info: APIKeyInfo = require_admin
):
    """Create a new API key with admin authentication."""
    try:
        # Log the access
        await log_api_access(
            request, key_info, "api_key_create",
            details={"target_name": key_data.get("name")}
        )
        
        # Extract parameters
        name = key_data.get("name")
        permissions = key_data.get("permissions", ["agent:read"])
        expires_in_days = key_data.get("expires_in_days", 30)
        
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name is required"
            )
        
        # Create the key
        api_key, key_info_new = await auth_service.create_user_key(
            user_name=name,
            permissions=permissions,
            expires_in_days=expires_in_days
        )
        
        logger.info(f"API key created: {key_info_new.key_id} by admin: {key_info.name}")
        
        return {
            "api_key": api_key,
            "key_info": {
                "key_id": key_info_new.key_id,
                "name": key_info_new.name,
                "permissions": key_info_new.permissions,
                "expires_at": key_info_new.expires_at.isoformat() if key_info_new.expires_at else None,
                "rate_limit": key_info_new.rate_limit,
                "allowed_endpoints": key_info_new.allowed_endpoints
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )


@auth_router.get(
    "/auth/keys",
    response_model=List[Dict[str, Any]],
    summary="List API keys",
    description="List all API keys (admin only)"
)
async def list_api_keys_authenticated(
    request: Request,
    auth_service: AuthenticationService = Depends(get_auth_service_dependency),
    key_info: APIKeyInfo = require_admin
):
    """List all API keys with admin authentication."""
    try:
        # Log the access
        await log_api_access(request, key_info, "api_key_list")
        
        # Get all keys
        keys = auth_service.api_key_manager.list_keys()
        
        # Convert to response format (without sensitive data)
        key_responses = [
            {
                "key_id": key.key_id,
                "name": key.name,
                "permissions": key.permissions,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "last_used": key.last_used.isoformat() if key.last_used else None,
                "is_active": key.is_active,
                "rate_limit": key.rate_limit,
                "allowed_endpoints": key.allowed_endpoints
            }
            for key in keys
        ]
        
        return key_responses
        
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}"
        )


@auth_router.delete(
    "/auth/keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API key",
    description="Revoke an API key (admin only)"
)
async def revoke_api_key_authenticated(
    key_id: str,
    request: Request,
    auth_service: AuthenticationService = Depends(get_auth_service_dependency),
    key_info: APIKeyInfo = require_admin
):
    """Revoke an API key with admin authentication."""
    try:
        # Log the access
        await log_api_access(
            request, key_info, "api_key_revoke",
            resource_id=key_id
        )
        
        # Revoke the key
        success = auth_service.api_key_manager.revoke_key(key_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key {key_id} not found"
            )
        
        logger.info(f"API key revoked: {key_id} by admin: {key_info.name}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key {key_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke API key: {str(e)}"
        )


# Health endpoint (public)
@auth_router.get(
    "/health/authenticated",
    response_model=HealthResponse,
    summary="Health check (authenticated)",
    description="Get service health status with authentication details"
)
async def health_check_authenticated(
    request: Request,
    key_info: APIKeyInfo = Depends(verify_api_key)
):
    """Health check with authentication information."""
    try:
        # Log the access
        await log_api_access(request, key_info, "health_check")
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            authenticated=True,
            api_key_name=key_info.name,
            permissions=key_info.permissions
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            authenticated=True,
            api_key_name=key_info.name,
            error=str(e)
        )

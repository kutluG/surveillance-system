"""
FastAPI Router Integration for Enhanced Agent Orchestrator Endpoints

This module demonstrates how to integrate the enhanced endpoints with 
authentication and Kafka event streaming into a FastAPI application.

Features:
- Complete router setup with authentication
- Kafka event streaming integration
- Proper error handling
- API documentation
- Health checks and monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Dict, Any, List, Optional
import logging

from enhanced_endpoints_authenticated import (
    register_agent_enhanced,
    list_agents_enhanced,
    get_agent_enhanced,
    create_task_enhanced,
    list_tasks_enhanced,
    assign_task_enhanced,
    database_health_check_enhanced,
    get_agent_statistics_enhanced
)
from validation import (
    EnhancedAgentRegistrationRequest,
    EnhancedCreateTaskRequest,
    AgentQueryParams,
    TaskQueryParams
)
from auth import APIKeyInfo, require_permission
from kafka_integration import init_kafka, shutdown_kafka, event_publisher

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v2",
    tags=["Enhanced Agent Orchestrator"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"}
    }
)


# Agent Management Endpoints

@router.post(
    "/agents/register",
    summary="Register Agent with Authentication",
    description="Register a new agent with database persistence, authentication, and event streaming",
    responses={
        200: {"description": "Agent registered successfully"},
        400: {"description": "Invalid request data"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"}
    }
)
async def register_agent(
    request: Request,
    agent_info: EnhancedAgentRegistrationRequest,
    result: Dict[str, Any] = Depends(register_agent_enhanced)
) -> Dict[str, Any]:
    """Register a new agent with full authentication and event streaming."""
    return result


@router.get(
    "/agents",
    summary="List Agents with Filtering",
    description="Get filtered list of agents with pagination and authentication",
    responses={
        200: {"description": "Agents retrieved successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"}
    }
)
async def list_agents(
    result: Dict[str, Any] = Depends(list_agents_enhanced)
) -> Dict[str, Any]:
    """Get filtered list of agents with pagination."""
    return result


@router.get(
    "/agents/{agent_id}",
    summary="Get Agent Details",
    description="Retrieve detailed information about a specific agent",
    responses={
        200: {"description": "Agent details retrieved successfully"},
        404: {"description": "Agent not found"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"}
    }
)
async def get_agent(
    agent_id: str,
    include_tasks: bool = Query(False, description="Include assigned tasks in response"),
    result: Dict[str, Any] = Depends(get_agent_enhanced)
) -> Dict[str, Any]:
    """Get detailed information about a specific agent."""
    return result


# Task Management Endpoints

@router.post(
    "/tasks",
    summary="Create Task",
    description="Create a new task with database persistence and authentication",
    responses={
        200: {"description": "Task created successfully"},
        400: {"description": "Invalid request data"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"}
    }
)
async def create_task(
    task_request: EnhancedCreateTaskRequest,
    result: Dict[str, Any] = Depends(create_task_enhanced)
) -> Dict[str, Any]:
    """Create a new task with authentication."""
    return result


@router.get(
    "/tasks",
    summary="List Tasks with Filtering",
    description="Get filtered list of tasks with pagination and authentication",
    responses={
        200: {"description": "Tasks retrieved successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"}
    }
)
async def list_tasks(
    result: Dict[str, Any] = Depends(list_tasks_enhanced)
) -> Dict[str, Any]:
    """Get filtered list of tasks with pagination."""
    return result


@router.post(
    "/tasks/{task_id}/assign/{agent_id}",
    summary="Assign Task to Agent",
    description="Assign a task to an agent with database transaction and event streaming",
    responses={
        200: {"description": "Task assigned successfully"},
        404: {"description": "Task or agent not found"},
        400: {"description": "Invalid task or agent ID"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"}
    }
)
async def assign_task(
    task_id: str,
    agent_id: str,
    result: Dict[str, Any] = Depends(assign_task_enhanced)
) -> Dict[str, Any]:
    """Assign a task to an agent with authentication and event streaming."""
    return result


# Health and Monitoring Endpoints

@router.get(
    "/health/database",
    summary="Database Health Check",
    description="Check database connectivity and health with authentication",
    responses={
        200: {"description": "Database is healthy"},
        503: {"description": "Database is unhealthy"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"}
    }
)
async def health_check(
    result: Dict[str, Any] = Depends(database_health_check_enhanced)
) -> Dict[str, Any]:
    """Check database health with authentication."""
    return result


@router.get(
    "/statistics/agents",
    summary="Agent Statistics",
    description="Get comprehensive agent statistics with authentication",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"}
    }
)
async def agent_statistics(
    result: Dict[str, Any] = Depends(get_agent_statistics_enhanced)
) -> Dict[str, Any]:
    """Get comprehensive agent statistics."""
    return result


@router.get(
    "/health/kafka",
    summary="Kafka Health Check",
    description="Check Kafka connectivity and health",
    responses={
        200: {"description": "Kafka is healthy"},
        503: {"description": "Kafka is unhealthy"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"}
    }
)
async def kafka_health_check(
    auth_info: APIKeyInfo = Depends(require_permission("system:health"))
) -> Dict[str, Any]:
    """Check Kafka connectivity and health."""
    try:
        # Test Kafka connection by attempting to publish a health event
        success = await event_publisher.publish_system_health(
            status="healthy",
            metrics={
                "timestamp": "now",
                "source": "health_check",
                "test": True
            },
            metadata={"health_check": True, "api_key_id": auth_info.key_id}
        )
        
        return {
            "status": "healthy" if success else "unhealthy",
            "kafka_producer": "connected" if success else "disconnected",
            "authenticated": True,
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"Kafka health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Kafka health check failed: {str(e)}")


# Lifecycle Management

@router.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting enhanced agent orchestrator service...")
    
    # Initialize Kafka
    kafka_success = await init_kafka()
    if kafka_success:
        logger.info("Kafka integration initialized successfully")
    else:
        logger.warning("Kafka integration failed to initialize")
    
    logger.info("Enhanced agent orchestrator service started")


@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down enhanced agent orchestrator service...")
    
    # Shutdown Kafka
    await shutdown_kafka()
    
    logger.info("Enhanced agent orchestrator service shutdown complete")


# Include additional utility endpoints

@router.get(
    "/info",
    summary="Service Information",
    description="Get service information and capabilities",
    responses={
        200: {"description": "Service information retrieved"},
        401: {"description": "Authentication required"}
    }
)
async def service_info(
    auth_info: APIKeyInfo = Depends(require_permission("system:read"))
) -> Dict[str, Any]:
    """Get service information and capabilities."""
    return {
        "service": "agent_orchestrator",
        "version": "2.0.0",
        "features": [
            "database_persistence",
            "api_key_authentication",
            "permission_based_access",
            "kafka_event_streaming",
            "transaction_safety",
            "connection_pooling",
            "audit_logging"
        ],
        "authentication": {
            "type": "api_key",
            "key_id": auth_info.key_id,
            "permissions": auth_info.permissions
        },
        "database": {
            "type": "postgresql",
            "persistence": "enabled",
            "transactions": "enabled"
        },
        "event_streaming": {
            "type": "kafka",
            "enabled": True,
            "async": True
        }
    }

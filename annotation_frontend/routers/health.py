"""
Health check endpoints for the annotation frontend service.
Provides liveness and readiness probes for Kubernetes/Docker deployment.
"""
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, status, HTTPException, Depends
from fastapi.responses import JSONResponse

from config import settings
from schemas import HealthResponse, KafkaMetricsResponse, ScalingInfoResponse, ErrorResponse
from kafka_pool import kafka_pool
from redis_service import redis_retry_service
from shared.logging_config import get_logger
from database import get_db
from sqlalchemy.orm import Session
from models import AnnotationExample, AnnotationStatus

logger = get_logger(__name__)

# Create router
router = APIRouter(
    prefix="",
    tags=["health"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Service unavailable"}
    }
)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Basic health check endpoint that verifies database connectivity and returns service status",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"}
    }
)
async def health_check(db: Session = Depends(get_db)):
    """
    Basic health check endpoint.
    
    Returns:
        HealthResponse: Basic health status with database connectivity
    """
    try:
        # Test database connection
        pending_count = db.query(AnnotationExample).filter(
            AnnotationExample.status == AnnotationStatus.PENDING
        ).count()
        
        database_connected = True
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        database_connected = False
        pending_count = -1
    
    # Basic Kafka connectivity check (non-blocking)
    kafka_connected = kafka_pool.is_healthy()
    
    # Determine overall health status
    is_healthy = database_connected and kafka_connected
    
    response = HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        service="annotation_frontend",
        database_connected=database_connected,
        kafka_connected=kafka_connected,
        pending_examples=pending_count,
        details={
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.1.0"
        }
    )
    
    if not is_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump()
        )
    
    return response


@router.get(
    "/healthz",
    response_model=HealthResponse,
    summary="Kubernetes liveness probe",
    description="Liveness probe for Kubernetes. Checks if the service is running and responsive",
    responses={
        200: {"description": "Service is alive"},
        503: {"description": "Service is not responding properly"}
    }
)
async def liveness_check(db: Session = Depends(get_db)):
    """
    Kubernetes liveness probe.
    
    This endpoint is used by Kubernetes to determine if the pod should be restarted.
    It performs basic checks to ensure the service is functioning.
    
    Returns:
        HealthResponse: Liveness status
    """
    try:
        # Test database connection
        db.execute("SELECT 1")
        database_connected = True
        
        # Get pending examples count
        pending_count = db.query(AnnotationExample).filter(
            AnnotationExample.status == AnnotationStatus.PENDING
        ).count()
        
    except Exception as e:
        logger.error(f"Liveness check database failed: {e}")
        database_connected = False
        pending_count = -1
    
    # Check Kafka pool health
    kafka_connected = kafka_pool.is_healthy()
    
    # Check Redis connectivity
    redis_connected = False
    try:
        redis_connected = await redis_retry_service.ping()
    except Exception as e:
        logger.error(f"Liveness check Redis failed: {e}")
    
    # Determine if service is alive (less strict than readiness)
    is_alive = database_connected  # Core requirement for liveness
    
    response = HealthResponse(
        status="alive" if is_alive else "dead",
        service="annotation_frontend",
        database_connected=database_connected,
        kafka_connected=kafka_connected,
        pending_examples=pending_count,
        details={
            "redis_connected": redis_connected,
            "timestamp": datetime.utcnow().isoformat(),
            "check_type": "liveness"
        }
    )
    
    if not is_alive:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump()
        )
    
    return response


@router.get(
    "/readyz",
    response_model=HealthResponse,
    summary="Kubernetes readiness probe",
    description="Readiness probe for Kubernetes. Checks if the service is ready to accept traffic",
    responses={
        200: {"description": "Service is ready to accept traffic"},
        503: {"description": "Service is not ready to accept traffic"}
    }
)
async def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe.
    
    This endpoint is used by Kubernetes to determine if the pod is ready to accept traffic.
    It performs comprehensive checks including Kafka consumer assignment verification.
    
    Returns:
        HealthResponse: Readiness status
    """
    try:
        # Test database connection with a simple query
        db.execute("SELECT 1")
        
        # Get pending examples count
        pending_count = db.query(AnnotationExample).filter(
            AnnotationExample.status == AnnotationStatus.PENDING
        ).count()
        
        database_connected = True
        
    except Exception as e:
        logger.error(f"Readiness check database failed: {e}")
        database_connected = False
        pending_count = -1
    
    # Check Kafka consumer health and partition assignment
    kafka_connected = False
    kafka_ready = False
    partition_assignments = {}
    
    try:
        kafka_connected = kafka_pool.is_healthy()
        
        if kafka_connected:
            # Check if consumer is properly assigned to partitions
            consumer_info = await kafka_pool.get_consumer_info()
            partition_assignments = consumer_info.get("partition_assignments", {})
            
            # Service is ready if it has partition assignments (can consume messages)
            kafka_ready = bool(partition_assignments)
            
    except Exception as e:
        logger.error(f"Readiness check Kafka failed: {e}")
    
    # Check Redis connectivity
    redis_connected = False
    try:
        redis_connected = await redis_retry_service.ping()
    except Exception as e:
        logger.error(f"Readiness check Redis failed: {e}")
    
    # Service is ready if all critical components are healthy
    # For a consumer service, this includes having partition assignments
    is_ready = database_connected and kafka_connected and kafka_ready and redis_connected
    
    response = HealthResponse(
        status="ready" if is_ready else "not_ready",
        service="annotation_frontend",
        database_connected=database_connected,
        kafka_connected=kafka_connected,
        pending_examples=pending_count,
        details={
            "redis_connected": redis_connected,
            "kafka_ready": kafka_ready,
            "partition_assignments": partition_assignments,
            "timestamp": datetime.utcnow().isoformat(),
            "check_type": "readiness"
        }
    )
    
    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump()
        )
    
    return response


@router.get(
    "/api/v1/kafka/metrics",
    response_model=KafkaMetricsResponse,
    summary="Kafka consumer metrics",
    description="Get detailed Kafka consumer metrics including partition assignments and lag",
    responses={
        200: {"description": "Kafka metrics retrieved successfully"},
        503: {"description": "Kafka service unavailable"}
    }
)
async def get_kafka_metrics():
    """
    Get detailed Kafka consumer metrics.
    
    Returns:
        KafkaMetricsResponse: Kafka consumer metrics and status
    """
    try:
        if not kafka_pool.is_healthy():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Kafka connection is not healthy"
            )
        
        # Get consumer information
        consumer_info = await kafka_pool.get_consumer_info()
        
        # Get consumer group information
        group_info = await kafka_pool.get_consumer_group_info()
        
        response = KafkaMetricsResponse(
            consumer_group=consumer_info.get("group_id", "unknown"),
            consumer_group_members=group_info.get("member_count", 0),
            partition_assignments=consumer_info.get("partition_assignments", {}),
            consumer_lag=consumer_info.get("consumer_lag", {}),
            topics=consumer_info.get("topics", []),
            connection_status="connected" if kafka_pool.is_healthy() else "disconnected",
            last_heartbeat=consumer_info.get("last_heartbeat")
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get Kafka metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to retrieve Kafka metrics: {str(e)}"
        )


@router.get(
    "/api/v1/scaling/info",
    response_model=ScalingInfoResponse,
    summary="Service scaling information",
    description="Get information about service scaling and load balancing",
    responses={
        200: {"description": "Scaling information retrieved successfully"},
        503: {"description": "Unable to retrieve scaling information"}
    }
)
async def get_scaling_info():
    """
    Get service scaling and load balancing information.
    
    Returns:
        ScalingInfoResponse: Service scaling metrics and status
    """
    try:
        # Get instance information
        instance_id = settings.INSTANCE_ID
        instance_index = getattr(settings, 'INSTANCE_INDEX', 0)
        
        # Get WebSocket connections count from Redis
        websocket_count = 0
        try:
            websocket_count = await redis_retry_service.get_websocket_count()
        except Exception as e:
            logger.warning(f"Failed to get WebSocket count from Redis: {e}")
        
        # Get consumer assignments
        consumer_assignments = {}
        try:
            consumer_info = await kafka_pool.get_consumer_info()
            consumer_assignments = consumer_info.get("partition_assignments", {})
        except Exception as e:
            logger.warning(f"Failed to get consumer assignments: {e}")
        
        # Check connectivity
        redis_connected = False
        kafka_connected = False
        
        try:
            redis_connected = await redis_retry_service.ping()
        except Exception:
            pass
        
        try:
            kafka_connected = kafka_pool.is_healthy()
        except Exception:
            pass
        
        # Calculate uptime (simplified - could be enhanced with actual startup time)
        uptime_seconds = 0.0  # This would need to be tracked from startup
        
        response = ScalingInfoResponse(
            instance_id=instance_id,
            instance_index=instance_index,
            total_instances=getattr(settings, 'TOTAL_INSTANCES', 1),
            websocket_connections=websocket_count,
            consumer_assignments=consumer_assignments,
            redis_connected=redis_connected,
            kafka_connected=kafka_connected,
            uptime_seconds=uptime_seconds
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get scaling info: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to retrieve scaling information: {str(e)}"
        )

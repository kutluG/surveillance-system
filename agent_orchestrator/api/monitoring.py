"""
Monitoring and health check API endpoints.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..core.orchestrator import get_orchestrator, OrchestratorService

router = APIRouter()


class HealthResponse(BaseModel):
    """Response model for health checks"""
    status: str
    timestamp: str
    services: Dict[str, str]
    metrics: Dict[str, Any]


class MetricsResponse(BaseModel):
    """Response model for metrics"""
    active_agents: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    system_load: float
    uptime: str


@router.get("/health", response_model=HealthResponse)
async def health_check(
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Get system health status"""
    try:
        from datetime import datetime
        
        # Check Redis connection
        redis_status = "healthy"
        try:
            if orchestrator.redis_client:
                await orchestrator.redis_client.ping()
        except Exception:
            redis_status = "unhealthy"
        
        return HealthResponse(
            status="healthy" if redis_status == "healthy" else "degraded",
            timestamp=datetime.utcnow().isoformat(),
            services={
                "redis": redis_status,
                "http_client": "healthy" if orchestrator.http_client else "unhealthy"
            },
            metrics={
                "agents_count": len(orchestrator._agents),
                "tasks_count": len(orchestrator._active_tasks)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Get system metrics"""
    try:
        # Count tasks by status
        completed_count = sum(1 for task in orchestrator._active_tasks.values() 
                            if task.get("status") == "completed")
        failed_count = sum(1 for task in orchestrator._active_tasks.values() 
                         if task.get("status") == "failed")
        
        return MetricsResponse(
            active_agents=len([a for a in orchestrator._agents.values() 
                             if a.get("status") == "idle"]),
            active_tasks=len([t for t in orchestrator._active_tasks.values() 
                            if t.get("status") in ["pending", "running", "assigned"]]),
            completed_tasks=completed_count,
            failed_tasks=failed_count,
            system_load=0.0,  # Placeholder - could implement actual system load
            uptime="unknown"  # Placeholder - could track service start time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_system_status(
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Get detailed system status"""
    try:
        return {
            "service": "agent_orchestrator",
            "version": "2.0.0",
            "status": "running",
            "agents": len(orchestrator._agents),
            "tasks": len(orchestrator._active_tasks),
            "background_tasks": len(orchestrator._background_tasks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

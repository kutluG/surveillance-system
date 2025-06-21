"""
Monitoring and health check API endpoints.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..core.orchestrator import get_orchestrator, OrchestratorService

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model"""
    service: str
    status: str
    timestamp: str
    details: Dict[str, Any] = {}


class MetricsResponse(BaseModel):
    """Metrics response model"""
    active_agents: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    system_load: float


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    from datetime import datetime
    return HealthResponse(
        service="agent_orchestrator",
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        details={"version": "2.0.0"}
    )


@router.get("/health/detailed", response_model=Dict[str, Any])
async def detailed_health_check(
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Detailed health check with service dependencies"""
    try:
        from datetime import datetime
        
        agents = await orchestrator.list_agents()
        tasks = await orchestrator.list_tasks()
        
        return {
            "service": "agent_orchestrator",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {
                "total_agents": len(agents),
                "active_agents": len([a for a in agents if a.get("status") == "busy"]),
                "total_tasks": len(tasks),
                "pending_tasks": len([t for t in tasks if t.get("status") == "pending"]),
                "running_tasks": len([t for t in tasks if t.get("status") == "running"]),
                "completed_tasks": len([t for t in tasks if t.get("status") == "completed"]),
                "failed_tasks": len([t for t in tasks if t.get("status") == "failed"]),
                "redis_connected": orchestrator.redis_client is not None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Get system metrics"""
    try:
        agents = await orchestrator.list_agents()
        tasks = await orchestrator.list_tasks()
        
        return MetricsResponse(
            active_agents=len([a for a in agents if a.get("status") == "busy"]),
            active_tasks=len([t for t in tasks if t.get("status") in ["pending", "running"]]),
            completed_tasks=len([t for t in tasks if t.get("status") == "completed"]),
            failed_tasks=len([t for t in tasks if t.get("status") == "failed"]),
            system_load=0.5  # Placeholder - would calculate actual system load
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=Dict[str, Any])
async def get_system_status(
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Get comprehensive system status"""
    try:
        from datetime import datetime
        
        agents = await orchestrator.list_agents()
        tasks = await orchestrator.list_tasks()
        
        agent_stats = {}
        for agent in agents:
            status = agent.get("status", "unknown")
            agent_stats[status] = agent_stats.get(status, 0) + 1
        
        task_stats = {}
        for task in tasks:
            status = task.get("status", "unknown")
            task_stats[status] = task_stats.get(status, 0) + 1
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "service": "agent_orchestrator",
            "version": "2.0.0",
            "agents": {
                "total": len(agents),
                "by_status": agent_stats
            },
            "tasks": {
                "total": len(tasks),
                "by_status": task_stats
            },
            "system": {
                "redis_connected": orchestrator.redis_client is not None,
                "background_tasks_running": len(orchestrator._background_tasks)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
Agent management API endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..core.orchestrator import get_orchestrator, OrchestratorService

router = APIRouter()


class AgentRegistrationRequest(BaseModel):
    """Request model for agent registration"""
    type: str = Field(..., description="Type of agent")
    name: str = Field(..., description="Name of the agent")
    endpoint: str = Field(..., description="Agent endpoint URL")
    capabilities: List[str] = Field(default=[], description="Agent capabilities")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class AgentResponse(BaseModel):
    """Response model for agent operations"""
    id: str
    type: str
    name: str
    endpoint: str
    capabilities: List[str]
    status: str
    last_seen: Optional[str] = None
    current_task_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


@router.post("/agents", response_model=Dict[str, str])
async def register_agent(
    request: AgentRegistrationRequest,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Register a new agent with the orchestrator"""
    try:
        agent_data = request.dict()
        agent_id = await orchestrator.register_agent(agent_data)
        return {"agent_id": agent_id, "status": "registered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents", response_model=List[AgentResponse])
async def list_agents(
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """List all registered agents"""
    try:
        agents = await orchestrator.list_agents()
        return [AgentResponse(**agent) for agent in agents]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Get details of a specific agent"""
    try:
        agent = await orchestrator.get_agent_status(agent_id)
        return AgentResponse(**agent)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_id}")
async def unregister_agent(
    agent_id: str,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Unregister an agent from the orchestrator"""
    try:
        # Implementation for agent unregistration
        # This would remove the agent from memory and Redis
        return {"status": "unregistered", "agent_id": agent_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(
    agent_id: str,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Update agent heartbeat"""
    try:
        # Implementation for heartbeat update
        return {"status": "heartbeat_updated", "agent_id": agent_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

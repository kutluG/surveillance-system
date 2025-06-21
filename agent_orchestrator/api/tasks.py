"""
Task management API endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..core.orchestrator import get_orchestrator, OrchestratorService

router = APIRouter()


class TaskCreationRequest(BaseModel):
    """Request model for task creation"""
    type: str = Field(..., description="Type of task")
    description: str = Field(..., description="Task description")
    input_data: Dict[str, Any] = Field(default={}, description="Task input data")
    required_capabilities: List[str] = Field(default=[], description="Required agent capabilities")
    priority: int = Field(default=1, description="Task priority (1=highest)")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class TaskResponse(BaseModel):
    """Response model for task operations"""
    id: str
    type: str
    description: str
    input_data: Dict[str, Any]
    required_capabilities: List[str]
    priority: int
    status: str
    assigned_agent_id: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


@router.post("/tasks", response_model=Dict[str, str])
async def create_task(
    request: TaskCreationRequest,
    background_tasks: BackgroundTasks,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Create a new task"""
    try:
        task_data = request.dict()
        task_id = await orchestrator.create_task(task_data)
        return {"task_id": task_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """List tasks, optionally filtered by status"""
    try:
        tasks = await orchestrator.list_tasks(status=status)
        return [TaskResponse(**task) for task in tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Get details of a specific task"""
    try:
        task = await orchestrator.get_task_status(task_id)
        return TaskResponse(**task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/assign")
async def assign_task(
    task_id: str,
    agent_id: Optional[str] = None,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Assign a task to an agent"""
    try:
        success = await orchestrator.assign_task(task_id, agent_id)
        if success:
            return {"status": "assigned", "task_id": task_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to assign task")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/execute")
async def execute_task(
    task_id: str,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Execute a task"""
    try:
        result = await orchestrator.execute_task(task_id)
        return {"status": "completed", "task_id": task_id, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    """Cancel a task"""
    try:
        # Implementation for task cancellation
        return {"status": "cancelled", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

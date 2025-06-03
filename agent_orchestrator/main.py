"""
Agent Orchestration Coordinator Service

This service acts as the central coordinator for all AI agent activities in the surveillance system.
It manages agent workflows, handles inter-agent communication, and orchestrates complex multi-agent tasks.

Features:
- Agent lifecycle management
- Task coordination and distribution
- Inter-agent communication
- Workflow orchestration
- Resource allocation
- Performance monitoring
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentType(str, Enum):
    PROMPT_AGENT = "prompt_agent"
    RAG_AGENT = "rag_agent"
    RULE_AGENT = "rule_agent"
    ANALYSIS_AGENT = "analysis_agent"
    NOTIFICATION_AGENT = "notification_agent"

@dataclass
class Agent:
    id: str
    type: AgentType
    name: str
    endpoint: str
    capabilities: List[str]
    status: str = "idle"
    last_seen: datetime = None
    current_task: Optional[str] = None
    performance_metrics: Dict = None

@dataclass
class Task:
    id: str
    type: str
    description: str
    input_data: Dict
    assigned_agents: List[str]
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    priority: int = 1
    dependencies: List[str] = None
    workflow_id: Optional[str] = None

@dataclass
class Workflow:
    id: str
    name: str
    description: str
    tasks: List[str]
    status: str
    created_at: datetime
    user_id: str
    configuration: Dict

# Request/Response Models
class CreateTaskRequest(BaseModel):
    type: str
    description: str
    input_data: dict
    priority: int = 1
    required_capabilities: List[str] = []
    workflow_id: Optional[str] = None

class CreateWorkflowRequest(BaseModel):
    name: str
    description: str
    tasks: List[CreateTaskRequest]
    user_id: str
    configuration: dict = {}

class AgentRegistrationRequest(BaseModel):
    type: AgentType
    name: str
    endpoint: str
    capabilities: List[str]

# Global state
class OrchestrationState:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.task_queue = asyncio.Queue()
        self.redis_client: Optional[redis.Redis] = None
        self.db_session: Optional[AsyncSession] = None

state = OrchestrationState()

# Database connection
async def get_database_session():
    """Get database session"""
    if not state.db_session:
        engine = create_async_engine("postgresql+asyncpg://user:password@localhost/surveillance")
        SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        state.db_session = SessionLocal()
    return state.db_session

# Redis connection
async def get_redis_client():
    """Get Redis client"""
    if not state.redis_client:
        state.redis_client = redis.from_url("redis://localhost:6379/5")
    return state.redis_client

# Agent Management
class AgentManager:
    @staticmethod
    async def register_agent(agent_info: AgentRegistrationRequest) -> str:
        """Register a new agent"""
        agent_id = str(uuid.uuid4())
        agent = Agent(
            id=agent_id,
            type=agent_info.type,
            name=agent_info.name,
            endpoint=agent_info.endpoint,
            capabilities=agent_info.capabilities,
            last_seen=datetime.utcnow(),
            performance_metrics={}
        )
        
        state.agents[agent_id] = agent
        
        # Store in Redis for persistence
        redis_client = await get_redis_client()
        await redis_client.hset(
            "agents",
            agent_id,
            json.dumps(asdict(agent), default=str)
        )
        
        logger.info(f"Registered agent: {agent.name} ({agent_id})")
        return agent_id

    @staticmethod
    async def find_suitable_agents(required_capabilities: List[str], task_type: str) -> List[Agent]:
        """Find agents suitable for a task"""
        suitable_agents = []
        
        for agent in state.agents.values():
            if agent.status != "idle":
                continue
                
            # Check if agent has required capabilities
            if required_capabilities and not set(required_capabilities).issubset(set(agent.capabilities)):
                continue
                
            # Check if agent type matches task requirements
            if task_type.startswith("prompt") and agent.type != AgentType.PROMPT_AGENT:
                continue
            elif task_type.startswith("search") and agent.type != AgentType.RAG_AGENT:
                continue
            elif task_type.startswith("rule") and agent.type != AgentType.RULE_AGENT:
                continue
                
            suitable_agents.append(agent)
        
        # Sort by performance metrics (if available)
        suitable_agents.sort(key=lambda a: a.performance_metrics.get("success_rate", 0.5), reverse=True)
        return suitable_agents

    @staticmethod
    async def update_agent_status(agent_id: str, status: str, current_task: Optional[str] = None):
        """Update agent status"""
        if agent_id in state.agents:
            state.agents[agent_id].status = status
            state.agents[agent_id].last_seen = datetime.utcnow()
            if current_task is not None:
                state.agents[agent_id].current_task = current_task
            
            # Update in Redis
            redis_client = await get_redis_client()
            await redis_client.hset(
                "agents",
                agent_id,
                json.dumps(asdict(state.agents[agent_id]), default=str)
            )

# Task Management
class TaskManager:
    @staticmethod
    async def create_task(task_request: CreateTaskRequest) -> str:
        """Create a new task"""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            type=task_request.type,
            description=task_request.description,
            input_data=task_request.input_data,
            assigned_agents=[],
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            priority=task_request.priority,
            dependencies=[],
            workflow_id=task_request.workflow_id
        )
        
        state.tasks[task_id] = task
        
        # Store in Redis
        redis_client = await get_redis_client()
        await redis_client.hset(
            "tasks",
            task_id,
            json.dumps(asdict(task), default=str)
        )
        
        # Add to task queue
        await state.task_queue.put(task_id)
        
        logger.info(f"Created task: {task.description} ({task_id})")
        return task_id

    @staticmethod
    async def assign_task(task_id: str, agent_id: str):
        """Assign task to agent"""
        if task_id not in state.tasks or agent_id not in state.agents:
            raise ValueError("Task or agent not found")
        
        task = state.tasks[task_id]
        task.assigned_agents.append(agent_id)
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        # Update agent status
        await AgentManager.update_agent_status(agent_id, "busy", task_id)
        
        logger.info(f"Assigned task {task_id} to agent {agent_id}")

    @staticmethod
    async def execute_task(task_id: str) -> Dict:
        """Execute a task by calling the assigned agent"""
        task = state.tasks[task_id]
        if not task.assigned_agents:
            raise ValueError("No agents assigned to task")
        
        agent_id = task.assigned_agents[0]  # Use first agent for simplicity
        agent = state.agents[agent_id]
        
        try:
            # Call agent endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{agent.endpoint}/process",
                    json={
                        "task_id": task_id,
                        "task_type": task.type,
                        "input_data": task.input_data
                    },
                    timeout=300  # 5 minute timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.utcnow()
                    
                    # Update agent performance metrics
                    if "performance_metrics" not in agent.performance_metrics:
                        agent.performance_metrics = {"success_rate": 1.0, "total_tasks": 1}
                    else:
                        metrics = agent.performance_metrics
                        total = metrics.get("total_tasks", 0) + 1
                        successes = metrics.get("total_tasks", 0) * metrics.get("success_rate", 0) + 1
                        agent.performance_metrics = {
                            "success_rate": successes / total,
                            "total_tasks": total
                        }
                    
                    logger.info(f"Task {task_id} completed successfully")
                    return result
                else:
                    raise Exception(f"Agent returned error: {response.status_code}")
                    
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            logger.error(f"Task {task_id} failed: {e}")
            raise
        finally:
            # Free up agent
            await AgentManager.update_agent_status(agent_id, "idle", None)

# Workflow Management
class WorkflowManager:
    @staticmethod
    async def create_workflow(workflow_request: CreateWorkflowRequest) -> str:
        """Create a new workflow"""
        workflow_id = str(uuid.uuid4())
        
        # Create tasks for workflow
        task_ids = []
        for task_request in workflow_request.tasks:
            task_request.workflow_id = workflow_id
            task_id = await TaskManager.create_task(task_request)
            task_ids.append(task_id)
        
        workflow = Workflow(
            id=workflow_id,
            name=workflow_request.name,
            description=workflow_request.description,
            tasks=task_ids,
            status="running",
            created_at=datetime.utcnow(),
            user_id=workflow_request.user_id,
            configuration=workflow_request.configuration
        )
        
        state.workflows[workflow_id] = workflow
        
        logger.info(f"Created workflow: {workflow.name} ({workflow_id})")
        return workflow_id

    @staticmethod
    async def execute_workflow(workflow_id: str):
        """Execute workflow tasks in sequence"""
        workflow = state.workflows[workflow_id]
        
        try:
            results = []
            for task_id in workflow.tasks:
                # Wait for task completion
                while state.tasks[task_id].status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                    await asyncio.sleep(1)
                
                if state.tasks[task_id].status == TaskStatus.FAILED:
                    workflow.status = "failed"
                    return
                
                results.append(state.tasks[task_id].result)
            
            workflow.status = "completed"
            logger.info(f"Workflow {workflow_id} completed successfully")
            
        except Exception as e:
            workflow.status = "failed"
            logger.error(f"Workflow {workflow_id} failed: {e}")

# Task Processor
async def task_processor():
    """Background task processor"""
    while True:
        try:
            # Get task from queue with timeout
            task_id = await asyncio.wait_for(state.task_queue.get(), timeout=1.0)
            
            # Find suitable agent
            task = state.tasks[task_id]
            suitable_agents = await AgentManager.find_suitable_agents(
                [], task.type
            )
            
            if suitable_agents:
                # Assign to best agent
                agent = suitable_agents[0]
                await TaskManager.assign_task(task_id, agent.id)
                
                # Execute task in background
                asyncio.create_task(TaskManager.execute_task(task_id))
            else:
                # No suitable agents, put back in queue
                await state.task_queue.put(task_id)
                await asyncio.sleep(5)  # Wait before retrying
                
        except asyncio.TimeoutError:
            # No tasks in queue, continue
            continue
        except Exception as e:
            logger.error(f"Error in task processor: {e}")
            await asyncio.sleep(1)

# FastAPI App
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Agent Orchestrator Service...")
    
    # Start background task processor
    processor_task = asyncio.create_task(task_processor())
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent Orchestrator Service...")
    processor_task.cancel()

app = FastAPI(
    title="Agent Orchestration Coordinator",
    description="Central coordinator for AI agent activities",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints
@app.post("/agents/register")
async def register_agent(agent_info: AgentRegistrationRequest):
    """Register a new agent"""
    try:
        agent_id = await AgentManager.register_agent(agent_info)
        return {"agent_id": agent_id, "status": "registered"}
    except Exception as e:
        logger.error(f"Error registering agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents")
async def list_agents():
    """List all registered agents"""
    agents = []
    for agent in state.agents.values():
        agent_dict = asdict(agent)
        agent_dict["last_seen"] = agent.last_seen.isoformat() if agent.last_seen else None
        agents.append(agent_dict)
    return {"agents": agents}

@app.post("/tasks")
async def create_task(task_request: CreateTaskRequest):
    """Create a new task"""
    try:
        task_id = await TaskManager.create_task(task_request)
        return {"task_id": task_id, "status": "created"}
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details"""
    if task_id not in state.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = state.tasks[task_id]
    task_dict = asdict(task)
    
    # Convert datetime objects to strings
    for field in ["created_at", "started_at", "completed_at"]:
        if task_dict[field]:
            task_dict[field] = task_dict[field].isoformat()
    
    return task_dict

@app.get("/tasks")
async def list_tasks(status: Optional[str] = None, workflow_id: Optional[str] = None):
    """List tasks with optional filtering"""
    tasks = []
    for task in state.tasks.values():
        # Apply filters
        if status and task.status != status:
            continue
        if workflow_id and task.workflow_id != workflow_id:
            continue
        
        task_dict = asdict(task)
        # Convert datetime objects to strings
        for field in ["created_at", "started_at", "completed_at"]:
            if task_dict[field]:
                task_dict[field] = task_dict[field].isoformat()
        tasks.append(task_dict)
    
    return {"tasks": tasks}

@app.post("/workflows")
async def create_workflow(workflow_request: CreateWorkflowRequest):
    """Create a new workflow"""
    try:
        workflow_id = await WorkflowManager.create_workflow(workflow_request)
        
        # Start workflow execution in background
        asyncio.create_task(WorkflowManager.execute_workflow(workflow_id))
        
        return {"workflow_id": workflow_id, "status": "created"}
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow details"""
    if workflow_id not in state.workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = state.workflows[workflow_id]
    workflow_dict = asdict(workflow)
    workflow_dict["created_at"] = workflow.created_at.isoformat()
    
    return workflow_dict

@app.get("/workflows")
async def list_workflows(user_id: Optional[str] = None):
    """List workflows with optional user filtering"""
    workflows = []
    for workflow in state.workflows.values():
        if user_id and workflow.user_id != user_id:
            continue
        
        workflow_dict = asdict(workflow)
        workflow_dict["created_at"] = workflow.created_at.isoformat()
        workflows.append(workflow_dict)
    
    return {"workflows": workflows}

@app.get("/status")
async def get_system_status():
    """Get system status"""
    active_agents = len([a for a in state.agents.values() if a.status == "busy"])
    idle_agents = len([a for a in state.agents.values() if a.status == "idle"])
    
    running_tasks = len([t for t in state.tasks.values() if t.status == TaskStatus.RUNNING])
    pending_tasks = len([t for t in state.tasks.values() if t.status == TaskStatus.PENDING])
    
    return {
        "agents": {
            "total": len(state.agents),
            "active": active_agents,
            "idle": idle_agents
        },
        "tasks": {
            "total": len(state.tasks),
            "running": running_tasks,
            "pending": pending_tasks,
            "queue_size": state.task_queue.qsize()
        },
        "workflows": {
            "total": len(state.workflows),
            "running": len([w for w in state.workflows.values() if w.status == "running"])
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)

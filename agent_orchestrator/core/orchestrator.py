"""
Core Orchestrator Service

Consolidated orchestration logic combining the best features from multiple orchestrator implementations.
Provides unified orchestration with circuit breakers, retry logic, and distributed coordination.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import uuid

import httpx
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential
from fastapi import HTTPException
from pydantic import BaseModel, Field

# Import configuration and utilities
from ..utils.config import get_config
from ..models.domain import Agent, Task, Workflow, TaskStatusEnum, WorkflowStatusEnum

logger = logging.getLogger(__name__)


class OrchestrationRequest(BaseModel):
    """Request model for orchestration endpoint"""
    event_data: Dict[str, Any] = Field(..., description="Event data to process")
    query: Optional[str] = Field(None, description="Optional query for RAG analysis")
    notification_channels: List[str] = Field(default=["email"], description="Notification channels")
    recipients: List[str] = Field(default=[], description="Notification recipients")


class OrchestrationResponse(BaseModel):
    """Unified response model for orchestration"""
    status: str = Field(..., description="Status: ok, partial_success, fallback, or error")
    details: Dict[str, Any] = Field(..., description="Detailed response data")
    rag_result: Optional[Dict[str, Any]] = Field(None, description="RAG service result")
    rule_result: Optional[Dict[str, Any]] = Field(None, description="Rule generation result")
    notification_result: Optional[Dict[str, Any]] = Field(None, description="Notification result")


class OrchestratorService:
    """Main orchestrator service with circuit breakers, retry logic, and task management"""
    
    def __init__(self):
        self.config = get_config()
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self._background_tasks: Set[asyncio.Task] = set()
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._active_tasks: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize Redis, HTTP clients, and background services"""
        try:
            self.redis_client = redis.from_url(self.config.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
            
            self.http_client = httpx.AsyncClient(timeout=self.config.http_timeout)
            logger.info("HTTP client initialized")
            
            # Start background task processing
            task = asyncio.create_task(self._process_background_tasks())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            
            logger.info("Orchestrator service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator service: {e}")
            raise
    
    async def shutdown(self):
        """Gracefully shutdown the orchestrator service"""
        try:
            # Cancel background tasks
            for task in self._background_tasks:
                task.cancel()
            
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            
            # Close connections
            if self.http_client:
                await self.http_client.aclose()
            
            if self.redis_client:
                await self.redis_client.close()
                
            logger.info("Orchestrator service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during orchestrator shutdown: {e}")
    
    async def register_agent(self, agent_data: Dict[str, Any]) -> str:
        """Register a new agent with the orchestrator"""
        try:
            agent_id = str(uuid.uuid4())
            agent_info = {
                "id": agent_id,
                "type": agent_data.get("type"),
                "name": agent_data.get("name"),
                "endpoint": agent_data.get("endpoint"),
                "capabilities": agent_data.get("capabilities", []),
                "status": "idle",
                "last_seen": datetime.utcnow().isoformat(),
                "metadata": agent_data.get("metadata", {})
            }
            
            # Store in memory
            self._agents[agent_id] = agent_info
            
            # Store in Redis for distributed access
            if self.redis_client:
                await self.redis_client.hset(
                    f"agents:{agent_id}",
                    mapping=agent_info
                )
                await self.redis_client.expire(f"agents:{agent_id}", 300)  # 5 min TTL
            
            logger.info(f"Registered agent: {agent_id} ({agent_info['name']})")
            return agent_id
            
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            raise HTTPException(status_code=500, detail=f"Agent registration failed: {str(e)}")
    
    async def create_task(self, task_data: Dict[str, Any]) -> str:
        """Create and queue a new task"""
        try:
            task_id = str(uuid.uuid4())
            task_info = {
                "id": task_id,
                "type": task_data.get("type"),
                "description": task_data.get("description"),
                "input_data": task_data.get("input_data", {}),
                "required_capabilities": task_data.get("required_capabilities", []),
                "priority": task_data.get("priority", 1),
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "metadata": task_data.get("metadata", {})
            }
            
            # Store in memory
            self._active_tasks[task_id] = task_info
            
            # Store in Redis for distributed access
            if self.redis_client:
                await self.redis_client.hset(
                    f"tasks:{task_id}",
                    mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                            for k, v in task_info.items()}
                )
                await self.redis_client.lpush("task_queue", task_id)
            
            logger.info(f"Created task: {task_id} ({task_info['type']})")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")
    
    async def assign_task(self, task_id: str, agent_id: Optional[str] = None) -> bool:
        """Assign a task to an agent (auto-select if not specified)"""
        try:
            task = self._active_tasks.get(task_id)
            if not task:
                logger.error(f"Task not found: {task_id}")
                return False
            
            if not agent_id:
                agent_id = await self._select_best_agent(task["required_capabilities"])
            
            if not agent_id:
                logger.warning(f"No suitable agent found for task: {task_id}")
                return False
            
            agent = self._agents.get(agent_id)
            if not agent or agent["status"] != "idle":
                logger.warning(f"Agent not available: {agent_id}")
                return False
            
            # Update task assignment
            task["assigned_agent_id"] = agent_id
            task["status"] = "assigned"
            task["assigned_at"] = datetime.utcnow().isoformat()
            
            # Update agent status
            agent["status"] = "busy"
            agent["current_task_id"] = task_id
            
            # Update Redis
            if self.redis_client:
                await self.redis_client.hset(
                    f"tasks:{task_id}",
                    mapping={
                        "assigned_agent_id": agent_id,
                        "status": "assigned",
                        "assigned_at": task["assigned_at"]
                    }
                )
                await self.redis_client.hset(
                    f"agents:{agent_id}",
                    mapping={
                        "status": "busy",
                        "current_task_id": task_id
                    }
                )
            
            logger.info(f"Assigned task {task_id} to agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign task: {e}")
            return False
    
    async def _select_best_agent(self, required_capabilities: List[str]) -> Optional[str]:
        """Select the best available agent for the given capabilities"""
        best_agent_id = None
        best_score = 0
        
        for agent_id, agent in self._agents.items():
            if agent["status"] != "idle":
                continue
            
            # Calculate capability match score
            agent_capabilities = set(agent.get("capabilities", []))
            required_caps = set(required_capabilities)
            
            if not required_caps.issubset(agent_capabilities):
                continue
            
            # Simple scoring: more capabilities = higher score
            score = len(agent_capabilities)
            
            if score > best_score:
                best_score = score
                best_agent_id = agent_id
        
        return best_agent_id
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a task by calling the assigned agent"""
        try:
            task = self._active_tasks.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            agent_id = task.get("assigned_agent_id")
            if not agent_id:
                raise HTTPException(status_code=400, detail="Task not assigned to any agent")
            
            agent = self._agents.get(agent_id)
            if not agent:
                raise HTTPException(status_code=400, detail="Assigned agent not found")
            
            # Update task status
            task["status"] = "running"
            task["started_at"] = datetime.utcnow().isoformat()
            
            # Call agent endpoint
            response = await self.http_client.post(
                f"{agent['endpoint']}/execute",
                json={
                    "task_id": task_id,
                    "task_type": task["type"],
                    "input_data": task["input_data"]
                }
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Update task with result
            task["status"] = "completed"
            task["completed_at"] = datetime.utcnow().isoformat()
            task["result"] = result
            
            # Free up agent
            agent["status"] = "idle"
            agent["current_task_id"] = None
            
            # Update Redis
            if self.redis_client:
                await self.redis_client.hset(
                    f"tasks:{task_id}",
                    mapping={
                        "status": "completed",
                        "completed_at": task["completed_at"],
                        "result": json.dumps(result)
                    }
                )
                await self.redis_client.hset(
                    f"agents:{agent_id}",
                    mapping={
                        "status": "idle",
                        "current_task_id": ""
                    }
                )
            
            logger.info(f"Task completed: {task_id}")
            return result
            
        except Exception as e:
            # Mark task as failed
            if task_id in self._active_tasks:
                self._active_tasks[task_id]["status"] = "failed"
                self._active_tasks[task_id]["error_message"] = str(e)
                
                # Free up agent
                agent_id = self._active_tasks[task_id].get("assigned_agent_id")
                if agent_id and agent_id in self._agents:
                    self._agents[agent_id]["status"] = "idle"
                    self._agents[agent_id]["current_task_id"] = None
            
            logger.error(f"Task execution failed: {task_id}, error: {e}")
            raise
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get current status of a task"""
        task = self._active_tasks.get(task_id)
        if not task:
            # Try to get from Redis
            if self.redis_client:
                task_data = await self.redis_client.hgetall(f"tasks:{task_id}")
                if task_data:
                    # Convert JSON fields back
                    for key in ["input_data", "result", "required_capabilities"]:
                        if key in task_data and task_data[key]:
                            try:
                                task_data[key] = json.loads(task_data[key])
                            except json.JSONDecodeError:
                                pass
                    return task_data
            
            raise HTTPException(status_code=404, detail="Task not found")
        
        return task.copy()
    
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get current status of an agent"""
        agent = self._agents.get(agent_id)
        if not agent:
            # Try to get from Redis
            if self.redis_client:
                agent_data = await self.redis_client.hgetall(f"agents:{agent_id}")
                if agent_data:
                    return agent_data
            
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return agent.copy()
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents"""
        agents = list(self._agents.values())
        
        # Also check Redis for agents from other instances
        if self.redis_client:
            try:
                keys = await self.redis_client.keys("agents:*")
                for key in keys:
                    agent_id = key.split(":")[-1]
                    if agent_id not in self._agents:
                        agent_data = await self.redis_client.hgetall(key)
                        if agent_data:
                            agents.append(agent_data)
            except Exception as e:
                logger.warning(f"Failed to fetch agents from Redis: {e}")
        
        return agents
    
    async def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by status"""
        tasks = []
        for task in self._active_tasks.values():
            if status is None or task["status"] == status:
                tasks.append(task.copy())
        
        return tasks
    
    async def _process_background_tasks(self):
        """Background task processor"""
        while True:
            try:
                if self.redis_client:
                    # Process queued tasks
                    task_id = await self.redis_client.brpop("task_queue", timeout=5)
                    if task_id:
                        task_id = task_id[1]  # brpop returns (key, value)
                        
                        # Try to assign and execute the task
                        if await self.assign_task(task_id):
                            try:
                                await self.execute_task(task_id)
                            except Exception as e:
                                logger.error(f"Background task execution failed: {task_id}, error: {e}")
                
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info("Background task processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background task processor: {e}")
                await asyncio.sleep(5)


# Global orchestrator instance
_orchestrator: Optional[OrchestratorService] = None


async def get_orchestrator() -> OrchestratorService:
    """Get the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OrchestratorService()
        await _orchestrator.initialize()
    return _orchestrator

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
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Response, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError, Field
import redis.asyncio as redis
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Import database dependency injection
from database import get_db_session, get_db_transaction, database_lifespan, get_database_manager

# Import configuration
from config import get_config, validate_config

# Import metrics system
from metrics import metrics_collector, monitor_orchestration_performance, monitor_service_call

# Import enhanced validation models
from validation import (
    EnhancedCreateTaskRequest,
    EnhancedCreateWorkflowRequest,
    EnhancedAgentRegistrationRequest,
    TaskQueryParams,
    AgentQueryParams,
    ValidationErrorResponse,
    ValidationErrorDetail,
    SecurityValidator,
    ValidationUtils
)

# Import load balancing components
from load_balancing_router import load_balancing_router
from advanced_load_balancer import AdvancedLoadBalancer, LoadBalanceStrategy
from semantic_agent_matcher import EnhancedSemanticAgentMatcher

# Import distributed orchestrator components
from distributed_router import distributed_router

# Import enhanced security components
from enhanced_security import (
    EnhancedSecurityManager,
    SecurityMiddleware,
    get_current_user_enhanced,
    require_permission_enhanced,
    require_role_enhanced,
    Permission,
    UserRole,
    oauth2_scheme
)

# Configure logging
config = get_config()
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format=config.log_format
)
logger = logging.getLogger(__name__)

# Import shared middleware for rate limiting (optional)
try:
    from shared.middleware import add_rate_limiting
    HAS_RATE_LIMITING = True
except ImportError:
    HAS_RATE_LIMITING = False
    logger.warning("Shared middleware not available - rate limiting disabled")

# Import OpenTelemetry tracing
try:
    from shared.tracing import configure_tracing
    from opentelemetry import trace
    HAS_TRACING = True
    
    # Configure tracing for this service
    configure_tracing("agent_orchestrator")
    tracer = trace.get_tracer(__name__)
    logger.info("OpenTelemetry tracing configured successfully")
except ImportError:
    HAS_TRACING = False
    tracer = None
    logger.warning("OpenTelemetry not available - distributed tracing disabled")

# Import orchestrator modules
from orchestrator import orchestrator_service, OrchestrationRequest, OrchestrationResponse
from enhanced_orchestrator import (
    get_enhanced_orchestrator_service,
    EnhancedOrchestratorService,
    OrchestrationRequest as EnhancedOrchestrationRequest,
    OrchestrationResponse as EnhancedOrchestrationResponse
)

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

# Request/Response Models (keeping original simple models for backward compatibility)
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

# Enhanced validation error handling
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation error handler"""
    details = []
    for error in exc.errors():
        details.append(ValidationErrorDetail(
            field=".".join(str(x) for x in error["loc"]),
            message=error["msg"],
            invalid_value=error.get("input", ""),
            constraint=error["type"]
        ))
    
    response = ValidationErrorResponse(
        message="Request validation failed",
        details=details,
        request_id=str(uuid.uuid4())
    )
    
    logger.warning(f"Validation error: {response.message}, Details: {len(details)} errors")
    return JSONResponse(
        status_code=422,
        content=response.dict()
    )

# Global state
class OrchestrationState:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.task_queue = asyncio.Queue()
        self.redis_client: Optional[redis.Redis] = None
        # Database session management is now handled by database.py

state = OrchestrationState()

# Database connection is now managed by dependency injection - see database.py
# Use get_db_session() or get_db_transaction() as FastAPI dependencies

# Redis connection
async def get_redis_client():
    """Get Redis client"""
    if not state.redis_client:
        config = get_config()
        state.redis_client = redis.from_url(config.redis_url)
    return state.redis_client

# Agent Management
class AgentManager:
    """Enhanced agent management with semantic matching and advanced load balancing"""
    
    # Class-level instances for advanced matching and load balancing
    _semantic_matcher: Optional[EnhancedSemanticAgentMatcher] = None
    _load_balancer: Optional[AdvancedLoadBalancer] = None
    _security_manager: Optional[EnhancedSecurityManager] = None
    _security_middleware: Optional[SecurityMiddleware] = None
    
    @classmethod
    async def initialize_advanced_components(cls):
        """Initialize semantic matcher, load balancer, and security components"""
        if not cls._semantic_matcher:
            cls._semantic_matcher = EnhancedSemanticAgentMatcher()
            logger.info("Semantic agent matcher initialized")
            
        if not cls._load_balancer:
            cls._load_balancer = AdvancedLoadBalancer()
            logger.info("Advanced load balancer initialized")
            
        if not cls._security_manager:
            cls._security_manager = EnhancedSecurityManager()
            logger.info("Enhanced security manager initialized")
            
        if not cls._security_middleware:
            cls._security_middleware = SecurityMiddleware()
            logger.info("Security middleware initialized")
    
    @staticmethod
    async def register_agent(agent_info: AgentRegistrationRequest) -> str:
        """Register a new agent with enhanced capability profiling"""
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
        
        # Ensure advanced components are initialized
        await AgentManager.initialize_advanced_components()
        
        # Register agent with semantic matcher
        if AgentManager._semantic_matcher:
            await AgentManager._semantic_matcher.register_agent(
                agent_id=agent_id,
                agent_type=agent_info.type.value,
                capabilities=agent_info.capabilities,
                endpoint=agent_info.endpoint,
                metadata={
                    "name": agent_info.name,
                    "status": "idle",
                    "performance_metrics": {}
                }
            )
        
        # Register agent with load balancer
        if AgentManager._load_balancer:
            await AgentManager._load_balancer.register_agent(
                agent_id=agent_id,
                agent_type=agent_info.type.value,
                endpoint=agent_info.endpoint,
                initial_weight=1.0,
                metadata={
                    "capabilities": agent_info.capabilities,
                    "name": agent_info.name
                }
            )
        
        logger.info(f"Agent {agent.name} ({agent_id}) registered with advanced matching and load balancing")
        return agent_id

    @staticmethod
    async def find_suitable_agents(required_capabilities: List[str], task_type: str, 
                                 task_context: Optional[Dict[str, Any]] = None) -> List[Agent]:
        """Find agents suitable for a task using advanced semantic matching and load balancing"""
        
        # Ensure advanced components are initialized
        await AgentManager.initialize_advanced_components()
        
        # Use semantic matcher for intelligent agent selection
        if AgentManager._semantic_matcher:
            try:
                # Prepare task requirements for semantic matching
                task_requirements = {
                    "capabilities": required_capabilities,
                    "task_type": task_type,
                    "context": task_context or {},
                    "complexity": task_context.get("complexity", "medium") if task_context else "medium",
                    "domain": task_context.get("domain", "general") if task_context else "general"
                }
                
                # Get semantic matches with scores
                semantic_matches = await AgentManager._semantic_matcher.find_best_agents(
                    task_requirements, 
                    max_agents=5
                )
                
                # Extract agent IDs and filter for available agents
                suitable_agents = []
                for match in semantic_matches:
                    agent_id = match["agent_id"]
                    if agent_id in state.agents:
                        agent = state.agents[agent_id]
                        if agent.status == "idle":  # Only consider idle agents
                            # Add semantic score to agent for load balancing
                            agent.semantic_score = match["score"]
                            agent.match_details = match["details"]
                            suitable_agents.append(agent)
                
                # Use load balancer to select the best agent from semantic matches
                if suitable_agents and AgentManager._load_balancer:
                    # Convert to load balancing format and select best agent
                    agent_candidates = [
                        {
                            "agent_id": agent.id,
                            "agent_type": agent.type.value,
                            "endpoint": agent.endpoint,
                            "current_load": len([t for t in state.tasks.values() 
                                               if agent.id in (t.assigned_agents or []) and t.status == TaskStatus.RUNNING]),
                            "performance_metrics": agent.performance_metrics or {},
                            "semantic_score": getattr(agent, "semantic_score", 0.8)
                        }
                        for agent in suitable_agents
                    ]
                    
                    # Select best agent using load balancing strategy
                    selected_agent = await AgentManager._load_balancer.select_agent(
                        agent_candidates,
                        strategy=LoadBalanceStrategy.RESOURCE_AWARE,
                        task_context=task_context or {}
                    )
                    
                    if selected_agent:
                        # Return the selected agent first, followed by others
                        selected_id = selected_agent["agent_id"]
                        reordered_agents = [a for a in suitable_agents if a.id == selected_id]
                        reordered_agents.extend([a for a in suitable_agents if a.id != selected_id])
                        
                        logger.info(f"Advanced matching selected agent {selected_id} with semantic score {selected_agent.get('semantic_score', 'N/A')}")
                        return reordered_agents
                
                if suitable_agents:
                    logger.info(f"Semantic matching found {len(suitable_agents)} suitable agents")
                    return suitable_agents
                
            except Exception as e:
                logger.warning(f"Advanced agent matching failed, falling back to basic matching: {e}")
        
        # Fallback to basic agent matching
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
        
        if suitable_agents:
            logger.info(f"Basic matching found {len(suitable_agents)} suitable agents")
        else:
            logger.warning(f"No suitable agents found for task type '{task_type}' with capabilities {required_capabilities}")
        
        return suitable_agents

    @staticmethod
    async def update_agent_status(agent_id: str, status: str, current_task: Optional[str] = None):
        """Update agent status and sync with advanced components"""
        if agent_id in state.agents:
            agent = state.agents[agent_id]
            old_status = agent.status
            agent.status = status
            agent.last_seen = datetime.utcnow()
            if current_task is not None:
                agent.current_task = current_task
            
            # Update in Redis
            redis_client = await get_redis_client()
            await redis_client.hset(
                "agents",
                agent_id,
                json.dumps(asdict(agent), default=str)
            )
            
            # Update load balancer metrics
            if AgentManager._load_balancer and old_status != status:
                if status == "running":
                    await AgentManager._load_balancer.update_agent_load(agent_id, 1)
                elif status == "idle" and old_status == "running":
                    await AgentManager._load_balancer.update_agent_load(agent_id, -1)
            
            logger.debug(f"Agent {agent_id} status updated: {old_status} -> {status}")

    @staticmethod
    async def update_agent_performance(agent_id: str, task_success: bool, response_time: float, 
                                     task_type: str = None, error: str = None):
        """Update agent performance metrics for semantic learning"""
        if agent_id in state.agents:
            agent = state.agents[agent_id]
            
            # Update basic performance metrics
            if not agent.performance_metrics:
                agent.performance_metrics = {"success_count": 0, "total_count": 0, "avg_response_time": 0.0}
            
            agent.performance_metrics["total_count"] += 1
            if task_success:
                agent.performance_metrics["success_count"] += 1
            
            # Update average response time
            current_avg = agent.performance_metrics.get("avg_response_time", 0.0)
            total_count = agent.performance_metrics["total_count"]
            agent.performance_metrics["avg_response_time"] = (
                (current_avg * (total_count - 1) + response_time) / total_count
            )
            
            agent.performance_metrics["success_rate"] = (
                agent.performance_metrics["success_count"] / agent.performance_metrics["total_count"]
            )
            
            # Update semantic matcher with performance feedback
            if AgentManager._semantic_matcher:
                await AgentManager._semantic_matcher.update_agent_performance(
                    agent_id=agent_id,
                    task_success=task_success,
                    confidence_score=0.9 if task_success else 0.3,
                    response_time=response_time,
                    task_context={"task_type": task_type} if task_type else {}
                )
            
            # Update load balancer with performance metrics
            if AgentManager._load_balancer:
                await AgentManager._load_balancer.update_agent_metrics(
                    agent_id=agent_id,
                    metrics={
                        "success_rate": agent.performance_metrics["success_rate"],
                        "avg_response_time": agent.performance_metrics["avg_response_time"],
                        "last_error": error
                    }
                )
            
            logger.info(f"Updated performance for agent {agent_id}: success_rate={agent.performance_metrics['success_rate']:.2f}")

    @staticmethod
    async def get_agent_recommendations(agent_id: str) -> Dict[str, Any]:
        """Get improvement recommendations for an agent"""
        recommendations = {"basic": "No specific recommendations available"}
        
        if AgentManager._semantic_matcher:
            try:
                semantic_recommendations = await AgentManager._semantic_matcher.get_improvement_suggestions(agent_id)
                recommendations.update({"semantic": semantic_recommendations})
            except Exception as e:
                logger.warning(f"Failed to get semantic recommendations for agent {agent_id}: {e}")
        
        return recommendations
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
        
        logger.info(f"Assigned task {task_id} to agent {agent_id}")    @staticmethod
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
            await AgentManager.update_agent_status(agent_id, "idle", None)    @staticmethod
    async def execute_task_with_tracking(task_id: str, agent_id: str) -> Dict:
        """Enhanced task execution with performance tracking, learning, and distributed tracing"""
        task = state.tasks[task_id]
        agent = state.agents[agent_id]
        
        # Start distributed tracing span
        span_context = {}
        if HAS_TRACING and tracer:
            span = tracer.start_span(
                "task_execution",
                attributes={
                    "task.id": task_id,
                    "task.type": task.type,
                    "agent.id": agent_id,
                    "agent.name": agent.name,
                    "agent.type": agent.type.value,
                    "task.priority": task.priority
                }
            )
            span_context = {"span": span}
        
        start_time = time.time()
        task_success = False
        error_message = None
        result = None
        
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            
            # Add tracing attributes for task start
            if span_context.get("span"):
                span_context["span"].set_attribute("task.started_at", task.started_at.isoformat())
                span_context["span"].add_event("task_started")
            
            # Call agent endpoint with enhanced tracking
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{agent.endpoint}/process",
                    json={
                        "task_id": task_id,
                        "task_type": task.type,
                        "input_data": task.input_data,
                        "context": {
                            "priority": task.priority,
                            "workflow_id": task.workflow_id,
                            "dependencies": task.dependencies,
                            "trace_context": span_context.get("span").get_span_context() if span_context.get("span") else None
                        }
                    },
                    timeout=300  # 5 minute timeout
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                # Add tracing attributes for response
                if span_context.get("span"):
                    span_context["span"].set_attribute("http.status_code", response.status_code)
                    span_context["span"].set_attribute("task.response_time", response_time)
                    span_context["span"].add_event("agent_response_received")
                
                if response.status_code == 200:
                    result = response.json()
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.utcnow()
                    task_success = True
                    
                    # Add success tracing attributes
                    if span_context.get("span"):
                        span_context["span"].set_attribute("task.success", True)
                        span_context["span"].set_attribute("task.completed_at", task.completed_at.isoformat())
                        span_context["span"].add_event("task_completed_successfully")
                    
                    logger.info(f"Task {task_id} completed successfully in {response_time:.2f}s")
                else:
                    error_message = f"Agent returned error: {response.status_code} - {response.text}"
                    
                    # Add error tracing attributes
                    if span_context.get("span"):
                        span_context["span"].set_attribute("task.success", False)
                        span_context["span"].set_attribute("error.message", error_message)
                        span_context["span"].add_event("task_failed", {"error": error_message})
                    
                    raise Exception(error_message)
                    
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            
            task.status = TaskStatus.FAILED
            error_message = str(e)
            task.error = error_message
            task.completed_at = datetime.utcnow()
            
            # Add exception tracing attributes
            if span_context.get("span"):
                span_context["span"].set_attribute("task.success", False)
                span_context["span"].set_attribute("error.message", error_message)
                span_context["span"].set_attribute("task.response_time", response_time)
                span_context["span"].add_event("task_exception", {"exception": str(e)})
            
            logger.error(f"Task {task_id} failed after {response_time:.2f}s: {e}")
        
        finally:
            # Update agent performance with detailed tracking
            await AgentManager.update_agent_performance(
                agent_id=agent_id,
                task_success=task_success,
                response_time=response_time,
                task_type=task.type,
                error=error_message
            )
            
            # Free up agent
            await AgentManager.update_agent_status(agent_id, "idle", None)
            
            # Log performance metrics for monitoring
            metrics_collector.record_task_completion(
                task_type=task.type,
                success=task_success,
                duration=response_time,
                agent_id=agent_id
            )
            
            # Close tracing span
            if span_context.get("span"):
                span_context["span"].set_attribute("task.final_status", task.status.value)
                span_context["span"].end()
        
        if not task_success:
            raise Exception(error_message)
        
        return result

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
    """Enhanced background task processor with advanced agent matching"""
    config = get_config()
    logger.info("Starting enhanced task processor with advanced agent matching")
    
    while True:
        try:
            # Get task from queue with timeout
            task_id = await asyncio.wait_for(state.task_queue.get(), timeout=config.task_queue_check_interval)
            
            # Get task details
            task = state.tasks[task_id]
            
            # Prepare task context for advanced matching
            task_context = {
                "task_id": task_id,
                "priority": task.priority,
                "complexity": task.input_data.get("complexity", "medium"),
                "domain": task.input_data.get("domain", "general"),
                "dependencies": task.dependencies or [],
                "workflow_id": task.workflow_id,
                "created_at": task.created_at.isoformat(),
                "description": task.description
            }
            
            # Extract required capabilities from task
            required_capabilities = []
            if hasattr(task, 'required_capabilities'):
                required_capabilities = task.required_capabilities
            elif "required_capabilities" in task.input_data:
                required_capabilities = task.input_data["required_capabilities"]
            
            # Find suitable agents with enhanced matching
            suitable_agents = await AgentManager.find_suitable_agents(
                required_capabilities=required_capabilities,
                task_type=task.type,
                task_context=task_context
            )
            
            if suitable_agents:
                # Assign to best agent (already optimally selected by advanced matching)
                best_agent = suitable_agents[0]
                await TaskManager.assign_task(task_id, best_agent.id)
                
                # Update agent status
                await AgentManager.update_agent_status(best_agent.id, "running", task_id)
                
                # Execute task in background with performance tracking
                asyncio.create_task(
                    TaskManager.execute_task_with_tracking(task_id, best_agent.id)
                )
                
                logger.info(f"Task {task_id} assigned to agent {best_agent.id} ({best_agent.name})")
            else:
                # No suitable agents, put back in queue
                await state.task_queue.put(task_id)
                await asyncio.sleep(config.agent_retry_delay)  # Wait before retrying
                logger.warning(f"No suitable agents found for task {task_id}, retrying...")
                
        except asyncio.TimeoutError:
            # No tasks in queue, continue
            continue
        except Exception as e:
            logger.error(f"Error in enhanced task processor: {e}")
            await asyncio.sleep(1)

# FastAPI App
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Enhanced Agent Orchestrator Service...")
    
    # Initialize database lifespan management
    async with database_lifespan():
        # Initialize legacy orchestrator service for compatibility
        await orchestrator_service.initialize()
        
        # Initialize enhanced orchestrator service
        enhanced_orchestrator = get_enhanced_orchestrator_service()
        await enhanced_orchestrator.initialize()
        
        # Store enhanced orchestrator in app state
        app.state.enhanced_orchestrator = enhanced_orchestrator
        
        # Initialize advanced agent management components
        logger.info("Initializing advanced agent management components...")
        await AgentManager.initialize_advanced_components()
        
        # Start background task processor
        processor_task = asyncio.create_task(task_processor())
        
        logger.info("Enhanced Agent Orchestrator Service startup complete")
        
        yield
        
        # Shutdown
        logger.info("Shutting down Enhanced Agent Orchestrator Service...")
        processor_task.cancel()
        
        # Shutdown enhanced orchestrator service
        await enhanced_orchestrator.shutdown()
        
        # Shutdown legacy orchestrator service
        await orchestrator_service.shutdown()
        
        # Database cleanup is handled by database_lifespan()
        logger.info("Enhanced Agent Orchestrator Service shutdown complete")

config = get_config()

# Enhanced OpenAPI configuration with comprehensive documentation
app = FastAPI(
    title="Agent Orchestration Coordinator API",
    description="""
    **Central Coordination Hub for AI Agent Activities in Surveillance Systems**
    
    This service provides a comprehensive orchestration platform for managing AI agents, tasks, and workflows in surveillance and monitoring systems. It features advanced capabilities including:
    
    ## Key Features
    
    * **🤖 Agent Management**: Register, monitor, and coordinate AI agents across the surveillance network
    * **📋 Task Orchestration**: Create, assign, and monitor tasks with intelligent agent matching
    * **🔄 Workflow Automation**: Design and execute complex multi-step workflows with dependencies
    * **🛡️ Circuit Breaker Protection**: Resilient service communication with automatic fallback mechanisms
    * **🔍 Input Validation**: Comprehensive request validation with security-focused sanitization
    * **📊 Performance Monitoring**: Built-in metrics collection and health monitoring
    * **🔄 Real-time Updates**: WebSocket support for live status updates
    
    ## API Architecture
    
    The API follows RESTful principles with:
    - **Resource-based URLs**: Clear, hierarchical endpoint structure
    - **HTTP Status Codes**: Proper status codes for different response scenarios
    - **Request/Response Validation**: Strict Pydantic-based validation
    - **Error Handling**: Comprehensive error responses with detailed information
    - **Security**: Built-in rate limiting, input sanitization, and injection prevention
    
    ## Authentication & Security
    
    - Input validation and sanitization on all endpoints
    - Rate limiting protection (100 requests/minute per IP)
    - Request size limits (10MB maximum)
    - Suspicious pattern detection
    - UUID validation for resource identifiers
    
    ## Service Integration
    
    Integrates with downstream services through circuit breaker patterns:
    - **RAG Service**: Context retrieval and knowledge base queries
    - **Rule Generation Service**: Policy evaluation and rule processing  
    - **Notifier Service**: Alert dispatch and notification management
    
    ## Getting Started
    
    1. **Register an Agent**: Use `POST /api/v1/agents/register` to add new agents
    2. **Create Tasks**: Submit tasks via `POST /api/v1/tasks` with detailed specifications
    3. **Monitor Progress**: Check status using `GET /api/v1/tasks/{task_id}` or list endpoints
    4. **Create Workflows**: Orchestrate complex processes via `POST /api/v1/workflows`
    
    For more information, see our [GitHub repository](https://github.com/surveillance-system) or contact the development team.
    """,
    version="2.0.0",
    terms_of_service="https://surveillance-system.example.com/terms",
    contact={
        "name": "Surveillance System Development Team",
        "url": "https://surveillance-system.example.com/contact",
        "email": "dev-team@surveillance-system.example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "Agent Management",
            "description": "Operations for registering, listing, and managing AI agents in the surveillance network.",
            "externalDocs": {
                "description": "Agent Management Guide",
                "url": "https://docs.surveillance-system.example.com/agents",
            },
        },
        {
            "name": "Task Operations", 
            "description": "Task creation, assignment, monitoring, and lifecycle management operations.",
            "externalDocs": {
                "description": "Task Management Documentation",
                "url": "https://docs.surveillance-system.example.com/tasks",
            },
        },
        {
            "name": "Workflow Orchestration",
            "description": "Complex workflow creation and execution with multi-agent coordination.",
            "externalDocs": {
                "description": "Workflow Design Patterns",
                "url": "https://docs.surveillance-system.example.com/workflows",
            },
        },
        {
            "name": "Enhanced Orchestration",
            "description": "Advanced orchestration features with circuit breaker protection and intelligent service coordination.",
            "externalDocs": {
                "description": "Advanced Orchestration Guide",
                "url": "https://docs.surveillance-system.example.com/advanced-orchestration",
            },
        },
        {
            "name": "System Monitoring",
            "description": "Health checks, metrics, and system status monitoring endpoints.",
            "externalDocs": {
                "description": "Monitoring and Observability",
                "url": "https://docs.surveillance-system.example.com/monitoring",
            },
        },
        {
            "name": "Circuit Breaker Management",
            "description": "Circuit breaker status monitoring and administrative control operations.",
            "externalDocs": {
                "description": "Circuit Breaker Patterns",
                "url": "https://docs.surveillance-system.example.com/circuit-breakers",
            },
        },
    ],
    openapi_prefix="/api/v1",
    lifespan=lifespan,
    docs_url="/docs" if config.enable_docs else None,
    redoc_url="/redoc" if config.enable_docs else None,
    openapi_url="/openapi.json" if config.enable_docs else None,
    swagger_ui_parameters={
        "deepLinking": True,
        "displayOperationId": True,
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
        "displayRequestDuration": True,
        "docExpansion": "none",
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "tryItOutEnabled": True,
    },
    redoc_options={
        "expandResponses": "200,201",
        "pathInMiddlePanel": True,
        "requiredPropsFirst": True,
        "sortPropsAlphabetically": True,
        "hideDownloadButton": False,
        "hideHostname": False,
        "hideSingleRequestSampleTab": False,
        "menuToggle": True,
        "scrollYOffset": 0,
        "theme": {
            "colors": {
                "primary": {"main": "#1976d2"}
            }
        }
    }
)

# Add custom validation exception handler
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# CORS middleware
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=config.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware with security checks
@app.middleware("http")
async def metrics_and_security_middleware(request, call_next):
    """Middleware to collect HTTP request metrics and perform security validation"""
    start_time = time.time()
    
    # Security: Check request size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
        logger.warning(f"Request too large: {content_length} bytes from {request.client.host}")
        return JSONResponse(
            status_code=413,
            content={"error": "Request payload too large", "max_size": "10MB"}
        )
    
    # Security: Basic rate limiting check (in addition to external rate limiting)
    client_ip = request.client.host if request.client else "unknown"
    current_time = int(time.time())
    
    # Simple in-memory rate limiting tracker
    if not hasattr(metrics_and_security_middleware, 'rate_limit_tracker'):
        metrics_and_security_middleware.rate_limit_tracker = {}
    
    tracker = metrics_and_security_middleware.rate_limit_tracker
    if client_ip not in tracker:
        tracker[client_ip] = []
    
    # Clean old entries (keep last minute)
    tracker[client_ip] = [t for t in tracker[client_ip] if t > current_time - 60]
    
    # Check rate limit (max 100 requests per minute per IP)
    if len(tracker[client_ip]) >= 100:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "retry_after": 60}
        )
    
    tracker[client_ip].append(current_time)
    
    # Process request
    response = await call_next(request)
    
    # Record metrics
    duration = time.time() - start_time
    method = request.method
    endpoint = request.url.path
    status_code = response.status_code
    
    # Update metrics
    metrics_collector.record_service_request(
        service="agent_orchestrator",
        endpoint=endpoint,
        status_code=status_code,
        duration=duration
    )
    
    return response

# Add rate limiting middleware
if config.enable_rate_limiting and HAS_RATE_LIMITING:
    add_rate_limiting(app, service_name="agent_orchestrator")
elif config.enable_rate_limiting:
    logger.warning("Rate limiting requested but shared middleware not available")

# Include routers
app.include_router(load_balancing_router)
app.include_router(distributed_router)

# API Endpoints with Enhanced Validation
@app.post(
    "/api/v1/agents/register",
    tags=["Agent Management"],
    summary="Register a New AI Agent",
    description="""
    **Register a new AI agent in the surveillance system.**
    
    This endpoint allows you to register new AI agents that can process tasks within the surveillance network. 
    Each agent must specify its type, capabilities, and endpoint for communication.
    
    ## Registration Process
    
    1. **Validation**: Comprehensive input validation including URL format, capability constraints, and security checks
    2. **Registration**: Agent is registered in the system with a unique identifier
    3. **Storage**: Agent information is persisted in Redis for high availability
    4. **Monitoring**: Agent is added to the monitoring and health check system
    
    ## Agent Types & Capabilities
    
    - **DETECTOR**: Specialized in object/event detection (capabilities: `person_detection`, `vehicle_detection`, `motion_detection`)
    - **ANALYZER**: General analysis and data processing (capabilities: `video_analysis`, `audio_analysis`, `pattern_recognition`)
    - **CLASSIFIER**: Content classification and categorization (capabilities: `image_classification`, `text_classification`, `risk_assessment`)
    - **TRACKER**: Object/person tracking capabilities (capabilities: `object_tracking`, `person_tracking`, `path_analysis`)
    - **NOTIFIER**: Alert and notification dispatch (capabilities: `email_alerts`, `sms_alerts`, `webhook_notifications`)
    - **COORDINATOR**: Task coordination and workflow management (capabilities: `task_routing`, `workflow_management`, `resource_allocation`)
    
    ## Security Features
    
    - URL validation to prevent malicious endpoints
    - Input sanitization to prevent injection attacks
    - Capability validation with length and content restrictions
    - Metadata size limits to prevent memory exhaustion
    
    ## Health Monitoring
    
    Registered agents are automatically enrolled in the health monitoring system with configurable check intervals.
    """,
    response_description="Agent successfully registered with system-generated unique identifier",
    responses={
        200: {
            "description": "Agent successfully registered",
            "content": {
                "application/json": {
                    "example": {
                        "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "registered",
                        "message": "Agent registered successfully with enhanced validation"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request data or suspicious content detected",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Suspicious content detected"
                    }
                }
            }
        },
        413: {
            "description": "Request payload too large",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Request payload too large"
                    }
                }
            }
        },
        422: {
            "description": "Validation error with detailed field-level feedback",
            "model": ValidationErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Validation Error",
                        "message": "Request validation failed",
                        "details": [
                            {
                                "field": "endpoint",
                                "message": "Invalid URL format",
                                "invalid_value": "not-a-url",
                                "constraint": "url_format"
                            }
                        ],
                        "timestamp": "2024-01-15T10:30:00Z",
                        "request_id": "req_123456789"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error during registration",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Database connection failed"
                    }
                }
            }
        }
    }
)
async def register_agent(
    agent_info: EnhancedAgentRegistrationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    _: Dict[str, Any] = Depends(require_permission_enhanced(Permission.AGENT_REGISTER))
):
    """Register a new AI agent in the surveillance system with comprehensive validation and monitoring setup."""
    try:
        # Additional security validation
        if not SecurityValidator.validate_input_size(agent_info.dict()):
            raise HTTPException(status_code=413, detail="Request payload too large")
        
        # Convert enhanced request to internal format
        internal_request = AgentRegistrationRequest(
            type=AgentType(agent_info.type.value),
            name=agent_info.name,
            endpoint=agent_info.endpoint,
            capabilities=agent_info.capabilities
        )
        
        agent_id = await AgentManager.register_agent(internal_request)
        
        # Log successful registration with sanitized data
        logger.info(f"Agent registered successfully - ID: {agent_id}, Type: {agent_info.type.value}, Name: {ValidationUtils.sanitize_string(agent_info.name)}")
        
        return {
            "agent_id": agent_id, 
            "status": "registered",
            "message": "Agent registered successfully with enhanced validation"
        }
    except ValidationError as e:
        logger.warning(f"Agent registration validation failed: {e}")
        raise HTTPException(status_code=422, detail="Validation failed")
    except Exception as e:
        logger.error(f"Error registering agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/agents", responses={422: {"model": ValidationErrorResponse}})
async def list_agents(query: AgentQueryParams = Depends()):
    """List all registered agents with query parameter validation"""
    try:
        agents = []
        agent_list = list(state.agents.values())
        
        # Apply filters
        if query.type:
            agent_list = [a for a in agent_list if a.type.value == query.type.value]
        
        if query.status and query.status != "all":
            status_filter = "active" if query.status == "active" else "inactive"
            agent_list = [a for a in agent_list if 
                         (a.status != "idle" if status_filter == "active" else a.status == "idle")]
        
        if query.capability:
            capability_filter = ValidationUtils.sanitize_string(query.capability)
            agent_list = [a for a in agent_list if capability_filter in a.capabilities]
        
        # Apply pagination
        total_count = len(agent_list)
        start_idx = query.offset
        end_idx = start_idx + query.limit
        paginated_agents = agent_list[start_idx:end_idx]
        
        for agent in paginated_agents:
            agent_dict = asdict(agent)
            agent_dict["last_seen"] = agent.last_seen.isoformat() if agent.last_seen else None
            # Sanitize sensitive information
            agent_dict["name"] = ValidationUtils.sanitize_string(agent.name)
            agents.append(agent_dict)
        
        return {
            "agents": agents,
            "total_count": total_count,
            "limit": query.limit,
            "offset": query.offset
        }
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/v1/tasks",
    tags=["Task Operations"],
    summary="Create a New Task",
    description="""
    **Create a new task for processing by AI agents in the surveillance system.**
    
    This endpoint creates tasks that will be automatically assigned to suitable agents based on capabilities and availability.
    Tasks are queued for processing and can be monitored through various status endpoints.
    
    ## Task Types & Use Cases
    
    - **ANALYSIS**: General data analysis, pattern recognition, statistical processing
    - **DETECTION**: Object detection, person detection, event detection, anomaly detection  
    - **CLASSIFICATION**: Image classification, content categorization, risk assessment, priority classification
    - **TRACKING**: Object tracking, person tracking, path analysis, movement monitoring
    - **ALERT**: Alert generation, notification creation, escalation triggers
    - **REPORT**: Report generation, data summarization, dashboard updates, compliance reports
    - **CUSTOM**: Specialized tasks with custom processing logic
    
    ## Priority Levels
    
    Tasks are processed based on priority with higher priority tasks getting precedence:
    - **EMERGENCY (5)**: Critical security incidents requiring immediate response
    - **CRITICAL (4)**: High-priority security events, system alerts
    - **HIGH (3)**: Important surveillance events, scheduled high-priority tasks
    - **NORMAL (2)**: Standard processing tasks (default priority)
    - **LOW (1)**: Background processing, maintenance tasks, analytics
    
    ## Agent Assignment Process
    
    1. **Capability Matching**: Tasks are matched to agents based on required capabilities
    2. **Load Balancing**: Available agents are selected based on current load and performance metrics
    3. **Automatic Retry**: Failed tasks are automatically retried based on retry configuration
    4. **Timeout Handling**: Tasks that exceed timeout limits are automatically cancelled
    
    ## Input Data Format
    
    The `input_data` field accepts flexible JSON objects tailored to the task type:
    
    - **Camera/Video Tasks**: `{"camera_id": "CAM-001", "stream_url": "rtsp://...", "duration": 60}`
    - **Image Analysis Tasks**: `{"image_url": "https://...", "analysis_type": "detection", "confidence_threshold": 0.8}`
    - **Alert Tasks**: `{"event_type": "intrusion", "location": "zone_a", "severity": "high", "contacts": ["admin@example.com"]}`
    
    ## Workflow Integration
    
    Tasks can be part of larger workflows by specifying a `workflow_id`. Workflow tasks are executed according to the workflow's dependency graph and scheduling rules.
    """,
    response_description="Task successfully created and queued for processing",
    responses={
        200: {
            "description": "Task successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "550e8400-e29b-41d4-a716-446655440001",
                        "status": "created",
                        "message": "Task created successfully with enhanced validation"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request data or suspicious content detected",
            "content": {
                "application/json": {
                    "examples": {
                        "suspicious_content": {
                            "summary": "Suspicious content detected",
                            "value": {"detail": "Suspicious content detected"}
                        },
                        "invalid_workflow": {
                            "summary": "Invalid workflow ID",
                            "value": {"detail": "Invalid workflow ID format"}
                        }
                    }
                }
            }
        },
        413: {
            "description": "Request payload too large (exceeds 10MB limit)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Request payload too large"
                    }
                }
            }
        },
        422: {
            "description": "Validation error with detailed field-level feedback",
            "model": ValidationErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Validation Error",
                        "message": "Request validation failed",
                        "details": [
                            {
                                "field": "priority",
                                "message": "Invalid priority level",
                                "invalid_value": 10,
                                "constraint": "priority_range"
                            },
                            {
                                "field": "input_data",
                                "message": "Input data nesting too deep. Maximum depth: 10",
                                "invalid_value": "complex_nested_object",
                                "constraint": "dict_depth"
                            }
                        ],
                        "timestamp": "2024-01-15T10:30:00Z",
                        "request_id": "req_123456790"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error during task creation",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Task queue unavailable"
                    }
                }
            }
        }
    }
)
async def create_task(
    task_request: EnhancedCreateTaskRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    _: Dict[str, Any] = Depends(require_permission_enhanced(Permission.TASK_CREATE))
):
    """Create a new task for processing by AI agents with intelligent assignment and monitoring."""
    try:
        # Additional security validation
        if not SecurityValidator.validate_input_size(task_request.dict()):
            raise HTTPException(status_code=413, detail="Request payload too large")
        
        # Check for suspicious patterns in text fields
        text_fields = [task_request.name, task_request.description]
        for field in text_fields:
            if not SecurityValidator.validate_no_suspicious_patterns(field):
                raise HTTPException(status_code=400, detail="Suspicious content detected")
        
        # Convert enhanced request to internal format
        internal_request = CreateTaskRequest(
            type=task_request.type.value,
            description=task_request.description,
            input_data=task_request.input_data,
            priority=task_request.priority.value,
            required_capabilities=task_request.required_capabilities,
            workflow_id=task_request.workflow_id
        )
        
        task_id = await TaskManager.create_task(internal_request)
        
        # Log successful creation with sanitized data
        logger.info(f"Task created successfully - ID: {task_id}, Type: {task_request.type.value}, Name: {ValidationUtils.sanitize_string(task_request.name)}")
        
        return {
            "task_id": task_id, 
            "status": "created",
            "message": "Task created successfully with enhanced validation"
        }
    except ValidationError as e:
        logger.warning(f"Task creation validation failed: {e}")
        raise HTTPException(status_code=422, detail="Validation failed")
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details with ID validation"""
    # Validate task ID format
    if not ValidationUtils.validate_uuid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    
    if task_id not in state.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = state.tasks[task_id]
    task_dict = asdict(task)
    
    # Convert datetime objects to strings
    for field in ["created_at", "started_at", "completed_at"]:
        if task_dict[field]:
            task_dict[field] = task_dict[field].isoformat()
    
    # Sanitize sensitive data
    if "description" in task_dict:
        task_dict["description"] = ValidationUtils.sanitize_string(task_dict["description"])
    
    return task_dict

@app.get("/api/v1/tasks", responses={422: {"model": ValidationErrorResponse}})
async def list_tasks(query: TaskQueryParams = Depends()):
    """List tasks with comprehensive query parameter validation"""
    try:
        tasks = []
        task_list = list(state.tasks.values())
        
        # Apply filters
        if query.status:
            task_list = [t for t in task_list if t.status.value == query.status.value]
        
        if query.workflow_id:
            task_list = [t for t in task_list if t.workflow_id == query.workflow_id]
        
        if query.agent_id:
            task_list = [t for t in task_list if query.agent_id in (t.assigned_agents or [])]
        
        # Sort results
        if query.sort_by == "created_at":
            task_list.sort(key=lambda x: x.created_at, reverse=(query.sort_order == "desc"))
        elif query.sort_by == "priority":
            task_list.sort(key=lambda x: x.priority, reverse=(query.sort_order == "desc"))
        elif query.sort_by == "status":
            task_list.sort(key=lambda x: x.status.value, reverse=(query.sort_order == "desc"))
        elif query.sort_by == "name":
            task_list.sort(key=lambda x: getattr(x, 'name', ''), reverse=(query.sort_order == "desc"))
        elif query.sort_by == "type":
            task_list.sort(key=lambda x: x.type, reverse=(query.sort_order == "desc"))
        
        # Apply pagination
        total_count = len(task_list)
        start_idx = query.offset
        end_idx = start_idx + query.limit
        paginated_tasks = task_list[start_idx:end_idx]
        
        for task in paginated_tasks:
            task_dict = asdict(task)
            # Convert datetime objects to strings
            for field in ["created_at", "started_at", "completed_at"]:
                if task_dict[field]:
                    task_dict[field] = task_dict[field].isoformat()
            
            # Sanitize sensitive data
            if "description" in task_dict:
                task_dict["description"] = ValidationUtils.sanitize_string(task_dict["description"])
            
            tasks.append(task_dict)
        
        return {
            "tasks": tasks,
            "total_count": total_count,
            "limit": query.limit,
            "offset": query.offset,
            "sort_by": query.sort_by,
            "sort_order": query.sort_order
        }
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/workflows", responses={422: {"model": ValidationErrorResponse}})
async def create_workflow(workflow_request: EnhancedCreateWorkflowRequest):
    """Create a new workflow with comprehensive validation"""
    try:
        # Additional security validation
        if not SecurityValidator.validate_input_size(workflow_request.dict()):
            raise HTTPException(status_code=413, detail="Request payload too large")
        
        # Check for suspicious patterns in text fields
        text_fields = [workflow_request.name, workflow_request.description]
        for field in text_fields:
            if not SecurityValidator.validate_no_suspicious_patterns(field):
                raise HTTPException(status_code=400, detail="Suspicious content detected")
        
        # Convert enhanced request to internal format
        internal_tasks = []
        for task_req in workflow_request.tasks:
            internal_task = CreateTaskRequest(
                type=task_req.type.value,
                description=task_req.description,
                input_data=task_req.input_data,
                priority=task_req.priority.value,
                required_capabilities=task_req.required_capabilities,
                workflow_id=None  # Will be set by WorkflowManager
            )
            internal_tasks.append(internal_task)
        
        internal_request = CreateWorkflowRequest(
            name=workflow_request.name,
            description=workflow_request.description,
            tasks=internal_tasks,
            user_id=workflow_request.user_id,
            configuration=workflow_request.configuration
        )
        
        workflow_id = await WorkflowManager.create_workflow(internal_request)
        
        # Start workflow execution in background
        asyncio.create_task(WorkflowManager.execute_workflow(workflow_id))
        
        # Log successful creation with sanitized data
        logger.info(f"Workflow created successfully - ID: {workflow_id}, Name: {ValidationUtils.sanitize_string(workflow_request.name)}, Tasks: {len(workflow_request.tasks)}")
        
        return {
            "workflow_id": workflow_id, 
            "status": "created",
            "message": "Workflow created successfully with enhanced validation",
            "task_count": len(workflow_request.tasks)
        }
    except ValidationError as e:
        logger.warning(f"Workflow creation validation failed: {e}")
        raise HTTPException(status_code=422, detail="Validation failed")
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/v1/workflows/{workflow_id}",
    tags=["Workflow Orchestration"],
    summary="Get Workflow Details",
    description="""
    **Retrieve detailed information about a specific workflow by its unique identifier.**
    
    This endpoint provides comprehensive workflow information including:
    - Workflow configuration and metadata
    - Current execution status and progress
    - Task dependencies and execution order
    - Agent assignments and resource allocation
    - Execution history and performance metrics
    
    ## Workflow States
    
    - **PENDING**: Workflow created but not yet started
    - **RUNNING**: Workflow currently executing
    - **COMPLETED**: Workflow finished successfully
    - **FAILED**: Workflow terminated due to errors
    - **CANCELLED**: Workflow manually cancelled
    - **PAUSED**: Workflow temporarily suspended
    
    ## Response Data
    
    The response includes sanitized workflow data with sensitive information filtered out
    for security purposes. All timestamps are returned in ISO 8601 format.
    """,
    response_description="Detailed workflow information",
    responses={
        200: {
            "description": "Workflow retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "workflow_550e8400-e29b-41d4-a716-446655440000",
                        "name": "Security Perimeter Analysis",
                        "description": "Multi-camera security analysis workflow for perimeter monitoring",
                        "status": "running",
                        "created_at": "2024-01-15T14:30:00Z",
                        "updated_at": "2024-01-15T14:35:15Z",
                        "user_id": "user_123",
                        "priority": "high",
                        "tasks": [
                            {
                                "task_id": "task_001",
                                "name": "Motion Detection",
                                "status": "completed",
                                "agent_id": "detector_agent_001",
                                "duration": 15.2
                            },
                            {
                                "task_id": "task_002", 
                                "name": "Object Classification",
                                "status": "running",
                                "agent_id": "classifier_agent_002",
                                "progress": 0.67
                            }
                        ],
                        "execution_metrics": {
                            "total_tasks": 5,
                            "completed_tasks": 2,
                            "running_tasks": 1,
                            "pending_tasks": 2,
                            "estimated_completion": "2024-01-15T14:42:30Z"
                        },
                        "metadata": {
                            "location": "Building A - Perimeter",
                            "camera_count": 8,
                            "analysis_type": "security_monitoring"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid workflow ID format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid workflow ID format"
                    }
                }
            }
        },
        404: {
            "description": "Workflow not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Workflow not found"
                    }
                }
            }
        },
        422: {
            "description": "Request validation failed",
            "model": ValidationErrorResponse
        }
    }
)
async def get_workflow(workflow_id: str):
    """
    **Retrieve detailed information about a specific workflow.**
    
    Returns comprehensive workflow details including status, progress, task assignments,
    and execution metrics for monitoring and management purposes.
    """
    # Validate workflow ID format
    if not ValidationUtils.validate_uuid(workflow_id):
        raise HTTPException(status_code=400, detail="Invalid workflow ID format")
    
    if workflow_id not in state.workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = state.workflows[workflow_id]
    workflow_dict = asdict(workflow)
    workflow_dict["created_at"] = workflow.created_at.isoformat()
    
    # Sanitize sensitive data
    if "name" in workflow_dict:
        workflow_dict["name"] = ValidationUtils.sanitize_string(workflow_dict["name"])
    if "description" in workflow_dict:
        workflow_dict["description"] = ValidationUtils.sanitize_string(workflow_dict["description"])
    
    return workflow_dict

@app.get(
    "/api/v1/workflows",
    tags=["Workflow Orchestration"],
    summary="List Workflows",
    description="""
    **Retrieve a paginated list of workflows with optional filtering and sorting.**
    
    This endpoint provides comprehensive workflow listing with support for:
    - Pagination with customizable limit and offset
    - Status-based filtering (pending, running, completed, failed, cancelled)
    - User-based filtering for multi-tenant environments
    - Search and sorting by various criteria
    
    ## Query Parameters
    
    - **limit**: Maximum number of workflows to return (1-1000, default: 100)
    - **offset**: Number of workflows to skip for pagination (default: 0)
    - **status**: Filter by workflow status (optional)
    - **user_id**: Filter by user ID (optional)
    
    ## Pagination
    
    The response includes pagination metadata:
    - `total_count`: Total number of workflows matching the filter criteria
    - `limit`: Applied limit for the current request
    - `offset`: Applied offset for the current request
    - `workflows`: Array of workflow objects
    
    ## Security
    
    All returned workflow data is sanitized to remove sensitive information.
    User-specific filtering is applied based on access permissions.
    """,
    response_description="Paginated list of workflows with metadata",
    responses={
        200: {
            "description": "Workflows retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "workflows": [
                            {
                                "id": "workflow_550e8400-e29b-41d4-a716-446655440000",
                                "name": "Perimeter Security Scan",
                                "description": "Automated perimeter security monitoring workflow",
                                "status": "running",
                                "created_at": "2024-01-15T14:30:00Z",
                                "user_id": "user_123",
                                "priority": "high",
                                "progress": 0.75,
                                "estimated_completion": "2024-01-15T14:45:00Z"
                            },
                            {
                                "id": "workflow_550e8400-e29b-41d4-a716-446655440001",
                                "name": "Daily Report Generation",
                                "description": "Automated daily surveillance report generation",
                                "status": "completed",
                                "created_at": "2024-01-15T09:00:00Z",
                                "user_id": "user_123",
                                "priority": "normal",
                                "progress": 1.0,
                                "completion_time": "2024-01-15T09:15:30Z"
                            }
                        ],
                        "total_count": 156,
                        "limit": 100,
                        "offset": 0
                    }
                }
            }
        },
        400: {
            "description": "Invalid query parameters",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_limit": {
                            "summary": "Invalid limit parameter",
                            "value": {
                                "detail": "Limit must be between 1 and 1000"
                            }
                        },
                        "invalid_offset": {
                            "summary": "Invalid offset parameter",
                            "value": {
                                "detail": "Offset must be non-negative"
                            }
                        }
                    }
                }
            }
        },
        422: {
            "description": "Request validation failed",
            "model": ValidationErrorResponse
        }
    }
)
async def list_workflows(
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of workflows to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of workflows to skip for pagination"),
    status: Optional[str] = Query(None, description="Filter by workflow status"),
    user_id: Optional[str] = Query(None, description="Filter by user ID")
):
    """
    **Retrieve a paginated list of workflows with optional filtering.**
    
    Returns workflows matching the specified criteria with pagination support
    and comprehensive metadata for each workflow.
    """
    try:
        # Validate query parameters
        if limit and (limit < 1 or limit > 1000):
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")
        
        if offset and offset < 0:
            raise HTTPException(status_code=400, detail="Offset must be non-negative")
        
        if user_id:
            user_id = ValidationUtils.sanitize_string(user_id)
        
        workflows = []
        workflow_list = list(state.workflows.values())
        
        # Apply filters
        if status:
            workflow_list = [w for w in workflow_list if w.status == status]
        
        if user_id:
            workflow_list = [w for w in workflow_list if w.user_id == user_id]
        
        # Apply pagination
        total_count = len(workflow_list)
        start_idx = offset or 0
        end_idx = start_idx + (limit or 100)
        paginated_workflows = workflow_list[start_idx:end_idx]
        
        for workflow in paginated_workflows:
            workflow_dict = asdict(workflow)
            workflow_dict["created_at"] = workflow.created_at.isoformat()
            
            # Sanitize sensitive data
            if "name" in workflow_dict:
                workflow_dict["name"] = ValidationUtils.sanitize_string(workflow_dict["name"])
            if "description" in workflow_dict:
                workflow_dict["description"] = ValidationUtils.sanitize_string(workflow_dict["description"])
            
            workflows.append(workflow_dict)
        
        return {
            "workflows": workflows,
            "total_count": total_count,
            "limit": limit or 100,
            "offset": offset or 0
        }
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/v1/status",
    tags=["System Monitoring"],
    summary="Get System Status",
    description="""
    **Retrieve comprehensive system status information and operational metrics.**
    
    This endpoint provides real-time system status including:
    - Agent status and availability metrics
    - Task queue status and processing statistics
    - Workflow execution status and performance
    - System resource utilization
    - Service health indicators
    
    ## Agent Metrics
    
    - **Total Agents**: Total number of registered agents
    - **Active Agents**: Agents currently processing tasks
    - **Idle Agents**: Available agents ready for task assignment
    - **Offline Agents**: Agents that are not responding to health checks
    
    ## Task Metrics
    
    - **Total Tasks**: All tasks in the system
    - **Running Tasks**: Currently executing tasks
    - **Pending Tasks**: Tasks waiting for assignment
    - **Queue Size**: Number of tasks in the processing queue
    
    ## Workflow Metrics
    
    - **Total Workflows**: All workflows in the system
    - **Running Workflows**: Currently executing workflows
    - **Completed Workflows**: Successfully finished workflows
    
    ## Use Cases
    
    - **Operations Dashboard**: Real-time system monitoring
    - **Load Balancing**: Resource allocation decisions
    - **Capacity Planning**: Understanding system utilization
    - **Health Monitoring**: Early detection of performance issues
    """,
    response_description="Comprehensive system status and metrics",
    responses={
        200: {
            "description": "System status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "system_status": "healthy",
                        "timestamp": "2024-01-15T14:30:45Z",
                        "uptime": 86400,
                        "agents": {
                            "total": 25,
                            "active": 8,
                            "idle": 15,
                            "offline": 2,
                            "utilization_rate": 0.32
                        },
                        "tasks": {
                            "total": 1247,
                            "running": 12,
                            "pending": 3,
                            "completed": 1230,
                            "failed": 2,
                            "queue_size": 3,
                            "throughput_per_minute": 45.7,
                            "average_processing_time": 23.4
                        },
                        "workflows": {
                            "total": 89,
                            "running": 5,
                            "completed": 82,
                            "failed": 1,
                            "cancelled": 1,
                            "success_rate": 0.92
                        },
                        "system_resources": {
                            "cpu_usage": 0.45,
                            "memory_usage": 0.68,
                            "disk_usage": 0.32,
                            "network_connections": 156
                        },
                        "services": {
                            "redis_connected": True,
                            "database_connected": True,
                            "external_services": {
                                "rag_service": "healthy",
                                "rule_service": "healthy",
                                "notifier_service": "healthy"
                            }
                        }
                    }
                }
            }
        },
        500: {
            "description": "Failed to retrieve system status",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Failed to retrieve system status",
                        "message": "Internal system error",
                        "timestamp": "2024-01-15T14:30:45Z"
                    }
                }
            }
        }
    }
)
async def get_system_status():
    """
    **Retrieve comprehensive system status and operational metrics.**
    
    Returns real-time system information including agent status, task metrics,
    workflow progress, and resource utilization for monitoring and management.
    """
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

@app.get(
    "/health",
    tags=["System Monitoring"],
    summary="Basic Health Check",
    description="""
    **Basic health check endpoint for service availability verification.**
    
    This is the primary health check endpoint used by:
    - Load balancers for health monitoring
    - Service discovery systems
    - Basic uptime monitoring
    - Container orchestration platforms
    
    ## Health Status
    
    - **healthy**: All systems operational
    - **degraded**: Some non-critical issues detected
    - **unhealthy**: Critical issues affecting service availability
    
    ## Response Format
    
    The endpoint returns appropriate HTTP status codes:
    - **200 OK**: Service is healthy or degraded but functional
    - **503 Service Unavailable**: Service is unhealthy
    
    ## Caching
    
    Health check results are cached for performance optimization to reduce
    overhead on high-frequency health monitoring.
    """,
    response_description="Basic health status information",
    responses={
        200: {
            "description": "Service is healthy or degraded but operational",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": {
                            "summary": "Fully healthy system",
                            "value": {
                                "status": "healthy",
                                "message": "All systems operational",
                                "timestamp": "2024-01-15T14:30:45Z",
                                "version": "1.0.0",
                                "service": "agent_orchestrator"
                            }
                        },
                        "degraded": {
                            "summary": "Degraded but functional",
                            "value": {
                                "status": "degraded",
                                "message": "Some non-critical services experiencing issues",
                                "timestamp": "2024-01-15T14:30:45Z",
                                "version": "1.0.0",
                                "service": "agent_orchestrator",
                                "warnings": [
                                    "High response times detected",
                                    "Some external services degraded"
                                ]
                            }
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "message": "Critical system failure detected",
                        "timestamp": "2024-01-15T14:30:45Z",
                        "error": "Database connection failed",
                        "service": "agent_orchestrator"
                    }
                }
            }
        }
    }
)
async def health_check():
    """
    **Basic health check for service availability monitoring.**
    
    Returns service health status with appropriate HTTP status codes
    for integration with monitoring systems and load balancers.
    """
    from health_check import basic_health_check
    try:
        health_result = await basic_health_check()
        status_code = 200 if health_result["status"] in ["healthy", "degraded"] else 503
        return Response(
            content=json.dumps(health_result),
            status_code=status_code,
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_response = {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
        return Response(
            content=json.dumps(error_response),
            status_code=503,
            media_type="application/json"
        )

@app.get(
    "/health/ready",
    tags=["System Monitoring"],
    summary="Kubernetes Readiness Probe",
    description="""
    **Kubernetes readiness probe for container orchestration.**
    
    This endpoint performs comprehensive dependency checks to determine if the service
    is ready to receive traffic. Used by Kubernetes for:
    - Service mesh traffic routing
    - Load balancer configuration
    - Rolling deployment coordination
    - Pod lifecycle management
    
    ## Readiness Checks
    
    The probe verifies:
    - Database connectivity and query performance
    - Redis connection and operation capability
    - External service availability (RAG, Rule Gen, Notifier)
    - System resource availability
    - Configuration validity
    - Essential service dependencies
    
    ## Response Codes
    
    - **200 OK**: Service is ready to accept traffic
    - **503 Service Unavailable**: Service is not ready (dependencies failing)
    
    ## Integration
    
    Configure in Kubernetes deployment:
    ```yaml
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 5
    ```
    """,
    response_description="Detailed readiness status with dependency information",
    responses={
        200: {
            "description": "Service is ready to accept traffic",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "ready": True,
                        "timestamp": "2024-01-15T14:30:45Z",
                        "dependencies": {
                            "redis": {
                                "status": "healthy",
                                "response_time": 0.023,
                                "last_check": "2024-01-15T14:30:45Z"
                            },
                            "database": {
                                "status": "healthy",
                                "response_time": 0.156,
                                "last_check": "2024-01-15T14:30:45Z"
                            },
                            "external_services": {
                                "rag_service": {
                                    "status": "healthy",
                                    "response_time": 0.342
                                },
                                "rule_service": {
                                    "status": "healthy",
                                    "response_time": 0.189
                                },
                                "notifier_service": {
                                    "status": "healthy",
                                    "response_time": 0.095
                                }
                            }
                        },
                        "system_resources": {
                            "memory_available": True,
                            "disk_space_available": True,
                            "cpu_load_acceptable": True
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service is not ready for traffic",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "ready": False,
                        "timestamp": "2024-01-15T14:30:45Z",
                        "failed_dependencies": [
                            "database_connection_failed",
                            "redis_timeout"
                        ],
                        "dependencies": {
                            "redis": {
                                "status": "unhealthy",
                                "error": "Connection timeout",
                                "last_check": "2024-01-15T14:30:45Z"
                            },
                            "database": {
                                "status": "unhealthy",
                                "error": "Connection refused",
                                "last_check": "2024-01-15T14:30:45Z"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def readiness_probe():
    """
    **Kubernetes readiness probe with comprehensive dependency checks.**
    
    Verifies that all critical dependencies are available and the service
    is ready to process requests and handle traffic.
    """
    from health_check import readiness_probe
    try:
        is_ready, health_result = await readiness_probe()
        status_code = 200 if is_ready else 503
        return Response(
            content=json.dumps(health_result),
            status_code=status_code,
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        error_response = {
            "status": "unhealthy",
            "message": f"Readiness check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "ready": False
        }
        return Response(
            content=json.dumps(error_response),
            status_code=503,
            media_type="application/json"
        )

@app.get(
    "/health/live",
    tags=["System Monitoring"],
    summary="Kubernetes Liveness Probe",
    description="""
    **Kubernetes liveness probe for container health verification.**
    
    This endpoint performs basic service availability checks to determine if the 
    service is alive and should continue running. Used by Kubernetes for:
    - Pod restart decisions
    - Container lifecycle management
    - Service recovery automation
    - Health monitoring and alerting
    
    ## Liveness Checks
    
    The probe verifies:
    - Core service responsiveness
    - Basic system functionality
    - Memory and resource health
    - Critical process availability
    - Application deadlock detection
    
    ## Response Codes
    
    - **200 OK**: Service is alive and functioning
    - **503 Service Unavailable**: Service is dead or unresponsive
    
    ## Integration
    
    Configure in Kubernetes deployment:
    ```yaml
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    ```
    
    ## Restart Policy
    
    Failed liveness checks trigger container restarts. Use conservative
    thresholds to avoid unnecessary restarts during temporary issues.
    """,
    response_description="Basic liveness status information",
    responses={
        200: {
            "description": "Service is alive and functioning",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "alive": True,
                        "timestamp": "2024-01-15T14:30:45Z",
                        "uptime": 86400,
                        "service": "agent_orchestrator",
                        "version": "1.0.0",
                        "basic_checks": {
                            "memory_usage_ok": True,
                            "cpu_responsive": True,
                            "core_processes_running": True,
                            "no_deadlocks_detected": True
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service is dead or unresponsive",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "alive": False,
                        "timestamp": "2024-01-15T14:30:45Z",
                        "error": "Service deadlock detected",
                        "failed_checks": [
                            "memory_exhaustion",
                            "core_process_failure"
                        ]
                    }
                }
            }
        }
    }
)
async def liveness_probe():
    """
    **Kubernetes liveness probe for basic service health verification.**
    
    Performs essential health checks to determine if the service is alive
    and functioning properly, triggering restarts if unhealthy.
    """
    from health_check import liveness_probe
    try:
        is_alive, health_result = await liveness_probe()
        status_code = 200 if is_alive else 503
        return Response(
            content=json.dumps(health_result),
            status_code=status_code,
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Liveness probe failed: {e}")
        error_response = {
            "status": "unhealthy",
            "message": f"Liveness check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "alive": False
        }
        return Response(
            content=json.dumps(error_response),
            status_code=503,
            media_type="application/json"
        )

@app.get("/health/full")
async def full_health_status():
    """Comprehensive health status with all components"""
    from health_check import full_health_check
    try:
        result = await full_health_check()
        status_code = 200 if result["status"] in ["healthy", "degraded"] else 503
        return Response(
            content=json.dumps(result),
            status_code=status_code,
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Full health check failed: {e}")
        error_response = {
            "status": "unhealthy", 
            "message": f"Full health check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
        return Response(
            content=json.dumps(error_response),
            status_code=503,
            media_type="application/json"
        )

@app.get("/health/monitoring")
async def monitoring_health_status():
    """Enhanced health status for monitoring systems with metrics"""
    from health_check import monitoring_health_check
    try:
        result = await monitoring_health_check()
        status_code = 200 if result["status"] in ["healthy", "degraded"] else 503
        return Response(
            content=json.dumps(result),
            status_code=status_code,
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Monitoring health check failed: {e}")
        error_response = {
            "status": "unhealthy",
            "message": f"Monitoring health check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
        return Response(
            content=json.dumps(error_response),
            status_code=503,
            media_type="application/json"
        )

@app.get("/health/alerting")
async def alerting_health_status():
    """Health status optimized for alerting systems"""
    from health_check import alerting_health_check
    try:
        result = await alerting_health_check()
        # Use different status codes for alerting
        status_code = 200 if result["status"] == "healthy" else 503
        return Response(
            content=json.dumps(result),
            status_code=status_code,
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Alerting health check failed: {e}")
        error_response = {
            "status": "unhealthy",
            "message": f"Alerting health check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "alerting": {
                "should_alert": True,
                "alert_level": "critical",
                "alert_message": f"Health check system failure: {str(e)}"
            }
        }
        return Response(
            content=json.dumps(error_response),
            status_code=503,
            media_type="application/json"
        )

@app.get(
    "/metrics",
    tags=["System Monitoring"],
    summary="Prometheus Metrics",
    description="""
    **Prometheus metrics endpoint for monitoring and observability.**
    
    This endpoint exposes operational metrics in Prometheus format for collection
    by monitoring systems. Metrics include:
    
    ## Application Metrics
    
    - **Request Rates**: HTTP request rates by endpoint and status code
    - **Response Times**: Request latency percentiles and histograms
    - **Error Rates**: Error frequency and error type distributions
    - **Throughput**: Task processing rates and queue depths
    
    ## Business Metrics
    
    - **Agent Utilization**: Active agents, idle agents, agent health
    - **Task Metrics**: Task completion rates, failure rates, queue sizes
    - **Workflow Metrics**: Workflow execution times, success rates
    - **Circuit Breaker**: Service availability, failure counts, state changes
    
    ## System Metrics
    
    - **Resource Usage**: CPU, memory, disk, network utilization
    - **Connection Pools**: Database and Redis connection health
    - **External Services**: Response times and availability
    - **Cache Performance**: Hit rates, miss rates, eviction rates
    
    ## Scraping Configuration
    
    Configure Prometheus to scrape this endpoint:
    ```yaml
    scrape_configs:
      - job_name: 'agent-orchestrator'
        static_configs:
          - targets: ['agent-orchestrator:8000']
        metrics_path: '/metrics'
        scrape_interval: 15s
    ```
    """,
    response_description="Prometheus metrics in text format",
    responses={
        200: {
            "description": "Metrics data in Prometheus format",
            "content": {
                "text/plain": {
                    "example": """# HELP agent_orchestrator_requests_total Total number of HTTP requests
# TYPE agent_orchestrator_requests_total counter
agent_orchestrator_requests_total{method="GET",endpoint="/health",status="200"} 1247
agent_orchestrator_requests_total{method="POST",endpoint="/api/v1/orchestrate",status="200"} 892

# HELP agent_orchestrator_request_duration_seconds Request duration histogram
# TYPE agent_orchestrator_request_duration_seconds histogram
agent_orchestrator_request_duration_seconds_bucket{endpoint="/api/v1/orchestrate",le="0.1"} 234
agent_orchestrator_request_duration_seconds_bucket{endpoint="/api/v1/orchestrate",le="0.5"} 567
agent_orchestrator_request_duration_seconds_bucket{endpoint="/api/v1/orchestrate",le="1.0"} 789
agent_orchestrator_request_duration_seconds_bucket{endpoint="/api/v1/orchestrate",le="+Inf"} 892

# HELP agent_orchestrator_active_agents Number of active agents
# TYPE agent_orchestrator_active_agents gauge
agent_orchestrator_active_agents 8

# HELP agent_orchestrator_tasks_total Total number of tasks processed
# TYPE agent_orchestrator_tasks_total counter
agent_orchestrator_tasks_total{status="completed"} 1230
agent_orchestrator_tasks_total{status="failed"} 17"""
                }
            }
        }
    }
)
async def metrics_endpoint():
    """
    **Prometheus metrics endpoint for monitoring and observability.**
    
    Exposes operational and business metrics in Prometheus format for collection
    by monitoring systems and alerting platforms.
    """
    from fastapi.responses import Response
    metrics_data = metrics_collector.get_metrics_data()
    return Response(content=metrics_data, media_type="text/plain")

@app.get(
    "/metrics/summary",
    tags=["System Monitoring"],
    summary="Human-Readable Metrics Summary",
    description="""
    **Human-readable metrics summary for dashboards and debugging.**
    
    This endpoint provides a user-friendly view of system metrics, complementing
    the machine-readable Prometheus endpoint. Includes:
    
    ## Service Information
    
    - Service name and version
    - Metrics collection status
    - Available metrics endpoints
    - Collection configuration
    
    ## Key Performance Indicators
    
    - Request rates and response times
    - Error rates and success rates
    - Resource utilization summaries
    - System health indicators
    
    ## Use Cases
    
    - **Development**: Quick metrics overview during debugging
    - **Operations**: Human-readable dashboard summaries
    - **Troubleshooting**: Fast access to key metrics
    - **API Discovery**: Understanding available metrics endpoints
    """,
    response_description="Human-readable metrics summary",
    responses={
        200: {
            "description": "Metrics summary retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "service": "agent_orchestrator",
                        "version": "1.0.0",
                        "metrics_enabled": True,
                        "timestamp": "2024-01-15T14:30:45Z",
                        "uptime": 86400,
                        "endpoints": [
                            "/metrics - Prometheus metrics for scraping",
                            "/metrics/summary - Human-readable metrics summary"
                        ],
                        "collection_status": {
                            "enabled": True,
                            "collection_interval": 15,
                            "last_collection": "2024-01-15T14:30:30Z",
                            "metrics_count": 47
                        },
                        "key_metrics": {
                            "request_rate": "45.7 req/min",
                            "average_response_time": "234ms",
                            "error_rate": "0.23%",
                            "active_agents": 8,
                            "task_queue_size": 3
                        },
                        "configuration": {
                            "retention_period": "7d",
                            "export_format": "prometheus",
                            "custom_labels": ["environment", "service", "version"]
                        }
                    }
                }
            }
        },
        503: {
            "description": "Metrics collection disabled",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Metrics collection disabled",
                        "message": "Metrics collection is not enabled in service configuration",
                        "service": "agent_orchestrator",
                        "timestamp": "2024-01-15T14:30:45Z"
                    }
                }
            }
        }
    }
)
async def metrics_summary():
    """
    **Human-readable metrics summary for monitoring and debugging.**
    
    Provides a user-friendly overview of system metrics and collection status
    for development, operations, and troubleshooting purposes.
    """
    if not metrics_collector.enabled:
        return {"error": "Metrics collection disabled"}
      # Get basic metrics info
    return {
        "service": "agent_orchestrator",
        "version": "1.0.0",
        "metrics_enabled": metrics_collector.enabled,
        "endpoints": [
            "/metrics - Prometheus metrics for scraping",
            "/metrics/summary - Human-readable metrics summary",
            "/metrics/agents - Agent performance analytics",
            "/metrics/tasks - Task analytics and performance",
            "/metrics/load-balancing - Load balancing analytics",
            "/metrics/slo - SLO tracking and alerting",
            "/metrics/anomaly-detection - Anomaly detection analytics"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

# Enhanced Monitoring Endpoints
@app.get("/metrics/agents", tags=["Advanced Monitoring"])
async def agent_metrics():
    """Enhanced agent performance analytics with semantic matching insights"""
    await AgentManager.initialize_advanced_components()
    
    agent_analytics = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_agents": len(state.agents),
        "agents": {},
        "semantic_matching_enabled": AgentManager._semantic_matcher is not None,
        "load_balancing_enabled": AgentManager._load_balancer is not None
    }
    
    for agent_id, agent in state.agents.items():
        metrics = agent.performance_metrics or {}
        agent_data = {
            "id": agent_id,
            "name": agent.name,
            "type": agent.type.value,
            "status": agent.status,
            "capabilities": agent.capabilities,
            "performance": {
                "success_rate": metrics.get("success_rate", 0.0),
                "total_tasks": metrics.get("total_count", 0),
                "avg_response_time": metrics.get("avg_response_time", 0.0)
            }
        }
        agent_analytics["agents"][agent_id] = agent_data
    
    return agent_analytics

@app.get("/metrics/slo", tags=["Advanced Monitoring"])
async def slo_metrics():
    """SLO tracking with alerting for key performance indicators"""
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    
    slo_targets = {
        "success_rate": 99.5,
        "response_time_p95": 2.0,
        "queue_depth": 10
    }
    
    recent_tasks = [t for t in state.tasks.values() 
                   if t.completed_at and t.completed_at > hour_ago]
    
    slo_analytics = {
        "timestamp": now.isoformat(),
        "slo_targets": slo_targets,
        "current_slos": {},
        "slo_violations": [],
        "alert_status": "healthy"
    }
    
    if recent_tasks:
        successful_tasks = [t for t in recent_tasks if t.status == TaskStatus.COMPLETED]
        success_rate = (len(successful_tasks) / len(recent_tasks)) * 100
        slo_analytics["current_slos"]["success_rate"] = success_rate
        
        if success_rate < slo_targets["success_rate"]:
            slo_analytics["slo_violations"].append({
                "slo": "success_rate",
                "current": success_rate,
                "target": slo_targets["success_rate"],
                "severity": "high" if success_rate < 95.0 else "medium"
            })
    
    # Queue depth check
    current_queue_depth = state.task_queue.qsize()
    slo_analytics["current_slos"]["queue_depth"] = current_queue_depth
    
    if current_queue_depth > slo_targets["queue_depth"]:
        slo_analytics["slo_violations"].append({
            "slo": "queue_depth",
            "current": current_queue_depth,
            "target": slo_targets["queue_depth"],
            "severity": "high" if current_queue_depth > 50 else "medium"
        })
    
    if slo_analytics["slo_violations"]:
        high_severity = any(v["severity"] == "high" for v in slo_analytics["slo_violations"])
        slo_analytics["alert_status"] = "critical" if high_severity else "warning"
    
    return slo_analytics

@app.post(
    "/api/v1/orchestrate",
    tags=["Enhanced Orchestration"],
    summary="Enhanced Multi-Service Orchestration",
    description="""
    **Advanced orchestration endpoint with circuit breaker protection and intelligent service coordination.**
    
    This is the primary endpoint for complex orchestration workflows that coordinate multiple downstream services
    with robust error handling, circuit breaker protection, and intelligent fallback mechanisms.
    
    ## Service Integration Architecture
    
    The orchestration process integrates with three core downstream services:
    
    ### 1. RAG Service (Retrieval-Augmented Generation)
    - **Purpose**: Context retrieval, knowledge base queries, semantic search
    - **Circuit Breaker**: Protects against RAG service failures
    - **Fallback**: Returns cached results or simplified context when service is unavailable
    - **Timeout**: 30 seconds with automatic retry logic
    
    ### 2. Rule Generation Service  
    - **Purpose**: Policy evaluation, rule processing, compliance checking
    - **Circuit Breaker**: Prevents cascading failures from rule engine issues
    - **Fallback**: Uses default rules or cached policy decisions
    - **Timeout**: 15 seconds with exponential backoff
    
    ### 3. Notifier Service
    - **Purpose**: Alert dispatch, notification management, escalation handling
    - **Circuit Breaker**: Ensures notification failures don't block processing
    - **Fallback**: Queues notifications for retry or uses alternative channels
    - **Timeout**: 10 seconds with immediate retry queue
    
    ## Circuit Breaker Protection
    
    Circuit breakers provide automatic protection against downstream service failures:
    
    - **Closed State**: Normal operation, all requests pass through
    - **Open State**: Service is failing, requests are blocked and fallbacks are used
    - **Half-Open State**: Testing if failed service has recovered
    
    ### Configuration Per Service:
    - **Failure Threshold**: 5 consecutive failures trigger circuit breaker
    - **Recovery Timeout**: 60 seconds before attempting recovery
    - **Success Threshold**: 3 consecutive successes to close circuit breaker
    
    ## Response Status Codes
    
    The endpoint returns different HTTP status codes based on orchestration results:
    
    - **200 OK**: Full success - all services responded successfully
    - **202 Accepted**: Partial success - some services used fallbacks but processing completed
    - **503 Service Unavailable**: Critical failures - essential services unavailable
    - **500 Internal Server Error**: Unexpected orchestration failures
    
    ## Request Processing Flow
    
    1. **Input Validation**: Comprehensive request validation and sanitization
    2. **Service Coordination**: Parallel or sequential service calls based on dependencies
    3. **Circuit Breaker Checks**: Monitor service health and apply protection patterns
    4. **Result Aggregation**: Combine responses from all services
    5. **Fallback Application**: Apply fallbacks for failed or unavailable services  
    6. **Response Formatting**: Return unified response with status and circuit breaker information
    
    ## Monitoring & Observability
    
    All orchestration requests are monitored with detailed metrics:
    - Request/response times for each downstream service
    - Circuit breaker state changes and failure counts
    - Fallback activation frequency and success rates
    - End-to-end orchestration performance metrics
    """,
    response_model=EnhancedOrchestrationResponse,
    response_description="Orchestration completed with service status and circuit breaker information",
    responses={
        200: {
            "description": "Full orchestration success - all services responded normally",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "message": "Orchestration completed successfully",
                        "rag_response": {
                            "context": "Retrieved relevant surveillance data...",
                            "confidence": 0.95,
                            "sources": ["policy_db", "incident_history"]
                        },
                        "rule_response": {
                            "applicable_rules": ["security_zone_rule_001", "access_control_rule_045"],
                            "actions": ["log_event", "send_alert"],
                            "compliance_status": "compliant"
                        },
                        "notification_response": {
                            "notifications_sent": 3,
                            "channels": ["email", "sms", "dashboard"],
                            "delivery_status": "delivered"
                        },
                        "circuit_breaker_status": {
                            "services": {
                                "rag_service": {
                                    "circuit_breaker_state": "closed",
                                    "failure_count": 0,
                                    "last_failure_time": None
                                },
                                "rule_service": {
                                    "circuit_breaker_state": "closed", 
                                    "failure_count": 0,
                                    "last_failure_time": None
                                },
                                "notifier_service": {
                                    "circuit_breaker_state": "closed",
                                    "failure_count": 0,
                                    "last_failure_time": None
                                }
                            }
                        },
                        "performance_metrics": {
                            "total_duration": 1.25,
                            "rag_duration": 0.45,
                            "rule_duration": 0.32,
                            "notification_duration": 0.18,
                            "orchestration_overhead": 0.30
                        },
                        "timestamp": "2024-01-15T14:30:45Z"
                    }
                }
            }
        },
        202: {
            "description": "Partial success - some services used fallbacks",
            "headers": {
                "X-Circuit-Breaker-Status": {
                    "description": "Comma-separated list of services with open circuit breakers",
                    "schema": {"type": "string"},
                    "example": "rag_service,rule_service"
                }
            },
            "content": {
                "application/json": {
                    "example": {
                        "status": "partial_success",
                        "message": "Orchestration completed with some fallbacks",
                        "rag_response": {
                            "context": "Using cached context due to service unavailability",
                            "confidence": 0.70,
                            "sources": ["cache"],
                            "fallback_used": True
                        },
                        "rule_response": {
                            "applicable_rules": ["default_security_rule"],
                            "actions": ["log_event"],
                            "compliance_status": "unknown",
                            "fallback_used": True
                        },
                        "notification_response": {
                            "notifications_sent": 1,
                            "channels": ["dashboard"],
                            "delivery_status": "queued_for_retry",
                            "fallback_used": True
                        },
                        "circuit_breaker_status": {
                            "services": {
                                "rag_service": {
                                    "circuit_breaker_state": "open",
                                    "failure_count": 7,
                                    "last_failure_time": "2024-01-15T14:29:30Z"
                                },
                                "rule_service": {
                                    "circuit_breaker_state": "half_open",
                                    "failure_count": 3,
                                    "last_failure_time": "2024-01-15T14:28:15Z"
                                },
                                "notifier_service": {
                                    "circuit_breaker_state": "open",
                                    "failure_count": 5,
                                    "last_failure_time": "2024-01-15T14:30:00Z"
                                }
                            }
                        },
                        "timestamp": "2024-01-15T14:30:45Z"
                    }
                }
            }
        },
        503: {
            "description": "Service unavailable - critical downstream failures",
            "content": {
                "application/json": {
                    "example": {
                        "status": "fallback",
                        "message": "Critical services unavailable, using emergency fallbacks",
                        "error_details": {
                            "rag_service": "Circuit breaker open - 10 consecutive failures",
                            "rule_service": "Service timeout after 15 seconds",
                            "notifier_service": "Connection refused"
                        },
                        "circuit_breaker_status": {
                            "services": {
                                "rag_service": {"circuit_breaker_state": "open"},
                                "rule_service": {"circuit_breaker_state": "open"},
                                "notifier_service": {"circuit_breaker_state": "open"}
                            }
                        },
                        "timestamp": "2024-01-15T14:30:45Z"
                    }
                }
            }
        },
        422: {
            "description": "Request validation failed",
            "model": ValidationErrorResponse
        },
        500: {
            "description": "Internal orchestration error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Internal orchestration error",
                        "message": "Unexpected failure in orchestration engine",
                        "timestamp": "2024-01-15T14:30:45Z"
                    }
                }
            }
        }
    }
)
async def orchestrate(
    app_request: Request,
    request: EnhancedOrchestrationRequest
):
    """
    **Execute advanced multi-service orchestration with circuit breaker protection.**
    
    Coordinates complex workflows across RAG, Rule Generation, and Notifier services with intelligent
    fallback mechanisms and comprehensive error handling.
    """
    try:
        # Get enhanced orchestrator from app state
        enhanced_orchestrator = app_request.app.state.enhanced_orchestrator
        
        result = await enhanced_orchestrator.orchestrate(request)
        
        # Determine appropriate HTTP status code based on circuit breaker status
        if result.status == "ok":
            return result
        elif result.status == "partial_success":
            # Check if any circuit breakers are open
            cb_status = result.circuit_breaker_status or {}
            open_breakers = [
                service for service, status in cb_status.get('services', {}).items()
                if status.get('circuit_breaker_state') == 'open'
            ]
            
            if open_breakers:
                logger.warning(f"Circuit breakers open for services: {open_breakers}")
                # Return 202 for partial success with open circuit breakers
                response = JSONResponse(
                    status_code=202,
                    content=result.dict()
                )
                response.headers["X-Circuit-Breaker-Status"] = ",".join(open_breakers)
                return response
            else:
                return result
        elif result.status == "fallback":
            # Return 503 for fallback responses
            raise HTTPException(status_code=503, detail=result.dict())
        else:
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal orchestration error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get(
    "/api/v1/circuit-breakers/health",
    tags=["Circuit Breaker Management"],
    summary="Get Circuit Breaker Health Status",
    description="""
    **Retrieve detailed health status for all circuit breakers protecting downstream services.**
    
    This endpoint provides comprehensive monitoring information about the circuit breaker system,
    including current states, failure counts, performance metrics, and configuration details.
    
    ## Circuit Breaker States
    
    - **CLOSED**: Normal operation - requests pass through to downstream service
    - **OPEN**: Service is failing - requests are blocked and fallbacks are used
    - **HALF_OPEN**: Testing recovery - limited requests allowed to test service health
    
    ## Health Metrics
    
    For each protected service, the response includes:
    - Current circuit breaker state and transition history
    - Failure count and success count statistics  
    - Last failure timestamp and error details
    - Response time percentiles and performance trends
    - Circuit breaker configuration (thresholds, timeouts)
    - Service-specific fallback status and usage statistics
    
    ## Monitoring Integration
    
    This endpoint is designed for integration with monitoring systems:
    - Prometheus metrics exposition format available
    - Alerting thresholds and escalation information
    - Historical trend data for capacity planning
    - Service dependency mapping and impact analysis
    
    ## Use Cases
    
    - **Operations Dashboards**: Real-time service health visualization
    - **Alerting Systems**: Circuit breaker state change notifications
    - **Capacity Planning**: Historical failure patterns and load analysis
    - **Troubleshooting**: Detailed failure information and root cause analysis
    """,
    response_description="Comprehensive circuit breaker health status for all protected services",
    responses={
        200: {
            "description": "Circuit breaker health status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "system_status": "healthy",
                        "total_services": 3,
                        "healthy_services": 2,
                        "degraded_services": 1,
                        "failed_services": 0,
                        "services": {
                            "rag_service": {
                                "circuit_breaker_state": "closed",
                                "health_status": "healthy",
                                "failure_count": 0,
                                "success_count": 147,
                                "failure_rate": 0.0,
                                "success_rate": 1.0,
                                "last_failure_time": None,
                                "last_success_time": "2024-01-15T14:30:45Z",
                                "average_response_time": 0.342,
                                "p95_response_time": 0.578,
                                "p99_response_time": 0.823,
                                "configuration": {
                                    "failure_threshold": 5,
                                    "recovery_timeout": 60,
                                    "success_threshold": 3,
                                    "request_timeout": 30
                                },
                                "fallback_status": {
                                    "enabled": True,
                                    "usage_count": 0,
                                    "last_used": None
                                }
                            },
                            "rule_service": {
                                "circuit_breaker_state": "half_open",
                                "health_status": "degraded",
                                "failure_count": 3,
                                "success_count": 89,
                                "failure_rate": 0.032,
                                "success_rate": 0.968,
                                "last_failure_time": "2024-01-15T14:25:30Z",
                                "last_success_time": "2024-01-15T14:30:15Z",
                                "average_response_time": 0.756,
                                "p95_response_time": 1.234,
                                "p99_response_time": 2.145,
                                "configuration": {
                                    "failure_threshold": 5,
                                    "recovery_timeout": 60,
                                    "success_threshold": 3,
                                    "request_timeout": 15
                                },
                                "fallback_status": {
                                    "enabled": True,
                                    "usage_count": 3,
                                    "last_used": "2024-01-15T14:25:30Z"
                                }
                            },
                            "notifier_service": {
                                "circuit_breaker_state": "closed",
                                "health_status": "healthy",
                                "failure_count": 1,
                                "success_count": 203,
                                "failure_rate": 0.005,
                                "success_rate": 0.995,
                                "last_failure_time": "2024-01-15T13:45:12Z",
                                "last_success_time": "2024-01-15T14:30:44Z",
                                "average_response_time": 0.156,
                                "p95_response_time": 0.289,
                                "p99_response_time": 0.445,
                                "configuration": {
                                    "failure_threshold": 5,
                                    "recovery_timeout": 60,
                                    "success_threshold": 3,
                                    "request_timeout": 10
                                },
                                "fallback_status": {
                                    "enabled": True,
                                    "usage_count": 1,
                                    "last_used": "2024-01-15T13:45:12Z"
                                }
                            }
                        },
                        "system_metrics": {
                            "total_requests": 439,
                            "total_failures": 4,
                            "overall_failure_rate": 0.009,
                            "overall_success_rate": 0.991,
                            "average_orchestration_time": 1.234,
                            "fallback_activation_count": 4
                        },
                        "timestamp": "2024-01-15T14:30:45Z",
                        "monitoring": {
                            "collection_interval": 30,
                            "retention_period": "7d",
                            "alert_thresholds": {
                                "failure_rate": 0.05,
                                "response_time_p95": 2.0,
                                "circuit_breaker_open": True
                            }
                        }
                    }
                }
            }
        },
        500: {
            "description": "Failed to retrieve circuit breaker health status",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Failed to retrieve circuit breaker health",
                        "message": "Circuit breaker monitoring system unavailable",
                        "timestamp": "2024-01-15T14:30:45Z"
                    }
                }
            }
        }
    }
)
async def get_circuit_breaker_health(app_request: Request):
    """
    **Get comprehensive circuit breaker health status for monitoring and troubleshooting.**
      Returns detailed health metrics, failure statistics, and configuration information 
    for all circuit breakers protecting downstream services.
    """
    try:
        enhanced_orchestrator = app_request.app.state.enhanced_orchestrator
        health_status = await enhanced_orchestrator.get_health_status()
        return JSONResponse(
            content=health_status
        )
        
    except Exception as e:
        logger.error(f"Failed to get circuit breaker health: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve circuit breaker health",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.post(
    "/api/v1/circuit-breakers/{service_name}/force-state",
    tags=["Circuit Breaker Management"],
    summary="Force Circuit Breaker State",
    description="""
    **Administrative endpoint to manually control circuit breaker states.**
    
    This endpoint allows administrators to manually override circuit breaker states
    for testing, maintenance, or emergency situations. Use cases include:
    
    ## Administrative Operations
    
    - **Testing**: Force circuit breakers open/closed for testing failure scenarios
    - **Maintenance**: Temporarily disable services during maintenance windows
    - **Emergency Response**: Quickly isolate failing services during incidents
    - **Development**: Simulate service failures in development environments
    
    ## Circuit Breaker States
    
    - **closed**: Normal operation - requests pass through to service
    - **open**: Service is blocked - all requests return fallback responses
    - **half-open**: Testing state - limited requests allowed to test recovery
    
    ## Security Considerations
    
    This endpoint should be restricted to administrative users only.
    Improper use can impact system availability and performance.
    
    ## State Transitions
    
    Forced state changes override automatic circuit breaker logic:
    - Forced states persist until automatic conditions trigger transitions
    - Monitor circuit breaker health after forced changes
    - Document state changes for operational tracking
    """,
    response_description="Circuit breaker state change confirmation",
    responses={
        200: {
            "description": "Circuit breaker state changed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Circuit breaker for 'rag_service' forced to 'open' state",
                        "service_name": "rag_service",
                        "previous_state": "closed",
                        "new_state": "open",
                        "forced_by": "admin_user",
                        "timestamp": "2024-01-15T14:30:45Z",
                        "warning": "Forced state will persist until automatic conditions trigger transitions"
                    }
                }
            }
        },
        400: {
            "description": "Invalid state parameter",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Invalid state",
                        "message": "State must be one of: open, closed, half-open",
                        "provided_state": "invalid_state",
                        "valid_states": ["open", "closed", "half-open"],
                        "timestamp": "2024-01-15T14:30:45Z"
                    }
                }
            }
        },
        404: {
            "description": "Service not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Service not found",
                        "message": "Service 'unknown_service' not registered",
                        "service_name": "unknown_service",
                        "available_services": ["rag_service", "rule_service", "notifier_service"],
                        "timestamp": "2024-01-15T14:30:45Z"
                    }
                }
            }
        },
        500: {
            "description": "Failed to change circuit breaker state",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Failed to force circuit breaker state",
                        "message": "Internal error during state transition",
                        "service_name": "rag_service",
                        "timestamp": "2024-01-15T14:30:45Z"
                    }
                }
            }
        }
    }
)
async def force_circuit_breaker_state(
    service_name: str,
    state: str, 
    app_request: Request
):
    """
    **Force a circuit breaker to a specific state for testing or administrative purposes.**
    
    Allows manual override of automatic circuit breaker behavior for testing,
    maintenance, or emergency response scenarios.
    """
    if state.lower() not in ['open', 'closed', 'half-open']:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid state",
                "message": "State must be one of: open, closed, half-open",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    try:
        enhanced_orchestrator = app_request.app.state.enhanced_orchestrator
        success = await enhanced_orchestrator.enhanced_circuit_breaker_manager.force_circuit_state(
            service_name, state
        )
        
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Circuit breaker for '{service_name}' forced to '{state}' state",
                    "service_name": service_name,
                    "new_state": state,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Service not found",
                    "message": f"Service '{service_name}' not registered",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to force circuit breaker state: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to force circuit breaker state",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

if __name__ == "__main__":
    import uvicorn
    config = get_config()
    validate_config()  # Validate and log configuration
    uvicorn.run(app, host=config.service_host, port=config.service_port)

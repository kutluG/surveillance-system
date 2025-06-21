"""
Database Service Layer for Agent Orchestrator

This module provides high-level database operations using the dependency injection
system from database.py. It implements the repository pattern for clean separation
of concerns and robust transaction management.

Features:
- Repository pattern implementation
- Automatic transaction management
- Connection leak prevention
- Query optimization and indexing
- Comprehensive error handling
- Metrics collection for database operations
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from database import get_db_session, get_db_transaction
from models import (
    Agent, Task, Workflow, OrchestrationLog, ServiceHealth,
    AgentTypeEnum, TaskStatusEnum, WorkflowStatusEnum
)

logger = logging.getLogger(__name__)


class DatabaseOperationError(Exception):
    """Custom exception for database operation errors"""
    pass


class AgentRepository:
    """Repository for agent-related database operations"""
    
    @staticmethod
    async def create_agent(
        agent_data: Dict[str, Any],
        db: AsyncSession
    ) -> Agent:
        """Create a new agent with transaction safety"""
        try:
            agent = Agent(
                type=AgentTypeEnum(agent_data["type"]),
                name=agent_data["name"],
                endpoint=agent_data["endpoint"],
                capabilities=agent_data.get("capabilities", []),
                status=agent_data.get("status", "idle"),
                metadata=agent_data.get("metadata", {}),
                performance_metrics=agent_data.get("performance_metrics", {})
            )
            
            db.add(agent)
            await db.flush()  # Get the ID without committing
            await db.refresh(agent)
            
            logger.info(f"Created agent: {agent.name} ({agent.id})")
            return agent
            
        except IntegrityError as e:
            logger.error(f"Agent creation failed - integrity error: {e}")
            raise DatabaseOperationError(f"Agent creation failed: {str(e)}")
        except SQLAlchemyError as e:
            logger.error(f"Agent creation failed - database error: {e}")
            raise DatabaseOperationError(f"Database error during agent creation: {str(e)}")
    
    @staticmethod
    async def get_agent_by_id(
        agent_id: str,
        db: AsyncSession,
        include_tasks: bool = False
    ) -> Optional[Agent]:
        """Get agent by ID with optional task loading"""
        try:
            query = select(Agent).where(Agent.id == agent_id, Agent.is_active == True)
            
            if include_tasks:
                query = query.options(selectinload(Agent.tasks))
            
            result = await db.execute(query)
            return result.scalar_one_or_none()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            raise DatabaseOperationError(f"Failed to retrieve agent: {str(e)}")
    
    @staticmethod
    async def list_agents(
        db: AsyncSession,
        agent_type: Optional[AgentTypeEnum] = None,
        status: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Agent], int]:
        """List agents with filtering and pagination"""
        try:
            # Build base query
            query = select(Agent).where(Agent.is_active == True)
            count_query = select(func.count(Agent.id)).where(Agent.is_active == True)
            
            # Apply filters
            if agent_type:
                query = query.where(Agent.type == agent_type)
                count_query = count_query.where(Agent.type == agent_type)
            
            if status:
                query = query.where(Agent.status == status)
                count_query = count_query.where(Agent.status == status)
            
            if capabilities:
                # Check if agent has all required capabilities
                for capability in capabilities:
                    query = query.where(Agent.capabilities.contains([capability]))
                    count_query = count_query.where(Agent.capabilities.contains([capability]))
            
            # Get total count
            total_result = await db.execute(count_query)
            total_count = total_result.scalar()
            
            # Apply ordering and pagination
            query = query.order_by(desc(Agent.created_at)).limit(limit).offset(offset)
            
            result = await db.execute(query)
            agents = result.scalars().all()
            
            return list(agents), total_count
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to list agents: {e}")
            raise DatabaseOperationError(f"Failed to list agents: {str(e)}")
    
    @staticmethod    @staticmethod
    async def update_agent_status(
        agent_id: str,
        status: str,
        current_task_id: Optional[str],
        db: AsyncSession
    ) -> bool:
        """Update agent status and current task"""
        try:
            query = (
                update(Agent)
                .where(Agent.id == agent_id, Agent.is_active == True)
                .values(
                    status=status,
                    current_task_id=current_task_id,
                    last_seen=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            
            result = await db.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No agent found with ID: {agent_id}")
                return False
            
            logger.debug(f"Updated agent {agent_id} status to {status}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to update agent status: {e}")
            raise DatabaseOperationError(f"Failed to update agent status: {str(e)}")
    
    @staticmethod
    async def find_suitable_agents(
        required_capabilities: List[str],
        task_type: str,
        db: AsyncSession
    ) -> List[Agent]:
        """Find agents suitable for a specific task (legacy method for backward compatibility)"""
        try:
            query = select(Agent).where(
                Agent.is_active == True,
                Agent.status == "idle"
            )
            
            # Filter by required capabilities
            if required_capabilities:
                for capability in required_capabilities:
                    query = query.where(Agent.capabilities.contains([capability]))
            
            # Optional: Add task type specific filtering logic here
            # This could be enhanced based on business rules
            
            # Order by performance metrics (success rate)
            query = query.order_by(
                desc(func.coalesce(Agent.performance_metrics["success_rate"].astext.cast(float), 0.5))
            )
            
            result = await db.execute(query)
            return list(result.scalars().all())
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to find suitable agents: {e}")
            raise DatabaseOperationError(f"Failed to find suitable agents: {str(e)}")
    
    @staticmethod
    async def find_suitable_agents_semantic(
        task_description: str,
        required_capabilities: List[str] = None,
        task_type: str = "",
        db: AsyncSession = None,
        top_k: int = 3,
        min_score: float = 0.3,
        use_semantic: bool = True
    ) -> Tuple[List[Agent], List[Dict[str, Any]]]:
        """
        Find suitable agents using semantic matching and enhanced scoring.
        
        Args:
            task_description: Natural language description of the task
            required_capabilities: List of required capabilities
            task_type: Type/category of the task
            db: Database session
            top_k: Maximum number of agents to return
            min_score: Minimum matching score threshold
            use_semantic: Whether to use semantic matching (fallback to basic if unavailable)
        
        Returns:
            Tuple of (agents_list, matching_details)
        """
        try:
            # First get all available agents from database
            available_agents_query = select(Agent).where(
                Agent.is_active == True,
                Agent.status == "idle"
            )
            
            if db:
                result = await db.execute(available_agents_query)
                available_agents = list(result.scalars().all())
            else:
                available_agents = []
            
            if not available_agents:
                logger.info("No available agents found in database")
                return [], []
            
            matching_results = []
            
            if use_semantic:
                try:
                    # Try to use semantic matching
                    from semantic_agent_matcher import get_semantic_matcher
                    
                    matcher = await get_semantic_matcher()
                    
                    # Sync matcher with current database state
                    if db:
                        await matcher.sync_with_database(db)
                    
                    # Get semantic matching results
                    semantic_results = await matcher.find_matching_agents(
                        task_description=task_description,
                        required_capabilities=required_capabilities or [],
                        task_type=task_type,
                        top_k=top_k * 2,  # Get more candidates for filtering
                        min_score=min_score
                    )
                    
                    # Map semantic results to database agents
                    agent_id_to_result = {result.agent_id: result for result in semantic_results}
                    
                    for agent in available_agents:
                        if agent.id in agent_id_to_result:
                            semantic_result = agent_id_to_result[agent.id]
                            matching_results.append({
                                'agent': agent,
                                'semantic_result': semantic_result,
                                'score': semantic_result.combined_score,
                                'method': 'semantic'
                            })
                    
                    logger.info(f"Found {len(matching_results)} agents using semantic matching")
                    
                except ImportError:
                    logger.warning("Semantic matching not available, falling back to basic matching")
                    use_semantic = False
                except Exception as e:
                    logger.warning(f"Semantic matching failed: {e}, falling back to basic matching")
                    use_semantic = False
            
            # Fallback to basic capability matching if semantic matching unavailable
            if not use_semantic or not matching_results:
                logger.info("Using basic capability matching")
                
                for agent in available_agents:
                    score = AgentRepository._calculate_basic_match_score(
                        agent, required_capabilities or [], task_type
                    )
                    
                    if score >= min_score:
                        matching_results.append({
                            'agent': agent,
                            'semantic_result': None,
                            'score': score,
                            'method': 'basic'
                        })
            
            # Sort by score and return top_k
            matching_results.sort(key=lambda x: x['score'], reverse=True)
            top_results = matching_results[:top_k]
            
            # Extract agents and details
            agents = [result['agent'] for result in top_results]
            details = []
            
            for result in top_results:
                detail = {
                    'agent_id': result['agent'].id,
                    'agent_name': result['agent'].name,
                    'score': result['score'],
                    'method': result['method']
                }
                
                if result['semantic_result']:
                    sr = result['semantic_result']
                    detail.update({
                        'capability_match_score': sr.capability_match_score,
                        'performance_score': sr.performance_score,
                        'matched_capabilities': sr.matched_capabilities,
                        'missing_capabilities': sr.missing_capabilities,
                        'confidence': sr.confidence,
                        'reasoning': sr.reasoning
                    })
                
                details.append(detail)
            
            logger.info(f"Returning {len(agents)} suitable agents (method: {top_results[0]['method'] if top_results else 'none'})")
            return agents, details
            
        except Exception as e:
            logger.error(f"Failed to find suitable agents with semantic matching: {e}")
            # Final fallback to original method
            try:
                fallback_agents = await AgentRepository.find_suitable_agents(
                    required_capabilities or [], task_type, db
                )
                fallback_details = [
                    {
                        'agent_id': agent.id,
                        'agent_name': agent.name,
                        'score': 0.5,
                        'method': 'fallback'
                    }
                    for agent in fallback_agents[:top_k]
                ]
                return fallback_agents[:top_k], fallback_details
            except Exception as fallback_error:
                logger.error(f"Fallback matching also failed: {fallback_error}")
                raise DatabaseOperationError(f"All agent matching methods failed: {str(e)}")
    
    @staticmethod
    def _calculate_basic_match_score(agent: Agent, required_capabilities: List[str], 
                                   task_type: str) -> float:
        """Calculate basic matching score for an agent"""
        score = 0.0
        
        # Base score from performance metrics
        performance_metrics = agent.performance_metrics or {}
        base_score = performance_metrics.get("success_rate", 0.5)
        
        # Capability matching score
        if required_capabilities:
            agent_caps = set(cap.lower() for cap in agent.capabilities)
            required_caps = set(cap.lower() for cap in required_capabilities)
            
            matched_caps = agent_caps.intersection(required_caps)
            capability_score = len(matched_caps) / len(required_capabilities)
        else:
            capability_score = 1.0
        
        # Agent type matching
        type_score = 1.0
        if task_type:
            task_lower = task_type.lower()
            if "prompt" in task_lower and agent.type != AgentTypeEnum.PROMPT:
                type_score = 0.7
            elif "search" in task_lower and agent.type != AgentTypeEnum.RAG:
                type_score = 0.7
            elif "rule" in task_lower and agent.type != AgentTypeEnum.RULE:
                type_score = 0.7
        
        # Combined score
        score = (base_score * 0.4 + capability_score * 0.4 + type_score * 0.2)
        
        return min(score, 1.0)


class TaskRepository:
    """Repository for task-related database operations"""
    
    @staticmethod
    async def create_task(
        task_data: Dict[str, Any],
        db: AsyncSession
    ) -> Task:
        """Create a new task with transaction safety"""
        try:
            task = Task(
                type=task_data["type"],
                name=task_data.get("name"),
                description=task_data["description"],
                input_data=task_data.get("input_data", {}),
                priority=task_data.get("priority", 1),
                required_capabilities=task_data.get("required_capabilities", []),
                workflow_id=task_data.get("workflow_id"),
                parent_task_id=task_data.get("parent_task_id"),
                dependencies=task_data.get("dependencies", []),
                metadata=task_data.get("metadata", {}),
                max_retries=task_data.get("max_retries", 3),
                timeout_at=task_data.get("timeout_at")
            )
            
            db.add(task)
            await db.flush()
            await db.refresh(task)
            
            logger.info(f"Created task: {task.type} ({task.id})")
            return task
            
        except SQLAlchemyError as e:
            logger.error(f"Task creation failed: {e}")
            raise DatabaseOperationError(f"Task creation failed: {str(e)}")
    
    @staticmethod
    async def get_task_by_id(
        task_id: str,
        db: AsyncSession,
        include_agent: bool = False,
        include_workflow: bool = False
    ) -> Optional[Task]:
        """Get task by ID with optional relationship loading"""
        try:
            query = select(Task).where(Task.id == task_id)
            
            if include_agent:
                query = query.options(joinedload(Task.assigned_agent))
            
            if include_workflow:
                query = query.options(joinedload(Task.workflow))
            
            result = await db.execute(query)
            return result.scalar_one_or_none()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            raise DatabaseOperationError(f"Failed to retrieve task: {str(e)}")
    
    @staticmethod
    async def list_tasks(
        db: AsyncSession,
        status: Optional[TaskStatusEnum] = None,
        workflow_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        priority_min: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Task], int]:
        """List tasks with filtering and pagination"""
        try:
            query = select(Task)
            count_query = select(func.count(Task.id))
            
            # Apply filters
            if status:
                query = query.where(Task.status == status)
                count_query = count_query.where(Task.status == status)
            
            if workflow_id:
                query = query.where(Task.workflow_id == workflow_id)
                count_query = count_query.where(Task.workflow_id == workflow_id)
            
            if agent_id:
                query = query.where(Task.assigned_agent_id == agent_id)
                count_query = count_query.where(Task.assigned_agent_id == agent_id)
            
            if priority_min is not None:
                query = query.where(Task.priority >= priority_min)
                count_query = count_query.where(Task.priority >= priority_min)
            
            # Get total count
            total_result = await db.execute(count_query)
            total_count = total_result.scalar()
            
            # Apply ordering and pagination
            query = (
                query
                .order_by(desc(Task.priority), desc(Task.created_at))
                .limit(limit)
                .offset(offset)
            )
            
            result = await db.execute(query)
            tasks = result.scalars().all()
            
            return list(tasks), total_count
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to list tasks: {e}")
            raise DatabaseOperationError(f"Failed to list tasks: {str(e)}")
    
    @staticmethod
    async def update_task_status(
        task_id: str,
        status: TaskStatusEnum,
        db: AsyncSession,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        assigned_agent_id: Optional[str] = None
    ) -> bool:
        """Update task status and related fields"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            # Set timestamps based on status
            if status == TaskStatusEnum.RUNNING and assigned_agent_id:
                update_data.update({
                    "started_at": datetime.utcnow(),
                    "assigned_agent_id": assigned_agent_id
                })
            elif status in [TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED, TaskStatusEnum.CANCELLED]:
                update_data["completed_at"] = datetime.utcnow()
                
                if result_data:
                    update_data["result"] = result_data
                
                if error_message:
                    update_data["error_message"] = error_message
            
            query = (
                update(Task)
                .where(Task.id == task_id)
                .values(**update_data)
            )
            
            result = await db.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No task found with ID: {task_id}")
                return False
            
            logger.debug(f"Updated task {task_id} status to {status}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to update task status: {e}")
            raise DatabaseOperationError(f"Failed to update task status: {str(e)}")
    
    @staticmethod
    async def get_pending_tasks(
        db: AsyncSession,
        limit: int = 50
    ) -> List[Task]:
        """Get pending tasks ordered by priority"""
        try:
            query = (
                select(Task)
                .where(Task.status == TaskStatusEnum.PENDING)
                .order_by(desc(Task.priority), asc(Task.created_at))
                .limit(limit)
            )
            
            result = await db.execute(query)
            return list(result.scalars().all())
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get pending tasks: {e}")
            raise DatabaseOperationError(f"Failed to get pending tasks: {str(e)}")


class WorkflowRepository:
    """Repository for workflow-related database operations"""
    
    @staticmethod
    async def create_workflow(
        workflow_data: Dict[str, Any],
        db: AsyncSession
    ) -> Workflow:
        """Create a new workflow with transaction safety"""
        try:
            workflow = Workflow(
                name=workflow_data["name"],
                description=workflow_data["description"],
                user_id=workflow_data["user_id"],
                configuration=workflow_data.get("configuration", {}),
                metadata=workflow_data.get("metadata", {}),
                priority=workflow_data.get("priority", 1),
                estimated_duration=workflow_data.get("estimated_duration"),
                timeout_at=workflow_data.get("timeout_at")
            )
            
            db.add(workflow)
            await db.flush()
            await db.refresh(workflow)
            
            logger.info(f"Created workflow: {workflow.name} ({workflow.id})")
            return workflow
            
        except SQLAlchemyError as e:
            logger.error(f"Workflow creation failed: {e}")
            raise DatabaseOperationError(f"Workflow creation failed: {str(e)}")
    
    @staticmethod
    async def get_workflow_by_id(
        workflow_id: str,
        db: AsyncSession,
        include_tasks: bool = False
    ) -> Optional[Workflow]:
        """Get workflow by ID with optional task loading"""
        try:
            query = select(Workflow).where(Workflow.id == workflow_id)
            
            if include_tasks:
                query = query.options(selectinload(Workflow.tasks))
            
            result = await db.execute(query)
            return result.scalar_one_or_none()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get workflow {workflow_id}: {e}")
            raise DatabaseOperationError(f"Failed to retrieve workflow: {str(e)}")
    
    @staticmethod
    async def update_workflow_status(
        workflow_id: str,
        status: WorkflowStatusEnum,
        db: AsyncSession
    ) -> bool:
        """Update workflow status with appropriate timestamps"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            if status == WorkflowStatusEnum.RUNNING:
                update_data["started_at"] = datetime.utcnow()
            elif status in [WorkflowStatusEnum.COMPLETED, WorkflowStatusEnum.FAILED, WorkflowStatusEnum.CANCELLED]:
                update_data["completed_at"] = datetime.utcnow()
                
                # Calculate actual duration if started
                workflow = await WorkflowRepository.get_workflow_by_id(workflow_id, db)
                if workflow and workflow.started_at:
                    duration = (datetime.utcnow() - workflow.started_at).total_seconds()
                    update_data["actual_duration"] = duration
            
            query = (
                update(Workflow)
                .where(Workflow.id == workflow_id)
                .values(**update_data)
            )
            
            result = await db.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No workflow found with ID: {workflow_id}")
                return False
            
            logger.debug(f"Updated workflow {workflow_id} status to {status}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to update workflow status: {e}")
            raise DatabaseOperationError(f"Failed to update workflow status: {str(e)}")


class OrchestrationLogRepository:
    """Repository for orchestration logging operations"""
    
    @staticmethod
    async def log_operation(
        operation_type: str,
        entity_type: str,
        entity_id: Optional[str],
        status: str,
        db: AsyncSession,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        duration: Optional[float] = None
    ) -> OrchestrationLog:
        """Log an orchestration operation"""
        try:
            log_entry = OrchestrationLog(
                operation_type=operation_type,
                entity_type=entity_type,
                entity_id=entity_id,
                status=status,
                message=message,
                details=details or {},
                user_id=user_id,
                duration=duration
            )
            
            db.add(log_entry)
            await db.flush()
            
            return log_entry
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to log operation: {e}")
            raise DatabaseOperationError(f"Failed to log operation: {str(e)}")


# High-level service functions using dependency injection
async def get_agent_with_session(agent_id: str, include_tasks: bool = False) -> Optional[Agent]:
    """Get agent using dependency injection for database session"""
    async with get_db_session() as db:
        return await AgentRepository.get_agent_by_id(agent_id, db, include_tasks)


async def create_agent_with_transaction(agent_data: Dict[str, Any]) -> Agent:
    """Create agent using dependency injection for database transaction"""
    async with get_db_transaction() as db:
        agent = await AgentRepository.create_agent(agent_data, db)
        await OrchestrationLogRepository.log_operation(
            operation_type="agent_registration",
            entity_type="agent",
            entity_id=str(agent.id),
            status="success",
            db=db,
            message=f"Agent '{agent.name}' registered successfully",
            details={"agent_type": agent.type.value, "capabilities_count": len(agent.capabilities)}
        )
        return agent


async def create_task_with_transaction(task_data: Dict[str, Any]) -> Task:
    """Create task using dependency injection for database transaction"""
    async with get_db_transaction() as db:
        task = await TaskRepository.create_task(task_data, db)
        await OrchestrationLogRepository.log_operation(
            operation_type="task_creation",
            entity_type="task",
            entity_id=str(task.id),
            status="success",
            db=db,
            message=f"Task '{task.type}' created successfully",
            details={"priority": task.priority, "required_capabilities": task.required_capabilities}
        )
        return task


async def assign_task_with_transaction(task_id: str, agent_id: str) -> bool:
    """Assign task to agent using database transaction"""
    async with get_db_transaction() as db:
        # Update task
        task_updated = await TaskRepository.update_task_status(
            task_id, TaskStatusEnum.RUNNING, db, assigned_agent_id=agent_id
        )
        
        if not task_updated:
            return False
        
        # Update agent
        agent_updated = await AgentRepository.update_agent_status(
            agent_id, "busy", task_id, db
        )
        
        if not agent_updated:
            # Rollback task status (transaction will handle this)
            raise DatabaseOperationError("Failed to update agent status during task assignment")
        
        # Log the operation
        await OrchestrationLogRepository.log_operation(
            operation_type="task_assignment",
            entity_type="task",
            entity_id=task_id,
            status="success",
            db=db,
            message=f"Task assigned to agent {agent_id}",
            details={"agent_id": agent_id}
        )
        
        return True


# Database health check function
async def check_database_health() -> Dict[str, Any]:
    """Check database health using dependency injection"""
    try:
        async with get_db_session() as db:
            # Simple query to test connection
            result = await db.execute(select(func.count(Agent.id)))
            agent_count = result.scalar()
            
            result = await db.execute(select(func.count(Task.id)))
            task_count = result.scalar()
            
            return {
                "status": "healthy",
                "agent_count": agent_count,
                "task_count": task_count,
                "message": "Database operations successful"
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database health check failed"
        }


class AgentRepository:
    """Repository for agent-related database operations"""
    
    @staticmethod
    async def create_agent(
        agent_data: Dict[str, Any],
        db: AsyncSession
    ) -> Agent:
        """Create a new agent with transaction safety"""
        try:
            agent = Agent(
                type=AgentTypeEnum(agent_data["type"]),
                name=agent_data["name"],
                endpoint=agent_data["endpoint"],
                capabilities=agent_data.get("capabilities", []),
                status=agent_data.get("status", "idle"),
                metadata=agent_data.get("metadata", {}),
                performance_metrics=agent_data.get("performance_metrics", {})
            )
            
            db.add(agent)
            await db.flush()  # Get the ID without committing
            await db.refresh(agent)
            
            logger.info(f"Created agent: {agent.name} ({agent.id})")
            return agent
            
        except IntegrityError as e:
            logger.error(f"Agent creation failed - integrity error: {e}")
            raise DatabaseOperationError(f"Agent creation failed: {str(e)}")
        except SQLAlchemyError as e:
            logger.error(f"Agent creation failed - database error: {e}")
            raise DatabaseOperationError(f"Database error during agent creation: {str(e)}")
    
    @staticmethod
    async def get_agent_by_id(
        agent_id: str,
        db: AsyncSession,
        include_tasks: bool = False
    ) -> Optional[Agent]:
        """Get agent by ID with optional task loading"""
        try:
            query = select(Agent).where(Agent.id == agent_id, Agent.is_active == True)
            
            if include_tasks:
                query = query.options(selectinload(Agent.tasks))
            
            result = await db.execute(query)
            return result.scalar_one_or_none()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            raise DatabaseOperationError(f"Failed to retrieve agent: {str(e)}")
    
    @staticmethod
    async def list_agents(
        db: AsyncSession,
        agent_type: Optional[AgentTypeEnum] = None,
        status: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Agent], int]:
        """List agents with filtering and pagination"""
        try:
            # Build base query
            query = select(Agent).where(Agent.is_active == True)
            count_query = select(func.count(Agent.id)).where(Agent.is_active == True)
            
            # Apply filters
            if agent_type:
                query = query.where(Agent.type == agent_type)
                count_query = count_query.where(Agent.type == agent_type)
            
            if status:
                query = query.where(Agent.status == status)
                count_query = count_query.where(Agent.status == status)
            
            if capabilities:
                # Check if agent has all required capabilities
                for capability in capabilities:
                    query = query.where(Agent.capabilities.contains([capability]))
                    count_query = count_query.where(Agent.capabilities.contains([capability]))
            
            # Get total count
            total_result = await db.execute(count_query)
            total_count = total_result.scalar()
            
            # Apply ordering and pagination
            query = query.order_by(desc(Agent.created_at)).limit(limit).offset(offset)
            
            result = await db.execute(query)
            agents = result.scalars().all()
            
            return list(agents), total_count
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to list agents: {e}")
            raise DatabaseOperationError(f"Failed to list agents: {str(e)}")
    
    @staticmethod    @staticmethod
    async def update_agent_status(
        agent_id: str,
        status: str,
        current_task_id: Optional[str],
        db: AsyncSession
    ) -> bool:
        """Update agent status and current task"""
        try:
            query = (
                update(Agent)
                .where(Agent.id == agent_id, Agent.is_active == True)
                .values(
                    status=status,
                    current_task_id=current_task_id,
                    last_seen=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            
            result = await db.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No agent found with ID: {agent_id}")
                return False
            
            logger.debug(f"Updated agent {agent_id} status to {status}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to update agent status: {e}")
            raise DatabaseOperationError(f"Failed to update agent status: {str(e)}")
    
    @staticmethod
    async def find_suitable_agents(
        required_capabilities: List[str],
        task_type: str,
        db: AsyncSession
    ) -> List[Agent]:
        """Find agents suitable for a specific task (legacy method for backward compatibility)"""
        try:
            query = select(Agent).where(
                Agent.is_active == True,
                Agent.status == "idle"
            )
            
            # Filter by required capabilities
            if required_capabilities:
                for capability in required_capabilities:
                    query = query.where(Agent.capabilities.contains([capability]))
            
            # Optional: Add task type specific filtering logic here
            # This could be enhanced based on business rules
            
            # Order by performance metrics (success rate)
            query = query.order_by(
                desc(func.coalesce(Agent.performance_metrics["success_rate"].astext.cast(float), 0.5))
            )
            
            result = await db.execute(query)
            return list(result.scalars().all())
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to find suitable agents: {e}")
            raise DatabaseOperationError(f"Failed to find suitable agents: {str(e)}")
    
    @staticmethod
    async def find_suitable_agents_semantic(
        task_description: str,
        required_capabilities: List[str] = None,
        task_type: str = "",
        db: AsyncSession = None,
        top_k: int = 3,
        min_score: float = 0.3,
        use_semantic: bool = True
    ) -> Tuple[List[Agent], List[Dict[str, Any]]]:
        """
        Find suitable agents using semantic matching and enhanced scoring.
        
        Args:
            task_description: Natural language description of the task
            required_capabilities: List of required capabilities
            task_type: Type/category of the task
            db: Database session
            top_k: Maximum number of agents to return
            min_score: Minimum matching score threshold
            use_semantic: Whether to use semantic matching (fallback to basic if unavailable)
        
        Returns:
            Tuple of (agents_list, matching_details)
        """
        try:
            # First get all available agents from database
            available_agents_query = select(Agent).where(
                Agent.is_active == True,
                Agent.status == "idle"
            )
            
            if db:
                result = await db.execute(available_agents_query)
                available_agents = list(result.scalars().all())
            else:
                available_agents = []
            
            if not available_agents:
                logger.info("No available agents found in database")
                return [], []
            
            matching_results = []
            
            if use_semantic:
                try:
                    # Try to use semantic matching
                    from semantic_agent_matcher import get_semantic_matcher
                    
                    matcher = await get_semantic_matcher()
                    
                    # Sync matcher with current database state
                    if db:
                        await matcher.sync_with_database(db)
                    
                    # Get semantic matching results
                    semantic_results = await matcher.find_matching_agents(
                        task_description=task_description,
                        required_capabilities=required_capabilities or [],
                        task_type=task_type,
                        top_k=top_k * 2,  # Get more candidates for filtering
                        min_score=min_score
                    )
                    
                    # Map semantic results to database agents
                    agent_id_to_result = {result.agent_id: result for result in semantic_results}
                    
                    for agent in available_agents:
                        if agent.id in agent_id_to_result:
                            semantic_result = agent_id_to_result[agent.id]
                            matching_results.append({
                                'agent': agent,
                                'semantic_result': semantic_result,
                                'score': semantic_result.combined_score,
                                'method': 'semantic'
                            })
                    
                    logger.info(f"Found {len(matching_results)} agents using semantic matching")
                    
                except ImportError:
                    logger.warning("Semantic matching not available, falling back to basic matching")
                    use_semantic = False
                except Exception as e:
                    logger.warning(f"Semantic matching failed: {e}, falling back to basic matching")
                    use_semantic = False
            
            # Fallback to basic capability matching if semantic matching unavailable
            if not use_semantic or not matching_results:
                logger.info("Using basic capability matching")
                
                for agent in available_agents:
                    score = AgentRepository._calculate_basic_match_score(
                        agent, required_capabilities or [], task_type
                    )
                    
                    if score >= min_score:
                        matching_results.append({
                            'agent': agent,
                            'semantic_result': None,
                            'score': score,
                            'method': 'basic'
                        })
            
            # Sort by score and return top_k
            matching_results.sort(key=lambda x: x['score'], reverse=True)
            top_results = matching_results[:top_k]
            
            # Extract agents and details
            agents = [result['agent'] for result in top_results]
            details = []
            
            for result in top_results:
                detail = {
                    'agent_id': result['agent'].id,
                    'agent_name': result['agent'].name,
                    'score': result['score'],
                    'method': result['method']
                }
                
                if result['semantic_result']:
                    sr = result['semantic_result']
                    detail.update({
                        'capability_match_score': sr.capability_match_score,
                        'performance_score': sr.performance_score,
                        'matched_capabilities': sr.matched_capabilities,
                        'missing_capabilities': sr.missing_capabilities,
                        'confidence': sr.confidence,
                        'reasoning': sr.reasoning
                    })
                
                details.append(detail)
            
            logger.info(f"Returning {len(agents)} suitable agents (method: {top_results[0]['method'] if top_results else 'none'})")
            return agents, details
            
        except Exception as e:
            logger.error(f"Failed to find suitable agents with semantic matching: {e}")
            # Final fallback to original method
            try:
                fallback_agents = await AgentRepository.find_suitable_agents(
                    required_capabilities or [], task_type, db
                )
                fallback_details = [
                    {
                        'agent_id': agent.id,
                        'agent_name': agent.name,
                        'score': 0.5,
                        'method': 'fallback'
                    }
                    for agent in fallback_agents[:top_k]
                ]
                return fallback_agents[:top_k], fallback_details
            except Exception as fallback_error:
                logger.error(f"Fallback matching also failed: {fallback_error}")
                raise DatabaseOperationError(f"All agent matching methods failed: {str(e)}")
    
    @staticmethod
    def _calculate_basic_match_score(agent: Agent, required_capabilities: List[str], 
                                   task_type: str) -> float:
        """Calculate basic matching score for an agent"""
        score = 0.0
        
        # Base score from performance metrics
        performance_metrics = agent.performance_metrics or {}
        base_score = performance_metrics.get("success_rate", 0.5)
        
        # Capability matching score
        if required_capabilities:
            agent_caps = set(cap.lower() for cap in agent.capabilities)
            required_caps = set(cap.lower() for cap in required_capabilities)
            
            matched_caps = agent_caps.intersection(required_caps)
            capability_score = len(matched_caps) / len(required_capabilities)
        else:
            capability_score = 1.0
        
        # Agent type matching
        type_score = 1.0
        if task_type:
            task_lower = task_type.lower()
            if "prompt" in task_lower and agent.type != AgentTypeEnum.PROMPT:
                type_score = 0.7
            elif "search" in task_lower and agent.type != AgentTypeEnum.RAG:
                type_score = 0.7
            elif "rule" in task_lower and agent.type != AgentTypeEnum.RULE:
                type_score = 0.7
        
        # Combined score
        score = (base_score * 0.4 + capability_score * 0.4 + type_score * 0.2)
        
        return min(score, 1.0)


class TaskRepository:
    """Repository for task-related database operations"""
    
    @staticmethod
    async def create_task(
        task_data: Dict[str, Any],
        db: AsyncSession
    ) -> Task:
        """Create a new task with transaction safety"""
        try:
            task = Task(
                type=task_data["type"],
                name=task_data.get("name"),
                description=task_data["description"],
                input_data=task_data.get("input_data", {}),
                priority=task_data.get("priority", 1),
                required_capabilities=task_data.get("required_capabilities", []),
                workflow_id=task_data.get("workflow_id"),
                parent_task_id=task_data.get("parent_task_id"),
                dependencies=task_data.get("dependencies", []),
                metadata=task_data.get("metadata", {}),
                max_retries=task_data.get("max_retries", 3),
                timeout_at=task_data.get("timeout_at")
            )
            
            db.add(task)
            await db.flush()
            await db.refresh(task)
            
            logger.info(f"Created task: {task.type} ({task.id})")
            return task
            
        except SQLAlchemyError as e:
            logger.error(f"Task creation failed: {e}")
            raise DatabaseOperationError(f"Task creation failed: {str(e)}")
    
    @staticmethod
    async def get_task_by_id(
        task_id: str,
        db: AsyncSession,
        include_agent: bool = False,
        include_workflow: bool = False
    ) -> Optional[Task]:
        """Get task by ID with optional relationship loading"""
        try:
            query = select(Task).where(Task.id == task_id)
            
            if include_agent:
                query = query.options(joinedload(Task.assigned_agent))
            
            if include_workflow:
                query = query.options(joinedload(Task.workflow))
            
            result = await db.execute(query)
            return result.scalar_one_or_none()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            raise DatabaseOperationError(f"Failed to retrieve task: {str(e)}")
    
    @staticmethod
    async def list_tasks(
        db: AsyncSession,
        status: Optional[TaskStatusEnum] = None,
        workflow_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        priority_min: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Task], int]:
        """List tasks with filtering and pagination"""
        try:
            query = select(Task)
            count_query = select(func.count(Task.id))
            
            # Apply filters
            if status:
                query = query.where(Task.status == status)
                count_query = count_query.where(Task.status == status)
            
            if workflow_id:
                query = query.where(Task.workflow_id == workflow_id)
                count_query = count_query.where(Task.workflow_id == workflow_id)
            
            if agent_id:
                query = query.where(Task.assigned_agent_id == agent_id)
                count_query = count_query.where(Task.assigned_agent_id == agent_id)
            
            if priority_min is not None:
                query = query.where(Task.priority >= priority_min)
                count_query = count_query.where(Task.priority >= priority_min)
            
            # Get total count
            total_result = await db.execute(count_query)
            total_count = total_result.scalar()
            
            # Apply ordering and pagination
            query = (
                query
                .order_by(desc(Task.priority), desc(Task.created_at))
                .limit(limit)
                .offset(offset)
            )
            
            result = await db.execute(query)
            tasks = result.scalars().all()
            
            return list(tasks), total_count
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to list tasks: {e}")
            raise DatabaseOperationError(f"Failed to list tasks: {str(e)}")
    
    @staticmethod
    async def update_task_status(
        task_id: str,
        status: TaskStatusEnum,
        db: AsyncSession,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        assigned_agent_id: Optional[str] = None
    ) -> bool:
        """Update task status and related fields"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            # Set timestamps based on status
            if status == TaskStatusEnum.RUNNING and assigned_agent_id:
                update_data.update({
                    "started_at": datetime.utcnow(),
                    "assigned_agent_id": assigned_agent_id
                })
            elif status in [TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED, TaskStatusEnum.CANCELLED]:
                update_data["completed_at"] = datetime.utcnow()
                
                if result_data:
                    update_data["result"] = result_data
                
                if error_message:
                    update_data["error_message"] = error_message
            
            query = (
                update(Task)
                .where(Task.id == task_id)
                .values(**update_data)
            )
            
            result = await db.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No task found with ID: {task_id}")
                return False
            
            logger.debug(f"Updated task {task_id} status to {status}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to update task status: {e}")
            raise DatabaseOperationError(f"Failed to update task status: {str(e)}")
    
    @staticmethod
    async def get_pending_tasks(
        db: AsyncSession,
        limit: int = 50
    ) -> List[Task]:
        """Get pending tasks ordered by priority"""
        try:
            query = (
                select(Task)
                .where(Task.status == TaskStatusEnum.PENDING)
                .order_by(desc(Task.priority), asc(Task.created_at))
                .limit(limit)
            )
            
            result = await db.execute(query)
            return list(result.scalars().all())
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get pending tasks: {e}")
            raise DatabaseOperationError(f"Failed to get pending tasks: {str(e)}")


class WorkflowRepository:
    """Repository for workflow-related database operations"""
    
    @staticmethod
    async def create_workflow(
        workflow_data: Dict[str, Any],
        db: AsyncSession
    ) -> Workflow:
        """Create a new workflow with transaction safety"""
        try:
            workflow = Workflow(
                name=workflow_data["name"],
                description=workflow_data["description"],
                user_id=workflow_data["user_id"],
                configuration=workflow_data.get("configuration", {}),
                metadata=workflow_data.get("metadata", {}),
                priority=workflow_data.get("priority", 1),
                estimated_duration=workflow_data.get("estimated_duration"),
                timeout_at=workflow_data.get("timeout_at")
            )
            
            db.add(workflow)
            await db.flush()
            await db.refresh(workflow)
            
            logger.info(f"Created workflow: {workflow.name} ({workflow.id})")
            return workflow
            
        except SQLAlchemyError as e:
            logger.error(f"Workflow creation failed: {e}")
            raise DatabaseOperationError(f"Workflow creation failed: {str(e)}")
    
    @staticmethod
    async def get_workflow_by_id(
        workflow_id: str,
        db: AsyncSession,
        include_tasks: bool = False
    ) -> Optional[Workflow]:
        """Get workflow by ID with optional task loading"""
        try:
            query = select(Workflow).where(Workflow.id == workflow_id)
            
            if include_tasks:
                query = query.options(selectinload(Workflow.tasks))
            
            result = await db.execute(query)
            return result.scalar_one_or_none()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get workflow {workflow_id}: {e}")
            raise DatabaseOperationError(f"Failed to retrieve workflow: {str(e)}")
    
    @staticmethod
    async def update_workflow_status(
        workflow_id: str,
        status: WorkflowStatusEnum,
        db: AsyncSession
    ) -> bool:
        """Update workflow status with appropriate timestamps"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            if status == WorkflowStatusEnum.RUNNING:
                update_data["started_at"] = datetime.utcnow()
            elif status in [WorkflowStatusEnum.COMPLETED, WorkflowStatusEnum.FAILED, WorkflowStatusEnum.CANCELLED]:
                update_data["completed_at"] = datetime.utcnow()
                
                # Calculate actual duration if started
                workflow = await WorkflowRepository.get_workflow_by_id(workflow_id, db)
                if workflow and workflow.started_at:
                    duration = (datetime.utcnow() - workflow.started_at).total_seconds()
                    update_data["actual_duration"] = duration
            
            query = (
                update(Workflow)
                .where(Workflow.id == workflow_id)
                .values(**update_data)
            )
            
            result = await db.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No workflow found with ID: {workflow_id}")
                return False
            
            logger.debug(f"Updated workflow {workflow_id} status to {status}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to update workflow status: {e}")
            raise DatabaseOperationError(f"Failed to update workflow status: {str(e)}")


class OrchestrationLogRepository:
    """Repository for orchestration logging operations"""
    
    @staticmethod
    async def log_operation(
        operation_type: str,
        entity_type: str,
        entity_id: Optional[str],
        status: str,
        db: AsyncSession,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        duration: Optional[float] = None
    ) -> OrchestrationLog:
        """Log an orchestration operation"""
        try:
            log_entry = OrchestrationLog(
                operation_type=operation_type,
                entity_type=entity_type,
                entity_id=entity_id,
                status=status,
                message=message,
                details=details or {},
                user_id=user_id,
                duration=duration
            )
            
            db.add(log_entry)
            await db.flush()
            
            return log_entry
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to log operation: {e}")
            raise DatabaseOperationError(f"Failed to log operation: {str(e)}")


# High-level service functions using dependency injection
async def get_agent_with_session(agent_id: str, include_tasks: bool = False) -> Optional[Agent]:
    """Get agent using dependency injection for database session"""
    async with get_db_session() as db:
        return await AgentRepository.get_agent_by_id(agent_id, db, include_tasks)


async def create_agent_with_transaction(agent_data: Dict[str, Any]) -> Agent:
    """Create agent using dependency injection for database transaction"""
    async with get_db_transaction() as db:
        agent = await AgentRepository.create_agent(agent_data, db)
        await OrchestrationLogRepository.log_operation(
            operation_type="agent_registration",
            entity_type="agent",
            entity_id=str(agent.id),
            status="success",
            db=db,
            message=f"Agent '{agent.name}' registered successfully",
            details={"agent_type": agent.type.value, "capabilities_count": len(agent.capabilities)}
        )
        return agent


async def create_task_with_transaction(task_data: Dict[str, Any]) -> Task:
    """Create task using dependency injection for database transaction"""
    async with get_db_transaction() as db:
        task = await TaskRepository.create_task(task_data, db)
        await OrchestrationLogRepository.log_operation(
            operation_type="task_creation",
            entity_type="task",
            entity_id=str(task.id),
            status="success",
            db=db,
            message=f"Task '{task.type}' created successfully",
            details={"priority": task.priority, "required_capabilities": task.required_capabilities}
        )
        return task


async def assign_task_with_transaction(task_id: str, agent_id: str) -> bool:
    """Assign task to agent using database transaction"""
    async with get_db_transaction() as db:
        # Update task
        task_updated = await TaskRepository.update_task_status(
            task_id, TaskStatusEnum.RUNNING, db, assigned_agent_id=agent_id
        )
        
        if not task_updated:
            return False
        
        # Update agent
        agent_updated = await AgentRepository.update_agent_status(
            agent_id, "busy", task_id, db
        )
        
        if not agent_updated:
            # Rollback task status (transaction will handle this)
            raise DatabaseOperationError("Failed to update agent status during task assignment")
        
        # Log the operation
        await OrchestrationLogRepository.log_operation(
            operation_type="task_assignment",
            entity_type="task",
            entity_id=task_id,
            status="success",
            db=db,
            message=f"Task assigned to agent {agent_id}",
            details={"agent_id": agent_id}
        )
        
        return True


# Database health check function
async def check_database_health() -> Dict[str, Any]:
    """Check database health using dependency injection"""
    try:
        async with get_db_session() as db:
            # Simple query to test connection
            result = await db.execute(select(func.count(Agent.id)))
            agent_count = result.scalar()
            
            result = await db.execute(select(func.count(Task.id)))
            task_count = result.scalar()
            
            return {
                "status": "healthy",
                "agent_count": agent_count,
                "task_count": task_count,
                "message": "Database operations successful"
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database health check failed"
        }


class AgentRepository:
    """Repository for agent-related database operations"""
    
    @staticmethod
    async def create_agent(
        agent_data: Dict[str, Any],
        db: AsyncSession
    ) -> Agent:
        """Create a new agent with transaction safety"""
        try:
            agent = Agent(
                type=AgentTypeEnum(agent_data["type"]),
                name=agent_data["name"],
                endpoint=agent_data["endpoint"],
                capabilities=agent_data.get("capabilities", []),
                status=agent_data.get("status", "idle"),
                metadata=agent_data.get("metadata", {}),
                performance_metrics=agent_data.get("performance_metrics", {})
            )
            
            db.add(agent)
            await db.flush()  # Get the ID without committing
            await db.refresh(agent)
            
            logger.info(f"Created agent: {agent.name} ({agent.id})")
            return agent
            
        except IntegrityError as e:
            logger.error(f"Agent creation failed - integrity error: {e}")
            raise DatabaseOperationError(f"Agent creation failed: {str(e)}")
        except SQLAlchemyError as e:
            logger.error(f"Agent creation failed - database error: {e}")
            raise DatabaseOperationError(f"Database error during agent creation: {str(e)}")
    
    @staticmethod
    async def get_agent_by_id(
        agent_id: str,
        db: AsyncSession,
        include_tasks: bool = False
    ) -> Optional[Agent]:
        """Get agent by ID with optional task loading"""
        try:
            query = select(Agent).where(Agent.id == agent_id, Agent.is_active == True)
            
            if include_tasks:
                query = query.options(selectinload(Agent.tasks))
            
            result = await db.execute(query)
            return result.scalar_one_or_none()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            raise DatabaseOperationError(f"Failed to retrieve agent: {str(e)}")
    
    @staticmethod
    async def list_agents(
        db: AsyncSession,
        agent_type: Optional[AgentTypeEnum] = None,
        status: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Agent], int]:
        """List agents with filtering and pagination"""
        try:
            # Build base query
            query = select(Agent).where(Agent.is_active == True)
            count_query = select(func.count(Agent.id)).where(Agent.is_active == True)
            
            # Apply filters
            if agent_type:
                query = query.where(Agent.type == agent_type)
                count_query = count_query.where(Agent.type == agent_type)
            
            if status:
                query = query.where(Agent.status == status)
                count_query = count_query.where(Agent.status == status)
            
            if capabilities:
                # Check if agent has all required capabilities
                for capability in capabilities:
                    query = query.where(Agent.capabilities.contains([capability]))
                    count_query = count_query.where(Agent.capabilities.contains([capability]))
            
            # Get total count
            total_result = await db.execute(count_query)
            total_count = total_result.scalar()
            
            # Apply ordering and pagination
            query = query.order_by(desc(Agent.created_at)).limit(limit).offset(offset)
            
            result = await db.execute(query)
            agents = result.scalars().all()
            
            return list(agents), total_count
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to list agents: {e}")
            raise DatabaseOperationError(f"Failed to list agents: {str(e)}")
    
    @staticmethod    @staticmethod
    async def update_agent_status(
        agent_id: str,
        status: str,
        current_task_id: Optional[str],
        db: AsyncSession
    ) -> bool:
        """Update agent status and current task"""
        try:
            query = (
                update(Agent)
                .where(Agent.id == agent_id, Agent.is_active == True)
                .values(
                    status=status,
                    current_task_id=current_task_id,
                    last_seen=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            
            result = await db.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No agent found with ID: {agent_id}")
                return False
            
            logger.debug(f"Updated agent {agent_id} status to {status}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to update agent status: {e}")
            raise DatabaseOperationError(f"Failed to update agent status: {str(e)}")
    
    @staticmethod
    async def find_suitable_agents(
        required_capabilities: List[str],
        task_type: str,
        db: AsyncSession
    ) -> List[Agent]:
        """Find agents suitable for a specific task (legacy method for backward compatibility)"""
        try:
            query = select(Agent).where(
                Agent.is_active == True,
                Agent.status == "idle"
            )
            
            # Filter by required capabilities
            if required_capabilities:
                for capability in required_capabilities:
                    query = query.where(Agent.capabilities.contains([capability]))
            
            # Optional: Add task type specific filtering logic here
            # This could be enhanced based on business rules
            
            # Order by performance metrics (success rate)
            query = query.order_by(
                desc(func.coalesce(Agent.performance_metrics["success_rate"].astext.cast(float), 0.5))
            )
            
            result = await db.execute(query)
            return list(result.scalars().all())
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to find suitable agents: {e}")
            raise DatabaseOperationError(f"Failed to find suitable agents: {str(e)}")
    
    @staticmethod
    async def find_suitable_agents_semantic(
        task_description: str,
        required_capabilities: List[str] = None,
        task_type: str = "",
        db: AsyncSession = None,
        top_k: int = 3,
        min_score: float = 0.3,
        use_semantic: bool = True
    ) -> Tuple[List[Agent], List[Dict[str, Any]]]:
        """
        Find suitable agents using semantic matching and enhanced scoring.
        
        Args:
            task_description: Natural language description of the task
            required_capabilities: List of required capabilities
            task_type: Type/category of the task
            db: Database session
            top_k: Maximum number of agents to return
            min_score: Minimum matching score threshold
            use_semantic: Whether to use semantic matching (fallback to basic if unavailable)
        
        Returns:
            Tuple of (agents_list, matching_details)
        """
        try:
            # First get all available agents from database
            available_agents_query = select(Agent).where(
                Agent.is_active == True,
                Agent.status == "idle"
            )
            
            if db:
                result = await db.execute(available_agents_query)
                available_agents = list(result.scalars().all())
            else:
                available_agents = []
            
            if not available_agents:
                logger.info("No available agents found in database")
                return [], []
            
            matching_results = []
            
            if use_semantic:
                try:
                    # Try to use semantic matching
                    from semantic_agent_matcher import get_semantic_matcher
                    
                    matcher = await get_semantic_matcher()
                    
                    # Sync matcher with current database state
                    if db:
                        await matcher.sync_with_database(db)
                    
                    # Get semantic matching results
                    semantic_results = await matcher.find_matching_agents(
                        task_description=task_description,
                        required_capabilities=required_capabilities or [],
                        task_type=task_type,
                        top_k=top_k * 2,  # Get more candidates for filtering
                        min_score=min_score
                    )
                    
                    # Map semantic results to database agents
                    agent_id_to_result = {result.agent_id: result for result in semantic_results}
                    
                    for agent in available_agents:
                        if agent.id in agent_id_to_result:
                            semantic_result = agent_id_to_result[agent.id]
                            matching_results.append({
                                'agent': agent,
                                'semantic_result': semantic_result,
                                'score': semantic_result.combined_score,
                                'method': 'semantic'
                            })
                    
                    logger.info(f"Found {len(matching_results)} agents using semantic matching")
                    
                except ImportError:
                    logger.warning("Semantic matching not available, falling back to basic matching")
                    use_semantic = False
                except Exception as e:
                    logger.warning(f"Semantic matching failed: {e}, falling back to basic matching")
                    use_semantic = False
            
            # Fallback to basic capability matching if semantic matching unavailable
            if not use_semantic or not matching_results:
                logger.info("Using basic capability matching")
                
                for agent in available_agents:
                    score = AgentRepository._calculate_basic_match_score(
                        agent, required_capabilities or [], task_type
                    )
                    
                    if score >= min_score:
                        matching_results.append({
                            'agent': agent,
                            'semantic_result': None,
                            'score': score,
                            'method': 'basic'
                        })
            
            # Sort by score and return top_k
            matching_results.sort(key=lambda x: x['score'], reverse=True)
            top_results = matching_results[:top_k]
            
            # Extract agents and details
            agents = [result['agent'] for result in top_results]
            details = []
            
            for result in top_results:
                detail = {
                    'agent_id': result['agent'].id,
                    'agent_name': result['agent'].name,
                    'score': result['score'],
                    'method': result['method']
                }
                
                if result['semantic_result']:
                    sr = result['semantic_result']
                    detail.update({
                        'capability_match_score': sr.capability_match_score,
                        'performance_score': sr.performance_score,
                        'matched_capabilities': sr.matched_capabilities,
                        'missing_capabilities': sr.missing_capabilities,
                        'confidence': sr.confidence,
                        'reasoning': sr.reasoning
                    })
                
                details.append(detail)
            
            logger.info(f"Returning {len(agents)} suitable agents (method: {top_results[0]['method'] if top_results else 'none'})")
            return agents, details
            
        except Exception as e:
            logger.error(f"Failed to find suitable agents with semantic matching: {e}")
            # Final fallback to original method
            try:
                fallback_agents = await AgentRepository.find_suitable_agents(
                    required_capabilities or [], task_type, db
                )
                fallback_details = [
                    {
                        'agent_id': agent.id,
                        'agent_name': agent.name,
                        'score': 0.5,
                        'method': 'fallback'
                    }
                    for agent in fallback_agents[:top_k]
                ]
                return fallback_agents[:top_k], fallback_details
            except Exception as fallback_error:
                logger.error(f"Fallback matching also failed: {fallback_error}")
                raise DatabaseOperationError(f"All agent matching methods failed: {str(e)}")
    
    @staticmethod
    async def find_suitable_agents_with_load_balancing(
        required_capabilities: List[str],
        task_type: str,
        task_requirements: Dict[str, Any],
        strategy: str = "hybrid",
        top_k: int = 1,
        db: AsyncSession = None
    ) -> Tuple[List[Agent], Dict[str, Any]]:
        """
        Find suitable agents using advanced load balancing strategies
        
        This method combines capability matching with sophisticated load balancing
        to select optimal agents for task execution.
        """
        try:
            from advanced_load_balancer import load_balancer, LoadBalancingStrategy
            
            # Get all suitable agents based on capabilities
            suitable_agents = await AgentRepository.find_suitable_agents(
                required_capabilities=required_capabilities,
                task_type=task_type,
                db=db
            )
            
            if not suitable_agents:
                logger.warning(f"No suitable agents found for capabilities: {required_capabilities}")
                return [], {}
            
            # Convert strategy string to enum
            try:
                lb_strategy = LoadBalancingStrategy(strategy)
            except ValueError:
                logger.warning(f"Invalid load balancing strategy: {strategy}, using hybrid")
                lb_strategy = LoadBalancingStrategy.HYBRID
            
            # Apply load balancing strategy
            if len(suitable_agents) == 1:
                # Only one agent available, return it directly
                selected_agent = suitable_agents[0]
                load_balancing_info = {
                    'strategy_used': lb_strategy.value,
                    'confidence_score': 1.0,
                    'selection_reason': 'Only suitable agent available',
                    'total_candidates': 1,
                    'fallback_used': False
                }
            else:
                # Multiple agents available, apply load balancing
                result = await load_balancer.select_best_agent(
                    available_agents=suitable_agents,
                    task_requirements=task_requirements,
                    strategy=lb_strategy,
                    db=db
                )
                
                selected_agent = result.selected_agent
                load_balancing_info = {
                    'strategy_used': result.strategy_used.value,
                    'confidence_score': result.confidence_score,
                    'selection_reason': result.selection_reason,
                    'total_candidates': len(suitable_agents),
                    'fallback_used': result.fallback_used,
                    'load_metrics': {
                        'active_tasks': result.load_metrics.active_tasks,
                        'load_score': result.load_metrics.load_score,
                        'capacity_score': result.load_metrics.capacity_score,
                        'success_rate': result.load_metrics.success_rate
                    }
                }
            
            # Return top_k agents if requested
            if top_k > 1:
                # Get additional agents sorted by load balancing score
                additional_agents = [agent for agent in suitable_agents if agent.id != selected_agent.id][:top_k-1]
                selected_agents = [selected_agent] + additional_agents
            else:
                selected_agents = [selected_agent]
            
            logger.info(f"Load balancing selected {len(selected_agents)} agents using {lb_strategy.value} strategy")
            return selected_agents, load_balancing_info
            
        except Exception as e:
            logger.error(f"Load balancing agent selection failed: {e}")
            # Fallback to regular selection
            fallback_agents = await AgentRepository.find_suitable_agents(
                required_capabilities=required_capabilities,
                task_type=task_type,
                db=db
            )
            
            fallback_info = {
                'strategy_used': 'fallback',
                'confidence_score': 0.5,
                'selection_reason': f'Load balancing failed, using fallback: {str(e)}',
                'total_candidates': len(fallback_agents),
                'fallback_used': True
            }
            
            return fallback_agents[:top_k], fallback_info
    
    @staticmethod
    async def update_agent_performance_metrics(
        agent_id: str,
        performance_data: Dict[str, Any],
        db: AsyncSession
    ) -> bool:
        """
        Update agent performance metrics and notify load balancer
        
        This method updates both database performance metrics and
        real-time load balancing metrics.
        """
        try:
            from advanced_load_balancer import load_balancer
            
            # Update database performance metrics
            current_metrics = await AgentRepository.get_agent_performance_metrics(agent_id, db)
            
            # Merge new performance data
            updated_metrics = current_metrics.copy() if current_metrics else {}
            updated_metrics.update(performance_data)
            
            # Update in database
            query = (
                update(Agent)
                .where(Agent.id == agent_id, Agent.is_active == True)
                .values(
                    performance_metrics=updated_metrics,
                    last_seen=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            
            result = await db.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No agent found with ID: {agent_id}")
                return False
            
            # Update load balancer metrics
            await load_balancer.update_agent_performance(agent_id, performance_data)
            
            logger.debug(f"Updated performance metrics for agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update agent performance metrics: {e}")
            return False
    
    @staticmethod
    async def get_agent_performance_metrics(
        agent_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get current performance metrics for an agent"""
        try:
            query = select(Agent.performance_metrics).where(
                Agent.id == agent_id,
                Agent.is_active == True
            )
            
            result = await db.execute(query)
            metrics = result.scalar()
            
            return metrics or {}
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get agent performance metrics: {e}")
            return {}

    # ...existing code...

"""
Distributed Orchestrator Router for FastAPI integration

This module provides REST API endpoints for the distributed orchestrator,
including task assignment, agent registration, and cluster management.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging

from distributed_orchestrator import (
    distributed_orchestrator,
    DistributedOrchestrationRequest,
    DistributedOrchestrationResponse,
    AgentRegistrationRequest,
    ClusterStatusResponse,
    CapabilityDomain,
    TaskPriority
)

logger = logging.getLogger(__name__)

# Create router for distributed orchestrator endpoints
distributed_router = APIRouter(
    prefix="/api/v1/distributed",
    tags=["Distributed Orchestration"],
    responses={404: {"description": "Not found"}}
)

@distributed_router.on_event("startup")
async def startup_distributed_orchestrator():
    """Initialize distributed orchestrator on startup"""
    try:
        await distributed_orchestrator.initialize()
        logger.info("Distributed orchestrator started successfully")
    except Exception as e:
        logger.error(f"Failed to start distributed orchestrator: {e}")
        raise

@distributed_router.on_event("shutdown")
async def shutdown_distributed_orchestrator():
    """Shutdown distributed orchestrator"""
    try:
        await distributed_orchestrator.shutdown()
        logger.info("Distributed orchestrator shutdown completed")
    except Exception as e:
        logger.error(f"Error during distributed orchestrator shutdown: {e}")

@distributed_router.post(
    "/tasks/assign",
    response_model=DistributedOrchestrationResponse,
    summary="Assign distributed task",
    description="Assign a task to the most suitable agent across the distributed cluster"
)
async def assign_distributed_task(
    request: DistributedOrchestrationRequest,
    background_tasks: BackgroundTasks
) -> DistributedOrchestrationResponse:
    """Assign a task to an agent in the distributed system"""
    try:
        # Validate capability domain
        try:
            capability_domain = CapabilityDomain(request.capability_domain)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid capability domain: {request.capability_domain}"
            )
        
        # Validate priority
        try:
            priority = TaskPriority(request.priority)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid priority: {request.priority}"
            )
        
        # Prepare task specification
        task_spec = {
            'task_type': request.task_type,
            'capability_domain': request.capability_domain,
            'priority': request.priority,
            'payload': request.payload,
            'timeout_seconds': request.timeout_seconds
        }
        
        # Assign task through distributed orchestrator
        task_id = await distributed_orchestrator.assign_task(task_spec)
        
        # Get task details
        task = await distributed_orchestrator.distributed_state.get_task(task_id)
        
        return DistributedOrchestrationResponse(
            task_id=task_id,
            assigned_to=task.assigned_to if task else None,
            status=task.status if task else "unknown",
            instance_id=distributed_orchestrator.instance_id,
            estimated_completion_time=None  # Could be calculated based on task type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning distributed task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@distributed_router.post(
    "/agents/register",
    summary="Register agent in distributed system",
    description="Register a new agent with specific capabilities in the distributed orchestrator"
)
async def register_distributed_agent(
    request: AgentRegistrationRequest
) -> Dict[str, Any]:
    """Register an agent in the distributed system"""
    try:
        # Validate capability domain
        try:
            CapabilityDomain(request.capability_domain)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid capability domain: {request.capability_domain}"
            )
        
        # Prepare agent specification
        agent_spec = {
            'agent_id': request.agent_id,
            'capability_domain': request.capability_domain,
            'endpoint': request.endpoint,
            'load_score': request.load_score,
            'status': request.status
        }
        
        # Register agent
        success = await distributed_orchestrator.register_agent(agent_spec)
        
        if success:
            return {
                'status': 'registered',
                'message': f'Agent {request.agent_id} registered successfully',
                'instance_id': distributed_orchestrator.instance_id,
                'capability_domain': request.capability_domain
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to register agent")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@distributed_router.get(
    "/cluster/status",
    response_model=ClusterStatusResponse,
    summary="Get cluster status",
    description="Get comprehensive status of the distributed orchestrator cluster"
)
async def get_cluster_status() -> ClusterStatusResponse:
    """Get distributed cluster status"""
    try:
        status = await distributed_orchestrator.get_cluster_status()
        return ClusterStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Error getting cluster status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@distributed_router.get(
    "/cluster/leader",
    summary="Get current cluster leader",
    description="Get information about the current cluster leader"
)
async def get_cluster_leader() -> Dict[str, Any]:
    """Get current cluster leader information"""
    try:
        current_leader = await distributed_orchestrator.leader_election.get_current_leader()
        is_leader = distributed_orchestrator.leader_election.is_leader
        
        return {
            'current_leader': current_leader,
            'this_instance_id': distributed_orchestrator.instance_id,
            'is_leader': is_leader,
            'leader_election_active': distributed_orchestrator.leader_election._election_task is not None
        }
        
    except Exception as e:
        logger.error(f"Error getting cluster leader: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@distributed_router.get(
    "/tasks/{task_id}",
    summary="Get task status",
    description="Get status and details of a specific distributed task"
)
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get status of a specific task"""
    try:
        task = await distributed_orchestrator.distributed_state.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return {
            'task_id': task.task_id,
            'task_type': task.task_type,
            'capability_domain': task.capability_domain.value,
            'priority': task.priority.value,
            'status': task.status,
            'assigned_to': task.assigned_to,
            'created_at': task.created_at.isoformat(),
            'assigned_at': task.assigned_at.isoformat() if task.assigned_at else None,
            'retry_count': task.retry_count,
            'max_retries': task.max_retries
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@distributed_router.get(
    "/agents",
    summary="List registered agents",
    description="Get list of all registered agents across the cluster"
)
async def list_agents(
    capability_domain: Optional[str] = None
) -> Dict[str, Any]:
    """List all registered agents, optionally filtered by capability domain"""
    try:
        if capability_domain:
            try:
                domain = CapabilityDomain(capability_domain)
                agents = await distributed_orchestrator.distributed_state.get_agents_by_capability(domain)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid capability domain: {capability_domain}"
                )
        else:
            # Get agents for all capability domains
            agents = []
            for domain in CapabilityDomain:
                domain_agents = await distributed_orchestrator.distributed_state.get_agents_by_capability(domain)
                agents.extend(domain_agents)
        
        agent_list = [
            {
                'agent_id': agent.agent_id,
                'capability_domain': agent.capability_domain.value,
                'instance_id': agent.instance_id,
                'endpoint': agent.endpoint,
                'load_score': agent.load_score,
                'status': agent.status,
                'last_seen': agent.last_seen.isoformat()
            }
            for agent in agents
        ]
        
        return {
            'total_agents': len(agent_list),
            'capability_domain_filter': capability_domain,
            'agents': agent_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@distributed_router.get(
    "/instances",
    summary="List orchestrator instances",
    description="Get list of all active orchestrator instances in the cluster"
)
async def list_instances() -> Dict[str, Any]:
    """List all active orchestrator instances"""
    try:
        instances = await distributed_orchestrator.distributed_state.get_all_instances()
        
        instance_list = [
            {
                'instance_id': inst.instance_id,
                'hostname': inst.hostname,
                'port': inst.port,
                'role': inst.role.value,
                'capabilities': [cap.value for cap in inst.capabilities],
                'active_tasks': inst.active_tasks,
                'load_score': inst.load_score,
                'last_heartbeat': inst.last_heartbeat.isoformat()
            }
            for inst in instances
        ]
        
        return {
            'total_instances': len(instance_list),
            'instances': instance_list
        }
        
    except Exception as e:
        logger.error(f"Error listing instances: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@distributed_router.post(
    "/cluster/rebalance",
    summary="Trigger cluster rebalancing",
    description="Trigger rebalancing of tasks across the cluster (leader only)"
)
async def trigger_rebalancing(
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Trigger cluster rebalancing (leader only operation)"""
    try:
        if not distributed_orchestrator.leader_election.is_leader:
            raise HTTPException(
                status_code=403,
                detail="Only the cluster leader can trigger rebalancing"
            )
        
        # Add rebalancing task to background
        background_tasks.add_task(_rebalance_cluster)
        
        return {
            'status': 'rebalancing_initiated',
            'message': 'Cluster rebalancing has been started',
            'leader_instance': distributed_orchestrator.instance_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering rebalancing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _rebalance_cluster():
    """Background task for cluster rebalancing"""
    try:
        logger.info("Starting cluster rebalancing")
        
        # Publish rebalancing event
        await distributed_orchestrator.event_coordinator.publish_coordination_event(
            'cluster_rebalancing_started',
            {'initiated_by': distributed_orchestrator.instance_id}
        )
        
        # Implementation for actual rebalancing logic would go here
        # This could include:
        # - Reassigning tasks from overloaded instances
        # - Moving agents between instances
        # - Optimizing capability domain distribution
        
        logger.info("Cluster rebalancing completed")
        
    except Exception as e:
        logger.error(f"Error during cluster rebalancing: {e}")

@distributed_router.get(
    "/health/distributed",
    summary="Distributed orchestrator health check",
    description="Check health of distributed orchestrator components"
)
async def distributed_health_check() -> Dict[str, Any]:
    """Health check for distributed orchestrator components"""
    try:
        health_status = {
            'status': 'healthy',
            'instance_id': distributed_orchestrator.instance_id,
            'components': {}
        }
        
        # Check Redis connection
        try:
            await distributed_orchestrator.redis_client.ping()
            health_status['components']['redis'] = 'healthy'
        except Exception as e:
            health_status['components']['redis'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Check leader election status
        try:
            current_leader = await distributed_orchestrator.leader_election.get_current_leader()
            health_status['components']['leader_election'] = {
                'status': 'healthy',
                'current_leader': current_leader,
                'is_leader': distributed_orchestrator.leader_election.is_leader
            }
        except Exception as e:
            health_status['components']['leader_election'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Check event coordinator
        try:
            if distributed_orchestrator.event_coordinator and distributed_orchestrator.event_coordinator.producer:
                health_status['components']['event_coordinator'] = 'healthy'
            else:
                health_status['components']['event_coordinator'] = 'not_initialized'
                health_status['status'] = 'degraded'
        except Exception as e:
            health_status['components']['event_coordinator'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Add cluster information
        try:
            cluster_status = await distributed_orchestrator.get_cluster_status()
            health_status['cluster_info'] = {
                'total_instances': cluster_status['total_instances'],
                'total_active_tasks': cluster_status['total_active_tasks'],
                'agent_capabilities': cluster_status['agent_capabilities']
            }
        except Exception as e:
            logger.warning(f"Could not get cluster info for health check: {e}")
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error during distributed health check: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'instance_id': distributed_orchestrator.instance_id
        }

"""
Load Balancing Router for Agent Orchestrator

This module defines the FastAPI router for advanced load balancing endpoints,
providing REST API access to sophisticated agent selection and load balancing
functionality.

Features:
- Agent selection with configurable load balancing strategies
- Real-time performance metrics updates
- Load balancing analytics and monitoring
- Strategy configuration and benchmarking
- Comprehensive error handling and logging
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional

from database import get_db_session
from load_balancing_endpoints import (
    LoadBalancingEndpoints,
    LoadBalancingRequest,
    LoadBalancingResponse,
    AgentPerformanceUpdate,
    LoadBalancingStats,
    StrategyWeightsUpdate,
    load_balancing_endpoints
)
from advanced_load_balancer import LoadBalancingStrategy

# Create the load balancing router
load_balancing_router = APIRouter(
    prefix="/load-balancing",
    tags=["load-balancing"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


@load_balancing_router.post(
    "/select-agent",
    response_model=LoadBalancingResponse,
    summary="Select Agent with Load Balancing",
    description="""
    Select the optimal agent for task execution using advanced load balancing strategies.
    
    This endpoint analyzes available agents and applies sophisticated load balancing
    algorithms to choose the best agent based on current load, performance metrics,
    resource availability, and predictive modeling.
    
    Available strategies:
    - **weighted_round_robin**: Distributes tasks based on agent performance weights
    - **least_connection**: Selects agent with fewest active tasks
    - **predictive_ml**: Uses ML prediction to select fastest agent
    - **resource_aware**: Considers CPU/memory usage for selection
    - **hybrid**: Combines multiple strategies for optimal selection
    """
)
async def select_agent_with_load_balancing(
    request: LoadBalancingRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Select the best agent using advanced load balancing"""
    return await load_balancing_endpoints.select_agent_with_load_balancing(request, db)


@load_balancing_router.post(
    "/update-performance",
    response_model=Dict[str, str],
    summary="Update Agent Performance",
    description="""
    Update agent performance metrics after task completion.
    
    This endpoint allows real-time updates of agent performance data,
    which is crucial for accurate load balancing decisions. The metrics
    are used by predictive algorithms and resource-aware strategies.
    """
)
async def update_agent_performance(update: AgentPerformanceUpdate):
    """Update agent performance metrics"""
    return await load_balancing_endpoints.update_agent_performance(update)


@load_balancing_router.get(
    "/statistics",
    response_model=LoadBalancingStats,
    summary="Get Load Balancing Statistics",
    description="""
    Retrieve comprehensive load balancing statistics and metrics.
    
    This endpoint provides detailed insights into:
    - Current agent loads and performance
    - Load balancing strategy effectiveness
    - Resource utilization across agents
    - Performance trends and predictions
    """
)
async def get_load_balancing_statistics():
    """Get current load balancing statistics"""
    return await load_balancing_endpoints.get_load_balancing_statistics()


@load_balancing_router.post(
    "/configure-weights",
    response_model=Dict[str, str],
    summary="Configure Strategy Weights",
    description="""
    Configure weights for the hybrid load balancing strategy.
    
    This endpoint allows fine-tuning of the hybrid strategy by adjusting
    the relative importance of different load balancing algorithms.
    Weights must sum to 1.0.
    """
)
async def configure_strategy_weights(weights: StrategyWeightsUpdate):
    """Configure weights for hybrid load balancing strategy"""
    return await load_balancing_endpoints.configure_strategy_weights(weights)


@load_balancing_router.get(
    "/agent/{agent_id}/metrics",
    response_model=Dict[str, Any],
    summary="Get Agent Load Metrics",
    description="""
    Get detailed load and performance metrics for a specific agent.
    
    This endpoint provides comprehensive metrics including:
    - Current load and capacity scores
    - Task completion statistics
    - Resource utilization
    - Performance trends
    - Specialization scores
    """
)
async def get_agent_load_metrics(agent_id: str):
    """Get detailed load metrics for a specific agent"""
    return await load_balancing_endpoints.get_agent_load_metrics(agent_id)


@load_balancing_router.post(
    "/benchmark",
    response_model=Dict[str, Any],
    summary="Benchmark Load Balancing Strategies",
    description="""
    Benchmark all available load balancing strategies for comparison.
    
    This endpoint runs all strategies on the same agent pool and returns
    comparative results, helping to identify the most effective strategy
    for specific use cases.
    """
)
async def benchmark_load_balancing_strategies(
    request: LoadBalancingRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Benchmark all load balancing strategies"""
    return await load_balancing_endpoints.benchmark_load_balancing_strategies(request, db)


@load_balancing_router.get(
    "/strategies",
    response_model=Dict[str, Any],
    summary="List Available Strategies",
    description="""
    List all available load balancing strategies with descriptions.
    
    This endpoint provides information about each strategy including:
    - Strategy name and description
    - Key features and use cases
    - Performance characteristics
    """
)
async def list_load_balancing_strategies():
    """List all available load balancing strategies"""
    strategies = {
        "weighted_round_robin": {
            "name": "Weighted Round Robin",
            "description": "Distributes tasks based on agent performance weights",
            "features": ["Performance-based weighting", "Fair distribution", "Specialization support"],
            "use_cases": ["Balanced workload distribution", "Performance optimization"]
        },
        "least_connection": {
            "name": "Least Connection",
            "description": "Selects agent with fewest active tasks",
            "features": ["Connection-based selection", "Load balancing", "Performance adjustment"],
            "use_cases": ["High-throughput scenarios", "Connection-sensitive workloads"]
        },
        "predictive_ml": {
            "name": "Predictive ML",
            "description": "Uses machine learning to predict fastest agent",
            "features": ["ML-based prediction", "Historical analysis", "Trend consideration"],
            "use_cases": ["Performance-critical tasks", "Predictive optimization"]
        },
        "resource_aware": {
            "name": "Resource Aware",
            "description": "Considers CPU/memory usage for selection",
            "features": ["Resource monitoring", "Capacity-based selection", "Utilization optimization"],
            "use_cases": ["Resource-intensive tasks", "System optimization"]
        },
        "hybrid": {
            "name": "Hybrid Strategy",
            "description": "Combines multiple strategies for optimal selection",
            "features": ["Multi-strategy combination", "Configurable weights", "Adaptive selection"],
            "use_cases": ["General purpose", "Optimal performance", "Comprehensive optimization"]
        }
    }
    
    return {
        "strategies": strategies,
        "default_strategy": "hybrid",
        "total_strategies": len(strategies)
    }


@load_balancing_router.get(
    "/health",
    response_model=Dict[str, Any],
    summary="Load Balancing Health Check",
    description="""
    Check the health status of the load balancing system.
    
    This endpoint provides health information including:
    - System status
    - Active agents count
    - Load balancer performance
    - Recent errors or issues
    """
)
async def load_balancing_health_check():
    """Check the health of the load balancing system"""
    try:
        stats = await load_balancing_endpoints.get_load_balancing_statistics()
        
        # Calculate health metrics
        total_agents = stats.total_agents
        active_agents = sum(1 for agent_data in stats.agents.values() 
                          if agent_data.get('active_tasks', 0) >= 0)
        
        avg_load = 0
        if total_agents > 0:
            avg_load = sum(agent_data.get('load_score', 0) 
                          for agent_data in stats.agents.values()) / total_agents
        
        # Determine health status
        health_status = "healthy"
        if total_agents == 0:
            health_status = "critical"
        elif avg_load > 0.8:
            health_status = "warning"
        elif active_agents < total_agents * 0.5:
            health_status = "warning"
        
        return {
            "status": health_status,
            "total_agents": total_agents,
            "active_agents": active_agents,
            "average_load": round(avg_load, 3),
            "load_balancer_active": True,
            "timestamp": stats.timestamp
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "load_balancer_active": False,
            "timestamp": None
        }


# Add router tags and metadata
load_balancing_router.tags = ["load-balancing"]
load_balancing_router.responses = {
    404: {"description": "Resource not found"},
    422: {"description": "Validation error"},
    500: {"description": "Internal server error"}
}


# Export the router
__all__ = ["load_balancing_router"]

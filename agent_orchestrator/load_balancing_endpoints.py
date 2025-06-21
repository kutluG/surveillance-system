"""
Load Balancing Endpoints for Agent Orchestrator

This module provides API endpoints for advanced load balancing functionality,
including strategy selection, performance monitoring, and load balancing analytics.

Features:
- Agent selection with various load balancing strategies
- Real-time load balancing metrics and monitoring
- Strategy configuration and performance tuning
- Load balancing analytics and reporting
- Agent performance tracking endpoints
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from database import get_db_session
from db_service import AgentRepository
from advanced_load_balancer import (
    AdvancedLoadBalancer, LoadBalancingStrategy, LoadBalancingResult,
    AgentLoadMetrics, load_balancer
)

logger = logging.getLogger(__name__)


# Pydantic models for API requests/responses
class LoadBalancingRequest(BaseModel):
    """Request model for agent selection with load balancing"""
    required_capabilities: List[str] = Field(default_factory=list)
    task_type: str = Field(default="general")
    task_requirements: Dict[str, Any] = Field(default_factory=dict)
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.HYBRID
    top_k: int = Field(default=1, ge=1, le=10)


class LoadBalancingResponse(BaseModel):
    """Response model for load balancing results"""
    selected_agent_id: str
    selected_agent_name: str
    strategy_used: str
    confidence_score: float
    selection_reason: str
    load_metrics: Dict[str, Any]
    alternative_agents: List[Dict[str, str]] = Field(default_factory=list)
    fallback_used: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentPerformanceUpdate(BaseModel):
    """Model for updating agent performance metrics"""
    agent_id: str
    task_duration: Optional[float] = None
    success: bool = True
    task_type: str = ""
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    active_tasks: Optional[int] = None


class LoadBalancingStats(BaseModel):
    """Model for load balancing statistics"""
    total_agents: int
    agents: Dict[str, Dict[str, Any]]
    strategy_weights: Dict[str, float]
    timestamp: str


class StrategyWeightsUpdate(BaseModel):
    """Model for updating strategy weights"""
    weighted_round_robin: float = Field(ge=0, le=1)
    least_connection: float = Field(ge=0, le=1)
    predictive_ml: float = Field(ge=0, le=1)
    resource_aware: float = Field(ge=0, le=1)


class LoadBalancingEndpoints:
    """Endpoints for advanced load balancing functionality"""
    
    @staticmethod
    async def select_agent_with_load_balancing(
        request: LoadBalancingRequest,
        db: AsyncSession = Depends(get_db_session)
    ) -> LoadBalancingResponse:
        """
        Select the best agent using advanced load balancing strategies
        
        This endpoint finds suitable agents based on capabilities and applies
        sophisticated load balancing algorithms to select the optimal agent
        for task execution.
        """
        try:
            logger.info(f"Load balancing request: strategy={request.strategy}, "
                       f"capabilities={request.required_capabilities}, task_type={request.task_type}")
            
            # Find suitable agents using existing repository
            suitable_agents = await AgentRepository.find_suitable_agents(
                required_capabilities=request.required_capabilities,
                task_type=request.task_type,
                db=db
            )
            
            if not suitable_agents:
                raise HTTPException(
                    status_code=404,
                    detail=f"No suitable agents found for capabilities: {request.required_capabilities}"
                )
            
            # Apply load balancing strategy
            result: LoadBalancingResult = await load_balancer.select_best_agent(
                available_agents=suitable_agents,
                task_requirements=request.task_requirements,
                strategy=request.strategy,
                db=db
            )
            
            # Convert load metrics to dict
            load_metrics_dict = {
                'active_tasks': result.load_metrics.active_tasks,
                'completed_tasks': result.load_metrics.completed_tasks,
                'failed_tasks': result.load_metrics.failed_tasks,
                'success_rate': result.load_metrics.success_rate,
                'avg_task_duration': result.load_metrics.avg_task_duration,
                'cpu_usage': result.load_metrics.cpu_usage,
                'memory_usage': result.load_metrics.memory_usage,
                'load_score': result.load_metrics.load_score,
                'capacity_score': result.load_metrics.capacity_score,
                'workload_trend': result.load_metrics.workload_trend
            }
            
            # Format alternative agents
            alternatives = [
                {
                    'agent_id': agent.id,
                    'agent_name': agent.name,
                    'agent_type': agent.type.value if hasattr(agent.type, 'value') else str(agent.type)
                }
                for agent in result.alternative_agents
            ]
            
            response = LoadBalancingResponse(
                selected_agent_id=result.selected_agent.id,
                selected_agent_name=result.selected_agent.name,
                strategy_used=result.strategy_used.value,
                confidence_score=result.confidence_score,
                selection_reason=result.selection_reason,
                load_metrics=load_metrics_dict,
                alternative_agents=alternatives,
                fallback_used=result.fallback_used
            )
            
            logger.info(f"Selected agent {result.selected_agent.name} with confidence {result.confidence_score:.3f}")
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Load balancing failed: {e}")
            raise HTTPException(status_code=500, detail=f"Load balancing failed: {str(e)}")
    
    @staticmethod
    async def update_agent_performance(
        update: AgentPerformanceUpdate
    ) -> Dict[str, str]:
        """
        Update agent performance metrics after task completion
        
        This endpoint allows the system to update agent performance data
        in real-time, which is used by the load balancing algorithms.
        """
        try:
            task_data = {
                'duration': update.task_duration,
                'success': update.success,
                'task_type': update.task_type,
                'cpu_usage': update.cpu_usage,
                'memory_usage': update.memory_usage,
                'new_active_count': update.active_tasks
            }
            
            await load_balancer.update_agent_performance(update.agent_id, task_data)
            
            logger.info(f"Updated performance metrics for agent {update.agent_id}")
            return {"status": "success", "message": "Agent performance updated"}
            
        except Exception as e:
            logger.error(f"Failed to update agent performance: {e}")
            raise HTTPException(status_code=500, detail=f"Performance update failed: {str(e)}")
    
    @staticmethod
    async def get_load_balancing_statistics() -> LoadBalancingStats:
        """
        Get current load balancing statistics and metrics
        
        This endpoint provides comprehensive statistics about agent loads,
        performance metrics, and load balancing effectiveness.
        """
        try:
            stats = load_balancer.get_load_balancing_stats()
            
            return LoadBalancingStats(
                total_agents=stats['total_agents'],
                agents=stats['agents'],
                strategy_weights=stats['strategy_weights'],
                timestamp=stats['timestamp']
            )
            
        except Exception as e:
            logger.error(f"Failed to get load balancing statistics: {e}")
            raise HTTPException(status_code=500, detail=f"Statistics retrieval failed: {str(e)}")
    
    @staticmethod
    async def configure_strategy_weights(
        weights_update: StrategyWeightsUpdate
    ) -> Dict[str, str]:
        """
        Configure weights for hybrid load balancing strategy
        
        This endpoint allows fine-tuning of the hybrid strategy by adjusting
        the weights of individual load balancing algorithms.
        """
        try:
            # Validate weights sum to 1.0
            total_weight = (
                weights_update.weighted_round_robin +
                weights_update.least_connection +
                weights_update.predictive_ml +
                weights_update.resource_aware
            )
            
            if abs(total_weight - 1.0) > 0.01:
                raise HTTPException(
                    status_code=400,
                    detail=f"Strategy weights must sum to 1.0, got {total_weight}"
                )
            
            # Update weights
            new_weights = {
                LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: weights_update.weighted_round_robin,
                LoadBalancingStrategy.LEAST_CONNECTION: weights_update.least_connection,
                LoadBalancingStrategy.PREDICTIVE_ML: weights_update.predictive_ml,
                LoadBalancingStrategy.RESOURCE_AWARE: weights_update.resource_aware
            }
            
            load_balancer.configure_strategy_weights(new_weights)
            
            logger.info(f"Updated load balancing strategy weights: {new_weights}")
            return {"status": "success", "message": "Strategy weights updated"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update strategy weights: {e}")
            raise HTTPException(status_code=500, detail=f"Strategy weights update failed: {str(e)}")
    
    @staticmethod
    async def get_agent_load_metrics(
        agent_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed load metrics for a specific agent
        
        This endpoint provides comprehensive load and performance metrics
        for individual agents, useful for monitoring and debugging.
        """
        try:
            metrics = load_balancer.load_tracker.agent_metrics.get(agent_id)
            
            if not metrics:
                raise HTTPException(
                    status_code=404,
                    detail=f"Load metrics not found for agent: {agent_id}"
                )
            
            return {
                'agent_id': metrics.agent_id,
                'agent_name': metrics.agent_name,
                'active_tasks': metrics.active_tasks,
                'completed_tasks': metrics.completed_tasks,
                'failed_tasks': metrics.failed_tasks,
                'avg_task_duration': metrics.avg_task_duration,
                'success_rate': metrics.success_rate,
                'recent_success_rate': metrics.recent_success_rate,
                'cpu_usage': metrics.cpu_usage,
                'memory_usage': metrics.memory_usage,
                'load_score': metrics.load_score,
                'capacity_score': metrics.capacity_score,
                'workload_trend': metrics.workload_trend,
                'predicted_completion_time': metrics.predicted_completion_time,
                'specialization_scores': metrics.specialization_score,
                'last_updated': metrics.last_updated.isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get agent load metrics: {e}")
            raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")
    
    @staticmethod
    async def benchmark_load_balancing_strategies(
        request: LoadBalancingRequest,
        db: AsyncSession = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """
        Benchmark all load balancing strategies for comparison
        
        This endpoint runs all available strategies on the same agent pool
        and returns comparative results for analysis and optimization.
        """
        try:
            logger.info("Running load balancing strategy benchmark")
            
            # Find suitable agents
            suitable_agents = await AgentRepository.find_suitable_agents(
                required_capabilities=request.required_capabilities,
                task_type=request.task_type,
                db=db
            )
            
            if not suitable_agents:
                raise HTTPException(
                    status_code=404,
                    detail=f"No suitable agents found for benchmarking"
                )
            
            # Test all strategies
            strategies = [
                LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
                LoadBalancingStrategy.LEAST_CONNECTION,
                LoadBalancingStrategy.PREDICTIVE_ML,
                LoadBalancingStrategy.RESOURCE_AWARE,
                LoadBalancingStrategy.HYBRID
            ]
            
            benchmark_results = {}
            
            for strategy in strategies:
                try:
                    result = await load_balancer.select_best_agent(
                        available_agents=suitable_agents,
                        task_requirements=request.task_requirements,
                        strategy=strategy,
                        db=db
                    )
                    
                    benchmark_results[strategy.value] = {
                        'selected_agent_id': result.selected_agent.id,
                        'selected_agent_name': result.selected_agent.name,
                        'confidence_score': result.confidence_score,
                        'selection_reason': result.selection_reason,
                        'load_score': result.load_metrics.load_score,
                        'capacity_score': result.load_metrics.capacity_score
                    }
                except Exception as e:
                    benchmark_results[strategy.value] = {
                        'error': str(e)
                    }
            
            return {
                'benchmark_results': benchmark_results,
                'total_agents': len(suitable_agents),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Load balancing benchmark failed: {e}")
            raise HTTPException(status_code=500, detail=f"Benchmark failed: {str(e)}")


# Create endpoints instance
load_balancing_endpoints = LoadBalancingEndpoints()

"""
Advanced Load Balancer for Agent Orchestrator

This module implements sophisticated load balancing strategies for optimal
agent selection and task distribution in the surveillance system.

Features:
- Weighted Round-Robin (performance-based weights)
- Least Connection (fewest active tasks)
- Predictive ML-based selection (fastest agent prediction)
- Resource-aware allocation (CPU/memory usage)
- Hybrid strategies and fallback mechanisms
- Real-time agent performance tracking
- Load balancing metrics and monitoring
"""

import logging
import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json
import random
from sqlalchemy.ext.asyncio import AsyncSession

from models import Agent, Task, AgentTypeEnum, TaskStatusEnum

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Available load balancing strategies"""
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTION = "least_connection"
    PREDICTIVE_ML = "predictive_ml"
    RESOURCE_AWARE = "resource_aware"
    HYBRID = "hybrid"
    RANDOM = "random"  # Fallback strategy


@dataclass
class AgentLoadMetrics:
    """Comprehensive load and performance metrics for an agent"""
    agent_id: str
    agent_name: str
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_task_duration: float = 0.0
    success_rate: float = 1.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    # Performance tracking
    recent_response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_success_rate: float = 1.0
    load_score: float = 0.0
    capacity_score: float = 1.0
    
    # Predictive features
    predicted_completion_time: float = 0.0
    workload_trend: str = "stable"  # increasing, decreasing, stable
    specialization_score: Dict[str, float] = field(default_factory=dict)


@dataclass
class LoadBalancingResult:
    """Result of load balancing algorithm"""
    selected_agent: Agent
    strategy_used: LoadBalancingStrategy
    confidence_score: float
    load_metrics: AgentLoadMetrics
    selection_reason: str
    fallback_used: bool = False
    alternative_agents: List[Agent] = field(default_factory=list)


class AgentLoadTracker:
    """Tracks and manages agent load metrics in real-time"""
    
    def __init__(self):
        self.agent_metrics: Dict[str, AgentLoadMetrics] = {}
        self.task_history: Dict[str, List[Dict]] = defaultdict(list)
        self.prediction_models: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        
    async def update_agent_metrics(self, agent_id: str, agent_name: str, 
                                 metrics_update: Dict[str, Any]):
        """Update agent metrics with new data"""
        async with self._lock:
            if agent_id not in self.agent_metrics:
                self.agent_metrics[agent_id] = AgentLoadMetrics(
                    agent_id=agent_id,
                    agent_name=agent_name
                )
            
            metrics = self.agent_metrics[agent_id]
            
            # Update basic metrics
            if 'active_tasks' in metrics_update:
                metrics.active_tasks = metrics_update['active_tasks']
            if 'completed_tasks' in metrics_update:
                metrics.completed_tasks = metrics_update['completed_tasks']
            if 'failed_tasks' in metrics_update:
                metrics.failed_tasks = metrics_update['failed_tasks']
            if 'cpu_usage' in metrics_update:
                metrics.cpu_usage = metrics_update['cpu_usage']
            if 'memory_usage' in metrics_update:
                metrics.memory_usage = metrics_update['memory_usage']
            
            # Update performance metrics
            if 'task_duration' in metrics_update:
                metrics.recent_response_times.append(metrics_update['task_duration'])
                metrics.avg_task_duration = np.mean(metrics.recent_response_times)
            
            # Calculate success rate
            total_tasks = metrics.completed_tasks + metrics.failed_tasks
            if total_tasks > 0:
                metrics.success_rate = metrics.completed_tasks / total_tasks
                
                # Recent success rate (last 20 tasks)
                recent_count = min(20, total_tasks)
                if recent_count > 0:
                    recent_history = self.task_history[agent_id][-recent_count:]
                    recent_successes = sum(1 for task in recent_history if task.get('success', False))
                    metrics.recent_success_rate = recent_successes / recent_count
            
            # Calculate load and capacity scores
            metrics.load_score = self._calculate_load_score(metrics)
            metrics.capacity_score = self._calculate_capacity_score(metrics)
            
            # Update workload trend
            metrics.workload_trend = self._analyze_workload_trend(agent_id)
            
            metrics.last_updated = datetime.utcnow()
    
    def _calculate_load_score(self, metrics: AgentLoadMetrics) -> float:
        """Calculate overall load score (0-1, higher = more loaded)"""
        # Weighted combination of various load factors
        task_load = min(metrics.active_tasks / 10.0, 1.0)  # Normalize to max 10 tasks
        resource_load = (metrics.cpu_usage + metrics.memory_usage) / 2.0
        response_time_factor = min(metrics.avg_task_duration / 30.0, 1.0)  # Normalize to 30s max
        
        load_score = (task_load * 0.4 + resource_load * 0.4 + response_time_factor * 0.2)
        return min(load_score, 1.0)
    
    def _calculate_capacity_score(self, metrics: AgentLoadMetrics) -> float:
        """Calculate agent capacity score (0-1, higher = more capacity)"""
        # Inverse of load score with success rate factor
        base_capacity = 1.0 - metrics.load_score
        success_factor = metrics.recent_success_rate
        
        return base_capacity * success_factor
    
    def _analyze_workload_trend(self, agent_id: str) -> str:
        """Analyze workload trend for predictive modeling"""
        history = self.task_history[agent_id]
        if len(history) < 5:
            return "stable"
        
        recent_loads = [task.get('load_at_time', 0) for task in history[-10:]]
        if len(recent_loads) < 3:
            return "stable"
        
        # Simple trend analysis
        trend_slope = np.polyfit(range(len(recent_loads)), recent_loads, 1)[0]
        
        if trend_slope > 0.1:
            return "increasing"
        elif trend_slope < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    async def record_task_completion(self, agent_id: str, task_data: Dict[str, Any]):
        """Record task completion for performance tracking"""
        async with self._lock:
            self.task_history[agent_id].append({
                'timestamp': datetime.utcnow(),
                'duration': task_data.get('duration', 0),
                'success': task_data.get('success', False),
                'task_type': task_data.get('task_type', ''),
                'load_at_time': task_data.get('load_at_time', 0)
            })
            
            # Keep only recent history (last 1000 tasks)
            if len(self.task_history[agent_id]) > 1000:
                self.task_history[agent_id] = self.task_history[agent_id][-1000:]


class AdvancedLoadBalancer:
    """Advanced load balancer with multiple strategies"""
    
    def __init__(self):
        self.load_tracker = AgentLoadTracker()
        self.strategy_weights = {
            LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: 0.25,
            LoadBalancingStrategy.LEAST_CONNECTION: 0.25,
            LoadBalancingStrategy.PREDICTIVE_ML: 0.25,
            LoadBalancingStrategy.RESOURCE_AWARE: 0.25
        }
        self.round_robin_state = {}
        self.prediction_cache = {}
        self.cache_ttl = 60  # seconds
        
    async def select_best_agent(
        self,
        available_agents: List[Agent],
        task_requirements: Dict[str, Any],
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.HYBRID,
        db: AsyncSession = None
    ) -> LoadBalancingResult:
        """Select the best agent using specified strategy"""
        
        if not available_agents:
            raise ValueError("No available agents provided")
        
        logger.info(f"Selecting agent using strategy: {strategy} from {len(available_agents)} agents")
        
        try:
            # Update agent metrics if database session is provided
            if db:
                await self._update_agent_metrics_from_db(available_agents, db)
            
            # Apply the selected strategy
            if strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                result = await self._weighted_round_robin(available_agents, task_requirements)
            elif strategy == LoadBalancingStrategy.LEAST_CONNECTION:
                result = await self._least_connection(available_agents, task_requirements)
            elif strategy == LoadBalancingStrategy.PREDICTIVE_ML:
                result = await self._predictive_ml_selection(available_agents, task_requirements)
            elif strategy == LoadBalancingStrategy.RESOURCE_AWARE:
                result = await self._resource_aware_selection(available_agents, task_requirements)
            elif strategy == LoadBalancingStrategy.HYBRID:
                result = await self._hybrid_selection(available_agents, task_requirements)
            else:
                result = await self._random_selection(available_agents, task_requirements)
            
            logger.info(f"Selected agent {result.selected_agent.name} with confidence {result.confidence_score:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"Load balancing failed: {e}")
            # Fallback to random selection
            return await self._random_selection(available_agents, task_requirements, fallback=True)
    
    async def _weighted_round_robin(self, agents: List[Agent], task_req: Dict[str, Any]) -> LoadBalancingResult:
        """Weighted round-robin based on agent performance"""
        agent_weights = {}
        
        for agent in agents:
            metrics = self.load_tracker.agent_metrics.get(agent.id)
            if metrics:
                # Weight based on success rate and capacity
                weight = metrics.success_rate * metrics.capacity_score
                # Boost weight for specialized agents
                specialization = metrics.specialization_score.get(task_req.get('task_type', ''), 1.0)
                weight *= specialization
            else:
                weight = 0.5  # Default weight
            
            agent_weights[agent.id] = max(weight, 0.1)  # Minimum weight
        
        # Initialize round-robin state if needed
        key = frozenset(agent.id for agent in agents)
        if key not in self.round_robin_state:
            self.round_robin_state[key] = {'index': 0, 'weights': {}}
        
        state = self.round_robin_state[key]
        
        # Select agent based on weighted round-robin
        total_weight = sum(agent_weights.values())
        cumulative_weights = []
        running_sum = 0
        
        for agent in agents:
            running_sum += agent_weights[agent.id] / total_weight
            cumulative_weights.append(running_sum)
        
        # Use round-robin position to select
        position = (state['index'] % len(agents)) / len(agents)
        state['index'] += 1
        
        selected_idx = 0
        for i, weight in enumerate(cumulative_weights):
            if position <= weight:
                selected_idx = i
                break
        
        selected_agent = agents[selected_idx]
        metrics = self.load_tracker.agent_metrics.get(selected_agent.id)
        
        return LoadBalancingResult(
            selected_agent=selected_agent,
            strategy_used=LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
            confidence_score=agent_weights[selected_agent.id],
            load_metrics=metrics or AgentLoadMetrics(selected_agent.id, selected_agent.name),
            selection_reason=f"Weighted round-robin selection with weight {agent_weights[selected_agent.id]:.3f}",
            alternative_agents=agents[:3]  # Top 3 alternatives
        )
    
    async def _least_connection(self, agents: List[Agent], task_req: Dict[str, Any]) -> LoadBalancingResult:
        """Select agent with fewest active connections/tasks"""
        best_agent = None
        min_connections = float('inf')
        confidence_scores = {}
        
        for agent in agents:
            metrics = self.load_tracker.agent_metrics.get(agent.id)
            active_tasks = metrics.active_tasks if metrics else 0
            
            # Adjust for agent performance
            success_rate = metrics.recent_success_rate if metrics else 0.5
            adjusted_load = active_tasks / max(success_rate, 0.1)
            
            confidence_scores[agent.id] = 1.0 / (1.0 + adjusted_load)
            
            if adjusted_load < min_connections:
                min_connections = adjusted_load
                best_agent = agent
        
        metrics = self.load_tracker.agent_metrics.get(best_agent.id)
        
        return LoadBalancingResult(
            selected_agent=best_agent,
            strategy_used=LoadBalancingStrategy.LEAST_CONNECTION,
            confidence_score=confidence_scores[best_agent.id],
            load_metrics=metrics or AgentLoadMetrics(best_agent.id, best_agent.name),
            selection_reason=f"Least connection selection with {min_connections:.1f} adjusted load",
            alternative_agents=sorted(agents, key=lambda a: confidence_scores.get(a.id, 0), reverse=True)[:3]
        )
    
    async def _predictive_ml_selection(self, agents: List[Agent], task_req: Dict[str, Any]) -> LoadBalancingResult:
        """Predict fastest agent using ML-based approach"""
        predictions = {}
        
        for agent in agents:
            metrics = self.load_tracker.agent_metrics.get(agent.id)
            if not metrics:
                predictions[agent.id] = random.uniform(10, 30)  # Default prediction
                continue
            
            # Simple predictive model based on historical data
            base_time = metrics.avg_task_duration
            
            # Adjust for current load
            load_factor = 1.0 + (metrics.load_score * 2.0)
            
            # Adjust for workload trend
            trend_factor = 1.0
            if metrics.workload_trend == "increasing":
                trend_factor = 1.2
            elif metrics.workload_trend == "decreasing":
                trend_factor = 0.8
            
            # Adjust for task type specialization
            task_type = task_req.get('task_type', '')
            specialization_factor = metrics.specialization_score.get(task_type, 1.0)
            
            predicted_time = base_time * load_factor * trend_factor / specialization_factor
            predictions[agent.id] = max(predicted_time, 1.0)  # Minimum 1 second
        
        # Select agent with fastest predicted completion
        best_agent = min(agents, key=lambda a: predictions[a.id])
        best_time = predictions[best_agent.id]
        
        # Calculate confidence based on prediction variance
        all_times = list(predictions.values())
        time_variance = np.var(all_times) if len(all_times) > 1 else 1.0
        confidence = 1.0 / (1.0 + time_variance / max(best_time, 1.0))
        
        metrics = self.load_tracker.agent_metrics.get(best_agent.id)
        if metrics:
            metrics.predicted_completion_time = best_time
        
        return LoadBalancingResult(
            selected_agent=best_agent,
            strategy_used=LoadBalancingStrategy.PREDICTIVE_ML,
            confidence_score=confidence,
            load_metrics=metrics or AgentLoadMetrics(best_agent.id, best_agent.name),
            selection_reason=f"Predictive ML selection with {best_time:.1f}s predicted completion",
            alternative_agents=sorted(agents, key=lambda a: predictions[a.id])[:3]
        )
    
    async def _resource_aware_selection(self, agents: List[Agent], task_req: Dict[str, Any]) -> LoadBalancingResult:
        """Select agent based on resource availability"""
        resource_scores = {}
        
        for agent in agents:
            metrics = self.load_tracker.agent_metrics.get(agent.id)
            if not metrics:
                resource_scores[agent.id] = 0.5
                continue
            
            # Calculate resource availability score
            cpu_availability = 1.0 - min(metrics.cpu_usage / 100.0, 1.0)
            memory_availability = 1.0 - min(metrics.memory_usage / 100.0, 1.0)
            
            # Consider task queue length
            queue_factor = 1.0 / (1.0 + metrics.active_tasks)
            
            # Performance factor
            performance_factor = metrics.recent_success_rate
            
            # Combined resource score
            resource_score = (
                cpu_availability * 0.3 +
                memory_availability * 0.3 +
                queue_factor * 0.2 +
                performance_factor * 0.2
            )
            
            resource_scores[agent.id] = resource_score
        
        # Select agent with best resource score
        best_agent = max(agents, key=lambda a: resource_scores[a.id])
        best_score = resource_scores[best_agent.id]
        
        metrics = self.load_tracker.agent_metrics.get(best_agent.id)
        
        return LoadBalancingResult(
            selected_agent=best_agent,
            strategy_used=LoadBalancingStrategy.RESOURCE_AWARE,
            confidence_score=best_score,
            load_metrics=metrics or AgentLoadMetrics(best_agent.id, best_agent.name),
            selection_reason=f"Resource-aware selection with score {best_score:.3f}",
            alternative_agents=sorted(agents, key=lambda a: resource_scores[a.id], reverse=True)[:3]
        )
    
    async def _hybrid_selection(self, agents: List[Agent], task_req: Dict[str, Any]) -> LoadBalancingResult:
        """Hybrid approach combining multiple strategies"""
        # Get results from all strategies
        strategies_results = {}
        
        strategies_results['wrr'] = await self._weighted_round_robin(agents, task_req)
        strategies_results['lc'] = await self._least_connection(agents, task_req)
        strategies_results['ml'] = await self._predictive_ml_selection(agents, task_req)
        strategies_results['ra'] = await self._resource_aware_selection(agents, task_req)
        
        # Score each agent based on all strategies
        agent_scores = defaultdict(float)
        
        for strategy_name, result in strategies_results.items():
            weight = {
                'wrr': 0.25,
                'lc': 0.25,
                'ml': 0.3,   # Slightly favor predictive ML
                'ra': 0.2
            }[strategy_name]
            
            agent_scores[result.selected_agent.id] += result.confidence_score * weight
            
            # Add bonus for being selected by multiple strategies
            for agent in agents:
                if agent.id == result.selected_agent.id:
                    agent_scores[agent.id] += 0.1 * weight
        
        # Select agent with highest combined score
        best_agent = max(agents, key=lambda a: agent_scores[a.id])
        best_score = agent_scores[best_agent.id]
        
        metrics = self.load_tracker.agent_metrics.get(best_agent.id)
        
        # Determine which strategies selected this agent
        selecting_strategies = [
            name for name, result in strategies_results.items()
            if result.selected_agent.id == best_agent.id
        ]
        
        return LoadBalancingResult(
            selected_agent=best_agent,
            strategy_used=LoadBalancingStrategy.HYBRID,
            confidence_score=best_score,
            load_metrics=metrics or AgentLoadMetrics(best_agent.id, best_agent.name),
            selection_reason=f"Hybrid selection (chosen by {len(selecting_strategies)} strategies: {', '.join(selecting_strategies)})",
            alternative_agents=sorted(agents, key=lambda a: agent_scores[a.id], reverse=True)[:3]
        )
    
    async def _random_selection(self, agents: List[Agent], task_req: Dict[str, Any], 
                              fallback: bool = False) -> LoadBalancingResult:
        """Random selection as fallback strategy"""
        selected_agent = random.choice(agents)
        metrics = self.load_tracker.agent_metrics.get(selected_agent.id)
        
        return LoadBalancingResult(
            selected_agent=selected_agent,
            strategy_used=LoadBalancingStrategy.RANDOM,
            confidence_score=1.0 / len(agents),  # Equal probability
            load_metrics=metrics or AgentLoadMetrics(selected_agent.id, selected_agent.name),
            selection_reason="Random selection" + (" (fallback)" if fallback else ""),
            fallback_used=fallback,
            alternative_agents=agents[:3]
        )
    
    async def _update_agent_metrics_from_db(self, agents: List[Agent], db: AsyncSession):
        """Update agent metrics from database information"""
        for agent in agents:
            # Get current task count
            active_tasks = len([t for t in getattr(agent, 'tasks', []) 
                              if getattr(t, 'status', None) in ['running', 'pending']])
            
            # Extract performance metrics
            perf_metrics = agent.performance_metrics or {}
            
            metrics_update = {
                'active_tasks': active_tasks,
                'completed_tasks': perf_metrics.get('completed_tasks', 0),
                'failed_tasks': perf_metrics.get('failed_tasks', 0),
                'cpu_usage': perf_metrics.get('cpu_usage', 0),
                'memory_usage': perf_metrics.get('memory_usage', 0)
            }
            
            await self.load_tracker.update_agent_metrics(
                agent.id, agent.name, metrics_update
            )
    
    async def update_agent_performance(self, agent_id: str, task_data: Dict[str, Any]):
        """Update agent performance after task completion"""
        await self.load_tracker.record_task_completion(agent_id, task_data)
        
        # Update metrics
        metrics_update = {
            'task_duration': task_data.get('duration', 0),
            'active_tasks': task_data.get('new_active_count', 0)
        }
        
        agent_name = task_data.get('agent_name', f'agent_{agent_id}')
        await self.load_tracker.update_agent_metrics(agent_id, agent_name, metrics_update)
    
    def get_load_balancing_stats(self) -> Dict[str, Any]:
        """Get current load balancing statistics"""
        stats = {
            'total_agents': len(self.load_tracker.agent_metrics),
            'agents': {},
            'strategy_weights': self.strategy_weights,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for agent_id, metrics in self.load_tracker.agent_metrics.items():
            stats['agents'][agent_id] = {
                'name': metrics.agent_name,
                'active_tasks': metrics.active_tasks,
                'load_score': metrics.load_score,
                'capacity_score': metrics.capacity_score,
                'success_rate': metrics.success_rate,
                'avg_response_time': metrics.avg_task_duration,
                'workload_trend': metrics.workload_trend,
                'last_updated': metrics.last_updated.isoformat()
            }
        
        return stats
    
    def configure_strategy_weights(self, weights: Dict[LoadBalancingStrategy, float]):
        """Configure weights for hybrid strategy"""
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError("Strategy weights must sum to 1.0")
        
        self.strategy_weights = weights
        logger.info(f"Updated strategy weights: {weights}")


# Global load balancer instance
load_balancer = AdvancedLoadBalancer()

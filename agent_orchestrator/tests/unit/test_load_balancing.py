"""
Comprehensive Tests for Advanced Load Balancing

This module provides extensive test coverage for the advanced load balancing
functionality, including all strategies, performance metrics, and edge cases.

Test Coverage:
- Load balancing strategy implementations
- Agent selection algorithms
- Performance metrics tracking
- Load balancing endpoints
- Error handling and fallback mechanisms
- Integration with database operations
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from advanced_load_balancer import (
    AdvancedLoadBalancer, LoadBalancingStrategy, LoadBalancingResult,
    AgentLoadMetrics, AgentLoadTracker
)
from load_balancing_endpoints import (
    LoadBalancingRequest, LoadBalancingResponse, AgentPerformanceUpdate,
    LoadBalancingEndpoints
)
from models import Agent, AgentTypeEnum


class MockAgent:
    """Mock agent for testing"""
    def __init__(self, agent_id: str, name: str, agent_type: AgentTypeEnum = AgentTypeEnum.PROMPT,
                 capabilities: List[str] = None, performance_metrics: Dict[str, Any] = None):
        self.id = agent_id
        self.name = name
        self.type = agent_type
        self.capabilities = capabilities or []
        self.performance_metrics = performance_metrics or {}
        self.status = "idle"
        self.is_active = True
        self.tasks = []


class TestAgentLoadTracker:
    """Test cases for AgentLoadTracker"""
    
    @pytest.fixture
    def load_tracker(self):
        return AgentLoadTracker()
    
    @pytest.mark.asyncio
    async def test_update_agent_metrics(self, load_tracker):
        """Test updating agent metrics"""
        agent_id = "test-agent-1"
        agent_name = "Test Agent 1"
        
        metrics_update = {
            'active_tasks': 3,
            'completed_tasks': 10,
            'failed_tasks': 1,
            'cpu_usage': 45.0,
            'memory_usage': 60.0,
            'task_duration': 5.5
        }
        
        await load_tracker.update_agent_metrics(agent_id, agent_name, metrics_update)
        
        # Verify metrics were updated
        assert agent_id in load_tracker.agent_metrics
        metrics = load_tracker.agent_metrics[agent_id]
        
        assert metrics.agent_id == agent_id
        assert metrics.agent_name == agent_name
        assert metrics.active_tasks == 3
        assert metrics.completed_tasks == 10
        assert metrics.failed_tasks == 1
        assert metrics.cpu_usage == 45.0
        assert metrics.memory_usage == 60.0
        assert metrics.success_rate == 10 / 11  # 10 completed out of 11 total
        assert len(metrics.recent_response_times) == 1
        assert metrics.recent_response_times[0] == 5.5
    
    @pytest.mark.asyncio
    async def test_record_task_completion(self, load_tracker):
        """Test recording task completion"""
        agent_id = "test-agent-1"
        
        task_data = {
            'duration': 3.2,
            'success': True,
            'task_type': 'prompt_generation',
            'load_at_time': 0.4
        }
        
        await load_tracker.record_task_completion(agent_id, task_data)
        
        # Verify task history was recorded
        assert agent_id in load_tracker.task_history
        history = load_tracker.task_history[agent_id]
        assert len(history) == 1
        assert history[0]['duration'] == 3.2
        assert history[0]['success'] is True
        assert history[0]['task_type'] == 'prompt_generation'
    
    def test_calculate_load_score(self, load_tracker):
        """Test load score calculation"""
        metrics = AgentLoadMetrics(
            agent_id="test-agent",
            agent_name="Test Agent",
            active_tasks=5,
            cpu_usage=70.0,
            memory_usage=80.0,
            avg_task_duration=15.0
        )
        
        load_score = load_tracker._calculate_load_score(metrics)
        
        # Load score should be between 0 and 1
        assert 0 <= load_score <= 1
        # Higher resource usage should result in higher load score
        assert load_score > 0.5  # Should be relatively high due to high resource usage
    
    def test_calculate_capacity_score(self, load_tracker):
        """Test capacity score calculation"""
        metrics = AgentLoadMetrics(
            agent_id="test-agent",
            agent_name="Test Agent",
            load_score=0.3,
            recent_success_rate=0.9
        )
        
        capacity_score = load_tracker._calculate_capacity_score(metrics)
        
        # Capacity score should be between 0 and 1
        assert 0 <= capacity_score <= 1
        # Lower load and high success rate should result in high capacity
        assert capacity_score > 0.6


class TestAdvancedLoadBalancer:
    """Test cases for AdvancedLoadBalancer"""
    
    @pytest.fixture
    def load_balancer(self):
        return AdvancedLoadBalancer()
    
    @pytest.fixture
    def mock_agents(self):
        """Create mock agents for testing"""
        return [
            MockAgent("agent-1", "Agent 1", AgentTypeEnum.PROMPT, ["prompt_generation", "text_analysis"]),
            MockAgent("agent-2", "Agent 2", AgentTypeEnum.RAG, ["document_search", "information_retrieval"]),
            MockAgent("agent-3", "Agent 3", AgentTypeEnum.RULE, ["rule_validation", "compliance_check"]),
            MockAgent("agent-4", "Agent 4", AgentTypeEnum.PROMPT, ["prompt_generation", "creative_writing"])
        ]
    
    @pytest.mark.asyncio
    async def test_weighted_round_robin_strategy(self, load_balancer, mock_agents):
        """Test weighted round-robin strategy"""
        task_requirements = {"task_type": "prompt_generation"}
        
        # Set up some performance metrics
        await load_balancer.load_tracker.update_agent_metrics(
            "agent-1", "Agent 1", {"active_tasks": 1, "completed_tasks": 10, "failed_tasks": 0}
        )
        await load_balancer.load_tracker.update_agent_metrics(
            "agent-4", "Agent 4", {"active_tasks": 3, "completed_tasks": 5, "failed_tasks": 2}
        )
        
        result = await load_balancer._weighted_round_robin(mock_agents, task_requirements)
        
        assert isinstance(result, LoadBalancingResult)
        assert result.strategy_used == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN
        assert result.selected_agent in mock_agents
        assert 0 <= result.confidence_score <= 1
        assert result.selection_reason.startswith("Weighted round-robin")
    
    @pytest.mark.asyncio
    async def test_least_connection_strategy(self, load_balancer, mock_agents):
        """Test least connection strategy"""
        task_requirements = {"task_type": "prompt_generation"}
        
        # Set up different active task counts
        await load_balancer.load_tracker.update_agent_metrics(
            "agent-1", "Agent 1", {"active_tasks": 5}
        )
        await load_balancer.load_tracker.update_agent_metrics(
            "agent-2", "Agent 2", {"active_tasks": 1}  # Should be selected
        )
        await load_balancer.load_tracker.update_agent_metrics(
            "agent-3", "Agent 3", {"active_tasks": 3}
        )
        
        result = await load_balancer._least_connection(mock_agents, task_requirements)
        
        assert isinstance(result, LoadBalancingResult)
        assert result.strategy_used == LoadBalancingStrategy.LEAST_CONNECTION
        assert result.selected_agent.id == "agent-2"  # Should select agent with least connections
        assert result.selection_reason.startswith("Least connection")
    
    @pytest.mark.asyncio
    async def test_predictive_ml_strategy(self, load_balancer, mock_agents):
        """Test predictive ML strategy"""
        task_requirements = {"task_type": "prompt_generation"}
        
        # Set up different performance histories
        await load_balancer.load_tracker.update_agent_metrics(
            "agent-1", "Agent 1", 
            {"avg_task_duration": 2.0, "load_score": 0.2, "recent_success_rate": 0.95}
        )
        await load_balancer.load_tracker.update_agent_metrics(
            "agent-4", "Agent 4", 
            {"avg_task_duration": 8.0, "load_score": 0.7, "recent_success_rate": 0.8}
        )
        
        result = await load_balancer._predictive_ml_selection(mock_agents, task_requirements)
        
        assert isinstance(result, LoadBalancingResult)
        assert result.strategy_used == LoadBalancingStrategy.PREDICTIVE_ML
        assert result.selected_agent in mock_agents
        assert result.selection_reason.startswith("Predictive ML")
        # Agent 1 should likely be selected due to better performance
        assert result.selected_agent.id == "agent-1"
    
    @pytest.mark.asyncio
    async def test_resource_aware_strategy(self, load_balancer, mock_agents):
        """Test resource-aware strategy"""
        task_requirements = {"task_type": "prompt_generation"}
        
        # Set up different resource utilizations
        await load_balancer.load_tracker.update_agent_metrics(
            "agent-1", "Agent 1", 
            {"cpu_usage": 90.0, "memory_usage": 85.0, "active_tasks": 4}
        )
        await load_balancer.load_tracker.update_agent_metrics(
            "agent-2", "Agent 2", 
            {"cpu_usage": 30.0, "memory_usage": 40.0, "active_tasks": 1}  # Should be selected
        )
        
        result = await load_balancer._resource_aware_selection(mock_agents, task_requirements)
        
        assert isinstance(result, LoadBalancingResult)
        assert result.strategy_used == LoadBalancingStrategy.RESOURCE_AWARE
        assert result.selected_agent.id == "agent-2"  # Should select agent with lower resource usage
        assert result.selection_reason.startswith("Resource-aware")
    
    @pytest.mark.asyncio
    async def test_hybrid_strategy(self, load_balancer, mock_agents):
        """Test hybrid strategy"""
        task_requirements = {"task_type": "prompt_generation"}
        
        # Set up diverse agent metrics
        await load_balancer.load_tracker.update_agent_metrics(
            "agent-1", "Agent 1", 
            {"active_tasks": 2, "cpu_usage": 50.0, "avg_task_duration": 3.0, "recent_success_rate": 0.9}
        )
        
        result = await load_balancer._hybrid_selection(mock_agents, task_requirements)
        
        assert isinstance(result, LoadBalancingResult)
        assert result.strategy_used == LoadBalancingStrategy.HYBRID
        assert result.selected_agent in mock_agents
        assert result.selection_reason.startswith("Hybrid selection")
    
    @pytest.mark.asyncio
    async def test_select_best_agent_no_agents(self, load_balancer):
        """Test error handling when no agents are available"""
        with pytest.raises(ValueError, match="No available agents provided"):
            await load_balancer.select_best_agent([], {})
    
    @pytest.mark.asyncio
    async def test_fallback_to_random(self, load_balancer, mock_agents):
        """Test fallback to random selection on error"""
        task_requirements = {"task_type": "prompt_generation"}
        
        # Mock an error in hybrid strategy by patching
        with patch.object(load_balancer, '_hybrid_selection', side_effect=Exception("Test error")):
            result = await load_balancer.select_best_agent(
                mock_agents, task_requirements, LoadBalancingStrategy.HYBRID
            )
            
            assert isinstance(result, LoadBalancingResult)
            assert result.strategy_used == LoadBalancingStrategy.RANDOM
            assert result.fallback_used is True
            assert result.selected_agent in mock_agents
    
    @pytest.mark.asyncio
    async def test_update_agent_performance(self, load_balancer):
        """Test updating agent performance"""
        agent_id = "test-agent"
        task_data = {
            'duration': 4.5,
            'success': True,
            'task_type': 'prompt_generation',
            'agent_name': 'Test Agent',
            'new_active_count': 2
        }
        
        await load_balancer.update_agent_performance(agent_id, task_data)
        
        # Verify metrics were updated
        assert agent_id in load_balancer.load_tracker.agent_metrics
        metrics = load_balancer.load_tracker.agent_metrics[agent_id]
        assert metrics.agent_name == 'Test Agent'
        assert len(metrics.recent_response_times) == 1
        assert metrics.recent_response_times[0] == 4.5
    
    def test_get_load_balancing_stats(self, load_balancer):
        """Test getting load balancing statistics"""
        # Add some metrics
        load_balancer.load_tracker.agent_metrics["agent-1"] = AgentLoadMetrics(
            agent_id="agent-1",
            agent_name="Agent 1",
            active_tasks=2,
            load_score=0.4,
            capacity_score=0.8
        )
        
        stats = load_balancer.get_load_balancing_stats()
        
        assert isinstance(stats, dict)
        assert stats['total_agents'] == 1
        assert 'agent-1' in stats['agents']
        assert stats['agents']['agent-1']['name'] == 'Agent 1'
        assert stats['agents']['agent-1']['active_tasks'] == 2
        assert 'timestamp' in stats
    
    def test_configure_strategy_weights(self, load_balancer):
        """Test configuring strategy weights"""
        new_weights = {
            LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: 0.3,
            LoadBalancingStrategy.LEAST_CONNECTION: 0.2,
            LoadBalancingStrategy.PREDICTIVE_ML: 0.4,
            LoadBalancingStrategy.RESOURCE_AWARE: 0.1
        }
        
        load_balancer.configure_strategy_weights(new_weights)
        
        assert load_balancer.strategy_weights == new_weights
    
    def test_configure_strategy_weights_invalid_sum(self, load_balancer):
        """Test error handling for invalid weight sums"""
        invalid_weights = {
            LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: 0.5,
            LoadBalancingStrategy.LEAST_CONNECTION: 0.3,
            LoadBalancingStrategy.PREDICTIVE_ML: 0.3,
            LoadBalancingStrategy.RESOURCE_AWARE: 0.1
        }  # Sum = 1.2, invalid
        
        with pytest.raises(ValueError, match="Strategy weights must sum to 1.0"):
            load_balancer.configure_strategy_weights(invalid_weights)


class TestLoadBalancingEndpoints:
    """Test cases for LoadBalancingEndpoints"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_select_agent_with_load_balancing_success(self, mock_db):
        """Test successful agent selection endpoint"""
        # Mock the database query
        mock_agent = MockAgent("agent-1", "Agent 1", AgentTypeEnum.PROMPT, ["prompt_generation"])
        
        with patch('load_balancing_endpoints.AgentRepository.find_suitable_agents', 
                  return_value=[mock_agent]), \
             patch('load_balancing_endpoints.load_balancer.select_best_agent') as mock_select:
            
            # Mock load balancer result
            mock_result = LoadBalancingResult(
                selected_agent=mock_agent,
                strategy_used=LoadBalancingStrategy.HYBRID,
                confidence_score=0.85,
                load_metrics=AgentLoadMetrics("agent-1", "Agent 1"),
                selection_reason="Hybrid selection",
                alternative_agents=[mock_agent]
            )
            mock_select.return_value = mock_result
            
            request = LoadBalancingRequest(
                required_capabilities=["prompt_generation"],
                task_type="prompt_task",
                strategy=LoadBalancingStrategy.HYBRID
            )
            
            response = await LoadBalancingEndpoints.select_agent_with_load_balancing(request, mock_db)
            
            assert isinstance(response, LoadBalancingResponse)
            assert response.selected_agent_id == "agent-1"
            assert response.selected_agent_name == "Agent 1"
            assert response.strategy_used == "hybrid"
            assert response.confidence_score == 0.85
    
    @pytest.mark.asyncio
    async def test_select_agent_no_suitable_agents(self, mock_db):
        """Test error handling when no suitable agents are found"""
        with patch('load_balancing_endpoints.AgentRepository.find_suitable_agents', 
                  return_value=[]):
            
            request = LoadBalancingRequest(
                required_capabilities=["nonexistent_capability"],
                task_type="impossible_task"
            )
            
            with pytest.raises(Exception):  # Should raise HTTPException
                await LoadBalancingEndpoints.select_agent_with_load_balancing(request, mock_db)
    
    @pytest.mark.asyncio
    async def test_update_agent_performance_success(self):
        """Test successful agent performance update"""
        update = AgentPerformanceUpdate(
            agent_id="agent-1",
            task_duration=3.5,
            success=True,
            task_type="prompt_generation",
            cpu_usage=45.0,
            memory_usage=60.0
        )
        
        with patch('load_balancing_endpoints.load_balancer.update_agent_performance') as mock_update:
            mock_update.return_value = None  # Successful update
            
            result = await LoadBalancingEndpoints.update_agent_performance(update)
            
            assert result == {"status": "success", "message": "Agent performance updated"}
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_load_balancing_statistics(self):
        """Test getting load balancing statistics"""
        mock_stats = {
            'total_agents': 2,
            'agents': {
                'agent-1': {'name': 'Agent 1', 'active_tasks': 1, 'load_score': 0.3},
                'agent-2': {'name': 'Agent 2', 'active_tasks': 3, 'load_score': 0.7}
            },
            'strategy_weights': {
                LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: 0.25,
                LoadBalancingStrategy.LEAST_CONNECTION: 0.25,
                LoadBalancingStrategy.PREDICTIVE_ML: 0.25,
                LoadBalancingStrategy.RESOURCE_AWARE: 0.25
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        with patch('load_balancing_endpoints.load_balancer.get_load_balancing_stats', 
                  return_value=mock_stats):
            
            result = await LoadBalancingEndpoints.get_load_balancing_statistics()
            
            assert isinstance(result, LoadBalancingStats)
            assert result.total_agents == 2
            assert len(result.agents) == 2
    
    @pytest.mark.asyncio
    async def test_configure_strategy_weights_success(self):
        """Test successful strategy weights configuration"""
        weights = StrategyWeightsUpdate(
            weighted_round_robin=0.3,
            least_connection=0.2,
            predictive_ml=0.4,
            resource_aware=0.1
        )
        
        with patch('load_balancing_endpoints.load_balancer.configure_strategy_weights') as mock_config:
            mock_config.return_value = None  # Successful configuration
            
            result = await LoadBalancingEndpoints.configure_strategy_weights(weights)
            
            assert result == {"status": "success", "message": "Strategy weights updated"}
            mock_config.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_configure_strategy_weights_invalid_sum(self):
        """Test error handling for invalid weight sums"""
        weights = StrategyWeightsUpdate(
            weighted_round_robin=0.5,
            least_connection=0.3,
            predictive_ml=0.3,
            resource_aware=0.1
        )  # Sum = 1.2, invalid
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await LoadBalancingEndpoints.configure_strategy_weights(weights)
    
    @pytest.mark.asyncio
    async def test_get_agent_load_metrics_success(self):
        """Test getting agent load metrics"""
        agent_id = "agent-1"
        mock_metrics = AgentLoadMetrics(
            agent_id=agent_id,
            agent_name="Agent 1",
            active_tasks=2,
            completed_tasks=10,
            success_rate=0.9,
            load_score=0.4,
            capacity_score=0.8
        )
        
        with patch('load_balancing_endpoints.load_balancer.load_tracker.agent_metrics', 
                  {agent_id: mock_metrics}):
            
            result = await LoadBalancingEndpoints.get_agent_load_metrics(agent_id)
            
            assert isinstance(result, dict)
            assert result['agent_id'] == agent_id
            assert result['agent_name'] == "Agent 1"
            assert result['active_tasks'] == 2
            assert result['success_rate'] == 0.9
    
    @pytest.mark.asyncio
    async def test_get_agent_load_metrics_not_found(self):
        """Test error handling when agent metrics not found"""
        with patch('load_balancing_endpoints.load_balancer.load_tracker.agent_metrics', {}):
            
            with pytest.raises(Exception):  # Should raise HTTPException
                await LoadBalancingEndpoints.get_agent_load_metrics("nonexistent-agent")


class TestIntegration:
    """Integration tests for load balancing system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_load_balancing_flow(self):
        """Test complete load balancing flow from request to response"""
        # This would test the complete flow in a real environment
        # with actual database connections and agent interactions
        pass
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_selections(self):
        """Test concurrent agent selection requests"""
        load_balancer = AdvancedLoadBalancer()
        mock_agents = [
            MockAgent(f"agent-{i}", f"Agent {i}") for i in range(5)
        ]
        
        # Simulate concurrent requests
        tasks = []
        for i in range(10):
            task = load_balancer.select_best_agent(
                available_agents=mock_agents,
                task_requirements={"task_type": f"task_{i}"},
                strategy=LoadBalancingStrategy.HYBRID
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify all requests completed successfully
        assert len(results) == 10
        for result in results:
            assert isinstance(result, LoadBalancingResult)
            assert result.selected_agent in mock_agents
    
    @pytest.mark.asyncio
    async def test_performance_metrics_consistency(self):
        """Test consistency of performance metrics across updates"""
        load_balancer = AdvancedLoadBalancer()
        agent_id = "test-agent"
        
        # Simulate multiple performance updates
        for i in range(10):
            task_data = {
                'duration': 2.0 + i * 0.1,
                'success': i % 8 != 0,  # 7/8 success rate
                'task_type': 'test_task',
                'agent_name': 'Test Agent',
                'new_active_count': i % 3
            }
            
            await load_balancer.update_agent_performance(agent_id, task_data)
        
        # Verify metrics are consistent
        metrics = load_balancer.load_tracker.agent_metrics[agent_id]
        assert len(metrics.recent_response_times) == 10
        assert metrics.success_rate > 0  # Should have some success rate


if __name__ == "__main__":
    # Run specific tests
    pytest.main([__file__, "-v"])

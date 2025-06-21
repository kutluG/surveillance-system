"""
Advanced Load Balancing Usage Examples

This script demonstrates how to use the advanced load balancing features
in the Agent Orchestrator service, including API usage, strategy configuration,
and performance monitoring.

Usage Examples:
- Agent selection with different strategies
- Performance metrics tracking
- Strategy configuration and optimization
- Monitoring and analytics integration
- Real-world scenario simulations
"""

import asyncio
import json
import httpx
from datetime import datetime
from typing import Dict, List, Any


class LoadBalancingClient:
    """Client for interacting with the load balancing API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def select_agent(self, capabilities: List[str], task_type: str, 
                          strategy: str = "hybrid") -> Dict[str, Any]:
        """Select an agent using the load balancing API"""
        url = f"{self.base_url}/load-balancing/select-agent"
        payload = {
            "required_capabilities": capabilities,
            "task_type": task_type,
            "strategy": strategy,
            "task_requirements": {
                "priority": "high",
                "complexity": "medium"
            }
        }
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    async def update_performance(self, agent_id: str, duration: float, 
                               success: bool, task_type: str) -> Dict[str, Any]:
        """Update agent performance metrics"""
        url = f"{self.base_url}/load-balancing/update-performance"
        payload = {
            "agent_id": agent_id,
            "task_duration": duration,
            "success": success,
            "task_type": task_type,
            "cpu_usage": 45.0,
            "memory_usage": 60.0
        }
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get load balancing statistics"""
        url = f"{self.base_url}/load-balancing/statistics"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
    
    async def configure_weights(self, weights: Dict[str, float]) -> Dict[str, Any]:
        """Configure strategy weights"""
        url = f"{self.base_url}/load-balancing/configure-weights"
        response = await self.client.post(url, json=weights)
        response.raise_for_status()
        return response.json()
    
    async def benchmark_strategies(self, capabilities: List[str], 
                                 task_type: str) -> Dict[str, Any]:
        """Benchmark all load balancing strategies"""
        url = f"{self.base_url}/load-balancing/benchmark"
        payload = {
            "required_capabilities": capabilities,
            "task_type": task_type,
            "task_requirements": {
                "priority": "high",
                "complexity": "medium"
            }
        }
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    async def get_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Get metrics for a specific agent"""
        url = f"{self.base_url}/load-balancing/agent/{agent_id}/metrics"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


async def example_basic_agent_selection():
    """Example 1: Basic agent selection with different strategies"""
    print("="*50)
    print("Example 1: Basic Agent Selection")
    print("="*50)
    
    client = LoadBalancingClient()
    
    # Test different strategies
    strategies = ["weighted_round_robin", "least_connection", "predictive_ml", 
                 "resource_aware", "hybrid"]
    
    for strategy in strategies:
        try:
            result = await client.select_agent(
                capabilities=["prompt_generation", "text_analysis"],
                task_type="prompt_task",
                strategy=strategy
            )
            
            print(f"\nStrategy: {strategy}")
            print(f"Selected Agent: {result['selected_agent_name']}")
            print(f"Confidence: {result['confidence_score']:.3f}")
            print(f"Reason: {result['selection_reason']}")
            
        except Exception as e:
            print(f"Error with strategy {strategy}: {e}")
    
    await client.close()


async def example_performance_tracking():
    """Example 2: Performance tracking and metrics update"""
    print("\n" + "="*50)
    print("Example 2: Performance Tracking")
    print("="*50)
    
    client = LoadBalancingClient()
    
    try:
        # Select an agent
        result = await client.select_agent(
            capabilities=["document_search"],
            task_type="search_task",
            strategy="hybrid"
        )
        
        agent_id = result['selected_agent_id']
        print(f"Selected Agent: {result['selected_agent_name']}")
        
        # Simulate task completion and update performance
        print("\nSimulating task completion...")
        
        # Successful task
        update_result = await client.update_performance(
            agent_id=agent_id,
            duration=3.5,
            success=True,
            task_type="search_task"
        )
        print(f"Performance Update: {update_result['message']}")
        
        # Get updated agent metrics
        metrics = await client.get_agent_metrics(agent_id)
        print(f"\nUpdated Agent Metrics:")
        print(f"  Active Tasks: {metrics['active_tasks']}")
        print(f"  Success Rate: {metrics['success_rate']:.3f}")
        print(f"  Load Score: {metrics['load_score']:.3f}")
        print(f"  Capacity Score: {metrics['capacity_score']:.3f}")
        
    except Exception as e:
        print(f"Error in performance tracking: {e}")
    
    await client.close()


async def example_strategy_configuration():
    """Example 3: Strategy configuration and optimization"""
    print("\n" + "="*50)
    print("Example 3: Strategy Configuration")
    print("="*50)
    
    client = LoadBalancingClient()
    
    try:
        # Get current statistics
        stats = await client.get_statistics()
        print(f"Current Strategy Weights:")
        for strategy, weight in stats.get('strategy_weights', {}).items():
            print(f"  {strategy}: {weight}")
        
        # Configure new weights (performance-focused)
        new_weights = {
            "weighted_round_robin": 0.1,
            "least_connection": 0.2,
            "predictive_ml": 0.5,  # Emphasize performance prediction
            "resource_aware": 0.2
        }
        
        print(f"\nConfiguring new weights...")
        config_result = await client.configure_weights(new_weights)
        print(f"Configuration: {config_result['message']}")
        
        # Test with new configuration
        result = await client.select_agent(
            capabilities=["rule_validation"],
            task_type="rule_task",
            strategy="hybrid"
        )
        
        print(f"\nAgent selection with new weights:")
        print(f"Selected: {result['selected_agent_name']}")
        print(f"Confidence: {result['confidence_score']:.3f}")
        
    except Exception as e:
        print(f"Error in strategy configuration: {e}")
    
    await client.close()


async def example_strategy_benchmarking():
    """Example 4: Strategy benchmarking and comparison"""
    print("\n" + "="*50)
    print("Example 4: Strategy Benchmarking")
    print("="*50)
    
    client = LoadBalancingClient()
    
    try:
        # Benchmark all strategies
        benchmark_result = await client.benchmark_strategies(
            capabilities=["prompt_generation", "text_analysis"],
            task_type="prompt_task"
        )
        
        print("Strategy Benchmark Results:")
        print("-" * 30)
        
        for strategy, result in benchmark_result['benchmark_results'].items():
            if 'error' in result:
                print(f"{strategy}: ERROR - {result['error']}")
            else:
                print(f"{strategy}:")
                print(f"  Selected: {result['selected_agent_name']}")
                print(f"  Confidence: {result['confidence_score']:.3f}")
                print(f"  Load Score: {result['load_score']:.3f}")
                print(f"  Capacity Score: {result['capacity_score']:.3f}")
                print()
        
        print(f"Total Agents Available: {benchmark_result['total_agents']}")
        
    except Exception as e:
        print(f"Error in benchmarking: {e}")
    
    await client.close()


async def example_monitoring_analytics():
    """Example 5: Monitoring and analytics"""
    print("\n" + "="*50)
    print("Example 5: Monitoring and Analytics")
    print("="*50)
    
    client = LoadBalancingClient()
    
    try:
        # Get comprehensive statistics
        stats = await client.get_statistics()
        
        print(f"Load Balancing System Statistics:")
        print(f"  Total Agents: {stats['total_agents']}")
        print(f"  Timestamp: {stats['timestamp']}")
        
        print(f"\nAgent Details:")
        for agent_id, agent_data in stats['agents'].items():
            print(f"  {agent_data['name']}:")
            print(f"    Active Tasks: {agent_data['active_tasks']}")
            print(f"    Load Score: {agent_data['load_score']:.3f}")
            print(f"    Success Rate: {agent_data['success_rate']:.3f}")
            print(f"    Workload Trend: {agent_data['workload_trend']}")
            print()
        
        # Get health status
        health_url = f"{client.base_url}/load-balancing/health"
        response = await client.client.get(health_url)
        health = response.json()
        
        print(f"System Health: {health['status']}")
        print(f"Active Agents: {health['active_agents']}")
        print(f"Average Load: {health['average_load']:.3f}")
        
    except Exception as e:
        print(f"Error in monitoring: {e}")
    
    await client.close()


async def example_real_world_scenario():
    """Example 6: Real-world scenario simulation"""
    print("\n" + "="*50)
    print("Example 6: Real-World Scenario Simulation")
    print("="*50)
    
    client = LoadBalancingClient()
    
    try:
        # Simulate a surveillance workflow
        tasks = [
            {
                "name": "Motion Detection",
                "capabilities": ["motion_detection", "video_analysis"],
                "task_type": "detection_task"
            },
            {
                "name": "Object Classification", 
                "capabilities": ["object_classification", "image_analysis"],
                "task_type": "classification_task"
            },
            {
                "name": "Alert Generation",
                "capabilities": ["alert_generation", "notification"],
                "task_type": "alert_task"
            },
            {
                "name": "Report Generation",
                "capabilities": ["report_generation", "data_analysis"],
                "task_type": "report_task"
            }
        ]
        
        print("Simulating surveillance workflow tasks...")
        
        for i, task in enumerate(tasks, 1):
            print(f"\nTask {i}: {task['name']}")
            
            # Select agent for this task
            result = await client.select_agent(
                capabilities=task['capabilities'],
                task_type=task['task_type'],
                strategy="hybrid"
            )
            
            agent_id = result['selected_agent_id']
            print(f"  Assigned to: {result['selected_agent_name']}")
            print(f"  Confidence: {result['confidence_score']:.3f}")
            
            # Simulate task execution time
            import random
            execution_time = random.uniform(2.0, 8.0)
            success = random.random() > 0.1  # 90% success rate
            
            print(f"  Execution time: {execution_time:.1f}s")
            print(f"  Status: {'Success' if success else 'Failed'}")
            
            # Update performance
            await client.update_performance(
                agent_id=agent_id,
                duration=execution_time,
                success=success,
                task_type=task['task_type']
            )
        
        # Get final statistics
        print("\nFinal System Statistics:")
        stats = await client.get_statistics()
        print(f"  Total Agents: {stats['total_agents']}")
        
        # Show agent utilization
        total_active_tasks = sum(
            agent['active_tasks'] for agent in stats['agents'].values()
        )
        print(f"  Total Active Tasks: {total_active_tasks}")
        
        avg_load = sum(
            agent['load_score'] for agent in stats['agents'].values()
        ) / len(stats['agents'])
        print(f"  Average Agent Load: {avg_load:.3f}")
        
    except Exception as e:
        print(f"Error in real-world scenario: {e}")
    
    await client.close()


async def main():
    """Run all usage examples"""
    print("Advanced Load Balancing Usage Examples")
    print("=====================================")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("\nNOTE: These examples require the Agent Orchestrator service to be running")
    print("Start the service with: uvicorn main:app --reload")
    print("\nRunning examples...")
    
    try:
        await example_basic_agent_selection()
        await example_performance_tracking()
        await example_strategy_configuration()
        await example_strategy_benchmarking()
        await example_monitoring_analytics()
        await example_real_world_scenario()
        
        print("\n" + "="*50)
        print("All examples completed successfully!")
        print("="*50)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Make sure the Agent Orchestrator service is running on localhost:8000")


if __name__ == "__main__":
    asyncio.run(main())

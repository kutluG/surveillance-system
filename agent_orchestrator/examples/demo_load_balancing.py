"""
Advanced Load Balancing Demo

This script demonstrates the advanced load balancing capabilities of the
agent orchestrator, showcasing different strategies and their effectiveness
in various scenarios.

Features Demonstrated:
- All load balancing strategies (weighted round-robin, least connection, predictive ML, resource-aware, hybrid)
- Performance metrics tracking and updates
- Real-time load balancing decisions
- Strategy comparison and benchmarking
- Load balancing analytics and monitoring
"""

import asyncio
import random
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import load balancing components
from advanced_load_balancer import (
    AdvancedLoadBalancer, LoadBalancingStrategy, AgentLoadMetrics
)
from models import Agent, AgentTypeEnum


class MockAgent:
    """Mock agent for demonstration purposes"""
    def __init__(self, agent_id: str, name: str, agent_type: AgentTypeEnum = AgentTypeEnum.PROMPT,
                 capabilities: List[str] = None, base_performance: float = 1.0):
        self.id = agent_id
        self.name = name
        self.type = agent_type
        self.capabilities = capabilities or []
        self.performance_metrics = {}
        self.status = "idle"
        self.is_active = True
        self.tasks = []
        self.base_performance = base_performance  # For simulation


class LoadBalancingDemo:
    """Demonstration of advanced load balancing capabilities"""
    
    def __init__(self):
        self.load_balancer = AdvancedLoadBalancer()
        self.agents = self._create_demo_agents()
        self.simulation_data = []
        
    def _create_demo_agents(self) -> List[MockAgent]:
        """Create a diverse set of demo agents"""
        agents = [
            MockAgent("agent-prompt-1", "Prompt Generator Alpha", AgentTypeEnum.PROMPT, 
                     ["prompt_generation", "text_analysis", "creative_writing"], 0.9),
            MockAgent("agent-prompt-2", "Prompt Generator Beta", AgentTypeEnum.PROMPT, 
                     ["prompt_generation", "text_analysis"], 0.7),
            MockAgent("agent-rag-1", "RAG Search Master", AgentTypeEnum.RAG, 
                     ["document_search", "information_retrieval", "knowledge_extraction"], 0.95),
            MockAgent("agent-rag-2", "RAG Query Engine", AgentTypeEnum.RAG, 
                     ["document_search", "information_retrieval"], 0.8),
            MockAgent("agent-rule-1", "Rule Validator Pro", AgentTypeEnum.RULE, 
                     ["rule_validation", "compliance_check", "policy_enforcement"], 0.85),
            MockAgent("agent-rule-2", "Rule Checker Lite", AgentTypeEnum.RULE, 
                     ["rule_validation", "compliance_check"], 0.6),
            MockAgent("agent-multi-1", "Multi-Purpose Agent", AgentTypeEnum.PROMPT, 
                     ["prompt_generation", "document_search", "rule_validation"], 0.75),
            MockAgent("agent-specialist", "Specialized Expert", AgentTypeEnum.PROMPT, 
                     ["advanced_reasoning", "complex_analysis"], 1.0)
        ]
        return agents
    
    async def initialize_agent_metrics(self):
        """Initialize agent metrics with realistic data"""
        logger.info("Initializing agent metrics...")
        
        for i, agent in enumerate(self.agents):
            # Simulate different load levels
            active_tasks = random.randint(0, 8)
            completed_tasks = random.randint(10, 100)
            failed_tasks = random.randint(0, max(1, completed_tasks // 10))
            
            # Simulate resource usage based on agent performance
            cpu_usage = (1.0 - agent.base_performance) * 60 + random.uniform(10, 30)
            memory_usage = (1.0 - agent.base_performance) * 70 + random.uniform(15, 40)
            
            metrics_update = {
                'active_tasks': active_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'cpu_usage': min(cpu_usage, 95),
                'memory_usage': min(memory_usage, 95),
                'task_duration': (2.0 - agent.base_performance) * 3 + random.uniform(1, 3)
            }
            
            await self.load_balancer.load_tracker.update_agent_metrics(
                agent.id, agent.name, metrics_update
            )
            
            # Add some task history
            for _ in range(random.randint(5, 15)):
                task_data = {
                    'duration': random.uniform(1, 10) * (2.0 - agent.base_performance),
                    'success': random.random() < agent.base_performance,
                    'task_type': random.choice(agent.capabilities) if agent.capabilities else 'general',
                    'load_at_time': random.uniform(0, 1)
                }
                await self.load_balancer.load_tracker.record_task_completion(agent.id, task_data)
        
        logger.info(f"Initialized metrics for {len(self.agents)} agents")
    
    async def demonstrate_strategy(self, strategy: LoadBalancingStrategy, 
                                 task_requirements: Dict[str, Any], 
                                 num_requests: int = 5) -> List[Dict[str, Any]]:
        """Demonstrate a specific load balancing strategy"""
        logger.info(f"\n=== Demonstrating {strategy.value.upper()} Strategy ===")
        
        results = []
        
        for i in range(num_requests):
            try:
                result = await self.load_balancer.select_best_agent(
                    available_agents=self.agents,
                    task_requirements=task_requirements,
                    strategy=strategy
                )
                
                selection_data = {
                    'request_id': i + 1,
                    'strategy': strategy.value,
                    'selected_agent': result.selected_agent.name,
                    'agent_id': result.selected_agent.id,
                    'confidence_score': result.confidence_score,
                    'selection_reason': result.selection_reason,
                    'load_metrics': {
                        'active_tasks': result.load_metrics.active_tasks,
                        'load_score': result.load_metrics.load_score,
                        'capacity_score': result.load_metrics.capacity_score,
                        'success_rate': result.load_metrics.success_rate
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                results.append(selection_data)
                
                logger.info(f"Request {i+1}: Selected {result.selected_agent.name} "
                           f"(confidence: {result.confidence_score:.3f})")
                logger.info(f"  Reason: {result.selection_reason}")
                
                # Simulate task completion and update metrics
                await self._simulate_task_completion(result.selected_agent.id)
                
                # Small delay between requests
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Request {i+1} failed: {e}")
                results.append({
                    'request_id': i + 1,
                    'strategy': strategy.value,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        return results
    
    async def _simulate_task_completion(self, agent_id: str):
        """Simulate task completion and update agent metrics"""
        # Get agent base performance
        agent = next((a for a in self.agents if a.id == agent_id), None)
        if not agent:
            return
        
        # Simulate task execution
        task_duration = random.uniform(1, 5) * (2.0 - agent.base_performance)
        success = random.random() < agent.base_performance
        
        # Update performance metrics
        task_data = {
            'duration': task_duration,
            'success': success,
            'task_type': random.choice(agent.capabilities) if agent.capabilities else 'general',
            'agent_name': agent.name,
            'new_active_count': max(0, random.randint(-1, 2))  # Simulate changing task count
        }
        
        await self.load_balancer.update_agent_performance(agent_id, task_data)
    
    async def compare_all_strategies(self, task_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Compare all load balancing strategies"""
        logger.info("\n" + "="*60)
        logger.info("COMPREHENSIVE STRATEGY COMPARISON")
        logger.info("="*60)
        
        strategies = [
            LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
            LoadBalancingStrategy.LEAST_CONNECTION,
            LoadBalancingStrategy.PREDICTIVE_ML,
            LoadBalancingStrategy.RESOURCE_AWARE,
            LoadBalancingStrategy.HYBRID
        ]
        
        comparison_results = {}
        
        for strategy in strategies:
            results = await self.demonstrate_strategy(strategy, task_requirements, 3)
            comparison_results[strategy.value] = results
            
            # Calculate strategy statistics
            successful_selections = [r for r in results if 'error' not in r]
            if successful_selections:
                avg_confidence = sum(r['confidence_score'] for r in successful_selections) / len(successful_selections)
                selected_agents = [r['selected_agent'] for r in successful_selections]
                agent_distribution = {agent: selected_agents.count(agent) for agent in set(selected_agents)}
                
                logger.info(f"\n{strategy.value.upper()} Results:")
                logger.info(f"  Average Confidence: {avg_confidence:.3f}")
                logger.info(f"  Agent Distribution: {agent_distribution}")
        
        return comparison_results
    
    async def demonstrate_load_balancing_analytics(self):
        """Demonstrate load balancing analytics and monitoring"""
        logger.info("\n" + "="*50)
        logger.info("LOAD BALANCING ANALYTICS")
        logger.info("="*50)
        
        # Get current statistics
        stats = self.load_balancer.get_load_balancing_stats()
        
        logger.info(f"Total Agents: {stats['total_agents']}")
        logger.info(f"Strategy Weights: {stats['strategy_weights']}")
        
        logger.info("\nAgent Performance Metrics:")
        for agent_id, metrics in stats['agents'].items():
            logger.info(f"  {metrics['name']}:")
            logger.info(f"    Active Tasks: {metrics['active_tasks']}")
            logger.info(f"    Load Score: {metrics['load_score']:.3f}")
            logger.info(f"    Capacity Score: {metrics['capacity_score']:.3f}")
            logger.info(f"    Success Rate: {metrics['success_rate']:.3f}")
            logger.info(f"    Workload Trend: {metrics['workload_trend']}")
        
        return stats
    
    async def demonstrate_dynamic_weight_adjustment(self):
        """Demonstrate dynamic strategy weight adjustment"""
        logger.info("\n" + "="*50)
        logger.info("DYNAMIC WEIGHT ADJUSTMENT")
        logger.info("="*50)
        
        # Test different weight configurations
        weight_configs = [
            {  # Performance-focused
                LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: 0.1,
                LoadBalancingStrategy.LEAST_CONNECTION: 0.2,
                LoadBalancingStrategy.PREDICTIVE_ML: 0.5,
                LoadBalancingStrategy.RESOURCE_AWARE: 0.2
            },
            {  # Load balancing focused
                LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: 0.3,
                LoadBalancingStrategy.LEAST_CONNECTION: 0.4,
                LoadBalancingStrategy.PREDICTIVE_ML: 0.1,
                LoadBalancingStrategy.RESOURCE_AWARE: 0.2
            },
            {  # Resource-focused
                LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: 0.2,
                LoadBalancingStrategy.LEAST_CONNECTION: 0.2,
                LoadBalancingStrategy.PREDICTIVE_ML: 0.2,
                LoadBalancingStrategy.RESOURCE_AWARE: 0.4
            }
        ]
        
        config_names = ["Performance-Focused", "Load-Balancing-Focused", "Resource-Focused"]
        task_requirements = {"task_type": "prompt_generation"}
        
        for i, (config, name) in enumerate(zip(weight_configs, config_names)):
            logger.info(f"\n--- Testing {name} Configuration ---")
            logger.info(f"Weights: {config}")
            
            # Apply new weights
            self.load_balancer.configure_strategy_weights(config)
            
            # Test with hybrid strategy
            result = await self.load_balancer.select_best_agent(
                available_agents=self.agents,
                task_requirements=task_requirements,
                strategy=LoadBalancingStrategy.HYBRID
            )
            
            logger.info(f"Selected: {result.selected_agent.name}")
            logger.info(f"Confidence: {result.confidence_score:.3f}")
            logger.info(f"Reason: {result.selection_reason}")
    
    async def simulate_high_load_scenario(self, duration_seconds: int = 30):
        """Simulate high load scenario with concurrent requests"""
        logger.info("\n" + "="*50)
        logger.info(f"HIGH LOAD SIMULATION ({duration_seconds}s)")
        logger.info("="*50)
        
        start_time = time.time()
        request_count = 0
        results = []
        
        async def make_request():
            nonlocal request_count
            request_count += 1
            
            task_requirements = {
                "task_type": random.choice(["prompt_generation", "document_search", "rule_validation"]),
                "priority": random.choice(["low", "medium", "high"]),
                "complexity": random.choice(["simple", "medium", "complex"])
            }
            
            try:
                result = await self.load_balancer.select_best_agent(
                    available_agents=self.agents,
                    task_requirements=task_requirements,
                    strategy=LoadBalancingStrategy.HYBRID
                )
                
                # Simulate task completion
                await self._simulate_task_completion(result.selected_agent.id)
                
                return {
                    'success': True,
                    'agent': result.selected_agent.name,
                    'confidence': result.confidence_score,
                    'duration': time.time() - start_time
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'duration': time.time() - start_time
                }
        
        # Generate concurrent requests
        while time.time() - start_time < duration_seconds:
            # Create batch of concurrent requests
            batch_size = random.randint(1, 5)
            batch_tasks = [make_request() for _ in range(batch_size)]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
            
            # Brief pause between batches
            await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Analyze results
        successful_requests = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_requests = [r for r in results if isinstance(r, dict) and not r.get('success')]
        
        logger.info(f"\nHigh Load Simulation Results:")
        logger.info(f"  Total Requests: {len(results)}")
        logger.info(f"  Successful: {len(successful_requests)}")
        logger.info(f"  Failed: {len(failed_requests)}")
        logger.info(f"  Success Rate: {len(successful_requests)/len(results)*100:.1f}%")
        
        if successful_requests:
            avg_confidence = sum(r['confidence'] for r in successful_requests) / len(successful_requests)
            logger.info(f"  Average Confidence: {avg_confidence:.3f}")
            
            # Agent distribution
            agent_counts = {}
            for r in successful_requests:
                agent = r['agent']
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
            
            logger.info(f"  Agent Distribution:")
            for agent, count in sorted(agent_counts.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"    {agent}: {count} tasks ({count/len(successful_requests)*100:.1f}%)")
        
        return results
    
    async def run_comprehensive_demo(self):
        """Run comprehensive demonstration of all load balancing features"""
        logger.info("="*70)
        logger.info("ADVANCED LOAD BALANCING COMPREHENSIVE DEMONSTRATION")
        logger.info("="*70)
        
        # Initialize
        await self.initialize_agent_metrics()
        
        # Demonstrate individual strategies
        task_requirements = {
            "task_type": "prompt_generation",
            "priority": "high",
            "complexity": "medium"
        }
        
        # Compare all strategies
        comparison_results = await self.compare_all_strategies(task_requirements)
        
        # Show analytics
        await self.demonstrate_load_balancing_analytics()
        
        # Demonstrate dynamic weight adjustment
        await self.demonstrate_dynamic_weight_adjustment()
        
        # High load simulation
        await self.simulate_high_load_scenario(10)  # 10 second simulation
        
        # Final analytics
        logger.info("\n" + "="*50)
        logger.info("FINAL SYSTEM STATE")
        logger.info("="*50)
        final_stats = await self.demonstrate_load_balancing_analytics()
        
        logger.info("\n" + "="*70)
        logger.info("DEMONSTRATION COMPLETED SUCCESSFULLY")
        logger.info("="*70)
        
        return {
            'comparison_results': comparison_results,
            'final_stats': final_stats,
            'demo_completed': True,
            'timestamp': datetime.utcnow().isoformat()
        }


async def main():
    """Main demonstration function"""
    try:
        demo = LoadBalancingDemo()
        results = await demo.run_comprehensive_demo()
        
        # Save results to file
        with open('load_balancing_demo_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info("\nDemo results saved to 'load_balancing_demo_results.json'")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

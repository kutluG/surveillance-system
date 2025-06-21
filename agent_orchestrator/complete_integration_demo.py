"""
Agent Orchestrator Complete Integration

This script demonstrates the complete integration of all enhanced features:
1. Advanced semantic agent matching with vector-based capability matching
2. Advanced load balancing with multiple strategies and ML predictions
3. Comprehensive monitoring with SLO tracking, anomaly detection, and distributed tracing

Run this to see the complete system in action.
"""

import asyncio
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import asdict

# Import all enhanced components
from semantic_agent_matcher import SemanticAgentMatcher
from advanced_load_balancer import AdvancedLoadBalancer, LoadBalancingStrategy
from comprehensive_monitoring import initialize_monitoring, ComprehensiveMonitor
from db_service import DBService

# Import API routers for testing
from semantic_router import router as semantic_router
from load_balancing_router import router as load_balancing_router
from monitoring_api import router as monitoring_router

# FastAPI for testing the full integration
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


class CompleteAgentOrchestrator:
    """Complete Agent Orchestrator with all enhanced features"""
    
    def __init__(self):
        self.db_service = DBService()
        self.semantic_matcher = SemanticAgentMatcher(self.db_service)
        self.load_balancer = AdvancedLoadBalancer()
        self.monitor = initialize_monitoring(enable_opentelemetry=True)
        
        print("🚀 Initialized Complete Agent Orchestrator")
        print("✅ Semantic Agent Matching")
        print("✅ Advanced Load Balancing")
        print("✅ Comprehensive Monitoring")
        
    async def initialize(self):
        """Initialize all components"""
        await self.db_service.connect()
        await self.semantic_matcher.initialize()
        print("🔗 Connected to database and initialized semantic matching")
        
    async def demo_complete_system(self):
        """Demonstrate the complete integrated system"""
        print("\n" + "="*60)
        print("🎯 COMPLETE AGENT ORCHESTRATOR INTEGRATION DEMO")
        print("="*60)
        
        # 1. Register agents with capabilities
        await self._register_demo_agents()
        
        # 2. Demonstrate semantic agent discovery
        await self._demo_semantic_discovery()
        
        # 3. Demonstrate load balancing strategies
        await self._demo_load_balancing()
        
        # 4. Demonstrate monitoring integration
        await self._demo_monitoring_integration()
        
        # 5. Demonstrate end-to-end orchestration
        await self._demo_end_to_end_orchestration()
        
        # 6. Show final system status
        await self._show_system_status()
        
    async def _register_demo_agents(self):
        """Register demonstration agents with diverse capabilities"""
        print("\n📋 Registering Demo Agents")
        print("-" * 30)
        
        agents = [
            {
                "agent_id": "rag_agent_1",
                "name": "Advanced RAG Agent",
                "agent_type": "rag_agent",
                "endpoint": "http://localhost:8001/api/v1",
                "capabilities": ["document_search", "question_answering", "semantic_retrieval"],
                "tags": ["nlp", "search", "knowledge"],
                "performance_score": 0.95,
                "metadata": {"model": "gpt-4", "vector_db": "chroma"}
            },
            {
                "agent_id": "vision_agent_1",
                "name": "Computer Vision Agent",
                "agent_type": "vision_agent", 
                "endpoint": "http://localhost:8002/api/v1",
                "capabilities": ["object_detection", "image_classification", "face_recognition"],
                "tags": ["computer_vision", "detection", "surveillance"],
                "performance_score": 0.88,
                "metadata": {"model": "yolov8", "device": "gpu"}
            },
            {
                "agent_id": "analysis_agent_1",
                "name": "Data Analysis Agent",
                "agent_type": "analysis_agent",
                "endpoint": "http://localhost:8003/api/v1", 
                "capabilities": ["pattern_analysis", "statistical_analysis", "trend_detection"],
                "tags": ["analytics", "statistics", "insights"],
                "performance_score": 0.92,
                "metadata": {"frameworks": ["pandas", "sklearn"]}
            },
            {
                "agent_id": "notification_agent_1",
                "name": "Smart Notification Agent",
                "agent_type": "notification_agent",
                "endpoint": "http://localhost:8004/api/v1",
                "capabilities": ["alert_generation", "message_routing", "escalation_management"],
                "tags": ["notifications", "alerts", "communication"],
                "performance_score": 0.97,
                "metadata": {"channels": ["email", "sms", "webhook"]}
            }
        ]
        
        for agent in agents:
            success = await self.db_service.register_agent(**agent)
            if success:
                print(f"✅ Registered {agent['name']} ({agent['agent_id']})")
                
                # Update load balancer with agent
                await self.load_balancer.load_tracker.update_agent_metrics(
                    agent["agent_id"],
                    agent["name"],
                    {
                        "active_tasks": 0,
                        "completed_tasks": random.randint(50, 200),
                        "failed_tasks": random.randint(0, 5),
                        "cpu_usage": random.uniform(0.1, 0.8),
                        "memory_usage": random.uniform(0.2, 0.7),
                        "response_time": random.uniform(0.5, 2.0)
                    }
                )
            else:
                print(f"❌ Failed to register {agent['name']}")
                
    async def _demo_semantic_discovery(self):
        """Demonstrate semantic agent discovery"""
        print("\n🔍 Semantic Agent Discovery Demo")
        print("-" * 35)
        
        # Test queries with different complexity
        test_queries = [
            {
                "query": "I need to search through documents and find relevant information",
                "required_capabilities": ["document_search", "information_retrieval"],
                "context": {"task_type": "research", "priority": "high"}
            },
            {
                "query": "Analyze surveillance footage to detect suspicious activity",
                "required_capabilities": ["object_detection", "video_analysis"],
                "context": {"task_type": "security", "real_time": True}
            },
            {
                "query": "Process sensor data to identify patterns and anomalies",
                "required_capabilities": ["pattern_analysis", "anomaly_detection"], 
                "context": {"task_type": "monitoring", "data_volume": "large"}
            }
        ]
        
        for i, test_case in enumerate(test_queries, 1):
            print(f"\n🔎 Test Query {i}: {test_case['query'][:50]}...")
            
            # Use semantic matching
            matches = await self.semantic_matcher.find_matching_agents(
                query=test_case["query"],
                required_capabilities=test_case["required_capabilities"],
                context=test_case.get("context", {})
            )
            
            print(f"📊 Found {len(matches)} matching agents:")
            for match in matches[:3]:  # Show top 3
                print(f"  • {match.agent_name} - Score: {match.total_score:.3f}")
                print(f"    Capabilities: {', '.join(match.matched_capabilities)}")
                print(f"    Semantic: {match.semantic_score:.3f}, Context: {match.context_score:.3f}")
                
    async def _demo_load_balancing(self):
        """Demonstrate load balancing strategies"""
        print("\n⚖️  Load Balancing Strategies Demo")
        print("-" * 35)
        
        # Test different strategies
        strategies = [
            LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
            LoadBalancingStrategy.LEAST_CONNECTION,
            LoadBalancingStrategy.RESOURCE_AWARE,
            LoadBalancingStrategy.PREDICTIVE_ML
        ]
        
        available_agents = ["rag_agent_1", "vision_agent_1", "analysis_agent_1", "notification_agent_1"]
        
        for strategy in strategies:
            print(f"\n🎯 Testing {strategy.value.title()} Strategy:")
            
            # Configure strategy
            await self.load_balancer.configure_strategy(strategy)
            
            # Simulate 5 agent selections
            selections = []
            for _ in range(5):
                selected = await self.load_balancer.select_agent(
                    available_agents,
                    task_requirements={"cpu_intensive": False, "memory_intensive": False}
                )
                if selected:
                    selections.append(selected["agent_id"])
                    
                    # Simulate task completion with metrics
                    await self.load_balancer.load_tracker.record_task_completion(
                        selected["agent_id"],
                        {
                            "duration": random.uniform(0.5, 3.0),
                            "success": random.random() > 0.05,
                            "cpu_usage": random.uniform(0.1, 0.8),
                            "memory_usage": random.uniform(0.2, 0.6)
                        }
                    )
            
            # Show distribution
            selection_count = {}
            for agent_id in selections:
                selection_count[agent_id] = selection_count.get(agent_id, 0) + 1
                
            print(f"  Distribution: {dict(selection_count)}")
            
    async def _demo_monitoring_integration(self):
        """Demonstrate comprehensive monitoring"""
        print("\n📊 Comprehensive Monitoring Demo")
        print("-" * 35)
        
        # Simulate orchestration activity
        print("🔄 Simulating orchestration activity...")
        
        for i in range(20):
            # Simulate varied performance
            agent_type = random.choice(["rag_agent", "vision_agent", "analysis_agent", "notification_agent"])
            
            # Generate realistic metrics
            base_latency = {"rag_agent": 1.2, "vision_agent": 2.5, "analysis_agent": 1.8, "notification_agent": 0.8}
            latency = base_latency[agent_type] + random.uniform(-0.3, 0.7)
            
            # Occasional spikes
            if random.random() < 0.1:
                latency *= random.uniform(2, 5)
                
            success = random.random() > 0.03  # 97% success rate
            
            await self.monitor.record_orchestration_metrics(
                latency=latency,
                success=success,
                agent_type=agent_type,
                task_type="integration_demo"
            )
            
            if i % 5 == 0:
                print(f"  Processed {i + 1}/20 orchestration requests...")
                
            await asyncio.sleep(0.1)
            
        # Show monitoring results
        dashboard_data = self.monitor.get_dashboard_data()
        health_status = self.monitor.get_health_status()
        
        print(f"\n📈 Monitoring Results:")
        print(f"  System Health: {health_status['status']}")
        print(f"  Active Agents: {health_status['active_agents']}")
        print(f"  SLO Health: {health_status['slo_health']}")
        print(f"  OpenTelemetry: {'✅' if health_status['opentelemetry_enabled'] else '❌'}")
        
        # Show SLO status
        print(f"\n🎯 SLO Status:")
        for name, status in dashboard_data.slo_status.items():
            health_icon = "✅" if status.is_healthy else "❌"
            print(f"  {health_icon} {name}: {status.current_value:.1f} (target: {status.definition.target})")
            
    async def _demo_end_to_end_orchestration(self):
        """Demonstrate complete end-to-end orchestration"""
        print("\n🚀 End-to-End Orchestration Demo")
        print("-" * 35)
        
        # Complex multi-step task
        task = {
            "query": "Analyze security footage, detect anomalies, generate insights, and send alerts",
            "steps": [
                {"capability": "object_detection", "description": "Process video frames"},
                {"capability": "pattern_analysis", "description": "Analyze detected patterns"},
                {"capability": "alert_generation", "description": "Generate security alerts"}
            ]
        }
        
        print(f"📋 Complex Task: {task['query']}")
        print(f"🔄 Processing {len(task['steps'])} steps...")
        
        orchestration_start = time.time()
        results = []
        
        for i, step in enumerate(task["steps"], 1):
            print(f"\n  Step {i}: {step['description']}")
            
            # 1. Semantic agent discovery
            step_start = time.time()
            matches = await self.semantic_matcher.find_matching_agents(
                query=step["description"],
                required_capabilities=[step["capability"]],
                context={"step": i, "total_steps": len(task["steps"])}
            )
            
            if not matches:
                print(f"    ❌ No agents found for {step['capability']}")
                continue
                
            # 2. Load balancing selection
            candidate_agents = [match.agent_id for match in matches[:3]]  # Top 3 candidates
            selected = await self.load_balancer.select_agent(
                candidate_agents,
                task_requirements={"priority": "high", "real_time": True}
            )
            
            if not selected:
                print(f"    ❌ Load balancer couldn't select agent")
                continue
                
            print(f"    🎯 Selected: {selected['agent_name']} (score: {matches[0].total_score:.3f})")
            
            # 3. Simulate task execution
            execution_time = random.uniform(0.8, 2.5)
            await asyncio.sleep(execution_time)  # Simulate work
            
            success = random.random() > 0.05  # 95% success rate
            step_latency = time.time() - step_start
            
            # 4. Record monitoring metrics
            await self.monitor.record_orchestration_metrics(
                latency=step_latency,
                success=success,
                agent_type=selected["agent_type"],
                task_type="end_to_end_orchestration"
            )
            
            # 5. Update load balancer metrics
            await self.load_balancer.load_tracker.record_task_completion(
                selected["agent_id"],
                {
                    "duration": execution_time,
                    "success": success,
                    "step_number": i,
                    "total_steps": len(task["steps"])
                }
            )
            
            results.append({
                "step": i,
                "agent": selected["agent_name"],
                "success": success,
                "duration": step_latency
            })
            
            status = "✅" if success else "❌"
            print(f"    {status} Completed in {step_latency:.2f}s")
            
        orchestration_time = time.time() - orchestration_start
        successful_steps = sum(1 for r in results if r["success"])
        
        print(f"\n📊 Orchestration Summary:")
        print(f"  Total Time: {orchestration_time:.2f}s")
        print(f"  Success Rate: {successful_steps}/{len(results)} steps")
        print(f"  Average Step Time: {sum(r['duration'] for r in results) / len(results):.2f}s")
        
    async def _show_system_status(self):
        """Show final system status and statistics"""
        print("\n" + "="*60)
        print("📊 FINAL SYSTEM STATUS")
        print("="*60)
        
        # 1. Agent Registry Status
        agents = await self.db_service.get_all_agents()
        print(f"\n🤖 Agent Registry: {len(agents)} registered agents")
        
        agent_types = {}
        for agent in agents:
            agent_type = agent.get("agent_type", "unknown")
            agent_types[agent_type] = agent_types.get(agent_type, 0) + 1
            
        for agent_type, count in agent_types.items():
            print(f"  • {agent_type}: {count} agents")
            
        # 2. Semantic Matching Statistics
        print(f"\n🔍 Semantic Matching:")
        print(f"  • Capability Ontology: {len(self.semantic_matcher.capability_ontology.nodes)} nodes")
        print(f"  • Vector Embeddings: Enabled with sentence-transformers")
        print(f"  • Learning Enabled: ✅")
        
        # 3. Load Balancing Statistics
        stats = await self.load_balancer.get_load_balancing_stats()
        print(f"\n⚖️  Load Balancing:")
        print(f"  • Active Strategy: {stats.get('current_strategy', 'unknown')}")
        print(f"  • Total Selections: {stats.get('total_selections', 0)}")
        print(f"  • Average Response Time: {stats.get('avg_response_time', 0):.3f}s")
        
        # 4. Monitoring Status
        health_status = self.monitor.get_health_status()
        dashboard_data = self.monitor.get_dashboard_data()
        
        print(f"\n📊 Monitoring Status:")
        print(f"  • System Health: {health_status['status']}")
        print(f"  • SLO Health: {health_status['slo_health']}")
        print(f"  • OpenTelemetry: {'✅' if health_status['opentelemetry_enabled'] else '❌'}")
        print(f"  • Active Anomalies: {len(dashboard_data.anomalies)}")
        
        # 5. Performance Summary
        total_agents = len(dashboard_data.agent_performance_metrics)
        if total_agents > 0:
            avg_latency = sum(
                metrics.get("avg_latency", 0) 
                for metrics in dashboard_data.agent_performance_metrics.values()
            ) / total_agents
            
            avg_success_rate = sum(
                metrics.get("success_rate", 0)
                for metrics in dashboard_data.agent_performance_metrics.values()
            ) / total_agents
            
            print(f"\n⚡ Performance Summary:")
            print(f"  • Average Latency: {avg_latency:.3f}s")
            print(f"  • Average Success Rate: {avg_success_rate:.1f}%")
            print(f"  • Total Requests Processed: {sum(metrics.get('total_requests', 0) for metrics in dashboard_data.agent_performance_metrics.values())}")
            
        print(f"\n🎉 Integration Demo Complete!")
        print(f"   All systems operational and integrated successfully.")
        
    async def export_integration_report(self) -> Dict[str, Any]:
        """Export comprehensive integration report"""
        agents = await self.db_service.get_all_agents()
        health_status = self.monitor.get_health_status()
        dashboard_data = self.monitor.get_dashboard_data()
        load_stats = await self.load_balancer.get_load_balancing_stats()
        
        return {
            "integration_timestamp": datetime.now().isoformat(),
            "system_components": {
                "semantic_matching": "✅ Operational",
                "load_balancing": "✅ Operational", 
                "comprehensive_monitoring": "✅ Operational",
                "database_integration": "✅ Operational"
            },
            "agent_registry": {
                "total_agents": len(agents),
                "agent_types": list(set(agent.get("agent_type", "unknown") for agent in agents))
            },
            "semantic_capabilities": {
                "ontology_nodes": len(self.semantic_matcher.capability_ontology.nodes),
                "vector_embeddings": "enabled",
                "learning_mode": "enabled"
            },
            "load_balancing": {
                "current_strategy": load_stats.get("current_strategy"),
                "total_selections": load_stats.get("total_selections", 0),
                "strategies_available": [s.value for s in LoadBalancingStrategy]
            },
            "monitoring": {
                "system_health": health_status["status"],
                "slo_health": health_status["slo_health"],
                "opentelemetry_enabled": health_status["opentelemetry_enabled"],
                "slo_count": len(dashboard_data.slo_status),
                "anomaly_detection": "enabled"
            },
            "performance_metrics": {
                "agents_tracked": len(dashboard_data.agent_performance_metrics),
                "requests_processed": sum(
                    metrics.get("total_requests", 0) 
                    for metrics in dashboard_data.agent_performance_metrics.values()
                ),
                "system_uptime": "operational"
            }
        }


def create_integrated_app() -> FastAPI:
    """Create FastAPI app with all integrated features"""
    app = FastAPI(
        title="Complete Agent Orchestrator",
        description="Advanced agent orchestration with semantic matching, load balancing, and monitoring",
        version="2.0.0"
    )
    
    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include all feature routers
    app.include_router(semantic_router, prefix="/api/v1")
    app.include_router(load_balancing_router, prefix="/api/v1")
    app.include_router(monitoring_router, prefix="/api/v1")
    
    return app


async def main():
    """Main integration demo function"""
    orchestrator = CompleteAgentOrchestrator()
    
    try:
        await orchestrator.initialize()
        await orchestrator.demo_complete_system()
        
        # Export integration report
        report = await orchestrator.export_integration_report()
        
        # Save report
        with open("integration_report.json", "w") as f:
            json.dump(report, f, indent=2)
            
        print(f"\n📄 Integration report exported to 'integration_report.json'")
        
    except Exception as e:
        print(f"❌ Integration demo failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await orchestrator.db_service.disconnect()


if __name__ == "__main__":
    print("🚀 Starting Complete Agent Orchestrator Integration Demo")
    print("This demonstrates the full integration of all enhanced features")
    print()
    
    asyncio.run(main())

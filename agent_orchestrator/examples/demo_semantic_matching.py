"""
Semantic Agent Matching Demo

This demo script showcases the enhanced semantic agent matching capabilities
of the agent orchestrator service. It demonstrates:

1. Setting up semantic matching with capability ontology
2. Registering agents with capabilities and performance data
3. Finding agents using semantic similarity
4. Performance tracking and dynamic learning
5. Capability analysis and ontology exploration

Run this script to see semantic matching in action.

Requirements:
- sentence-transformers
- scikit-learn  
- numpy

Author: Agent Orchestrator Team
Version: 1.0.0
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_semantic_matching():
    """Comprehensive demo of semantic agent matching"""
    
    print("🤖 Semantic Agent Matching Demo")
    print("=" * 50)
    
    try:
        # Import semantic matching components
        from semantic_agent_matcher import (
            SemanticAgentMatcher, 
            get_semantic_matcher,
            find_agents_semantic,
            update_agent_performance_semantic
        )
        
        print("✅ Semantic matching dependencies loaded successfully")
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Install required packages:")
        print("pip install sentence-transformers scikit-learn numpy")
        return
    
    # Initialize semantic matcher
    print("\n🔧 Initializing Semantic Agent Matcher...")
    matcher = SemanticAgentMatcher(model_name="all-MiniLM-L6-v2")
    
    if matcher.embedding_model:
        print("✅ Embedding model loaded successfully")
    else:
        print("⚠️ Embedding model not available, using fallback matching")
    
    # Demo 1: Capability Ontology
    print("\n📊 Demo 1: Capability Ontology Exploration")
    print("-" * 40)
    
    ontology = matcher.ontology
    print(f"Ontology contains {len(ontology.nodes)} capability nodes")
    
    # Show some ontology relationships
    if "surveillance" in ontology.nodes:
        surveillance_node = ontology.nodes["surveillance"]
        print(f"'surveillance' has children: {list(surveillance_node.children)}")
    
    # Test capability expansion
    test_capabilities = ["person_detection", "video_analysis"]
    expanded = ontology.get_expanded_capabilities(test_capabilities)
    print(f"Capabilities {test_capabilities} expanded to: {list(expanded)}")
    
    # Test capability similarity
    similarity = ontology.calculate_capability_similarity("person_detection", "vehicle_detection")
    print(f"Similarity between 'person_detection' and 'vehicle_detection': {similarity:.2f}")
    
    # Demo 2: Agent Registration
    print("\n🤖 Demo 2: Agent Registration with Capabilities")
    print("-" * 40)
    
    agents_data = [
        {
            "id": "surveillance_agent_001",
            "capabilities": ["person_detection", "face_recognition", "video_analysis", "real_time_monitoring"],
            "performance": {"success_rate": 0.92, "avg_response_time": 1.5, "task_count": 35}
        },
        {
            "id": "security_agent_002", 
            "capabilities": ["vehicle_detection", "license_plate_recognition", "tracking", "alerting"],
            "performance": {"success_rate": 0.87, "avg_response_time": 2.1, "task_count": 28}
        },
        {
            "id": "analysis_agent_003",
            "capabilities": ["behavior_analysis", "anomaly_detection", "pattern_recognition", "video_analysis"],
            "performance": {"success_rate": 0.89, "avg_response_time": 3.2, "task_count": 22}
        },
        {
            "id": "rag_agent_004",
            "capabilities": ["rag_query", "search", "knowledge_retrieval", "text_analysis"],
            "performance": {"success_rate": 0.94, "avg_response_time": 0.8, "task_count": 45}
        },
        {
            "id": "prompt_agent_005",
            "capabilities": ["prompt_generation", "text_generation", "ai_processing"],
            "performance": {"success_rate": 0.91, "avg_response_time": 1.2, "task_count": 40}
        }
    ]
    
    for agent_data in agents_data:
        await matcher.register_agent(
            agent_id=agent_data["id"],
            capabilities=agent_data["capabilities"],
            agent_data=agent_data["performance"]
        )
        print(f"✅ Registered {agent_data['id']} with {len(agent_data['capabilities'])} capabilities")
    
    print(f"\nTotal agents registered: {len(matcher.agent_profiles)}")
    
    # Demo 3: Semantic Task Matching
    print("\n🎯 Demo 3: Semantic Task Matching")
    print("-" * 40)
    
    test_scenarios = [
        {
            "description": "Monitor parking lot for unauthorized people and vehicles using security cameras",
            "required_capabilities": ["person_detection", "vehicle_detection", "video_analysis"],
            "task_type": "surveillance_monitoring",
            "scenario_name": "Parking Lot Surveillance"
        },
        {
            "description": "Analyze customer behavior patterns in retail store footage",
            "required_capabilities": ["behavior_analysis", "person_detection", "pattern_recognition"],
            "task_type": "behavior_analysis",
            "scenario_name": "Retail Analytics"
        },
        {
            "description": "Search knowledge base for information about security protocols and procedures",
            "required_capabilities": ["search", "knowledge_retrieval"],
            "task_type": "information_retrieval",
            "scenario_name": "Knowledge Search"
        },
        {
            "description": "Generate detailed incident report based on surveillance data",
            "required_capabilities": ["prompt_generation", "text_generation"],
            "task_type": "report_generation",
            "scenario_name": "Report Generation"
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n📋 Scenario: {scenario['scenario_name']}")
        print(f"Task: {scenario['description']}")
        print(f"Required: {scenario['required_capabilities']}")
        
        results = await matcher.find_matching_agents(
            task_description=scenario["description"],
            required_capabilities=scenario["required_capabilities"],
            task_type=scenario["task_type"],
            top_k=3,
            min_score=0.2
        )
        
        if results:
            print(f"Found {len(results)} matching agents:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. Agent: {result.agent_id}")
                print(f"     Score: {result.combined_score:.3f}")
                print(f"     Matched: {result.matched_capabilities}")
                print(f"     Missing: {result.missing_capabilities}")
                if result.reasoning:
                    print(f"     Reasoning: {result.reasoning}")
        else:
            print("❌ No suitable agents found")
    
    # Demo 4: Performance Learning
    print("\n📈 Demo 4: Dynamic Performance Learning")
    print("-" * 40)
    
    # Simulate task executions and performance updates
    performance_updates = [
        {"agent_id": "surveillance_agent_001", "task_type": "person_detection", "success": True, "response_time": 1.2},
        {"agent_id": "surveillance_agent_001", "task_type": "person_detection", "success": True, "response_time": 1.1},
        {"agent_id": "surveillance_agent_001", "task_type": "vehicle_detection", "success": False, "response_time": 2.5},
        {"agent_id": "security_agent_002", "task_type": "vehicle_detection", "success": True, "response_time": 1.8},
        {"agent_id": "security_agent_002", "task_type": "vehicle_detection", "success": True, "response_time": 1.9},
        {"agent_id": "analysis_agent_003", "task_type": "behavior_analysis", "success": True, "response_time": 2.8},
    ]
    
    print("Simulating task executions and performance updates...")
    
    for update in performance_updates:
        agent_id = update["agent_id"]
        
        # Get performance before update
        if agent_id in matcher.agent_profiles:
            before_score = matcher.agent_profiles[agent_id].success_rate
        else:
            before_score = 0.5
        
        # Update performance
        await matcher.update_agent_performance(
            agent_id=update["agent_id"],
            task_type=update["task_type"],
            success=update["success"],
            response_time=update["response_time"]
        )
        
        # Get performance after update
        after_score = matcher.agent_profiles[agent_id].success_rate
        
        status = "✅" if update["success"] else "❌"
        direction = "↗️" if after_score > before_score else "↘️" if after_score < before_score else "➡️"
        
        print(f"  {status} {agent_id}: {update['task_type']} "
              f"({update['response_time']:.1f}s) {direction} {after_score:.3f}")
    
    # Demo 5: Re-run matching to show learning effects
    print("\n🔄 Demo 5: Matching After Performance Learning")
    print("-" * 40)
    
    print("Re-running person detection task after performance updates...")
    
    results_after_learning = await matcher.find_matching_agents(
        task_description="Detect people in surveillance camera feeds for security monitoring",
        required_capabilities=["person_detection"],
        task_type="person_detection",
        top_k=3,
        min_score=0.2
    )
    
    if results_after_learning:
        print("Updated rankings:")
        for i, result in enumerate(results_after_learning, 1):
            agent_profile = matcher.agent_profiles.get(result.agent_id)
            if agent_profile:
                task_performance = agent_profile.performance_scores.get("person_detection", "N/A")
                print(f"  {i}. {result.agent_id}")
                print(f"     Combined Score: {result.combined_score:.3f}")
                print(f"     Overall Success Rate: {agent_profile.success_rate:.3f}")
                print(f"     Person Detection Performance: {task_performance:.3f if task_performance != 'N/A' else 'N/A'}")
                print(f"     Task Count: {agent_profile.task_count}")
    
    # Demo 6: Capability Analysis
    print("\n🔍 Demo 6: Advanced Capability Analysis")
    print("-" * 40)
    
    analysis_capabilities = ["motion_detection", "real_time_alerts", "ai_processing"]
    
    print(f"Analyzing capabilities: {analysis_capabilities}")
    
    # Expand through ontology
    expanded_analysis = ontology.get_expanded_capabilities(analysis_capabilities)
    print(f"Expanded to: {list(expanded_analysis)}")
    
    # Find related capabilities
    for cap in analysis_capabilities:
        print(f"\nCapability: '{cap}'")
        
        # Find similar capabilities
        similarities = []
        for other_cap in ontology.nodes:
            if other_cap != cap:
                sim = ontology.calculate_capability_similarity(cap, other_cap)
                if sim > 0.3:
                    similarities.append((other_cap, sim))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        if similarities:
            print("  Similar capabilities:")
            for similar_cap, sim_score in similarities[:5]:  # Top 5
                print(f"    - {similar_cap}: {sim_score:.2f}")
        else:
            print("  No similar capabilities found")
    
    # Demo 7: System Statistics
    print("\n📊 Demo 7: System Statistics and Health")
    print("-" * 40)
    
    print(f"Agent Profiles: {len(matcher.agent_profiles)}")
    print(f"Capability Embeddings: {len(matcher.capability_embeddings)}")
    print(f"Task Embeddings Cache: {len(matcher.task_embeddings_cache)}")
    print(f"Ontology Nodes: {len(matcher.ontology.nodes)}")
    
    # Agent statistics
    if matcher.agent_profiles:
        avg_capabilities = sum(len(profile.capabilities) for profile in matcher.agent_profiles.values()) / len(matcher.agent_profiles)
        avg_success_rate = sum(profile.success_rate for profile in matcher.agent_profiles.values()) / len(matcher.agent_profiles)
        avg_task_count = sum(profile.task_count for profile in matcher.agent_profiles.values()) / len(matcher.agent_profiles)
        
        print(f"Average capabilities per agent: {avg_capabilities:.1f}")
        print(f"Average success rate: {avg_success_rate:.3f}")
        print(f"Average task count: {avg_task_count:.1f}")
    
    # Performance summary
    print("\n🏆 Performance Summary:")
    for agent_id, profile in matcher.agent_profiles.items():
        print(f"  {agent_id}:")
        print(f"    Success Rate: {profile.success_rate:.3f}")
        print(f"    Avg Response Time: {profile.avg_response_time:.2f}s")
        print(f"    Task Count: {profile.task_count}")
        if profile.specialization_scores:
            best_capability = max(profile.specialization_scores.items(), key=lambda x: x[1])
            print(f"    Best at: {best_capability[0]} ({best_capability[1]:.3f})")
    
    print("\n✅ Semantic Agent Matching Demo Complete!")
    print("🎉 The system successfully demonstrated:")
    print("   - Capability ontology and expansion")
    print("   - Semantic similarity matching")
    print("   - Dynamic performance learning")
    print("   - Multi-dimensional agent scoring")
    print("   - Real-time capability analysis")


async def demo_api_integration():
    """Demo API integration with semantic matching"""
    
    print("\n🌐 API Integration Demo")
    print("=" * 30)
    
    try:
        from semantic_endpoints import (
            SemanticTaskRequest,
            CapabilityAnalysisRequest,
            find_agents_semantic_enhanced,
            analyze_capabilities_enhanced
        )
        
        print("✅ API components loaded")
        
        # Demo API request structures
        print("\n📝 Example API Requests:")
        
        # Semantic matching request
        semantic_request = SemanticTaskRequest(
            task_description="Monitor building entrance for unauthorized access using facial recognition",
            required_capabilities=["face_recognition", "person_detection", "access_control"],
            task_type="security_monitoring",
            max_agents=2,
            min_score=0.4,
            use_semantic=True
        )
        
        print("\n1. Semantic Matching Request:")
        print(json.dumps(semantic_request.dict(), indent=2))
        
        # Capability analysis request
        capability_request = CapabilityAnalysisRequest(
            capabilities=["face_recognition", "vehicle_detection", "anomaly_detection"]
        )
        
        print("\n2. Capability Analysis Request:")
        print(json.dumps(capability_request.dict(), indent=2))
        
        print("\n📡 These requests can be sent to:")
        print("  POST /api/v2/semantic/agents/match")
        print("  POST /api/v2/semantic/capabilities/analyze")
        print("  POST /api/v2/semantic/agents/{agent_id}/performance")
        print("  GET  /api/v2/semantic/status")
        
    except ImportError as e:
        print(f"❌ API components not available: {e}")


async def run_performance_benchmark():
    """Run performance benchmarks for semantic matching"""
    
    print("\n⚡ Performance Benchmark")
    print("=" * 25)
    
    try:
        from semantic_agent_matcher import SemanticAgentMatcher
        
        matcher = SemanticAgentMatcher()
        
        # Register many agents for performance testing
        print("Registering 100 test agents...")
        start_time = datetime.now()
        
        for i in range(100):
            await matcher.register_agent(
                agent_id=f"perf_agent_{i:03d}",
                capabilities=[
                    f"capability_{i % 10}",
                    f"skill_{i % 15}",
                    "common_capability"
                ],
                agent_data={
                    "success_rate": 0.5 + (i % 5) * 0.1,
                    "avg_response_time": 1.0 + (i % 3) * 0.5,
                    "task_count": i % 20
                }
            )
        
        registration_time = (datetime.now() - start_time).total_seconds()
        print(f"✅ Registration time: {registration_time:.2f}s")
        
        # Benchmark matching performance
        print("Running matching benchmark...")
        start_time = datetime.now()
        
        for i in range(10):
            results = await matcher.find_matching_agents(
                task_description=f"Benchmark task {i} requiring specialized processing and analysis capabilities",
                required_capabilities=["common_capability", f"capability_{i % 5}"],
                top_k=5
            )
        
        matching_time = (datetime.now() - start_time).total_seconds()
        print(f"✅ 10 matching operations time: {matching_time:.2f}s")
        print(f"✅ Average per match: {matching_time / 10:.3f}s")
        
        # Memory usage estimate
        profile_count = len(matcher.agent_profiles)
        embedding_count = len(matcher.capability_embeddings)
        cache_size = len(matcher.task_embeddings_cache)
        
        print(f"📊 Memory usage:")
        print(f"   Agent profiles: {profile_count}")
        print(f"   Capability embeddings: {embedding_count}")
        print(f"   Cache entries: {cache_size}")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")


async def main():
    """Main demo function"""
    
    print("🚀 Starting Semantic Agent Matching Comprehensive Demo")
    print("=" * 60)
    
    try:
        # Run main semantic matching demo
        await demo_semantic_matching()
        
        # Run API integration demo
        await demo_api_integration()
        
        # Run performance benchmark
        await run_performance_benchmark()
        
        print("\n🎯 Next Steps:")
        print("1. Install the package: pip install -r requirements.txt")
        print("2. Start the service: python main.py")
        print("3. Try the API endpoints:")
        print("   POST /api/v2/semantic/agents/match")
        print("   GET  /api/v2/semantic/status")
        print("4. View documentation at: /docs")
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logger.exception("Demo error details:")
    
    print("\n✨ Demo complete! Check the logs for detailed information.")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())

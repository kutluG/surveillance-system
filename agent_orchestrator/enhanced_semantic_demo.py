"""
Enhanced Semantic Agent Matching Demo

This demo script showcases the enhanced semantic agent matching capabilities
including advanced learning algorithms, improved capability ontology, and
contextual performance tracking.

Features Demonstrated:
1. Enhanced capability ontology with domain clustering
2. Advanced performance tracking with context
3. Failure pattern analysis and learning
4. Domain expertise development
5. Adaptive learning rates
6. Multi-dimensional scoring

Author: Agent Orchestrator Team
Version: 2.0.0
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


async def demo_enhanced_semantic_matching():
    """Comprehensive demo of enhanced semantic agent matching"""
    
    print("🚀 Enhanced Semantic Agent Matching Demo")
    print("=" * 60)
    
    try:
        # Import enhanced semantic matching components
        from semantic_agent_matcher import (
            SemanticAgentMatcher, 
            CapabilityOntology,
            AgentCapabilityProfile,
            PerformanceMetric
        )
        
        print("✅ Enhanced semantic matching components loaded successfully")
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Install required packages:")
        print("pip install sentence-transformers scikit-learn numpy")
        return
    
    # Initialize enhanced semantic matcher
    print("\n🔧 Initializing Enhanced Semantic Agent Matcher...")
    matcher = SemanticAgentMatcher(model_name="all-MiniLM-L6-v2")
    
    if matcher.embedding_model:
        print("✅ Embedding model loaded successfully")
    else:
        print("⚠️ Embedding model not available, using fallback matching")
    
    # Demo 1: Enhanced Capability Ontology
    print("\n" + "="*60)
    print("📚 Demo 1: Enhanced Capability Ontology")
    print("="*60)
    
    ontology = matcher.ontology
    print(f"📋 Total capabilities in ontology: {len(ontology.nodes)}")
    print(f"🏢 Domain clusters: {len(ontology.domain_clusters)}")
    
    # Show domain clustering
    for domain, capabilities in ontology.domain_clusters.items():
        if len(capabilities) > 1:
            print(f"  🏷️ {domain}: {capabilities[:3]}...")
    
    # Test enhanced similarity calculation
    test_pairs = [
        ("person_detection", "face_detection"),
        ("vehicle_tracking", "person_tracking"),
        ("behavior_analysis", "pattern_recognition"),
        ("real_time_alerts", "email_notifications")
    ]
    
    print("\n🔍 Enhanced Similarity Scores:")
    for cap1, cap2 in test_pairs:
        similarity = ontology.calculate_enhanced_similarity(cap1, cap2)
        print(f"  {cap1} ↔ {cap2}: {similarity:.3f}")
    
    # Demo 2: Advanced Agent Registration
    print("\n" + "="*60)
    print("🤖 Demo 2: Advanced Agent Registration")
    print("="*60)
    
    # Register agents with enhanced profiles
    agents_config = [
        {
            "id": "enhanced_surveillance_001",
            "capabilities": ["person_detection", "vehicle_detection", "real_time_alerts"],
            "performance": {"success_rate": 0.85, "avg_response_time": 1.2, "task_count": 25}
        },
        {
            "id": "enhanced_ai_analyst_002", 
            "capabilities": ["behavior_analysis", "pattern_recognition", "risk_assessment"],
            "performance": {"success_rate": 0.92, "avg_response_time": 2.8, "task_count": 15}
        },
        {
            "id": "enhanced_tracker_003",
            "capabilities": ["person_tracking", "trajectory_analysis", "multi_object_tracking"],
            "performance": {"success_rate": 0.78, "avg_response_time": 1.8, "task_count": 40}
        },
        {
            "id": "enhanced_processor_004",
            "capabilities": ["video_processing", "image_processing", "format_conversion"],
            "performance": {"success_rate": 0.95, "avg_response_time": 0.9, "task_count": 60}
        }
    ]
    
    for agent_config in agents_config:
        await matcher.register_agent(
            agent_id=agent_config["id"],
            capabilities=agent_config["capabilities"], 
            agent_data=agent_config["performance"]
        )
        
        profile = matcher.agent_profiles[agent_config["id"]]
        expanded_count = len(profile.capabilities)
        original_count = len(agent_config["capabilities"])
        
        print(f"✅ {agent_config['id']}")
        print(f"   📈 Capabilities expanded: {original_count} → {expanded_count}")
        print(f"   🎯 Initial success rate: {profile.success_rate:.3f}")
        print(f"   ⚡ Avg response time: {profile.avg_response_time:.1f}s")
        print(f"   🧠 Learning rate: {profile.learning_rate:.3f}")
    
    # Demo 3: Contextual Performance Updates
    print("\n" + "="*60)
    print("📊 Demo 3: Contextual Performance Learning")
    print("="*60)
    
    # Simulate contextual task executions
    performance_scenarios = [
        {
            "agent_id": "enhanced_surveillance_001",
            "task_type": "person_detection", 
            "success": True,
            "response_time": 1.1,
            "context": {"time_of_day": "morning", "lighting": "good", "crowd_density": "low"}
        },
        {
            "agent_id": "enhanced_surveillance_001",
            "task_type": "person_detection",
            "success": False,
            "response_time": 2.3,
            "context": {"time_of_day": "night", "lighting": "poor", "crowd_density": "high"}
        },
        {
            "agent_id": "enhanced_ai_analyst_002",
            "task_type": "behavior_analysis",
            "success": True,
            "response_time": 2.5,
            "context": {"scene_complexity": "medium", "activity_level": "normal"}
        },
        {
            "agent_id": "enhanced_tracker_003",
            "task_type": "person_tracking",
            "success": True,
            "response_time": 1.5,
            "context": {"object_count": 3, "occlusion_level": "low"}
        },
        {
            "agent_id": "enhanced_tracker_003",
            "task_type": "person_tracking",
            "success": False,
            "response_time": 3.2,
            "context": {"object_count": 15, "occlusion_level": "high"}
        }
    ]
    
    print("🔄 Simulating contextual performance updates...")
    
    for scenario in performance_scenarios:
        agent_id = scenario["agent_id"]
        
        # Get performance before update
        if agent_id in matcher.agent_profiles:
            before_success = matcher.agent_profiles[agent_id].success_rate
            before_adaptation = matcher.agent_profiles[agent_id].adaptation_score
        else:
            before_success = 0.5
            before_adaptation = 0.5
        
        # Update performance with context
        await matcher.update_agent_performance(
            agent_id=scenario["agent_id"],
            task_type=scenario["task_type"],
            success=scenario["success"],
            response_time=scenario["response_time"],
            context=scenario["context"]
        )
        
        # Get performance after update
        profile = matcher.agent_profiles[agent_id]
        after_success = profile.success_rate
        after_adaptation = profile.adaptation_score
        
        status = "✅" if scenario["success"] else "❌"
        success_trend = "↗️" if after_success > before_success else "↘️" if after_success < before_success else "➡️"
        adaptation_trend = "↗️" if after_adaptation > before_adaptation else "↘️" if after_adaptation < before_adaptation else "➡️"
        
        print(f"  {status} {agent_id[:20]}...")
        print(f"     📋 Task: {scenario['task_type']} ({scenario['response_time']:.1f}s)")
        print(f"     🎯 Success: {before_success:.3f} → {after_success:.3f} {success_trend}")
        print(f"     🧠 Adaptation: {before_adaptation:.3f} → {after_adaptation:.3f} {adaptation_trend}")
        
        # Show context learning
        if scenario["task_type"] in profile.capability_confidence:
            confidence = profile.capability_confidence[scenario["task_type"]]
            print(f"     🎲 Confidence: {confidence:.3f}")
    
    # Demo 4: Enhanced Task Matching
    print("\n" + "="*60)
    print("🎯 Demo 4: Enhanced Task Matching with Multi-Dimensional Scoring")
    print("="*60)
    
    test_tasks = [
        {
            "description": "Detect and track people in crowded shopping mall during peak hours",
            "required_capabilities": ["person_detection", "person_tracking", "crowd_analysis"],
            "task_type": "surveillance_monitoring"
        },
        {
            "description": "Analyze suspicious behavioral patterns in parking garage surveillance footage",
            "required_capabilities": ["behavior_analysis", "pattern_recognition", "anomaly_detection"],
            "task_type": "security_analysis"
        },
        {
            "description": "Process and convert multiple video formats for real-time streaming",
            "required_capabilities": ["video_processing", "format_conversion", "stream_processing"],
            "task_type": "media_processing"
        }
    ]
    
    for i, task in enumerate(test_tasks, 1):
        print(f"\n🎯 Test Task {i}: {task['description'][:50]}...")
        print(f"📋 Required capabilities: {task['required_capabilities']}")
        
        try:
            # Find matching agents
            results = await matcher.find_matching_agents(
                task_description=task["description"],
                required_capabilities=task["required_capabilities"],
                task_type=task["task_type"],
                top_k=3,
                min_score=0.3
            )
            
            if results:
                print(f"🔍 Found {len(results)} matching agents:")
                for j, result in enumerate(results, 1):
                    print(f"  {j}. {result.agent_name} (Score: {result.combined_score:.3f})")
                    print(f"     🎯 Capability Match: {result.capability_match_score:.3f}")
                    print(f"     🔗 Semantic Similarity: {result.similarity_score:.3f}")
                    print(f"     📊 Performance Score: {result.performance_score:.3f}")
                    print(f"     🎲 Confidence: {result.confidence:.3f}")
                    print(f"     ✅ Matched: {result.matched_capabilities}")
                    if result.missing_capabilities:
                        print(f"     ❌ Missing: {result.missing_capabilities}")
                    print(f"     💭 Reasoning: {result.reasoning[:80]}...")
            else:
                print("❌ No suitable agents found")
                
        except Exception as e:
            print(f"❌ Error in matching: {e}")
    
    # Demo 5: Capability Improvement Suggestions
    print("\n" + "="*60)
    print("🎓 Demo 5: Capability Improvement Suggestions")
    print("="*60)
    
    for agent_id, profile in matcher.agent_profiles.items():
        print(f"\n🤖 Agent: {agent_id}")
        print(f"📚 Current capabilities: {len(profile.capabilities)}")
        
        # Get domain expertise
        if profile.domain_expertise:
            top_domain = max(profile.domain_expertise.items(), key=lambda x: x[1])
            print(f"🏆 Top domain expertise: {top_domain[0]} ({top_domain[1]:.3f})")
        
        # Show specialization scores
        if profile.specialization_scores:
            top_specializations = sorted(
                profile.specialization_scores.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
            print(f"⭐ Top specializations:")
            for spec, score in top_specializations:
                print(f"   - {spec}: {score:.3f}")
        
        # Show recent performance trends
        if profile.performance_history:
            recent_tasks = list(profile.performance_history.keys())[:3]
            print(f"📈 Recent task performance:")
            for task_type in recent_tasks:
                if task_type in profile.performance_scores:
                    score = profile.performance_scores[task_type]
                    print(f"   - {task_type}: {score:.3f}")
    
    # Demo 6: Failure Pattern Analysis
    print("\n" + "="*60)
    print("🔍 Demo 6: Failure Pattern Analysis")
    print("="*60)
    
    # Add some failures to demonstrate pattern analysis
    failure_scenarios = [
        {
            "agent_id": "enhanced_surveillance_001",
            "task_type": "person_detection",
            "success": False,
            "response_time": 3.5,
            "context": {"lighting": "poor", "weather": "rain"}
        },
        {
            "agent_id": "enhanced_surveillance_001", 
            "task_type": "person_detection",
            "success": False,
            "response_time": 2.8,
            "context": {"lighting": "poor", "weather": "fog"}
        },
        {
            "agent_id": "enhanced_surveillance_001",
            "task_type": "person_detection", 
            "success": False,
            "response_time": 4.1,
            "context": {"lighting": "poor", "weather": "night"}
        }
    ]
    
    print("⚠️ Simulating failure scenarios for pattern analysis...")
    
    for scenario in failure_scenarios:
        await matcher.update_agent_performance(
            agent_id=scenario["agent_id"],
            task_type=scenario["task_type"],
            success=scenario["success"],
            response_time=scenario["response_time"],
            context=scenario["context"]
        )
    
    # Analyze failure patterns
    agent_id = "enhanced_surveillance_001"
    if agent_id in matcher.agent_profiles:
        profile = matcher.agent_profiles[agent_id]
        if profile.failure_patterns:
            print(f"\n🔍 Failure Analysis for {agent_id}:")
            print(f"   📊 Total failures tracked: {len(profile.failure_patterns)}")
            
            # Common failure contexts
            context_analysis = {}
            for failure in profile.failure_patterns:
                for key, value in failure["context"].items():
                    context_key = f"{key}:{value}"
                    context_analysis[context_key] = context_analysis.get(context_key, 0) + 1
            
            if context_analysis:
                print(f"   🎯 Common failure contexts:")
                for context, count in sorted(context_analysis.items(), key=lambda x: x[1], reverse=True)[:3]:
                    print(f"      - {context}: {count} occurrences")
            
            # Learning adjustments
            print(f"   🧠 Current learning rate: {profile.learning_rate:.3f}")
            if "person_detection" in profile.capability_confidence:
                confidence = profile.capability_confidence["person_detection"]
                print(f"   🎲 Person detection confidence: {confidence:.3f}")
    
    print("\n" + "="*60)
    print("🎉 Enhanced Semantic Agent Matching Demo Complete!")
    print("="*60)
    
    # Summary statistics
    print(f"\n📊 Demo Summary:")
    print(f"   🤖 Agents registered: {len(matcher.agent_profiles)}")
    print(f"   📚 Capabilities in ontology: {len(matcher.ontology.nodes)}")
    print(f"   🏢 Domain clusters: {len(matcher.ontology.domain_clusters)}")
    print(f"   🔍 Embedding model active: {'Yes' if matcher.embedding_model else 'No'}")
    
    total_tasks = sum(profile.task_count for profile in matcher.agent_profiles.values())
    avg_success = sum(profile.success_rate for profile in matcher.agent_profiles.values()) / len(matcher.agent_profiles)
    print(f"   📈 Total tasks processed: {total_tasks}")
    print(f"   🎯 Average success rate: {avg_success:.3f}")


if __name__ == "__main__":
    asyncio.run(demo_enhanced_semantic_matching())

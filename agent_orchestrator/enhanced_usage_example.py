"""
Enhanced Semantic Agent Matching - Usage Example

This example demonstrates how to use the enhanced semantic agent matching
capabilities in your applications.

Features:
- Vector-based capability matching with embeddings
- Hierarchical capability ontology with inheritance  
- Dynamic capability learning from performance
- Multi-dimensional scoring with confidence estimation
- Contextual performance tracking

Author: Agent Orchestrator Team
Version: 2.0.0
"""

import asyncio
from typing import Dict, List, Any
from semantic_agent_matcher import SemanticAgentMatcher


class EnhancedSemanticMatchingExample:
    """Example usage of enhanced semantic agent matching"""
    
    def __init__(self):
        self.matcher = SemanticAgentMatcher(model_name="all-MiniLM-L6-v2")
    
    async def setup_agents(self):
        """Register example agents with enhanced capabilities"""
        
        # Security Camera Agent
        await self.matcher.register_agent(
            agent_id="security_cam_001",
            capabilities=["person_detection", "vehicle_detection", "motion_detection", "real_time_alerts"],
            agent_data={
                "success_rate": 0.89,
                "avg_response_time": 1.2,
                "task_count": 150,
                "performance_scores": {
                    "person_detection": 0.92,
                    "vehicle_detection": 0.85,
                    "motion_detection": 0.95
                }
            }
        )
        
        # AI Behavior Analyst Agent  
        await self.matcher.register_agent(
            agent_id="behavior_analyst_002",
            capabilities=["behavior_analysis", "pattern_recognition", "anomaly_detection", "risk_assessment"],
            agent_data={
                "success_rate": 0.94,
                "avg_response_time": 3.5,
                "task_count": 75,
                "performance_scores": {
                    "behavior_analysis": 0.96,
                    "pattern_recognition": 0.91,
                    "anomaly_detection": 0.88
                }
            }
        )
        
        # Multi-Object Tracker Agent
        await self.matcher.register_agent(
            agent_id="object_tracker_003", 
            capabilities=["person_tracking", "vehicle_tracking", "trajectory_analysis"],
            agent_data={
                "success_rate": 0.82,
                "avg_response_time": 2.1,
                "task_count": 200,
                "performance_scores": {
                    "person_tracking": 0.84,
                    "vehicle_tracking": 0.79,
                    "trajectory_analysis": 0.81
                }
            }
        )
        
        print("✅ Enhanced agents registered successfully")
    
    async def example_semantic_matching(self):
        """Demonstrate enhanced semantic matching"""
        
        # Complex surveillance task
        task_description = """
        Monitor busy intersection for traffic violations and suspicious behavior.
        Detect vehicles running red lights, track suspicious individuals,
        and generate real-time alerts for security personnel.
        """
        
        required_capabilities = [
            "vehicle_detection", 
            "person_tracking",
            "behavior_analysis", 
            "real_time_alerts"
        ]
        
        print("\n🎯 Finding agents for complex surveillance task...")
        print(f"📋 Task: {task_description[:60]}...")
        print(f"🔧 Required capabilities: {required_capabilities}")
        
        # Find matching agents with enhanced scoring
        results = await self.matcher.find_matching_agents(
            task_description=task_description,
            required_capabilities=required_capabilities,
            task_type="traffic_surveillance",
            top_k=3,
            min_score=0.4
        )
        
        print(f"\n🔍 Found {len(results)} matching agents:")
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Agent: {result.agent_name}")
            print(f"   🎯 Combined Score: {result.combined_score:.3f}")
            print(f"   📊 Capability Match: {result.capability_match_score:.3f}")
            print(f"   🔗 Semantic Similarity: {result.similarity_score:.3f}")
            print(f"   📈 Performance Score: {result.performance_score:.3f}")
            print(f"   🎲 Confidence: {result.confidence:.3f}")
            print(f"   ✅ Matched Capabilities: {result.matched_capabilities}")
            if result.missing_capabilities:
                print(f"   ❌ Missing Capabilities: {result.missing_capabilities}")
            print(f"   💭 Reasoning: {result.reasoning}")
            
            # Enhanced scoring details
            print(f"   🏢 Domain Match: {result.domain_match_score:.3f}")
            print(f"   🧠 Adaptation Score: {result.adaptation_score:.3f}")
            print(f"   📈 Learning Trajectory: {result.learning_trajectory}")
            print(f"   ⚠️ Risk Assessment: {result.risk_assessment}")
    
    async def example_performance_learning(self):
        """Demonstrate contextual performance learning"""
        
        print("\n📊 Demonstrating contextual performance learning...")
        
        # Simulate task execution with context
        learning_scenarios = [
            {
                "agent_id": "security_cam_001",
                "task_type": "person_detection",
                "success": True,
                "response_time": 1.1,
                "context": {
                    "lighting_conditions": "daylight",
                    "weather": "clear", 
                    "crowd_density": "medium",
                    "camera_angle": "optimal"
                }
            },
            {
                "agent_id": "security_cam_001", 
                "task_type": "person_detection",
                "success": False,
                "response_time": 2.8,
                "context": {
                    "lighting_conditions": "night",
                    "weather": "heavy_rain",
                    "crowd_density": "high", 
                    "camera_angle": "suboptimal"
                }
            },
            {
                "agent_id": "behavior_analyst_002",
                "task_type": "behavior_analysis",
                "success": True,
                "response_time": 3.2,
                "context": {
                    "scene_complexity": "high",
                    "activity_level": "busy",
                    "time_of_day": "rush_hour"
                }
            }
        ]
        
        for scenario in learning_scenarios:
            agent_id = scenario["agent_id"]
            
            # Get performance before update
            profile = self.matcher.agent_profiles[agent_id]
            before_success = profile.success_rate
            before_confidence = profile.capability_confidence.get(scenario["task_type"], 0.5)
            
            # Update performance with context
            await self.matcher.update_agent_performance(
                agent_id=scenario["agent_id"],
                task_type=scenario["task_type"], 
                success=scenario["success"],
                response_time=scenario["response_time"],
                context=scenario["context"]
            )
            
            # Show learning results
            after_success = profile.success_rate
            after_confidence = profile.capability_confidence.get(scenario["task_type"], 0.5)
            
            status = "✅" if scenario["success"] else "❌"
            success_change = after_success - before_success
            confidence_change = after_confidence - before_confidence
            
            print(f"\n{status} {agent_id}")
            print(f"   📋 Task: {scenario['task_type']}")
            print(f"   ⚡ Response Time: {scenario['response_time']:.1f}s")
            print(f"   🎯 Success Rate: {before_success:.3f} → {after_success:.3f} ({success_change:+.3f})")
            print(f"   🎲 Confidence: {before_confidence:.3f} → {after_confidence:.3f} ({confidence_change:+.3f})")
            print(f"   🌍 Context: {scenario['context']}")
            
            # Show domain expertise development
            if profile.domain_expertise:
                top_domain = max(profile.domain_expertise.items(), key=lambda x: x[1])
                print(f"   🏆 Top Domain: {top_domain[0]} ({top_domain[1]:.3f})")
    
    async def example_capability_analysis(self):
        """Demonstrate capability analysis and suggestions"""
        
        print("\n📚 Analyzing agent capabilities and suggesting improvements...")
        
        for agent_id, profile in self.matcher.agent_profiles.items():
            print(f"\n🤖 Agent: {agent_id}")
            
            # Current capabilities
            original_caps = ["person_detection", "vehicle_detection"] # Example original caps
            expanded_caps = profile.capabilities
            print(f"   📈 Capabilities: {len(original_caps)} → {len(expanded_caps)} (expanded)")
            
            # Specialization analysis
            if profile.specialization_scores:
                top_specs = sorted(
                    profile.specialization_scores.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
                print(f"   ⭐ Top Specializations:")
                for spec, score in top_specs:
                    print(f"      - {spec}: {score:.3f}")
            
            # Domain expertise
            if profile.domain_expertise:
                print(f"   🏢 Domain Expertise:")
                for domain, expertise in profile.domain_expertise.items():
                    print(f"      - {domain}: {expertise:.3f}")
            
            # Learning characteristics
            print(f"   🧠 Learning Rate: {profile.learning_rate:.3f}")
            print(f"   📊 Adaptation Score: {profile.adaptation_score:.3f}")
            print(f"   📋 Task Count: {profile.task_count}")
            
            # Failure analysis
            if profile.failure_patterns:
                print(f"   ⚠️ Recent Failures: {len(profile.failure_patterns)}")
                
                # Common failure contexts
                context_counts = {}
                for failure in profile.failure_patterns[-5:]:  # Last 5 failures
                    for key, value in failure["context"].items():
                        context_key = f"{key}:{value}"
                        context_counts[context_key] = context_counts.get(context_key, 0) + 1
                
                if context_counts:
                    common_context = max(context_counts.items(), key=lambda x: x[1])
                    print(f"      Most common failure context: {common_context[0]} ({common_context[1]} times)")
    
    async def example_ontology_exploration(self):
        """Demonstrate capability ontology features"""
        
        print("\n🌐 Exploring enhanced capability ontology...")
        
        ontology = self.matcher.ontology
        
        # Show ontology statistics
        print(f"📊 Ontology Statistics:")
        print(f"   📚 Total capabilities: {len(ontology.nodes)}")
        print(f"   🏢 Domain clusters: {len(ontology.domain_clusters)}")
        print(f"   🔗 Capability relationships: {len(ontology.capability_relationships)}")
        
        # Show domain clustering
        print(f"\n🏢 Domain Clusters:")
        for domain, capabilities in ontology.domain_clusters.items():
            if len(capabilities) > 1:
                print(f"   {domain}: {capabilities[:3]}{'...' if len(capabilities) > 3 else ''}")
        
        # Test capability expansion
        test_capabilities = ["person_detection", "alerting"]
        expanded = ontology.get_expanded_capabilities(test_capabilities)
        print(f"\n📈 Capability Expansion Example:")
        print(f"   Original: {test_capabilities}")
        print(f"   Expanded: {sorted(list(expanded))}")
        
        # Test similarity calculations
        print(f"\n🔍 Enhanced Similarity Examples:")
        similarity_tests = [
            ("person_detection", "face_detection"),
            ("behavior_analysis", "pattern_recognition"),
            ("real_time_alerts", "email_notifications"),
            ("person_tracking", "vehicle_tracking")
        ]
        
        for cap1, cap2 in similarity_tests:
            similarity = ontology.calculate_enhanced_similarity(cap1, cap2)
            print(f"   {cap1} ↔ {cap2}: {similarity:.3f}")
        
        # Domain scoring example
        agent_caps = ["person_detection", "face_detection", "real_time_alerts"]
        cv_score = ontology.get_capability_domain_score(agent_caps, "computer_vision")
        print(f"\n🎯 Domain Scoring Example:")
        print(f"   Capabilities: {agent_caps}")
        print(f"   Computer Vision domain score: {cv_score:.3f}")
        
        # Improvement suggestions
        current_caps = ["person_detection"]
        target_caps = ["person_detection", "behavior_analysis", "risk_assessment"]
        suggestions = ontology.suggest_capability_improvements(current_caps, target_caps)
        print(f"\n💡 Improvement Suggestions:")
        print(f"   Current: {current_caps}")
        print(f"   Target: {target_caps}")
        if suggestions:
            for suggestion in suggestions:
                print(f"   - {suggestion}")
        else:
            print("   - No specific suggestions available")
    
    async def run_example(self):
        """Run the complete enhanced semantic matching example"""
        
        print("🚀 Enhanced Semantic Agent Matching Example")
        print("=" * 60)
        
        # Setup
        await self.setup_agents()
        
        # Demonstrate features
        await self.example_semantic_matching()
        await self.example_performance_learning()
        await self.example_capability_analysis()
        await self.example_ontology_exploration()
        
        print("\n" + "=" * 60)
        print("🎉 Enhanced Semantic Matching Example Complete!")
        print("=" * 60)


# Usage
async def main():
    example = EnhancedSemanticMatchingExample()
    await example.run_example()


if __name__ == "__main__":
    asyncio.run(main())

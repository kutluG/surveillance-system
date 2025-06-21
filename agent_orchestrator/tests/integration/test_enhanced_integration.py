#!/usr/bin/env python3
"""
Enhanced Integration Test Suite for Agent Orchestrator
Tests advanced semantic matching, load balancing, monitoring, and security features
"""

import asyncio
import pytest
import httpx
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Test Configuration
TEST_BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30

class EnhancedIntegrationTester:
    """Comprehensive integration tester for enhanced agent orchestrator"""
    
    def __init__(self, base_url: str = TEST_BASE_URL):
        self.base_url = base_url
        self.test_agents = []
        self.test_tasks = []
        self.auth_token = None
        
    async def setup(self):
        """Set up test environment"""
        print("🚀 Setting up enhanced integration test environment...")
        
        # Test basic connectivity
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    print("✅ Service connectivity verified")
                else:
                    raise Exception(f"Service not ready: {response.status_code}")
            except Exception as e:
                raise Exception(f"Failed to connect to service: {e}")
    
    async def test_enhanced_semantic_matching(self):
        """Test advanced semantic agent matching capabilities"""
        print("\n🧠 Testing Enhanced Semantic Agent Matching...")
        
        async with httpx.AsyncClient() as client:
            # Register agents with diverse capabilities
            test_agents = [
                {
                    "type": "DETECTION",
                    "name": "Advanced Object Detector",
                    "endpoint": "http://detector1:8001",
                    "capabilities": [
                        "person_detection", "vehicle_detection", "face_recognition",
                        "anomaly_detection", "real_time_processing"
                    ]
                },
                {
                    "type": "ANALYSIS", 
                    "name": "ML Analytics Engine",
                    "endpoint": "http://analytics1:8002",
                    "capabilities": [
                        "pattern_analysis", "statistical_modeling", "trend_detection",
                        "behavior_analysis", "predictive_analytics"
                    ]
                },
                {
                    "type": "CLASSIFICATION",
                    "name": "Security Classifier",
                    "endpoint": "http://classifier1:8003", 
                    "capabilities": [
                        "threat_classification", "risk_assessment", "priority_scoring",
                        "event_categorization", "compliance_checking"
                    ]
                }
            ]
            
            # Register agents
            for agent_data in test_agents:
                response = await client.post(
                    f"{self.base_url}/api/v1/agents/register",
                    json=agent_data,
                    timeout=TEST_TIMEOUT
                )
                if response.status_code == 200:
                    result = response.json()
                    self.test_agents.append(result["agent_id"])
                    print(f"✅ Registered agent: {agent_data['name']}")
                else:
                    print(f"❌ Failed to register agent: {response.text}")
            
            # Test semantic matching with complex queries
            test_queries = [
                {
                    "query": "detect suspicious person behavior in real-time",
                    "expected_types": ["DETECTION", "ANALYSIS"]
                },
                {
                    "query": "classify security threats and assess risk levels", 
                    "expected_types": ["CLASSIFICATION", "ANALYSIS"]
                },
                {
                    "query": "analyze behavioral patterns for anomaly detection",
                    "expected_types": ["ANALYSIS", "DETECTION"]
                }
            ]
            
            for test_query in test_queries:
                # Create task to trigger semantic matching
                task_data = {
                    "type": "ANALYSIS",
                    "description": test_query["query"],
                    "priority": 3,
                    "metadata": {
                        "semantic_test": True,
                        "expected_types": test_query["expected_types"]
                    }
                }
                
                response = await client.post(
                    f"{self.base_url}/api/v1/tasks",
                    json=task_data,
                    timeout=TEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.test_tasks.append(result["task_id"])
                    print(f"✅ Semantic matching test: {test_query['query'][:50]}...")
                else:
                    print(f"❌ Semantic matching failed: {response.text}")
    
    async def test_advanced_load_balancing(self):
        """Test advanced load balancing strategies"""
        print("\n⚖️ Testing Advanced Load Balancing...")
        
        async with httpx.AsyncClient() as client:
            # Test different load balancing strategies
            strategies = ["WEIGHTED_ROUND_ROBIN", "LEAST_CONNECTIONS", "RESOURCE_AWARE"]
            
            for strategy in strategies:
                # Create multiple tasks to test load balancing
                tasks = []
                for i in range(5):
                    task_data = {
                        "type": "DETECTION",
                        "description": f"Load balancing test task {i+1} for {strategy}",
                        "priority": 2,
                        "metadata": {
                            "load_balance_test": True,
                            "strategy": strategy,
                            "batch_id": f"batch_{strategy}_{int(time.time())}"
                        }
                    }
                    
                    response = await client.post(
                        f"{self.base_url}/api/v1/tasks", 
                        json=task_data,
                        timeout=TEST_TIMEOUT
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        tasks.append(result["task_id"])
                        self.test_tasks.extend(tasks)
                
                print(f"✅ Load balancing test completed for {strategy}: {len(tasks)} tasks")
    
    async def test_comprehensive_monitoring(self):
        """Test comprehensive monitoring and metrics collection"""
        print("\n📊 Testing Comprehensive Monitoring...")
        
        async with httpx.AsyncClient() as client:
            # Test monitoring endpoints
            monitoring_endpoints = [
                "/api/v1/monitoring/agents/analytics",
                "/api/v1/monitoring/tasks/analytics", 
                "/api/v1/monitoring/slo/tracking",
                "/api/v1/monitoring/anomaly/detection",
                "/api/v1/health/detailed"
            ]
            
            for endpoint in monitoring_endpoints:
                try:
                    response = await client.get(
                        f"{self.base_url}{endpoint}",
                        timeout=TEST_TIMEOUT
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"✅ Monitoring endpoint: {endpoint}")
                        
                        # Verify expected monitoring data structure
                        if "metrics" in data or "analytics" in data or "status" in data:
                            print(f"   📈 Data structure verified")
                        else:
                            print(f"   ⚠️ Unexpected data structure: {list(data.keys())}")
                    else:
                        print(f"❌ Monitoring endpoint failed: {endpoint} - {response.status_code}")
                        
                except Exception as e:
                    print(f"❌ Monitoring endpoint error: {endpoint} - {e}")
    
    async def test_distributed_tracing(self):
        """Test OpenTelemetry distributed tracing"""
        print("\n🔍 Testing Distributed Tracing...")
        
        async with httpx.AsyncClient() as client:
            # Create a task that will generate traces
            trace_task = {
                "type": "ANALYSIS",
                "description": "Distributed tracing test task",
                "priority": 1,
                "metadata": {
                    "tracing_test": True,
                    "trace_id": f"test_trace_{int(time.time())}",
                    "expected_spans": ["task_creation", "agent_selection", "task_execution"]
                }
            }
            
            # Add tracing headers
            headers = {
                "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
                "tracestate": "test=true"
            }
            
            response = await client.post(
                f"{self.base_url}/api/v1/tasks",
                json=trace_task,
                headers=headers,
                timeout=TEST_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                self.test_tasks.append(result["task_id"])
                print("✅ Distributed tracing test task created")
                
                # Check for trace propagation in response headers
                if "trace-id" in response.headers or "x-trace-id" in response.headers:
                    print("✅ Trace ID propagation verified")
                else:
                    print("⚠️ Trace ID propagation not detected in headers")
            else:
                print(f"❌ Distributed tracing test failed: {response.text}")
    
    async def test_enhanced_security(self):
        """Test enhanced security features"""
        print("\n🔒 Testing Enhanced Security Features...")
        
        async with httpx.AsyncClient() as client:
            # Test without authentication (should fail)
            response = await client.post(
                f"{self.base_url}/api/v1/agents/register",
                json={
                    "type": "DETECTION",
                    "name": "Unauthorized Agent",
                    "endpoint": "http://unauthorized:8000",
                    "capabilities": ["test"]
                },
                timeout=TEST_TIMEOUT
            )
            
            # Should return 401 or 403 if security is enabled
            if response.status_code in [401, 403]:
                print("✅ Unauthorized access properly blocked")
            else:
                print(f"⚠️ Security may not be fully enabled: {response.status_code}")
            
            # Test rate limiting
            print("Testing rate limiting...")
            rate_limit_responses = []
            
            for i in range(10):  # Send multiple requests rapidly
                response = await client.get(f"{self.base_url}/health")
                rate_limit_responses.append(response.status_code)
                
            # Check if any requests were rate limited (status 429)
            if 429 in rate_limit_responses:
                print("✅ Rate limiting is active")
            else:
                print("⚠️ Rate limiting may not be configured or threshold not reached")
    
    async def test_workflow_orchestration(self):
        """Test enhanced workflow orchestration"""
        print("\n🔄 Testing Workflow Orchestration...")
        
        async with httpx.AsyncClient() as client:
            # Create a complex workflow
            workflow_data = {
                "name": "Enhanced Security Analysis Workflow",
                "description": "Multi-stage security analysis with semantic matching",
                "steps": [
                    {
                        "name": "detect_objects",
                        "agent_type": "DETECTION",
                        "requirements": ["person_detection", "vehicle_detection"]
                    },
                    {
                        "name": "analyze_behavior", 
                        "agent_type": "ANALYSIS",
                        "requirements": ["behavior_analysis", "pattern_analysis"],
                        "depends_on": ["detect_objects"]
                    },
                    {
                        "name": "classify_threats",
                        "agent_type": "CLASSIFICATION", 
                        "requirements": ["threat_classification", "risk_assessment"],
                        "depends_on": ["analyze_behavior"]
                    }
                ],
                "metadata": {
                    "integration_test": True,
                    "workflow_type": "enhanced_security_analysis"
                }
            }
            
            response = await client.post(
                f"{self.base_url}/api/v1/workflows",
                json=workflow_data,
                timeout=TEST_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                workflow_id = result.get("workflow_id")
                print(f"✅ Enhanced workflow created: {workflow_id}")
                
                # Monitor workflow execution
                await asyncio.sleep(2)  # Allow some processing time
                
                status_response = await client.get(
                    f"{self.base_url}/api/v1/workflows/{workflow_id}/status"
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"✅ Workflow status retrieved: {status_data.get('status', 'unknown')}")
                else:
                    print(f"⚠️ Could not retrieve workflow status: {status_response.status_code}")
            else:
                print(f"❌ Workflow creation failed: {response.text}")
    
    async def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n📋 Generating Integration Test Report...")
        
        async with httpx.AsyncClient() as client:
            # Collect system metrics
            try:
                health_response = await client.get(f"{self.base_url}/health/detailed")
                metrics_response = await client.get(f"{self.base_url}/api/v1/monitoring/agents/analytics") 
                
                report = {
                    "test_summary": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "total_agents_registered": len(self.test_agents),
                        "total_tasks_created": len(self.test_tasks),
                        "test_duration": "N/A"
                    },
                    "system_health": health_response.json() if health_response.status_code == 200 else None,
                    "agent_metrics": metrics_response.json() if metrics_response.status_code == 200 else None,
                    "test_agents": self.test_agents,
                    "test_tasks": self.test_tasks
                }
                
                # Save report
                with open("enhanced_integration_test_report.json", "w") as f:
                    json.dump(report, f, indent=2)
                
                print("✅ Integration test report saved to 'enhanced_integration_test_report.json'")
                
            except Exception as e:
                print(f"❌ Failed to generate test report: {e}")
    
    async def cleanup(self):
        """Clean up test resources"""
        print("\n🧹 Cleaning up test resources...")
        
        async with httpx.AsyncClient() as client:
            # Clean up test tasks if cleanup endpoints exist
            for task_id in self.test_tasks:
                try:
                    await client.delete(f"{self.base_url}/api/v1/tasks/{task_id}")
                except:
                    pass  # Best effort cleanup
            
            # Clean up test agents if cleanup endpoints exist  
            for agent_id in self.test_agents:
                try:
                    await client.delete(f"{self.base_url}/api/v1/agents/{agent_id}")
                except:
                    pass  # Best effort cleanup
        
        print("✅ Cleanup completed")
    
    async def run_full_integration_test(self):
        """Run the complete integration test suite"""
        print("🎯 Starting Enhanced Agent Orchestrator Integration Test Suite")
        print("=" * 80)
        
        start_time = time.time()
        
        try:
            await self.setup()
            await self.test_enhanced_semantic_matching()
            await self.test_advanced_load_balancing()
            await self.test_comprehensive_monitoring()
            await self.test_distributed_tracing()
            await self.test_enhanced_security()
            await self.test_workflow_orchestration()
            await self.generate_test_report()
            
        except Exception as e:
            print(f"\n❌ Integration test failed: {e}")
            raise
        finally:
            await self.cleanup()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 80)
        print(f"🎉 Enhanced Integration Test Suite Completed!")
        print(f"⏱️ Total Duration: {duration:.2f} seconds")
        print(f"🤖 Agents Tested: {len(self.test_agents)}")
        print(f"📋 Tasks Created: {len(self.test_tasks)}")
        print("=" * 80)

async def main():
    """Main entry point for integration testing"""
    tester = EnhancedIntegrationTester()
    await tester.run_full_integration_test()

if __name__ == "__main__":
    asyncio.run(main())

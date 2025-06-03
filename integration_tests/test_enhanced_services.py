#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite for Enhanced Surveillance System
Tests all new AI services and their integration with existing components
"""

import asyncio
import aiohttp
import json
import time
import websockets
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SurveillanceSystemTester:
    def __init__(self):
        self.base_url = "http://localhost"
        self.services = {
            "edge_service": 8001,
            "mqtt_kafka_bridge": 8002,
            "ingest_service": 8003,
            "rag_service": 8004,
            "prompt_service": 8005,
            "rulegen_service": 8006,
            "notifier": 8007,
            "vms_service": 8008,
            "enhanced_prompt_service": 8009,
            "websocket_service": 8010,
            "agent_orchestrator": 8011,
            "rule_builder_service": 8012,
            "advanced_rag_service": 8013,
            "ai_dashboard_service": 8014,
            "voice_interface_service": 8015
        }
        self.test_results = {}

    async def test_service_health(self, service_name: str, port: int) -> bool:
        """Test if a service is healthy and responding"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}:{port}/health", timeout=10) as response:
                    if response.status == 200:
                        logger.info(f"✅ {service_name} is healthy")
                        return True
                    else:
                        logger.error(f"❌ {service_name} health check failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ {service_name} health check error: {str(e)}")
            return False

    async def test_enhanced_prompt_service(self) -> bool:
        """Test enhanced prompt service conversational capabilities"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test conversation initiation
                payload = {
                    "query": "What security events have occurred in the last hour?",
                    "user_id": "test_user_integration"
                }
                
                async with session.post(
                    f"{self.base_url}:8009/conversation/query",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "response" in result and "conversation_id" in result:
                            logger.info("✅ Enhanced prompt service conversation test passed")
                            
                            # Test follow-up questions
                            conv_id = result["conversation_id"]
                            followup_payload = {
                                "conversation_id": conv_id,
                                "query": "Can you provide more details about the most recent event?"
                            }
                            
                            async with session.post(
                                f"{self.base_url}:8009/conversation/continue",
                                json=followup_payload,
                                timeout=30
                            ) as followup_response:
                                if followup_response.status == 200:
                                    logger.info("✅ Enhanced prompt service follow-up test passed")
                                    return True
                                else:
                                    logger.error(f"❌ Follow-up query failed: {followup_response.status}")
                                    return False
                        else:
                            logger.error("❌ Enhanced prompt service missing required fields")
                            return False
                    else:
                        logger.error(f"❌ Enhanced prompt service test failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Enhanced prompt service test error: {str(e)}")
            return False

    async def test_websocket_service(self) -> bool:
        """Test WebSocket bidirectional communication"""
        try:
            uri = "ws://localhost:8010/ws/test_client"
            async with websockets.connect(uri) as websocket:
                # Test sending a command
                command = {
                    "type": "camera_control",
                    "action": "pan",
                    "camera_id": "cam_001",
                    "direction": "left",
                    "speed": 5
                }
                
                await websocket.send(json.dumps(command))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)
                
                if response_data.get("status") == "success":
                    logger.info("✅ WebSocket service command test passed")
                    return True
                else:
                    logger.error(f"❌ WebSocket command failed: {response_data}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ WebSocket service test error: {str(e)}")
            return False

    async def test_agent_orchestrator(self) -> bool:
        """Test agent orchestration capabilities"""
        try:
            async with aiohttp.ClientSession() as session:
                # Register a test agent
                agent_data = {
                    "agent_id": "test_analysis_agent",
                    "agent_type": "analysis",
                    "capabilities": ["video_analysis", "pattern_detection"],
                    "status": "active"
                }
                
                async with session.post(
                    f"{self.base_url}:8011/agents/register",
                    json=agent_data,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        logger.info("✅ Agent registration test passed")
                        
                        # Test task assignment
                        task_data = {
                            "task_type": "video_analysis",
                            "priority": "high",
                            "data": {"video_url": "test_video.mp4"}
                        }
                        
                        async with session.post(
                            f"{self.base_url}:8011/tasks/assign",
                            json=task_data,
                            timeout=10
                        ) as task_response:
                            if task_response.status == 200:
                                logger.info("✅ Agent orchestrator task assignment test passed")
                                return True
                            else:
                                logger.error(f"❌ Task assignment failed: {task_response.status}")
                                return False
                    else:
                        logger.error(f"❌ Agent registration failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Agent orchestrator test error: {str(e)}")
            return False

    async def test_rule_builder_service(self) -> bool:
        """Test interactive rule building capabilities"""
        try:
            async with aiohttp.ClientSession() as session:
                # Start rule building session
                session_data = {
                    "user_id": "test_user",
                    "rule_type": "motion_detection"
                }
                
                async with session.post(
                    f"{self.base_url}:8012/rule-builder/start",
                    json=session_data,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        session_id = result.get("session_id")
                        
                        if session_id:
                            logger.info("✅ Rule builder session creation test passed")
                            
                            # Test step progression
                            step_data = {
                                "session_id": session_id,
                                "user_input": "I want to detect motion in the parking area"
                            }
                            
                            async with session.post(
                                f"{self.base_url}:8012/rule-builder/step",
                                json=step_data,
                                timeout=10
                            ) as step_response:
                                if step_response.status == 200:
                                    logger.info("✅ Rule builder step progression test passed")
                                    return True
                                else:
                                    logger.error(f"❌ Rule builder step failed: {step_response.status}")
                                    return False
                        else:
                            logger.error("❌ Rule builder session ID missing")
                            return False
                    else:
                        logger.error(f"❌ Rule builder session creation failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Rule builder service test error: {str(e)}")
            return False

    async def test_advanced_rag_service(self) -> bool:
        """Test advanced RAG multi-modal capabilities"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test multi-modal analysis
                analysis_data = {
                    "query": "Analyze recent security incidents with video evidence",
                    "include_video": True,
                    "include_images": True,
                    "time_range": "last_24_hours"
                }
                
                async with session.post(
                    f"{self.base_url}:8013/analyze/multi-modal",
                    json=analysis_data,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "analysis" in result and "evidence_chain" in result:
                            logger.info("✅ Advanced RAG multi-modal analysis test passed")
                            return True
                        else:
                            logger.error("❌ Advanced RAG missing required fields")
                            return False
                    else:
                        logger.error(f"❌ Advanced RAG analysis failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Advanced RAG service test error: {str(e)}")
            return False

    async def test_ai_dashboard_service(self) -> bool:
        """Test AI dashboard predictive analytics"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test trend analysis
                async with session.get(
                    f"{self.base_url}:8014/analytics/trends?period=week",
                    timeout=20
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "trends" in result and "predictions" in result:
                            logger.info("✅ AI dashboard trends analysis test passed")
                            
                            # Test anomaly detection
                            async with session.get(
                                f"{self.base_url}:8014/analytics/anomalies",
                                timeout=20
                            ) as anomaly_response:
                                if anomaly_response.status == 200:
                                    logger.info("✅ AI dashboard anomaly detection test passed")
                                    return True
                                else:
                                    logger.error(f"❌ Anomaly detection failed: {anomaly_response.status}")
                                    return False
                        else:
                            logger.error("❌ AI dashboard missing required fields")
                            return False
                    else:
                        logger.error(f"❌ AI dashboard trends failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ AI dashboard service test error: {str(e)}")
            return False

    async def test_voice_interface_service(self) -> bool:
        """Test voice interface capabilities"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test text-to-speech
                tts_data = {
                    "text": "Security alert: Motion detected in zone A",
                    "voice": "nova"
                }
                
                async with session.post(
                    f"{self.base_url}:8015/tts/synthesize",
                    json=tts_data,
                    timeout=15
                ) as response:
                    if response.status == 200:
                        logger.info("✅ Voice interface TTS test passed")
                        
                        # Test voice command processing
                        command_data = {
                            "command": "Show me the latest security alerts"
                        }
                        
                        async with session.post(
                            f"{self.base_url}:8015/voice/process-command",
                            json=command_data,
                            timeout=15
                        ) as cmd_response:
                            if cmd_response.status == 200:
                                logger.info("✅ Voice interface command processing test passed")
                                return True
                            else:
                                logger.error(f"❌ Voice command processing failed: {cmd_response.status}")
                                return False
                    else:
                        logger.error(f"❌ Voice interface TTS failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Voice interface service test error: {str(e)}")
            return False

    async def test_service_integration(self) -> bool:
        """Test integration between enhanced services"""
        try:
            # Test Enhanced Prompt -> Agent Orchestrator -> Advanced RAG flow
            async with aiohttp.ClientSession() as session:
                # 1. Start conversation with enhanced prompt service
                payload = {
                    "query": "I need a comprehensive analysis of today's security events",
                    "user_id": "integration_test_user"
                }
                
                async with session.post(
                    f"{self.base_url}:8009/conversation/query",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        conversation_id = result.get("conversation_id")
                        
                        if conversation_id:
                            logger.info("✅ Service integration: Enhanced prompt initiated")
                            
                            # 2. Test if analysis triggers agent orchestration
                            # This would normally be automatic, but we'll simulate
                            task_data = {
                                "task_type": "comprehensive_analysis",
                                "priority": "high",
                                "conversation_id": conversation_id,
                                "data": {"analysis_scope": "today"}
                            }
                            
                            async with session.post(
                                f"{self.base_url}:8011/tasks/assign",
                                json=task_data,
                                timeout=10
                            ) as task_response:
                                if task_response.status == 200:
                                    logger.info("✅ Service integration: Agent orchestration triggered")
                                    return True
                                else:
                                    logger.error(f"❌ Integration: Agent task failed: {task_response.status}")
                                    return False
                        else:
                            logger.error("❌ Integration: No conversation ID returned")
                            return False
                    else:
                        logger.error(f"❌ Integration: Enhanced prompt failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Service integration test error: {str(e)}")
            return False

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        logger.info("🚀 Starting comprehensive surveillance system integration tests...")
        
        # Test service health
        logger.info("📊 Testing service health...")
        health_results = {}
        for service_name, port in self.services.items():
            health_results[service_name] = await self.test_service_health(service_name, port)
        
        # Test enhanced services functionality
        logger.info("🧠 Testing enhanced AI services...")
        functionality_tests = {
            "enhanced_prompt_service": await self.test_enhanced_prompt_service(),
            "websocket_service": await self.test_websocket_service(),
            "agent_orchestrator": await self.test_agent_orchestrator(),
            "rule_builder_service": await self.test_rule_builder_service(),
            "advanced_rag_service": await self.test_advanced_rag_service(),
            "ai_dashboard_service": await self.test_ai_dashboard_service(),
            "voice_interface_service": await self.test_voice_interface_service()
        }
        
        # Test service integration
        logger.info("🔗 Testing service integration...")
        integration_test = await self.test_service_integration()
        
        # Compile results
        results = {
            "timestamp": time.time(),
            "health_checks": health_results,
            "functionality_tests": functionality_tests,
            "integration_test": integration_test,
            "summary": {
                "total_services": len(self.services),
                "healthy_services": sum(health_results.values()),
                "passing_functionality": sum(functionality_tests.values()),
                "integration_passed": integration_test
            }
        }
        
        # Log summary
        logger.info(f"📈 Test Results Summary:")
        logger.info(f"   Services Healthy: {results['summary']['healthy_services']}/{results['summary']['total_services']}")
        logger.info(f"   Functionality Tests Passed: {results['summary']['passing_functionality']}/{len(functionality_tests)}")
        logger.info(f"   Integration Test: {'✅ PASSED' if integration_test else '❌ FAILED'}")
        
        return results

async def main():
    """Main test execution"""
    tester = SurveillanceSystemTester()
    results = await tester.run_all_tests()
    
    # Save results to file
    with open("integration_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info("💾 Test results saved to integration_test_results.json")
    
    # Return exit code based on results
    all_passed = (
        results['summary']['healthy_services'] == results['summary']['total_services'] and
        results['summary']['passing_functionality'] == len(results['functionality_tests']) and
        results['integration_test']
    )
    
    if all_passed:
        logger.info("🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.error("💥 SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

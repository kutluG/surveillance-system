#!/usr/bin/env python3
"""
Integration test script for Voice Interface Service with Speaker Verification
Tests all endpoints and functionality while services are running.
"""

import requests
import base64
import json
import time
from typing import Dict, Any

class VoiceServiceTester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results = []
        
    def log_test(self, test_name: str, success: bool, details: Dict[str, Any] = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details or {},
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            success = response.status_code == 200
            data = response.json() if success else None
            self.log_test("Health Endpoint", success, {
                "status_code": response.status_code,
                "response": data
            })
            return success
        except Exception as e:
            self.log_test("Health Endpoint", False, {"error": str(e)})
            return False
    
    def test_enrollment_status(self):
        """Test the enrollment status endpoint"""
        try:
            response = requests.get(f"{self.base_url}/voice/enrollment/status", timeout=5)
            success = response.status_code == 200
            data = response.json() if success else None
            self.log_test("Enrollment Status", success, {
                "status_code": response.status_code,
                "response": data
            })
            return success
        except Exception as e:
            self.log_test("Enrollment Status", False, {"error": str(e)})
            return False
    
    def test_voice_command(self, transcript: str, expected_success: bool = True):
        """Test voice command processing"""
        try:
            # Create fake audio data
            test_audio = f"audio_for_{transcript.replace(' ', '_')}".encode()
            audio_base64 = base64.b64encode(test_audio).decode('utf-8')
            
            data = {
                'transcript': transcript,
                'audio_clip': audio_base64
            }
            
            response = requests.post(f"{self.base_url}/voice/command", data=data, timeout=10)
            success = response.status_code == 200
            
            if success:
                result_data = response.json()
                command_success = result_data.get('status') == 'success'
                if expected_success:
                    success = command_success
                else:
                    # For invalid commands, we expect success=False in command_result
                    success = not result_data.get('command_result', {}).get('success', True)
            
            self.log_test(f"Voice Command: '{transcript}'", success, {
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else response.text,
                "expected_success": expected_success
            })
            return success
        except Exception as e:
            self.log_test(f"Voice Command: '{transcript}'", False, {"error": str(e)})
            return False
    
    def test_api_gateway_connectivity(self):
        """Test connectivity to API Gateway"""
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            success = response.status_code == 200
            self.log_test("API Gateway Connectivity", success, {
                "status_code": response.status_code,
                "api_gateway_running": success
            })
            return success
        except Exception as e:
            self.log_test("API Gateway Connectivity", False, {"error": str(e)})
            return False
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🔊 Voice Interface Service - Integration Test Suite")
        print("=" * 60)
        
        # Basic connectivity tests
        print("\n📡 Connectivity Tests:")
        self.test_health_endpoint()
        self.test_enrollment_status()
        self.test_api_gateway_connectivity()
        
        # Voice command tests
        print("\n🎤 Voice Command Tests:")
        
        # Valid camera commands
        self.test_voice_command("disable camera 1")
        self.test_voice_command("enable camera 2")
        self.test_voice_command("disable camera 10")
        
        # Valid alert threshold commands
        self.test_voice_command("set alert threshold to 0.8")
        self.test_voice_command("set alert threshold to 0.5")
        self.test_voice_command("set alert threshold to 0.9")
        
        # Invalid commands (should be handled gracefully)
        print("\n🚫 Invalid Command Tests:")
        self.test_voice_command("delete all files", expected_success=False)
        self.test_voice_command("shutdown system", expected_success=False)
        self.test_voice_command("random nonsense", expected_success=False)
        
        # Edge cases
        print("\n🔍 Edge Case Tests:")
        self.test_voice_command("enable camera")  # Missing ID
        self.test_voice_command("set alert threshold")  # Missing value
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.results:
                if not result['success']:
                    print(f"  - {result['test']}")
                    if result['details'].get('error'):
                        print(f"    Error: {result['details']['error']}")
        
        print("\n🔊 Voice Interface Service Status:")
        health_test = next((r for r in self.results if r['test'] == 'Health Endpoint'), None)
        if health_test and health_test['success']:
            health_data = health_test['details']['response']
            print(f"  Mode: {health_data.get('mode', 'unknown')}")
            print(f"  Speaker Verification: {'✅' if health_data.get('services', {}).get('speaker_verification') else '🔄'}")
            print(f"  Enrollment: {'✅' if health_data.get('services', {}).get('enrollment') else '🔄'}")
            print(f"  API Gateway Connected: {'✅' if health_data.get('services', {}).get('api_gateway_connected') else '❌'}")

if __name__ == "__main__":
    tester = VoiceServiceTester()
    tester.run_all_tests()

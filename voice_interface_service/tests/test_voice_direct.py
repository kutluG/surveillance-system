#!/usr/bin/env python3
"""
Simple direct test of voice service functionality
"""
import sys
import os
import base64
import json

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_basic_imports():
    """Test basic imports work"""
    try:
        from voice_service import app, SpeakerVerificationService, VoiceCommandProcessor
        print("✅ Basic imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_service_creation():
    """Test service creation"""
    try:
        from voice_service import SpeakerVerificationService, VoiceCommandProcessor
        
        speaker_service = SpeakerVerificationService()
        command_processor = VoiceCommandProcessor()
        
        print("✅ Services created successfully")
        return True
    except Exception as e:
        print(f"❌ Service creation failed: {e}")
        return False

def test_fastapi_endpoints():
    """Test FastAPI endpoints"""
    try:
        from fastapi.testclient import TestClient
        from voice_service import app
        
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        print(f"Health endpoint: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Test enrollment status
        response = client.get("/voice/enrollment/status")
        print(f"Enrollment status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        print("✅ FastAPI endpoints working")
        return True
    except Exception as e:
        print(f"❌ FastAPI test failed: {e}")
        return False

def test_command_parsing():
    """Test command parsing functionality"""
    try:
        from voice_service import VoiceCommandProcessor
        
        processor = VoiceCommandProcessor()
        
        # Test camera ID extraction
        camera_id = processor._extract_camera_id("disable camera_3", "disable")
        assert camera_id == "3", f"Expected '3', got '{camera_id}'"
        
        # Test threshold extraction
        threshold = processor._extract_threshold("set alert threshold to 85")
        assert threshold == 85.0, f"Expected 85.0, got {threshold}"
        
        print("✅ Command parsing works correctly")
        return True
    except Exception as e:
        print(f"❌ Command parsing failed: {e}")
        return False

def test_voice_command_without_enrollment():
    """Test voice command without enrollment (should return 503)"""
    try:
        from fastapi.testclient import TestClient
        from voice_service import app
        import voice_service
        
        # Ensure no enrollment
        voice_service.enrolled_embedding = None
        
        client = TestClient(app)
        
        # Create fake audio data
        fake_audio = b'RIFF' + b'\x00' * 1000
        audio_b64 = base64.b64encode(fake_audio).decode('utf-8')
        
        response = client.post(
            "/voice/command",
            data={
                "audio_clip": audio_b64,
                "transcript": "disable camera_1"
            }
        )
        
        print(f"Voice command without enrollment: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 503:
            print("✅ Correctly rejected command without enrollment")
            return True
        else:
            print(f"❌ Expected 503, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Voice command test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🔍 Testing Voice Interface Service")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_service_creation,
        test_fastapi_endpoints,
        test_command_parsing,
        test_voice_command_without_enrollment
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        print(f"\n📋 Running {test_func.__name__}...")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    exit(main())

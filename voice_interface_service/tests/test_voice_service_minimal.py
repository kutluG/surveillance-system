"""
Minimal test suite for Voice Service with Speaker Verification
This file tests the core functionality to ensure basic operations work.
"""

import pytest
import numpy as np
import base64
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Import the voice service
from voice_service import app, SpeakerVerificationService, VoiceCommandProcessor

class TestVoiceServiceBasic:
    """Basic tests for voice service components"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
      @pytest.fixture 
    def sample_audio_data(self):
        """Generate sample audio data"""
        return b'RIFF' + b'\x00' * 32000  # Simple mock audio data
    
    def test_health_endpoint(self, client):
        """Test basic health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data  # Changed from components to services
    
    def test_enrollment_status_endpoint(self, client):
        """Test enrollment status endpoint"""
        response = client.get("/voice/enrollment/status")
        assert response.status_code in [200, 503]  # Either enrolled or not enrolled
        data = response.json()
        assert "enrolled" in data  # Changed from enrollment_status to enrolled
    
    @patch('voice_service.speaker_service')
    def test_speaker_verification_service_creation(self, mock_service):
        """Test that speaker verification service can be created"""
        service = SpeakerVerificationService()
        assert service is not None
        
    def test_voice_command_processor_creation(self):
        """Test that voice command processor can be created"""
        processor = VoiceCommandProcessor()
        assert processor is not None
        
    @patch('voice_service.speaker_service')  
    def test_voice_command_no_enrollment(self, mock_service, client, sample_audio_data):
        """Test voice command without enrollment returns 503"""
        # Ensure no global enrollment
        import voice_service
        voice_service.enrolled_embedding = None
        
        audio_b64 = base64.b64encode(sample_audio_data).decode('utf-8')
        response = client.post(
            "/voice/command",
            data={
                "audio_clip": audio_b64,
                "transcript": "disable camera_1"
            }
        )
          assert response.status_code == 503
        data = response.json()
        # The detail is a string, not a dict in this case
        assert "Speaker enrollment not available" in str(data["detail"])

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

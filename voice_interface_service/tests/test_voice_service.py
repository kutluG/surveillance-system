"""
Tests for Enhanced Voice Interface Service with Speaker Verification
"""

import pytest
import asyncio
import base64
import json
import os
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Mock pyannote.audio before importing voice_service
with patch.dict('sys.modules', {
    'pyannote': MagicMock(),
    'pyannote.audio': MagicMock(),
    'sklearn': MagicMock(),
    'sklearn.metrics': MagicMock(),
    'sklearn.metrics.pairwise': MagicMock(),
}):
    # Import the voice service after mocking dependencies
    from voice_service import (
        app, 
        SpeakerVerificationService, 
        VoiceCommandProcessor,
        verify_speaker_dependency,
        load_enrollment_embedding,
        enrolled_embedding,
        speaker_service
    )

# Test constants
SIMILARITY_THRESHOLD = 0.75

# Global fixtures
@pytest.fixture
def sample_audio_data():
    """Generate sample WAV audio data"""
    # Create a simple WAV file in memory
    import wave
    import io
    
    # Generate 1 second of sine wave at 16kHz
    sample_rate = 16000
    duration = 1.0
    frequency = 440  # A4 note
    
    samples = np.sin(2 * np.pi * frequency * np.linspace(0, duration, int(sample_rate * duration)))
    samples = (samples * 32767).astype(np.int16)
    
    # Create WAV data
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    
    return wav_buffer.getvalue()

@pytest.fixture
def matching_speaker_embedding():
    """Embedding that should match enrolled speaker"""
    # Create a consistent embedding vector
    np.random.seed(42)
    return np.random.rand(512)  # Typical embedding size

@pytest.fixture
def non_matching_speaker_embedding():
    """Embedding that should NOT match enrolled speaker"""
    # Create a different embedding vector
    np.random.seed(123)
    return np.random.rand(512)

class TestSpeakerVerification:
    """Tests for speaker verification functionality"""
    
    @pytest.fixture
    def mock_speaker_service(self):
        """Mock speaker verification service"""
        service = SpeakerVerificationService()
        service.model = MagicMock()
        service.inference = MagicMock()
        return service
    
    @patch('tempfile.NamedTemporaryFile')
    def test_extract_embedding(self, mock_temp_file, mock_speaker_service, sample_audio_data):
        """Test speaker embedding extraction"""
        # Mock temporary file
        mock_file = MagicMock()
        mock_file.name = "test_audio.wav"
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        # Mock the inference to return a test embedding
        test_embedding = np.random.rand(512)
        mock_speaker_service.inference.return_value = test_embedding
          # Test embedding extraction with proper mocking
        with patch('voice_service.os.unlink'):
            result = mock_speaker_service.extract_embedding(sample_audio_data)
            assert isinstance(result, np.ndarray)
            assert result.shape == test_embedding.shape
            np.testing.assert_array_equal(result, test_embedding)
    
    def test_verify_speaker_match(self, mock_speaker_service, matching_speaker_embedding):
        """Test speaker verification with matching speaker"""
        enrolled = matching_speaker_embedding
        test = matching_speaker_embedding + np.random.normal(0, 0.01, enrolled.shape)  # Add small noise
        
        similarity = mock_speaker_service.verify_speaker(test, enrolled)
        
        assert isinstance(similarity, float)
        assert similarity > SIMILARITY_THRESHOLD  # Should be above threshold
    
    def test_verify_speaker_no_match(self, mock_speaker_service, matching_speaker_embedding, non_matching_speaker_embedding):
        """Test speaker verification with non-matching speaker"""
        enrolled = matching_speaker_embedding
        test = non_matching_speaker_embedding
        
        # Mock cosine_similarity to return low similarity for different embeddings
        with patch('voice_service.cosine_similarity') as mock_cosine:
            mock_cosine.return_value = [[0.3]]  # Below threshold
            similarity = mock_speaker_service.verify_speaker(test, enrolled)
        
        assert isinstance(similarity, float)
        # The mock should return 0.3 which is below the threshold
        assert similarity == 0.3

class TestVoiceCommandProcessor:
    """Tests for voice command processing"""
    
    @pytest.fixture
    def command_processor(self):
        """Create command processor with mocked HTTP client"""
        processor = VoiceCommandProcessor()
        processor.http_client = AsyncMock()
        return processor
    
    @pytest.mark.asyncio
    async def test_disable_camera_command(self, command_processor):
        """Test camera disable command"""
        # Mock successful API response
        command_processor.http_client.post.return_value.status_code = 200
        
        result = await command_processor.process_command("disable camera_3")
        
        assert result.success is True
        assert result.action_taken == "disabled_camera_3"
        assert result.details["camera_id"] == "3"
        
        # Verify API call
        command_processor.http_client.post.assert_called_once_with(
            "http://localhost:8000/api/camera/3/disable",
            timeout=10.0
        )
    
    @pytest.mark.asyncio
    async def test_enable_camera_command(self, command_processor):
        """Test camera enable command"""
        # Mock successful API response
        command_processor.http_client.post.return_value.status_code = 200
        
        result = await command_processor.process_command("enable camera 12")
        
        assert result.success is True
        assert result.action_taken == "enabled_camera_12"
        assert result.details["camera_id"] == "12"
        
        # Verify API call
        command_processor.http_client.post.assert_called_once_with(
            "http://localhost:8000/api/camera/12/enable",
            timeout=10.0
        )
    
    @pytest.mark.asyncio
    async def test_set_alert_threshold_command(self, command_processor):
        """Test alert threshold setting command"""
        # Mock successful API response
        command_processor.http_client.post.return_value.status_code = 200
        
        result = await command_processor.process_command("set alert threshold to 85")
        
        assert result.success is True
        assert result.action_taken == "set_alert_threshold_85.0"
        assert result.details["threshold"] == 85.0
        
        # Verify API call
        command_processor.http_client.post.assert_called_once_with(
            "http://localhost:8000/api/config/alert_threshold",
            json={"value": 85.0},
            timeout=10.0
        )
    
    @pytest.mark.asyncio
    async def test_unknown_command(self, command_processor):
        """Test handling of unknown commands"""
        result = await command_processor.process_command("play music")
        
        assert result.success is False
        assert result.action_taken == "none"
        assert "unknown_command" in result.details["error"]
        assert "supported_commands" in result.details
    
    def test_extract_camera_id(self, command_processor):
        """Test camera ID extraction from various formats"""
        assert command_processor._extract_camera_id("disable camera_3", "disable") == "3"
        assert command_processor._extract_camera_id("disable camera 12", "disable") == "12"
        assert command_processor._extract_camera_id("enable camera_test_cam", "enable") == "test_cam"
        assert command_processor._extract_camera_id("invalid command", "disable") is None
    
    def test_extract_threshold(self, command_processor):
        """Test threshold extraction from commands"""
        assert command_processor._extract_threshold("set alert threshold to 75") == 75.0
        assert command_processor._extract_threshold("set alert threshold to 0.8") == 0.8
        assert command_processor._extract_threshold("set alert threshold to invalid") is None

class TestVoiceServiceAPI:
    """Integration tests for the voice service API"""
    
    @pytest.fixture
    def client(self):
        """Test client for the FastAPI app"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_enrollment_setup(self, sample_audio_data, matching_speaker_embedding):
        """Setup mock enrollment for testing"""
        global enrolled_embedding
        from voice_service import SpeakerEmbedding
        
        # Mock enrolled embedding
        enrolled_embedding = SpeakerEmbedding(
            vector=matching_speaker_embedding,
            user_id="test_user",
            enrolled_at="test_time"
        )
        
        # Mock speaker service
        with patch('voice_service.speaker_service') as mock_service:        mock_service.extract_embedding.return_value = matching_speaker_embedding
        mock_service.verify_speaker.return_value = 0.85  # Above threshold
        yield mock_service

    @patch('voice_service.command_processor')
    def test_voice_command_success_matching_speaker(self, mock_processor, client, mock_enrollment_setup, sample_audio_data):
        """Test successful voice command with matching speaker"""
        # Set global enrollment
        global enrolled_embedding
        from voice_service import SpeakerEmbedding
        enrolled_embedding = SpeakerEmbedding(
            vector=np.random.rand(512),
            user_id="test_user",
            enrolled_at="test_time"
        )
        
        # Mock command processor response
        from voice_service import CommandResult
        mock_processor.process_command.return_value = CommandResult(
            success=True,
            command="disable camera_3",
            action_taken="disabled_camera_3",
            details={"camera_id": "3", "status": "disabled"}
        )
          # Prepare request data
        audio_b64 = base64.b64encode(sample_audio_data).decode('utf-8')
        
        response = client.post(
            "/voice/command",
            data={
                "audio_clip": audio_b64,
                "transcript": "disable camera_3"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["executed_command"] == "disable camera_3"
        assert data["speaker_similarity"] == 0.85
        assert data["command_result"]["success"] is True
        assert data["command_result"]["action_taken"] == "disabled_camera_3"
    
    def test_voice_command_rejected_non_matching_speaker(self, client, sample_audio_data, non_matching_speaker_embedding):
        """Test voice command rejection with non-matching speaker"""
        global enrolled_embedding
        from voice_service import SpeakerEmbedding
        
        # Setup enrolled embedding
        enrolled_embedding = SpeakerEmbedding(
            vector=np.random.rand(512),
            user_id="test_user", 
            enrolled_at="test_time"
        )
        
        # Mock speaker service to return low similarity
        with patch('voice_service.speaker_service') as mock_service:
            mock_service.extract_embedding.return_value = non_matching_speaker_embedding
            mock_service.verify_speaker.return_value = 0.3  # Below threshold
            
            audio_b64 = base64.b64encode(sample_audio_data).decode('utf-8')
            response = client.post(
                "/voice/command",
                data={
                    "audio_clip": audio_b64,
                    "transcript": "disable camera_3"
                }
            )
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"]["error"] == "speaker_not_recognized"
    
    def test_voice_command_invalid_audio(self, client):
        """Test voice command with invalid audio data"""
        # Mock enrollment to avoid 503 error
        global enrolled_embedding
        from voice_service import SpeakerEmbedding
        
        enrolled_embedding = SpeakerEmbedding(
            vector=np.random.rand(512),
            user_id="test_user",
            enrolled_at="test_time"
        )
        
        response = client.post(
            "/voice/command",
            data={
                "audio_clip": "invalid_base64_data",
                "transcript": "disable camera_3"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid base64 audio data" in response.json()["detail"]
    
    def test_enrollment_status_endpoint(self, client):
        """Test enrollment status endpoint"""
        response = client.get("/voice/enrollment/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "enrolled" in data
        assert "enrollment_file_exists" in data
        assert "model_loaded" in data
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "services" in data
        assert "speaker_verification" in data["services"]
        assert "enrollment" in data["services"]
        assert "thread_pool" in data["services"]

@pytest.mark.asyncio
class TestAsyncFunctions:
    """Tests for async functions"""
    
    @patch('voice_service.os.path.exists')
    @patch('voice_service.speaker_service')
    async def test_load_enrollment_embedding_success(self, mock_service, mock_exists, sample_audio_data):
        """Test successful enrollment loading"""
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock file reading
        with patch('builtins.open', mock_open(read_data=sample_audio_data)):
            # Mock embedding extraction
            test_embedding = np.random.rand(512)
            mock_service.extract_embedding.return_value = test_embedding
            
            # Mock Redis
            with patch('voice_service.get_redis_client') as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis.return_value = mock_redis_client
                
                # Test loading
                result = await load_enrollment_embedding()
                
                assert result is not None
                assert isinstance(result.vector, np.ndarray)
                assert result.user_id == "authorized_user"
                
                # Verify Redis storage
                mock_redis_client.set.assert_called_once()
    
    @patch('voice_service.os.path.exists')
    async def test_load_enrollment_embedding_file_not_found(self, mock_exists):
        """Test enrollment loading when file doesn't exist"""
        mock_exists.return_value = False
        
        result = await load_enrollment_embedding()
        
        assert result is None

def mock_open(read_data=b""):
    """Helper to mock file open with binary data"""
    from unittest.mock import mock_open as base_mock_open
    return base_mock_open(read_data=read_data)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

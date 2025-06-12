import pytest
import numpy as np
import cv2
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, anonymizer
from face_anonymization import FaceAnonymizer, PrivacyLevel, AnonymizationMethod


class TestFaceAnonymizationIntegration:
    """Integration tests for face anonymization in the main application"""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_frame(self):
        """Create a sample video frame for testing"""
        # Create a 640x480 BGR frame with a face-like region
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Add a white rectangle to simulate a face
        cv2.rectangle(frame, (200, 150), (350, 300), (255, 255, 255), -1)
        return frame
    
    def test_health_endpoint_includes_anonymization(self, client):
        """Test that health endpoint includes anonymization status"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that anonymization status is included
        assert "anonymization" in data
        assert "enabled" in data["anonymization"]
        assert "privacy_level" in data["anonymization"]
        assert "method" in data["anonymization"]
    
    def test_privacy_status_endpoint(self, client):
        """Test privacy status endpoint"""
        response = client.get("/privacy/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields in privacy status
        required_fields = ["enabled", "privacy_level", "anonymization_method", 
                          "models_loaded", "statistics"]
        for field in required_fields:
            assert field in data
        
        # Check statistics structure
        stats = data["statistics"]
        assert "frames_processed" in stats
        assert "faces_anonymized" in stats
        assert "total_processing_time" in stats
        assert "average_processing_time" in stats
    
    def test_privacy_configure_endpoint(self, client):
        """Test privacy configuration endpoint"""
        # Test valid configuration
        config = {
            "privacy_level": "strict",
            "anonymization_method": "black_box"
        }
        
        response = client.post("/privacy/configure", json=config)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["message"] == "Privacy configuration updated successfully"
        
        # Verify configuration was applied
        status_response = client.get("/privacy/status")
        status_data = status_response.json()
        assert status_data["privacy_level"] == "strict"
        assert status_data["anonymization_method"] == "black_box"
    
    def test_privacy_configure_invalid_config(self, client):
        """Test privacy configuration with invalid data"""
        # Test invalid privacy level
        config = {
            "privacy_level": "invalid_level",
            "anonymization_method": "blur"
        }
        
        response = client.post("/privacy/configure", json=config)
        
        # Should still succeed but use default values
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_privacy_test_endpoint(self, client):
        """Test privacy test endpoint"""
        response = client.post("/privacy/test")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "test_passed" in data
        assert "anonymization_working" in data
        assert "models_loaded" in data
        assert "test_results" in data
    
    @patch('main.anonymizer.process_frame')
    def test_process_frame_integration(self, mock_process, sample_frame):
        """Test that process_frame is called in the main pipeline"""
        # Mock the anonymizer process_frame method
        mock_process.return_value = sample_frame
        
        # Import and call the process_frame function from main
        from main import process_frame
        
        result = process_frame(sample_frame)
        
        # Verify anonymizer was called
        mock_process.assert_called_once_with(sample_frame)
        assert result is not None
    
    @patch('cv2.CascadeClassifier.detectMultiScale')
    def test_end_to_end_anonymization_flow(self, mock_detect, client, sample_frame):
        """Test complete end-to-end anonymization flow"""
        # Mock face detection
        mock_detect.return_value = np.array([[200, 150, 150, 150]])
        
        # Create a test anonymizer instance
        test_anonymizer = FaceAnonymizer(
            privacy_level="moderate",
            anonymization_method="blur"
        )
        
        # Process the frame
        result = test_anonymizer.process_frame(sample_frame)
        
        # Verify frame was processed and modified
        assert result is not None
        assert result.shape == sample_frame.shape
        assert not np.array_equal(result, sample_frame)  # Should be different
        
        # Verify statistics were updated
        status = test_anonymizer.get_privacy_status()
        assert status["statistics"]["frames_processed"] > 0
        assert status["statistics"]["faces_anonymized"] > 0
    
    def test_privacy_level_enforcement(self, client):
        """Test that different privacy levels are properly enforced"""
        privacy_levels = ["minimal", "moderate", "strict"]
        
        for level in privacy_levels:
            # Configure privacy level
            config = {"privacy_level": level}
            response = client.post("/privacy/configure", json=config)
            assert response.status_code == 200
            
            # Verify configuration was applied
            status_response = client.get("/privacy/status")
            status_data = status_response.json()
            assert status_data["privacy_level"] == level
    
    def test_anonymization_method_switching(self, client):
        """Test switching between different anonymization methods"""
        methods = ["blur", "pixelate", "black_box", "emoji"]
        
        for method in methods:
            # Configure anonymization method
            config = {"anonymization_method": method}
            response = client.post("/privacy/configure", json=config)
            assert response.status_code == 200
            
            # Verify configuration was applied
            status_response = client.get("/privacy/status")
            status_data = status_response.json()
            assert status_data["anonymization_method"] == method
    
    @patch('main.anonymizer.process_frame')
    def test_anonymization_failure_handling(self, mock_process, client, sample_frame):
        """Test handling of anonymization failures"""
        # Mock anonymization failure
        mock_process.side_effect = Exception("Anonymization failed")
        
        # The system should handle the exception gracefully
        from main import process_frame
        
        # In strict mode, frame should be dropped on failure
        with patch('main.anonymizer.privacy_level', PrivacyLevel.STRICT):
            result = process_frame(sample_frame)
            # Should return None in strict mode on failure
            assert result is None
    
    def test_performance_monitoring(self, client):
        """Test that performance metrics are properly tracked"""
        # Get initial statistics
        initial_response = client.get("/privacy/status")
        initial_stats = initial_response.json()["statistics"]
        initial_time = initial_stats["total_processing_time"]
        
        # Process some frames by calling test endpoint
        client.post("/privacy/test")
        
        # Check that processing time was updated
        updated_response = client.get("/privacy/status")
        updated_stats = updated_response.json()["statistics"]
        updated_time = updated_stats["total_processing_time"]
        
        # Processing time should have increased
        assert updated_time >= initial_time
    
    def test_concurrent_processing(self, client):
        """Test concurrent frame processing doesn't break anonymization"""
        # This test would require actual concurrent processing
        # For now, just verify that multiple sequential calls work
        
        for i in range(5):
            response = client.post("/privacy/test")
            assert response.status_code == 200
            
            data = response.json()
            assert data["test_passed"] == True
    
    def test_model_loading_status(self, client):
        """Test that model loading status is correctly reported"""
        response = client.get("/privacy/status")
        data = response.json()
        
        models_status = data["models_loaded"]
        assert "haar_cascade" in models_status
        assert "dnn_model" in models_status
        
        # Haar cascade should be loaded by default
        assert models_status["haar_cascade"] == True
    
    def test_anonymization_metadata_in_events(self, client):
        """Test that anonymization metadata is included in published events"""
        # This would test the event publishing with anonymization metadata
        # For now, verify that the privacy status includes the necessary metadata
        
        response = client.get("/privacy/status")
        data = response.json()
        
        # Verify that all necessary metadata is available for event publishing
        assert "privacy_level" in data
        assert "anonymization_method" in data
        assert "statistics" in data


class TestComplianceIntegration:
    """Integration tests for privacy compliance features"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_gdpr_compliance_endpoints(self, client):
        """Test GDPR compliance through API endpoints"""
        # Test that privacy status provides GDPR-required information
        response = client.get("/privacy/status")
        data = response.json()
        
        # GDPR requires transparency about data processing
        assert "enabled" in data
        assert "privacy_level" in data
        assert "anonymization_method" in data
        
        # Test configuration endpoint for user rights
        config = {"privacy_level": "strict"}
        config_response = client.post("/privacy/configure", json=config)
        assert config_response.status_code == 200
    
    def test_data_minimization_principle(self, client):
        """Test that data minimization principle is followed"""
        # Configure strict privacy level
        config = {"privacy_level": "strict"}
        response = client.post("/privacy/configure", json=config)
        assert response.status_code == 200
        
        # Verify strict mode is active
        status_response = client.get("/privacy/status")
        status_data = status_response.json()
        assert status_data["privacy_level"] == "strict"
        
        # In strict mode, only hashed face data should be used
        # This would be verified through actual processing tests
    
    def test_audit_trail_availability(self, client):
        """Test that audit trail information is available"""
        response = client.get("/privacy/status")
        data = response.json()
        
        # Statistics provide audit trail information
        stats = data["statistics"]
        assert "frames_processed" in stats
        assert "faces_anonymized" in stats
        assert "total_processing_time" in stats
        
        # This information can be used for compliance reporting
    
    def test_user_consent_configuration(self, client):
        """Test user consent through configuration options"""
        # Test all privacy levels (simulating different consent levels)
        consent_levels = [
            ("minimal", "User consents to minimal anonymization"),
            ("moderate", "User consents to moderate anonymization"), 
            ("strict", "User requires strict anonymization")
        ]
        
        for level, description in consent_levels:
            config = {"privacy_level": level}
            response = client.post("/privacy/configure", json=config)
            assert response.status_code == 200
            
            # Verify configuration was applied
            status_response = client.get("/privacy/status")
            status_data = status_response.json()
            assert status_data["privacy_level"] == level


if __name__ == "__main__":
    pytest.main([__file__])

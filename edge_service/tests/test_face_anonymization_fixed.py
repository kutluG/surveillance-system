# Test file for Face Anonymization Module with correct API
import numpy as np
import cv2
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from face_anonymization import (
    FaceAnonymizer, AnonymizationConfig, FaceDetection,
    PrivacyLevel, AnonymizationMethod,
    get_strict_config, get_moderate_config, get_minimal_config
)

class TestFaceAnonymizer:
    """Test suite for FaceAnonymizer class"""
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample BGR image for testing"""
        # Create a 300x300 BGR image with a white rectangle (simulating a face region)
        img = np.zeros((300, 300, 3), dtype=np.uint8)
        # Add a white rectangle at (50, 50, 100, 100) to simulate a face
        cv2.rectangle(img, (50, 50), (150, 150), (255, 255, 255), -1)
        return img
    
    @pytest.fixture
    def face_detections(self):
        """Sample face detections for testing"""
        return [FaceDetection(x=50, y=50, width=100, height=100, confidence=0.9)]
    
    @pytest.fixture
    def anonymizer(self):
        """Create FaceAnonymizer instance for testing"""
        config = AnonymizationConfig()
        return FaceAnonymizer(config)
    
    @pytest.fixture 
    def strict_anonymizer(self):
        """Create strict privacy FaceAnonymizer"""
        return FaceAnonymizer(get_strict_config())
    
    @pytest.fixture
    def moderate_anonymizer(self):
        """Create moderate privacy FaceAnonymizer"""
        return FaceAnonymizer(get_moderate_config())
    
    @pytest.fixture
    def minimal_anonymizer(self):
        """Create minimal privacy FaceAnonymizer"""
        return FaceAnonymizer(get_minimal_config())
    
    def test_anonymizer_initialization(self, anonymizer):
        """Test proper initialization of FaceAnonymizer"""
        assert anonymizer.config.privacy_level == PrivacyLevel.STRICT
        assert anonymizer.config.method == AnonymizationMethod.BLUR
        assert anonymizer.face_cascade is not None
    
    def test_privacy_level_configs(self):
        """Test different privacy level configurations"""
        strict_config = get_strict_config()
        assert strict_config.privacy_level == PrivacyLevel.STRICT
        assert strict_config.hash_embeddings_only == False
        assert strict_config.store_face_hashes == False
        
        moderate_config = get_moderate_config()
        assert moderate_config.privacy_level == PrivacyLevel.MODERATE
        assert moderate_config.store_face_hashes == True
        
        minimal_config = get_minimal_config()
        assert minimal_config.privacy_level == PrivacyLevel.MINIMAL
        assert minimal_config.blur_factor == 10
    
    def test_anonymization_method_configs(self):
        """Test different anonymization method configurations"""
        # Test blur method
        config = AnonymizationConfig(method=AnonymizationMethod.BLUR)
        anonymizer = FaceAnonymizer(config)
        assert anonymizer.config.method == AnonymizationMethod.BLUR
        
        # Test pixelate method  
        config = AnonymizationConfig(method=AnonymizationMethod.PIXELATE)
        anonymizer = FaceAnonymizer(config)
        assert anonymizer.config.method == AnonymizationMethod.PIXELATE
        
        # Test black box method
        config = AnonymizationConfig(method=AnonymizationMethod.BLACK_BOX)
        anonymizer = FaceAnonymizer(config)
        assert anonymizer.config.method == AnonymizationMethod.BLACK_BOX
    
    def test_blur_anonymization(self, anonymizer, sample_image):
        """Test blur anonymization method"""
        anonymizer.config.method = AnonymizationMethod.BLUR
        result, detected_faces = anonymizer.anonymize_frame(sample_image)
        
        # Check that image dimensions are preserved
        assert result.shape == sample_image.shape
        
        # Should detect faces (though may not in test image)
        assert isinstance(detected_faces, list)
    
    def test_pixelate_anonymization(self, moderate_anonymizer, sample_image):
        """Test pixelate anonymization method"""
        moderate_anonymizer.config.method = AnonymizationMethod.PIXELATE
        result, detected_faces = moderate_anonymizer.anonymize_frame(sample_image)
        
        # Check that image dimensions are preserved
        assert result.shape == sample_image.shape
        assert isinstance(detected_faces, list)
    
    def test_black_box_anonymization(self, strict_anonymizer, sample_image):
        """Test black box anonymization method"""
        strict_anonymizer.config.method = AnonymizationMethod.BLACK_BOX
        result, detected_faces = strict_anonymizer.anonymize_frame(sample_image)
        
        # Check that image dimensions are preserved
        assert result.shape == sample_image.shape
        assert isinstance(detected_faces, list)
    
    def test_emoji_anonymization(self, minimal_anonymizer, sample_image):
        """Test emoji anonymization method"""
        minimal_anonymizer.config.method = AnonymizationMethod.EMOJI
        result, detected_faces = minimal_anonymizer.anonymize_frame(sample_image)
        
        # Check that image dimensions are preserved
        assert result.shape == sample_image.shape
        assert isinstance(detected_faces, list)
    
    def test_disabled_anonymization(self, sample_image):
        """Test anonymization when disabled"""
        config = AnonymizationConfig(enabled=False)
        anonymizer = FaceAnonymizer(config)
        result, detected_faces = anonymizer.anonymize_frame(sample_image)
        
        # Image should remain unchanged when disabled
        np.testing.assert_array_equal(result, sample_image)
        assert len(detected_faces) == 0
    
    def test_face_detection_with_mock(self, anonymizer, sample_image):
        """Test face detection with mocked detector"""
        with patch.object(anonymizer, 'detect_faces') as mock_detect:
            mock_faces = [FaceDetection(x=50, y=50, width=100, height=100, confidence=0.9)]
            mock_detect.return_value = mock_faces
            
            result, detected_faces = anonymizer.anonymize_frame(sample_image)
            
            assert len(detected_faces) == 1
            assert detected_faces[0].anonymized == True
            mock_detect.assert_called_once_with(sample_image)
    
    def test_face_hash_generation(self, anonymizer, sample_image):
        """Test face hash generation for privacy compliance"""
        face = FaceDetection(x=50, y=50, width=100, height=100, confidence=0.9)
        hash1 = anonymizer._generate_face_hash(sample_image, face)
        hash2 = anonymizer._generate_face_hash(sample_image, face)
        
        # Same face should generate same hash
        assert hash1 == hash2
        assert len(hash1) == 16  # Hash is truncated to 16 chars
        
        # Different face should generate different hash
        different_face = FaceDetection(x=100, y=100, width=100, height=100, confidence=0.9)
        hash3 = anonymizer._generate_face_hash(sample_image, different_face)
        assert hash1 != hash3
    
    def test_get_anonymization_stats(self, anonymizer):
        """Test anonymization statistics reporting"""
        faces = [
            FaceDetection(x=50, y=50, width=100, height=100, confidence=0.9, anonymized=True),
            FaceDetection(x=150, y=150, width=80, height=80, confidence=0.8, anonymized=True)
        ]
        
        stats = anonymizer.get_anonymization_stats(faces)
        
        assert stats["faces_detected"] == 2
        assert stats["faces_anonymized"] == 2
        assert stats["anonymization_method"] == anonymizer.config.method.value
        assert stats["privacy_level"] == anonymizer.config.privacy_level.value
        assert stats["average_confidence"] == 0.85
    
    def test_empty_frame_handling(self, anonymizer):
        """Test handling of empty or invalid frames"""
        # Test with None
        result, faces = anonymizer.anonymize_frame(None)
        assert result is None
        assert faces == []
        
        # Test with empty array
        empty_frame = np.array([])
        result, faces = anonymizer.anonymize_frame(empty_frame)
        assert result is empty_frame
        assert faces == []
    
    def test_face_boundary_validation(self, anonymizer):
        """Test that face boundaries are properly validated"""
        # Create a face detection with coordinates outside image bounds
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        face = FaceDetection(x=80, y=80, width=50, height=50, confidence=0.9)
        
        # Should handle out-of-bounds coordinates gracefully
        result = anonymizer._apply_anonymization(frame, face)
        assert result.shape == frame.shape
    
    def test_configuration_updates(self, anonymizer):
        """Test configuration updates during runtime"""
        # Test method change
        original_method = anonymizer.config.method
        anonymizer.config.method = AnonymizationMethod.PIXELATE
        assert anonymizer.config.method == AnonymizationMethod.PIXELATE
        
        # Test privacy level change
        anonymizer.config.privacy_level = PrivacyLevel.MINIMAL
        assert anonymizer.config.privacy_level == PrivacyLevel.MINIMAL
    
    def test_performance_with_large_image(self, anonymizer):
        """Test performance with larger images"""
        # Create a larger test image
        large_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # Should handle large images without crashing
        result, faces = anonymizer.anonymize_frame(large_image)
        assert result.shape == large_image.shape


class TestPrivacyCompliance:
    """Test suite for privacy compliance features"""
    
    def test_strict_privacy_level_behavior(self):
        """Test that strict privacy level has appropriate behavior"""
        anonymizer = FaceAnonymizer(get_strict_config())
        
        # Strict mode should use strong anonymization
        assert anonymizer.config.privacy_level == PrivacyLevel.STRICT
        
        # Test that configuration reflects strict settings
        stats = anonymizer.get_anonymization_stats([])
        assert stats["privacy_level"] == "strict"
    
    def test_gdpr_compliance_hash_only(self):
        """Test GDPR compliance mode where only hashes are stored"""
        anonymizer = FaceAnonymizer(get_strict_config())
        
        sample_image = np.zeros((300, 300, 3), dtype=np.uint8)
        cv2.rectangle(sample_image, (50, 50), (150, 150), (255, 255, 255), -1)
        
        face = FaceDetection(x=50, y=50, width=100, height=100, confidence=0.9)
        face_hash = anonymizer._generate_face_hash(sample_image, face)
        
        # Hash should be generated for identification without storing face data
        assert face_hash is not None
        assert len(face_hash) == 16  # Truncated hash length
    
    def test_minimal_face_size_filtering(self, anonymizer):
        """Test that faces below minimum size are filtered out"""
        # Create a very small face detection
        small_face = FaceDetection(x=50, y=50, width=10, height=10, confidence=0.9)
        
        # Should not be processed if below min_face_size
        anonymizer.config.min_face_size = 30
        
        sample_image = np.zeros((300, 300, 3), dtype=np.uint8)
        result = anonymizer._apply_anonymization(sample_image, small_face)
        
        # Should handle gracefully
        assert result.shape == sample_image.shape
    
    def test_confidence_threshold_filtering(self, anonymizer):
        """Test that low confidence detections are handled"""
        # Test with low confidence face
        low_conf_face = FaceDetection(x=50, y=50, width=100, height=100, confidence=0.3)
        
        anonymizer.config.detection_confidence = 0.7
        
        # Face should still be processed (confidence filtering happens in detect_faces)
        sample_image = np.zeros((300, 300, 3), dtype=np.uint8)
        result = anonymizer._apply_anonymization(sample_image, low_conf_face)
        assert result.shape == sample_image.shape


class TestAnonymizationMethods:
    """Test specific anonymization method implementations"""
    
    @pytest.fixture
    def test_frame(self):
        """Create test frame with face region"""
        frame = np.ones((200, 200, 3), dtype=np.uint8) * 128  # Gray image
        # Add bright face region
        cv2.rectangle(frame, (50, 50), (150, 150), (255, 255, 255), -1)
        return frame
    
    @pytest.fixture
    def test_face(self):
        """Create test face detection"""
        return FaceDetection(x=50, y=50, width=100, height=100, confidence=0.9)
    
    def test_blur_method_implementation(self, test_frame, test_face):
        """Test blur method implementation details"""
        config = AnonymizationConfig(method=AnonymizationMethod.BLUR, blur_factor=15)
        anonymizer = FaceAnonymizer(config)
        
        result = anonymizer._apply_anonymization(test_frame, test_face)
        
        # Face region should be different (blurred)
        original_region = test_frame[50:150, 50:150]
        blurred_region = result[50:150, 50:150]
        
        # Should be different due to blur
        assert not np.array_equal(original_region, blurred_region)
        
        # Non-face regions should be unchanged
        np.testing.assert_array_equal(test_frame[0:40, 0:40], result[0:40, 0:40])
    
    def test_pixelate_method_implementation(self, test_frame, test_face):
        """Test pixelate method implementation details"""
        config = AnonymizationConfig(method=AnonymizationMethod.PIXELATE, pixelate_factor=10)
        anonymizer = FaceAnonymizer(config)
        
        result = anonymizer._apply_anonymization(test_frame, test_face)
        
        # Face region should be different (pixelated)
        original_region = test_frame[50:150, 50:150]
        pixelated_region = result[50:150, 50:150]
        
        assert not np.array_equal(original_region, pixelated_region)
    
    def test_black_box_method_implementation(self, test_frame, test_face):
        """Test black box method implementation details"""
        config = AnonymizationConfig(method=AnonymizationMethod.BLACK_BOX)
        anonymizer = FaceAnonymizer(config)
        
        result = anonymizer._apply_anonymization(test_frame, test_face)
        
        # Face region should be black
        black_region = result[50:150, 50:150]
        assert np.all(black_region == 0)
        
        # Non-face regions should be unchanged
        np.testing.assert_array_equal(test_frame[0:40, 0:40], result[0:40, 0:40])
    
    def test_emoji_method_implementation(self, test_frame, test_face):
        """Test emoji method implementation details"""
        config = AnonymizationConfig(method=AnonymizationMethod.EMOJI)
        anonymizer = FaceAnonymizer(config)
        
        result = anonymizer._apply_anonymization(test_frame, test_face)
        
        # Face region should be different (emoji overlay)
        original_region = test_frame[50:150, 50:150]
        emoji_region = result[50:150, 50:150]
        
        assert not np.array_equal(original_region, emoji_region)


if __name__ == "__main__":
    pytest.main([__file__])

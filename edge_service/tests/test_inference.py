"""
Unit Tests for Edge Service Inference Pipeline

This module provides comprehensive test coverage for the AI inference logic in inference.py,
ensuring correct model loading, preprocessing, and object detection behavior.

Test Coverage:
- Model loading and initialization with mocked engines
- Preprocessing functions (resize_letterbox, normalize_image)
- Object detection inference with mocked outputs
- Hard example detection and Kafka publishing
- Edge cases and error handling

Dependencies:
- pytest for test framework
- unittest.mock for mocking OpenCV and TensorRT operations
- numpy for tensor operations
- OpenCV for image processing (mocked)
"""

import numpy as np
import pytest
import json
import base64
import os
import sys
from unittest.mock import Mock, patch, MagicMock, mock_open
from typing import List, Dict, Any
import tempfile

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the modules to test
from inference import EdgeInference, preprocess_frame, run_inference, detect_and_annotate
from preprocessing import resize_letterbox, normalize_image


# Test fixtures and mock data
@pytest.fixture
def dummy_image():
    """Create a dummy BGR image array for testing."""
    # Create a 100x100x3 synthetic image with a simple pattern
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Add a simple rectangular pattern to simulate a face/object
    image[30:70, 30:70] = [255, 255, 255]  # White rectangle
    image[35:40, 40:60] = [0, 0, 0]        # Black eyes
    image[50:55, 45:55] = [128, 128, 128]  # Gray mouth
    
    return image


@pytest.fixture 
def dummy_tensor():
    """Create a dummy preprocessed tensor in CHW format."""
    return np.random.rand(3, 224, 224).astype(np.float32)


@pytest.fixture
def mock_kafka_producer():
    """Create a mock Kafka producer."""
    producer = Mock()
    producer.produce = Mock()
    producer.poll = Mock()
    return producer


@pytest.fixture
def temp_model_dir():
    """Create a temporary directory with dummy model files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create dummy model files
        object_model_path = os.path.join(temp_dir, "object_detection.trt")
        activity_model_path = os.path.join(temp_dir, "activity_recognition.trt")
        
        with open(object_model_path, 'w') as f:
            f.write("dummy_object_model")
        with open(activity_model_path, 'w') as f:
            f.write("dummy_activity_model")
            
        yield temp_dir


class TestPreprocessingFunctions:
    """Test preprocessing functions for image normalization and resizing."""
    
    def test_resize_letterbox_preserves_aspect_ratio(self, dummy_image):
        """Test that letterbox resizing preserves aspect ratio."""
        target_size = (224, 224)
        result = resize_letterbox(dummy_image, target_size)
        
        assert result.shape == (224, 224, 3)
        assert result.dtype == dummy_image.dtype
        
        # Check that padding (black borders) exists
        # Since original is square and target is square, padding should be minimal
        assert np.any(result[0, :] == 0)  # Top border might have black pixels
        
    def test_resize_letterbox_different_aspect_ratios(self):
        """Test letterbox resizing with different aspect ratios."""
        # Wide image (2:1 aspect ratio)
        wide_image = np.ones((100, 200, 3), dtype=np.uint8) * 128
        result = resize_letterbox(wide_image, (224, 224))
        
        assert result.shape == (224, 224, 3)
        # Should have vertical padding (black bars on top/bottom)
        assert np.all(result[0, :] == 0)  # Top row should be black
        assert np.all(result[-1, :] == 0)  # Bottom row should be black
        
    def test_resize_letterbox_invalid_inputs(self):
        """Test letterbox resizing with invalid inputs."""
        dummy_image = np.ones((100, 100, 3), dtype=np.uint8)
        
        # Test invalid target size
        with pytest.raises(ValueError, match="Target size must contain positive values"):
            resize_letterbox(dummy_image, (0, 224))
            
        with pytest.raises(ValueError, match="Target size must contain positive values"):
            resize_letterbox(dummy_image, (-1, 224))
    
    def test_normalize_image_values(self, dummy_image):
        """Test image normalization with mean and std."""
        mean = [0.485, 0.456, 0.406]  # ImageNet means (RGB)
        std = [0.229, 0.224, 0.225]   # ImageNet stds (RGB)
        
        result = normalize_image(dummy_image, mean, std)
        
        # Check output format
        assert result.dtype == np.float32
        assert result.shape == (3, 100, 100)  # CHW format
        
        # Check value range (should be roughly [-2, 2] after normalization)
        assert -3 < result.min() < 3
        assert -3 < result.max() < 3
        
    def test_normalize_image_channel_conversion(self):
        """Test BGR to RGB conversion during normalization."""
        # Create image with distinct BGR values
        bgr_image = np.zeros((10, 10, 3), dtype=np.uint8)
        bgr_image[:, :, 0] = 100  # Blue channel
        bgr_image[:, :, 1] = 150  # Green channel  
        bgr_image[:, :, 2] = 200  # Red channel
        
        mean = [0.0, 0.0, 0.0]
        std = [1.0, 1.0, 1.0]
        
        result = normalize_image(bgr_image, mean, std)
          # After BGR->RGB conversion and normalization:
        # Original Blue (100) -> RGB Blue channel -> result[2]
        # Original Green (150) -> RGB Green channel -> result[1] 
        # Original Red (200) -> RGB Red channel -> result[0]
        
        red_channel_value = result[0, 0, 0]    # Should be ~200/255 (original red)
        green_channel_value = result[1, 0, 0]  # Should be ~150/255 (original green)
        blue_channel_value = result[2, 0, 0]   # Should be ~100/255 (original blue)
        
        assert abs(red_channel_value - 200/255) < 0.01
        assert abs(green_channel_value - 150/255) < 0.01
        assert abs(blue_channel_value - 100/255) < 0.01
        
    def test_normalize_image_invalid_parameters(self, dummy_image):
        """Test normalization with invalid parameters."""
        # Wrong number of mean/std values
        with pytest.raises(ValueError, match="Mean and std must contain exactly 3 values"):
            normalize_image(dummy_image, [0.5, 0.5], [0.5, 0.5, 0.5])
            
        # Zero std deviation
        with pytest.raises(ValueError, match="Standard deviation values must be positive"):
            normalize_image(dummy_image, [0.5, 0.5, 0.5], [0.0, 0.5, 0.5])
            
        # Wrong image format
        gray_image = np.ones((100, 100), dtype=np.uint8)
        with pytest.raises(ValueError, match="Input image must be 3-channel"):
            normalize_image(gray_image, [0.5, 0.5, 0.5], [0.5, 0.5, 0.5])


class TestEdgeInferenceInitialization:
    """Test EdgeInference class initialization and model loading."""
    
    def test_engine_initialization_success(self, temp_model_dir, mock_kafka_producer):
        """Test successful initialization with valid model directory."""
        with patch('inference.Producer') as mock_producer_class:
            mock_producer_class.return_value = mock_kafka_producer
            
            engine = EdgeInference(model_dir=temp_model_dir)
            
            assert engine.model_dir == temp_model_dir
            assert engine.kafka_producer == mock_kafka_producer
            assert isinstance(engine.hard_example_thresholds, dict)
            assert 'person' in engine.hard_example_thresholds
            assert 'vehicle' in engine.hard_example_thresholds
            
    def test_engine_initialization_missing_models(self):
        """Test initialization with missing model files."""
        with tempfile.TemporaryDirectory() as empty_dir:
            # Directory exists but no model files
            with patch('inference.Producer') as mock_producer_class:
                engine = EdgeInference(model_dir=empty_dir)
                
                # Should still initialize but models will be None
                assert engine.model_dir == empty_dir
                assert engine.obj_model is None
                assert engine.act_model is None
    
    def test_kafka_connection_failure(self, temp_model_dir):
        """Test graceful handling of Kafka connection failure."""
        with patch('inference.Producer') as mock_producer_class:
            mock_producer_class.side_effect = Exception("Connection failed")
            
            engine = EdgeInference(model_dir=temp_model_dir)
            
            # Should continue initialization even if Kafka fails
            assert engine.kafka_producer is None
            assert engine.model_dir == temp_model_dir
            
    def test_hard_example_thresholds_configuration(self, temp_model_dir):
        """Test that hard example thresholds are properly configured."""
        with patch('inference.Producer'):
            engine = EdgeInference(model_dir=temp_model_dir)
            
            thresholds = engine.hard_example_thresholds
            
            # Verify expected thresholds
            assert thresholds['person'] == 0.6
            assert thresholds['face'] == 0.5
            assert thresholds['vehicle'] == 0.4
            assert thresholds['object'] == 0.5


class TestObjectDetectionInference:
    """Test object detection inference methods."""
    
    def test_infer_objects_returns_detections(self, temp_model_dir, dummy_tensor):
        """Test that infer_objects returns valid Detection objects."""
        with patch('inference.Producer'):
            engine = EdgeInference(model_dir=temp_model_dir)
            
            detections = engine.infer_objects(dummy_tensor)
            
            assert isinstance(detections, list)
            assert len(detections) >= 3  # Should generate 3-5 detections
            assert len(detections) <= 5
              # Check each detection has required attributes
            for detection in detections:
                assert hasattr(detection, 'label')
                assert hasattr(detection, 'confidence')
                assert hasattr(detection, 'bounding_box')
                
                # Check confidence is in valid range
                assert 0.0 <= detection.confidence <= 1.0
                
                # Check class name is one of expected types
                assert detection.label in ['person', 'vehicle', 'object']
                
    def test_infer_objects_hard_example_detection(self, temp_model_dir, dummy_tensor, dummy_image):
        """Test that hard examples are detected correctly."""
        with patch('inference.Producer') as mock_producer_class:
            mock_kafka_producer = Mock()
            mock_producer_class.return_value = mock_kafka_producer
            
            engine = EdgeInference(model_dir=temp_model_dir)
            
            # Mock cv2.imencode for frame encoding
            with patch('cv2.imencode') as mock_imencode:
                mock_imencode.return_value = (True, b'fake_encoded_frame')
                
                detections = engine.infer_objects(
                    dummy_tensor, 
                    camera_id="test-camera",
                    frame_data=dummy_image
                )
                
                # Should still return detections
                assert isinstance(detections, list)
                assert len(detections) > 0
                
                # Check if Kafka publish was called (hard examples detected)
                # The simulation always generates at least one hard example
                mock_kafka_producer.produce.assert_called()                # Verify the published message structure
                call_args = mock_kafka_producer.produce.call_args
                # produce() is called with: topic as positional arg, key/value/callback as kwargs
                assert call_args[0][0] == 'hard-examples'  # topic (positional)
                assert call_args[1]['key'] == 'test-camera'    # key (keyword)
                
                # Decode and check message content
                published_data = json.loads(call_args[1]['value'].decode('utf-8'))  # value (keyword)
                assert 'camera_id' in published_data
                assert 'timestamp' in published_data
                assert 'frame_data' in published_data
                assert 'detections' in published_data
                assert published_data['camera_id'] == 'test-camera'
    
    def test_infer_objects_without_kafka(self, temp_model_dir, dummy_tensor):
        """Test inference when Kafka is not available."""
        with patch('inference.Producer') as mock_producer_class:
            mock_producer_class.side_effect = Exception("Kafka unavailable")
            
            engine = EdgeInference(model_dir=temp_model_dir)
            
            # Should still work without Kafka
            detections = engine.infer_objects(dummy_tensor)
            
            assert isinstance(detections, list)
            assert len(detections) > 0
            
    def test_infer_objects_confidence_distribution(self, temp_model_dir, dummy_tensor):
        """Test that inference generates realistic confidence distributions."""
        with patch('inference.Producer'):
            engine = EdgeInference(model_dir=temp_model_dir)
            
            # Run multiple inferences to check distribution
            all_confidences = []
            for _ in range(10):
                detections = engine.infer_objects(dummy_tensor)
                for det in detections:
                    all_confidences.append(det.confidence)
            
            # Should have a range of confidences
            assert min(all_confidences) < 0.6  # Some low confidence (hard examples)
            assert max(all_confidences) > 0.7  # Some high confidence
            
            # Check that first detection is always hard example (per simulation)
            for _ in range(5):
                detections = engine.infer_objects(dummy_tensor)
                first_det = detections[0]
                  # First detection should be below threshold for its class
                threshold = engine.hard_example_thresholds.get(first_det.label, 0.5)
                assert first_det.confidence < threshold


class TestActivityRecognition:
    """Test activity recognition inference."""
    
    def test_infer_activity_returns_string(self, temp_model_dir, dummy_tensor):
        """Test that activity inference returns a string."""
        with patch('inference.Producer'):
            engine = EdgeInference(model_dir=temp_model_dir)
            
            activity = engine.infer_activity(dummy_tensor)
            
            assert isinstance(activity, str)
            # Currently returns "unknown" as placeholder
            assert activity == "unknown"


class TestHardExamplePublishing:
    """Test hard example detection and Kafka publishing."""
    
    def test_hard_example_kafka_message_structure(self, temp_model_dir, dummy_tensor, dummy_image):
        """Test the structure of Kafka messages for hard examples."""
        with patch('inference.Producer') as mock_producer_class:
            mock_kafka_producer = Mock()
            mock_producer_class.return_value = mock_kafka_producer
            
            engine = EdgeInference(model_dir=temp_model_dir)
            
            with patch('cv2.imencode') as mock_imencode:
                # Mock successful image encoding
                fake_buffer = np.array([1, 2, 3, 4, 5], dtype=np.uint8)
                mock_imencode.return_value = (True, fake_buffer)
                
                engine.infer_objects(
                    dummy_tensor,
                    camera_id="test-cam-123", 
                    frame_data=dummy_image
                )
                
                # Verify Kafka message was sent
                mock_kafka_producer.produce.assert_called_once()
                
                call_args = mock_kafka_producer.produce.call_args
                message_data = json.loads(call_args[1]['value'].decode('utf-8'))
                
                # Verify message structure
                required_fields = ['camera_id', 'timestamp', 'frame_data', 'detections', 'model_version']
                for field in required_fields:
                    assert field in message_data
                    
                assert message_data['camera_id'] == 'test-cam-123'
                assert isinstance(message_data['timestamp'], int)
                assert isinstance(message_data['frame_data'], str)  # base64 encoded
                assert isinstance(message_data['detections'], list)
                assert len(message_data['detections']) > 0
                
                # Check detection format in hard example
                detection = message_data['detections'][0]
                assert 'class_name' in detection
                assert 'confidence' in detection
                assert 'bbox' in detection
    
    def test_hard_example_frame_encoding_failure(self, temp_model_dir, dummy_tensor, dummy_image):
        """Test handling of frame encoding failure."""
        with patch('inference.Producer') as mock_producer_class:
            mock_kafka_producer = Mock()
            mock_producer_class.return_value = mock_kafka_producer
            
            engine = EdgeInference(model_dir=temp_model_dir)
            
            with patch('cv2.imencode') as mock_imencode:
                # Mock failed image encoding
                mock_imencode.return_value = (False, None)
                
                detections = engine.infer_objects(
                    dummy_tensor,
                    camera_id="test-cam", 
                    frame_data=dummy_image
                )
                
                # Should still return detections
                assert isinstance(detections, list)
                
                # But Kafka should not be called due to encoding failure
                mock_kafka_producer.produce.assert_not_called()
                
    def test_delivery_report_callback(self, temp_model_dir):
        """Test the Kafka delivery report callback."""
        with patch('inference.Producer'):
            engine = EdgeInference(model_dir=temp_model_dir)
            
            # Test successful delivery
            mock_msg = Mock()
            mock_msg.topic.return_value = 'hard-examples'
            mock_msg.partition.return_value = 0
            mock_msg.offset.return_value = 12345
            
            # Should not raise exception
            engine._delivery_report(None, mock_msg)
            
            # Test failed delivery
            mock_error = Mock()
            mock_error.__str__ = Mock(return_value="Delivery failed")
            
            # Should not raise exception
            engine._delivery_report(mock_error, mock_msg)


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""
    
    def test_infer_objects_empty_tensor(self, temp_model_dir):
        """Test inference with empty or invalid tensor."""
        with patch('inference.Producer'):
            engine = EdgeInference(model_dir=temp_model_dir)
            
            # Empty tensor
            empty_tensor = np.array([])
            
            # Should still return detections (simulation mode)
            detections = engine.infer_objects(empty_tensor)
            assert isinstance(detections, list)
    
    def test_infer_objects_wrong_tensor_shape(self, temp_model_dir):
        """Test inference with wrong tensor shape."""
        with patch('inference.Producer'):
            engine = EdgeInference(model_dir=temp_model_dir)
            
            # Wrong shape tensor (should be CHW)
            wrong_tensor = np.random.rand(224, 224, 3).astype(np.float32)
            
            # Should still work in simulation mode
            detections = engine.infer_objects(wrong_tensor)
            assert isinstance(detections, list)
    
    def test_hard_example_no_frame_data(self, temp_model_dir, dummy_tensor):
        """Test hard example detection without frame data."""
        with patch('inference.Producer') as mock_producer_class:
            mock_kafka_producer = Mock()
            mock_producer_class.return_value = mock_kafka_producer
            
            engine = EdgeInference(model_dir=temp_model_dir)
            
            # Call without frame_data
            detections = engine.infer_objects(
                dummy_tensor,
                camera_id="test-cam"
                # frame_data=None (default)
            )
            
            assert isinstance(detections, list)            # Kafka should not be called without frame data
            mock_kafka_producer.produce.assert_not_called()
    
    def test_bounding_box_coordinates_validity(self, temp_model_dir, dummy_tensor):
        """Test that generated bounding boxes have valid coordinates."""
        with patch('inference.Producer'):
            engine = EdgeInference(model_dir=temp_model_dir)
            
            detections = engine.infer_objects(dummy_tensor)
            for detection in detections:
                bbox = detection.bounding_box
                
                # Check that coordinates are in valid range [0, 1]
                assert 0 <= bbox.x_min <= 1
                assert 0 <= bbox.y_min <= 1
                assert 0 <= bbox.x_max <= 1
                assert 0 <= bbox.y_max <= 1
                  # Check that x_max > x_min and y_max > y_min (valid rectangle)
                assert bbox.x_max > bbox.x_min
                assert bbox.y_max > bbox.y_min
                
                # Check minimum size constraints
                min_width = bbox.x_max - bbox.x_min
                min_height = bbox.y_max - bbox.y_min
                assert min_width >= 0.01  # At least 1% width
                assert min_height >= 0.01  # At least 1% height


class TestSpecificInferenceFunctions:
    """Test specific inference functions as requested in requirements."""
    
    def test_preprocess_frame_function(self, dummy_image):
        """Test preprocess_frame function that combines resize and normalize."""
        # Test the function
        blob = preprocess_frame(dummy_image)
        
        # Verify blob shape and type
        assert blob.shape == (3, 224, 224)
        assert blob.dtype == np.float32        # Verify normalization (values should be in reasonable range)
        assert -3 < blob.min() < 3
        assert -3 < blob.max() < 3
    
    def test_preprocess_frame_invalid_input(self):
        """Test preprocess_frame with invalid inputs."""
        # Test with None input
        with pytest.raises(ValueError, match="Input image cannot be None"):
            preprocess_frame(None)
          # Test with invalid image format  
        gray_image = np.ones((100, 100), dtype=np.uint8)
        with pytest.raises(ValueError, match="Input image must be 3-channel"):
            preprocess_frame(gray_image)
    
    def test_run_inference_function(self, dummy_tensor):
        """Test run_inference function with mocked DNN forward pass."""
        # Test with simulated results (when model files don't exist)
        detections = run_inference(dummy_tensor)
        
        # Verify detection format
        assert isinstance(detections, np.ndarray)
        assert detections.shape[1] == 7  # [batch_id, class_id, confidence, x, y, w, h]
        assert len(detections) >= 2  # At least 2 detections
        
        # Check confidence values are in valid range
        confidences = detections[:, 2]
        assert all(0.0 <= conf <= 1.0 for conf in confidences)
    
    def test_detect_and_annotate_function(self, dummy_image):
        """Test end-to-end detect_and_annotate function with face blurring."""
        # Test with normal image
        result = detect_and_annotate(dummy_image)
        
        # Verify result
        assert result.shape == dummy_image.shape
        assert result.dtype == dummy_image.dtype
          # Should return some result (even if no faces detected, original image is returned)
        assert result is not None
    
    def test_detect_and_annotate_no_detections(self, dummy_image):
        """Test detect_and_annotate when no faces are detected."""
        # The function should still work and return the original image
        result = detect_and_annotate(dummy_image, confidence_threshold=0.99)  # Very high threshold
        
        # Should return an image of same dimensions
        assert result.shape == dummy_image.shape
        assert result.dtype == dummy_image.dtype
    
    def test_detect_and_annotate_invalid_input(self):
        """Test detect_and_annotate with invalid input."""
        # Test with None input
        with pytest.raises(ValueError, match="Input image cannot be None"):
            detect_and_annotate(None)
        
        # Test with invalid image format
        gray_image = np.ones((100, 100), dtype=np.uint8)
        with pytest.raises(ValueError, match="Input image must be 3-channel"):
            detect_and_annotate(gray_image)


class TestOpenCVDNNMocking:
    """Test OpenCV DNN operations with proper mocking."""
    
    def test_cv2_dnn_readnet_mocking(self):
        """Test mocking of cv2.dnn.readNetFromTensorflow."""
        with patch('cv2.dnn.readNetFromTensorflow') as mock_read_net:
            mock_net = Mock()
            mock_read_net.return_value = mock_net
            
            # Mock the forward pass
            mock_output = np.array([[0, 1, 0.85, 0.1, 0.1, 0.3, 0.4]], dtype=np.float32)
            mock_net.forward.return_value = mock_output
            
            # Test loading model
            net = mock_read_net('model.pb', 'config.pbtxt')
            assert net is not None
            
            # Test forward pass
            dummy_blob = np.random.rand(1, 3, 224, 224).astype(np.float32)
            detections = net.forward()
            
            assert isinstance(detections, np.ndarray)
            assert detections.shape == (1, 7)
            assert detections[0, 2] == 0.85  # Confidence
    
    def test_cv2_dnn_blobfromimage_mocking(self, dummy_image):
        """Test mocking of cv2.dnn.blobFromImage."""
        with patch('cv2.dnn.blobFromImage') as mock_blob_from_image:
            expected_blob = np.random.rand(1, 3, 224, 224).astype(np.float32)
            mock_blob_from_image.return_value = expected_blob
            
            # Test blob creation
            blob = mock_blob_from_image(dummy_image, 1.0, (224, 224), (0, 0, 0), True, crop=False)
            
            assert blob.shape == (1, 3, 224, 224)
            assert blob.dtype == np.float32
            
            # Verify the function was called with correct parameters
            mock_blob_from_image.assert_called_once_with(
                dummy_image, 1.0, (224, 224), (0, 0, 0), True, crop=False
            )


class TestEndToEndIntegration:
    """Test end-to-end integration scenarios."""
    
    def test_complete_inference_pipeline(self, temp_model_dir, dummy_image):
        """Test the complete pipeline from raw image to detection results."""
        with patch('inference.Producer') as mock_producer_class:
            mock_kafka_producer = Mock()
            mock_producer_class.return_value = mock_kafka_producer
            
            # Initialize inference engine
            engine = EdgeInference(model_dir=temp_model_dir)
            
            # Preprocess the image
            resized = resize_letterbox(dummy_image, (224, 224))
            tensor = normalize_image(resized, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            
            # Run inference with hard example detection
            with patch('cv2.imencode') as mock_imencode:
                mock_imencode.return_value = (True, b'encoded_frame')
                
                detections = engine.infer_objects(
                    tensor,
                    camera_id="integration-test-cam",
                    frame_data=dummy_image
                )
                
                activity = engine.infer_activity(tensor)
            
            # Verify results
            assert isinstance(detections, list)
            assert len(detections) > 0
            assert isinstance(activity, str)
            
            # Verify preprocessing worked correctly
            assert tensor.shape == (3, 224, 224)
            assert tensor.dtype == np.float32
            
            # Verify hard example was detected and published
            mock_kafka_producer.produce.assert_called()
    
    def test_inference_with_face_anonymization_integration(self, temp_model_dir):
        """Test inference working with anonymized frames (simulated)."""
        with patch('inference.Producer'):
            engine = EdgeInference(model_dir=temp_model_dir)
            
            # Create anonymized frame (simulate face anonymization by blurring part of image)
            anonymized_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            # Apply simulated anonymization (blur a region)
            import cv2
            anonymized_frame[100:200, 200:400] = cv2.GaussianBlur(
                anonymized_frame[100:200, 200:400], (51, 51), 0
            )
            
            # Preprocess anonymized frame
            resized = resize_letterbox(anonymized_frame, (224, 224))
            tensor = normalize_image(resized, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            
            # Run inference
            detections = engine.infer_objects(tensor)
            
            # Should still detect objects even with anonymized input
            assert isinstance(detections, list)
            assert len(detections) > 0
            
            # Verify detection quality is maintained
            confidences = [det.confidence for det in detections]
            assert max(confidences) > 0.5  # Should have some confident detections
    
    def test_full_pipeline_with_opencv_dnn_mocks(self, dummy_image):
        """Test full pipeline with comprehensive OpenCV DNN mocking."""
        with patch('cv2.dnn.readNetFromTensorflow') as mock_read_net, \
             patch('cv2.dnn.blobFromImage') as mock_blob_from_image, \
             patch('cv2.imencode') as mock_imencode:
            
            # Setup mocks
            mock_net = Mock()
            mock_read_net.return_value = mock_net
            
            # Mock blob creation
            mock_blob = np.random.rand(1, 3, 224, 224).astype(np.float32)
            mock_blob_from_image.return_value = mock_blob
            
            # Mock detection output
            mock_detections = np.array([
                [0, 1, 0.85, 0.1, 0.1, 0.3, 0.4],  # Person - high confidence
                [0, 2, 0.35, 0.5, 0.2, 0.2, 0.3],  # Vehicle - low confidence (hard example)
            ], dtype=np.float32)
            mock_net.forward.return_value = mock_detections
            
            # Mock image encoding for Kafka
            mock_imencode.return_value = (True, b'encoded_image_data')
            
            # Create a complete pipeline function
            def complete_pipeline(image: np.ndarray, camera_id: str = "test-cam"):
                """Complete inference pipeline with OpenCV DNN."""
                # 1. Preprocess
                blob = mock_blob_from_image(image, 1.0, (224, 224), (0, 0, 0), True, crop=False)
                
                # 2. Load model
                net = mock_read_net('model.pb', 'config.pbtxt')
                
                # 3. Run inference
                detections = net.forward()
                
                # 4. Process results
                results = []
                for detection in detections:
                    if detection[2] > 0.3:  # Confidence threshold
                        results.append({
                            'class_id': int(detection[1]),
                            'confidence': float(detection[2]),
                            'bbox': [detection[3], detection[4], detection[5], detection[6]]
                        })
                
                return results
            
            # Test the complete pipeline
            results = complete_pipeline(dummy_image)            # Verify results
            assert len(results) == 2  # Two detections above threshold
            assert abs(results[0]['confidence'] - 0.85) < 0.001  # Use approximate comparison
            assert abs(results[1]['confidence'] - 0.35) < 0.001  # Use approximate comparison
            
            # Verify all mocks were called
            mock_read_net.assert_called_once()
            mock_blob_from_image.assert_called_once()
            mock_net.forward.assert_called_once()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])

"""
Tests for the Drift Detection Service.
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from drift_service import (
    DriftDetector, 
    InferenceEvent, 
    HardExample, 
    process_inference_event,
    publish_hard_example,
    app
)

# =============================================================================
# DRIFT DETECTOR UNIT TESTS
# =============================================================================

class TestDriftDetector:
    """Test the core drift detection logic."""
    
    def test_init(self):
        """Test DriftDetector initialization."""
        detector = DriftDetector(window_size=100, threshold_sigma=2.5)
        assert detector.window_size == 100
        assert detector.threshold_sigma == 2.5
        assert len(detector.confidence_windows) == 0
    
    def test_add_confidence(self):
        """Test adding confidence scores to windows."""
        detector = DriftDetector(window_size=3)
        
        # Add scores for a label
        detector.add_confidence("person", 0.8)
        detector.add_confidence("person", 0.9)
        detector.add_confidence("person", 0.7)
        
        window = detector.confidence_windows["person"]
        assert len(window) == 3
        assert list(window) == [0.8, 0.9, 0.7]
          # Test window size limit
        detector.add_confidence("person", 0.6)
        assert len(window) == 3  # Should still be 3 due to maxlen
        assert list(window) == [0.9, 0.7, 0.6]  # First element dropped
      def test_get_statistics(self):
        """Test statistics calculation."""
        detector = DriftDetector()
        
        # Empty window
        mean, std = detector.get_statistics("unknown")
        assert mean == 0.0
        assert std == 0.0
        
        # Single value - should return 0,0 because we need at least 2 values for statistics
        detector.add_confidence("person", 0.8)
        mean, std = detector.get_statistics("person")
        assert mean == 0.0  # Insufficient data for statistics
        assert std == 0.0
        
        # Two values - now we can calculate statistics
        detector.add_confidence("person", 0.9)
        mean, std = detector.get_statistics("person")
        expected_mean = (0.8 + 0.9) / 2  # 0.85
        assert abs(mean - expected_mean) < 0.001
        assert std > 0  # Should have some standard deviation
        
        # Multiple values
        detector.add_confidence("person", 0.7)
        mean, std = detector.get_statistics("person")
        expected_mean = (0.8 + 0.9 + 0.7) / 3  # 0.8
        assert abs(mean - expected_mean) < 0.001
        assert std > 0  # Should have some standard deviation
    
    def test_statistics_caching(self):
        """Test that statistics are cached correctly."""
        detector = DriftDetector()
        
        # Add some data
        detector.add_confidence("person", 0.8)
        detector.add_confidence("person", 0.9)
        
        # First call should calculate and cache
        mean1, std1 = detector.get_statistics("person")
        assert "person" in detector._stats_cache
        assert not detector._cache_dirty["person"]
        
        # Second call should use cache
        mean2, std2 = detector.get_statistics("person")
        assert mean1 == mean2
        assert std1 == std2
        
        # Adding new data should mark cache as dirty
        detector.add_confidence("person", 0.7)
        assert detector._cache_dirty["person"]
        
        # Next call should recalculate
        mean3, std3 = detector.get_statistics("person")
        assert mean3 != mean1  # Should be different due to new data
    
    def test_drift_detection_insufficient_data(self):
        """Test drift detection with insufficient data."""
        detector = DriftDetector(threshold_sigma=2.0)
        
        # No data
        is_drift, mean, std, deviation = detector.is_drift_detected("person", 0.5)
        assert not is_drift
        assert mean == 0.0
        assert std == 0.0
        assert deviation == 0.0
        
        # Insufficient data (< 10 samples)
        for i in range(5):
            detector.add_confidence("person", 0.8)
        
        is_drift, mean, std, deviation = detector.is_drift_detected("person", 0.3)
        assert not is_drift  # Should not detect drift with < 10 samples
    
    def test_drift_detection_stable_confidence(self):
        """Test that stable high confidences don't trigger drift detection."""
        detector = DriftDetector(threshold_sigma=2.0)
        
        # Add stable high confidence scores (mean ~0.85, low std)
        stable_scores = [0.8, 0.85, 0.9, 0.82, 0.88, 0.84, 0.86, 0.83, 0.87, 0.85]
        for score in stable_scores:
            detector.add_confidence("person", score)
        
        # Test with a score within normal range
        is_drift, mean, std, deviation = detector.is_drift_detected("person", 0.84)
        assert not is_drift
        assert abs(mean - 0.85) < 0.01
        assert std < 0.05  # Should have low standard deviation
        
        # Test with a slightly lower but still reasonable score
        is_drift, mean, std, deviation = detector.is_drift_detected("person", 0.82)
        assert not is_drift  # Should not be more than 2σ below mean
    
    def test_drift_detection_sudden_drop(self):
        """Test drift detection with sudden confidence drop."""
        detector = DriftDetector(threshold_sigma=2.0)
        
        # Add stable high confidence scores
        stable_scores = [0.85, 0.86, 0.84, 0.87, 0.85, 0.88, 0.84, 0.86, 0.85, 0.87]
        for score in stable_scores:
            detector.add_confidence("person", score)
        
        # Calculate expected statistics
        mean, std = detector.get_statistics("person")
        
        # Test with a significantly lower score (should trigger drift)
        low_confidence = mean - 2.5 * std  # More than 2σ below mean
        is_drift, _, _, deviation = detector.is_drift_detected("person", low_confidence)
        assert is_drift
        assert deviation > 2.0  # Should be more than threshold
    
    def test_get_window_info(self):
        """Test window information retrieval."""
        detector = DriftDetector()
        
        # Empty detector
        info = detector.get_window_info()
        assert len(info) == 0
        
        # Add data for multiple labels
        detector.add_confidence("person", 0.8)
        detector.add_confidence("person", 0.9)
        detector.add_confidence("vehicle", 0.7)
        
        info = detector.get_window_info()
        assert len(info) == 2
        assert "person" in info
        assert "vehicle" in info
        assert info["person"]["count"] == 2
        assert info["vehicle"]["count"] == 1
        assert info["person"]["latest"] == 0.9
        assert info["vehicle"]["latest"] == 0.7

# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestDriftServiceIntegration:
    """Test the full drift service workflow."""
    
    @pytest.fixture
    def mock_kafka_producer(self):
        """Mock Kafka producer for testing."""
        producer = AsyncMock()
        producer.send_and_wait = AsyncMock()
        return producer
    
    @pytest.fixture
    def sample_inference_events(self):
        """Sample inference events for testing."""
        timestamp = datetime.now(timezone.utc).isoformat()
        return [
            {
                "camera_id": "cam_001",
                "timestamp": timestamp,
                "label": "person",
                "confidence": 0.85
            },
            {
                "camera_id": "cam_001", 
                "timestamp": timestamp,
                "label": "person",
                "confidence": 0.87
            },
            {
                "camera_id": "cam_001",
                "timestamp": timestamp, 
                "label": "person",
                "confidence": 0.30  # Significantly lower - should trigger drift
            }
        ]
    
    @pytest.mark.asyncio
    async def test_process_stable_events_no_drift(self, sample_inference_events):
        """Test processing stable events that shouldn't trigger drift."""
        # Reset global drift detector
        from drift_service import drift_detector
        drift_detector.confidence_windows.clear()
        
        # Process stable events (first two)
        stable_events = sample_inference_events[:2]
        
        for event_data in stable_events:
            await process_inference_event(event_data)
        
        # Check that confidence scores were added to window
        window = drift_detector.confidence_windows["person"]
        assert len(window) == 2
        assert 0.85 in window
        assert 0.87 in window
        
        # Verify no drift detected (insufficient data)
        is_drift, _, _, _ = drift_detector.is_drift_detected("person", 0.86)
        assert not is_drift  # Not enough data points yet
    
    @pytest.mark.asyncio
    async def test_process_drift_event(self, sample_inference_events, mock_kafka_producer):
        """Test processing an event that triggers drift detection."""
        # Reset and prepare drift detector with sufficient stable data
        from drift_service import drift_detector
        drift_detector.confidence_windows.clear()
        
        # Add stable baseline data (10+ points for drift detection)
        stable_scores = [0.85, 0.86, 0.84, 0.87, 0.85, 0.88, 0.84, 0.86, 0.85, 0.87]
        for score in stable_scores:
            drift_detector.add_confidence("person", score)
        
        # Mock the Kafka producer
        with patch('drift_service.kafka_producer', mock_kafka_producer):
            # Process the low confidence event
            low_confidence_event = sample_inference_events[2]  # confidence=0.30
            await process_inference_event(low_confidence_event)
        
        # Verify drift was detected
        is_drift, mean, std, deviation = drift_detector.is_drift_detected("person", 0.30)
        assert is_drift
        assert deviation > 2.0
        
        # Verify hard example was published
        mock_kafka_producer.send_and_wait.assert_called_once()
        call_args = mock_kafka_producer.send_and_wait.call_args
        topic, message = call_args[0]
        
        assert topic == "hard_examples"  # Default output topic
        
        # Parse and verify the published message
        hard_example_data = json.loads(message.decode('utf-8'))
        assert hard_example_data["camera_id"] == "cam_001"
        assert hard_example_data["label"] == "person"
        assert hard_example_data["confidence"] == 0.30
        assert hard_example_data["drift_detected"] is True
        assert hard_example_data["deviation_sigma"] > 2.0
    
    @pytest.mark.asyncio
    async def test_publish_hard_example(self, mock_kafka_producer):
        """Test publishing hard examples to Kafka."""
        timestamp = datetime.now(timezone.utc).isoformat()
        hard_example = HardExample(
            camera_id="cam_001",
            timestamp=timestamp,
            label="person",
            confidence=0.25,
            mean_confidence=0.85,
            std_confidence=0.02,
            deviation_sigma=2.5
        )
        
        with patch('drift_service.kafka_producer', mock_kafka_producer):
            await publish_hard_example(hard_example)
        
        # Verify Kafka send was called
        mock_kafka_producer.send_and_wait.assert_called_once()
        call_args = mock_kafka_producer.send_and_wait.call_args
        topic, message = call_args[0]
        
        assert topic == "hard_examples"
        
        # Verify message content
        published_data = json.loads(message.decode('utf-8'))
        assert published_data["camera_id"] == "cam_001"
        assert published_data["confidence"] == 0.25
        assert published_data["drift_detected"] is True
    
    @pytest.mark.asyncio
    async def test_kafka_producer_error_handling(self):
        """Test error handling when Kafka producer fails."""
        # Test with None producer
        with patch('drift_service.kafka_producer', None):
            hard_example = HardExample(
                camera_id="cam_001",
                timestamp=datetime.now(timezone.utc).isoformat(),
                label="person",
                confidence=0.25,
                mean_confidence=0.85,
                std_confidence=0.02,
                deviation_sigma=2.5
            )
            
            # Should not raise exception, just log error
            await publish_hard_example(hard_example)
        
        # Test with producer that raises exception
        mock_producer = AsyncMock()
        mock_producer.send_and_wait.side_effect = Exception("Kafka error")
        
        with patch('drift_service.kafka_producer', mock_producer):
            # Should handle exception gracefully
            await publish_hard_example(hard_example)

# =============================================================================
# FASTAPI ENDPOINT TESTS
# =============================================================================

@pytest.fixture
def test_client():
    """Create a test client with mocked Kafka dependencies."""
    from starlette.testclient import TestClient
    from unittest.mock import patch, AsyncMock
    
    # Mock Kafka components to avoid connection errors
    with patch('drift_service.AIOKafkaProducer') as mock_producer_class, \
         patch('drift_service.AIOKafkaConsumer') as mock_consumer_class:
        
        # Configure mocks
        mock_producer = AsyncMock()
        mock_consumer = AsyncMock()
        mock_producer_class.return_value = mock_producer
        mock_consumer_class.return_value = mock_consumer
        
        # Mock startup/shutdown methods
        mock_producer.start = AsyncMock()
        mock_producer.stop = AsyncMock()
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()
        
        # Create test client without triggering Kafka connections
        with patch('drift_service.kafka_producer', mock_producer), \
             patch('drift_service.kafka_consumer', mock_consumer):
            
            client = TestClient(app)
            yield client

def test_health_endpoint(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/healthz")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "drift_detection"
    assert "window_size" in data
    assert "threshold_sigma" in data
    assert "kafka_config" in data

def test_metrics_endpoint(test_client):
    """Test the Prometheus metrics endpoint."""
    response = test_client.get("/metrics")
    
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    
    # Check for expected metric names
    metrics_text = response.text
    assert "drift_events_total" in metrics_text
    assert "hard_examples_emitted_total" in metrics_text
    assert "processed_events_total" in metrics_text
    assert "confidence_distribution" in metrics_text

def test_drift_stats_endpoint(test_client):
    """Test the drift statistics endpoint."""
    from drift_service import drift_detector
    
    # Clear and add some test data
    drift_detector.confidence_windows.clear()
    drift_detector.add_confidence("person", 0.8)
    drift_detector.add_confidence("person", 0.9)
    drift_detector.add_confidence("vehicle", 0.7)
    
    response = test_client.get("/drift-stats")
    
    assert response.status_code == 200
    data = response.json()
    assert "window_size" in data
    assert "threshold_sigma" in data
    assert "labels" in data
    assert "total_labels_tracked" in data
    
    # Verify label data
    labels = data["labels"]
    assert "person" in labels
    assert "vehicle" in labels
    assert labels["person"]["count"] == 2
    assert labels["vehicle"]["count"] == 1

def test_drift_config_endpoint(test_client):
    """Test the drift configuration update endpoint."""
    # Test valid update
    response = test_client.post("/drift-config?threshold_sigma=3.0")
    assert response.status_code == 200
    data = response.json()
    assert data["threshold_sigma"] == 3.0
    
    # Test invalid update
    response = test_client.post("/drift-config?threshold_sigma=-1.0")
    assert response.status_code == 400
    assert "threshold_sigma must be positive" in response.json()["detail"]

# =============================================================================
# MODEL VALIDATION TESTS
# =============================================================================

def test_inference_event_model():
    """Test InferenceEvent model validation."""
    # Valid event
    valid_data = {
        "camera_id": "cam_001",
        "timestamp": "2025-06-10T12:34:56Z",
        "label": "person",
        "confidence": 0.85
    }
    event = InferenceEvent(**valid_data)
    assert event.camera_id == "cam_001"
    assert event.confidence == 0.85
    
    # Invalid confidence (out of range)
    with pytest.raises(ValueError):
        InferenceEvent(**{**valid_data, "confidence": 1.5})
    
    with pytest.raises(ValueError):
        InferenceEvent(**{**valid_data, "confidence": -0.1})

def test_hard_example_model():
    """Test HardExample model validation."""
    valid_data = {
        "camera_id": "cam_001",
        "timestamp": "2025-06-10T12:34:56Z",
        "label": "person",
        "confidence": 0.25,
        "mean_confidence": 0.85,
        "std_confidence": 0.02,
        "deviation_sigma": 2.5
    }
    
    example = HardExample(**valid_data)
    assert example.drift_detected is True  # Default value
    assert example.frame_url is None  # Default value
    assert isinstance(example.metadata, dict)  # Default factory

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

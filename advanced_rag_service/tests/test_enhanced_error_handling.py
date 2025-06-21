"""
Test Enhanced Error Handling for Advanced RAG Service

This test file validates the enhanced error handling functionality
including graceful degradation, specific error types, and fallback mechanisms.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import the enhanced error handling types
from error_handling import (
    EnhancedRAGError, WeaviateConnectionError, OpenAIAPIError, 
    EmbeddingGenerationError, TemporalProcessingError, ServiceDegradationError,
    FallbackTemporalRAGResponse, RetryConfig, ErrorType
)
from service_status import service_status_manager, ServiceStatus


class TestEnhancedErrorHandling:
    """Test enhanced error handling patterns"""
    
    def test_specific_error_types(self):
        """Test that specific error types are created correctly"""
        # Test WeaviateConnectionError
        weaviate_error = WeaviateConnectionError("Connection failed", ValueError("network error"))
        assert weaviate_error.error_type == ErrorType.NETWORK_ERROR
        assert "Connection failed" in str(weaviate_error)
        assert isinstance(weaviate_error.original_error, ValueError)
        
        # Test OpenAIAPIError
        openai_error = OpenAIAPIError("API rate limit exceeded")
        assert openai_error.error_type == ErrorType.API_ERROR
        
        # Test EmbeddingGenerationError
        embedding_error = EmbeddingGenerationError("Model not found")
        assert embedding_error.error_type == ErrorType.API_ERROR
        
        # Test TemporalProcessingError
        temporal_error = TemporalProcessingError("Invalid timestamp format")
        assert temporal_error.error_type == ErrorType.VALIDATION_ERROR
        
        # Test ServiceDegradationError
        degradation_error = ServiceDegradationError("Running in degraded mode")
        assert degradation_error.error_type == ErrorType.API_ERROR
    
    def test_fallback_response_creation(self):
        """Test fallback response creation for graceful degradation"""
        # Mock query event
        mock_event = Mock()
        mock_event.label = "person_detected"
        mock_event.camera_id = "cam_001"
        mock_event.timestamp = "2025-06-13T10:30:00Z"
        
        # Create fallback response
        fallback = FallbackTemporalRAGResponse.create_minimal_response(
            mock_event, "Weaviate service unavailable", Exception("Connection timeout")
        )
        
        assert fallback.service_name == "temporal_rag"
        assert fallback.fallback_reason == "Weaviate service unavailable"
        assert fallback.degraded_mode is True
        assert fallback.explanation_confidence == 0.0
        assert len(fallback.retrieved_context) == 0
        assert "Service temporarily degraded" in fallback.linked_explanation
        assert mock_event.label in fallback.linked_explanation
        assert mock_event.camera_id in fallback.linked_explanation
    
    def test_service_status_manager(self):
        """Test service status tracking functionality"""
        # Test initial state
        status = service_status_manager.get_service_status("test_service")
        assert status == ServiceStatus.UNKNOWN
        
        # Test service availability check
        assert not service_status_manager.is_service_available("nonexistent_service")
        
        # Test setting service status
        service_status_manager.services["test_service"].status = ServiceStatus.HEALTHY
        assert service_status_manager.is_service_healthy("test_service")
        assert service_status_manager.is_service_available("test_service")
        
        # Test degraded service detection
        service_status_manager.services["test_service"].status = ServiceStatus.DEGRADED
        degraded = service_status_manager.get_degraded_services()
        assert "test_service" in degraded
        assert service_status_manager.is_service_available("test_service")
        assert not service_status_manager.is_service_healthy("test_service")
        
        # Test unavailable service detection
        service_status_manager.services["test_service"].status = ServiceStatus.UNAVAILABLE
        unavailable = service_status_manager.get_unavailable_services()
        assert "test_service" in unavailable
        assert not service_status_manager.is_service_available("test_service")
    
    @pytest.mark.asyncio
    async def test_health_check_with_timeout(self):
        """Test health check functionality with timeout handling"""
        async def slow_health_check():
            await asyncio.sleep(15)  # Longer than timeout
            return True
        
        # Test timeout handling
        status = await service_status_manager.check_service_health(
            "slow_service", slow_health_check
        )
        assert status == ServiceStatus.UNAVAILABLE
        assert service_status_manager.services["slow_service"].last_error == "Health check timeout"
    
    @pytest.mark.asyncio
    async def test_health_check_with_failure(self):
        """Test health check with service failure"""
        async def failing_health_check():
            raise Exception("Service is down")
        
        status = await service_status_manager.check_service_health(
            "failing_service", failing_health_check
        )
        assert status == ServiceStatus.UNAVAILABLE
        assert "Service is down" in service_status_manager.services["failing_service"].last_error
    
    @pytest.mark.asyncio
    async def test_health_check_degraded_performance(self):
        """Test health check detecting degraded performance"""
        async def slow_but_working_health_check():
            await asyncio.sleep(6)  # Slower than degradation threshold (5s)
            return True
        
        status = await service_status_manager.check_service_health(
            "slow_service", slow_but_working_health_check
        )
        assert status == ServiceStatus.DEGRADED
        assert service_status_manager.services["slow_service"].response_time_ms > 6000
    
    def test_service_health_summary(self):
        """Test service health summary generation"""
        # Set up some test services
        service_status_manager.services["healthy_service"].status = ServiceStatus.HEALTHY
        service_status_manager.services["degraded_service"].status = ServiceStatus.DEGRADED
        service_status_manager.services["unavailable_service"].status = ServiceStatus.UNAVAILABLE
        
        summary = service_status_manager.get_service_health_summary()
        
        assert "healthy_service" in summary
        assert "degraded_service" in summary
        assert "unavailable_service" in summary
        assert summary["healthy_service"]["status"] == "healthy"
        assert summary["degraded_service"]["status"] == "degraded"
        assert summary["unavailable_service"]["status"] == "unavailable"
    
    def test_retry_config_creation(self):
        """Test retry configuration setup"""
        config = RetryConfig(max_attempts=5, base_delay=2.0, exponential_base=3.0)
        assert hasattr(config, 'max_attempts')  # Basic validation that config exists
    
    def test_error_hierarchy(self):
        """Test that error types maintain proper hierarchy"""
        base_error = EnhancedRAGError("Base error", ErrorType.UNKNOWN_ERROR)
        weaviate_error = WeaviateConnectionError("Weaviate error")
        openai_error = OpenAIAPIError("OpenAI error")
        
        # Test inheritance
        assert isinstance(weaviate_error, EnhancedRAGError)
        assert isinstance(openai_error, EnhancedRAGError)
        
        # Test error type categorization
        assert weaviate_error.error_type == ErrorType.NETWORK_ERROR
        assert openai_error.error_type == ErrorType.API_ERROR
        assert base_error.error_type == ErrorType.UNKNOWN_ERROR


if __name__ == "__main__":
    pytest.main([__file__])

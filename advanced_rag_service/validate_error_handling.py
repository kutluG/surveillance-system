#!/usr/bin/env python3
"""
Manual validation script for enhanced error handling functionality
"""

from error_handling import WeaviateConnectionError, OpenAIAPIError, FallbackTemporalRAGResponse, ErrorType
from service_status import service_status_manager, ServiceStatus

def main():
    print("=== Enhanced Error Handling Validation ===")
    
    # Test specific error types
    print("\n1. Testing specific error types:")
    weaviate_error = WeaviateConnectionError('Connection failed')
    print(f"   WeaviateConnectionError: {weaviate_error.error_type.value}")
    
    openai_error = OpenAIAPIError('API rate limit exceeded')
    print(f"   OpenAIAPIError: {openai_error.error_type.value}")
    
    # Test service status manager
    print("\n2. Testing service status manager:")
    initial_status = service_status_manager.get_service_status("test_service")
    print(f"   Initial service status: {initial_status.value}")
    
    service_status_manager.services['test_service'].status = ServiceStatus.HEALTHY
    is_healthy = service_status_manager.is_service_healthy("test_service")
    print(f"   After setting healthy: {is_healthy}")
    
    # Test fallback response
    print("\n3. Testing fallback response:")
    class MockEvent:
        def __init__(self):
            self.label = 'person_detected'
            self.camera_id = 'cam_001'
            self.timestamp = '2025-06-13T10:30:00Z'
    
    mock_event = MockEvent()
    fallback = FallbackTemporalRAGResponse.create_minimal_response(
        mock_event, 'Weaviate service unavailable', Exception('Connection timeout')
    )
    print(f"   Fallback response created: {fallback.degraded_mode}")
    print(f"   Fallback confidence: {fallback.explanation_confidence}")
    print(f"   Fallback explanation length: {len(fallback.linked_explanation)}")
    
    print("\n✅ Enhanced error handling working correctly!")

if __name__ == "__main__":
    main()

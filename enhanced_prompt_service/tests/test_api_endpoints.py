"""
End-to-end API tests for FastAPI endpoints in main.py.

Tests the complete API flow with real HTTP requests using TestClient.
"""
import os
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any
import pytest
from fastapi.testclient import TestClient

# Add the project root to the path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the shared modules before importing main
sys.modules['shared.logging_config'] = Mock()
sys.modules['shared.audit_middleware'] = Mock()
sys.modules['shared.metrics'] = Mock()
sys.modules['shared.auth'] = Mock()
sys.modules['shared.middleware'] = Mock()
sys.modules['shared.config'] = Mock()
sys.modules['shared.models'] = Mock()

# Mock the enhanced_prompt_service modules
sys.modules['enhanced_prompt_service.weaviate_client'] = Mock()
sys.modules['enhanced_prompt_service.clip_store'] = Mock()
sys.modules['enhanced_prompt_service.conversation_manager'] = Mock()
sys.modules['enhanced_prompt_service.llm_client'] = Mock()

# Set up the mocks with proper return values
def setup_mocks():
    """Set up all the required mocks for the FastAPI app."""
    
    # Mock logging
    mock_logger = Mock()
    mock_logger.info = Mock()
    mock_logger.warning = Mock()
    mock_logger.error = Mock()
    sys.modules['shared.logging_config'].configure_logging = Mock(return_value=mock_logger)
    sys.modules['shared.logging_config'].get_logger = Mock(return_value=mock_logger)
    sys.modules['shared.logging_config'].log_context = Mock()
    
    # Mock audit middleware
    sys.modules['shared.audit_middleware'].add_audit_middleware = Mock()
    
    # Mock metrics
    sys.modules['shared.metrics'].instrument_app = Mock()
    
    # Mock auth
    mock_token_data = Mock()
    mock_token_data.sub = "test_user_123"
    sys.modules['shared.auth'].get_current_user = Mock(return_value=mock_token_data)
    sys.modules['shared.auth'].TokenData = Mock
    
    # Mock middleware
    sys.modules['shared.middleware'].add_rate_limiting = Mock()
    
    # Mock config
    mock_config = {
        "redis_url": "redis://localhost:6379/0",
        "vms_service_url": "http://localhost:8001",
        "clip_base_url": "http://localhost:8001/clips",
        "default_clip_expiry_minutes": 60,
        "openai_api_key": "test-key",
        "openai_model": "gpt-4",
        "weaviate_url": "http://localhost:8080"
    }
    sys.modules['shared.config'].get_service_config = Mock(return_value=mock_config)
    
    # Mock models
    sys.modules['shared.models'].QueryResult = Mock
    
    # Mock enhanced_prompt_service modules
    sys.modules['enhanced_prompt_service.weaviate_client'].semantic_search = Mock()
    sys.modules['enhanced_prompt_service.clip_store'].get_clip_url = Mock()
    sys.modules['enhanced_prompt_service.llm_client'].generate_conversational_response = Mock()
    sys.modules['enhanced_prompt_service.llm_client'].generate_follow_up_questions = Mock()
    
    # Mock conversation manager
    mock_conversation_manager_class = Mock()
    mock_conversation_manager = Mock()
    mock_conversation_manager_class.return_value = mock_conversation_manager
    sys.modules['enhanced_prompt_service.conversation_manager'].ConversationManager = mock_conversation_manager_class
    
    return {
        "logger": mock_logger,
        "token_data": mock_token_data,
        "config": mock_config,
        "conversation_manager": mock_conversation_manager
    }

# Set up mocks before importing main
mocks = setup_mocks()

# Now import the main app
from main import app


class TestAPIEndpoints:
    """End-to-end tests for FastAPI endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a TestClient instance for the FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user_token(self):
        """Mock user token for authentication."""
        return "Bearer test-jwt-token"
    
    @pytest.fixture
    def sample_conversation_request(self):
        """Sample conversation request payload."""
        return {
            "query": "Show me security events from camera 1 today",
            "user_context": {"location": "main_entrance"},
            "limit": 5
        }
    
    @pytest.fixture
    def sample_proactive_insight_request(self):
        """Sample proactive insight request payload."""
        return {
            "time_range": "24h",
            "severity_threshold": "medium",
            "include_predictions": True
        }
    
    @pytest.fixture
    def mock_conversation_response(self):
        """Mock conversation response data."""
        return {
            "id": "conv_123",
            "user_id": "test_user_123",
            "created_at": "2025-06-18T10:30:00Z",
            "context": {"location": "main_entrance"}
        }
    
    @pytest.fixture
    def mock_search_results(self):
        """Mock semantic search results."""
        return [
            {
                "event_id": "evt_001",
                "timestamp": "2025-06-18T10:30:00Z",
                "camera_id": "cam_001",
                "event_type": "motion_detected",
                "confidence": 0.95,
                "description": "Motion detected at main entrance"
            },
            {
                "event_id": "evt_002", 
                "timestamp": "2025-06-18T10:35:00Z",
                "camera_id": "cam_001",
                "event_type": "person_detected",
                "confidence": 0.88,
                "description": "Person detected at main entrance"
            }
        ]
    
    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM response data."""
        return {
            "response": "I found 2 security events from camera 1 today. There was motion detected at 10:30 AM followed by a person detection at 10:35 AM at the main entrance.",
            "confidence": 0.92,
            "type": "answer",
            "processing_time": 1200
        }
    
    @pytest.fixture
    def mock_follow_up_questions(self):
        """Mock follow-up questions."""
        return [
            "Would you like to see the video clips for these events?",
            "Do you want to check for similar events from other cameras?",
            "Should I analyze the person detection for more details?"
        ]

    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_conversation_endpoint_success(self, client, mock_user_token, sample_conversation_request, 
                                         mock_conversation_response, mock_search_results, 
                                         mock_llm_response, mock_follow_up_questions):
        """Test successful conversation endpoint."""
        
        # Setup mocks
        with patch('main.conversation_manager') as mock_conv_mgr:
            with patch('main.enhanced_semantic_search') as mock_search:
                with patch('main.generate_conversational_response') as mock_llm:
                    with patch('main.generate_follow_up_questions') as mock_followup:
                        with patch('main.get_clip_url') as mock_clip:
                            
                            # Configure mock returns
                            mock_conv_mgr.create_conversation = AsyncMock(return_value=mock_conversation_response)
                            mock_conv_mgr.add_message = AsyncMock(return_value="msg_123")
                            mock_conv_mgr.get_recent_messages = AsyncMock(return_value=[])
                            
                            mock_search.return_value = mock_search_results
                            mock_llm.return_value = mock_llm_response
                            mock_followup.return_value = mock_follow_up_questions
                            mock_clip.side_effect = lambda event_id: f"http://localhost:8001/clips/{event_id}.mp4"
                            
                            # Make request
                            response = client.post(
                                "/api/v1/conversation",
                                json=sample_conversation_request,
                                headers={"Authorization": mock_user_token}
                            )
                            
                            # Assertions
                            assert response.status_code == 200
                            
                            data = response.json()
                            assert "conversation_id" in data
                            assert "response" in data
                            assert "follow_up_questions" in data
                            assert "evidence" in data
                            assert "clip_links" in data
                            assert "confidence_score" in data
                            assert "response_type" in data
                            assert "metadata" in data
                            
                            # Verify response content
                            assert data["response"] == mock_llm_response["response"]
                            assert data["confidence_score"] == mock_llm_response["confidence"]
                            assert data["response_type"] == mock_llm_response["type"]
                            assert len(data["follow_up_questions"]) == 3
                            assert len(data["evidence"]) == 2
                            assert len(data["clip_links"]) == 2

    def test_conversation_endpoint_missing_query(self, client, mock_user_token):
        """Test conversation endpoint with missing query field."""
        
        invalid_request = {
            "user_context": {"location": "main_entrance"},
            "limit": 5
            # Missing required "query" field
        }
        
        response = client.post(
            "/api/v1/conversation",
            json=invalid_request,
            headers={"Authorization": mock_user_token}
        )
        
        assert response.status_code == 422
        error_detail = response.json()
        assert "detail" in error_detail

    def test_conversation_endpoint_validation_error(self, client, mock_user_token):
        """Test conversation endpoint with invalid data types."""
        
        invalid_request = {
            "query": "Show me events",
            "limit": "invalid_number"  # Should be integer
        }
        
        response = client.post(
            "/api/v1/conversation",
            json=invalid_request,
            headers={"Authorization": mock_user_token}
        )
        
        assert response.status_code == 422

    def test_conversation_endpoint_with_existing_conversation(self, client, mock_user_token, 
                                                            sample_conversation_request,
                                                            mock_conversation_response,
                                                            mock_search_results,
                                                            mock_llm_response,
                                                            mock_follow_up_questions):
        """Test conversation endpoint with existing conversation ID."""
        
        # Include conversation_id in request
        request_with_conv_id = sample_conversation_request.copy()
        request_with_conv_id["conversation_id"] = "existing_conv_456"
        
        with patch('main.conversation_manager') as mock_conv_mgr:
            with patch('main.enhanced_semantic_search') as mock_search:
                with patch('main.generate_conversational_response') as mock_llm:
                    with patch('main.generate_follow_up_questions') as mock_followup:
                        with patch('main.get_clip_url') as mock_clip:
                            
                            # Configure mock returns
                            mock_conv_mgr.get_conversation = AsyncMock(return_value=mock_conversation_response)
                            mock_conv_mgr.add_message = AsyncMock(return_value="msg_456")
                            mock_conv_mgr.get_recent_messages = AsyncMock(return_value=[
                                {"role": "user", "content": "Previous message", "timestamp": "2025-06-18T10:00:00Z"}
                            ])
                            
                            mock_search.return_value = mock_search_results
                            mock_llm.return_value = mock_llm_response
                            mock_followup.return_value = mock_follow_up_questions
                            mock_clip.side_effect = lambda event_id: f"http://localhost:8001/clips/{event_id}.mp4"
                            
                            # Make request
                            response = client.post(
                                "/api/v1/conversation",
                                json=request_with_conv_id,
                                headers={"Authorization": mock_user_token}
                            )
                            
                            # Assertions
                            assert response.status_code == 200
                            
                            # Verify that get_conversation was called instead of create_conversation
                            mock_conv_mgr.get_conversation.assert_called_once_with("existing_conv_456")

    def test_conversation_history_endpoint(self, client, mock_user_token):
        """Test conversation history retrieval endpoint."""
        
        conversation_id = "conv_789"
        mock_messages = [
            {
                "id": "msg_001",
                "role": "user", 
                "content": "Show me today's events",
                "timestamp": "2025-06-18T10:00:00Z"
            },
            {
                "id": "msg_002",
                "role": "assistant",
                "content": "I found 3 events today...",
                "timestamp": "2025-06-18T10:00:15Z"
            }
        ]
        
        with patch('main.conversation_manager') as mock_conv_mgr:
            mock_conv_mgr.get_recent_messages = AsyncMock(return_value=mock_messages)
            
            response = client.get(
                f"/api/v1/conversation/{conversation_id}/history",
                headers={"Authorization": mock_user_token}
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert "conversation_id" in data
            assert "messages" in data
            assert data["conversation_id"] == conversation_id
            assert len(data["messages"]) == 2
            assert data["messages"][0]["role"] == "user"
            assert data["messages"][1]["role"] == "assistant"

    def test_conversation_history_endpoint_with_limit(self, client, mock_user_token):
        """Test conversation history endpoint with custom limit."""
        
        conversation_id = "conv_789"
        
        with patch('main.conversation_manager') as mock_conv_mgr:
            mock_conv_mgr.get_recent_messages = AsyncMock(return_value=[])
            
            response = client.get(
                f"/api/v1/conversation/{conversation_id}/history?limit=10",
                headers={"Authorization": mock_user_token}
            )
            
            assert response.status_code == 200
            mock_conv_mgr.get_recent_messages.assert_called_once_with(conversation_id, limit=10)

    def test_delete_conversation_endpoint(self, client, mock_user_token):
        """Test conversation deletion endpoint."""
        
        conversation_id = "conv_to_delete"
        
        with patch('main.conversation_manager') as mock_conv_mgr:
            mock_conv_mgr.delete_conversation = AsyncMock(return_value=True)
            
            response = client.delete(
                f"/api/v1/conversation/{conversation_id}",
                headers={"Authorization": mock_user_token}
            )
            
            assert response.status_code == 200
            
            data = response.json()
            assert data["message"] == "Conversation deleted successfully"
            mock_conv_mgr.delete_conversation.assert_called_once_with(conversation_id)

    def test_proactive_insights_endpoint(self, client, mock_user_token, sample_proactive_insight_request):
        """Test proactive insights endpoint."""
        
        mock_insights = [
            {
                "type": "anomaly_detection",
                "message": "Unusual activity detected in Zone A during off-hours",
                "suggested_actions": [
                    "Review security footage for the past 2 hours",
                    "Check if authorized personnel were present"
                ],
                "evidence": [
                    {"event_id": "evt_003", "timestamp": "2025-06-18T02:30:00Z"}
                ],
                "clip_links": ["http://localhost:8001/clips/evt_003.mp4"],
                "confidence": 0.85,
                "severity": "medium",
                "timestamp": "2025-06-18T10:30:00Z"
            }
        ]
        
        mock_conversation_response = {
            "id": "insight_conv_001",
            "user_id": "test_user_123",
            "created_at": "2025-06-18T10:30:00Z"
        }
        
        with patch('main.analyze_system_patterns') as mock_analyze:
            with patch('main.conversation_manager') as mock_conv_mgr:
                
                mock_analyze.return_value = mock_insights
                mock_conv_mgr.create_conversation = AsyncMock(return_value=mock_conversation_response)
                
                response = client.get(
                    "/api/v1/proactive-insights",
                    params=sample_proactive_insight_request,
                    headers={"Authorization": mock_user_token}
                )
                
                assert response.status_code == 200
                
                data = response.json()
                assert isinstance(data, list)
                assert len(data) == 1
                
                insight = data[0]
                assert "conversation_id" in insight
                assert "response" in insight
                assert "follow_up_questions" in insight
                assert "evidence" in insight
                assert "clip_links" in insight
                assert "confidence_score" in insight
                assert "response_type" in insight
                assert insight["response_type"] == "proactive_insight"

    def test_proactive_insights_endpoint_default_params(self, client, mock_user_token):
        """Test proactive insights endpoint with default parameters."""
        
        with patch('main.analyze_system_patterns') as mock_analyze:
            with patch('main.conversation_manager') as mock_conv_mgr:
                
                mock_analyze.return_value = []
                mock_conv_mgr.create_conversation = AsyncMock()
                
                response = client.get(
                    "/api/v1/proactive-insights",
                    headers={"Authorization": mock_user_token}
                )
                
                assert response.status_code == 200
                
                # Verify default parameters were used
                mock_analyze.assert_called_once()
                call_args = mock_analyze.call_args[1]
                assert call_args["time_range"] == "24h"
                assert call_args["severity_threshold"] == "medium"
                assert call_args["include_predictions"] is True

    def test_authentication_required(self, client, sample_conversation_request):
        """Test that endpoints require authentication."""
        
        # Test conversation endpoint without auth header
        response = client.post(
            "/api/v1/conversation",
            json=sample_conversation_request
        )
        
        # Should return authentication error
        assert response.status_code in [401, 403]

    def test_invalid_json_payload(self, client, mock_user_token):
        """Test endpoint with invalid JSON payload."""
        
        response = client.post(
            "/api/v1/conversation",
            data="invalid json",
            headers={
                "Authorization": mock_user_token,
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 422

    def test_conversation_endpoint_server_error(self, client, mock_user_token, sample_conversation_request):
        """Test conversation endpoint with internal server error."""
        
        with patch('main.conversation_manager') as mock_conv_mgr:
            # Simulate server error
            mock_conv_mgr.create_conversation = AsyncMock(side_effect=Exception("Database connection failed"))
            
            response = client.post(
                "/api/v1/conversation",
                json=sample_conversation_request,
                headers={"Authorization": mock_user_token}
            )
            
            assert response.status_code == 500
            error_detail = response.json()
            assert "detail" in error_detail
            assert error_detail["detail"] == "Conversation processing failed"

    def test_conversation_history_server_error(self, client, mock_user_token):
        """Test conversation history endpoint with server error."""
        
        conversation_id = "conv_error"
        
        with patch('main.conversation_manager') as mock_conv_mgr:
            mock_conv_mgr.get_recent_messages = AsyncMock(side_effect=Exception("Redis connection failed"))
            
            response = client.get(
                f"/api/v1/conversation/{conversation_id}/history",
                headers={"Authorization": mock_user_token}
            )
            
            assert response.status_code == 500
            error_detail = response.json()
            assert error_detail["detail"] == "Failed to retrieve conversation history"

    def test_proactive_insights_server_error(self, client, mock_user_token):
        """Test proactive insights endpoint with server error."""
        
        with patch('main.analyze_system_patterns') as mock_analyze:
            mock_analyze.side_effect = Exception("Analysis service unavailable")
            
            response = client.get(
                "/api/v1/proactive-insights",
                headers={"Authorization": mock_user_token}
            )
            
            assert response.status_code == 500
            error_detail = response.json()
            assert error_detail["detail"] == "Insights generation failed"

    def test_conversation_endpoint_large_payload(self, client, mock_user_token, mock_conversation_response,
                                               mock_search_results, mock_llm_response, mock_follow_up_questions):
        """Test conversation endpoint with large query payload."""
        
        large_request = {
            "query": "A" * 10000,  # Very long query
            "user_context": {"location": "main_entrance", "additional_data": "B" * 5000},
            "limit": 100  # Large limit
        }
        
        with patch('main.conversation_manager') as mock_conv_mgr:
            with patch('main.enhanced_semantic_search') as mock_search:
                with patch('main.generate_conversational_response') as mock_llm:
                    with patch('main.generate_follow_up_questions') as mock_followup:
                        with patch('main.get_clip_url') as mock_clip:
                            
                            # Configure mock returns
                            mock_conv_mgr.create_conversation = AsyncMock(return_value=mock_conversation_response)
                            mock_conv_mgr.add_message = AsyncMock(return_value="msg_123")
                            mock_conv_mgr.get_recent_messages = AsyncMock(return_value=[])
                            
                            mock_search.return_value = mock_search_results
                            mock_llm.return_value = mock_llm_response
                            mock_followup.return_value = mock_follow_up_questions
                            mock_clip.side_effect = lambda event_id: f"http://localhost:8001/clips/{event_id}.mp4"
                            
                            response = client.post(
                                "/api/v1/conversation",
                                json=large_request,
                                headers={"Authorization": mock_user_token}
                            )
                            
                            # Should handle large payload gracefully
                            assert response.status_code == 200

    def test_conversation_endpoint_edge_cases(self, client, mock_user_token):
        """Test conversation endpoint with edge case inputs."""
        
        edge_cases = [
            {"query": ""},  # Empty query
            {"query": " "},  # Whitespace only
            {"query": "valid query", "limit": 0},  # Zero limit
            {"query": "valid query", "limit": -1},  # Negative limit
        ]
        
        for edge_case in edge_cases:
            response = client.post(
                "/api/v1/conversation",
                json=edge_case,
                headers={"Authorization": mock_user_token}
            )
            
            # Some edge cases might be handled gracefully, others should return validation errors
            assert response.status_code in [200, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

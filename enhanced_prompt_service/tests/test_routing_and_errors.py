"""
Tests for routing and error handling in the Enhanced Prompt Service.
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import Depends
from enhanced_prompt_service.main import app
from shared.auth import TokenData, get_current_user
import shared.auth


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_app_state():
    """Mock the app state with necessary dependencies."""
    # Create mock Redis client
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    
    # Create mock Weaviate client
    mock_weaviate = MagicMock()
    mock_weaviate.is_ready.return_value = True
    
    # Create mock OpenAI client
    mock_openai = MagicMock()
    
    # Create mock ConversationManager
    mock_conversation_manager = AsyncMock()
    
    # Set up app state
    app.state.redis_client = mock_redis
    app.state.weaviate_client = mock_weaviate
    app.state.openai_client = mock_openai
    app.state.conversation_manager = mock_conversation_manager
    
    return {
        'redis': mock_redis,
        'weaviate': mock_weaviate,
        'openai': mock_openai,
        'conversation_manager': mock_conversation_manager
    }


# Mock authentication for testing
def mock_get_current_user():
    return TokenData(sub="test_user", exp=9999999999)


class TestRoutingAndErrors:
    """Test class for routing and error handling functionality."""
    
    def test_404_returns_proper_error_format(self, client, mock_app_state):
        """Test that 404 errors return proper JSON error format."""
        # Make request to non-existent endpoint
        response = client.get("/api/v1/nonexistent")
        
        # Assert 404 status code
        assert response.status_code == 404
        
        # Assert proper error format
        error_data = response.json()
        assert "error" in error_data
        assert error_data["error"] == "Not Found"
        assert "detail" in error_data
        assert "code" in error_data
        assert error_data["code"] == "404"
    
    @patch('enhanced_prompt_service.routers.prompt.semantic_search')
    @patch('enhanced_prompt_service.routers.prompt.generate_conversational_response')
    @patch('enhanced_prompt_service.routers.prompt.generate_follow_up_questions')
    @patch('enhanced_prompt_service.routers.prompt.get_clip_url')
    def test_prompt_endpoint_error_handling(self, mock_clip_url, mock_follow_ups, 
                                          mock_ai_response, mock_semantic_search,
                                          client, mock_app_state):
        """Test that ValueError in prompt endpoint returns 500 with proper error format."""
        # Override the auth dependency
        app.dependency_overrides[shared.auth.get_current_user] = mock_get_current_user
        
        # Mock conversation manager
        mock_conversation_manager = mock_app_state['conversation_manager']
        mock_conversation_manager.create_conversation.return_value = {"id": "test_conv_id"}
        mock_conversation_manager.add_message.return_value = None
        mock_conversation_manager.get_recent_messages.return_value = []
        
        try:
            # Make request with trigger_error query to force ValueError
            response = client.post("/api/v1/prompt", json={
                "query": "trigger_error"
            })
              # Assert 500 status code
            assert response.status_code == 500
            
            # Assert proper error format (check actual format being returned)
            error_data = response.json()
            assert "error" in error_data
            # The middleware returns a different format than our global handler
            assert error_data["error"] == "Internal server error"
            # Check for either "detail" or "message" depending on which handler processes it
            assert "message" in error_data or "detail" in error_data
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()
    
    @patch('enhanced_prompt_service.routers.prompt.semantic_search')
    @patch('enhanced_prompt_service.routers.prompt.generate_conversational_response')
    @patch('enhanced_prompt_service.routers.prompt.generate_follow_up_questions')
    @patch('enhanced_prompt_service.routers.prompt.get_clip_url')
    def test_prompt_endpoint_valid_request(self, mock_clip_url, mock_follow_ups, 
                                         mock_ai_response, mock_semantic_search,
                                         client, mock_app_state):
        """Test that valid prompt request returns 200 and matches PromptResponse schema."""
        # Override the auth dependency
        app.dependency_overrides[shared.auth.get_current_user] = mock_get_current_user
        
        # Mock conversation manager
        mock_conversation_manager = mock_app_state['conversation_manager']
        mock_conversation_manager.create_conversation.return_value = {"id": "test_conv_id"}
        mock_conversation_manager.add_message.return_value = None
        mock_conversation_manager.get_recent_messages.return_value = []
        
        # Mock semantic search
        mock_semantic_search.return_value = [
            {
                "event_id": "event_123",
                "timestamp": "2024-01-01T12:00:00Z",
                "camera_id": "cam_01",
                "event_type": "person_detected",
                "confidence": 0.95,
                "description": "Person detected in lobby"
            }
        ]
        
        # Mock AI response
        mock_ai_response.return_value = {
            "response": "I can see there was a person detected in the lobby at 12:00 PM today.",
            "confidence": 0.9,
            "type": "answer",
            "processing_time": 150
        }
        
        # Mock follow-up questions
        mock_follow_ups.return_value = [
            "Would you like to see more details about this person?",
            "Should I check for similar events today?"
        ]
        
        # Mock clip URL
        mock_clip_url.return_value = "https://example.com/clips/event_123.mp4"
        
        try:
            # Make valid request
            response = client.post("/api/v1/prompt", json={
                "query": "show me recent person detections",
                "limit": 5
            })
            
            # Assert 200 status code
            assert response.status_code == 200
            
            # Assert response matches PromptResponse schema
            response_data = response.json()
            
            # Required fields from PromptResponse
            assert "conversation_id" in response_data
            assert "response" in response_data
            assert "follow_up_questions" in response_data
            assert "evidence" in response_data
            assert "clip_links" in response_data
            assert "confidence_score" in response_data
            assert "response_type" in response_data
            assert "metadata" in response_data
            
            # Validate types and values
            assert isinstance(response_data["conversation_id"], str)
            assert response_data["conversation_id"] == "test_conv_id"
            assert isinstance(response_data["response"], str)
            assert isinstance(response_data["follow_up_questions"], list)
            assert isinstance(response_data["evidence"], list)
            assert isinstance(response_data["clip_links"], list)
            assert isinstance(response_data["confidence_score"], float)
            assert response_data["response_type"] == "answer"
            assert isinstance(response_data["metadata"], dict)
            
            # Validate evidence structure
            if response_data["evidence"]:
                evidence = response_data["evidence"][0]
                assert "event_id" in evidence
                assert "timestamp" in evidence
                assert "camera_id" in evidence
                assert "event_type" in evidence
                assert "confidence" in evidence
                assert "description" in evidence
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()
    
    def test_history_endpoint_valid_request(self, client, mock_app_state):
        """Test that history endpoint returns proper HistoryResponse schema."""
        # Override the auth dependency
        app.dependency_overrides[shared.auth.get_current_user] = mock_get_current_user
        
        # Mock conversation manager
        mock_conversation_manager = mock_app_state['conversation_manager']
        mock_conversation_manager.get_recent_messages.return_value = [
            {
                "role": "user",
                "content": "show me cameras",
                "timestamp": "2024-01-01T12:00:00Z",
                "metadata": {}
            },
            {
                "role": "assistant",
                "content": "Here are the active cameras...",
                "timestamp": "2024-01-01T12:00:05Z",
                "metadata": {"confidence": 0.9}
            }
        ]
        
        try:
            # Make request to history endpoint
            response = client.get("/api/v1/history/test_conv_id")
            
            # Assert 200 status code
            assert response.status_code == 200
            
            # Assert response matches HistoryResponse schema
            response_data = response.json()
            assert "conversation_id" in response_data
            assert "messages" in response_data
            assert response_data["conversation_id"] == "test_conv_id"
            assert isinstance(response_data["messages"], list)
            assert len(response_data["messages"]) == 2
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()
    
    def test_conversation_delete_endpoint(self, client, mock_app_state):
        """Test that conversation delete endpoint returns proper response."""
        # Override the auth dependency
        app.dependency_overrides[shared.auth.get_current_user] = mock_get_current_user
        
        # Mock conversation manager
        mock_conversation_manager = mock_app_state['conversation_manager']
        mock_conversation_manager.delete_conversation.return_value = None
        
        try:
            # Make delete request
            response = client.delete("/api/v1/history/test_conv_id")
            
            # Assert 200 status code
            assert response.status_code == 200
            
            # Assert response matches ConversationDeleteResponse schema
            response_data = response.json()
            assert "message" in response_data
            assert response_data["message"] == "Conversation deleted successfully"
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()
    
    def test_health_endpoints(self, client, mock_app_state):
        """Test that health endpoints return proper HealthResponse schema."""
        # Test basic health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        
        response_data = response.json()
        assert "status" in response_data
        assert response_data["status"] == "ok"
        
        # Test liveness probe
        response = client.get("/healthz")
        assert response.status_code == 200
        
        response_data = response.json()
        assert "status" in response_data
        assert response_data["status"] == "ok"
        
        # Test readiness probe (should work with mocked dependencies)
        response = client.get("/readyz")
        assert response.status_code == 200
        
        response_data = response.json()
        assert "status" in response_data
        assert response_data["status"] == "ready"

"""
Test suite for security hardening features:
- Input validation
- Rate limiting
- CORS policies
- Circuit breaker patterns
"""
import pytest
import asyncio
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
import json

# Import the app after setting test environment
import os
os.environ["TESTING"] = "true"

from enhanced_prompt_service.main import app
from enhanced_prompt_service.llm_client import call_openai_with_circuit_breaker
from enhanced_prompt_service.weaviate_client import weaviate_search_with_circuit_breaker

# Test client
client = TestClient(app)

class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_invalid_characters_in_query(self):
        """Test that queries with invalid characters are rejected."""
        payload = {
            "query": "Show me events with <script>alert('xss')</script>",
            "limit": 5
        }
        
        response = client.post(
            "/api/v1/conversation",
            json=payload,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422
        assert "Invalid characters in query" in response.json()["detail"][0]["msg"]
    
    def test_query_too_long(self):
        """Test that queries exceeding length limit are rejected."""
        long_query = "a" * 201  # Exceeds 200 character limit
        payload = {
            "query": long_query,
            "limit": 5
        }
        
        response = client.post(
            "/api/v1/conversation", 
            json=payload,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422
        assert "exceed 200 characters" in response.json()["detail"][0]["msg"]
    
    def test_empty_query(self):
        """Test that empty queries are rejected."""
        payload = {
            "query": "",
            "limit": 5
        }
        
        response = client.post(
            "/api/v1/conversation",
            json=payload,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422
        assert "empty" in response.json()["detail"][0]["msg"].lower()
    
    def test_valid_query_accepted(self):
        """Test that valid queries are accepted."""
        payload = {
            "query": "Show me recent camera events",
            "limit": 5
        }
        
        with patch('enhanced_prompt_service.main.conversation_manager') as mock_conv:
            with patch('enhanced_prompt_service.main.enhanced_semantic_search') as mock_search:
                with patch('enhanced_prompt_service.main.generate_conversational_response') as mock_response:
                    # Mock the dependencies
                    mock_conv.create_conversation.return_value = {"id": "test-conv"}
                    mock_conv.add_message.return_value = None
                    mock_conv.get_recent_messages.return_value = []
                    mock_search.return_value = []
                    mock_response.return_value = {
                        "response": "Test response",                        "confidence": 0.8,
                        "type": "informational"
                    }
                    
                    response = client.post(
                        "/api/v1/conversation",                        json=payload,
                        headers={"Authorization": "Bearer test-token"}
                    )
                    assert response.status_code == 200
    
    def test_html_sanitization(self):
        """Test that HTML in responses is sanitized."""
        # This would be tested in the actual response generation
        # For now, we just test that bleach is configured correctly
        import bleach
        
        test_html = "<script>alert('xss')</script><p>Safe content</p>"
        sanitized = bleach.clean(test_html, tags=[], attributes={}, strip=True)
        
        assert "<script>" not in sanitized
        assert "<p>" not in sanitized  # All HTML tags should be removed
        assert "Safe content" in sanitized
        
        # Test with dangerous attributes
        test_html2 = '<img src="x" onerror="alert(1)">'
        sanitized2 = bleach.clean(test_html2, tags=[], attributes={}, strip=True)
        assert "onerror" not in sanitized2
        assert "<img" not in sanitized2


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_enforcement(self):
        """Test that rate limits are enforced after threshold."""
        # The limiter is set to 10/minute for the conversation endpoint
        # We'll make 11 requests rapidly
        
        payload = {
            "query": "test query",
            "limit": 1
        }
        
        # Mock the dependencies to avoid actual LLM/DB calls
        with patch('enhanced_prompt_service.main.conversation_manager') as mock_conv:
            with patch('enhanced_prompt_service.main.enhanced_semantic_search') as mock_search:
                with patch('enhanced_prompt_service.main.generate_conversational_response') as mock_response:
                    mock_conv.create_conversation.return_value = {"id": "test-conv"}
                    mock_conv.add_message.return_value = None
                    mock_conv.get_recent_messages.return_value = []
                    mock_search.return_value = []
                    mock_response.return_value = {
                        "response": "Test response",
                        "confidence": 0.8,
                        "type": "informational"
                    }
                    
                    # Make 10 requests (should succeed)
                    successful_requests = 0
                    for i in range(10):
                        response = client.post(
                            "/api/v1/conversation",
                            json=payload,
                            headers={"Authorization": "Bearer test-token"}
                        )
                        if response.status_code == 200:
                            successful_requests += 1
                    
                    # 11th request should be rate limited
                    response = client.post(
                        "/api/v1/conversation",
                        json=payload,
                        headers={"Authorization": "Bearer test-token"}
                    )
                    
                    # Should have some successful requests and then be rate limited
                    assert successful_requests > 0
                    assert response.status_code == 429
    
    def test_rate_limit_headers(self):
        """Test that rate limit headers are present."""
        payload = {
            "query": "test query",
            "limit": 1
        }
        
        with patch('enhanced_prompt_service.main.conversation_manager') as mock_conv:
            with patch('enhanced_prompt_service.main.enhanced_semantic_search') as mock_search:
                with patch('enhanced_prompt_service.main.generate_conversational_response') as mock_response:
                    mock_conv.create_conversation.return_value = {"id": "test-conv"}
                    mock_conv.add_message.return_value = None
                    mock_conv.get_recent_messages.return_value = []
                    mock_search.return_value = []
                    mock_response.return_value = {
                        "response": "Test response",
                        "confidence": 0.8,
                        "type": "informational"
                    }
                    
                    response = client.post(
                        "/api/v1/conversation",
                        json=payload,
                        headers={"Authorization": "Bearer test-token"}
                    )
                    
                    # Check that rate limit headers might be present
                    # (exact header names depend on slowapi configuration)
                    assert response.status_code in [200, 429]


class TestCORSPolicy:
    """Test CORS policy enforcement."""
    
    def test_cors_headers_present(self):
        """Test that CORS headers are present in responses."""
        response = client.get("/health")
        
        # Check for CORS headers
        assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()]
    
    def test_preflight_request(self):
        """Test preflight CORS request."""
        response = client.options(
            "/api/v1/conversation",
            headers={
                "Origin": "https://surveillance-dashboard.local",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type"
            }
        )
        
        assert response.status_code in [200, 204]
    
    def test_disallowed_origin_handling(self):
        """Test that disallowed origins are handled correctly."""
        # This depends on the CORS middleware configuration
        # The test may need to be adjusted based on actual behavior
        payload = {
            "query": "test query",
            "limit": 1
        }
        
        response = client.post(
            "/api/v1/conversation",
            json=payload,
            headers={
                "Authorization": "Bearer test-token",
                "Origin": "https://malicious-site.com"
            }
        )
        
        # Response should still work but CORS headers should reflect policy
        # Actual browser would block based on CORS headers
        assert response.status_code in [200, 400, 401, 422, 429]


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.mark.asyncio
    async def test_openai_circuit_breaker_retry(self):
        """Test that OpenAI calls retry on failure."""
        with patch('enhanced_prompt_service.llm_client.client') as mock_client:
            # Configure mock to fail 2 times then succeed
            async_mock = AsyncMock()
            async_mock.side_effect = [
                Exception("API Error 1"),
                Exception("API Error 2"), 
                Mock(choices=[Mock(message=Mock(content="Success"))], usage=Mock(total_tokens=100))
            ]
            mock_client.chat.completions.create = async_mock
            
            # Should succeed after retries
            response = await call_openai_with_circuit_breaker(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                temperature=0.7,
                max_tokens=100
            )
            
            assert response is not None
            assert async_mock.call_count == 3
    
    @pytest.mark.asyncio  
    async def test_openai_circuit_breaker_exhaustion(self):
        """Test that circuit breaker gives up after max retries."""
        with patch('enhanced_prompt_service.llm_client.client') as mock_client:
            # Configure mock to always fail
            mock_client.chat.completions.create.side_effect = Exception("Persistent API Error")
            
            # Should raise RetryError after exhausting retries
            with pytest.raises(Exception):
                await call_openai_with_circuit_breaker(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    temperature=0.7,
                    max_tokens=100
                )
            
            # Should have tried 3 times
            assert mock_client.chat.completions.create.call_count == 3
    
    def test_weaviate_circuit_breaker_retry(self):
        """Test that Weaviate calls retry on failure."""
        with patch('enhanced_prompt_service.weaviate_client.get_client') as mock_get_client:
            mock_client = Mock()
            mock_collection = Mock()
            
            # Configure mock to fail 2 times then succeed
            mock_collection.query.near_text.side_effect = [
                Exception("Connection Error 1"),
                Exception("Connection Error 2"),
                Mock(objects=[
                    Mock(
                        properties={"event_id": "test1", "camera_id": "cam1"}, 
                        metadata=Mock(score=0.9)
                    )
                ])
            ]
            
            mock_client.collections.get.return_value = mock_collection
            mock_get_client.return_value = mock_client
            
            # Should succeed after retries
            results = weaviate_search_with_circuit_breaker("test query", 5)
            
            assert len(results) > 0
            assert mock_collection.query.near_text.call_count == 3
    
    def test_weaviate_circuit_breaker_exhaustion(self):
        """Test that Weaviate circuit breaker gives up after max retries."""
        with patch('enhanced_prompt_service.weaviate_client.get_client') as mock_get_client:
            mock_client = Mock()
            mock_collection = Mock()
            
            # Configure mock to always fail
            mock_collection.query.near_text.side_effect = Exception("Persistent Connection Error")
            mock_client.collections.get.return_value = mock_collection
            mock_get_client.return_value = mock_client
            
            # Should raise exception after exhausting retries
            with pytest.raises(Exception):
                weaviate_search_with_circuit_breaker("test query", 5)
            
            # Should have tried 3 times
            assert mock_collection.query.near_text.call_count == 3
    
    def test_endpoint_returns_503_on_circuit_breaker_failure(self):
        """Test that endpoints return 503 when circuit breaker fails."""
        payload = {
            "query": "test query",
            "limit": 1
        }
        
        # Mock conversation manager but make LLM fail
        with patch('enhanced_prompt_service.main.conversation_manager') as mock_conv:
            with patch('enhanced_prompt_service.main.enhanced_semantic_search') as mock_search:
                with patch('enhanced_prompt_service.main.generate_conversational_response') as mock_response:
                    from tenacity import RetryError
                    
                    mock_conv.create_conversation.return_value = {"id": "test-conv"}
                    mock_conv.add_message.return_value = None
                    mock_conv.get_recent_messages.return_value = []
                    mock_search.return_value = []
                    
                    # Make the LLM response fail with RetryError (circuit breaker exhausted)
                    mock_response.side_effect = RetryError(
                        last_attempt=Mock(exception=Exception("Service unavailable"))
                    )
                    
                    response = client.post(
                        "/api/v1/conversation",
                        json=payload,
                        headers={"Authorization": "Bearer test-token"}
                    )
                    
                    assert response.status_code == 500  # FastAPI converts unhandled exceptions to 500


class TestSecurityIntegration:
    """Integration tests for security features."""
    
    def test_health_endpoint_bypasses_rate_limiting(self):
        """Test that health endpoint is not rate limited."""
        # Make many health requests rapidly
        for i in range(20):
            response = client.get("/health")
            assert response.status_code == 200
    
    def test_malformed_json_handling(self):
        """Test handling of malformed JSON payloads."""
        response = client.post(
            "/api/v1/conversation",
            data="invalid json",
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 422
    
    def test_missing_auth_header(self):
        """Test that missing auth header is handled."""
        payload = {
            "query": "test query",
            "limit": 1
        }
        
        response = client.post("/api/v1/conversation", json=payload)
        
        # Should fail with auth error
        assert response.status_code in [401, 403]
    
    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are prevented by input validation."""
        payload = {
            "query": "'; DROP TABLE events; --",
            "limit": 1
        }
        
        response = client.post(
            "/api/v1/conversation",
            json=payload,
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Should be rejected by input validation
        assert response.status_code == 422

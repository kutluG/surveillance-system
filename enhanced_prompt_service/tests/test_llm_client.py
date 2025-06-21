"""
Unit tests for llm_client.py - Enhanced LLM client with conversational responses and follow-up generation.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Import the module to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_client import (
    generate_conversational_response,
    generate_follow_up_questions,
    generate_proactive_insights
)


class TestGenerateConversationalResponse:
    """Test cases for generate_conversational_response function."""
    
    @patch('llm_client.client')
    @patch('llm_client.config', {'openai_model': 'gpt-4', 'openai_api_key': 'test-key'})
    def test_successful_response_generation(self, mock_client):
        """Test successful conversational response generation."""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Based on the surveillance data, I can see there were several security events today."
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 150
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test data
        query = "What security events happened today?"
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi, how can I help you?"}
        ]
        search_results = [
            {
                "event_id": "evt-001",
                "timestamp": "2025-06-18T10:00:00Z",
                "camera_id": "cam-001",
                "event_type": "person_detected",
                "details": "Person detected at main entrance",
                "confidence": 0.95
            }
        ]
        
        # Execute
        result = generate_conversational_response(
            query=query,
            conversation_history=conversation_history,
            search_results=search_results
        )
        
        # Assertions
        assert isinstance(result, dict)
        assert "response" in result
        assert "confidence" in result
        assert "evidence_ids" in result
        assert result["response"] == "Based on the surveillance data, I can see there were several security events today."
        assert result["confidence"] > 0.5
        assert "evt-001" in result["evidence_ids"]
        
        # Verify OpenAI API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4"
        assert call_args[1]["temperature"] == 0.7
        assert call_args[1]["max_tokens"] == 1000
    
    @patch('llm_client.client')
    @patch('llm_client.config', {'openai_model': 'gpt-4', 'openai_api_key': 'test-key'})
    def test_response_with_system_context(self, mock_client):
        """Test response generation with additional system context."""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "I've detected increased activity patterns."
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 120
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test with system context
        system_context = {
            "proactive_insights": ["Increased activity at main entrance"],
            "patterns": "Peak activity 8-9 AM",
            "anomalies": "Unusual motion detected"
        }
        
        result = generate_conversational_response(
            query="Tell me about current patterns",
            conversation_history=[],
            search_results=[],
            system_context=system_context
        )
        
        # Assertions        assert result["response"] == "I've detected increased activity patterns."
        assert result["metadata"]["system_insights"] is True
        
        # Check that system context was included in the prompt
        call_args = mock_client.chat.completions.create.call_args
        user_message = call_args[1]["messages"][1]["content"]
        assert "System Insights" in user_message
        assert "Detected Patterns" in user_message
        assert "Recent Anomalies" in user_message
    
    @patch('llm_client.client')
    @patch('llm_client.config', {'openai_model': 'gpt-4', 'openai_api_key': 'test-key'})
    def test_openai_api_error_handling(self, mock_client):
        """Test handling of OpenAI API errors."""
        from openai import APIConnectionError
          # Mock API error - APIConnectionError requires a request parameter
        mock_request = Mock()
        mock_client.chat.completions.create.side_effect = APIConnectionError(request=mock_request)
        
        # Execute and expect exception
        with pytest.raises(ValueError, match="Failed to generate conversational response"):
            generate_conversational_response(
                query="Test query",
                conversation_history=[],
                search_results=[]
            )
    
    @patch('llm_client.client')
    @patch('llm_client.config', {'openai_model': 'gpt-4', 'openai_api_key': 'test-key'})
    def test_empty_search_results(self, mock_client):
        """Test response generation with no search results."""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "I don't have specific events to show you right now."
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 80
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result = generate_conversational_response(
            query="Show me events",
            conversation_history=[],
            search_results=[]  # Empty results
        )
          # Assertions
        assert result["confidence"] == 0.5  # Base confidence only, no search results or conversation
        assert result["context_used"] == 0
        assert len(result["evidence_ids"]) == 0
        
        # Check prompt contains "No specific events found"
        call_args = mock_client.chat.completions.create.call_args
        user_message = call_args[1]["messages"][1]["content"]
        assert "No specific events found" in user_message


class TestGenerateFollowUpQuestions:
    """Test cases for generate_follow_up_questions function."""
    
    @patch('llm_client.client')
    @patch('llm_client.config', {'openai_model': 'gpt-4', 'openai_api_key': 'test-key'})
    def test_successful_json_follow_up_generation(self, mock_client):
        """Test successful follow-up question generation with valid JSON response."""
        # Setup mock response with valid JSON
        follow_up_questions = [
            "Can you show me more details about these events?",
            "What cameras are involved in these detections?",
            "Are there any patterns in the timing?",
            "How can I set up alerts for similar events?"
        ]
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(follow_up_questions)
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 100
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test data
        query = "Show me recent security events"
        response = "I found 3 recent security events at your main entrance."
        conversation_history = []
        search_results = [
            {"event_id": "evt-001", "camera_id": "cam-001", "event_type": "person_detected"}
        ]
        
        # Execute
        result = generate_follow_up_questions(
            query=query,
            response=response,
            conversation_history=conversation_history,
            search_results=search_results
        )
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 4
        assert result == follow_up_questions
        
        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.6
        assert call_args[1]["max_tokens"] == 400
    
    @patch('llm_client.client')
    @patch('llm_client.config', {'openai_model': 'gpt-4', 'openai_api_key': 'test-key'})
    def test_invalid_json_fallback_to_text_extraction(self, mock_client):
        """Test fallback to text extraction when JSON parsing fails."""
        # Setup mock response with invalid JSON but extractable questions
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
        Here are some follow-up questions:
        1. Can you show more camera details?
        2. What time did this happen?
        - Are there other similar events?
        """
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 90
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Execute
        result = generate_follow_up_questions(
            query="Test query",
            response="Test response",
            conversation_history=[],
            search_results=[]
        )
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) > 0
        # Should extract questions without prefixes
        for question in result:
            assert not question.startswith(('1. ', '2. ', '- '))
    
    @patch('llm_client.client')
    @patch('llm_client.config', {'openai_model': 'gpt-4', 'openai_api_key': 'test-key'})
    def test_openai_error_returns_default_questions(self, mock_client):
        """Test that OpenAI errors return default follow-up questions."""
        from openai import RateLimitError
        
        # Mock rate limit error
        mock_client.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=Mock(),
            body=None
        )
        
        search_results = [
            {"camera_id": "cam-001", "event_type": "person_detected"}
        ]
        
        # Execute
        result = generate_follow_up_questions(
            query="Show me events",
            response="Found some events",
            conversation_history=[],
            search_results=search_results
        )
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 4  # Default questions limit
        # Should contain default questions
        default_questions = [
            "Can you show me more details about these events?",
            "Are there any patterns in the timing of these incidents?",
            "What preventive measures would you recommend?",
            "How can I set up alerts for similar events?"
        ]
        for question in result:
            assert question in default_questions or "cam-001" in question
    
    @patch('llm_client.client')
    @patch('llm_client.config', {'openai_model': 'gpt-4', 'openai_api_key': 'test-key'})
    def test_follow_up_with_conversation_context(self, mock_client):
        """Test follow-up generation considering conversation history."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps([
            "What happened before the motion detection?",
            "Should we increase monitoring for this area?"
        ])
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 85
        
        mock_client.chat.completions.create.return_value = mock_response
        
        conversation_history = [
            {"role": "user", "content": "Show me parking lot events"},
            {"role": "assistant", "content": "Found motion detection events"},
            {"role": "user", "content": "Tell me more about the motion"}
        ]
        
        result = generate_follow_up_questions(
            query="Tell me more about the motion",
            response="Motion was detected at 2 AM in the parking lot",
            conversation_history=conversation_history,
            search_results=[]
        )
        
        # Verify conversation context was included
        call_args = mock_client.chat.completions.create.call_args
        user_message = call_args[1]["messages"][1]["content"]
        assert "Recent topics" in user_message
        assert "parking lot events" in user_message.lower()


class TestGenerateProactiveInsights:
    """Test cases for generate_proactive_insights function."""
    
    @patch('llm_client.client')
    @patch('llm_client.config', {'openai_model': 'gpt-4', 'openai_api_key': 'test-key'})
    def test_successful_insights_generation(self, mock_client):
        """Test successful proactive insights generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
        1. Increased foot traffic suggests higher security risk during peak hours
        2. Motion detection patterns indicate potential blind spots in coverage
        3. Consider implementing automated alerts for unusual nighttime activity
        """
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 120
        
        mock_client.chat.completions.create.return_value = mock_response
        
        recent_events = [
            {
                "event_id": "evt-001",
                "event_type": "person_detected",
                "timestamp": "2025-06-18T14:00:00Z",
                "details": "Person walking through main area"
            },
            {
                "event_id": "evt-002", 
                "event_type": "motion_detected",
                "timestamp": "2025-06-18T02:00:00Z",
                "details": "Motion in restricted zone"
            }
        ]
        
        patterns = {
            "peak_hours": "14:00-16:00",
            "anomaly_count": 2
        }
        
        # Execute
        result = generate_proactive_insights(recent_events, patterns)
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 3
        
        # Check insights are cleaned up (no prefixes)
        for insight in result:
            assert not insight.startswith(('1. ', '2. ', '3. '))
            assert len(insight) > 10  # Should be meaningful insights
        
        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.3  # Lower temperature for insights
        assert call_args[1]["max_tokens"] == 300
        
        # Check that events and patterns were included in prompt
        user_message = call_args[1]["messages"][1]["content"]
        assert "person_detected" in user_message
        assert "motion_detected" in user_message
        assert "peak_hours" in user_message
    
    @patch('llm_client.client')
    @patch('llm_client.config', {'openai_model': 'gpt-4', 'openai_api_key': 'test-key'})
    def test_api_error_returns_fallback_insights(self, mock_client):
        """Test that API errors return fallback insights."""
        from openai import APIConnectionError        # Mock API error - APIConnectionError requires a request parameter
        mock_request = Mock()
        mock_client.chat.completions.create.side_effect = APIConnectionError(request=mock_request)
        
        recent_events = [{"event_id": "evt-001"}]
        
        # Execute
        result = generate_proactive_insights(recent_events)
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 3
        
        # Should return fallback insights
        fallback_insights = [
            "Monitor for unusual activity patterns",
            "Review recent high-confidence detections", 
            "Consider updating security protocols"
        ]
        assert result == fallback_insights
    
    @patch('llm_client.client')
    @patch('llm_client.config', {'openai_model': 'gpt-4', 'openai_api_key': 'test-key'})
    def test_empty_events_handling(self, mock_client):
        """Test insights generation with empty events list."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
        Based on recent activity:
        • Review current security protocols
        • Consider baseline monitoring adjustments
        • Maintain regular system health checks
        """
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 80
        
        mock_client.chat.completions.create.return_value = mock_response
          # Execute with empty events
        result = generate_proactive_insights([])
        
        # Assertions - should return empty list for empty events
        assert isinstance(result, list)
        assert len(result) == 0  # Should return empty list for no events
        
        # Verify no LLM call was made since there are no events
        assert not mock_client.chat.completions.create.called
    
    @patch('llm_client.client')
    @patch('llm_client.config', {'openai_model': 'gpt-4', 'openai_api_key': 'test-key'})
    def test_insights_text_cleaning(self, mock_client):
        """Test proper cleaning of insight text (removing prefixes and headers)."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
        Based on the analysis, here are the insights:
        
        1. Security breach detected in zone 3
        2. Unusual vehicle patterns during night hours  
        3. Camera maintenance needed for optimal coverage
        
        The following recommendations should be considered.
        """
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 95
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result = generate_proactive_insights([{"event_id": "test"}])
        
        # Assertions
        expected_insights = [
            "Security breach detected in zone 3",
            "Unusual vehicle patterns during night hours",
            "Camera maintenance needed for optimal coverage"
        ]
        
        assert result == expected_insights
        
        # Ensure no insights start with common prefixes or headers
        for insight in result:
            assert not insight.lower().startswith(('based on', 'here are', 'the following'))
            assert not insight.startswith(('1. ', '2. ', '3. ', '- ', '• ', '* '))


class TestLLMClientConfiguration:
    """Test LLM client configuration and initialization."""
    
    def test_client_initialization(self):
        """Test OpenAI client initialization."""
        import llm_client
        
        # Verify client exists and is accessible
        assert hasattr(llm_client, 'client')
        assert llm_client.client is not None
    
    def test_system_prompts_defined(self):
        """Test that system prompts are properly defined."""
        from llm_client import CONVERSATIONAL_SYSTEM_PROMPT, FOLLOW_UP_SYSTEM_PROMPT
        
        assert isinstance(CONVERSATIONAL_SYSTEM_PROMPT, str)
        assert len(CONVERSATIONAL_SYSTEM_PROMPT) > 100
        assert "surveillance system assistant" in CONVERSATIONAL_SYSTEM_PROMPT.lower()
        
        assert isinstance(FOLLOW_UP_SYSTEM_PROMPT, str)
        assert len(FOLLOW_UP_SYSTEM_PROMPT) > 100
        assert "follow-up questions" in FOLLOW_UP_SYSTEM_PROMPT.lower()
        assert "JSON array" in FOLLOW_UP_SYSTEM_PROMPT


if __name__ == "__main__":
    pytest.main([__file__])

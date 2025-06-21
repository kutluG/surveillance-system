"""
Unit Tests for LLM Client Service

This module provides comprehensive unit tests for the LLMService class,
covering AI-powered text generation, insight summarization, and natural
language processing functionality. Tests include API interaction validation,
error handling, and response processing verification.

Test Coverage:
- Insights summary generation with realistic surveillance data
- Report content generation with structured outputs
- Anomaly pattern analysis with JSON response parsing
- Predictive insights generation with forecasting
- Metric change explanations with contextual analysis
- Error handling: API failures, malformed responses, connection issues
- Response validation: content structure, token usage, formatting

Key Test Scenarios:
- Successful AI response generation and processing
- API error simulation and graceful degradation
- JSON response parsing and fallback mechanisms
- Content validation and sanitization
- Rate limiting and timeout handling
"""

import json
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from openai import AsyncOpenAI

from app.services.llm_client import LLMService


class TestLLMService:
    """Comprehensive test suite for LLMService functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_insights_summary_success(self, llm_service, mock_openai_client, sample_insights_data):
        """
        Test successful insights summary generation.
        
        Validates that the LLM service correctly processes surveillance
        insights data and generates human-readable summaries with proper
        API interaction and response handling.
        """
        # Configure mock response
        mock_response = AsyncMock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "System analysis shows increased motion detection with 15% trend growth. Processing latency anomaly detected requiring attention. Recommendations: Monitor trends and scale resources during peak hours."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Execute insights summary generation
        result = await llm_service.generate_insights_summary(sample_insights_data)
        
        # Verify response
        assert isinstance(result, str)
        assert len(result) > 0
        assert "motion detection" in result.lower() or "trend" in result.lower()
        
        # Verify API call was made correctly
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args
        
        # Verify API call parameters
        assert call_args[1]["model"] == "gpt-3.5-turbo"
        assert call_args[1]["max_tokens"] == 300
        assert call_args[1]["temperature"] == 0.3
        assert len(call_args[1]["messages"]) == 2
        assert call_args[1]["messages"][0]["role"] == "system"
        assert call_args[1]["messages"][1]["role"] == "user"
        
        # Verify prompt contains insights data
        user_message = call_args[1]["messages"][1]["content"]
        assert "trends" in user_message
        assert "anomalies" in user_message
        assert "performance_metrics" in user_message
    
    @pytest.mark.asyncio
    async def test_generate_insights_summary_api_error(self, llm_service, simulate_openai_error, sample_insights_data):
        """
        Test insights summary generation with API error.
        
        Validates that the service gracefully handles OpenAI API errors
        and returns appropriate fallback responses without crashing.
        """
        # Execute insights summary generation (should handle error gracefully)
        result = await llm_service.generate_insights_summary(sample_insights_data)
        
        # Verify fallback response
        assert isinstance(result, str)
        assert "Unable to generate insights summary" in result
    
    @pytest.mark.asyncio
    async def test_generate_report_content_success(self, llm_service, mock_openai_client):
        """
        Test successful report content generation.
        
        Validates that comprehensive surveillance reports are generated
        with proper structure and professional formatting.
        """
        # Sample report data
        report_data = {
            "time_period": "last_24_hours",
            "security_events": [
                {"type": "motion_detected", "count": 45},
                {"type": "person_detected", "count": 12}
            ],
            "system_performance": {
                "uptime": 0.99,
                "processing_speed": "normal"
            }
        }
        
        # Configure mock response
        mock_response = AsyncMock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = """
        # Surveillance System Report
        
        ## Executive Summary
        System operating at optimal levels with 99% uptime.
        
        ## Key Metrics Overview
        - Motion events: 45 detected
        - Person detections: 12 confirmed
        
        ## Recommendations
        - Continue current monitoring protocols
        - Review peak activity patterns
        """
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Execute report generation
        result = await llm_service.generate_report_content(report_data)
        
        # Verify response structure
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Executive Summary" in result or "surveillance" in result.lower()
        
        # Verify API call
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-3.5-turbo"
        assert call_args[1]["max_tokens"] == 1500
        assert call_args[1]["temperature"] == 0.2
    
    @pytest.mark.asyncio
    async def test_generate_report_content_api_error(self, llm_service, simulate_openai_error):
        """
        Test report content generation with API error.
        
        Validates error handling and fallback response for report generation
        when the OpenAI API is unavailable or returns errors.
        """
        report_data = {"test": "data"}
        
        # Execute report generation (should handle error gracefully)
        result = await llm_service.generate_report_content(report_data)
        
        # Verify fallback response
        assert isinstance(result, str)
        assert "Unable to generate report content" in result
    
    @pytest.mark.asyncio
    async def test_analyze_anomaly_patterns_success(self, llm_service, mock_openai_client):
        """
        Test successful anomaly pattern analysis.
        
        Validates that anomaly analysis correctly processes surveillance
        anomalies and returns structured insights with JSON formatting.
        """
        # Sample anomaly data
        anomalies = [
            {
                "id": "anomaly_001",
                "metric": "processing_latency",
                "severity": "high",
                "description": "Processing latency spike detected",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "anomaly_002",
                "metric": "detection_count",
                "severity": "medium",
                "description": "Unusual detection pattern",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        # Configure mock response with valid JSON
        mock_response = AsyncMock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({
            "summary": "Multiple performance anomalies detected requiring attention",
            "patterns": [
                "Processing latency spikes during peak hours",
                "Detection count variations in specific zones"
            ],
            "recommendations": [
                "Scale processing resources",
                "Review detection sensitivity settings"
            ],
            "priority_level": "high"
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Execute anomaly pattern analysis
        result = await llm_service.analyze_anomaly_patterns(anomalies)
        
        # Verify response structure
        assert isinstance(result, dict)
        assert "summary" in result
        assert "patterns" in result
        assert "recommendations" in result
        assert "priority_level" in result
        
        # Verify content
        assert isinstance(result["summary"], str)
        assert isinstance(result["patterns"], list)
        assert isinstance(result["recommendations"], list)
        assert result["priority_level"] in ["low", "medium", "high"]
    
    @pytest.mark.asyncio
    async def test_analyze_anomaly_patterns_empty_anomalies(self, llm_service):
        """
        Test anomaly pattern analysis with empty anomaly list.
        
        Validates proper handling when no anomalies are provided
        for analysis, returning appropriate default response.
        """
        # Execute with empty anomalies list
        result = await llm_service.analyze_anomaly_patterns([])
        
        # Verify default response
        assert isinstance(result, dict)
        assert result["summary"] == "No anomalies detected"
        assert result["patterns"] == []
        assert result["recommendations"] == []
    
    @pytest.mark.asyncio
    async def test_analyze_anomaly_patterns_invalid_json(self, llm_service, mock_openai_client):
        """
        Test anomaly pattern analysis with invalid JSON response.
        
        Validates fallback handling when the AI returns malformed JSON
        that cannot be parsed properly.
        """
        anomalies = [{"id": "test", "metric": "test_metric", "severity": "medium"}]
        
        # Configure mock response with invalid JSON
        mock_response = AsyncMock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "This is not valid JSON content"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Execute anomaly pattern analysis
        result = await llm_service.analyze_anomaly_patterns(anomalies)
        
        # Verify fallback response
        assert isinstance(result, dict)
        assert "summary" in result
        assert "patterns" in result
        assert "recommendations" in result
        assert "priority_level" in result
        assert result["summary"] == "Pattern analysis completed"
    
    @pytest.mark.asyncio
    async def test_generate_predictive_insights_success(self, llm_service, mock_openai_client):
        """
        Test successful predictive insights generation.
        
        Validates that predictive analysis correctly processes historical
        surveillance data and generates future forecasts with actionable insights.
        """
        # Sample historical data
        historical_data = {
            "detection_trends": {
                "last_week": [10, 12, 8, 15, 11, 9, 13],
                "patterns": ["peak_afternoon", "low_night"]
            },
            "system_performance": {
                "cpu_usage": [65, 70, 68, 75, 72, 69, 71],
                "memory_usage": [55, 60, 58, 65, 62, 57, 63]
            }
        }
        
        # Configure mock response with valid JSON
        mock_response = AsyncMock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({
            "security_forecast": "Normal activity expected with peak periods during afternoon hours",
            "performance_forecast": "Stable system performance with slight CPU increase trend",
            "maintenance_recommendations": [
                "Schedule maintenance during low-activity periods",
                "Monitor CPU usage during peak hours"
            ],
            "confidence_level": "high"
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Execute predictive insights generation
        result = await llm_service.generate_predictive_insights(historical_data)
        
        # Verify response structure
        assert isinstance(result, dict)
        assert "security_forecast" in result
        assert "performance_forecast" in result
        assert "maintenance_recommendations" in result
        assert "confidence_level" in result
        
        # Verify content types
        assert isinstance(result["security_forecast"], str)
        assert isinstance(result["performance_forecast"], str)
        assert isinstance(result["maintenance_recommendations"], list)
        assert result["confidence_level"] in ["low", "medium", "high"]
    
    @pytest.mark.asyncio
    async def test_generate_predictive_insights_api_error(self, llm_service, simulate_openai_error):
        """
        Test predictive insights generation with API error.
        
        Validates error handling and fallback response for predictive
        analysis when the OpenAI API is unavailable.
        """
        historical_data = {"test": "data"}
        
        # Execute predictive insights generation (should handle error gracefully)
        result = await llm_service.generate_predictive_insights(historical_data)
        
        # Verify fallback response
        assert isinstance(result, dict)
        assert result["security_forecast"] == "Analysis unavailable"
        assert result["performance_forecast"] == "Analysis unavailable"
        assert result["maintenance_recommendations"] == []
        assert result["confidence_level"] == "low"
    
    @pytest.mark.asyncio
    async def test_explain_metric_changes_success(self, llm_service, mock_openai_client):
        """
        Test successful metric change explanation.
        
        Validates that metric change analysis correctly explains surveillance
        metric variations with contextual insights and recommendations.
        """
        # Configure mock response
        mock_response = AsyncMock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "The detection count increased by 25% from 100 to 125, indicating higher activity levels in monitored areas. This change suggests increased foot traffic or improved sensor sensitivity. Monitor for sustained increases and consider adjusting alert thresholds if needed."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Execute metric change explanation
        result = await llm_service.explain_metric_changes(
            metric_name="detection_count",
            old_value=100.0,
            new_value=125.0,
            context={"time_period": "last_hour", "location": "main_entrance"}
        )
        
        # Verify response
        assert isinstance(result, str)
        assert len(result) > 0
        assert "detection_count" in result or "increase" in result.lower()
        
        # Verify API call
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-3.5-turbo"
        assert call_args[1]["max_tokens"] == 150
        assert call_args[1]["temperature"] == 0.3
        
        # Verify prompt contains metric details
        user_message = call_args[1]["messages"][1]["content"]
        assert "detection_count" in user_message
        assert "100" in user_message
        assert "125" in user_message
        assert "25.0%" in user_message  # Calculated percentage change
    
    @pytest.mark.asyncio
    async def test_explain_metric_changes_zero_division(self, llm_service, mock_openai_client):
        """
        Test metric change explanation with zero old value.
        
        Validates proper handling of percentage calculation when
        the old value is zero to avoid division by zero errors.
        """
        # Configure mock response
        mock_response = AsyncMock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "New metric detected with initial value of 50. This represents the establishment of baseline measurements."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Execute metric change explanation with zero old value
        result = await llm_service.explain_metric_changes(
            metric_name="new_metric",
            old_value=0.0,
            new_value=50.0,
            context={}
        )
        
        # Verify response (should not crash on division by zero)
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_explain_metric_changes_api_error(self, llm_service, simulate_openai_error):
        """
        Test metric change explanation with API error.
        
        Validates error handling and fallback response for metric
        explanations when the OpenAI API is unavailable.
        """
        # Execute metric change explanation (should handle error gracefully)
        result = await llm_service.explain_metric_changes(
            metric_name="test_metric",
            old_value=10.0,
            new_value=15.0,
            context={}
        )
        
        # Verify fallback response
        assert isinstance(result, str)
        assert "test_metric changed from 10.0 to 15.0" in result
        assert "Manual review recommended" in result
    
    @pytest.mark.asyncio
    async def test_model_configuration(self, mock_openai_client):
        """
        Test LLM service model configuration and initialization.
        
        Validates that the service is properly configured with the
        correct model and client settings.
        """
        # Initialize service
        service = LLMService(openai_client=mock_openai_client)
        
        # Verify configuration
        assert service.client == mock_openai_client
        assert service.model == "gpt-3.5-turbo"
        assert isinstance(service.client, (AsyncMock, AsyncOpenAI))
    
    @pytest.mark.asyncio
    async def test_prompt_engineering_insights_summary(self, llm_service, mock_openai_client, sample_insights_data):
        """
        Test prompt engineering for insights summary generation.
        
        Validates that prompts are properly structured with appropriate
        instructions, context, and formatting requirements.
        """
        # Configure mock response
        mock_response = AsyncMock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Professional surveillance analysis response"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Execute insights summary generation
        await llm_service.generate_insights_summary(sample_insights_data)
        
        # Verify prompt structure
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        
        # Verify system message
        system_message = messages[0]
        assert system_message["role"] == "system"
        assert "surveillance system analysis" in system_message["content"].lower()
        
        # Verify user message structure
        user_message = messages[1]
        assert user_message["role"] == "user"
        user_content = user_message["content"]
        
        # Check prompt elements
        assert "trends and patterns" in user_content.lower()
        assert "anomalies" in user_content.lower()
        assert "recommendations" in user_content.lower()
        assert "200 words" in user_content
        assert json.dumps(sample_insights_data, default=str) in user_content
    
    @pytest.mark.asyncio
    async def test_response_processing_and_cleanup(self, llm_service, mock_openai_client, sample_insights_data):
        """
        Test response processing and content cleanup.
        
        Validates that AI responses are properly processed, cleaned,
        and formatted for consistent output quality.
        """
        # Configure mock response with extra whitespace
        mock_response = AsyncMock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "  \n\n  System analysis shows normal operation.  \n\n  "
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Execute insights summary generation
        result = await llm_service.generate_insights_summary(sample_insights_data)
        
        # Verify response is cleaned
        assert result == "System analysis shows normal operation."
        assert not result.startswith(" ")
        assert not result.endswith(" ")
        assert "\n\n" not in result
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, llm_service, mock_openai_client, sample_insights_data):
        """
        Test handling of concurrent LLM requests.
        
        Validates that the service can handle multiple simultaneous
        requests without interference or resource conflicts.
        """
        # Configure mock response
        mock_response = AsyncMock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Concurrent response test"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Execute multiple concurrent requests
        tasks = [
            llm_service.generate_insights_summary(sample_insights_data),
            llm_service.generate_insights_summary(sample_insights_data),
            llm_service.generate_insights_summary(sample_insights_data)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all requests completed successfully
        assert len(results) == 3
        assert all(isinstance(result, str) for result in results)
        assert all(len(result) > 0 for result in results)
        
        # Verify API was called for each request
        assert mock_openai_client.chat.completions.create.call_count == 3

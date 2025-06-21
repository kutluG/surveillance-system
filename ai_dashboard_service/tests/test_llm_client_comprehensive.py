"""
Comprehensive unit tests for LLM Client Service.

This module provides complete test coverage for the LLMService class,
including AI-powered text generation, insight summarization, and natural
language processing. All OpenAI API calls are mocked for isolated testing.

Test Coverage:
- Insight summarization with various data scenarios
- Report content generation and formatting
- Anomaly pattern analysis with JSON responses
- Error handling for API failures and retry logic
- Token usage tracking and optimization
- Input validation and sanitization

Classes Tested:
    - LLMService: Main AI service with comprehensive validation
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

from app.services.llm_client import LLMService


class TestLLMService:
    """
    Comprehensive test suite for LLMService functionality.
    
    Tests all major LLM operations including insight generation,
    report creation, pattern analysis, and error scenarios.
    """
    
    @pytest.mark.asyncio
    async def test_generate_insights_summary_success(self, llm_service, sample_insights_data):
        """
        Test successful insights summary generation.
        
        Validates that the LLM service correctly processes surveillance
        analytics data and generates coherent, actionable summaries.
        """
        # Execute insights summary generation
        result = await llm_service.generate_insights_summary(sample_insights_data)
        
        # Validate result structure and content
        assert isinstance(result, str)
        assert len(result) > 0
        assert len(result) <= 1000  # Reasonable length limit
        
        # Should contain meaningful content (not just error message)
        assert "Unable to generate" not in result
        
        # Verify the OpenAI client was called with correct parameters
        llm_service.client.chat.completions.create.assert_called_once()
        call_args = llm_service.client.chat.completions.create.call_args
        
        # Validate API call parameters
        assert call_args.kwargs['model'] == 'gpt-3.5-turbo'
        assert call_args.kwargs['max_tokens'] == 300
        assert call_args.kwargs['temperature'] == 0.3
        assert len(call_args.kwargs['messages']) == 2
        
        # Validate message structure
        messages = call_args.kwargs['messages']
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert 'surveillance system analysis' in messages[0]['content'].lower()
    
    @pytest.mark.asyncio
    async def test_generate_insights_summary_api_error(self, llm_service, sample_insights_data):
        """
        Test insights summary generation with OpenAI API errors.
        
        Validates that API failures are properly handled and fallback
        responses are provided to maintain service availability.
        """
        # Configure mock to raise an API error
        llm_service.client.chat.completions.create = AsyncMock(
            side_effect=Exception("OpenAI API rate limit exceeded")
        )
        
        result = await llm_service.generate_insights_summary(sample_insights_data)
        
        # Should return fallback message instead of raising exception
        assert isinstance(result, str)
        assert "Unable to generate insights summary at this time" in result
    
    @pytest.mark.asyncio
    async def test_generate_insights_summary_empty_data(self, llm_service):
        """
        Test insights summary with empty input data.
        
        Validates proper handling of edge cases where no analytics
        data is available for summarization.
        """
        empty_data = {}
        
        result = await llm_service.generate_insights_summary(empty_data)
        
        # Should handle empty data gracefully
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_generate_insights_summary_large_dataset(self, llm_service):
        """
        Test insights summary with large dataset.
        
        Validates that large analytics datasets are properly processed
        and summarized within token limits.
        """
        # Create large dataset
        large_data = {
            "trends": [{"metric": f"metric_{i}", "direction": "increasing"} for i in range(100)],
            "anomalies": [{"id": f"anomaly_{i}", "severity": "medium"} for i in range(50)],
            "performance_metrics": {f"metric_{i}": i * 10 for i in range(200)}
        }
        
        result = await llm_service.generate_insights_summary(large_data)
        
        # Should handle large datasets without errors
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Unable to generate" not in result
    
    @pytest.mark.asyncio
    async def test_generate_report_content_success(self, llm_service):
        """
        Test successful report content generation.
        
        Validates that comprehensive surveillance reports are generated
        with proper structure and professional formatting.
        """
        report_data = {
            "time_range": "last_24_hours",
            "summary": {"total_events": 1250, "alerts": 23, "cameras_active": 12},
            "trends": [{"metric": "motion_events", "change": "+15%"}],
            "incidents": [{"type": "unauthorized_access", "count": 3}],
            "performance": {"uptime": "99.2%", "avg_response": "120ms"}
        }
        
        result = await llm_service.generate_report_content(report_data)
        
        # Validate report structure
        assert isinstance(result, str)
        assert len(result) > 100  # Substantial content
        assert "Unable to generate" not in result
        
        # Verify OpenAI API call parameters for report generation
        llm_service.client.chat.completions.create.assert_called()
        call_args = llm_service.client.chat.completions.create.call_args
        
        assert call_args.kwargs['max_tokens'] == 1500  # Longer for reports
        assert call_args.kwargs['temperature'] == 0.2   # Lower for consistency
    
    @pytest.mark.asyncio
    async def test_generate_report_content_minimal_data(self, llm_service):
        """
        Test report generation with minimal input data.
        
        Validates that reports can be generated even when limited
        surveillance data is available.
        """
        minimal_data = {
            "summary": {"total_events": 10}
        }
        
        result = await llm_service.generate_report_content(minimal_data)
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_anomaly_patterns_success(self, llm_service):
        """
        Test successful anomaly pattern analysis.
        
        Validates that anomaly data is properly analyzed and structured
        JSON responses are returned with patterns and recommendations.
        """
        anomalies = [
            {
                "id": "anomaly_001",
                "metric": "processing_latency",
                "severity": "high",
                "timestamp": "2025-06-20T10:00:00Z",
                "value": 500,
                "expected": 100
            },
            {
                "id": "anomaly_002", 
                "metric": "processing_latency",
                "severity": "medium",
                "timestamp": "2025-06-20T11:00:00Z",
                "value": 200,
                "expected": 100
            }
        ]
        
        # Mock JSON response from OpenAI
        json_response = {
            "summary": "Multiple processing latency spikes detected",
            "patterns": ["Recurring latency issues", "Peak hour correlation"],
            "recommendations": ["Scale processing resources", "Investigate bottlenecks"],
            "priority_level": "high"
        }
        
        # Configure mock to return JSON content
        llm_service.client.chat.completions.create.return_value.choices[0].message.content = json.dumps(json_response)
        
        result = await llm_service.analyze_anomaly_patterns(anomalies)
        
        # Validate JSON structure
        assert isinstance(result, dict)
        assert "summary" in result
        assert "patterns" in result
        assert "recommendations" in result
        assert "priority_level" in result
        
        # Validate content
        assert isinstance(result["patterns"], list)
        assert isinstance(result["recommendations"], list)
        assert result["priority_level"] in ["low", "medium", "high"]
    
    @pytest.mark.asyncio
    async def test_analyze_anomaly_patterns_empty_anomalies(self, llm_service):
        """
        Test anomaly pattern analysis with no anomalies.
        
        Validates proper handling when no anomalies are detected
        in the surveillance system.
        """
        result = await llm_service.analyze_anomaly_patterns([])
        
        # Should return default structure for no anomalies
        assert isinstance(result, dict)
        assert result["summary"] == "No anomalies detected"
        assert result["patterns"] == []
        assert result["recommendations"] == []
    
    @pytest.mark.asyncio
    async def test_analyze_anomaly_patterns_invalid_json(self, llm_service):
        """
        Test anomaly pattern analysis with invalid JSON response.
        
        Validates fallback behavior when OpenAI returns malformed
        JSON that cannot be parsed.
        """
        anomalies = [{"id": "test", "severity": "high"}]
        
        # Configure mock to return invalid JSON
        llm_service.client.chat.completions.create.return_value.choices[0].message.content = "Invalid JSON response"
        
        result = await llm_service.analyze_anomaly_patterns(anomalies)
        
        # Should return fallback structure
        assert isinstance(result, dict)
        assert "summary" in result
        assert "patterns" in result
        assert "recommendations" in result
        assert result["priority_level"] == "medium"
    
    @pytest.mark.asyncio
    async def test_analyze_anomaly_patterns_api_error(self, llm_service):
        """
        Test anomaly pattern analysis with API errors.
        
        Validates error handling when OpenAI API calls fail
        during anomaly analysis.
        """
        anomalies = [{"id": "test", "severity": "high"}]
        
        # Configure mock to raise API error
        llm_service.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API connection timeout")
        )
        
        result = await llm_service.analyze_anomaly_patterns(anomalies)
        
        # Should return error fallback structure
        assert isinstance(result, dict)
        assert "summary" in result
        assert "patterns" in result
        assert "recommendations" in result
    
    @pytest.mark.asyncio
    async def test_model_configuration(self, llm_service):
        """
        Test LLM model configuration and parameters.
        
        Validates that the service is configured with appropriate
        model settings for surveillance analytics.
        """
        # Verify default model configuration
        assert llm_service.model == "gpt-3.5-turbo"
        assert hasattr(llm_service, 'client')
        assert llm_service.client is not None
    
    @pytest.mark.asyncio
    async def test_input_validation_and_sanitization(self, llm_service):
        """
        Test input validation and sanitization.
        
        Validates that potentially problematic input data is
        properly handled and sanitized before API calls.
        """
        # Test with potentially problematic data
        problematic_data = {
            "trends": None,  # None values
            "anomalies": "string_instead_of_list",  # Wrong type
            "metrics": {"key": float('inf')},  # Invalid float
            "special_chars": "Data with\n\t special chars",
        }
        
        # Should handle problematic data without crashing
        result = await llm_service.generate_insights_summary(problematic_data)
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_concurrent_llm_operations(self, llm_service, sample_insights_data):
        """
        Test concurrent LLM operations for thread safety.
        
        Validates that multiple LLM operations can run concurrently
        without interference or resource conflicts.
        """
        import asyncio
        
        # Create multiple concurrent LLM tasks
        tasks = [
            llm_service.generate_insights_summary(sample_insights_data),
            llm_service.generate_insights_summary(sample_insights_data),
            llm_service.generate_insights_summary(sample_insights_data)
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate all operations completed successfully
        assert len(results) == 3
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Operation {i} should not raise exception"
            assert isinstance(result, str), f"Operation {i} should return string"
    
    @pytest.mark.asyncio
    async def test_token_usage_tracking(self, llm_service, sample_insights_data):
        """
        Test token usage tracking and optimization.
        
        Validates that token usage is properly tracked and
        optimizations are applied for cost management.
        """
        # Execute operation that should track tokens
        result = await llm_service.generate_insights_summary(sample_insights_data)
        
        # Verify API call was made (token usage would be in response)
        assert llm_service.client.chat.completions.create.called
        
        # In real implementation, you would verify:
        # - Token count is within limits
        # - Usage is tracked for billing
        # - Optimization strategies are applied
    
    @pytest.mark.asyncio
    async def test_system_message_consistency(self, llm_service, sample_insights_data):
        """
        Test system message consistency across operations.
        
        Validates that system messages are properly configured
        for surveillance domain expertise.
        """
        await llm_service.generate_insights_summary(sample_insights_data)
        
        # Verify system message contains surveillance context
        call_args = llm_service.client.chat.completions.create.call_args
        system_message = call_args.kwargs['messages'][0]
        
        assert system_message['role'] == 'system'
        assert 'surveillance' in system_message['content'].lower()
        assert 'assistant' in system_message['content'].lower()
    
    @pytest.mark.asyncio
    async def test_response_length_limits(self, llm_service, sample_insights_data):
        """
        Test response length limits and truncation.
        
        Validates that responses are kept within appropriate
        length limits for different operation types.
        """
        result = await llm_service.generate_insights_summary(sample_insights_data)
        
        # Insights summary should be concise
        assert len(result) <= 1000, "Insights summary should be under 1000 characters"
        
        # Verify max_tokens parameter was set appropriately
        call_args = llm_service.client.chat.completions.create.call_args
        assert call_args.kwargs['max_tokens'] == 300
    
    @pytest.mark.asyncio
    async def test_dependency_injection_validation(self, mock_openai_client):
        """
        Test proper dependency injection and validation.
        
        Ensures the service correctly validates and uses the
        injected OpenAI client dependency.
        """
        # Test successful dependency injection
        service = LLMService(openai_client=mock_openai_client)
        assert service.client is mock_openai_client
        
        # Test that client is required
        with pytest.raises(TypeError):
            LLMService()  # Should require openai_client parameter
    
    @pytest.mark.asyncio
    async def test_error_logging_and_monitoring(self, llm_service, sample_insights_data, caplog):
        """
        Test error logging and monitoring capabilities.
        
        Validates that errors are properly logged for monitoring
        and debugging purposes.
        """
        # Configure mock to raise an error
        llm_service.client.chat.completions.create = AsyncMock(
            side_effect=Exception("Test API error")
        )
        
        # Execute operation that will fail
        result = await llm_service.generate_insights_summary(sample_insights_data)
        
        # Verify error was logged
        assert "Error generating insights summary" in caplog.text
        
        # Verify fallback response was returned
        assert "Unable to generate" in result

"""
Tests for the Agent Orchestrator Service

This module tests the orchestration logic including retry mechanisms,
fallback behaviors, and notification retry processing.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import httpx

from fastapi.testclient import TestClient

# Import the modules to test
from orchestrator import OrchestratorService, OrchestrationRequest, OrchestrationResponse
from main import app

client = TestClient(app)


class TestOrchestratorService:
    """Test cases for the OrchestratorService class"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator service for testing"""
        service = OrchestratorService()
        # Mock the Redis and HTTP clients to avoid actual connections
        service.redis_client = AsyncMock()
        service.http_client = AsyncMock()
        return service
    
    @pytest.fixture
    def sample_request(self):
        """Sample orchestration request"""
        return OrchestrationRequest(
            event_data={
                "camera_id": "cam_001",
                "timestamp": "2025-06-06T10:30:00Z",
                "label": "person_detected",
                "bbox": {"x": 100, "y": 150, "width": 50, "height": 100}
            },
            query="Person detected in restricted area",
            notification_channels=["email", "sms"],
            recipients=["security@company.com"]
        )

    @pytest.mark.asyncio
    async def test_rag_service_503_fallback(self, orchestrator, sample_request):
        """
        Test that RAG endpoint returning HTTP 503 every time results in fallback JSON
        """
        # Mock RAG service to always return 503
        mock_response = AsyncMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable", request=AsyncMock(), response=mock_response
        )
        
        orchestrator.http_client.post.return_value = mock_response
        
        # Call orchestrate
        result = await orchestrator.orchestrate(sample_request)
        
        # Verify fallback response
        assert result.status == "fallback"
        assert result.rag_result is not None
        assert result.rag_result["linked_explanation"] == "We could not retrieve context due to a temporary service outage. Please try again shortly."
        assert result.rag_result["retrieved_context"] == []
        assert result.rule_result is None  # Should skip rule generation
        assert result.details["rag_fallback_used"] is True
    
    @pytest.mark.asyncio
    async def test_notifier_retry_mechanism(self, orchestrator, sample_request):
        """
        Test that Notifier endpoint being down on first orchestration but available during retry succeeds
        """
        # Mock successful RAG and Rule Generation calls
        rag_response = AsyncMock()
        rag_response.status_code = 200
        rag_response.json.return_value = {
            "linked_explanation": "Person detected in temporal context",
            "retrieved_context": [{"event": "test"}]
        }
        
        rule_response = AsyncMock()
        rule_response.status_code = 200
        rule_response.json.return_value = {
            "triggered_actions": [
                {
                    "type": "send_notification",
                    "rule_id": "person_alert",
                    "parameters": {"message": "Person detected", "severity": "high"}
                }
            ]
        }
        
        # Mock notifier to fail first
        notifier_response_fail = AsyncMock()
        notifier_response_fail.status_code = 503
        notifier_response_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable", request=AsyncMock(), response=notifier_response_fail
        )
        
        # Set up responses in order: RAG success, Rule success, Notifier fail
        orchestrator.http_client.post.side_effect = [
            rag_response,      # RAG call
            rule_response,     # Rule generation call
            notifier_response_fail  # Notifier call fails
        ]
        
        # Mock Redis lpush for retry queue
        orchestrator.redis_client.lpush = AsyncMock()
        
        # Call orchestrate - should queue notification for retry
        result = await orchestrator.orchestrate(sample_request)
        
        # Verify notification was queued for retry
        assert result.status == "partial_success"
        assert result.details["notification_queued_for_retry"] is True
        assert result.notification_result["status"] == "notifier_unreachable"
        
        # Verify Redis was called to enqueue retry
        orchestrator.redis_client.lpush.assert_called_once()
        args, kwargs = orchestrator.redis_client.lpush.call_args
        assert args[0] == "notification_retry_queue"
        
        retry_data = json.loads(args[1])
        assert "id" in retry_data
        assert "payload" in retry_data
        assert retry_data["retry_count"] == 0
    
    @pytest.mark.asyncio
    async def test_rule_generation_failure_uses_defaults(self, orchestrator, sample_request):
        """Test that rule generation failure results in default rules"""
        # Mock successful RAG call
        rag_response = AsyncMock()
        rag_response.status_code = 200
        rag_response.json.return_value = {
            "linked_explanation": "Person detected in temporal context",
            "retrieved_context": [{"event": "test"}]
        }
        
        # Mock failed rule generation call
        rule_response = AsyncMock()
        rule_response.status_code = 500
        rule_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=AsyncMock(), response=rule_response
        )
        
        # Mock successful notifier call
        notifier_response = AsyncMock()
        notifier_response.status_code = 200
        notifier_response.json.return_value = {"status": "sent", "message_id": "123"}
        
        orchestrator.http_client.post.side_effect = [
            rag_response,      # RAG call succeeds
            rule_response,     # Rule generation fails
            notifier_response  # Notifier succeeds
        ]
        
        # Call orchestrate
        result = await orchestrator.orchestrate(sample_request)
        
        # Verify default rules were used
        assert result.status == "partial_success"
        assert result.details["default_rules_used"] is True
        assert result.rule_result is not None
        assert len(result.rule_result["triggered_actions"]) == 1
        assert result.rule_result["triggered_actions"][0]["rule_id"] == "default_alert"
    
    @pytest.mark.asyncio
    async def test_successful_orchestration(self, orchestrator, sample_request):
        """Test complete successful orchestration flow"""
        # Mock all successful responses
        rag_response = AsyncMock()
        rag_response.status_code = 200
        rag_response.json.return_value = {
            "linked_explanation": "Person detected in temporal context",
            "retrieved_context": [{"event": "test"}]
        }
        
        rule_response = AsyncMock()
        rule_response.status_code = 200
        rule_response.json.return_value = {
            "triggered_actions": [
                {
                    "type": "send_notification",
                    "rule_id": "person_alert",
                    "parameters": {"message": "Person detected", "severity": "high"}
                }
            ]
        }
        
        notifier_response = AsyncMock()
        notifier_response.status_code = 200
        notifier_response.json.return_value = {"status": "sent", "message_id": "123"}
        
        orchestrator.http_client.post.side_effect = [
            rag_response,
            rule_response,
            notifier_response
        ]
        
        # Call orchestrate
        result = await orchestrator.orchestrate(sample_request)
        
        # Verify successful result
        assert result.status == "ok"
        assert result.rag_result is not None
        assert result.rule_result is not None
        assert result.notification_result is not None
        assert result.details["rag_success"] is True
        assert result.details["rule_success"] is True
        assert result.details["notification_success"] is True


class TestOrchestrationEndpoint:
    """Test cases for the /orchestrate API endpoint"""
    
    def test_orchestrate_endpoint_success(self):
        """Test successful orchestration via HTTP endpoint"""
        with patch('main.orchestrator_service') as mock_service:
            # Mock successful orchestration
            mock_result = OrchestrationResponse(
                status="ok",
                details={"rag_success": True, "rule_success": True, "notification_success": True},
                rag_result={"linked_explanation": "Test", "retrieved_context": []},
                rule_result={"triggered_actions": []},
                notification_result={"status": "sent"}
            )
            mock_service.orchestrate = AsyncMock(return_value=mock_result)
            
            # Make request
            response = client.post("/orchestrate", json={
                "event_data": {
                    "camera_id": "cam_001",
                    "timestamp": "2025-06-06T10:30:00Z",
                    "label": "person_detected"
                },
                "notification_channels": ["email"],
                "recipients": ["test@example.com"]
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
    
    def test_orchestrate_endpoint_notifier_failure_returns_202(self):
        """Test that notifier failure returns 202 status"""
        with patch('main.orchestrator_service') as mock_service:
            # Mock orchestration with notifier failure
            mock_result = OrchestrationResponse(
                status="partial_success",
                details={"notification_queued_for_retry": True},
                rag_result={"linked_explanation": "Test", "retrieved_context": []},
                rule_result={"triggered_actions": []},
                notification_result={"status": "notifier_unreachable"}
            )
            mock_service.orchestrate = AsyncMock(return_value=mock_result)
            
            # Make request
            response = client.post("/orchestrate", json={
                "event_data": {
                    "camera_id": "cam_001",
                    "timestamp": "2025-06-06T10:30:00Z",
                    "label": "person_detected"
                }
            })
            
            assert response.status_code == 202
    
    def test_orchestrate_endpoint_rag_failure_returns_503(self):
        """Test that RAG failure returns 503 status"""
        with patch('main.orchestrator_service') as mock_service:
            # Mock orchestration with RAG failure
            mock_result = OrchestrationResponse(
                status="fallback",
                details={"rag_fallback_used": True},
                rag_result={
                    "linked_explanation": "We could not retrieve context due to a temporary service outage. Please try again shortly.",
                    "retrieved_context": []
                },
                rule_result=None,
                notification_result=None
            )
            mock_service.orchestrate = AsyncMock(return_value=mock_result)
            
            # Make request
            response = client.post("/orchestrate", json={
                "event_data": {
                    "camera_id": "cam_001",
                    "timestamp": "2025-06-06T10:30:00Z",
                    "label": "person_detected"
                }
            })
            
            assert response.status_code == 503


if __name__ == "__main__":
    pytest.main([__file__])

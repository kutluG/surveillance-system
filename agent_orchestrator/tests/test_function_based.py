"""
Simple function-based test for orchestrator
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock
import httpx

from orchestrator import OrchestratorService, OrchestrationRequest, OrchestrationResponse


@pytest.mark.asyncio
async def test_orchestrator_basic():
    """Basic test of orchestrator functionality"""
    # Create orchestrator service
    service = OrchestratorService()
    service.redis_client = AsyncMock()
    service.http_client = AsyncMock()
    
    # Create sample request
    request = OrchestrationRequest(
        event_data={
            "camera_id": "cam_001",
            "timestamp": "2025-06-06T10:30:00Z",
            "label": "person_detected"
        },
        query="Test query",
        notification_channels=["email"],
        recipients=["test@example.com"]
    )
    
    # Mock successful responses
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
    
    service.http_client.post.side_effect = [
        rag_response,
        rule_response,
        notifier_response
    ]
    
    # Call orchestrate
    result = await service.orchestrate(request)
    
    # Verify successful result
    assert result.status == "ok"
    assert result.rag_result is not None
    assert result.rule_result is not None
    assert result.notification_result is not None


def test_simple():
    """Simple sync test"""
    assert True


if __name__ == "__main__":
    pytest.main([__file__])

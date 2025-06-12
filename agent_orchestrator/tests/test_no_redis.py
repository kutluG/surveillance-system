#!/usr/bin/env python3
"""
Test orchestrator without Redis dependency
"""
import asyncio
from unittest.mock import AsyncMock
from orchestrator import OrchestratorService, OrchestrationRequest

async def test_without_redis():
    print("🔄 Testing orchestrator without Redis...")
    
    # Create service but don't initialize (which would try to connect to Redis)
    service = OrchestratorService()
    
    # Mock the clients instead of initializing
    service.redis_client = AsyncMock()
    service.http_client = AsyncMock()
    
    print("✅ Service created with mocked clients!")
    
    # Test request creation
    request = OrchestrationRequest(
        event_data={
            "camera_id": "cam_001",
            "timestamp": "2025-06-07T10:30:00Z",
            "label": "person_detected"
        },
        query="Person detected in restricted area"
    )
    print("✅ Request created!")
    
    # Mock successful HTTP responses
    rag_response = AsyncMock()
    rag_response.status_code = 200
    rag_response.json = lambda: {
        "linked_explanation": "Person detected successfully",
        "retrieved_context": [{"event": "test_event"}]
    }
    
    rule_response = AsyncMock()
    rule_response.status_code = 200
    rule_response.json = lambda: {
        "triggered_actions": [{
            "type": "send_notification",
            "rule_id": "person_alert",
            "parameters": {"message": "Person detected", "severity": "high"}
        }]
    }
    
    notifier_response = AsyncMock()
    notifier_response.status_code = 200
    notifier_response.json = lambda: {"status": "sent", "message_id": "123"}
    
    service.http_client.post.side_effect = [
        rag_response,
        rule_response,
        notifier_response
    ]
    
    print("🔄 Testing orchestration...")
    result = await service.orchestrate(request)
    
    print(f"✅ Orchestration completed!")
    print(f"   Status: {result.status}")
    print(f"   RAG Success: {result.details.get('rag_success', False)}")
    print(f"   Rule Success: {result.details.get('rule_success', False)}")
    print(f"   Notification Success: {result.details.get('notification_success', False)}")
    
    # Verify results
    assert result.status == "ok"
    assert result.rag_result is not None
    assert result.rule_result is not None
    assert result.notification_result is not None
    
    print("🎉 All assertions passed!")
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_without_redis())
        print(f"\n🎯 Final result: {'SUCCESS' if result else 'FAILED'}")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

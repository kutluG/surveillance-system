#!/usr/bin/env python3
"""
Quick validation test for Enhanced Prompt Service downstream integration schemas.
This script validates that all Pydantic models are working correctly and can generate JSON schemas.
"""

import json
import sys
from pathlib import Path

# Add the enhanced_prompt_service to Python path
sys.path.insert(0, str(Path(__file__).parent / "enhanced_prompt_service"))

try:
    from schemas import (
        PromptResponsePayload,
        HistoryRetrievalPayload, 
        ProactiveInsightPayload,
        Evidence,
        ConversationMessage
    )
    print("✅ Successfully imported all schemas")
except ImportError as e:
    print(f"❌ Failed to import schemas: {e}")
    sys.exit(1)

def test_prompt_response_payload():
    """Test PromptResponsePayload validation and JSON schema generation."""
    print("\n🧪 Testing PromptResponsePayload...")
    
    # Test with valid data
    valid_data = {
        "conversation_id": "conv_test_123",
        "user_id": "user_test_456", 
        "query": "Test query for validation",
        "response": "Test response from AI system",
        "response_type": "answer",
        "confidence_score": 0.85,
        "evidence_count": 2,
        "conversation_turn": 1,
        "processing_time_ms": 1500,
        "evidence": [
            {
                "event_id": "evt_test_001",
                "timestamp": "2024-01-15T10:30:00Z",
                "camera_id": "camera_test",
                "event_type": "motion_detected",
                "confidence": 0.9,
                "description": "Test motion detection"
            }
        ]
    }
    
    try:
        payload = PromptResponsePayload(**valid_data)
        print(f"   ✅ Valid payload created: {payload.conversation_id}")
        
        # Test JSON schema generation
        schema = PromptResponsePayload.model_json_schema()
        print(f"   ✅ JSON schema generated with {len(schema.get('properties', {}))} properties")
        
        # Test serialization
        json_data = payload.model_dump_json()
        print(f"   ✅ JSON serialization successful ({len(json_data)} characters)")
        
        return True
    except Exception as e:
        print(f"   ❌ PromptResponsePayload test failed: {e}")
        return False

def test_history_retrieval_payload():
    """Test HistoryRetrievalPayload validation and JSON schema generation."""
    print("\n🧪 Testing HistoryRetrievalPayload...")
    
    valid_data = {
        "conversation_id": "conv_hist_123",
        "user_id": "user_hist_456",
        "conversation_created": "2024-01-15T10:00:00Z",
        "total_messages": 4,
        "messages": [
            {
                "role": "user",
                "content": "Test user message",
                "timestamp": "2024-01-15T10:00:00Z",
                "metadata": {}
            },
            {
                "role": "assistant", 
                "content": "Test assistant response",
                "timestamp": "2024-01-15T10:00:15Z",
                "metadata": {"confidence": 0.85}
            }
        ],
        "user_queries": 2,
        "ai_responses": 2,
        "average_confidence": 0.85,
        "evidence_items_total": 5,
        "last_activity": "2024-01-15T10:30:00Z"
    }
    
    try:
        payload = HistoryRetrievalPayload(**valid_data)
        print(f"   ✅ Valid payload created: {payload.conversation_id}")
        
        schema = HistoryRetrievalPayload.model_json_schema()
        print(f"   ✅ JSON schema generated with {len(schema.get('properties', {}))} properties")
        
        json_data = payload.model_dump_json()
        print(f"   ✅ JSON serialization successful ({len(json_data)} characters)")
        
        return True
    except Exception as e:
        print(f"   ❌ HistoryRetrievalPayload test failed: {e}")
        return False

def test_proactive_insight_payload():
    """Test ProactiveInsightPayload validation and JSON schema generation."""
    print("\n🧪 Testing ProactiveInsightPayload...")
    
    valid_data = {
        "insight_id": "insight_test_001",
        "insight_type": "activity_spike",
        "severity": "medium",
        "title": "Test Activity Spike",
        "message": "Test insight message for validation",
        "confidence_score": 0.82,
        "analysis_period": "1h",
        "event_count": 45,
        "priority_level": 3,
        "affected_cameras": ["camera_1", "camera_2"]
    }
    
    try:
        payload = ProactiveInsightPayload(**valid_data)
        print(f"   ✅ Valid payload created: {payload.insight_id}")
        
        schema = ProactiveInsightPayload.model_json_schema()
        print(f"   ✅ JSON schema generated with {len(schema.get('properties', {}))} properties")
        
        json_data = payload.model_dump_json()
        print(f"   ✅ JSON serialization successful ({len(json_data)} characters)")
        
        return True
    except Exception as e:
        print(f"   ❌ ProactiveInsightPayload test failed: {e}")
        return False

def test_schema_examples():
    """Test that the examples in schemas are valid."""
    print("\n🧪 Testing schema examples...")
    
    try:
        # Test PromptResponsePayload example
        prompt_schema = PromptResponsePayload.model_json_schema()
        if 'examples' in prompt_schema:
            example = prompt_schema['examples'][0]
            payload = PromptResponsePayload(**example)
            print("   ✅ PromptResponsePayload example is valid")
        
        # Test HistoryRetrievalPayload example
        history_schema = HistoryRetrievalPayload.model_json_schema()
        if 'examples' in history_schema:
            example = history_schema['examples'][0]
            payload = HistoryRetrievalPayload(**example)
            print("   ✅ HistoryRetrievalPayload example is valid")
        
        # Test ProactiveInsightPayload example
        insight_schema = ProactiveInsightPayload.model_json_schema()
        if 'examples' in insight_schema:
            example = insight_schema['examples'][0]
            payload = ProactiveInsightPayload(**example)
            print("   ✅ ProactiveInsightPayload example is valid")
        
        return True
    except Exception as e:
        print(f"   ❌ Schema examples test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("🚀 Enhanced Prompt Service - Downstream Integration Schema Validation")
    print("=" * 70)
    
    tests = [
        test_prompt_response_payload,
        test_history_retrieval_payload,
        test_proactive_insight_payload,
        test_schema_examples
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 70)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Downstream integration schemas are ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the schema implementations.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

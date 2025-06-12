#!/usr/bin/env python3
"""
Test the orchestrator API endpoint directly
"""
import requests
import json

def test_orchestrator_api():
    """Test the orchestrator API endpoint"""
    print("🔄 Testing Orchestrator API...")
    
    # Test data
    test_request = {
        "event_data": {
            "camera_id": "cam_001",
            "timestamp": "2025-06-07T10:30:00Z",
            "label": "person_detected",
            "bbox": {"x": 100, "y": 150, "width": 50, "height": 100}
        },
        "query": "Person detected in restricted area",
        "notification_channels": ["email"],
        "recipients": ["admin@company.com"]
    }
    
    try:
        # Make request to orchestrator service
        response = requests.post(
            "http://localhost:8011/orchestrate",
            json=test_request,
            timeout=30
        )
        
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code in [200, 202, 503]:
            print("✅ API endpoint responding correctly!")
            return True
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to orchestrator service on port 8011")
        print("   Make sure the service is running with: uvicorn main:app --port 8011")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_orchestrator_api()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")

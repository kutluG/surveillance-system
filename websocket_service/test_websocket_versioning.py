"""
WebSocket Versioning Test Script
Tests both versioned endpoints and backwards compatibility redirects
"""

import asyncio
import websockets
import json
from datetime import datetime

# WebSocket URLs (adjust as needed)
WS_BASE_URL = "ws://localhost:8001"

async def test_versioned_endpoint(endpoint_path, client_id="test_client"):
    """Test a versioned WebSocket endpoint"""
    url = f"{WS_BASE_URL}{endpoint_path}"
    print(f"\n🔗 Testing versioned endpoint: {url}")
    
    try:
        async with websockets.connect(url) as websocket:
            print("   ✅ Connected successfully")
            
            # Listen for welcome message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                print(f"   📨 Received: {data.get('payload', {}).get('status', 'Unknown')}")
                print(f"   🏷️  Endpoint: {data.get('payload', {}).get('endpoint', 'Unknown')}")
                return True
            except asyncio.TimeoutError:
                print("   ⚠️  No welcome message received (timeout)")
                return False
                
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

async def test_redirect_endpoint(endpoint_path, client_id="test_client"):
    """Test an old endpoint that should redirect"""
    url = f"{WS_BASE_URL}{endpoint_path}"
    print(f"\n🔀 Testing redirect endpoint: {url}")
    
    try:
        async with websockets.connect(url) as websocket:
            print("   ✅ Connected (redirect endpoint)")
            
            # Listen for deprecation notice
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                
                if data.get("type") == "deprecation_notice":
                    print("   📢 Received deprecation notice:")
                    print(f"      Message: {data.get('message')}")
                    print(f"      Old endpoint: {data.get('old_endpoint')}")
                    print(f"      New endpoint: {data.get('new_endpoint')}")
                    print(f"      Action: {data.get('action')}")
                    
                    # Wait for connection close
                    try:
                        await websocket.wait_closed()
                        print(f"   🔒 Connection closed with code: {websocket.close_code}")
                        print(f"      Reason: {websocket.close_reason}")
                        return True
                    except Exception as close_e:
                        print(f"   ⚠️  Close error: {close_e}")
                        return True
                else:
                    print(f"   ⚠️  Unexpected message type: {data.get('type')}")
                    return False
                    
            except asyncio.TimeoutError:
                print("   ❌ No deprecation notice received (timeout)")
                return False
                
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

async def main():
    """Run all WebSocket tests"""
    print("🔌 WebSocket Versioning and Redirect Tests")
    print("=" * 50)
    
    # Test versioned endpoints
    print("\n📍 Testing Versioned Endpoints:")
    print("-" * 30)
    
    v1_events_success = await test_versioned_endpoint("/ws/v1/events/test_client")
    v1_alerts_success = await test_versioned_endpoint("/ws/v1/alerts/test_client")
    
    # Test redirect endpoints  
    print("\n📍 Testing Redirect Endpoints:")
    print("-" * 30)
    
    old_events_success = await test_redirect_endpoint("/ws/events/test_client")
    old_alerts_success = await test_redirect_endpoint("/ws/alerts/test_client")
    
    # Summary
    print("\n📊 Test Results Summary:")
    print("=" * 30)
    print(f"✅ /ws/v1/events: {'PASS' if v1_events_success else 'FAIL'}")
    print(f"✅ /ws/v1/alerts: {'PASS' if v1_alerts_success else 'FAIL'}")
    print(f"🔀 /ws/events (redirect): {'PASS' if old_events_success else 'FAIL'}")
    print(f"🔀 /ws/alerts (redirect): {'PASS' if old_alerts_success else 'FAIL'}")
    
    all_passed = all([v1_events_success, v1_alerts_success, old_events_success, old_alerts_success])
    print(f"\n🎯 Overall Result: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    if not all_passed:
        print("\n💡 Note: Make sure the WebSocket service and API Gateway are running:")
        print("   docker-compose up websocket_service api_gateway")

if __name__ == "__main__":
    print("Starting WebSocket tests...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test error: {e}")

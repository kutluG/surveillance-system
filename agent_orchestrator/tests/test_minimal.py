#!/usr/bin/env python3
"""
Minimal test to debug the issue
"""
print("Starting minimal test...")

try:
    print("1. Importing orchestrator...")
    from orchestrator import OrchestratorService, OrchestrationRequest
    print("   ✅ Import successful")
    
    print("2. Creating service...")
    service = OrchestratorService()
    print("   ✅ Service created")
    
    print("3. Creating request...")
    request = OrchestrationRequest(
        event_data={"camera_id": "test"},
        query="test"
    )
    print("   ✅ Request created")
    
    print("4. Test completed successfully!")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

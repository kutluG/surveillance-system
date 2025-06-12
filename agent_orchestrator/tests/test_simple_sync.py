#!/usr/bin/env python3
"""
Ultra simple test
"""

def main():
    print("Starting simple test...")
    
    try:
        from orchestrator import OrchestrationRequest
        print("✅ Import successful")
        
        request = OrchestrationRequest(
            event_data={"camera_id": "test"},
            query="test query"
        )
        print("✅ Request created")
        print(f"Request query: {request.query}")
        
        print("🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

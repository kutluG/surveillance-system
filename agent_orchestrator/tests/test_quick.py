#!/usr/bin/env python3
"""
Quick test for orchestrator
"""
import asyncio
from orchestrator import OrchestratorService, OrchestrationRequest

async def quick_test():
    print("🔄 Testing orchestrator creation...")
    service = OrchestratorService()
    print("✅ Service created!")
    
    print("🔄 Testing request creation...")
    request = OrchestrationRequest(
        event_data={"camera_id": "test", "label": "person_detected"},
        query="test query"
    )
    print("✅ Request created!")
    print(f"Request: {request}")
    
    return True

if __name__ == "__main__":
    result = asyncio.run(quick_test())
    print(f"Test result: {result}")

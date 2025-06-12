#!/usr/bin/env python3
"""
Test retention service HTTP endpoints directly using uvicorn and httpx.
"""

import asyncio
import subprocess
import time
import httpx
import signal
import os
import sys
from datetime import datetime


async def test_endpoints():
    """Test retention service endpoints by starting the server and making requests."""
    server_process = None
    
    try:
        # Start the retention service
        print("🚀 Starting retention service...")
        server_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "retention_service.main:app", 
            "--host", "127.0.0.1",
            "--port", "8001"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
          # Wait for server to start
        print("⏳ Waiting for server to start...")
        await asyncio.sleep(5)
        
        # Check if server started successfully
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print(f"❌ Server failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return
        
        base_url = "http://127.0.0.1:8001"
        
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            print("🔍 Testing health endpoint...")
            response = await client.get(f"{base_url}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            print("✓ Health endpoint working")
            
            # Test status endpoint
            print("🔍 Testing status endpoint...")
            response = await client.get(f"{base_url}/purge/status")
            assert response.status_code == 200
            data = response.json()
            assert "retention_days" in data
            assert "storage_path" in data
            assert "storage_type" in data
            print("✓ Status endpoint working")
            print(f"  - Retention period: {data['retention_days']} days")
            print(f"  - Storage path: {data['storage_path']}")
            print(f"  - Storage type: {data['storage_type']}")
            
            # Test docs endpoint
            print("🔍 Testing docs endpoint...")
            response = await client.get(f"{base_url}/docs")
            assert response.status_code == 200
            print("✓ OpenAPI docs endpoint working")
            
            print("\n🎉 All HTTP endpoint tests passed!")
            
    except Exception as e:
        print(f"❌ Endpoint test failed: {e}")
        raise
    finally:
        if server_process:
            print("🛑 Stopping retention service...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()


if __name__ == "__main__":
    asyncio.run(test_endpoints())

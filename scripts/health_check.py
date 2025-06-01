#!/usr/bin/env python3
"""
Health check script for the surveillance system.
Verifies all services are running and healthy.
"""

import requests
import sys
import time
from typing import Dict, List

# Service health check endpoints
SERVICES = {
    "Edge Service": "http://localhost:8001/health",
    "MQTT Bridge": "http://localhost:8002/health", 
    "Ingest Service": "http://localhost:8003/health",
    "RAG Service": "http://localhost:8004/health",
    "Prompt Service": "http://localhost:8005/health",
    "RuleGen Service": "http://localhost:8006/health",
    "Notifier": "http://localhost:8007/health",
    "VMS Service": "http://localhost:8008/health",
}

INFRASTRUCTURE = {
    "Postgres": "http://localhost:5432",
    "Redis": "http://localhost:6379", 
    "Kafka": "http://localhost:9092",
    "Weaviate": "http://localhost:8080/v1/.well-known/ready",
    "Prometheus": "http://localhost:9090/-/ready",
    "Grafana": "http://localhost:3000/api/health",
}

def check_service(name: str, url: str, timeout: int = 5) -> Dict[str, any]:
    """Check if a service is healthy."""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return {"status": "✅ HEALTHY", "response_time": response.elapsed.total_seconds()}
        else:
            return {"status": f"❌ ERROR ({response.status_code})", "response_time": None}
    except requests.exceptions.ConnectionError:
        return {"status": "🔴 DOWN", "response_time": None}
    except requests.exceptions.Timeout:
        return {"status": "⏱️ TIMEOUT", "response_time": None}
    except Exception as e:
        return {"status": f"❌ ERROR ({str(e)})", "response_time": None}

def main():
    """Run health checks for all services."""
    print("🔍 Surveillance System Health Check")
    print("=" * 50)
    
    all_healthy = True
    
    # Check application services
    print("\n📱 Application Services:")
    print("-" * 30)
    for name, url in SERVICES.items():
        result = check_service(name, url)
        status = result["status"]
        response_time = result["response_time"]
        
        if response_time:
            print(f"{name:<20} {status} ({response_time:.3f}s)")
        else:
            print(f"{name:<20} {status}")
            
        if "❌" in status or "🔴" in status:
            all_healthy = False
    
    # Check infrastructure services
    print("\n🏗️ Infrastructure Services:")
    print("-" * 30)
    for name, url in INFRASTRUCTURE.items():
        result = check_service(name, url)
        status = result["status"]
        response_time = result["response_time"]
        
        if response_time:
            print(f"{name:<20} {status} ({response_time:.3f}s)")
        else:
            print(f"{name:<20} {status}")
            
        if "❌" in status or "🔴" in status:
            all_healthy = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_healthy:
        print("🎉 All services are healthy!")
        print("\n📊 Access points:")
        print("   • Grafana:    http://localhost:3000")
        print("   • Prometheus: http://localhost:9090") 
        print("   • API Docs:   http://localhost:800X/docs")
        sys.exit(0)
    else:
        print("⚠️  Some services are not healthy!")
        print("\n🔧 Troubleshooting:")
        print("   • Check logs: make logs")
        print("   • Restart services: make restart")
        print("   • View status: make status")
        sys.exit(1)

if __name__ == "__main__":
    main()

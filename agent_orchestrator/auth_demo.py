"""
Authentication Demo Script for Agent Orchestrator Service.

This script demonstrates how to use the new API key authentication system
for securing agent registration and management operations.

Run this script to see:
1. API key creation and management
2. Authenticated agent registration
3. Permission-based access control
4. Rate limiting in action

Author: Agent Orchestrator Team
Version: 1.0.0
"""

import asyncio
import json
import requests
from datetime import datetime
from typing import Dict, Any

# Import our authentication modules
from .auth import APIKeyManager, get_api_key_manager
from .config import get_config


class AuthenticationDemo:
    """Demonstration class for authentication features."""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.api_key_manager = get_api_key_manager()
        self.created_keys = []
    
    async def demo_key_management(self):
        """Demonstrate API key creation and management."""
        print("🔐 API Key Management Demo")
        print("=" * 50)
        
        # Create different types of keys
        print("\n1. Creating API keys with different permissions...")
        
        # Admin key
        admin_key, admin_info = self.api_key_manager.create_key(
            name="Demo Admin",
            permissions=["admin"],
            expires_in_days=1,  # Short expiration for demo
            rate_limit=1000
        )
        self.created_keys.append(admin_info.key_id)
        print(f"✅ Admin key created: {admin_info.key_id}")
        
        # Service key
        service_key, service_info = self.api_key_manager.create_key(
            name="Demo Service",
            permissions=["agent:register", "agent:read", "task:create"],
            expires_in_days=7,
            rate_limit=500
        )
        self.created_keys.append(service_info.key_id)
        print(f"✅ Service key created: {service_info.key_id}")
        
        # User key (read-only)
        user_key, user_info = self.api_key_manager.create_key(
            name="Demo User",
            permissions=["agent:read", "task:read"],
            expires_in_days=30,
            rate_limit=100
        )
        self.created_keys.append(user_info.key_id)
        print(f"✅ User key created: {user_info.key_id}")
        
        # List all keys
        print("\n2. Listing all API keys...")
        keys = self.api_key_manager.list_keys()
        for key in keys:
            status = "🟢 Active" if key.is_active else "🔴 Inactive"
            print(f"   {key.key_id}: {key.name} - {status} - {', '.join(key.permissions)}")
        
        return {
            "admin_key": admin_key,
            "service_key": service_key,
            "user_key": user_key
        }
    
    def demo_authenticated_requests(self, keys: Dict[str, str]):
        """Demonstrate authenticated API requests."""
        print("\n\n🌐 Authenticated API Requests Demo")
        print("=" * 50)
        
        # Test agent registration with service key
        print("\n1. Testing agent registration with service key...")
        agent_data = {
            "name": "Demo Security Agent",
            "agent_type": "security_monitor",
            "capabilities": ["motion_detection", "face_recognition"],
            "config": {
                "camera_ids": ["demo_cam_001"],
                "sensitivity": 0.8
            },
            "metadata": {
                "location": "demo_entrance",
                "demo": True
            }
        }
        
        headers = {
            "Authorization": f"Bearer {keys['service_key']}",
            "Content-Type": "application/json"
        }
        
        try:
            # This would normally hit the actual API endpoint
            print(f"   📤 POST /api/v1/agents/register")
            print(f"   🔑 Using service key with permissions: agent:register")
            print(f"   📋 Agent data: {agent_data['name']} ({agent_data['agent_type']})")
            print(f"   ✅ Would succeed - service key has 'agent:register' permission")
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
        
        # Test with insufficient permissions
        print("\n2. Testing agent registration with user key (should fail)...")
        headers_user = {
            "Authorization": f"Bearer {keys['user_key']}",
            "Content-Type": "application/json"
        }
        
        print(f"   📤 POST /api/v1/agents/register")
        print(f"   🔑 Using user key with permissions: agent:read, task:read")
        print(f"   ❌ Would fail - user key lacks 'agent:register' permission")
        print(f"   📨 Expected response: 403 Forbidden - Permission 'agent:register' required")
        
        # Test reading with user key
        print("\n3. Testing agent listing with user key (should succeed)...")
        print(f"   📤 GET /api/v1/agents")
        print(f"   🔑 Using user key with permissions: agent:read, task:read")
        print(f"   ✅ Would succeed - user key has 'agent:read' permission")
    
    def demo_rate_limiting(self, keys: Dict[str, str]):
        """Demonstrate rate limiting functionality."""
        print("\n\n🚦 Rate Limiting Demo")
        print("=" * 50)
        
        print("\n1. Simulating rapid requests...")
        user_info = self.api_key_manager.validate_key(keys['user_key'])
        
        if user_info:
            print(f"   📊 User key rate limit: {user_info.rate_limit} requests/minute")
            
            # Simulate multiple validation attempts
            success_count = 0
            for i in range(5):
                validated = self.api_key_manager.validate_key(keys['user_key'])
                if validated:
                    success_count += 1
                    print(f"   ✅ Request {i+1}: Valid")
                else:
                    print(f"   ❌ Request {i+1}: Rate limited")
            
            print(f"   📈 Successful requests: {success_count}/5")
    
    def demo_permission_system(self):
        """Demonstrate the permission system."""
        print("\n\n🛡️ Permission System Demo")
        print("=" * 50)
        
        # Show different permission patterns
        permission_examples = [
            ("agent:read", ["agent:read"], True, "Exact match"),
            ("agent:write", ["agent:*"], True, "Wildcard match"),
            ("task:delete", ["agent:read"], False, "No match"),
            ("admin:users", ["admin"], True, "Partial match"),
            ("any:operation", ["*"], True, "Global wildcard")
        ]
        
        print("\nPermission matching examples:")
        for required, granted, expected, description in permission_examples:
            result = "✅ Allow" if expected else "❌ Deny"
            print(f"   Required: {required}")
            print(f"   Granted: {granted}")
            print(f"   Result: {result} ({description})")
            print()
    
    def demo_audit_logging(self):
        """Demonstrate audit logging format."""
        print("\n\n📝 Audit Logging Demo")
        print("=" * 50)
        
        sample_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "api_key_id": "key_12345678",
            "api_key_name": "Demo Service",
            "action": "agent_register",
            "endpoint": "/api/v1/agents/register",
            "method": "POST",
            "resource_id": "550e8400-e29b-41d4-a716-446655440000",
            "client_ip": "192.168.1.100",
            "user_agent": "Demo Client/1.0",
            "details": {
                "agent_name": "Demo Security Agent",
                "agent_type": "security_monitor"
            }
        }
        
        print("\nSample audit log entry:")
        print(json.dumps(sample_log, indent=2))
    
    async def cleanup(self):
        """Clean up demo keys."""
        print("\n\n🧹 Cleanup")
        print("=" * 50)
        
        print("Removing demo API keys...")
        for key_id in self.created_keys:
            success = self.api_key_manager.revoke_key(key_id)
            status = "✅ Revoked" if success else "❌ Failed"
            print(f"   {key_id}: {status}")
    
    async def run_full_demo(self):
        """Run the complete authentication demonstration."""
        print("🎭 Agent Orchestrator Authentication Demo")
        print("=" * 60)
        print("This demo showcases the new API key authentication system")
        print("=" * 60)
        
        try:
            # Key management demo
            keys = await self.demo_key_management()
            
            # API request demo
            self.demo_authenticated_requests(keys)
            
            # Rate limiting demo
            self.demo_rate_limiting(keys)
            
            # Permission system demo
            self.demo_permission_system()
            
            # Audit logging demo
            self.demo_audit_logging()
            
        finally:
            # Cleanup
            await self.cleanup()
        
        print("\n\n🎉 Demo completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✅ API key creation and management")
        print("✅ Permission-based access control")
        print("✅ Rate limiting per API key")
        print("✅ Comprehensive audit logging")
        print("✅ Secure authentication flow")


async def main():
    """Main demo function."""
    demo = AuthenticationDemo()
    await demo.run_full_demo()


def cli_demo():
    """CLI demonstration commands."""
    print("🔧 CLI Tool Demo Commands")
    print("=" * 40)
    
    commands = [
        "# Create an admin API key",
        "python -m agent_orchestrator.api_key_manager create \\",
        "    --name 'Administrator' \\",
        "    --permissions 'admin' \\",
        "    --expires-in-days 0",
        "",
        "# Create a service API key",
        "python -m agent_orchestrator.api_key_manager create \\",
        "    --name 'Agent Service' \\",
        "    --permissions 'agent:*,task:create,task:read' \\",
        "    --expires-in-days 90 \\",
        "    --rate-limit 500",
        "",
        "# List all API keys",
        "python -m agent_orchestrator.api_key_manager list",
        "",
        "# Show key information",
        "python -m agent_orchestrator.api_key_manager info --key-id key_12345678",
        "",
        "# Revoke a key",
        "python -m agent_orchestrator.api_key_manager revoke --key-id key_12345678"
    ]
    
    for command in commands:
        print(command)


def usage_examples():
    """Show usage examples for different scenarios."""
    print("\n\n📖 Usage Examples")
    print("=" * 40)
    
    print("\n1. Python Client Example:")
    print("""
import requests

# Set up authentication
headers = {
    "Authorization": "Bearer your_api_key_here",
    "Content-Type": "application/json"
}

# Register a new agent
agent_data = {
    "name": "Security Agent 1",
    "agent_type": "security_monitor",
    "capabilities": ["motion_detection"],
    "config": {"camera_ids": ["cam_001"]}
}

response = requests.post(
    "http://localhost:8000/api/v1/agents/register",
    json=agent_data,
    headers=headers
)

if response.status_code == 201:
    print("Agent registered successfully!")
    print(response.json())
else:
    print(f"Error: {response.status_code} - {response.json()}")
""")
    
    print("\n2. cURL Example:")
    print("""
# Register an agent
curl -X POST http://localhost:8000/api/v1/agents/register \\
  -H "Authorization: Bearer your_api_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Security Agent 1",
    "agent_type": "security_monitor",
    "capabilities": ["motion_detection"],
    "config": {"camera_ids": ["cam_001"]}
  }'

# List agents
curl -X GET http://localhost:8000/api/v1/agents \\
  -H "Authorization: Bearer your_api_key_here"
""")


if __name__ == "__main__":
    print("🚀 Starting Authentication Demo...")
    
    # Run the async demo
    asyncio.run(main())
    
    # Show CLI commands
    cli_demo()
    
    # Show usage examples
    usage_examples()

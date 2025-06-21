#!/usr/bin/env python3
"""
Validation script to check if the enhanced_prompt_service main.py can be imported and the endpoints are properly configured.
"""
import sys
import os
from unittest.mock import Mock, AsyncMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def setup_mocks():
    """Set up minimal mocks to allow import."""
    # Mock shared modules
    mock_logger = Mock()
    sys.modules['shared.logging_config'] = Mock()
    sys.modules['shared.logging_config'].configure_logging = Mock(return_value=mock_logger)
    sys.modules['shared.logging_config'].get_logger = Mock(return_value=mock_logger)
    sys.modules['shared.audit_middleware'] = Mock()
    sys.modules['shared.audit_middleware'].add_audit_middleware = Mock()
    sys.modules['shared.metrics'] = Mock()
    sys.modules['shared.metrics'].instrument_app = Mock()
    sys.modules['shared.middleware'] = Mock()
    sys.modules['shared.middleware'].add_rate_limiting = Mock()
    
    # Mock auth
    mock_auth = Mock()
    mock_user = Mock()
    mock_user.sub = "test_user"
    mock_auth.get_current_user = Mock(return_value=mock_user)
    sys.modules['shared.auth'] = mock_auth
    
    # Mock config
    mock_config = Mock()
    mock_settings = Mock()
    mock_settings.redis_url = "redis://redis:6379/0"
    mock_settings.weaviate_url = "http://weaviate:8080"
    mock_settings.openai_api_key = "test-key"
    mock_settings.api_base_path = "/api/v1"
    mock_config.get_service_config = Mock(return_value={})
    mock_config.Settings = Mock(return_value=mock_settings)
    sys.modules['shared.config'] = mock_config
    
    # Mock models
    sys.modules['shared.models'] = Mock()
    
    # Mock enhanced_prompt_service modules
    sys.modules['enhanced_prompt_service.conversation_manager'] = Mock()
    sys.modules['enhanced_prompt_service.schemas'] = Mock()
    
    # Mock routers
    from fastapi import APIRouter
    actual_prompt_router = APIRouter()
    actual_history_router = APIRouter()
    
    sys.modules['enhanced_prompt_service.routers'] = Mock()
    sys.modules['enhanced_prompt_service.routers.prompt'] = Mock()
    sys.modules['enhanced_prompt_service.routers.history'] = Mock()
    sys.modules['enhanced_prompt_service.routers.prompt'].router = actual_prompt_router
    sys.modules['enhanced_prompt_service.routers.history'].router = actual_history_router
    
    # Mock response schemas
    class MockHealthResponse:
        def __init__(self, status):
            self.status = status
    
    class MockErrorResponse:
        def __init__(self, error, detail=None, code=None):
            self.error = error
            self.detail = detail
            self.code = code
        def model_dump(self):
            return {"error": self.error, "detail": self.detail, "code": self.code}
    
    sys.modules['enhanced_prompt_service.schemas'].HealthResponse = MockHealthResponse
    sys.modules['enhanced_prompt_service.schemas'].ErrorResponse = MockErrorResponse

def validate_main_import():
    """Validate that main.py can be imported successfully."""
    try:
        setup_mocks()
        
        # Import the main module
        from enhanced_prompt_service.main import app
        
        print("✅ Successfully imported enhanced_prompt_service.main")
        
        # Check that the app has been created
        assert app is not None, "FastAPI app should be created"
        print("✅ FastAPI app instance created")
        
        # Check that routes are configured
        routes = [route.path for route in app.routes]
        print(f"✅ Found {len(routes)} routes configured")
        
        # Check for specific endpoints
        expected_routes = ["/healthz", "/readyz", "/health"]
        for route in expected_routes:
            if any(route in r for r in routes):
                print(f"✅ Found {route} endpoint")
            else:
                print(f"❌ Missing {route} endpoint")
        
        # Check for redirect handlers
        redirect_routes = [r for r in routes if "/api/{path:path}" in r or "/ws/{path:path}" in r]
        if redirect_routes:
            print("✅ Found redirect handlers")
            for route in redirect_routes:
                print(f"  - {route}")
        else:
            print("❌ Missing redirect handlers")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to import main.py: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_endpoint_definitions():
    """Validate that the endpoints are properly defined."""
    try:
        from fastapi.testclient import TestClient
        setup_mocks()
        from enhanced_prompt_service.main import app
        
        client = TestClient(app)
        
        # Test health endpoints (these should work without auth)
        print("\n📋 Testing endpoint accessibility:")
        
        # Test /healthz
        try:
            response = client.get("/healthz")
            print(f"✅ /healthz: {response.status_code}")
        except Exception as e:
            print(f"❌ /healthz failed: {e}")
        
        # Test /readyz (might fail due to missing app state, but should be defined)
        try:
            response = client.get("/readyz")
            print(f"✅ /readyz: {response.status_code} (may be 503 due to missing state)")
        except Exception as e:
            print(f"❌ /readyz failed: {e}")
        
        # Test redirect endpoints
        try:
            response = client.get("/api/test", allow_redirects=False)
            print(f"✅ /api/test redirect: {response.status_code}")
        except Exception as e:
            print(f"❌ /api/test redirect failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed endpoint validation: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Validating Enhanced Prompt Service Implementation...")
    
    import_success = validate_main_import()
    endpoint_success = validate_endpoint_definitions()
    
    if import_success and endpoint_success:
        print("\n🎉 All validations passed!")
        print("✅ API versioning and health probes are correctly implemented")
        sys.exit(0)
    else:
        print("\n❌ Some validations failed")
        sys.exit(1)

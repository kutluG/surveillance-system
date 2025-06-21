#!/usr/bin/env python3
"""
Validation script to test that the new integration and E2E tests can be imported and run.
"""
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_integration_imports():
    """Test that integration test modules can be imported."""
    try:
        print("🧪 Testing integration test imports...")
        
        # Test clip store integration tests
        from tests import test_clip_store
        print("✅ test_clip_store.py imported successfully")
        
        # Test API endpoint E2E tests
        from tests import test_api_endpoints  
        print("✅ test_api_endpoints.py imported successfully")
        
        # Verify test classes exist
        assert hasattr(test_clip_store, 'TestClipStoreIntegration')
        print("✅ TestClipStoreIntegration class found")
        
        assert hasattr(test_api_endpoints, 'TestAPIEndpoints')
        print("✅ TestAPIEndpoints class found")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_pytest_availability():
    """Test that pytest and required dependencies are available."""
    try:
        print("\n🔧 Testing pytest availability...")
        
        import pytest
        print(f"✅ pytest {pytest.__version__} available")
        
        import pytest_asyncio
        print(f"✅ pytest-asyncio available")
        
        import pytest_mock  
        print(f"✅ pytest-mock available")
        
        try:
            import httpx
            print(f"✅ httpx {httpx.__version__} available (required for FastAPI testing)")
        except ImportError:
            print("⚠️ httpx not available - install with: pip install httpx")
            
        try:
            import fakeredis
            print(f"✅ fakeredis available")
        except ImportError:
            print("⚠️ fakeredis not available - install with: pip install fakeredis")
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Install with: pip install pytest pytest-asyncio pytest-mock httpx fakeredis")
        return False

def test_fastapi_testclient():
    """Test that FastAPI TestClient can be imported."""
    try:
        print("\n🌐 Testing FastAPI TestClient...")
        
        from fastapi.testclient import TestClient
        print("✅ FastAPI TestClient imported successfully")
        
        # Test basic TestClient functionality
        from fastapi import FastAPI
        
        test_app = FastAPI()
        
        @test_app.get("/test")
        def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(test_app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.json() == {"message": "test"}
        print("✅ TestClient basic functionality works")
        
        return True
        
    except Exception as e:
        print(f"❌ FastAPI TestClient error: {e}")
        return False

def test_mock_patterns():
    """Test that mocking patterns work correctly."""
    try:
        print("\n🎭 Testing mock patterns...")
        
        from unittest.mock import Mock, patch, AsyncMock
        print("✅ unittest.mock imports work")
        
        # Test async mock
        async def test_async_function():
            return "async_result"
        
        mock = AsyncMock(return_value="mocked_result")
        
        # Test patching
        with patch('sys.version', 'mocked_version'):
            assert sys.version == 'mocked_version'
        print("✅ Patching works correctly")
        
        print("✅ Mock patterns work correctly")
        return True
        
    except Exception as e:
        print(f"❌ Mock pattern error: {e}")
        return False

def test_temporary_files():
    """Test temporary file operations."""
    try:
        print("\n📁 Testing temporary file operations...")
        
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a test file
            test_file = temp_path / "test_clip.mp4"
            test_file.write_bytes(b"dummy video content")
            
            assert test_file.exists()
            assert test_file.read_bytes() == b"dummy video content"
            
        print("✅ Temporary file operations work correctly")
        return True
        
    except Exception as e:
        print(f"❌ Temporary file error: {e}")
        return False

def main():
    """Run all validation tests."""
    print("🚀 Enhanced Prompt Service - Integration & E2E Test Validation")
    print("=" * 70)
    
    tests = [
        ("Integration Test Imports", test_integration_imports),
        ("Pytest Availability", test_pytest_availability), 
        ("FastAPI TestClient", test_fastapi_testclient),
        ("Mock Patterns", test_mock_patterns),
        ("Temporary Files", test_temporary_files)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {test_name}: PASSED")
            else:
                print(f"\n❌ {test_name}: FAILED")
        except Exception as e:
            print(f"\n❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 70)
    print("📊 Validation Summary")
    print("=" * 70)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All validation tests passed!")
        print("Your integration and E2E tests are ready to run.")
        print("\nNext steps:")
        print("1. Run: python run_integration_tests.py")
        print("2. Or: pytest tests/test_clip_store.py -v")
        print("3. Or: pytest tests/test_api_endpoints.py -v")
        return 0
    else:
        print(f"\n⚠️ {total - passed} validation test(s) failed.")
        print("Please install missing dependencies or fix issues before running tests.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

#!/usr/bin/env python3
"""
Integration test to verify all test modules can be imported and basic functionality works.
"""
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all test modules can be imported."""
    try:
        # Test importing test modules
        from tests import test_conversation_manager
        from tests import test_llm_client
        from tests import test_weaviate_client
        
        print("✓ All test modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_fixtures():
    """Test that conftest.py fixtures work."""
    try:
        from tests.conftest import (
            create_test_conversation,
            create_test_message,
            create_test_search_result
        )
        
        # Test fixture generators
        conv = create_test_conversation()
        msg = create_test_message()
        result = create_test_search_result()
        
        assert conv["id"] == "test-conv-123"
        assert msg["role"] == "user"
        assert result["event_id"] == "event-123"
        
        print("✓ Fixture generators work correctly")
        return True
    except Exception as e:
        print(f"✗ Fixture error: {e}")
        return False

def test_mock_setup():
    """Test that mock setup works."""
    try:
        from unittest.mock import Mock
        
        # Test fakeredis import
        try:
            import fakeredis
            fake_redis = fakeredis.FakeRedis()
            fake_redis.set("test", "value")
            assert fake_redis.get("test") == b"value"
            print("✓ fakeredis works correctly")
        except ImportError:
            print("⚠ fakeredis not installed - will be installed during test setup")
        
        # Test basic mocking
        mock_obj = Mock()
        mock_obj.method.return_value = "mocked"
        assert mock_obj.method() == "mocked"
        print("✓ Basic mocking works")
        
        return True
    except Exception as e:
        print(f"✗ Mock setup error: {e}")
        return False

def main():
    """Run all basic tests."""
    print("Running basic integration tests...")
    print("-" * 40)
    
    tests = [
        test_imports,
        test_fixtures,
        test_mock_setup
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("-" * 40)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All basic tests passed! Test framework is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the setup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

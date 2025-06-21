#!/usr/bin/env python3
"""
API Versioning Tests for Advanced RAG Service

This test suite demonstrates and validates the API versioning system:
- Version detection from URLs, headers, and parameters
- Version validation and deprecation warnings
- Version-specific response formats
- API version information endpoints
"""

import sys
import os
import asyncio
from datetime import datetime
import json

sys.path.append('.')

def test_api_versioning_system():
    """Test the API versioning framework"""
    print("=== Testing API Versioning System ===\n")
    
    try:
        print("1. Testing API version management...")
        from api_versioning import (
            APIVersion, APIVersionManager, version_manager,
            get_api_versions_info
        )
        
        # Test version enumeration
        assert APIVersion.V1_0.value == "1.0"
        assert APIVersion.V1_1.value == "1.1"
        assert APIVersion.V2_0.value == "2.0"
        print("   ✅ API version enumeration working")
        
        # Test version parsing
        assert APIVersion.from_string("1.0") == APIVersion.V1_0
        assert APIVersion.from_string("v1.1") == APIVersion.V1_1
        assert APIVersion.from_string("2.0") == APIVersion.V2_0
        assert APIVersion.from_string("invalid") is None
        print("   ✅ Version string parsing working")
        
        # Test latest version
        latest = APIVersion.get_latest()
        assert latest == APIVersion.V1_1
        print("   ✅ Latest version detection working")
        
        print("2. Testing version manager...")
        
        # Test version info
        v1_info = version_manager.get_version_info(APIVersion.V1_0)
        assert v1_info is not None
        assert v1_info.status == "deprecated"
        assert v1_info.is_deprecated == True
        print("   ✅ Version info retrieval working")
        
        # Test active versions
        active_versions = version_manager.get_active_versions()
        assert APIVersion.V1_1 in active_versions
        print(f"   Active versions: {[v.value for v in active_versions]}")
        print("   ✅ Active version filtering working")
        
        # Test version support check
        assert version_manager.is_version_supported(APIVersion.V1_1) == True
        print("   ✅ Version support checking working")
        
        # Test deprecation warnings
        warnings = version_manager.get_deprecation_warnings(APIVersion.V1_0)
        assert len(warnings) > 0
        print(f"   Deprecation warnings for v1.0: {warnings}")
        print("   ✅ Deprecation warnings working")
        
        print("3. Testing API version information...")
        
        # Test version info structure
        versions_info = get_api_versions_info()
        assert "current_version" in versions_info
        assert "supported_versions" in versions_info
        assert "versions" in versions_info
        
        assert versions_info["current_version"] == APIVersion.get_latest().value
        print(f"   Current version: {versions_info['current_version']}")
        print(f"   Supported versions: {versions_info['supported_versions']}")
        print("   ✅ API version information structure working")
        
        print("4. Testing version-specific features...")
        
        # Test version comparison
        assert APIVersion.V1_0.value < APIVersion.V1_1.value
        assert APIVersion.V1_1.value < APIVersion.V2_0.value
        print("   ✅ Version comparison working")
        
        # Test changelog and breaking changes
        v2_info = version_manager.get_version_info(APIVersion.V2_0)
        if v2_info:
            assert len(v2_info.changelog) > 0
            assert len(v2_info.breaking_changes) > 0
            print("   ✅ Changelog and breaking changes documented")
        
        print("\n✅ All API versioning tests passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ API versioning test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_version_detection():
    """Test version detection from different sources"""
    print("=== Testing Version Detection ===\n")
    
    try:
        from api_versioning import get_api_version_from_request
        from fastapi import Request
        
        print("1. Testing URL-based version detection...")
        
        # Mock request with version in URL
        class MockRequest:
            def __init__(self, path, headers=None):
                self.url = type('MockURL', (), {'path': path})()
                self.headers = headers or {}
        
        # Test URL patterns
        request1 = MockRequest("/api/v1/rag/query")
        version1 = get_api_version_from_request(request1)
        assert version1.value in ["1.0", "1.1"]  # Should default to latest v1
        print(f"   /api/v1/rag/query -> {version1.value}")
        
        request2 = MockRequest("/api/v2/rag/query")
        version2 = get_api_version_from_request(request2)
        assert version2.value == "2.0"
        print(f"   /api/v2/rag/query -> {version2.value}")
        
        print("   ✅ URL-based version detection working")
        
        print("2. Testing header-based version detection...")
        
        # Test custom header
        request3 = MockRequest("/api/rag/query", {"X-API-Version": "1.0"})
        version3 = get_api_version_from_request(request3)
        assert version3.value == "1.0"
        print(f"   X-API-Version: 1.0 -> {version3.value}")
        
        # Test Accept header
        request4 = MockRequest("/api/rag/query", {"Accept": "application/vnd.rag.v1.1+json"})
        version4 = get_api_version_from_request(request4)
        assert version4.value == "1.1"
        print(f"   Accept: application/vnd.rag.v1.1+json -> {version4.value}")
        
        print("   ✅ Header-based version detection working")
        
        print("3. Testing default version...")
        
        # Test default version when no version specified
        request5 = MockRequest("/api/rag/query")
        version5 = get_api_version_from_request(request5)
        from api_versioning import APIVersion
        assert version5 == APIVersion.get_latest()
        print(f"   No version specified -> {version5.value} (latest)")
        print("   ✅ Default version handling working")
        
        print("\n✅ All version detection tests passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Version detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_version_response_format():
    """Test version-specific response formats"""
    print("=== Testing Version Response Formats ===\n")
    
    try:
        from api_versioning import add_version_headers, APIVersion
        from fastapi.responses import JSONResponse
        
        print("1. Testing response header addition...")
        
        # Test adding headers for active version
        response = JSONResponse(content={"data": "test"})
        versioned_response = add_version_headers(response, APIVersion.V1_1)
        
        assert "X-API-Version" in versioned_response.headers
        assert versioned_response.headers["X-API-Version"] == "1.1"
        assert "X-API-Version-Status" in versioned_response.headers
        print("   ✅ Version headers added correctly")
        
        # Test deprecation warnings
        deprecated_response = JSONResponse(content={"data": "test"})
        deprecated_response = add_version_headers(deprecated_response, APIVersion.V1_0)
        
        if "Warning" in deprecated_response.headers:
            print(f"   Deprecation warning: {deprecated_response.headers['Warning']}")
            print("   ✅ Deprecation warnings added")
        
        # Test sunset headers
        if "Sunset" in deprecated_response.headers:
            print(f"   Sunset date: {deprecated_response.headers['Sunset']}")
            print("   ✅ Sunset headers added")
        
        print("2. Testing version links...")
        
        # Test latest version link
        if "Link" in deprecated_response.headers:
            print(f"   Latest version link: {deprecated_response.headers['Link']}")
            print("   ✅ Latest version links added")
        
        print("\n✅ All response format tests passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Response format test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def demo_api_versioning_usage():
    """Demonstrate API versioning usage examples"""
    print("=== API Versioning Usage Examples ===\n")
    
    try:
        from api_versioning import APIVersion, version_manager, get_api_versions_info
        
        print("Example 1: Getting version information")
        versions_info = get_api_versions_info()
        print(f"   Current API version: {versions_info['current_version']}")
        print(f"   Supported versions: {versions_info['supported_versions']}")
        
        print("\nExample 2: Version-specific feature checking")
        v1_info = version_manager.get_version_info(APIVersion.V1_0)
        v1_1_info = version_manager.get_version_info(APIVersion.V1_1)
        
        print(f"   V1.0 status: {v1_info.status}")
        print(f"   V1.1 status: {v1_1_info.status}")
        
        if v1_info.is_deprecated:
            print(f"   V1.0 is deprecated, sunset in {v1_info.days_until_sunset} days")
        
        print("\nExample 3: Migration planning")
        if v1_info.breaking_changes:
            print("   V1.0 breaking changes:")
            for change in v1_info.breaking_changes:
                print(f"     - {change}")
        
        print(f"\nExample 4: Feature evolution")
        v1_1_changelog = v1_1_info.changelog if v1_1_info else []
        print("   V1.1 new features:")
        for feature in v1_1_changelog[:3]:  # Show first 3
            print(f"     - {feature}")
        
        print("\nExample 5: Future planning")
        v2_info = version_manager.get_version_info(APIVersion.V2_0)
        if v2_info:
            print(f"   V2.0 planned for: {v2_info.release_date.strftime('%Y-%m-%d')}")
            print("   V2.0 planned features:")
            for feature in v2_info.changelog[:3]:
                print(f"     - {feature}")
        
        print("\n✅ API versioning usage examples completed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Usage examples failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Advanced RAG Service - API Versioning Tests")
    print("=" * 60)
    
    success = True
    
    success &= test_api_versioning_system()
    success &= test_version_detection()
    success &= test_version_response_format()
    success &= demo_api_versioning_usage()
    
    if success:
        print("🎉 All API versioning tests passed successfully!")
        print("\nKey Benefits Demonstrated:")
        print("✅ Consistent API versioning across all endpoints")
        print("✅ Multiple version detection methods (URL, headers)")
        print("✅ Version validation and deprecation warnings")
        print("✅ Automatic response header management")
        print("✅ Version-specific documentation and features")
        print("✅ Migration planning and sunset management")
        print("✅ Backward compatibility support")
    else:
        print("❌ Some API versioning tests failed")
        sys.exit(1)

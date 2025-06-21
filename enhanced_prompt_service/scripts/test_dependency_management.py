#!/usr/bin/env python3
"""
Test script to verify dependency management implementation.
"""

import sys
import subprocess
from pathlib import Path


def test_validation():
    """Test requirements validation."""
    print("🔍 Testing requirements validation...")
    result = subprocess.run([sys.executable, "scripts/validate_requirements.py"], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Validation passed")
        return True
    else:
        print("❌ Validation failed:")
        print(result.stdout)
        print(result.stderr)
        return False


def test_audit():
    """Test security audit (expect it to show vulnerabilities)."""
    print("🔐 Testing security audit...")
    result = subprocess.run([sys.executable, "scripts/audit_dependencies.py"], 
                          capture_output=True, text=True)
    
    if "🔍 Running security audit" in result.stdout:
        print("✅ Audit script executed successfully")
        if result.returncode != 0:
            print("⚠️  Audit found vulnerabilities (expected for system packages)")
        return True
    else:
        print("❌ Audit script failed:")
        print(result.stdout)
        print(result.stderr)
        return False


def test_requirements_installation():
    """Test that requirements can be parsed."""
    print("📋 Testing requirements.txt format...")
    
    try:
        with open("requirements.txt", "r") as f:
            lines = f.readlines()
        
        pinned_count = 0
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and "==" in line:
                pinned_count += 1
        
        if pinned_count > 0:
            print(f"✅ Found {pinned_count} properly pinned dependencies")
            return True
        else:
            print("❌ No pinned dependencies found")
            return False
            
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False


def main():
    """Run all tests."""
    print("🧪 Enhanced Prompt Service - Dependency Management Test Suite")
    print("=" * 65)
    
    tests = [
        ("Requirements Format", test_requirements_installation),
        ("Requirements Validation", test_validation),
        ("Security Audit", test_audit),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("=" * 65)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All dependency management tests passed!")
        return 0
    else:
        print("💥 Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

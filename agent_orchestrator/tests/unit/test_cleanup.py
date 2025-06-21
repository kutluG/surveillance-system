#!/usr/bin/env python3
"""
Test Organization Cleanup Script

This script provides utilities for managing the old archived test files
and cleaning up the test structure.
"""

import os
import shutil
from pathlib import Path


def list_archived_tests():
    """List all archived test files"""
    archive_dir = Path("tests_archive")
    if not archive_dir.exists():
        print("❌ No tests_archive directory found")
        return
    
    print("📁 Archived test files:")
    for file in archive_dir.glob("test_*.py"):
        size = file.stat().st_size
        print(f"  - {file.name} ({size} bytes)")


def remove_archived_tests():
    """Remove all archived test files (use with caution)"""
    archive_dir = Path("tests_archive")
    if not archive_dir.exists():
        print("❌ No tests_archive directory found")
        return
    
    files = list(archive_dir.glob("test_*.py"))
    if not files:
        print("✅ No archived test files to remove")
        return
    
    print(f"🗑️  Removing {len(files)} archived test files...")
    for file in files:
        file.unlink()
        print(f"  - Removed {file.name}")
    
    # Remove the archive directory if empty
    try:
        archive_dir.rmdir()
        print("✅ Removed empty tests_archive directory")
    except OSError:
        print("ℹ️  tests_archive directory not empty (contains other files)")


def validate_current_test_structure():
    """Validate that the new test structure is properly set up"""
    print("🔍 Validating current test structure...")
    
    required_paths = [
        "tests/",
        "tests/unit/",
        "tests/integration/", 
        "tests/e2e/",
        "tests/unit/test_core_components.py",
        "tests/integration/test_service_integration.py",
        "tests/e2e/test_api_workflows.py",
        "test_config.py",
        "test_runner.py",
        "pytest.ini"
    ]
    
    missing = []
    for path in required_paths:
        if not Path(path).exists():
            missing.append(path)
    
    if missing:
        print("❌ Missing required files/directories:")
        for path in missing:
            print(f"  - {path}")
    else:
        print("✅ All required test structure files present")
    
    return len(missing) == 0


def show_test_statistics():
    """Show statistics about the test reorganization"""
    print("📊 Test Organization Statistics:")
    
    # Count archived files
    archive_dir = Path("tests_archive")
    archived_count = len(list(archive_dir.glob("test_*.py"))) if archive_dir.exists() else 0
    
    # Count current test files
    current_tests = []
    for test_dir in ["tests/unit", "tests/integration", "tests/e2e"]:
        if Path(test_dir).exists():
            current_tests.extend(Path(test_dir).glob("test_*.py"))
    
    # Add root test files
    for test_file in ["test_config.py"]:
        if Path(test_file).exists():
            current_tests.append(Path(test_file))
    
    print(f"  📁 Archived test files: {archived_count}")
    print(f"  📝 Current organized test files: {len(current_tests)}")
    print(f"  📈 Organization improvement: {archived_count} → {len(current_tests)} files")
    
    if current_tests:
        print("  📋 Current test structure:")
        for test_file in sorted(current_tests):
            print(f"    - {test_file}")


if __name__ == "__main__":
    import sys
    
    print("🧪 Test Organization Cleanup Tool")
    print("=" * 40)
    
    if len(sys.argv) < 2:
        print("Usage: python test_cleanup.py <command>")
        print("Commands:")
        print("  list     - List archived test files")
        print("  validate - Validate current test structure")
        print("  stats    - Show test organization statistics")
        print("  remove   - Remove archived test files (DANGEROUS)")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_archived_tests()
    elif command == "validate":
        if validate_current_test_structure():
            print("✅ Test structure validation passed")
        else:
            print("❌ Test structure validation failed")
            sys.exit(1)
    elif command == "stats":
        show_test_statistics()
    elif command == "remove":
        print("⚠️  WARNING: This will permanently delete archived test files!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() == "yes":
            remove_archived_tests()
        else:
            print("❌ Cancelled")
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)

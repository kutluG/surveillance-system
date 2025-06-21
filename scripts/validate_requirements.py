#!/usr/bin/env python3
"""
Validation script to ensure all Python dependencies are properly pinned.

This script checks that all packages in requirements.txt files have pinned versions
(using == operator) to ensure reproducible builds.

Usage:
    python scripts/validate_requirements.py
    python scripts/validate_requirements.py path/to/requirements.txt

Returns:
    Exit code 0: All dependencies are properly pinned
    Exit code 1: Unpinned dependencies found
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple


def check_requirements_file(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Check a single requirements file for unpinned dependencies.
    
    Args:
        file_path: Path to the requirements file
        
    Returns:
        Tuple of (is_valid, list_of_unpinned_packages)
    """
    unpinned_packages = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ Requirements file not found: {file_path}")
        return False, [f"File not found: {file_path}"]
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False, [f"Error reading file: {e}"]
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
            
        # Skip -e (editable) installs and other pip options
        if line.startswith('-'):
            continue
            
        # Check for proper version pinning
        # We require == for exact version pinning
        if '==' not in line:
            # Check if it has other version specifiers (>=, <=, ~=, etc.)
            has_version_spec = any(op in line for op in ['>=', '<=', '>', '<', '~=', '!='])
            
            if has_version_spec:
                unpinned_packages.append(f"Line {line_num}: {line} (uses flexible versioning instead of exact pinning)")
            else:
                unpinned_packages.append(f"Line {line_num}: {line} (no version specified)")
        else:
            # Additional validation: ensure the pinned version is not empty
            parts = line.split('==')
            if len(parts) != 2 or not parts[1].strip():
                unpinned_packages.append(f"Line {line_num}: {line} (invalid version format)")
    
    return len(unpinned_packages) == 0, unpinned_packages


def find_requirements_files() -> List[Path]:
    """Find all requirements.txt files in the project."""
    project_root = Path(__file__).parent.parent
    requirements_files = []
    
    # Look for requirements files in common locations
    common_patterns = [
        "requirements.txt",
        "*/requirements.txt",
        "*/requirements/*.txt",
        "**/requirements.txt"
    ]
    
    for pattern in common_patterns:
        requirements_files.extend(project_root.glob(pattern))
    
    return sorted(set(requirements_files))


def main():
    """Main validation function."""
    print("🔍 Validating Python dependency version pinning...")
    
    # Check if specific file was provided
    if len(sys.argv) > 1:
        requirements_files = [Path(sys.argv[1])]
        print(f"📁 Checking specific file: {requirements_files[0]}")
    else:
        # Find all requirements files
        requirements_files = find_requirements_files()
        print(f"📁 Found {len(requirements_files)} requirements files to check")
    
    if not requirements_files:
        print("❌ No requirements.txt files found!")
        return 1
    
    overall_valid = True
    total_unpinned = 0
    
    for req_file in requirements_files:
        print(f"\n📋 Checking {req_file}...")
        
        is_valid, unpinned = check_requirements_file(req_file)
        
        if is_valid:
            print(f"✅ All dependencies in {req_file.name} are properly pinned")
        else:
            print(f"❌ Found {len(unpinned)} unpinned dependencies in {req_file.name}:")
            for package in unpinned:
                print(f"   • {package}")
            overall_valid = False
            total_unpinned += len(unpinned)
    
    print(f"\n{'='*60}")
    if overall_valid:
        print("✅ All dependencies are properly pinned!")
        print("🎉 Reproducible builds ensured!")
        return 0
    else:
        print(f"❌ Found {total_unpinned} unpinned dependencies across all files")
        print("\n🔧 To fix unpinned dependencies:")
        print("   1. Pin each package to a specific version using ==")
        print("   2. Example: requests==2.31.0 instead of requests>=2.0.0")
        print("   3. Use 'pip freeze' to see currently installed versions")
        print("   4. Consider using 'pip-tools' for better dependency management")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

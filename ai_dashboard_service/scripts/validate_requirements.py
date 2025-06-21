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
            
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
                
            # Skip options like -r, -e, --extra-index-url
            if line.startswith('-'):
                continue
                
            # Check for proper version pinning
            # Allow == pinning, but flag >= or ~ or other operators
            if '==' not in line:
                # Check if it contains other version specifiers
                version_specifiers = ['>=', '<=', '>', '<', '~=', '!=']
                has_version_spec = any(spec in line for spec in version_specifiers)
                
                if has_version_spec:
                    unpinned_packages.append(f"{file_path}:{line_num} - {line} (not pinned with ==)")
                else:
                    unpinned_packages.append(f"{file_path}:{line_num} - {line} (no version specified)")
                    
    except FileNotFoundError:
        print(f"❌ Requirements file not found: {file_path}")
        return False, [f"File not found: {file_path}"]
        
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False, [f"Error reading {file_path}: {e}"]
    
    return len(unpinned_packages) == 0, unpinned_packages


def find_requirements_files() -> List[Path]:
    """Find all requirements.txt files in the current directory and subdirectories."""
    current_dir = Path.cwd()
    requirements_files = []
    
    # Look for requirements.txt files
    for req_file in current_dir.rglob("requirements*.txt"):
        requirements_files.append(req_file)
    
    return requirements_files


def main():
    """Main validation function."""
    print("🔍 Validating Python dependency pinning...")
    
    # Check if specific file was provided
    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return 1
        requirements_files = [file_path]
    else:
        # Find all requirements files
        requirements_files = find_requirements_files()
        
    if not requirements_files:
        print("❌ No requirements.txt files found")
        return 1
    
    print(f"📋 Found {len(requirements_files)} requirements file(s)")
    
    all_valid = True
    total_unpinned = []
    
    for req_file in requirements_files:
        print(f"  📄 Checking {req_file}")
        is_valid, unpinned = check_requirements_file(req_file)
        
        if not is_valid:
            all_valid = False
            total_unpinned.extend(unpinned)
            print(f"    ❌ Found {len(unpinned)} unpinned dependencies")
        else:
            print(f"    ✅ All dependencies properly pinned")
    
    if not all_valid:
        print(f"\n❌ Found {len(total_unpinned)} unpinned dependencies:")
        for unpinned in total_unpinned:
            print(f"  • {unpinned}")
        print("\n💡 All dependencies should be pinned with == for reproducible builds")
        return 1
    
    print("\n✅ All dependencies are properly pinned!")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

#!/usr/bin/env python3
"""
Requirements validation script for enhanced_prompt_service.

This script ensures all dependencies in requirements.txt are properly pinned
to specific versions using the == operator for reproducible builds.

Usage:
    python scripts/validate_requirements.py

Returns:
    Exit code 0: All dependencies are properly pinned
    Exit code 1: Unpinned dependencies found or validation failed
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple, Dict


def parse_requirement_line(line: str) -> Tuple[str, str, bool]:
    """
    Parse a requirement line and return (package_name, version_spec, is_pinned).
    
    Args:
        line: A line from requirements.txt
        
    Returns:
        Tuple of (package_name, version_spec, is_pinned)
    """
    line = line.strip()
    
    # Skip empty lines and comments
    if not line or line.startswith('#'):
        return "", "", True
    
    # Handle extras like python-jose[cryptography]==3.4.0
    if '[' in line and ']' in line:
        # Extract package name with extras
        package_match = re.match(r'^([^<>=!\s]+(?:\[[^\]]+\])?)', line)
    else:
        # Extract package name without extras
        package_match = re.match(r'^([^<>=!\s]+)', line)
    
    if not package_match:
        return line, "invalid", False
    
    package_name = package_match.group(1)
    
    # Check for exact version pinning (==)
    if '==' in line:
        version_spec = line.split('==')[1].strip()
        return package_name, version_spec, True
    
    # Check for other version specifiers (not properly pinned)
    version_patterns = ['>=', '<=', '>', '<', '~=', '!=']
    for pattern in version_patterns:
        if pattern in line:
            version_part = line.split(pattern)[1].strip()
            return package_name, f"{pattern}{version_part}", False
    
    # No version specified at all
    return package_name, "no version", False


def validate_requirements_file(file_path: Path) -> Tuple[bool, List[str], Dict[str, List[str]]]:
    """
    Validate a requirements file for proper version pinning.
    
    Args:
        file_path: Path to the requirements.txt file
        
    Returns:
        Tuple of (is_valid, error_messages, stats)
    """
    if not file_path.exists():
        return False, [f"Requirements file not found: {file_path}"], {}
    
    errors = []
    stats = {
        'total_packages': 0,
        'pinned_packages': 0,
        'unpinned_packages': 0,
        'invalid_lines': 0,
        'pinned_list': [],
        'unpinned_list': [],
        'invalid_list': []
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        line_number = 0
        for line in lines:
            line_number += 1
            original_line = line.strip()
            
            # Skip empty lines and comments
            if not original_line or original_line.startswith('#'):
                continue
            
            package_name, version_spec, is_pinned = parse_requirement_line(original_line)
            
            if not package_name:
                continue
            
            stats['total_packages'] += 1
            
            if version_spec == "invalid":
                stats['invalid_lines'] += 1
                stats['invalid_list'].append(f"Line {line_number}: {original_line}")
                errors.append(f"Line {line_number}: Invalid requirement format: {original_line}")
                continue
            
            if is_pinned:
                stats['pinned_packages'] += 1
                stats['pinned_list'].append(f"{package_name}=={version_spec}")
            else:
                stats['unpinned_packages'] += 1
                stats['unpinned_list'].append(f"{package_name} ({version_spec})")
                errors.append(f"Line {line_number}: Unpinned dependency: {package_name} ({version_spec})")
        
    except Exception as e:
        return False, [f"Error reading requirements file: {e}"], stats
    
    is_valid = len(errors) == 0
    return is_valid, errors, stats


def print_validation_results(is_valid: bool, errors: List[str], stats: Dict[str, List[str]]):
    """Print formatted validation results."""
    print("📊 Validation Results:")
    print("-" * 50)
    
    print(f"📦 Total packages: {stats['total_packages']}")
    print(f"✅ Properly pinned: {stats['pinned_packages']}")
    print(f"❌ Unpinned: {stats['unpinned_packages']}")
    print(f"🚫 Invalid lines: {stats['invalid_lines']}")
    
    if stats['pinned_list']:
        print(f"\n✅ Properly pinned packages ({len(stats['pinned_list'])}):")
        for pkg in sorted(stats['pinned_list']):
            print(f"   • {pkg}")
    
    if stats['unpinned_list']:
        print(f"\n❌ Unpinned packages ({len(stats['unpinned_list'])}):")
        for pkg in sorted(stats['unpinned_list']):
            print(f"   • {pkg}")
    
    if stats['invalid_list']:
        print(f"\n🚫 Invalid lines ({len(stats['invalid_list'])}):")
        for line in stats['invalid_list']:
            print(f"   • {line}")
    
    if not is_valid:
        print(f"\n💥 Validation failed with {len(errors)} errors:")
        for error in errors:
            print(f"   • {error}")
        
        print(f"\n🔧 To fix unpinned dependencies:")
        print("1. Install the packages: pip install -r requirements.txt")
        print("2. Generate pinned versions: pip freeze > requirements.txt")
        print("3. Review and clean up the generated file")
        print("4. Run this validation script again")


def main():
    """Main function to validate requirements."""
    print("🔍 Enhanced Prompt Service - Requirements Validation")
    print("=" * 55)
    
    # Find requirements.txt file
    requirements_file = Path("requirements.txt")
    
    # Check if we're in the right directory
    if not requirements_file.exists():
        # Try to find it in the enhanced_prompt_service directory
        alt_file = Path("enhanced_prompt_service/requirements.txt")
        if alt_file.exists():
            requirements_file = alt_file
        else:
            print("❌ requirements.txt not found in current directory or enhanced_prompt_service/")
            print("Please run from the service root directory or project root.")
            return 1
    
    print(f"📋 Validating: {requirements_file}")
    
    # Validate the requirements file
    is_valid, errors, stats = validate_requirements_file(requirements_file)
    
    # Print results
    print_validation_results(is_valid, errors, stats)
    
    if is_valid:
        print("\n🎉 All dependencies are properly pinned!")
        return 0
    else:
        print(f"\n💥 Validation failed - {stats['unpinned_packages']} packages need version pinning!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

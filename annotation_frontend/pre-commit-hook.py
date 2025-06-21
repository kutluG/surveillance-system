#!/usr/bin/env python3
"""
Pre-commit hook for dependency validation.

This script runs as a git pre-commit hook to ensure that:
1. All dependencies in requirements.txt are properly pinned
2. No security vulnerabilities are introduced
3. No duplicate dependencies exist

Installation:
    1. Copy this file to .git/hooks/pre-commit
    2. Make it executable: chmod +x .git/hooks/pre-commit

Usage:
    This hook runs automatically before each commit.
    To bypass: git commit --no-verify
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def check_staged_requirements_files():
    """Find staged requirements.txt files."""
    success, stdout, stderr = run_command("git diff --cached --name-only")
    
    if not success:
        print(f"❌ Failed to get staged files: {stderr}")
        return []
    
    staged_files = stdout.strip().split('\n') if stdout.strip() else []
    requirements_files = [f for f in staged_files if f.endswith('requirements.txt')]
    
    return requirements_files


def validate_requirements_file(req_file):
    """Validate a specific requirements file."""
    print(f"🔍 Validating {req_file}...")
    
    # Get the directory containing the requirements file
    req_dir = Path(req_file).parent
    
    # Check if validation script exists in the same directory
    validator_script = req_dir / "validate_dependencies.py"
    
    if not validator_script.exists():
        # Look for validator in annotation_frontend directory
        annotation_validator = Path("annotation_frontend/validate_dependencies.py")
        if annotation_validator.exists():
            validator_script = annotation_validator
        else:
            print(f"⚠️ No validation script found for {req_file}")
            return True  # Don't fail if validator not available
    
    # Run the validation
    cmd = f"python {validator_script} --requirements {req_file} --strict"
    success, stdout, stderr = run_command(cmd)
    
    if not success:
        print(f"❌ Validation failed for {req_file}:")
        print(stdout)
        print(stderr)
        return False
    
    print(f"✅ {req_file} validation passed")
    return True


def main():
    """Main pre-commit hook function."""
    print("🚀 Running dependency validation pre-commit hook...")
    
    # Check if we're in a git repository
    if not Path(".git").exists():
        print("⚠️ Not in a git repository, skipping validation")
        return 0
    
    # Find staged requirements.txt files
    requirements_files = check_staged_requirements_files()
    
    if not requirements_files:
        print("✅ No requirements.txt files staged for commit")
        return 0
    
    print(f"📦 Found {len(requirements_files)} requirements file(s) to validate:")
    for req_file in requirements_files:
        print(f"  - {req_file}")
    
    # Validate each requirements file
    all_valid = True
    for req_file in requirements_files:
        if not validate_requirements_file(req_file):
            all_valid = False
    
    if not all_valid:
        print("\n❌ Dependency validation failed!")
        print("💡 To fix:")
        print("   1. Review the validation errors above")
        print("   2. Pin any unpinned dependencies")
        print("   3. Fix any security vulnerabilities")
        print("   4. Re-stage your changes and commit again")
        print("\n🚫 To bypass this hook (not recommended): git commit --no-verify")
        return 1
    
    print("\n✅ All dependency validations passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

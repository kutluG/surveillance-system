#!/usr/bin/env python3
"""
Dependency Validation Script

This script validates that all dependencies in requirements.txt are properly
pinned to specific versions to ensure reproducible builds.

Usage:
    python validate_dependencies.py
    python validate_dependencies.py --strict  # Fail on any issues
    python validate_dependencies.py --check-security  # Check for known vulnerabilities
"""

import re
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import json


class DependencyValidator:
    """Validates dependency pinning and security."""
    
    def __init__(self, requirements_file: str = "requirements.txt"):
        self.requirements_file = Path(requirements_file)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        
        # Critical packages that must be pinned
        self.critical_packages = {
            'fastapi', 'uvicorn', 'pydantic', 'confluent-kafka', 
            'python-jose', 'pyjwt', 'structlog', 'pytest'
        }
        
        # Packages allowed to have version ranges (typically for compatibility)
        self.range_allowed_packages = {
            'python-json-logger', 'prometheus_client'
        }
    
    def parse_requirement_line(self, line: str) -> Optional[Tuple[str, str, str]]:
        """
        Parse a requirement line into package name, operator, and version.
        
        Returns:
            Tuple of (package_name, operator, version) or None if not a requirement
        """
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            return None
        
        # Handle extras like package[extra]==version
        extras_pattern = r'^([a-zA-Z0-9_-]+)(?:\[[^\]]+\])?\s*([><=!~]+)\s*([0-9.]+.*)'
        match = re.match(extras_pattern, line)
        
        if match:
            package, operator, version = match.groups()
            return package.lower(), operator, version
        
        # Handle unpinned packages
        unpinned_pattern = r'^([a-zA-Z0-9_-]+)(?:\[[^\]]+\])?\s*$'
        match = re.match(unpinned_pattern, line)
        
        if match:
            package = match.group(1)
            return package.lower(), '', ''
        
        return None
    
    def validate_pinning(self) -> None:
        """Validate that critical packages are properly pinned."""
        if not self.requirements_file.exists():
            self.errors.append(f"Requirements file {self.requirements_file} not found")
            return
        
        with open(self.requirements_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        found_packages = set()
        
        for line_num, line in enumerate(lines, 1):
            parsed = self.parse_requirement_line(line)
            if not parsed:
                continue
            
            package, operator, version = parsed
            found_packages.add(package)
            
            # Check if package is unpinned
            if not operator or not version:
                if package in self.critical_packages:
                    self.errors.append(
                        f"Line {line_num}: Critical package '{package}' is not pinned to a specific version"
                    )
                else:
                    self.warnings.append(
                        f"Line {line_num}: Package '{package}' is not pinned to a specific version"
                    )
                continue
            
            # Check pinning strictness for critical packages
            if package in self.critical_packages:
                if operator != '==':
                    if package not in self.range_allowed_packages:
                        self.errors.append(
                            f"Line {line_num}: Critical package '{package}' should use exact pinning (==) not '{operator}'"
                        )
                else:
                    self.info.append(f"✓ {package} is properly pinned to {version}")
            
            # Check for version ranges on non-critical packages
            elif operator in ['>=', '~=', '>', '<', '<=', '!=']:
                if package not in self.range_allowed_packages:
                    self.warnings.append(
                        f"Line {line_num}: Package '{package}' uses version range '{operator}{version}'. Consider exact pinning for reproducibility."
                    )
        
        # Check for missing critical packages
        missing_critical = self.critical_packages - found_packages
        for package in missing_critical:
            self.warnings.append(f"Critical package '{package}' not found in requirements")
    
    def check_duplicate_packages(self) -> None:
        """Check for duplicate package entries."""
        if not self.requirements_file.exists():
            return
        
        with open(self.requirements_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        seen_packages = {}
        
        for line_num, line in enumerate(lines, 1):
            parsed = self.parse_requirement_line(line)
            if not parsed:
                continue
            
            package, operator, version = parsed
            
            if package in seen_packages:                self.errors.append(
                    f"Line {line_num}: Duplicate package '{package}' (also on line {seen_packages[package]})"
                )
            else:
                seen_packages[package] = line_num
    
    def check_security_vulnerabilities(self) -> None:
        """Check for known security vulnerabilities using pip-audit if available."""
        try:
            # First check if pip-audit is available in the current environment
            result = subprocess.run(
                [sys.executable, '-c', 'import pip_audit'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.warnings.append(
                    "pip-audit not available. Run 'pip install pip-audit' to check for security vulnerabilities"
                )
                return
            
            # Run pip-audit on requirements file
            result = subprocess.run(
                ['pip-audit', '-r', str(self.requirements_file), '--format', 'json'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                try:
                    audit_data = json.loads(result.stdout)
                    if isinstance(audit_data, list) and len(audit_data) == 0:
                        self.info.append("✓ No known security vulnerabilities found")
                    else:
                        for vuln in audit_data:
                            package = vuln.get('package', 'unknown')
                            version = vuln.get('installed_version', 'unknown')
                            vuln_id = vuln.get('id', 'unknown')
                            self.errors.append(
                                f"Security vulnerability {vuln_id} found in {package} {version}"
                            )
                except json.JSONDecodeError:
                    self.warnings.append("Could not parse pip-audit output")
            else:
                # If pip-audit fails, try alternative approach
                self.warnings.append(f"pip-audit returned non-zero exit code: {result.returncode}")
                if result.stderr:
                    self.warnings.append(f"pip-audit stderr: {result.stderr[:200]}...")
                
        except FileNotFoundError:
            self.warnings.append("pip-audit command not found in PATH")
        except Exception as e:
            self.warnings.append(f"Error running pip-audit: {str(e)}")
    
    
    def validate_version_format(self) -> None:
        """Validate that version strings follow semantic versioning."""
        if not self.requirements_file.exists():
            return
        
        # Semantic versioning pattern: major.minor.patch with optional pre-release/build
        semver_pattern = r'^\d+\.\d+\.\d+(?:[-.]?(?:a|b|rc|alpha|beta|dev)\d*)?(?:\+[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*)?$'
        
        with open(self.requirements_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            parsed = self.parse_requirement_line(line)
            if not parsed:
                continue
            
            package, operator, version = parsed
            
            if version and operator == '==':
                if not re.match(semver_pattern, version):
                    self.warnings.append(
                        f"Line {line_num}: Package '{package}' version '{version}' doesn't follow semantic versioning"
                    )
    
    def generate_lock_file(self) -> None:
        """Generate a requirements.lock file with all dependencies pinned."""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'freeze'],
                capture_output=True,
                text=True,
                check=True
            )
            
            lock_file = self.requirements_file.parent / 'requirements.lock'
            with open(lock_file, 'w', encoding='utf-8') as f:
                f.write(f"# Generated lock file - {self.requirements_file.name}\n")
                f.write(f"# Generated on: {subprocess.run(['date', '/t'], capture_output=True, text=True, shell=True).stdout.strip()}\n")
                f.write("# DO NOT EDIT - Generated automatically\n\n")
                f.write(result.stdout)
            
            self.info.append(f"✓ Generated {lock_file} with all dependencies pinned")
            
        except subprocess.CalledProcessError as e:
            self.warnings.append(f"Could not generate lock file: {e}")
    
    def run_validation(self, check_security: bool = False, generate_lock: bool = False) -> bool:
        """
        Run all validations.
        
        Args:
            check_security: Whether to check for security vulnerabilities
            generate_lock: Whether to generate a lock file
            
        Returns:
            True if validation passed, False if there were errors
        """
        print(f"🔍 Validating dependencies in {self.requirements_file}")
        print("=" * 60)
        
        self.validate_pinning()
        self.check_duplicate_packages()
        self.validate_version_format()
        
        if check_security:
            print("🔒 Checking for security vulnerabilities...")
            self.check_security_vulnerabilities()
        
        if generate_lock:
            print("🔒 Generating lock file...")
            self.generate_lock_file()
        
        # Report results
        if self.info:
            print("\n✅ INFO:")
            for msg in self.info:
                print(f"  {msg}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for msg in self.warnings:
                print(f"  {msg}")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for msg in self.errors:
                print(f"  {msg}")
            print(f"\n💥 Validation failed with {len(self.errors)} error(s)")
            return False
        
        print(f"\n✅ Validation passed! Found {len(self.warnings)} warning(s)")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate dependency pinning in requirements.txt"
    )
    parser.add_argument(
        "--requirements", "-r",
        default="requirements.txt",
        help="Path to requirements file (default: requirements.txt)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--check-security",
        action="store_true",
        help="Check for known security vulnerabilities"
    )
    parser.add_argument(
        "--generate-lock",
        action="store_true",
        help="Generate a requirements.lock file"
    )
    
    args = parser.parse_args()
    
    validator = DependencyValidator(args.requirements)
    success = validator.run_validation(
        check_security=args.check_security,
        generate_lock=args.generate_lock
    )
    
    # In strict mode, treat warnings as errors
    if args.strict and validator.warnings:
        print(f"\n💥 Strict mode: {len(validator.warnings)} warning(s) treated as errors")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Automated security audit for Python dependencies using pip-audit.

This script runs pip-audit to check for known vulnerabilities in installed packages
and fails the build if any vulnerabilities are found.

Usage:
    python scripts/audit_dependencies.py

Returns:
    Exit code 0: No vulnerabilities found
    Exit code 1: Vulnerabilities found or audit failed
"""

import subprocess
import sys
import os
from pathlib import Path


def main():
    """Run pip-audit and check for vulnerabilities."""
    print("🔍 Running security audit on Python dependencies...")
    
    try:
        # Run pip-audit with text output
        result = subprocess.run(
            ["pip-audit", "--output", "text", "--progress-spinner", "off"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Print the output
        if result.stdout:
            print("📋 Audit Results:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️  Audit Warnings/Errors:")
            print(result.stderr)
        
        # Check for vulnerabilities in the output
        if result.returncode != 0:
            print("❌ Security audit failed!")
            if "No known vulnerabilities found" in result.stdout:
                print("✅ No vulnerabilities found, but audit returned non-zero code")
                return 0
            else:
                print("🚨 Vulnerabilities detected or audit tool error occurred")
                return 1
        
        if "No known vulnerabilities found" in result.stdout:
            print("✅ Security audit passed - no vulnerabilities found!")
            return 0
        elif "VULNERABILITY" in result.stdout.upper() or "VULN" in result.stdout.upper():
            print("❌ Security vulnerabilities detected!")
            print("🔧 Please update the vulnerable packages or pin to secure versions")
            return 1
        else:
            print("✅ Security audit completed successfully!")
            return 0
            
    except subprocess.TimeoutExpired:
        print("❌ Security audit timed out after 5 minutes")
        return 1
    except FileNotFoundError:
        print("❌ pip-audit not found. Please install it with: pip install pip-audit>=2.6.0")
        return 1
    except Exception as e:
        print(f"❌ Error running security audit: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

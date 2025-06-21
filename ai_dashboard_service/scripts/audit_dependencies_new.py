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
        
        print("📄 Audit output:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  Audit stderr:")
            print(result.stderr)
        
        # Check for vulnerabilities in the output
        if "No known vulnerabilities found" in result.stdout:
            print("✅ No vulnerabilities found in dependencies!")
            return 0
        elif "VULNERABILITY" in result.stdout or result.returncode != 0:
            print("❌ Vulnerabilities found or audit failed!")
            print(f"Return code: {result.returncode}")
            return 1
        else:
            print("✅ Security audit completed successfully")
            return 0
            
    except subprocess.TimeoutExpired:
        print("❌ Audit timed out after 5 minutes")
        return 1
    except FileNotFoundError:
        print("❌ pip-audit not found. Please ensure it's installed:")
        print("pip install pip-audit>=2.9.0")
        return 1
    except Exception as e:
        print(f"❌ Error running audit: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

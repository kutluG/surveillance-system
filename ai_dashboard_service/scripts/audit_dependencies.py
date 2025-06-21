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
        # Run pip-audit with requirements file for faster scanning
        result = subprocess.run(
            ["pip-audit", "--requirement", "requirements.txt", "--output", "text", "--progress-spinner", "off"],
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout
        )
        
        # Print the output for debugging
        if result.stdout:
            print("📄 Audit output:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️  Audit stderr:")
            print(result.stderr)
        
        print(f"Exit code: {result.returncode}")
        
        # Check for vulnerabilities in the output
        if result.returncode == 0:
            if "No known vulnerabilities found" in result.stdout:
                print("✅ No vulnerabilities found in dependencies!")
                return 0
            else:
                print("✅ Security audit completed successfully")
                return 0
        else:
            print("❌ Security audit failed or vulnerabilities found!")
            return 1
            
    except subprocess.TimeoutExpired:
        print("❌ Audit timed out after 1 minute")
        print("💡 This may happen due to network issues. Try running manually:")
        print("pip-audit --requirement requirements.txt")
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

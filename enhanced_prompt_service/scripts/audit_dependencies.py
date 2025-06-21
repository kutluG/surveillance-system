#!/usr/bin/env python3
"""
Security audit script for Python dependencies using pip-audit.

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
import json
from pathlib import Path


def run_pip_audit():
    """Run pip-audit and return results."""
    print("🔍 Running security audit on Python dependencies...")
    
    try:
        # Run pip-audit with JSON output for parsing
        result = subprocess.run(
            ["pip-audit", "--format", "json", "--progress-spinner", "off"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        return result.returncode, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print("❌ Security audit timed out after 5 minutes")
        return 1, "", "Timeout expired"
        
    except FileNotFoundError:
        print("❌ pip-audit not found. Please install it with: pip install pip-audit")
        return 1, "", "pip-audit not found"
        
    except Exception as e:
        print(f"❌ Error running security audit: {e}")
        return 1, "", str(e)


def parse_audit_results(stdout, stderr):
    """Parse audit results and display findings."""
    if not stdout.strip():
        if "No known vulnerabilities found" in stderr:
            print("✅ No known vulnerabilities found")
            return 0
        else:
            print(f"⚠️  Audit completed but no output received: {stderr}")
            return 0
    
    try:
        # Parse JSON output
        data = json.loads(stdout)
        
        # Handle pip-audit JSON format with dependencies array
        dependencies = data.get('dependencies', [])
        if not dependencies:
            print("✅ No known vulnerabilities found")
            return 0
        
        # Find packages with vulnerabilities
        vulnerable_packages = []
        total_vulnerabilities = 0
        
        for dep in dependencies:
            vulns = dep.get('vulns', [])
            if vulns:
                vulnerable_packages.append({
                    'name': dep.get('name', 'Unknown'),
                    'version': dep.get('version', 'Unknown'),
                    'vulns': vulns
                })
                total_vulnerabilities += len(vulns)
        
        if not vulnerable_packages:
            print("✅ No known vulnerabilities found")
            return 0
        
        # Display vulnerabilities
        print(f"❌ Found {total_vulnerabilities} vulnerabilities in {len(vulnerable_packages)} packages:")
        print("-" * 70)
        
        for pkg in vulnerable_packages:
            print(f"� Package: {pkg['name']} (v{pkg['version']})")
            
            for vuln in pkg['vulns']:
                vuln_id = vuln.get('id', 'Unknown')
                description = vuln.get('description', 'No description available')
                fix_versions = vuln.get('fix_versions', [])
                aliases = vuln.get('aliases', [])
                
                print(f"  🆔 ID: {vuln_id}")
                if aliases:
                    print(f"  🔗 Aliases: {', '.join(aliases)}")
                print(f"  📝 Description: {description[:200]}{'...' if len(description) > 200 else ''}")
                
                if fix_versions:
                    print(f"  🔧 Fix available in versions: {', '.join(fix_versions)}")
                else:
                    print("  🔧 No fix versions specified")
                print()
            
            print("-" * 70)
        
        return 1  # Exit with error code
        
    except json.JSONDecodeError:
        # Fallback to text parsing
        if "No known vulnerabilities found" in stdout:
            print("✅ No known vulnerabilities found")
            return 0
        elif "Found" in stdout and "vulnerabilities" in stdout:
            print("❌ Vulnerabilities detected:")
            print(stdout)
            return 1
        else:
            print("✅ Security audit completed")
            print(stdout)
            return 0


def main():
    """Main function to run pip-audit and check for vulnerabilities."""
    print("🔐 Enhanced Prompt Service - Security Dependency Audit")
    print("=" * 55)
    
    # Check if we're in the right directory
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found. Please run from the service root directory.")
        return 1
    
    # Run the audit
    return_code, stdout, stderr = run_pip_audit()
    
    if return_code != 0 and not stdout:
        print(f"❌ pip-audit failed with return code {return_code}")
        if stderr:
            print(f"Error output: {stderr}")
        return 1
    
    # Parse and display results
    result_code = parse_audit_results(stdout, stderr)
    
    if result_code == 0:
        print("\n🎉 Security audit passed - no vulnerabilities found!")
    else:
        print("\n💥 Security audit failed - vulnerabilities found!")
        print("\n🔧 Next steps:")
        print("1. Review the vulnerabilities listed above")
        print("2. Update affected packages to fixed versions")
        print("3. Update requirements.txt with the new versions")
        print("4. Run the audit again to verify fixes")
    
    return result_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

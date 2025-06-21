#!/usr/bin/env python3
"""
MQTT Client Integration Test Runner

This script runs the MQTT client integration tests and provides a summary
of the test results. It can be used to validate MQTT client functionality
in CI/CD pipelines or during development.

Usage:
    python run_mqtt_tests.py [--verbose] [--coverage]
    
Options:
    --verbose    Show detailed test output
    --coverage   Generate test coverage report
"""
import sys
import os
import subprocess
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Run MQTT client integration tests")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Show verbose test output")
    parser.add_argument("--coverage", "-c", action="store_true",
                       help="Generate coverage report")
    parser.add_argument("--broker-check", "-b", action="store_true",
                       help="Check if mosquitto broker is available")
    
    args = parser.parse_args()
    
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    tests_dir = script_dir / "tests"
    
    # Change to the edge service directory
    os.chdir(script_dir)
    
    print("🧪 MQTT Client Integration Tests")
    print("=" * 40)
    
    if args.broker_check:
        print("🔍 Checking for MQTT broker availability...")
        check_mqtt_broker()
    
    # Prepare pytest command
    pytest_cmd = ["python", "-m", "pytest"]
    
    if args.verbose:
        pytest_cmd.extend(["-v", "--tb=short"])
    else:
        pytest_cmd.extend(["-q"])
    
    if args.coverage:
        pytest_cmd.extend([
            "--cov=mqtt_client",
            "--cov-report=term-missing",
            "--cov-report=html:coverage_html"
        ])
    
    # Add specific test file
    pytest_cmd.append("tests/test_mqtt_client.py")
    
    print(f"Running: {' '.join(pytest_cmd)}")
    print()
    
    try:
        # Run the tests
        result = subprocess.run(pytest_cmd, check=False)
        
        if result.returncode == 0:
            print("\n✅ All MQTT client tests passed!")
            if args.coverage:
                print("📊 Coverage report generated in coverage_html/")
        else:
            print(f"\n❌ Tests failed with exit code {result.returncode}")
            print("💡 Try running with --verbose for more details")
        
        return result.returncode
        
    except FileNotFoundError:
        print("❌ pytest not found. Install test dependencies:")
        print("   pip install -r requirements.txt")
        return 1
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 130


def check_mqtt_broker():
    """Check if mosquitto broker is available on the system."""
    print("Checking mosquitto installation...")
    
    try:
        result = subprocess.run(["mosquitto", "-h"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ mosquitto broker available")
        else:
            print("⚠️  mosquitto installed but may have issues")
    except FileNotFoundError:
        print("⚠️  mosquitto not found - will try Docker fallback")
    except subprocess.TimeoutExpired:
        print("⚠️  mosquitto check timed out")
    
    print("Checking Docker availability...")
    try:
        result = subprocess.run(["docker", "--version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Docker available for broker fallback")
            print(f"   {result.stdout.strip()}")
        else:
            print("❌ Docker not available")
    except FileNotFoundError:
        print("❌ Docker not found")
    except subprocess.TimeoutExpired:
        print("⚠️  Docker check timed out")
    
    print()


if __name__ == "__main__":
    sys.exit(main())

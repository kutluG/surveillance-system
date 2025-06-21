#!/usr/bin/env python3
"""
Test Runner for MQTT Client Integration Tests

This script runs the comprehensive MQTT client integration tests,
providing both quick validation and full integration test suites.

Usage:
    python run_mqtt_tests.py [--quick] [--integration] [--all]
    
Options:
    --quick       Run only basic functionality tests (fast)
    --integration Run full integration tests including reconnection
    --all         Run all tests (default)
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_pytest_command(args: list) -> int:
    """Run pytest with the given arguments."""
    cmd = ["python", "-m", "pytest"] + args
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd)

def main():
    parser = argparse.ArgumentParser(description="Run MQTT Client Integration Tests")
    parser.add_argument("--quick", action="store_true", 
                       help="Run only quick basic tests")
    parser.add_argument("--integration", action="store_true",
                       help="Run full integration tests")
    parser.add_argument("--all", action="store_true", default=True,
                       help="Run all tests (default)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Base pytest arguments
    pytest_args = [
        "tests/test_mqtt_client_integration.py",
        "--tb=short",
    ]
    
    if args.verbose:
        pytest_args.append("-v")
    
    # Add markers based on test selection
    if args.quick:
        pytest_args.extend(["-m", "not integration"])
        print("Running quick MQTT client tests...")
    elif args.integration:
        pytest_args.extend(["-m", "integration"])
        print("Running full integration tests (including reconnection)...")
    else:
        print("Running all MQTT client tests...")
    
    # Set environment for tests
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(project_root),
        "MQTT_BROKER": "localhost",
        "MQTT_PORT": "8883",
        "MQTT_PORT_INSECURE": "1883"
    })
    
    # Run the tests
    return run_pytest_command(pytest_args)

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Test runner script for annotation frontend service.

Usage:
    python run_tests.py                 # Run all tests
    python run_tests.py --unit          # Run only unit tests
    python run_tests.py --integration   # Run only integration tests
    python run_tests.py --kafka         # Run only Kafka tests
    python run_tests.py --coverage      # Run with coverage report
"""
import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle the result."""
    print(f"\n🔄 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
    else:
        print(f"❌ {description} - FAILED")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Run annotation frontend tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests") 
    parser.add_argument("--kafka", action="store_true", help="Run only Kafka tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    if args.verbose:
        cmd.append("-v")
    
    # Add test selection markers
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    elif args.kafka:
        cmd.extend(["-m", "kafka"])
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend([
            "--cov=.",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-exclude=tests/*"
        ])
    
    # Add test directory
    cmd.append("tests/")
    
    # Check if we're in the right directory
    if not Path("tests").exists():
        print("❌ Error: tests directory not found. Run this script from the annotation_frontend directory.")
        sys.exit(1)
    
    # Run the tests
    success = run_command(cmd, "Running annotation frontend tests")
    
    if success:
        print("\n🎉 All tests completed successfully!")
        if args.coverage:
            print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("\n💥 Some tests failed. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

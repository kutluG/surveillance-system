#!/usr/bin/env python3
"""
Test runner script for enhanced_prompt_service tests.
Provides coverage reporting and test execution options.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_tests(
    test_path: str = "tests/",
    coverage: bool = True,
    verbose: bool = True,
    fail_fast: bool = False,
    html_report: bool = False
):
    """
    Run tests with optional coverage reporting.
    
    Args:
        test_path: Path to tests directory or specific test file
        coverage: Enable coverage reporting
        verbose: Enable verbose output
        fail_fast: Stop on first failure
        html_report: Generate HTML coverage report
    """
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if fail_fast:
        cmd.append("-x")
    
    # Add coverage options
    if coverage:
        cmd.extend([
            "--cov=llm_client",
            "--cov=weaviate_client", 
            "--cov=conversation_manager",
            "--cov-report=term-missing"
        ])
        
        if html_report:
            cmd.append("--cov-report=html:htmlcov")
    
    # Add test path
    cmd.append(test_path)
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 50)
    
    # Execute tests
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def run_specific_module(module_name: str, **kwargs):
    """Run tests for a specific module."""
    test_file_map = {
        "llm": "tests/test_llm_client.py",
        "llm_client": "tests/test_llm_client.py",
        "weaviate": "tests/test_weaviate_client.py",
        "weaviate_client": "tests/test_weaviate_client.py", 
        "conversation": "tests/test_conversation_manager.py",
        "conversation_manager": "tests/test_conversation_manager.py",
        "clip_store": "tests/test_clip_store.py",
        "clip": "tests/test_clip_store.py",
        "api": "tests/test_api_endpoints.py",
        "endpoints": "tests/test_api_endpoints.py",
        "e2e": "tests/test_api_endpoints.py",
        "integration": "tests/test_clip_store.py"
    }
    
    test_path = test_file_map.get(module_name.lower())
    if not test_path:
        print(f"Unknown module: {module_name}")
        print(f"Available modules: {', '.join(test_file_map.keys())}")
        return 1
        
    if not os.path.exists(test_path):
        print(f"Test file not found: {test_path}")
        return 1
        
    print(f"Running tests for {module_name} module...")
    return run_tests(test_path, **kwargs)

def install_test_dependencies():
    """Install required test dependencies."""
    print("Installing test dependencies...")
    
    dependencies = [
        "pytest==7.4.4",
        "pytest-mock==3.12.0", 
        "pytest-asyncio==0.23.2",
        "pytest-cov==4.1.0",
        "httpx==0.27.2",
        "fakeredis==2.20.1"
    ]
    
    for dep in dependencies:
        try:
            subprocess.run(["pip", "install", dep], check=True)
            print(f"✓ Installed {dep}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {dep}: {e}")
            return False
    
    print("All test dependencies installed successfully!")
    return True

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Test runner for enhanced_prompt_service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                          # Run all tests with coverage
  python run_tests.py --no-coverage           # Run all tests without coverage  
  python run_tests.py --module llm            # Run only LLM client tests
  python run_tests.py --module conversation   # Run only conversation manager tests
  python run_tests.py --html                  # Generate HTML coverage report
  python run_tests.py --install-deps          # Install test dependencies
        """
    )
    
    parser.add_argument(
        "--module", "-m",
        help="Run tests for specific module (llm, weaviate, conversation)"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    parser.add_argument(
        "--html",
        action="store_true", 
        help="Generate HTML coverage report"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce output verbosity"
    )
    
    parser.add_argument(
        "--fail-fast", "-x",
        action="store_true",
        help="Stop on first test failure" 
    )
    
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install required test dependencies"
    )
    
    parser.add_argument(
        "test_path",
        nargs="?",
        default="tests/",
        help="Specific test file or directory to run"
    )
    
    args = parser.parse_args()
    
    # Handle dependency installation
    if args.install_deps:
        success = install_test_dependencies()
        return 0 if success else 1
    
    # Validate test environment
    if not os.path.exists("tests/"):
        print("Error: tests/ directory not found")
        print("Make sure you're running this from the enhanced_prompt_service directory")
        return 1
    
    # Run specific module tests
    if args.module:
        return run_specific_module(
            args.module,
            coverage=not args.no_coverage,
            verbose=not args.quiet,
            fail_fast=args.fail_fast,
            html_report=args.html
        )
    
    # Run all tests
    return run_tests(
        test_path=args.test_path,
        coverage=not args.no_coverage, 
        verbose=not args.quiet,
        fail_fast=args.fail_fast,
        html_report=args.html
    )

if __name__ == "__main__":
    sys.exit(main())

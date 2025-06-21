#!/usr/bin/env python3
"""
Test runner script for enhanced_prompt_service integration and E2E tests.
"""
import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle the result."""
    print(f"\n🧪 {description}")
    print("=" * 50)
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True,
            capture_output=False,
            text=True
        )
        print(f"✅ {description} passed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    """Run all tests including integration and E2E tests."""
    print("🚀 Enhanced Prompt Service - Integration & E2E Test Runner")
    print("=" * 60)
    
    # Change to the enhanced_prompt_service directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Ensure we're in the right directory
    if not Path("tests").exists():
        print("❌ Error: tests directory not found. Are you in the enhanced_prompt_service directory?")
        sys.exit(1)
    
    if not Path("main.py").exists():
        print("❌ Error: main.py not found. Are you in the enhanced_prompt_service directory?")
        sys.exit(1)
    
    tests_passed = 0
    tests_total = 0
    
    # Test commands to run
    test_commands = [
        (
            "python -m pytest tests/test_clip_store.py -v --disable-warnings",
            "ClipStore Integration Tests"
        ),
        (
            "python -m pytest tests/test_api_endpoints.py -v --disable-warnings", 
            "FastAPI E2E Tests"
        ),
        (
            "python -m pytest tests/test_conversation_manager.py -v --disable-warnings",
            "Conversation Manager Unit Tests"
        ),
        (
            "python -m pytest tests/test_llm_client.py -v --disable-warnings",
            "LLM Client Unit Tests"
        ),
        (
            "python -m pytest tests/test_weaviate_client.py -v --disable-warnings",
            "Weaviate Client Unit Tests"
        ),
        (
            "python -m pytest --maxfail=1 --disable-warnings -q",
            "Quick Test Run (Fail Fast)"
        ),
        (
            "python -m pytest tests/ --cov=. --cov-report=term-missing --disable-warnings",
            "Full Test Suite with Coverage"
        )
    ]
    
    # Check if pytest is installed
    try:
        subprocess.run(["python", "-m", "pytest", "--version"], 
                      check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("❌ Error: pytest is not installed. Please run: pip install pytest")
        sys.exit(1)
    
    print("📋 Running test suite...")
    
    for command, description in test_commands:
        tests_total += 1
        if run_command(command, description):
            tests_passed += 1
        else:
            # Continue running other tests even if one fails
            continue
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print(f"✅ Passed: {tests_passed}/{tests_total}")
    print(f"❌ Failed: {tests_total - tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("\n🎉 All tests passed! Your integration and E2E tests are working correctly.")
        return 0
    else:
        print(f"\n⚠️ {tests_total - tests_passed} test suite(s) failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

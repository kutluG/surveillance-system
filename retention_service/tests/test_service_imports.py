#!/usr/bin/env python3
"""
Test that all migrated services can import the new logging modules correctly.
"""

import subprocess
import sys
import os

def test_service_imports():
    """Test that all services can import the logging modules."""
    services = [
        'rag_service',
        'prompt_service', 
        'rulegen_service',
        'notifier',
        'rule_builder_service',
        'enhanced_prompt_service',
        'websocket_service',
        'vms_service',
        'training_service',
        'mqtt_kafka_bridge',
        'hard_example_collector',
        'annotation_frontend'
    ]
    
    print("🧪 Testing service imports for enterprise logging...")
    print("=" * 60)
    
    success_count = 0
    total_count = len(services)
    
    for service in services:
        try:
            print(f"Testing {service}...", end=" ")
            
            # Test imports from service directory
            test_script = f"""
import sys
import os
sys.path.insert(0, '.')
sys.path.insert(0, '{service}')
os.chdir('{service}')

try:
    from shared.logging_config import configure_logging, get_logger
    from shared.audit_middleware import add_audit_middleware
    print("✓ SUCCESS")
except ImportError as e:
    print(f"✗ IMPORT FAILED: {{e}}")
    sys.exit(1)
except Exception as e:
    print(f"✗ ERROR: {{e}}")
    sys.exit(1)
"""
            
            result = subprocess.run([
                sys.executable, '-c', test_script
            ], capture_output=True, text=True, cwd='.')
            
            if result.returncode == 0:
                print(result.stdout.strip())
                success_count += 1
            else:
                print(f"✗ FAILED")
                if result.stderr:
                    print(f"  Error: {result.stderr.strip()}")
                if result.stdout:
                    print(f"  Output: {result.stdout.strip()}")
                    
        except Exception as e:
            print(f"✗ EXCEPTION: {e}")
    
    print("=" * 60)
    print(f"📊 Results: {success_count}/{total_count} services passed import tests")
    
    if success_count == total_count:
        print("🎉 All services can successfully import the logging modules!")
        return True
    else:
        print(f"⚠️  {total_count - success_count} services failed import tests")
        return False

def test_service_startup():
    """Test that a sample service can start with the new logging."""
    print("\n🚀 Testing service startup with enterprise logging...")
    print("=" * 60)
    
    # Test the notifier service as it's simple
    test_script = """
import sys
import os
sys.path.insert(0, '.')
sys.path.insert(0, 'notifier')
os.chdir('notifier')

# Set environment variables for logging
os.environ['SERVICE_NAME'] = 'notifier'
os.environ['LOG_LEVEL'] = 'INFO'

try:
    from shared.logging_config import configure_logging
    from shared.audit_middleware import add_audit_middleware
    
    # Configure logging
    logger = configure_logging('notifier')
    
    # Test basic logging
    logger.info("Service startup test", extra={
        'action': 'startup_test',
        'test_phase': 'initialization'
    })
    
    print("✓ Service startup test successful!")
    
except Exception as e:
    print(f"✗ Service startup test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    
    try:
        result = subprocess.run([
            sys.executable, '-c', test_script
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            print("✓ Service startup test PASSED")
            if result.stdout:
                print("Sample log output:")
                for line in result.stdout.strip().split('\n'):
                    if line.strip() and '{' in line:  # JSON log line
                        print(f"  {line}")
            return True
        else:
            print("✗ Service startup test FAILED")
            if result.stderr:
                print(f"Error: {result.stderr}")
            if result.stdout:
                print(f"Output: {result.stdout}")
            return False
            
    except Exception as e:
        print(f"✗ Exception during startup test: {e}")
        return False

def main():
    """Run all tests."""
    print("🔍 Enterprise Logging Integration Test Suite")
    print("=" * 60)
    
    # Test 1: Import tests
    imports_passed = test_service_imports()
    
    # Test 2: Startup test
    startup_passed = test_service_startup()
    
    print("\n" + "=" * 60)
    print("📋 FINAL RESULTS:")
    print(f"  ✓ Import Tests: {'PASSED' if imports_passed else 'FAILED'}")
    print(f"  ✓ Startup Test: {'PASSED' if startup_passed else 'FAILED'}")
    
    if imports_passed and startup_passed:
        print("\n🎉 ALL TESTS PASSED! Enterprise logging is ready for production!")
        print("🚀 You can now start services with structured JSON logging and audit trails.")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

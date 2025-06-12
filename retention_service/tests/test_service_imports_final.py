#!/usr/bin/env python3
"""
Test script to validate that all migrated services can import the new logging infrastructure.
"""
import subprocess
import sys
import os
from pathlib import Path

def test_service_imports():
    """Test that all service requirements can be imported."""
    
    # Services that have been migrated to the new logging system
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
    
    print("Testing service imports for logging infrastructure...")
    print("=" * 60)
    
    success_count = 0
    total_count = len(services)
    
    for service in services:
        print(f"\nTesting {service}...")
        
        # Check if service directory exists
        service_path = Path(service)
        if not service_path.exists():
            print(f"  ❌ Service directory not found: {service}")
            continue
            
        # Check if main.py exists
        main_py = service_path / "main.py"
        if not main_py.exists():
            print(f"  ❌ main.py not found in {service}")
            continue
            
        # Test imports
        try:
            # Test basic logging imports
            test_script = f"""
import sys
import os
sys.path.insert(0, '.')
sys.path.insert(0, 'shared')

# Test logging imports
try:
    from shared.logging_config import configure_logging, get_logger, log_context
    print("✓ logging_config imports successful")
except ImportError as e:
    print(f"✗ logging_config import failed: {{e}}")
    sys.exit(1)

# Test middleware imports  
try:
    from shared.audit_middleware import add_audit_middleware
    print("✓ audit_middleware imports successful")
except ImportError as e:
    print(f"✗ audit_middleware import failed: {{e}}")
    sys.exit(1)

# Test service-specific requirements
try:
    import os
    os.chdir('{service}')
    with open('requirements.txt', 'r') as f:
        requirements = f.read()
        if 'python-json-logger' in requirements and 'PyJWT' in requirements:
            print("✓ requirements.txt updated with logging dependencies")
        else:
            print("✗ requirements.txt missing logging dependencies")
            sys.exit(1)
except Exception as e:
    print(f"✗ requirements.txt check failed: {{e}}")
    sys.exit(1)

print("✓ All imports successful for {service}")
"""
            
            result = subprocess.run([
                sys.executable, '-c', test_script
            ], capture_output=True, text=True, cwd='.')
            
            if result.returncode == 0:
                print(f"  ✅ {service} - All imports successful")
                print(f"     {result.stdout.strip()}")
                success_count += 1
            else:
                print(f"  ❌ {service} - Import failed:")
                print(f"     {result.stderr.strip()}")
                
        except Exception as e:
            print(f"  ❌ {service} - Error during test: {e}")
    
    print("\n" + "=" * 60)
    print(f"Import Test Results: {success_count}/{total_count} services passed")
    
    if success_count == total_count:
        print("🎉 All services successfully import the logging infrastructure!")
        return True
    else:
        print(f"⚠️  {total_count - success_count} services need attention")
        return False

def test_basic_functionality():
    """Test basic logging functionality."""
    print("\nTesting basic logging functionality...")
    print("=" * 60)
    
    try:
        # Set environment variables for testing
        os.environ['SERVICE_NAME'] = 'test_service'
        os.environ['LOG_LEVEL'] = 'INFO'
        
        # Import and test logging
        from shared.logging_config import configure_logging, get_logger, log_context
        from shared.audit_middleware import add_audit_middleware
        
        # Configure logging
        logger = configure_logging('test_service', 'INFO')
        
        # Test basic logging
        logger.info("Test log message", extra={'action': 'test_logging'})
        
        # Test context manager
        with log_context(user_id="test_user", action="test_context"):
            logger.info("Test context logging")
        
        print("✅ Basic logging functionality works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Basic logging test failed: {e}")
        return False

if __name__ == "__main__":
    print("Enterprise Logging Infrastructure Validation")
    print("=" * 60)
    
    # Test service imports
    imports_ok = test_service_imports()
    
    # Test basic functionality
    functionality_ok = test_basic_functionality()
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print(f"Service Imports: {'PASS' if imports_ok else 'FAIL'}")
    print(f"Basic Functionality: {'PASS' if functionality_ok else 'FAIL'}")
    
    if imports_ok and functionality_ok:
        print("\n🎉 Enterprise logging infrastructure is ready for production!")
        sys.exit(0)
    else:
        print("\n⚠️  Some issues found. Please review the output above.")
        sys.exit(1)

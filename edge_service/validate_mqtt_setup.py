#!/usr/bin/env python3
"""
MQTT Test Setup Validator

This script validates that the MQTT client integration test setup is correct
and all dependencies are available. Run this before executing the full test suite.
"""
import sys
import os
import subprocess
import importlib
from pathlib import Path


def check_python_version():
    """Check Python version compatibility."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} is too old (need 3.8+)")
        return False
    else:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True


def check_module_imports():
    """Check that required Python modules can be imported."""
    print("\n📦 Checking Python module imports...")
    
    required_modules = [
        ("pytest", "pytest"),
        ("paho.mqtt.client", "paho-mqtt"),
        ("json", "json (built-in)"),
        ("datetime", "datetime (built-in)"),
        ("threading", "threading (built-in)"),
        ("socket", "socket (built-in)"),
        ("subprocess", "subprocess (built-in)"),
        ("tempfile", "tempfile (built-in)"),
        ("unittest.mock", "unittest.mock (built-in)")
    ]
    
    all_good = True
    for module_name, package_name in required_modules:
        try:
            importlib.import_module(module_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - run: pip install {package_name}")
            all_good = False
    
    return all_good


def check_mqtt_client_module():
    """Check if the MQTT client module can be imported."""
    print("\n🔌 Checking MQTT client module...")
    
    # Add current directory to path
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    try:
        from mqtt_client import MQTTClient
        print("✅ mqtt_client.MQTTClient can be imported")
        
        # Try to create an instance (this will fail connection but should not crash)
        try:
            # Mock environment to avoid real connection
            test_env = {
                "MQTT_BROKER": "nonexistent.test.broker",
                "MQTT_PORT_INSECURE": "1883",
                "MQTT_TLS_CA": "/nonexistent/ca.crt",
                "MQTT_TLS_CERT": "/nonexistent/client.crt",
                "MQTT_TLS_KEY": "/nonexistent/client.key"
            }
            
            # Temporarily set environment
            old_env = {}
            for key, value in test_env.items():
                old_env[key] = os.environ.get(key)
                os.environ[key] = value
            
            try:
                client = MQTTClient(client_id="validation_test")
                print("❌ MQTTClient should have failed with nonexistent broker")
                return False
            except ConnectionError:
                print("✅ MQTTClient correctly rejects invalid broker")
                return True
            finally:
                # Restore environment
                for key, old_value in old_env.items():
                    if old_value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = old_value
                        
        except Exception as e:
            print(f"❌ MQTTClient validation failed: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Cannot import mqtt_client: {e}")
        print("   Make sure you're running this from the edge_service directory")
        return False


def check_mqtt_broker_availability():
    """Check if MQTT broker tools are available."""
    print("\n🏢 Checking MQTT broker availability...")
    
    mosquitto_available = False
    docker_available = False
    
    # Check mosquitto
    try:
        result = subprocess.run(["mosquitto", "-h"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ mosquitto broker available")
            mosquitto_available = True
        else:
            print("⚠️  mosquitto installed but may have issues")
    except FileNotFoundError:
        print("⚠️  mosquitto not found")
    except subprocess.TimeoutExpired:
        print("⚠️  mosquitto check timed out")
    
    # Check Docker
    try:
        result = subprocess.run(["docker", "--version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Docker available")
            docker_available = True
        else:
            print("❌ Docker not working")
    except FileNotFoundError:
        print("❌ Docker not found")
    except subprocess.TimeoutExpired:
        print("⚠️  Docker check timed out")
    
    if mosquitto_available or docker_available:
        print("✅ At least one broker option is available")
        return True
    else:
        print("❌ No broker options available")
        print("   Install mosquitto or Docker to run tests")
        return False


def check_test_files():
    """Check that test files exist and are readable."""
    print("\n📄 Checking test files...")
    
    current_dir = Path(__file__).parent
    test_files = [
        "tests/conftest.py",
        "tests/test_mqtt_client.py",
        "mqtt_client.py"
    ]
    
    all_exist = True
    for test_file in test_files:
        file_path = current_dir / test_file
        if file_path.exists() and file_path.is_file():
            print(f"✅ {test_file}")
        else:
            print(f"❌ {test_file} not found or not readable")
            all_exist = False
    
    return all_exist


def run_quick_test():
    """Run a quick pytest dry-run to check test discovery."""
    print("\n🧪 Running pytest test discovery...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_mqtt_client.py", 
            "--collect-only", "-q"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            test_count = len([line for line in lines if '::test_' in line])
            print(f"✅ Test discovery successful ({test_count} tests found)")
            return True
        else:
            print(f"❌ Test discovery failed:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("❌ pytest not found - install: pip install pytest")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️  Test discovery timed out")
        return False


def main():
    """Run all validation checks."""
    print("🔍 MQTT Test Setup Validation")
    print("=" * 40)
    
    checks = [
        ("Python Version", check_python_version),
        ("Module Imports", check_module_imports),
        ("MQTT Client Module", check_mqtt_client_module),
        ("MQTT Broker Tools", check_mqtt_broker_availability),
        ("Test Files", check_test_files),
        ("Test Discovery", run_quick_test)
    ]
    
    results = {}
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            print(f"❌ {check_name} check failed with exception: {e}")
            results[check_name] = False
    
    # Summary
    print("\n📊 Validation Summary")
    print("=" * 25)
    
    passed = sum(results.values())
    total = len(results)
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All validation checks passed!")
        print("You can now run the MQTT integration tests:")
        print("   python run_mqtt_tests.py")
        return 0
    else:
        print(f"\n⚠️  {total - passed} validation checks failed")
        print("Please fix the issues above before running tests")
        return 1


if __name__ == "__main__":
    sys.exit(main())

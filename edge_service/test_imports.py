#!/usr/bin/env python3
"""Test imports for edge service modules"""

import sys
import traceback

def test_import(module_name, import_statement):
    """Test a single import"""
    try:
        exec(import_statement)
        print(f"✓ {module_name} imported successfully")
        return True
    except Exception as e:
        print(f"✗ {module_name} import failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all import tests"""
    print("Testing edge service module imports...")
    print("=" * 50)
    
    tests = [
        ("Quantization module", "from tools.quantize_model import ModelQuantizer"),
        ("Monitoring module", "from monitoring import ResourceMonitor"),
        ("Inference module", "from inference import EdgeInference"),
    ]
    
    results = []
    for module_name, import_statement in tests:
        result = test_import(module_name, import_statement)
        results.append(result)
        print()
    
    print("=" * 50)
    if all(results):
        print("🎉 All modules imported successfully!")
        return 0
    else:
        print("❌ Some imports failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

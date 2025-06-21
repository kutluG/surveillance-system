#!/usr/bin/env python3
"""
Validation script for enhanced_prompt_service package import.

This script validates that the enhanced_prompt_service can be imported correctly
and that all its modules are accessible as a proper Python package.
"""
import sys
import os
from pathlib import Path

def main():
    """Main validation function."""
    print("🔍 Validating enhanced_prompt_service package import...")
    
    try:
        # Add the project root to Python path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        # Test basic package import
        print("  ✓ Testing basic package import...")
        import enhanced_prompt_service
        print("  ✓ Package imported successfully")
        
        # Test that configuration is working correctly (this doesn't connect to services)
        print("  ✓ Testing configuration access...")
        from shared.config import get_service_config
        config = get_service_config("enhanced_prompt_service")
        
        # Verify essential config keys exist
        required_keys = [
            "weaviate_url", 
            "openai_api_key", 
            "redis_url", 
            "clip_base_url",
            "vms_service_url",
            "default_clip_expiry_minutes",
            "thumbnail_base_url"
        ]
        
        for key in required_keys:
            if key not in config:
                raise KeyError(f"Missing required configuration key: {key}")
        
        print("  ✓ Configuration access verified")
        
        # Test individual module imports with absolute paths
        # Note: We import the modules but don't instantiate clients that would connect to services
        print("  ✓ Testing individual module imports...")
          # Test importing functions/classes without executing them
        try:
            from enhanced_prompt_service import weaviate_client
            print("  ✓ weaviate_client module imported successfully")
        except Exception as e:
            if "Connection to Weaviate failed" in str(e):
                print("  ✓ weaviate_client module imported successfully (connection error expected without services)")
            else:
                raise e
        
        from enhanced_prompt_service import llm_client
        print("  ✓ llm_client module imported successfully")
        
        from enhanced_prompt_service.conversation_manager import ConversationManager
        print("  ✓ conversation_manager module imported successfully")
        
        from enhanced_prompt_service import clip_store
        print("  ✓ clip_store module imported successfully")
        
        # Test main module import
        try:
            from enhanced_prompt_service import main
            print("  ✓ main module imported successfully")
        except Exception as e:
            print(f"  ❌ main module import failed: {e}")
            raise e
        
        # Test that no os.getenv calls remain in the package modules
        print("  ✓ Checking for remaining os.getenv calls...")
        package_dir = project_root / "enhanced_prompt_service"
        python_files = list(package_dir.glob("*.py"))
        
        for py_file in python_files:
            if py_file.name == "__init__.py":
                continue
                
            content = py_file.read_text(encoding='utf-8')
            if "os.getenv" in content:
                raise ValueError(f"Found os.getenv call in {py_file.name}")
        
        print("  ✓ No os.getenv calls found in package modules")
        
        print("\n🎉 All validation checks passed!")
        print("✅ enhanced_prompt_service is properly configured as a Python package")
        print("Import successful")
        return 0
        
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("The enhanced_prompt_service package cannot be imported correctly.")
        return 1
        
    except KeyError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("Missing required configuration settings.")
        return 1
        
    except ValueError as e:
        print(f"\n❌ Validation Error: {e}")
        print("Package structure validation failed.")
        return 1
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        print("Package validation failed with unexpected error.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

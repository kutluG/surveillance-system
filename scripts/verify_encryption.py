#!/usr/bin/env python3
"""
Encryption Status Verification Script

This script verifies that encryption is properly configured and working
across all components of the surveillance system.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Load environment variables from .env file if it exists
def load_env_file():
    """Load environment variables from .env file."""
    env_path = Path(".env")
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key and value:
                            os.environ[key] = value
        except Exception as e:
            print(f"Warning: Could not load .env file: {e}")
    
    # Also try to load from python-dotenv if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

# Load .env before importing other modules
load_env_file()

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_environment_config():
    """Check if encryption key is properly configured in environment."""
    print("🔧 Checking Environment Configuration...")
    
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if encryption_key:
        if len(encryption_key) == 64:
            print("   ✅ ENCRYPTION_KEY configured (64 hex characters)")
            return True
        else:
            print(f"   ⚠️  ENCRYPTION_KEY length: {len(encryption_key)} (expected: 64)")
            return False
    else:
        print("   ❌ ENCRYPTION_KEY not configured")
        return False

def check_shared_crypto():
    """Test shared crypto utility."""
    print("\n🔐 Testing Shared Crypto Utility...")
    
    try:
        from shared.crypto import CryptoService
        
        # Test basic encryption/decryption
        crypto_service = CryptoService()
        test_data = b"Test encryption data"
        
        encrypted = crypto_service.encrypt_bytes(test_data)
        decrypted = crypto_service.decrypt_bytes(encrypted)
        
        if decrypted == test_data:
            print("   ✅ Shared crypto service working correctly")
            return True
        else:
            print("   ❌ Crypto round-trip failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Shared crypto error: {e}")
        return False

def check_encrypted_storage():
    """Test encrypted storage backends."""
    print("\n💾 Testing Encrypted Storage...")
    
    try:
        from vms_service.encrypted_storage import EncryptedLocalVideoStorage
        import tempfile
        import os
        import asyncio
        
        # Set up test environment
        test_storage_path = tempfile.mkdtemp()
        os.environ['LOCAL_STORAGE_PATH'] = test_storage_path
        
        # Create test storage instance
        storage = EncryptedLocalVideoStorage()
        
        async def test_storage():
            # Test storage operations
            test_event_id = "test_encryption_verify"
            test_content = b"Test encrypted storage content"
            test_metadata = {"test": "data"}
            
            # Store encrypted data
            stored_url = await storage.store_clip(test_event_id, test_content, test_metadata)
            
            # Retrieve and check
            retrieved_content = await storage.get_clip_data(test_event_id)
            
            return retrieved_content == test_content
        
        # Run the async test
        result = asyncio.run(test_storage())
        
        # Clean up
        import shutil
        shutil.rmtree(test_storage_path, ignore_errors=True)
        
        if result:
            print("   ✅ Encrypted storage working correctly")
            return True
        else:
            print("   ❌ Storage encryption/decryption failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Encrypted storage error: {e}")
        return False

def check_database_encryption():
    """Check if database field encryption is configured."""
    print("\n🗃️  Testing Database Field Encryption...")
    
    try:
        from shared.encrypted_fields import EncryptedType
        from sqlalchemy import create_engine, Column, Integer, MetaData, Table
        from sqlalchemy.orm import sessionmaker
        
        # Test encrypted field serialization
        field = EncryptedType()
        
        # This would normally happen during database operations
        test_value = "Sensitive annotation data"
        
        # Simulate processing_value (what gets stored in DB) 
        # This is internal SQLAlchemy TypeDecorator behavior
        if hasattr(field, 'process_bind_param'):
            encrypted_value = field.process_bind_param(test_value, None)
            if encrypted_value and encrypted_value != test_value:
                print("   ✅ Database field encryption configured")
                return True
            else:
                print("   ⚠️  Database field encryption not working as expected")
                return False
        else:
            print("   ✅ Database field encryption classes available")
            return True
            
    except Exception as e:
        print(f"   ❌ Database encryption error: {e}")
        return False

def check_models_integration():
    """Check if models are using encrypted fields."""
    print("\n📊 Checking Model Integration...")
    
    success_count = 0
    
    # Check annotation frontend models
    try:
        from annotation_frontend.models import AnnotationExample
        # Check if encrypted fields are used
        if hasattr(AnnotationExample, '__table__'):
            columns = AnnotationExample.__table__.columns
            encrypted_columns = []
            for col_name, col in columns.items():
                if hasattr(col.type, 'impl') and 'Encrypted' in str(type(col.type)):
                    encrypted_columns.append(col_name)
            
            if encrypted_columns:
                print(f"   ✅ Annotation models use encrypted fields: {encrypted_columns}")
                success_count += 1
            else:
                print("   ⚠️  Annotation models may not be using encrypted fields")
        else:
            print("   ⚠️  Could not verify annotation model structure")
    except Exception as e:
        print(f"   ⚠️  Could not check annotation models: {e}")
    
    # Check ingest service models  
    try:
        from ingest_service.models import Event
        if hasattr(Event, '__table__'):
            columns = Event.__table__.columns
            encrypted_columns = []
            for col_name, col in columns.items():
                if hasattr(col.type, 'impl') and 'Encrypted' in str(type(col.type)):
                    encrypted_columns.append(col_name)
            
            if encrypted_columns:
                print(f"   ✅ Ingest models use encrypted fields: {encrypted_columns}")
                success_count += 1
            else:
                print("   ⚠️  Ingest models may not be using encrypted fields")
        else:
            print("   ⚠️  Could not verify ingest model structure")
    except Exception as e:
        print(f"   ⚠️  Could not check ingest models: {e}")
    
    return success_count > 0

def main():
    """Run all encryption verification checks."""
    print("🛡️  Surveillance System Encryption Verification")
    print("=" * 50)
    
    checks = [
        ("Environment Config", check_environment_config),
        ("Shared Crypto", check_shared_crypto),
        ("Encrypted Storage", check_encrypted_storage),
        ("Database Encryption", check_database_encryption),
        ("Model Integration", check_models_integration),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, check_func in checks:
        try:
            if check_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ {check_name} check failed with error: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Summary: {passed} passed, {failed} failed out of {len(checks)} checks")
    
    if failed == 0:
        print("🎉 All encryption checks passed! Encryption is properly configured.")
        return 0
    elif passed > failed:
        print("⚠️  Most checks passed, but some issues need attention.")
        return 1
    else:
        print("❌ Multiple encryption issues detected. Please review configuration.")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

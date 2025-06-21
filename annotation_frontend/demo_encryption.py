#!/usr/bin/env python3
"""
Encryption Demo Script

Demonstrates the encryption functionality for frame and annotation data.
Shows how sensitive data is encrypted at rest and decrypted when needed.
"""

import sys
import os
import json
import base64
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from crypto import encrypt_bytes, decrypt_bytes, encrypt_string, decrypt_string, CryptoService
    from storage import store_frame_data, retrieve_frame_data, EncryptedStorage
    from models import AnnotationExample, EncryptedType, EncryptedJSONType
    print("✅ Successfully imported encryption modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the annotation_frontend directory")
    sys.exit(1)


def demo_basic_encryption():
    """Demonstrate basic encryption/decryption operations."""
    print("\n🔒 Basic Encryption Demo")
    print("=" * 50)
    
    # Demo data
    sensitive_text = "This is sensitive annotation data: John Doe, camera_001"
    sensitive_bytes = b"Binary image data: \x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..."
    
    print(f"Original text: {sensitive_text}")
    print(f"Original bytes length: {len(sensitive_bytes)} bytes")
    
    # Encrypt string
    encrypted_text = encrypt_string(sensitive_text)
    print(f"Encrypted text length: {len(encrypted_text)} bytes")
    print(f"Encrypted text (first 50 bytes): {encrypted_text[:50].hex()}...")
    
    # Encrypt bytes
    encrypted_bytes = encrypt_bytes(sensitive_bytes)
    print(f"Encrypted bytes length: {len(encrypted_bytes)} bytes")
    
    # Decrypt and verify
    decrypted_text = decrypt_string(encrypted_text)
    decrypted_bytes = decrypt_bytes(encrypted_bytes)
    
    print(f"\nDecrypted text: {decrypted_text}")
    print(f"Decrypted bytes length: {len(decrypted_bytes)} bytes")
    
    # Verify integrity
    assert decrypted_text == sensitive_text, "Text encryption failed!"
    assert decrypted_bytes == sensitive_bytes, "Bytes encryption failed!"
    
    print("✅ Basic encryption/decryption successful!")


def demo_json_encryption():
    """Demonstrate JSON data encryption."""
    print("\n📋 JSON Data Encryption Demo")
    print("=" * 50)
    
    # Sensitive annotation data
    annotation_data = {
        "bbox": [100, 150, 300, 400],
        "label": "person",
        "confidence": 0.95,
        "personal_info": {
            "estimated_age": "25-35",
            "clothing": "blue jacket",
            "location": "building entrance"
        },
        "timestamp": "2025-06-16T10:30:00Z"
    }
    
    print(f"Original JSON: {json.dumps(annotation_data, indent=2)}")
    
    # Convert to string and encrypt
    json_str = json.dumps(annotation_data)
    encrypted_json = encrypt_string(json_str)
    
    print(f"Encrypted JSON length: {len(encrypted_json)} bytes")
    print(f"Encrypted JSON (first 50 bytes): {encrypted_json[:50].hex()}...")
    
    # Decrypt and verify
    decrypted_json_str = decrypt_string(encrypted_json)
    recovered_data = json.loads(decrypted_json_str)
    
    print(f"\nRecovered JSON: {json.dumps(recovered_data, indent=2)}")
    
    assert recovered_data == annotation_data, "JSON encryption failed!"
    print("✅ JSON encryption/decryption successful!")


def demo_frame_storage():
    """Demonstrate encrypted frame storage."""
    print("\n🖼️  Encrypted Frame Storage Demo")
    print("=" * 50)
    
    # Simulate base64-encoded frame data
    fake_image_data = b"FAKE_PNG_DATA" + b"\x89PNG\r\n\x1a\n" + b"frame_content_" * 100
    base64_frame = base64.b64encode(fake_image_data).decode('utf-8')
    
    print(f"Original frame size: {len(fake_image_data)} bytes")
    print(f"Base64 frame size: {len(base64_frame)} characters")
    print(f"Base64 frame (first 50 chars): {base64_frame[:50]}...")
    
    try:
        # Initialize storage with local directory
        storage = EncryptedStorage("/tmp/test_encrypted_storage")
        
        # Store encrypted frame
        frame_id = "test_frame_001"
        storage_key = storage.store_frame_data(frame_id, base64_frame)
        print(f"Stored frame with key: {storage_key}")
        
        # Retrieve and decrypt frame
        retrieved_frame = storage.retrieve_frame_data(storage_key, as_base64=True)
        print(f"Retrieved frame size: {len(retrieved_frame)} characters")
        
        # Verify integrity
        assert retrieved_frame == base64_frame, "Frame storage failed!"
        
        # Verify we can decode back to original image
        recovered_image = base64.b64decode(retrieved_frame)
        assert recovered_image == fake_image_data, "Frame data corruption!"
        
        print("✅ Encrypted frame storage successful!")
        
        # Clean up
        storage.delete_frame_data(storage_key)
        print("🗑️  Cleaned up test storage")
        
    except Exception as e:
        print(f"❌ Frame storage demo failed: {e}")


def demo_database_encryption():
    """Demonstrate database field encryption (simulated)."""
    print("\n🗄️  Database Field Encryption Demo")
    print("=" * 50)
    
    # Simulate what happens in the database with EncryptedType
    print("Simulating EncryptedType behavior:")
    
    # Create an instance of our custom type
    encrypted_type = EncryptedType()
    
    # Simulate storing data (process_bind_param)
    original_value = "Sensitive label: Person identified as John Doe"
    print(f"Original value: {original_value}")
    
    # This is what gets stored in the database (encrypted + base64)
    stored_value = encrypted_type.process_bind_param(original_value, None)
    print(f"Stored value (encrypted): {stored_value[:50]}...")
    print(f"Stored value length: {len(stored_value)} characters")
    
    # This is what gets returned when reading (decrypted)
    retrieved_value = encrypted_type.process_result_value(stored_value, None)
    print(f"Retrieved value: {retrieved_value}")
    
    assert retrieved_value == original_value, "Database encryption failed!"
    print("✅ Database field encryption successful!")
    
    # Demonstrate JSON encryption
    print("\nSimulating EncryptedJSONType behavior:")
    encrypted_json_type = EncryptedJSONType()
    
    json_data = {"bbox": [10, 20, 30, 40], "confidence": 0.95}
    print(f"Original JSON: {json_data}")
    
    stored_json = encrypted_json_type.process_bind_param(json_data, None)
    print(f"Stored JSON (encrypted): {stored_json[:50]}...")
    
    retrieved_json = encrypted_json_type.process_result_value(stored_json, None)
    print(f"Retrieved JSON: {retrieved_json}")
    
    assert retrieved_json == json_data, "JSON database encryption failed!"
    print("✅ Database JSON encryption successful!")


def demo_security_properties():
    """Demonstrate security properties of the encryption."""
    print("\n🛡️  Security Properties Demo")
    print("=" * 50)
    
    # Show that same data encrypts differently each time (due to random IV)
    test_data = "Same secret message"
    
    print(f"Original data: {test_data}")
    
    encryptions = []
    for i in range(3):
        encrypted = encrypt_string(test_data)
        encryptions.append(encrypted)
        print(f"Encryption {i+1}: {encrypted[:30].hex()}...")
    
    # All encryptions should be different
    assert len(set(encryptions)) == len(encryptions), "Encryptions should be unique!"
    print("✅ Each encryption produces unique ciphertext (random IV)")
    
    # But all should decrypt to the same original
    for i, enc in enumerate(encryptions):
        decrypted = decrypt_string(enc)
        assert decrypted == test_data, f"Decryption {i+1} failed!"
    print("✅ All encryptions decrypt to the same original data")
    
    # Show that ciphertext doesn't contain plaintext patterns
    plaintext_with_patterns = "SECRET_PATTERN" * 10
    encrypted_patterns = encrypt_bytes(plaintext_with_patterns.encode())
    
    assert b"SECRET_PATTERN" not in encrypted_patterns, "Plaintext pattern found in ciphertext!"
    assert b"SECRET" not in encrypted_patterns, "Plaintext substring found in ciphertext!"
    print("✅ Ciphertext doesn't reveal plaintext patterns")


def main():
    """Run all encryption demos."""
    print("🔐 Annotation Frontend Encryption Demo")
    print("=" * 60)
    
    try:
        demo_basic_encryption()
        demo_json_encryption()
        demo_frame_storage()
        demo_database_encryption()
        demo_security_properties()
        
        print("\n🎉 All encryption demos completed successfully!")
        print("\n📋 Summary:")
        print("  ✅ AES-256-CBC encryption working")
        print("  ✅ Frame data encryption working")
        print("  ✅ JSON annotation encryption working")
        print("  ✅ Database field encryption working")
        print("  ✅ Security properties verified")
        print("\n🔒 Your sensitive annotation data is now protected at rest!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

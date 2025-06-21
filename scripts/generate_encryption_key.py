#!/usr/bin/env python3
"""
Encryption Key Generator

Generates a cryptographically secure 32-byte (256-bit) key 
for AES-256-CBC encryption used by the surveillance system.
"""

import secrets
import sys

def generate_encryption_key():
    """Generate a secure 32-byte encryption key as hex string."""
    return secrets.token_hex(32)

def main():
    """Generate and display encryption key with instructions."""
    print("🔐 Surveillance System Encryption Key Generator")
    print("=" * 50)
    
    # Generate the key
    key = generate_encryption_key()
    
    print("\n✅ Generated secure 32-byte encryption key:")
    print(f"\nENCRYPTION_KEY={key}")
    
    print("\n📋 Next Steps:")
    print("1. Copy the key above")
    print("2. Add it to your .env file:")
    print("   echo 'ENCRYPTION_KEY=" + key + "' >> .env")
    print("3. Keep the key secure and backed up")
    print("4. Never commit the key to version control")
    
    print("\n⚠️  Security Notes:")
    print("• This key encrypts ALL sensitive data in your system")
    print("• Loss of this key means loss of access to encrypted data")
    print("• Generate different keys for development/staging/production")
    print("• Store production keys in secure key management systems")
    
    return key

if __name__ == "__main__":
    main()

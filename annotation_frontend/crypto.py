"""
AES Encryption Utility for Frame and Annotation Data

Provides secure AES-256-CBC encryption for sensitive data at rest including:
- Base64 encoded frame images
- Sensitive JSON data (bounding boxes, labels, annotations)
- Other personally identifiable information

Security Features:
- AES-256-CBC encryption with random IV per operation
- PKCS7 padding for proper block alignment
- Cryptographically secure random IV generation
- Key validation and error handling
"""

import os
import logging
from typing import Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.exceptions import InvalidSignature

from config import settings

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Custom exception for encryption/decryption errors."""
    pass


class CryptoService:
    """Service for encrypting and decrypting sensitive data."""
    
    def __init__(self):
        """Initialize the crypto service with the configured encryption key."""
        self._validate_key()
        self._key = bytes.fromhex(settings.ENCRYPTION_KEY)
    
    def _validate_key(self):
        """Validate the encryption key format and length."""
        if not settings.ENCRYPTION_KEY:
            raise EncryptionError("ENCRYPTION_KEY not configured")
        
        try:
            key_bytes = bytes.fromhex(settings.ENCRYPTION_KEY)
            if len(key_bytes) != 32:  # 256 bits
                raise EncryptionError(f"Invalid key length: {len(key_bytes)} bytes. Expected 32 bytes for AES-256")
        except ValueError as e:
            raise EncryptionError(f"Invalid hex key format: {e}")
    
    def encrypt_bytes(self, data: bytes) -> bytes:
        """
        Encrypt bytes using AES-256-CBC.
        
        Args:
            data: Raw bytes to encrypt
            
        Returns:
            Encrypted bytes with IV prepended (IV + encrypted_data)
            
        Raises:
            EncryptionError: If encryption fails
        """
        if not isinstance(data, bytes):
            raise EncryptionError("Data must be bytes")
        
        if len(data) == 0:
            logger.warning("Encrypting empty data")
            return b""
        
        try:
            # Generate a random 16-byte IV for CBC mode
            iv = os.urandom(16)
            
            # Create cipher with AES-256-CBC
            cipher = Cipher(algorithms.AES(self._key), modes.CBC(iv))
            encryptor = cipher.encryptor()
            
            # Apply PKCS7 padding
            padder = padding.PKCS7(128).padder()  # 128 bits = 16 bytes
            padded_data = padder.update(data)
            padded_data += padder.finalize()
            
            # Encrypt the padded data
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Return IV + encrypted_data
            result = iv + encrypted_data
            
            logger.debug(f"Encrypted {len(data)} bytes to {len(result)} bytes")
            return result
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt bytes using AES-256-CBC.
        
        Args:
            encrypted_data: Encrypted bytes with IV prepended
            
        Returns:
            Decrypted raw bytes
            
        Raises:
            EncryptionError: If decryption fails
        """
        if not isinstance(encrypted_data, bytes):
            raise EncryptionError("Encrypted data must be bytes")
        
        if len(encrypted_data) == 0:
            logger.warning("Decrypting empty data")
            return b""
        
        if len(encrypted_data) < 16:
            raise EncryptionError("Invalid encrypted data: too short for IV")
        
        try:
            # Extract IV and encrypted content
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            
            if len(ciphertext) == 0:
                raise EncryptionError("No encrypted content after IV")
            
            # Create cipher with AES-256-CBC
            cipher = Cipher(algorithms.AES(self._key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            
            # Decrypt the data
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove PKCS7 padding
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data)
            data += unpadder.finalize()
            
            logger.debug(f"Decrypted {len(encrypted_data)} bytes to {len(data)} bytes")
            return data
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Decryption failed: {e}")
    
    def encrypt_string(self, text: str) -> bytes:
        """
        Encrypt a string to encrypted bytes.
        
        Args:
            text: String to encrypt
            
        Returns:
            Encrypted bytes
        """
        if not isinstance(text, str):
            raise EncryptionError("Text must be string")
        
        return self.encrypt_bytes(text.encode('utf-8'))
    
    def decrypt_string(self, encrypted_data: bytes) -> str:
        """
        Decrypt bytes to a string.
        
        Args:
            encrypted_data: Encrypted bytes
            
        Returns:
            Decrypted string
        """
        decrypted_bytes = self.decrypt_bytes(encrypted_data)
        try:
            return decrypted_bytes.decode('utf-8')
        except UnicodeDecodeError as e:
            raise EncryptionError(f"Failed to decode decrypted data as UTF-8: {e}")


# Global crypto service instance
crypto_service = CryptoService()


def encrypt_bytes(data: bytes) -> bytes:
    """
    Convenience function to encrypt bytes.
    
    Args:
        data: Raw bytes to encrypt
        
    Returns:
        Encrypted bytes with IV prepended
    """
    return crypto_service.encrypt_bytes(data)


def decrypt_bytes(encrypted_data: bytes) -> bytes:
    """
    Convenience function to decrypt bytes.
    
    Args:
        encrypted_data: Encrypted bytes with IV prepended
        
    Returns:
        Decrypted raw bytes
    """
    return crypto_service.decrypt_bytes(encrypted_data)


def encrypt_string(text: str) -> bytes:
    """
    Convenience function to encrypt a string.
    
    Args:
        text: String to encrypt
        
    Returns:
        Encrypted bytes
    """
    return crypto_service.encrypt_string(text)


def decrypt_string(encrypted_data: bytes) -> str:
    """
    Convenience function to decrypt to string.
    
    Args:
        encrypted_data: Encrypted bytes
        
    Returns:
        Decrypted string
    """
    return crypto_service.decrypt_string(encrypted_data)

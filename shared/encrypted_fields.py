"""
SQLAlchemy TypeDecorators for encrypted database fields

This module provides reusable TypeDecorator classes that can be used
across different services to encrypt sensitive data at the database level.
These decorators provide transparent encryption/decryption of data when
stored in or retrieved from the database.

Features:
- EncryptedType: For encrypting string/text fields
- EncryptedJSONType: For encrypting JSON data
- EncryptedBinaryType: For encrypting binary data (images, files)
- Graceful fallback when encryption fails
- Base64 encoding for safe storage in text columns
"""

import base64
import json
import logging
from typing import Any, Optional

from sqlalchemy import TypeDecorator, Text, LargeBinary
from sqlalchemy.dialects import postgresql

from shared.crypto import encrypt_bytes, decrypt_bytes, encrypt_string, decrypt_string, EncryptionError

logger = logging.getLogger(__name__)


class EncryptedType(TypeDecorator):
    """
    SQLAlchemy TypeDecorator for transparent string field encryption.
    
    Encrypts string data before storing and decrypts when retrieving.
    Stores encrypted data as base64-encoded strings in TEXT columns.
    """
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt value before storing in database."""
        if value is None:
            return None
        
        if not isinstance(value, str):
            # Convert to string if not already
            value = str(value)
        
        try:
            # Encrypt the string value
            encrypted_bytes = encrypt_string(value)
            # Convert to base64 for storage in TEXT column
            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except EncryptionError as e:
            logger.error(f"Failed to encrypt field value: {e}")
            # In production, you might want to raise this error
            # For now, store as plaintext with a warning
            logger.warning("Storing value as plaintext due to encryption failure")
            return value
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Decrypt value after retrieving from database."""
        if value is None:
            return None
        
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(value)
            # Decrypt the string value
            return decrypt_string(encrypted_bytes)
        except (EncryptionError, ValueError) as e:
            logger.error(f"Failed to decrypt field value: {e}")
            # If decryption fails, return the original value
            # This handles the case where data was stored unencrypted
            logger.warning("Returning value as plaintext due to decryption failure")
            return value


class EncryptedJSONType(TypeDecorator):
    """
    SQLAlchemy TypeDecorator for transparent JSON field encryption.
    
    Encrypts JSON data before storing and decrypts when retrieving.
    Handles both dict objects and JSON strings.
    """
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        """Encrypt JSON value before storing in database."""
        if value is None:
            return None
        
        try:
            # Convert to JSON string if needed
            if isinstance(value, str):
                # Validate it's valid JSON
                json.loads(value)
                json_str = value
            else:
                json_str = json.dumps(value)
            
            # Encrypt the JSON string
            encrypted_bytes = encrypt_string(json_str)
            # Convert to base64 for storage
            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except (EncryptionError, TypeError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to encrypt JSON field: {e}")
            # Store as plaintext JSON with warning
            logger.warning("Storing JSON as plaintext due to encryption failure")
            return json.dumps(value) if not isinstance(value, str) else value
    
    def process_result_value(self, value: Optional[str], dialect) -> Any:
        """Decrypt JSON value after retrieving from database."""
        if value is None:
            return None
        
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(value)
            # Decrypt to get JSON string
            json_str = decrypt_string(encrypted_bytes)
            # Parse JSON
            return json.loads(json_str)
        except (EncryptionError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to decrypt JSON field: {e}")
            # Try to parse as plaintext JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning("Returning raw value due to JSON parse failure")
                return value


class EncryptedBinaryType(TypeDecorator):
    """
    SQLAlchemy TypeDecorator for transparent binary field encryption.
    
    Encrypts binary data (like images, files) before storing and 
    decrypts when retrieving. Uses LargeBinary column type for 
    efficient binary storage.
    """
    
    impl = LargeBinary
    cache_ok = True
    
    def process_bind_param(self, value: Optional[bytes], dialect) -> Optional[bytes]:
        """Encrypt binary value before storing in database."""
        if value is None:
            return None
        
        if not isinstance(value, bytes):
            logger.warning(f"Converting {type(value)} to bytes for encryption")
            if isinstance(value, str):
                value = value.encode('utf-8')
            else:
                raise ValueError(f"Cannot convert {type(value)} to bytes")
        
        try:
            # Encrypt the binary data
            return encrypt_bytes(value)
        except EncryptionError as e:
            logger.error(f"Failed to encrypt binary field: {e}")
            # Store as plaintext with warning
            logger.warning("Storing binary data unencrypted due to encryption failure")
            return value
    
    def process_result_value(self, value: Optional[bytes], dialect) -> Optional[bytes]:
        """Decrypt binary value after retrieving from database."""
        if value is None:
            return None
        
        try:
            # Decrypt the binary data
            return decrypt_bytes(value)
        except EncryptionError as e:
            logger.error(f"Failed to decrypt binary field: {e}")
            # Return original data as fallback
            logger.warning("Returning unencrypted binary data due to decryption failure")
            return value


class EncryptedBase64Type(TypeDecorator):
    """
    SQLAlchemy TypeDecorator for encrypting base64-encoded data.
    
    This is specifically useful for frame data and other base64-encoded
    content that needs to be encrypted at rest. The data is expected
    to be base64 strings and is stored as encrypted text.
    """
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt base64 string before storing in database."""
        if value is None:
            return None
        
        if not isinstance(value, str):
            logger.warning(f"Converting {type(value)} to string for base64 encryption")
            value = str(value)
        
        try:
            # Validate it's base64 (this will raise an exception if invalid)
            base64.b64decode(value, validate=True)
            
            # Encrypt the base64 string
            encrypted_bytes = encrypt_string(value)
            # Convert to base64 for storage (base64 of encrypted base64)
            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except (EncryptionError, ValueError) as e:
            logger.error(f"Failed to encrypt base64 field: {e}")
            # Store as plaintext with warning
            logger.warning("Storing base64 data as plaintext due to encryption failure")
            return value
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Decrypt base64 string after retrieving from database."""
        if value is None:
            return None
        
        try:
            # Decode from base64 (encrypted data)
            encrypted_bytes = base64.b64decode(value)
            # Decrypt to get original base64 string
            decrypted_base64 = decrypt_string(encrypted_bytes)
            
            # Validate the decrypted result is still valid base64
            base64.b64decode(decrypted_base64, validate=True)
            
            return decrypted_base64
        except (EncryptionError, ValueError) as e:
            logger.error(f"Failed to decrypt base64 field: {e}")
            # Try to validate as direct base64
            try:
                base64.b64decode(value, validate=True)
                logger.warning("Returning unencrypted base64 data due to decryption failure")
                return value
            except ValueError:
                logger.error("Value is neither encrypted nor valid base64")
                return value


# PostgreSQL-specific variants that use more efficient column types
class EncryptedJSONBType(TypeDecorator):
    """
    PostgreSQL-specific TypeDecorator for encrypting JSONB fields.
    
    Falls back to regular JSON if not using PostgreSQL.
    """
    
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.JSONB())
        else:
            return dialect.type_descriptor(Text())
    
    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        """Encrypt JSON value before storing in database."""
        if value is None:
            return None
        
        try:
            # Convert to JSON string if needed
            if isinstance(value, str):
                # Validate it's valid JSON
                json.loads(value)
                json_str = value
            else:
                json_str = json.dumps(value)
            
            # Encrypt the JSON string
            encrypted_bytes = encrypt_string(json_str)
            # Convert to base64 for storage
            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except (EncryptionError, TypeError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to encrypt JSONB field: {e}")
            # Store as plaintext JSON with warning
            logger.warning("Storing JSONB as plaintext due to encryption failure")
            if dialect.name == 'postgresql':
                return value  # PostgreSQL can handle dict directly
            else:
                return json.dumps(value) if not isinstance(value, str) else value
    
    def process_result_value(self, value: Any, dialect) -> Any:
        """Decrypt JSON value after retrieving from database."""
        if value is None:
            return None
        
        # Handle PostgreSQL JSONB returning dict vs other dialects returning string
        if isinstance(value, dict):
            # This shouldn't happen with encrypted data, but handle gracefully
            logger.warning("Received dict from database, expected encrypted string")
            return value
        
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(value)
            # Decrypt to get JSON string
            json_str = decrypt_string(encrypted_bytes)
            # Parse JSON
            return json.loads(json_str)
        except (EncryptionError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to decrypt JSONB field: {e}")
            # Try to parse as plaintext JSON
            try:
                if isinstance(value, str):
                    return json.loads(value)
                else:
                    return value  # Already a dict/object
            except json.JSONDecodeError:
                logger.warning("Returning raw value due to JSON parse failure")
                return value

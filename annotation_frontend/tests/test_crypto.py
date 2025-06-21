"""
Tests for crypto.py - AES encryption/decryption functionality

Tests cover:
1. Basic encrypt/decrypt round-trip functionality
2. Error handling for invalid inputs
3. Key validation and security
4. String vs bytes handling
5. Edge cases (empty data, wrong keys, etc.)
"""

import pytest
import os
from unittest.mock import patch, Mock

# Import the crypto module
from crypto import (
    CryptoService, 
    encrypt_bytes, 
    decrypt_bytes, 
    encrypt_string, 
    decrypt_string,
    EncryptionError
)


class TestCryptoService:
    """Test the CryptoService class."""
    
    def test_crypto_service_initialization_valid_key(self):
        """Test CryptoService initializes with valid 32-byte hex key."""
        # Use a valid 32-byte (64 hex chars) key
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch('crypto.settings') as mock_settings:
            mock_settings.ENCRYPTION_KEY = valid_key
            service = CryptoService()
            assert service._key == bytes.fromhex(valid_key)
    
    def test_crypto_service_initialization_invalid_key_length(self):
        """Test CryptoService raises error with invalid key length."""
        # Use a key that's too short (16 bytes instead of 32)
        short_key = "0123456789abcdef0123456789abcdef"  # 32 hex chars = 16 bytes
        
        with patch('crypto.settings') as mock_settings:
            mock_settings.ENCRYPTION_KEY = short_key
            with pytest.raises(EncryptionError, match="Invalid key length"):
                CryptoService()
    
    def test_crypto_service_initialization_invalid_hex_format(self):
        """Test CryptoService raises error with invalid hex format."""
        # Use invalid hex characters
        invalid_key = "gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg"
        
        with patch('crypto.settings') as mock_settings:
            mock_settings.ENCRYPTION_KEY = invalid_key
            with pytest.raises(EncryptionError, match="Invalid hex key format"):
                CryptoService()
    
    def test_crypto_service_initialization_missing_key(self):
        """Test CryptoService raises error when key is not configured."""
        with patch('crypto.settings') as mock_settings:
            mock_settings.ENCRYPTION_KEY = ""
            with pytest.raises(EncryptionError, match="ENCRYPTION_KEY not configured"):
                CryptoService()


class TestBasicEncryptionDecryption:
    """Test basic encryption and decryption functionality."""
    
    @pytest.fixture
    def crypto_service(self):
        """Create a CryptoService instance for testing."""
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        with patch('crypto.settings') as mock_settings:
            mock_settings.ENCRYPTION_KEY = valid_key
            return CryptoService()
    
    def test_encrypt_decrypt_bytes_round_trip(self, crypto_service):
        """Test encrypt/decrypt round-trip with bytes maintains data integrity."""
        original_data = b"This is a test message for encryption"
        
        # Encrypt the data
        encrypted = crypto_service.encrypt_bytes(original_data)
        
        # Verify encrypted data is different and longer (includes IV)
        assert encrypted != original_data
        assert len(encrypted) > len(original_data)
        assert len(encrypted) >= 16  # At least IV length
        
        # Decrypt the data
        decrypted = crypto_service.decrypt_bytes(encrypted)
        
        # Verify round-trip integrity
        assert decrypted == original_data
    
    def test_encrypt_decrypt_string_round_trip(self, crypto_service):
        """Test encrypt/decrypt round-trip with strings maintains data integrity."""
        original_text = "This is a test message with unicode: ñüñoñó 🔒"
        
        # Encrypt the string
        encrypted = crypto_service.encrypt_string(original_text)
        
        # Verify encrypted data is bytes and different
        assert isinstance(encrypted, bytes)
        assert len(encrypted) > len(original_text.encode('utf-8'))
        
        # Decrypt the string
        decrypted = crypto_service.decrypt_string(encrypted)
        
        # Verify round-trip integrity
        assert decrypted == original_text
        assert isinstance(decrypted, str)
    
    def test_encrypt_decrypt_large_data(self, crypto_service):
        """Test encryption/decryption with large data."""
        # Create a large test payload (1MB)
        large_data = b"A" * (1024 * 1024)
        
        encrypted = crypto_service.encrypt_bytes(large_data)
        decrypted = crypto_service.decrypt_bytes(encrypted)
        
        assert decrypted == large_data
    
    def test_encrypt_decrypt_empty_data(self, crypto_service):
        """Test handling of empty data."""
        # Empty bytes
        encrypted_empty = crypto_service.encrypt_bytes(b"")
        assert encrypted_empty == b""
        
        decrypted_empty = crypto_service.decrypt_bytes(b"")
        assert decrypted_empty == b""
        
        # Empty string
        encrypted_str = crypto_service.encrypt_string("")
        assert encrypted_str == b""
        
        # Note: decrypt_string on empty bytes should return empty string
        decrypted_str = crypto_service.decrypt_string(b"")
        assert decrypted_str == ""
    
    def test_different_encryption_results(self, crypto_service):
        """Test that encrypting the same data twice produces different results (due to random IV)."""
        data = b"Same data encrypted twice"
        
        encrypted1 = crypto_service.encrypt_bytes(data)
        encrypted2 = crypto_service.encrypt_bytes(data)
        
        # Should be different due to random IV
        assert encrypted1 != encrypted2
        
        # But both should decrypt to the same original data
        assert crypto_service.decrypt_bytes(encrypted1) == data
        assert crypto_service.decrypt_bytes(encrypted2) == data


class TestConvenienceFunctions:
    """Test the module-level convenience functions."""
    
    def test_convenience_functions_encrypt_decrypt_bytes(self):
        """Test module-level encrypt_bytes and decrypt_bytes functions."""
        original_data = b"Test data for convenience functions"
        
        encrypted = encrypt_bytes(original_data)
        decrypted = decrypt_bytes(encrypted)
        
        assert decrypted == original_data
    
    def test_convenience_functions_encrypt_decrypt_string(self):
        """Test module-level encrypt_string and decrypt_string functions."""
        original_text = "Test string for convenience functions"
        
        encrypted = encrypt_string(original_text)
        decrypted = decrypt_string(encrypted)
        
        assert decrypted == original_text


class TestErrorHandling:
    """Test error handling for various edge cases."""
    
    @pytest.fixture
    def crypto_service(self):
        """Create a CryptoService instance for testing."""
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        with patch('crypto.settings') as mock_settings:
            mock_settings.ENCRYPTION_KEY = valid_key
            return CryptoService()
    
    def test_encrypt_bytes_invalid_input_type(self, crypto_service):
        """Test encryption with invalid input type."""
        with pytest.raises(EncryptionError, match="Data must be bytes"):
            crypto_service.encrypt_bytes("this is a string, not bytes")
        
        with pytest.raises(EncryptionError, match="Data must be bytes"):
            crypto_service.encrypt_bytes(123)
    
    def test_encrypt_string_invalid_input_type(self, crypto_service):
        """Test string encryption with invalid input type."""
        with pytest.raises(EncryptionError, match="Text must be string"):
            crypto_service.encrypt_string(b"this is bytes, not string")
        
        with pytest.raises(EncryptionError, match="Text must be string"):
            crypto_service.encrypt_string(123)
    
    def test_decrypt_bytes_invalid_input_type(self, crypto_service):
        """Test decryption with invalid input type."""
        with pytest.raises(EncryptionError, match="Encrypted data must be bytes"):
            crypto_service.decrypt_bytes("this is a string, not bytes")
    
    def test_decrypt_bytes_too_short(self, crypto_service):
        """Test decryption with data too short to contain IV."""
        with pytest.raises(EncryptionError, match="too short for IV"):
            crypto_service.decrypt_bytes(b"short")  # Less than 16 bytes
    
    def test_decrypt_bytes_only_iv(self, crypto_service):
        """Test decryption with only IV, no content."""
        iv_only = os.urandom(16)  # 16 bytes of random data (IV length)
        with pytest.raises(EncryptionError, match="No encrypted content after IV"):
            crypto_service.decrypt_bytes(iv_only)
    
    def test_decrypt_with_wrong_key(self):
        """Test decryption fails with wrong key."""
        # Create service with first key
        key1 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        with patch('crypto.settings') as mock_settings:
            mock_settings.ENCRYPTION_KEY = key1
            service1 = CryptoService()
        
        # Encrypt data with first key
        data = b"Secret data"
        encrypted = service1.encrypt_bytes(data)
        
        # Create service with different key
        key2 = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
        with patch('crypto.settings') as mock_settings:
            mock_settings.ENCRYPTION_KEY = key2
            service2 = CryptoService()
        
        # Attempt to decrypt with wrong key should fail
        with pytest.raises(EncryptionError, match="Decryption failed"):
            service2.decrypt_bytes(encrypted)
    
    def test_decrypt_corrupted_data(self, crypto_service):
        """Test decryption fails with corrupted data."""
        # Create valid encrypted data
        data = b"Valid data"
        encrypted = crypto_service.encrypt_bytes(data)
        
        # Corrupt the encrypted data
        corrupted = encrypted[:-5] + b"XXXXX"
        
        # Decryption should fail
        with pytest.raises(EncryptionError, match="Decryption failed"):
            crypto_service.decrypt_bytes(corrupted)
    
    def test_decrypt_string_invalid_utf8(self, crypto_service):
        """Test string decryption fails with invalid UTF-8."""
        # Create encrypted data that will result in invalid UTF-8
        # This is tricky to test directly, so we'll mock the decrypt_bytes method
        with patch.object(crypto_service, 'decrypt_bytes') as mock_decrypt:
            # Return invalid UTF-8 bytes
            mock_decrypt.return_value = b'\xff\xfe\xfd'  # Invalid UTF-8 sequence
            
            with pytest.raises(EncryptionError, match="Failed to decode decrypted data as UTF-8"):
                crypto_service.decrypt_string(b"dummy_encrypted_data")


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    @pytest.fixture
    def crypto_service(self):
        """Create a CryptoService instance for testing."""
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        with patch('crypto.settings') as mock_settings:
            mock_settings.ENCRYPTION_KEY = valid_key
            return CryptoService()
    
    def test_encrypt_base64_frame_data(self, crypto_service):
        """Test encrypting base64-encoded frame data."""
        import base64
        
        # Simulate image data
        fake_image_data = b"FAKE_PNG_DATA" + b"\x89PNG\r\n\x1a\n" + b"more_fake_data" * 100
        base64_image = base64.b64encode(fake_image_data).decode('utf-8')
        
        # Encrypt the base64 string
        encrypted = crypto_service.encrypt_string(base64_image)
        
        # Decrypt and verify
        decrypted = crypto_service.decrypt_string(encrypted)
        assert decrypted == base64_image
        
        # Verify we can decode back to original binary data
        recovered_image = base64.b64decode(decrypted)
        assert recovered_image == fake_image_data
    
    def test_encrypt_json_annotation_data(self, crypto_service):
        """Test encrypting JSON annotation data."""
        import json
        
        annotation_data = {
            "bbox": [100, 200, 300, 400],
            "label": "person",
            "confidence": 0.95,
            "metadata": {
                "camera_id": "cam_001",
                "timestamp": "2025-06-16T10:30:00Z"
            }
        }
        
        # Convert to JSON string and encrypt
        json_str = json.dumps(annotation_data)
        encrypted = crypto_service.encrypt_string(json_str)
        
        # Decrypt and verify
        decrypted_json = crypto_service.decrypt_string(encrypted)
        recovered_data = json.loads(decrypted_json)
        
        assert recovered_data == annotation_data
    
    def test_encrypt_sensitive_notes(self, crypto_service):
        """Test encrypting sensitive annotation notes."""
        sensitive_notes = "This person appears to be John Doe, age 35, seen near building entrance"
        
        encrypted = crypto_service.encrypt_string(sensitive_notes)
        decrypted = crypto_service.decrypt_string(encrypted)
        
        assert decrypted == sensitive_notes
        # Verify original text is not present in encrypted data
        assert sensitive_notes.encode('utf-8') not in encrypted


class TestSecurityProperties:
    """Test security properties of the encryption."""
    
    @pytest.fixture
    def crypto_service(self):
        """Create a CryptoService instance for testing."""
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        with patch('crypto.settings') as mock_settings:
            mock_settings.ENCRYPTION_KEY = valid_key
            return CryptoService()
    
    def test_iv_randomness(self, crypto_service):
        """Test that IVs are random for each encryption."""
        data = b"Same data for IV test"
        
        # Encrypt the same data multiple times
        encryptions = [crypto_service.encrypt_bytes(data) for _ in range(10)]
        
        # Extract IVs (first 16 bytes)
        ivs = [enc[:16] for enc in encryptions]
        
        # All IVs should be different
        assert len(set(ivs)) == len(ivs), "IVs should be unique"
        
        # Each IV should be 16 bytes
        for iv in ivs:
            assert len(iv) == 16
    
    def test_ciphertext_appears_random(self, crypto_service):
        """Test that ciphertext doesn't contain patterns from plaintext."""
        # Test with repeated patterns
        plaintext = b"AAAABBBBCCCCDDDD" * 100
        encrypted = crypto_service.encrypt_bytes(plaintext)
        
        # Ciphertext should not contain the repeated patterns
        assert b"AAAABBBBCCCCDDDD" not in encrypted
        assert b"AAAA" not in encrypted
        
        # Test with structured data
        structured_data = b'{"key": "value", "repeated": "pattern"}' * 50
        encrypted_structured = crypto_service.encrypt_bytes(structured_data)
        
        # Should not contain JSON patterns
        assert b'{"key":' not in encrypted_structured
        assert b'"repeated"' not in encrypted_structured
    
    def test_key_derivation_from_settings(self):
        """Test that different keys produce different encryption results."""
        data = b"Test data for key differences"
        
        # Encrypt with first key
        key1 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        with patch('crypto.settings') as mock_settings:
            mock_settings.ENCRYPTION_KEY = key1
            service1 = CryptoService()
            encrypted1 = service1.encrypt_bytes(data)
        
        # Encrypt with second key
        key2 = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
        with patch('crypto.settings') as mock_settings:
            mock_settings.ENCRYPTION_KEY = key2
            service2 = CryptoService()
            encrypted2 = service2.encrypt_bytes(data)
        
        # Results should be different
        assert encrypted1 != encrypted2
        
        # Each should decrypt correctly with its own key
        assert service1.decrypt_bytes(encrypted1) == data
        assert service2.decrypt_bytes(encrypted2) == data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

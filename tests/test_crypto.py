"""
Tests for shared/crypto.py - AES encryption/decryption functionality

Tests cover:
1. Basic encrypt/decrypt round-trip functionality
2. Error handling for invalid inputs
3. Key validation and security
4. String vs bytes handling
5. Edge cases (empty data, wrong keys, etc.)
6. Global service instance management
"""

import pytest
import os
from unittest.mock import patch, Mock

# Import the crypto module
from shared.crypto import (
    CryptoService, 
    encrypt_bytes, 
    decrypt_bytes, 
    encrypt_string, 
    decrypt_string,
    get_crypto_service,
    EncryptionError
)


class TestCryptoService:
    """Test the CryptoService class."""
    
    def test_crypto_service_initialization_valid_key(self):
        """Test CryptoService initializes with valid 32-byte hex key."""
        # Use a valid 32-byte (64 hex chars) key
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        service = CryptoService(encryption_key=valid_key)
        assert service._key == bytes.fromhex(valid_key)
    
    def test_crypto_service_initialization_from_env(self):
        """Test CryptoService initializes from environment variable."""
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': valid_key}):
            service = CryptoService()
            assert service._key == bytes.fromhex(valid_key)
    
    def test_crypto_service_initialization_invalid_key_length(self):
        """Test CryptoService raises error with invalid key length."""
        # Use a key that's too short (16 bytes instead of 32)
        short_key = "0123456789abcdef0123456789abcdef"  # 32 hex chars = 16 bytes
        
        with pytest.raises(EncryptionError, match="Invalid key length"):
            CryptoService(encryption_key=short_key)
    
    def test_crypto_service_initialization_invalid_hex_format(self):
        """Test CryptoService raises error with invalid hex format."""
        # Use invalid hex characters
        invalid_key = "gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg"
        
        with pytest.raises(EncryptionError, match="Invalid hex key format"):
            CryptoService(encryption_key=invalid_key)
    
    def test_crypto_service_initialization_missing_key(self):
        """Test CryptoService raises error when key is not configured."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EncryptionError, match="ENCRYPTION_KEY not configured"):
                CryptoService()


class TestBasicEncryptionDecryption:
    """Test basic encryption and decryption functionality."""
    
    @pytest.fixture
    def crypto_service(self):
        """Create a CryptoService instance for testing."""
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        return CryptoService(encryption_key=valid_key)
    
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
        
        # Verify encrypted data is bytes and different from original
        assert isinstance(encrypted, bytes)
        assert encrypted != original_text.encode('utf-8')
        
        # Decrypt the string
        decrypted = crypto_service.decrypt_string(encrypted)
        
        # Verify round-trip integrity
        assert decrypted == original_text
        assert isinstance(decrypted, str)
    
    def test_encrypt_large_data(self, crypto_service):
        """Test encryption/decryption of large data."""
        # Create 1MB of test data
        large_data = b"A" * (1024 * 1024)
        
        # Encrypt and decrypt
        encrypted = crypto_service.encrypt_bytes(large_data)
        decrypted = crypto_service.decrypt_bytes(encrypted)
        
        # Verify integrity
        assert decrypted == large_data
        assert len(encrypted) > len(large_data)  # Should be larger due to padding and IV
    
    def test_encrypt_binary_data(self, crypto_service):
        """Test encryption/decryption of binary data."""
        # Create binary data with all possible byte values
        binary_data = bytes(range(256))
        
        # Encrypt and decrypt
        encrypted = crypto_service.encrypt_bytes(binary_data)
        decrypted = crypto_service.decrypt_bytes(encrypted)
        
        # Verify integrity
        assert decrypted == binary_data
    
    def test_multiple_encryptions_different_results(self, crypto_service):
        """Test that multiple encryptions of same data produce different results (due to random IV)."""
        data = b"Same data encrypted multiple times"
        
        # Encrypt the same data multiple times
        encrypted1 = crypto_service.encrypt_bytes(data)
        encrypted2 = crypto_service.encrypt_bytes(data)
        encrypted3 = crypto_service.encrypt_bytes(data)
        
        # Results should be different (due to random IV)
        assert encrypted1 != encrypted2
        assert encrypted2 != encrypted3
        assert encrypted1 != encrypted3
        
        # But all should decrypt to the same original data
        assert crypto_service.decrypt_bytes(encrypted1) == data
        assert crypto_service.decrypt_bytes(encrypted2) == data
        assert crypto_service.decrypt_bytes(encrypted3) == data


class TestInputValidation:
    """Test input validation and error handling."""
    
    @pytest.fixture
    def crypto_service(self):
        """Create a CryptoService instance for testing."""
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        return CryptoService(encryption_key=valid_key)
    
    def test_encrypt_bytes_invalid_input_type(self, crypto_service):
        """Test encrypt_bytes raises error for non-bytes input."""
        with pytest.raises(EncryptionError, match="Data must be bytes"):
            crypto_service.encrypt_bytes("string instead of bytes")
    
    def test_encrypt_string_invalid_input_type(self, crypto_service):
        """Test encrypt_string raises error for non-string input."""
        with pytest.raises(EncryptionError, match="Text must be string"):
            crypto_service.encrypt_string(b"bytes instead of string")
    
    def test_decrypt_bytes_invalid_input_type(self, crypto_service):
        """Test decrypt_bytes raises error for non-bytes input."""
        with pytest.raises(EncryptionError, match="Encrypted data must be bytes"):
            crypto_service.decrypt_bytes("string instead of bytes")
    
    def test_encrypt_empty_data(self, crypto_service):
        """Test encryption of empty data."""
        empty_data = b""
        encrypted = crypto_service.encrypt_bytes(empty_data)
        
        # Empty data should return empty bytes
        assert encrypted == b""
    
    def test_decrypt_empty_data(self, crypto_service):
        """Test decryption of empty data."""
        empty_data = b""
        decrypted = crypto_service.decrypt_bytes(empty_data)
        
        # Empty data should return empty bytes
        assert decrypted == b""
    
    def test_decrypt_too_short_data(self, crypto_service):
        """Test decryption fails with data too short for IV."""
        # Data shorter than IV length (16 bytes)
        short_data = b"tooshort"
        
        with pytest.raises(EncryptionError, match="too short for IV"):
            crypto_service.decrypt_bytes(short_data)
    
    def test_decrypt_iv_only_data(self, crypto_service):
        """Test decryption fails with IV-only data (no content)."""
        # Exactly 16 bytes (IV length) but no content
        iv_only = b"1234567890123456"  # 16 bytes
        
        with pytest.raises(EncryptionError, match="No encrypted content after IV"):
            crypto_service.decrypt_bytes(iv_only)
    
    def test_decrypt_with_wrong_key(self):
        """Test decryption fails with wrong key."""
        # Create service with first key
        key1 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        service1 = CryptoService(encryption_key=key1)
        
        # Encrypt data with first key
        data = b"Secret data"
        encrypted = service1.encrypt_bytes(data)
        
        # Create service with different key
        key2 = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
        service2 = CryptoService(encryption_key=key2)
        
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
        # We'll encrypt binary data that's not valid UTF-8
        invalid_utf8_data = b'\xff\xfe\xfd\xfc'
        encrypted = crypto_service.encrypt_bytes(invalid_utf8_data)
        
        # Decryption should fail when trying to decode as UTF-8
        with pytest.raises(EncryptionError, match="Failed to decode decrypted data as UTF-8"):
            crypto_service.decrypt_string(encrypted)


class TestConvenienceFunctions:
    """Test global convenience functions."""
    
    def test_convenience_functions_work(self):
        """Test that convenience functions work correctly."""
        # Test with a known key
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': valid_key}):
            # Reset global service to pick up new env
            import shared.crypto
            shared.crypto._crypto_service = None
            
            # Test bytes functions
            data = b"Test data for convenience functions"
            encrypted = encrypt_bytes(data)
            decrypted = decrypt_bytes(encrypted)
            assert decrypted == data
            
            # Test string functions
            text = "Test string for convenience functions"
            encrypted_str = encrypt_string(text)
            decrypted_str = decrypt_string(encrypted_str)
            assert decrypted_str == text
    
    def test_get_crypto_service_singleton(self):
        """Test that get_crypto_service returns the same instance."""
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': valid_key}):
            # Reset global service
            import shared.crypto
            shared.crypto._crypto_service = None
            
            # Get service instances
            service1 = get_crypto_service()
            service2 = get_crypto_service()
            
            # Should be the same instance
            assert service1 is service2


class TestVideoDataEncryption:
    """Test encryption/decryption of video-like binary data."""
    
    @pytest.fixture
    def crypto_service(self):
        """Create a CryptoService instance for testing."""
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        return CryptoService(encryption_key=valid_key)
    
    def test_encrypt_mp4_header(self, crypto_service):
        """Test encryption of MP4 file header data."""
        # MP4 file starts with specific bytes
        mp4_header = b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom'
        
        # Encrypt and decrypt
        encrypted = crypto_service.encrypt_bytes(mp4_header)
        decrypted = crypto_service.decrypt_bytes(encrypted)
        
        # Verify integrity
        assert decrypted == mp4_header
    
    def test_encrypt_large_video_chunk(self, crypto_service):
        """Test encryption of large video-like data chunk."""
        # Simulate a chunk of video data (512KB)
        video_chunk = os.urandom(512 * 1024)
        
        # Encrypt and decrypt
        encrypted = crypto_service.encrypt_bytes(video_chunk)
        decrypted = crypto_service.decrypt_bytes(encrypted)
        
        # Verify integrity
        assert decrypted == video_chunk
        
        # Verify encrypted data is larger (padding + IV)
        assert len(encrypted) > len(video_chunk)
        
        # Verify encrypted data is different
        assert encrypted != video_chunk


class TestImageDataEncryption:
    """Test encryption/decryption of image-like data."""
    
    @pytest.fixture
    def crypto_service(self):
        """Create a CryptoService instance for testing."""
        valid_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        return CryptoService(encryption_key=valid_key)
    
    def test_encrypt_base64_frame_data(self, crypto_service):
        """Test encryption of base64-encoded frame data."""
        # Simulate base64-encoded image data
        import base64
        fake_image_data = b"fake image data that would be much larger in reality"
        base64_data = base64.b64encode(fake_image_data).decode('utf-8')
        
        # Encrypt and decrypt the base64 string
        encrypted = crypto_service.encrypt_string(base64_data)
        decrypted = crypto_service.decrypt_string(encrypted)
        
        # Verify integrity
        assert decrypted == base64_data
        
        # Verify we can still decode the base64 after decryption
        decoded_image = base64.b64decode(decrypted)
        assert decoded_image == fake_image_data
    
    def test_encrypt_json_detection_data(self, crypto_service):
        """Test encryption of JSON detection data."""
        import json
        
        # Simulate detection data with bounding boxes
        detection_data = {
            "detections": [
                {
                    "label": "person",
                    "confidence": 0.95,
                    "bbox": {"x1": 100, "y1": 50, "x2": 200, "y2": 300}
                },
                {
                    "label": "vehicle", 
                    "confidence": 0.87,
                    "bbox": {"x1": 300, "y1": 200, "x2": 500, "y2": 400}
                }
            ],
            "timestamp": "2025-01-01T12:00:00Z",
            "camera_id": "cam-001"
        }
        
        # Convert to JSON string and encrypt
        json_string = json.dumps(detection_data)
        encrypted = crypto_service.encrypt_string(json_string)
        decrypted = crypto_service.decrypt_string(encrypted)
        
        # Verify integrity
        assert decrypted == json_string
        
        # Verify we can still parse JSON after decryption
        parsed_data = json.loads(decrypted)
        assert parsed_data == detection_data

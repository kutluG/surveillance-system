"""
Tests for encrypted storage functionality

Tests cover:
1. Encrypted S3 video storage
2. Encrypted local video storage  
3. Video data encryption/decryption round-trip
4. Fallback behavior when encryption fails
5. Metadata preservation
6. Integration with existing storage interfaces
"""

import pytest
import tempfile
import os
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime

# Set encryption key for testing before importing crypto modules
TEST_ENCRYPTION_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

# Mock the environment variable before any imports
with patch.dict(os.environ, {'ENCRYPTION_KEY': TEST_ENCRYPTION_KEY}):
    # Import the encrypted storage modules
    from vms_service.encrypted_storage import (
        EncryptedS3VideoStorage,
        EncryptedLocalVideoStorage,
        EncryptedVideoStorageMixin,
        get_encrypted_storage
    )
from shared.crypto import EncryptionError

@pytest.fixture(autouse=True)
def setup_encryption():
    """Setup encryption key for all tests."""
    with patch.dict(os.environ, {'ENCRYPTION_KEY': TEST_ENCRYPTION_KEY}):
        # Reset the global crypto service to pick up the test key
        import shared.crypto
        shared.crypto._crypto_service = None
        yield
        # Reset after test
        shared.crypto._crypto_service = None


class TestEncryptedVideoStorageMixin:
    """Test the encryption mixin functionality."""
    
    @pytest.fixture
    def mixin(self):
        """Create a mixin instance for testing."""
        return EncryptedVideoStorageMixin()
    
    def test_encrypt_decrypt_video_data_round_trip(self, mixin):
        """Test video data encryption/decryption maintains integrity."""
        # Simulate video data (MP4 header + content)
        video_data = b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom' + b'A' * 1000
        
        # Encrypt the video data
        encrypted = mixin._encrypt_video_data(video_data)
        
        # Verify encrypted data is different and larger
        assert encrypted != video_data
        assert len(encrypted) > len(video_data)
        
        # Decrypt the video data
        decrypted = mixin._decrypt_video_data(encrypted)
        
        # Verify round-trip integrity
        assert decrypted == video_data
    
    def test_is_encrypted_data_detection(self, mixin):
        """Test detection of encrypted vs unencrypted data."""
        # Test with encrypted-looking data (has IV + content)
        encrypted_like = b'A' * 20  # 20 bytes should be considered encrypted
        assert mixin._is_encrypted_data(encrypted_like) == True
        
        # Test with too-short data
        short_data = b'A' * 10  # 10 bytes should not be considered encrypted
        assert mixin._is_encrypted_data(short_data) == False
        
        # Test with exactly minimum length
        min_data = b'A' * 17  # 17 bytes should be considered encrypted
        assert mixin._is_encrypted_data(min_data) == True
    
    def test_encrypt_video_data_error_handling(self, mixin):
        """Test error handling in video data encryption."""
        with patch('vms_service.encrypted_storage.encrypt_bytes') as mock_encrypt:
            mock_encrypt.side_effect = EncryptionError("Encryption failed")
            
            with pytest.raises(EncryptionError):
                mixin._encrypt_video_data(b"test data")
    
    def test_decrypt_video_data_error_handling(self, mixin):
        """Test error handling in video data decryption."""
        with patch('vms_service.encrypted_storage.decrypt_bytes') as mock_decrypt:
            mock_decrypt.side_effect = EncryptionError("Decryption failed")
            
            with pytest.raises(EncryptionError):
                mixin._decrypt_video_data(b"encrypted data")


class TestEncryptedLocalVideoStorage:
    """Test encrypted local video storage."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary directory for encrypted local storage tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = EncryptedLocalVideoStorage()
            storage.storage_path = temp_dir
            yield storage
    
    @pytest.mark.asyncio
    async def test_store_clip_with_encryption(self, temp_storage):
        """Test storing video clip with encryption."""
        event_id = "test-encrypted-event"
        video_data = b"fake video data for encryption test"
        metadata = {
            "camera_id": "cam01",
            "timestamp": "2025-06-17T10:30:00Z",
            "duration_seconds": 30
        }
        
        # Store the clip
        storage_url = await temp_storage.store_clip(event_id, video_data, metadata)
        
        # Verify storage URL is returned
        assert storage_url.startswith("file://")
        assert event_id in storage_url
        
        # Verify files exist
        video_path = os.path.join(temp_storage.storage_path, f"{event_id}.mp4")
        metadata_path = os.path.join(temp_storage.storage_path, f"{event_id}.json")
        
        assert os.path.exists(video_path)
        assert os.path.exists(metadata_path)
        
        # Verify video file is encrypted (different from original)
        with open(video_path, 'rb') as f:
            stored_data = f.read()
        assert stored_data != video_data
        assert len(stored_data) > len(video_data)  # Encrypted data is larger
        
        # Verify metadata includes encryption info
        import json
        with open(metadata_path, 'r') as f:
            stored_metadata = json.load(f)
        assert stored_metadata['encrypted'] == True
        assert stored_metadata['encryption_method'] == 'AES-256-CBC'
    
    @pytest.mark.asyncio
    async def test_get_clip_data_with_decryption(self, temp_storage):
        """Test retrieving and decrypting video clip data."""
        event_id = "test-decrypt-event"
        original_data = b"original video data to decrypt"
        metadata = {"camera_id": "cam01"}
        
        # Store the clip first
        await temp_storage.store_clip(event_id, original_data, metadata)
        
        # Retrieve the clip data
        retrieved_data = await temp_storage.get_clip_data(event_id)
        
        # Verify the data was decrypted correctly
        assert retrieved_data == original_data
    
    @pytest.mark.asyncio
    async def test_get_clip_data_nonexistent(self, temp_storage):
        """Test retrieving data for non-existent clip."""
        result = await temp_storage.get_clip_data("nonexistent-event")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_store_clip_encryption_fallback(self, temp_storage):
        """Test fallback to unencrypted storage when encryption fails."""
        event_id = "test-fallback-event"
        video_data = b"test video data"
        metadata = {"camera_id": "cam01"}
        
        # Mock encryption to fail
        with patch.object(temp_storage, '_encrypt_video_data') as mock_encrypt:
            mock_encrypt.side_effect = EncryptionError("Encryption failed")
            
            # Should still store the clip but unencrypted
            storage_url = await temp_storage.store_clip(event_id, video_data, metadata)
            assert storage_url is not None
            
            # Verify metadata shows encryption failed
            metadata_path = os.path.join(temp_storage.storage_path, f"{event_id}.json")
            import json
            with open(metadata_path, 'r') as f:
                stored_metadata = json.load(f)
            assert stored_metadata['encrypted'] == False
    
    @pytest.mark.asyncio
    async def test_get_clip_data_decryption_fallback(self, temp_storage):
        """Test fallback when decryption fails."""
        event_id = "test-decrypt-fallback"
        video_data = b"test video data"
        metadata = {"camera_id": "cam01"}
        
        # Store clip normally (encrypted)
        await temp_storage.store_clip(event_id, video_data, metadata)
        
        # Mock decryption to fail
        with patch.object(temp_storage, '_decrypt_video_data') as mock_decrypt:
            mock_decrypt.side_effect = EncryptionError("Decryption failed")
            
            # Should return encrypted data as fallback
            retrieved_data = await temp_storage.get_clip_data(event_id)
            assert retrieved_data is not None
            assert retrieved_data != video_data  # Should be encrypted data


class TestEncryptedS3VideoStorage:
    """Test encrypted S3 video storage."""
    
    @pytest.fixture
    def s3_storage(self):
        """Create an encrypted S3 storage instance with mocked S3 client."""
        storage = EncryptedS3VideoStorage()
        storage.s3_client = Mock()
        return storage
    
    @pytest.mark.asyncio
    async def test_store_clip_with_s3_encryption(self, s3_storage):
        """Test storing video clip to S3 with encryption."""
        event_id = "test-s3-encrypted"
        video_data = b"fake video data for S3 encryption test"
        metadata = {
            "camera_id": "cam01",
            "timestamp": "2025-06-17T10:30:00Z"
        }
        
        # Mock the S3 put_object call
        s3_storage.s3_client.put_object.return_value = {}
        
        # Store the clip
        storage_url = await s3_storage.store_clip(event_id, video_data, metadata)
        
        # Verify S3 put_object was called
        s3_storage.s3_client.put_object.assert_called_once()
        
        # Get the call arguments
        call_args = s3_storage.s3_client.put_object.call_args
        
        # Verify the data passed to S3 is encrypted (different from original)
        stored_body = call_args[1]['Body']
        assert stored_body != video_data
        assert len(stored_body) > len(video_data)
          # Verify metadata includes encryption info
        stored_metadata = call_args[1]['Metadata']
        assert stored_metadata['encrypted'] == 'true'
        assert stored_metadata['encryption-method'] == 'AES-256-CBC'
        
        # Verify storage URL format
        assert storage_url.startswith("s3://")
        assert event_id in storage_url
    
    @pytest.mark.asyncio 
    async def test_get_clip_data_s3_decryption(self, s3_storage):
        """Test retrieving and decrypting data from S3."""
        event_id = "test-s3-decrypt"
        original_data = b"original S3 video data"
        
        # Mock S3 head_object response with encryption metadata
        s3_storage.s3_client.head_object.return_value = {
            'Metadata': {
                'encrypted': 'true',
                'encryption_method': 'AES-256-CBC'
            }
        }
        
        # First encrypt the data to simulate what would be stored
        encrypted_data = s3_storage._encrypt_video_data(original_data)
        
        # Mock S3 get_object response
        mock_body = Mock()
        mock_body.read.return_value = encrypted_data
        s3_storage.s3_client.get_object.return_value = {'Body': mock_body}
        
        # Retrieve the data
        retrieved_data = await s3_storage._get_clip_data(event_id)
        
        # Verify the data was decrypted correctly
        assert retrieved_data == original_data
    
    @pytest.mark.asyncio
    async def test_get_clip_data_s3_not_found(self, s3_storage):
        """Test handling of non-existent S3 objects."""
        event_id = "nonexistent-s3-event"
        
        # Mock S3 to raise NoSuchKey exception
        s3_storage.s3_client.head_object.side_effect = s3_storage.s3_client.exceptions.NoSuchKey({
            'Error': {'Code': 'NoSuchKey'}
        }, 'head_object')
        
        # Should return None
        result = await s3_storage._get_clip_data(event_id)
        assert result is None


class TestGetEncryptedStorage:
    """Test the encrypted storage factory function."""
    
    def test_get_encrypted_storage_local(self):
        """Test factory returns encrypted local storage."""
        with patch.dict(os.environ, {'VIDEO_STORAGE_TYPE': 'local'}):
            storage = get_encrypted_storage()
            assert isinstance(storage, EncryptedLocalVideoStorage)
    
    def test_get_encrypted_storage_s3(self):
        """Test factory returns encrypted S3 storage."""
        with patch.dict(os.environ, {'VIDEO_STORAGE_TYPE': 's3'}):
            storage = get_encrypted_storage()
            assert isinstance(storage, EncryptedS3VideoStorage)

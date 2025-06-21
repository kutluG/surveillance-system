"""
Tests for vms_service/encrypted_storage.py - Encrypted video storage functionality

Tests cover:
1. Encrypted S3 and local storage operations
2. Transparent encryption/decryption of video data
3. Fallback behavior when encryption fails
4. Metadata handling for encrypted content
5. Backward compatibility with unencrypted data
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the encrypted storage classes
from vms_service.encrypted_storage import (
    EncryptedS3VideoStorage,
    EncryptedLocalVideoStorage,
    EncryptedVideoStorageMixin,
    get_encrypted_storage
)


class TestEncryptedVideoStorageMixin:
    """Test the encryption mixin functionality."""
    
    @pytest.fixture
    def mixin(self):
        """Create a mixin instance for testing."""
        return EncryptedVideoStorageMixin()
    
    def test_encrypt_decrypt_video_data_round_trip(self, mixin):
        """Test encrypt/decrypt round-trip maintains video data integrity."""
        # Simulate video data
        video_data = b"fake video data that represents MP4 bytes"
        
        with patch('vms_service.encrypted_storage.encrypt_bytes') as mock_encrypt, \
             patch('vms_service.encrypted_storage.decrypt_bytes') as mock_decrypt:
            
            # Mock encryption/decryption
            encrypted_data = b"encrypted_fake_video_data"
            mock_encrypt.return_value = encrypted_data
            mock_decrypt.return_value = video_data
            
            # Test encryption
            result = mixin._encrypt_video_data(video_data)
            assert result == encrypted_data
            mock_encrypt.assert_called_once_with(video_data)
            
            # Test decryption
            result = mixin._decrypt_video_data(encrypted_data)
            assert result == video_data
            mock_decrypt.assert_called_once_with(encrypted_data)
    
    def test_is_encrypted_data(self, mixin):
        """Test detection of encrypted data."""
        # Too short to be encrypted (less than IV + content)
        short_data = b"short"
        assert not mixin._is_encrypted_data(short_data)
        
        # Minimum encrypted size (16 bytes IV + 1 byte content)
        min_encrypted = b"1234567890123456A"  # 17 bytes
        assert mixin._is_encrypted_data(min_encrypted)
        
        # Larger encrypted data
        large_encrypted = b"1234567890123456" + b"A" * 100
        assert mixin._is_encrypted_data(large_encrypted)
        
        # Empty data
        empty_data = b""
        assert not mixin._is_encrypted_data(empty_data)


class TestEncryptedS3VideoStorage:
    """Test encrypted S3 video storage."""
    
    @pytest.fixture
    def storage(self):
        """Create an encrypted S3 storage instance for testing."""
        with patch('vms_service.encrypted_storage.boto3.client'):
            return EncryptedS3VideoStorage()
    
    @pytest.mark.asyncio
    async def test_store_clip_with_encryption(self, storage):
        """Test storing a video clip with encryption."""
        event_id = "test-event-123"
        video_data = b"fake video data for testing"
        metadata = {"camera_id": "cam01", "timestamp": "2025-01-01T12:00:00Z"}
        
        # Mock the parent store_clip method
        expected_url = f"s3://test-bucket/clips/{event_id}.mp4"
        
        with patch.object(storage.__class__.__bases__[1], 'store_clip', return_value=expected_url) as mock_parent, \
             patch.object(storage, '_encrypt_video_data', return_value=b"encrypted_data") as mock_encrypt:
            
            # Store the clip
            result = await storage.store_clip(event_id, video_data, metadata)
            
            # Verify encryption was called
            mock_encrypt.assert_called_once_with(video_data)
            
            # Verify parent method was called with encrypted data and updated metadata
            mock_parent.assert_called_once()
            call_args = mock_parent.call_args
            assert call_args[0][0] == event_id  # event_id
            assert call_args[0][1] == b"encrypted_data"  # encrypted video data
            
            # Check metadata was updated
            call_metadata = call_args[0][2]
            assert call_metadata['encrypted'] == 'true'
            assert call_metadata['encryption_method'] == 'AES-256-CBC'
            assert call_metadata['camera_id'] == 'cam01'  # Original metadata preserved
            
            assert result == expected_url
    
    @pytest.mark.asyncio
    async def test_store_clip_encryption_fallback(self, storage):
        """Test fallback to unencrypted storage when encryption fails."""
        event_id = "test-event-456"
        video_data = b"fake video data"
        metadata = {"camera_id": "cam02"}
        
        expected_url = f"s3://test-bucket/clips/{event_id}.mp4"
        
        with patch.object(storage.__class__.__bases__[1], 'store_clip', return_value=expected_url) as mock_parent, \
             patch.object(storage, '_encrypt_video_data', side_effect=Exception("Encryption failed")) as mock_encrypt:
            
            # Store the clip (should fallback to unencrypted)
            result = await storage.store_clip(event_id, video_data, metadata)
            
            # Verify encryption was attempted
            mock_encrypt.assert_called_once_with(video_data)
            
            # Verify parent method was called with original data and fallback metadata
            mock_parent.assert_called_once()
            call_args = mock_parent.call_args
            assert call_args[0][0] == event_id
            assert call_args[0][1] == video_data  # Original data, not encrypted
            
            # Check metadata indicates unencrypted
            call_metadata = call_args[0][2]
            assert call_metadata['encrypted'] == 'false'
            
            assert result == expected_url
    
    @pytest.mark.asyncio
    async def test_get_clip_data_encrypted(self, storage):
        """Test retrieving and decrypting encrypted clip data."""
        event_id = "test-event-789"
        encrypted_data = b"encrypted_fake_video_data"
        original_data = b"original_fake_video_data"
        
        # Mock S3 client responses
        mock_head_response = {
            'Metadata': {
                'encrypted': 'true',
                'encryption-method': 'AES-256-CBC'
            }
        }
        
        mock_get_response = {
            'Body': Mock()
        }
        mock_get_response['Body'].read.return_value = encrypted_data
        
        storage.s3_client.head_object.return_value = mock_head_response
        storage.s3_client.get_object.return_value = mock_get_response
        
        with patch.object(storage, '_decrypt_video_data', return_value=original_data) as mock_decrypt:
            # Get clip data
            result = await storage._get_clip_data(event_id)
            
            # Verify S3 calls
            storage.s3_client.head_object.assert_called_once_with(
                Bucket=storage.bucket_name, 
                Key=f"clips/{event_id}.mp4"
            )
            storage.s3_client.get_object.assert_called_once_with(
                Bucket=storage.bucket_name, 
                Key=f"clips/{event_id}.mp4"
            )
            
            # Verify decryption was called
            mock_decrypt.assert_called_once_with(encrypted_data)
            
            assert result == original_data
    
    @pytest.mark.asyncio
    async def test_get_clip_data_unencrypted(self, storage):
        """Test retrieving unencrypted clip data."""
        event_id = "test-event-unencrypted"
        video_data = b"unencrypted_video_data"
        
        # Mock S3 client responses for unencrypted data
        mock_head_response = {
            'Metadata': {
                'encrypted': 'false'
            }
        }
        
        mock_get_response = {
            'Body': Mock()
        }
        mock_get_response['Body'].read.return_value = video_data
        
        storage.s3_client.head_object.return_value = mock_head_response
        storage.s3_client.get_object.return_value = mock_get_response
        
        with patch.object(storage, '_decrypt_video_data') as mock_decrypt:
            # Get clip data
            result = await storage._get_clip_data(event_id)
            
            # Verify decryption was NOT called for unencrypted data
            mock_decrypt.assert_not_called()
            
            assert result == video_data
    
    @pytest.mark.asyncio
    async def test_get_clip_data_not_found(self, storage):
        """Test handling of non-existent clip data."""
        event_id = "non-existent-event"
        
        # Mock S3 client to raise NoSuchKey exception
        from botocore.exceptions import ClientError
        storage.s3_client.exceptions.NoSuchKey = ClientError
        storage.s3_client.head_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'HeadObject'
        )
        
        # Get clip data
        result = await storage._get_clip_data(event_id)
        
        assert result is None


class TestEncryptedLocalVideoStorage:
    """Test encrypted local video storage."""
    
    @pytest.fixture
    def storage(self):
        """Create an encrypted local storage instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = EncryptedLocalVideoStorage()
            storage.storage_path = temp_dir
            yield storage
    
    @pytest.mark.asyncio
    async def test_store_clip_with_encryption(self, storage):
        """Test storing a video clip with encryption."""
        event_id = "test-local-event"
        video_data = b"fake local video data"
        metadata = {"camera_id": "local-cam", "duration_seconds": 30}
        
        expected_url = f"file://{storage.storage_path}/{event_id}.mp4"
        
        with patch.object(storage.__class__.__bases__[1], 'store_clip', return_value=expected_url) as mock_parent, \
             patch.object(storage, '_encrypt_video_data', return_value=b"local_encrypted_data") as mock_encrypt:
            
            # Store the clip
            result = await storage.store_clip(event_id, video_data, metadata)
            
            # Verify encryption was called
            mock_encrypt.assert_called_once_with(video_data)
            
            # Verify parent method was called with encrypted data
            mock_parent.assert_called_once()
            call_args = mock_parent.call_args
            assert call_args[0][1] == b"local_encrypted_data"
            
            # Check metadata was updated
            call_metadata = call_args[0][2]
            assert call_metadata['encrypted'] is True
            assert call_metadata['encryption_method'] == 'AES-256-CBC'
            
            assert result == expected_url
    
    @pytest.mark.asyncio
    async def test_get_clip_data_encrypted(self, storage):
        """Test retrieving and decrypting encrypted local clip data."""
        event_id = "test-local-encrypted"
        encrypted_data = b"local_encrypted_video_data"
        original_data = b"local_original_video_data"
        
        # Create test files
        video_file = os.path.join(storage.storage_path, f"{event_id}.mp4")
        metadata_file = os.path.join(storage.storage_path, f"{event_id}.json")
        
        # Write encrypted video file
        with open(video_file, 'wb') as f:
            f.write(encrypted_data)
        
        # Write metadata file indicating encryption
        metadata = {
            "encrypted": True,
            "encryption_method": "AES-256-CBC",
            "camera_id": "local-cam"
        }
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        with patch.object(storage, '_decrypt_video_data', return_value=original_data) as mock_decrypt:
            # Get clip data
            result = await storage.get_clip_data(event_id)
            
            # Verify decryption was called
            mock_decrypt.assert_called_once_with(encrypted_data)
            
            assert result == original_data
    
    @pytest.mark.asyncio
    async def test_get_clip_data_unencrypted(self, storage):
        """Test retrieving unencrypted local clip data."""
        event_id = "test-local-unencrypted"
        video_data = b"local_unencrypted_video_data"
        
        # Create test files
        video_file = os.path.join(storage.storage_path, f"{event_id}.mp4")
        metadata_file = os.path.join(storage.storage_path, f"{event_id}.json")
        
        # Write unencrypted video file
        with open(video_file, 'wb') as f:
            f.write(video_data)
        
        # Write metadata file indicating no encryption
        metadata = {
            "encrypted": False,
            "camera_id": "local-cam"
        }
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        with patch.object(storage, '_decrypt_video_data') as mock_decrypt:
            # Get clip data
            result = await storage.get_clip_data(event_id)
            
            # Verify decryption was NOT called
            mock_decrypt.assert_not_called()
            
            assert result == video_data
    
    @pytest.mark.asyncio
    async def test_get_clip_data_not_found(self, storage):
        """Test handling of non-existent local clip data."""
        event_id = "non-existent-local-event"
        
        # Get clip data (files don't exist)
        result = await storage.get_clip_data(event_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_clip_data_no_metadata(self, storage):
        """Test retrieving clip data when metadata file is missing."""
        event_id = "test-no-metadata"
        video_data = b"video_data_without_metadata"
        
        # Create only video file (no metadata file)
        video_file = os.path.join(storage.storage_path, f"{event_id}.mp4")
        with open(video_file, 'wb') as f:
            f.write(video_data)
        
        with patch.object(storage, '_is_encrypted_data', return_value=False):
            # Get clip data
            result = await storage.get_clip_data(event_id)
            
            # Should return the data as-is (assume unencrypted)
            assert result == video_data
    
    @pytest.mark.asyncio
    async def test_get_clip_data_decryption_fallback(self, storage):
        """Test fallback when decryption fails."""
        event_id = "test-decrypt-fail"
        encrypted_data = b"data_that_fails_to_decrypt"
        
        # Create test files
        video_file = os.path.join(storage.storage_path, f"{event_id}.mp4")
        metadata_file = os.path.join(storage.storage_path, f"{event_id}.json")
        
        # Write video file
        with open(video_file, 'wb') as f:
            f.write(encrypted_data)
        
        # Write metadata indicating encryption
        metadata = {"encrypted": True}
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        with patch.object(storage, '_decrypt_video_data', side_effect=Exception("Decryption failed")):
            # Get clip data (should fallback to returning encrypted data)
            result = await storage.get_clip_data(event_id)
            
            # Should return encrypted data as fallback
            assert result == encrypted_data


class TestStorageFactory:
    """Test the storage factory function."""
    
    def test_get_encrypted_storage_s3(self):
        """Test factory returns encrypted S3 storage."""
        with patch.dict(os.environ, {'VIDEO_STORAGE_TYPE': 's3'}), \
             patch('vms_service.encrypted_storage.boto3.client'):
            
            storage = get_encrypted_storage()
            assert isinstance(storage, EncryptedS3VideoStorage)
    
    def test_get_encrypted_storage_local(self):
        """Test factory returns encrypted local storage."""
        with patch.dict(os.environ, {'VIDEO_STORAGE_TYPE': 'local'}):
            storage = get_encrypted_storage()
            assert isinstance(storage, EncryptedLocalVideoStorage)
    
    def test_get_encrypted_storage_default(self):
        """Test factory returns local storage by default."""
        with patch.dict(os.environ, {}, clear=True):
            storage = get_encrypted_storage()
            assert isinstance(storage, EncryptedLocalVideoStorage)


class TestIntegrationWithExistingStorage:
    """Test integration with existing storage backends."""
    
    def test_encrypted_storage_inherits_from_base(self):
        """Test that encrypted storage classes inherit from base storage classes."""
        # Check inheritance hierarchy
        assert issubclass(EncryptedS3VideoStorage, EncryptedVideoStorageMixin)
        
        # Should also inherit from original storage classes
        with patch('vms_service.encrypted_storage.boto3.client'):
            s3_storage = EncryptedS3VideoStorage()
            # Should have methods from both mixin and base S3 storage
            assert hasattr(s3_storage, '_encrypt_video_data')  # From mixin
            assert hasattr(s3_storage, 'bucket_name')  # From S3VideoStorage
        
        local_storage = EncryptedLocalVideoStorage()
        assert hasattr(local_storage, '_encrypt_video_data')  # From mixin
        assert hasattr(local_storage, 'storage_path')  # From LocalVideoStorage

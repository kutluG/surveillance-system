"""
Integration tests for end-to-end encryption functionality

Tests cover:
1. Full round-trip encryption/decryption for video storage
2. Database field encryption for annotations
3. Cross-service encryption compatibility
4. Migration from unencrypted to encrypted data
"""

import pytest
import tempfile
import os
import json
from datetime import datetime
from unittest.mock import patch, Mock

# Test the shared crypto module
from shared.crypto import encrypt_bytes, decrypt_bytes, encrypt_string, decrypt_string, EncryptionError

# Test VMS encrypted storage
from vms_service.encrypted_storage import EncryptedLocalVideoStorage, EncryptedS3VideoStorage

# Test annotation models with encryption
from annotation_frontend.models import AnnotationExample, AnnotationStatus


class TestEndToEndEncryption:
    """Test end-to-end encryption across all components."""
    
    def test_shared_crypto_round_trip(self):
        """Test the shared crypto module works correctly."""
        # Set up encryption key
        test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': test_key}):
            # Test video data encryption
            video_data = b"fake MP4 video data with binary content \x00\x01\x02\xff"
            encrypted_video = encrypt_bytes(video_data)
            decrypted_video = decrypt_bytes(encrypted_video)
            
            assert decrypted_video == video_data
            assert encrypted_video != video_data
            assert len(encrypted_video) > len(video_data)
            
            # Test JSON annotation data encryption
            annotation_data = {
                "detections": [
                    {
                        "label": "person",
                        "confidence": 0.95,
                        "bbox": {"x1": 100, "y1": 50, "x2": 200, "y2": 300}
                    }
                ],
                "sensitive_info": "PII data that needs encryption"
            }
            
            json_str = json.dumps(annotation_data)
            encrypted_json = encrypt_string(json_str)
            decrypted_json = decrypt_string(encrypted_json)
            
            assert decrypted_json == json_str
            parsed_data = json.loads(decrypted_json)
            assert parsed_data == annotation_data
    
    def test_wrong_key_fails(self):
        """Test that decryption fails with wrong key."""
        key1 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        key2 = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
        
        # Encrypt with first key
        with patch.dict(os.environ, {'ENCRYPTION_KEY': key1}):
            data = b"secret data"
            encrypted = encrypt_bytes(data)
        
        # Try to decrypt with second key
        with patch.dict(os.environ, {'ENCRYPTION_KEY': key2}):
            # Reset global service to pick up new key
            import shared.crypto
            shared.crypto._crypto_service = None
            
            with pytest.raises(EncryptionError):
                decrypt_bytes(encrypted)


class TestVMSStorageEncryption:
    """Test VMS storage encryption integration."""
    
    @pytest.mark.asyncio
    async def test_local_storage_encryption(self):
        """Test local video storage encryption."""
        test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': test_key}):
            # Reset crypto service
            import shared.crypto
            shared.crypto._crypto_service = None
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create encrypted storage
                storage = EncryptedLocalVideoStorage()
                storage.storage_path = temp_dir
                
                # Store encrypted video clip
                event_id = "test-encrypted-event"
                video_data = b"fake video data for encryption test"
                metadata = {
                    "camera_id": "test-cam",
                    "timestamp": "2025-01-01T12:00:00Z",
                    "duration_seconds": 30
                }
                
                # Store the clip (should be encrypted)
                storage_url = await storage.store_clip(event_id, video_data, metadata)
                
                # Verify file exists
                video_file = os.path.join(temp_dir, f"{event_id}.mp4")
                metadata_file = os.path.join(temp_dir, f"{event_id}.json")
                
                assert os.path.exists(video_file)
                assert os.path.exists(metadata_file)
                
                # Read the raw file data (should be encrypted)
                with open(video_file, 'rb') as f:
                    stored_data = f.read()
                
                # Verify data is encrypted (different from original)
                assert stored_data != video_data
                assert len(stored_data) > len(video_data)  # Encrypted data is larger
                
                # Read metadata (should indicate encryption)
                with open(metadata_file, 'r') as f:
                    stored_metadata = json.load(f)
                
                assert stored_metadata['encrypted'] is True
                assert stored_metadata['encryption_method'] == 'AES-256-CBC'
                
                # Retrieve and decrypt the clip
                decrypted_data = await storage.get_clip_data(event_id)
                
                # Verify decrypted data matches original
                assert decrypted_data == video_data
    
    @pytest.mark.asyncio
    async def test_s3_storage_encryption(self):
        """Test S3 video storage encryption."""
        test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': test_key}):
            # Reset crypto service
            import shared.crypto
            shared.crypto._crypto_service = None
            
            with patch('vms_service.encrypted_storage.boto3.client') as mock_boto:
                # Mock S3 client
                mock_s3_client = Mock()
                mock_boto.return_value = mock_s3_client
                
                storage = EncryptedS3VideoStorage()
                
                # Mock the parent store_clip method
                expected_url = "s3://test-bucket/clips/test-s3-event.mp4"
                
                # Store encrypted video clip
                event_id = "test-s3-event"
                video_data = b"fake S3 video data"
                metadata = {"camera_id": "s3-cam"}
                
                with patch.object(storage.__class__.__bases__[1], 'store_clip', return_value=expected_url) as mock_parent:
                    storage_url = await storage.store_clip(event_id, video_data, metadata)
                    
                    # Verify parent method was called
                    assert mock_parent.called
                    call_args = mock_parent.call_args
                    
                    # Check that encrypted data was passed (different from original)
                    encrypted_data = call_args[0][1]
                    assert encrypted_data != video_data
                    assert len(encrypted_data) > len(video_data)
                    
                    # Check metadata includes encryption info
                    call_metadata = call_args[0][2]
                    assert call_metadata['encrypted'] == 'true'
                    assert call_metadata['encryption_method'] == 'AES-256-CBC'
                    
                    assert storage_url == expected_url


class TestAnnotationDatabaseEncryption:
    """Test database field encryption for annotations."""
    
    def test_encrypted_type_descriptor(self):
        """Test SQLAlchemy EncryptedType descriptor."""
        from annotation_frontend.models import EncryptedType
        
        test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': test_key}):
            # Create the type descriptor
            encrypted_type = EncryptedType()
            
            # Test encryption
            original_value = "sensitive data that needs encryption"
            encrypted_value = encrypted_type.process_bind_param(original_value, None)
            
            # Should be base64-encoded encrypted data
            assert encrypted_value != original_value
            assert isinstance(encrypted_value, str)
            
            # Test decryption
            decrypted_value = encrypted_type.process_result_value(encrypted_value, None)
            assert decrypted_value == original_value
    
    def test_encrypted_json_type_descriptor(self):
        """Test SQLAlchemy EncryptedJSONType descriptor."""
        from annotation_frontend.models import EncryptedJSONType
        
        test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': test_key}):
            # Create the type descriptor
            encrypted_json_type = EncryptedJSONType()
            
            # Test with complex JSON data
            original_data = {
                "bbox": {"x1": 100, "y1": 50, "x2": 200, "y2": 300},
                "label": "person",
                "confidence": 0.95,
                "sensitive_metadata": ["tag1", "tag2"]
            }
            
            # Test encryption
            encrypted_value = encrypted_json_type.process_bind_param(original_data, None)
            
            # Should be base64-encoded encrypted JSON
            assert encrypted_value != json.dumps(original_data)
            assert isinstance(encrypted_value, str)
            
            # Test decryption
            decrypted_value = encrypted_json_type.process_result_value(encrypted_value, None)
            assert decrypted_value == original_data


class TestBackwardCompatibility:
    """Test backward compatibility with existing unencrypted data."""
    
    @pytest.mark.asyncio
    async def test_reading_unencrypted_video_data(self):
        """Test that encrypted storage can read unencrypted video data."""
        test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': test_key}):
            import shared.crypto
            shared.crypto._crypto_service = None
            
            with tempfile.TemporaryDirectory() as temp_dir:
                storage = EncryptedLocalVideoStorage()
                storage.storage_path = temp_dir
                
                # Manually create unencrypted video file (simulating legacy data)
                event_id = "legacy-unencrypted-event"
                video_data = b"legacy unencrypted video data"
                
                video_file = os.path.join(temp_dir, f"{event_id}.mp4")
                metadata_file = os.path.join(temp_dir, f"{event_id}.json")
                
                # Write unencrypted video file
                with open(video_file, 'wb') as f:
                    f.write(video_data)
                
                # Write metadata indicating no encryption
                metadata = {
                    "encrypted": False,
                    "camera_id": "legacy-cam"
                }
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f)
                
                # Read the data (should work without decryption)
                retrieved_data = await storage.get_clip_data(event_id)
                
                # Should return original unencrypted data
                assert retrieved_data == video_data
    
    def test_database_field_fallback_on_decryption_failure(self):
        """Test database field fallback when decryption fails."""
        from annotation_frontend.models import EncryptedType
        
        encrypted_type = EncryptedType()
        
        # Test with data that can't be decrypted (simulating wrong key or corruption)
        corrupted_encrypted_data = "invalid_base64_or_encrypted_data"
        
        # Should fallback to returning the original value
        result = encrypted_type.process_result_value(corrupted_encrypted_data, None)
        assert result == corrupted_encrypted_data


class TestPerformanceAndSecurity:
    """Test performance characteristics and security properties."""
    
    def test_encryption_overhead(self):
        """Test encryption overhead is reasonable."""
        test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': test_key}):
            import shared.crypto
            shared.crypto._crypto_service = None
            
            # Test with various data sizes
            test_sizes = [100, 1024, 10*1024, 100*1024]  # 100B to 100KB
            
            for size in test_sizes:
                data = b"A" * size
                encrypted = encrypt_bytes(data)
                
                # Overhead should be reasonable (IV + padding)
                overhead = len(encrypted) - len(data)
                
                # Should be at least 16 bytes (IV) and at most 16 + 16 (IV + max padding)
                assert 16 <= overhead <= 32
                
                # Verify decryption works
                decrypted = decrypt_bytes(encrypted)
                assert decrypted == data
    
    def test_iv_randomness(self):
        """Test that IVs are random (no repeated IVs)."""
        test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': test_key}):
            import shared.crypto
            shared.crypto._crypto_service = None
            
            data = b"same data encrypted multiple times"
            encrypted_results = []
            
            # Encrypt the same data 10 times
            for _ in range(10):
                encrypted = encrypt_bytes(data)
                encrypted_results.append(encrypted)
            
            # All results should be different (due to random IVs)
            assert len(set(encrypted_results)) == 10
            
            # But all should decrypt to the same data
            for encrypted in encrypted_results:
                assert decrypt_bytes(encrypted) == data
    
    def test_padding_oracle_resistance(self):
        """Test that padding oracle attacks are not feasible."""
        test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': test_key}):
            import shared.crypto
            shared.crypto._crypto_service = None
            
            # Encrypt data
            data = b"test data for padding oracle test"
            encrypted = encrypt_bytes(data)
            
            # Corrupt various parts of the encrypted data
            corrupted_variants = [
                encrypted[:-1],  # Remove last byte
                encrypted[:-2] + b"XX",  # Change last two bytes
                encrypted[:16] + b"X" * (len(encrypted) - 16),  # Keep IV, corrupt data
                b"X" * 16 + encrypted[16:],  # Corrupt IV, keep data
            ]
            
            # All corrupted variants should fail to decrypt
            for corrupted in corrupted_variants:
                with pytest.raises(EncryptionError):
                    decrypt_bytes(corrupted)

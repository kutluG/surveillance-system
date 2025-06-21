"""
Encrypted Video Storage Backends

This module extends the existing video storage backends to provide
transparent encryption for video clips at rest. It wraps the original
S3VideoStorage and LocalVideoStorage to encrypt video data before
storage and decrypt on retrieval.

Features:
- Transparent encryption/decryption of video file data
- AES-256-CBC encryption with per-file random IV
- Maintains compatibility with existing storage interfaces
- Preserves metadata and URL generation functionality
"""

import os
import base64
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .storage import VideoStorage, S3VideoStorage, LocalVideoStorage
from shared.crypto import encrypt_bytes, decrypt_bytes, EncryptionError

logger = logging.getLogger(__name__)


class EncryptedVideoStorageMixin:
    """Mixin to add encryption capabilities to video storage backends."""
    
    def _encrypt_video_data(self, video_data: bytes) -> bytes:
        """
        Encrypt video data using AES-256-CBC.
        
        Args:
            video_data: Raw video bytes to encrypt
            
        Returns:
            Encrypted video bytes
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            return encrypt_bytes(video_data)
        except EncryptionError as e:
            logger.error(f"Failed to encrypt video data: {e}")
            raise
    
    def _decrypt_video_data(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt video data using AES-256-CBC.
        
        Args:
            encrypted_data: Encrypted video bytes
            
        Returns:
            Decrypted video bytes
            
        Raises:
            EncryptionError: If decryption fails
        """
        try:
            return decrypt_bytes(encrypted_data)
        except EncryptionError as e:
            logger.error(f"Failed to decrypt video data: {e}")
            raise
    
    def _is_encrypted_data(self, data: bytes) -> bool:
        """
        Check if data appears to be encrypted (has minimum length for IV + content).
        
        Args:
            data: Bytes to check
            
        Returns:
            True if data appears encrypted, False otherwise
        """
        # Encrypted data should be at least 16 bytes (IV) + some content
        return len(data) >= 17  # 16 bytes IV + at least 1 byte content


class EncryptedS3VideoStorage(EncryptedVideoStorageMixin, S3VideoStorage):
    """S3 video storage with encryption at rest."""
    async def store_clip(self, event_id: str, video_data: bytes, metadata: Dict[str, Any]) -> str:
        """Store encrypted video clip in S3."""
        try:
            # Encrypt video data
            encrypted_data = self._encrypt_video_data(video_data)
            
            logger.info(f"Encrypted video data: {len(video_data)} -> {len(encrypted_data)} bytes")
            
            # Prepare S3 metadata with encryption info
            key = f"clips/{event_id}.mp4"
            s3_metadata = {
                'event-id': event_id,
                'camera-id': metadata.get('camera_id', ''),
                'timestamp': metadata.get('timestamp', ''),
                'duration': str(metadata.get('duration_seconds', 0)),
                'encrypted': 'true',
                'encryption-method': 'AES-256-CBC'
            }
            
            # Store encrypted data in S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=encrypted_data,
                ContentType='video/mp4',
                Metadata=s3_metadata
            )
            
            logger.info("Video clip stored", extra={"event_id": event_id, "key": key})
            return f"s3://{self.bucket_name}/{key}"
            
        except EncryptionError as e:
            logger.error(f"Encryption failed for event {event_id}: {e}")
            # Fallback: store unencrypted with warning
            logger.warning(f"Storing unencrypted video for event {event_id}")
            
            # Prepare S3 metadata without encryption
            key = f"clips/{event_id}.mp4"
            s3_metadata = {
                'event-id': event_id,
                'camera-id': metadata.get('camera_id', ''),
                'timestamp': metadata.get('timestamp', ''),
                'duration': str(metadata.get('duration_seconds', 0)),
                'encrypted': 'false'
            }
            
            # Store unencrypted data
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=video_data,
                ContentType='video/mp4',
                Metadata=s3_metadata
            )
            
            logger.info("Video clip stored", extra={"event_id": event_id, "key": key})
            return f"s3://{self.bucket_name}/{key}"
            
        except Exception as e:
            logger.error(f"Failed to store encrypted clip for event {event_id}: {e}")
            raise
    
    async def _get_clip_data(self, event_id: str) -> Optional[bytes]:
        """
        Retrieve and decrypt video clip data from S3.
        
        Args:
            event_id: Event ID to retrieve
            
        Returns:
            Decrypted video bytes or None if not found
        """
        try:
            key = f"clips/{event_id}.mp4"
            
            # Check if object exists and get metadata
            try:
                head_response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
                metadata = head_response.get('Metadata', {})
            except self.s3_client.exceptions.NoSuchKey:
                logger.warning(f"Video clip not found for event {event_id}")
                return None
            
            # Get object data
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            encrypted_data = response['Body'].read()
            
            # Check if data is encrypted
            is_encrypted = metadata.get('encrypted', 'false').lower() == 'true'
            
            if is_encrypted:
                try:
                    # Decrypt the data
                    decrypted_data = self._decrypt_video_data(encrypted_data)
                    logger.debug(f"Decrypted clip data: {len(encrypted_data)} -> {len(decrypted_data)} bytes")
                    return decrypted_data
                except EncryptionError as e:
                    logger.error(f"Failed to decrypt clip for event {event_id}: {e}")
                    # Return encrypted data as fallback
                    logger.warning(f"Returning encrypted data for event {event_id}")
                    return encrypted_data
            else:
                # Data is not encrypted
                return encrypted_data
                
        except Exception as e:
            logger.error(f"Failed to retrieve clip data for event {event_id}: {e}")
            return None


class EncryptedLocalVideoStorage(EncryptedVideoStorageMixin, LocalVideoStorage):
    """Local filesystem video storage with encryption at rest."""
    
    async def store_clip(self, event_id: str, video_data: bytes, metadata: Dict[str, Any]) -> str:
        """Store encrypted video clip locally."""
        try:
            # Add encryption metadata
            metadata = metadata.copy()
            metadata['encrypted'] = True
            metadata['encryption_method'] = 'AES-256-CBC'
            
            # Encrypt video data
            encrypted_data = self._encrypt_video_data(video_data)
            
            logger.info(f"Encrypted video data: {len(video_data)} -> {len(encrypted_data)} bytes")
            
            # Store encrypted data using parent method
            return await super().store_clip(event_id, encrypted_data, metadata)
            
        except EncryptionError as e:
            logger.error(f"Encryption failed for event {event_id}: {e}")
            # Fallback: store unencrypted with warning
            logger.warning(f"Storing unencrypted video for event {event_id}")
            metadata['encrypted'] = False
            return await super().store_clip(event_id, video_data, metadata)
        except Exception as e:
            logger.error(f"Failed to store encrypted clip for event {event_id}: {e}")
            raise
    
    async def get_clip_data(self, event_id: str) -> Optional[bytes]:
        """
        Retrieve and decrypt video clip data from local storage.
        
        Args:
            event_id: Event ID to retrieve
            
        Returns:
            Decrypted video bytes or None if not found
        """
        try:
            filename = f"{event_id}.mp4"
            filepath = os.path.join(self.storage_path, filename)
            metadata_path = os.path.join(self.storage_path, f"{event_id}.json")
            
            if not os.path.exists(filepath):
                logger.warning(f"Video clip not found for event {event_id}")
                return None
            
            # Read metadata to check encryption status
            metadata = {}
            if os.path.exists(metadata_path):
                import json
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse metadata for event {event_id}")
            
            # Read video file
            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            # Check if data is encrypted
            is_encrypted = metadata.get('encrypted', False)
            
            if is_encrypted:
                try:
                    # Decrypt the data
                    decrypted_data = self._decrypt_video_data(file_data)
                    logger.debug(f"Decrypted clip data: {len(file_data)} -> {len(decrypted_data)} bytes")
                    return decrypted_data
                except EncryptionError as e:
                    logger.error(f"Failed to decrypt clip for event {event_id}: {e}")
                    # Return encrypted data as fallback
                    logger.warning(f"Returning encrypted data for event {event_id}")
                    return file_data
            else:
                # Data is not encrypted, but check if it looks encrypted
                if self._is_encrypted_data(file_data):
                    logger.warning(f"Data appears encrypted but metadata says otherwise for event {event_id}")
                return file_data
                
        except Exception as e:
            logger.error(f"Failed to retrieve clip data for event {event_id}: {e}")
            return None


def get_encrypted_storage() -> VideoStorage:
    """Get configured encrypted video storage backend."""
    storage_type = os.getenv("VIDEO_STORAGE_TYPE", "local").lower()
    
    if storage_type == "s3":
        logger.info("Using encrypted S3 video storage")
        return EncryptedS3VideoStorage()
    else:
        logger.info("Using encrypted local video storage")
        return EncryptedLocalVideoStorage()

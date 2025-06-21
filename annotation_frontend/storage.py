"""
Storage Layer with Encryption

Handles secure storage and retrieval of files with transparent encryption.
Supports both local filesystem and S3-compatible storage backends.
"""

import os
import logging
import base64
from typing import Optional, Union
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception

from crypto import encrypt_bytes, decrypt_bytes, EncryptionError
from config import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Custom exception for storage operations."""
    pass


class EncryptedStorage:
    """Storage service with transparent encryption/decryption."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize storage service.
        
        Args:
            storage_path: Base path for file storage (for local storage)
        """
        self.storage_path = storage_path or getattr(settings, 'STORAGE_PATH', '/app/data')
        self._s3_client = None
        self._init_storage()
    
    def _init_storage(self):
        """Initialize storage backend."""
        if self._is_s3_path(self.storage_path):
            if not S3_AVAILABLE:
                raise StorageError("S3 storage requested but boto3 not available")
            self._init_s3()
        else:
            self._init_local_storage()
    
    def _init_s3(self):
        """Initialize S3 client."""
        try:
            self._s3_client = boto3.client('s3')
            logger.info("S3 storage initialized")
        except NoCredentialsError:
            logger.error("S3 credentials not found")
            raise StorageError("S3 credentials not configured")
        except Exception as e:
            logger.error(f"Failed to initialize S3: {e}")
            raise StorageError(f"S3 initialization failed: {e}")
    
    def _init_local_storage(self):
        """Initialize local filesystem storage."""
        try:
            Path(self.storage_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Local storage initialized at {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to create storage directory {self.storage_path}: {e}")
            raise StorageError(f"Local storage initialization failed: {e}")
    
    def _is_s3_path(self, path: str) -> bool:
        """Check if path is S3-based."""
        return path.startswith("s3://")
    
    def _parse_s3_path(self, path: str) -> tuple:
        """Parse S3 path into bucket and key."""
        if not path.startswith("s3://"):
            raise StorageError(f"Invalid S3 path: {path}")
        
        path = path[5:]  # Remove s3://
        parts = path.split("/", 1)
        if len(parts) != 2:
            raise StorageError(f"Invalid S3 path format: {path}")
        
        return parts[0], parts[1]
    
    def store_frame_data(self, frame_id: str, frame_data: Union[str, bytes]) -> str:
        """
        Store encrypted frame data.
        
        Args:
            frame_id: Unique identifier for the frame
            frame_data: Base64 encoded frame data or raw bytes
            
        Returns:
            Storage path/key for the stored data
            
        Raises:
            StorageError: If storage fails
        """
        try:
            # Convert base64 string to bytes if needed
            if isinstance(frame_data, str):
                try:
                    raw_bytes = base64.b64decode(frame_data)
                except Exception as e:
                    raise StorageError(f"Invalid base64 frame data: {e}")
            else:
                raw_bytes = frame_data
            
            if len(raw_bytes) == 0:
                logger.warning(f"Empty frame data for frame_id: {frame_id}")
                return ""
            
            # Encrypt the frame data
            encrypted_data = encrypt_bytes(raw_bytes)
            
            # Store the encrypted data
            storage_key = f"frames/{frame_id}.enc"
            self._store_bytes(storage_key, encrypted_data)
            
            logger.info(f"Stored encrypted frame data: {frame_id} ({len(raw_bytes)} -> {len(encrypted_data)} bytes)")
            return storage_key
            
        except EncryptionError as e:
            logger.error(f"Encryption failed for frame {frame_id}: {e}")
            raise StorageError(f"Frame encryption failed: {e}")
        except Exception as e:
            logger.error(f"Storage failed for frame {frame_id}: {e}")
            raise StorageError(f"Frame storage failed: {e}")
    
    def retrieve_frame_data(self, storage_key: str, as_base64: bool = True) -> Union[str, bytes]:
        """
        Retrieve and decrypt frame data.
        
        Args:
            storage_key: Storage path/key for the data
            as_base64: Whether to return as base64 string (default) or raw bytes
            
        Returns:
            Decrypted frame data as base64 string or raw bytes
            
        Raises:
            StorageError: If retrieval or decryption fails
        """
        try:
            if not storage_key:
                logger.warning("Empty storage key provided")
                return "" if as_base64 else b""
            
            # Retrieve encrypted data
            encrypted_data = self._retrieve_bytes(storage_key)
            
            if len(encrypted_data) == 0:
                logger.warning(f"Empty encrypted data for key: {storage_key}")
                return "" if as_base64 else b""
            
            # Decrypt the data
            raw_bytes = decrypt_bytes(encrypted_data)
            
            if as_base64:
                result = base64.b64encode(raw_bytes).decode('utf-8')
            else:
                result = raw_bytes
            
            logger.debug(f"Retrieved encrypted frame data: {storage_key} ({len(encrypted_data)} -> {len(raw_bytes)} bytes)")
            return result
            
        except EncryptionError as e:
            logger.error(f"Decryption failed for key {storage_key}: {e}")
            raise StorageError(f"Frame decryption failed: {e}")
        except Exception as e:
            logger.error(f"Retrieval failed for key {storage_key}: {e}")
            raise StorageError(f"Frame retrieval failed: {e}")
    
    def _store_bytes(self, key: str, data: bytes):
        """Store raw bytes to storage backend."""
        if self._is_s3_path(self.storage_path):
            self._store_s3(key, data)
        else:
            self._store_local(key, data)
    
    def _retrieve_bytes(self, key: str) -> bytes:
        """Retrieve raw bytes from storage backend."""
        if self._is_s3_path(self.storage_path):
            return self._retrieve_s3(key)
        else:
            return self._retrieve_local(key)
    
    def _store_local(self, key: str, data: bytes):
        """Store data to local filesystem."""
        file_path = Path(self.storage_path) / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'wb') as f:
                f.write(data)
        except Exception as e:
            raise StorageError(f"Local storage write failed: {e}")
    
    def _retrieve_local(self, key: str) -> bytes:
        """Retrieve data from local filesystem."""
        file_path = Path(self.storage_path) / key
        
        try:
            if not file_path.exists():
                raise StorageError(f"File not found: {file_path}")
            
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise StorageError(f"Local storage read failed: {e}")
    
    def _store_s3(self, key: str, data: bytes):
        """Store data to S3."""
        if not self._s3_client:
            raise StorageError("S3 client not initialized")
        
        bucket, s3_key = self._parse_s3_path(self.storage_path)
        full_key = f"{s3_key}/{key}" if s3_key else key
        
        try:
            self._s3_client.put_object(
                Bucket=bucket,
                Key=full_key,
                Body=data,
                ServerSideEncryption='AES256'  # Additional S3-level encryption
            )
        except ClientError as e:
            raise StorageError(f"S3 storage write failed: {e}")
    
    def _retrieve_s3(self, key: str) -> bytes:
        """Retrieve data from S3."""
        if not self._s3_client:
            raise StorageError("S3 client not initialized")
        
        bucket, s3_key = self._parse_s3_path(self.storage_path)
        full_key = f"{s3_key}/{key}" if s3_key else key
        
        try:
            response = self._s3_client.get_object(Bucket=bucket, Key=full_key)
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise StorageError(f"File not found in S3: {full_key}")
            raise StorageError(f"S3 storage read failed: {e}")
    
    def delete_frame_data(self, storage_key: str):
        """
        Delete stored frame data.
        
        Args:
            storage_key: Storage path/key for the data
        """
        try:
            if self._is_s3_path(self.storage_path):
                self._delete_s3(storage_key)
            else:
                self._delete_local(storage_key)
            
            logger.info(f"Deleted frame data: {storage_key}")
            
        except Exception as e:
            logger.error(f"Failed to delete frame data {storage_key}: {e}")
            raise StorageError(f"Frame deletion failed: {e}")
    
    def _delete_local(self, key: str):
        """Delete data from local filesystem."""
        file_path = Path(self.storage_path) / key
        
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            raise StorageError(f"Local storage delete failed: {e}")
    
    def _delete_s3(self, key: str):
        """Delete data from S3."""
        if not self._s3_client:
            raise StorageError("S3 client not initialized")
        
        bucket, s3_key = self._parse_s3_path(self.storage_path)
        full_key = f"{s3_key}/{key}" if s3_key else key
        
        try:
            self._s3_client.delete_object(Bucket=bucket, Key=full_key)
        except ClientError as e:
            raise StorageError(f"S3 storage delete failed: {e}")


# Global storage service instance
storage_service = EncryptedStorage()


def store_frame_data(frame_id: str, frame_data: Union[str, bytes]) -> str:
    """
    Convenience function to store encrypted frame data.
    
    Args:
        frame_id: Unique identifier for the frame
        frame_data: Base64 encoded frame data or raw bytes
        
    Returns:
        Storage path/key for the stored data
    """
    return storage_service.store_frame_data(frame_id, frame_data)


def retrieve_frame_data(storage_key: str, as_base64: bool = True) -> Union[str, bytes]:
    """
    Convenience function to retrieve encrypted frame data.
    
    Args:
        storage_key: Storage path/key for the data
        as_base64: Whether to return as base64 string or raw bytes
        
    Returns:
        Decrypted frame data
    """
    return storage_service.retrieve_frame_data(storage_key, as_base64)


def delete_frame_data(storage_key: str):
    """
    Convenience function to delete stored frame data.
    
    Args:
        storage_key: Storage path/key for the data
    """
    return storage_service.delete_frame_data(storage_key)

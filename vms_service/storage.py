"""
Video storage interface for managing video clips and metadata.
"""
import os
import boto3
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from shared.logging_config import get_logger, log_context

logger = get_logger("vms_service")

class VideoStorage(ABC):
    """Abstract base class for video storage backends."""
    
    @abstractmethod
    async def store_clip(self, event_id: str, video_data: bytes, metadata: Dict[str, Any]) -> str:
        """Store video clip and return storage URL."""
        pass
    
    @abstractmethod
    async def get_clip_url(self, event_id: str, expiry_minutes: int = 60) -> Optional[str]:
        """Generate signed URL for video clip access."""
        pass
    
    @abstractmethod
    async def delete_clip(self, event_id: str) -> bool:
        """Delete video clip from storage."""
        pass
    
    @abstractmethod
    async def list_clips(self, camera_id: str = None, start_date: datetime = None, end_date: datetime = None) -> list:
        """List available video clips with optional filters."""
        pass

class S3VideoStorage(VideoStorage):
    """AWS S3 video storage implementation."""
    
    def __init__(self):
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "surveillance-clips")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.s3_client = boto3.client(
            's3',
            region_name=self.aws_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
    
    async def store_clip(self, event_id: str, video_data: bytes, metadata: Dict[str, Any]) -> str:
        """Store video clip in S3."""
        try:
            key = f"clips/{event_id}.mp4"
            
            # Add metadata as S3 object metadata
            s3_metadata = {
                'event-id': event_id,
                'camera-id': metadata.get('camera_id', ''),
                'timestamp': metadata.get('timestamp', ''),
                'duration': str(metadata.get('duration_seconds', 0)),
            }
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=video_data,
                ContentType='video/mp4',
                Metadata=s3_metadata
            )
            
            logger.info("Video clip stored", extra={event_id=event_id, key=key})
            return f"s3://{self.bucket_name}/{key}"
            
        except Exception as e:
            logger.error("Failed to store video clip", event_id=event_id, error=str(e))
            raise
    
    async def get_clip_url(self, event_id: str, expiry_minutes: int = 60) -> Optional[str]:
        """Generate presigned URL for video clip."""
        try:
            key = f"clips/{event_id}.mp4"
            
            # Check if object exists
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            except self.s3_client.exceptions.NoSuchKey:
                logger.warning("Video clip not found", event_id=event_id)
                return None
            
            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiry_minutes * 60
            )
            
            logger.info("Generated presigned URL", extra={event_id=event_id, expiry_minutes=expiry_minutes})
            return url
            
        except Exception as e:
            logger.error("Failed to generate clip URL", event_id=event_id, error=str(e))
            return None
    
    async def delete_clip(self, event_id: str) -> bool:
        """Delete video clip from S3."""
        try:
            key = f"clips/{event_id}.mp4"
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info("Video clip deleted", extra={event_id=event_id})
            return True
            
        except Exception as e:
            logger.error("Failed to delete video clip", event_id=event_id, error=str(e))
            return False
    
    async def list_clips(self, camera_id: str = None, start_date: datetime = None, end_date: datetime = None) -> list:
        """List video clips with optional filters."""
        try:
            # List objects in clips/ prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="clips/"
            )
            
            clips = []
            for obj in response.get('Contents', []):
                # Get object metadata
                head_response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=obj['Key']
                )
                
                metadata = head_response.get('Metadata', {})
                obj_camera_id = metadata.get('camera-id', '')
                
                # Apply camera filter
                if camera_id and obj_camera_id != camera_id:
                    continue
                
                # Apply date filters
                obj_timestamp = metadata.get('timestamp')
                if obj_timestamp:
                    try:
                        obj_date = datetime.fromisoformat(obj_timestamp.replace('Z', '+00:00'))
                        if start_date and obj_date < start_date:
                            continue
                        if end_date and obj_date > end_date:
                            continue
                    except ValueError:
                        pass
                
                event_id = obj['Key'].replace('clips/', '').replace('.mp4', '')
                clips.append({
                    'event_id': event_id,
                    'camera_id': obj_camera_id,
                    'timestamp': obj_timestamp,
                    'size_bytes': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'duration_seconds': metadata.get('duration', '0'),                })
            
            logger.info("Listed video clips", extra={"count": len(clips), "camera_id": camera_id})
            return clips
            
        except Exception as e:
            logger.error("Failed to list video clips", error=str(e))
            return []

class LocalVideoStorage(VideoStorage):
    """Local filesystem video storage implementation."""
    
    def __init__(self):
        self.storage_path = os.getenv("LOCAL_STORAGE_PATH", "/data/clips")
        self.base_url = os.getenv("CLIP_BASE_URL", "http://localhost:8000/clips")
        os.makedirs(self.storage_path, exist_ok=True)
    
    async def store_clip(self, event_id: str, video_data: bytes, metadata: Dict[str, Any]) -> str:
        """Store video clip locally."""
        try:
            filename = f"{event_id}.mp4"
            filepath = os.path.join(self.storage_path, filename)
            
            with open(filepath, 'wb') as f:
                f.write(video_data)
            
            # Store metadata as companion JSON file
            metadata_path = os.path.join(self.storage_path, f"{event_id}.json")
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, default=str)
            
            logger.info("Video clip stored locally", extra={event_id=event_id, path=filepath})
            return f"file://{filepath}"
            
        except Exception as e:
            logger.error("Failed to store video clip locally", event_id=event_id, error=str(e))
            raise
    
    async def get_clip_url(self, event_id: str, expiry_minutes: int = 60) -> Optional[str]:
        """Generate URL for local video clip."""
        filename = f"{event_id}.mp4"
        filepath = os.path.join(self.storage_path, filename)
        
        if os.path.exists(filepath):
            return f"{self.base_url}/{filename}"
        else:
            logger.warning("Video clip not found locally", event_id=event_id)
            return None
    
    async def delete_clip(self, event_id: str) -> bool:
        """Delete local video clip."""
        try:
            filename = f"{event_id}.mp4"
            filepath = os.path.join(self.storage_path, filename)
            metadata_path = os.path.join(self.storage_path, f"{event_id}.json")
            
            if os.path.exists(filepath):
                os.remove(filepath)
            
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            
            logger.info("Video clip deleted locally", extra={event_id=event_id})
            return True
            
        except Exception as e:
            logger.error("Failed to delete local video clip", event_id=event_id, error=str(e))
            return False
    
    async def list_clips(self, camera_id: str = None, start_date: datetime = None, end_date: datetime = None) -> list:
        """List local video clips."""
        try:
            clips = []
            
            for filename in os.listdir(self.storage_path):
                if not filename.endswith('.mp4'):
                    continue
                
                event_id = filename.replace('.mp4', '')
                filepath = os.path.join(self.storage_path, filename)
                metadata_path = os.path.join(self.storage_path, f"{event_id}.json")
                
                # Load metadata if available
                metadata = {}
                if os.path.exists(metadata_path):
                    import json
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                    except json.JSONDecodeError:
                        pass
                
                obj_camera_id = metadata.get('camera_id', '')
                
                # Apply camera filter
                if camera_id and obj_camera_id != camera_id:
                    continue
                
                # Apply date filters
                obj_timestamp = metadata.get('timestamp')
                if obj_timestamp and start_date:
                    try:
                        obj_date = datetime.fromisoformat(obj_timestamp.replace('Z', '+00:00'))
                        if start_date and obj_date < start_date:
                            continue
                        if end_date and obj_date > end_date:
                            continue
                    except ValueError:
                        pass
                
                file_stats = os.stat(filepath)
                clips.append({
                    'event_id': event_id,
                    'camera_id': obj_camera_id,
                    'timestamp': obj_timestamp,
                    'size_bytes': file_stats.st_size,
                    'last_modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    'duration_seconds': metadata.get('duration_seconds', 0),
                })
            
            logger.info("Listed local video clips", extra={count=len(clips}), camera_id=camera_id)
            return clips
            
        except Exception as e:
            logger.error("Failed to list local video clips", error=str(e))
            return []

# Storage factory
def get_storage() -> VideoStorage:
    """Get configured video storage backend."""
    storage_type = os.getenv("VIDEO_STORAGE_TYPE", "local")
    
    if storage_type == "s3":
        return S3VideoStorage()
    elif storage_type == "local":
        return LocalVideoStorage()
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")

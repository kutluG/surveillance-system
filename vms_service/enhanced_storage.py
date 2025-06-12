"""
Enhanced storage service that integrates with the video_segments database table.

This service extends the basic storage functionality to track video clips
in the database for retention management.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .storage import VideoStorage, get_storage
from .models import VideoSegment, ClipMetadata, Base
from shared.logging_config import get_logger, log_context

logger = get_logger("vms_service")

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    os.getenv("DB_URL", "postgresql://surveillance_user:surveillance_pass_5487@postgres:5432/events_db")
)

# Create SQLAlchemy engine and session factory
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

class DatabaseTrackingStorage:
    """
    Storage wrapper that tracks video clips in the database.
    
    This class wraps the underlying storage implementation (S3 or local)
    and maintains database records for retention management.
    """
    
    def __init__(self, underlying_storage: VideoStorage = None):
        self.storage = underlying_storage or get_storage()
        
        # Ensure database tables exist
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Video segments database tables initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database tables: {e}")
    
    async def store_clip_with_tracking(
        self, 
        event_id: str, 
        video_data: bytes, 
        metadata: Dict[str, Any]
    ) -> str:
        """
        Store video clip and create database tracking record.
        
        Args:
            event_id: Event ID associated with the clip
            video_data: Video file data
            metadata: Clip metadata
            
        Returns:
            Storage URL of the stored clip
        """
        session = SessionLocal()
        
        try:
            with log_context(action="store_clip_with_tracking", event_id=event_id):
                # Store the video file using underlying storage
                storage_url = await self.storage.store_clip(event_id, video_data, metadata)
                
                # Extract file key from storage URL
                file_key = self._extract_file_key(storage_url, event_id)
                
                # Create video segment record
                video_segment = VideoSegment.from_clip_metadata(
                    event_id=event_id,
                    metadata=metadata,
                    file_key=file_key,
                    file_size=len(video_data)
                )
                
                session.add(video_segment)
                session.flush()  # Get the ID
                
                # Create additional metadata record
                clip_metadata = ClipMetadata(
                    video_segment_id=video_segment.id,
                    fps=metadata.get('fps', 15),
                    resolution_width=self._parse_resolution_width(metadata.get('resolution', '640x480')),
                    resolution_height=self._parse_resolution_height(metadata.get('resolution', '640x480')),
                    codec='mp4',
                    generated_by=metadata.get('generated_by', 'vms_service'),
                    processing_time_ms=metadata.get('processing_time_ms')
                )
                
                session.add(clip_metadata)
                session.commit()
                
                logger.info("Video clip stored and tracked in database", extra={
                    "action": "clip_stored",
                    "event_id": event_id,
                    "file_key": file_key,
                    "file_size": len(video_data),
                    "video_segment_id": str(video_segment.id)
                })
                
                return storage_url
                
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store clip with tracking: {e}", extra={
                "action": "store_clip_error",
                "event_id": event_id,
                "error": str(e)
            })
            raise
        finally:
            session.close()
    
    async def get_clip_url(self, event_id: str, expiry_minutes: int = 60) -> Optional[str]:
        """Get URL for video clip."""
        return await self.storage.get_clip_url(event_id, expiry_minutes)
    
    async def delete_clip_with_tracking(self, event_id: str) -> bool:
        """
        Delete video clip and remove database tracking records.
        
        Args:
            event_id: Event ID of the clip to delete
            
        Returns:
            True if successful, False otherwise
        """
        session = SessionLocal()
        
        try:
            with log_context(action="delete_clip_with_tracking", event_id=event_id):
                # Find video segment record
                video_segment = session.query(VideoSegment).filter_by(event_id=event_id).first()
                
                if not video_segment:
                    logger.warning(f"No video segment found for event {event_id}")
                    return await self.storage.delete_clip(event_id)
                
                # Delete from underlying storage
                storage_success = await self.storage.delete_clip(event_id)
                
                if storage_success:
                    # Delete database records (cascade will handle metadata)
                    session.delete(video_segment)
                    session.commit()
                    
                    logger.info("Video clip deleted and tracking removed", extra={
                        "action": "clip_deleted",
                        "event_id": event_id,
                        "file_key": video_segment.file_key
                    })
                
                return storage_success
                
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete clip with tracking: {e}", extra={
                "action": "delete_clip_error",
                "event_id": event_id,
                "error": str(e)
            })
            return False
        finally:
            session.close()
    
    async def list_clips(
        self, 
        camera_id: str = None, 
        start_date: datetime = None, 
        end_date: datetime = None
    ) -> list:
        """List video clips from database records."""
        session = SessionLocal()
        
        try:
            query = session.query(VideoSegment)
            
            # Apply filters
            if camera_id:
                query = query.filter(VideoSegment.camera_id == camera_id)
            
            if start_date:
                query = query.filter(VideoSegment.start_ts >= start_date)
            
            if end_date:
                query = query.filter(VideoSegment.end_ts <= end_date)
            
            # Order by creation time (newest first)
            query = query.order_by(VideoSegment.created_at.desc())
            
            video_segments = query.all()
            
            # Convert to list format
            clips = []
            for segment in video_segments:
                clips.append({
                    'event_id': str(segment.event_id),
                    'camera_id': segment.camera_id,
                    'file_key': segment.file_key,
                    'start_timestamp': segment.start_ts.isoformat() if segment.start_ts else None,
                    'end_timestamp': segment.end_ts.isoformat() if segment.end_ts else None,
                    'file_size': segment.file_size,
                    'created_at': segment.created_at.isoformat() if segment.created_at else None,
                })
            
            logger.info(f"Listed {len(clips)} video clips from database", extra={
                "action": "list_clips",
                "count": len(clips),
                "camera_id": camera_id
            })
            
            return clips
            
        except Exception as e:
            logger.error(f"Failed to list clips from database: {e}", extra={
                "action": "list_clips_error",
                "error": str(e)
            })
            # Fallback to underlying storage
            return await self.storage.list_clips(camera_id, start_date, end_date)
        finally:
            session.close()
    
    def get_retention_stats(self, retention_days: int) -> Dict[str, int]:
        """
        Get statistics about clips that would be affected by retention policy.
        
        Args:
            retention_days: Number of days for retention policy
            
        Returns:
            Dictionary with counts of clips to be removed
        """
        session = SessionLocal()
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # Count old segments
            old_segments_count = session.query(VideoSegment).filter(
                VideoSegment.end_ts < cutoff_date
            ).count()
            
            # Count total segments
            total_segments_count = session.query(VideoSegment).count()
            
            # Calculate total file size of old segments
            old_segments = session.query(VideoSegment).filter(
                VideoSegment.end_ts < cutoff_date
            ).all()
            
            total_old_size = sum(seg.file_size or 0 for seg in old_segments)
            
            return {
                "total_segments": total_segments_count,
                "segments_to_remove": old_segments_count,
                "segments_to_keep": total_segments_count - old_segments_count,
                "total_old_size_bytes": total_old_size,
                "cutoff_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get retention stats: {e}")
            return {
                "total_segments": 0,
                "segments_to_remove": 0,
                "segments_to_keep": 0,
                "total_old_size_bytes": 0,
                "cutoff_date": cutoff_date.isoformat(),
                "error": str(e)
            }
        finally:
            session.close()
    
    def _extract_file_key(self, storage_url: str, event_id: str) -> str:
        """Extract file key from storage URL."""
        if storage_url.startswith("s3://"):
            # S3 URL format: s3://bucket-name/path/to/file.mp4
            return storage_url.split("/", 3)[3] if "/" in storage_url[5:] else f"clips/{event_id}.mp4"
        elif storage_url.startswith("file://"):
            # Local file URL format: file:///path/to/file.mp4
            return os.path.basename(storage_url)
        else:
            # Fallback
            return f"clips/{event_id}.mp4"
    
    def _parse_resolution_width(self, resolution_str: str) -> int:
        """Parse width from resolution string like '640x480'."""
        try:
            return int(resolution_str.split('x')[0])
        except (ValueError, IndexError):
            return 640
    
    def _parse_resolution_height(self, resolution_str: str) -> int:
        """Parse height from resolution string like '640x480'."""
        try:
            return int(resolution_str.split('x')[1])
        except (ValueError, IndexError):
            return 480


# Factory function to get enhanced storage
def get_enhanced_storage() -> DatabaseTrackingStorage:
    """Get database-tracking storage instance."""
    return DatabaseTrackingStorage()

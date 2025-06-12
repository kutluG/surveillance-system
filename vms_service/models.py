"""
SQLAlchemy ORM models for VMS (Video Management System) service.

This module defines database models for tracking video clips and segments
that integrate with the retention service.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class VideoSegment(Base):
    """
    Model for video_segments table that tracks video clip files.
    This table is used by both VMS service and retention service.
    """
    __tablename__ = "video_segments"
    
    id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    event_id = Column(PgUUID(as_uuid=True), nullable=False)
    camera_id = Column(String(50), nullable=False)
    file_key = Column(String(500), nullable=False)  # Path/key to the video file
    start_ts = Column(DateTime, nullable=False)     # Start timestamp of the video segment
    end_ts = Column(DateTime, nullable=False)       # End timestamp of the video segment
    file_size = Column(Integer, nullable=True)      # File size in bytes
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<VideoSegment(id={self.id}, event_id={self.event_id}, file_key={self.file_key})>"
    
    @classmethod
    def from_clip_metadata(cls, event_id: str, metadata: Dict[str, Any], file_key: str, file_size: int = None):
        """
        Create a VideoSegment from clip metadata.
        
        Args:
            event_id: Event ID associated with the clip
            metadata: Clip metadata containing camera_id, timestamp, duration, etc.
            file_key: Storage path/key for the video file
            file_size: Size of the video file in bytes
        
        Returns:
            VideoSegment instance
        """
        # Parse timestamp from metadata
        timestamp_str = metadata.get('timestamp', datetime.utcnow().isoformat())
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        
        event_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        duration_seconds = metadata.get('duration_seconds', 30)
        
        # Calculate start and end timestamps based on event time and duration
        start_ts = event_timestamp - timedelta(seconds=duration_seconds // 2)
        end_ts = event_timestamp + timedelta(seconds=duration_seconds // 2)
        
        return cls(
            event_id=event_id,
            camera_id=metadata.get('camera_id', 'unknown'),
            file_key=file_key,
            start_ts=start_ts,
            end_ts=end_ts,
            file_size=file_size
        )


class ClipMetadata(Base):
    """
    Additional metadata for video clips beyond what's in video_segments.
    This table stores VMS-specific metadata.
    """
    __tablename__ = "clip_metadata"
    
    id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    video_segment_id = Column(
        PgUUID(as_uuid=True), 
        ForeignKey('video_segments.id', ondelete='CASCADE'),
        nullable=False
    )
    fps = Column(Integer, nullable=True)
    resolution_width = Column(Integer, nullable=True)
    resolution_height = Column(Integer, nullable=True)
    codec = Column(String(50), nullable=True)
    generated_by = Column(String(100), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)  # Time taken to generate clip
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to VideoSegment
    video_segment = relationship("VideoSegment", backref="metadata")
    
    def __repr__(self):
        return f"<ClipMetadata(id={self.id}, video_segment_id={self.video_segment_id})>"

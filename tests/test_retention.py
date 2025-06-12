"""
Tests for the Data Retention Service

Tests cover:
1. Database purging functionality with SQLite test database
2. File deletion for local filesystem mode
3. Edge cases and error handling
"""

import os
import pytest
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from retention_service.main import (
    VideoSegment, Base, purge_old_events, purge_old_video_segments,
    delete_file_from_storage, run_retention_job
)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    
    # Also create the events table for testing
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                camera_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                detections TEXT,
                activity TEXT,
                event_metadata TEXT
            )
        """))
        conn.commit()
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for file storage testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_events_data():
    """Sample events data for testing."""
    now = datetime.utcnow()
    return [
        {
            "id": "event-old-1",
            "timestamp": now - timedelta(days=40),  # Old
            "camera_id": "cam01",
            "event_type": "detection"
        },
        {
            "id": "event-old-2", 
            "timestamp": now - timedelta(days=35),  # Old
            "camera_id": "cam02",
            "event_type": "activity"
        },
        {
            "id": "event-new-1",
            "timestamp": now - timedelta(days=10),  # New
            "camera_id": "cam01",
            "event_type": "detection"
        },
        {
            "id": "event-new-2",
            "timestamp": now - timedelta(days=5),   # New
            "camera_id": "cam03",
            "event_type": "activity"
        }
    ]


@pytest.fixture
def sample_video_segments_data():
    """Sample video segments data for testing."""
    now = datetime.utcnow()
    return [
        {
            "id": "seg-old-1",
            "event_id": "event-old-1",
            "camera_id": "cam01",
            "file_key": "clips/old-video-1.mp4",
            "start_ts": now - timedelta(days=40, minutes=5),
            "end_ts": now - timedelta(days=40),  # Old
            "file_size": 1024000
        },
        {
            "id": "seg-old-2",
            "event_id": "event-old-2",
            "camera_id": "cam02", 
            "file_key": "clips/old-video-2.mp4",
            "start_ts": now - timedelta(days=35, minutes=5),
            "end_ts": now - timedelta(days=35),  # Old
            "file_size": 2048000
        },
        {
            "id": "seg-new-1",
            "event_id": "event-new-1",
            "camera_id": "cam01",
            "file_key": "clips/new-video-1.mp4",
            "start_ts": now - timedelta(days=10, minutes=5),
            "end_ts": now - timedelta(days=10),  # New
            "file_size": 1536000
        }
    ]


class TestRetentionService:
    """Test class for retention service functionality."""
    
    def test_purge_old_events(self, temp_db, sample_events_data):
        """Test that old events are purged while new events remain."""
        session = temp_db()
        
        # Insert sample events
        for event_data in sample_events_data:
            session.execute(text("""
                INSERT INTO events (id, timestamp, camera_id, event_type, detections, activity, event_metadata)
                VALUES (:id, :timestamp, :camera_id, :event_type, '', '', '{}')
            """), event_data)
        session.commit()
        
        # Verify initial count
        initial_count = session.execute(text("SELECT COUNT(*) FROM events")).scalar()
        assert initial_count == 4
        
        # Run purge with 30 days retention
        import asyncio
        deleted_count = asyncio.run(purge_old_events(session, 30))
        
        # Should delete 2 old events (40 and 35 days old)
        assert deleted_count == 2
        
        # Verify remaining events
        remaining_events = session.execute(text("""
            SELECT id FROM events ORDER BY timestamp
        """)).fetchall()
        
        remaining_ids = [row[0] for row in remaining_events]
        assert "event-new-1" in remaining_ids
        assert "event-new-2" in remaining_ids
        assert "event-old-1" not in remaining_ids
        assert "event-old-2" not in remaining_ids
        
        session.close()
    
    
    def test_purge_old_video_segments_with_files(self, temp_db, temp_storage_dir, sample_video_segments_data):
        """Test video segment purging with actual file deletion."""
        session = temp_db()
        
        # Create sample video files
        clips_dir = os.path.join(temp_storage_dir, "clips")
        os.makedirs(clips_dir, exist_ok=True)
        
        created_files = []
        for segment_data in sample_video_segments_data:
            file_path = os.path.join(temp_storage_dir, segment_data["file_key"])
            with open(file_path, 'wb') as f:
                f.write(b"fake video content")
            created_files.append(file_path)
            
            # Also create metadata files
            metadata_path = file_path.replace('.mp4', '.json')
            with open(metadata_path, 'w') as f:
                json.dump({"event_id": segment_data["event_id"]}, f)
            created_files.append(metadata_path)
        
        # Insert video segments into database
        for segment_data in sample_video_segments_data:
            segment = VideoSegment(**segment_data)
            session.add(segment)
        session.commit()
        
        # Verify initial state
        initial_count = session.query(VideoSegment).count()
        assert initial_count == 3
        
        for file_path in created_files:
            assert os.path.exists(file_path)
        
        # Run purge with 30 days retention
        import asyncio
        stats = asyncio.run(purge_old_video_segments(session, 30, temp_storage_dir))
        
        # Should delete 2 old segments
        assert stats["deleted_records"] == 2
        assert stats["deleted_files"] == 2
        assert stats["failed_files"] == 0
        
        # Verify database state
        remaining_segments = session.query(VideoSegment).all()
        assert len(remaining_segments) == 1
        assert remaining_segments[0].file_key == "clips/new-video-1.mp4"
        
        # Verify file deletion
        old_files = [
            os.path.join(temp_storage_dir, "clips/old-video-1.mp4"),
            os.path.join(temp_storage_dir, "clips/old-video-2.mp4"),
            os.path.join(temp_storage_dir, "clips/old-video-1.json"),
            os.path.join(temp_storage_dir, "clips/old-video-2.json")
        ]
        
        for file_path in old_files:
            assert not os.path.exists(file_path)
        
        # New files should remain
        new_files = [
            os.path.join(temp_storage_dir, "clips/new-video-1.mp4"),
            os.path.join(temp_storage_dir, "clips/new-video-1.json")
        ]
        
        for file_path in new_files:
            assert os.path.exists(file_path)
        
        session.close()
    
    
    def test_delete_file_from_local_storage(self, temp_storage_dir):
        """Test local file deletion functionality."""
        # Create test file
        test_file = os.path.join(temp_storage_dir, "test_video.mp4")
        metadata_file = os.path.join(temp_storage_dir, "test_video.json")
        
        with open(test_file, 'wb') as f:
            f.write(b"test video content")
        
        with open(metadata_file, 'w') as f:
            json.dump({"test": "metadata"}, f)
        
        assert os.path.exists(test_file)
        assert os.path.exists(metadata_file)
        
        # Test deletion
        import asyncio
        success = asyncio.run(delete_file_from_storage("test_video.mp4", temp_storage_dir))
        
        assert success
        assert not os.path.exists(test_file)
        assert not os.path.exists(metadata_file)  # Metadata should also be deleted
    
    
    def test_delete_nonexistent_file(self, temp_storage_dir):
        """Test deletion of non-existent file returns False."""
        import asyncio
        success = asyncio.run(delete_file_from_storage("nonexistent.mp4", temp_storage_dir))
        assert not success
    
    
    @patch('retention_service.main.get_s3_client')
    def test_delete_file_from_s3_storage(self, mock_get_s3_client):
        """Test S3 file deletion functionality."""
        # Mock S3 client
        mock_s3 = Mock()
        mock_get_s3_client.return_value = mock_s3
        
        import asyncio
        success = asyncio.run(delete_file_from_storage("clips/test_video.mp4", "s3://test-bucket"))
        
        assert success
        mock_s3.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="clips/test_video.mp4"
        )
    
    
    def test_video_segments_table_not_exists(self, temp_db):
        """Test behavior when video_segments table doesn't exist."""
        session = temp_db()
        
        # Drop the video_segments table
        session.execute(text("DROP TABLE IF EXISTS video_segments"))
        session.commit()
        
        import asyncio
        stats = asyncio.run(purge_old_video_segments(session, 30, "/tmp"))
          # Should return empty stats without error
        assert stats["deleted_records"] == 0
        assert stats["deleted_files"] == 0
        assert stats["failed_files"] == 0
        
        session.close()
    
    @patch.dict(os.environ, {
        "DB_URL": "sqlite:///:memory:",
        "STORAGE_PATH": "/tmp/test",
        "RETENTION_DAYS": "7"
    })
    @patch('retention_service.main.purge_old_events')
    @patch('retention_service.main.purge_old_video_segments')
    def test_run_retention_job(self, mock_purge_videos, mock_purge_events):
        """Test the main retention job execution."""
        # Mock the purge functions
        mock_purge_events.return_value = 5
        mock_purge_videos.return_value = {"deleted_records": 3, "deleted_files": 3, "failed_files": 0}
        
        # Mock SessionLocal
        with patch('retention_service.main.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
              # Need to mock the constants that were loaded at import time
            with patch('retention_service.main.RETENTION_DAYS', 7):
                with patch('retention_service.main.STORAGE_PATH', "/tmp/test"):
                    import asyncio
                    asyncio.run(run_retention_job())
                    
                    # Verify both purge functions were called
                    mock_purge_events.assert_called_once_with(mock_session, 7)
                    mock_purge_videos.assert_called_once_with(mock_session, 7, "/tmp/test")
                    
                    # Verify session was closed
                    mock_session.close.assert_called_once()
    
    
    def test_video_segment_model(self):
        """Test VideoSegment model creation and attributes."""
        now = datetime.utcnow()
        segment = VideoSegment(
            event_id="test-event-id",
            camera_id="cam01",
            file_key="clips/test.mp4",
            start_ts=now - timedelta(minutes=5),
            end_ts=now,
            file_size=1024000
        )
        
        assert segment.event_id == "test-event-id"
        assert segment.camera_id == "cam01"
        assert segment.file_key == "clips/test.mp4"
        assert segment.file_size == 1024000
        assert segment.created_at is not None  # Should be set by default


if __name__ == "__main__":
    pytest.main([__file__])

"""
Database migration to create video_segments table for the retention service.

This migration adds the video_segments table that tracks video clip files
and their metadata for the VMS (Video Management System).
"""

from sqlalchemy import text

# Migration version
VERSION = "004"
NAME = "add_video_segments_table"

# SQL to create the video_segments table
MIGRATION_SQL = """
-- Create video_segments table for tracking video clip files
CREATE TABLE IF NOT EXISTS video_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL,
    camera_id VARCHAR(50) NOT NULL,
    file_key VARCHAR(500) NOT NULL,  -- Path/key to the video file
    start_ts TIMESTAMP NOT NULL,     -- Start timestamp of the video segment
    end_ts TIMESTAMP NOT NULL,       -- End timestamp of the video segment  
    file_size INTEGER,               -- File size in bytes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Add indexes for performance
    CONSTRAINT video_segments_event_id_fkey FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Create indexes for efficient querying and retention cleanup
CREATE INDEX IF NOT EXISTS idx_video_segments_event_id ON video_segments(event_id);
CREATE INDEX IF NOT EXISTS idx_video_segments_camera_id ON video_segments(camera_id);
CREATE INDEX IF NOT EXISTS idx_video_segments_end_ts ON video_segments(end_ts);
CREATE INDEX IF NOT EXISTS idx_video_segments_file_key ON video_segments(file_key);

-- Add comments for documentation
COMMENT ON TABLE video_segments IS 'Tracks video clip files and their metadata for retention management';
COMMENT ON COLUMN video_segments.file_key IS 'Path or S3 key to the video file';
COMMENT ON COLUMN video_segments.start_ts IS 'Start timestamp of the video segment';
COMMENT ON COLUMN video_segments.end_ts IS 'End timestamp of the video segment - used for retention cleanup';
"""

def upgrade(connection):
    """Apply the migration."""
    connection.execute(text(MIGRATION_SQL))
    print(f"Migration {VERSION}_{NAME} applied successfully")

def downgrade(connection):
    """Reverse the migration."""
    downgrade_sql = """
    DROP INDEX IF EXISTS idx_video_segments_file_key;
    DROP INDEX IF EXISTS idx_video_segments_end_ts;
    DROP INDEX IF EXISTS idx_video_segments_camera_id;
    DROP INDEX IF EXISTS idx_video_segments_event_id;
    DROP TABLE IF EXISTS video_segments;
    """
    connection.execute(text(downgrade_sql))
    print(f"Migration {VERSION}_{NAME} rolled back successfully")

if __name__ == "__main__":
    import os
    from sqlalchemy import create_engine
    
    # Get database URL from environment
    db_url = os.getenv("DB_URL", "postgresql://surveillance_user:surveillance_pass_5487@localhost:5432/events_db")
    
    # Create engine and run migration
    engine = create_engine(db_url)
    with engine.connect() as conn:
        upgrade(conn)
        conn.commit()
    
    print("Video segments table migration completed!")

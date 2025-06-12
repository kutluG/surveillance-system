"""
Data Retention Service: automated cleanup of old database records and video files.

This service runs once per day to purge old records from the surveillance system:
- Deletes old events from the events table
- Deletes old video clip records from video_segments table (if it exists)
- Removes corresponding video files from storage (local FS or S3)
- Provides scheduling via APScheduler for daily execution at 02:00 AM
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

import boto3
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text, Column, String, DateTime, Integer
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.exc import SQLAlchemyError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import uuid

from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.middleware import add_rate_limiting

# Configure logging
logger = configure_logging("retention_service")

# Environment configuration
DB_URL = os.getenv("DB_URL", "postgresql://user:password@postgres:5432/events_db")
STORAGE_PATH = os.getenv("STORAGE_PATH", "/data/clips")
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))

# SQLAlchemy setup
engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()

# Create FastAPI app for health checks and manual triggers
app = FastAPI(
    title="Data Retention Service",
    openapi_prefix="/api/v1"
)
add_audit_middleware(app, service_name="retention_service")
instrument_app(app, service_name="retention_service")

# Add rate limiting middleware
add_rate_limiting(app, service_name="retention_service")

# Scheduler for daily execution
scheduler = AsyncIOScheduler()

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL UUID for PostgreSQL and CHAR(36) for SQLite.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PgUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, str):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, str):
                return str(value)
            return value

class VideoSegment(Base):
    """
    SQLAlchemy model for video_segments table.
    This table tracks video clip files and their metadata.
    """
    __tablename__ = "video_segments"
    
    id = Column(
        GUID(),
        primary_key=True,        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    event_id = Column(GUID(), nullable=False)
    camera_id = Column(String, nullable=False)
    file_key = Column(String, nullable=False)  # Path/key to the video file
    start_ts = Column(DateTime, nullable=False)
    end_ts = Column(DateTime, nullable=False)
    file_size = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.created_at:
            self.created_at = datetime.utcnow()


def is_s3_path(path: str) -> bool:
    """Check if the storage path is an S3 URI."""
    return path.startswith("s3://") or path.startswith("https://")


def get_s3_client():
    """Get configured S3 client."""
    return boto3.client(
        's3',
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )


async def delete_file_from_storage(file_key: str, storage_path: str) -> bool:
    """
    Delete a file from storage (local filesystem or S3).
    
    Args:
        file_key: The file path/key to delete
        storage_path: Base storage path (local dir or S3 bucket URI)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if is_s3_path(storage_path):
            # S3 storage
            parsed_url = urlparse(storage_path)
            bucket_name = parsed_url.netloc
            
            # Handle different S3 URI formats
            if storage_path.startswith("s3://"):
                bucket_name = storage_path.replace("s3://", "").split("/")[0]
            
            s3_client = get_s3_client()
            
            # Remove bucket prefix from file_key if present
            if file_key.startswith(bucket_name):
                s3_key = file_key[len(bucket_name):].lstrip("/")
            else:
                s3_key = file_key.lstrip("/")
            
            with log_context(action="delete_s3_file", bucket=bucket_name, key=s3_key):
                logger.info(f"Deleting S3 object: s3://{bucket_name}/{s3_key}")
                s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
                return True
                
        else:
            # Local filesystem
            import os
            full_path = os.path.join(storage_path, file_key)
            
            with log_context(action="delete_local_file", path=full_path):
                if os.path.exists(full_path):
                    logger.info(f"Deleting local file: {full_path}")
                    os.remove(full_path)
                    
                    # Also remove metadata file if it exists
                    metadata_path = full_path.replace(".mp4", ".json")
                    if os.path.exists(metadata_path):
                        os.remove(metadata_path)
                        logger.info(f"Deleted metadata file: {metadata_path}")
                    
                    return True
                else:
                    logger.warning(f"File not found: {full_path}")
                    return False
                    
    except Exception as e:
        logger.error(f"Failed to delete file {file_key}: {str(e)}", 
                    extra={"action": "delete_file_error", "file_key": file_key, "error": str(e)})
        return False


async def purge_old_events(session: Session, retention_days: int) -> int:
    """
    Delete old events from the events table.
    
    Args:
        session: Database session
        retention_days: Number of days to retain
        
    Returns:
        Number of deleted records
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    with log_context(action="purge_old_events", cutoff_date=cutoff_date.isoformat()):
        try:
            # Query to delete old events
            result = session.execute(
                text("DELETE FROM events WHERE timestamp < :cutoff_date"),
                {"cutoff_date": cutoff_date}
            )
            deleted_count = result.rowcount
            session.commit()
            
            logger.info(f"Deleted {deleted_count} old events", 
                       extra={"action": "purge_events", "deleted_count": deleted_count})
            return deleted_count
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to delete old events: {str(e)}", 
                        extra={"action": "purge_events_error", "error": str(e)})
            raise


async def purge_old_video_segments(session: Session, retention_days: int, storage_path: str) -> Dict[str, int]:
    """
    Delete old video segments and their corresponding files.
    
    Args:
        session: Database session
        retention_days: Number of days to retain
        storage_path: Base storage path
        
    Returns:
        Dictionary with counts of deleted records and files
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    stats = {"deleted_records": 0, "deleted_files": 0, "failed_files": 0}
    
    with log_context(action="purge_old_video_segments", cutoff_date=cutoff_date.isoformat()):
        try:            # Check if video_segments table exists (SQLite compatible)
            table_exists = session.execute(
                text("""
                    SELECT COUNT(name) FROM sqlite_master 
                    WHERE type='table' AND name='video_segments'
                """)
            ).scalar()
            
            if not table_exists:
                logger.info("video_segments table does not exist, skipping video purge")
                return stats
            
            # Query old video segments
            result = session.execute(
                text("""
                    SELECT file_key FROM video_segments 
                    WHERE end_ts < :cutoff_date
                """),
                {"cutoff_date": cutoff_date}
            )
            
            file_keys = [row[0] for row in result.fetchall()]
            logger.info(f"Found {len(file_keys)} old video segments to delete")
            
            # Delete files first
            for file_key in file_keys:
                deleted_at = datetime.utcnow().isoformat()
                success = await delete_file_from_storage(file_key, storage_path)
                
                if success:
                    stats["deleted_files"] += 1
                    logger.info("Video file deleted successfully", 
                               extra={"action": "purge_video", "file_key": file_key, "deleted_at": deleted_at})
                else:
                    stats["failed_files"] += 1
                    logger.error("Failed to delete video file", 
                                extra={"action": "purge_video_error", "file_key": file_key})
            
            # Delete database records
            if file_keys:
                result = session.execute(
                    text("DELETE FROM video_segments WHERE end_ts < :cutoff_date"),
                    {"cutoff_date": cutoff_date}
                )
                stats["deleted_records"] = result.rowcount
                session.commit()
                
                logger.info(f"Deleted {stats['deleted_records']} video segment records",
                           extra={"action": "purge_video_segments", "deleted_count": stats['deleted_records']})
            
            return stats
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to delete old video segments: {str(e)}", 
                        extra={"action": "purge_video_segments_error", "error": str(e)})
            raise


async def run_retention_job():
    """
    Main retention job that purges old data and files.
    """
    start_time = datetime.utcnow()
    
    with log_context(action="retention_job_start", retention_days=RETENTION_DAYS):
        logger.info(f"Starting data retention job - purging data older than {RETENTION_DAYS} days")
        
        try:
            session = SessionLocal()
            
            # Purge old events
            deleted_events = await purge_old_events(session, RETENTION_DAYS)
            
            # Purge old video segments and files
            video_stats = await purge_old_video_segments(session, RETENTION_DAYS, STORAGE_PATH)
            
            session.close()
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info("Data retention job completed successfully", extra={
                "action": "retention_job_complete",
                "duration_seconds": duration,
                "deleted_events": deleted_events,
                "deleted_video_records": video_stats["deleted_records"],
                "deleted_video_files": video_stats["deleted_files"],
                "failed_video_files": video_stats["failed_files"]
            })
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Data retention job failed: {str(e)}", extra={
                "action": "retention_job_error",
                "duration_seconds": duration,
                "error": str(e)
            })
            raise


# FastAPI endpoints
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "retention_service"}


@app.post("/api/v1/purge/run")
async def manual_purge():
    """Manually trigger the retention job."""
    try:
        await run_retention_job()
        return {"message": "Retention job completed successfully"}
    except Exception as e:
        logger.error(f"Manual purge failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Purge failed: {str(e)}")


@app.get("/api/v1/purge/status")
async def purge_status():
    """Get information about the retention configuration."""
    return {
        "retention_days": RETENTION_DAYS,
        "storage_path": STORAGE_PATH,
        "storage_type": "s3" if is_s3_path(STORAGE_PATH) else "local",
        "db_url": DB_URL.split('@')[-1] if '@' in DB_URL else "configured",  # Hide credentials
        "next_scheduled_run": "02:00 AM daily (server time)"
    }


async def startup_event():
    """Initialize scheduler on startup."""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Schedule daily job at 02:00 AM
    scheduler.add_job(
        run_retention_job,
        CronTrigger(hour=2, minute=0),  # 02:00 AM daily
        id="daily_retention_job",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Retention service started with daily job scheduled at 02:00 AM")


async def shutdown_event():
    """Cleanup on shutdown."""
    scheduler.shutdown()
    logger.info("Retention service shutdown completed")


# Event handlers
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


async def main():
    """Main entry point for standalone execution."""
    parser = argparse.ArgumentParser(description="Data Retention Service")
    parser.add_argument("--run-once", action="store_true", 
                       help="Run retention job once and exit")
    parser.add_argument("--port", type=int, default=8000,
                       help="Port for the FastAPI server")
    
    args = parser.parse_args()
    
    if args.run_once:
        # Run once and exit (for cron jobs)
        logger.info("Running retention job once")
        await run_retention_job()
        logger.info("Retention job completed, exiting")
    else:
        # Run as FastAPI server with scheduler
        import uvicorn
        await startup_event()
        logger.info(f"Starting retention service on port {args.port}")
        uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    asyncio.run(main())

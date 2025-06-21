"""
Data Subject Deletion Service - GDPR/CCPA Compliance endpoint for annotation_frontend
Handles data subject deletion requests for face_hash_id based data removal.
"""
import os
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import text

from auth import require_role, TokenData
from database import get_db
from rate_limiting import rate_limit_data_deletion, MAX_JSON_FIELD_SIZE

logger = logging.getLogger(__name__)

# Configuration
STORAGE_PATH = os.getenv("STORAGE_PATH", "/app/data")

def is_s3_path(path: str) -> bool:
    """Check if path is S3-based"""
    return path.startswith("s3://")

def get_s3_client():
    """Get S3 client for file operations"""
    import boto3
    return boto3.client('s3')

router = APIRouter(tags=["data-subject"])

class DataSubjectDeleteRequest(BaseModel):
    """Request model for data subject deletion"""
    face_hash_id: str = Field(..., description="64-character hexadecimal face hash ID")
    
    @validator('face_hash_id')
    def validate_face_hash_id(cls, v):
        if not isinstance(v, str):
            raise ValueError('face_hash_id must be a string')
        if len(v) != 64:
            raise ValueError('face_hash_id must be a 64-character hexadecimal string')
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('face_hash_id must be a 64-character hexadecimal string')
        return v.lower()

class DataSubjectDeleteResponse(BaseModel):
    """Response model for data subject deletion"""
    status: str
    face_hash_id: str
    events: int
    files: int
    message: str = "Data deletion completed successfully"

@router.post("/delete", response_model=DataSubjectDeleteResponse)
@rate_limit_data_deletion()
async def delete_data_subject_data(
    request: Request,
    delete_request: DataSubjectDeleteRequest = Body(..., max_length=MAX_JSON_FIELD_SIZE),
    current_user: TokenData = Depends(require_role("compliance_officer")),
    db: Session = Depends(get_db)
) -> DataSubjectDeleteResponse:
    """
    Delete all data associated with a face_hash_id for GDPR/CCPA compliance.
    
    This endpoint:
    1. Finds all events containing the face_hash_id in privacy metadata
    2. Deletes associated video segments and files
    3. Deletes the events themselves
    4. Returns a summary of deleted items
    
    Rate limited to 5 requests per hour per IP.
    Request body size limited to 4KB for individual fields.
    Requires 'compliance_officer' role for access.
    """
    logger.info(f"Data subject deletion request", face_hash_id=delete_request.face_hash_id, user_id=current_user.sub)
    
    try:
        # Find events with the face_hash_id in privacy metadata
        events_query = text("""
            SELECT id, event_metadata 
            FROM events 
            WHERE JSON_EXTRACT(event_metadata, '$.privacy.face_hashes') LIKE :face_hash_pattern
        """)
        
        face_hash_pattern = f'%"{delete_request.face_hash_id}"%'
        events_result = db.execute(events_query, {"face_hash_pattern": face_hash_pattern})
        matching_events = events_result.fetchall()
        
        if not matching_events:
            logger.info(f"No data found for face_hash_id", face_hash_id=delete_request.face_hash_id)
            return DataSubjectDeleteResponse(
                status="deleted",
                face_hash_id=delete_request.face_hash_id,
                events=0,
                files=0,
                message="No data found for the provided face_hash_id"
            )
        
        event_ids = [event.id for event in matching_events]
        logger.info(f"Found {len(event_ids)} events for deletion", event_ids=event_ids)
        
        # Find and delete video segments associated with these events
        segments_query = text("""
            SELECT file_key FROM video_segments 
            WHERE event_id IN :event_ids
        """)
        
        segments_result = db.execute(segments_query, {"event_ids": tuple(event_ids)})
        video_segments = segments_result.fetchall()
        
        files_deleted = 0
        
        # Delete files (S3 or local storage)
        for segment in video_segments:
            file_key = segment.file_key
            
            try:
                if is_s3_path(STORAGE_PATH):
                    # S3 deletion
                    s3_client = get_s3_client()
                    bucket_name = STORAGE_PATH.replace("s3://", "").split("/")[0]
                    s3_client.delete_object(Bucket=bucket_name, Key=file_key)
                    logger.info(f"Deleted S3 file", file_key=file_key, bucket=bucket_name)
                else:
                    # Local file deletion
                    file_path = os.path.join(STORAGE_PATH, file_key)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted local file", file_path=file_path)
                
                files_deleted += 1
                
            except Exception as e:
                logger.error(f"Failed to delete file", file_key=file_key, error=str(e))
                # Continue with database cleanup even if file deletion fails
        
        # Delete video segments from database
        if video_segments:
            delete_segments_query = text("""
                DELETE FROM video_segments 
                WHERE event_id IN :event_ids
            """)
            db.execute(delete_segments_query, {"event_ids": tuple(event_ids)})
        
        # Delete events from database
        delete_events_query = text("""
            DELETE FROM events 
            WHERE id IN :event_ids
        """)
        db.execute(delete_events_query, {"event_ids": tuple(event_ids)})
        
        # Commit all database changes
        db.commit()
        
        logger.info(
            f"Data subject deletion completed",
            face_hash_id=delete_request.face_hash_id,
            events_deleted=len(event_ids),
            files_deleted=files_deleted,
            user_id=current_user.sub
        )
        
        return DataSubjectDeleteResponse(
            status="deleted",
            face_hash_id=delete_request.face_hash_id,
            events=len(event_ids),
            files=files_deleted
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Data subject deletion failed", face_hash_id=delete_request.face_hash_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete data subject information"
        )

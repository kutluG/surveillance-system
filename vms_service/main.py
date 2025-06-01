"""
VMS (Video Management System) Service: handles video clip generation, storage, and retrieval.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from shared.logging import get_logger
from shared.metrics import instrument_app
from shared.models import CameraEvent

from storage import get_storage
from clip_generator import ClipGenerator

LOGGER = get_logger("vms_service")
app = FastAPI(title="VMS Service")
instrument_app(app, service_name="vms_service")

# Initialize components
storage = get_storage()
clip_generator = ClipGenerator()

class ClipGenerateRequest(BaseModel):
    event: dict  # CameraEvent as dict
    camera_url: Optional[str] = None

class ClipResponse(BaseModel):
    event_id: str
    clip_url: str
    metadata: dict

class ClipListResponse(BaseModel):
    clips: List[dict]
    total_count: int

@app.get("/health")
async def health():
    return {"status": "ok"}

async def generate_and_store_clip_task(
    event_id: str,
    camera_id: str,
    event_timestamp: datetime,
    camera_url: Optional[str] = None
):
    """Background task to generate and store video clip."""
    try:
        LOGGER.info("Starting clip generation task", event_id=event_id, camera_id=camera_id)
        
        # Generate video clip
        clip_data = await clip_generator.generate_clip(
            camera_id=camera_id,
            event_timestamp=event_timestamp,
            event_id=event_id,
            camera_url=camera_url
        )
        
        # Generate metadata
        metadata = await clip_generator.get_clip_metadata(
            event_id=event_id,
            camera_id=camera_id,
            duration_seconds=30  # Default duration
        )
        
        # Store clip
        storage_url = await storage.store_clip(event_id, clip_data, metadata)
        
        LOGGER.info("Clip generation completed", event_id=event_id, storage_url=storage_url)
        
    except Exception as e:
        LOGGER.error("Clip generation failed", event_id=event_id, error=str(e))

@app.post("/clips/generate", response_model=ClipResponse)
async def generate_clip(
    req: ClipGenerateRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate a video clip for the given event.
    """
    try:
        # Parse event
        event = CameraEvent.parse_obj(req.event)
        
        LOGGER.info("Clip generation requested", event_id=str(event.id), camera_id=event.camera_id)
        
        # Schedule background task
        background_tasks.add_task(
            generate_and_store_clip_task,
            str(event.id),
            event.camera_id,
            event.timestamp,
            req.camera_url
        )
        
        # Return immediate response with future clip URL
        clip_url = f"/clips/{event.id}"
        
        return ClipResponse(
            event_id=str(event.id),
            clip_url=clip_url,
            metadata={"status": "generating"}
        )
        
    except Exception as e:
        LOGGER.error("Failed to schedule clip generation", error=str(e))
        raise HTTPException(status_code=500, detail="Clip generation failed")

@app.get("/clips/{event_id}")
async def get_clip(event_id: str, expiry_minutes: int = 60):
    """
    Get a video clip by event ID. Returns a redirect to the actual clip URL.
    """
    try:
        clip_url = await storage.get_clip_url(event_id, expiry_minutes)
        
        if not clip_url:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        LOGGER.info("Clip URL generated", event_id=event_id, expiry_minutes=expiry_minutes)
        
        # Redirect to the actual clip URL
        return RedirectResponse(url=clip_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error("Failed to get clip URL", event_id=event_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve clip")

@app.get("/clips/{event_id}/url")
async def get_clip_url(event_id: str, expiry_minutes: int = 60):
    """
    Get the direct URL for a video clip without redirecting.
    """
    try:
        clip_url = await storage.get_clip_url(event_id, expiry_minutes)
        
        if not clip_url:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        return {"event_id": event_id, "clip_url": clip_url, "expires_in_minutes": expiry_minutes}
        
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error("Failed to get clip URL", event_id=event_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve clip URL")

@app.get("/clips", response_model=ClipListResponse)
async def list_clips(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(50, description="Maximum number of clips to return")
):
    """
    List available video clips with optional filters.
    """
    try:
        # Parse date filters
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Get clips from storage
        clips = await storage.list_clips(
            camera_id=camera_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        # Apply limit
        limited_clips = clips[:limit]
        
        LOGGER.info("Listed clips", count=len(limited_clips), total=len(clips), camera_id=camera_id)
        
        return ClipListResponse(
            clips=limited_clips,
            total_count=len(clips)
        )
        
    except Exception as e:
        LOGGER.error("Failed to list clips", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list clips")

@app.delete("/clips/{event_id}")
async def delete_clip(event_id: str):
    """
    Delete a video clip by event ID.
    """
    try:
        success = await storage.delete_clip(event_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        LOGGER.info("Clip deleted", event_id=event_id)
        return {"message": "Clip deleted successfully", "event_id": event_id}
        
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error("Failed to delete clip", event_id=event_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete clip")

@app.post("/clips/cleanup")
async def cleanup_old_clips(days_old: int = 30):
    """
    Delete clips older than specified number of days.
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # List all clips
        clips = await storage.list_clips()
        
        deleted_count = 0
        for clip in clips:
            try:
                clip_date = datetime.fromisoformat(clip['timestamp'].replace('Z', '+00:00'))
                if clip_date < cutoff_date:
                    await storage.delete_clip(clip['event_id'])
                    deleted_count += 1
            except (ValueError, KeyError):
                # Skip clips with invalid timestamps
                continue
        
        LOGGER.info("Cleanup completed", deleted_count=deleted_count, days_old=days_old)
        
        return {
            "message": f"Cleanup completed",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        LOGGER.error("Cleanup failed", error=str(e))
        raise HTTPException(status_code=500, detail="Cleanup failed")
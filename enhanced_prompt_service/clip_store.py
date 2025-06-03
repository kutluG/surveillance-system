"""
Enhanced clip store client for video URL generation with advanced features.
"""
import os
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

# Configuration
VMS_SERVICE_URL = os.getenv("VMS_SERVICE_URL", "http://vms-service:8000")
CLIP_BASE_URL = os.getenv("CLIP_BASE_URL", "https://cdn.example.com/clips")
DEFAULT_EXPIRY_MINUTES = int(os.getenv("DEFAULT_CLIP_EXPIRY_MINUTES", "60"))

def get_clip_url(
    event_id: str, 
    expiry_minutes: int = DEFAULT_EXPIRY_MINUTES,
    include_metadata: bool = False
) -> str:
    """
    Get URL for a video clip with enhanced features.
    
    Args:
        event_id: Event ID for the clip
        expiry_minutes: URL expiration time in minutes
        include_metadata: Whether to include additional metadata
    
    Returns:
        Clip URL or enhanced response with metadata
    """
    try:
        # Try to get clip URL from VMS service first
        vms_url = _get_clip_url_from_vms(event_id, expiry_minutes)
        if vms_url:
            if include_metadata:
                return {
                    "url": vms_url,
                    "event_id": event_id,
                    "expires_in_minutes": expiry_minutes,
                    "source": "vms_service",
                    "generated_at": datetime.utcnow().isoformat() + "Z"
                }
            return vms_url
    
    except Exception as e:
        print(f"Failed to get clip URL from VMS service: {e}")
    
    # Fallback to simple URL construction
    fallback_url = f"{CLIP_BASE_URL}/{event_id}.mp4"
    
    if include_metadata:
        return {
            "url": fallback_url,
            "event_id": event_id,
            "expires_in_minutes": expiry_minutes,
            "source": "fallback",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "warning": "Using fallback URL generation"
        }
    
    return fallback_url

def get_multiple_clip_urls(
    event_ids: List[str], 
    expiry_minutes: int = DEFAULT_EXPIRY_MINUTES
) -> Dict[str, str]:
    """
    Get URLs for multiple clips efficiently.
    
    Args:
        event_ids: List of event IDs
        expiry_minutes: URL expiration time in minutes
    
    Returns:
        Dictionary mapping event_id to clip URL
    """
    urls = {}
    
    for event_id in event_ids:
        try:
            url = get_clip_url(event_id, expiry_minutes)
            urls[event_id] = url
        except Exception as e:
            print(f"Failed to get URL for event {event_id}: {e}")
            # Provide fallback URL
            urls[event_id] = f"{CLIP_BASE_URL}/{event_id}.mp4"
    
    return urls

def get_clip_with_metadata(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Get clip URL along with comprehensive metadata.
    
    Args:
        event_id: Event ID for the clip
    
    Returns:
        Dictionary with URL and metadata, or None if not found
    """
    try:
        # Try to get metadata from VMS service
        response = requests.get(
            f"{VMS_SERVICE_URL}/clips/{event_id}",
            timeout=5
        )
        
        if response.status_code == 200:
            # If VMS service returns redirect or clip info
            if response.status_code == 302 or 'Location' in response.headers:
                clip_url = response.headers.get('Location') or response.url
            else:
                # Try to get direct URL
                url_response = requests.get(
                    f"{VMS_SERVICE_URL}/clips/{event_id}/url",
                    timeout=5
                )
                if url_response.status_code == 200:
                    url_data = url_response.json()
                    clip_url = url_data.get('clip_url')
                else:
                    clip_url = None
            
            if clip_url:
                return {
                    "event_id": event_id,
                    "clip_url": clip_url,
                    "available": True,
                    "source": "vms_service",
                    "metadata": {
                        "retrieved_at": datetime.utcnow().isoformat() + "Z",
                        "service_status": "available"
                    }
                }
    
    except Exception as e:
        print(f"Error getting clip metadata for {event_id}: {e}")
    
    # Return fallback with limited metadata
    return {
        "event_id": event_id,
        "clip_url": f"{CLIP_BASE_URL}/{event_id}.mp4",
        "available": False,  # Unknown availability
        "source": "fallback",
        "metadata": {
            "retrieved_at": datetime.utcnow().isoformat() + "Z",
            "service_status": "fallback",
            "warning": "Could not verify clip availability"
        }
    }

def check_clip_availability(event_id: str) -> bool:
    """
    Check if a clip is available without generating a full URL.
    
    Args:
        event_id: Event ID to check
    
    Returns:
        True if clip is available, False otherwise
    """
    try:
        # Use HEAD request to check existence
        response = requests.head(
            f"{VMS_SERVICE_URL}/clips/{event_id}",
            timeout=5
        )
        return response.status_code in [200, 302]  # 302 for redirect to actual clip
    
    except Exception as e:
        print(f"Error checking clip availability for {event_id}: {e}")
        return False

def get_clip_thumbnails(event_ids: List[str]) -> Dict[str, Optional[str]]:
    """
    Get thumbnail URLs for multiple clips.
    
    Args:
        event_ids: List of event IDs
    
    Returns:
        Dictionary mapping event_id to thumbnail URL (or None if not available)
    """
    thumbnails = {}
    
    for event_id in event_ids:
        try:
            # Try to get thumbnail from VMS or construct URL
            thumbnail_url = _get_thumbnail_url(event_id)
            thumbnails[event_id] = thumbnail_url
        except Exception as e:
            print(f"Failed to get thumbnail for {event_id}: {e}")
            thumbnails[event_id] = None
    
    return thumbnails

def generate_shareable_link(
    event_id: str, 
    expiry_hours: int = 24,
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Generate a shareable link for a clip with extended expiry.
    
    Args:
        event_id: Event ID for the clip
        expiry_hours: Link expiration time in hours
        include_metadata: Whether to include sharing metadata
    
    Returns:
        Dictionary with shareable link and metadata
    """
    try:
        # Get extended expiry URL
        clip_url = get_clip_url(event_id, expiry_hours * 60)
        
        share_link = {
            "event_id": event_id,
            "share_url": clip_url,
            "expires_at": (datetime.utcnow() + timedelta(hours=expiry_hours)).isoformat() + "Z",
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        if include_metadata:
            share_link["metadata"] = {
                "expiry_hours": expiry_hours,
                "share_type": "temporary_link",
                "access_level": "view_only"
            }
        
        return share_link
    
    except Exception as e:
        print(f"Error generating shareable link for {event_id}: {e}")
        return {
            "event_id": event_id,
            "share_url": None,
            "error": str(e),
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }

def get_clip_download_info(event_id: str) -> Dict[str, Any]:
    """
    Get information needed to download a clip.
    
    Args:
        event_id: Event ID for the clip
    
    Returns:
        Dictionary with download information
    """
    try:
        # Get clip URL and metadata
        clip_data = get_clip_with_metadata(event_id)
        
        if not clip_data or not clip_data.get("available"):
            return {
                "event_id": event_id,
                "downloadable": False,
                "reason": "Clip not available"
            }
        
        return {
            "event_id": event_id,
            "downloadable": True,
            "download_url": clip_data["clip_url"],
            "filename": f"clip_{event_id}.mp4",
            "metadata": clip_data.get("metadata", {}),
            "instructions": "Use the download_url to fetch the video file"
        }
    
    except Exception as e:
        return {
            "event_id": event_id,
            "downloadable": False,
            "reason": f"Error: {str(e)}"
        }

# Helper functions

def _get_clip_url_from_vms(event_id: str, expiry_minutes: int) -> Optional[str]:
    """Get clip URL from VMS service."""
    try:
        response = requests.get(
            f"{VMS_SERVICE_URL}/clips/{event_id}/url",
            params={"expiry_minutes": expiry_minutes},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("clip_url")
        
        return None
    
    except Exception as e:
        print(f"VMS service request failed: {e}")
        return None

def _get_thumbnail_url(event_id: str) -> Optional[str]:
    """Get thumbnail URL for a clip."""
    # Try VMS service first
    try:
        response = requests.get(
            f"{VMS_SERVICE_URL}/clips/{event_id}/thumbnail",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("thumbnail_url")
    
    except Exception:
        pass
    
    # Fallback to constructed URL
    thumbnail_base = os.getenv("THUMBNAIL_BASE_URL", f"{CLIP_BASE_URL}/thumbnails")
    return f"{thumbnail_base}/{event_id}.jpg"

def batch_check_availability(event_ids: List[str]) -> Dict[str, bool]:
    """
    Check availability of multiple clips efficiently.
    
    Args:
        event_ids: List of event IDs to check
    
    Returns:
        Dictionary mapping event_id to availability status
    """
    availability = {}
    
    # Try batch API if available
    try:
        response = requests.post(
            f"{VMS_SERVICE_URL}/clips/batch/check",
            json={"event_ids": event_ids},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("availability", {})
    
    except Exception as e:
        print(f"Batch availability check failed: {e}")
    
    # Fallback to individual checks
    for event_id in event_ids:
        availability[event_id] = check_clip_availability(event_id)
    
    return availability

def get_clip_streaming_url(event_id: str, quality: str = "auto") -> Optional[str]:
    """
    Get streaming URL for a clip with quality options.
    
    Args:
        event_id: Event ID for the clip
        quality: Video quality ("auto", "high", "medium", "low")
    
    Returns:
        Streaming URL or None if not available
    """
    try:
        response = requests.get(
            f"{VMS_SERVICE_URL}/clips/{event_id}/stream",
            params={"quality": quality},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("stream_url")
        
        # Fallback to regular clip URL
        return get_clip_url(event_id)
    
    except Exception as e:
        print(f"Error getting streaming URL for {event_id}: {e}")
        return get_clip_url(event_id)  # Fallback to regular URL

def get_related_clips(event_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get clips related to the given event.
    
    Args:
        event_id: Reference event ID
        limit: Maximum number of related clips
    
    Returns:
        List of related clip information
    """
    try:
        response = requests.get(
            f"{VMS_SERVICE_URL}/clips/{event_id}/related",
            params={"limit": limit},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            related_clips = []
            
            for clip in data.get("related_clips", []):
                clip_info = {
                    "event_id": clip.get("event_id"),
                    "clip_url": get_clip_url(clip.get("event_id")),
                    "relationship_type": clip.get("relationship_type"),
                    "similarity_score": clip.get("similarity_score", 0.0),
                    "timestamp": clip.get("timestamp"),
                    "camera_id": clip.get("camera_id")
                }
                related_clips.append(clip_info)
            
            return related_clips
    
    except Exception as e:
        print(f"Error getting related clips for {event_id}: {e}")
    
    return []

"""
Simple clip store client: generate URLs for stored video clips based on event IDs.
"""
import os

def get_clip_url(event_id: str) -> str:
    """
    Build a public URL for the given event's video clip.
    """
    base_url = os.getenv("CLIP_BASE_URL", "https://cdn.example.com/clips")
    return f"{base_url}/{event_id}.mp4"
import pytest
from datetime import datetime
from vms_service.clip_generator import ClipGenerator

@pytest.fixture
def clip_generator():
    return ClipGenerator()

@pytest.mark.asyncio
async def test_generate_clip_metadata(clip_generator):
    event_id = "test-event"
    camera_id = "cam01"
    duration = 30
    
    metadata = await clip_generator.get_clip_metadata(event_id, camera_id, duration)
    
    assert metadata["event_id"] == event_id
    assert metadata["camera_id"] == camera_id
    assert metadata["duration_seconds"] == duration
    assert metadata["fps"] == clip_generator.fps
    assert "timestamp" in metadata
    assert "resolution" in metadata

@pytest.mark.asyncio
async def test_create_synthetic_clip(clip_generator):
    event_id = "test-synthetic"
    
    # Generate synthetic clip
    clip_data = await clip_generator._create_synthetic_clip(event_id)
    
    assert isinstance(clip_data, bytes)
    assert len(clip_data) > 0
    
    # Basic check that it's a video file (MP4 signature)
    assert clip_data[:4] in [b'ftyp', b'\x00\x00\x00\x18'] or b'mp4' in clip_data[:100]

def test_get_camera_url(clip_generator):
    # Test environment variable fallback
    camera_id = "test-cam"
    url = clip_generator._get_camera_url(camera_id)
    
    # Should return fallback RTSP URL
    assert "rtsp://" in url
    assert camera_id in url
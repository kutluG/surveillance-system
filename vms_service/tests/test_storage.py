import pytest
import tempfile
import os
from datetime import datetime
from vms_service.storage import LocalVideoStorage, S3VideoStorage

@pytest.fixture
def temp_storage():
    """Create temporary directory for local storage tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = LocalVideoStorage()
        storage.storage_path = temp_dir
        yield storage

@pytest.mark.asyncio
async def test_local_storage_store_and_retrieve(temp_storage):
    event_id = "test-event-123"
    video_data = b"fake video data"
    metadata = {
        "camera_id": "cam01",
        "timestamp": "2025-05-31T10:30:00Z",
        "duration_seconds": 30
    }
    
    # Store clip
    storage_url = await temp_storage.store_clip(event_id, video_data, metadata)
    assert storage_url.startswith("file://")
    
    # Retrieve clip URL
    clip_url = await temp_storage.get_clip_url(event_id)
    assert clip_url is not None
    assert event_id in clip_url
    
    # Verify file exists
    expected_path = os.path.join(temp_storage.storage_path, f"{event_id}.mp4")
    assert os.path.exists(expected_path)
    
    # Verify file content
    with open(expected_path, 'rb') as f:
        stored_data = f.read()
    assert stored_data == video_data

@pytest.mark.asyncio
async def test_local_storage_list_clips(temp_storage):
    # Store multiple clips
    for i in range(3):
        event_id = f"event-{i}"
        metadata = {
            "camera_id": f"cam0{i}",
            "timestamp": f"2025-05-31T10:3{i}:00Z"
        }
        await temp_storage.store_clip(event_id, b"data", metadata)
    
    # List all clips
    clips = await temp_storage.list_clips()
    assert len(clips) == 3
    
    # List clips for specific camera
    clips = await temp_storage.list_clips(camera_id="cam01")
    assert len(clips) == 1
    assert clips[0]["camera_id"] == "cam01"

@pytest.mark.asyncio
async def test_local_storage_delete_clip(temp_storage):
    event_id = "test-delete"
    await temp_storage.store_clip(event_id, b"data", {"camera_id": "cam01"})
    
    # Verify clip exists
    clip_url = await temp_storage.get_clip_url(event_id)
    assert clip_url is not None
    
    # Delete clip
    success = await temp_storage.delete_clip(event_id)
    assert success
    
    # Verify clip no longer exists
    clip_url = await temp_storage.get_clip_url(event_id)
    assert clip_url is None

# Note: S3 tests would require mocking boto3 or using moto library
# For brevity, including just the structure here
def test_s3_storage_configuration():
    """Test S3 storage initialization."""
    storage = S3VideoStorage()
    assert storage.bucket_name is not None
    assert storage.aws_region is not None
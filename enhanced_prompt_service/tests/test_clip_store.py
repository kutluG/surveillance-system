"""
Integration tests for clip_store.py module.

Tests file system operations and URL generation with real temporary files.
"""
import os
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import pytest
import requests

# Add the project root to the path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clip_store import (
    get_clip_url,
    get_multiple_clip_urls,
    get_clip_with_metadata,
    check_clip_availability,
    get_clip_thumbnails,
    generate_shareable_link,
    get_clip_download_info,
    batch_check_availability,
    get_clip_streaming_url,
    get_related_clips
)


class TestClipStoreIntegration:
    """Integration tests for clip store operations."""
    
    @pytest.fixture
    def temp_clip_store(self):
        """Create a temporary clip store directory with sample clip files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample clip files
            clip_files = {
                "event_001": {"filename": "event_001.mp4", "size": 1024},
                "event_002": {"filename": "event_002.mp4", "size": 2048},
                "event_003": {"filename": "event_003.mp4", "size": 512}
            }
            
            for event_id, info in clip_files.items():
                clip_path = Path(temp_dir) / info["filename"]
                clip_path.write_bytes(b"dummy video content" * (info["size"] // 20))
            
            # Create metadata file
            metadata_file = Path(temp_dir) / "metadata.json"
            metadata = {
                "event_001": {
                    "camera_id": "cam_001",
                    "timestamp": "2025-06-18T10:30:00Z",
                    "duration": 30,
                    "resolution": "1920x1080"
                },
                "event_002": {
                    "camera_id": "cam_002", 
                    "timestamp": "2025-06-18T11:15:00Z",
                    "duration": 45,
                    "resolution": "1280x720"
                }
            }
            metadata_file.write_text(json.dumps(metadata))
            
            yield {
                "path": temp_dir,
                "files": clip_files,
                "metadata": metadata
            }

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for clip store tests."""
        return {
            "vms_service_url": "http://localhost:8001",
            "clip_base_url": "http://localhost:8001/clips",
            "default_clip_expiry_minutes": 60
        }

    @pytest.fixture
    def mock_vms_service(self):
        """Mock VMS service responses."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "clip_url": "http://localhost:8001/clips/event_001.mp4",
            "expires_at": "2025-06-18T12:30:00Z"
        }
        return mock_response

    @patch('clip_store.config')
    @patch('clip_store.requests.get')
    def test_get_clip_url_success(self, mock_get, mock_config_patch, mock_config, mock_vms_service):
        """Test successful clip URL retrieval."""
        # Setup mocks
        mock_config_patch.__getitem__.side_effect = mock_config.__getitem__
        mock_get.return_value = mock_vms_service
        
        # Test
        result = get_clip_url("event_001")
        
        # Assertions
        assert result == "http://localhost:8001/clips/event_001.mp4"
        mock_get.assert_called_once()

    @patch('clip_store.config')
    @patch('clip_store.requests.get')
    def test_get_clip_url_with_metadata(self, mock_get, mock_config_patch, mock_config, mock_vms_service):
        """Test clip URL retrieval with metadata."""
        # Setup mocks
        mock_config_patch.__getitem__.side_effect = mock_config.__getitem__
        mock_get.return_value = mock_vms_service
        
        # Test
        result = get_clip_url("event_001", include_metadata=True)
        
        # Assertions
        assert isinstance(result, dict)
        assert result["url"] == "http://localhost:8001/clips/event_001.mp4"
        assert result["event_id"] == "event_001"
        assert result["expires_in_minutes"] == 60
        assert result["source"] == "vms_service"
        assert "generated_at" in result

    @patch('clip_store.config')
    @patch('clip_store.requests.get')
    def test_get_clip_url_vms_failure(self, mock_get, mock_config_patch, mock_config):
        """Test clip URL retrieval when VMS service fails."""
        # Setup mocks
        mock_config_patch.__getitem__.side_effect = mock_config.__getitem__
        mock_get.side_effect = requests.exceptions.ConnectionError("Service unavailable")
        
        # Test
        result = get_clip_url("event_001")
        
        # Should fallback to direct URL generation
        assert result == "http://localhost:8001/clips/event_001.mp4"

    @patch('clip_store.config')
    def test_get_clip_url_missing_event(self, mock_config_patch, mock_config):
        """Test clip URL generation for missing event."""
        # Setup mocks
        mock_config_patch.__getitem__.side_effect = mock_config.__getitem__
        
        # Test
        result = get_clip_url("nonexistent_event")
        
        # Should still generate URL even if event doesn't exist
        assert result == "http://localhost:8001/clips/nonexistent_event.mp4"

    def test_get_multiple_clip_urls(self, temp_clip_store, mock_config):
        """Test retrieving multiple clip URLs."""
        with patch('clip_store.config', mock_config):
            with patch('clip_store._get_clip_url_from_vms') as mock_vms:
                mock_vms.side_effect = lambda event_id, _:f"http://localhost:8001/clips/{event_id}.mp4"
                
                event_ids = ["event_001", "event_002"]
                result = get_multiple_clip_urls(event_ids)
                
                assert len(result) == 2
                assert result["event_001"] == "http://localhost:8001/clips/event_001.mp4"
                assert result["event_002"] == "http://localhost:8001/clips/event_002.mp4"

    def test_check_clip_availability_file_exists(self, temp_clip_store):
        """Test clip availability check when file exists."""
        with patch('clip_store.config', {
            "vms_service_url": "http://localhost:8001",
            "clip_base_url": f"file://{temp_clip_store['path']}"
        }):
            # Mock the actual file check
            with patch('clip_store.os.path.exists', return_value=True):
                result = check_clip_availability("event_001")
                assert result is True

    def test_check_clip_availability_file_missing(self, temp_clip_store):
        """Test clip availability check when file is missing."""
        with patch('clip_store.config', {
            "vms_service_url": "http://localhost:8001", 
            "clip_base_url": f"file://{temp_clip_store['path']}"
        }):
            # Mock the actual file check
            with patch('clip_store.os.path.exists', return_value=False):
                result = check_clip_availability("nonexistent_event")
                assert result is False

    def test_get_clip_thumbnails(self, temp_clip_store, mock_config):
        """Test thumbnail URL generation."""
        with patch('clip_store.config', mock_config):
            with patch('clip_store._get_thumbnail_url') as mock_thumb:
                mock_thumb.side_effect = lambda event_id: f"http://localhost:8001/thumbnails/{event_id}.jpg"
                
                event_ids = ["event_001", "event_002"]
                result = get_clip_thumbnails(event_ids)
                
                assert len(result) == 2
                assert result["event_001"] == "http://localhost:8001/thumbnails/event_001.jpg"
                assert result["event_002"] == "http://localhost:8001/thumbnails/event_002.jpg"

    def test_generate_shareable_link(self, temp_clip_store, mock_config):
        """Test shareable link generation."""
        with patch('clip_store.config', mock_config):
            with patch('clip_store.get_clip_url', return_value="http://localhost:8001/clips/event_001.mp4"):
                result = generate_shareable_link("event_001", expiry_hours=24)
                
                assert isinstance(result, dict)
                assert "url" in result
                assert "expires_at" in result
                assert "event_id" in result
                assert result["event_id"] == "event_001"

    def test_get_clip_download_info(self, temp_clip_store, mock_config):
        """Test clip download info retrieval."""
        with patch('clip_store.config', mock_config):
            with patch('clip_store.get_clip_url', return_value="http://localhost:8001/clips/event_001.mp4"):
                result = get_clip_download_info("event_001")
                
                assert isinstance(result, dict)
                assert "download_url" in result
                assert "filename" in result
                assert "content_type" in result
                assert result["event_id"] == "event_001"

    def test_batch_check_availability(self, temp_clip_store, mock_config):
        """Test batch availability checking."""
        with patch('clip_store.config', mock_config):
            with patch('clip_store.check_clip_availability') as mock_check:
                mock_check.side_effect = lambda event_id: event_id in ["event_001", "event_002"]
                
                event_ids = ["event_001", "event_002", "event_999"]
                result = batch_check_availability(event_ids)
                
                assert len(result) == 3
                assert result["event_001"] is True
                assert result["event_002"] is True
                assert result["event_999"] is False

    def test_get_clip_streaming_url(self, temp_clip_store, mock_config):
        """Test streaming URL generation."""
        with patch('clip_store.config', mock_config):
            result = get_clip_streaming_url("event_001", quality="720p")
            
            assert result == "http://localhost:8001/clips/event_001.mp4?quality=720p"

    def test_get_related_clips(self, temp_clip_store, mock_config):
        """Test related clips retrieval."""
        with patch('clip_store.config', mock_config):
            with patch('clip_store.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "related_clips": [
                        {"event_id": "event_002", "similarity": 0.8},
                        {"event_id": "event_003", "similarity": 0.6}
                    ]
                }
                mock_get.return_value = mock_response
                
                result = get_related_clips("event_001", limit=2)
                
                assert len(result) == 2
                assert result[0]["event_id"] == "event_002"
                assert result[1]["event_id"] == "event_003"

    def test_error_handling_network_timeout(self, mock_config):
        """Test error handling for network timeouts."""
        with patch('clip_store.config', mock_config):
            with patch('clip_store.requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
                
                # Should fallback gracefully
                result = get_clip_url("event_001")
                assert result == "http://localhost:8001/clips/event_001.mp4"

    def test_error_handling_invalid_response(self, mock_config):
        """Test error handling for invalid VMS responses."""
        with patch('clip_store.config', mock_config):
            with patch('clip_store.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.json.side_effect = ValueError("Invalid JSON")
                mock_get.return_value = mock_response
                
                # Should fallback gracefully
                result = get_clip_url("event_001")
                assert result == "http://localhost:8001/clips/event_001.mp4"

    def test_custom_expiry_handling(self, mock_config):
        """Test custom expiry time handling."""
        with patch('clip_store.config', mock_config):
            with patch('clip_store._get_clip_url_from_vms') as mock_vms:
                mock_vms.return_value = "http://localhost:8001/clips/event_001.mp4"
                
                result = get_clip_url("event_001", expiry_minutes=120)
                
                mock_vms.assert_called_once_with("event_001", 120)
                assert result == "http://localhost:8001/clips/event_001.mp4"

    def test_metadata_inclusion_toggle(self, mock_config):
        """Test metadata inclusion toggle."""
        with patch('clip_store.config', mock_config):
            with patch('clip_store._get_clip_url_from_vms') as mock_vms:
                mock_vms.return_value = "http://localhost:8001/clips/event_001.mp4"
                
                # Without metadata
                result1 = get_clip_url("event_001", include_metadata=False)
                assert isinstance(result1, str)
                
                # With metadata
                result2 = get_clip_url("event_001", include_metadata=True)
                assert isinstance(result2, dict)
                assert "url" in result2
                assert "event_id" in result2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

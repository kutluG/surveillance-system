"""
Video clip generation from live camera streams.
"""
import os
import cv2
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from shared.logging import get_logger
import numpy as np 

LOGGER = get_logger("vms_service")

class ClipGenerator:
    """Generates video clips from camera streams around specific events."""
    
    def __init__(self):
        self.clip_duration = int(os.getenv("CLIP_DURATION_SECONDS", "30"))
        self.pre_event_buffer = int(os.getenv("PRE_EVENT_BUFFER_SECONDS", "10"))
        self.post_event_buffer = int(os.getenv("POST_EVENT_BUFFER_SECONDS", "20"))
        self.fps = int(os.getenv("CLIP_FPS", "15"))
        self.resolution = tuple(map(int, os.getenv("CLIP_RESOLUTION", "640,480").split(",")))
    
    async def generate_clip(
        self,
        camera_id: str,
        event_timestamp: datetime,
        event_id: str,
        camera_url: Optional[str] = None
    ) -> bytes:
        """
        Generate a video clip around the specified event time.
        
        Args:
            camera_id: ID of the camera
            event_timestamp: Timestamp when the event occurred
            event_id: Unique ID for the event
            camera_url: Optional URL to camera stream (if None, uses default)
        
        Returns:
            Video clip data as bytes
        """
        try:
            LOGGER.info("Generating video clip", event_id=event_id, camera_id=camera_id)
            
            # Calculate clip time range
            start_time = event_timestamp - timedelta(seconds=self.pre_event_buffer)
            end_time = event_timestamp + timedelta(seconds=self.post_event_buffer)
            
            # Get camera stream URL
            if not camera_url:
                camera_url = self._get_camera_url(camera_id)
            
            # Generate clip data
            clip_data = await self._capture_clip(
                camera_url,
                start_time,
                end_time,
                event_id
            )
            
            LOGGER.info("Video clip generated", event_id=event_id, size_bytes=len(clip_data))
            return clip_data
            
        except Exception as e:
            LOGGER.error("Failed to generate video clip", event_id=event_id, error=str(e))
            raise
    
    def _get_camera_url(self, camera_id: str) -> str:
        """Get stream URL for camera."""
        # In a real implementation, this would query a camera registry
        # For now, use environment variable pattern
        env_key = f"CAMERA_{camera_id.upper()}_URL"
        camera_url = os.getenv(env_key)
        
        if not camera_url:
            # Fallback to generic pattern
            camera_url = f"rtsp://admin:password@camera-{camera_id}:554/stream"
        
        return camera_url
    
    async def _capture_clip(
        self,
        camera_url: str,
        start_time: datetime,
        end_time: datetime,
        event_id: str
    ) -> bytes:
        """
        Capture video clip from camera stream.
        
        Note: This is a simplified implementation. In production, you would:
        1. Use a proper video storage system with rolling buffers
        2. Handle RTSP streams properly with ffmpeg
        3. Implement proper error handling and retries
        """
        try:
            # For demo purposes, create a synthetic video clip
            # In production, this would capture from actual camera streams
            return await self._create_synthetic_clip(event_id)
            
        except Exception as e:
            LOGGER.error("Failed to capture clip", event_id=event_id, error=str(e))
            raise
    
    async def _create_synthetic_clip(self, event_id: str) -> bytes:
        """Create a synthetic video clip for demo purposes."""
        import tempfile
        import os
        
        # Create temporary file for video
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(temp_path, fourcc, self.fps, self.resolution)
            
            # Generate frames
            total_frames = self.clip_duration * self.fps
            for frame_num in range(total_frames):
                # Create a simple test frame
                frame = self._create_test_frame(frame_num, event_id)
                writer.write(frame)
            
            writer.release()
            
            # Read the generated video file
            with open(temp_path, 'rb') as f:
                video_data = f.read()
            
            return video_data
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _create_test_frame(self, frame_num: int, event_id: str) -> 'np.ndarray':
        """Create a test frame for synthetic video."""
        import numpy as np
        
        # Create a blue background
        frame = np.full((self.resolution[1], self.resolution[0], 3), (100, 50, 0), dtype=np.uint8)
        
        # Add some text
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = f"Event: {event_id[:8]}"
        text_size = cv2.getTextSize(text, font, 0.7, 2)[0]
        text_x = (self.resolution[0] - text_size[0]) // 2
        text_y = (self.resolution[1] + text_size[1]) // 2
        
        cv2.putText(frame, text, (text_x, text_y), font, 0.7, (255, 255, 255), 2)
        
        # Add frame number
        frame_text = f"Frame: {frame_num}"
        cv2.putText(frame, frame_text, (10, 30), font, 0.5, (255, 255, 255), 1)
        
        # Add timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        cv2.putText(frame, timestamp, (10, self.resolution[1] - 10), font, 0.4, (255, 255, 255), 1)
        
        return frame

    async def get_clip_metadata(self, event_id: str, camera_id: str, duration_seconds: int) -> Dict[str, Any]:
        """Generate metadata for a video clip."""
        return {
            'event_id': event_id,
            'camera_id': camera_id,
            'duration_seconds': duration_seconds,
            'fps': self.fps,
            'resolution': f"{self.resolution[0]}x{self.resolution[1]}",
            'format': 'mp4',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'generated_by': 'vms_service',
        }
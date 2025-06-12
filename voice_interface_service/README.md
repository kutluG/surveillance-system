# Enhanced Voice Interface Service

A secure voice command processing service for the surveillance system with speaker verification capabilities.

## Features

- **Speaker Verification**: Uses pyannote.audio for speaker recognition
- **Secure Commands**: Only authorized speakers can execute system commands
- **Camera Control**: Enable/disable specific cameras via voice
- **Alert Configuration**: Set alert thresholds using voice commands
- **Multithreaded Processing**: Efficient audio processing using thread pools
- **Real-time Processing**: Fast speaker verification and command execution

## Installation

### Prerequisites

- Python 3.8+
- Redis server
- OpenAI API key (for Whisper transcription if needed)

### Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

### Setup Speaker Enrollment

To use speaker verification, you need to create an enrollment audio file:

1. **Create the secure directory**:
   ```bash
   mkdir -p /secure/voice_profile
   ```

2. **Record enrollment audio**:
   - Record at least 5 seconds of clear speech
   - Use 16 kHz sample rate, mono channel
   - Save as WAV format
   - Speak naturally in your normal voice
   - Include varied speech content (not just one phrase)

3. **Save the enrollment file**:
   ```bash
   # Save your recording as:
   /secure/voice_profile/enrollment.wav
   ```

4. **Example using FFmpeg** (if you have an existing audio file):
   ```bash
   ffmpeg -i your_voice_sample.wav -ar 16000 -ac 1 /secure/voice_profile/enrollment.wav
   ```

### Environment Variables

Set the following environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key"  # Optional, for Whisper fallback
export REDIS_URL="redis://localhost:6379/9"  # Redis connection
```

## API Endpoints

### Voice Command Processing

**POST /voice/command**

Process a voice command with speaker verification.

**Request Format**: `multipart/form-data`
- `audio_clip`: Base64-encoded WAV audio file
- `transcript`: Text transcript of the spoken command

**Example**:
```python
import base64
import requests

# Read your audio file
with open("command.wav", "rb") as f:
    audio_data = f.read()

# Encode as base64
audio_b64 = base64.b64encode(audio_data).decode('utf-8')

# Make request
response = requests.post(
    "http://localhost:8010/voice/command",
    data={
        "audio_clip": audio_b64,
        "transcript": "disable camera_3"
    }
)
```

**Response (Success)**:
```json
{
    "status": "success",
    "executed_command": "disable camera_3",
    "speaker_similarity": 0.87,
    "command_result": {
        "success": true,
        "action_taken": "disabled_camera_3",
        "details": {
            "camera_id": "3",
            "status": "disabled"
        }
    }
}
```

**Response (Speaker Not Recognized)**:
```json
{
    "error": "speaker_not_recognized"
}
```
HTTP Status: 403

### Supported Voice Commands

1. **Camera Control**:
   - `"disable camera_<id>"` - Disable specific camera
   - `"enable camera_<id>"` - Enable specific camera
   - Examples: "disable camera_3", "enable camera 12"

2. **Alert Configuration**:
   - `"set alert threshold to <number>"` - Set alert threshold
   - Examples: "set alert threshold to 75", "set alert threshold to 0.8"

### System Endpoints

**GET /voice/enrollment/status**

Check enrollment and system status.

```json
{
    "enrolled": true,
    "enrollment_file_exists": true,
    "model_loaded": true
}
```

**POST /voice/enrollment/reload**

Reload the enrollment embedding from file.

**GET /health**

Health check endpoint.

## Security Features

### Speaker Verification

- **Threshold**: Cosine similarity ≥ 0.75 required for verification
- **Model**: Uses pyannote/speaker-verification pretrained model
- **Processing**: All audio processing happens in background threads
- **Storage**: Embeddings stored in memory and Redis for persistence

### Command Authorization

- Commands only executed after successful speaker verification
- Unauthorized access attempts are logged and rejected
- Sensitive system operations require voice biometric confirmation

## Configuration

### Similarity Threshold

The default similarity threshold is 0.75. To adjust:

```python
# In voice_service.py
SIMILARITY_THRESHOLD = 0.80  # Stricter verification
```

### Thread Pool Size

Adjust the number of worker threads for audio processing:

```python
# In voice_service.py
THREAD_POOL_SIZE = 4  # More concurrent processing
```

## Running the Service

### Development

```bash
python voice_service.py
```

### Production

```bash
uvicorn voice_service:app --host 0.0.0.0 --port 8010 --workers 1
```

### Docker

```bash
docker build -t voice-service .
docker run -p 8010:8010 \
    -v /secure/voice_profile:/secure/voice_profile \
    -e OPENAI_API_KEY=your-key \
    voice-service
```

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest test_voice_service.py -v

# Run specific test categories
pytest test_voice_service.py::TestSpeakerVerification -v
pytest test_voice_service.py::TestVoiceCommandProcessor -v
pytest test_voice_service.py::TestVoiceServiceAPI -v
```

### Test Coverage

The test suite includes:

- **Speaker Verification Tests**: Embedding extraction, similarity calculation
- **Command Processing Tests**: All supported voice commands
- **API Integration Tests**: Full request/response cycle testing
- **Security Tests**: Unauthorized access attempt handling
- **Error Handling Tests**: Various failure scenarios

## Troubleshooting

### Common Issues

1. **Enrollment file not found**:
   ```
   Error: Enrollment file not found at /secure/voice_profile/enrollment.wav
   ```
   - Solution: Create enrollment audio file as described above

2. **Speaker verification failing**:
   ```
   Error: speaker_not_recognized
   ```
   - Solution: Re-record enrollment with clearer audio
   - Check audio quality and background noise
   - Ensure consistent speaking style

3. **Model loading errors**:
   ```
   Error: Failed to load speaker verification model
   ```
   - Solution: Install pyannote.audio correctly
   - Check internet connection for model download
   - Verify Python version compatibility

4. **Redis connection issues**:
   ```
   Error: Redis connection failed
   ```
   - Solution: Start Redis server
   - Check Redis URL configuration
   - Verify Redis authentication if required

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

Check enrollment status:
```bash
curl http://localhost:8010/voice/enrollment/status
```

Reload enrollment:
```bash
curl -X POST http://localhost:8010/voice/enrollment/reload
```

## Performance Considerations

- **Audio Processing**: Runs in separate threads to avoid blocking
- **Memory Usage**: Embeddings cached in memory for fast verification
- **Redis Storage**: Persistent embedding storage for service restarts
- **Model Loading**: One-time initialization at startup

## Security Best Practices

1. **Secure Storage**: Keep enrollment files in protected directories
2. **Access Control**: Limit access to enrollment endpoints
3. **Audit Logging**: All verification attempts are logged
4. **Threshold Tuning**: Adjust similarity threshold based on security needs
5. **Regular Re-enrollment**: Periodic re-recording for better accuracy

## Integration

### API Gateway Integration

The service integrates with the surveillance system API Gateway:
- Camera control: `POST /api/camera/{id}/enable|disable`
- Alert configuration: `POST /api/config/alert_threshold`

### Mobile App Integration

For mobile app integration, use the multipart form API:

```javascript
const formData = new FormData();
formData.append('audio_clip', base64AudioData);
formData.append('transcript', transcriptText);

fetch('/voice/command', {
    method: 'POST',
    body: formData
});
```

## License

Part of the surveillance system project. See main project license.

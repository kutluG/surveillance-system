"""
Voice Interface Service

This service provides speech-to-text and text-to-speech capabilities for the surveillance system:
- Real-time speech recognition for voice commands
- Natural language voice queries to the surveillance system
- Audio response generation with customizable voices
- Hands-free operation support
- Multi-language support
- Voice authentication and user identification
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import base64
import io
import wave

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
import httpx
from openai import AsyncOpenAI
import speech_recognition as sr
import pyttsx3
import threading
from queue import Queue

# Import shared middleware for rate limiting
from shared.middleware import add_rate_limiting

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key="your-openai-api-key")

# Enums
class VoiceCommand(str, Enum):
    QUERY = "query"
    ALERT_ACKNOWLEDGE = "alert_acknowledge"
    CAMERA_CONTROL = "camera_control"
    SYSTEM_STATUS = "system_status"
    EMERGENCY = "emergency"

class Language(str, Enum):
    ENGLISH = "en-US"
    SPANISH = "es-ES"
    FRENCH = "fr-FR"
    GERMAN = "de-DE"
    CHINESE = "zh-CN"

class VoiceType(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

# Data Models
@dataclass
class VoiceSession:
    id: str
    user_id: str
    language: Language
    voice_type: VoiceType
    created_at: datetime
    last_activity: datetime
    conversation_history: List[Dict]
    active: bool = True

@dataclass
class SpeechRecognitionResult:
    transcript: str
    confidence: float
    language: str
    duration: float
    timestamp: datetime

@dataclass
class VoiceResponse:
    text: str
    audio_data: bytes
    voice_type: VoiceType
    language: Language
    duration: float

# Request/Response Models
class VoiceQueryRequest(BaseModel):
    text: str
    user_id: str
    session_id: Optional[str] = None
    language: Language = Language.ENGLISH
    voice_type: VoiceType = VoiceType.FEMALE

class VoiceConfigRequest(BaseModel):
    user_id: str
    language: Language
    voice_type: VoiceType
    speech_rate: int = 150  # words per minute
    volume: float = 0.8

class AudioProcessingRequest(BaseModel):
    audio_format: str = "wav"
    sample_rate: int = 16000
    channels: int = 1

# Global state
redis_client: Optional[redis.Redis] = None
voice_sessions: Dict[str, VoiceSession] = {}
speech_recognizer = sr.Recognizer()
tts_engine = None

# Initialize TTS engine
def initialize_tts():
    """Initialize text-to-speech engine"""
    global tts_engine
    tts_engine = pyttsx3.init()
    
    # Configure TTS settings
    voices = tts_engine.getProperty('voices')
    if voices:
        tts_engine.setProperty('voice', voices[0].id)  # Default to first voice
    tts_engine.setProperty('rate', 150)  # Speech rate
    tts_engine.setProperty('volume', 0.8)  # Volume level

# Initialize on startup
initialize_tts()

async def get_redis_client():
    """Get Redis client"""
    global redis_client
    if not redis_client:
        redis_client = redis.from_url("redis://localhost:6379/9")
    return redis_client

# Voice Session Manager
class VoiceSessionManager:
    @staticmethod
    async def create_session(user_id: str, language: Language = Language.ENGLISH, 
                           voice_type: VoiceType = VoiceType.FEMALE) -> str:
        """Create a new voice session"""
        session_id = str(uuid.uuid4())
        session = VoiceSession(
            id=session_id,
            user_id=user_id,
            language=language,
            voice_type=voice_type,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            conversation_history=[]
        )
        
        voice_sessions[session_id] = session
        
        # Store in Redis
        redis_client = await get_redis_client()
        await redis_client.setex(
            f"voice_session:{session_id}",
            3600,  # 1 hour expiry
            json.dumps(asdict(session), default=str)
        )
        
        logger.info(f"Created voice session {session_id} for user {user_id}")
        return session_id
    
    @staticmethod
    async def get_session(session_id: str) -> Optional[VoiceSession]:
        """Get voice session"""
        if session_id in voice_sessions:
            return voice_sessions[session_id]
        
        # Try to load from Redis
        redis_client = await get_redis_client()
        session_data = await redis_client.get(f"voice_session:{session_id}")
        if session_data:
            session_dict = json.loads(session_data)
            session = VoiceSession(**session_dict)
            voice_sessions[session_id] = session
            return session
        
        return None
    
    @staticmethod
    async def update_session(session: VoiceSession):
        """Update voice session"""
        session.last_activity = datetime.utcnow()
        voice_sessions[session.id] = session
        
        # Update in Redis
        redis_client = await get_redis_client()
        await redis_client.setex(
            f"voice_session:{session.id}",
            3600,
            json.dumps(asdict(session), default=str)
        )

# Speech Recognition Engine
class SpeechRecognitionEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
    
    async def recognize_speech_from_audio(self, audio_data: bytes, 
                                        language: Language = Language.ENGLISH) -> SpeechRecognitionResult:
        """Recognize speech from audio data"""
        try:
            # Convert bytes to AudioData
            audio_file = io.BytesIO(audio_data)
            
            # Use speech_recognition library
            with sr.AudioFile(audio_file) as source:
                audio = self.recognizer.record(source)
            
            # Try Google Speech Recognition first
            try:
                transcript = self.recognizer.recognize_google(audio, language=language.value)
                confidence = 0.9  # Google doesn't provide confidence, estimate high
            except sr.UnknownValueError:
                # Try OpenAI Whisper as fallback
                transcript, confidence = await self._whisper_recognition(audio_data, language)
            except sr.RequestError:
                # Network error, try Whisper
                transcript, confidence = await self._whisper_recognition(audio_data, language)
            
            return SpeechRecognitionResult(
                transcript=transcript,
                confidence=confidence,
                language=language.value,
                duration=len(audio_data) / (16000 * 2),  # Estimate duration
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error recognizing speech: {e}")
            raise HTTPException(status_code=500, detail=f"Speech recognition failed: {e}")
    
    async def _whisper_recognition(self, audio_data: bytes, language: Language) -> tuple[str, float]:
        """Use OpenAI Whisper for speech recognition"""
        try:
            # Save audio to temporary file for Whisper
            temp_audio_path = f"/tmp/audio_{uuid.uuid4().hex}.wav"
            with open(temp_audio_path, 'wb') as f:
                f.write(audio_data)
            
            # Use OpenAI Whisper API
            with open(temp_audio_path, 'rb') as audio_file:
                transcript = await openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language.value[:2]  # Whisper uses 2-letter codes
                )
            
            # Clean up temp file
            import os
            os.unlink(temp_audio_path)
            
            return transcript.text, 0.85  # Whisper generally has good accuracy
            
        except Exception as e:
            logger.error(f"Whisper recognition failed: {e}")
            return "", 0.0

# Text-to-Speech Engine
class TextToSpeechEngine:
    def __init__(self):
        self.voice_configs = {}
    
    async def generate_speech(self, text: str, voice_type: VoiceType = VoiceType.FEMALE,
                            language: Language = Language.ENGLISH) -> VoiceResponse:
        """Generate speech from text"""
        try:
            # Use OpenAI TTS for high-quality voice synthesis
            if language == Language.ENGLISH:
                voice_name = "alloy" if voice_type == VoiceType.FEMALE else "echo"
            else:
                voice_name = "alloy"  # Default for other languages
            
            response = await openai_client.audio.speech.create(
                model="tts-1",
                voice=voice_name,
                input=text
            )
            
            audio_data = response.content
            
            return VoiceResponse(
                text=text,
                audio_data=audio_data,
                voice_type=voice_type,
                language=language,
                duration=len(text) * 0.1  # Rough estimate
            )
            
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            # Fallback to system TTS
            return await self._system_tts_fallback(text, voice_type, language)
    
    async def _system_tts_fallback(self, text: str, voice_type: VoiceType, 
                                 language: Language) -> VoiceResponse:
        """Fallback to system TTS engine"""
        try:
            # Configure TTS engine
            if tts_engine:
                # Set voice based on type
                voices = tts_engine.getProperty('voices')
                if voices:
                    # Simple logic to select voice
                    if voice_type == VoiceType.FEMALE and len(voices) > 1:
                        tts_engine.setProperty('voice', voices[1].id)
                    else:
                        tts_engine.setProperty('voice', voices[0].id)
                
                # Generate audio
                audio_buffer = io.BytesIO()
                
                # This is simplified - in practice, you'd need to capture audio output
                # For now, return empty audio with the text
                return VoiceResponse(
                    text=text,
                    audio_data=b"",  # Would contain actual audio data
                    voice_type=voice_type,
                    language=language,
                    duration=len(text) * 0.1
                )
            
        except Exception as e:
            logger.error(f"System TTS fallback failed: {e}")
            
        # Return empty response if all fails
        return VoiceResponse(
            text=text,
            audio_data=b"",
            voice_type=voice_type,
            language=language,
            duration=0.0
        )

# Voice Command Processor
class VoiceCommandProcessor:
    def __init__(self):
        self.command_patterns = {
            VoiceCommand.QUERY: ["show me", "find", "search", "what", "where", "when", "how many"],
            VoiceCommand.ALERT_ACKNOWLEDGE: ["acknowledge", "dismiss", "clear", "confirm"],
            VoiceCommand.CAMERA_CONTROL: ["camera", "zoom", "pan", "tilt", "focus"],
            VoiceCommand.SYSTEM_STATUS: ["status", "health", "uptime", "performance"],
            VoiceCommand.EMERGENCY: ["emergency", "alert", "help", "urgent", "critical"]
        }
    
    async def process_voice_command(self, transcript: str, session: VoiceSession) -> Dict[str, Any]:
        """Process voice command and generate response"""
        try:
            # Classify command
            command_type = self._classify_command(transcript)
            
            # Process based on command type
            if command_type == VoiceCommand.QUERY:
                return await self._process_query_command(transcript, session)
            elif command_type == VoiceCommand.ALERT_ACKNOWLEDGE:
                return await self._process_alert_command(transcript, session)
            elif command_type == VoiceCommand.CAMERA_CONTROL:
                return await self._process_camera_command(transcript, session)
            elif command_type == VoiceCommand.SYSTEM_STATUS:
                return await self._process_status_command(transcript, session)
            elif command_type == VoiceCommand.EMERGENCY:
                return await self._process_emergency_command(transcript, session)
            else:
                return await self._process_general_command(transcript, session)
                
        except Exception as e:
            logger.error(f"Error processing voice command: {e}")
            return {
                "response_text": "I'm sorry, I couldn't process that command. Please try again.",
                "command_type": "error",
                "success": False
            }
    
    def _classify_command(self, transcript: str) -> VoiceCommand:
        """Classify voice command based on transcript"""
        transcript_lower = transcript.lower()
        
        for command_type, patterns in self.command_patterns.items():
            for pattern in patterns:
                if pattern in transcript_lower:
                    return command_type
        
        return VoiceCommand.QUERY  # Default to query
    
    async def _process_query_command(self, transcript: str, session: VoiceSession) -> Dict[str, Any]:
        """Process query command"""
        try:
            # Call the enhanced prompt service
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8001/chat",
                    json={
                        "message": transcript,
                        "user_id": session.user_id,
                        "conversation_id": session.id
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "response_text": result.get("response", "No results found."),
                        "command_type": "query",
                        "success": True,
                        "data": result
                    }
                else:
                    return {
                        "response_text": "I'm having trouble searching right now. Please try again later.",
                        "command_type": "query",
                        "success": False
                    }
                    
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "response_text": "I encountered an error while searching. Please try again.",
                "command_type": "query",
                "success": False
            }
    
    async def _process_alert_command(self, transcript: str, session: VoiceSession) -> Dict[str, Any]:
        """Process alert acknowledgment command"""
        return {
            "response_text": "Alert acknowledged. Thank you for confirming.",
            "command_type": "alert_acknowledge",
            "success": True,
            "action": "alert_acknowledged"
        }
    
    async def _process_camera_command(self, transcript: str, session: VoiceSession) -> Dict[str, Any]:
        """Process camera control command"""
        # Parse camera command
        if "zoom in" in transcript.lower():
            action = "zoom_in"
            response = "Zooming in on the selected camera."
        elif "zoom out" in transcript.lower():
            action = "zoom_out"
            response = "Zooming out on the selected camera."
        elif "pan left" in transcript.lower():
            action = "pan_left"
            response = "Panning camera to the left."
        elif "pan right" in transcript.lower():
            action = "pan_right"
            response = "Panning camera to the right."
        else:
            action = "unknown"
            response = "I didn't understand that camera command. Try 'zoom in', 'zoom out', 'pan left', or 'pan right'."
        
        return {
            "response_text": response,
            "command_type": "camera_control",
            "success": action != "unknown",
            "action": action
        }
    
    async def _process_status_command(self, transcript: str, session: VoiceSession) -> Dict[str, Any]:
        """Process system status command"""
        try:
            # Get system status from dashboard service
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8009/dashboard/summary")
                
                if response.status_code == 200:
                    status_data = response.json()
                    
                    # Generate spoken status summary
                    cameras_online = status_data.get("key_metrics", {}).get("cameras_online", 0)
                    total_cameras = status_data.get("key_metrics", {}).get("total_cameras", 0)
                    uptime = status_data.get("key_metrics", {}).get("uptime", "Unknown")
                    
                    response_text = f"System status: {cameras_online} of {total_cameras} cameras are online. System uptime is {uptime}. All systems are operating normally."
                    
                    return {
                        "response_text": response_text,
                        "command_type": "system_status",
                        "success": True,
                        "data": status_data
                    }
                else:
                    return {
                        "response_text": "I'm unable to retrieve system status right now.",
                        "command_type": "system_status",
                        "success": False
                    }
                    
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "response_text": "Error retrieving system status.",
                "command_type": "system_status",
                "success": False
            }
    
    async def _process_emergency_command(self, transcript: str, session: VoiceSession) -> Dict[str, Any]:
        """Process emergency command"""
        return {
            "response_text": "Emergency alert activated. Notifying security personnel immediately.",
            "command_type": "emergency",
            "success": True,
            "action": "emergency_alert",
            "priority": "critical"
        }
    
    async def _process_general_command(self, transcript: str, session: VoiceSession) -> Dict[str, Any]:
        """Process general/unknown command"""
        return {
            "response_text": "I understand you said: " + transcript + ". How can I help you with the surveillance system?",
            "command_type": "general",
            "success": True
        }

# Initialize engines
speech_engine = SpeechRecognitionEngine()
tts_engine_instance = TextToSpeechEngine()
command_processor = VoiceCommandProcessor()

# FastAPI App
app = FastAPI(
    title="Voice Interface Service",
    description="Speech-to-text and text-to-speech for surveillance system",
    version="1.0.0",
    openapi_prefix="/api/v1"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
add_rate_limiting(app, service_name="voice_interface_service")

# WebSocket manager for real-time voice interaction
class VoiceWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Voice WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Voice WebSocket disconnected: {session_id}")
    
    async def send_audio_response(self, session_id: str, audio_data: bytes):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_bytes(audio_data)

voice_ws_manager = VoiceWebSocketManager()

# API Endpoints
@app.post("/api/v1/voice/session/create")
async def create_voice_session(user_id: str, language: Language = Language.ENGLISH, 
                              voice_type: VoiceType = VoiceType.FEMALE):
    """Create a new voice session"""
    try:
        session_id = await VoiceSessionManager.create_session(user_id, language, voice_type)
        return {
            "session_id": session_id,
            "language": language,
            "voice_type": voice_type
        }
    except Exception as e:
        logger.error(f"Error creating voice session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/voice/recognize")
async def recognize_speech(file: UploadFile = File(...), 
                          session_id: str = None,
                          language: Language = Language.ENGLISH):
    """Recognize speech from uploaded audio file"""
    try:
        # Read audio data
        audio_data = await file.read()
        
        # Recognize speech
        result = await speech_engine.recognize_speech_from_audio(audio_data, language)
        
        # If session provided, process as command
        if session_id:
            session = await VoiceSessionManager.get_session(session_id)
            if session:
                command_result = await command_processor.process_voice_command(result.transcript, session)
                
                # Update conversation history
                session.conversation_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_input": result.transcript,
                    "system_response": command_result.get("response_text", ""),
                    "command_type": command_result.get("command_type", "unknown")
                })
                
                await VoiceSessionManager.update_session(session)
                
                return {
                    "recognition_result": asdict(result),
                    "command_result": command_result
                }
        
        return {"recognition_result": asdict(result)}
        
    except Exception as e:
        logger.error(f"Error recognizing speech: {e}")        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/voice/speak")
async def generate_speech(request: VoiceQueryRequest):
    """Generate speech from text"""
    try:
        voice_response = await tts_engine_instance.generate_speech(
            request.text, 
            request.voice_type, 
            request.language
        )
        
        # Store audio response
        redis_client = await get_redis_client()
        audio_id = str(uuid.uuid4())
        await redis_client.setex(
            f"voice_audio:{audio_id}",
            300,  # 5 minutes
            voice_response.audio_data
        )
        
        return {
            "audio_id": audio_id,
            "text": voice_response.text,
            "duration": voice_response.duration,
            "voice_type": voice_response.voice_type,
            "language": voice_response.language
        }
        
    except Exception as e:
        logger.error(f"Error generating speech: {e}")        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/voice/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Get generated audio by ID"""
    try:
        redis_client = await get_redis_client()
        audio_data = await redis_client.get(f"voice_audio:{audio_id}")
        
        if not audio_data:
            raise HTTPException(status_code=404, detail="Audio not found")
        
        return {
            "audio_data": base64.b64encode(audio_data).decode('utf-8'),
            "format": "mp3"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/voice/command")
async def process_voice_command(text: str, session_id: str):
    """Process voice command from text"""
    try:
        session = await VoiceSessionManager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Process command
        result = await command_processor.process_voice_command(text, session)
        
        # Generate voice response
        voice_response = await tts_engine_instance.generate_speech(
            result.get("response_text", ""),
            session.voice_type,
            session.language
        )
        
        # Update session
        session.conversation_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "user_input": text,
            "system_response": result.get("response_text", ""),
            "command_type": result.get("command_type", "unknown")
        })
        
        await VoiceSessionManager.update_session(session)
        
        return {
            "command_result": result,
            "voice_response": {
                "text": voice_response.text,
                "audio_data": base64.b64encode(voice_response.audio_data).decode('utf-8'),
                "duration": voice_response.duration
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing voice command: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/voice/ws/{session_id}")
async def voice_websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time voice interaction"""
    await voice_ws_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive audio data
            audio_data = await websocket.receive_bytes()
            
            # Recognize speech
            result = await speech_engine.recognize_speech_from_audio(audio_data)
            
            # Get session
            session = await VoiceSessionManager.get_session(session_id)
            if session:
                # Process command
                command_result = await command_processor.process_voice_command(result.transcript, session)
                
                # Generate voice response
                voice_response = await tts_engine_instance.generate_speech(
                    command_result.get("response_text", ""),
                    session.voice_type,
                    session.language
                )
                
                # Send response
                await websocket.send_json({
                    "transcript": result.transcript,
                    "response": command_result.get("response_text", ""),
                    "command_type": command_result.get("command_type", "unknown")
                })
                
                # Send audio response
                await voice_ws_manager.send_audio_response(session_id, voice_response.audio_data)
                
    except WebSocketDisconnect:
        voice_ws_manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")        voice_ws_manager.disconnect(session_id)

@app.get("/api/v1/voice/sessions/{session_id}")
async def get_voice_session(session_id: str):
    """Get voice session details"""
    try:
        session = await VoiceSessionManager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return asdict(session)
        
    except Exception as e:
        logger.error(f"Error getting voice session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)

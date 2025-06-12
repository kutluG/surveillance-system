"""
Bidirectional WebSocket Service: Real-time command and control system.
Enables two-way communication for surveillance system management.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional, Set
import json
import uuid
import asyncio
from datetime import datetime, timedelta
import redis.asyncio as redis
from enum import Enum

from shared.logging_config import configure_logging, get_logger
from shared.metrics import instrument_app
from shared.auth import get_current_user, TokenData
from shared.middleware.rate_limit import WebSocketRateLimiter

LOGGER = configure_logging("websocket_service")
app = FastAPI(
    title="Bidirectional WebSocket Service",
    openapi_prefix="/api/v1"
)
instrument_app(app, service_name="websocket_service")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection for pub/sub and session management
redis_client = redis.from_url("redis://redis:6379", decode_responses=True)

# WebSocket rate limiters for specialized endpoints
events_limiter = WebSocketRateLimiter("30/minute")  # 30 messages per minute for events
alerts_limiter = WebSocketRateLimiter("30/minute")  # 30 messages per minute for alerts

class CommandType(str, Enum):
    # Camera Control Commands
    CAMERA_START_RECORDING = "camera.start_recording"
    CAMERA_STOP_RECORDING = "camera.stop_recording"
    CAMERA_CAPTURE_SNAPSHOT = "camera.capture_snapshot"
    CAMERA_ADJUST_SETTINGS = "camera.adjust_settings"
    CAMERA_PTZ_CONTROL = "camera.ptz_control"
    
    # Alert Management Commands
    ALERT_ACKNOWLEDGE = "alert.acknowledge"
    ALERT_DISMISS = "alert.dismiss"
    ALERT_ESCALATE = "alert.escalate"
    ALERT_CREATE_CUSTOM = "alert.create_custom"
    
    # System Control Commands
    SYSTEM_HEALTH_CHECK = "system.health_check"
    SYSTEM_STATUS_UPDATE = "system.status_update"
    SYSTEM_RESTART_SERVICE = "system.restart_service"
    
    # Recording Management Commands
    RECORDING_START = "recording.start"
    RECORDING_STOP = "recording.stop"
    RECORDING_DELETE = "recording.delete"
    RECORDING_DOWNLOAD = "recording.download"
    
    # Real-time Notifications
    NOTIFICATION_SEND = "notification.send"
    NOTIFICATION_BROADCAST = "notification.broadcast"
    
    # AI/LLM Commands
    AI_PROMPT_EXECUTE = "ai.prompt_execute"
    AI_RULE_GENERATE = "ai.rule_generate"
    AI_ANALYSIS_REQUEST = "ai.analysis_request"

class MessageType(str, Enum):
    COMMAND = "command"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    STATUS_UPDATE = "status_update"
    ERROR = "error"

class WebSocketMessage(BaseModel):
    message_id: str
    message_type: MessageType
    command_type: Optional[CommandType] = None
    payload: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    requires_response: bool = False
    response_to: Optional[str] = None

class CommandRequest(BaseModel):
    command_type: CommandType
    parameters: Dict[str, Any] = {}
    target_id: Optional[str] = None  # Camera ID, service name, etc.
    priority: str = "normal"  # low, normal, high, critical
    timeout_seconds: int = 30

class CommandResponse(BaseModel):
    command_id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int
    timestamp: datetime

# Connection manager for WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        """Accept new WebSocket connection."""
        await websocket.accept()
        
        self.active_connections[session_id] = websocket
        
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)
        
        self.session_metadata[session_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "message_count": 0        }
        
        LOGGER.info(f"WebSocket connection established - session_id: {session_id}, user_id: {user_id}")
    
    async def disconnect(self, session_id: str):
        """Handle WebSocket disconnection."""
        if session_id in self.active_connections:
            websocket = self.active_connections.pop(session_id)
            
            # Remove from user sessions
            metadata = self.session_metadata.get(session_id, {})
            user_id = metadata.get("user_id")
            
            if user_id and user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]
              # Clean up session metadata
            if session_id in self.session_metadata:
                del self.session_metadata[session_id]
            
            LOGGER.info(f"WebSocket connection closed - session_id: {session_id}, user_id: {user_id}")
    
    async def send_message(self, session_id: str, message: WebSocketMessage):
        """Send message to specific session."""
        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                message_dict = message.model_dump(mode='json')
                message_dict['timestamp'] = message.timestamp.isoformat()
                
                await websocket.send_text(json.dumps(message_dict))
                  # Update session activity
                if session_id in self.session_metadata:
                    self.session_metadata[session_id]["last_activity"] = datetime.utcnow()
                    self.session_metadata[session_id]["message_count"] += 1
                return True
            except Exception as e:
                LOGGER.error(f"Failed to send WebSocket message - session_id: {session_id}, error: {str(e)}")
                await self.disconnect(session_id)
                return False
        return False
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage):
        """Send message to all sessions of a user."""
        if user_id in self.user_sessions:
            session_ids = list(self.user_sessions[user_id])
            tasks = [self.send_message(session_id, message) for session_id in session_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return sum(1 for r in results if r is True)
        return 0
    
    async def broadcast(self, message: WebSocketMessage, exclude_sessions: Set[str] = None):
        """Broadcast message to all connected sessions."""
        exclude_sessions = exclude_sessions or set()
        session_ids = [sid for sid in self.active_connections.keys() 
                      if sid not in exclude_sessions]
        
        tasks = [self.send_message(session_id, message) for session_id in session_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return sum(1 for r in results if r is True)
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get information about active sessions."""
        return [
            {
                "session_id": session_id,
                **metadata
            }
            for session_id, metadata in self.session_metadata.items()
        ]

# Global connection manager
manager = ConnectionManager()

# Command handlers
class CommandHandler:
    """Handles execution of WebSocket commands."""
    
    def __init__(self):
        self.handlers = {
            CommandType.CAMERA_START_RECORDING: self._handle_camera_start_recording,
            CommandType.CAMERA_STOP_RECORDING: self._handle_camera_stop_recording,
            CommandType.CAMERA_CAPTURE_SNAPSHOT: self._handle_camera_snapshot,
            CommandType.CAMERA_ADJUST_SETTINGS: self._handle_camera_settings,
            CommandType.CAMERA_PTZ_CONTROL: self._handle_camera_ptz,
            
            CommandType.ALERT_ACKNOWLEDGE: self._handle_alert_acknowledge,
            CommandType.ALERT_DISMISS: self._handle_alert_dismiss,
            CommandType.ALERT_ESCALATE: self._handle_alert_escalate,
            
            CommandType.SYSTEM_HEALTH_CHECK: self._handle_system_health,
            CommandType.SYSTEM_STATUS_UPDATE: self._handle_system_status,
            
            CommandType.RECORDING_START: self._handle_recording_start,
            CommandType.RECORDING_STOP: self._handle_recording_stop,
            CommandType.RECORDING_DELETE: self._handle_recording_delete,
            
            CommandType.AI_PROMPT_EXECUTE: self._handle_ai_prompt,
            CommandType.AI_RULE_GENERATE: self._handle_ai_rule_generate,
        }
    
    async def execute_command(self, command: CommandRequest, user_id: str) -> CommandResponse:
        """Execute a command and return response."""
        start_time = datetime.utcnow()
        command_id = str(uuid.uuid4())
        
        try:
            if command.command_type not in self.handlers:
                raise ValueError(f"Unknown command type: {command.command_type}")
            
            handler = self.handlers[command.command_type]
            result = await handler(command, user_id)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return CommandResponse(
                command_id=command_id,
                success=True,
                result=result,
                execution_time_ms=int(execution_time),
                timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000        LOGGER.error(f"Command execution failed - command_type: {command.command_type}, user_id: {user_id}, error: {str(e)}")
            
            return CommandResponse(
                command_id=command_id,
                success=False,
                error=str(e),
                execution_time_ms=int(execution_time),
                timestamp=datetime.utcnow()
            )
    
    # Camera Control Handlers
    async def _handle_camera_start_recording(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle camera recording start command."""
        camera_id = command.parameters.get("camera_id")
        duration_minutes = command.parameters.get("duration_minutes", 60)
        
        # In a real implementation, this would call the camera service
        await asyncio.sleep(0.1)  # Simulate API call
        
        return {
            "camera_id": camera_id,
            "recording_started": True,
            "duration_minutes": duration_minutes,
            "recording_id": str(uuid.uuid4())
        }
    
    async def _handle_camera_stop_recording(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle camera recording stop command."""
        camera_id = command.parameters.get("camera_id")
        recording_id = command.parameters.get("recording_id")
        
        await asyncio.sleep(0.1)  # Simulate API call
        
        return {
            "camera_id": camera_id,
            "recording_id": recording_id,
            "recording_stopped": True,
            "final_duration_minutes": 45  # Example
        }
    
    async def _handle_camera_snapshot(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle camera snapshot capture command."""
        camera_id = command.parameters.get("camera_id")
        
        await asyncio.sleep(0.2)  # Simulate capture time
        
        return {
            "camera_id": camera_id,
            "snapshot_captured": True,
            "snapshot_url": f"https://cdn.example.com/snapshots/{uuid.uuid4()}.jpg",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_camera_settings(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle camera settings adjustment."""
        camera_id = command.parameters.get("camera_id")
        settings = command.parameters.get("settings", {})
        
        await asyncio.sleep(0.1)
        
        return {
            "camera_id": camera_id,
            "settings_updated": True,
            "applied_settings": settings
        }
    
    async def _handle_camera_ptz(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle PTZ (Pan-Tilt-Zoom) control."""
        camera_id = command.parameters.get("camera_id")
        action = command.parameters.get("action")  # pan_left, pan_right, tilt_up, tilt_down, zoom_in, zoom_out
        amount = command.parameters.get("amount", 1)
        
        await asyncio.sleep(0.1)
        
        return {
            "camera_id": camera_id,
            "ptz_action": action,
            "amount": amount,
            "executed": True
        }
    
    # Alert Management Handlers
    async def _handle_alert_acknowledge(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle alert acknowledgment."""
        alert_id = command.parameters.get("alert_id")
        
        await asyncio.sleep(0.1)
        
        return {
            "alert_id": alert_id,
            "acknowledged": True,
            "acknowledged_by": user_id,
            "acknowledged_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_alert_dismiss(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle alert dismissal."""
        alert_id = command.parameters.get("alert_id")
        reason = command.parameters.get("reason", "User dismissed")
        
        await asyncio.sleep(0.1)
        
        return {
            "alert_id": alert_id,
            "dismissed": True,
            "dismissed_by": user_id,
            "reason": reason
        }
    
    async def _handle_alert_escalate(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle alert escalation."""
        alert_id = command.parameters.get("alert_id")
        escalation_level = command.parameters.get("level", "high")
        
        await asyncio.sleep(0.1)
        
        return {
            "alert_id": alert_id,
            "escalated": True,
            "escalation_level": escalation_level,
            "escalated_by": user_id
        }
    
    # System Control Handlers
    async def _handle_system_health(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle system health check."""
        await asyncio.sleep(0.2)
        
        return {
            "system_status": "healthy",
            "services": {
                "camera_service": "running",
                "vms_service": "running",
                "rag_service": "running",
                "alert_service": "running"
            },
            "uptime_seconds": 3600,
            "last_check": datetime.utcnow().isoformat()
        }
    
    async def _handle_system_status(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle system status update request."""
        await asyncio.sleep(0.1)
        
        return {
            "status_updated": True,
            "current_status": "operational",
            "active_alerts": 2,
            "active_recordings": 5
        }
    
    # Recording Management Handlers
    async def _handle_recording_start(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle recording start command."""
        cameras = command.parameters.get("cameras", [])
        duration = command.parameters.get("duration_minutes", 30)
        
        await asyncio.sleep(0.1)
        
        return {
            "recording_started": True,
            "cameras": cameras,
            "duration_minutes": duration,
            "recording_session_id": str(uuid.uuid4())
        }
    
    async def _handle_recording_stop(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle recording stop command."""
        session_id = command.parameters.get("recording_session_id")
        
        await asyncio.sleep(0.1)
        
        return {
            "recording_stopped": True,
            "session_id": session_id,
            "final_duration": 25
        }
    
    async def _handle_recording_delete(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle recording deletion."""
        recording_id = command.parameters.get("recording_id")
        
        await asyncio.sleep(0.1)
        
        return {
            "recording_deleted": True,
            "recording_id": recording_id
        }
    
    # AI/LLM Handlers
    async def _handle_ai_prompt(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle AI prompt execution."""
        prompt = command.parameters.get("prompt")
        context = command.parameters.get("context", {})
        
        await asyncio.sleep(0.5)  # Simulate AI processing
        
        return {
            "prompt_executed": True,
            "response": f"AI response to: {prompt}",
            "confidence": 0.85,
            "processing_time_ms": 450
        }
    
    async def _handle_ai_rule_generate(self, command: CommandRequest, user_id: str) -> Dict[str, Any]:
        """Handle AI rule generation."""
        description = command.parameters.get("description")
        
        await asyncio.sleep(0.3)
        
        return {
            "rule_generated": True,
            "rule_id": str(uuid.uuid4()),
            "description": description,
            "conditions": ["motion_detected", "after_hours"],
            "actions": ["send_alert", "start_recording"]
        }

# Global command handler
command_handler = CommandHandler()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, token: str = None):
    """Main WebSocket endpoint for bidirectional communication."""
    
    # Authentication (simplified for demo)
    user_id = "user_123"  # In production, extract from token
    
    await manager.connect(websocket, session_id, user_id)
    
    # Send welcome message
    welcome_message = WebSocketMessage(
        message_id=str(uuid.uuid4()),
        message_type=MessageType.STATUS_UPDATE,
        payload={
            "status": "connected",
            "session_id": session_id,
            "user_id": user_id,
            "server_time": datetime.utcnow().isoformat(),
            "available_commands": [cmd.value for cmd in CommandType]
        },
        timestamp=datetime.utcnow(),
        user_id=user_id,
        session_id=session_id
    )
    await manager.send_message(session_id, welcome_message)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                
                # Handle different message types
                if message_data.get("message_type") == MessageType.COMMAND:
                    await handle_command_message(message_data, session_id, user_id)
                else:
                    # Handle other message types (status updates, etc.)
                    await handle_general_message(message_data, session_id, user_id)
                    
            except json.JSONDecodeError as e:
                error_message = WebSocketMessage(
                    message_id=str(uuid.uuid4()),
                    message_type=MessageType.ERROR,
                    payload={"error": "Invalid JSON format", "details": str(e)},
                    timestamp=datetime.utcnow(),
                    session_id=session_id
                )
                await manager.send_message(session_id, error_message)
                
    except WebSocketDisconnect:
        await manager.disconnect(session_id)
    except Exception as e:
        LOGGER.error(f"WebSocket error - session_id: {session_id}, error: {str(e)}")
        await manager.disconnect(session_id)

async def handle_command_message(message_data: Dict[str, Any], session_id: str, user_id: str):
    """Handle command execution requests."""
    try:
        # Parse command request
        command_request = CommandRequest(
            command_type=CommandType(message_data.get("command_type")),
            parameters=message_data.get("parameters", {}),
            target_id=message_data.get("target_id"),
            priority=message_data.get("priority", "normal"),
            timeout_seconds=message_data.get("timeout_seconds", 30)
        )
        
        # Execute command
        response = await command_handler.execute_command(command_request, user_id)
        
        # Send response back to client
        response_message = WebSocketMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.RESPONSE,
            command_type=command_request.command_type,
            payload=response.model_dump(),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            response_to=message_data.get("message_id")
        )
        
        await manager.send_message(session_id, response_message)
        
        # If command affects system state, broadcast update to other users
        if should_broadcast_command(command_request.command_type):
            await broadcast_system_update(command_request, response, user_id, {session_id})
        
    except Exception as e:
        error_message = WebSocketMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.ERROR,
            payload={"error": "Command execution failed", "details": str(e)},
            timestamp=datetime.utcnow(),
            session_id=session_id,
            response_to=message_data.get("message_id")
        )
        await manager.send_message(session_id, error_message)

async def handle_general_message(message_data: Dict[str, Any], session_id: str, user_id: str):
    """Handle non-command messages."""
    message_type = message_data.get("message_type")
    
    if message_type == MessageType.STATUS_UPDATE:
        # Handle status update requests
        status_response = WebSocketMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.STATUS_UPDATE,
            payload={
                "server_status": "operational",
                "active_sessions": len(manager.active_connections),
                "server_time": datetime.utcnow().isoformat()
            },
            timestamp=datetime.utcnow(),
            session_id=session_id
        )
        await manager.send_message(session_id, status_response)

def should_broadcast_command(command_type: CommandType) -> bool:
    """Determine if command results should be broadcast to other users."""
    broadcast_commands = {
        CommandType.CAMERA_START_RECORDING,
        CommandType.CAMERA_STOP_RECORDING,
        CommandType.ALERT_ACKNOWLEDGE,
        CommandType.ALERT_ESCALATE,
        CommandType.SYSTEM_STATUS_UPDATE,
        CommandType.RECORDING_START,
        CommandType.RECORDING_STOP
    }
    return command_type in broadcast_commands

async def broadcast_system_update(
    command: CommandRequest, 
    response: CommandResponse, 
    executing_user: str,
    exclude_sessions: Set[str]
):
    """Broadcast system state changes to other users."""
    update_message = WebSocketMessage(
        message_id=str(uuid.uuid4()),
        message_type=MessageType.NOTIFICATION,
        command_type=command.command_type,
        payload={
            "event": "system_update",
            "command_executed": command.command_type.value,
            "executed_by": executing_user,
            "success": response.success,
            "summary": generate_update_summary(command, response)
        },
        timestamp=datetime.utcnow()
    )
    
    await manager.broadcast(update_message, exclude_sessions)

def generate_update_summary(command: CommandRequest, response: CommandResponse) -> str:
    """Generate human-readable summary of system update."""
    if not response.success:
        return f"Failed to execute {command.command_type.value}"
    
    summaries = {
        CommandType.CAMERA_START_RECORDING: "Camera recording started",
        CommandType.CAMERA_STOP_RECORDING: "Camera recording stopped",
        CommandType.ALERT_ACKNOWLEDGE: "Alert acknowledged",
        CommandType.ALERT_ESCALATE: "Alert escalated",
        CommandType.RECORDING_START: "System recording started",
        CommandType.RECORDING_STOP: "System recording stopped"
    }
    
    return summaries.get(command.command_type, f"System command executed: {command.command_type.value}")

# REST API endpoints for WebSocket management

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "timestamp": datetime.utcnow().isoformat()    }

@app.get("/api/v1/sessions")
async def get_active_sessions():
    """Get information about active WebSocket sessions."""
    return {
        "sessions": manager.get_active_sessions(),
        "total_count": len(manager.active_connections)
    }

@app.post("/api/v1/broadcast")
async def broadcast_message(message: Dict[str, Any]):
    """Broadcast a message to all connected clients."""
    broadcast_msg = WebSocketMessage(
        message_id=str(uuid.uuid4()),
        message_type=MessageType.NOTIFICATION,
        payload=message,
        timestamp=datetime.utcnow()
    )
    
    sent_count = await manager.broadcast(broadcast_msg)
    return {"message_sent_to": sent_count, "total_sessions": len(manager.active_connections)}

@app.post("/api/v1/send/{user_id}")
async def send_to_user(user_id: str, message: Dict[str, Any]):
    """Send a message to all sessions of a specific user."""
    user_msg = WebSocketMessage(
        message_id=str(uuid.uuid4()),
        message_type=MessageType.NOTIFICATION,
        payload=message,
        timestamp=datetime.utcnow(),
        user_id=user_id
    )
    
    sent_count = await manager.send_to_user(user_id, user_msg)
    return {"message_sent_to_sessions": sent_count, "user_id": user_id}

# Background task for periodic updates
async def periodic_status_broadcast():
    """Send periodic status updates to all connected clients."""
    while True:
        try:
            await asyncio.sleep(30)  # Every 30 seconds
            
            if manager.active_connections:
                status_message = WebSocketMessage(
                    message_id=str(uuid.uuid4()),
                    message_type=MessageType.STATUS_UPDATE,
                    payload={
                        "event": "periodic_update",
                        "server_time": datetime.utcnow().isoformat(),
                        "active_sessions": len(manager.active_connections),
                        "system_status": "operational"
                    },
                    timestamp=datetime.utcnow()
                )
                
                await manager.broadcast(status_message)
                
        except Exception as e:
            LOGGER.error(f"Error in periodic status broadcast - error: {str(e)}")

# Start background tasks
@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on startup."""
    asyncio.create_task(periodic_status_broadcast())
    LOGGER.info("Bidirectional WebSocket Service started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await redis_client.close()
    LOGGER.info("Bidirectional WebSocket Service stopped")

@app.websocket("/ws/v1/events/{session_id}")
async def events_websocket_endpoint(websocket: WebSocket, session_id: str, token: str = None):
    """Specialized WebSocket endpoint for real-time events with rate limiting (30 messages/min)."""
    
    # Authentication (simplified for demo)
    user_id = "user_123"  # In production, extract from token
    
    await manager.connect(websocket, f"events_{session_id}", user_id)
    
    # Send welcome message for events endpoint
    welcome_message = WebSocketMessage(
        message_id=str(uuid.uuid4()),
        message_type=MessageType.STATUS_UPDATE,
        payload={
            "status": "connected_to_events",
            "session_id": session_id,
            "user_id": user_id,
            "endpoint": "events",
            "rate_limit": "30 messages per minute",
            "server_time": datetime.utcnow().isoformat()
        },
        timestamp=datetime.utcnow(),
        user_id=user_id,
        session_id=f"events_{session_id}"
    )
    await manager.send_message(f"events_{session_id}", welcome_message)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Apply rate limiting
            if not events_limiter.is_allowed(websocket):
                error_message = {
                    "error": "Rate limit exceeded",
                    "message": "Too many messages. Limit: 30 messages per minute for events endpoint.",
                    "retry_after": 60
                }
                await websocket.send_json(error_message)
                continue
            
            try:
                message_data = json.loads(data)
                
                # Handle event-specific messages
                if message_data.get("message_type") == "event_subscription":
                    # Handle event subscription requests
                    event_types = message_data.get("event_types", [])
                    response = {
                        "message_type": "subscription_confirmed",
                        "subscribed_events": event_types,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_json(response)
                else:
                    # Handle other event messages
                    response = {
                        "message_type": "event_processed",
                        "original_message": message_data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_json(response)
                    
            except json.JSONDecodeError as e:
                error_message = {
                    "error": "Invalid JSON format",
                    "details": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_json(error_message)
                
    except WebSocketDisconnect:
        await manager.disconnect(f"events_{session_id}")
    except Exception as e:
        print(f"Events WebSocket error - session_id: {session_id}, error: {str(e)}")
        await manager.disconnect(f"events_{session_id}")

@app.websocket("/ws/v1/alerts/{session_id}")
async def alerts_websocket_endpoint(websocket: WebSocket, session_id: str, token: str = None):
    """Specialized WebSocket endpoint for real-time alerts with rate limiting (30 messages/min)."""
    
    # Authentication (simplified for demo)
    user_id = "user_123"  # In production, extract from token
    
    await manager.connect(websocket, f"alerts_{session_id}", user_id)
    
    # Send welcome message for alerts endpoint
    welcome_message = WebSocketMessage(
        message_id=str(uuid.uuid4()),
        message_type=MessageType.STATUS_UPDATE,
        payload={
            "status": "connected_to_alerts",
            "session_id": session_id,
            "user_id": user_id,
            "endpoint": "alerts",
            "rate_limit": "30 messages per minute",
            "server_time": datetime.utcnow().isoformat()
        },
        timestamp=datetime.utcnow(),
        user_id=user_id,
        session_id=f"alerts_{session_id}"
    )
    await manager.send_message(f"alerts_{session_id}", welcome_message)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Apply rate limiting
            if not alerts_limiter.is_allowed(websocket):
                error_message = {
                    "error": "Rate limit exceeded",
                    "message": "Too many messages. Limit: 30 messages per minute for alerts endpoint.",
                    "retry_after": 60
                }
                await websocket.send_json(error_message)
                continue
            
            try:
                message_data = json.loads(data)
                
                # Handle alert-specific messages
                if message_data.get("message_type") == "alert_acknowledgment":
                    # Handle alert acknowledgment
                    alert_id = message_data.get("alert_id")
                    response = {
                        "message_type": "alert_acknowledged",
                        "alert_id": alert_id,
                        "acknowledged_by": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_json(response)
                elif message_data.get("message_type") == "alert_filter":
                    # Handle alert filtering requests
                    filters = message_data.get("filters", {})
                    response = {
                        "message_type": "filter_applied",
                        "active_filters": filters,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_json(response)
                else:
                    # Handle other alert messages
                    response = {
                        "message_type": "alert_processed",
                        "original_message": message_data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_json(response)
                    
            except json.JSONDecodeError as e:
                error_message = {
                    "error": "Invalid JSON format",
                    "details": str(e),
                    "timestamp": datetime.utcnow().isoformat()                }
                await websocket.send_json(error_message)
                
    except WebSocketDisconnect:
        await manager.disconnect(f"alerts_{session_id}")
    except Exception as e:
        print(f"Alerts WebSocket error - session_id: {session_id}, error: {str(e)}")
        await manager.disconnect(f"alerts_{session_id}")

# Backwards compatibility: Redirect old WebSocket endpoints to versioned ones
@app.websocket("/ws/events/{session_id}")
async def events_websocket_redirect(websocket: WebSocket, session_id: str, token: str = None):
    """
    Backwards compatibility redirect for /ws/events/{session_id} to /ws/v1/events/{session_id}
    Provides seamless transition for existing WebSocket clients.
    """
    # Accept the connection first
    await websocket.accept()
    
    # Send deprecation notice and redirect information
    deprecation_message = {
        "type": "deprecation_notice",
        "message": "This WebSocket endpoint is deprecated. Please use /ws/v1/events/{session_id}",
        "old_endpoint": f"/ws/events/{session_id}",
        "new_endpoint": f"/ws/v1/events/{session_id}",
        "timestamp": datetime.utcnow().isoformat(),
        "action": "redirecting_automatically"
    }
    
    try:
        await websocket.send_json(deprecation_message)
        await asyncio.sleep(0.1)  # Brief pause to ensure message is sent
        
        # Close with a redirect code and reason
        await websocket.close(
            code=3000,  # Custom code for redirect
            reason=f"Redirecting to /ws/v1/events/{session_id}"
        )
        
        LOGGER.info(f"WebSocket redirect: /ws/events/{session_id} -> /ws/v1/events/{session_id}")
        
    except Exception as e:
        LOGGER.error(f"Error during WebSocket redirect for events endpoint: {e}")
        try:
            await websocket.close(code=1011, reason="Redirect failed")
        except:
            pass

@app.websocket("/ws/alerts/{session_id}")  
async def alerts_websocket_redirect(websocket: WebSocket, session_id: str, token: str = None):
    """
    Backwards compatibility redirect for /ws/alerts/{session_id} to /ws/v1/alerts/{session_id}
    Provides seamless transition for existing WebSocket clients.
    """
    # Accept the connection first
    await websocket.accept()
    
    # Send deprecation notice and redirect information
    deprecation_message = {
        "type": "deprecation_notice", 
        "message": "This WebSocket endpoint is deprecated. Please use /ws/v1/alerts/{session_id}",
        "old_endpoint": f"/ws/alerts/{session_id}",
        "new_endpoint": f"/ws/v1/alerts/{session_id}",
        "timestamp": datetime.utcnow().isoformat(),
        "action": "redirecting_automatically"
    }
    
    try:
        await websocket.send_json(deprecation_message)
        await asyncio.sleep(0.1)  # Brief pause to ensure message is sent
        
        # Close with a redirect code and reason
        await websocket.close(
            code=3000,  # Custom code for redirect  
            reason=f"Redirecting to /ws/v1/alerts/{session_id}"
        )
        
        LOGGER.info(f"WebSocket redirect: /ws/alerts/{session_id} -> /ws/v1/alerts/{session_id}")
        
    except Exception as e:
        LOGGER.error(f"Error during WebSocket redirect for alerts endpoint: {e}")
        try:
            await websocket.close(code=1011, reason="Redirect failed")
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

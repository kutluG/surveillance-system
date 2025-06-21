# Downstream Integration Guide

This document provides complete integration specifications for consuming Enhanced Prompt Service payloads in downstream services including the Ingest Service, Notifier Service, and AI Dashboard.

## Overview

The Enhanced Prompt Service generates structured JSON payloads for three primary downstream integrations:

1. **Prompt Response Payloads** - Real-time AI conversation responses
2. **History Retrieval Payloads** - Conversation history and analytics
3. **Proactive Insight Payloads** - System monitoring and predictive alerts

## JSON Schema Specifications

### 1. Prompt Response Payload

**Schema Reference:** `PromptResponsePayload` in `enhanced_prompt_service/schemas.py`

**Use Cases:** Real-time responses, user interaction logging, performance monitoring

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PromptResponsePayload",
  "type": "object",
  "properties": {
    "service_name": {
      "type": "string",
      "default": "enhanced_prompt_service",
      "description": "Source service identifier"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Response generation timestamp (ISO 8601)"
    },
    "conversation_id": {
      "type": "string",
      "description": "Unique conversation identifier"
    },
    "user_id": {
      "type": "string",
      "description": "User identifier who made the request"
    },
    "query": {
      "type": "string",
      "description": "Original user query"
    },
    "response": {
      "type": "string",
      "description": "AI-generated response"
    },
    "response_type": {
      "type": "string",
      "enum": ["answer", "clarification", "proactive_insight"],
      "description": "Type of response generated"
    },
    "confidence_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Response confidence score"
    },
    "evidence_count": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of evidence items found"
    },
    "evidence": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/Evidence"
      },
      "description": "Supporting evidence"
    },
    "clip_links": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uri"
      },
      "description": "Video clip URLs"
    },
    "follow_up_questions": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Generated follow-up questions"
    },
    "conversation_turn": {
      "type": "integer",
      "minimum": 1,
      "description": "Turn number in conversation"
    },
    "processing_time_ms": {
      "type": "integer",
      "minimum": 0,
      "description": "Response processing time in milliseconds"
    },
    "metadata": {
      "type": "object",
      "description": "Additional system metadata"
    }
  },
  "required": [
    "conversation_id",
    "user_id",
    "query",
    "response",
    "response_type",
    "confidence_score",
    "evidence_count",
    "conversation_turn",
    "processing_time_ms"
  ],
  "definitions": {
    "Evidence": {
      "type": "object",
      "properties": {
        "event_id": {
          "type": "string",
          "description": "Unique identifier for the event"
        },
        "timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "ISO 8601 timestamp of the event"
        },
        "camera_id": {
          "type": "string",
          "description": "Camera identifier that captured the event"
        },
        "event_type": {
          "type": "string",
          "description": "Type of event (e.g., 'person_detected', 'motion')"
        },
        "confidence": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Confidence score from 0.0 to 1.0"
        },
        "description": {
          "type": "string",
          "description": "Human-readable description of the event"
        }
      },
      "required": ["event_id", "timestamp", "camera_id", "event_type", "confidence", "description"]
    }
  }
}
```

**Example Payload:**

```json
{
  "service_name": "enhanced_prompt_service",
  "timestamp": "2024-01-15T10:30:00Z",
  "conversation_id": "conv_12345",
  "user_id": "user_67890",
  "query": "What happened in camera 3 today?",
  "response": "I found 5 motion detection events in camera 3 today, including 2 person detections between 2-3 PM.",
  "response_type": "answer",
  "confidence_score": 0.87,
  "evidence_count": 5,
  "evidence": [
    {
      "event_id": "evt_001",
      "timestamp": "2024-01-15T14:30:00Z",
      "camera_id": "camera_3",
      "event_type": "person_detected",
      "confidence": 0.92,
      "description": "Person detected near entrance"
    }
  ],
  "clip_links": ["https://clips.example.com/evt_001.mp4"],
  "follow_up_questions": [
    "Would you like to see the video clips?",
    "Do you want to check other cameras?"
  ],
  "conversation_turn": 1,
  "processing_time_ms": 1250,
  "metadata": {
    "search_duration_ms": 850,
    "ai_model": "gpt-4",
    "context_used": true
  }
}
```

### 2. History Retrieval Payload

**Schema Reference:** `HistoryRetrievalPayload` in `enhanced_prompt_service/schemas.py`

**Use Cases:** Conversation analytics, audit logs, user behavior analysis

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "HistoryRetrievalPayload",
  "type": "object",
  "properties": {
    "service_name": {
      "type": "string",
      "default": "enhanced_prompt_service"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "conversation_id": {
      "type": "string"
    },
    "user_id": {
      "type": "string"
    },
    "conversation_created": {
      "type": "string",
      "format": "date-time"
    },
    "total_messages": {
      "type": "integer",
      "minimum": 0
    },
    "conversation_duration_minutes": {
      "type": "integer",
      "minimum": 0
    },
    "messages": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/ConversationMessage"
      }
    },
    "user_queries": {
      "type": "integer",
      "minimum": 0
    },
    "ai_responses": {
      "type": "integer",
      "minimum": 0
    },
    "average_confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "evidence_items_total": {
      "type": "integer",
      "minimum": 0
    },
    "conversation_topics": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "cameras_discussed": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "last_activity": {
      "type": "string",
      "format": "date-time"
    },
    "metadata": {
      "type": "object"
    }
  },
  "required": [
    "conversation_id",
    "user_id",
    "conversation_created",
    "total_messages",
    "messages",
    "user_queries",
    "ai_responses",
    "average_confidence",
    "evidence_items_total",
    "last_activity"
  ],
  "definitions": {
    "ConversationMessage": {
      "type": "object",
      "properties": {
        "role": {
          "type": "string",
          "enum": ["user", "assistant"]
        },
        "content": {
          "type": "string"
        },
        "timestamp": {
          "type": "string",
          "format": "date-time"
        },
        "metadata": {
          "type": "object"
        }
      },
      "required": ["role", "content", "timestamp"]
    }
  }
}
```

### 3. Proactive Insight Payload

**Schema Reference:** `ProactiveInsightPayload` in `enhanced_prompt_service/schemas.py`

**Use Cases:** System monitoring, alerting, predictive maintenance

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ProactiveInsightPayload",
  "type": "object",
  "properties": {
    "service_name": {
      "type": "string",
      "default": "enhanced_prompt_service"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "insight_id": {
      "type": "string"
    },
    "insight_type": {
      "type": "string",
      "enum": ["activity_spike", "camera_performance", "security_anomaly", "prediction"]
    },
    "severity": {
      "type": "string",
      "enum": ["low", "medium", "high", "critical"]
    },
    "title": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "confidence_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "analysis_period": {
      "type": "string"
    },
    "affected_cameras": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "event_count": {
      "type": "integer",
      "minimum": 0
    },
    "suggested_actions": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "priority_level": {
      "type": "integer",
      "minimum": 1,
      "maximum": 5
    },
    "evidence": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/Evidence"
      }
    },
    "clip_links": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uri"
      }
    },
    "related_insights": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "metadata": {
      "type": "object"
    }
  },
  "required": [
    "insight_id",
    "insight_type",
    "severity",
    "title",
    "message",
    "confidence_score",
    "analysis_period",
    "event_count",
    "priority_level"
  ]
}
```

## Integration Code Examples

### Ingest Service Integration (httpx)

The Ingest Service receives and processes prompt response payloads for data pipeline integration.

```python
import httpx
import asyncio
from typing import Dict, Any
from datetime import datetime
import json

class PromptServiceIngestClient:
    """
    Client for integrating Enhanced Prompt Service payloads with Ingest Service.
    """
    
    def __init__(self, ingest_base_url: str, api_key: str):
        self.base_url = ingest_base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
    
    async def send_prompt_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send prompt response payload to ingest service for processing.
        
        Args:
            payload: PromptResponsePayload dictionary
            
        Returns:
            Ingest service response
        """
        try:
            # Validate required fields
            required_fields = [
                'conversation_id', 'user_id', 'query', 'response', 
                'response_type', 'confidence_score'
            ]
            for field in required_fields:
                if field not in payload:
                    raise ValueError(f"Missing required field: {field}")
            
            # Add ingest metadata
            ingest_payload = {
                **payload,
                "ingest_timestamp": datetime.now().isoformat(),
                "source_service": "enhanced_prompt_service",
                "data_type": "prompt_response"
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/ingest/prompt-responses",
                json=ingest_payload
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "success": True,
                "ingest_id": result.get("ingest_id"),
                "processed_at": result.get("timestamp"),
                "status": result.get("status", "queued")
            }
            
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "retry_after": e.response.headers.get("retry-after")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_conversation_history(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send conversation history payload to ingest service.
        """
        try:
            ingest_payload = {
                **payload,
                "ingest_timestamp": datetime.now().isoformat(),
                "source_service": "enhanced_prompt_service",
                "data_type": "conversation_history"
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/ingest/conversation-history",
                json=ingest_payload
            )
            response.raise_for_status()
            
            return {"success": True, "data": response.json()}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def batch_send_insights(self, insights: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send multiple proactive insights in batch to ingest service.
        """
        try:
            batch_payload = {
                "insights": insights,
                "batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "source_service": "enhanced_prompt_service"
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/ingest/proactive-insights/batch",
                json=batch_payload
            )
            response.raise_for_status()
            
            return {"success": True, "data": response.json()}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

# Usage Example
async def main():
    client = PromptServiceIngestClient(
        ingest_base_url="http://ingest-service:8080",
        api_key="your_api_key_here"
    )
    
    # Example prompt response payload
    payload = {
        "conversation_id": "conv_12345",
        "user_id": "user_67890",
        "query": "Show me recent activity",
        "response": "I found 3 recent events...",
        "response_type": "answer",
        "confidence_score": 0.89,
        "evidence_count": 3,
        "conversation_turn": 1,
        "processing_time_ms": 1100
    }
    
    result = await client.send_prompt_response(payload)
    print(f"Ingest result: {result}")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Notifier Service Integration (WebSocket)

The Notifier Service receives real-time notifications for proactive insights and high-priority responses.

```python
import asyncio
import websockets
import json
from typing import Dict, Any, Callable
from dataclasses import dataclass
import logging

@dataclass
class NotificationConfig:
    websocket_url: str
    api_key: str
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10

class PromptServiceNotifierClient:
    """
    WebSocket client for sending prompt service notifications to Notifier Service.
    """
    
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.websocket = None
        self.reconnect_count = 0
        self.is_connected = False
        self.message_handlers = {}
        self.logger = logging.getLogger(__name__)
    
    async def connect(self):
        """Establish WebSocket connection with authentication."""
        try:
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            self.websocket = await websockets.connect(
                self.config.websocket_url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10
            )
            self.is_connected = True
            self.reconnect_count = 0
            self.logger.info("Connected to Notifier Service")
            
            # Start message listener
            asyncio.create_task(self._listen_for_messages())
            
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            raise
    
    async def send_proactive_insight_notification(self, insight_payload: Dict[str, Any]):
        """
        Send proactive insight notification via WebSocket.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to Notifier Service")
        
        notification = {
            "type": "proactive_insight",
            "timestamp": insight_payload.get("timestamp"),
            "data": {
                "insight_id": insight_payload["insight_id"],
                "insight_type": insight_payload["insight_type"],
                "severity": insight_payload["severity"],
                "title": insight_payload["title"],
                "message": insight_payload["message"],
                "confidence_score": insight_payload["confidence_score"],
                "affected_cameras": insight_payload.get("affected_cameras", []),
                "priority_level": insight_payload["priority_level"],
                "suggested_actions": insight_payload.get("suggested_actions", [])
            },
            "metadata": {
                "source": "enhanced_prompt_service",
                "notification_id": f"notif_{insight_payload['insight_id']}",
                "requires_acknowledgment": insight_payload["severity"] in ["high", "critical"]
            }
        }
        
        await self._send_message(notification)
    
    async def send_response_notification(self, response_payload: Dict[str, Any]):
        """
        Send prompt response notification for high-confidence or urgent responses.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to Notifier Service")
        
        # Only send notifications for high-confidence responses or specific types
        if (response_payload["confidence_score"] < 0.8 and 
            response_payload["response_type"] != "proactive_insight"):
            return
        
        notification = {
            "type": "prompt_response",
            "timestamp": response_payload.get("timestamp"),
            "data": {
                "conversation_id": response_payload["conversation_id"],
                "user_id": response_payload["user_id"],
                "response_type": response_payload["response_type"],
                "confidence_score": response_payload["confidence_score"],
                "evidence_count": response_payload["evidence_count"],
                "summary": response_payload["response"][:200] + "..." if len(response_payload["response"]) > 200 else response_payload["response"]
            },
            "metadata": {
                "source": "enhanced_prompt_service",
                "notification_id": f"notif_{response_payload['conversation_id']}_{response_payload['conversation_turn']}"
            }
        }
        
        await self._send_message(notification)
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send message via WebSocket with error handling."""
        try:
            message_json = json.dumps(message)
            await self.websocket.send(message_json)
            self.logger.debug(f"Sent notification: {message['type']}")
            
        except websockets.exceptions.ConnectionClosed:
            self.is_connected = False
            await self._reconnect()
            # Retry sending the message
            await self.websocket.send(json.dumps(message))
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise
    
    async def _listen_for_messages(self):
        """Listen for incoming messages from Notifier Service."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_incoming_message(data)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON received: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.is_connected = False
            self.logger.warning("WebSocket connection closed")
            
        except Exception as e:
            self.logger.error(f"Error listening for messages: {e}")
    
    async def _handle_incoming_message(self, message: Dict[str, Any]):
        """Handle incoming messages from Notifier Service."""
        message_type = message.get("type")
        if message_type == "acknowledgment":
            self.logger.info(f"Notification acknowledged: {message.get('notification_id')}")
        elif message_type == "status":
            self.logger.info(f"Notifier status: {message.get('status')}")
        elif message_type == "error":
            self.logger.error(f"Notifier error: {message.get('error')}")
    
    async def _reconnect(self):
        """Attempt to reconnect with exponential backoff."""
        if self.reconnect_count >= self.config.max_reconnect_attempts:
            self.logger.error("Max reconnection attempts reached")
            return
        
        self.reconnect_count += 1
        wait_time = min(self.config.reconnect_interval * (2 ** self.reconnect_count), 60)
        
        self.logger.info(f"Reconnecting in {wait_time} seconds (attempt {self.reconnect_count})")
        await asyncio.sleep(wait_time)
        
        try:
            await self.connect()
        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")
            await self._reconnect()
    
    async def close(self):
        """Close WebSocket connection."""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()

# Usage Example
async def main():
    config = NotificationConfig(
        websocket_url="ws://notifier-service:8080/ws/prompt-service",
        api_key="your_websocket_api_key"
    )
    
    client = PromptServiceNotifierClient(config)
    await client.connect()
    
    # Example proactive insight notification
    insight = {
        "insight_id": "insight_001",
        "insight_type": "security_anomaly",
        "severity": "high",
        "title": "Unusual Activity Detected",
        "message": "Multiple person detections in restricted area",
        "confidence_score": 0.91,
        "affected_cameras": ["camera_5"],
        "priority_level": 4,
        "suggested_actions": ["Review footage", "Contact security team"]
    }
    
    await client.send_proactive_insight_notification(insight)
    
    # Keep connection alive
    await asyncio.sleep(60)
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### AI Dashboard Integration (Recharts)

The AI Dashboard visualizes prompt service data using React and Recharts for analytics and monitoring.

```tsx
import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';

interface PromptResponsePayload {
  service_name: string;
  timestamp: string;
  conversation_id: string;
  user_id: string;
  query: string;
  response: string;
  response_type: 'answer' | 'clarification' | 'proactive_insight';
  confidence_score: number;
  evidence_count: number;
  evidence: Evidence[];
  clip_links: string[];
  follow_up_questions: string[];
  conversation_turn: number;
  processing_time_ms: number;
  metadata: Record<string, any>;
}

interface Evidence {
  event_id: string;
  timestamp: string;
  camera_id: string;
  event_type: string;
  confidence: number;
  description: string;
}

interface ProactiveInsightPayload {
  insight_id: string;
  insight_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  message: string;
  confidence_score: number;
  analysis_period: string;
  affected_cameras: string[];
  event_count: number;
  suggested_actions: string[];
  priority_level: number;
  timestamp: string;
}

// Dashboard Component for Prompt Service Analytics
const PromptServiceDashboard: React.FC = () => {
  const [responseData, setResponseData] = useState<PromptResponsePayload[]>([]);
  const [insightData, setInsightData] = useState<ProactiveInsightPayload[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [responsesRes, insightsRes] = await Promise.all([
        fetch('/api/v1/dashboard/prompt-responses'),
        fetch('/api/v1/dashboard/proactive-insights')
      ]);

      const responses = await responsesRes.json();
      const insights = await insightsRes.json();

      setResponseData(responses);
      setInsightData(insights);
      setIsLoading(false);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      setIsLoading(false);
    }
  };

  // Process data for charts
  const processResponseTimeData = () => {
    return responseData
      .slice(-50) // Last 50 responses
      .map((item, index) => ({
        index: index + 1,
        processing_time: item.processing_time_ms,
        confidence: item.confidence_score * 100,
        evidence_count: item.evidence_count,
        timestamp: new Date(item.timestamp).toLocaleTimeString()
      }));
  };

  const processConfidenceDistribution = () => {
    const buckets = { 'Low (0-0.3)': 0, 'Medium (0.3-0.7)': 0, 'High (0.7-1.0)': 0 };
    
    responseData.forEach(item => {
      if (item.confidence_score <= 0.3) buckets['Low (0-0.3)']++;
      else if (item.confidence_score <= 0.7) buckets['Medium (0.3-0.7)']++;
      else buckets['High (0.7-1.0)']++;
    });

    return Object.entries(buckets).map(([name, value]) => ({ name, value }));
  };

  const processInsightSeverityData = () => {
    const severityCounts = { low: 0, medium: 0, high: 0, critical: 0 };
    
    insightData.forEach(insight => {
      severityCounts[insight.severity]++;
    });

    return Object.entries(severityCounts).map(([severity, count]) => ({
      severity: severity.toUpperCase(),
      count,
      color: {
        low: '#10B981',
        medium: '#F59E0B', 
        high: '#EF4444',
        critical: '#7C2D12'
      }[severity]
    }));
  };

  const processHourlyActivity = () => {
    const hourlyData: Record<string, number> = {};
    
    responseData.forEach(item => {
      const hour = new Date(item.timestamp).getHours();
      const hourLabel = `${hour.toString().padStart(2, '0')}:00`;
      hourlyData[hourLabel] = (hourlyData[hourLabel] || 0) + 1;
    });

    return Object.entries(hourlyData)
      .map(([hour, count]) => ({ hour, count }))
      .sort((a, b) => a.hour.localeCompare(b.hour));
  };

  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c'];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">
        Enhanced Prompt Service Dashboard
      </h1>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <MetricCard
          title="Total Responses"
          value={responseData.length}
          trend="+12%"
          color="blue"
        />
        <MetricCard
          title="Avg Confidence"
          value={`${(responseData.reduce((sum, item) => sum + item.confidence_score, 0) / responseData.length * 100).toFixed(1)}%`}
          trend="+3%"
          color="green"
        />
        <MetricCard
          title="Active Insights"
          value={insightData.length}
          trend="+2"
          color="yellow"
        />
        <MetricCard
          title="Avg Processing Time"
          value={`${Math.round(responseData.reduce((sum, item) => sum + item.processing_time_ms, 0) / responseData.length)}ms`}
          trend="-50ms"
          color="purple"
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Response Time Trend */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold mb-4">Response Time Trend</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={processResponseTimeData()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="processing_time" 
                stroke="#8884d8" 
                strokeWidth={2}
                name="Processing Time (ms)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Confidence Distribution */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold mb-4">Confidence Score Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={processConfidenceDistribution()}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {processConfidenceDistribution().map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Hourly Activity */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold mb-4">Hourly Activity Pattern</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={processHourlyActivity()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" />
              <YAxis />
              <Tooltip />
              <Area 
                type="monotone" 
                dataKey="count" 
                stroke="#82ca9d" 
                fill="#82ca9d" 
                fillOpacity={0.6}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Insight Severity Breakdown */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold mb-4">Insight Severity Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={processInsightSeverityData()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="severity" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#8884d8">
                {processInsightSeverityData().map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Insights Table */}
      <div className="mt-8 bg-white rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold">Recent Proactive Insights</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Severity
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cameras
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Confidence
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {insightData.slice(-10).reverse().map((insight) => (
                <tr key={insight.insight_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(insight.timestamp).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {insight.insight_type.replace('_', ' ').toUpperCase()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      insight.severity === 'critical' ? 'bg-red-100 text-red-800' :
                      insight.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                      insight.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-green-100 text-green-800'
                    }`}>
                      {insight.severity.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                    {insight.title}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {insight.affected_cameras.length > 0 ? insight.affected_cameras.join(', ') : 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {(insight.confidence_score * 100).toFixed(0)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// Metric Card Component
interface MetricCardProps {
  title: string;
  value: string | number;
  trend: string;
  color: 'blue' | 'green' | 'yellow' | 'purple';
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, trend, color }) => {
  const colorClasses = {
    blue: 'border-blue-500 text-blue-600',
    green: 'border-green-500 text-green-600',
    yellow: 'border-yellow-500 text-yellow-600',
    purple: 'border-purple-500 text-purple-600'
  };

  return (
    <div className={`bg-white p-6 rounded-lg shadow-md border-l-4 ${colorClasses[color]}`}>
      <h3 className="text-sm font-medium text-gray-500 mb-2">{title}</h3>
      <div className="flex items-baseline">
        <p className="text-2xl font-semibold text-gray-900">{value}</p>
        <p className={`ml-2 text-sm font-medium ${colorClasses[color]}`}>
          {trend}
        </p>
      </div>
    </div>
  );
};

export default PromptServiceDashboard;
```

## Payload Generation in Enhanced Prompt Service

To use these payload models in your Enhanced Prompt Service endpoints, import and utilize them as follows:

```python
from enhanced_prompt_service.schemas import (
    PromptResponsePayload, 
    HistoryRetrievalPayload, 
    ProactiveInsightPayload
)

# In your router endpoint
@router.post("/prompt", response_model=PromptResponse)
async def enhanced_conversation(request, req, current_user, conversation_manager):
    # ... existing logic ...
    
    # Generate downstream payload
    downstream_payload = PromptResponsePayload(
        conversation_id=conversation["id"],
        user_id=current_user.sub,
        query=req.query,
        response=ai_response["response"],
        response_type=ai_response["type"],
        confidence_score=ai_response["confidence"],
        evidence_count=len(contexts),
        evidence=[Evidence(**ctx) for ctx in contexts],
        clip_links=clip_links,
        follow_up_questions=follow_ups,
        conversation_turn=len(conversation_history) // 2 + 1,
        processing_time_ms=ai_response.get("processing_time", 0)
    )
    
    # Send to downstream services
    await send_to_ingest_service(downstream_payload.dict())
    await send_to_notifier_service(downstream_payload.dict())
    
    return response
```

## Testing and Validation

### JSON Schema Validation

You can validate payloads against the schemas using standard JSON Schema validation tools:

```python
import jsonschema
from enhanced_prompt_service.schemas import PromptResponsePayload

# Generate JSON schema from Pydantic model
schema = PromptResponsePayload.model_json_schema()

# Validate payload
payload = {
    "conversation_id": "conv_123",
    "user_id": "user_456",
    # ... other fields
}

try:
    jsonschema.validate(payload, schema)
    print("Payload is valid")
except jsonschema.ValidationError as e:
    print(f"Validation error: {e.message}")
```

### Integration Testing

Create comprehensive integration tests to validate the end-to-end flow:

```python
# tests/test_downstream_integration.py
import pytest
from enhanced_prompt_service.schemas import PromptResponsePayload

def test_prompt_response_payload_creation():
    payload = PromptResponsePayload(
        conversation_id="test_conv",
        user_id="test_user",
        query="test query",
        response="test response",
        response_type="answer",
        confidence_score=0.85,
        evidence_count=2,
        conversation_turn=1,
        processing_time_ms=1000
    )
    
    assert payload.conversation_id == "test_conv"
    assert payload.confidence_score == 0.85
    assert payload.service_name == "enhanced_prompt_service"

def test_payload_json_serialization():
    payload = PromptResponsePayload(
        conversation_id="test_conv",
        user_id="test_user",
        query="test query",
        response="test response", 
        response_type="answer",
        confidence_score=0.85,
        evidence_count=0,
        conversation_turn=1,
        processing_time_ms=1000
    )
    
    json_data = payload.model_dump_json()
    assert "conversation_id" in json_data
    assert "enhanced_prompt_service" in json_data
```

## Security Considerations

1. **Authentication**: All downstream integrations should use proper API authentication
2. **Data Sanitization**: Ensure all text fields are sanitized before sending to downstream services
3. **Rate Limiting**: Implement rate limiting for downstream API calls
4. **Encryption**: Use HTTPS/WSS for all data transmission
5. **Audit Logging**: Log all downstream integrations for security auditing

## Monitoring and Alerting

Set up monitoring for downstream integration health:

1. **Integration Success Rates**: Monitor successful vs failed downstream calls
2. **Response Times**: Track latency for downstream service calls
3. **Payload Size Monitoring**: Alert on unusually large payloads
4. **Error Rate Thresholds**: Alert when error rates exceed acceptable limits

## Conclusion

This documentation provides complete specifications and integration examples for consuming Enhanced Prompt Service payloads in downstream services. The structured JSON schemas ensure consistent data contracts while the code examples provide practical implementation guidance for real-world integrations.

For questions or support, please refer to the Enhanced Prompt Service API documentation or contact the development team.

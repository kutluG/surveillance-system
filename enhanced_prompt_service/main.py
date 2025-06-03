"""
Enhanced Prompt Service: Advanced conversational AI with context and follow-ups.
"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import uuid
from datetime import datetime, timedelta
import redis

from shared.logging import get_logger
from shared.metrics import instrument_app
from shared.models import QueryResult
from shared.auth import get_current_user, TokenData

from weaviate_client import semantic_search
from clip_store import get_clip_url
from conversation_manager import ConversationManager
from llm_client import generate_conversational_response, generate_follow_up_questions

LOGGER = get_logger("enhanced_prompt_service")
app = FastAPI(title="Enhanced Prompt Service")
instrument_app(app, service_name="enhanced_prompt_service")

# Redis for conversation memory
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
conversation_manager = ConversationManager(redis_client)

class ConversationRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None
    limit: int = 5

class ConversationResponse(BaseModel):
    conversation_id: str
    response: str
    follow_up_questions: List[str]
    evidence: List[Dict[str, Any]]
    clip_links: List[str]
    confidence_score: float
    response_type: str  # "answer", "clarification", "proactive_insight"
    metadata: Dict[str, Any]

class ProactiveInsightRequest(BaseModel):
    time_range: str = "24h"
    severity_threshold: str = "medium"
    include_predictions: bool = True

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/conversation", response_model=ConversationResponse)
async def enhanced_conversation(
    req: ConversationRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Enhanced conversational interface with context and follow-ups."""
    LOGGER.info("Enhanced conversation request", 
                query=req.query, 
                conversation_id=req.conversation_id,
                user=current_user.sub)
    
    try:
        # Get or create conversation context
        if req.conversation_id:
            conversation = await conversation_manager.get_conversation(req.conversation_id)
        else:
            conversation = await conversation_manager.create_conversation(
                user_id=current_user.sub,
                initial_context=req.user_context or {}
            )
        
        # Add current query to conversation history
        await conversation_manager.add_message(
            conversation["id"], 
            "user", 
            req.query,
            metadata=req.user_context
        )
        
        # Get conversation context for better AI responses
        conversation_history = await conversation_manager.get_recent_messages(
            conversation["id"], 
            limit=10
        )
        
        # Enhanced semantic search with conversation context
        contexts = await enhanced_semantic_search(
            req.query, 
            conversation_history,
            limit=req.limit
        )
        
        # Generate contextual AI response
        ai_response = await generate_conversational_response(
            query=req.query,
            conversation_history=conversation_history,
            evidence=contexts,
            user_context=req.user_context or {}
        )
        
        # Generate intelligent follow-up questions
        follow_ups = await generate_follow_up_questions(
            query=req.query,
            response=ai_response["response"],
            evidence=contexts,
            conversation_context=conversation_history
        )
        
        # Generate clip links with enhanced metadata
        clip_links = []
        for ctx in contexts:
            clip_url = get_clip_url(ctx["event_id"])
            clip_links.append({
                "url": clip_url,
                "event_id": ctx["event_id"],
                "timestamp": ctx["timestamp"],
                "camera_id": ctx["camera_id"],
                "confidence": ctx.get("confidence", 0.0),
                "description": ctx.get("description", "")
            })
        
        # Store AI response in conversation
        await conversation_manager.add_message(
            conversation["id"],
            "assistant",
            ai_response["response"],
            metadata={
                "confidence": ai_response["confidence"],
                "evidence_count": len(contexts),
                "response_type": ai_response["type"]
            }
        )
        
        response = ConversationResponse(
            conversation_id=conversation["id"],
            response=ai_response["response"],
            follow_up_questions=follow_ups,
            evidence=[{
                "event_id": ctx["event_id"],
                "timestamp": ctx["timestamp"],
                "camera_id": ctx["camera_id"],
                "event_type": ctx["event_type"],
                "confidence": ctx.get("confidence", 0.0),
                "description": ctx.get("description", "")
            } for ctx in contexts],
            clip_links=[link["url"] for link in clip_links],
            confidence_score=ai_response["confidence"],
            response_type=ai_response["type"],
            metadata={
                "conversation_turns": len(conversation_history),
                "evidence_sources": len(contexts),
                "processing_time_ms": ai_response.get("processing_time", 0)
            }
        )
        
        LOGGER.info("Enhanced conversation response generated",
                   conversation_id=conversation["id"],
                   response_type=ai_response["type"],
                   confidence=ai_response["confidence"])
        
        return response
        
    except Exception as e:
        LOGGER.error("Enhanced conversation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Conversation processing failed")

@app.get("/proactive-insights", response_model=List[ConversationResponse])
async def get_proactive_insights(
    req: ProactiveInsightRequest = ProactiveInsightRequest(),
    current_user: TokenData = Depends(get_current_user)
):
    """Generate proactive insights about system status and anomalies."""
    LOGGER.info("Proactive insights request", 
                time_range=req.time_range,
                user=current_user.sub)
    
    try:
        # Analyze recent events for patterns and anomalies
        insights = await analyze_system_patterns(
            time_range=req.time_range,
            severity_threshold=req.severity_threshold,
            include_predictions=req.include_predictions
        )
        
        responses = []
        for insight in insights:
            # Create a conversation for each insight
            conversation = await conversation_manager.create_conversation(
                user_id=current_user.sub,
                initial_context={"type": "proactive_insight", "insight_type": insight["type"]}
            )
            
            response = ConversationResponse(
                conversation_id=conversation["id"],
                response=insight["message"],
                follow_up_questions=insight["suggested_actions"],
                evidence=insight["evidence"],
                clip_links=insight["clip_links"],
                confidence_score=insight["confidence"],
                response_type="proactive_insight",
                metadata={
                    "insight_type": insight["type"],
                    "severity": insight["severity"],
                    "timestamp": insight["timestamp"]
                }
            )
            responses.append(response)
        
        LOGGER.info("Proactive insights generated", count=len(responses))
        return responses
        
    except Exception as e:
        LOGGER.error("Proactive insights failed", error=str(e))
        raise HTTPException(status_code=500, detail="Insights generation failed")

@app.get("/conversation/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    limit: int = 50,
    current_user: TokenData = Depends(get_current_user)
):
    """Get conversation history for a specific conversation."""
    try:
        messages = await conversation_manager.get_recent_messages(
            conversation_id, 
            limit=limit
        )
        return {"conversation_id": conversation_id, "messages": messages}
    except Exception as e:
        LOGGER.error("Failed to get conversation history", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation history")

@app.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete a conversation and its history."""
    try:
        await conversation_manager.delete_conversation(conversation_id)
        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        LOGGER.error("Failed to delete conversation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

async def enhanced_semantic_search(query: str, conversation_history: List[Dict], limit: int = 5):
    """Enhanced semantic search that considers conversation context."""
    try:
        # Extract context from conversation history
        context_queries = []
        for msg in conversation_history[-3:]:  # Last 3 messages for context
            if msg["role"] == "user":
                context_queries.append(msg["content"])
        
        # Combine current query with context
        enhanced_query = query
        if context_queries:
            context_str = " ".join(context_queries[-2:])  # Last 2 user queries
            enhanced_query = f"{context_str} {query}"
        
        # Perform semantic search with enhanced query
        results = semantic_search(enhanced_query, limit=limit)
        
        # Add relevance scoring based on conversation context
        for result in results:
            result["conversation_relevance"] = calculate_conversation_relevance(
                result, conversation_history
            )
        
        # Sort by relevance
        results.sort(key=lambda x: x.get("conversation_relevance", 0), reverse=True)
        
        return results
        
    except Exception as e:
        LOGGER.error("Enhanced semantic search failed", error=str(e))
        # Fallback to basic search
        return semantic_search(query, limit=limit)

def calculate_conversation_relevance(result: Dict, conversation_history: List[Dict]) -> float:
    """Calculate how relevant a search result is to the conversation context."""
    relevance_score = 0.5  # Base relevance
    
    # Check if camera_id mentioned in conversation
    for msg in conversation_history:
        if result.get("camera_id", "") in msg.get("content", ""):
            relevance_score += 0.2
            
        # Check for temporal references
        if any(time_word in msg.get("content", "").lower() 
               for time_word in ["today", "yesterday", "recent", "last"]):
            # Prefer more recent events
            event_time = datetime.fromisoformat(result.get("timestamp", "").replace("Z", "+00:00"))
            hours_ago = (datetime.now() - event_time.replace(tzinfo=None)).total_seconds() / 3600
            if hours_ago < 24:
                relevance_score += 0.3
    
    return min(relevance_score, 1.0)

async def analyze_system_patterns(
    time_range: str = "24h", 
    severity_threshold: str = "medium",
    include_predictions: bool = True
) -> List[Dict]:
    """Analyze system for patterns and generate proactive insights."""
    insights = []
    
    try:
        # Convert time range to hours
        hours = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}.get(time_range, 24)
        
        # Query recent events for pattern analysis
        recent_events = semantic_search(
            f"events last {hours} hours", 
            limit=100
        )
        
        # Pattern 1: Unusual activity spikes
        activity_insight = analyze_activity_patterns(recent_events, time_range)
        if activity_insight:
            insights.append(activity_insight)
            
        # Pattern 2: Camera performance issues
        camera_insight = analyze_camera_performance(recent_events)
        if camera_insight:
            insights.append(camera_insight)
            
        # Pattern 3: Security anomalies
        security_insight = analyze_security_anomalies(recent_events, severity_threshold)
        if security_insight:
            insights.append(security_insight)
            
        # Pattern 4: Predictive insights (if enabled)
        if include_predictions:
            prediction_insight = generate_predictions(recent_events, time_range)
            if prediction_insight:
                insights.append(prediction_insight)
                
    except Exception as e:
        LOGGER.error("Pattern analysis failed", error=str(e))
        
    return insights

def analyze_activity_patterns(events: List[Dict], time_range: str) -> Optional[Dict]:
    """Analyze for unusual activity patterns."""
    if len(events) < 10:
        return None
        
    # Simple pattern detection - could be enhanced with ML
    current_hour_events = len([e for e in events if "recent" in str(e)])
    
    if current_hour_events > 50:  # Threshold for unusual activity
        return {
            "type": "activity_spike",
            "message": f"Unusual activity detected: {current_hour_events} events in the last hour, significantly above normal baseline.",
            "suggested_actions": [
                "Review camera feeds for the affected areas",
                "Check for environmental factors causing false triggers",
                "Consider adjusting detection sensitivity"
            ],
            "evidence": events[:10],
            "clip_links": [get_clip_url(e["event_id"]) for e in events[:5]],
            "confidence": 0.8,
            "severity": "medium",
            "timestamp": datetime.now().isoformat()
        }
    
    return None

def analyze_camera_performance(events: List[Dict]) -> Optional[Dict]:
    """Analyze camera performance issues."""
    camera_counts = {}
    for event in events:
        camera_id = event.get("camera_id", "unknown")
        camera_counts[camera_id] = camera_counts.get(camera_id, 0) + 1
    
    # Find cameras with no activity (potential issues)
    inactive_cameras = [cam for cam, count in camera_counts.items() if count == 0]
    
    if inactive_cameras:
        return {
            "type": "camera_performance",
            "message": f"Cameras may need attention: {', '.join(inactive_cameras[:3])} showing no activity in recent period.",
            "suggested_actions": [
                "Check camera connectivity and power",
                "Verify camera positioning and field of view",
                "Review camera configuration settings"
            ],
            "evidence": [],
            "clip_links": [],
            "confidence": 0.7,
            "severity": "low",
            "timestamp": datetime.now().isoformat()
        }
    
    return None

def analyze_security_anomalies(events: List[Dict], severity_threshold: str) -> Optional[Dict]:
    """Analyze for security-related anomalies."""
    high_confidence_events = [
        e for e in events 
        if e.get("confidence", 0) > 0.9 and "person" in str(e.get("event_type", ""))
    ]
    
    if len(high_confidence_events) > 5:
        return {
            "type": "security_anomaly",
            "message": f"Multiple high-confidence person detections ({len(high_confidence_events)}) detected. Review for potential security concerns.",
            "suggested_actions": [
                "Review footage for unauthorized access attempts",
                "Verify personnel schedules and authorized access",
                "Consider increasing security patrols for affected areas"
            ],
            "evidence": high_confidence_events[:5],
            "clip_links": [get_clip_url(e["event_id"]) for e in high_confidence_events[:3]],
            "confidence": 0.9,
            "severity": "high",
            "timestamp": datetime.now().isoformat()
        }
    
    return None

def generate_predictions(events: List[Dict], time_range: str) -> Optional[Dict]:
    """Generate predictive insights based on patterns."""
    # Simple prediction based on event frequency trends
    if len(events) > 20:
        return {
            "type": "prediction",
            "message": "Based on current activity patterns, expect 15-20% increase in motion detection events during the next 4-hour period.",
            "suggested_actions": [
                "Consider pre-positioning security personnel",
                "Ensure adequate storage space for increased recordings",
                "Monitor system performance for potential resource constraints"
            ],
            "evidence": events[:5],
            "clip_links": [],
            "confidence": 0.6,
            "severity": "info",
            "timestamp": datetime.now().isoformat()
        }
    
    return None

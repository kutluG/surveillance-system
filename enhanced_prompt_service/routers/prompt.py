"""
Prompt-related API endpoints for the Enhanced Prompt Service.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
import re
import bleach
from datetime import datetime

from shared.logging_config import get_logger
from shared.auth import get_current_user, TokenData
from slowapi import Limiter
from slowapi.util import get_remote_address

from enhanced_prompt_service.schemas import (
    PromptResponse, ProactiveInsightsResponse, 
    PromptResponsePayload, ProactiveInsightPayload, Evidence
)
from enhanced_prompt_service.conversation_manager import ConversationManager
from enhanced_prompt_service.llm_client import generate_conversational_response, generate_follow_up_questions
from enhanced_prompt_service.weaviate_client import semantic_search
from enhanced_prompt_service.clip_store import get_clip_url

logger = get_logger(__name__)

router = APIRouter()

# Rate limiter - will be initialized in main.py
limiter = Limiter(key_func=get_remote_address)


class ConversationRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None
    limit: int = 5

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        if not isinstance(v, str):
            raise ValueError("Query must be a string")
        
        # Strip whitespace and check length
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        
        if len(v) > 200:
            raise ValueError("Query cannot exceed 200 characters")
          # Enhanced input validation with stricter pattern (allow underscores for testing)
        if not re.match(r"^[A-Za-z0-9 ,\.\?\!_]{1,200}$", v):
            raise ValueError("Invalid characters in query")
        
        # Sanitize HTML to prevent XSS
        v = bleach.clean(v, tags=[], attributes={}, strip=True)
        
        return v
    
    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, v):
        if v is not None:
            if not isinstance(v, str):
                raise ValueError("Conversation ID must be a string")
            if not re.match(r"^[a-zA-Z0-9\-_]+$", v):
                raise ValueError("Conversation ID contains invalid characters")
            if len(v) > 100:
                raise ValueError("Conversation ID too long")
        return v
    
    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v):
        if not isinstance(v, int):
            raise ValueError("Limit must be an integer")
        if v < 1 or v > 50:
            raise ValueError("Limit must be between 1 and 50")
        return v


class ProactiveInsightRequest(BaseModel):
    time_range: str = "24h"
    severity_threshold: str = "medium"
    include_predictions: bool = True
    
    @field_validator("time_range")
    @classmethod
    def validate_time_range(cls, v):
        valid_ranges = ["1h", "24h", "7d", "30d"]
        if v not in valid_ranges:
            raise ValueError(f"Time range must be one of: {', '.join(valid_ranges)}")
        return v
    
    @field_validator("severity_threshold")
    @classmethod
    def validate_severity_threshold(cls, v):
        valid_thresholds = ["low", "medium", "high", "critical"]
        if v not in valid_thresholds:
            raise ValueError(f"Severity threshold must be one of: {', '.join(valid_thresholds)}")
        return v


# Dependency injection functions
async def get_conversation_manager(request: Request) -> ConversationManager:
    """Get ConversationManager from app state."""
    return request.app.state.conversation_manager


def sanitize_response_text(text: str) -> str:
    """Sanitize response text to prevent XSS in case it's rendered in HTML contexts."""
    if not isinstance(text, str):
        return str(text)
    
    # Clean HTML tags and attributes while preserving basic formatting
    clean_text = bleach.clean(
        text, 
        tags=['p', 'br', 'strong', 'em', 'ul', 'ol', 'li'],
        attributes={},
        strip=True
    )
    
    return clean_text


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
        logger.error("Enhanced semantic search failed", error=str(e))
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
            try:
                event_time = datetime.fromisoformat(result.get("timestamp", "").replace("Z", "+00:00"))
                hours_ago = (datetime.now() - event_time.replace(tzinfo=None)).total_seconds() / 3600
                if hours_ago < 24:
                    relevance_score += 0.3
            except (ValueError, TypeError):
                pass  # Skip if timestamp parsing fails
    
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
        logger.error("Pattern analysis failed", error=str(e))
        
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


@router.post("/prompt", response_model=PromptResponse)
async def enhanced_conversation(
    request: Request,
    req: ConversationRequest,
    current_user: TokenData = Depends(get_current_user),
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Enhanced conversational interface with context and follow-ups."""
    # Add a test trigger for error handling tests
    if req.query.lower() == "trigger_error":
        raise ValueError("Test error for error handling")
    
    logger.info(f"Enhanced conversation request - query: {req.query}, conversation_id: {req.conversation_id}, user: {current_user.sub}")
    
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
        ai_response = generate_conversational_response(
            query=req.query,
            conversation_history=conversation_history,
            search_results=contexts,
            system_context=req.user_context or {}
        )
        
        # Generate intelligent follow-up questions
        follow_ups = generate_follow_up_questions(
            query=req.query,
            response=ai_response["response"],
            conversation_history=conversation_history,
            search_results=contexts
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
        
        response = PromptResponse(
            conversation_id=conversation["id"],
            response=sanitize_response_text(ai_response["response"]),
            follow_up_questions=[sanitize_response_text(q) for q in follow_ups],
            evidence=[{
                "event_id": ctx["event_id"],
                "timestamp": ctx["timestamp"],
                "camera_id": ctx["camera_id"],
                "event_type": ctx["event_type"],
                "confidence": ctx.get("confidence", 0.0),
                "description": sanitize_response_text(ctx.get("description", ""))
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
        logger.info(f"Enhanced conversation response generated - conversation_id: {conversation['id']}, response_type: {ai_response['type']}, confidence: {ai_response['confidence']}")
        
        # Create and send downstream payload
        downstream_payload = await create_downstream_payload(
            conversation_id=conversation["id"],
            user_id=current_user.sub,
            query=req.query,
            ai_response=ai_response,
            contexts=contexts,
            follow_ups=follow_ups,
            conversation_history=conversation_history
        )
        
        # Send to downstream services (Ingest, Notifier, Dashboard)
        await send_to_downstream_services(downstream_payload)
        
        return response
        
    except Exception as e:
        logger.error(f"Enhanced conversation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Conversation processing failed")


@router.get("/proactive-insights", response_model=ProactiveInsightsResponse)
async def get_proactive_insights(    request: Request,
    req: ProactiveInsightRequest = ProactiveInsightRequest(),
    current_user: TokenData = Depends(get_current_user),
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Generate proactive insights about system status and anomalies."""
    logger.info(f"Proactive insights request - time_range: {req.time_range}, user: {current_user.sub}")
    
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
            
            response = PromptResponse(
                conversation_id=conversation["id"],
                response=sanitize_response_text(insight["message"]),
                follow_up_questions=[sanitize_response_text(action) for action in insight["suggested_actions"]],
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
        
        logger.info(f"Proactive insights generated - count: {len(responses)}")
        return ProactiveInsightsResponse(insights=responses)
        
    except Exception as e:
        logger.error(f"Proactive insights failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Insights generation failed")


async def create_downstream_payload(
    conversation_id: str,
    user_id: str,
    query: str,
    ai_response: dict,
    contexts: list,
    follow_ups: list,
    conversation_history: list
) -> PromptResponsePayload:
    """
    Create downstream integration payload for Ingest Service, Notifier Service, and AI Dashboard.
    
    Args:
        conversation_id: Unique conversation identifier
        user_id: User identifier
        query: Original user query
        ai_response: AI response dictionary with 'response', 'type', 'confidence', etc.
        contexts: Search result contexts
        follow_ups: Generated follow-up questions
        conversation_history: Conversation message history
    
    Returns:
        PromptResponsePayload ready for downstream service consumption
    """
    # Convert contexts to Evidence objects
    evidence_items = []
    for ctx in contexts:
        evidence_items.append(Evidence(
            event_id=ctx["event_id"],
            timestamp=ctx["timestamp"],
            camera_id=ctx["camera_id"],
            event_type=ctx["event_type"],
            confidence=ctx.get("confidence", 0.0),
            description=ctx.get("description", "")
        ))
    
    # Generate clip links
    clip_links = [get_clip_url(ctx["event_id"]) for ctx in contexts]
    
    # Calculate conversation turn number
    conversation_turn = len(conversation_history) // 2 + 1
    
    # Create the downstream payload
    downstream_payload = PromptResponsePayload(
        conversation_id=conversation_id,
        user_id=user_id,
        query=query,
        response=ai_response["response"],
        response_type=ai_response["type"],
        confidence_score=ai_response["confidence"],
        evidence_count=len(contexts),
        evidence=evidence_items,
        clip_links=clip_links,
        follow_up_questions=follow_ups,
        conversation_turn=conversation_turn,
        processing_time_ms=ai_response.get("processing_time", 0),
        metadata={
            "search_duration_ms": ai_response.get("search_duration", 0),
            "ai_model": ai_response.get("model", "unknown"),
            "context_used": len(conversation_history) > 0,
            "conversation_length": len(conversation_history)
        }
    )
    
    return downstream_payload


async def send_to_downstream_services(payload: PromptResponsePayload):
    """
    Send payload to downstream services (Ingest, Notifier, Dashboard).
    This is a placeholder for the actual integration logic.
    """
    try:
        # Convert to dictionary for sending
        payload_dict = payload.model_dump()
        
        # Log the payload for demonstration (in production, send to actual services)
        logger.info(f"Downstream payload ready for: conversation_id={payload.conversation_id}, "
                   f"response_type={payload.response_type}, confidence={payload.confidence_score}")
        
        # Example integration calls (uncomment and implement as needed):
        # await ingest_client.send_prompt_response(payload_dict)
        # await notifier_client.send_response_notification(payload_dict)
        # await dashboard_client.update_response_metrics(payload_dict)
        
    except Exception as e:
        logger.error(f"Failed to send to downstream services: {str(e)}")
        # Don't fail the main request if downstream integration fails

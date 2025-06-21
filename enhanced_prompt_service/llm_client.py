"""
Enhanced LLM client for conversational responses and intelligent follow-up generation.
"""
import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from fastapi import HTTPException

from shared.config import get_service_config
from shared.logging_config import get_logger

logger = get_logger(__name__)

# Get service configuration
config = get_service_config("enhanced_prompt_service")

# Initialize OpenAI client
client = OpenAI(api_key=config["openai_api_key"])

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, max=10),
    reraise=True
)
def call_openai_with_circuit_breaker(model: str, messages: List[Dict], **kwargs) -> Any:
    """
    Call OpenAI API with circuit breaker protection.
    Retries up to 3 times with exponential backoff.
    """
    try:
        logger.info("Calling OpenAI API", extra={"model": model, "attempt": "starting"})
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        logger.info("OpenAI API call successful", extra={"model": model})
        return response
    except Exception as e:
        logger.error("OpenAI API call failed", extra={"model": model, "error": str(e)})
        raise

# System prompts for different capabilities
CONVERSATIONAL_SYSTEM_PROMPT = """You are an intelligent surveillance system assistant with expertise in security analysis and anomaly detection. 

You help users understand security events, patterns, and insights from surveillance data. You can:
- Analyze security events and provide insights
- Explain patterns in surveillance data
- Suggest security improvements
- Answer questions about camera systems and events
- Provide contextual information about detected activities

Key guidelines:
- Be conversational and helpful while maintaining professionalism
- Use technical terms when appropriate but explain them clearly
- Reference specific events, cameras, or timestamps when available
- Provide actionable insights and recommendations
- Ask clarifying questions when needed
- Consider the conversation history and context

Always maintain security awareness and provide accurate, helpful responses based on the surveillance data and context provided."""

FOLLOW_UP_SYSTEM_PROMPT = """You are an expert at generating intelligent follow-up questions for surveillance system interactions.

Based on the user's query and the assistant's response, generate relevant follow-up questions that would help the user:
- Dive deeper into security analysis
- Explore related events or patterns
- Take preventive actions
- Better understand the surveillance system
- Access additional relevant information

Generate 3-5 concise, actionable follow-up questions that are:
- Directly related to the current context
- Progressively more specific or actionable
- Helpful for security analysis and decision-making
- Natural extensions of the current conversation

Output as a JSON array of strings containing the follow-up questions."""

def generate_conversational_response(
    query: str,
    conversation_history: List[Dict[str, str]],
    search_results: List[Dict[str, Any]],
    system_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a conversational response considering conversation history and search results.
    
    Args:
        query: Current user query
        conversation_history: List of previous messages in conversation
        search_results: Relevant search results from RAG system
        system_context: Additional system context (proactive insights, patterns, etc.)
    
    Returns:
        Dict with response text, confidence, and metadata
    """
    
    # Build context from search results
    context_lines = []
    evidence_ids = []
    
    for idx, result in enumerate(search_results, start=1):
        context_lines.append(
            f"{idx}. Event ID: {result.get('event_id', 'N/A')}\n"
            f"   Time: {result.get('timestamp', 'N/A')}\n"
            f"   Camera: {result.get('camera_id', 'N/A')}\n"
            f"   Type: {result.get('event_type', 'N/A')}\n"
            f"   Details: {result.get('details', 'N/A')}\n"
            f"   Confidence: {result.get('confidence', 'N/A')}"
        )
        if result.get('event_id'):
            evidence_ids.append(str(result['event_id']))
    
    # Build conversation context
    conversation_context = ""
    if conversation_history:
        conversation_context = "Previous conversation:\n"
        for msg in conversation_history[-5:]:  # Include last 5 messages for context
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            conversation_context += f"{role.title()}: {content}\n"
        conversation_context += "\n"
    
    # Build system context
    system_context_text = ""
    if system_context:
        if system_context.get('proactive_insights'):
            system_context_text += f"System Insights: {'; '.join(system_context['proactive_insights'])}\n"
        if system_context.get('patterns'):
            system_context_text += f"Detected Patterns: {system_context['patterns']}\n"
        if system_context.get('anomalies'):
            system_context_text += f"Recent Anomalies: {system_context['anomalies']}\n"
    
    # Construct the user message
    user_content = f"""Current Query: {query}

{conversation_context}Available Context:
{chr(10).join(context_lines) if context_lines else "No specific events found."}

{system_context_text}Please provide a helpful, conversational response that:
1. Directly addresses the user's query
2. References relevant events or patterns when available
3. Considers the conversation history
4. Provides actionable insights or recommendations
5. Maintains a professional but approachable tone"""
    
    messages = [
        {"role": "system", "content": CONVERSATIONAL_SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]
    
    try:
        # Generate response using OpenAI with circuit breaker
        resp = call_openai_with_circuit_breaker(
            model=config["openai_model"],
            messages=messages,
            temperature=0.7,  # Slightly higher for more conversational responses
            max_tokens=1000,
        )
        
        response_text = resp.choices[0].message.content
        
        # Calculate confidence based on available context
        confidence = 0.5  # Base confidence
        if search_results:
            confidence += 0.3  # Boost for relevant search results
        if conversation_history:
            confidence += 0.1  # Boost for conversation context
        if system_context:
            confidence += 0.1  # Boost for system context
        
        confidence = min(confidence, 1.0)
        
        return {
            "response": response_text,
            "confidence": confidence,
            "evidence_ids": evidence_ids,
            "context_used": len(search_results),
            "has_conversation_context": len(conversation_history) > 0,
            "metadata": {
                "model_used": config["openai_model"],
                "temperature": 0.7,
                "tokens_used": resp.usage.total_tokens if resp.usage else None,
                "system_insights": bool(system_context)
            }
        }
        
    except RetryError as e:
        logger.error("OpenAI API retry exhausted", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail="Upstream service unavailable")
    except Exception as e:
        logger.error("Failed to generate conversational response", extra={"error": str(e)})
        raise ValueError(f"Failed to generate conversational response: {e}")

def generate_follow_up_questions(
    query: str,
    response: str,
    conversation_history: List[Dict[str, str]],
    search_results: List[Dict[str, Any]]
) -> List[str]:
    """
    Generate intelligent follow-up questions based on the conversation context.
    
    Args:
        query: User's original query
        response: Assistant's response
        conversation_history: Previous conversation messages
        search_results: Relevant search results used in response
    
    Returns:
        List of follow-up question strings
    """
    
    # Build context for follow-up generation
    context_summary = ""
    if search_results:
        event_types = list(set(r.get('event_type', 'unknown') for r in search_results))
        cameras = list(set(r.get('camera_id', 'unknown') for r in search_results))
        context_summary = f"Events involve: {', '.join(event_types[:3])}. Cameras: {', '.join(cameras[:3])}"
    
    conversation_summary = ""
    if conversation_history:
        # Summarize recent conversation topics
        recent_queries = [msg.get('content', '') for msg in conversation_history[-3:] if msg.get('role') == 'user']
        if recent_queries:
            conversation_summary = f"Recent topics: {'; '.join(recent_queries)}"
    
    user_content = f"""User Query: {query}

Assistant Response: {response}

{conversation_summary}

{context_summary}

Generate 3-5 intelligent follow-up questions that would help the user:
1. Explore deeper analysis of the current situation
2. Take preventive or corrective actions
3. Understand related patterns or trends
4. Access additional relevant information
5. Improve security posture

Focus on actionable, specific questions that build on the current context."""

    messages = [
        {"role": "system", "content": FOLLOW_UP_SYSTEM_PROMPT},
        {"role": "user", "content": user_content}    ]
    
    try:
        # Generate follow-up questions with circuit breaker
        resp = call_openai_with_circuit_breaker(
            model=config["openai_model"],
            messages=messages,
            temperature=0.6,
            max_tokens=400,
        )
        
        questions_text = resp.choices[0].message.content
        
        # Parse JSON response
        try:
            questions = json.loads(questions_text)
            if isinstance(questions, list):
                return [str(q) for q in questions[:5]]  # Limit to 5 questions            else:
                # Fallback: try to extract questions from text
                return _extract_questions_from_text(questions_text)
        except json.JSONDecodeError:
            # Fallback: extract questions from text response
            return _extract_questions_from_text(questions_text)
            
    except RetryError as e:
        logger.error("OpenAI API retry exhausted for follow-up questions", extra={"error": str(e)})
        # Return default follow-up questions on error
        return _get_default_follow_ups(query, search_results)
    except Exception as e:
        logger.error("Failed to generate follow-up questions", extra={"error": str(e)})
        # Return default follow-up questions on error
        return _get_default_follow_ups(query, search_results)

def _extract_questions_from_text(text: str) -> List[str]:
    """Extract questions from text response when JSON parsing fails."""
    questions = []
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if line and ('?' in line or line.lower().startswith(('what', 'how', 'when', 'where', 'why', 'which', 'can', 'should', 'would', 'could'))):
            # Clean up common prefixes
            for prefix in ['1. ', '2. ', '3. ', '4. ', '5. ', '- ', '• ', '* ']:
                if line.startswith(prefix):
                    line = line[len(prefix):].strip()
            if line:
                questions.append(line)
    
    return questions[:5]

def _get_default_follow_ups(query: str, search_results: List[Dict[str, Any]]) -> List[str]:
    """Generate default follow-up questions when LLM generation fails."""
    defaults = [
        "Can you show me more details about these events?",
        "Are there any patterns in the timing of these incidents?",
        "What preventive measures would you recommend?",
        "How can I set up alerts for similar events?"
    ]
    
    # Customize based on available context
    if search_results:
        cameras = list(set(r.get('camera_id', '') for r in search_results if r.get('camera_id')))
        if cameras:
            defaults.append(f"What other recent activity has occurred on {cameras[0]}?")
    
    return defaults[:4]

def generate_proactive_insights(
    recent_events: List[Dict[str, Any]],
    patterns: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Generate proactive insights based on recent system activity.
    
    Args:
        recent_events: Recent surveillance events
        patterns: Detected patterns or anomalies
    
    Returns:
        List of insight strings
    """
    
    if not recent_events and not patterns:
        return []
    
    context_lines = []
    for event in recent_events[:10]:  # Limit to recent 10 events
        context_lines.append(
            f"- {event.get('timestamp', 'N/A')}: {event.get('event_type', 'N/A')} "
            f"on {event.get('camera_id', 'N/A')}"
        )
    
    patterns_text = ""
    if patterns:
        patterns_text = f"Detected patterns: {json.dumps(patterns, indent=2)}"
    
    user_content = f"""Recent surveillance activity:
{chr(10).join(context_lines)}

{patterns_text}

Based on this recent activity, provide 2-3 concise proactive insights about:
1. Security patterns or trends
2. Potential risks or concerns
3. Recommended actions or monitoring focus

Keep insights brief, actionable, and focused on security implications."""

    messages = [
        {
            "role": "system", 
            "content": "You are a security analyst providing proactive insights. Generate brief, actionable security insights based on surveillance patterns."
        },
        {"role": "user", "content": user_content}    ]
    
    try:
        resp = call_openai_with_circuit_breaker(
            model=config["openai_model"],
            messages=messages,
            temperature=0.3,
            max_tokens=300,
        )
        
        insights_text = resp.choices[0].message.content
        
        # Extract insights from response
        insights = []
        lines = insights_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.lower().startswith(('based on', 'here are', 'the following')):                # Clean up prefixes
                for prefix in ['1. ', '2. ', '3. ', '- ', '• ', '* ']:
                    if line.startswith(prefix):
                        line = line[len(prefix):].strip()
                if line:
                    insights.append(line)
        
        return insights[:3]  # Limit to 3 insights
        
    except RetryError as e:
        logger.error("OpenAI API retry exhausted for proactive insights", extra={"error": str(e)})
        # Return fallback insights
        return [
            "Monitor for unusual activity patterns",
            "Review recent high-confidence detections",
            "Consider updating security protocols"
        ]
    except Exception as e:
        logger.error("Failed to generate proactive insights", extra={"error": str(e)})
        # Return fallback insights
        return [
            "Monitor for unusual activity patterns",
            "Review recent high-confidence detections",
            "Consider updating security protocols"
        ]

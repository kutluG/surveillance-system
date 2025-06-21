"""
History-related API endpoints for the Enhanced Prompt Service.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from shared.logging_config import get_logger
from shared.auth import get_current_user, TokenData
from slowapi import Limiter
from slowapi.util import get_remote_address

from enhanced_prompt_service.schemas import HistoryResponse, ConversationDeleteResponse
from enhanced_prompt_service.conversation_manager import ConversationManager

logger = get_logger(__name__)

router = APIRouter()

# Rate limiter - will be initialized in main.py
limiter = Limiter(key_func=get_remote_address)


# Dependency injection functions
async def get_conversation_manager(request: Request) -> ConversationManager:
    """Get ConversationManager from app state."""
    return request.app.state.conversation_manager


@router.get("/{conversation_id}", response_model=HistoryResponse)
async def get_conversation_history(
    request: Request,
    conversation_id: str,
    limit: int = 50,
    current_user: TokenData = Depends(get_current_user),
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Get conversation history for a specific conversation."""
    try:
        messages = await conversation_manager.get_recent_messages(
            conversation_id, 
            limit=limit
        )
        return HistoryResponse(conversation_id=conversation_id, messages=messages)
    except Exception as e:
        logger.error("Failed to get conversation history", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation history")


@router.delete("/{conversation_id}", response_model=ConversationDeleteResponse)
async def delete_conversation(
    request: Request,
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user),
    conversation_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Delete a conversation and its history."""
    try:
        await conversation_manager.delete_conversation(conversation_id)
        return ConversationDeleteResponse(message="Conversation deleted successfully")
    except Exception as e:
        logger.error("Failed to delete conversation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

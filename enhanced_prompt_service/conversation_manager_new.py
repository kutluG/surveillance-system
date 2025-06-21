"""
Conversation Manager: Handle multi-turn conversations with Redis-based memory.
"""
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import redis.asyncio as redis

from shared.logging_config import get_logger, log_context

logger = get_logger("conversation_manager")

class ConversationManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.conversation_ttl = 86400 * 7  # 7 days
        self.message_ttl = 86400 * 30  # 30 days
        
    async def create_conversation(
        self, 
        user_id: str, 
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new conversation."""
        conversation_id = str(uuid.uuid4())
        
        conversation = {
            "id": conversation_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "context": initial_context or {},
            "message_count": 0,
            "status": "active"
        }
        
        # Store conversation metadata
        conversation_key = f"conversation:{conversation_id}"
        await self.redis.setex(
            conversation_key,
            self.conversation_ttl,
            json.dumps(conversation)
        )
        
        # Add to user's conversation list
        user_conversations_key = f"user_conversations:{user_id}"
        await self.redis.zadd(
            user_conversations_key,
            {conversation_id: datetime.utcnow().timestamp()}
        )
        await self.redis.expire(user_conversations_key, self.conversation_ttl)
        
        logger.info("Created conversation", extra={"conversation_id": conversation_id, "user_id": user_id})
        return conversation
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        conversation_key = f"conversation:{conversation_id}"
        conversation_data = await self.redis.get(conversation_key)
        
        if conversation_data:
            return json.loads(conversation_data)
        
        logger.warning(f"Conversation not found: {conversation_id}")
        return None
    
    async def update_conversation(
        self, 
        conversation_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """Update conversation metadata."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False
            
        conversation.update(updates)
        conversation["last_activity"] = datetime.utcnow().isoformat()
        
        conversation_key = f"conversation:{conversation_id}"
        await self.redis.setex(
            conversation_key,
            self.conversation_ttl,
            json.dumps(conversation)
        )
        
        return True
    
    async def add_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a message to the conversation."""
        message_id = str(uuid.uuid4())
        
        message = {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,  # "user" or "assistant"
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Store message
        message_key = f"message:{message_id}"
        await self.redis.setex(
            message_key,
            self.message_ttl,
            json.dumps(message)
        )
        
        # Add to conversation message list
        messages_key = f"conversation_messages:{conversation_id}"
        await self.redis.zadd(
            messages_key,
            {message_id: datetime.utcnow().timestamp()}
        )
        await self.redis.expire(messages_key, self.conversation_ttl)
        
        # Update conversation metadata
        await self.update_conversation(conversation_id, {
            "message_count": await self.get_message_count(conversation_id)
        })
        
        logger.info("Added message", 
                   conversation_id=conversation_id, 
                   message_id=message_id, 
                   role=role)
        
        return message_id
    
    async def get_recent_messages(
        self, 
        conversation_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent messages from a conversation."""
        messages_key = f"conversation_messages:{conversation_id}"
        
        # Get message IDs in reverse chronological order
        message_ids = await self.redis.zrevrange(messages_key, 0, limit - 1)
        
        messages = []
        for message_id in message_ids:
            message_key = f"message:{message_id.decode()}"
            message_data = await self.redis.get(message_key)
            if message_data:
                message = json.loads(message_data)
                # Ensure timestamp exists for sorting
                if "timestamp" not in message:
                    message["timestamp"] = datetime.utcnow().isoformat()
                messages.append(message)
        
        # Sort by timestamp (oldest first for conversation context)
        messages.sort(key=lambda x: x.get("timestamp", ""))
        
        return messages
    
    async def get_message_count(self, conversation_id: str) -> int:
        """Get total message count for a conversation."""
        messages_key = f"conversation_messages:{conversation_id}"
        return await self.redis.zcard(messages_key)
    
    async def get_user_conversations(
        self, 
        user_id: str, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get user's recent conversations."""
        user_conversations_key = f"user_conversations:{user_id}"
        
        # Get conversation IDs in reverse chronological order
        conversation_ids = await self.redis.zrevrange(user_conversations_key, 0, limit - 1)
        
        conversations = []
        for conversation_id in conversation_ids:
            conversation = await self.get_conversation(conversation_id.decode())
            if conversation:
                conversations.append(conversation)
        
        return conversations
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        # Delete all messages
        messages_key = f"conversation_messages:{conversation_id}"
        message_ids = await self.redis.zrange(messages_key, 0, -1)
        
        async with self.redis.pipeline() as pipe:
            for message_id in message_ids:
                message_key = f"message:{message_id.decode()}"
                pipe.delete(message_key)
            
            # Delete conversation metadata and message list
            conversation_key = f"conversation:{conversation_id}"
            pipe.delete(conversation_key)
            pipe.delete(messages_key)
            
            # Remove from user's conversation list
            user_conversations_key = f"user_conversations:{conversation['user_id']}"
            pipe.zrem(user_conversations_key, conversation_id)
            
            await pipe.execute()
        
        logger.info("Deleted conversation", extra={"conversation_id": conversation_id})
        return True
    
    async def cleanup_expired_conversations(self) -> int:
        """Clean up expired conversations (called by background task)."""
        cleaned_count = 0
        
        # This is a simplified cleanup - in production, you'd want more sophisticated logic
        # to handle TTL expiration automatically
        
        return cleaned_count
    
    async def get_conversation_summary(self, conversation_id: str) -> Optional[str]:
        """Generate a summary of the conversation for context."""
        messages = await self.get_recent_messages(conversation_id, limit=10)
        
        if not messages:
            return None
        
        # Simple summary generation - could be enhanced with AI
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        if user_messages:
            latest_query = user_messages[-1]["content"]
            return f"Recent conversation about: {latest_query[:100]}..."
        
        return "Conversation in progress"
    
    async def update_conversation_context(
        self, 
        conversation_id: str, 
        context_updates: Dict[str, Any]
    ) -> bool:
        """Update conversation context with new information."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        current_context = conversation.get("context", {})
        current_context.update(context_updates)
        
        return await self.update_conversation(conversation_id, {
            "context": current_context
        })

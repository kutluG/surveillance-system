"""
Unit tests for conversation_manager.py
"""
import pytest
import json
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import redis

# Mock the shared.logging_config module before importing ConversationManager
import sys
from unittest.mock import Mock as MockLogger

# Create a mock logger
mock_logger = MockLogger()
mock_logger.info = Mock()
mock_logger.warning = Mock()
mock_logger.error = Mock()

# Patch the module before importing
sys.modules['shared.logging_config'] = Mock()
sys.modules['shared.logging_config'].get_logger = Mock(return_value=mock_logger)
sys.modules['shared.logging_config'].log_context = Mock()

from conversation_manager import ConversationManager


class TestConversationManager:
    """Test cases for ConversationManager class."""
    
    @pytest.fixture
    def redis_client(self):
        """Mock Redis client."""
        return Mock(spec=redis.Redis)
    
    @pytest.fixture
    def manager(self, redis_client):
        """ConversationManager instance with mock Redis."""
        return ConversationManager(redis_client)
    
    @pytest.fixture
    def sample_conversation(self):
        """Sample conversation data."""
        return {
            "id": "conv-123",
            "user_id": "user-456",
            "created_at": "2025-06-18T10:00:00",
            "last_activity": "2025-06-18T10:00:00",
            "context": {"test": "context"},
            "message_count": 0,
            "status": "active"
        }
    
    @pytest.fixture
    def sample_message(self):
        """Sample message data."""
        return {
            "id": "msg-789",
            "conversation_id": "conv-123",
            "role": "user",
            "content": "Test message",
            "timestamp": "2025-06-18T10:05:00",
            "metadata": {"source": "web"}
        }

    # Test create_conversation
    @pytest.mark.asyncio
    async def test_create_conversation_success(self, manager, redis_client):
        """Test successful conversation creation."""
        user_id = "test-user-123"
        initial_context = {"camera": "main_entrance"}
        
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="test-conv-id")
            
            result = await manager.create_conversation(user_id, initial_context)
            
            # Verify conversation structure
            assert result["id"] == "test-conv-id"
            assert result["user_id"] == user_id
            assert result["context"] == initial_context
            assert result["message_count"] == 0
            assert result["status"] == "active"
            assert "created_at" in result
            assert "last_activity" in result
            
            # Verify Redis calls
            redis_client.setex.assert_called()
            redis_client.zadd.assert_called()
            redis_client.expire.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_conversation_no_initial_context(self, manager, redis_client):
        """Test conversation creation without initial context."""
        user_id = "test-user-123"
        
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="test-conv-id")
            
            result = await manager.create_conversation(user_id)
            
            assert result["context"] == {}
            assert result["user_id"] == user_id
    
    @pytest.mark.asyncio
    async def test_create_conversation_redis_error(self, manager, redis_client):
        """Test conversation creation with Redis error."""
        redis_client.setex.side_effect = redis.RedisError("Connection failed")
        
        with pytest.raises(redis.RedisError):
            await manager.create_conversation("test-user")

    # Test get_conversation
    @pytest.mark.asyncio
    async def test_get_conversation_found(self, manager, redis_client, sample_conversation):
        """Test retrieving an existing conversation."""
        conversation_id = "conv-123"
        redis_client.get.return_value = json.dumps(sample_conversation).encode()
        
        result = await manager.get_conversation(conversation_id)
        
        assert result == sample_conversation
        redis_client.get.assert_called_with(f"conversation:{conversation_id}")
    
    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, manager, redis_client):
        """Test retrieving a non-existent conversation."""
        conversation_id = "nonexistent"
        redis_client.get.return_value = None
        
        result = await manager.get_conversation(conversation_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_conversation_invalid_json(self, manager, redis_client):
        """Test retrieving conversation with invalid JSON data."""
        conversation_id = "conv-123"
        redis_client.get.return_value = b"invalid-json"
        
        with pytest.raises(json.JSONDecodeError):
            await manager.get_conversation(conversation_id)

    # Test update_conversation
    @pytest.mark.asyncio
    async def test_update_conversation_success(self, manager, redis_client, sample_conversation):
        """Test successful conversation update."""
        conversation_id = "conv-123"
        updates = {"status": "inactive", "new_field": "new_value"}
        
        # Mock get_conversation to return sample conversation
        with patch.object(manager, 'get_conversation', return_value=sample_conversation):
            result = await manager.update_conversation(conversation_id, updates)
            
            assert result is True
            redis_client.setex.assert_called()
            
            # Verify the call includes updated data
            call_args = redis_client.setex.call_args
            stored_data = json.loads(call_args[0][2])
            assert stored_data["status"] == "inactive"
            assert stored_data["new_field"] == "new_value"
            assert "last_activity" in stored_data
    
    @pytest.mark.asyncio
    async def test_update_conversation_not_found(self, manager, redis_client):
        """Test updating a non-existent conversation."""
        conversation_id = "nonexistent"
        updates = {"status": "inactive"}
        
        with patch.object(manager, 'get_conversation', return_value=None):
            result = await manager.update_conversation(conversation_id, updates)
            
            assert result is False
            redis_client.setex.assert_not_called()

    # Test add_message
    @pytest.mark.asyncio
    async def test_add_message_success(self, manager, redis_client):
        """Test successful message addition."""
        conversation_id = "conv-123"
        role = "user"
        content = "Test message content"
        metadata = {"source": "mobile"}
        
        # Mock get_message_count
        with patch.object(manager, 'get_message_count', return_value=1):
            with patch.object(manager, 'update_conversation', return_value=True):
                with patch('uuid.uuid4') as mock_uuid:
                    mock_uuid.return_value = Mock()
                    mock_uuid.return_value.__str__ = Mock(return_value="msg-456")
                    
                    result = await manager.add_message(conversation_id, role, content, metadata)
                    
                    assert result == "msg-456"
                    
                    # Verify Redis operations
                    redis_client.setex.assert_called()  # Store message
                    redis_client.zadd.assert_called()   # Add to message list
                    redis_client.expire.assert_called() # Set expiry
                    
                    # Verify message structure
                    message_call = None
                    for call in redis_client.setex.call_args_list:
                        if call[0][0].startswith("message:"):
                            message_call = call
                            break
                    
                    assert message_call is not None
                    stored_message = json.loads(message_call[0][2])
                    assert stored_message["role"] == role
                    assert stored_message["content"] == content
                    assert stored_message["metadata"] == metadata
    
    @pytest.mark.asyncio
    async def test_add_message_no_metadata(self, manager, redis_client):
        """Test adding message without metadata."""
        conversation_id = "conv-123"
        role = "assistant"
        content = "Response content"
        
        with patch.object(manager, 'get_message_count', return_value=1):
            with patch.object(manager, 'update_conversation', return_value=True):
                with patch('uuid.uuid4') as mock_uuid:
                    mock_uuid.return_value = Mock()
                    mock_uuid.return_value.__str__ = Mock(return_value="msg-789")
                    
                    result = await manager.add_message(conversation_id, role, content)
                    
                    assert result == "msg-789"

    # Test get_recent_messages
    @pytest.mark.asyncio
    async def test_get_recent_messages_success(self, manager, redis_client, sample_message):
        """Test retrieving recent messages."""
        conversation_id = "conv-123"
        message_ids = [b"msg-1", b"msg-2", b"msg-3"]
        
        redis_client.zrevrange.return_value = message_ids
        
        # Mock Redis get calls for individual messages
        def mock_get(key):
            if key == "message:msg-1":
                msg1 = sample_message.copy()
                msg1["id"] = "msg-1"
                msg1["timestamp"] = "2025-06-18T10:00:00"
                return json.dumps(msg1).encode()
            elif key == "message:msg-2":
                msg2 = sample_message.copy()
                msg2["id"] = "msg-2"
                msg2["timestamp"] = "2025-06-18T10:01:00"
                return json.dumps(msg2).encode()
            elif key == "message:msg-3":
                msg3 = sample_message.copy()
                msg3["id"] = "msg-3"
                msg3["timestamp"] = "2025-06-18T10:02:00"
                return json.dumps(msg3).encode()
            return None
        
        redis_client.get.side_effect = mock_get
        
        result = await manager.get_recent_messages(conversation_id, limit=10)
        
        assert len(result) == 3
        # Verify messages are sorted by timestamp (oldest first)
        timestamps = [msg["timestamp"] for msg in result]
        assert timestamps == sorted(timestamps)
        
        redis_client.zrevrange.assert_called_with(f"conversation_messages:{conversation_id}", 0, 9)
    
    @pytest.mark.asyncio
    async def test_get_recent_messages_empty(self, manager, redis_client):
        """Test retrieving messages from conversation with no messages."""
        conversation_id = "empty-conv"
        redis_client.zrevrange.return_value = []
        
        result = await manager.get_recent_messages(conversation_id)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_recent_messages_missing_message(self, manager, redis_client):
        """Test handling of missing individual messages."""
        conversation_id = "conv-123"
        message_ids = [b"msg-1", b"msg-missing"]
        
        redis_client.zrevrange.return_value = message_ids
        
        def mock_get(key):
            if key == "message:msg-1":
                return json.dumps({"id": "msg-1", "content": "test"}).encode()
            return None  # Simulate missing message
        
        redis_client.get.side_effect = mock_get
        
        result = await manager.get_recent_messages(conversation_id)
        
        assert len(result) == 1
        assert result[0]["id"] == "msg-1"

    # Test get_message_count
    @pytest.mark.asyncio
    async def test_get_message_count(self, manager, redis_client):
        """Test getting message count for a conversation."""
        conversation_id = "conv-123"
        expected_count = 5
        redis_client.zcard.return_value = expected_count
        
        result = await manager.get_message_count(conversation_id)
        
        assert result == expected_count
        redis_client.zcard.assert_called_with(f"conversation_messages:{conversation_id}")

    # Test get_user_conversations
    @pytest.mark.asyncio
    async def test_get_user_conversations(self, manager, redis_client, sample_conversation):
        """Test retrieving user's conversations."""
        user_id = "user-123"
        conversation_ids = [b"conv-1", b"conv-2"]
        
        redis_client.zrevrange.return_value = conversation_ids
        
        # Mock get_conversation calls
        async def mock_get_conversation(conv_id):
            if conv_id == "conv-1":
                conv1 = sample_conversation.copy()
                conv1["id"] = "conv-1"
                return conv1
            elif conv_id == "conv-2":
                conv2 = sample_conversation.copy()
                conv2["id"] = "conv-2"
                return conv2
            return None
        
        with patch.object(manager, 'get_conversation', side_effect=mock_get_conversation):
            result = await manager.get_user_conversations(user_id, limit=10)
            
            assert len(result) == 2
            assert result[0]["id"] == "conv-1"
            assert result[1]["id"] == "conv-2"
            
            redis_client.zrevrange.assert_called_with(f"user_conversations:{user_id}", 0, 9)
    
    @pytest.mark.asyncio
    async def test_get_user_conversations_with_missing(self, manager, redis_client):
        """Test handling of missing conversations in user list."""
        user_id = "user-123"
        conversation_ids = [b"conv-1", b"conv-missing"]
        
        redis_client.zrevrange.return_value = conversation_ids
        
        async def mock_get_conversation(conv_id):
            if conv_id == "conv-1":
                return {"id": "conv-1", "user_id": user_id}
            return None  # Simulate missing conversation
        
        with patch.object(manager, 'get_conversation', side_effect=mock_get_conversation):
            result = await manager.get_user_conversations(user_id)
            
            assert len(result) == 1
            assert result[0]["id"] == "conv-1"

    # Test delete_conversation
    @pytest.mark.asyncio
    async def test_delete_conversation_success(self, manager, redis_client, sample_conversation):
        """Test successful conversation deletion."""
        conversation_id = "conv-123"
        message_ids = [b"msg-1", b"msg-2"]
        
        redis_client.zrange.return_value = message_ids
        
        # Mock pipeline
        pipeline_mock = Mock()
        redis_client.pipeline.return_value = pipeline_mock
        
        with patch.object(manager, 'get_conversation', return_value=sample_conversation):
            result = await manager.delete_conversation(conversation_id)
            
            assert result is True
            
            # Verify pipeline operations
            assert pipeline_mock.delete.call_count >= 2  # Messages + conversation + message list
            pipeline_mock.zrem.assert_called()  # Remove from user conversations
            pipeline_mock.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_delete_conversation_not_found(self, manager, redis_client):
        """Test deleting non-existent conversation."""
        conversation_id = "nonexistent"
        
        with patch.object(manager, 'get_conversation', return_value=None):
            result = await manager.delete_conversation(conversation_id)
            
            assert result is False
            redis_client.pipeline.assert_not_called()

    # Test cleanup_expired_conversations
    @pytest.mark.asyncio
    async def test_cleanup_expired_conversations(self, manager):
        """Test cleanup of expired conversations."""
        # This is a placeholder implementation in the original code
        result = await manager.cleanup_expired_conversations()
        
        assert isinstance(result, int)
        assert result >= 0

    # Test get_conversation_summary
    @pytest.mark.asyncio
    async def test_get_conversation_summary_with_messages(self, manager, sample_message):
        """Test generating conversation summary with messages."""
        conversation_id = "conv-123"
        messages = [
            {**sample_message, "role": "user", "content": "What's the weather like?"},
            {**sample_message, "role": "assistant", "content": "It's sunny today."},
            {**sample_message, "role": "user", "content": "Show me security events from today"}
        ]
        
        with patch.object(manager, 'get_recent_messages', return_value=messages):
            result = await manager.get_conversation_summary(conversation_id)
            
            assert result is not None
            assert "Show me security events from today" in result
    
    @pytest.mark.asyncio
    async def test_get_conversation_summary_no_messages(self, manager):
        """Test generating summary for conversation with no messages."""
        conversation_id = "empty-conv"
        
        with patch.object(manager, 'get_recent_messages', return_value=[]):
            result = await manager.get_conversation_summary(conversation_id)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_conversation_summary_no_user_messages(self, manager, sample_message):
        """Test generating summary with only assistant messages."""
        conversation_id = "conv-123"
        messages = [
            {**sample_message, "role": "assistant", "content": "Hello, how can I help?"}
        ]
        
        with patch.object(manager, 'get_recent_messages', return_value=messages):
            result = await manager.get_conversation_summary(conversation_id)
            
            assert result == "Conversation in progress"

    # Test update_conversation_context
    @pytest.mark.asyncio
    async def test_update_conversation_context_success(self, manager, sample_conversation):
        """Test updating conversation context."""
        conversation_id = "conv-123"
        context_updates = {"new_key": "new_value", "camera_focus": "parking_lot"}
        
        with patch.object(manager, 'get_conversation', return_value=sample_conversation):
            with patch.object(manager, 'update_conversation', return_value=True) as mock_update:
                result = await manager.update_conversation_context(conversation_id, context_updates)
                
                assert result is True
                
                # Verify update_conversation was called with merged context
                mock_update.assert_called_once()
                call_args = mock_update.call_args[0]
                updated_context = call_args[1]["context"]
                assert updated_context["new_key"] == "new_value"
                assert updated_context["camera_focus"] == "parking_lot"
    
    @pytest.mark.asyncio
    async def test_update_conversation_context_not_found(self, manager):
        """Test updating context for non-existent conversation."""
        conversation_id = "nonexistent"
        context_updates = {"key": "value"}
        
        with patch.object(manager, 'get_conversation', return_value=None):
            result = await manager.update_conversation_context(conversation_id, context_updates)
            
            assert result is False

    # Test Redis connection failures
    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, manager, redis_client):
        """Test handling of Redis connection failures."""
        redis_client.get.side_effect = redis.ConnectionError("Redis connection failed")
        
        with pytest.raises(redis.ConnectionError):
            await manager.get_conversation("conv-123")
    
    @pytest.mark.asyncio
    async def test_redis_timeout_error(self, manager, redis_client):
        """Test handling of Redis timeout errors."""
        redis_client.setex.side_effect = redis.TimeoutError("Redis timeout")
        
        with pytest.raises(redis.TimeoutError):
            await manager.create_conversation("user-123")

    # Test edge cases and error conditions
    @pytest.mark.asyncio
    async def test_conversation_with_very_long_content(self, manager, redis_client):
        """Test handling of messages with very long content."""
        conversation_id = "conv-123"
        role = "user"
        content = "x" * 10000  # Very long content
        
        with patch.object(manager, 'get_message_count', return_value=1):
            with patch.object(manager, 'update_conversation', return_value=True):
                with patch('uuid.uuid4') as mock_uuid:
                    mock_uuid.return_value = Mock()
                    mock_uuid.return_value.__str__ = Mock(return_value="msg-long")
                    
                    result = await manager.add_message(conversation_id, role, content)
                    
                    assert result == "msg-long"
                    redis_client.setex.assert_called()
    
    @pytest.mark.asyncio
    async def test_conversation_with_special_characters(self, manager, redis_client):
        """Test handling of content with special characters."""
        conversation_id = "conv-123"
        role = "user"
        content = "Test with émojis 🚨 and spéciál chars: < > & \" '"
        
        with patch.object(manager, 'get_message_count', return_value=1):
            with patch.object(manager, 'update_conversation', return_value=True):
                with patch('uuid.uuid4') as mock_uuid:
                    mock_uuid.return_value = Mock()
                    mock_uuid.return_value.__str__ = Mock(return_value="msg-special")
                    
                    result = await manager.add_message(conversation_id, role, content)
                    
                    assert result == "msg-special"
                    
                    # Verify the content was properly JSON encoded
                    call_args = redis_client.setex.call_args_list
                    message_call = None
                    for call in call_args:
                        if call[0][0].startswith("message:"):
                            message_call = call
                            break
                    
                    assert message_call is not None
                    stored_message = json.loads(message_call[0][2])
                    assert stored_message["content"] == content

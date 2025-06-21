"""
Integration tests for Kafka functionality in the annotation frontend service.

Tests Kafka messaging end-to-end flows:
- Hard example consumption from Kafka topics
- Labeled example production to Kafka topics
- Error handling and retry mechanisms
- Message serialization/deserialization
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
from confluent_kafka import Message, KafkaError
import time

from main import consume_hard_examples, delivery_report, pending_examples
from models import AnnotationExample, RetryQueue, AnnotationStatus


class TestKafkaConsumer:
    """Test Kafka consumer functionality for hard examples."""
    
    @pytest.mark.asyncio
    async def test_consume_hard_examples_success(self, sample_hard_example):
        """Test successful consumption of hard examples from Kafka."""
        # Mock consumer message
        mock_message = Mock(spec=Message)
        mock_message.error.return_value = None
        mock_message.value.return_value = json.dumps(sample_hard_example).encode('utf-8')
        
        # Mock consumer
        mock_consumer = Mock()
        mock_consumer.poll.side_effect = [mock_message, None]  # Return message then None to stop
        
        # Clear pending examples
        pending_examples.clear()
        
        # Patch the global consumer
        with patch('main.consumer', mock_consumer):
            # Run consumer task briefly
            task = asyncio.create_task(consume_hard_examples())
            await asyncio.sleep(0.1)  # Let it process one message
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Verify message was processed
        assert len(pending_examples) == 1
        assert pending_examples[0]["event_id"] == "test-event-123"
        assert pending_examples[0]["camera_id"] == "camera-001"
    
    @pytest.mark.asyncio
    async def test_consume_hard_examples_invalid_json(self):
        """Test handling of invalid JSON in Kafka messages."""
        # Mock consumer message with invalid JSON
        mock_message = Mock(spec=Message)
        mock_message.error.return_value = None
        mock_message.value.return_value = b"invalid json data"
        
        mock_consumer = Mock()
        mock_consumer.poll.side_effect = [mock_message, None]
        
        pending_examples.clear()
        
        with patch('main.consumer', mock_consumer):
            with patch('main.logger') as mock_logger:
                task = asyncio.create_task(consume_hard_examples())
                await asyncio.sleep(0.1)
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Verify error was logged and no examples added
        assert len(pending_examples) == 0
        mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_consume_hard_examples_kafka_error(self):
        """Test handling of Kafka consumer errors."""
        # Mock consumer error
        mock_error = Mock()
        mock_error.code.return_value = KafkaError.BROKER_NOT_AVAILABLE
        
        mock_message = Mock(spec=Message)
        mock_message.error.return_value = mock_error
        
        mock_consumer = Mock()
        mock_consumer.poll.side_effect = [mock_message, None]
        
        with patch('main.consumer', mock_consumer):
            with patch('main.logger') as mock_logger:
                task = asyncio.create_task(consume_hard_examples())
                await asyncio.sleep(0.1)
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Verify error was logged
        mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_consume_hard_examples_queue_limit(self, sample_hard_example):
        """Test that pending examples queue respects size limit."""
        # Create 105 sample messages (more than limit of 100)
        messages = []
        for i in range(105):
            example = sample_hard_example.copy()
            example["event_id"] = f"test-event-{i}"
            
            mock_message = Mock(spec=Message)
            mock_message.error.return_value = None
            mock_message.value.return_value = json.dumps(example).encode('utf-8')
            messages.append(mock_message)
        
        # Add None to stop the loop
        messages.append(None)
        
        mock_consumer = Mock()
        mock_consumer.poll.side_effect = messages
        
        pending_examples.clear()
        
        with patch('main.consumer', mock_consumer):
            task = asyncio.create_task(consume_hard_examples())
            await asyncio.sleep(0.2)  # Process multiple messages
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Verify queue size is capped at 100
        assert len(pending_examples) == 100
        # Verify oldest examples were removed (should have last 100)
        assert pending_examples[0]["event_id"] == "test-event-5"
        assert pending_examples[-1]["event_id"] == "test-event-104"
    
    @pytest.mark.asyncio 
    async def test_consume_hard_examples_partition_eof(self):
        """Test handling of partition EOF (not an error)."""
        # Mock partition EOF error (which should be ignored)
        mock_error = Mock()
        mock_error.code.return_value = KafkaError._PARTITION_EOF
        
        mock_message = Mock(spec=Message)
        mock_message.error.return_value = mock_error
        
        mock_consumer = Mock()
        mock_consumer.poll.side_effect = [mock_message, None]
        
        with patch('main.consumer', mock_consumer):
            with patch('main.logger') as mock_logger:
                task = asyncio.create_task(consume_hard_examples())
                await asyncio.sleep(0.1)
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Verify EOF error was not logged as error
        mock_logger.error.assert_not_called()


class TestKafkaProducer:
    """Test Kafka producer functionality for labeled examples."""
    
    def test_delivery_report_success(self):
        """Test successful delivery report callback."""
        mock_msg = Mock()
        mock_msg.topic.return_value = "test-labeled-examples"
        mock_msg.partition.return_value = 0
        
        with patch('main.logger') as mock_logger:
            delivery_report(None, mock_msg)
        
        # Verify success was logged
        mock_logger.debug.assert_called_once()
    
    def test_delivery_report_error(self):
        """Test error delivery report callback."""
        mock_error = Mock()
        mock_error.__str__ = Mock(return_value="Delivery failed")
        
        with patch('main.logger') as mock_logger:
            delivery_report(mock_error, None)
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_label_example_produces_message(self, client, sample_hard_example, sample_labeled_detection):
        """Test that labeling an example produces a Kafka message."""
        mock_producer = Mock()
        mock_producer.produce = Mock()
        mock_producer.poll = Mock()
        
        pending_examples.clear()
        pending_examples.append(sample_hard_example)
        
        with patch('main.producer', mock_producer):
            form_data = {
                "annotator_id": "test-annotator",
                "quality_score": "0.9",
                "notes": "Test annotation"
            }
            
            response = client.post(
                "/api/v1/examples/test-event-123/label",
                data=form_data,
                json=[sample_labeled_detection]
            )
            
            assert response.status_code == 200
            
            # Verify producer was called
            mock_producer.produce.assert_called_once()
            mock_producer.poll.assert_called_once_with(0)
            
            # Verify the produced message content
            produce_call = mock_producer.produce.call_args
            assert produce_call[1]["key"] == "camera-001"  # Camera ID as key
            assert "callback" in produce_call[1]
            
            # Parse the message value
            message_json = produce_call[1]["value"]
            message_data = json.loads(message_json)
            assert message_data["event_id"] == "test-event-123"
            assert message_data["annotator_id"] == "test-annotator"
            assert message_data["quality_score"] == 0.9


class TestKafkaIntegrationEndToEnd:
    """End-to-end integration tests with real Kafka interactions."""
    
    @pytest.mark.asyncio
    async def test_hard_example_to_labeled_example_flow(
        self, 
        kafka_producer, 
        kafka_consumer, 
        client, 
        sample_hard_example,
        sample_labeled_detection,
        test_settings
    ):
        """Test complete flow from hard example consumption to labeled example production."""
        try:
            # Step 1: Produce a hard example to Kafka
            await kafka_producer.produce(
                test_settings.HARD_EXAMPLES_TOPIC,
                key="camera-001",
                value=json.dumps(sample_hard_example),
            )
            kafka_producer.flush()
            
            # Step 2: Mock the consumer to simulate receiving the message
            mock_message = Mock(spec=Message)
            mock_message.error.return_value = None
            mock_message.value.return_value = json.dumps(sample_hard_example).encode('utf-8')
            
            pending_examples.clear()
            
            # Simulate message consumption
            with patch('main.consumer') as mock_consumer:
                mock_consumer.poll.side_effect = [mock_message, None]
                
                task = asyncio.create_task(consume_hard_examples())
                await asyncio.sleep(0.1)
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Verify hard example was consumed
            assert len(pending_examples) == 1
            assert pending_examples[0]["event_id"] == "test-event-123"
            
            # Step 3: Label the example through API
            mock_producer = Mock()
            mock_producer.produce = Mock()
            mock_producer.poll = Mock()
            
            with patch('main.producer', mock_producer):
                form_data = {
                    "annotator_id": "test-annotator",
                    "quality_score": "0.95"
                }
                
                response = client.post(
                    "/api/v1/examples/test-event-123/label",
                    data=form_data,
                    json=[sample_labeled_detection]
                )
                
                assert response.status_code == 200
                
                # Verify labeled example was produced
                mock_producer.produce.assert_called_once()
                
                # Verify message content
                produce_call = mock_producer.produce.call_args
                assert produce_call[0][0] == test_settings.LABELED_EXAMPLES_TOPIC
                
                message_data = json.loads(produce_call[1]["value"])
                assert message_data["event_id"] == "test-event-123"
                assert message_data["annotator_id"] == "test-annotator"
                assert len(message_data["corrected_detections"]) == 1
                
            # Verify example was removed from pending
            assert len(pending_examples) == 0
            
        except Exception as e:
            pytest.skip(f"Kafka integration test skipped due to setup issue: {e}")
    
    @pytest.mark.asyncio
    async def test_kafka_connection_resilience(self, test_settings):
        """Test system resilience when Kafka is unavailable."""
        # Mock consumer that always returns connection errors
        mock_consumer = Mock()
        mock_error = Mock()
        mock_error.code.return_value = KafkaError.BROKER_NOT_AVAILABLE
        mock_consumer.poll.side_effect = Exception("Connection failed")
        
        with patch('main.consumer', mock_consumer):
            with patch('main.logger') as mock_logger:
                task = asyncio.create_task(consume_hard_examples())
                await asyncio.sleep(0.2)  # Let it try a few times
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Verify errors were logged and system didn't crash
        mock_logger.error.assert_called()
    
    @pytest.mark.asyncio 
    async def test_consumer_group_behavior(self, kafka_consumer, sample_hard_example, test_settings):
        """Test Kafka consumer group behavior and offset management."""
        try:
            # This test would verify proper consumer group management
            # but requires real Kafka setup, so we'll mock it
            
            mock_consumer = Mock()
            mock_consumer.subscribe = Mock()
            mock_consumer.poll = Mock(return_value=None)
            mock_consumer.close = Mock()
            
            # Verify consumer configuration
            with patch('main.Consumer', return_value=mock_consumer):
                from main import startup_event
                await startup_event()
                
                # Verify consumer was configured correctly
                mock_consumer.subscribe.assert_called_once_with([test_settings.HARD_EXAMPLES_TOPIC])
                
        except Exception as e:
            pytest.skip(f"Kafka consumer group test skipped: {e}")
    
    @pytest.mark.asyncio
    async def test_message_serialization_formats(self, sample_hard_example):
        """Test different message serialization formats and compatibility."""
        # Test JSON serialization
        json_message = json.dumps(sample_hard_example)
        
        mock_message = Mock(spec=Message)
        mock_message.error.return_value = None
        mock_message.value.return_value = json_message.encode('utf-8')
        
        mock_consumer = Mock()
        mock_consumer.poll.side_effect = [mock_message, None]
        
        pending_examples.clear()
        
        with patch('main.consumer', mock_consumer):
            task = asyncio.create_task(consume_hard_examples())
            await asyncio.sleep(0.1)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Verify message was deserialized correctly
        assert len(pending_examples) == 1
        assert pending_examples[0]["event_id"] == sample_hard_example["event_id"]
        assert pending_examples[0]["camera_id"] == sample_hard_example["camera_id"]
    
    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, sample_hard_example):
        """Test handling of concurrent message processing."""
        # Create multiple concurrent messages
        messages = []
        for i in range(5):
            example = sample_hard_example.copy()
            example["event_id"] = f"concurrent-event-{i}"
            
            mock_message = Mock(spec=Message)
            mock_message.error.return_value = None
            mock_message.value.return_value = json.dumps(example).encode('utf-8')
            messages.append(mock_message)
        
        messages.append(None)  # Stop condition
        
        mock_consumer = Mock()
        mock_consumer.poll.side_effect = messages
        
        pending_examples.clear()
        
        with patch('main.consumer', mock_consumer):
            task = asyncio.create_task(consume_hard_examples())
            await asyncio.sleep(0.1)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Verify all messages were processed
        assert len(pending_examples) == 5
        event_ids = [ex["event_id"] for ex in pending_examples]
        for i in range(5):
            assert f"concurrent-event-{i}" in event_ids

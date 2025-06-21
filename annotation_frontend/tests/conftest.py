"""
Test fixtures and configuration for annotation frontend tests.
"""
import pytest
import asyncio
import tempfile
import os
import sys
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

try:
    from testcontainers.kafka import KafkaContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False
    KafkaContainer = None

from confluent_kafka import Producer, Consumer
import json

# Mock shared modules before importing main
sys.modules['shared'] = Mock()
sys.modules['shared.logging_config'] = Mock()
sys.modules['shared.audit_middleware'] = Mock()
sys.modules['shared.metrics'] = Mock()
sys.modules['shared.middleware'] = Mock()

# Configure mocks
mock_logger = Mock()
mock_logger.info = Mock()
mock_logger.error = Mock()
mock_logger.debug = Mock()

sys.modules['shared.logging_config'].configure_logging = Mock(return_value=mock_logger)
sys.modules['shared.logging_config'].get_logger = Mock(return_value=mock_logger)
sys.modules['shared.logging_config'].log_context = Mock()
sys.modules['shared.audit_middleware'].add_audit_middleware = Mock()
sys.modules['shared.metrics'].instrument_app = Mock()
sys.modules['shared.middleware'].add_rate_limiting = Mock()

# Import the application components after mocking
from database import get_db, create_tables
from models import Base, AnnotationExample, AnnotationStatus, RetryQueue
from config import Settings
from auth import get_current_user, TokenData

# Now import main components
from main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Create test-specific settings."""
    return Settings(
        API_BASE_URL="http://localhost:8000",
        KAFKA_BOOTSTRAP_SERVERS="localhost:9092",
        JWT_SECRET_KEY="test-secret-key",
        ANNOTATION_PAGE_SIZE=10,
        HOST="0.0.0.0",
        PORT=8000,
        KAFKA_GROUP_ID="test-annotation-frontend",
        HARD_EXAMPLES_TOPIC="test-hard-examples",
        LABELED_EXAMPLES_TOPIC="test-labeled-examples"
    )


@pytest.fixture
def test_db():
    """Create a temporary SQLite database for testing."""
    # Create a temporary file for the test database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # Create engine with SQLite
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield TestingSessionLocal
    
    # Cleanup - dispose engine first to close connections
    engine.dispose()
    
    # Close file descriptor and cleanup
    try:
        os.close(db_fd)
        os.unlink(db_path)
    except (OSError, PermissionError):
        # On Windows, the file might still be locked, ignore cleanup error
        pass


@pytest.fixture
def db_session(test_db):
    """Create a database session for testing."""
    session = test_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    from datetime import datetime, timedelta
    
    # Create expiration time 1 hour from now
    exp_time = int((datetime.utcnow() + timedelta(hours=1)).timestamp())
    
    return TokenData(
        sub="test-user-123",
        exp=exp_time,
        scopes=["annotation:read", "annotation:write"],
        roles=["annotator"]
    )


@pytest.fixture
def client(test_db, mock_user):
    """Create a test client with database and auth overrides."""
    
    def override_get_db():
        session = test_db()
        try:
            yield session
        finally:
            session.close()
    
    def override_get_current_user():
        return mock_user
      # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    # Clear any existing test data in database
    db = next(override_get_db())
    try:
        db.query(AnnotationExample).delete()
        db.commit()
    finally:
        db.close()
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def sample_hard_example():
    """Create a sample hard example for testing."""
    return {
        "event_id": "test-event-123",
        "camera_id": "camera-001",
        "timestamp": "2025-06-16T10:30:00Z",
        "frame_data": "base64encodedframedata==",
        "detections": [
            {
                "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 400},
                "class_name": "person",
                "confidence": 0.75
            }
        ],
        "reason": "Low confidence detection",
        "confidence_scores": {"person": 0.75, "vehicle": 0.15}
    }


@pytest.fixture
def sample_labeled_detection():
    """Create a sample labeled detection for testing."""
    return {
        "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 400},
        "class_name": "person",
        "confidence": 0.75,
        "corrected_class": "person",
        "is_correct": True
    }


@pytest.fixture
def invalid_bbox_data():
    """Create invalid bounding box data for validation testing."""
    return [
        # x2 <= x1
        {"x1": 300, "y1": 200, "x2": 100, "y2": 400},
        # y2 <= y1
        {"x1": 100, "y1": 400, "x2": 300, "y2": 200},
        # Negative coordinates
        {"x1": -10, "y1": 200, "x2": 300, "y2": 400},
        # Out of bounds coordinates
        {"x1": 100, "y1": 200, "x2": 2000, "y2": 400},
    ]


@pytest.fixture(scope="session")
async def kafka_container():
    """Create a Kafka test container."""
    if TESTCONTAINERS_AVAILABLE:
        try:
            with KafkaContainer() as kafka:
                # Wait for Kafka to be ready
                kafka.start()
                yield kafka
        except Exception as e:
            # If testcontainers fails, use a mock
            mock_kafka = Mock()
            mock_kafka.get_bootstrap_server.return_value = "localhost:9092"
            yield mock_kafka
    else:
        # Use mock if testcontainers not available
        mock_kafka = Mock()
        mock_kafka.get_bootstrap_server.return_value = "localhost:9092"
        yield mock_kafka


@pytest.fixture
async def kafka_producer(kafka_container):
    """Create a Kafka producer for testing."""
    if TESTCONTAINERS_AVAILABLE:
        try:
            bootstrap_servers = kafka_container.get_bootstrap_server()
            producer = Producer({
                'bootstrap.servers': bootstrap_servers,
                'client.id': 'test-producer'
            })
            yield producer
            producer.flush()
        except Exception:
            # Use mock if Kafka container fails
            mock_producer = Mock()
            mock_producer.produce = Mock()
            mock_producer.poll = Mock()
            mock_producer.flush = Mock()
            yield mock_producer
    else:
        # Use mock if testcontainers not available
        mock_producer = Mock()
        mock_producer.produce = Mock()
        mock_producer.poll = Mock()
        mock_producer.flush = Mock()
        yield mock_producer


@pytest.fixture
async def kafka_consumer(kafka_container, test_settings):
    """Create a Kafka consumer for testing."""
    if TESTCONTAINERS_AVAILABLE:
        try:
            bootstrap_servers = kafka_container.get_bootstrap_server()
            consumer = Consumer({
                'bootstrap.servers': bootstrap_servers,
                'group.id': 'test-consumer',
                'auto.offset.reset': 'earliest'
            })
            consumer.subscribe([test_settings.HARD_EXAMPLES_TOPIC])
            yield consumer
            consumer.close()
        except Exception:
            # Use mock if Kafka container fails
            mock_consumer = Mock()
            mock_consumer.subscribe = Mock()
            mock_consumer.poll = Mock()
            mock_consumer.close = Mock()
            yield mock_consumer
    else:
        # Use mock if testcontainers not available
        mock_consumer = Mock()
        mock_consumer.subscribe = Mock()
        mock_consumer.poll = Mock()
        mock_consumer.close = Mock()
        yield mock_consumer


@pytest.fixture
def annotation_example_in_db(db_session):
    """Create an annotation example in the test database."""
    example = AnnotationExample(
        example_id="test-example-db-123",
        camera_id="camera-001", 
        timestamp="2025-06-16T10:30:00",
        frame_data="base64encodedframedata==",
        original_detections=[{"class": "person", "confidence": 0.8}],
        confidence_scores={"person": 0.8},
        reason="Test example",
        bbox={"x1": 100, "y1": 200, "x2": 300, "y2": 400},
        status=AnnotationStatus.PENDING
    )
    db_session.add(example)
    db_session.commit()
    db_session.refresh(example)
    return example


@pytest.fixture
def retry_queue_item(db_session):
    """Create a retry queue item in the test database."""
    retry_item = RetryQueue(
        example_id="retry-example-123",
        topic="test-labeled-examples",
        key="camera-001",
        payload='{"event_id": "retry-example-123", "status": "failed"}',
        attempts=1,
        error_message="Connection timeout"
    )
    db_session.add(retry_item)
    db_session.commit()
    db_session.refresh(retry_item)
    return retry_item

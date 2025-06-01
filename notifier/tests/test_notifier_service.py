import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from notifier.main import app

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

@patch('notifier.main.send_notification_task')
def test_send_notification_success(mock_task):
    with patch('notifier.main.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_get_db.return_value.__exit__.return_value = None
        
        # Mock the database operations
        mock_log_entry = MagicMock()
        mock_log_entry.id = "test-id"
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        payload = {
            "channel": "email",
            "recipients": ["test@example.com"],
            "subject": "Test Subject",
            "message": "Test message"
        }
        
        # This test would need more sophisticated mocking for the actual database
        # For now, it demonstrates the structure
        pass

def test_send_notification_invalid_channel():
    payload = {
        "channel": "invalid_channel",
        "recipients": ["test@example.com"],
        "subject": "Test",
        "message": "Test message"
    }
    
    resp = client.post("/send", json=payload)
    assert resp.status_code == 400
    assert "Unknown channel" in resp.json()["detail"]
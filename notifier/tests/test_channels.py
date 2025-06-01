import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from notifier.channels import EmailChannel, SlackChannel, SMSChannel, WebhookChannel

@pytest.mark.asyncio
async def test_email_channel():
    channel = EmailChannel()
    
    with patch('smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        await channel.send(
            recipients=["test@example.com"],
            subject="Test Subject",
            message="Test message",
            metadata={"key": "value"}
        )
        
        mock_smtp.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

@pytest.mark.asyncio
async def test_slack_channel():
    channel = SlackChannel()
    channel.webhook_url = "https://hooks.slack.com/test"
    
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        await channel.send(
            recipients=["#general"],
            subject="Test Alert",
            message="Test message",
            metadata={"clip_links": ["https://example.com/clip1.mp4"]}
        )
        
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "blocks" in call_args[1]["json"]

@pytest.mark.asyncio
async def test_webhook_channel():
    channel = WebhookChannel()
    channel.webhook_url = "https://webhook.example.com"
    channel.webhook_secret = "secret123"
    
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        await channel.send(
            recipients=["user1"],
            subject="Test",
            message="Test message"
        )
        
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer secret123"
        assert "subject" in call_args[1]["json"]
"""
Notification channel implementations for different delivery methods.
"""
import os
import smtplib
import json
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
import requests
from shared.logging_config import get_logger, log_context

logger = get_logger("notifier")

class NotificationChannel(ABC):
    """Abstract base class for notification channels."""
    
    @abstractmethod
    async def send(self, recipients: List[str], subject: str, message: str, metadata: Dict[str, Any] = None):
        """Send notification to recipients."""
        pass

class EmailChannel(NotificationChannel):
    """Email notification channel using SMTP."""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
    
    async def send(self, recipients: List[str], subject: str, message: str, metadata: Dict[str, Any] = None):
        """Send email notification."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # Add metadata as HTML if provided
            body = message
            if metadata:
                body += f"\n\nMetadata:\n{json.dumps(metadata, indent=2)}"
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info("Email sent", extra={recipients=recipients, subject=subject})
            
        except Exception as e:
            logger.error("Email send failed", error=str(e), recipients=recipients)
            raise

class SlackChannel(NotificationChannel):
    """Slack notification channel using webhooks."""
    
    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    
    async def send(self, recipients: List[str], subject: str, message: str, metadata: Dict[str, Any] = None):
        """Send Slack notification."""
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return
        
        try:
            # Build Slack message
            slack_message = {
                "text": subject,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{subject}*\n{message}"
                        }
                    }
                ]
            }
            
            # Add metadata as fields if provided
            if metadata:
                fields = []
                for key, value in metadata.items():
                    fields.append({
                        "type": "mrkdwn",
                        "text": f"*{key}:* {value}"
                    })
                
                if fields:
                    slack_message["blocks"].append({
                        "type": "section",
                        "fields": fields
                    })
            
            # Add clip links if available
            if metadata and metadata.get("clip_links"):
                for i, link in enumerate(metadata["clip_links"]):
                    slack_message["blocks"].append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"<{link}|View Clip {i+1}>"
                        }
                    })
            
            response = requests.post(self.webhook_url, json=slack_message, timeout=10)
            response.raise_for_status()
            
            logger.info("Slack notification sent", extra={subject=subject})
            
        except Exception as e:
            logger.error("Slack send failed", error=str(e), subject=subject)
            raise

class SMSChannel(NotificationChannel):
    """SMS notification channel using Twilio."""
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER", "")
    
    async def send(self, recipients: List[str], subject: str, message: str, metadata: Dict[str, Any] = None):
        """Send SMS notification."""
        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.warning("Twilio credentials not configured")
            return
        
        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            
            # Truncate message for SMS
            sms_message = f"{subject}: {message}"
            if len(sms_message) > 160:
                sms_message = sms_message[:157] + "..."
            
            for recipient in recipients:
                client.messages.create(
                    body=sms_message,
                    from_=self.from_number,
                    to=recipient
                )
            
            logger.info("SMS sent", extra={recipients=recipients, subject=subject})
            
        except Exception as e:
            logger.error("SMS send failed", error=str(e), recipients=recipients)
            raise

class WebhookChannel(NotificationChannel):
    """Generic webhook notification channel."""
    
    def __init__(self):
        self.webhook_url = os.getenv("WEBHOOK_URL", "")
        self.webhook_secret = os.getenv("WEBHOOK_SECRET", "")
    
    async def send(self, recipients: List[str], subject: str, message: str, metadata: Dict[str, Any] = None):
        """Send webhook notification."""
        if not self.webhook_url:
            logger.warning("Webhook URL not configured")
            return
        
        try:
            payload = {
                "subject": subject,
                "message": message,
                "recipients": recipients,
                "metadata": metadata or {},
                "timestamp": "2025-05-31T10:27:44Z"
            }
            
            headers = {"Content-Type": "application/json"}
            if self.webhook_secret:
                headers["Authorization"] = f"Bearer {self.webhook_secret}"
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info("Webhook notification sent", extra={url=self.webhook_url, subject=subject})
            
        except Exception as e:
            logger.error("Webhook send failed", error=str(e), url=self.webhook_url)
            raise

# Channel registry
CHANNELS = {
    "email": EmailChannel(),
    "slack": SlackChannel(),
    "sms": SMSChannel(),
    "webhook": WebhookChannel(),
}

"""
Notifier Service: sends notifications through various channels based on triggered actions.
"""
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from shared.logging import get_logger
from shared.metrics import instrument_app

from database import SessionLocal, engine
from models import Base, NotificationLog, NotificationStatus
from channels import CHANNELS

LOGGER = get_logger("notifier")
app = FastAPI(title="Notifier Service")
instrument_app(app, service_name="notifier")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class NotificationRequest(BaseModel):
    channel: str
    recipients: List[str]
    subject: str
    message: str
    metadata: Optional[dict] = None
    rule_id: Optional[str] = None

class NotificationResponse(BaseModel):
    id: str
    status: str
    message: str

@app.on_event("startup")
def startup_event():
    LOGGER.info("Starting Notifier Service")
    Base.metadata.create_all(bind=engine)

@app.get("/health")
async def health():
    return {"status": "ok"}

async def send_notification_task(
    notification_id: str,
    channel: str,
    recipients: List[str],
    subject: str,
    message: str,
    metadata: dict = None
):
    """Background task to send notification and update status."""
    db = SessionLocal()
    try:
        # Get notification log entry
        log_entry = db.query(NotificationLog).filter(
            NotificationLog.id == notification_id
        ).first()
        
        if not log_entry:
            LOGGER.error("Notification log entry not found", id=notification_id)
            return
        
        # Get channel implementation
        if channel not in CHANNELS:
            log_entry.status = NotificationStatus.FAILED
            log_entry.error_message = f"Unknown channel: {channel}"
            db.commit()
            return
        
        channel_impl = CHANNELS[channel]
        
        # Send notification
        try:
            await channel_impl.send(recipients, subject, message, metadata)
            log_entry.status = NotificationStatus.SENT
            log_entry.sent_at = datetime.utcnow()
            LOGGER.info("Notification sent successfully", id=notification_id, channel=channel)
            
        except Exception as e:
            log_entry.status = NotificationStatus.FAILED
            log_entry.error_message = str(e)
            LOGGER.error("Notification send failed", id=notification_id, error=str(e))
        
        db.commit()
        
    except Exception as e:
        LOGGER.error("Notification task failed", id=notification_id, error=str(e))
    finally:
        db.close()

@app.post("/send", response_model=NotificationResponse)
async def send_notification(
    req: NotificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Send a notification through the specified channel.
    """
    LOGGER.info("Notification request received", channel=req.channel, recipients=req.recipients)
    
    # Validate channel
    if req.channel not in CHANNELS:
        raise HTTPException(status_code=400, detail=f"Unknown channel: {req.channel}")
    
    # Create notification log entry
    log_entry = NotificationLog(        channel=req.channel,
        recipients=req.recipients,
        subject=req.subject,
        message=req.message,
        notification_metadata=req.metadata,
        status=NotificationStatus.PENDING,
        rule_id=req.rule_id,
    )
    
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    
    # Schedule background task
    background_tasks.add_task(
        send_notification_task,
        str(log_entry.id),
        req.channel,
        req.recipients,
        req.subject,
        req.message,
        req.metadata
    )
    
    return NotificationResponse(
        id=str(log_entry.id),
        status="scheduled",
        message="Notification queued for delivery"
    )

@app.get("/notifications/{notification_id}")
async def get_notification_status(
    notification_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the status of a notification.
    """
    log_entry = db.query(NotificationLog).filter(
        NotificationLog.id == notification_id
    ).first()
    
    if not log_entry:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {
        "id": str(log_entry.id),
        "channel": log_entry.channel,
        "recipients": log_entry.recipients,
        "subject": log_entry.subject,
        "status": log_entry.status.value,
        "error_message": log_entry.error_message,
        "sent_at": log_entry.sent_at.isoformat() if log_entry.sent_at else None,
        "created_at": log_entry.created_at.isoformat(),
        "rule_id": log_entry.rule_id,
    }

@app.get("/notifications")
async def list_notifications(
    channel: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List notification history with optional filters.
    """
    query = db.query(NotificationLog)
    
    if channel:
        query = query.filter(NotificationLog.channel == channel)
    
    if status:
        query = query.filter(NotificationLog.status == NotificationStatus(status))
    
    notifications = query.order_by(NotificationLog.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": str(notif.id),
            "channel": notif.channel,
            "recipients": notif.recipients,
            "subject": notif.subject,
            "status": notif.status.value,
            "sent_at": notif.sent_at.isoformat() if notif.sent_at else None,
            "created_at": notif.created_at.isoformat(),
            "rule_id": notif.rule_id,
        }
        for notif in notifications
    ]

@app.post("/test/{channel}")
async def test_channel(
    channel: str,
    recipients: List[str],
    background_tasks: BackgroundTasks
):
    """
    Send a test notification through the specified channel.
    """
    if channel not in CHANNELS:
        raise HTTPException(status_code=400, detail=f"Unknown channel: {channel}")
    
    test_req = NotificationRequest(
        channel=channel,
        recipients=recipients,
        subject="Test Notification",
        message=f"This is a test notification from the Notifier Service at {datetime.utcnow().isoformat()}",
        metadata={"test": True}
    )
    
    return await send_notification(test_req, background_tasks, next(get_db()))
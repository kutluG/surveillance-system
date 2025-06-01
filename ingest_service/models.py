"""
SQLAlchemy ORM model definitions for storing camera events.
"""
import uuid
from sqlalchemy import Column, String, DateTime, JSON, Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.declarative import declarative_base
from shared.models import EventType

Base = declarative_base()

class Event(Base):
    __tablename__ = "events"

    id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    timestamp = Column(DateTime, nullable=False)
    camera_id = Column(String, nullable=False)
    event_type = Column(PgEnum(EventType, name="event_type"), nullable=False)
    detections = Column(JSON, nullable=True)
    activity = Column(String, nullable=True)
    metadata = Column(JSON, nullable=True)

    @classmethod
    def from_camera_event(cls, ev):
        """
        Build a DB Event from a shared.models.CameraEvent.
        """
        return cls(
            id=ev.id,
            timestamp=ev.timestamp,
            camera_id=ev.camera_id,
            event_type=ev.event_type,
            detections=[d.dict() for d in ev.detections] if ev.detections else None,
            activity=ev.activity,
            metadata=ev.metadata,
        )
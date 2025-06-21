"""
Service layer for annotation business logic.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import logging

from models import AnnotationExample, RetryQueue, AnnotationStatus
from schemas import AnnotationRequest, ExampleResponse, ExampleListResponse
from database import get_db_session

logger = logging.getLogger(__name__)


class AnnotationService:
    """Service class for annotation operations."""
    
    @staticmethod
    def create_example_from_kafka(data: Dict[str, Any], db: Session) -> AnnotationExample:
        """Create a new annotation example from Kafka message."""
        try:
            example = AnnotationExample(
                example_id=data.get("event_id"),
                camera_id=data.get("camera_id"),
                timestamp=datetime.fromisoformat(data.get("timestamp", "").replace("Z", "+00:00")),
                frame_data=data.get("frame_data"),
                original_detections=data.get("detections", []),
                confidence_scores=data.get("confidence_scores", {}),
                reason=data.get("reason"),
                status=AnnotationStatus.PENDING
            )
            
            db.add(example)
            db.commit()
            db.refresh(example)
            
            logger.info(f"Created annotation example: {example.example_id}")
            return example
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create annotation example: {e}")
            raise
    
    @staticmethod
    def get_pending_examples(db: Session, page: int = 1, page_size: int = 50) -> ExampleListResponse:
        """Get list of pending annotation examples."""
        try:
            offset = (page - 1) * page_size
            
            query = db.query(AnnotationExample).filter(
                AnnotationExample.status == AnnotationStatus.PENDING
            )
            
            total = query.count()
            examples = query.order_by(desc(AnnotationExample.created_at)).offset(offset).limit(page_size).all()
            
            return ExampleListResponse(
                examples=[ExampleResponse.from_orm(ex) for ex in examples],
                total=total,
                page=page,
                page_size=page_size
            )
            
        except Exception as e:
            logger.error(f"Failed to get pending examples: {e}")
            raise
    
    @staticmethod
    def get_example_by_id(db: Session, example_id: str) -> Optional[AnnotationExample]:
        """Get annotation example by ID."""
        try:
            return db.query(AnnotationExample).filter(
                AnnotationExample.example_id == example_id
            ).first()
        except Exception as e:
            logger.error(f"Failed to get example {example_id}: {e}")
            raise
    
    @staticmethod
    def submit_annotation(db: Session, request: AnnotationRequest) -> AnnotationExample:
        """Submit annotation for an example."""
        try:
            example = db.query(AnnotationExample).filter(
                AnnotationExample.example_id == request.example_id
            ).first()
            
            if not example:
                raise ValueError(f"Example {request.example_id} not found")
            
            if example.status != AnnotationStatus.PENDING:
                raise ValueError(f"Example {request.example_id} is not pending")
            
            # Update the example with annotation data
            example.bbox = {
                "x1": request.bbox.x1,
                "y1": request.bbox.y1,
                "x2": request.bbox.x2,
                "y2": request.bbox.y2
            }
            example.label = request.label
            example.annotator_id = request.annotator_id
            example.quality_score = request.quality_score
            example.notes = request.notes
            example.status = AnnotationStatus.COMPLETED
            
            db.commit()
            db.refresh(example)
            
            logger.info(f"Submitted annotation for example: {example.example_id}")
            return example
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to submit annotation: {e}")
            raise
    
    @staticmethod
    def skip_example(db: Session, example_id: str) -> AnnotationExample:
        """Skip an annotation example."""
        try:
            example = db.query(AnnotationExample).filter(
                AnnotationExample.example_id == example_id
            ).first()
            
            if not example:
                raise ValueError(f"Example {example_id} not found")
            
            example.status = AnnotationStatus.SKIPPED
            db.commit()
            db.refresh(example)
            
            logger.info(f"Skipped example: {example.example_id}")
            return example
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to skip example: {e}")
            raise
    
    @staticmethod
    def get_statistics(db: Session) -> Dict[str, int]:
        """Get annotation statistics."""
        try:
            pending_count = db.query(AnnotationExample).filter(
                AnnotationExample.status == AnnotationStatus.PENDING
            ).count()
            
            completed_count = db.query(AnnotationExample).filter(
                AnnotationExample.status == AnnotationStatus.COMPLETED
            ).count()
            
            retry_count = db.query(RetryQueue).count()
            
            return {
                "pending_examples": pending_count,
                "completed_examples": completed_count,
                "retry_queue_size": retry_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            raise


class RetryService:
    """Service class for retry queue operations."""
    
    @staticmethod
    def add_to_retry_queue(db: Session, example_id: str, topic: str, key: str, 
                          payload: str, error_message: str) -> RetryQueue:
        """Add failed message to retry queue."""
        try:
            retry_entry = RetryQueue(
                example_id=example_id,
                topic=topic,
                key=key,
                payload=payload,
                attempts=0,
                error_message=error_message
            )
            
            db.add(retry_entry)
            db.commit()
            db.refresh(retry_entry)
            
            logger.info(f"Added to retry queue: {example_id}")
            return retry_entry
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to add to retry queue: {e}")
            raise
    
    @staticmethod
    def get_retry_items(db: Session, max_attempts: int = 5) -> List[RetryQueue]:
        """Get items from retry queue that need processing."""
        try:
            return db.query(RetryQueue).filter(
                RetryQueue.attempts < max_attempts
            ).order_by(RetryQueue.created_at).all()
            
        except Exception as e:
            logger.error(f"Failed to get retry items: {e}")
            raise
    
    @staticmethod
    def update_retry_attempt(db: Session, retry_id: int, success: bool, error_message: str = None):
        """Update retry attempt status."""
        try:
            retry_entry = db.query(RetryQueue).filter(RetryQueue.id == retry_id).first()
            if retry_entry:
                retry_entry.attempts += 1
                retry_entry.last_attempt = datetime.utcnow()
                
                if success:
                    db.delete(retry_entry)
                    logger.info(f"Retry successful, removed from queue: {retry_entry.example_id}")
                else:
                    retry_entry.error_message = error_message
                    logger.warning(f"Retry failed: {retry_entry.example_id}, attempt {retry_entry.attempts}")
                
                db.commit()
                
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update retry attempt: {e}")
            raise

"""
Examples endpoints for the annotation frontend service.
Handles CRUD operations for annotation examples and submissions.
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status, Query, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from database import get_db
from models import AnnotationExample, AnnotationStatus
from schemas import (
    AnnotationRequest,
    AnnotationResponse,
    ExampleResponse,
    ExampleListResponse,
    DeleteResponse,
    ErrorResponse,
    ValidationErrorResponse
)
from services import AnnotationService
from auth import get_current_user, require_role, TokenData
from shared.logging_config import get_logger
from kafka_pool import kafka_pool
from redis_service import redis_retry_service

# Rate limiting imports
from rate_limiting import (
    rate_limit_annotation_submission,
    rate_limit_data_deletion,
    MAX_JSON_FIELD_SIZE
)

logger = get_logger(__name__)

# Create router
router = APIRouter(
    tags=["examples"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Not found"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


@router.get(
    "/",
    response_model=ExampleListResponse,
    summary="Get annotation examples",
    description="Retrieve a paginated list of annotation examples with optional filtering",
    responses={
        200: {"description": "Examples retrieved successfully"},
        401: {"description": "Authentication required"}
    }
)
async def get_examples(
    skip: int = Query(0, ge=0, description="Number of examples to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of examples to return"),
    status_filter: Optional[AnnotationStatus] = Query(None, description="Filter by annotation status"),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get a paginated list of annotation examples.
    
    Args:
        skip: Number of examples to skip (for pagination)
        limit: Maximum number of examples to return
        status_filter: Optional filter by annotation status
        db: Database session
        current_user: Authenticated user information
        
    Returns:
        ExampleListResponse: Paginated list of examples
    """
    try:
        logger.info(f"Fetching examples for user {current_user.sub}, skip={skip}, limit={limit}")
        
        # Build query
        query = db.query(AnnotationExample)
        
        # Apply status filter if provided
        if status_filter:
            query = query.filter(AnnotationExample.status == status_filter)
        
        # Get total count for pagination
        total = query.count()
        
        # Apply pagination and ordering
        examples = query.order_by(AnnotationExample.created_at.desc()).offset(skip).limit(limit).all()
        
        # Convert to response format
        example_responses = [
            ExampleResponse(
                id=example.id,
                example_id=example.example_id,
                camera_id=example.camera_id,
                timestamp=example.timestamp,
                original_detections=example.original_detections,
                confidence_scores=example.confidence_scores,
                reason=example.reason,
                bbox=example.bbox,
                label=example.label,
                status=example.status,
                created_at=example.created_at
            )
            for example in examples
        ]
        
        return ExampleListResponse(
            examples=example_responses,
            total=total,
            page=(skip // limit) + 1,
            page_size=limit
        )
        
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching examples: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching examples"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching examples: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get(
    "/examples/{event_id}",
    response_model=ExampleResponse,
    summary="Get specific annotation example",
    description="Retrieve a specific annotation example by event ID",
    responses={
        200: {"description": "Example retrieved successfully"},
        404: {"description": "Example not found"},
        401: {"description": "Authentication required"}
    }
)
async def get_example(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get a specific annotation example by event ID.
    
    Args:
        event_id: The unique event identifier
        db: Database session
        current_user: Authenticated user information
        
    Returns:
        ExampleResponse: The requested example
        
    Raises:
        HTTPException: If example not found or access denied
    """
    try:
        logger.info(f"Fetching example {event_id} for user {current_user.sub}")
        
        example = db.query(AnnotationExample).filter(
            AnnotationExample.example_id == event_id
        ).first()
        
        if not example:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Example with event_id '{event_id}' not found"
            )
        
        return ExampleResponse(
            id=example.id,
            example_id=example.example_id,
            camera_id=example.camera_id,
            timestamp=example.timestamp,
            original_detections=example.original_detections,
            confidence_scores=example.confidence_scores,
            reason=example.reason,
            bbox=example.bbox,
            label=example.label,
            status=example.status,
            created_at=example.created_at
        )
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching example {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching example"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching example {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.post(
    "/examples/{event_id}/label",
    response_model=AnnotationResponse,
    summary="Submit annotation for example",
    description="Submit an annotation label for a specific example",
    responses={
        200: {"description": "Annotation submitted successfully"},
        404: {"description": "Example not found"},
        422: {"description": "Validation error"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient privileges - annotator role required"},
        429: {"description": "Rate limit exceeded"}
    }
)
@rate_limit_annotation_submission()
async def submit_annotation(
    event_id: str,
    request: Request,
    annotation: AnnotationRequest = Body(..., max_length=MAX_JSON_FIELD_SIZE),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_role("annotator"))
):
    """
    Submit an annotation for a specific example.
    
    Args:
        event_id: The unique event identifier
        annotation: The annotation data
        db: Database session
        current_user: Authenticated user information
        
    Returns:
        AnnotationResponse: Confirmation of annotation submission
        
    Raises:
        HTTPException: If example not found, validation fails, or other errors
    """
    try:
        logger.info(f"Submitting annotation for example {event_id} by user {current_user.sub}")
        
        # Validate that event_id matches the annotation
        if annotation.example_id != event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event ID in URL does not match annotation example_id"
            )
        
        # Check if example exists
        example = db.query(AnnotationExample).filter(
            AnnotationExample.example_id == event_id
        ).first()
        
        if not example:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Example with event_id '{event_id}' not found"
            )
        
        # Initialize annotation service
        annotation_service = AnnotationService(db, kafka_pool, redis_retry_service)
        
        # Process the annotation
        try:
            result = await annotation_service.process_annotation(
                annotation=annotation,
                annotator_id=current_user.sub
            )
            
            if result["status"] == "success":
                logger.info(f"Annotation submitted successfully for example {event_id}")
                return AnnotationResponse(
                    status="success",
                    example_id=event_id,
                    message="Annotation submitted successfully"
                )
            else:
                logger.warning(f"Annotation processing failed for example {event_id}: {result.get('message')}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Failed to process annotation")
                )
                
        except Exception as service_error:
            logger.error(f"Annotation service error for example {event_id}: {service_error}")
            
            # Try to add to retry queue if processing fails
            try:
                await redis_retry_service.add_to_retry_queue(
                    "annotation_submission",
                    {
                        "example_id": event_id,
                        "annotation": annotation.model_dump(),
                        "annotator_id": current_user.sub,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                return AnnotationResponse(
                    status="queued",
                    example_id=event_id,
                    message="Annotation queued for retry due to temporary processing error"
                )
                
            except Exception as retry_error:
                logger.error(f"Failed to queue annotation for retry: {retry_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to process annotation and unable to queue for retry"
                )
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error processing annotation for {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while processing annotation"
        )
    except Exception as e:
        logger.error(f"Unexpected error processing annotation for {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing annotation"
        )


@router.delete(
    "/examples/{event_id}",
    response_model=DeleteResponse,
    summary="Delete annotation example",
    description="Delete a specific annotation example (requires admin role)",
    responses={
        200: {"description": "Example deleted successfully"},
        404: {"description": "Example not found"},
        403: {"description": "Insufficient privileges"},
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"}
    }
)
@rate_limit_data_deletion()
async def delete_example(
    event_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Delete a specific annotation example.
    
    This endpoint requires admin privileges and should be used carefully.
    Deleted examples cannot be recovered.
    
    Args:
        event_id: The unique event identifier
        db: Database session
        current_user: Authenticated user information
        
    Returns:
        DeleteResponse: Confirmation of deletion
        
    Raises:
        HTTPException: If example not found, insufficient privileges, or other errors
    """
    try:
        logger.info(f"Delete request for example {event_id} by user {current_user.sub}")
        
        # Check admin privileges (assuming this is stored in user claims)
        if not current_user.scopes or "admin" not in current_user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to delete examples"
            )
        
        # Find the example
        example = db.query(AnnotationExample).filter(
            AnnotationExample.example_id == event_id
        ).first()
        
        if not example:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Example with event_id '{event_id}' not found"
            )
        
        # Perform deletion
        try:
            db.delete(example)
            db.commit()
            
            logger.info(f"Example {event_id} deleted successfully by user {current_user.sub}")
            
            # Publish deletion event to Kafka for audit trail
            try:
                deletion_event = {
                    "event_type": "example_deleted",
                    "example_id": event_id,
                    "deleted_by": current_user.sub,
                    "timestamp": datetime.utcnow().isoformat(),
                    "original_status": example.status.value if example.status else None
                }
                
                await kafka_pool.publish_message(
                    "annotation.events",
                    deletion_event,
                    key=event_id
                )
                
            except Exception as kafka_error:
                logger.warning(f"Failed to publish deletion event to Kafka: {kafka_error}")
                # Don't fail the deletion if Kafka publishing fails
            
            return DeleteResponse(
                status="success",
                message=f"Example '{event_id}' deleted successfully",
                deleted_id=event_id,
                timestamp=datetime.utcnow()
            )
            
        except SQLAlchemyError as db_error:
            db.rollback()
            logger.error(f"Database error deleting example {event_id}: {db_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while deleting example"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting example {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting example"
        )


@router.post(
    "/",
    response_model=ExampleResponse,
    summary="Create a new annotation example",
    description="Create a new annotation example for labeling",
    responses={
        201: {"description": "Example created successfully"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"}
    }
)
async def create_example(
    request: AnnotationRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_role("admin"))
):
    """
    Create a new annotation example.
    
    Args:
        request: The annotation request data
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        ExampleResponse: The created example
    """
    try:
        logger.info(f"Creating new example for user {current_user.sub}")
        
        # Create new example
        new_example = AnnotationExample(
            example_id=request.example_id,
            camera_id="default",  # This would come from the request in a real implementation
            timestamp=datetime.utcnow(),
            bbox=request.bbox.model_dump(),
            label=request.label,
            status=AnnotationStatus.PENDING,
            original_detections={},
            confidence_scores={},
            reason="Manual creation"
        )
        
        db.add(new_example)
        db.commit()
        db.refresh(new_example)
        
        logger.info(f"Created example with ID {new_example.id}")
        
        return ExampleResponse(
            id=new_example.id,
            example_id=new_example.example_id,
            camera_id=new_example.camera_id,
            timestamp=new_example.timestamp,
            original_detections=new_example.original_detections,
            confidence_scores=new_example.confidence_scores,
            reason=new_example.reason,
            bbox=new_example.bbox,
            label=new_example.label,
            status=new_example.status,
            created_at=new_example.created_at
        )
        
    except SQLAlchemyError as e:
        logger.error(f"Database error creating example: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while creating example"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating example: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

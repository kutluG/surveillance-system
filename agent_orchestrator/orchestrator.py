"""
Orchestrator Module for Agent Orchestrator Service

This module implements the core orchestration logic with robust retry mechanisms,
fallback behaviors, circuit breaker pattern, and background task processing for notification retries.

Features:
- Retry logic with exponential backoff for all downstream calls
- Circuit breaker pattern for preventing cascading failures
- Fallback responses for service failures  
- Background notification retry processing
- Redis-based retry queue management
- Unified response format with status indicators
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

import httpx
import redis.asyncio as redis
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential, 
    retry_if_exception_type,
    retry_if_result
)
from fastapi import HTTPException
from pydantic import BaseModel, Field

# Import configuration
from config import get_config

# Import metrics system
from metrics import metrics_collector, monitor_orchestration_performance, monitor_service_call

# Import enhanced circuit breaker system
from enhanced_circuit_breaker import (
    EnhancedCircuitBreakerManager,
    ServiceConfig, 
    ServiceType,
    get_enhanced_circuit_breaker_manager
)

# Import legacy circuit breaker for fallback compatibility
from circuit_breaker import (
    CircuitBreakerManager, 
    CircuitBreakerConfig, 
    CircuitBreakerError,
    circuit_breaker_manager
)

# Configure logging
logger = logging.getLogger(__name__)

# Get configuration instance
config = get_config()

# Request/Response Models
class OrchestrationRequest(BaseModel):
    """Request model for orchestration endpoint"""
    event_data: Dict[str, Any] = Field(..., description="Event data to process")
    query: Optional[str] = Field(None, description="Optional query for RAG analysis")
    notification_channels: List[str] = Field(default=["email"], description="Notification channels")
    recipients: List[str] = Field(default=[], description="Notification recipients")

class OrchestrationResponse(BaseModel):
    """Unified response model for orchestration"""
    status: str = Field(..., description="Status: ok, partial_success, fallback, or error")
    details: Dict[str, Any] = Field(..., description="Detailed response data")
    rag_result: Optional[Dict[str, Any]] = Field(None, description="RAG service result")
    rule_result: Optional[Dict[str, Any]] = Field(None, description="Rule generation result")
    notification_result: Optional[Dict[str, Any]] = Field(None, description="Notification result")


class OrchestratorService:
    """Main orchestrator service with enhanced circuit breakers, retry logic, and fallback mechanisms"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self._background_task: Optional[asyncio.Task] = None
        self.enhanced_circuit_breaker_manager: Optional[EnhancedCircuitBreakerManager] = None
        # Keep legacy circuit breakers for compatibility
        self.circuit_breakers: Dict[str, Any] = {}
        
    async def initialize(self):
        """Initialize Redis, HTTP clients, and enhanced circuit breakers"""
        try:
            self.redis_client = redis.from_url(config.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
            
            self.http_client = httpx.AsyncClient(timeout=config.http_timeout)
            logger.info("HTTP client initialized")
            
            # Initialize enhanced circuit breaker manager
            self.enhanced_circuit_breaker_manager = get_enhanced_circuit_breaker_manager(self.redis_client)
            
            # Initialize enhanced circuit breakers for each service
            await self._initialize_enhanced_circuit_breakers()
            
            # Start background notification retry task
            self._background_task = asyncio.create_task(self.process_notification_retries())
            logger.info("Background notification retry task started")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator service: {e}")
            raise
    
    async def _initialize_enhanced_circuit_breakers(self):
        """Initialize enhanced circuit breakers for downstream services"""
        
        # RAG Service Configuration - High priority, more tolerant
        rag_config = ServiceConfig(
            name="rag_service",
            service_type=ServiceType.RAG_SERVICE,
            fail_max=5,                    # Open after 5 consecutive failures
            recovery_timeout=60,           # Try recovery after 60 seconds
            timeout=30.0,                  # 30 second timeout for requests
            fallback_enabled=True,         # Enable fallback responses
            priority=1                     # High priority service
        )
        self.enhanced_circuit_breaker_manager.register_service(rag_config)
        
        # Rule Generation Service Configuration - Medium priority, less tolerant
        rulegen_config = ServiceConfig(
            name="rulegen_service",
            service_type=ServiceType.RULEGEN_SERVICE,
            fail_max=3,                    # More sensitive - open after 3 failures
            recovery_timeout=45,           # Shorter recovery timeout
            timeout=20.0,                  # 20 second timeout
            fallback_enabled=True,         # Enable fallback responses
            priority=2                     # Medium priority service
        )
        self.enhanced_circuit_breaker_manager.register_service(rulegen_config)
        
        # Notifier Service Configuration - High priority, quick recovery
        notifier_config = ServiceConfig(
            name="notifier_service",
            service_type=ServiceType.NOTIFIER_SERVICE,
            fail_max=4,                    # Open after 4 failures
            recovery_timeout=30,           # Quick recovery for notifications
            timeout=15.0,                  # 15 second timeout
            fallback_enabled=True,         # Enable fallback (queuing)
            priority=1                     # High priority service
        )
        self.enhanced_circuit_breaker_manager.register_service(notifier_config)
        
        # VMS Service Configuration - Lower priority, more tolerant
        vms_config = ServiceConfig(
            name="vms_service",
            service_type=ServiceType.VMS_SERVICE,
            fail_max=6,                    # More tolerant
            recovery_timeout=90,           # Longer recovery timeout
            timeout=25.0,                  # 25 second timeout
            fallback_enabled=True,         # Enable fallback responses            priority=3                     # Lower priority service
        )
        self.enhanced_circuit_breaker_manager.register_service(vms_config)
        
        logger.info("Enhanced circuit breakers initialized for all downstream services")
    
    async def shutdown(self):
        """Cleanup resources"""
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        
        if self.http_client:
            await self.http_client.aclose()
            
        if self.redis_client:
            await self.redis_client.close()
            
        logger.info("Orchestrator service shutdown complete")
    
    def _is_retryable_error(self, result: httpx.Response) -> bool:
        """Check if HTTP response indicates a retryable error"""
        return result.status_code >= 500 or result.status_code in [408, 429]
    
    async def _call_rag_service(self, event_data: Dict[str, Any], query: Optional[str] = None) -> Dict[str, Any]:
        """Call RAG service through enhanced circuit breaker"""
        
        async def rag_service_call():
            """Internal RAG service call"""
            # Construct payload for advanced RAG service
            payload = {
                "query_event": {
                    "camera_id": event_data.get("camera_id", "unknown"),
                    "timestamp": event_data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                    "label": event_data.get("label", "event_detected"),
                    "bbox": event_data.get("bbox")
                },
                "k": 10
            }
            
            response = await self.http_client.post(
                f"{config.rag_service_url}/rag/query",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info("RAG service call successful")
                return response.json()
            else:
                logger.warning(f"RAG service returned status {response.status_code}")
                response.raise_for_status()
        
        # Call through enhanced circuit breaker
        result = await self.enhanced_circuit_breaker_manager.call_service(
            "rag_service", 
            rag_service_call
        )
        
        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=0.5, max=10),
        retry=(
            retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)) |
            retry_if_result(lambda result: isinstance(result, httpx.Response) and result.status_code >= 500)
        ),
        reraise=True
    )
    async def _call_rulegen_service(self, event_data: Dict[str, Any], rag_context: Dict[str, Any]) -> Dict[str, Any]:
        """Call rule generation service with retry logic"""
        try:
            # Construct payload for rule generation service
            payload = {
                "event": event_data,
                "context": rag_context.get("retrieved_context", [])
            }
            
            response = await self.http_client.post(
                f"{config.rulegen_service_url}/evaluate",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info("Rule generation service call successful")
                return response.json()
            else:
                logger.warning(f"Rule generation service returned status {response.status_code}")
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Rule generation service call failed: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=0.5, max=10),
        retry=(
            retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)) |
            retry_if_result(lambda result: isinstance(result, httpx.Response) and result.status_code >= 500)
        ),
        reraise=True
    )
    async def _call_notifier_service(self, notification_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call notifier service with retry logic"""
        try:
            response = await self.http_client.post(
                f"{config.notifier_service_url}/notify",
                json=notification_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 202]:
                logger.info("Notifier service call successful")
                return response.json()
            else:
                logger.warning(f"Notifier service returned status {response.status_code}")
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Notifier service call failed: {e}")
            raise

    async def _enqueue_notification_retry(self, notification_payload: Dict[str, Any]):
        """Enqueue failed notification for retry processing"""
        try:
            retry_item = {
                "id": str(uuid.uuid4()),
                "payload": notification_payload,
                "timestamp": datetime.utcnow().isoformat(),
                "retry_count": 0
            }
            
            await self.redis_client.lpush("notification_retry_queue", json.dumps(retry_item))
            logger.info(f"Enqueued notification retry: {retry_item['id']}")
            
        except Exception as e:
            logger.error(f"Failed to enqueue notification retry: {e}")

    async def process_notification_retries(self):
        """Background task to process notification retries"""
        logger.info("Starting notification retry background task")
        
        while True:
            try:
                # Wait 60 seconds between retry attempts
                await asyncio.sleep(60)
                
                # Pop one item from the retry queue
                retry_data = await self.redis_client.rpop("notification_retry_queue")
                
                if not retry_data:
                    continue
                    
                retry_item = json.loads(retry_data)
                retry_item["retry_count"] = retry_item.get("retry_count", 0) + 1
                
                logger.info(f"Processing notification retry {retry_item['id']} (attempt {retry_item['retry_count']})")
                
                try:
                    # Try to send notification once
                    await self._call_notifier_service(retry_item["payload"])
                    logger.info(f"Notification retry {retry_item['id']} succeeded")
                    
                except Exception as e:
                    logger.error(f"Notification retry {retry_item['id']} failed: {e}")
                    
                    # Push back to queue if retry count is reasonable
                    if retry_item["retry_count"] < 5:
                        await self.redis_client.lpush("notification_retry_queue", json.dumps(retry_item))
                        logger.info(f"Re-enqueued notification retry {retry_item['id']}")
                    else:
                        logger.error(f"Giving up on notification retry {retry_item['id']} after {retry_item['retry_count']} attempts")
                
            except asyncio.CancelledError:
                logger.info("Notification retry task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in notification retry background task: {e}")
                await asyncio.sleep(5)  # Brief pause before continuing

    @monitor_orchestration_performance("success")
    async def orchestrate(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Main orchestration logic with retry and fallback mechanisms
        
        Flow:
        1. Call RAG service (with fallback on failure)
        2. Call Rule Generation service (skip if RAG failed, use defaults on failure)
        3. Call Notifier service (queue for retry on failure)
        4. Return unified response
        """
        status = "ok"
        details = {}
        rag_result = None
        rule_result = None
        notification_result = None
        
        # Record orchestration request start
        with metrics_collector.concurrent_request_tracker():
            # Step 1: Call RAG Service with fallback
            try:
                with metrics_collector.time_orchestration_stage("success", "rag_query"):
                    rag_result = await self._call_rag_service(request.event_data, request.query)
                logger.info("RAG service completed successfully")
                
            except Exception as e:
                logger.warning(f"RAG service failed after retries: {e}")
                metrics_collector.record_fallback_activation("rag_service", "temporary_outage")
                # Use fallback response
                rag_result = {
                    "linked_explanation": "We could not retrieve context due to a temporary service outage. Please try again shortly.",
                    "retrieved_context": []
                }
                status = "fallback"
                details["rag_error"] = str(e)
                details["rag_fallback_used"] = True
                
                # Skip rule generation if RAG failed entirely
                logger.info("Skipping rule generation due to RAG service failure")
                
                return OrchestrationResponse(
                    status=status,
                    details=details,
                    rag_result=rag_result,
                    rule_result=None,
                    notification_result=None
                )
            
            # Step 2: Call Rule Generation Service
            try:
                with metrics_collector.time_orchestration_stage("success", "rule_generation"):
                    rule_result = await self._call_rulegen_service(request.event_data, rag_result)
                logger.info("Rule generation service completed successfully")
                
            except Exception as e:
                logger.error(f"Rule generation service failed after retries: {e}")
                metrics_collector.record_fallback_activation("rulegen_service", "default_rules")
                # Use default rules as fallback
                rule_result = {
                    "triggered_actions": [
                        {
                            "type": "send_notification",
                            "rule_id": "default_alert",
                            "parameters": {
                                "message": "Alert triggered based on default rules",
                                "severity": "medium"
                            }
                        }
                    ] if request.event_data.get("label") == "person_detected" else []
                }
                status = "partial_success"
                details["rule_error"] = str(e)
                details["default_rules_used"] = True
            
            # Step 3: Call Notifier Service
            if rule_result and rule_result.get("triggered_actions"):
                # Construct notification payload outside try block
                notification_payload = {
                    "alert": {
                        "id": str(uuid.uuid4()),
                        "timestamp": datetime.utcnow().isoformat(),
                        "alert_text": rag_result.get("linked_explanation", "Alert triggered"),
                        "severity": "medium",
                        "evidence_ids": []
                    },
                    "channels": request.notification_channels,
                    "recipients": request.recipients or ["admin@example.com"]
                }
                
                try:
                    with metrics_collector.time_orchestration_stage("success", "notification"):
                        notification_result = await self._call_notifier_service(notification_payload)
                    logger.info("Notifier service completed successfully")
                    
                except Exception as e:
                    logger.error(f"Notifier service failed after retries: {e}")
                    
                    # Enqueue for background retry
                    await self._enqueue_notification_retry(notification_payload)
                    
                    # Return 202 status indicating notification will be retried
                    notification_result = {
                        "status": "notifier_unreachable",
                        "message": "We have generated the alert but could not send notifications. Will retry in background."
                    }
                    
                    if status == "ok":
                        status = "partial_success"
                    details["notification_error"] = str(e)
                    details["notification_queued_for_retry"] = True
            
            else:
                logger.info("No notification required - no triggered actions")
                
            # Record final orchestration status
            metrics_collector.record_orchestration_request(status, request.event_data.get("label", "unknown"))
            
            return OrchestrationResponse(
                status=status,
                details=details,
                rag_result=rag_result,
                rule_result=rule_result,
                notification_result=notification_result
            )
            notification_result = {"status": "no_notification_required", "message": "No rules triggered"}
        
        # Compile final response
        details.update({
            "rag_success": rag_result is not None and "fallback" not in status,
            "rule_success": rule_result is not None and "rule_error" not in details,
            "notification_success": notification_result is not None and "notification_error" not in details,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return OrchestrationResponse(
            status=status,
            details=details,
            rag_result=rag_result,
            rule_result=rule_result,
            notification_result=notification_result
        )


# Global orchestrator instance
orchestrator_service = OrchestratorService()

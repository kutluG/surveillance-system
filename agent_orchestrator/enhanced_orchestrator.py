"""
Enhanced Orchestrator Module for Agent Orchestrator Service

This module implements the core orchestration logic with enhanced circuit breaker pattern,
robust retry mechanisms, fallback behaviors, and background task processing for notification retries.

Features:
- Enhanced circuit breaker pattern with pybreaker integration
- Service-specific circuit breaker configurations
- Graceful degradation and fallback responses
- Background notification retry processing
- Redis-based retry queue management and state persistence
- Comprehensive metrics collection
- Unified response format with detailed status indicators
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
    circuit_breaker_status: Optional[Dict[str, Any]] = Field(None, description="Circuit breaker status information")


class EnhancedOrchestratorService:
    """Enhanced orchestrator service with circuit breakers, retry logic, and fallback mechanisms"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self._background_task: Optional[asyncio.Task] = None
        self.enhanced_circuit_breaker_manager: Optional[EnhancedCircuitBreakerManager] = None
        
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
            logger.error(f"Failed to initialize enhanced orchestrator service: {e}")
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
            fallback_enabled=True,         # Enable fallback responses
            priority=3                     # Lower priority service
        )
        self.enhanced_circuit_breaker_manager.register_service(vms_config)
        
        # Prediction Service Configuration - Medium priority
        prediction_config = ServiceConfig(
            name="prediction_service",
            service_type=ServiceType.PREDICTION_SERVICE,
            fail_max=4,                    # Moderate tolerance
            recovery_timeout=60,           # Standard recovery timeout
            timeout=20.0,                  # 20 second timeout
            fallback_enabled=True,         # Enable fallback responses
            priority=2                     # Medium priority service
        )
        self.enhanced_circuit_breaker_manager.register_service(prediction_config)
        
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
            
        logger.info("Enhanced orchestrator service shutdown complete")
    
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
    
    async def _call_rulegen_service(self, event_data: Dict[str, Any], rag_context: Dict[str, Any]) -> Dict[str, Any]:
        """Call rule generation service through enhanced circuit breaker"""
        
        async def rulegen_service_call():
            """Internal rule generation service call"""
            # Use RAG data if available, otherwise empty context
            context_data = []
            if rag_context.get('success', False):
                context_data = rag_context.get('data', {}).get('retrieved_context', [])
            
            payload = {
                "event": event_data,
                "context": context_data
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
        
        # Call through enhanced circuit breaker
        result = await self.enhanced_circuit_breaker_manager.call_service(
            "rulegen_service", 
            rulegen_service_call
        )
        
        return result
    
    async def _call_notifier_service(self, notification_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call notifier service through enhanced circuit breaker"""
        
        async def notifier_service_call():
            """Internal notifier service call"""
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
        
        # Call through enhanced circuit breaker
        result = await self.enhanced_circuit_breaker_manager.call_service(
            "notifier_service", 
            notifier_service_call
        )
        
        # If notification failed, queue for retry
        if not result.get('success', False):
            await self._enqueue_notification_retry(notification_payload)
        
        return result

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
                    # Try to send notification through circuit breaker
                    result = await self._call_notifier_service(retry_item["payload"])
                    
                    if result.get('success', False):
                        logger.info(f"Notification retry {retry_item['id']} succeeded")
                    else:
                        logger.warning(f"Notification retry {retry_item['id']} failed but not re-queuing")
                    
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
        Main orchestration logic with enhanced circuit breakers and fallback mechanisms
        
        Flow:
        1. Call RAG service (with fallback on failure)
        2. Call Rule Generation service (skip if RAG failed, use defaults on failure)
        3. Call Notifier service (queue for retry on failure)
        4. Return unified response with circuit breaker status
        """
        status = "ok"
        details = {}
        rag_result = None
        rule_result = None
        notification_result = None
        circuit_breaker_status = {}
        
        try:
            # Step 1: Call RAG Service
            logger.info("Calling RAG service for event analysis")
            rag_result = await self._call_rag_service(request.event_data, request.query)
            
            if not rag_result.get('success', False):
                status = "partial_success"
                logger.warning("RAG service call failed or returned fallback response")
            
            # Step 2: Call Rule Generation Service
            logger.info("Calling rule generation service for event evaluation")
            rule_result = await self._call_rulegen_service(request.event_data, rag_result or {})
            
            if not rule_result.get('success', False):
                if status == "ok":
                    status = "partial_success"
                logger.warning("Rule generation service call failed or returned fallback response")
            
            # Step 3: Call Notifier Service (if recipients provided)
            if request.recipients:
                logger.info("Calling notifier service for event notifications")
                
                # Construct notification payload
                notification_payload = {
                    "event": request.event_data,
                    "rag_analysis": rag_result.get('data', {}) if rag_result else {},
                    "rule_evaluation": rule_result.get('data', {}) if rule_result else {},
                    "channels": request.notification_channels,
                    "recipients": request.recipients,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                notification_result = await self._call_notifier_service(notification_payload)
                
                if not notification_result.get('success', False):
                    if status == "ok":
                        status = "partial_success"
                    logger.warning("Notifier service call failed or returned fallback response")
            else:
                logger.info("No recipients specified, skipping notification")
                notification_result = {"success": True, "message": "No recipients specified"}
            
            # Get circuit breaker status for all services
            circuit_breaker_status = await self.enhanced_circuit_breaker_manager.get_all_service_health()
            
            # Construct details
            details = {
                "processing_timestamp": datetime.utcnow().isoformat(),
                "services_called": ["rag_service", "rulegen_service"] + (["notifier_service"] if request.recipients else []),
                "fallback_used": any([
                    rag_result.get('fallback_used', False) if rag_result else False,
                    rule_result.get('fallback_used', False) if rule_result else False,
                    notification_result.get('fallback_used', False) if notification_result else False
                ])
            }
            
            logger.info(f"Orchestration completed with status: {status}")
            
        except Exception as e:
            logger.error(f"Orchestration failed with error: {e}")
            status = "error"
            details = {
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_timestamp": datetime.utcnow().isoformat()
            }
            
            # Still try to get circuit breaker status
            try:
                circuit_breaker_status = await self.enhanced_circuit_breaker_manager.get_all_service_health()
            except Exception as cb_e:
                logger.error(f"Failed to get circuit breaker status: {cb_e}")
                circuit_breaker_status = {"error": "Failed to retrieve circuit breaker status"}
        
        return OrchestrationResponse(
            status=status,
            details=details,
            rag_result=rag_result,
            rule_result=rule_result,
            notification_result=notification_result,
            circuit_breaker_status=circuit_breaker_status
        )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status including circuit breaker states"""
        health_status = {
            "orchestrator_status": "healthy",
            "redis_connected": False,
            "http_client_ready": False,
            "background_task_running": False,
            "circuit_breakers": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Check Redis connection
            if self.redis_client:
                await self.redis_client.ping()
                health_status["redis_connected"] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            health_status["orchestrator_status"] = "degraded"
        
        # Check HTTP client
        if self.http_client:
            health_status["http_client_ready"] = True
        
        # Check background task
        if self._background_task and not self._background_task.done():
            health_status["background_task_running"] = True
        
        # Get circuit breaker status
        if self.enhanced_circuit_breaker_manager:
            try:
                health_status["circuit_breakers"] = await self.enhanced_circuit_breaker_manager.get_all_service_health()
            except Exception as e:
                logger.error(f"Failed to get circuit breaker health: {e}")
                health_status["circuit_breakers"] = {"error": str(e)}
        
        return health_status

# Global enhanced orchestrator service instance
enhanced_orchestrator_service: Optional[EnhancedOrchestratorService] = None

def get_enhanced_orchestrator_service() -> EnhancedOrchestratorService:
    """Get or create the global enhanced orchestrator service"""
    global enhanced_orchestrator_service
    
    if enhanced_orchestrator_service is None:
        enhanced_orchestrator_service = EnhancedOrchestratorService()
    
    return enhanced_orchestrator_service

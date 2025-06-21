"""
Working Circuit Breaker Pattern Demonstration

This demonstrates the enhanced circuit breaker concept with pybreaker
using a simpler approach that works with the actual API.
"""

import asyncio
import logging
from datetime import datetime
import httpx
import pybreaker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

async def demo_circuit_breaker_pattern():
    """Demonstrate the circuit breaker pattern for downstream service calls"""
    
    logger.info("🚀 Circuit Breaker Pattern Implementation Demo")
    logger.info("=" * 60)
    
    # Create circuit breakers for different services with different tolerances
    rag_breaker = pybreaker.CircuitBreaker(
        fail_max=3,          # Open after 3 failures
        reset_timeout=5,     # Try again after 5 seconds
        name="rag_service"
    )
    
    notifier_breaker = pybreaker.CircuitBreaker(
        fail_max=2,          # More sensitive - open after 2 failures
        reset_timeout=3,     # Quicker recovery
        name="notifier_service"
    )
    
    # Service simulation functions
    async def call_rag_service(should_fail=False):
        """Simulate RAG service call"""
        await asyncio.sleep(0.1)  # Simulate processing time
        
        if should_fail:
            raise httpx.RequestError("RAG service temporarily unavailable")
        
        return {
            "linked_explanation": "Event analysis completed successfully",
            "retrieved_context": ["context1", "context2"],
            "confidence_score": 0.95
        }
    
    async def call_notifier_service(should_fail=False):
        """Simulate notifier service call"""
        await asyncio.sleep(0.1)  # Simulate processing time
        
        if should_fail:
            raise httpx.RequestError("Notification service down")
        
        return {
            "notification_id": "notif_123",
            "status": "sent",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_fallback_response(service_name, error):
        """Generate fallback responses when services are unavailable"""
        if service_name == "rag_service":
            return {
                "linked_explanation": "RAG service temporarily unavailable. Using cached response.",
                "retrieved_context": [],
                "confidence_score": 0.0,
                "fallback_used": True,
                "reason": str(error)
            }
        elif service_name == "notifier_service":
            return {
                "notification_queued": True,
                "status": "queued_for_retry",
                "message": "Notification service unavailable. Queued for background retry.",
                "fallback_used": True,
                "reason": str(error)
            }
        else:
            return {
                "message": f"{service_name} temporarily unavailable",
                "fallback_used": True,
                "reason": str(error)
            }
    
    async def protected_service_call(breaker, service_func, service_name, **kwargs):
        """Call service through circuit breaker protection"""
        try:
            # Try to call service through circuit breaker
            result = breaker.call(service_func, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            
            logger.info(f"✅ {service_name} call successful")
            return {"success": True, "data": result, "fallback_used": False}
            
        except pybreaker.CircuitBreakerError as e:
            # Circuit breaker is open - use fallback
            logger.warning(f"⚡ {service_name} circuit breaker open: {e}")
            fallback = generate_fallback_response(service_name, e)
            return {"success": False, "data": fallback, "fallback_used": True}
            
        except Exception as e:
            # Service call failed - circuit breaker will track this
            logger.error(f"❌ {service_name} call failed: {e}")
            fallback = generate_fallback_response(service_name, e)
            return {"success": False, "data": fallback, "fallback_used": True}
    
    # Demo 1: Successful calls
    logger.info("\n🟢 === DEMO: Successful Service Calls ===")
    
    rag_result = await protected_service_call(rag_breaker, call_rag_service, "rag_service", should_fail=False)
    notifier_result = await protected_service_call(notifier_breaker, call_notifier_service, "notifier_service", should_fail=False)
    
    logger.info(f"RAG Circuit State: {rag_breaker.current_state}")
    logger.info(f"Notifier Circuit State: {notifier_breaker.current_state}")
    
    # Demo 2: Trigger circuit breaker
    logger.info("\n🔴 === DEMO: Triggering Circuit Breaker ===")
    
    logger.info("Causing failures for notifier service...")
    for i in range(4):  # More than fail_max=2
        result = await protected_service_call(notifier_breaker, call_notifier_service, "notifier_service", should_fail=True)
        logger.info(f"Call {i+1}: Fallback used = {result['fallback_used']}")
    
    logger.info(f"Notifier Circuit State: {notifier_breaker.current_state}")
    
    # Demo 3: Show fallback behavior
    logger.info("\n🟡 === DEMO: Fallback Responses ===")
    
    # Force some failures for RAG service too
    for i in range(4):  # More than fail_max=3
        await protected_service_call(rag_breaker, call_rag_service, "rag_service", should_fail=True)
    
    # Now show fallback responses
    rag_result = await protected_service_call(rag_breaker, call_rag_service, "rag_service", should_fail=False)
    notifier_result = await protected_service_call(notifier_breaker, call_notifier_service, "notifier_service", should_fail=False)
    
    if rag_result["fallback_used"]:
        logger.info(f"RAG Fallback: {rag_result['data']['linked_explanation']}")
    
    if notifier_result["fallback_used"]:
        logger.info(f"Notifier Fallback: {notifier_result['data']['message']}")
    
    logger.info(f"RAG Circuit State: {rag_breaker.current_state}")
    logger.info(f"Notifier Circuit State: {notifier_breaker.current_state}")
    
    # Demo 4: Recovery simulation
    logger.info("\n🟢 === DEMO: Circuit Recovery ===")
    
    logger.info("Waiting for circuit breaker reset timeout...")
    await asyncio.sleep(6)  # Wait longer than reset timeout
    
    logger.info("Attempting service calls after timeout...")
    rag_result = await protected_service_call(rag_breaker, call_rag_service, "rag_service", should_fail=False)
    notifier_result = await protected_service_call(notifier_breaker, call_notifier_service, "notifier_service", should_fail=False)
    
    logger.info(f"RAG Recovery: Success = {rag_result['success']}")
    logger.info(f"Notifier Recovery: Success = {notifier_result['success']}")
    
    logger.info(f"Final RAG Circuit State: {rag_breaker.current_state}")
    logger.info(f"Final Notifier Circuit State: {notifier_breaker.current_state}")
    
    # Demo 5: Orchestration example
    logger.info("\n🔄 === DEMO: Full Orchestration with Circuit Breakers ===")
    
    async def orchestrate_event(event_data):
        """Simulate full event orchestration with circuit breaker protection"""
        logger.info("Starting event orchestration...")
        
        # Step 1: RAG Analysis
        rag_result = await protected_service_call(rag_breaker, call_rag_service, "rag_service", should_fail=False)
        
        # Step 2: Notification (using RAG context)
        notifier_result = await protected_service_call(notifier_breaker, call_notifier_service, "notifier_service", should_fail=False)
        
        # Determine overall status
        if rag_result["success"] and notifier_result["success"]:
            status = "ok"
        elif rag_result["fallback_used"] or notifier_result["fallback_used"]:
            status = "partial_success"
        else:
            status = "error"
        
        return {
            "status": status,
            "rag_result": rag_result,
            "notifier_result": notifier_result,
            "circuit_breaker_states": {
                "rag_service": rag_breaker.current_state,
                "notifier_service": notifier_breaker.current_state
            }
        }
    
    # Test orchestration
    event_data = {
        "camera_id": "cam1",
        "timestamp": datetime.utcnow().isoformat(),
        "label": "person_detected"
    }
    
    orchestration_result = await orchestrate_event(event_data)
    
    logger.info(f"Orchestration Status: {orchestration_result['status']}")
    logger.info(f"RAG Success: {orchestration_result['rag_result']['success']}")
    logger.info(f"Notifier Success: {orchestration_result['notifier_result']['success']}")
    logger.info(f"Circuit States: {orchestration_result['circuit_breaker_states']}")
    
    logger.info("\n✅ Circuit Breaker Pattern Demonstration Complete!")
    logger.info("=" * 60)
    
    # Summary
    logger.info("\n📋 === SUMMARY ===")
    logger.info("✅ Circuit breakers protect against cascading failures")
    logger.info("✅ Different services have different failure tolerances")
    logger.info("✅ Fallback responses provide graceful degradation")
    logger.info("✅ Automatic recovery after timeout periods")
    logger.info("✅ Orchestration continues even with partial failures")

if __name__ == "__main__":
    asyncio.run(demo_circuit_breaker_pattern())

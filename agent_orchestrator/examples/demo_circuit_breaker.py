"""
Circuit Breaker Pattern Demonstration Script

This script demonstrates the enhanced circuit breaker functionality including:
- Service registration and configuration
- State transitions during failures
- Fallback response generation
- Recovery behavior
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx

from enhanced_circuit_breaker import (
    EnhancedCircuitBreakerManager,
    ServiceConfig,
    ServiceType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircuitBreakerDemo:
    """Demonstration of circuit breaker functionality"""
    
    def __init__(self):
        self.manager = EnhancedCircuitBreakerManager()
        
    async def setup_services(self):
        """Register demo services with different configurations"""
        
        # Demo RAG service - more tolerant
        rag_config = ServiceConfig(
            name="demo_rag_service",
            service_type=ServiceType.RAG_SERVICE,
            fail_max=3,
            recovery_timeout=5,  # Short for demo
            timeout=2.0,
            fallback_enabled=True,
            priority=1
        )
        self.manager.register_service(rag_config)
        
        # Demo notification service - less tolerant  
        notifier_config = ServiceConfig(
            name="demo_notifier_service", 
            service_type=ServiceType.NOTIFIER_SERVICE,
            fail_max=2,
            recovery_timeout=3,  # Short for demo
            timeout=1.0,
            fallback_enabled=True,
            priority=1
        )
        self.manager.register_service(notifier_config)
        
        logger.info("✅ Demo services registered")
    
    async def demo_successful_calls(self):
        """Demonstrate successful service calls"""
        logger.info("\n🟢 === DEMO: Successful Service Calls ===")
        
        async def successful_rag_call():
            await asyncio.sleep(0.1)  # Simulate processing
            return {
                "linked_explanation": "Analysis completed successfully",
                "retrieved_context": ["context1", "context2"],
                "confidence_score": 0.95
            }
        
        async def successful_notifier_call():
            await asyncio.sleep(0.1)  # Simulate processing
            return {
                "notification_id": "notif_123",
                "status": "sent",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Test successful calls
        rag_result = await self.manager.call_service("demo_rag_service", successful_rag_call)
        notifier_result = await self.manager.call_service("demo_notifier_service", successful_notifier_call)
        
        logger.info(f"RAG Result: Success={rag_result['success']}, Response Time={rag_result['response_time']:.3f}s")
        logger.info(f"Notifier Result: Success={notifier_result['success']}, Response Time={notifier_result['response_time']:.3f}s")
        
        # Show circuit breaker states
        await self.show_circuit_breaker_status()
    
    async def demo_circuit_breaker_opening(self):
        """Demonstrate circuit breaker opening due to failures"""
        logger.info("\n🔴 === DEMO: Circuit Breaker Opening ===")
        
        async def failing_service_call():
            raise httpx.RequestError("Service temporarily unavailable")
        
        # Trigger failures for notifier service (fail_max=2)
        logger.info("Triggering failures for demo_notifier_service...")
        
        for i in range(4):  # More than fail_max
            result = await self.manager.call_service("demo_notifier_service", failing_service_call)
            logger.info(f"Call {i+1}: Success={result['success']}, Fallback={result.get('fallback_used', False)}")
            
            # Show state after each call
            health = await self.manager.get_service_health("demo_notifier_service")
            logger.info(f"  Circuit State: {health['circuit_breaker_state']}")
        
        await self.show_circuit_breaker_status()
    
    async def demo_fallback_responses(self):
        """Demonstrate different fallback responses"""
        logger.info("\n🟡 === DEMO: Fallback Response Generation ===")
        
        async def failing_call():
            raise httpx.RequestError("Service down")
        
        # Force circuit breakers open
        await self.manager.force_circuit_state("demo_rag_service", "open")
        await self.manager.force_circuit_state("demo_notifier_service", "open")
        
        # Call services with open circuit breakers
        rag_result = await self.manager.call_service("demo_rag_service", failing_call)
        notifier_result = await self.manager.call_service("demo_notifier_service", failing_call)
        
        logger.info("RAG Fallback Response:")
        logger.info(f"  - Explanation: {rag_result['data']['linked_explanation']}")
        logger.info(f"  - Context: {rag_result['data']['retrieved_context']}")
        logger.info(f"  - Confidence: {rag_result['data']['confidence_score']}")
        
        logger.info("Notifier Fallback Response:")
        logger.info(f"  - Status: {notifier_result['data']['status']}")
        logger.info(f"  - Queued: {notifier_result['data']['notification_queued']}")
        logger.info(f"  - Message: {notifier_result['data']['message']}")
    
    async def demo_circuit_breaker_recovery(self):
        """Demonstrate circuit breaker recovery"""
        logger.info("\n🟢 === DEMO: Circuit Breaker Recovery ===")
        
        async def recovering_service_call():
            await asyncio.sleep(0.1)
            return {"status": "recovered", "message": "Service is back online"}
        
        # Close circuits manually for demo
        await self.manager.force_circuit_state("demo_rag_service", "closed")
        await self.manager.force_circuit_state("demo_notifier_service", "closed")
        
        logger.info("Circuit breakers reset to closed state")
        
        # Make successful calls
        rag_result = await self.manager.call_service("demo_rag_service", recovering_service_call)
        notifier_result = await self.manager.call_service("demo_notifier_service", recovering_service_call)
        
        logger.info(f"RAG Recovery: Success={rag_result['success']}")
        logger.info(f"Notifier Recovery: Success={notifier_result['success']}")
        
        await self.show_circuit_breaker_status()
    
    async def demo_concurrent_load(self):
        """Demonstrate circuit breaker behavior under concurrent load"""
        logger.info("\n⚡ === DEMO: Concurrent Load Testing ===")
        
        async def variable_service_call(call_id: int):
            await asyncio.sleep(0.1)
            if call_id % 4 == 0:  # Every 4th call fails
                raise httpx.RequestError(f"Call {call_id} failed")
            return {"call_id": call_id, "result": "success"}
        
        # Reset circuit breakers
        await self.manager.force_circuit_state("demo_rag_service", "closed")
        
        # Make concurrent calls
        logger.info("Making 20 concurrent calls with 25% failure rate...")
        
        tasks = []
        for i in range(20):
            task = asyncio.create_task(
                self.manager.call_service(
                    "demo_rag_service", 
                    lambda i=i: variable_service_call(i)
                )
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successes = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        fallbacks = sum(1 for r in results if isinstance(r, dict) and r.get("fallback_used"))
        errors = len(results) - successes - fallbacks
        
        logger.info(f"Results: {successes} successes, {fallbacks} fallbacks, {errors} errors")
        
        await self.show_circuit_breaker_status()
    
    async def show_circuit_breaker_status(self):
        """Display current circuit breaker status"""
        health = await self.manager.get_all_service_health()
        
        logger.info("\n📊 Circuit Breaker Status:")
        for service_name, status in health["services"].items():
            state = status["circuit_breaker_state"]
            fail_count = status["fail_counter"]
            config = status["configuration"]
            
            state_emoji = {"closed": "🟢", "open": "🔴", "half-open": "🟡"}.get(state, "❓")
            logger.info(f"  {state_emoji} {service_name}: {state.upper()} (failures: {fail_count}/{config['fail_max']})")
    
    async def run_demo(self):
        """Run the complete circuit breaker demonstration"""
        logger.info("🚀 Starting Enhanced Circuit Breaker Demonstration")
        logger.info("=" * 60)
        
        try:
            await self.setup_services()
            await self.demo_successful_calls()
            await asyncio.sleep(1)
            
            await self.demo_circuit_breaker_opening()
            await asyncio.sleep(1)
            
            await self.demo_fallback_responses()
            await asyncio.sleep(1)
            
            await self.demo_circuit_breaker_recovery()
            await asyncio.sleep(1)
            
            await self.demo_concurrent_load()
            
            logger.info("\n✅ Circuit Breaker Demonstration Complete!")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            raise

async def main():
    """Main demo function"""
    demo = CircuitBreakerDemo()
    await demo.run_demo()

if __name__ == "__main__":
    asyncio.run(main())

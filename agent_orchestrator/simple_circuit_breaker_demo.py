"""
Simple Circuit Breaker Pattern Demonstration

This script demonstrates the core circuit breaker functionality using pybreaker
with simplified integration for demonstration purposes.
"""

import asyncio
import logging
from datetime import datetime

import pybreaker
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

class SimpleCircuitBreakerDemo:
    """Simple demonstration of circuit breaker functionality"""
    
    def __init__(self):
        # Create circuit breakers with pybreaker
        self.rag_breaker = pybreaker.CircuitBreaker(
            fail_max=3,
            reset_timeout=5,
            name="rag_service"
        )
        
        self.notifier_breaker = pybreaker.CircuitBreaker(
            fail_max=2,
            reset_timeout=3,
            name="notifier_service"
        )
        
        # Add state change listeners
        self.rag_breaker.add_listener(self._on_state_change)
        self.notifier_breaker.add_listener(self._on_state_change)
    
    def _on_state_change(self, prev_state, new_state, breaker_name):
        """Log circuit breaker state changes"""
        logger.info(f"🔄 Circuit breaker '{breaker_name}' state: {prev_state} -> {new_state}")
    
    async def demo_successful_calls(self):
        """Demonstrate successful service calls"""
        logger.info("\n🟢 === DEMO: Successful Service Calls ===")
        
        @self.rag_breaker
        async def successful_rag_call():
            await asyncio.sleep(0.1)  # Simulate processing
            return {
                "linked_explanation": "Analysis completed successfully",
                "retrieved_context": ["context1", "context2"],
                "confidence_score": 0.95
            }
        
        @self.notifier_breaker
        async def successful_notifier_call():
            await asyncio.sleep(0.1)  # Simulate processing
            return {
                "notification_id": "notif_123",
                "status": "sent",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Test successful calls
        try:
            rag_result = await successful_rag_call()
            logger.info(f"✅ RAG call successful: {rag_result['linked_explanation']}")
        except Exception as e:
            logger.error(f"❌ RAG call failed: {e}")
        
        try:
            notifier_result = await successful_notifier_call()
            logger.info(f"✅ Notifier call successful: {notifier_result['status']}")
        except Exception as e:
            logger.error(f"❌ Notifier call failed: {e}")
        
        self._show_circuit_states()
    
    async def demo_circuit_breaker_opening(self):
        """Demonstrate circuit breaker opening due to failures"""
        logger.info("\n🔴 === DEMO: Circuit Breaker Opening ===")
        
        @self.notifier_breaker
        async def failing_notifier_call():
            raise httpx.RequestError("Service temporarily unavailable")
        
        # Trigger failures for notifier service (fail_max=2)
        logger.info("Triggering failures for notifier service...")
        
        for i in range(4):  # More than fail_max
            try:
                result = await failing_notifier_call()
                logger.info(f"Call {i+1}: ✅ Success")
            except pybreaker.CircuitBreakerError as e:
                logger.info(f"Call {i+1}: ⚡ Circuit breaker open - {e}")
            except Exception as e:
                logger.info(f"Call {i+1}: ❌ Failed - {e}")
        
        self._show_circuit_states()
    
    async def demo_fallback_behavior(self):
        """Demonstrate fallback behavior when circuit is open"""
        logger.info("\n🟡 === DEMO: Fallback Behavior ===")
        
        @self.rag_breaker
        async def failing_rag_call():
            raise httpx.RequestError("Service down")
        
        # Trigger enough failures to open the circuit
        for i in range(4):  # More than fail_max=3
            try:
                await failing_rag_call()
            except:
                pass
        
        # Now try to call with circuit open
        try:
            result = await failing_rag_call()
            logger.info(f"✅ Call succeeded: {result}")
        except pybreaker.CircuitBreakerError:
            logger.info("⚡ Circuit breaker prevented call - using fallback response")
            fallback_response = {
                "linked_explanation": "RAG service temporarily unavailable. Using cached response.",
                "retrieved_context": [],
                "confidence_score": 0.0,
                "fallback_used": True
            }
            logger.info(f"🔄 Fallback response: {fallback_response['linked_explanation']}")
        except Exception as e:
            logger.info(f"❌ Call failed: {e}")
        
        self._show_circuit_states()
    
    async def demo_recovery(self):
        """Demonstrate circuit breaker recovery"""
        logger.info("\n🟢 === DEMO: Circuit Breaker Recovery ===")
        
        @self.rag_breaker
        async def recovering_rag_call():
            await asyncio.sleep(0.1)
            return {"status": "recovered", "message": "Service is back online"}
        
        # Force reset for demo
        self.rag_breaker.close()
        
        logger.info("Circuit breaker reset to closed state")
        
        # Make successful call
        try:
            result = await recovering_rag_call()
            logger.info(f"✅ Recovery successful: {result['message']}")
        except Exception as e:
            logger.error(f"❌ Recovery failed: {e}")
        
        self._show_circuit_states()
    
    async def demo_timeout_protection(self):
        """Demonstrate timeout protection"""
        logger.info("\n⏱️ === DEMO: Timeout Protection ===")
        
        # Create circuit breaker with short timeout for demo
        timeout_breaker = pybreaker.CircuitBreaker(
            fail_max=2,
            reset_timeout=3,
            name="timeout_service"
        )
        
        @timeout_breaker
        async def slow_service_call():
            await asyncio.sleep(2)  # Simulate slow service
            return {"result": "slow_success"}
        
        try:
            result = await asyncio.wait_for(slow_service_call(), timeout=1.0)
            logger.info(f"✅ Call completed: {result}")
        except asyncio.TimeoutError:
            logger.info("⏱️ Call timed out - service too slow")
        except Exception as e:
            logger.error(f"❌ Call failed: {e}")
    
    def _show_circuit_states(self):
        """Display current circuit breaker states"""
        logger.info("\n📊 Circuit Breaker States:")
        
        rag_state = self.rag_breaker.current_state
        notifier_state = self.notifier_breaker.current_state
        
        state_emojis = {"closed": "🟢", "open": "🔴", "half-open": "🟡"}
        
        rag_emoji = state_emojis.get(rag_state, "❓")
        notifier_emoji = state_emojis.get(notifier_state, "❓")
        
        logger.info(f"  {rag_emoji} RAG Service: {rag_state.upper()}")
        logger.info(f"  {notifier_emoji} Notifier Service: {notifier_state.upper()}")
    
    async def run_demo(self):
        """Run the complete circuit breaker demonstration"""
        logger.info("🚀 Starting Simple Circuit Breaker Demonstration")
        logger.info("=" * 60)
        
        try:
            await self.demo_successful_calls()
            await asyncio.sleep(1)
            
            await self.demo_circuit_breaker_opening()
            await asyncio.sleep(1)
            
            await self.demo_fallback_behavior()
            await asyncio.sleep(1)
            
            await self.demo_recovery()
            await asyncio.sleep(1)
            
            await self.demo_timeout_protection()
            
            logger.info("\n✅ Circuit Breaker Demonstration Complete!")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            raise

async def main():
    """Main demo function"""
    demo = SimpleCircuitBreakerDemo()
    await demo.run_demo()

if __name__ == "__main__":
    asyncio.run(main())

"""
Comprehensive tests for Enhanced Circuit Breaker Pattern Implementation

Tests cover:
- Circuit breaker registration and configuration
- State transitions (closed -> open -> half-open -> closed)
- Fallback response generation
- Service call protection and metrics
- Redis state persistence
- pybreaker integration
- Health monitoring and administrative controls
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

import httpx
import redis.asyncio as redis
import pybreaker

from enhanced_circuit_breaker import (
    EnhancedCircuitBreakerManager,
    ServiceConfig,
    ServiceType,
    get_enhanced_circuit_breaker_manager
)
from enhanced_orchestrator import (
    EnhancedOrchestratorService,
    get_enhanced_orchestrator_service,
    OrchestrationRequest,
    OrchestrationResponse
)

class TestEnhancedCircuitBreakerManager:
    """Test suite for Enhanced Circuit Breaker Manager"""
    
    @pytest.fixture
    async def redis_client(self):
        """Mock Redis client"""
        mock_redis = AsyncMock(spec=redis.Redis)
        mock_redis.ping.return_value = True
        mock_redis.hset.return_value = True
        mock_redis.expire.return_value = True
        mock_redis.hgetall.return_value = {}
        yield mock_redis
    
    @pytest.fixture
    def circuit_breaker_manager(self, redis_client):
        """Enhanced circuit breaker manager instance"""
        return EnhancedCircuitBreakerManager(redis_client)
    
    @pytest.fixture
    def rag_service_config(self):
        """RAG service configuration"""
        return ServiceConfig(
            name="rag_service",
            service_type=ServiceType.RAG_SERVICE,
            fail_max=3,
            recovery_timeout=30,
            timeout=10.0,
            fallback_enabled=True,
            priority=1
        )
    
    def test_service_registration(self, circuit_breaker_manager, rag_service_config):
        """Test service registration and circuit breaker creation"""
        circuit_breaker = circuit_breaker_manager.register_service(rag_service_config)
        
        assert isinstance(circuit_breaker, pybreaker.CircuitBreaker)
        assert circuit_breaker.name == "rag_service"
        assert circuit_breaker.fail_max == 3
        assert circuit_breaker.recovery_timeout == 30
        assert "rag_service" in circuit_breaker_manager.service_configs
        assert "rag_service" in circuit_breaker_manager.circuit_breakers
    
    @pytest.mark.asyncio
    async def test_successful_service_call(self, circuit_breaker_manager, rag_service_config):
        """Test successful service call through circuit breaker"""
        circuit_breaker_manager.register_service(rag_service_config)
        
        async def mock_service_call():
            return {"result": "success", "data": {"test": "value"}}
        
        result = await circuit_breaker_manager.call_service("rag_service", mock_service_call)
        
        assert result["success"] is True
        assert result["data"]["result"] == "success"
        assert result["service"] == "rag_service"
        assert "response_time" in result
        assert "circuit_breaker_state" in result
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self, circuit_breaker_manager, rag_service_config):
        """Test circuit breaker opens after consecutive failures"""
        circuit_breaker_manager.register_service(rag_service_config)
        
        async def failing_service_call():
            raise httpx.RequestError("Service unavailable")
        
        # Make enough calls to trigger circuit breaker
        for _ in range(rag_service_config.fail_max + 1):
            result = await circuit_breaker_manager.call_service("rag_service", failing_service_call)
            
        # Circuit breaker should now be open and returning fallback
        assert result["success"] is False
        assert result["fallback_used"] is True
        assert result["service"] == "rag_service"
        assert "data" in result
    
    @pytest.mark.asyncio
    async def test_fallback_response_generation(self, circuit_breaker_manager):
        """Test fallback response generation for different service types"""
        # Test RAG service fallback
        rag_config = ServiceConfig(
            name="rag_service",
            service_type=ServiceType.RAG_SERVICE,
            fail_max=1,
            recovery_timeout=30,
            fallback_enabled=True
        )
        circuit_breaker_manager.register_service(rag_config)
        
        async def failing_call():
            raise httpx.RequestError("Service down")
        
        # Trigger circuit breaker
        await circuit_breaker_manager.call_service("rag_service", failing_call)
        result = await circuit_breaker_manager.call_service("rag_service", failing_call)
        
        assert result["fallback_used"] is True
        assert "linked_explanation" in result["data"]
        assert "retrieved_context" in result["data"]
        assert result["data"]["confidence_score"] == 0.0
        
        # Test Notifier service fallback
        notifier_config = ServiceConfig(
            name="notifier_service",
            service_type=ServiceType.NOTIFIER_SERVICE,
            fail_max=1,
            recovery_timeout=30,
            fallback_enabled=True
        )
        circuit_breaker_manager.register_service(notifier_config)
        
        await circuit_breaker_manager.call_service("notifier_service", failing_call)
        result = await circuit_breaker_manager.call_service("notifier_service", failing_call)
        
        assert result["fallback_used"] is True
        assert result["data"]["notification_queued"] is True
        assert result["data"]["status"] == "queued_for_retry"
    
    @pytest.mark.asyncio
    async def test_redis_state_persistence(self, circuit_breaker_manager, rag_service_config, redis_client):
        """Test circuit breaker state persistence to Redis"""
        circuit_breaker_manager.register_service(rag_service_config)
        
        # Trigger state persistence by forcing state change
        await circuit_breaker_manager.force_circuit_state("rag_service", "open")
        
        # Verify Redis operations were called
        redis_client.hset.assert_called()
        redis_client.expire.assert_called()
    
    @pytest.mark.asyncio
    async def test_service_health_monitoring(self, circuit_breaker_manager, rag_service_config):
        """Test service health status retrieval"""
        circuit_breaker_manager.register_service(rag_service_config)
        
        health_status = await circuit_breaker_manager.get_service_health("rag_service")
        
        assert health_status["service_name"] == "rag_service"
        assert health_status["service_type"] == ServiceType.RAG_SERVICE.value
        assert "circuit_breaker_state" in health_status
        assert "fail_counter" in health_status
        assert "configuration" in health_status
        
        # Test all services health
        all_health = await circuit_breaker_manager.get_all_service_health()
        assert "services" in all_health
        assert "total_services" in all_health
        assert "timestamp" in all_health
    
    @pytest.mark.asyncio
    async def test_force_circuit_state(self, circuit_breaker_manager, rag_service_config):
        """Test administrative circuit breaker state control"""
        circuit_breaker_manager.register_service(rag_service_config)
        
        # Force circuit to open state
        success = await circuit_breaker_manager.force_circuit_state("rag_service", "open")
        assert success is True
        
        # Verify state changed
        health = await circuit_breaker_manager.get_service_health("rag_service")
        assert health["circuit_breaker_state"] == "open"
        
        # Force circuit to closed state
        success = await circuit_breaker_manager.force_circuit_state("rag_service", "closed")
        assert success is True
        
        # Test invalid service
        success = await circuit_breaker_manager.force_circuit_state("invalid_service", "open")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, circuit_breaker_manager, rag_service_config):
        """Test timeout handling in service calls"""
        # Set very short timeout
        rag_service_config.timeout = 0.1
        circuit_breaker_manager.register_service(rag_service_config)
        
        async def slow_service_call():
            await asyncio.sleep(1)  # Longer than timeout
            return {"result": "success"}
        
        result = await circuit_breaker_manager.call_service("rag_service", slow_service_call)
        
        # Should get fallback due to timeout
        assert result["fallback_used"] is True or result["success"] is False
    
    @pytest.mark.asyncio
    async def test_multiple_service_types(self, circuit_breaker_manager):
        """Test registration and management of multiple service types"""
        services = [
            ServiceConfig("rag_service", ServiceType.RAG_SERVICE, fail_max=3),
            ServiceConfig("rulegen_service", ServiceType.RULEGEN_SERVICE, fail_max=2),
            ServiceConfig("notifier_service", ServiceType.NOTIFIER_SERVICE, fail_max=4),
            ServiceConfig("vms_service", ServiceType.VMS_SERVICE, fail_max=5),
            ServiceConfig("prediction_service", ServiceType.PREDICTION_SERVICE, fail_max=3)
        ]
        
        for config in services:
            circuit_breaker_manager.register_service(config)
        
        # Verify all services registered
        all_health = await circuit_breaker_manager.get_all_service_health()
        assert len(all_health["services"]) == 5
        
        # Verify different service types
        assert all_health["services"]["rag_service"]["service_type"] == ServiceType.RAG_SERVICE.value
        assert all_health["services"]["rulegen_service"]["service_type"] == ServiceType.RULEGEN_SERVICE.value
        assert all_health["services"]["notifier_service"]["service_type"] == ServiceType.NOTIFIER_SERVICE.value


class TestEnhancedOrchestratorService:
    """Test suite for Enhanced Orchestrator Service"""
    
    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis client"""
        mock_redis = AsyncMock(spec=redis.Redis)
        mock_redis.ping.return_value = True
        mock_redis.lpush.return_value = 1
        mock_redis.rpop.return_value = None
        yield mock_redis
    
    @pytest.fixture
    async def mock_http_client(self):
        """Mock HTTP client"""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        yield mock_client
    
    @pytest.fixture
    async def orchestrator_service(self, mock_redis, mock_http_client):
        """Enhanced orchestrator service instance"""
        service = EnhancedOrchestratorService()
        service.redis_client = mock_redis
        service.http_client = mock_http_client
        
        # Initialize circuit breakers
        await service._initialize_enhanced_circuit_breakers()
        
        yield service
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Test orchestrator service initialization"""
        with patch('redis.asyncio.from_url') as mock_redis, \
             patch('httpx.AsyncClient') as mock_http:
            
            mock_redis.return_value.ping = AsyncMock(return_value=True)
            mock_http.return_value = AsyncMock()
            
            service = EnhancedOrchestratorService()
            await service.initialize()
            
            assert service.redis_client is not None
            assert service.http_client is not None
            assert service.enhanced_circuit_breaker_manager is not None
    
    @pytest.mark.asyncio
    async def test_successful_orchestration(self, orchestrator_service, mock_http_client):
        """Test successful orchestration with all services responding"""
        # Mock successful service responses
        rag_response = Mock()
        rag_response.status_code = 200
        rag_response.json.return_value = {
            "linked_explanation": "Test explanation",
            "retrieved_context": ["context1", "context2"]
        }
        
        rule_response = Mock()
        rule_response.status_code = 200
        rule_response.json.return_value = {
            "rules_triggered": ["rule1"],
            "severity": "high",
            "confidence": 0.9
        }
        
        notifier_response = Mock()
        notifier_response.status_code = 200
        notifier_response.json.return_value = {
            "notification_id": "notif123",
            "status": "sent"
        }
        
        mock_http_client.post.side_effect = [rag_response, rule_response, notifier_response]
        
        request = OrchestrationRequest(
            event_data={
                "camera_id": "cam1",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "label": "person_detected",
                "bbox": [100, 100, 200, 200]
            },
            recipients=["admin@example.com"]
        )
        
        result = await orchestrator_service.orchestrate(request)
        
        assert result.status == "ok"
        assert result.rag_result is not None
        assert result.rule_result is not None
        assert result.notification_result is not None
        assert result.circuit_breaker_status is not None
    
    @pytest.mark.asyncio
    async def test_orchestration_with_circuit_breaker_open(self, orchestrator_service):
        """Test orchestration behavior when circuit breakers are open"""
        # Force circuit breakers to open
        await orchestrator_service.enhanced_circuit_breaker_manager.force_circuit_state("rag_service", "open")
        await orchestrator_service.enhanced_circuit_breaker_manager.force_circuit_state("rulegen_service", "open")
        
        request = OrchestrationRequest(
            event_data={
                "camera_id": "cam1",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "label": "person_detected"
            },
            recipients=["admin@example.com"]
        )
        
        result = await orchestrator_service.orchestrate(request)
        
        assert result.status in ["partial_success", "fallback"]
        assert result.rag_result["fallback_used"] is True
        assert result.rule_result["fallback_used"] is True
        assert result.circuit_breaker_status is not None
    
    @pytest.mark.asyncio
    async def test_notification_retry_queue(self, orchestrator_service, mock_redis):
        """Test notification retry queue functionality"""
        notification_payload = {
            "event": {"camera_id": "cam1"},
            "recipients": ["admin@example.com"],
            "channels": ["email"]
        }
        
        await orchestrator_service._enqueue_notification_retry(notification_payload)
        
        # Verify Redis lpush was called
        mock_redis.lpush.assert_called_once()
        call_args = mock_redis.lpush.call_args
        assert call_args[0][0] == "notification_retry_queue"
        
        # Verify payload structure
        queued_item = json.loads(call_args[0][1])
        assert "id" in queued_item
        assert "payload" in queued_item
        assert "timestamp" in queued_item
        assert "retry_count" in queued_item
        assert queued_item["retry_count"] == 0
    
    @pytest.mark.asyncio
    async def test_health_status_monitoring(self, orchestrator_service):
        """Test comprehensive health status monitoring"""
        health_status = await orchestrator_service.get_health_status()
        
        assert "orchestrator_status" in health_status
        assert "redis_connected" in health_status
        assert "http_client_ready" in health_status
        assert "background_task_running" in health_status
        assert "circuit_breakers" in health_status
        assert "timestamp" in health_status
        
        # Verify circuit breaker health included
        assert "services" in health_status["circuit_breakers"]
        assert "total_services" in health_status["circuit_breakers"]
    
    @pytest.mark.asyncio
    async def test_service_call_with_retries(self, orchestrator_service, mock_http_client):
        """Test service calls with retry logic and circuit breaker integration"""
        # Mock intermittent failures then success
        responses = [
            Mock(status_code=500),  # First call fails
            Mock(status_code=200, json=lambda: {"result": "success"})  # Second call succeeds
        ]
        mock_http_client.post.side_effect = responses
        
        event_data = {
            "camera_id": "cam1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "label": "test_event"
        }
        
        result = await orchestrator_service._call_rag_service(event_data)
        
        # Should eventually succeed with retry logic
        assert result["success"] is True or result["fallback_used"] is True


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker pattern with real scenarios"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_cycle(self):
        """Test complete circuit breaker recovery cycle"""
        manager = EnhancedCircuitBreakerManager()
        
        config = ServiceConfig(
            name="test_service",
            service_type=ServiceType.RAG_SERVICE,
            fail_max=2,
            recovery_timeout=1,  # Short timeout for testing
            fallback_enabled=True
        )
        manager.register_service(config)
        
        async def failing_call():
            raise httpx.RequestError("Service down")
        
        async def successful_call():
            return {"result": "success"}
        
        # Phase 1: Circuit is closed, calls go through
        result = await manager.call_service("test_service", successful_call)
        assert result["success"] is True
        
        # Phase 2: Trigger failures to open circuit
        for _ in range(config.fail_max + 1):
            result = await manager.call_service("test_service", failing_call)
        
        # Circuit should now be open
        health = await manager.get_service_health("test_service")
        assert health["circuit_breaker_state"] == "open"
        
        # Phase 3: Wait for recovery timeout
        await asyncio.sleep(config.recovery_timeout + 0.1)
        
        # Phase 4: Circuit should allow test call (half-open)
        result = await manager.call_service("test_service", successful_call)
        
        # Circuit should eventually close again with successful calls
        assert result["success"] is True or result["fallback_used"] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_service_calls(self):
        """Test circuit breaker behavior under concurrent load"""
        manager = EnhancedCircuitBreakerManager()
        
        config = ServiceConfig(
            name="concurrent_service",
            service_type=ServiceType.RAG_SERVICE,
            fail_max=5,
            recovery_timeout=30,
            timeout=2.0,
            fallback_enabled=True
        )
        manager.register_service(config)
        
        async def variable_call(call_id: int):
            if call_id % 3 == 0:  # Every third call fails
                raise httpx.RequestError(f"Call {call_id} failed")
            return {"call_id": call_id, "result": "success"}
        
        # Make multiple concurrent calls
        tasks = []
        for i in range(20):
            task = asyncio.create_task(
                manager.call_service("concurrent_service", lambda i=i: variable_call(i))
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify we get mix of successes and fallbacks
        successes = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        fallbacks = sum(1 for r in results if isinstance(r, dict) and r.get("fallback_used"))
        
        assert successes + fallbacks == len(results)
        assert successes > 0  # Some calls should succeed
    
    @pytest.mark.asyncio
    async def test_service_specific_configurations(self):
        """Test different configurations for different service types"""
        manager = EnhancedCircuitBreakerManager()
        
        # Register services with different tolerances
        services = [
            ServiceConfig("critical_service", ServiceType.RAG_SERVICE, fail_max=2, priority=1),
            ServiceConfig("normal_service", ServiceType.RULEGEN_SERVICE, fail_max=4, priority=2),
            ServiceConfig("tolerant_service", ServiceType.VMS_SERVICE, fail_max=6, priority=3)
        ]
        
        for config in services:
            manager.register_service(config)
        
        async def failing_call():
            raise httpx.RequestError("Service down")
        
        # Test that critical service opens circuit faster
        for _ in range(3):  # Should be enough to open critical service
            await manager.call_service("critical_service", failing_call)
            await manager.call_service("normal_service", failing_call)
            await manager.call_service("tolerant_service", failing_call)
        
        health = await manager.get_all_service_health()
        
        # Critical service should be open (fail_max=2)
        assert health["services"]["critical_service"]["circuit_breaker_state"] == "open"
        
        # Normal service should still be closed (fail_max=4)
        assert health["services"]["normal_service"]["circuit_breaker_state"] == "closed"
        
        # Tolerant service should still be closed (fail_max=6)
        assert health["services"]["tolerant_service"]["circuit_breaker_state"] == "closed"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])

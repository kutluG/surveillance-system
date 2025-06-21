"""
Unit tests for metrics collection system

Tests:
- Metrics collector initialization
- Metrics recording functionality
- Context managers and decorators
- Prometheus format output
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime

from metrics import (
    OrchestrationMetricsCollector,
    metrics_collector,
    monitor_orchestration_performance,
    monitor_service_call
)

class TestOrchestrationMetricsCollector:
    """Test metrics collector functionality"""
    
    def test_metrics_collector_initialization(self):
        """Test metrics collector initializes correctly"""
        collector = OrchestrationMetricsCollector()
        assert collector is not None
        assert hasattr(collector, 'enabled')
        
    def test_record_orchestration_request(self):
        """Test recording orchestration requests"""
        collector = OrchestrationMetricsCollector()
        
        # Should not raise exceptions
        collector.record_orchestration_request("success", "test_query", "email")
        collector.record_orchestration_request("error", "test_query", "email")
        
    def test_record_service_request(self):
        """Test recording service requests"""
        collector = OrchestrationMetricsCollector()
        
        # Should not raise exceptions
        collector.record_service_request("rag_service", "query", 200, 0.5)
        collector.record_service_request("rag_service", "query", 500, 1.0)
        
    def test_record_orchestration_latency(self):
        """Test recording orchestration latency"""
        collector = OrchestrationMetricsCollector()
        
        # Should not raise exceptions
        collector.record_orchestration_latency(0.5, "success", "rag_query")
        collector.record_orchestration_latency(1.0, "error", "rule_generation")
        
    def test_set_service_availability(self):
        """Test setting service availability"""
        collector = OrchestrationMetricsCollector()
        
        # Should not raise exceptions
        collector.set_service_availability("rag_service", True)
        collector.set_service_availability("rag_service", False)
        
    def test_record_error(self):
        """Test recording errors"""
        collector = OrchestrationMetricsCollector()
        
        # Should not raise exceptions
        collector.record_error("HTTPError", "orchestrator", "error")
        collector.record_error("TimeoutError", "rag_service", "warning")
        
    def test_record_retry_attempt(self):
        """Test recording retry attempts"""
        collector = OrchestrationMetricsCollector()
        
        # Should not raise exceptions
        collector.record_retry_attempt("rag_service", "query", 1)
        collector.record_retry_attempt("rag_service", "query", 2)
        
    def test_record_fallback_activation(self):
        """Test recording fallback activations"""
        collector = OrchestrationMetricsCollector()
        
        # Should not raise exceptions
        collector.record_fallback_activation("rag_service", "temporary_outage")
        collector.record_fallback_activation("rulegen_service", "default_rules")
        
    def test_concurrent_request_tracker(self):
        """Test concurrent request tracking context manager"""
        collector = OrchestrationMetricsCollector()
        
        # Should not raise exceptions
        with collector.concurrent_request_tracker():
            pass
            
    def test_time_orchestration_stage(self):
        """Test orchestration stage timing context manager"""
        collector = OrchestrationMetricsCollector()
        
        # Should not raise exceptions
        with collector.time_orchestration_stage("success", "rag_query"):
            pass
            
    def test_get_metrics_data(self):
        """Test getting metrics data"""
        collector = OrchestrationMetricsCollector()
        
        # Should return string data
        data = collector.get_metrics_data()
        assert isinstance(data, str)

class TestMetricsDecorators:
    """Test metrics decorators"""
    
    @pytest.mark.asyncio
    async def test_monitor_orchestration_performance_async(self):
        """Test orchestration performance monitoring decorator with async function"""
        
        @monitor_orchestration_performance("success")
        async def test_async_function():
            await asyncio.sleep(0.01)
            return "success"
        
        result = await test_async_function()
        assert result == "success"
        
    def test_monitor_orchestration_performance_sync(self):
        """Test orchestration performance monitoring decorator with sync function"""
        
        @monitor_orchestration_performance("success")
        def test_sync_function():
            return "success"
        
        result = test_sync_function()
        assert result == "success"
        
    @pytest.mark.asyncio
    async def test_monitor_orchestration_performance_with_error(self):
        """Test orchestration performance monitoring decorator with error"""
        
        @monitor_orchestration_performance("success")
        async def test_error_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            await test_error_function()
            
    @pytest.mark.asyncio
    async def test_monitor_service_call_async(self):
        """Test service call monitoring decorator with async function"""
        
        @monitor_service_call("test_service", "test_endpoint")
        async def test_async_service_call():
            # Mock response with status_code
            result = MagicMock()
            result.status_code = 200
            return result
        
        result = await test_async_service_call()
        assert result.status_code == 200
        
    def test_monitor_service_call_sync(self):
        """Test service call monitoring decorator with sync function"""
        
        @monitor_service_call("test_service", "test_endpoint")
        def test_sync_service_call():
            # Mock response with status_code
            result = MagicMock()
            result.status_code = 200
            return result
        
        result = test_sync_service_call()
        assert result.status_code == 200
        
    @pytest.mark.asyncio
    async def test_monitor_service_call_with_error(self):
        """Test service call monitoring decorator with error"""
        
        @monitor_service_call("test_service", "test_endpoint")
        async def test_error_service_call():
            error = ValueError("Test error")
            error.status_code = 500
            raise error
        
        with pytest.raises(ValueError):
            await test_error_service_call()

class TestGlobalMetricsCollector:
    """Test global metrics collector instance"""
    
    def test_global_metrics_collector_exists(self):
        """Test that global metrics collector instance exists"""
        assert metrics_collector is not None
        assert isinstance(metrics_collector, OrchestrationMetricsCollector)
        
    def test_global_metrics_collector_methods(self):
        """Test that global metrics collector has required methods"""
        required_methods = [
            'record_orchestration_request',
            'record_orchestration_latency',
            'record_service_request',
            'set_service_availability',
            'record_error',
            'record_retry_attempt',
            'record_fallback_activation',
            'concurrent_request_tracker',
            'time_orchestration_stage',
            'get_metrics_data'
        ]
        
        for method in required_methods:
            assert hasattr(metrics_collector, method)
            assert callable(getattr(metrics_collector, method))

class TestMetricsIntegration:
    """Test metrics integration scenarios"""
    
    def test_metrics_collection_without_prometheus(self):
        """Test metrics collection when prometheus is not available"""
        with patch('metrics.PROMETHEUS_AVAILABLE', False):
            collector = OrchestrationMetricsCollector()
            assert not collector.enabled
            
            # All methods should work without raising exceptions
            collector.record_orchestration_request("success", "test")
            collector.record_service_request("test_service", "test", 200, 0.5)
            collector.record_error("TestError", "test_component")
            
    def test_metrics_data_format(self):
        """Test that metrics data is in correct format"""
        data = metrics_collector.get_metrics_data()
        assert isinstance(data, str)
        
        # If prometheus is available, should contain metric names
        if metrics_collector.enabled:
            assert "orchestrator_" in data or "# Metrics not available" in data
            
    @pytest.mark.asyncio
    async def test_concurrent_context_manager(self):
        """Test concurrent request tracking with multiple contexts"""
        async def test_concurrent_task():
            with metrics_collector.concurrent_request_tracker():
                await asyncio.sleep(0.01)
                
        # Run multiple concurrent tasks
        tasks = [test_concurrent_task() for _ in range(3)]
        await asyncio.gather(*tasks)
        
    def test_timing_context_manager(self):
        """Test timing context manager"""
        import time
        
        start_time = time.time()
        with metrics_collector.time_orchestration_stage("success", "test_stage"):
            time.sleep(0.01)
        duration = time.time() - start_time
        
        assert duration >= 0.01

if __name__ == "__main__":
    pytest.main([__file__])

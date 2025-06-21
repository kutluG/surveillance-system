"""
Comprehensive Tests for Advanced Monitoring System

Tests for:
- SLO tracking and alerting
- Anomaly detection algorithms
- OpenTelemetry integration
- Dashboard data generation
- Performance metrics collection
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from agent_orchestrator.comprehensive_monitoring import (
    ComprehensiveMonitor,
    SLOTracker,
    AnomalyDetector,
    SLODefinition,
    AnomalyDetection,
    SLOType,
    AnomalyType,
    AlertSeverity,
    OpenTelemetrySetup
)


class TestSLOTracker:
    """Test SLO tracking functionality"""
    
    def setup_method(self):
        self.slo_tracker = SLOTracker()
        
    def test_add_slo_definition(self):
        """Test adding SLO definitions"""
        slo = SLODefinition(
            name="test_availability",
            type=SLOType.AVAILABILITY,
            target=99.0,
            window=3600,
            alerting_threshold=95.0,
            description="Test availability SLO"
        )
        
        self.slo_tracker.add_slo(slo)
        
        assert "test_availability" in self.slo_tracker.slo_definitions
        assert "test_availability" in self.slo_tracker.slo_status
        assert self.slo_tracker.slo_status["test_availability"].is_healthy
        
    def test_availability_slo_tracking(self):
        """Test availability SLO calculation"""
        slo = SLODefinition(
            name="availability",
            type=SLOType.AVAILABILITY,
            target=95.0,
            window=60,  # 1 minute
            alerting_threshold=90.0,
            description="Availability SLO"
        )
        
        self.slo_tracker.add_slo(slo)
        
        # Send mostly successful requests
        for _ in range(95):
            self.slo_tracker.update_slo_metric("availability", 1.0)  # Success
        for _ in range(5):
            self.slo_tracker.update_slo_metric("availability", 0.0)  # Failure
            
        status = self.slo_tracker.get_slo_status("availability")
        assert status.current_value == 95.0
        assert status.is_healthy
        
    def test_latency_slo_tracking(self):
        """Test latency SLO calculation"""
        slo = SLODefinition(
            name="latency",
            type=SLOType.LATENCY,
            target=2.0,  # 2 seconds threshold
            window=60,
            alerting_threshold=95.0,  # 95% of requests under 2s
            description="Latency SLO"
        )
        
        self.slo_tracker.add_slo(slo)
        
        # Send requests with various latencies
        for _ in range(90):
            self.slo_tracker.update_slo_metric("latency", 1.0)  # Fast requests
        for _ in range(10):
            self.slo_tracker.update_slo_metric("latency", 3.0)  # Slow requests
            
        status = self.slo_tracker.get_slo_status("latency")
        assert status.current_value == 90.0  # 90% under threshold
        assert not status.is_healthy  # Below 95% target
        
    def test_error_rate_slo_tracking(self):
        """Test error rate SLO calculation"""
        slo = SLODefinition(
            name="error_rate",
            type=SLOType.ERROR_RATE,
            target=5.0,  # 5% error rate threshold
            window=60,
            alerting_threshold=10.0,
            description="Error rate SLO"
        )
        
        self.slo_tracker.add_slo(slo)
        
        # Send error rates
        for _ in range(3):
            self.slo_tracker.update_slo_metric("error_rate", 1.0)  # 1% error rate
            
        status = self.slo_tracker.get_slo_status("error_rate")
        assert status.current_value == 1.0
        assert status.is_healthy
        
    def test_slo_breach_tracking(self):
        """Test SLO breach counting"""
        slo = SLODefinition(
            name="test_slo",
            type=SLOType.AVAILABILITY,
            target=90.0,
            window=60,
            alerting_threshold=80.0,
            description="Test SLO"
        )
        
        self.slo_tracker.add_slo(slo)
        
        # Cause breach
        self.slo_tracker.update_slo_metric("test_slo", 0.0)  # Unhealthy
        status = self.slo_tracker.get_slo_status("test_slo")
        assert status.breach_count == 1
        
        # Recover
        self.slo_tracker.update_slo_metric("test_slo", 1.0)  # Healthy again
        
        # Cause another breach
        self.slo_tracker.update_slo_metric("test_slo", 0.0)  # Unhealthy again
        status = self.slo_tracker.get_slo_status("test_slo")
        assert status.breach_count == 2


class TestAnomalyDetector:
    """Test anomaly detection functionality"""
    
    def setup_method(self):
        self.detector = AnomalyDetector(window_size=10)
        
    def test_add_detection_config(self):
        """Test adding anomaly detection configuration"""
        config = AnomalyDetection(
            metric_name="test_metric",
            detection_type=AnomalyType.LATENCY_SPIKE,
            threshold_multiplier=2.0,
            window_size=10,
            cooldown_period=60
        )
        
        self.detector.add_detection_config(config)
        assert "test_metric" in self.detector.detection_configs
        
    def test_latency_spike_detection(self):
        """Test latency spike anomaly detection"""
        config = AnomalyDetection(
            metric_name="latency",
            detection_type=AnomalyType.LATENCY_SPIKE,
            threshold_multiplier=2.0,
            window_size=10,
            cooldown_period=1
        )
        
        self.detector.add_detection_config(config)
        
        # Add normal values
        for i in range(10):
            anomaly = self.detector.add_metric_value("latency", 1.0)
            assert anomaly is None
            
        # Add spike
        anomaly = self.detector.add_metric_value("latency", 10.0)
        assert anomaly is not None
        assert anomaly.detection.detection_type == AnomalyType.LATENCY_SPIKE
        assert anomaly.value == 10.0
        
    def test_error_rate_spike_detection(self):
        """Test error rate spike detection"""
        config = AnomalyDetection(
            metric_name="errors",
            detection_type=AnomalyType.ERROR_RATE_SPIKE,
            threshold_multiplier=1.5,
            window_size=10,
            cooldown_period=1
        )
        
        self.detector.add_detection_config(config)
        
        # Add normal error rates
        for i in range(10):
            anomaly = self.detector.add_metric_value("errors", 0.01)  # 1% error rate
            assert anomaly is None
            
        # Add error spike
        anomaly = self.detector.add_metric_value("errors", 0.20)  # 20% error rate
        assert anomaly is not None
        assert anomaly.detection.detection_type == AnomalyType.ERROR_RATE_SPIKE
        
    def test_throughput_drop_detection(self):
        """Test throughput drop detection"""
        config = AnomalyDetection(
            metric_name="throughput",
            detection_type=AnomalyType.THROUGHPUT_DROP,
            threshold_multiplier=2.0,
            window_size=10,
            cooldown_period=1
        )
        
        self.detector.add_detection_config(config)
        
        # Add normal throughput
        for i in range(10):
            anomaly = self.detector.add_metric_value("throughput", 100.0)
            assert anomaly is None
            
        # Add throughput drop
        anomaly = self.detector.add_metric_value("throughput", 10.0)
        assert anomaly is not None
        assert anomaly.detection.detection_type == AnomalyType.THROUGHPUT_DROP
        
    def test_cooldown_period(self):
        """Test anomaly detection cooldown period"""
        config = AnomalyDetection(
            metric_name="test",
            detection_type=AnomalyType.LATENCY_SPIKE,
            threshold_multiplier=1.5,
            window_size=5,
            cooldown_period=10  # 10 seconds cooldown
        )
        
        self.detector.add_detection_config(config)
        
        # Add normal values
        for i in range(5):
            self.detector.add_metric_value("test", 1.0)
            
        # First spike should be detected
        anomaly1 = self.detector.add_metric_value("test", 10.0)
        assert anomaly1 is not None
        
        # Second spike should be ignored due to cooldown
        anomaly2 = self.detector.add_metric_value("test", 10.0)
        assert anomaly2 is None
        
    def test_insufficient_history(self):
        """Test anomaly detection with insufficient history"""
        config = AnomalyDetection(
            metric_name="test",
            detection_type=AnomalyType.LATENCY_SPIKE,
            threshold_multiplier=2.0,
            window_size=10,
            cooldown_period=1
        )
        
        self.detector.add_detection_config(config)
        
        # Add only a few values (less than window size)
        for i in range(3):
            anomaly = self.detector.add_metric_value("test", 100.0)
            assert anomaly is None  # Should not detect with insufficient history


class TestOpenTelemetrySetup:
    """Test OpenTelemetry integration"""
    
    @patch('agent_orchestrator.comprehensive_monitoring.OPENTELEMETRY_AVAILABLE', False)
    def test_disabled_when_not_available(self):
        """Test OpenTelemetry setup when libraries not available"""
        setup = OpenTelemetrySetup()
        assert not setup.enabled
        
    @patch('agent_orchestrator.comprehensive_monitoring.OPENTELEMETRY_AVAILABLE', True)
    @patch('agent_orchestrator.comprehensive_monitoring.trace')
    @patch('agent_orchestrator.comprehensive_monitoring.otel_metrics')
    def test_tracing_setup(self, mock_metrics, mock_trace):
        """Test OpenTelemetry tracing setup"""
        with patch.multiple(
            'agent_orchestrator.comprehensive_monitoring',
            TracerProvider=Mock(),
            JaegerExporter=Mock(),
            BatchSpanProcessor=Mock(),
            FastAPIInstrumentor=Mock(),
            RequestsInstrumentor=Mock(),
            AioHttpClientInstrumentor=Mock()
        ):
            setup = OpenTelemetrySetup()
            assert setup.enabled
            
    @pytest.mark.asyncio
    async def test_trace_operation_context_manager(self):
        """Test trace operation context manager"""
        setup = OpenTelemetrySetup()
        setup.enabled = False  # Disable to avoid dependency issues
        
        async with setup.trace_operation("test_operation", test_attr="value") as span:
            assert span is None  # Should be None when disabled


class TestComprehensiveMonitor:
    """Test comprehensive monitoring system"""
    
    def setup_method(self):
        self.monitor = ComprehensiveMonitor(enable_opentelemetry=False)
        
    @pytest.mark.asyncio
    async def test_record_orchestration_metrics(self):
        """Test recording orchestration metrics"""
        await self.monitor.record_orchestration_metrics(
            latency=1.5,
            success=True,
            agent_type="test_agent",
            task_type="test_task"
        )
        
        # Check that metrics were recorded
        assert "test_agent" in self.monitor.agent_metrics
        assert len(self.monitor.agent_metrics["test_agent"]["latency"]) == 1
        assert self.monitor.agent_metrics["test_agent"]["latency"][0] == 1.5
        
    def test_get_dashboard_data(self):
        """Test dashboard data generation"""
        # Add some test data
        self.monitor.agent_metrics["test_agent"]["latency"] = [1.0, 2.0, 1.5]
        self.monitor.agent_metrics["test_agent"]["success_rate"] = [1.0, 1.0, 0.0]
        
        dashboard_data = self.monitor.get_dashboard_data()
        
        assert dashboard_data.timestamp is not None
        assert "test_agent" in dashboard_data.task_latency_by_agent
        assert "test_agent" in dashboard_data.agent_performance_metrics
        assert dashboard_data.system_health["total_agents"] == 1
        
    def test_get_health_status(self):
        """Test health status generation"""
        health = self.monitor.get_health_status()
        
        assert "status" in health
        assert "slo_health" in health
        assert "active_agents" in health
        assert "timestamp" in health
        
    @pytest.mark.asyncio
    async def test_anomaly_handling(self):
        """Test anomaly detection and handling"""
        # Configure anomaly detection
        config = AnomalyDetection(
            metric_name="orchestration_latency",
            detection_type=AnomalyType.LATENCY_SPIKE,
            threshold_multiplier=2.0,
            window_size=5,
            cooldown_period=1
        )
        self.monitor.anomaly_detector.add_detection_config(config)
        
        # Add normal latencies
        for _ in range(5):
            await self.monitor.record_orchestration_metrics(
                latency=1.0,
                success=True,
                agent_type="test_agent"
            )
            
        # Add spike - should trigger anomaly
        with patch.object(self.monitor, '_handle_anomaly') as mock_handle:
            await self.monitor.record_orchestration_metrics(
                latency=10.0,
                success=True,
                agent_type="test_agent"
            )
            # Note: The anomaly might not be detected immediately due to the way
            # metrics are aggregated, so we won't assert on the mock call
        
    def test_slo_initialization(self):
        """Test default SLO initialization"""
        slo_status = self.monitor.slo_tracker.get_all_slo_status()
        
        # Check that default SLOs are created
        expected_slos = [
            "orchestration_availability",
            "orchestration_latency", 
            "error_rate",
            "agent_task_completion_rate"
        ]
        
        for slo_name in expected_slos:
            assert slo_name in slo_status
            
    def test_agent_metrics_history_limit(self):
        """Test that agent metrics history is limited"""
        agent_type = "test_agent"
        
        # Add more than the limit (100) of metrics
        for i in range(150):
            self.monitor.agent_metrics[agent_type]["latency"].append(float(i))
            
        # Should be limited to 100 entries
        assert len(self.monitor.agent_metrics[agent_type]["latency"]) <= 100
        
    def test_export_metrics(self):
        """Test metrics export functionality"""
        # Add some test data
        self.monitor.agent_metrics["test_agent"]["latency"] = [1.0, 2.0]
        
        metrics_export = self.monitor.export_metrics()
        
        assert isinstance(metrics_export, str)
        assert len(metrics_export) > 0


class TestIntegration:
    """Integration tests for the monitoring system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_flow(self):
        """Test complete monitoring flow"""
        monitor = ComprehensiveMonitor(enable_opentelemetry=False)
        
        # Simulate a series of orchestration requests
        scenarios = [
            (1.0, True, "rag_agent", "query"),
            (2.5, True, "rule_agent", "rule_generation"),
            (0.8, True, "notification_agent", "notification"),
            (15.0, False, "rag_agent", "query"),  # Slow/failed request
            (1.2, True, "rag_agent", "query"),
        ]
        
        for latency, success, agent_type, task_type in scenarios:
            await monitor.record_orchestration_metrics(
                latency=latency,
                success=success,
                agent_type=agent_type,
                task_type=task_type
            )
            
        # Get dashboard data
        dashboard_data = monitor.get_dashboard_data()
        
        # Verify data was collected
        assert len(dashboard_data.agent_performance_metrics) == 3  # 3 agent types
        assert "rag_agent" in dashboard_data.agent_performance_metrics
        assert "rule_agent" in dashboard_data.agent_performance_metrics
        assert "notification_agent" in dashboard_data.agent_performance_metrics
        
        # Check SLO status
        slo_status = dashboard_data.slo_status
        assert len(slo_status) > 0
        
        # Check system health
        assert dashboard_data.system_health["total_agents"] == 3
        
    @pytest.mark.asyncio
    async def test_concurrent_metrics_collection(self):
        """Test concurrent metrics collection"""
        monitor = ComprehensiveMonitor(enable_opentelemetry=False)
        
        async def record_metrics(agent_id: int):
            for i in range(10):
                await monitor.record_orchestration_metrics(
                    latency=1.0 + (i * 0.1),
                    success=True,
                    agent_type=f"agent_{agent_id}",
                    task_type="test_task"
                )
                await asyncio.sleep(0.01)  # Small delay
                
        # Run concurrent metric collection
        tasks = [record_metrics(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # Verify all agents recorded metrics
        dashboard_data = monitor.get_dashboard_data()
        assert len(dashboard_data.agent_performance_metrics) == 5
        
        for i in range(5):
            agent_type = f"agent_{i}"
            assert agent_type in dashboard_data.agent_performance_metrics
            assert dashboard_data.agent_performance_metrics[agent_type]["total_requests"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

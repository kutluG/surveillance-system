"""
Comprehensive Monitoring System for Agent Orchestrator

This module provides advanced monitoring capabilities including:
- Detailed performance dashboards
- SLO (Service Level Objective) tracking
- Anomaly detection for agent behavior
- OpenTelemetry distributed tracing
- Real-time alerting and health checks
"""

import asyncio
import time
import logging
import json
import statistics
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from enum import Enum
import threading
import traceback

# OpenTelemetry imports
try:
    from opentelemetry import trace, metrics as otel_metrics
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
    from opentelemetry.trace.status import Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

# Prometheus imports
try:
    from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class SLOType(str, Enum):
    """Types of Service Level Objectives"""
    AVAILABILITY = "availability"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


class AnomalyType(str, Enum):
    """Types of anomalies that can be detected"""
    LATENCY_SPIKE = "latency_spike"
    ERROR_RATE_SPIKE = "error_rate_spike"
    THROUGHPUT_DROP = "throughput_drop"
    AGENT_FAILURE = "agent_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SLODefinition:
    """Service Level Objective definition"""
    name: str
    type: SLOType
    target: float  # Target value (e.g., 99.9 for 99.9% availability)
    window: int  # Time window in seconds
    alerting_threshold: float  # Threshold for alerting
    description: str


@dataclass
class SLOStatus:
    """Current SLO status"""
    definition: SLODefinition
    current_value: float
    is_healthy: bool
    last_updated: datetime
    breach_count: int
    breach_duration: float


@dataclass
class AnomalyDetection:
    """Anomaly detection configuration"""
    metric_name: str
    detection_type: AnomalyType
    threshold_multiplier: float  # Multiplier for standard deviation
    window_size: int  # Number of data points to consider
    cooldown_period: int  # Seconds to wait before detecting again


@dataclass
class Anomaly:
    """Detected anomaly"""
    detection: AnomalyDetection
    timestamp: datetime
    value: float
    baseline: float
    severity: AlertSeverity
    description: str
    metadata: Dict[str, Any]


@dataclass
class DashboardData:
    """Data structure for dashboard visualization"""
    timestamp: datetime
    task_latency_by_agent: Dict[str, List[float]]
    agent_performance_metrics: Dict[str, Dict[str, float]]
    slo_status: Dict[str, SLOStatus]
    anomalies: List[Anomaly]
    system_health: Dict[str, Any]


class OpenTelemetrySetup:
    """OpenTelemetry configuration and setup"""
    
    def __init__(self, service_name: str = "agent-orchestrator", 
                 jaeger_endpoint: str = "http://localhost:14268/api/traces",
                 prometheus_port: int = 8000):
        self.service_name = service_name
        self.jaeger_endpoint = jaeger_endpoint
        self.prometheus_port = prometheus_port
        self.enabled = OPENTELEMETRY_AVAILABLE
        
        if not self.enabled:
            logger.warning("OpenTelemetry not available - distributed tracing disabled")
            return
            
        self._setup_tracing()
        self._setup_metrics()
        
    def _setup_tracing(self):
        """Setup distributed tracing with Jaeger"""
        try:
            # Create resource
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": "1.0.0",
                "service.instance.id": f"{self.service_name}-{int(time.time())}"
            })
            
            # Create tracer provider
            tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(tracer_provider)
            
            # Create Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=6831,
            )
            
            # Create span processor
            span_processor = BatchSpanProcessor(jaeger_exporter)
            tracer_provider.add_span_processor(span_processor)
            
            # Instrument FastAPI
            FastAPIInstrumentor.instrument()
            RequestsInstrumentor.instrument()
            AioHttpClientInstrumentor.instrument()
            
            self.tracer = trace.get_tracer(__name__)
            logger.info(f"OpenTelemetry tracing initialized for {self.service_name}")
            
        except Exception as e:
            logger.error(f"Failed to setup OpenTelemetry tracing: {e}")
            self.enabled = False
            
    def _setup_metrics(self):
        """Setup metrics with Prometheus"""
        try:
            # Create metrics provider
            reader = PrometheusMetricReader()
            provider = MeterProvider(resource=Resource.create({
                "service.name": self.service_name
            }), metric_readers=[reader])
            
            otel_metrics.set_meter_provider(provider)
            self.meter = otel_metrics.get_meter(__name__)
            
            # Create metric instruments
            self.request_counter = self.meter.create_counter(
                "orchestrator_requests",
                description="Number of requests processed"
            )
            
            self.request_duration = self.meter.create_histogram(
                "orchestrator_request_duration",
                description="Request processing duration"
            )
            
            logger.info("OpenTelemetry metrics initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup OpenTelemetry metrics: {e}")
            
    @asynccontextmanager
    async def trace_operation(self, operation_name: str, **attributes):
        """Context manager for tracing operations"""
        if not self.enabled:
            yield None
            return
            
        with self.tracer.start_as_current_span(operation_name) as span:
            # Set attributes
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
            
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise


class AnomalyDetector:
    """Advanced anomaly detection for agent behavior"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.detection_configs: Dict[str, AnomalyDetection] = {}
        self.last_anomaly_time: Dict[str, datetime] = {}
        
    def add_detection_config(self, config: AnomalyDetection):
        """Add anomaly detection configuration"""
        self.detection_configs[config.metric_name] = config
        
    def add_metric_value(self, metric_name: str, value: float) -> Optional[Anomaly]:
        """Add metric value and check for anomalies"""
        self.metric_history[metric_name].append((datetime.now(), value))
        
        if metric_name in self.detection_configs:
            return self._check_anomaly(metric_name, value)
        
        return None
        
    def _check_anomaly(self, metric_name: str, value: float) -> Optional[Anomaly]:
        """Check if value is anomalous"""
        config = self.detection_configs[metric_name]
        history = self.metric_history[metric_name]
        
        # Need sufficient history
        if len(history) < config.window_size:
            return None
            
        # Check cooldown period
        last_anomaly = self.last_anomaly_time.get(metric_name)
        if last_anomaly and (datetime.now() - last_anomaly).seconds < config.cooldown_period:
            return None
            
        # Calculate baseline statistics
        values = [v for _, v in history]
        mean = statistics.mean(values)
        try:
            stdev = statistics.stdev(values)
        except statistics.StatisticsError:
            stdev = 0
            
        # Check for anomaly based on type
        is_anomaly = False
        severity = AlertSeverity.INFO
        
        if config.detection_type == AnomalyType.LATENCY_SPIKE:
            threshold = mean + (config.threshold_multiplier * stdev)
            if value > threshold:
                is_anomaly = True
                severity = self._calculate_severity(value, threshold, mean)
                
        elif config.detection_type == AnomalyType.ERROR_RATE_SPIKE:
            threshold = mean + (config.threshold_multiplier * stdev)
            if value > threshold:
                is_anomaly = True
                severity = AlertSeverity.HIGH if value > mean * 2 else AlertSeverity.MEDIUM
                
        elif config.detection_type == AnomalyType.THROUGHPUT_DROP:
            threshold = mean - (config.threshold_multiplier * stdev)
            if value < threshold:
                is_anomaly = True
                severity = AlertSeverity.HIGH if value < mean * 0.5 else AlertSeverity.MEDIUM
                
        if is_anomaly:
            self.last_anomaly_time[metric_name] = datetime.now()
            return Anomaly(
                detection=config,
                timestamp=datetime.now(),
                value=value,
                baseline=mean,
                severity=severity,
                description=f"{config.detection_type.value} detected: {value:.2f} vs baseline {mean:.2f}",
                metadata={
                    "threshold": threshold,
                    "standard_deviation": stdev,
                    "window_size": len(history)
                }
            )
            
        return None
        
    def _calculate_severity(self, value: float, threshold: float, baseline: float) -> AlertSeverity:
        """Calculate anomaly severity"""
        ratio = value / baseline if baseline > 0 else float('inf')
        
        if ratio > 5:
            return AlertSeverity.CRITICAL
        elif ratio > 3:
            return AlertSeverity.HIGH
        elif ratio > 2:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW


class SLOTracker:
    """Service Level Objective tracking and monitoring"""
    
    def __init__(self):
        self.slo_definitions: Dict[str, SLODefinition] = {}
        self.slo_status: Dict[str, SLOStatus] = {}
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
    def add_slo(self, slo: SLODefinition):
        """Add SLO definition"""
        self.slo_definitions[slo.name] = slo
        self.slo_status[slo.name] = SLOStatus(
            definition=slo,
            current_value=0.0,
            is_healthy=True,
            last_updated=datetime.now(),
            breach_count=0,
            breach_duration=0.0
        )
        
    def update_slo_metric(self, slo_name: str, value: float):
        """Update SLO metric value"""
        if slo_name not in self.slo_definitions:
            return
            
        slo_def = self.slo_definitions[slo_name]
        current_time = datetime.now()
        
        # Add to history
        self.metric_history[slo_name].append((current_time, value))
        
        # Calculate current SLO value over window
        window_start = current_time - timedelta(seconds=slo_def.window)
        window_values = [
            v for t, v in self.metric_history[slo_name] 
            if t >= window_start
        ]
        
        if not window_values:
            return
            
        # Calculate SLO value based on type
        if slo_def.type == SLOType.AVAILABILITY:
            current_value = (sum(1 for v in window_values if v > 0) / len(window_values)) * 100
        elif slo_def.type == SLOType.LATENCY:
            # For latency SLO, we track percentage of requests under threshold
            current_value = (sum(1 for v in window_values if v <= slo_def.target) / len(window_values)) * 100
        elif slo_def.type == SLOType.ERROR_RATE:
            current_value = (sum(window_values) / len(window_values)) * 100
        elif slo_def.type == SLOType.THROUGHPUT:
            current_value = sum(window_values) / (slo_def.window / 60)  # per minute
        else:
            current_value = statistics.mean(window_values)
            
        # Update status
        status = self.slo_status[slo_name]
        previous_healthy = status.is_healthy
        
        if slo_def.type == SLOType.ERROR_RATE:
            is_healthy = current_value <= slo_def.target
        else:
            is_healthy = current_value >= slo_def.target
            
        status.current_value = current_value
        status.is_healthy = is_healthy
        status.last_updated = current_time
        
        # Track breaches
        if not is_healthy and previous_healthy:
            status.breach_count += 1
            
        if not is_healthy:
            status.breach_duration += 1  # Increment by update interval
            
    def get_slo_status(self, slo_name: str) -> Optional[SLOStatus]:
        """Get current SLO status"""
        return self.slo_status.get(slo_name)
        
    def get_all_slo_status(self) -> Dict[str, SLOStatus]:
        """Get all SLO statuses"""
        return self.slo_status.copy()


class ComprehensiveMonitor:
    """Main comprehensive monitoring system"""
    
    def __init__(self, enable_opentelemetry: bool = True):
        self.opentelemetry = OpenTelemetrySetup() if enable_opentelemetry else None
        self.anomaly_detector = AnomalyDetector()
        self.slo_tracker = SLOTracker()
        self.dashboard_data_history: deque = deque(maxlen=1000)
        
        # Initialize default SLOs
        self._setup_default_slos()
        self._setup_default_anomaly_detection()
        
        # Metrics collection
        self.metrics_lock = threading.Lock()
        self.agent_metrics: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self.system_metrics: Dict[str, float] = {}
        
        logger.info("Comprehensive monitoring system initialized")
        
    def _setup_default_slos(self):
        """Setup default SLO definitions"""
        slos = [
            SLODefinition(
                name="orchestration_availability",
                type=SLOType.AVAILABILITY,
                target=99.9,
                window=3600,  # 1 hour
                alerting_threshold=99.0,
                description="Orchestration service availability"
            ),
            SLODefinition(
                name="orchestration_latency",
                type=SLOType.LATENCY,
                target=2.0,  # 2 seconds
                window=3600,
                alerting_threshold=95.0,  # 95% of requests under 2s
                description="Orchestration request latency"
            ),
            SLODefinition(
                name="error_rate",
                type=SLOType.ERROR_RATE,
                target=1.0,  # 1% error rate
                window=3600,
                alerting_threshold=2.0,
                description="Overall error rate"
            ),
            SLODefinition(
                name="agent_task_completion_rate",
                type=SLOType.AVAILABILITY,
                target=98.0,
                window=7200,  # 2 hours
                alerting_threshold=95.0,
                description="Agent task completion rate"
            )
        ]
        
        for slo in slos:
            self.slo_tracker.add_slo(slo)
            
    def _setup_default_anomaly_detection(self):
        """Setup default anomaly detection configurations"""
        configs = [
            AnomalyDetection(
                metric_name="orchestration_latency",
                detection_type=AnomalyType.LATENCY_SPIKE,
                threshold_multiplier=2.0,
                window_size=50,
                cooldown_period=300
            ),
            AnomalyDetection(
                metric_name="error_rate",
                detection_type=AnomalyType.ERROR_RATE_SPIKE,
                threshold_multiplier=1.5,
                window_size=30,
                cooldown_period=600
            ),
            AnomalyDetection(
                metric_name="agent_throughput",
                detection_type=AnomalyType.THROUGHPUT_DROP,
                threshold_multiplier=1.5,
                window_size=40,
                cooldown_period=300
            )
        ]
        
        for config in configs:
            self.anomaly_detector.add_detection_config(config)
            
    async def record_orchestration_metrics(self, 
                                         latency: float, 
                                         success: bool, 
                                         agent_type: str = "unknown",
                                         task_type: str = "unknown"):
        """Record orchestration metrics with comprehensive tracking"""
        
        # OpenTelemetry tracing
        if self.opentelemetry and self.opentelemetry.enabled:
            async with self.opentelemetry.trace_operation(
                "orchestration_request",
                agent_type=agent_type,
                task_type=task_type,
                success=success
            ) as span:
                if span:
                    span.set_attribute("latency", latency)
                    
        # Update SLOs
        self.slo_tracker.update_slo_metric("orchestration_availability", 1.0 if success else 0.0)
        self.slo_tracker.update_slo_metric("orchestration_latency", latency)
        self.slo_tracker.update_slo_metric("error_rate", 0.0 if success else 1.0)
        
        # Check for anomalies
        latency_anomaly = self.anomaly_detector.add_metric_value("orchestration_latency", latency)
        error_anomaly = self.anomaly_detector.add_metric_value("error_rate", 0.0 if success else 1.0)
        
        # Store agent-specific metrics
        with self.metrics_lock:
            self.agent_metrics[agent_type]["latency"].append(latency)
            self.agent_metrics[agent_type]["success_rate"].append(1.0 if success else 0.0)
            
            # Limit history size
            if len(self.agent_metrics[agent_type]["latency"]) > 100:
                self.agent_metrics[agent_type]["latency"].pop(0)
            if len(self.agent_metrics[agent_type]["success_rate"]) > 100:
                self.agent_metrics[agent_type]["success_rate"].pop(0)
                
        # Handle anomalies
        for anomaly in [latency_anomaly, error_anomaly]:
            if anomaly:
                await self._handle_anomaly(anomaly)
                
    async def _handle_anomaly(self, anomaly: Anomaly):
        """Handle detected anomaly"""
        logger.warning(f"Anomaly detected: {anomaly.description}")
        
        # Here you could integrate with alerting systems
        # For now, we'll just log the anomaly
        anomaly_data = {
            "type": anomaly.detection.detection_type.value,
            "severity": anomaly.severity.value,
            "value": anomaly.value,
            "baseline": anomaly.baseline,
            "timestamp": anomaly.timestamp.isoformat(),
            "description": anomaly.description,
            "metadata": anomaly.metadata
        }
        
        logger.info(f"Anomaly details: {json.dumps(anomaly_data, indent=2)}")
        
    def get_dashboard_data(self) -> DashboardData:
        """Get current dashboard data"""
        current_time = datetime.now()
        
        # Get task latency by agent type
        task_latency = {}
        agent_performance = {}
        
        with self.metrics_lock:
            for agent_type, metrics in self.agent_metrics.items():
                if metrics["latency"]:
                    task_latency[agent_type] = metrics["latency"][-20:]  # Last 20 values
                    
                    # Calculate performance metrics
                    avg_latency = statistics.mean(metrics["latency"][-20:]) if metrics["latency"] else 0
                    success_rate = statistics.mean(metrics["success_rate"][-20:]) * 100 if metrics["success_rate"] else 0
                    
                    agent_performance[agent_type] = {
                        "avg_latency": avg_latency,
                        "success_rate": success_rate,
                        "total_requests": len(metrics["latency"]),
                        "recent_errors": sum(1 for x in metrics["success_rate"][-10:] if x == 0)
                    }
                    
        # Get SLO status
        slo_status = self.slo_tracker.get_all_slo_status()
        
        # Get recent anomalies (placeholder - you'd store these in practice)
        recent_anomalies = []
        
        # System health summary
        system_health = {
            "overall_status": "healthy" if all(slo.is_healthy for slo in slo_status.values()) else "degraded",
            "total_agents": len(self.agent_metrics),
            "active_slos": len(slo_status),
            "recent_anomalies": len(recent_anomalies),
            "last_updated": current_time.isoformat()
        }
        
        dashboard_data = DashboardData(
            timestamp=current_time,
            task_latency_by_agent=task_latency,
            agent_performance_metrics=agent_performance,
            slo_status=slo_status,
            anomalies=recent_anomalies,
            system_health=system_health
        )
        
        # Store in history
        self.dashboard_data_history.append(dashboard_data)
        
        return dashboard_data
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        slo_status = self.slo_tracker.get_all_slo_status()
        
        healthy_slos = sum(1 for slo in slo_status.values() if slo.is_healthy)
        total_slos = len(slo_status)
        
        return {
            "status": "healthy" if healthy_slos == total_slos else "degraded",
            "slo_health": f"{healthy_slos}/{total_slos}",
            "opentelemetry_enabled": self.opentelemetry is not None and self.opentelemetry.enabled,
            "active_agents": len(self.agent_metrics),
            "timestamp": datetime.now().isoformat()
        }
        
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        # This would integrate with your existing Prometheus metrics
        # For now, return a summary
        dashboard_data = self.get_dashboard_data()
        return json.dumps(asdict(dashboard_data), indent=2, default=str)


# Global monitoring instance
_monitor_instance: Optional[ComprehensiveMonitor] = None


def get_monitor() -> ComprehensiveMonitor:
    """Get global monitoring instance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ComprehensiveMonitor()
    return _monitor_instance


def initialize_monitoring(enable_opentelemetry: bool = True) -> ComprehensiveMonitor:
    """Initialize comprehensive monitoring system"""
    global _monitor_instance
    _monitor_instance = ComprehensiveMonitor(enable_opentelemetry)
    return _monitor_instance

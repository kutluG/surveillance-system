"""
Configuration for Comprehensive Monitoring System

This file defines configuration settings for:
- OpenTelemetry setup
- SLO definitions  
- Anomaly detection parameters
- Dashboard settings
- Alert thresholds
"""

from pydantic import BaseSettings, Field
from typing import Dict, List, Optional, Any
from enum import Enum

from .comprehensive_monitoring import SLOType, AnomalyType, AlertSeverity


class MonitoringConfig(BaseSettings):
    """Comprehensive monitoring configuration"""
    
    # OpenTelemetry Configuration
    opentelemetry_enabled: bool = Field(default=True, description="Enable OpenTelemetry tracing")
    jaeger_endpoint: str = Field(default="http://localhost:14268/api/traces", description="Jaeger endpoint URL")
    jaeger_agent_host: str = Field(default="localhost", description="Jaeger agent host")
    jaeger_agent_port: int = Field(default=6831, description="Jaeger agent port")
    service_name: str = Field(default="agent-orchestrator", description="Service name for tracing")
    service_version: str = Field(default="1.0.0", description="Service version")
    
    # Prometheus Configuration
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    prometheus_port: int = Field(default=8000, description="Prometheus metrics port")
    prometheus_path: str = Field(default="/metrics", description="Prometheus metrics path")
    
    # Dashboard Configuration
    dashboard_enabled: bool = Field(default=True, description="Enable monitoring dashboard")
    dashboard_refresh_interval: int = Field(default=5, description="Dashboard refresh interval in seconds")
    dashboard_history_size: int = Field(default=1000, description="Number of data points to keep in history")
    
    # SLO Configuration
    slo_enabled: bool = Field(default=True, description="Enable SLO tracking")
    slo_evaluation_interval: int = Field(default=60, description="SLO evaluation interval in seconds")
    
    # Default SLO Definitions
    default_slos: Dict[str, Dict[str, Any]] = Field(default={
        "orchestration_availability": {
            "type": "availability",
            "target": 99.9,
            "window": 3600,  # 1 hour
            "alerting_threshold": 99.0,
            "description": "Orchestration service availability"
        },
        "orchestration_latency": {
            "type": "latency", 
            "target": 2.0,  # 2 seconds
            "window": 3600,
            "alerting_threshold": 95.0,  # 95% of requests under 2s
            "description": "Orchestration request latency"
        },
        "error_rate": {
            "type": "error_rate",
            "target": 1.0,  # 1% error rate
            "window": 3600,
            "alerting_threshold": 2.0,
            "description": "Overall error rate"
        },
        "agent_task_completion_rate": {
            "type": "availability",
            "target": 98.0,
            "window": 7200,  # 2 hours
            "alerting_threshold": 95.0,
            "description": "Agent task completion rate"
        }
    })
    
    # Anomaly Detection Configuration
    anomaly_detection_enabled: bool = Field(default=True, description="Enable anomaly detection")
    anomaly_detection_window_size: int = Field(default=100, description="Anomaly detection window size")
    
    # Default Anomaly Detection Rules
    default_anomaly_detections: Dict[str, Dict[str, Any]] = Field(default={
        "orchestration_latency": {
            "detection_type": "latency_spike",
            "threshold_multiplier": 2.0,
            "window_size": 50,
            "cooldown_period": 300
        },
        "error_rate": {
            "detection_type": "error_rate_spike", 
            "threshold_multiplier": 1.5,
            "window_size": 30,
            "cooldown_period": 600
        },
        "agent_throughput": {
            "detection_type": "throughput_drop",
            "threshold_multiplier": 1.5,
            "window_size": 40,
            "cooldown_period": 300
        }
    })
    
    # Alerting Configuration
    alerting_enabled: bool = Field(default=True, description="Enable alerting")
    alert_channels: List[str] = Field(default=["log", "webhook"], description="Alert channels")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for alerts")
    alert_severity_threshold: str = Field(default="medium", description="Minimum severity for alerts")
    
    # Alert Escalation Rules
    alert_escalation_rules: Dict[str, Dict[str, Any]] = Field(default={
        "critical": {
            "immediate_notification": True,
            "escalation_delay": 300,  # 5 minutes
            "max_escalations": 3
        },
        "high": {
            "immediate_notification": True,
            "escalation_delay": 600,  # 10 minutes
            "max_escalations": 2
        },
        "medium": {
            "immediate_notification": False,
            "escalation_delay": 1800,  # 30 minutes
            "max_escalations": 1
        }
    })
    
    # Performance Monitoring Configuration
    performance_monitoring_enabled: bool = Field(default=True, description="Enable performance monitoring")
    agent_metrics_history_size: int = Field(default=100, description="Number of metrics to keep per agent")
    performance_baseline_window: int = Field(default=3600, description="Performance baseline window in seconds")
    
    # Health Check Configuration
    health_check_enabled: bool = Field(default=True, description="Enable health checks")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=10, description="Health check timeout in seconds")
    
    # Export Configuration
    export_enabled: bool = Field(default=True, description="Enable metrics export")
    export_formats: List[str] = Field(default=["prometheus", "json"], description="Export formats")
    export_interval: int = Field(default=60, description="Export interval in seconds")
    
    # Logging Configuration
    monitoring_log_level: str = Field(default="INFO", description="Monitoring log level")
    monitoring_log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Monitoring log format"
    )
    
    # Feature Flags
    features: Dict[str, bool] = Field(default={
        "distributed_tracing": True,
        "custom_metrics": True,
        "real_time_alerts": True,
        "performance_profiling": True,
        "capacity_planning": True,
        "automated_scaling": False,  # Future feature
        "predictive_analytics": False  # Future feature
    })
    
    class Config:
        env_prefix = "MONITORING_"
        case_sensitive = False


# Environment-specific configurations
class DevelopmentMonitoringConfig(MonitoringConfig):
    """Development environment monitoring configuration"""
    opentelemetry_enabled: bool = False  # Disable for local development
    prometheus_port: int = 8001
    slo_evaluation_interval: int = 30  # More frequent for testing
    anomaly_detection_window_size: int = 20  # Smaller window for testing
    monitoring_log_level: str = "DEBUG"


class ProductionMonitoringConfig(MonitoringConfig):
    """Production environment monitoring configuration"""
    opentelemetry_enabled: bool = True
    prometheus_port: int = 8000
    slo_evaluation_interval: int = 60
    anomaly_detection_window_size: int = 100
    monitoring_log_level: str = "WARNING"
    
    # More stringent SLOs for production
    default_slos: Dict[str, Dict[str, Any]] = {
        "orchestration_availability": {
            "type": "availability",
            "target": 99.95,  # Higher availability target
            "window": 3600,
            "alerting_threshold": 99.5,
            "description": "Production orchestration service availability"
        },
        "orchestration_latency": {
            "type": "latency",
            "target": 1.0,  # Lower latency target
            "window": 3600,
            "alerting_threshold": 98.0,  # Higher percentage target
            "description": "Production orchestration request latency"
        },
        "error_rate": {
            "type": "error_rate",
            "target": 0.5,  # Lower error rate target
            "window": 3600,
            "alerting_threshold": 1.0,
            "description": "Production error rate"
        }
    }


class TestingMonitoringConfig(MonitoringConfig):
    """Testing environment monitoring configuration"""
    opentelemetry_enabled: bool = False
    prometheus_enabled: bool = False
    alerting_enabled: bool = False
    slo_enabled: bool = False
    monitoring_log_level: str = "ERROR"


# Configuration factory
def get_monitoring_config(environment: str = "development") -> MonitoringConfig:
    """Get monitoring configuration for specific environment"""
    
    configs = {
        "development": DevelopmentMonitoringConfig,
        "testing": TestingMonitoringConfig,
        "production": ProductionMonitoringConfig
    }
    
    config_class = configs.get(environment, MonitoringConfig)
    return config_class()


# Default configuration instance
monitoring_config = get_monitoring_config()


# Configuration validation helpers
def validate_slo_config(slo_config: Dict[str, Any]) -> bool:
    """Validate SLO configuration"""
    required_fields = ["type", "target", "window", "alerting_threshold", "description"]
    
    for field in required_fields:
        if field not in slo_config:
            return False
    
    # Validate SLO type
    if slo_config["type"] not in [slo_type.value for slo_type in SLOType]:
        return False
    
    # Validate numeric values
    if not isinstance(slo_config["target"], (int, float)):
        return False
    if not isinstance(slo_config["window"], int) or slo_config["window"] <= 0:
        return False
    if not isinstance(slo_config["alerting_threshold"], (int, float)):
        return False
    
    return True


def validate_anomaly_config(anomaly_config: Dict[str, Any]) -> bool:
    """Validate anomaly detection configuration"""
    required_fields = ["detection_type", "threshold_multiplier", "window_size", "cooldown_period"]
    
    for field in required_fields:
        if field not in anomaly_config:
            return False
    
    # Validate detection type
    if anomaly_config["detection_type"] not in [anom_type.value for anom_type in AnomalyType]:
        return False
    
    # Validate numeric values
    if not isinstance(anomaly_config["threshold_multiplier"], (int, float)) or anomaly_config["threshold_multiplier"] <= 0:
        return False
    if not isinstance(anomaly_config["window_size"], int) or anomaly_config["window_size"] <= 0:
        return False
    if not isinstance(anomaly_config["cooldown_period"], int) or anomaly_config["cooldown_period"] < 0:
        return False
    
    return True


# Example usage and testing
if __name__ == "__main__":
    import json
    
    # Test different environment configurations
    for env in ["development", "testing", "production"]:
        print(f"\n{env.upper()} Configuration:")
        print("=" * 50)
        
        config = get_monitoring_config(env)
        
        # Show key configuration values
        print(f"OpenTelemetry Enabled: {config.opentelemetry_enabled}")
        print(f"Prometheus Port: {config.prometheus_port}")
        print(f"SLO Evaluation Interval: {config.slo_evaluation_interval}s")
        print(f"Log Level: {config.monitoring_log_level}")
        print(f"Default SLOs: {len(config.default_slos)}")
        print(f"Anomaly Detections: {len(config.default_anomaly_detections)}")
        
        # Validate configurations
        valid_slos = all(validate_slo_config(slo) for slo in config.default_slos.values())
        valid_anomalies = all(validate_anomaly_config(anom) for anom in config.default_anomaly_detections.values())
        
        print(f"SLO Config Valid: {valid_slos}")
        print(f"Anomaly Config Valid: {valid_anomalies}")
    
    print("\n✅ Configuration validation completed")

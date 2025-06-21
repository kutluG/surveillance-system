"""
Monitoring Dashboard API for Agent Orchestrator

Provides REST endpoints for accessing comprehensive monitoring data including:
- Real-time dashboards
- SLO status and tracking
- Anomaly detection results
- System health metrics
- Performance analytics
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import asyncio

from .comprehensive_monitoring import (
    get_monitor, 
    ComprehensiveMonitor,
    SLOStatus,
    DashboardData,
    Anomaly,
    AlertSeverity,
    SLOType
)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
async def get_health_status():
    """Get overall system health status"""
    monitor = get_monitor()
    return monitor.get_health_status()


@router.get("/dashboard")
async def get_dashboard_data():
    """Get comprehensive dashboard data"""
    monitor = get_monitor()
    dashboard_data = monitor.get_dashboard_data()
    
    # Convert to JSON-serializable format
    return {
        "timestamp": dashboard_data.timestamp.isoformat(),
        "task_latency_by_agent": dashboard_data.task_latency_by_agent,
        "agent_performance_metrics": dashboard_data.agent_performance_metrics,
        "slo_status": {
            name: {
                "name": status.definition.name,
                "type": status.definition.type.value,
                "target": status.definition.target,
                "current_value": status.current_value,
                "is_healthy": status.is_healthy,
                "last_updated": status.last_updated.isoformat(),
                "breach_count": status.breach_count,
                "breach_duration": status.breach_duration,
                "description": status.definition.description
            }
            for name, status in dashboard_data.slo_status.items()
        },
        "anomalies": [
            {
                "type": anomaly.detection.detection_type.value,
                "timestamp": anomaly.timestamp.isoformat(),
                "value": anomaly.value,
                "baseline": anomaly.baseline,
                "severity": anomaly.severity.value,
                "description": anomaly.description,
                "metadata": anomaly.metadata
            }
            for anomaly in dashboard_data.anomalies
        ],
        "system_health": dashboard_data.system_health
    }


@router.get("/slo")
async def get_slo_status():
    """Get all SLO statuses"""
    monitor = get_monitor()
    slo_status = monitor.slo_tracker.get_all_slo_status()
    
    return {
        name: {
            "name": status.definition.name,
            "type": status.definition.type.value,
            "target": status.definition.target,
            "current_value": status.current_value,
            "is_healthy": status.is_healthy,
            "last_updated": status.last_updated.isoformat(),
            "breach_count": status.breach_count,
            "breach_duration": status.breach_duration,
            "window": status.definition.window,
            "alerting_threshold": status.definition.alerting_threshold,
            "description": status.definition.description
        }
        for name, status in slo_status.items()
    }


@router.get("/slo/{slo_name}")
async def get_specific_slo_status(slo_name: str):
    """Get specific SLO status"""
    monitor = get_monitor()
    slo_status = monitor.slo_tracker.get_slo_status(slo_name)
    
    if not slo_status:
        raise HTTPException(status_code=404, detail=f"SLO '{slo_name}' not found")
    
    return {
        "name": slo_status.definition.name,
        "type": slo_status.definition.type.value,
        "target": slo_status.definition.target,
        "current_value": slo_status.current_value,
        "is_healthy": slo_status.is_healthy,
        "last_updated": slo_status.last_updated.isoformat(),
        "breach_count": slo_status.breach_count,
        "breach_duration": slo_status.breach_duration,
        "window": slo_status.definition.window,
        "alerting_threshold": slo_status.definition.alerting_threshold,
        "description": slo_status.definition.description
    }


@router.get("/metrics/agents")
async def get_agent_metrics():
    """Get performance metrics by agent type"""
    monitor = get_monitor()
    dashboard_data = monitor.get_dashboard_data()
    
    return {
        "agent_performance": dashboard_data.agent_performance_metrics,
        "task_latency": dashboard_data.task_latency_by_agent,
        "timestamp": dashboard_data.timestamp.isoformat()
    }


@router.get("/metrics/agents/{agent_type}")
async def get_agent_specific_metrics(agent_type: str):
    """Get metrics for a specific agent type"""
    monitor = get_monitor()
    dashboard_data = monitor.get_dashboard_data()
    
    if agent_type not in dashboard_data.agent_performance_metrics:
        raise HTTPException(status_code=404, detail=f"Agent type '{agent_type}' not found")
    
    return {
        "agent_type": agent_type,
        "performance_metrics": dashboard_data.agent_performance_metrics[agent_type],
        "recent_latency": dashboard_data.task_latency_by_agent.get(agent_type, []),
        "timestamp": dashboard_data.timestamp.isoformat()
    }


@router.get("/anomalies")
async def get_anomalies(
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    limit: int = Query(50, description="Maximum number of anomalies to return")
):
    """Get detected anomalies"""
    monitor = get_monitor()
    dashboard_data = monitor.get_dashboard_data()
    
    anomalies = dashboard_data.anomalies
    
    # Filter by severity if specified
    if severity:
        try:
            severity_enum = AlertSeverity(severity.lower())
            anomalies = [a for a in anomalies if a.severity == severity_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity level: {severity}")
    
    # Limit results
    anomalies = anomalies[:limit]
    
    return {
        "anomalies": [
            {
                "type": anomaly.detection.detection_type.value,
                "timestamp": anomaly.timestamp.isoformat(),
                "value": anomaly.value,
                "baseline": anomaly.baseline,
                "severity": anomaly.severity.value,
                "description": anomaly.description,
                "metadata": anomaly.metadata
            }
            for anomaly in anomalies
        ],
        "total_count": len(anomalies),
        "timestamp": dashboard_data.timestamp.isoformat()
    }


@router.get("/trends/latency")
async def get_latency_trends(
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    hours: int = Query(24, description="Number of hours to analyze")
):
    """Get latency trends over time"""
    monitor = get_monitor()
    
    # Get historical data from the last N hours
    cutoff_time = datetime.now() - timedelta(hours=hours)
    relevant_data = [
        data for data in monitor.dashboard_data_history
        if data.timestamp >= cutoff_time
    ]
    
    if not relevant_data:
        return {
            "message": "No data available for the specified time range",
            "agent_type": agent_type,
            "hours": hours
        }
    
    trends = {}
    
    for data in relevant_data:
        timestamp = data.timestamp.isoformat()
        
        if agent_type:
            if agent_type in data.task_latency_by_agent:
                latencies = data.task_latency_by_agent[agent_type]
                avg_latency = sum(latencies) / len(latencies) if latencies else 0
                trends[timestamp] = {agent_type: avg_latency}
        else:
            # All agent types
            agent_latencies = {}
            for agent, latencies in data.task_latency_by_agent.items():
                avg_latency = sum(latencies) / len(latencies) if latencies else 0
                agent_latencies[agent] = avg_latency
            trends[timestamp] = agent_latencies
    
    return {
        "trends": trends,
        "agent_type": agent_type,
        "hours": hours,
        "data_points": len(trends)
    }


@router.get("/alerts")
async def get_active_alerts():
    """Get active alerts based on SLO breaches and anomalies"""
    monitor = get_monitor()
    dashboard_data = monitor.get_dashboard_data()
    
    alerts = []
    
    # SLO breach alerts
    for name, slo_status in dashboard_data.slo_status.items():
        if not slo_status.is_healthy:
            severity = "critical" if slo_status.current_value < slo_status.definition.alerting_threshold else "high"
            alerts.append({
                "type": "slo_breach",
                "severity": severity,
                "title": f"SLO Breach: {slo_status.definition.name}",
                "description": f"Current value {slo_status.current_value:.2f} is below target {slo_status.definition.target}",
                "timestamp": slo_status.last_updated.isoformat(),
                "metadata": {
                    "slo_name": name,
                    "slo_type": slo_status.definition.type.value,
                    "breach_count": slo_status.breach_count,
                    "breach_duration": slo_status.breach_duration
                }
            })
    
    # Anomaly alerts
    for anomaly in dashboard_data.anomalies:
        alerts.append({
            "type": "anomaly",
            "severity": anomaly.severity.value,
            "title": f"Anomaly Detected: {anomaly.detection.detection_type.value}",
            "description": anomaly.description,
            "timestamp": anomaly.timestamp.isoformat(),
            "metadata": anomaly.metadata
        })
    
    # Sort by severity and timestamp
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    alerts.sort(key=lambda x: (severity_order.get(x["severity"], 5), x["timestamp"]), reverse=True)
    
    return {
        "alerts": alerts,
        "total_count": len(alerts),
        "critical_count": len([a for a in alerts if a["severity"] == "critical"]),
        "high_count": len([a for a in alerts if a["severity"] == "high"]),
        "timestamp": dashboard_data.timestamp.isoformat()
    }


@router.get("/performance/summary")
async def get_performance_summary():
    """Get overall performance summary"""
    monitor = get_monitor()
    dashboard_data = monitor.get_dashboard_data()
    
    # Calculate overall metrics
    total_agents = len(dashboard_data.agent_performance_metrics)
    healthy_slos = sum(1 for slo in dashboard_data.slo_status.values() if slo.is_healthy)
    total_slos = len(dashboard_data.slo_status)
    
    # Calculate average latency across all agents
    all_latencies = []
    for agent_latencies in dashboard_data.task_latency_by_agent.values():
        all_latencies.extend(agent_latencies)
    
    avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0
    
    # Calculate overall success rate
    success_rates = []
    for metrics in dashboard_data.agent_performance_metrics.values():
        success_rates.append(metrics.get("success_rate", 0))
    
    overall_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
    
    return {
        "overall_health": dashboard_data.system_health["overall_status"],
        "total_agents": total_agents,
        "slo_health": f"{healthy_slos}/{total_slos}",
        "average_latency_seconds": round(avg_latency, 3),
        "overall_success_rate_percent": round(overall_success_rate, 2),
        "active_anomalies": len(dashboard_data.anomalies),
        "last_updated": dashboard_data.timestamp.isoformat()
    }


@router.get("/export/prometheus")
async def export_prometheus_metrics():
    """Export metrics in Prometheus format"""
    monitor = get_monitor()
    metrics_data = monitor.export_metrics()
    return PlainTextResponse(content=f"# Agent Orchestrator Metrics\n{metrics_data}")


@router.post("/test/simulate-load")
async def simulate_load(
    background_tasks: BackgroundTasks,
    duration_seconds: int = Query(60, description="Duration of load simulation"),
    requests_per_second: int = Query(10, description="Requests per second to simulate")
):
    """Simulate load for testing monitoring system"""
    
    async def simulate_requests():
        monitor = get_monitor()
        import random
        
        for _ in range(duration_seconds * requests_per_second):
            # Simulate random orchestration metrics
            latency = random.uniform(0.1, 5.0)  # Random latency between 0.1-5 seconds
            success = random.random() > 0.05  # 95% success rate
            agent_type = random.choice(["rag_agent", "rule_agent", "notification_agent"])
            task_type = random.choice(["query", "rule_generation", "notification"])
            
            await monitor.record_orchestration_metrics(
                latency=latency,
                success=success,
                agent_type=agent_type,
                task_type=task_type
            )
            
            await asyncio.sleep(1 / requests_per_second)
    
    background_tasks.add_task(simulate_requests)
    
    return {
        "message": "Load simulation started",
        "duration_seconds": duration_seconds,
        "requests_per_second": requests_per_second,
        "total_requests": duration_seconds * requests_per_second
    }


@router.get("/config/anomaly-detection")
async def get_anomaly_detection_config():
    """Get current anomaly detection configuration"""
    monitor = get_monitor()
    
    configs = {}
    for metric_name, config in monitor.anomaly_detector.detection_configs.items():
        configs[metric_name] = {
            "detection_type": config.detection_type.value,
            "threshold_multiplier": config.threshold_multiplier,
            "window_size": config.window_size,
            "cooldown_period": config.cooldown_period
        }
    
    return {
        "anomaly_detection_configs": configs,
        "window_size": monitor.anomaly_detector.window_size
    }


@router.get("/config/slo")
async def get_slo_config():
    """Get current SLO configuration"""
    monitor = get_monitor()
    
    slo_configs = {}
    for name, slo_def in monitor.slo_tracker.slo_definitions.items():
        slo_configs[name] = {
            "type": slo_def.type.value,
            "target": slo_def.target,
            "window": slo_def.window,
            "alerting_threshold": slo_def.alerting_threshold,
            "description": slo_def.description
        }
    
    return {
        "slo_definitions": slo_configs
    }


# Health check endpoint for external monitoring
@router.get("/ping")
async def ping():
    """Simple health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

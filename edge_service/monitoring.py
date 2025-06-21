"""
Resource Monitoring Module for Edge Service

This module provides comprehensive system resource monitoring for edge devices,
including CPU, memory, and GPU utilization tracking. It integrates with Prometheus
metrics to provide observability and alerting capabilities.

Features:
- Real-time CPU and memory monitoring
- GPU memory tracking (NVIDIA GPUs via pynvml)
- Configurable alerting thresholds
- Background monitoring thread
- Prometheus metrics integration
- Alert suppression and rate limiting

Dependencies:
    - psutil for system resource monitoring
    - prometheus_client for metrics collection
    - pynvml for GPU monitoring (optional)
"""

import threading
import time
import logging
from typing import Optional, Dict, Any
import os

# System monitoring imports
import psutil
from prometheus_client import Gauge, Counter, Info

# GPU monitoring (optional)
try:
    import pynvml
    GPU_MONITORING_AVAILABLE = True
except ImportError:
    GPU_MONITORING_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

# =============================================================================
# SINGLETON METRICS MANAGER
# =============================================================================

class MetricsManager:
    """Singleton metrics manager to avoid metric duplication"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._init_metrics()
            self._initialized = True
    
    def _init_metrics(self):
        """Initialize Prometheus metrics"""
        self.cpu_usage = Gauge('edge_cpu_usage_percent', 'Current CPU usage percentage')
        self.memory_usage_bytes = Gauge('edge_memory_usage_bytes', 'Current memory usage in bytes')
        self.memory_usage_percent = Gauge('edge_memory_usage_percent', 'Current memory usage percentage')
        self.disk_usage_percent = Gauge('edge_disk_usage_percent', 'Current disk usage percentage')
        
        # Alert counters
        self.high_cpu_alerts = Counter('edge_high_cpu_alerts_total', 'High CPU usage alerts')
        self.high_memory_alerts = Counter('edge_high_memory_alerts_total', 'High memory usage alerts')
        
        # GPU metrics (optional)
        if GPU_MONITORING_AVAILABLE:
            self.gpu_memory_usage_bytes = Gauge('edge_gpu_memory_usage_bytes', 'Current GPU memory usage in bytes')
            self.gpu_memory_usage_percent = Gauge('edge_gpu_memory_usage_percent', 'Current GPU memory usage percentage')
            self.gpu_temperature = Gauge('edge_gpu_temperature_celsius', 'Current GPU temperature in Celsius')
            self.gpu_utilization = Gauge('edge_gpu_utilization_percent', 'Current GPU utilization percentage')
        
        # System info
        self.system_info = Info('edge_system_info', 'System information')
        try:
            self.system_info.info({
                'cpu_count': str(psutil.cpu_count()),
                'cpu_count_logical': str(psutil.cpu_count(logical=True)),
                'total_memory_gb': str(round(psutil.virtual_memory().total / (1024**3), 2))
            })
        except Exception as e:
            logger.warning(f"Failed to set system info: {e}")
        
        logger.info("Prometheus metrics initialized")

# Global metrics instance
_metrics_manager = MetricsManager()

def get_metrics():
    """Get the singleton metrics manager"""
    return _metrics_manager

# =============================================================================
# RESOURCE MONITOR CLASS
# =============================================================================

class ResourceMonitor:
    """Resource monitoring with Prometheus metrics"""
    
    def __init__(self):
        self.monitoring_active = False
        self.monitoring_thread = None
        self.monitor_interval = float(os.getenv('RESOURCE_MONITOR_INTERVAL', '10.0'))  # 10s default for better efficiency
        
        # Thresholds
        self.cpu_threshold = float(os.getenv('HIGH_CPU_THRESHOLD', '80.0'))
        self.memory_threshold = float(os.getenv('HIGH_MEMORY_THRESHOLD', '85.0'))
        
        # Consecutive readings tracking for alert suppression
        self.consecutive_high_cpu_count = 0
        self.consecutive_high_memory_count = 0
        self.required_consecutive_readings = 5  # 5 consecutive readings before alerting
        
        # Get singleton metrics
        self.metrics = get_metrics()
        
        # Initialize GPU monitoring if available
        self.gpu_initialized = False
        if GPU_MONITORING_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # First GPU
                self.gpu_initialized = True
                logger.info("GPU monitoring initialized")
            except Exception as e:
                logger.warning(f"GPU monitoring initialization failed: {e}")
        
        logger.info(f"ResourceMonitor initialized with {self.monitor_interval}s interval")
    
    def get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used
            
            # Disk usage (root partition)
            try:
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent
            except:
                # For Windows, use C: drive
                disk = psutil.disk_usage('C:')
                disk_percent = disk.percent
            
            resources = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_used_bytes': memory_used,
                'disk_percent': disk_percent,
                'timestamp': time.time()
            }
            
            # GPU resources (if available)
            if self.gpu_initialized:
                try:
                    gpu_info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
                    gpu_temp = pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
                    gpu_util = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
                    
                    resources.update({
                        'gpu_memory_used_bytes': gpu_info.used,
                        'gpu_memory_total_bytes': gpu_info.total,
                        'gpu_memory_percent': (gpu_info.used / gpu_info.total) * 100,
                        'gpu_temperature': gpu_temp,
                        'gpu_utilization_percent': gpu_util.gpu
                    })
                except Exception as e:
                    logger.warning(f"GPU monitoring error: {e}")
            
            return resources
            
        except Exception as e:
            logger.error(f"Error getting system resources: {e}")
            return {}
    
    def update_metrics(self, resources: Dict[str, Any]):
        """Update Prometheus metrics with resource data"""
        try:
            # Update basic metrics
            if 'cpu_percent' in resources:
                self.metrics.cpu_usage.set(resources['cpu_percent'])
            
            if 'memory_percent' in resources:
                self.metrics.memory_usage_percent.set(resources['memory_percent'])
            
            if 'memory_used_bytes' in resources:
                self.metrics.memory_usage_bytes.set(resources['memory_used_bytes'])
            
            if 'disk_percent' in resources:
                self.metrics.disk_usage_percent.set(resources['disk_percent'])
            
            # Update GPU metrics if available
            if hasattr(self.metrics, 'gpu_memory_usage_bytes') and 'gpu_memory_used_bytes' in resources:
                self.metrics.gpu_memory_usage_bytes.set(resources['gpu_memory_used_bytes'])
            
            if hasattr(self.metrics, 'gpu_memory_usage_percent') and 'gpu_memory_percent' in resources:
                self.metrics.gpu_memory_usage_percent.set(resources['gpu_memory_percent'])            
            if hasattr(self.metrics, 'gpu_temperature') and 'gpu_temperature' in resources:
                self.metrics.gpu_temperature.set(resources['gpu_temperature'])
            
            if hasattr(self.metrics, 'gpu_utilization') and 'gpu_utilization_percent' in resources:
                self.metrics.gpu_utilization.set(resources['gpu_utilization_percent'])
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
    
    def check_alerts(self, resources: Dict[str, Any]):
        """Check for alert conditions with consecutive reading requirements"""
        try:
            # CPU threshold check with consecutive readings
            if resources.get('cpu_percent', 0) > self.cpu_threshold:
                self.consecutive_high_cpu_count += 1
                if self.consecutive_high_cpu_count >= self.required_consecutive_readings:
                    self.metrics.high_cpu_alerts.inc()
                    logger.warning(f"High CPU usage alert: {resources['cpu_percent']:.1f}% > {self.cpu_threshold}% for {self.consecutive_high_cpu_count} consecutive readings")
            else:
                self.consecutive_high_cpu_count = 0  # Reset counter
            
            # Memory threshold check with consecutive readings
            if resources.get('memory_percent', 0) > self.memory_threshold:
                self.consecutive_high_memory_count += 1
                if self.consecutive_high_memory_count >= self.required_consecutive_readings:
                    self.metrics.high_memory_alerts.inc()
                    logger.warning(f"High memory usage alert: {resources['memory_percent']:.1f}% > {self.memory_threshold}% for {self.consecutive_high_memory_count} consecutive readings")
            else:
                self.consecutive_high_memory_count = 0  # Reset counter
        
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        logger.info("Resource monitoring loop started")
        
        while self.monitoring_active:
            try:
                # Get current resources
                resources = self.get_system_resources()
                
                if resources:
                    # Update metrics
                    self.update_metrics(resources)
                    
                    # Check alerts
                    self.check_alerts(resources)
                
                # Sleep for configured interval
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitor_interval)
        
        logger.info("Resource monitoring loop stopped")
    
    def start_monitoring(self):
        """Start the background monitoring thread"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="ResourceMonitor"
            )
            self.monitoring_thread.start()
            logger.info("Resource monitoring started")
        else:
            logger.warning("Resource monitoring is already active")
    
    def stop_monitoring(self):
        """Stop the background monitoring thread"""
        if self.monitoring_active:
            self.monitoring_active = False
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5.0)
            logger.info("Resource monitoring stopped")
        else:
            logger.warning("Resource monitoring is not active")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        resources = self.get_system_resources()
        return {
            'monitoring_active': self.monitoring_active,
            'monitor_interval': self.monitor_interval,
            'thresholds': {
                'cpu_threshold': self.cpu_threshold,
                'memory_threshold': self.memory_threshold
            },
            'gpu_available': self.gpu_initialized,
            'current_resources': resources
        }

# =============================================================================
# GLOBAL INSTANCE AND AUTO-START
# =============================================================================

# Create global resource monitor instance
resource_monitor = ResourceMonitor()

def get_resource_monitor() -> ResourceMonitor:
    """Get the global resource monitor instance"""
    return resource_monitor


def get_current_resource_status() -> Dict[str, Any]:
    """
    Get current resource status.
    
    :return: Dictionary containing current resource utilization
    """
    monitor = get_resource_monitor()
    return monitor.get_current_status()


def start_resource_monitoring():
    """Start the global resource monitoring"""
    monitor = get_resource_monitor()
    monitor.start_monitoring()


def stop_resource_monitoring():
    """Stop the global resource monitoring"""
    monitor = get_resource_monitor()
    monitor.stop_monitoring()


# Auto-start monitoring when module is imported (for edge deployment)
import atexit

# Start monitoring automatically
try:
    resource_monitor.start_monitoring()
    logger.info("Auto-started resource monitoring on module import")
    
    # Register cleanup on exit
    atexit.register(resource_monitor.stop_monitoring)
    
except Exception as e:
    logger.warning(f"Failed to auto-start resource monitoring: {e}")

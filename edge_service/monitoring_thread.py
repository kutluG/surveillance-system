"""
Background Resource Monitoring Thread for Edge Service

This module provides a dedicated background thread for resource monitoring
that integrates with the inference pipeline to ensure optimal performance
and resource utilization tracking.

Features:
- Dedicated background thread for resource monitoring
- Integration with Prometheus metrics
- Configurable monitoring intervals
- CPU and memory threshold monitoring with alerts
- Graceful shutdown handling

Dependencies:
    - monitoring module for ResourceMonitor class
    - threading for background execution
    - time for monitoring intervals
"""

import threading
import time
import logging
import atexit
from typing import Optional

try:
    from .monitoring import get_resource_monitor, get_metrics
except ImportError:
    # Fallback for direct execution
    from monitoring import get_resource_monitor, get_metrics

# Configure logging
logger = logging.getLogger(__name__)


class InferenceResourceMonitor:
    """
    Dedicated resource monitoring thread for inference operations.
    
    This class provides background resource monitoring specifically tailored
    for inference workloads, with configurable intervals and alert thresholds.
    """
    
    def __init__(self, interval: float = 10.0):
        """
        Initialize the inference resource monitor.
        
        :param interval: Monitoring interval in seconds (default: 10s)
        """
        self.interval = interval
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Get the global resource monitor
        self.resource_monitor = get_resource_monitor()
        self.metrics = get_metrics()
        
        logger.info(f"InferenceResourceMonitor initialized with {interval}s interval")
    
    def _monitoring_loop(self):
        """
        Background monitoring loop for inference resource tracking.
        
        This loop runs in a separate thread and continuously monitors
        system resources, updating Prometheus metrics and checking
        for alert conditions.
        """
        logger.info("Inference resource monitoring loop started")
        
        while self.monitoring_active and not self._shutdown_event.is_set():
            try:
                # Get current system resources
                resources = self.resource_monitor.get_system_resources()
                
                if resources:
                    # Update Prometheus metrics
                    self.resource_monitor.update_metrics(resources)
                    
                    # Check for alert conditions
                    self.resource_monitor.check_alerts(resources)
                    
                    # Log debug information
                    logger.debug(f"Resources: CPU={resources.get('cpu_percent', 0):.1f}%, "
                               f"Memory={resources.get('memory_percent', 0):.1f}%")
                
                # Wait for next interval or shutdown signal
                if self._shutdown_event.wait(timeout=self.interval):
                    break  # Shutdown signal received
                    
            except Exception as e:
                logger.error(f"Error in inference monitoring loop: {e}")
                # Sleep to prevent tight error loop
                time.sleep(self.interval)
        
        logger.info("Inference resource monitoring loop stopped")
    
    def start_monitoring(self):
        """Start the background resource monitoring thread."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self._shutdown_event.clear()
            
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="InferenceResourceMonitor"
            )
            self.monitoring_thread.start()
            
            logger.info("Inference resource monitoring started")
        else:
            logger.warning("Inference resource monitoring is already active")
    
    def stop_monitoring(self):
        """Stop the background resource monitoring thread."""
        if self.monitoring_active:
            self.monitoring_active = False
            self._shutdown_event.set()
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                # Give the thread up to 5 seconds to shutdown gracefully
                self.monitoring_thread.join(timeout=5.0)
                
                if self.monitoring_thread.is_alive():
                    logger.warning("Monitoring thread did not stop gracefully")
                else:
                    logger.info("Inference resource monitoring stopped gracefully")
            
            self.monitoring_thread = None
        else:
            logger.warning("Inference resource monitoring is not active")
    
    def is_monitoring_active(self) -> bool:
        """
        Check if monitoring is currently active.
        
        :return: True if monitoring is active, False otherwise
        """
        return self.monitoring_active and (
            self.monitoring_thread is not None and 
            self.monitoring_thread.is_alive()
        )
    
    def get_monitoring_status(self) -> dict:
        """
        Get current monitoring status.
        
        :return: Dictionary containing monitoring status information
        """
        return {
            'monitoring_active': self.is_monitoring_active(),
            'interval': self.interval,
            'thread_name': self.monitoring_thread.name if self.monitoring_thread else None,
            'thread_alive': self.monitoring_thread.is_alive() if self.monitoring_thread else False,
            'resource_monitor_status': self.resource_monitor.get_current_status()
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

# Create global inference monitoring instance
inference_monitor = InferenceResourceMonitor()


def start_inference_monitoring():
    """Start the global inference resource monitoring."""
    inference_monitor.start_monitoring()


def stop_inference_monitoring():
    """Stop the global inference resource monitoring."""
    inference_monitor.stop_monitoring()


def get_inference_monitoring_status() -> dict:
    """Get the current inference monitoring status."""
    return inference_monitor.get_monitoring_status()


# Auto-start monitoring and register cleanup
def _cleanup_monitoring():
    """Cleanup function for graceful shutdown."""
    try:
        stop_inference_monitoring()
    except Exception as e:
        logger.error(f"Error during monitoring cleanup: {e}")


# Register cleanup function
atexit.register(_cleanup_monitoring)

# Auto-start monitoring when module is imported
try:
    start_inference_monitoring()
    logger.info("Auto-started inference resource monitoring")
except Exception as e:
    logger.warning(f"Failed to auto-start inference monitoring: {e}")

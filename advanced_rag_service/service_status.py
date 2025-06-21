"""
Service Status Manager for tracking external service health

Provides centralized monitoring and status tracking for external services
like Weaviate, OpenAI, and Redis to enable graceful degradation.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Status of external services"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """Health information for a service"""
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_check: datetime = field(default_factory=datetime.utcnow)
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    response_time_ms: Optional[float] = None
    degraded_since: Optional[datetime] = None


class ServiceStatusManager:
    """Manages status of external services for graceful degradation"""
    
    def __init__(self):
        self.services: Dict[str, ServiceHealth] = {
            "weaviate": ServiceHealth(),
            "openai": ServiceHealth(),
            "redis": ServiceHealth(),
            "embedding_model": ServiceHealth()
        }
        self.health_check_interval = 30  # seconds
        self.max_consecutive_failures = 3
        self.degradation_threshold = 5.0  # seconds
        
    async def check_service_health(self, service_name: str, health_check_func) -> ServiceStatus:
        """
        Check health of a specific service
        
        Args:
            service_name: Name of service to check
            health_check_func: Async function that returns True if service is healthy
            
        Returns:
            Current service status
        """
        if service_name not in self.services:
            self.services[service_name] = ServiceHealth()
            
        service = self.services[service_name]
        start_time = time.time()
        
        try:
            # Run health check with timeout
            is_healthy = await asyncio.wait_for(health_check_func(), timeout=10.0)
            response_time = (time.time() - start_time) * 1000
            
            service.last_check = datetime.utcnow()
            service.response_time_ms = response_time
            
            if is_healthy:
                service.consecutive_failures = 0
                service.last_error = None
                
                # Determine status based on response time
                if response_time > self.degradation_threshold * 1000:  # Convert to ms
                    service.status = ServiceStatus.DEGRADED
                    if not service.degraded_since:
                        service.degraded_since = datetime.utcnow()
                else:
                    service.status = ServiceStatus.HEALTHY
                    service.degraded_since = None
                    
            else:
                service.consecutive_failures += 1
                service.status = ServiceStatus.UNAVAILABLE
                service.last_error = "Health check returned False"
                
        except asyncio.TimeoutError:
            service.consecutive_failures += 1
            service.status = ServiceStatus.UNAVAILABLE
            service.last_error = "Health check timeout"
            logger.warning(f"Health check timeout for {service_name}")
            
        except Exception as e:
            service.consecutive_failures += 1
            service.status = ServiceStatus.UNAVAILABLE
            service.last_error = str(e)
            logger.error(f"Health check failed for {service_name}: {e}")
            
        return service.status
        
    def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get current status of a service"""
        service = self.services.get(service_name)
        if not service:
            return ServiceStatus.UNKNOWN
            
        # Check if status is stale (no check in last 5 minutes)
        if datetime.utcnow() - service.last_check > timedelta(minutes=5):
            return ServiceStatus.UNKNOWN
            
        return service.status
        
    def is_service_available(self, service_name: str) -> bool:
        """Check if service is available for requests"""
        status = self.get_service_status(service_name)
        return status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]
        
    def is_service_healthy(self, service_name: str) -> bool:
        """Check if service is fully healthy"""
        return self.get_service_status(service_name) == ServiceStatus.HEALTHY
        
    def get_degraded_services(self) -> List[str]:
        """Get list of degraded services"""
        degraded = []
        for name, service in self.services.items():
            if service.status == ServiceStatus.DEGRADED:
                degraded.append(name)
        return degraded
        
    def get_unavailable_services(self) -> List[str]:
        """Get list of unavailable services"""
        unavailable = []
        for name, service in self.services.items():
            if service.status == ServiceStatus.UNAVAILABLE:
                unavailable.append(name)
        return unavailable
        
    def get_service_health_summary(self) -> Dict[str, Any]:
        """Get summary of all service health"""
        summary = {}
        for name, service in self.services.items():
            summary[name] = {
                "status": service.status.value,
                "last_check": service.last_check.isoformat(),
                "consecutive_failures": service.consecutive_failures,
                "response_time_ms": service.response_time_ms,
                "last_error": service.last_error,
                "degraded_since": service.degraded_since.isoformat() if service.degraded_since else None
            }
        return summary
        
    def reset_service_status(self, service_name: str):
        """Reset service status to unknown"""
        if service_name in self.services:
            self.services[service_name] = ServiceHealth()
            
    async def start_health_monitoring(self, health_checks: Dict[str, callable]):
        """
        Start background health monitoring for services
        
        Args:
            health_checks: Dict mapping service names to health check functions
        """
        async def monitor_loop():
            while True:
                try:
                    for service_name, health_check_func in health_checks.items():
                        await self.check_service_health(service_name, health_check_func)
                        await asyncio.sleep(1)  # Small delay between checks
                        
                    await asyncio.sleep(self.health_check_interval)
                    
                except Exception as e:
                    logger.error(f"Error in health monitoring loop: {e}")
                    await asyncio.sleep(5)  # Brief pause on error
                    
        # Start monitoring task
        asyncio.create_task(monitor_loop())
        logger.info("Started service health monitoring")


# Global service status manager instance
service_status_manager = ServiceStatusManager()

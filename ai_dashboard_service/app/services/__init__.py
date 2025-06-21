"""
Services package for AI Dashboard Service

Contains business logic, analytics engines, and external service integrations.
All services now use dependency injection pattern.
"""

# Import service classes (no global instances)
from .analytics import AnalyticsService
from .llm_client import LLMService
from .dashboard import DashboardService

__all__ = [
    "AnalyticsService",
    "LLMService", 
    "DashboardService"
]

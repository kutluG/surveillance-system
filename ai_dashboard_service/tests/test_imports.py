"""
Import Tests for AI Dashboard Service

These tests verify that all modules can be imported correctly,
ensuring the package structure is properly organized.
"""

import importlib
import pytest


@pytest.mark.parametrize("module", [
    "app.main",
    "app.models",
    "app.services.analytics", 
    "app.services.predictive",
    "app.services.reports",
    "app.services.llm_client",
    "app.routers.dashboard",
    "app.utils.database",
    "app.utils.helpers",
    "config.config"
])
def test_imports(module):
    """Test that all main modules can be imported without errors"""
    try:
        importlib.import_module(module)
    except ImportError as e:
        pytest.fail(f"Failed to import {module}: {e}")


def test_config_settings():
    """Test that configuration settings are properly loaded"""
    from config.config import settings
    
    # Test that settings object exists
    assert settings is not None
    
    # Test that key settings have default values
    assert hasattr(settings, 'SERVICE_PORT')
    assert hasattr(settings, 'SERVICE_HOST')
    assert hasattr(settings, 'LOG_LEVEL')


def test_app_creation():
    """Test that the FastAPI app can be created"""
    from app.main import create_app
    
    app = create_app()
    assert app is not None
    assert hasattr(app, 'routes')


def test_model_imports():
    """Test that all model classes can be imported"""
    from app.models import (
        AnalyticsRequest, PredictionRequest, ReportGenerationRequest,
        WidgetRequest, AnalyticsType, TimeRange, WidgetType, PredictionType
    )
    
    # Test enum values
    assert AnalyticsType.TREND_ANALYSIS == "trend_analysis"
    assert TimeRange.LAST_24_HOURS == "last_24_hours"
    assert WidgetType.CHART == "chart"
    assert PredictionType.SECURITY_THREAT == "security_threat"


def test_service_instances():
    """Test that service classes can be instantiated"""
    from app.services import AnalyticsService, LLMService, DashboardService
    
    # Test that classes can be imported
    assert AnalyticsService is not None
    assert LLMService is not None  
    assert DashboardService is not None


def test_router_creation():
    """Test that routers are properly configured"""
    from app.routers import dashboard_router
    
    assert dashboard_router is not None
    assert hasattr(dashboard_router, 'routes')
    
    # Check that some expected routes exist
    route_paths = [route.path for route in dashboard_router.routes]
    assert any("/analytics/trends" in path for path in route_paths)
    assert any("/predictions" in path for path in route_paths)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

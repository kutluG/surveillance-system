"""
Test Dependency Injection Imports

This test file verifies that all dependency injection functions and service classes
can be imported without error.
"""

import sys
import os
import pytest

# Add the parent directory to the path so we can import from the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_dependencies_can_be_imported():
    """Test that all dependency functions can be imported"""
    from app.utils.dependencies import (
        get_redis,
        get_openai_client,
        get_weaviate_client,
        get_db_session,
        get_analytics_service,
        get_llm_service,
        get_dashboard_service,
        cleanup_dependencies
    )
    
    # Test that all functions are importable and callable (not called, just checked)
    assert callable(get_redis)
    assert callable(get_openai_client)
    assert callable(get_weaviate_client)
    assert callable(get_db_session)
    assert callable(get_analytics_service)
    assert callable(get_llm_service)
    assert callable(get_dashboard_service)
    assert callable(cleanup_dependencies)


def test_service_classes_can_be_imported():
    """Test that all service classes can be imported"""
    from app.services.analytics import AnalyticsService
    from app.services.llm_client import LLMService
    from app.services.dashboard import DashboardService
    
    # Test that all classes are importable
    assert AnalyticsService is not None
    assert LLMService is not None
    assert DashboardService is not None


def test_config_settings_accessible():
    """Test that configuration settings are accessible"""
    from config.config import settings
    
    # Test that settings are accessible
    assert hasattr(settings, 'REDIS_URL')
    assert hasattr(settings, 'DATABASE_URL')
    assert hasattr(settings, 'OPENAI_API_KEY')
    assert hasattr(settings, 'WEAVIATE_URL')


def test_models_can_be_imported():
    """Test that all models can be imported"""
    from app.models import (
        AnalyticsRequest,
        PredictionRequest,
        ReportGenerationRequest,
        WidgetRequest,
        AnalyticsType,
        TimeRange,
        WidgetType
    )
    
    # Test that all models are importable
    assert AnalyticsRequest is not None
    assert PredictionRequest is not None
    assert ReportGenerationRequest is not None
    assert WidgetRequest is not None
    assert AnalyticsType is not None
    assert TimeRange is not None
    assert WidgetType is not None


if __name__ == "__main__":
    pytest.main([__file__])

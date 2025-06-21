"""
Tests for Configuration Management

This module tests the centralized configuration management system
to ensure environment variables are properly loaded and validated.
"""

import os
import pytest
from unittest.mock import patch
from config import OrchestratorConfig, get_config, reload_config, validate_config


class TestOrchestratorConfig:
    """Test cases for the OrchestratorConfig class"""
    
    def test_default_configuration(self):
        """Test that default configuration values are loaded correctly"""
        config = OrchestratorConfig()
        
        # Test default values
        assert config.service_host == "0.0.0.0"
        assert config.service_port == 8006
        assert config.redis_url == "redis://redis:6379/0"
        assert config.rag_service_url == "http://advanced_rag_service:8000"
        assert config.rulegen_service_url == "http://rulegen_service:8000"
        assert config.notifier_service_url == "http://notifier:8000"
        assert config.log_level == "INFO"
        assert config.debug_mode is False
        assert config.enable_rate_limiting is True
    
    def test_environment_variable_override(self):
        """Test that environment variables override default values"""
        with patch.dict(os.environ, {
            'HOST': '127.0.0.1',
            'PORT': '9000',
            'LOG_LEVEL': 'DEBUG',
            'DEBUG_MODE': 'true',
            'RAG_SERVICE_URL': 'http://custom-rag:8080'
        }):
            config = OrchestratorConfig()
            assert config.service_host == "127.0.0.1"
            assert config.service_port == 9000
            assert config.log_level == "DEBUG"
            assert config.debug_mode is True
            assert config.rag_service_url == "http://custom-rag:8080"
    
    def test_cors_origins_parsing(self):
        """Test that CORS origins are parsed correctly from string"""
        with patch.dict(os.environ, {
            'CORS_ORIGINS': 'http://localhost:3000,https://example.com,http://app.local'
        }):
            config = OrchestratorConfig()
            expected_origins = ['http://localhost:3000', 'https://example.com', 'http://app.local']
            assert config.cors_origins == expected_origins
    
    def test_validation_errors(self):
        """Test that validation errors are raised for invalid values"""
        with patch.dict(os.environ, {'PORT': '99999'}):
            with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
                OrchestratorConfig()
        
        with patch.dict(os.environ, {'LOG_LEVEL': 'INVALID'}):
            with pytest.raises(ValueError, match="Log level must be one of"):
                OrchestratorConfig()
        
        with patch.dict(os.environ, {'MAX_RETRY_ATTEMPTS': '0'}):
            with pytest.raises(ValueError, match="Max retry attempts must be at least 1"):
                OrchestratorConfig()
    
    def test_positive_float_validation(self):
        """Test validation of positive float values"""
        with patch.dict(os.environ, {'HTTP_TIMEOUT': '-1.0'}):
            with pytest.raises(ValueError, match="Value must be positive"):
                OrchestratorConfig()
        
        with patch.dict(os.environ, {'RETRY_BASE_DELAY': '0'}):
            with pytest.raises(ValueError, match="Value must be positive"):
                OrchestratorConfig()
    
    def test_get_config_singleton(self):
        """Test that get_config returns the same instance"""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2
    
    def test_reload_config(self):
        """Test configuration reloading"""
        original_config = get_config()
        original_port = original_config.service_port
        
        with patch.dict(os.environ, {'PORT': '7777'}):
            new_config = reload_config()
            assert new_config.service_port == 7777
            assert new_config is not original_config
    
    def test_validate_config_function(self):
        """Test that validate_config runs without errors"""
        # This should not raise any exceptions
        result = validate_config()
        assert result is True


class TestEnvironmentHelpers:
    """Test environment helper functions"""
    
    def test_is_development(self):
        """Test development environment detection"""
        from config import is_development
        
        # Test debug mode
        with patch.dict(os.environ, {'DEBUG_MODE': 'true'}):
            config = reload_config()
            assert is_development() is True
        
        # Test environment variable
        with patch.dict(os.environ, {'ENVIRONMENT': 'development', 'DEBUG_MODE': 'false'}):
            config = reload_config()
            assert is_development() is True
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'production', 'DEBUG_MODE': 'false'}):
            config = reload_config()
            assert is_development() is False
    
    def test_is_production(self):
        """Test production environment detection"""
        from config import is_production
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            assert is_production() is True
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            assert is_production() is False
    
    def test_is_testing(self):
        """Test testing environment detection"""
        from config import is_testing
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'testing'}):
            assert is_testing() is True
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            assert is_testing() is False


class TestConfigurationIntegration:
    """Test configuration integration with services"""
    
    def test_database_url_format(self):
        """Test that database URL has correct format"""
        config = OrchestratorConfig()
        assert config.database_url.startswith("postgresql+asyncpg://")
    
    def test_redis_url_format(self):
        """Test that Redis URL has correct format"""
        config = OrchestratorConfig()
        assert config.redis_url.startswith("redis://")
    
    def test_service_urls_format(self):
        """Test that service URLs have correct format"""
        config = OrchestratorConfig()
        
        assert config.rag_service_url.startswith("http")
        assert config.rulegen_service_url.startswith("http")
        assert config.notifier_service_url.startswith("http")
        
        # Should not end with slash
        assert not config.rag_service_url.endswith("/")
        assert not config.rulegen_service_url.endswith("/")
        assert not config.notifier_service_url.endswith("/")
    
    def test_retry_configuration_consistency(self):
        """Test that retry configuration values are consistent"""
        config = OrchestratorConfig()
        
        assert config.retry_base_delay < config.retry_max_delay
        assert config.retry_multiplier > 1.0
        assert config.max_retry_attempts >= 1


if __name__ == "__main__":
    pytest.main([__file__])

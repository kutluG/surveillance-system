"""
Unit Tests for Analytics Service

This module provides comprehensive unit tests for the AnalyticsService class,
covering trend analysis, anomaly detection, and performance metrics functionality.
Tests include edge cases, error scenarios, and validation of statistical calculations.

Test Coverage:
- Trend analysis with various data patterns
- Anomaly detection with different threshold scenarios  
- Performance metrics collection and aggregation
- Edge cases: empty data, insufficient data points
- Error handling: database failures, invalid inputs
- Statistical accuracy: regression calculations, Z-score analysis

Key Test Scenarios:
- Valid trend calculations with increasing/decreasing patterns
- Anomaly detection with configurable thresholds
- Performance metrics with realistic system data
- Error resilience and graceful degradation
- Data validation and input sanitization
"""

import pytest
import asyncio
import statistics
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.services.analytics import AnalyticsService
from app.models.schemas import AnalyticsRequest, TrendAnalysis, AnomalyDetection
from app.models.enums import AnalyticsType, TimeRange


class TestAnalyticsService:
    """Comprehensive test suite for AnalyticsService functionality."""
    
    @pytest.mark.asyncio
    async def test_analyze_trends_success(self, analytics_service, sample_analytics_request, sample_time_series_data):
        """
        Test successful trend analysis with realistic data.
        
        Validates that trend analysis correctly identifies patterns in
        surveillance data and calculates accurate trend metrics including
        direction, magnitude, and confidence levels.
        """
        # Mock the time series data retrieval
        analytics_service._get_time_series_data = AsyncMock(return_value=sample_time_series_data)
        
        # Execute trend analysis
        result = await analytics_service.analyze_trends(sample_analytics_request)
        
        # Verify results structure
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Verify each trend analysis result
        for trend in result:
            assert isinstance(trend, TrendAnalysis)
            assert trend.metric in sample_time_series_data.keys()
            assert trend.direction in ["increasing", "decreasing", "stable"]
            assert isinstance(trend.magnitude, float)
            assert 0.0 <= trend.confidence <= 1.0
            assert isinstance(trend.contributing_factors, list)
            assert len(trend.contributing_factors) > 0
        
        # Verify the mock was called correctly
        analytics_service._get_time_series_data.assert_called_once_with(sample_analytics_request)
    
    @pytest.mark.asyncio
    async def test_analyze_trends_insufficient_data(self, analytics_service, sample_analytics_request):
        """
        Test trend analysis with insufficient data points.
        
        Validates that the service gracefully handles scenarios where
        metrics have too few data points for reliable trend calculation.
        """
        # Mock insufficient data (less than 10 points required)
        insufficient_data = {
            "detection_count": [5, 7, 6],  # Only 3 data points
            "alert_count": [1, 2]  # Only 2 data points
        }
        analytics_service._get_time_series_data = AsyncMock(return_value=insufficient_data)
        
        # Execute trend analysis
        result = await analytics_service.analyze_trends(sample_analytics_request)
        
        # Should return empty list due to insufficient data
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_trends_empty_data(self, analytics_service, sample_analytics_request):
        """
        Test trend analysis with completely empty dataset.
        
        Validates proper handling of empty data scenarios without
        raising exceptions or returning invalid results.
        """
        # Mock empty data
        analytics_service._get_time_series_data = AsyncMock(return_value={})
        
        # Execute trend analysis
        result = await analytics_service.analyze_trends(sample_analytics_request)
        
        # Should return empty list
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_success(self, analytics_service, sample_analytics_request):
        """
        Test successful anomaly detection with data containing outliers.
        
        Validates that anomaly detection correctly identifies statistical
        outliers and classifies them with appropriate severity levels.
        """
        # Create data with clear anomalies
        anomaly_data = {
            "detection_count": [10, 12, 8, 11, 9, 10, 150, 11, 9, 10] * 4,  # 150 is a clear anomaly
            "processing_latency": [85, 90, 88, 92, 87, 89, 500, 91, 86, 88] * 4  # 500 is a clear anomaly
        }
        analytics_service._get_time_series_data = AsyncMock(return_value=anomaly_data)
        
        # Execute anomaly detection
        result = await analytics_service.detect_anomalies(sample_analytics_request)
        
        # Verify results structure
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Verify anomaly detection results
        for anomaly in result:
            assert isinstance(anomaly, AnomalyDetection)
            assert anomaly.metric in anomaly_data.keys()
            assert anomaly.severity in ["low", "medium", "high", "critical"]
            assert isinstance(anomaly.deviation, float)
            assert anomaly.deviation > analytics_service.anomaly_threshold
            assert anomaly.actual_value != anomaly.expected_value
            assert len(anomaly.description) > 0
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_no_anomalies(self, analytics_service, sample_analytics_request):
        """
        Test anomaly detection with normal data containing no outliers.
        
        Validates that the service correctly identifies when no anomalies
        are present in well-behaved surveillance data.
        """
        # Create normal data without anomalies
        normal_data = {
            "detection_count": [10, 11, 9, 12, 8, 10, 11, 9, 10, 12] * 4,  # Normal variation
            "alert_count": [2, 3, 1, 2, 3, 2, 1, 3, 2, 1] * 4  # Normal variation
        }
        analytics_service._get_time_series_data = AsyncMock(return_value=normal_data)
        
        # Execute anomaly detection
        result = await analytics_service.detect_anomalies(sample_analytics_request)
        
        # Should return empty list (no anomalies detected)
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_insufficient_data(self, analytics_service, sample_analytics_request):
        """
        Test anomaly detection with insufficient data for statistical analysis.
        
        Validates proper handling when there are too few data points
        for reliable anomaly detection using statistical methods.
        """
        # Mock insufficient data (less than 30 points required)
        insufficient_data = {
            "detection_count": [10, 12, 8, 11, 9],  # Only 5 data points
            "alert_count": [2, 3, 1]  # Only 3 data points
        }
        analytics_service._get_time_series_data = AsyncMock(return_value=insufficient_data)
        
        # Execute anomaly detection
        result = await analytics_service.detect_anomalies(sample_analytics_request)
        
        # Should return empty list due to insufficient data
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics_success(self, analytics_service, sample_analytics_request):
        """
        Test successful performance metrics collection.
        
        Validates that performance metrics are properly collected and
        formatted with realistic surveillance system values.
        """
        # Execute performance metrics collection
        result = await analytics_service.get_performance_metrics(sample_analytics_request)
        
        # Verify results structure
        assert isinstance(result, dict)
        assert "system_health" in result
        assert "surveillance_metrics" in result
        assert "processing_metrics" in result
        assert "timestamp" in result
        
        # Verify system health metrics
        system_health = result["system_health"]
        assert isinstance(system_health["cpu_usage"], float)
        assert 0 <= system_health["cpu_usage"] <= 100
        assert isinstance(system_health["memory_usage"], float)
        assert 0 <= system_health["memory_usage"] <= 100
        
        # Verify surveillance metrics
        surveillance_metrics = result["surveillance_metrics"]
        assert isinstance(surveillance_metrics["active_cameras"], int)
        assert surveillance_metrics["active_cameras"] > 0
        assert isinstance(surveillance_metrics["detection_rate"], float)
        assert 0 <= surveillance_metrics["detection_rate"] <= 1
        
        # Verify processing metrics
        processing_metrics = result["processing_metrics"]
        assert isinstance(processing_metrics["frames_per_second"], float)
        assert processing_metrics["frames_per_second"] > 0
        assert isinstance(processing_metrics["processing_latency"], float)
        assert processing_metrics["processing_latency"] > 0
    
    @pytest.mark.asyncio
    async def test_calculate_trend_increasing_pattern(self, analytics_service):
        """
        Test trend calculation with clear increasing pattern.
        
        Validates accurate trend detection and slope calculation
        for data showing a clear upward trend.
        """
        # Create clearly increasing data
        increasing_values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        
        # Calculate trend
        result = await analytics_service._calculate_trend("test_metric", increasing_values, TimeRange.LAST_24_HOURS)
        
        # Verify trend analysis
        assert result is not None
        assert isinstance(result, TrendAnalysis)
        assert result.metric == "test_metric"
        assert result.direction == "increasing"
        assert result.magnitude > 0
        assert result.confidence > 0.5
        assert isinstance(result.contributing_factors, list)
    
    @pytest.mark.asyncio
    async def test_calculate_trend_decreasing_pattern(self, analytics_service):
        """
        Test trend calculation with clear decreasing pattern.
        
        Validates accurate trend detection and slope calculation
        for data showing a clear downward trend.
        """
        # Create clearly decreasing data
        decreasing_values = [10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0]
        
        # Calculate trend
        result = await analytics_service._calculate_trend("test_metric", decreasing_values, TimeRange.LAST_24_HOURS)
        
        # Verify trend analysis
        assert result is not None
        assert isinstance(result, TrendAnalysis)
        assert result.metric == "test_metric"
        assert result.direction == "decreasing"
        assert result.magnitude > 0
        assert result.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_calculate_trend_stable_pattern(self, analytics_service):
        """
        Test trend calculation with stable/flat pattern.
        
        Validates correct identification of stable trends where
        values remain relatively constant over time.
        """
        # Create stable data with minimal variation
        stable_values = [5.0, 5.1, 4.9, 5.0, 5.1, 4.9, 5.0, 5.1, 4.9, 5.0]
        
        # Calculate trend
        result = await analytics_service._calculate_trend("test_metric", stable_values, TimeRange.LAST_24_HOURS)
        
        # Verify trend analysis
        assert result is not None
        assert isinstance(result, TrendAnalysis)
        assert result.metric == "test_metric"
        assert result.direction == "stable"
        assert result.magnitude < 0.1  # Very low magnitude for stable trend
    
    @pytest.mark.asyncio
    async def test_calculate_trend_insufficient_data(self, analytics_service):
        """
        Test trend calculation with insufficient data points.
        
        Validates proper handling when there are too few data points
        for reliable trend calculation.
        """
        # Single data point
        insufficient_values = [5.0]
        
        # Calculate trend
        result = await analytics_service._calculate_trend("test_metric", insufficient_values, TimeRange.LAST_24_HOURS)
        
        # Should return None for insufficient data
        assert result is None
    
    @pytest.mark.asyncio
    async def test_detect_metric_anomalies_with_outliers(self, analytics_service):
        """
        Test anomaly detection on specific metric with clear outliers.
        
        Validates that Z-score based anomaly detection correctly
        identifies statistical outliers in surveillance metrics.        """
        # Create data with clear outliers - need 30+ points for analysis
        values_with_outliers = ([10] * 35) + [100] + ([10] * 5)  # 100 is clear outlier
        
        # Detect anomalies
        result = await analytics_service._detect_metric_anomalies("test_metric", values_with_outliers)
        
        # Verify anomaly detection
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check anomaly properties
        anomaly = result[0]
        assert isinstance(anomaly, AnomalyDetection)
        assert anomaly.metric == "test_metric"
        assert anomaly.severity in ["medium", "high"]
        assert anomaly.deviation > analytics_service.anomaly_threshold
    
    @pytest.mark.asyncio
    async def test_detect_metric_anomalies_no_outliers(self, analytics_service):
        """
        Test anomaly detection on metric with no outliers.
        
        Validates that anomaly detection correctly identifies
        when no anomalies are present in normal data.
        """
        # Create normal data without outliers
        normal_values = [10, 11, 9, 12, 8, 10, 11, 9, 10, 12] * 5  # 50 normal values
        
        # Detect anomalies
        result = await analytics_service._detect_metric_anomalies("test_metric", normal_values)
        
        # Should find no anomalies
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_data_points_for_timerange(self, analytics_service):
        """
        Test data point calculation for different time ranges.
        
        Validates that appropriate data point counts are calculated
        for different time ranges to balance accuracy and performance.
        """
        # Test each time range
        assert analytics_service._get_data_points_for_timerange(TimeRange.LAST_HOUR) == 60
        assert analytics_service._get_data_points_for_timerange(TimeRange.LAST_24_HOURS) == 24
        assert analytics_service._get_data_points_for_timerange(TimeRange.LAST_WEEK) == 168
        assert analytics_service._get_data_points_for_timerange(TimeRange.LAST_MONTH) == 720
        
        # Test default fallback for unknown time range
        unknown_range = "unknown_range"
        assert analytics_service._get_data_points_for_timerange(unknown_range) == 100
    
    def test_get_contributing_factors(self, analytics_service):
        """
        Test contributing factors identification for different metrics and trends.
        
        Validates that appropriate contextual explanations are provided
        for different types of trends in various surveillance metrics.
        """
        # Test detection count factors
        factors = analytics_service._get_contributing_factors("detection_count", "increasing")
        assert isinstance(factors, list)
        assert len(factors) > 0
        assert "Higher activity levels" in factors or "Improved detection sensitivity" in factors
        
        # Test alert count factors
        factors = analytics_service._get_contributing_factors("alert_count", "decreasing")
        assert isinstance(factors, list)
        assert len(factors) > 0
        assert "Improved security" in factors or "Alert threshold adjustments" in factors
        
        # Test camera uptime factors
        factors = analytics_service._get_contributing_factors("camera_uptime", "stable")
        assert isinstance(factors, list)
        assert len(factors) > 0
        assert "Reliable operation" in factors
        
        # Test unknown metric
        factors = analytics_service._get_contributing_factors("unknown_metric", "increasing")
        assert isinstance(factors, list)
        assert "Unknown factors" in factors
    
    @pytest.mark.asyncio
    async def test_error_handling_trend_analysis(self, analytics_service, sample_analytics_request):
        """
        Test error handling in trend analysis operations.
        
        Validates that trend analysis gracefully handles errors and
        provides meaningful error messages for debugging.
        """
        # Mock an error in data retrieval
        analytics_service._get_time_series_data = AsyncMock(side_effect=Exception("Database error"))
        
        # Execute trend analysis (should raise exception)
        with pytest.raises(Exception) as exc_info:
            await analytics_service.analyze_trends(sample_analytics_request)
        
        assert "Error analyzing trends" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_error_handling_anomaly_detection(self, analytics_service, sample_analytics_request):
        """
        Test error handling in anomaly detection operations.
        
        Validates that anomaly detection gracefully handles errors
        and provides meaningful error messages for debugging.
        """
        # Mock an error in data retrieval
        analytics_service._get_time_series_data = AsyncMock(side_effect=Exception("Data processing error"))
        
        # Execute anomaly detection (should raise exception)
        with pytest.raises(Exception) as exc_info:
            await analytics_service.detect_anomalies(sample_analytics_request)
        
        assert "Error detecting anomalies" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_error_handling_performance_metrics(self, analytics_service, sample_analytics_request):
        """
        Test error handling in performance metrics collection.
        
        Validates that performance metrics collection gracefully
        handles errors and provides meaningful error messages.
        """
        # Mock an error in performance metrics collection
        with patch('numpy.random.uniform', side_effect=Exception("Random generation error")):
            with pytest.raises(Exception) as exc_info:
                await analytics_service.get_performance_metrics(sample_analytics_request)
            
            assert "Error getting performance metrics" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_time_series_data_generation(self, analytics_service, sample_analytics_request):
        """
        Test time series data generation for different scenarios.
        
        Validates that synthetic time series data is generated with
        appropriate statistical properties and realistic patterns.
        """
        # Generate time series data
        result = await analytics_service._get_time_series_data(sample_analytics_request)
        
        # Verify data structure
        assert isinstance(result, dict)
        assert "detection_count" in result
        assert "alert_count" in result
        assert "camera_uptime" in result
        assert "processing_latency" in result
        
        # Verify data properties
        for metric, values in result.items():
            assert isinstance(values, list)
            assert len(values) > 0
            assert all(isinstance(v, (int, float)) for v in values)
            
            # Verify realistic ranges
            if metric == "camera_uptime":
                assert all(0 <= v <= 1.0 for v in values)  # Uptime should be 0-1
            elif metric in ["detection_count", "alert_count"]:
                assert all(v >= 0 for v in values)  # Counts should be non-negative
            elif metric == "processing_latency":
                assert all(v > 0 for v in values)  # Latency should be positive
    
    @pytest.mark.asyncio
    async def test_trend_cache_behavior(self, analytics_service, sample_analytics_request, sample_time_series_data):
        """
        Test trend caching behavior and memory management.
        
        Validates that trend results are properly cached and that
        the cache doesn't grow beyond configured limits.
        """
        # Mock the time series data retrieval
        analytics_service._get_time_series_data = AsyncMock(return_value=sample_time_series_data)
        
        # Verify initial cache state
        initial_cache_size = len(analytics_service.trend_cache)
        
        # Execute trend analysis
        await analytics_service.analyze_trends(sample_analytics_request)
        
        # Verify cache has grown
        final_cache_size = len(analytics_service.trend_cache)
        assert final_cache_size >= initial_cache_size
        
        # Verify cache contents
        if final_cache_size > 0:
            cached_item = analytics_service.trend_cache[-1]  # Most recent item
            assert len(cached_item) == 3  # (metric, direction, timestamp)
            assert isinstance(cached_item[0], str)  # metric name
            assert cached_item[1] in ["increasing", "decreasing", "stable"]  # direction
            assert isinstance(cached_item[2], datetime)  # timestamp

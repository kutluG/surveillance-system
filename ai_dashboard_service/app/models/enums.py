"""
Enumerations for AI Dashboard Service

This module contains all enumeration definitions used across the AI Dashboard
application. These enums provide type-safe constants for various operations
including analytics types, time ranges, widget types, and prediction categories.

The enums inherit from both str and Enum to provide string representation
while maintaining type safety and IDE support. They are used throughout
the application for request validation, service operations, and API responses.

Classes:
    AnalyticsType: Types of analytics operations available
    TimeRange: Predefined time ranges for data analysis
    WidgetType: Available dashboard widget types
    PredictionType: Categories of predictive analytics
"""

from enum import Enum


class AnalyticsType(str, Enum):
    """
    Analytics operation types for surveillance data processing.
    
    Defines the available types of analytics operations that can be performed
    on surveillance data. Each type corresponds to a specific analysis method
    with different algorithms and output formats.
    
    Values:
        TREND_ANALYSIS: Statistical trend analysis using regression
        ANOMALY_DETECTION: Outlier detection using statistical methods
        PREDICTIVE_FORECAST: Future prediction using ML models
        PATTERN_RECOGNITION: Pattern identification in data
        PERFORMANCE_METRICS: System performance analysis
    """
    TREND_ANALYSIS = "trend_analysis"
    ANOMALY_DETECTION = "anomaly_detection"
    PREDICTIVE_FORECAST = "predictive_forecast"
    PATTERN_RECOGNITION = "pattern_recognition"
    PERFORMANCE_METRICS = "performance_metrics"


class TimeRange(str, Enum):
    """
    Predefined time ranges for analytics and reporting operations.
    
    Provides standard time periods for data analysis and reporting.
    These ranges are used throughout the application for consistent
    time-based filtering and analysis operations.
    
    Values:
        LAST_HOUR: Data from the past hour
        LAST_24_HOURS: Data from the past 24 hours
        LAST_WEEK: Data from the past week
        LAST_MONTH: Data from the past month
        CUSTOM: User-defined time range with custom start/end
    """
    LAST_HOUR = "last_hour"
    LAST_24_HOURS = "last_24_hours"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    CUSTOM = "custom"


class WidgetType(str, Enum):
    """
    Dashboard widget types for visualization and display.
    
    Defines the available widget types that can be displayed on
    surveillance dashboards. Each type provides different visualization
    capabilities and data presentation formats.
    
    Values:
        CHART: Line, bar, or pie charts for metrics
        MAP: Geographic or floor plan visualizations
        TABLE: Tabular data display with sorting/filtering
        METRIC: Single value displays with status indicators
        TIMELINE: Time-based event visualization
        HEATMAP: Density visualization for activity patterns
        ALERT_FEED: Real-time alert notification display
    """
    CHART = "chart"
    MAP = "map"
    TABLE = "table"
    METRIC = "metric"
    TIMELINE = "timeline"
    HEATMAP = "heatmap"
    ALERT_FEED = "alert_feed"


class PredictionType(str, Enum):
    """
    Prediction categories for predictive analytics operations.
    
    Defines the types of predictions that can be generated using
    machine learning models and statistical analysis. Each type
    uses specialized algorithms optimized for specific scenarios.
    
    Values:
        SECURITY_THREAT: Threat level prediction based on patterns
        EQUIPMENT_FAILURE: Equipment failure forecasting
        TRAFFIC_PATTERN: Traffic flow and pattern prediction
        OCCUPANCY_LEVEL: Space occupancy level forecasting
    """
    SECURITY_THREAT = "security_threat"
    EQUIPMENT_FAILURE = "equipment_failure"
    TRAFFIC_PATTERN = "traffic_pattern"
    OCCUPANCY_LEVEL = "occupancy_level"

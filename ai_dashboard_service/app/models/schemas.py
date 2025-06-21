"""
Pydantic schemas for AI Dashboard Service

Contains all request/response models and data structures.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pydantic import BaseModel

from .enums import AnalyticsType, TimeRange, WidgetType, PredictionType


# Data Classes
@dataclass
class AnalyticsInsight:
    """
    Analytics insight data structure for surveillance intelligence.
    
    Represents a single insight generated from surveillance data analysis,
    including AI-powered recommendations and impact assessment. Used throughout
    the analytics pipeline for insight storage and presentation.
    
    Attributes:
        id: Unique identifier for the insight
        type: Analytics type that generated this insight
        title: Human-readable insight title
        description: Detailed insight description
        confidence: Confidence score (0.0 to 1.0)
        timestamp: When the insight was generated
        data: Raw data supporting the insight
        recommendations: List of actionable recommendations
        impact_level: Impact severity (low, medium, high, critical)
    """
    id: str
    type: AnalyticsType
    title: str
    description: str
    confidence: float
    timestamp: datetime
    data: Dict[str, Any]
    recommendations: List[str]
    impact_level: str  # low, medium, high, critical


@dataclass
class PredictiveModel:
    """
    Predictive model metadata and performance information.
    
    Stores information about machine learning models used for predictive
    analytics, including performance metrics, training status, and
    prediction capabilities. Used for model management and selection.
    
    Attributes:
        id: Unique model identifier
        name: Human-readable model name
        description: Model description and use case
        type: Type of predictions this model generates
        accuracy: Model accuracy score (0.0 to 1.0)
        last_trained: Timestamp of last training session
        parameters: Model hyperparameters and configuration
        predictions: Recent prediction results for validation
    """
    id: str
    name: str
    description: str
    type: PredictionType
    accuracy: float
    last_trained: datetime
    parameters: Dict[str, Any]
    predictions: List[Dict]


@dataclass
class DashboardWidget:
    """
    Dashboard widget configuration and metadata.
    
    Defines the structure and behavior of dashboard widgets including
    visualization type, data sources, refresh intervals, and layout
    configuration. Used for dynamic dashboard generation and customization.
    
    Attributes:
        id: Unique widget identifier
        type: Widget visualization type
        title: Widget display title
        description: Widget description for tooltips
        configuration: Widget-specific configuration options
        data_source: Source of data for the widget
        refresh_interval: Auto-refresh interval in seconds
        filters: Data filtering configuration
        layout: Widget positioning and sizing information
    """
    id: str
    type: WidgetType
    title: str
    description: str
    configuration: Dict[str, Any]
    data_source: str
    refresh_interval: int  # seconds
    filters: Dict[str, Any]
    layout: Dict[str, Any]


@dataclass
class TrendAnalysis:
    """
    Trend analysis result from statistical processing.
    
    Contains the results of trend analysis performed on surveillance metrics,
    including direction, magnitude, and contributing factors. Used for
    identifying patterns and changes in surveillance data over time.
    
    Attributes:
        metric: Name of the analyzed metric
        direction: Trend direction (increasing, decreasing, stable)
        magnitude: Numerical measure of trend strength
        confidence: Statistical confidence in the trend (0.0 to 1.0)
        timeframe: Time period analyzed for the trend
        contributing_factors: List of factors influencing the trend
    """
    metric: str
    direction: str  # increasing, decreasing, stable
    magnitude: float
    confidence: float
    timeframe: str
    contributing_factors: List[str]


@dataclass
class AnomalyDetection:
    """
    Anomaly detection result from statistical analysis.
    
    Represents a detected anomaly in surveillance data, including the
    deviation from expected values and severity assessment. Used for
    alerting and investigation of unusual patterns or events.
    
    Attributes:
        id: Unique anomaly identifier
        timestamp: When the anomaly was detected
        metric: Name of the metric showing anomalous behavior
        expected_value: Statistically expected value
        actual_value: Actual observed value
        deviation: Numerical deviation from expected
        severity: Severity level (low, medium, high, critical)
        description: Human-readable anomaly description
    """
    id: str
    timestamp: datetime
    metric: str
    expected_value: float
    actual_value: float
    deviation: float
    severity: str
    description: str


# Request/Response Models
class AnalyticsRequest(BaseModel):
    """
    Request model for analytics operations.
    
    Pydantic model for validating analytics requests including time ranges,
    filters, and operation parameters. Used by API endpoints to ensure
    proper request formatting and parameter validation.
    
    Attributes:
        analytics_type: Type of analytics operation to perform
        time_range: Predefined time range for data analysis
        custom_start: Custom start time (required if time_range is CUSTOM)
        custom_end: Custom end time (required if time_range is CUSTOM)
        filters: Additional filters for data selection
        parameters: Analytics-specific parameters and configuration
    """
    analytics_type: AnalyticsType
    time_range: TimeRange
    custom_start: Optional[datetime] = None
    custom_end: Optional[datetime] = None
    filters: Dict[str, Any] = {}
    parameters: Dict[str, Any] = {}


class PredictionRequest(BaseModel):
    """
    Request model for predictive analytics operations.
    
    Validates requests for generating predictions using machine learning
    models. Includes parameters for forecast horizon, confidence thresholds,
    and recommendation generation preferences.
    
    Attributes:
        prediction_type: Category of prediction to generate
        forecast_horizon: How far into the future to predict (hours)
        confidence_threshold: Minimum confidence for prediction results
        include_recommendations: Whether to include actionable recommendations
    """
    prediction_type: PredictionType
    forecast_horizon: int = 24  # hours
    confidence_threshold: float = 0.7
    include_recommendations: bool = True


class ReportGenerationRequest(BaseModel):
    """
    Request model for report generation operations.
    
    Validates requests for generating intelligent surveillance reports.
    Supports multiple report types, time ranges, custom sections, and
    output formats for comprehensive reporting capabilities.
    
    Attributes:
        report_type: Type of report to generate (security, performance, etc.)
        time_range: Time range for report data collection
        custom_start: Custom start time for report period
        custom_end: Custom end time for report period
        sections: Specific report sections to include
        format: Output format (html, pdf, json)
    """
    report_type: str
    time_range: TimeRange
    custom_start: Optional[datetime] = None
    custom_end: Optional[datetime] = None
    sections: List[str] = []
    format: str = "html"  # html, pdf, json


class WidgetRequest(BaseModel):
    """
    Request model for dashboard widget creation and management.
    
    Validates requests for creating or updating dashboard widgets including
    widget type, configuration, and filtering options. Used by dashboard
    management endpoints for widget lifecycle operations.
    
    Attributes:
        widget_type: Type of widget to create
        title: Widget display title
        description: Widget description for UI tooltips
        configuration: Widget-specific configuration settings
        filters: Data filtering configuration for the widget
    """
    widget_type: WidgetType
    title: str
    description: str
    configuration: dict
    filters: dict = {}
